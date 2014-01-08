import unittest

from django.conf import settings
from ui.templatetags.launchpad_extras import explore


class ExploreTests(unittest.TestCase):

    def test_summon(self):
        settings.EXPLORE_TYPE = 'summon'

        url = explore('author', 'Melville, Herman')
        self.assertEqual(url, 'http://gw.summon.serialssolutions.com/search?s.cmd=addTextFilter(SourceType%5C:%5C(%22Library+Catalog%22%5C))&s.q=author:%22Melville%2C%20Herman%22')

        url = explore('subject', 'Whaling')
        self.assertEqual(url, 'http://gw.summon.serialssolutions.com/search?s.cmd=addTextFilter(SourceType%5C:%5C(%22Library+Catalog%22%5C))&s.q=subjectterms%3A%22Whaling%22')

        url = explore('series', 'X-Men')
        self.assertEqual(url, 'http://gw.summon.serialssolutions.com/search?s.cmd=addTextFilter(SourceType%5C:%5C(%22Library+Catalog%22%5C))&s.q=%22X-Men%22')

    def test_surveyor(self):
        settings.EXPLORE_TYPE = 'surveyor'

        url = explore('author', 'Melville, Herman')
        self.assertEqual(url, 'http://surveyor.gelman.gwu.edu/?q=author:%22Melville%2C%20Herman%22')

        url = explore('subject', 'Whaling')
        self.assertEqual(url, 'http://surveyor.gelman.gwu.edu/?q=subject:%22Whaling%22')

        url = explore('series', 'X-Men')
        self.assertEqual(url, 'http://surveyor.gelman.gwu.edu/?q=series:%22X-Men%22')
