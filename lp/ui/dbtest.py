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
