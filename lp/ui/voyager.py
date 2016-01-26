import copy
import difflib
import re
import urllib
import urlparse

import pycountry
import pymarc
from PyZ3950 import zoom

from django.conf import settings
from django.db import connection
from django.utils.encoding import smart_str, DjangoUnicodeDecodeError

from ui import apis
from ui import marc
from ui import z3950
from ui.templatetags.launchpad_extras import cjk_info
from ui.templatetags.launchpad_extras import clean_isbn
from ui.templatetags.launchpad_extras import clean_lccn
from ui.templatetags.launchpad_extras import clean_oclc
from django.utils.encoding import iri_to_uri
from django.utils.http import urlquote

GW_LIBRARY_IDS = [7, 11, 18, 21]


def _make_dict(cursor, first=False):
    desc = cursor.description
    mapped = [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]
    # strip string values of trailing whitespace
    for d in mapped:
        for k, v in d.items():
            try:
                d[k] = smart_str(v.strip())
            except:
                pass
    if first:
        if len(mapped) > 0:
            return mapped[0]
        return {}
    return mapped


def get_added_authors(bib):
    """Starting with the main author entry, build up a list of all authors."""
    query = """
SELECT bib_index.display_heading AS author
FROM bib_index
WHERE bib_index.bib_id = %s
AND bib_index.index_code IN ('700H', '710H', '711H')"""
    cursor = connection.cursor()
    cursor.execute(query, [bib['BIB_ID']])
    authors = []
    if bib['AUTHOR']:
        authors.append(bib['AUTHOR'])
    
    while True:
        try:
            row = cursor.fetchone()
            if row:
                authors.append(smart_str(row[0]))
            else:
                break
        except DjangoUnicodeDecodeError:
            continue 
 
    # trim whitespace
    if not authors:
        return []
    for i in range(len(authors)):
        author = authors[i].strip()
        if author.endswith('.'):
            author = author[:-1]
        authors[i] = author
    # remove duplicates
    #for author in authors:
    #    while authors.count(author) > 1:
    #        authors.remove(author)
    return authors


def get_all_bibs(bibids):
    bibs = []
    for bib in bibids:
        bibs.append(bib['BIB_ID'])
    return bibs


def get_marc_blob(bibid):
    query = """
SELECT wrlcdb.getBibBlob(%s) AS marcblob
from bib_master"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    row = cursor.fetchone()
    raw_marc = str(row[0])
    rec = pymarc.record.Record(data=raw_marc)
    return rec


def get_bib_data(bibid, expand_ids=True, exclude_names=False):
    query = """
SELECT bib_text.bib_id, lccn,
       edition, isbn, issn, network_number AS OCLC,
       pub_place, imPrint, bib_format,
       language, library_name, publisher_date,
       RTRIM(wrlcdb.GetMarcField(%s,0,0,'856','','u',1)) AS LINK,
       RTRIM(wrlcdb.GetMarcField(%s,0,0,'856','','z',1)) AS MESSAGE,
       wrlcdb.GetAllBibTag(%s, '880', 1) AS CJK_INFO,
       wrlcdb.GetBibTag(%s, '006') AS MARC006,
       wrlcdb.GetBibTag(%s, '007') AS MARC007,
       wrlcdb.GetBibTag(%s, '008') AS MARC008"""
    if not exclude_names:
        query += """
,title, author, publisher,
RTRIM(wrlcdb.GetMarcField(%s,0,0,'245','','',1)) AS TITLE_ALL
        """
    query += """
FROM bib_text, bib_master, library
WHERE bib_text.bib_id=%s
AND bib_text.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'"""
    cursor = connection.cursor()
    paramcount = 8 if not exclude_names else 7
    cursor.execute(query, [bibid] * paramcount)
    rec = get_marc_blob(bibid)
    bib = {}
    try:
        if exclude_names:
            bib['TITLE'] = rec.title()
            bib['AUTHOR'] = rec.author()
            bib['PUBLISHER'] = rec.publisher()
            title_fields = rec.get_fields('245')
            bib['LIBRARY_NAME'] = get_library_name(bibid)
            bib['TITLE_ALL'] = ''
            bib['BIB_FORMAT'] = ''
            bib['BIB_ID'] = bibid
            for title in title_fields:
                bib['TITLE_ALL'] += title.format_field().decode('iso-8859-1')\
                    .encode('utf-8')
        else:
            bib = _make_dict(cursor, first=True)
    except DjangoUnicodeDecodeError:
        return get_bib_data(bibid=bibid, expand_ids=expand_ids,
                            exclude_names=True)
    # if bib is empty, there's no match -- return immediately
    if not bib:
        return None
    if bib.get('LCCN'):
        bib['LCCN'] = clean_lccn(bib['LCCN'])
    # ensure the NETWORK_NUMBER is OCLC
    if not bib.get('OCLC', '') or not _is_oclc(bib.get('OCLC', '')):
        bib['OCLC'] = ''
    # get additional authors; main entry is AUTHOR, all are AUTHORS
    bib['AUTHORS'] = get_added_authors(bib)
    # split up the 880 (CJK) fields/values if available
    if bib.get('CJK_INFO', ''):
        bib['CJK_INFO'] = cjk_info(bib['CJK_INFO'])
    if not exclude_names:
        bib['TITLE_ALL'] = clean_title(bib['TITLE_ALL'][7:])
    if len(bib['TITLE_ALL']) > settings.TITLE_CHARS:
        brief = bib['TITLE_ALL'][:settings.TITLE_CHARS]
        ind = brief.rfind(' ')
        if ind == -1:
            ind = settings.TITLE_CHARS
        bib['TITLE_BRIEF'] = brief[0:ind]
        bib['BRIEF_LENGTH'] = len(bib['TITLE_ALL']) - len(bib['TITLE_BRIEF'])
    try:
        language = pycountry.languages.get(bibliographic=bib['LANGUAGE'])
        bib['LANGUAGE_DISPLAY'] = language.name
    except:
        bib['LANGUAGE_DISPLAY'] = ''
    if expand_ids:
        bibids = [
            {'BIB_ID': bib['BIB_ID'], 'LIBRARY_NAME':bib['LIBRARY_NAME']}]
        for num_type in ['isbn', 'issn', 'oclc', 'lccn']:
            if bib.get(num_type.upper(), ''):
                norm_set, disp_set = set(), set()
                std_nums = get_related_std_nums(bib['BIB_ID'], num_type)
                if std_nums:
                    norm, disp = zip(*std_nums)
                    norm_set.update(norm)
                    disp_set.update([num.strip() for num in disp])
                    bib['NORMAL_%s_LIST' % num_type.upper()] = list(norm_set)
                    bib['DISPLAY_%s_LIST' % num_type.upper()] = list(disp_set)
                    # use std nums to get related bibs
                    new_bibids = get_related_bibids(norm, num_type,
                                                    bib.get('TITLE', ''))
                    for nb in new_bibids:
                        if nb['BIB_ID'] not in [x['BIB_ID'] for x in bibids]:
                            bibids.append(nb)
        bib['BIB_ID_LIST'] = list(bibids)
    # parse fields for microdata
    bib['MICRODATA_TYPE'] = get_microdata_type(bib)
    if bib.get('LINK') \
            and bib.get('MESSAGE', '') == '856:42:$zCONNECT TO FINDING AID':
        bib['FINDING_AID'] = bib['LINK'][9:]
    marc.extract(rec, bib)
    return bib


def _is_oclc(num):
    if num.find('OCoLC') >= 0:
        return True
    if num.find('ocn') >= 0:
        return True
    if num.find('ocm') >= 0:
        return True
    return False


def get_microdata_type(bib):
    output = 'http://schema.org/'
    format = bib.get('BIB_FORMAT', '')
    if format == 'am':
        return output + 'Book'
    if len(bib.get('DISPLAY_ISBN_LIST', '')) > 0:
        return output + 'Book'
    return output + 'CreativeWork'


def get_primary_bibid(num, num_type):
    num = _normalize_num(num, num_type)
    query = """
SELECT bib_index.bib_id, bib_master.library_id, library.library_name,
    bib_index.normal_heading, bib_index.display_heading
FROM bib_index, bib_master, library
WHERE bib_index.index_code IN (%s)
AND bib_index.normal_heading = '%s'
AND bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac = 'N'
AND ROWNUM < 7"""
    cursor = connection.cursor()
    query = query % (_in_clause(settings.INDEX_CODES[num_type]), num)
    cursor.execute(query, [])
    bibs = _make_dict(cursor)
    if num_type == 'oclc':
        bibs = [b for b in bibs if b['NORMAL_HEADING'] != b['DISPLAY_HEADING']]
    for bib in bibs:
        if bib['LIBRARY_NAME'] == settings.PREF_LIB:
            return bib['BIB_ID']
    return bibs[0]['BIB_ID'] if bibs else None


def get_library_name(bibid):
    query = """
SELECT library_name
FROM bib_master, library
WHERE bib_master.bib_id = %s
AND bib_master.library_id=library.library_id"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    result = _make_dict(cursor)
    return result[0]['LIBRARY_NAME']

def get_item_recalls(itemid):
    query = """
SELECT Count(hold_recall_items.item_id) AS recalls
FROM hold_recall_items
GROUP BY hold_recall_items.item_id
HAVING hold_recall_items.item_id = %s """
    cursor = connection.cursor()
    cursor.execute(query, [itemid])
    result = _make_dict(cursor)
    return result[0]['RECALLS'] if result else 0

def _normalize_num(num, num_type):
    if num_type == 'isbn':
        return clean_isbn(num)
    elif num_type == 'issn':
        return num.replace('-', ' ')
    elif num_type == 'oclc':
        return clean_oclc(num)
    return num


def get_related_bibids(num_list, num_type, title):
    query = [None] * 7
    query[0] = """
SELECT DISTINCT bib_index.bib_id,
       bib_index.display_heading,
       library.library_name
FROM bib_index, library, bib_master
WHERE bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'
AND bib_index.index_code IN (%s)
AND bib_index.normal_heading != 'OCOLC'"""
    query[1] = """
AND UPPER(bib_index.display_heading) NOT LIKE %s
AND UPPER(bib_index.display_heading) NOT LIKE %s"""
    query[2] = """
AND bib_index.normal_heading IN (
    SELECT bib_index.normal_heading
    FROM bib_index
    WHERE bib_index.index_code IN (%s)"""
    if num_type == 'oclc':
        query[2] = query[2] + """
    AND bib_index.normal_heading != bib_index.display_heading"""
    query[3] = """
    AND UPPER(bib_index.display_heading) NOT LIKE %s
    AND UPPER(bib_index.display_heading) NOT LIKE %s
    AND ROWNUM < 7"""
    query[4] = """
    AND bib_id IN (
        SELECT DISTINCT bib_index.bib_id
        FROM bib_index
        WHERE bib_index.index_code IN (%s)
        AND bib_index.normal_heading IN (%s)
        AND bib_index.normal_heading != 'OCOLC'"""
    if num_type == 'oclc':
        query[4] = query[4] + """
        AND bib_index.normal_heading != bib_index.display_heading"""
    query[5] = """
        AND UPPER(bib_index.display_heading) NOT LIKE %s
        AND UPPER(bib_index.display_heading) NOT LIKE %s"""
    query[6] = """
        )
    )
ORDER BY bib_index.bib_id"""
    indexclause = _in_clause(settings.INDEX_CODES[num_type])
    numclause = _in_clause(num_list)
    likeclause1 = '%' + 'SET' + '%'
    likeclause2 = '%' + 'SER' + '%'
    query[0] = query[0] % indexclause
    query[2] = query[2] % indexclause
    query[4] = query[4] % (indexclause, numclause)
    query = ''.join(query)
    args = [likeclause1, likeclause2] * 3
    cursor = connection.cursor()
    cursor.execute(query, args)
    results = _make_dict(cursor)
    for row in results[:]:
        if title is None:
            title = ''
        result = get_title(row['BIB_ID'])
        new_title = result.get('TITLE', '')
        # remove the holding if titles are different. No more than 8 chars
        if new_title is None:
            continue
        if title[0:8].lower() != new_title[0:8].lower():
            results.remove(row)
    output_keys = ('BIB_ID', 'LIBRARY_NAME')
    if num_type == 'oclc':
        return [dict([
            (k, row[k]) for k in output_keys]) for row in
            results if _is_oclc(row['DISPLAY_HEADING'])]
    return [dict([(k, row[k]) for k in output_keys]) for row in results]


def get_related_isbns(bibs):
    query = """
SELECT bib_index.display_heading
    FROM bib_index
    WHERE bib_index.bib_id IN (%s)
    AND bib_index.index_code IN (%s)
    AND ROWNUM < 7
    ORDER BY bib_index.display_heading"""
    indexclause = _in_clause(settings.INDEX_CODES['isbn'])
    numclause = _in_clause(bibs)
    cursor = connection.cursor()
    #args = [numclause, indexclause]
    query = query % (numclause, indexclause)
    cursor.execute(query, [])
    results = cursor.fetchall()
    return [(clean_isbn(p[0])) for p in results]


def get_title(bibid):
    query = """
    SELECT TITLE FROM bib_text
    WHERE bib_text.bib_id = %s"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    result = _make_dict(cursor, first=True)
    return result


def get_related_std_nums(bibid, num_type):
    query = """
SELECT normal_heading, display_heading
FROM bib_index
INNER JOIN bib_master ON bib_index.bib_id = bib_master.bib_id
WHERE bib_index.index_code IN (%s)
AND bib_index.bib_id = %s
AND bib_index.normal_heading != 'OCOLC'
AND bib_master.suppress_in_opac='N'"""
    if num_type == 'oclc':
        query = query + """
AND bib_index.normal_heading != bib_index.display_heading"""
    query = query + """
AND ROWNUM < 7
ORDER BY bib_index.normal_heading"""
    query = query % (_in_clause(settings.INDEX_CODES[num_type]), bibid)
    cursor = connection.cursor()
    cursor.execute(query, [])
    results = cursor.fetchall()
    # cull out ISBNs for sets of books
    results = [pair for pair in results if 'SET' not in pair[0].upper()]
    if num_type == 'oclc':
        return [pair for pair in results if _is_oclc(pair[1])]
    if num_type == 'issn':
        return [pair for pair in results if _is_valid_issn(pair[0])]
    if num_type == 'isbn':
        return [(clean_isbn(p[0]), clean_isbn(p[1])) for p in results]
    return results


def _is_valid_issn(num):
    if re.match('\d{4}[ -]\d{3}[0-9xX]', num):
        return True
    return False


def get_holdings(bib_data, lib=None, translate_bib=True):
    done = []
    query = """
SELECT bib_mfhd.bib_id, mfhd_master.mfhd_id, mfhd_master.location_id,
       mfhd_master.display_call_no, location.location_display_name,
       library.library_name, location.location_name
FROM bib_mfhd
INNER JOIN mfhd_master ON bib_mfhd.mfhd_id = mfhd_master.mfhd_id,
     location, library,bib_master
WHERE mfhd_master.location_id=location.location_id
AND bib_mfhd.bib_id IN (%s)
AND mfhd_master.suppress_in_opac !='Y'
AND bib_mfhd.bib_id = bib_master.bib_id
AND bib_master.library_id=library.library_id
ORDER BY library.library_name"""
    if bib_data.get('BIB_ID_LIST', []):
        idclause = _in_clause([b['BIB_ID'] for b in bib_data['BIB_ID_LIST']])
    else:
        idclause = "'%s'" % bib_data['BIB_ID']
    query = query % idclause
    cursor = connection.cursor()
    if not lib:
        cursor.execute(query, [])
        holdings = _make_dict(cursor)
    if not translate_bib:
        holdings = init_z3950_holdings(bib_data['BIB_ID'], lib)
    illiad_link = get_illiad_link(bib_data)
    try:
        refworks_link = get_refworks_link(bib_data)
        bib_data.update({'REFWORKS_LINK': refworks_link})
    except:
        bib_data.update({'REFWORKS_LINK': ''})
    eligibility = False
    added_holdings = []
    for holding in holdings:
        HI_link = ''
        if (holding['LIBRARY_NAME'] == 'GM' or
                holding['LIBRARY_NAME'] == 'GT' or
                holding['LIBRARY_NAME'] == 'DA'):
            if holding['BIB_ID'] in done:
                continue
            else:
                done.append(holding['BIB_ID'])
            result = get_z3950_holdings(holding['BIB_ID'],
                                        holding['LIBRARY_NAME'], 'bib',
                                        '', bib_data, translate_bib)
            if len(result) > 0:
                if (len(result[0]['items']) == 0 and
                        len(result[0]['mfhd']['marc856list']) == 0 and
                        len(result[0]['mfhd']['marc866list']) == 0 and
                        result[0]['mfhd']['marc852'] == ''):
                    continue
                holding.update({'MFHD_DATA': result[0]['mfhd'],
                                'ITEMS': result[0]['items'],
                                'ELECTRONIC_DATA': result[0]['electronic'],
                                'AVAILABILITY': result[0]['availability']})
            if len(result) > 1 and holding['LIBRARY_NAME'] == 'GM':
                for item in get_additional_holdings(result, holding):
                    added_holdings.append(item)
            if len(result) == 0:
                holding.update({'MFHD_DATA': {},
                                'ITEMS': [],
                                'AVAILABILITY': {},
                                'ELECTRONIC_DATA': {}})
                holding['REMOVE'] = True
            if len(result) > 0:
                if holding.get('AVAILABILITY', {}).get('PERMLOCATION', ''):
                    holding['LOCATION_DISPLAY_NAME'] = \
                        holding['AVAILABILITY']['PERMLOCATION']
                else:
                    holding['LOCATION_DISPLAY_NAME'] = \
                        holding.get('LIBRARY_NAME', '')
                holding['DISPLAY_CALL_NO'] = \
                    holding['AVAILABILITY']['DISPLAY_CALL_NO']
        else:
            if holding['LIBRARY_NAME'] == 'HI':
                # check for eresource link on the bib linked to this holding
                HI_link = get_himmelfarb_bib_and_link(holding['MFHD_ID'])
            holding.update({'ELECTRONIC_DATA':
                            get_electronic_data(holding['MFHD_ID']),
                            'AVAILABILITY':
                            get_items(holding['MFHD_ID'], first=True)})
            holding.update({'MFHD_DATA': get_mfhd_data(holding['MFHD_ID']),
                            'ITEMS': get_items(holding['MFHD_ID'])}),
            if HI_link and not holding['ELECTRONIC_DATA']['LINK856U']:
                    holding['ELECTRONIC_DATA']['LINK856U'] = HI_link
                    HI_link = ''
        if holding.get('ITEMS', []):
            i = 0
            for item in holding['ITEMS']:
                if 'DUE' in item and item['DUE'] is not None:
                    item['ITEM_STATUS_DESC'] = 'DUE ' + item['DUE']
                if item['ITEM_STATUS_DESC'] == 'Charged':
                    item['ITEM_STATUS_DESC'] = 'Checked out'
                if item['ITEM_STATUS_DESC'] == 'Discharged':
                    item['ITEM_STATUS_DESC'] = 'Recently Returned'
                item['ELIGIBLE'] = \
                    is_item_eligible(item, holding.get('LIBRARY_NAME', ''))
                if lib is not None:
                    item['ELIGIBLE'] = False
                item['LIBRARY_FULL_NAME'] = \
                    settings.LIB_LOOKUP[holding['LIBRARY_NAME']]
                item['TRIMMED_LOCATION_DISPLAY_NAME'] = \
                    trim_item_display_name(item)
                item['TEMPLOCATION'] = trim_item_temp_location(item)
                # WRLC items have an id, check if there are recall notices 
                if item['ITEM_ID'] is not 0:
                    item['RECALLS'] = get_item_recalls(item['ITEM_ID'])
                else:
                    item['RECALLS'] = 0
                remove_duplicate_items(i, holding['ITEMS'])
                i = i + 1
            holding['LIBRARY_FULL_NAME'] = \
                holding['ITEMS'][0]['LIBRARY_FULL_NAME']
        holding.update({'ELIGIBLE': is_eligible(holding)})
        holding.update({'LIBRARY_HAS': get_library_has(holding)})
        holding['LIBRARY_FULL_NAME'] = \
            settings.LIB_LOOKUP[holding['LIBRARY_NAME']]
        holding['TRIMMED_LOCATION_DISPLAY_NAME'] = trim_display_name(holding)
        if (holding['LIBRARY_NAME'] == 'HU' and
                holding['LOCATION_NAME'] == 'hu link'):
            holding['REMOVE'] = True
        if (holding['LIBRARY_NAME'] == 'HS' and
                holding['LOCATION_NAME'] == 'hs link'):
            holding['REMOVE'] = True
        if holding['TRIMMED_LOCATION_DISPLAY_NAME'] == ' Online' \
                and holding['ELECTRONIC_DATA']['LINK856U'] is None \
                and len(holding['ITEMS']) == 0:
            holding['REMOVE'] = True
    for item in added_holdings:
        holdings.append(item)
    for holding in holdings:
        i = 0
        if holding.get('AVAILABILITY'):
            if holding['AVAILABILITY'].get('ITEM_STATUS_DESC'):
                if holding['AVAILABILITY']['ITEM_STATUS_DESC'] == 'Charged':
                    holding['AVAILABILITY']['ITEM_STATUS_DESC'] = 'Checked out'
                if holding['AVAILABILITY']['ITEM_STATUS_DESC'] == 'Discharged':
                    holding['AVAILABILITY']['ITEM_STATUS_DESC'] =\
                        'Recently Returned'
        for item in holding.get('ITEMS', []):
            if item['ELIGIBLE'] is True:
                eligibility = True
            remove_duplicate_items(i, holding['ITEMS'])
            i = i + 1
        if holding.get('ITEMS'):
            for item in holding['ITEMS'][:]:
                if 'REMOVE' in item:
                    holding['ITEMS'].remove(item)
    if eligibility is False or bib_data['BIB_FORMAT'] == 'as':
        bib_data.update({'ILLIAD_LINK': illiad_link})
    else:
        bib_data.update({'ILLIAD_LINK': ''})
    holdings = correct_gt_holding(holdings)
    # get 360Link API information where possible
    for holding in holdings:
        holding['LinkResolverData'] = []
        links = holding.get('MFHD_DATA', {}).get('marc856list', [])
        for link in links:
            url = link.get('u', '').lower()
            if url.startswith('http://sfx.wrlc.org/gw') or \
                    url.startswith('http://findit.library.gwu.edu/go'):
                issnindex = url.lower().find('issn=')
                if issnindex > -1:
                    num_type = 'issn'
                    num = url[issnindex + 5:]
                    stop = num.find('&')
                    num = num[:stop] if stop > -1 else num
                else:
                    isbnindex = url.lower().find('isbn=')
                    if isbnindex > -1:
                        num_type = 'isbn'
                        num = url[isbnindex + 5:]
                        stop = num.find('&')
                        num = num[:stop] if stop > -1 else num
                if 'num' in locals():
                    linkdata = apis.sersol360link(num, num_type)
                    for ld in linkdata:
                        holding['LinkResolverData'].append(ld)
    # get free electronic book link from open library and/or hathi trust
    for numformat in ('LCCN', 'ISBN', 'OCLC'):
        if bib_data.get(numformat):
            if numformat == 'OCLC':
                num = filter(lambda x: x.isdigit(), bib_data[numformat])
            # check if key exists before using it
            elif numformat == 'ISBN' and \
                    'NORMAL_ISBN_LIST' in bib_data and \
                    len(bib_data['NORMAL_ISBN_LIST']) > 0:
                num = bib_data['NORMAL_ISBN_LIST'][0]
            else:
                num = bib_data[numformat]

            # Internet Archive / Open Library
            openlibhold = apis.openlibrary(num, numformat)
            title = ''
            if openlibhold.get('MFHD_DATA', None):
                title = get_open_library_item_title(openlibhold['MFHD_DATA']
                                                    ['marc856list'][0]['u'])
            if openlibhold:
                # Compare the title. Can't trust Open Library match.
                bib_title = bib_data['TITLE'][0:10].lower()
                open_title = title[0:10].lower()
                ratio = difflib.SequenceMatcher(None, bib_title,
                                                open_title).ratio()
                if ratio >= settings.TITLE_SIMILARITY_RATIO:
                    holdings.append(openlibhold)
                    
            # HathiTrust. No need to check title, and OCLC match is sufficient. 
            if numformat == 'OCLC': 
                hathitrusthold = apis.hathitrust(num, numformat)
                if hathitrusthold:
                    holdings.append(hathitrusthold)
    
    for holding in holdings:
        dda_isbn = bib_data.get('ISBN', '')
        dda_title = bib_data.get('TITLE','')
        holding['ONLINE'] = get_links(holding, dda_isbn, dda_title)
 
    return [h for h in holdings if not h.get('REMOVE', False)]


def get_open_library_item_title(link):
    index = link.rfind('/')
    title = link[index+1:]
    title = title.replace("_", " ")
    return title


def init_z3950_holdings(bibid, lib):
    holdings = []
    data = {}
    data['MFHD_ID'] = ''
    data['LIBRARY_NAME'] = lib
    data['LOCATION_NAME'] = ''
    data['LOCATION_DISPLAY_NAME'] = ''
    data['LOCATION_ID'] = 0
    data['BIB_ID'] = bibid
    data['DISPLAY_CALL_NO'] = ''
    holdings.append(data)
    return holdings


def get_additional_holdings(result, holding):
    i = 1
    added_holdings = []
    item = {}
    while i < len(result):
        item = copy.deepcopy(holding)
        item.update({'MFHD_DATA': result[i]['mfhd'],
                     'ITEMS': result[i]['items'],
                     'ELECTRONIC_DATA': result[i]['electronic'],
                     'AVAILABILITY': result[i]['availability']})
        if item.get('AVAILABILITY', {}).get('PERMLOCATION', ''):
            item['LOCATION_DISPLAY_NAME'] = \
                item['AVAILABILITY']['PERMLOCATION']
        else:
            item['LOCATION_DISPLAY_NAME'] = item['LIBRARY_NAME']
        item['DISPLAY_CALL_NO'] = item['AVAILABILITY']['DISPLAY_CALL_NO']
        if item.get('ITEMS'):
            for it in item['ITEMS']:
                it['ELIGIBLE'] = \
                    is_item_eligible(it, item.get('LIBRARY_NAME', ''))
                it['LIBRARY_FULL_NAME'] = \
                    settings.LIB_LOOKUP[item['LIBRARY_NAME']]
                it['TRIMMED_LOCATION_DISPLAY_NAME'] = \
                    trim_item_display_name(it)
            item['LIBRARY_FULL_NAME'] = item['ITEMS'][0]['LIBRARY_FULL_NAME']
        item.update({'ELIGIBLE': is_eligible(item)})
        item.update({'LIBRARY_HAS': get_library_has(item)})
        item['LIBRARY_FULL_NAME'] = settings.LIB_LOOKUP[item['LIBRARY_NAME']]
        item['TRIMMED_LOCATION_DISPLAY_NAME'] = trim_display_name(item)
        added_holdings.append(item)
        i = i + 1
    return added_holdings


def remove_duplicate_items(i, items):
    #check if the item has already been processed
    if items[i].get('REMOVE'):
        return
    j = i + 1
    while j < len(items):
        if items[i]['ITEM_ID'] == items[j]['ITEM_ID']:
            if 'ITEM_STATUS_DATE' in items[i] and\
                    'ITEM_STATUS_DATE' in items[j]:
                if items[i]['ITEM_STATUS_DATE'] is not None and\
                        items[j]['ITEM_STATUS_DATE'] is not None:
                    if items[i]['ITEM_STATUS_DATE'] >\
                            items[j]['ITEM_STATUS_DATE']\
                            and items[j]['ITEM_STATUS'] <= 11:
                        items[j]['REMOVE'] = True
                    elif items[j]['ITEM_STATUS'] > 11 and\
                            items[i]['ITEM_STATUS'] <= 11:
                        items[i]['REMOVE'] = True
                if items[j]['ITEM_STATUS_DATE'] is None:
                    items[j]['REMOVE'] = True
                elif items[i]['ITEM_STATUS_DATE'] is None:
                    items[i]['REMOVE'] = True
                elif (items[i]['ITEM_STATUS_DATE'] >
                        items[j]['ITEM_STATUS_DATE']) and\
                        items[j]['ITEM_STATUS'] <= 11:
                    items[j]['REMOVE'] = True
                elif (items[j]['ITEM_STATUS_DATE'] >
                        items[i]['ITEM_STATUS_DATE']) and\
                        items[i]['ITEM_STATUS'] <= 11:
                    items[i]['REMOVE'] = True
                elif (items[j]['ITEM_STATUS_DATE'] ==
                        items[i]['ITEM_STATUS_DATE']) and\
                        items[i]['ITEM_STATUS'] <= 11 and\
                        items[i]['ITEM_STATUS'] <= 11:
                    items[j]['REMOVE'] = True

        j = j + 1


def trim_display_name(holding):
    index = holding['LOCATION_DISPLAY_NAME'].find(':')
    if index == 2:
        return holding['LOCATION_DISPLAY_NAME'][3:]
    return holding['LOCATION_DISPLAY_NAME']


def trim_item_display_name(item):
    index = item['PERMLOCATION'].find(':') if item['PERMLOCATION'] else -1
    if index == 2:
        return item['PERMLOCATION'][3:].strip()
    return item['PERMLOCATION']


def trim_item_temp_location(item):
    index = item['TEMPLOCATION'].find(':') if item['TEMPLOCATION'] else -1
    if index == 2:
        return item['TEMPLOCATION'][3:].strip()
    return item['TEMPLOCATION']


def _in_clause(items):
    return ','.join(["'" + smart_str(item) + "'" for item in items])


# deprecated
def get_electronic_data(mfhd_id):
    query = """
SELECT mfhd_master.mfhd_id,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','u')) as LINK856u,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','z')) as LINK856z,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','z')) as LINK852z,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','a')) as LINK852a,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','h')) as LINK852h,
       RTRIM(wrlcdb.GetAllTags(%s,'M','866',2)) as LINK866,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','3')) as LINK8563
FROM mfhd_master
WHERE mfhd_master.mfhd_id=%s"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id] * 8)
    results = _make_dict(cursor, first=True)
    string = results.get('LINK856U')
    return results


def get_mfhd_data(mfhd_id):
    query = """
SELECT RTRIM(wrlcdb.GetAllTags(%s,'M','852',2)) as MARC852,
       RTRIM(wrlcdb.GetAllTags(%s,'M','856',2)) as MARC856,
       RTRIM(wrlcdb.GetAllTags(%s,'M','866',2)) as MARC866
FROM mfhd_master
WHERE mfhd_master.mfhd_id=%s"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id] * 4)
    results = _make_dict(cursor, first=True)
    # parse notes from 852
    string = results.get('MARC852', '')
    marc852 = ''
    if string:
        for subfield in string.split('$')[1:]:
            if subfield and subfield[0] == 'z':
                marc852 = marc852 + subfield[1:]
    # parse link from 856
    string = results.get('MARC856', '')
    marc856 = []
    if string:
        marc856 = get_marc856(string)
    # parse "library has" info from 866
    marc866 = []
    string = results.get('MARC866', '')
    if string:
        for line in string.split('//'):
            for subfield in line.split('$')[1:]:
                if subfield[0] == 'a':
                    marc866.append(subfield[1:].strip(" '"))
                    break
    return {'marc852': marc852, 'marc856list': marc856,
            'marc866list': marc866}

def get_himmelfarb_bib_and_link(mfhdid):
# Get the bibid of the bib record associated with a Himmelfarb holding,
# then call get_himmelfarb_linkonbib to get the eresource link, if any,
# from Himmelfarb bib record.
        query = """
        SELECT 
        BIB_MASTER.BIB_ID
        FROM 
        BIB_MFHD INNER JOIN BIB_MASTER ON BIB_MFHD.BIB_ID = BIB_MASTER.BIB_ID
        WHERE 
        BIB_MFHD.MFHD_ID= %s"""
        cursor = connection.cursor()
        cursor.execute(query, [mfhdid])
        result = _make_dict(cursor, first=True)
        himmelfarb_bib = result['BIB_ID']
        link = get_himmelfarb_linkonbib(himmelfarb_bib)
        if link:
            return link
        else:
            return []

def get_himmelfarb_linkonbib(bibid):
# Himmelfarb may have a second 856 on the bib record with a link.
# This GetMarcField retrieves that specific link. The bibid param
# should be the bibid of the bib owned by library 'HI'
        query = """
        SELECT
        wrlcdb.GetMarcField(%s,0,0,'856','','u',2) as LINK856U
        FROM BIB_MASTER
        WHERE 
        BIB_MASTER.BIB_ID= %s"""
        cursor = connection.cursor()
        cursor.execute(query, [bibid]*2)
        bib856result = _make_dict(cursor, first=True)
        if bib856result:
            link = bib856result.values()
            return link[0][9:]
        else:
            return []

def get_marc856(marc856_field):
    marc856 = []
    for item in marc856_field.split(' // '):
        temp = {'3': '', 'u': '', 'z': ''}
        for subfield in item.split('$')[1:]:
           if subfield[0] in temp:
               temp[subfield[0]] = subfield[1:]
           else:
               # Possibly not subfield 3, u, or z because a '$' character was 
               # part of the URL string. Append whatever found onto the $u
               # including the $ symbol.
               url_plus_segment= temp['u'],'$',subfield[0],subfield[1:]
               fullurl = ''.join(url_plus_segment)
               temp['u'] = fullurl
        marc856.append(temp)
    return marc856


def get_mfhd_raw(mfhd_id):
    query = """
SELECT RTRIM(wrlcdb.GetAllTags(%s,'M','852',2)) as MARC852,
       RTRIM(wrlcdb.GetAllTags(%s,'M','856',2)) as MARC856,
       RTRIM(wrlcdb.GetAllTags(%s,'M','866',2)) as MARC866
FROM mfhd_master
WHERE mfhd_master.mfhd_id=%s"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id] * 4)
    return _make_dict(cursor, first=True)


def get_items(mfhd_id, first=False):
    query = """
SELECT DISTINCT display_call_no, item_status_desc, item_status.item_status,
       permLocation.location_display_name as PermLocation,
       tempLocation.location_display_name as TempLocation,
       mfhd_item.item_enum, mfhd_item.chron, item.item_id, item_status_date,
       bib_master.bib_id,
       to_char(CIRC_TRANSACTIONS.current_DUE_DATE, 'mm-dd-yyyy') AS DUE
FROM bib_master
JOIN library ON library.library_id = bib_master.library_id
JOIN bib_mfhd ON bib_master.bib_id = bib_mfhd.bib_id
JOIN mfhd_master ON mfhd_master.mfhd_id = bib_mfhd.mfhd_id
JOIN mfhd_item on mfhd_item.mfhd_id = mfhd_master.mfhd_id
JOIN item ON item.item_id = mfhd_item.item_id
JOIN item_status ON item_status.item_id = item.item_id
JOIN item_status_type ON
    item_status.item_status = item_status_type.item_status_type
JOIN location permLocation ON permLocation.location_id = item.perm_location
LEFT OUTER JOIN location tempLocation ON
    tempLocation.location_id = item.temp_location
LEFT OUTER JOIN circ_transactions on item.item_id = circ_transactions.item_id
WHERE bib_mfhd.mfhd_id = %s
AND mfhd_master.suppress_in_opac = 'N'
ORDER BY PermLocation, TempLocation, item_status_date desc"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id])
    if first:
        return _make_dict(cursor, first=True)
    return _make_dict(cursor)


def get_z3950_bib_data(bibid, lib):
    conn = None
    res = []
    id_list = []
    bib = None
    try:
        conn = _get_z3950_connection(settings.Z3950_SERVERS[lib])
    except:
        return None
    query = zoom.Query('PQF', '@attr 1=12 %s' % bibid.encode('utf-8'))
    try:
        res = conn.search(query)
        for r in res:
            bib = {}
            rec = pymarc.record.Record(r.data.bibliographicRecord.encoding[1])
            bib['LIBRARY_NAME'] = lib
            bib['AUTHOR'] = rec.author()
            bib['BIB_ID'] = bibid
            bib['BIB_FORMAT'] = rec['000']
            id_list.append({'BIB_ID': bibid, 'LIBRARY_NAME': lib})
            bib['BIB_ID_LIST'] = id_list
            if rec['250']:
                bib['EDITION'] = rec['250']['a']
            else:
                bib['EDITION'] = None
            bib['IMPRINT'] = rec['260'].format_field()
            bib['LANGUAGE'] = rec['008'].value()[35:38]
            if rec['856']:
                bib['LINK'] = rec['856']['u']
            else:
                bib['LINK'] = []
            if rec['006']:
                bib['MARC006'] = rec['006'].value()
            else:
                bib['MARC006'] = None
            if rec['007']:
                bib['MARC007'] = rec['007'].value()
            else:
                bib['MARC007'] = None
            if rec['008']:
                bib['MARC008'] = rec['008'].value()
            else:
                bib['MARC008'] = None
            if rec['MESSAGE']:
                bib['MESSAGE'] = rec['856']['z']
            else:
                bib['MESSAGE'] = None
            if rec['035']:
                num = rec['035']['a']
                if _is_oclc(num):
                    bib['OCLC'] = num
            else:
                bib['OCLC'] = None
            bib['PUBLISHER'] = rec.publisher()
            bib['PUBLISHER_DATE'] = rec.pubyear()
            if rec['260']:
                bib['PUB_PLACE'] = rec['260']['a']
            else:
                bib['PUB_PLACE'] = None
            bib['TITLE'] = rec.title()
            bib['TITLE_ALL'] = rec.title().decode('iso-8859-1').encode('utf8')
    except:
        return None
    return bib


def _get_z3950_connection(server):
    conn = zoom.Connection(server['IP'], server['PORT'])
    conn.databaseName = server['DB']
    conn.preferredRecordSyntax = server['SYNTAX']
    return conn


def _GetValue(skey, tlist):
    """Get data for subfield code skey, given the subfields list."""
    for (subkey, subval) in tlist:
        if skey == subkey:
            return subval
    return None


def get_z3950_holdings(id, school, id_type, query_type, bib_data,
                       translate_bib=True):
    conn = None
    zoomrecord = None
    results = res = dataset = []
    availability = electronic = {}
    item_status = 0
    correctbib = status = location = callno = url = msg = note = ''
    if translate_bib:
        bib = get_nongwbib_from_gwbib(id, school)
    else:
        bib = id
    try:
        conn = z3950.Z3950Catalog(settings.Z3950_SERVERS[school]['IP'],
                                  settings.Z3950_SERVERS[school]['PORT'],
                                  settings.Z3950_SERVERS[school]['DB'],
                                  settings.Z3950_SERVERS[school]['SYNTAX'])
    except:
        return z3950_holdings_exception(bib, school, bib_data)
    try:
        if school in ['GT', 'DA'] and isinstance(bib, list):
            zoomrecord = conn.zoom_record(bib[0])
            result = get_z3950_holding_data(zoomrecord, conn, bib[0], school,
                                            bib_data)
            return result
        elif school in ['GT', 'DA'] and not isinstance(bib, list):
            zoomrecord = conn.zoom_record(str(id))
            result = get_z3950_holding_data(zoomrecord, conn, str(id), school,
                                            bib_data)
            return result
        elif school == 'GM' and isinstance(bib, list):
            correctbib = get_correct_gm_bib(bib)
            if not translate_bib:
                correctbib = bib
            zoomrecord = conn.zoom_record(correctbib)
            return get_z3950_holding_data(zoomrecord, conn, correctbib, school,
                                          bib_data)
    except:
        return z3950_holdings_exception(bib, school, bib_data)
    if school == 'GM' and bib and not isinstance(bib, list):
        dataset = []
        res = get_bib_data(id)
        if res and len(res) > 0:
            ind = res['LINK'].find('$u')
            url = res['LINK'][ind + 2:]
            if res['MESSAGE']:
                ind = res['MESSAGE'].find('$z')
                msg = res['MESSAGE'][ind + 2:]
            item_status = 1
            status = 'Not Charged'
            results.append({'STATUS': '', 'LOCATION': '', 'CALLNO': '',
                            'LINK': url, 'MESSAGE': msg, 'NOTE': note})
        availability = get_z3950_availability_data(bib, 'GM', location,
                                                   status, callno, item_status)
        electronic = get_z3950_electronic_data('GM', url, msg, note)
        res = get_z3950_mfhd_data(id, school, results, [], bib_data)
        marc856list = marc866list = items = []
        if res:
            if len(res) > 0:
                marc866list = res[0]
            if len(res) > 1:
                marc856list = res[1]
            if len(res) > 2:
                items = res[2]
        dataset.append({'availability': availability,
                        'electronic': electronic,
                        'mfhd': {'marc866list': marc866list,
                                 'marc856list': marc856list,
                                 'marc852': ''},
                        'items': items})
        return dataset


def z3950_holdings_exception(bib, school, bib_data):
    results = []
    dataset = []
    status = location = callno = url = msg = note = item_status = ''
    availability = get_z3950_availability_data(bib, school, '', '',
                                               '', item_status, False)
    electronic = get_z3950_electronic_data(school, '', '', note,
                                           False)
    arow = {'STATUS': status, 'LOCATION': location,
            'CALLNO': callno, 'LINK': url, 'MESSAGE': msg,
            'NOTE': note}
    results.append(arow)
    res = get_z3950_mfhd_data(bib, school, results, [], bib_data)
    if len(res) > 0:
        dataset.append({'availability': availability,
                        'electronic': electronic,
                        'mfhd': {'marc866list': res[0],
                                 'marc856list': res[1], 'marc852': ''},
                        'items': res[2]})
    return dataset


def get_correct_gm_bib(bib_list):
    correctbib = ''
    for bibid in bib_list:
        ind = bibid.find(' ')
        if ind != -1:
            continue
        correctbib = bibid
        break
    return correctbib


def get_z3950_holding_data(zoomrecord, conn, correctbib, school, bib_data):
    hold = conn.get_holding(bibid=correctbib, zoom_record=zoomrecord,
                            school=school)
    results = []
    dataset = []
    msg = note = status = location = url = callno = ''
    item_status = 0
    for h in hold:
        msg = h['msg']
        note = h['note']
        status = h['status']
        url = h['url']
        location = h['location']
        callno = h['callnum']
        item_status = h['item_status']
        arow = {'STATUS': h['status'], 'LOCATION': h['location'],
                'CALLNO': h['callnum'], 'LINK': h['url'], 'MESSAGE': h['msg'],
                'NOTE': h['note']}
        results.append(arow)
    availability = get_z3950_availability_data(correctbib, school, location,
                                               status, callno, item_status)
    electronic = get_z3950_electronic_data(school, url, msg, note)
    res = get_z3950_mfhd_data(correctbib, school, results, [], bib_data)
    if len(res) > 0:
        dataset.append({'availability': availability,
                        'electronic': electronic,
                        'mfhd': {'marc866list': res[0],
                                 'marc856list': res[1],
                                 'marc852': res[3]},
                        'items': res[2]})
    return dataset


def get_nongwbib_from_gwbib(bibid, school):
    if school == 'GM':
        query = """
SELECT bib_index.normal_heading
FROM bib_index
WHERE bib_index.bib_id = %s
AND bib_index.index_code ='035A'
AND bib_index.normal_heading=bib_index.display_heading"""
    else:
        query = """
SELECT LOWER(SUBSTR(bib_index.normal_heading, 0,
    LENGTH(bib_index.normal_heading)-1))  \"NORMAL_HEADING\"
FROM bib_index
WHERE bib_index.bib_id = %s
AND bib_index.index_code ='907A'"""
    try:
        cursor = connection.cursor()
        cursor.execute(query, [bibid])
        results = _make_dict(cursor)
    except:
        return [bibid]
    return [row['NORMAL_HEADING'] for row in results]


def get_gtbib_from_gwbib(bibid):
    query = """
SELECT LOWER(SUBSTR(bib_index.normal_heading, 0,
    LENGTH(bib_index.normal_heading)-1))  \"NORMAL_HEADING\"
FROM bib_index
WHERE bib_index.bib_id = %s
AND bib_index.index_code ='907A'"""
    try:
        cursor = connection.cursor()
        cursor.execute(query, [bibid])
        results = _make_dict(cursor)
    except:
        return [bibid]
    return [row['NORMAL_HEADING'] for row in results]


def get_wrlcbib_from_gtbib(gtbibid):
    query = """
SELECT bib_index.bib_id
FROM bib_index,bib_master
WHERE bib_index.normal_heading = %s
AND bib_index.index_code = '907A'
AND bib_index.bib_id = bib_master.bib_id
AND bib_master.library_id IN ('14', '15')"""
    cursor = connection.cursor()
    cursor.execute(query, [gtbibid.upper()])
    results = _make_dict(cursor)
    return results[0]['BIB_ID'] if results else None


def get_wrlcbib_from_gmbib(gmbibid):
    query = """
SELECT bib_index.bib_id
FROM bib_index, bib_master
WHERE bib_index.index_code = '035A'
AND bib_index.bib_id=bib_master.bib_id
AND bib_index.normal_heading=bib_index.display_heading
AND bib_master.library_id = '6'
AND bib_index.normal_heading = %s"""
    cursor = connection.cursor()
    cursor.execute(query, [gmbibid])
    results = _make_dict(cursor)
    return results[0]['BIB_ID'] if results else None


def is_eligible(holding):
    if holding.get('LIBRARY_NAME', '') in settings.INELIGIBLE_LIBRARIES:
        return False
    marc856 = holding.get('MFHD_DATA', {}).get('marc856list', [])
    if not marc856 and not holding.get('ITEMS', None) and \
            not holding.get('AVAILABILITY', {}):
        return True
    if holding.get('AVAILABILITY', {}):
        perm_loc = holding['AVAILABILITY']['PERMLOCATION'].upper() if \
            holding['AVAILABILITY'].get('PERMLOCATION', '') else ''
        temp_loc = holding['AVAILABILITY']['TEMPLOCATION'].upper() if \
            holding['AVAILABILITY'].get('TEMPLOCATION', '') else ''
        status = holding['AVAILABILITY']['ITEM_STATUS_DESC'].upper() if \
            holding['AVAILABILITY'].get('ITEM_STATUS_DESC', '') else ''
    else:
        return False
    if (holding.get('LIBRARY_NAME', '') == 'GM' and
        'Law Library' in holding.get('AVAILABILITY', {}).get('PERMLOCATION',
                                                             '')):
        return False
    for loc in settings.INELIGIBLE_PERM_LOCS:
        if loc in perm_loc:
            return False
    if 'WRLC' in temp_loc or 'WRLC' in perm_loc:
        return True
    for loc in settings.INELIGIBLE_TEMP_LOCS:
        if loc in temp_loc:
            return False
    for stat in settings.INELIGIBLE_STATUS:
        if stat == status[:len(stat)]:
            return False
    if marc856 and marc856[0].get('u', ''):
        return False
    return True


def is_item_eligible(item, library_name):
    if library_name in settings.INELIGIBLE_LIBRARIES:
        return False
    perm_loc = item['PERMLOCATION'].upper() if item['PERMLOCATION'] else ''
    temp_loc = item['TEMPLOCATION'].upper() if item['TEMPLOCATION'] else ''
    status = item['ITEM_STATUS_DESC'].upper() if \
        item['ITEM_STATUS_DESC'] else ''
    if library_name == 'GM' and 'Law Library' in perm_loc:
        return False
    if library_name in settings.INELIGIBLE_LIBRARIES:
        return False
    for loc in settings.INELIGIBLE_PERM_LOCS:
        if loc in perm_loc:
            return False
    if 'WRLC' in temp_loc or 'WRLC' in perm_loc:
        return True
    for loc in settings.INELIGIBLE_TEMP_LOCS:
        if loc in temp_loc:
            return False
    for stat in settings.INELIGIBLE_STATUS:
        if stat == status[:len(stat)]:
            return False
    return True


def get_z3950_availability_data(bib, school, location, status, callno,
                                item_status, found=True):
    availability = {}
    catlink = ''
    if bib and school == 'GT':
        catlink = '''Click on the following link to get the information about
this item from GeorgeTown Catalog <br>
http://catalog.library.georgetown.edu/record=b%s~S4'''
    elif school == 'GM' and len(bib) > 0:
        catlink = '''Click on the following link to get the information about
this item from George Mason Catalog <br>
http://magik.gmu.edu/cgi-bin/Pwebrecon.cgi?BBID=%s'''
    elif len(bib) > 0:
        catlink = '''Click on the following link to get the information about
this item from Dahlgren library Catalog <br>
http://catalog.library.georgetown.edu/record=b%s~S4'''
    if bib:
        catlink = catlink % bib
    if found:
        availability = {'BIB_ID': bib,
                        'CHRON': None,
                        'DISPLAY_CALL_NO': callno,
                        'ITEM_ENUM': None,
                        'ITEM_ID': None,
                        'ITEM_STATUS': item_status,
                        'ITEM_STATUS_DATE': '',
                        'ITEM_STATUS_DESC': status,
                        'PERMLOCATION': location,
                        'TEMPLOCATION': None}
    else:
        availability = {'BIB_ID': bib,
                        'CHRON': None,
                        'DISPLAY_CALL_NO': callno,
                        'ITEM_ENUM': None,
                        'ITEM_ID': None,
                        'ITEM_STATUS': item_status,
                        'ITEM_STATUS_DATE': '',
                        'ITEM_STATUS_DESC': status,
                        'PERMLOCATION': catlink,
                        'TEMPLOCATION': None}
    return availability


def get_z3950_electronic_data(school, link, message, note, Found=True):
    link852h = ''
    if link != '':
        link852h = school + ': Electronic Resource'
    electronic = {'LINK852A': None,
                  'LINK852H': link852h,
                  'LINK856Z': message,
                  'LINK856U': link,
                  'LINK866': None,
                  'MFHD_ID': None}
    return electronic


def get_library_has(holding):
    if holding['ELECTRONIC_DATA'] and holding['ELECTRONIC_DATA']['LINK866']:
        lib_has = holding['ELECTRONIC_DATA']['LINK866'].split('//')
        for i in range(len(lib_has)):
            line = lib_has[i]
            ind = line.find('$a')
            ind2 = line.find('$', ind + 2)
            if ind > -1:
                if ind2 != -1:
                    line = line[ind + 2:ind2]
                else:
                    line = line[ind + 2:]
            if ind > -1:
                lib_has[i] = line
            elif line.find('$') > -1:
                while line.find('$') > -1:
                    line = line[line.find('$') + 2:]
                lib_has[i] = line
        return lib_has
    else:
        return []


def get_callno(line):
    ind = line.find('50')
    if ind != -1:
        ind = line.find('$a')
        if ind != -1:
            callno = line[ind + 2:]
            return callno
    return None


def get_clean_callno(callno):
    ind = callno.find('$b')
    if ind != -1:
        callno = callno[0: ind] + callno[ind + 2:]
    return callno


def get_z3950_mfhd_data(id, school, links, internet_items, bib_data):
    m866list = []
    m856list = []
    items = []
    m852 = ''
    if len(links) > 0:
        m852 = links[0]['NOTE']
    else:
        m852 = ''
    res = []
    if len(links) == 0:
        # follow this, but ignore links on a George Mason bib record
        if bib_data['LINK'] and school != 'GM':
            if '$u' in bib_data['LINK']:
                ind = bib_data['LINK'].find('$u')
                bib_data['LINK'] = bib_data['LINK'][ind + 2:]
            val = {'3': '',
                   'z': bib_data['LIBRARY_NAME'] + ' Electronic Resource',
                   'u': bib_data['LINK']}
            m856list.append(val)
            library_full_name = settings.LIB_LOOKUP[bib_data['LIBRARY_NAME']]
            display_call_no = bib_data['LIBRARY_NAME'] + \
                ' Electronic Resource'
            item = {
                'ITEM_ENUM': None, 'ELIGIBLE': False,
                'ITEM_STATUS': 1, 'ITEM_STATUS_DATE': '',
                'TEMPLOCATION': None, 'ITEM_STATUS_DESC': '',
                'BIB_ID': bib_data['BIB_ID'], 'ITEM_ID': '',
                'LIBRARY_FULL_NAME': library_full_name,
                'PERMLOCATION': bib_data['LIBRARY_NAME'] + ': Online',
                'TRIMMED_LOCATION_DISPLAY_NAME': 'ONLINE',
                'DISPLAY_CALL_NO': display_call_no,
                'CHRON': None
            }
            items.append(item)
        else:
            return []
    for link in links:
        if link['STATUS'] == 'MISSING':
            link['STATUS'] = 'Missing'
        if link['LINK']:
            val = {'3': '', 'z': link['MESSAGE'], 'u': link['LINK']}
            m856list.append(val)
            continue
        if (link['STATUS'] not in settings.INELIGIBLE_866_STATUS and
                'DUE' not in link['STATUS'] and
            'INTERNET' not in link['LOCATION'] and
                'Online' not in link['LOCATION'] and link['STATUS'] != ''):
            m866list.append(link['STATUS'])
        elif (link['STATUS'] != '' or link['LOCATION'] != '' or
                link['CALLNO'] != ''):
            val = {'ITEM_ENUM': None,
                   'ELIGIBLE': '',
                   'ITEM_STATUS': 0,
                   'TEMPLOCATION': None,
                   'ITEM_STATUS_DESC': link['STATUS'],
                   'BIB_ID': id,
                   'ITEM_ID': 0,
                   'LIBRARY_FULL_NAME': '',
                   'PERMLOCATION': link['LOCATION'],
                   'TRIMMED_LOCATION_DISPLAY_NAME': '',
                   'DISPLAY_CALL_NO': link['CALLNO'],
                   'CHRON': None}
            items.append(val)
    res.append(m866list)
    res.append(m856list)
    res.append(items)
    res.append(m852)
    return res


def get_gt_link(lines):
    url = msg = ''
    for line in lines:
        ind = line.find('856 40')
        if ind != -1:
            ind = line.find('$u')
            ind1 = line.find(' ', ind)
            url = line[ind + 2:]
            ind = line.find('$z')
            ind1 = line.find('$u', ind)
            msg = line[ind + 2: ind1]
            break
        ind = line.find('856 41')
        if ind != -1:
            ind = line.find('$u')
            ind1 = line.find(' ', ind)
            url = line[ind + 2:]
            ind = line.find('$z')
            ind1 = line.find('$u', ind)
            msg = line[ind + 2: ind1]
            break
    res = {'url': url, 'msg': msg}
    return res


def get_gm_link(lines, line):
    url = msg = ''
    status = location = callno = url = msg = note = ''
    arow = {}
    found = False
    internet_items = []
    ind = line.find('856 4')
    if ind != -1:
        ind = line.find('$x')
        if ind == -1:
            ind = line.find('$a')
        ind1 = line.find(' ', ind)
        if ind1 != -1:
            url = line[ind + 2: ind1]
        else:
            url = line[ind + 2:]
        location = 'GM: online'
        ind = line.find('$z')
        ind1 = line.rfind(' ', ind)
        msg = line[ind + 2: ind1]
    i = 0
    for line in lines:
        i = i + 1
        ind = line.find("""receiptAcqStatus: '4'""")
        if ind != -1:
            found = True
            break
    if found:
        line = lines[i + 3]
        ind = line.find(':')
        chars = len(line)
        location = 'GM: ' + \
            line[ind + 3: chars - 1].strip(' -.').strip('\\x00')
    if location in ['GM: Electronic Subscription (GMU Patrons Only)',
                    'GM: Available Online through Mason Libraries']:
        arow = {'STATUS': status, 'LOCATION': location, 'CALLNO': callno,
                'LINK': url, 'MESSAGE': msg, 'NOTE': note}
        internet_items.append(arow)
        res = {'url': url, 'msg': msg, 'internet_items': internet_items}
        return res
    else:
        return {'url': '', 'msg': '', 'internet_items': []}


def get_illiad_link(bib_data):
    if 'openurl' in bib_data \
            and 'query_string_encoded' in bib_data['openurl'] \
            and bib_data['openurl']['query_string_encoded']:
        return insert_sid(bib_data['openurl']['query_string_encoded'])
    title = ''
    ind = 0
    query_args = {}
    url = settings.ILLIAD_URL
    if bib_data.get('BIB_FORMAT') and bib_data.get('BIB_FORMAT')[1:] == 's':
        query_args['rft.genre'] = 'journal'
        query_args['rft_genre'] = 'journal'
        if bib_data.get('AUTHOR', ''):
            query_args['rft.au'] = bib_data['AUTHOR']
        elif bib_data.get('AUTHORS', []):
            query_args['rft.au'] = bib_data['AUTHORS'][0]
        if bib_data.get('PUBLISHER', ''):
            query_args['rft.pub'] = bib_data['PUBLISHER'][1:]
        if bib_data.get('ISBN', ''):
            query_args['rft.isbn'] = bib_data['ISBN']
        if bib_data.get('PUB_PLACE', ''):
            query_args['rft.place'] = bib_data['PUB_PLACE']
        if bib_data.get('PUBLISHER_DATE', ''):
            query_args['rft.date'] = bib_data['PUBLISHER_DATE']
        if bib_data.get('TITLE', ''):
            ind = bib_data['TITLE'].find('/')
        if ind != -1:
            title = bib_data['TITLE'][0:ind]
        else:
            title = bib_data['TITLE']
        if bib_data.get('OCLC', ''):
            query_args['rft_id'] = clean_oclc(bib_data['OCLC'])
        if bib_data.get('ISSN', ''):
            query_args['rft.issn'] = bib_data['ISSN']
        query_args['rft.jtitle'] = smart_str(title)
        if bib_data['openurl']['params'].get('sid'):
            query_args['rfr_id'] = bib_data['openurl']['params']['sid'] + ':'\
                + settings.ILLIAD_SID
        elif bib_data['openurl']['params'].get('rfr_id'):
            query_args['rfr_id'] = bib_data['openurl']['params']['rfr_id'] +\
                ':' + settings.ILLIAD_SID
        else:
            query_args['rfr_id'] = settings.ILLIAD_SID
    else:
        query_args['rft.genre'] = 'book'
        if bib_data.get('AUTHOR', ''):
            query_args['rft.au'] = bib_data['AUTHOR']
        elif len(bib_data.get('AUTHORS', [])) > 0:
            query_args['rft.au'] = bib_data['AUTHORS'][0]
        if bib_data.get('PUBLISHER', ''):
            query_args['rft.pub'] = bib_data['PUBLISHER']
        if bib_data.get('ISBN', ''):
            query_args['rft.isbn'] = bib_data['ISBN']
        if bib_data.get('PUB_PLACE', ''):
            query_args['rft.place'] = bib_data['PUB_PLACE']
        if bib_data.get('OCLC', ''):
            query_args['rft_id'] = clean_oclc(bib_data['OCLC'])
        if bib_data.get('PUBLISHER_DATE', ''):
            query_args['rft.date'] = bib_data['PUBLISHER_DATE'][1:]
        if bib_data.get('TITLE', ''):
            ind = bib_data['TITLE'].find('/')
            if ind != -1:
                title = bib_data['TITLE'][0:ind]
            else:
                title = bib_data['TITLE']
            query_args['rft.btitle'] = ''
            try:
                query_args['rft.btitle'] = title.encode('utf-8')
            except UnicodeDecodeError:
                query_args['rft.btitle'] = \
                    title.decode('iso-8859-1').encode('utf-8')
            if bib_data.get('openurl', {}).get('params', {}).get('rfr_id'):
                query_args['rfr_id'] = bib_data['openurl']['params']['rfr_id']\
                    + ':' + settings.ILLIAD_SID
            elif bib_data.get('openurl', {}).get('params', {}).get('sid'):
                query_args['rfr_id'] = bib_data['openurl']['params']['sid']\
                    + ':' + settings.ILLIAD_SID
            else:
                query_args['rfr_id'] = settings.ILLIAD_SID
    str_args = {}
    for k, v in query_args.iteritems():
        try:
            str_args[k] = v.encode('utf-8')
        except UnicodeDecodeError:
            str_args[k] = v.decode('iso-8859-1').encode('utf-8')
    encoded_args = urllib.urlencode(str_args)
    for item in str_args:
        item = item.encode('ascii', 'replace')
    url += encoded_args
    url = urllib.unquote(url)
    return url

def get_refworks_link(bib_data):
    title = ''
    ind = 0
    query_args = {}
    pattern = re.compile('\d{4}')
    url = settings.REFWORKS_URL
    if bib_data.get('BIB_FORMAT') and bib_data.get('BIB_FORMAT')[1:] == 's':
        query_args['genre'] = 'journal'
    else:
        query_args['genre'] = 'book'
    if bib_data.get('THESIS_DISSERTATION',''):
        author = ''
        if bib_data.get('AUTHOR',''):
            author = bib_data['AUTHOR']
            if pattern.search(author):
                author = author[0:author.rfind(',')]
            query_args['aulast'] = author

    else:
        if bib_data.get('AUTHORS', []):
            authors = ''
            count = 0
            for auth in bib_data['AUTHORS']:
                count = count+1
                if count < 6 :
                    if pattern.search(auth):
                        auth = auth[0:auth.rfind(',')]
                    authors = authors +';'+ unicode_encode(auth);
                else:
                    authors = authors +';'+unicode_encode("et al.")
                    break
            query_args['aulast'] = authors

    if bib_data.get('ISBN', ''):
        query_args['isbn'] = ",".join(bib_data['NORMAL_ISBN_LIST'])
        if bib_data['ISBN'][-1:] == ':':
            query_args['isbn'] = bib_data['ISBN'][:-1]
    if bib_data.get('PUBLISHER_DATE', ''):
        if len(re.findall('\d+',bib_data['PUBLISHER_DATE']))>0:
            query_args['date'] = re.findall('\d+',bib_data['PUBLISHER_DATE'])[0]
    if bib_data.get('PUBLISHER',''):
        query_args['pub'] = unicode_encode(bib_data['PUBLISHER'][:-1])
    if bib_data.get('PUB_PLACE',''):
        query_args['place'] = unicode_encode(bib_data['PUB_PLACE'][:-1])
    if bib_data.get('LANGUAGE_DISPLAY',''):
        query_args['language'] = unicode_encode(bib_data['LANGUAGE_DISPLAY'])
    if bib_data.get('SUBJECTS',''):
        sub = unicode_encode(bib_data['SUBJECTS'][0:6])
        query_args['subject'] = ",".join(sub)
    if bib_data.get('TITLE', ''):
        ind = bib_data['TITLE'].find('/')
        if ind != -1:
            title = unicode_encode(bib_data['TITLE'][0:ind])
        else:
            title = unicode_encode(bib_data['TITLE'])
        query_args['title'] = title
        if bib_data.get('openurl', {}).get('params', {}).get('rfr_id'):
            query_args['sid'] = bib_data['openurl']['params']['rfr_id']\
                + ':' + settings.ILLIAD_SID
        elif bib_data.get('openurl', {}).get('params', {}).get('sid'):
            query_args['sid'] = bib_data['openurl']['params']['sid']\
                + ':' + settings.ILLIAD_SID
        else:
            query_args['sid'] = settings.ILLIAD_SID
    for k, v in  query_args.iteritems():
        url += iri_to_uri("&%s=%s" % (k,v))
    return url

def unicode_encode(data):
    if isinstance(data, basestring):
        data = urlquote(data)
    else:
        tmp_list = []
        for var in data:
            tmp_list.append(urlquote(var))
        data = tmp_list
    return data


def insert_sid(qs):
    """
    create an ILLIAD url using an openurl querystring. The sid (openurl v0.1)
    or rfr_id (openurl v1.0) will be rewritten to include settings.ILLIAD_SID
    at the end.
    """
    try:
        q = urlparse.parse_qs(qs, strict_parsing=True)
    except ValueError:
        qs = fix_ampersands(qs)
        q = urlparse.parse_qs(qs)

    # look to see if we've got openurl v0.1 or v1.0
    sid_name = sid = None
    if 'sid' in q and len(q['sid']) == 1:
        sid_name = 'sid'
        sid = q['sid'][0]
    elif 'rfr_id' in q and len(q['rfr_id']) == 1:
        sid_name = 'rfr_id'
        sid = q['rfr_id'][0]
    if 'rft.genre' in q and q['rft.genre'][0] == 'unknown':
        if 'rft_val_fmt' in q and len(q['rft_val_fmt']) == 1:
            length = len(q['rft_val_fmt'][0])
            index = q['rft_val_fmt'][0].rfind(':', 0, length)
            q['rft.genre'] = [q['rft_val_fmt'][0][index+1:length]]

    if sid_name and sid:
        # trim the sid value so that it is not longer than 40 characters
        # https://github.com/gwu-libraries/launchpad/issues/340
        max_size = 40 - len(settings.ILLIAD_SID) - 1  # 1 for the colon
        new_sid = sid[0:max_size]

        # encode the querystring using the new sid
        new_sid += ":" + settings.ILLIAD_SID
        q[sid_name] = [new_sid]
        qs = urllib.urlencode(q, doseq=True)

    return settings.ILLIAD_URL + qs


def fix_ampersands(qs):
    """
    Try to fix openurl that don't encode ampersands correctly. This is kind of
    tricky business. The basic idea is to split the query string on '=' and
    then inpsect each part to make sure there aren't more than one '&'
    characters in it. If there are, all but the last are assumed to need
    encoding. Similarly, if an ampersand is present in the last part, it
    is assumed to need encoding since there is no '=' following it.

    TODO: if possible we should really try to fix wherever these OpenURLs are
    getting created upstream instead of hacking around it here.
    """
    parts = []
    for p in qs.split('='):
        if p.count('&') > 1:
            l = p.split('&')
            last = l.pop()
            p = '%26'.join(l) + '&' + last
        parts.append(p)

    # an & in the last part definitely needs encoding
    parts[-1] = parts[-1].replace('&', '%26')

    return '='.join(parts)


def clean_title(title):
    for field in settings.MARC_245_SUBFIELDS:
        title = title.replace(field, " ")
    title = title.strip()
    if title.startswith('880-'):
        title = title[6:].strip()
    return title


def correct_gt_holding(holdings):
    internet_items = []
    for holding in holdings:
        if holding['LIBRARY_NAME'] == 'GT':
            if holding.get('ITEMS'):
                for item in holding['ITEMS']:
                    if 'INTERNET' in item['PERMLOCATION']:
                        internet_items.append(item)
                        item['REMOVE'] = True
                holding['ITEMS'][:] = [x for x in holding['ITEMS'] if
                                       not x.get('REMOVE', False)]
    for holding in holdings:
        if holding['LIBRARY_NAME'] == 'GT' or holding['LIBRARY_NAME'] == 'DA':
            if 'MFHD_DATA' in holding.keys():
                if holding['MFHD_DATA'].get('marc856list', []):
                    holding = allign_gt_internet_link(internet_items, holding)
    return [h for h in holdings if not h.get('REMOVE', False)]


def allign_gt_internet_link(items, internet):
    for item in items:
        internet['ITEMS'].append(item)
    return internet


def get_links(holding, title, isbn):
    '''
    draws from marc856list and ELECTRONIC_DATA to create a list containing a 
    dictionary for each link with url, label, available (online 
    to GW community)
    '''  
    online = []
    #check MFHD_DATA marc856list
    links = holding.get('MFHD_DATA', {}).get('marc856list',[])
    if not links and holding.get('ELECTRONIC_DATA', {}).get('LINK856U', None):
        links = [{'u': holding['ELECTRONIC_DATA']['LINK856U']}] 
    for link in links:
        if link.get('u', None):
            access = {} 
            access['url'] = link['u']
            if 'http' not in access['url']:
                continue
            access['label'] = link.get('3', '')
            if holding['LIBRARY_NAME'] in ['GW','HI','IA','HT','WRLC','E-Resources']: 
                access['available'] = True
                if holding.get('LinkResolverData', None):
                    continue 
                if 'RushPrintRequest' in access['url']:
                    access['url'] = settings.DDA_URL + '&entry_994442820=ID:' + \
                                    str(holding['BIB_ID']) + ' TITLE:' + title \
                                    + ' ISBN:' + isbn 
                    access['label'] = 'Request print edition'
                    access['available'] = False
		if settings.BOUND_WITH_ITEM_LINK in access['url']: 
                    access['label'] = 'Bound with item'
                    access['available'] = False 
            else:
                if 'endowment' in access['url'] or 'catdir' in access['url']:
                    continue 
                if 'mrqe' in access['url']:
                    access['label'] = 'Movie Review'
                access['available'] = online_available(link)
                if not access['available'] and not access['label']:
                    access['label'] = 'Full text online' 
            online.append(access)
    # check for duplicate URLs in online holdings 
    urls = []
    for x in online:
        if x['url'] in urls:
            online.remove(x)
        else:
            urls.append(x['url'])
    
    return online 


def online_available(link):
    '''    
    analyze other campus's links for online availability to GW: 
    '''    
    if 'proxy' in link['u'] or 'serialssolutions' in link['u'] \
       or 'eblib' in link['u'] or 'mutex' in link['u']:
        return False
    else: 
        return True
