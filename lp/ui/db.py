"""
Refactored helper methods for working with the database. This is a work in 
progress. You should probably be looking at ui.voyager until this work is
more fully developed.
"""

import pymarc

from django.db import connection
from django.conf import settings


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

def get_availability(bibid):

    # old query
    """        
        SELECT mfhd_master.mfhd_id, mfhd_master.location_id, 
               mfhd_master.display_call_no, location.location_display_name,
               library.library_name, location.location_name
        FROM bib_mfhd
        INNER JOIN mfhd_master ON bib_mfhd.mfhd_id = mfhd_master.mfhd_id,
             location, library, bib_master
        WHERE mfhd_master.location_id = location.location_id
        AND bib_mfhd.bib_id = %s
        AND mfhd_master.suppress_in_opac != 'Y'
        AND bib_mfhd.bib_id = bib_master.bib_id
        AND bib_master.library_id=library.library_id
        ORDER BY library.library_name
    """

    # TODO: left outer join on item so we can get library name for GT, GM, etc
    query = """
SELECT DISTINCT display_call_no, item_status_desc, item_status.item_status,
       permLocation.location_display_name as PermLocation,
       tempLocation.location_display_name as TempLocation,
       mfhd_item.item_enum, mfhd_item.chron, item.item_id, item_status_date,
       to_char(CIRC_TRANSACTIONS.CHARGE_DUE_DATE, 'mm-dd-yyyy') AS DUE,
       library.library_display_name
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
JOIN library ON bib_master.library_id = library.library_id
LEFT OUTER JOIN location tempLocation ON
    tempLocation.location_id = item.temp_location
LEFT OUTER JOIN circ_transactions ON item.item_id = circ_transactions.item_id
WHERE bib_master.bib_id = %s
AND mfhd_master.suppress_in_opac != 'Y'
ORDER BY PermLocation, TempLocation, item_status_date desc"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])

    results = []
    for row in cursor.fetchall():
        seller = settings.LIB_LOOKUP.get(row[10], '?')
        a = {
            '@type': 'Offer',
            'seller': seller,
            'availabilityAtOrFrom': row[3],
            'sku': row[0],
            'status': row[2],
            'serialNumber': row[7],
        }
        results.append(a)

    return results

