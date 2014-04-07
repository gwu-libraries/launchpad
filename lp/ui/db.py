"""
Refactored helper methods for working with the database. This is a work in 
progress. You should probably be looking at ui.voyager until this work is
more fully developed.
"""

import pymarc

from django.db import connection


def get_item(bibid):
    marc = get_marc(bibid)
    return {
        '@type': 'Book',
        'title': marc['245']['a']
    }


def get_marc(bibid):
    query = "SELECT wrlcdb.getBibBlob(%s) AS marcblob from bib_master"
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    row = cursor.fetchone()
    raw_marc = str(row[0])
    record = pymarc.record.Record(data=raw_marc)
    return record

