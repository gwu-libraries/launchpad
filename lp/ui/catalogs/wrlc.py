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
    cursor.execute(query, [bibid, bibid, bibid, bibid, bibid, bibid, bibid, bibid, bibid, bibid])
    data = _make_dict(cursor, first=True)
    bib = Bib()
    for field in data:
        bib[field.lower()] = data[field]
    return bib


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

