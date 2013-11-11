from django.test import TestCase

from ui.templatetags.launchpad_extras import clean_isbn


class CleanIsbnTest(TestCase):
    examples = [
        ('0080212472. 0080212464', '0080212472'),
        ('0679302603; 0679302611 (papbk)', '0679302603'),
        (u'9789264096110 (e-book)', '9789264096110'),
        (u'9789264096103 (imprim\\xa9\\u266d)', '9789264096103'),
        (u'9789264096103 IMPRIM \\u266d', '9789264096103'),
    ]

    def test_bad_isbns(self):
        """ensure some odd cases come out right."""
        for in_isbn, out_isbn in self.examples:
            self.assertEqual(clean_isbn(in_isbn), out_isbn)
