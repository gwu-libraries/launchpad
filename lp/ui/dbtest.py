"""
This is a specialized command for running unit tests against the 
live, read-only Voyager database. The normal test command will attempt
to create a test database, which we cannot do in the Voyager db.
"""

from unittest import TestCase

from ui.db import get_item

class DbTests(TestCase):

    def test_book(self):
        i = get_item('12278722')
        self.assertEqual(i['@type'], 'Book')
