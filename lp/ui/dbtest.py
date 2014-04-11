"""
These unit tests run against the live read-only Voyager database. They
are separate from the vanilla unit tests found in lp.ui.tests, since they
do not set up and tear down a test database and schema. Use the dbtest
management command to run them.
"""

from unittest import TestCase

from ui.db import get_item, get_availability, fetch_one


class DbTests(TestCase):

    def test_book(self):
        i = get_item('12278722')
        self.assertEqual(i['@type'], 'Book')

    def test_availability(self):
        a = get_availability('5769326')
        self.assertEqual(len(a), 1)

        o = a[0]
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
        a = get_availability(bib_id)
        for o in a:
            if 'serialNumber' in o and o['serialNumber'] == str(item_id):
                self.assertEqual(
                    o['availabilityAtOrFrom'].lower(),
                    'wrlc shared collections facility'
                )

    def test_availability_georgetown(self):
        a = get_availability('4218864')
        self.assertEqual(len(a), 1)

        o = a[0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'Georgetown')
        # TODO: this should be something else once z39.50 lookup is working
        self.assertEqual(o['sku'], None)
