from urlparse import urlparse, parse_qs

from django.test import TestCase
from django.conf import settings

from ui.templatetags.launchpad_extras import clean_isbn, clean_lccn
from ui.voyager import insert_sid


class CleanIsbnTest(TestCase):

    def test_bad_isbns(self):
        """ensure some odd cases come out right."""
        bad_isbn1 = '0080212472. 0080212464'
        self.assertEqual(clean_isbn(bad_isbn1), '0080212472')
        bad_isbn2 = '0679302603; 0679302611 (papbk)'
        self.assertEqual(clean_isbn(bad_isbn2), '0679302603')


class CleanLccnTest(TestCase):

    examples = [
            ('89-456', '89000456'),
            ('2001-1114', '2001001114'),
            ('gm 71-2450', 'gm71002450'),
            ('n 79-18774', 'n79018774'),
            ('sh 85026371', 'sh85026371'),
            ('sn2006058112', 'sn2006058112'),
            ('n 2011033569', 'n2011033569'),
            ('sh2006006990', 'sh2006006990'),
            ('n78-890351', 'n78890351'),
            ('n78-89035', 'n78089035'),
            ('n 78890351', 'n78890351'),
            (' 85000002', '85000002'),
            ('85-2', '85000002'),
            ('2001-000002', '2001000002'),
            ('75-425165//r75', '75425165'),
            (' 79139101 /AC/r932', '79139101'),
            ]

    def test_normalized_lccns(self):
        """ensure example cases are handled correctly"""
        for in_lccn, out_lccn in self.examples:
            self.assertEqual(clean_lccn(in_lccn), out_lccn)


class IlliadSidTest(TestCase):

    def test_sid(self):
        qs = 'genre=article&issn=01644297&title=Arizona+State+Law+Journal&volume=1974&issue=&date=19740101&atitle=Closing+the+gap%3a+protection+for+mobile+home+owners.&spage=101&pages=101-127&sid=EBSCO:Index+to+Legal+Periodicals+Retrospective%3a+1908-1981'
        url = insert_sid(qs)
        u = urlparse(url)
        q = parse_qs(u.query)

        self.assertEqual(q['genre'][0], 'article')
        self.assertEqual(q['issn'][0], '01644297')
        self.assertEqual(q['title'][0], 'Arizona State Law Journal')
        self.assertEqual(q['volume'][0], '1974')
        self.assertEqual(q['date'][0], '19740101')
        self.assertEqual(q['atitle'][0], 'Closing the gap: protection for mobile home owners.')
        self.assertEqual(q['spage'][0], '101')
        self.assertEqual(q['pages'][0], '101-127')
        self.assertEqual(q['sid'][0], 'EBSCO:Index to Legal Periodicals Re:GWLP')

    def test_rfr_id(self):
        qs = 'genre=article&issn=01644297&title=Arizona+State+Law+Journal&volume=1974&issue=&date=19740101&atitle=Closing+the+gap%3a+protection+for+mobile+home+owners.&spage=101&pages=101-127&rfr_id=EBSCO:Index+to+Legal+Periodicals+Retrospective%3a+1908-1981'
        url = insert_sid(qs)
        u = urlparse(url)
        q = parse_qs(u.query)

        self.assertEqual(q['genre'][0], 'article')
        self.assertEqual(q['issn'][0], '01644297')
        self.assertEqual(q['title'][0], 'Arizona State Law Journal')
        self.assertEqual(q['volume'][0], '1974')
        self.assertEqual(q['date'][0], '19740101')
        self.assertEqual(q['atitle'][0], 'Closing the gap: protection for mobile home owners.')
        self.assertEqual(q['spage'][0], '101')
        self.assertEqual(q['pages'][0], '101-127')
        self.assertEqual(q['rfr_id'][0], 'EBSCO:Index to Legal Periodicals Re:GWLP')

    def test_no_sid_or_rfr_id(self):
        q = 'genre=article&issn=01644297&title=Arizona+State+Law+Journal&volume=1974&issue=&date=19740101&atitle=Closing+the+gap%3a+protection+for+mobile+home+owners.&spage=101&pages=101-127'
        url = insert_sid(q)
        self.assertEqual(url, settings.ILLIAD_URL + q)

    def test_unescaped_ampersand(self):
        qs = 'genre=article&issn=01644297&title=Arizona+State+Law+Journal&volume=1974&issue=&date=19740101&atitle=Closing+the+gap%3a+protection+for+mobile+&+home+owners.&spage=101&pages=101-127&sid=EBSCO:Index+to+Legal+&+Periodicals+Retrospective%3a+1908-1981'
        url = insert_sid(qs)
        u = urlparse(url)
        q = parse_qs(u.query)

        self.assertEqual(q['genre'][0], 'article')
        self.assertEqual(q['issn'][0], '01644297')
        self.assertEqual(q['title'][0], 'Arizona State Law Journal')
        self.assertEqual(q['volume'][0], '1974')
        self.assertEqual(q['date'][0], '19740101')
        self.assertEqual(q['atitle'][0], 'Closing the gap: protection for mobile & home owners.')
        self.assertEqual(q['spage'][0], '101')
        self.assertEqual(q['pages'][0], '101-127')
        self.assertEqual(q['sid'][0], 'EBSCO:Index to Legal & Periodicals :GWLP')
