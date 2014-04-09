"""
These unit tests run against the live read-only Voyager database. They 
are separate from the vanilla unit tests found in lp.ui.tests, since they 
do not set up and tear down a test database and schema. Use the dbtest 
management command to run them.
"""

from unittest import TestCase

from ui.db import get_item, get_availability

class DbTests(TestCase):

    def test_book(self):
        i = get_item('12278722')
        self.assertEqual(i['@type'], 'Book')

    def test_availability(self):
        a = get_availability('5769326')
        print a
        self.assertEqual(len(a), 1)

        o = a[0]
        self.assertEqual(o['@type'], 'Offer')
        self.assertEqual(o['seller'], 'George Washington')
        self.assertEqual(o['availabilityAtOrFrom'], 'Gelman stacks')
        self.assertEqual(o['sku'], 'PR6019.O9 F5 1999')
        self.assertEqual(o['status'], 'http://purl.org/goodrelations/v1#LeaseOut')
        self.assertEqual(o['serialNumber'], '999')
