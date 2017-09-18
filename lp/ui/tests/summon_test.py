# -*- coding: utf-8 -*-

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
        search = self.summon.search("isbn:9780387312965")

        self.assertEqual(search['startIndex'], 0)
        self.assertTrue(search['itemsPerPage'], 10)

        self.assertTrue(len(search['results']) > 0)
        i = search['results'][0]
        self.assertEqual(i['@id'], '/item/11658285')
        self.assertEqual(i['@type'], 'Book')
        self.assertEqual(i['wrlc'], '11658285')
        self.assertEqual(i['name'], 'Nanotechnology for biology and medicine : at the building block level')
        self.assertEqual(i['isbn'], ["9780387312965", "9780387312828", "038731296X", "038731282X"])

        self.assertEqual(len(i['author']), 2)
        self.assertEqual(i['author'][0]['name'], 'Parpura, Vladimir, 1964')
        self.assertEqual(i['author'][0]['url'], '/search?q=Author%3A%22Parpura%2C+Vladimir%2C+1964%22')
        self.assertEqual(i['author'][1]['name'], 'Silva, Gabriel A')
        self.assertEqual(i['author'][1]['url'], '/search?q=Author%3A%22Silva%2C+Gabriel+A%22')

        self.assertEqual(len(i['about']), 4)
        self.assertEqual(i['about'][0]['name'], 'Nanomedicine')
        self.assertEqual(i['about'][0]['url'], '/search?q=SubjectTerms%3A%22Nanomedicine%22')

        self.assertEqual(i['publisher']['name'], 'Springer')
        self.assertEqual(i['publisher']['address'], 'New York')
        self.assertEqual(i['datePublished'], '2012')
        self.assertEqual(i['offers'][0]['seller'], 'George Washington University')
       

    def test_newspaper(self):
        search = self.summon.search("2269371 new york times")
        i = search['results'][0]
        # Travis count doesn't match
        #self.assertEqual(search['totalResults'], 1)
        self.assertEqual(i['@type'], 'Periodical')

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

    def test_facets(self):
        search = self.summon.search("interesting",
                fq='SourceType:("Library Catalog")',
                ff=["ContentType,or", "Author,or"])
        self.assertTrue('facets' in search)
        self.assertEqual(len(search['facets']), 2)
        self.assertEqual(search['facets'][0]['name'], 'ContentType')
        self.assertEqual(search['facets'][1]['name'], 'Author')
        counts = search['facets'][0]['counts']
        self.assertEqual(counts[0]['name'], 'Book / eBook')
        self.assertTrue(counts[0]['count'] > 0)

    def test_georgemason_summon_id(self):
        search = self.summon.search(
            'information',
            ps=50,
            fq='SourceType:("Library Catalog")',
            fvf='%s,%s,%s' % ('Institution', 'George Mason University (GM)', 'false')
        )
        for item in search['results']:
            if len(item['offers']) == 1 \
                and item['offers'][0]['seller'] == 'George Mason University':
                self.assertEqual(item['wrlc'][0], 'm')

    def test_georgetown_summon_id(self):
        search = self.summon.search(
            'information',
            ps=50,
            fq='SourceType:("Library Catalog")',
            fvf='%s,%s,%s' % ('Institution', 'Georgetown University (GT)', 'false')
        )
        for item in search['results']:
            if len(item['offers']) == 1 \
                and item['offers'][0]['seller'] == 'Georgetown University':
                self.assertEqual(item['wrlc'][0], 'b')

    def test_alternate_name(self):
        search = self.summon.search('isbn:9784062879248',
            fq='SourceType:("Library Catalog")')
        self.assertEqual(len(search['results']), 1)
        i = search['results'][0]
        self.assertEqual(i['alternateName'], u'\u6771\u4eac\u88c1\u5224')
        self.assertEqual(i['author'][0]['alternateName'],
            u'\u65e5\u66ae\u5409\u5ef6')

    def test_web_resource(self):
        search = self.summon.search(
            'politics',
            fq='ContentType:("Web Resource")'
        )
        self.assertTrue(len(search['results']) > 0)

    def test_offer_ids(self):
        search = self.summon.search('isbn:9780596007973',
            fq='SourceType:("Library Catalog")')
        self.assertEqual(len(search['results']), 1)
        i = search['results'][0]
        self.assertEqual(len(i['offers']), 2)
        self.assertEqual(i['offers'][1]['serialNumber'], 'b27682912')
