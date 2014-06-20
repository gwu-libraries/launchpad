"""
These unit tests run against the live read-only Voyager database. They
are separate from the vanilla unit tests found in lp.ui.tests, since they
do not set up and tear down a test database and schema. Use the dbtest
management command to run them.
"""

import datetime
import unittest

from ui import db
from ui.db import get_item, get_availability, _fetch_one

status = ['http://schema.org/InStock', 'http://schema.org/OutOfStock']


class DbTests(unittest.TestCase):

    def test_get_item(self):
        i = get_item('6566525')
        self.assertEqual(i['@type'], 'Book')
        self.assertEqual(i['name'], 'Annotations to Finnegans wake')
        self.assertEqual(i['oclc'], ['61456541'])
        self.assertEqual(i['lccn'], '2005024683')
        self.assertEqual(i['isbn'], ['0801883814', '0801883822'])

    def test_issn(self):
        i = get_item('3155728')
        self.assertEqual(i['issn'], ['1059-1028'])

    def test_get_related_items(self):
        i = get_item('2281511')
        expected = set(['2281511', '1278053', '13079375', '4377796',
                        '5094040'])
        bibids = set(db.get_related_bibids(i))
        # we compare as sets because the order can change
        self.assertEqual(bibids, expected)

    def test_get_related_bibids_by_oclc(self):
        i = get_item('2281511')
        expected = ['1278053', '2281511', '13079375']
        bibids = db.get_related_bibids_by_oclc(i)
        self.assertEqual(expected, bibids)

        # this item has multiple oclc numbers to lookup
        i = get_item('12278722')
        self.assertEqual(db.get_related_bibids_by_oclc(i), ['12278722'])

    def test_get_related_bibids_by_lccn(self):
        i = get_item('2281511')
        expected = ['1278053', '2281511', '4377796', '5094040', '13079375']
        bibids = db.get_related_bibids_by_lccn(i)
        self.assertEqual(bibids, expected)

    def test_get_related_bibids_by_isbn(self):
        i = get_item('2281511')
        bibids = db.get_related_bibids_by_isbn(i)
        self.assertEqual(bibids, [])

    def test_get_related_bibids_by_issn(self):
        i = get_item('3155728')
        expected = ['519894', '1939227', '2946288', '3155728', '4990328']
        bibids = db.get_related_bibids_by_issn(i)
        self.assertEqual(bibids, expected)

    def test_availability(self):
        a = get_availability('5769326')
        self.assertEqual(a['wrlc'], '5769326')
        self.assertEqual(len(a['offers']), 1)

        o = a['offers'][0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'George Washington')
        self.assertEqual(o['availabilityAtOrFrom'].lower(), 'gelman stacks')
        self.assertEqual(o['sku'], 'PR6019.O9 F5 1999')
        self.assertTrue(o['status'] in status)
        self.assertEqual(o['serialNumber'], '3927007')

    def test_temp_location(self):
        # get a bib_id for something that's in temp location to make sure
        # that availabilityAtOrFrom uses that instead of the permanent location
        q = """
            SELECT bib_id, item.item_id
            FROM bib_mfhd, mfhd_item, item
            WHERE ROWNUM = 1
              AND item.temp_location = 682
              AND item.item_id = mfhd_item.item_id
              AND mfhd_item.mfhd_id = bib_mfhd.mfhd_id
            """
        bib_id, item_id = _fetch_one(q)
        a = get_availability(str(bib_id))
        for o in a['offers']:
            if 'serialNumber' in o and o['serialNumber'] == str(item_id):
                self.assertEqual(
                    o['availabilityAtOrFrom'].lower(),
                    'wrlc shared collections facility'
                )

    def test_checked_out(self):
        # get a bib_id for something that's checked out
        # 2382-12-31 due dates are indicators that the item
        # is in offsite storage
        q = """
            SELECT bib_id, circ_transactions.circ_transaction_id
            FROM bib_mfhd, mfhd_item, item, circ_transactions
            WHERE ROWNUM = 1
              AND circ_transactions.charge_due_date IS NOT NULL
              AND circ_transactions.charge_due_date < TO_DATE('2382-12-31', 'YYYY-MM-DD')
              AND circ_transactions.item_id = item.item_id
              AND item.item_id = mfhd_item.item_id
              AND mfhd_item.mfhd_id = bib_mfhd.mfhd_id
            """
        bib_id, circ_id = _fetch_one(q)
        a = get_availability(str(bib_id))
        found = False
        for offer in a['offers']:
            if 'availabilityStarts' in offer:
                found = True
        self.assertTrue(found)

    def test_georgetown_id(self):
        # lookup should run at subsecond speed but if encoding is messed up
        # they can turn into a full table scan which taks multiple seconds
        t0 = datetime.datetime.now()
        bibid = db.get_bibid_from_summonid('b10086948')
        t1 = datetime.datetime.now()
        self.assertEqual((t1 - t0).seconds, 0)
        self.assertEqual(bibid, '4218864')

        # make sure trailing x works
        bibid = db.get_bibid_from_summonid('b1268708x')
        self.assertEqual(bibid, '4467824')

    def test_georgemason_id(self):
        # lookup should run at subsecond speed but if encoding is messed up
        # they can turn into a full table scan which taks multiple seconds
        t0 = datetime.datetime.now()
        bibid = db.get_bibid_from_summonid('m55883')
        t1 = datetime.datetime.now()
        self.assertEqual((t1 - t0).seconds, 0)
        self.assertEqual(bibid, '1560207')

    def test_availability_georgemason(self):
        a = get_availability('m55883')
        self.assertEqual(a['wrlc'], '1560207')
        self.assertEqual(a['summon'], 'm55883')

        self.assertEqual(len(a['offers']), 1)
        o = a['offers'][0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'George Mason')
        self.assertEqual(o['sku'], 'PR6019.O9 F5')
        self.assertTrue(o['status'] in status)

    def test_availability_georgetown(self):
        a = get_availability('b10086948')
        self.assertEqual(a['wrlc'], '4218864')
        self.assertEqual(a['summon'], 'b10086948')

        self.assertEqual(len(a['offers']), 1)
        o = a['offers'][0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'Georgetown')
        self.assertEqual(o['sku'], 'PR6019.O9 F45 1959')
        self.assertTrue(o['status'] in status)

    def test_no_item_record(self):
        # can we get location from holdings record when no item exists?
        a = get_availability('12967951')
        self.assertEqual(a['offers'][0]['status'], 'http://schema.org/InStock')
        self.assertEqual(a['offers'][0]['availabilityAtOrFrom'],
                         'Lib special collections')

    def test_availability_no_bib_record(self):
        # this bibid is a legit georgetown id but we have no bib record
        a = get_availability('b29950983')
        self.assertEqual(a['offers'][0]['seller'], 'Georgetown')

    def test_bad_bibid(self):
        self.assertRaisesRegexp(Exception, 'unknown bibid format nevermind',
                                get_availability, 'nevermind')
