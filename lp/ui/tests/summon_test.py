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
        search = self.summon.search("isbn:1573870994")

        self.assertEqual(search['totalResults'], 1)
        self.assertEqual(search['startIndex'], 0)
        self.assertTrue(search['itemsPerPage'], 10)

        self.assertTrue(len(search['results']) > 0)
        i = search['results'][0]
        self.assertEqual(i['@id'], '/item/m2402189')
        self.assertEqual(i['@type'], 'Book')
        self.assertEqual(i['wrlc'], 'm2402189')
        self.assertEqual(i['name'], 'The web of knowledge : a festschrift in honor of Eugene Garfield')
        self.assertEqual(i['isbn'], ["9781573870993", "1573870994"])

        self.assertEqual(len(i['author']), 3)
        self.assertEqual(i['author'][0]['name'], 'Garfield, Eugene')
        self.assertEqual(i['author'][0]['url'], '/search?q=Author%3A%22Garfield%2C+Eugene%22')
        self.assertEqual(i['author'][1]['name'], 'Cronin, Blaise')
        self.assertEqual(i['author'][1]['url'], '/search?q=Author%3A%22Cronin%2C+Blaise%22')
        self.assertEqual(i['author'][2]['name'], 'Atkins, Helen Barsky')
        self.assertEqual(i['author'][2]['url'], '/search?q=Author%3A%22Atkins%2C+Helen+Barsky%22')

        self.assertEqual(len(i['about']), 3)
        self.assertEqual(i['about'][0]['name'], 'Science -- Abstracting and indexing')
        self.assertEqual(i['about'][0]['url'], '/search?q=SubjectTerms%3A%22Science+--+Abstracting+and+indexing%22')
        self.assertEqual(i['about'][1]['name'], 'Indexing')
        self.assertEqual(i['about'][1]['url'], '/search?q=SubjectTerms%3A%22Indexing%22')
        self.assertEqual(i['about'][2]['name'], 'Garfield, Eugene')
        self.assertEqual(i['about'][2]['url'], '/search?q=SubjectTerms%3A%22Garfield%2C+Eugene%22')

        self.assertEqual(i['publisher']['name'], 'Information Today')
        self.assertEqual(i['publisher']['address'], 'Medford, N.J')
        self.assertEqual(i['datePublished'], '2000')
        self.assertEqual(i['thumbnailUrl'], 'http://covers-cdn.summon.serialssolutions.com/index.aspx?isbn=9781573870993/mc.gif&client=summon&freeimage=true')
        self.assertEqual(i['bookEdition'], '1. print')
        self.assertEqual(len(i['offers']), 2)
        self.assertEqual(i['offers'][0]['seller'], 'George Mason University')
        self.assertEqual(i['offers'][1]['seller'], 'Howard University')

    def test_newspaper(self):
        search = self.summon.search("2269371 new york times")
        i = search['results'][0]
        self.assertEqual(search['totalResults'], 1)
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
        for result in search['results']:
            self.assertEqual(result['@type'], 'WebPage')

    def test_offer_ids(self):
        search = self.summon.search('isbn:9780596007973',
            fq='SourceType:("Library Catalog")')
        self.assertEqual(len(search['results']), 1)
        i = search['results'][0]
        self.assertEqual(len(i['offers']), 2)
        self.assertEqual(i['offers'][0]['serialNumber'], 'm1240674')
        self.assertEqual(i['offers'][1]['serialNumber'], 'b27682912')
