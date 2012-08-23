import pycountry
from PyZ3950 import zoom
import urllib
import copy
import re

from django.conf import settings
from django.db import connection, transaction
from django.utils.encoding import smart_str, smart_unicode

from ui.templatetags.launchpad_extras import cjk_info
from ui.templatetags.launchpad_extras import clean_isbn, clean_oclc, clean_issn
from ui.models import Bib, Holding, Item


'''
Primary function for retrieving a record from the Voyager DB using the Bib
object type
'''
def bib(bibid, expand=True):
    query = """
SELECT bib_text.bib_id AS bibid,
       title,
       author,
       edition,
       isbn,
       issn,
       imprint,
       publisher,
       pub_place AS pubplace,
       publisher_date AS pubyear,
       bib_format AS formatcode,
       language AS langcode,
       library_name AS libcode,
       network_number AS oclc,
       wrlcdb.getBibBlob(%s) AS marcblob
FROM bib_text, bib_master, library
WHERE bib_text.bib_id=%s
AND bib_text.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid] * 2)
    data = _make_dict(cursor, first=True)
    raw_marc = str(data.pop('marcblob'))
    bib = Bib(metadata=data, raw_marc=raw_marc)
    return bib


'''
This function takes various standard numbers and returns a WRLC bibid number.
It can accept: isbn, issn, oclc, gtbibid, gmbibid
If there are multiple bibids it gives preference to the preferred library (as
specified in the settings file)
'''
def bibid(num, num_type):
    num = _normalize_num(num, num_type)
    query = """
SELECT bib_index.bib_id AS  bibid,
       library.library_name AS library_code
FROM bib_index, bib_master, library
WHERE bib_index.index_code IN %s
AND bib_index.normal_heading = '%s'
AND bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id"""
    if num_type == 'gtbibid':
        index_codes = "('907A')"
    elif num_type == 'gmbibid':
        index_codes = "('035A')"
        query += "\nAND bib_index.normal_heading=bib_index.display_heading"
    else:
        index_codes = _in_clause(settings.INDEX_CODES[num_type])
    query = query % (index_codes, num)
    cursor = connection.cursor()
    cursor.execute(query, [])
    bibs = _make_dict(cursor)
    if bibs:
        for bib in bibs:
            if bib['library_code'] == settings.PREF_LIB:
                return bib['bibid']
        return bibs[0]['bibid']


def related_stdnums(bibid, debug=False):
    output = {'isbn': [], 'issn': [], 'oclc': []}
    query = '''
SELECT normal_heading,
       display_heading,
       index_code
FROM bib_index
WHERE index_code IN %s
AND bib_id = %s
AND normal_heading != 'OCOLC'
ORDER BY normal_heading'''
    index_codes = []
    for numtype in output:
        index_codes.extend(settings.INDEX_CODES[numtype])
    query = query % (_in_clause(index_codes), bibid)
    if debug:
        print 'QUERY:\n%s\n' % query
    cursor = connection.cursor()
    cursor.execute(query, [])
    results = _make_dict(cursor)
    if debug:
        print 'RESULTS:\n%s\n' % results
    for item in results:
        dictionary = {'norm': item['normal_heading'],
                      'disp': item['display_heading']}
        if item['index_code'] in settings.INDEX_CODES['isbn']:
            output['isbn'].append(dictionary)
        elif item['index_code'] in settings.INDEX_CODES['issn']:
            if _is_valid_issn(item['normal_heading']):
                output['issn'].append(dictionary)
        elif item['index_code'] in settings.INDEX_CODES['oclc']:
            if _is_oclc(item['display_heading']):
                output['oclc'].append(dictionary)
    return output


def _is_valid_issn(num):
    if re.match('\d{4}[ -]\d{3}[0-9xX]', num):
        return True
    return False


def _is_oclc(num):
    if num.find('OCoLC') >= 0:
        return True
    if num.find('ocn') >= 0:
        return True
    if num.find('ocm') >= 0:
        return True
    return False


def related_bibids(stdnums, debug=False):
    if debug:
        print 'stdnums: %s\n' % stdnums
    for key in stdnums.keys():
        if not stdnums[key]:
            stdnums.pop(key)
    if debug:
        print 'stdnums stripped: %s\n' % stdnums
    query = """
SELECT DISTINCT bib_index.bib_id AS bibid,
       library.library_name AS libcode,
       bib_index.display_heading AS disp
FROM bib_index, library, bib_master
WHERE bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'
AND bib_index.index_code IN %s
AND bib_index.normal_heading IN (
    SELECT bib_index.normal_heading
    FROM bib_index
    WHERE bib_id IN (
        SELECT DISTINCT bib_index.bib_id
        FROM bib_index
        WHERE bib_index.index_code IN %s
        AND bib_index.normal_heading IN %s
        )
    )
ORDER BY bib_index.bib_id"""
    bibids = []
    for numtype in stdnums:
        codes = settings.INDEX_CODES[numtype]
        nums = [n['norm'] for n in stdnums[numtype]]
        if debug:
            print 'codes: %s\nnums: %s\n' % (codes, nums)
        query = query % (_in_clause(codes),
                         _in_clause(codes),
                         _in_clause(nums))
        if debug:
            print 'QUERY:\n%s\n' % query
        cursor = connection.cursor()
        cursor.execute(query, [])
        results = _make_dict(cursor)
        if debug:
            print 'RESULTS:\n%s\n' % results
        if numtype == 'oclc':
            results = [row for row in results if _is_oclc(row['disp'])]
        bibids.extend([{'bibid':row['bibid'], 'libcode':row['libcode']}
            for row in results])
        if debug:
            print 'bibids so far:\n%s' % bibids
    return bibids


def holdings(bibids):
    query = """
SELECT bib_mfhd.bib_id AS bibid,
       mfhd_master.mfhd_id AS mfhdid,
       mfhd_master.location_id AS locid,
       mfhd_master.display_call_no AS callnum,
       location.location_display_name AS loc,
       library.library_name AS libcode,
       mfhdblob_vw.marc_record AS marcblob
FROM bib_mfhd INNER JOIN mfhd_master ON bib_mfhd.mfhd_id = mfhd_master.mfhd_id,
     location,
     library,
     bib_master,
     mfhdblob_vw
WHERE mfhd_master.location_id=location.location_id
AND mfhdblob_vw.mfhd_id=mfhd_master.mfhd_id
AND bib_mfhd.bib_id IN %s
AND mfhd_master.suppress_in_opac !='Y'
AND bib_mfhd.bib_id = bib_master.bib_id
AND bib_master.library_id = library.library_id
ORDER BY library.library_name"""
    query = query % _in_clause(bibids)
    cursor = connection.cursor()
    cursor.execute(query, [])
    results = _make_dict(cursor)
    holdings = []
    for record in results:
        marcblob = str(record.pop('marcblob'))
        holding = Holding(metadata=record, raw_marc=marcblob)
        holdings.append(holding)
    return holdings


def items(mfhdid):
    query = '''
SELECT DISTINCT display_call_no AS callnum,
       item_status_desc AS status,
       item_status.item_status AS statuscode,
       permLocation.location_display_name as permloc,
       tempLocation.location_display_name as temploc,
       item.item_id AS itemid,
       item_status_date AS statusdate,
       bib_master.bib_id AS bibid,
       mfhd_item.mfhd_id AS mfhdid,
       library.library_id AS libcode
FROM bib_master
JOIN library ON library.library_id = bib_master.library_id
JOIN bib_text ON bib_text.bib_id = bib_master.bib_id
JOIN bib_mfhd ON bib_master.bib_id = bib_mfhd.bib_id
JOIN mfhd_master ON mfhd_master.mfhd_id = bib_mfhd.mfhd_id
JOIN mfhd_item on mfhd_item.mfhd_id = mfhd_master.mfhd_id
JOIN item ON item.item_id = mfhd_item.item_id
JOIN item_status ON item_status.item_id = item.item_id
JOIN item_status_type
    ON item_status.item_status = item_status_type.item_status_type
JOIN location permLocation ON permLocation.location_id = item.perm_location
LEFT OUTER JOIN location tempLocation
    ON tempLocation.location_id = item.temp_location
WHERE bib_mfhd.mfhd_id = %s
ORDER BY itemid'''
    cursor = connection.cursor()
    cursor.execute(query, [mfhdid])
    results = _make_dict(cursor)
    items = []
    for record in results:
        item = Item(metadata=record)
        items.append(item)
        # now deduplicate
        # (sometimes when an item has a temploc change there are two items with
        # different statuses. We'll use the most recent change)
        if items and item.itemid == items[-1].itemid:
            if item.statusdate > items[-1].statusdate:
                items[-1] = item
        else:
            items.append(item)
    return items


def bibblob(bibid):
    query = """
SELECT wrlcdb.getBibBlob(%s) AS bibblob
FROM bib_text
WHERE bib_text.bib_id = %s"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid, bibid])
    return cursor.fetchone()


def mfhdblob(mfhdid):
    query = """
SELECT wrlcdb.getMFHDBlob(%s) AS mfhdblob
FROM mfhd_master
WHERE mfhd_id = %s"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhdid] * 2)
    return cursor.fetchone()


def _make_dict(cursor, first=False):
    desc = cursor.description
    mapped = [
        dict(zip([col[0].lower() for col in desc], row))
        for row in cursor.fetchall()
    ]
    # strip string values of trailing whitespace
    for d in mapped:
        for k, v in d.items():
            try:
                d[k] = v.strip()
            except:
                pass
    if first:
        if len(mapped) > 0:
            return mapped[0]
        return {}
    return mapped


def _normalize_num(num, num_type):
    if num_type == 'isbn':
        return clean_isbn(num)
    elif num_type == 'issn':
        return num.replace('-', ' ')
    elif num_type == 'oclc':
        return clean_oclc(num)
    return num


def _in_clause(items):
    return '(%s)' % ','.join(["'%s'" % item for item in items])
