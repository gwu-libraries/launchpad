import copy
import re
import urllib

import pycountry
from PyZ3950 import zoom
import pymarc

from django.conf import settings
from django.db import connection
from django.utils.encoding import smart_str, DjangoUnicodeDecodeError

from ui import apis
from ui.templatetags.launchpad_extras import cjk_info
from ui.templatetags.launchpad_extras import clean_isbn
from ui.templatetags.launchpad_extras import clean_lccn
from ui.templatetags.launchpad_extras import clean_oclc

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
    row = cursor.fetchone()
    while row:
        authors.append(row[0])
        row = cursor.fetchone()
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


def get_marc_blob(bibid):
    query = """
SELECT wrlcdb.getBibBlob(%s) AS marcblob
from bib_master"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    row = cursor.fetchone()
    raw_marc = str(row[0])
    marc = pymarc.record.Record(data=raw_marc)
    return marc


def get_bib_data(bibid, expand_ids=True, exclude_names=False):
    query = """
SELECT bib_text.bib_id, lccn,
       edition, isbn, issn, network_number AS OCLC,
       pub_place, imprint, bib_format,
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
    try:
        bib = _make_dict(cursor, first=True)
        if exclude_names:
            marc = get_marc_blob(bibid)
            bib['TITLE'] = marc.title()
            bib['AUTHOR'] = marc.author()
            bib['PUBLISHER'] = marc.publisher()
            title_fields = marc.get_fields('245')
            bib['TITLE_ALL'] = ''
            for title in title_fields:
                bib['TITLE_ALL'] += title.format_field().decode('iso-8859-1').encode('utf-8')
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
            {'BIB_ID':bib['BIB_ID'], 'LIBRARY_NAME':bib['LIBRARY_NAME']}]
        for num_type in ['isbn', 'issn', 'oclc']:
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
                    new_bibids = get_related_bibids(norm, num_type)
                    for nb in new_bibids:
                        if nb['BIB_ID'] not in [x['BIB_ID'] for x in bibids]:
                            bibids.append(nb)
        bib['BIB_ID_LIST'] = list(bibids)
    # parse fields for microdata
    bib['MICRODATA_TYPE'] = get_microdata_type(bib)
    if bib.get('LINK') \
            and bib.get('MESSAGE', '') == '856:42:$zCONNECT TO FINDING AID':
        bib['FINDING_AID'] = bib['LINK'][9:]
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
    if num_type == 'oclc':
        num = 'OCOLC %s' % num
    query = """
SELECT bib_index.bib_id, bib_master.library_id, library.library_name
FROM bib_index, bib_master, library
WHERE bib_index.index_code IN (%s)
AND bib_index.normal_heading = '%s'
AND bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac = 'N'"""
    cursor = connection.cursor()
    query = query % (_in_clause(settings.INDEX_CODES[num_type]), num)
    cursor.execute(query, [])
    bibs = _make_dict(cursor)
    for bib in bibs:
        if bib['LIBRARY_NAME'] == settings.PREF_LIB:
            return bib['BIB_ID']
    return bibs[0]['BIB_ID'] if bibs else None


def _normalize_num(num, num_type):
    if num_type == 'isbn':
        return clean_isbn(num)
    elif num_type == 'issn':
        return num.replace('-', ' ')
    elif num_type == 'oclc':
        return clean_oclc(num)
    return num


def get_related_bibids(num_list, num_type):
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
AND UPPER(bib_index.display_heading) NOT LIKE %s"""
    query[2] = """
AND bib_index.normal_heading IN (
    SELECT bib_index.normal_heading
    FROM bib_index
    WHERE bib_index.index_code IN (%s)"""
    query[3] = """
    AND UPPER(bib_index.display_heading) NOT LIKE %s"""
    query[4] = """
    AND bib_id IN (
        SELECT DISTINCT bib_index.bib_id
        FROM bib_index
        WHERE bib_index.index_code IN (%s)
        AND bib_index.normal_heading IN (%s)
        AND bib_index.normal_heading != 'OCOLC'"""
    query[5] = """
        AND UPPER(bib_index.display_heading) NOT LIKE %s"""
    query[6] = """
        )
    )
ORDER BY bib_index.bib_id"""
    indexclause = _in_clause(settings.INDEX_CODES[num_type])
    numclause = _in_clause(num_list)
    likeclause = '%' + 'SET' + '%'
    query[0] = query[0] % indexclause
    query[2] = query[2] % indexclause
    query[4] = query[4] % (indexclause, numclause)
    query = ''.join(query)
    args = [likeclause] * 3
    cursor = connection.cursor()
    cursor.execute(query, args)
    results = _make_dict(cursor)
    output_keys = ('BIB_ID', 'LIBRARY_NAME')
    if num_type == 'oclc':
        return [dict([
            (k, row[k]) for k in output_keys]) for row in
                results if _is_oclc(row['DISPLAY_HEADING'])]
    return [dict([(k, row[k]) for k in output_keys]) for row in results]


def get_related_std_nums(bibid, num_type):
    query = """
SELECT normal_heading, display_heading
FROM bib_index
INNER JOIN bib_master ON bib_index.bib_id = bib_master.bib_id
WHERE bib_index.index_code IN (%s)
AND bib_index.bib_id = %s
AND bib_index.normal_heading != 'OCOLC'
AND bib_master.suppress_in_opac='N'
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
    eligibility = False
    added_holdings = []
    for holding in holdings:
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
            holding.update({'ELECTRONIC_DATA':
                            get_electronic_data(holding['MFHD_ID']),
                            'AVAILABILITY':
                            get_availability(holding['MFHD_ID'])})
            holding.update({'MFHD_DATA': get_mfhd_data(holding['MFHD_ID']),
                            'ITEMS': get_items(holding['MFHD_ID'])})
        if holding.get('ITEMS', []):
            i = 0
            for item in holding['ITEMS']:
                item['ELIGIBLE'] = \
                    is_item_eligible(item, holding.get('LIBRARY_NAME', ''))
                if lib is not None:
                    item['ELIGIBLE'] = False
                item['LIBRARY_FULL_NAME'] = \
                    settings.LIB_LOOKUP[holding['LIBRARY_NAME']]
                item['TRIMMED_LOCATION_DISPLAY_NAME'] = \
                    trim_item_display_name(item)
                item['TEMPLOCATION'] = trim_item_temp_location(item)
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
                linkdata = apis.sersol360link(num, num_type)
                for ld in linkdata:
                    holding['LinkResolverData'].append(ld)
    # get free electronic book link from open library
    for numformat in ('LCCN', 'ISBN', 'OCLC'):
        if bib_data.get(numformat):
            if numformat == 'OCLC':
                num = filter(lambda x: x.isdigit(), bib_data[numformat])
            elif numformat == 'ISBN':
                num = bib_data['NORMAL_ISBN_LIST'][0]
            else:
                num = bib_data[numformat]
            openlibhold = apis.openlibrary(num, numformat)
            if openlibhold:
                holdings.append(openlibhold)
                break
    return [h for h in holdings if not h.get('REMOVE', False)]


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
    if 'REMOVE' in items[i]:
        return
    if 'ITEM_STATUS_DATE' in items[i]:
        if items[i]['ITEM_STATUS_DATE'] is None:
            items[i]['REMOVE'] = True
    j = i + 1
    while j < len(items):
        if items[i]['ITEM_ID'] == items[j]['ITEM_ID']:
            if 'ITEM_STATUS_DATE' in items[i]:
                if items[i]['ITEM_STATUS_DATE'] is None:
                    items[i]['REMOVE'] = True
            if 'ITEM_STATUS_DATE' in items[j]:
                if items[j]['ITEM_STATUS_DATE'] is None:
                    items[j]['REMOVE'] = True
            if ('ITEM_STATUS_DATE' in items[i] and
                'ITEM_STATUS_DATE' in items[j]):
                if (items[i]['ITEM_STATUS_DATE'] is not None and
                    items[j]['ITEM_STATUS_DATE'] is not None):
                    if (items[i]['ITEM_STATUS_DATE'] >
                        items[j]['ITEM_STATUS_DATE']):
                        items[j]['REMOVE'] = True
                    else:
                        items[i]['REMOVE'] = True
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
    return _make_dict(cursor, first=True)


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
            if subfield[0] == 'z':
                marc852 = subfield[1:]
    # parse link from 856
    string = results.get('MARC856', '')
    marc856 = []
    if string:
        for item in string.split(' // '):
            temp = {'3': '', 'u': '', 'z': ''}
            for subfield in item.split('$')[1:]:
                if subfield[0] in temp:
                    temp[subfield[0]] = subfield[1:]
            marc856.append(temp)
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


def get_availability(mfhd_id):
    query = """
SELECT DISTINCT display_call_no, item_status_desc, item_status.item_status,
       permLocation.location_display_name as PermLocation,
       tempLocation.location_display_name as TempLocation,
       mfhd_item.item_enum, mfhd_item.chron, item.item_id, item_status_date,
       bib_master.bib_id
FROM bib_master
JOIN library ON library.library_id = bib_master.library_id
JOIN bib_text ON bib_text.bib_id = bib_master.bib_id
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
WHERE bib_mfhd.mfhd_id = %s
ORDER BY PermLocation, TempLocation, item_status_date desc"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id])
    return _make_dict(cursor, first=True)


def get_items(mfhd_id):
    query = """
SELECT DISTINCT display_call_no, item_status_desc, item_status.item_status,
       permLocation.location_display_name as PermLocation,
       tempLocation.location_display_name as TempLocation,
       mfhd_item.item_enum, mfhd_item.chron, item.item_id, item_status_date,
       bib_master.bib_id
FROM bib_master
JOIN library ON library.library_id = bib_master.library_id
JOIN bib_text ON bib_text.bib_id = bib_master.bib_id
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
WHERE bib_mfhd.mfhd_id = %s
ORDER BY PermLocation, TempLocation, item_status_date desc"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id])
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
    query = zoom.Query('PQF', '@attr 1=12 %s' %
        bibid.encode('utf-8'))
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
            bib['IMPRINT'] = rec['260'].value()
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
            bib['TITLE_ALL'] = rec.title()
    except:
        return None
    return bib


def _get_z3950_connection(server):
    conn = zoom.Connection(server['SERVER_ADDRESS'], server['SERVER_PORT'])
    conn.databaseName = server['DATABASE_NAME']
    conn.preferredRecordSyntax = server['PREFERRED_RECORD_SYNTAX']
    return conn


def _GetValue(skey, tlist):
    """Get data for subfield code skey, given the subfields list."""
    for (subkey, subval) in tlist:
        if skey == subkey:
            return subval
    return None


def _get_gt_holdings(id, query, query_type, bib, lib, bib_data):
    res = []
    results = []
    values = status = location = callno = url = msg = note = ''
    item_status = 0
    arow = {}
    internet_items = []
    conn = None
    dataset = []
    linkdata = {'url': '', 'msg': ''}
    try:
        conn = _get_z3950_connection(settings.Z3950_SERVERS[lib])
    except:
        availability = get_z3950_availability_data(bib, lib, '', '', '',
            item_status, False)
        electronic = get_z3950_electronic_data(lib, '', '', note, False)
        arow = {'STATUS': status, 'LOCATION': location,
            'CALLNO': callno, 'LINK': url, 'MESSAGE': msg, 'NOTE': note}
        results.append(arow)
        res = get_z3950_mfhd_data(id, lib, results, [], bib_data)
        if len(res) > 0:
            dataset.append({'availability': availability,
                'electronic': electronic,
                'mfhd': {'marc866list': res[0],
                    'marc856list': res[1],
                    'marc852': ''},
                    'items': res[2]})
        return dataset
    try:
        res = conn.search(query)
    except:
        availability = get_z3950_availability_data(bib, lib, '', '', '',
            item_status, False)
        electronic = get_z3950_electronic_data(lib, '', '', note, False)
        arow = {'STATUS': status, 'LOCATION': location, 'CALLNO': callno,
            'LINK': url, 'MESSAGE': msg, 'NOTE': note}
        results.append(arow)
        res = get_z3950_mfhd_data(id, lib, results, [], bib_data)
        if len(res) > 0:
            dataset.append({'availability': availability,
                'electronic': electronic,
                'mfhd': {'marc866list': res[0],
                    'marc856list': res[1],
                    'marc852': ''},
                'items': res[2]})
        return dataset
    arow = {}
    for r in res:
        values = str(r)
        status = location = callno = note = ''
        lines = values.split('\n')
        for line in lines:
            #if alt_callno is None:
                #alt_callno = get_callno(line)
            if line.find('Holdings') > -1:
                continue
            ind = line.find('localLocation')
            if ind != -1:
                ind = line.find(':')
                chars = len(line)
                location = lib + ': ' + line[ind + 3:chars - 1].strip(' .-')
                continue
            ind = line.find('publicNote')
            if ind != -1:
                ind = line.find(':')
                status = str(line[ind + 2:]).strip(" '")
            if status == 'AVAILABLE':
                status = 'Not Charged'
                item_status = 1
                continue
            elif status[0:4] == 'DUE':
                status = 'Charged'
                item_status = 0
                continue
            ind = line.find('callNumber')
            if ind != -1:
                ind = line.find(':')
                chars = len(line)
                callno = line[ind + 3: chars - 1]
                arow = {'STATUS': status, 'LOCATION': location,
                    'CALLNO': callno, 'LINK': linkdata['url'],
                    'MESSAGE': linkdata['msg'], 'NOTE': note}
                if location == 'GT: INTERNET':
                    internet_items.append(arow)
                if status != '' or location != '' or callno != '' or \
                linkdata['url'] != '' or linkdata['msg'] != '' or note != '':
                    results.append(arow)
        if 'Rec: USMARCnonstrict MARC:' in lines[0] or 'Rec: OPAC Bibliographic MARC:' in lines[0]:
            linkdata = get_gt_link(lines)
            arow = {'STATUS': status, 'LOCATION': location, 'CALLNO': callno,
                'LINK': linkdata['url'], 'MESSAGE': linkdata['msg'],
                'NOTE': note}
            if status != '' or location != '' or callno != '' or \
            linkdata['url'] != '' or linkdata['msg'] != '' or note != '':
                results.append(arow)
    conn.close()
    res = get_z3950_mfhd_data(id, lib, results, [], bib_data)
    availability = get_z3950_availability_data(bib, lib, location, status,
        callno, item_status)
    electronic = get_z3950_electronic_data(lib, linkdata['url'],
                                           linkdata['msg'], note)
    if len(res) > 0:
        dataset.append({'availability': availability,
            'electronic': electronic, 'mfhd': {'marc866list': res[0],
                'marc856list': res[1],
                'marc852': ''},
            'items': res[2]})
    return dataset


def get_z3950_holdings(id, school, id_type, query_type, bib_data,
        translate_bib=True):
    holding_found = False
    conn = None
    if school == 'GM':
        results = []
        availability = {}
        electronic = {}
        internet_items = []
        item_status = 0
        values = status = location = callno = url = msg = note = ''
        alt_callno = None
        arow = {}
        lines = []
        res = []
        dataset = []
        if translate_bib:
            bib = get_gmbib_from_gwbib(id)
        else:
            bib = id
        try:
            conn = _get_z3950_connection(settings.Z3950_SERVERS['GM'])
        except:
            availability = get_z3950_availability_data(bib, 'GM', '', '', '',
                item_status, False)
            electronic = get_z3950_electronic_data('GM', '', '', note, False)
            arow = {'STATUS': status, 'LOCATION': location,
                'CALLNO': callno, 'LINK': url, 'MESSAGE': msg, 'NOTE': note}
            results.append(arow)
            res = get_z3950_mfhd_data(id, school, results, [], bib_data)
            if len(res) > 0:
                dataset.append({'availability': availability,
                    'electronic': electronic, 'mfhd': {'marc866list': res[0],
                        'marc856list': res[1], 'marc852': ''},
                    'items': res[2]})
            return dataset
        if bib and isinstance(bib, list):
            correctbib = ''
            query = None
            for bibid in bib:
                ind = bibid.find(' ')
                if ind != -1:
                    continue
                correctbib = bibid
                break
            if not translate_bib:
                correctbib = bib
            try:
                query = zoom.Query('PQF', '@attr 1=12 %s' %
                    correctbib.encode('utf-8'))
            except:
                availability = get_z3950_availability_data(bib, 'GM', '', '',
                    '', item_status, False)
                electronic = get_z3950_electronic_data('GM', '', '', note,
                    False)
                arow = {'STATUS': status, 'LOCATION': location,
                    'CALLNO': callno, 'LINK': url, 'MESSAGE': msg,
                    'NOTE': note}
                results.append(arow)
                res = get_z3950_mfhd_data(id, school, results, [], bib_data)
                if len(res) > 0:
                    dataset.append({'availability': availability,
                        'electronic': electronic,
                        'mfhd': {'marc866list': res[0],
                            'marc856list': res[1], 'marc852': ''},
                        'items': res[2]})
                return dataset
            res = conn.search(query)
            for r in res:
                values = str(r)
                lines = values.split('\n')
                for line in lines:
                    if alt_callno is None:
                        alt_callno = get_callno(line)
                    ind = line.find('852')
                    if ind != -1:
                        ind = line.find('$u')
                        if ind != -1:
                            note = line[ind + 2]
                    ind = line.find('publicNote')
                    if ind != -1:
                        ind = line.find(':')
                        note = line[ind + 2:].strip("""\\x00.'""")
                    ind = line.find('availableNow')
                    if ind != -1:
                        ind = line.find(':')
                        status = line[ind + 2:]
                        if status == 'True':
                            status = 'Not Charged'
                            item_status = 1
                        elif status == 'False':
                            status = 'Charged'
                            item_status = 0
                    ind = line.find('callNumber')
                    if ind != -1:
                        ind = line.find(':')
                        ind1 = line.find('\\')
                        callno = line[ind + 3:ind1]
                    ind = line.find('localLocation')
                    if ind != -1:
                        ind = line.find('Electronic Subscription')
                        ind1 = line.find('Online')
                        if ind == -1 and ind1 == -1:
                            holding_found = True
                        else:
                            holding_found = False
                            continue
                        ind = line.find(':')
                        ind1 = line.find('\\')
                        location = 'GM: ' + line[ind + 3:ind1].strip(' -.')
                        #ind = location.find('Electronic Subscription')
                        #if ind == -1:
                            #holding_found = True
                    if holding_found:
                        arow = {'STATUS': status, 'LOCATION': location,
                            'CALLNO': callno, 'LINK': url, 'MESSAGE': msg,
                            'NOTE': note}
                        results.append(arow)
                    holding_found = False
                found = False
                i = 0
                for line in lines:
                    if '856 40$' in line:
                        found = True
                        break
                    else:
                        i = i + 1
                if found:
                    linkdata = get_gm_link(lines, lines[i])
                    #if len(linkdata['internet_items'])> 0:
                    for item in linkdata['internet_items']:
                        arow = {'STATUS': item['STATUS'],
                            'LOCATION': item['LOCATION'],
                            'CALLNO': '', 'LINK': '', 'MESSAGE': '',
                            'NOTE': ''}
                        internet_items.append(arow)
                    arow = {'STATUS': '', 'LOCATION': '', 'CALLNO': '',
                        'LINK': linkdata['url'], 'MESSAGE': linkdata['msg'],
                        'NOTE': ''}
                    internet_items.append(arow)
            conn.close()
            availability = get_z3950_availability_data(bib, 'GM', location,
                status, callno, item_status)
            electronic = get_z3950_electronic_data('GM', url, msg, note)
            res = get_z3950_mfhd_data(id, school, results, [], bib_data)
            if len(res) > 0:
                dataset.append({'availability': availability,
                    'electronic': electronic,
                    'mfhd': {'marc866list': res[0],
                        'marc856list': res[1],
                        'marc852': res[3]},
                    'items': res[2]})
            if len(internet_items) > 0:
                res = get_z3950_mfhd_data(id, school, internet_items, [],
                        bib_data)
                dataset.append({'availability': availability,
                    'electronic': electronic,
                    'mfhd': {'marc866list': res[0],
                        'marc856list': res[1],
                        'marc852': ''},
                    'items': res[2]})
            return dataset
        else:
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
                if 0 < len(res):
                    marc866list = res[0]
                if 1 < len(res):
                    marc856list = res[1]
                if 2 < len(res):
                    items = res[2]
            dataset.append({'availability': availability,
                    'electronic': electronic,
                    'mfhd': {'marc866list': marc866list,
                    'marc856list': marc856list,
                    'marc852': ''},
                    'items': items})
            return dataset
    elif school == 'GT' or school == 'DA':
        res = []
        if id_type == 'bib':
            if translate_bib:
                bib = get_gtbib_from_gwbib(id)
                if bib:
                    if bib[0] is not None:
                        query = zoom.Query('PQF', '@attr 1=12 %s' %
                            bib[0].encode('utf-8'))
                        return _get_gt_holdings(id, query, query_type,
                            bib, school, bib_data)
                    else:
                        return []
                elif not bib or not translate_bib:
                    query = zoom.Query('PQF', '@attr 1=12 %s' %
                        str(id).encode('utf-8'))
                    return _get_gt_holdings(id, query, query_type,
                        id, school, bib_data)
            else:
                bib = get_gtbib_from_gwbib(id)
                query = zoom.Query('PQF', '@attr 1=12 %s' %
                    str(bib).encode('utf-8'))
                return _get_gt_holdings(id, query, query_type,
                    bib, school, bib_data)
        elif id_type == 'isbn':
            query = zoom.Query('PQF', '@attr 1=7 %s' % id)
        elif id_type == 'issn':
            query = zoom.Query('PQF', '@attr 1=8 %s' % id)
        elif id_type == 'oclc':
            query = zoom.Query('PQF', '@attr 1=1007 %s' % id)
        return _get_gt_holdings(id, query, query_type, bib, school,
                bib_data)


def get_gmbib_from_gwbib(bibid):
    query = """
SELECT bib_index.normal_heading
FROM bib_index
WHERE bib_index.bib_id = %s
AND bib_index.index_code ='035A'
AND bib_index.normal_heading=bib_index.display_heading"""
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
    if not marc856 and not holding.get('ITEMS', None):
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
        if bib_data['LINK']:
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
            for item in internet_items:
                val = {'ITEM_ENUM': None,
                   'ELIGIBLE': '',
                   'ITEM_STATUS': 0,
                   'TEMPLOCATION': None,
                   'ITEM_STATUS_DESC': item['STATUS'],
                   'BIB_ID': id,
                   'ITEM_ID': 0,
                   'LIBRARY_FULL_NAME': '',
                   'PERMLOCATION': item['LOCATION'],
                   'TRIMMED_LOCATION_DISPLAY_NAME': '',
                   'DISPLAY_CALL_NO': item['CALLNO'],
                   'CHRON': None}
            items.append(val)
        if links:
            if (link['STATUS'] not in ['Charged', 'Not Charged', 'Missing',
                'LIB USE ONLY'] and 'DUE' not in link['STATUS'] and
                'INTERNET' not in link['LOCATION'] and
                'Online' not in link['LOCATION'] and link['STATUS'] != ''):
                m866list.append(link['STATUS'])
            elif (link['STATUS'] != '' or link['LOCATION'] != '' or
                link['CALLNO'] != '' and not link['LINK']):
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
    if 'openurl' in bib_data:
        if bib_data['openurl']['query_string']:
            ind = bib_data['openurl']['query_string'].find('sid=')
            #Find the end of the sid key
            if ind != -1:
                end = bib_data['openurl']['query_string'].\
                        find('&', ind)
                if end == -1:
                    new_sid = bib_data['openurl']['query_string'][ind:]\
                            + ':' + settings.ILLIAD_SID
                    return settings.ILLIAD_URL + new_sid
                else: #it's not at the end
                    new_sid = bib_data['openurl']['query_string'][ind:end]\
                            + ':' + settings.ILLIAD_SID
                    before_string = bib_data['openurl']['query_string'][0:ind]\
                            + new_sid
                    after_sid = bib_data['openurl']['query_string'][end:]
                    new_string = before_string + after_sid
                    return settings.ILLIAD_URL + new_string
            ind = bib_data['openurl']['query_string'].find('rfr_id=')
            #Find the end of the sid key
            if ind != -1:
                end = bib_data['openurl']['query_string'].\
                        find('&', ind)
                if end == -1:
                    new_sid = bib_data['openurl']['query_string'][ind:]\
                            + ':' + settings.ILLIAD_SID
                    return settings.ILLIAD_URL + new_sid
                else:
                    new_sid = bib_data['openurl']['query_string'][ind:end]\
                            + ':' + settings.ILLIAD_SID
                    before_string = bib_data['openurl']['query_string'][0:ind]\
                            + new_sid
                    after_sid = bib_data['openurl']['query_string'][end:]
                    new_string = before_string + after_sid
                    return settings.ILLIAD_URL + new_string
            return settings.ILLIAD_URL +\
                    bib_data['openurl']['query_string']
    auinit = ''
    aufirst = ''
    aulast = ''
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
            query_args['rft.pub'] = bib_data['PUBLISHER']
        if bib_data.get('ISBN', ''):
            query_args['rft.isbn'] = bib_data['ISBN']
        if bib_data.get('PUB_PLACE', ''):
            query_args['rft.place'] = bib_data['PUB_PLACE']
        if bib_data.get('PUBLISHER_DATE', ''):
            query_args['rft.date'] = bib_data['PUBLISHER_DATE'][1:]
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
    return url


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
