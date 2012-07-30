from django.test import TestCase

from ui.templatetags.launchpad_extras import clean_isbn


class CleanIsbnTest(TestCase):

    def test_bad_isbns(self):
        """ensure some odd cases come out right."""
        bad_isbn1 = '0080212472. 0080212464'
        self.assertEqual(clean_isbn(bad_isbn1), '0080212472')
        bad_isbn2 = '0679302603; 0679302611 (papbk)'
        self.assertEqual(clean_isbn(bad_isbn2), '0679302603')
