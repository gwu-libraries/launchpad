from urlparse import urlparse, parse_qs

from django.conf import settings
from django.test import TestCase

from ui.voyager import insert_sid

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
