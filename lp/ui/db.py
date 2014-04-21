"""
Refactored helper methods for working with the database. This is a work in
progress. You should probably be looking at ui.voyager until this work is
more fully developed.
"""

import re
import pymarc

from django.db import connection
from django.conf import settings
from django.core.urlresolvers import reverse


def get_item(bibid):
    """
    Get JSON-LD for a given bibid.
    """
    marc = get_marc(bibid)
    return {
        '@type': 'Book',
        'title': marc['245']['a']
    }


def get_marc(bibid):
    """
    Get pymarc.Record for a given bibid.
    """
    query = "SELECT wrlcdb.getBibBlob(%s) AS marcblob from bib_master"
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    row = cursor.fetchone()
    raw_marc = str(row[0])
    record = pymarc.record.Record(data=raw_marc)
    return record


def get_availability(bibid):
    """
    Get availability information as JSON-LD for a given bibid.
    """
    # TODO: add all parameter to get related bibids from other institutions?

    if not isinstance(bibid, basestring):
        raise Exception("supplied a non-string: %s" % bibid)

    # if bibid isn't numeric it's a temporary summon id that we need to resolve
    if not re.match('^\d+', bibid):
        summon_id = bibid
        bibid = get_bibid_from_summonid(bibid)
        if not bibid:
            return None
    else:
        summon_id = None

    query = \
        """
        SELECT DISTINCT
          display_call_no,
          item_status_desc,
          item_status.item_status,
          permLocation.location_display_name as PermLocation,
          tempLocation.location_display_name as TempLocation,
          mfhd_item.item_enum,
          mfhd_item.chron,
          item.item_id,
          item_status_date,
          to_char(CIRC_TRANSACTIONS.CHARGE_DUE_DATE, 'yyyy-mm-dd') AS DUE,
          library.library_display_name
        FROM bib_master
        JOIN library ON library.library_id = bib_master.library_id
        JOIN bib_mfhd ON bib_master.bib_id = bib_mfhd.bib_id
        JOIN mfhd_master ON mfhd_master.mfhd_id = bib_mfhd.mfhd_id
        JOIN library ON bib_master.library_id = library.library_id
        LEFT OUTER JOIN mfhd_item
          ON mfhd_item.mfhd_id = mfhd_master.mfhd_id
        LEFT OUTER JOIN item
          ON item.item_id = mfhd_item.item_id
        LEFT OUTER JOIN item_status
          ON item_status.item_id = item.item_id
        LEFT OUTER JOIN item_status_type
          ON item_status.item_status = item_status_type.item_status_type
        LEFT OUTER JOIN location permLocation
          ON permLocation.location_id = item.perm_location
        LEFT OUTER JOIN location tempLocation
          ON tempLocation.location_id = item.temp_location
        LEFT OUTER JOIN circ_transactions
          ON item.item_id = circ_transactions.item_id
        WHERE bib_master.bib_id = %s
        AND mfhd_master.suppress_in_opac != 'Y'
        ORDER BY PermLocation, TempLocation, item_status_date desc
        """

    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    hostname = get_hostname()

    results = {
        '@context': {
            '@vocab': 'http://schema.org/',
        },
        '@id': 'http://' + hostname + reverse('item', args=[bibid]),
        'offers': [],
        # TODO: make sure wrlc is defined in json-ld @context
        'wrlc': bibid,
    }

    # if they asked using the temporary summon id (Georgetown/GeorgeMason)
    # include that in the response too
    # TODO: make sure summon is definied in json-ld @context
    if summon_id:
        results['summon'] = summon_id

    for row in cursor.fetchall():
        seller = settings.LIB_LOOKUP.get(row[10], '?')
        a = {
            '@type': 'Offer',
            'seller': seller,
            'sku': row[0],
            'status': _normalize_status(row[2]),
        }

        # use temp location if there is one, otherwise use perm location
        if row[4]:
            a['availabilityAtOrFrom'] = _normalize_location(row[4])
        else:
            a['availabilityAtOrFrom'] = _normalize_location(row[3])

        # serial number can be null, apparently
        if row[7]:
            a['serialNumber'] = str(row[7])

        # add due date if we have one
        if row[9]:
            a['availabilityStarts'] = row[9]

        results['offers'].append(a)

    return results


def _normalize_status(status_id):
    """
    This function will turn one of the standard item status codes
    into a GoodRelations URI:

    http://www.w3.org/community/schemabibex/wiki/Holdings_via_Offer

    Here is a snapshot in time of item_status_ids, their description,
    and count:

      1 Not Charged                  5897029
      2 Charged                      1832241
      3 Renewed                        39548
     17 Withdrawn                      26613
      4 Overdue                        22966
     14 Lost--System Applied           16687
     12 Missing                        15816
     19 Cataloging Review              15584
     20 Circulation Review             11225
      9 In Transit Discharged           7493
     13 Lost--Library Applied           7262
     11 Discharged                      2001
     18 At Bindery                      1603
     15 Claims Returned                  637
     16 Damaged                          525
     22 In Process                       276
      6 Hold Request                      39
     10 In Transit On Hold                24
      8 In Transit                        23
      5 Recall Request                    17
      7 On Hold                            6
     24 Short Loan Request                 2

    """

    # TODO: more granularity needed?
    if status_id == 1:
        return 'http://schema.org/InStock'
    elif status_id:
        return 'http://schema.org/OutOfStock'


def fetch_one(query, params=[]):
    cursor = connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchone()


def fetch_all(query, params):
    cursor = connection
    cursor.execute(query, params)
    return cursor.fetchall()


def _normalize_location(location):
    if not location:
        return None
    parts = location.split(': ', 1)
    return parts.pop().capitalize()


def get_bibid_from_summonid(id):
    """
    For some reason Georgetown and GeorgeMason loaded Summon with their
    own IDs so we need to look them up differently.
    """
    if id.startswith('b'):
        return get_bibid_from_gtid(id)
    elif id.startswith('m'):
        return get_bibid_from_gmid(id)
    else:
        return None


def get_bibid_from_gtid(id):
    query = \
        """
        SELECT bib_index.bib_id
        FROM bib_index, bib_master
        WHERE bib_index.normal_heading = %s
        AND bib_index.index_code = '907A'
        AND bib_index.bib_id = bib_master.bib_id
        AND bib_master.library_id IN ('14', '15')
        """
    cursor = connection.cursor()
    cursor.execute(query, [id.upper()])
    results = cursor.fetchone()
    return str(results[0]) if results else None


def get_bibid_from_gmid(id):
    id = id.lstrip("m")
    query = \
        """
        SELECT bib_index.bib_id
        FROM bib_index, bib_master
        WHERE bib_index.index_code = '035A'
        AND bib_index.bib_id=bib_master.bib_id
        AND bib_index.normal_heading=bib_index.display_heading
        AND bib_master.library_id = '6'
        AND bib_index.normal_heading = %s
        """
    cursor = connection.cursor()
    cursor.execute(query, [id.upper()])
    results = cursor.fetchone()
    return str(results[0]) if results else None


def get_hostname():
    if len(settings.ALLOWED_HOSTS) > 0:
        return settings.ALLOWED_HOSTS[0]
    return 'localhost'
