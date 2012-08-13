import pycountry
from PyZ3950 import zoom
import urllib
import copy

from django.conf import settings
from django.db import connection, transaction
from django.utils.encoding import smart_str, smart_unicode

from ui.templatetags.launchpad_extras import cjk_info
from ui.templatetags.launchpad_extras import clean_isbn, clean_oclc, clean_issn
from ui.models import Bib


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
       pub_place AS publisher_date,
       publisher_date,
       bib_format AS format_code,
       language AS language_code,
       library_name AS library_code,
       network_number AS oclc,
       wrlcdb.GetBibTag(%s,'856') AS marc856,
       RTRIM(wrlcdb.GetMarcField(%s,0,0,'245','','',1)) AS marc245,
       wrlcdb.GetAllBibTag(%s, '880', 1) AS marc880,
       wrlcdb.GetBibTag(%s, '006') AS marc006,
       wrlcdb.GetBibTag(%s, '007') AS marc007,
       wrlcdb.GetBibTag(%s, '008') AS marc008,
       wrlcdb.GetAllBibTag(%s, '700', 1) AS marc700,
       wrlcdb.GetAllBibTag(%s, '710', 1) AS marc710,
       wrlcdb.GetAllBibTag(%s, '711', 1) AS marc711
FROM bib_text, bib_master, library
WHERE bib_text.bib_id=%s
AND bib_text.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid]*10)
    data = _make_dict(cursor, first=True)
    bib = Bib()
    for field in data:
        bib[field.lower()] = data[field]
    return bib


def bibid(num, num_type):
    if num_type in ('gtbibid', 'gmbibid'):
        return _convert_to_wrlc_bibid(bibid=num, bibid_type=num_type)
    num = _normalize_num(num, num_type)
    query = """
SELECT bib_index.bib_id, bib_master.library_id, library.library_name
FROM bib_index, bib_master, library
WHERE bib_index.index_code IN %s
AND bib_index.normal_heading = '%s'
AND bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id"""
    query = query % (_in_clause(settings.INDEX_CODES[num_type]), num)
    cursor = connection.cursor()
    cursor.execute(query, [])
    bibs = _make_dict(cursor)
    for bib in bibs:
        if bib['LIBRARY_NAME'] == settings.PREF_LIB:
            return bib['BIB_ID']
    return bibs[0]['BIB_ID'] if bibs else None


def _convert_to_wrlc_bibid(bibid, bibid_type):
    query = """
SELECT bib_index.bib_id
FROM bib_index
WHERE bib_index.index_code = '%s'
AND bib_index.normal_heading = '%s'"""
    if bibid_type == 'gtbibid':
        index_code = '907A'
    elif bibid_type == 'gmbibid':
        index_code = '035A'
        query += "\nAND bib_index.normal_heading=bib_index.display_heading"
    query = query % (index_code, bibid)
    print query
    cursor = connection.cursor()
    cursor.execute(query, [])
    return cursor.fetchone()[0] 


def related_bibids(num_list, num_type):
    query = """
SELECT DISTINCT bib_index.bib_id, bib_index.display_heading, library.library_name
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
    query = query % (_in_clause(settings.INDEX_CODES[num_type]), _in_clause(settings.INDEX_CODES[num_type]), _in_clause(num_list))
    cursor = connection.cursor()
    cursor.execute(query, [])
    results = _make_dict(cursor)
    output_keys = ('BIB_ID', 'LIBRARY_NAME')
    if num_type == 'oclc':
        return [dict([(k, row[k]) for k in output_keys]) for row in results if _is_oclc(row['DISPLAY_HEADING'])]
    return [dict([(k, row[k]) for k in output_keys]) for row in results]


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
        return num.replace('-',' ')
    elif num_type == 'oclc':
        return clean_oclc(num)
    return num


def _in_clause(items):
    return '(%s)' % ','.join(["'%s'" % item for item in items])
