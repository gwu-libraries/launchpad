"""
Refactored helper methods for working with the database. This is a work in
progress. You should probably be looking at ui.voyager until this work is
more fully developed.
"""

import re
import pymarc
import logging

from PyZ3950 import zoom
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
    # Voyager's antiquated Oracle indexes properly
    # https://github.com/gwu-libraries/launchpad/issues/611
    django.db.backends.oracle.base.convert_unicode = \
        django.utils.encoding.force_bytes


def get_item(bibid):
    """
    Get JSON-LD for a given bibid.
    """
    item = {
        '@type': 'Book',
    }

    marc = get_marc(bibid)

    item['wrlc'] = bibid

    # get item name (title)
    item['name'] = marc['245']['a'].strip(' /')

    # get oclc number
    for f in marc.get_fields('035'):
        if f['a'] and f['a'].startswith('(OCoLC)'):
            if 'oclc' not in item:
                item['oclc'] = []
            oclc = f['a'].replace('(OCoLC)', '').replace('OCM', '')
            item['oclc'].append(oclc)

    # get lccn
    f = marc['010']
    if f:
        item['lccn'] = marc['010']['a'].strip()

    # get isbns
    for f in marc.get_fields('020'):
        if 'isbn' not in item:
            item['isbn'] = []
        isbn = f['a']
        # extract just the isbn, e.g. "0801883814 (hardcover : alk. paper)"
        isbn = isbn.split()[0]
        item['isbn'].append(isbn)

    # get issns
    for f in marc.get_fields('022'):
        if 'issn' not in item:
            item['issn'] = []
        item['issn'].append(f['a'])

    return item


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

    url = 'http://%s/item/%s' % (_get_hostname(), bibid)
    results = {
        '@context': {
            '@vocab': 'http://schema.org/',
        },
        '@id': url,
        'offers': [],
        'wrlc': bibid,
    }

    # if the bibid is numeric we can look it up locally in Voyager
    if re.match('^\d+$', bibid):
        results['offers'] = _get_offers(bibid)

    # George Mason and Georgetown have special ids in Summon and we need
    # to talk to their catalogs to determine availability
    else:
        if bibid.startswith('m'):
            results['offers'] = _get_offers_z3950(bibid, 'George Mason')
        elif bibid.startswith('b'):
            results['offers'] = _get_offers_z3950(bibid, 'Georgetown')
        else:
            raise Exception("unknown bibid format %s" % bibid)

        # update wrlc id if there is a record in voyager for it
        wrlc_id = get_bibid_from_summonid(bibid)
        if wrlc_id:
            results['wrlc'] = wrlc_id
            results['summon'] = bibid

    return results


def get_bibid_from_summonid(id):
    """
    For some reason Georgetown and GeorgeMason loaded Summon with their
    own IDs so we need to look them up differently.
    """
    if re.match('^\d+$', id):
        return id
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


def get_related_bibids(item):
    bibid = item['wrlc']
    bibids = set([bibid])
    bibids |= set(get_related_bibids_by_oclc(item))
    bibids |= set(get_related_bibids_by_lccn(item))
    bibids |= set(get_related_bibids_by_isbn(item))
    return list(bibids)


def get_related_bibids_by_lccn(item):
    if 'lccn' not in item:
        return []

    q = '''
    SELECT DISTINCT bib_index.bib_id, bib_text.title
    FROM bib_index, library, bib_master, bib_text
    WHERE bib_index.bib_id=bib_master.bib_id
    AND bib_master.library_id=library.library_id
    AND bib_master.suppress_in_opac='N'
    AND bib_index.index_code IN ('010A')
    AND bib_index.normal_heading != 'OCOLC'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
    AND bib_text.bib_id = bib_master.bib_id
    AND bib_index.normal_heading IN (
        SELECT bib_index.normal_heading
        FROM bib_index
        WHERE bib_index.index_code IN ('010A')
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
        AND bib_id IN (
            SELECT DISTINCT bib_index.bib_id
            FROM bib_index
            WHERE bib_index.index_code IN ('010A')
            AND bib_index.normal_heading = %s
            AND bib_index.normal_heading != 'OCOLC'
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
            )
        )
    ORDER BY bib_index.bib_id
    '''

    rows = _fetch_all(q, [item['lccn']])
    rows = _filter_by_title(rows, item['name'])

    return rows


def get_related_bibids_by_oclc(item):
    if 'oclc' not in item or len(item['oclc']) == 0:
        return []

    binds = ','.join(['%s'] * len(item['oclc']))

    q = u'''
    SELECT DISTINCT bib_index.bib_id, bib_text.title
    FROM bib_index, bib_master, bib_text
    WHERE bib_index.bib_id=bib_master.bib_id
    AND bib_master.suppress_in_opac='N'
    AND bib_index.index_code IN ('035A')
    AND bib_index.normal_heading != 'OCOLC'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
    AND bib_text.bib_id = bib_master.bib_id
    AND bib_index.normal_heading IN (
        SELECT bib_index.normal_heading
        FROM bib_index
        WHERE bib_index.index_code IN ('035A')
        AND bib_index.normal_heading != bib_index.display_heading
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
        AND bib_id IN (
            SELECT DISTINCT bib_index.bib_id
            FROM bib_index
            WHERE bib_index.index_code IN ('035A')
            AND bib_index.normal_heading IN (%s)
            AND bib_index.normal_heading != 'OCOLC'
            AND bib_index.normal_heading != bib_index.display_heading
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
            )
        )
    ORDER BY bib_index.bib_id
    ''' % binds

    rows = _fetch_all(q, item['oclc'])
    rows = _filter_by_title(rows, item['name'])

    return rows


def get_related_bibids_by_isbn(item):
    if 'isbn' not in item or len(item['isbn']) == 0:
        return []

    binds = ','.join(['%s'] * len(item['isbn']))

    q = '''
    SELECT DISTINCT bib_index.bib_id, bib_text.title
    FROM bib_index, bib_master, bib_text
    WHERE bib_index.bib_id=bib_master.bib_id
    AND bib_master.suppress_in_opac='N'
    AND bib_index.index_code IN ('020N','020A','ISB3','020Z')
    AND bib_index.normal_heading != 'OCOLC'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
    AND bib_text.bib_id = bib_master.bib_id
    AND bib_index.normal_heading IN (
        SELECT bib_index.normal_heading
        FROM bib_index
        WHERE bib_index.index_code IN ('020N','020A','ISB3','020Z')
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
        AND bib_id IN (
            SELECT DISTINCT bib_index.bib_id
            FROM bib_index
            WHERE bib_index.index_code IN ('020N','020A','ISB3','020Z')
            AND bib_index.normal_heading IN (%s)
            AND bib_index.normal_heading != 'OCOLC'
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
            )
        )
    ORDER BY bib_index.bib_id
    ''' % binds

    rows = _fetch_all(q, item['isbn'])
    rows = _filter_by_title(rows, item['name'])

    return rows


def get_related_bibids_by_issn(item):
    if 'issn' not in item or len(item['issn']) == 0:
        return []

    binds = ','.join(['%s'] * len(item['issn']))

    q = '''
    SELECT DISTINCT bib_index.bib_id, bib_text.title
    FROM bib_index, bib_master, bib_text
    WHERE bib_index.bib_id=bib_master.bib_id
    AND bib_master.suppress_in_opac='N'
    AND bib_index.index_code IN ('022A','022Z','022L')
    AND bib_index.normal_heading != 'OCOLC'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
    AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
    AND bib_text.bib_id = bib_master.bib_id
    AND bib_index.normal_heading IN (
        SELECT bib_index.normal_heading
        FROM bib_index
        WHERE bib_index.index_code IN ('022A','022Z','022L')
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
        AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
        AND bib_id IN (
            SELECT DISTINCT bib_index.bib_id
            FROM bib_index
            WHERE bib_index.index_code IN ('022A','022Z','022L')
            AND bib_index.normal_heading IN (%s)
            AND bib_index.normal_heading != 'OCOLC'
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SET%%%%'
            AND UPPER(bib_index.display_heading) NOT LIKE '%%%%SER%%%%'
            )
        )
    ORDER BY bib_index.bib_id
    ''' % binds

    # voyager wants "1059-1028" to look like "1059 1028"
    issns = [i.replace('-', ' ') for i in item['issn']]

    rows = _fetch_all(q, issns)
    rows = _filter_by_title(rows, item['name'])

    return rows


def _get_offers(bibid):
    offers = []
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
    # this will get set to true for libraries that require a z39.50 lookup
    need_z3950_lookup = False
    for row in cursor.fetchall():
        seller = settings.LIB_LOOKUP.get(row[10], '?')
        desc = row[1] or 'Available'
        if row[9] == '2382-12-31' or (row[9] == None and row[11] == 'WRLC Shared Collections Facility'):
            desc = 'Off Site'
        if desc == 'Not Charged':
            desc = 'Available'
        o = {
            '@type': 'Offer',
            'seller': seller,
            'sku': row[0],
            'availability': _normalize_status(row[2]),
            'description': desc,
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
            # due date of 2382-12-31 means it's in offsite storage
            if row[9] == '2382-12-31':
                o['availability'] = 'http://schema.org/InStock'
            else:
                o['availabilityStarts'] = row[9]

        # z39.50 lookups
        if seller == 'George Mason' or seller == 'Georgetown':
            need_z3950_lookup = True

        offers.append(o)

    if need_z3950_lookup:
        library = offers[0]['seller']
        return _get_offers_z3950(bibid, library)

    return offers


def _get_offers_z3950(id, library):
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

    if hasattr(rec, 'data') and not hasattr(rec.data, 'holdingsData'):
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
                o['availability'] = 'http://schema.org/InStock'
                o['description'] = 'Available'
            elif note in ('SPC USE ONLY', 'LIB USE ONLY'):
                o['availability'] = 'http://schema.org/InStoreOnly'
                o['description'] = 'Available'
            else:
                # set availabilityStarts from "DUE 09-15-14"
                m = re.match('DUE (\d\d)-(\d\d)-(\d\d)', note)
                if m:
                    m, d, y = [int(i) for i in m.groups()]
                    o['availabilityStarts'] = "20%02i-%02i-%02i" % (y, m, d)

                o['availability'] = 'http://schema.org/OutOfStock'
                o['description'] = 'Checked Out'

        elif hasattr(h, 'circulationData'):
            cd = h.circulationData[0]
            if cd.availableNow is True:
                o['availability'] = 'http://schema.org/InStock'
                o['description'] = 'Available'
            else:
                if hasattr(cd, 'availabilityDate') and cd.availablityDate:
                    m = re.match("^(\d{4}-\d{2}-\d{2}).+", cd.availablityDate)
                    if m:
                        o['availabilityStarts'] = m.group(1)
                o['availability'] = 'http://schema.org/OutOfStock'
                o['description'] = 'Checked Out'

        else:
            logging.warn("unknown availability: bibid=%s library=%s h=%s",
                         id, library, h)

        # some locations have a weird period before the name
        o['availabilityAtOrFrom'] = o['availabilityAtOrFrom'].lstrip('.')

        offers.append(o)

    return offers


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
    elif status_id in (19, 20):
        return 'http://schema.org/PreOrder'
    elif status_id:
        return 'http://schema.org/OutOfStock'
    else:
        return 'http://schema.org/InStock'


def _fetch_one(query, params=[]):
    cursor = connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchone()


def _fetch_all(query, params=None):
    cursor = connection.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    return cursor.fetchall()


def _normalize_location(location):
    if not location:
        return None
    parts = location.split(': ', 1)
    norm_location = parts.pop().title()
    if parts:
        tmp = parts.pop()
        if tmp == "GW Law" or tmp == "GW Medical":
            norm_location = "%s: %s" % (tmp,norm_location)
    return norm_location


def _get_hostname():
    if len(settings.ALLOWED_HOSTS) > 0:
        return settings.ALLOWED_HOSTS[0]
    return 'localhost'


def _filter_by_title(rows, expected):
    bibids = []
    for bibid, title in rows:
        min_len = min(len(expected), len(title))
        if title.lower()[0:min_len] == expected.lower()[0:min_len]:
            bibids.append(str(bibid))
    return bibids
