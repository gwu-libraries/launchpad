from django.test import TestCase

from ui.voyager import get_open_library_item_title


class OpenLibraryTitleTest(TestCase):
    def test_correct_title(self):
        "this is from issue 487 where open libray link points to correct title"
        title = "Life on the Mississippi"
        open_library_link = "http://openlibrary.org/books/OL6710196M/Life_on_the_Mississippi"
        open_library_title = get_open_library_item_title(open_library_link)
        self.assertEqual(title[0:10], open_library_title[0:10])

    def test_incorrect_title(self):
        "from issue 420"
        title = "Frank Lloyd Wright's Hanna House : the clients' report Paul R. and Jean S. Hanna"
        open_library_link = "http://openlibrary.org/books/OL24933180M/The_Baptist_position_as_to_the_Bible"
        open_library_title = get_open_library_item_title(open_library_link)
        self.assertNotEqual(title[0:10], open_library_title[0:10])
