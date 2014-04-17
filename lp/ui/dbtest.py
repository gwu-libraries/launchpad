"""
These unit tests run against the live read-only Voyager database. They
are separate from the vanilla unit tests found in lp.ui.tests, since they
do not set up and tear down a test database and schema. Use the dbtest
management command to run them.
"""

from unittest import TestCase

from ui import db
from ui.db import get_item, get_availability, fetch_one


class DbTests(TestCase):

    def test_book(self):
        i = get_item('12278722')
        self.assertEqual(i['@type'], 'Book')

    def test_availability(self):
        a = get_availability('5769326')
        self.assertEqual(a['wrlc'], '5769326')
        self.assertEqual(len(a['offers']), 1)

        o = a['offers'][0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'George Washington')
        self.assertEqual(o['availabilityAtOrFrom'].lower(), 'gelman stacks')
        self.assertEqual(o['sku'], 'PR6019.O9 F5 1999')
        self.assertTrue(o['status'] in [
            'http://schema.org/InStock',
            'http://schema.org/OutOfStock'
        ])
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
        bib_id, item_id = fetch_one(q)
        a = get_availability(str(bib_id))
        for o in a['offers']:
            if 'serialNumber' in o and o['serialNumber'] == str(item_id):
                self.assertEqual(
                    o['availabilityAtOrFrom'].lower(),
                    'wrlc shared collections facility'
                )

    def test_checked_out(self):
        # get a bib_id for something that's checked out
        q = """
            SELECT bib_id, circ_transactions.circ_transaction_id
            FROM bib_mfhd, mfhd_item, item, circ_transactions
            WHERE ROWNUM = 1
              AND circ_transactions.charge_due_date IS NOT NULL
              AND circ_transactions.item_id = item.item_id
              AND item.item_id = mfhd_item.item_id
              AND mfhd_item.mfhd_id = bib_mfhd.mfhd_id
            """
        bib_id, circ_id = fetch_one(q)
        a = get_availability(str(bib_id))
        found = False
        for offer in a['offers']:
            if 'availabilityStarts' in offer:
                found = True
        self.assertTrue(found)

    def test_georgetown_id(self):
        bibid = db.get_bibid_from_summonid('b10086948')
        self.assertEqual(bibid, '4218864')
        bibid = db.get_bibid_from_summonid('b1268708x')
        self.assertEqual(bibid, '4467824')

    def test_georgemason_id(self):
        bibid = db.get_bibid_from_summonid('m55883')
        self.assertEqual(bibid, '1560207')

    def test_bad_bibd(self):
        self.assertEqual(get_availability('nevermind'), None)

    def test_availability_georgemason(self):
        a = get_availability('m55883')
        self.assertEqual(a['wrlc'], '1560207')
        self.assertEqual(a['summon'], 'm55883')

        self.assertEqual(len(a['offers']), 1)
        o = a['offers'][0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'George Mason')
        self.assertEqual(o['sku'], 'PR6019.O9 F5')

        # TODO: status shoudn't be None
        self.assertEqual(o['status'], None)

    def test_availability_georgetown(self):
        a = get_availability('b10086948')
        self.assertEqual(a['wrlc'], '4218864')
        self.assertEqual(a['summon'], 'b10086948')

        self.assertEqual(len(a['offers']), 1)
        o = a['offers'][0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'Georgetown')

        # TODO: where is the call number
        # self.assertEqual(o['sku'], None)

        # TODO: status shoudn't be None
        self.assertEqual(o['status'], None)
