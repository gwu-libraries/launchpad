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

    def test_search(self):
        search = self.summon.search("isbn:1573870994")
        self.assertTrue(len(search['results']) > 0)
        i = search['results'][0]
        self.assertEqual(i['@id'], '/item/2402189')
        self.assertEqual(i['@type'], 'Book')
        self.assertEqual(i['name'], 'The web of knowledge : a festschrift in honor of Eugene Garfield')

        self.assertEqual(len(i['author']), 3)
        self.assertEqual(i['author'][0]['name'], 'Garfield, Eugene')
        self.assertEqual(i['author'][1]['name'], 'Atkins, Helen Barsky')
        self.assertEqual(i['author'][2]['name'], 'Cronin, Blaise')
        self.assertEqual(i['publisher']['name'], 'Information Today')
        self.assertEqual(i['publisher']['address'], 'Medford, N.J')
        self.assertEqual(i['datePublished'], '2000')
        self.assertEqual(i['thumbnailUrl'], 'http://covers-cdn.summon.serialssolutions.com/index.aspx?isbn=9781573870993/mc.gif&client=summon&freeimage=true')

    def test_raw(self):
        results = self.summon.search("isbn:1573870994", raw=True)
        self.assertEqual(results['documents'][0]['Title'], ['The web of knowledge'])

    def test_search_for_template(self):
        search = self.summon.search("isbn:1573870994", for_template=True)
        self.assertTrue(len(search['results']) > 0)
        i = search['results'][0]
        self.assertTrue('id' in i)
        self.assertTrue('type' in i)
        self.assertTrue('@id' not in i)
        self.assertTrue('@type' not in i)
