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
from ui.models import Bib


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
    cursor.execute(query, [bibid]*2)
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
    output = {'isbn':[], 'issn':[], 'oclc':[]}
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
        dictionary = {'norm':item['normal_heading'], 'disp':item['display_heading']}
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


def related_bibids(num_list, num_type, debug=False):
    query = """
SELECT DISTINCT bib_index.bib_id AS bibid, 
       bib_index.display_heading, 
       library.library_name AS libcode
FROM bib_index, library, bib_master
WHERE bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
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
    query = query % (_in_clause(settings.INDEX_CODES[num_type]), 
                     _in_clause(settings.INDEX_CODES[num_type]), 
                     _in_clause(num_list))
    if debug:
        print 'QUERY:\n%s\n' % query
    cursor = connection.cursor()
    cursor.execute(query, [])
    results = _make_dict(cursor)
    if debug:
        print 'RESULTS:\n%s\n' % results
    output_keys = ('bibid', 'libcode')
    if num_type == 'oclc':
        return [dict([(k, row[k]) for k in output_keys]) for row in results if _is_oclc(row['display_heading'])]
    return [dict([(k, row[k]) for k in output_keys]) for row in results]


def holdings(bibids):
    query = """
SELECT bib_mfhd.bib_id AS bibid,
       mfhd_master.mfhd_id AS mfhdid,
       mfhd_master.location_id AS locid,
       mfhd_master.display_call_no AS callnum,
       location.location_display_name AS loc,
       library.library_name AS libcode,
       wrlcdb.getMFHDBlob(mfhdid) AS mfhdblob
FROM bib_mfhd INNER JOIN mfhd_master ON bib_mfhd.mfhd_id = mfhd_master.mfhd_id,
     location,
     library,
     bib_master
WHERE mfhd_master.location_id=location.location_id
AND bib_mfhd.bib_id IN %s
AND mfhd_master.suppress_in_opac !='Y'
AND bib_mfhd.bib_id = bib_master.bib_id
AND bib_master.library_id = library.library_id
ORDER BY library.library_name"""
    query = query % _in_clause(bibids)
    cursor = connection.cursor()
    cursor.execute(query, [])
    return _make_dict(cursor)


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
    cursor.execute(query, [mfhdid]*2)
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
