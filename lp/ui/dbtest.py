"""
These unit tests run against the live read-only Voyager database. They 
are separate from the vanilla unit tests found in lp.ui.tests, since they 
do not set up and tear down a test database and schema. Use the dbtest 
management command to run them.
"""

from unittest import TestCase

from ui.db import get_item

class DbTests(TestCase):

    def test_book(self):
        i = get_item('12278722')
        self.assertEqual(i['@type'], 'Book')

    def test_availability(self):
        a = get_availability('4467824')
        self.assertEqual(len(a), 1)

        o = a[0]
        self.assertEqual(o, 'Offer')
        self.assertEqual(o['seller'], 'Georgetown University')
        self.assertEqual(o['availabilityAtOrFrom'], 'Lauinger stacks')
        self.assertEqual(o['sku'], 'PR6019.O9 F45 1939')
        self.assertEqual(o['status'], 'http://purl.org/goodrelations/v1#LeaseOut')
        self.assertEqual(o['serialNumber'], '8988479')
