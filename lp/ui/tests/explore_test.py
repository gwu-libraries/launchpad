import unittest

from django.conf import settings
from ui.templatetags.launchpad_extras import explore_subject, explore_author, explore_series


class ExploreTests(unittest.TestCase):

    def test_author(self):
        settings.EXPLORE_TYPE = 'summon'
        url = explore_author('Melville, Herman')
        self.assertEqual(url, 'http://gw.summon.serialssolutions.com/search?s.cmd=addTextFilter%28SourceType%5C%3A%5C%28%22Library+Catalog%22%5C%29%29&s.q=author%3A%22Melville%2C+Herman%22')

        settings.EXPLORE_TYPE = 'surveyor'
        url = explore_author('Melville, Herman')
        self.assertEqual(url, 'http://surveyor.gelman.gwu.edu/?q=author%3A%22Melville%2C+Herman%22')


    def test_series(self):
        settings.EXPLORE_TYPE = 'summon'
        url = explore_series('X-Men')
        self.assertEqual(url, 'http://gw.summon.serialssolutions.com/search?s.cmd=addTextFilter%28SourceType%5C%3A%5C%28%22Library+Catalog%22%5C%29%29&s.q=%22X-Men%22')

        settings.EXPLORE_TYPE = 'surveyor'
        url = explore_series('X-Men')
        self.assertEqual(url, 'http://surveyor.gelman.gwu.edu/?q=series%3A%22X-Men%22')


    def test_subject(self):
        settings.EXPLORE_TYPE = 'summon'
        url = explore_subject('Whaling')
        self.assertEqual(url, 'http://gw.summon.serialssolutions.com/search?s.cmd=addTextFilter%28SourceType%5C%3A%5C%28%22Library+Catalog%22%5C%29%29&s.q=subjectterms%3A%22Whaling%22')

        settings.EXPLORE_TYPE = 'surveyor'
        url = explore_subject('Whaling')
        self.assertEqual(url, 'http://surveyor.gelman.gwu.edu/?q=subject%3A%22Whaling%22')

        # TODO test structured subject
