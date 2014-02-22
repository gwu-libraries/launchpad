import os
import summoner
import unittest

from ui.summon import Summon
from django.conf import settings


class SummonTests(unittest.TestCase):

    def setUp(self):
        if os.environ.get("TRAVIS", False):
            id = os.environ.get("SUMMON_ID")
            key = os.environ.get("SUMMON_SECRET_KEY")
        else:
            id = settings.SUMMON_ID
            key = settings.SUMMON_SECRET_KEY

        self.summon = Summon(id, key)
        self.summoner = summoner.Summon(id, key)

    def test_status(self):
        self.assertEqual(self.summon.status(), 'available')

    def test_search(self):
        results = self.summon.search("isbn:1573870994")
        self.assertTrue(len(results) > 0)
        i = results[0]
        self.assertEqual(i['name'], 'The web of knowledge : a festschrift in honor of Eugene Garfield')

