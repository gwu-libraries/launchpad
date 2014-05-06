"""
Refactored helper methods for working with the database. This is a work in
progress. You should probably be looking at ui.voyager until this work is
more fully developed.
"""

import re
import pymarc

from django.db import connection
from django.conf import settings

# oracle specific configuration since Voyager's Oracle requires ASCII

if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.oracle':
    import django.utils.encoding
    import django.db.backends.oracle.base
    # connections are in ascii
    django.db.backends.oracle.base._setup_environment([
        ('NLS_LANG', '.US7ASCII'),
    ])
    # string bind parameters must not be promoted to Unicode in order to use
    # Oracle indexes properly
    # https://github.com/gwu-libraries/launchpad/issues/611
    django.db.backends.oracle.base.convert_unicode = \
        django.utils.encoding.force_bytes


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
    if not isinstance(bibid, basestring):
        raise Exception("supplied a non-string: %s" % bibid)

    # if bibid isn't numeric it's a temporary summon id that we need to resolve
    if not re.match('^\d+', bibid):
        summon_id = bibid
        bibid = get_bibid_from_summonid(bibid)
        if not bibid:
            # TODO: not all georgetown ids have bib records e.g. b29950983
            bibid = summon_id
    else:
        summon_id = None

    query = \
        """
        SELECT DISTINCT
          display_call_no,
          item_status_desc,
          item_status.item_status,
          perm_location.location_display_name as PermLocation,
          temp_location.location_display_name as TempLocation,
          mfhd_item.item_enum,
          mfhd_item.chron,
          item.item_id,
          item_status_date,
          to_char(CIRC_TRANSACTIONS.CHARGE_DUE_DATE, 'yyyy-mm-dd') AS DUE,
          library.library_display_name,
          holding_location.location_display_name as HoldingLocation
        FROM bib_master
        JOIN library ON library.library_id = bib_master.library_id
        JOIN bib_mfhd ON bib_master.bib_id = bib_mfhd.bib_id
        JOIN mfhd_master ON mfhd_master.mfhd_id = bib_mfhd.mfhd_id
        JOIN library ON bib_master.library_id = library.library_id
        JOIN location holding_location 
          ON mfhd_master.location_id = holding_location.location_id
        LEFT OUTER JOIN mfhd_item
          ON mfhd_item.mfhd_id = mfhd_master.mfhd_id
        LEFT OUTER JOIN item
          ON item.item_id = mfhd_item.item_id
        LEFT OUTER JOIN item_status
          ON item_status.item_id = item.item_id
        LEFT OUTER JOIN item_status_type
          ON item_status.item_status = item_status_type.item_status_type
        LEFT OUTER JOIN location perm_location
          ON perm_location.location_id = item.perm_location
        LEFT OUTER JOIN location temp_location
          ON temp_location.location_id = item.temp_location
        LEFT OUTER JOIN circ_transactions
          ON item.item_id = circ_transactions.item_id
        WHERE bib_master.bib_id = %s
        AND mfhd_master.suppress_in_opac != 'Y'
        ORDER BY PermLocation, TempLocation, item_status_date desc
        """

    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    hostname = _get_hostname()

    results = {
        '@context': {
            '@vocab': 'http://schema.org/',
        },
        '@id': 'http://' + hostname + '/item/' + bibid,
        'offers': [],
        # TODO: make sure wrlc is defined in json-ld @context
        'wrlc': bibid,
    }

    # if they asked using the temporary summon id (Georgetown/GeorgeMason)
    # include that in the response too
    # TODO: make sure summon is definied in json-ld @context
    if summon_id:
        results['summon'] = summon_id

    # this will get set to true for libraries that require a z39.50 lookup
    need_z3950_lookup = False

    for row in cursor.fetchall():
        seller = settings.LIB_LOOKUP.get(row[10], '?')
        o = {
            '@type': 'Offer',
            'seller': seller,
            'sku': row[0],
            'status': _normalize_status(row[2]),
        }

        # use temp location if there is one, otherwise use perm location
        # or the holding location in cases where there is no item record
        if row[4]:
            o['availabilityAtOrFrom'] = _normalize_location(row[4])
        elif row[3]:
            o['availabilityAtOrFrom'] = _normalize_location(row[3])
        else:
            o['availabilityAtOrFrom'] = _normalize_location(row[11])

        # serial number can be null, apparently
        if row[7]:
            o['serialNumber'] = str(row[7])

        # add due date if we have one
        if row[9]:
            o['availabilityStarts'] = row[9]

        # z39.50 lookups
        if seller == 'George Mason' or seller == 'Georgetown':
            need_z3950_lookup = True

        results['offers'].append(o)

    if need_z3950_lookup:
        library = results['offers'][0]['seller']
        if summon_id:
            id = summon_id
        else:
            id = bibid
        results['offers'] = _get_availability_z3950(id, library)

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
    else:
        return 'http://schema.org/InStock'



def _fetch_one(query, params=[]):
    cursor = connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchone()


def _fetch_all(query, params):
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


def _get_hostname():
    if len(settings.ALLOWED_HOSTS) > 0:
        return settings.ALLOWED_HOSTS[0]
    return 'localhost'


def _get_availability_z3950(id, library):
    from PyZ3950 import zoom
    offers = []

    # determine which server to talk to
    if library == 'Georgetown':
        conf = settings.Z3950_SERVERS['GT']
    elif library == 'George Mason':
        id = id.strip('m')
        conf = settings.Z3950_SERVERS['GM']
    else:
        raise Exception("unrecognized library %s" % library)

    # search for the id, and get the first record
    z = zoom.Connection(conf['IP'], conf['PORT'])
    z.databaseName = conf['DB']
    z.preferredRecordSyntax = conf['SYNTAX']
    q = zoom.Query('PQF', '@attr 1=12 %s' % id.encode('utf-8'))
    results = z.search(q)
    if len(results) == 0:
        return []
    rec = results[0]

    # normalize holdings information as schema.org offers

    if not hasattr(rec, 'data') and not hasattr(rec.data, 'holdingsData'):
        return []

    for holdings_data in rec.data.holdingsData:
        h = holdings_data[1]
        o = {'@type': 'Offer', 'seller': library}

        if hasattr(h, 'callNumber'):
            o['sku'] = h.callNumber.rstrip('\x00').strip()

        if hasattr(h, 'localLocation'):
            o['availabilityAtOrFrom'] = h.localLocation.rstrip('\x00')

        if hasattr(h, 'publicNote') and library == 'Georgetown':
            note = h.publicNote.rstrip('\x00')
            if note == 'AVAILABLE':
                o['status'] = 'http://schema.org/InStock'
            else:
                # set availabilityStarts from "DUE 09-15-14"
                # try b3635072
                m = re.match('DUE (\d\d)-(\d\d)-(\d\d)', note)
                if m:
                    m, d, y = [int(i) for i in m.groups()]
                    o['availabilityStarts'] = "20%s-%s-%s" % (y, m, d)

                o['status'] = 'http://schema.org/OutOfStock'

        elif hasattr(h, 'circulationData'):
            cd = h.circulationData[0]
            if cd.availableNow is True:
                o['status'] = 'http://schema.org/InStock'
            else:
                if cd.availabilityDate:
                    o['availabilityStarts'] = cd.availablityDate
                    # TODO: set availabilityStarts to YYYY-MM-DD
                o['status'] = 'http://schema.org/OutOfStock'

        else:
            raise Exception("unknown availability: bibid=%s library=%s" %
                            (id, library))

        offers.append(o)

    return offers
