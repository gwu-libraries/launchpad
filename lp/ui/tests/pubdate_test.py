import datetime
from django.test import TestCase

from ui.views import _filter_by_pubdate


class PublicationDateTest(TestCase):

    def test_no_pubdate(self):
        q, o = _filter_by_pubdate('foo', {})
        self.assertEqual(q, 'foo')
        self.assertTrue('rf' not in o)

    def test_single_pubdate(self):
        q, o = _filter_by_pubdate('foo AND PublicationDate:1984', {})
        self.assertEqual(q, 'foo AND PublicationDate:1984')
        self.assertTrue('rf' not in o)

    def test_pubdate_range(self):
        q, o = _filter_by_pubdate('foo AND PublicationDate:[1984-1986]', {})
        self.assertEqual(q, 'foo')
        self.assertEqual(o['rf'], 'PublicationDate,1984:1986')

    def test_pubdate_no_start(self):
        q, o = _filter_by_pubdate('foo AND PublicationDate:[-1986]', {})
        self.assertEqual(q, 'foo')
        self.assertEqual(o['rf'], 'PublicationDate,1000:1986')

    def test_pubdate_no_end(self):
        year = datetime.datetime.now().year
        q, o = _filter_by_pubdate('foo AND PublicationDate:[1980-]', {})
        self.assertEqual(q, 'foo')
        self.assertEqual(o['rf'], 'PublicationDate,1980:' + str(year))
