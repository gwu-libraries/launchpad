import datetime

from django.test import TestCase

from ui import voyager as v


class MissingItemTest(TestCase):
    items = [
        {
            'ITEM_ENUM': None,
            'ITEM_STATUS': 1,
            'ITEM_STATUS_DATE': datetime.datetime(1998, 4, 24, 0, 16, 17),
            'TEMPLOCATION': None,
            'ITEM_STATUS_DESC': 'Not Charged',
            'BIB_ID': 681520,
            'ITEM_ID': 667707,
            'PERMLOCATION': 'CU: Mullen Library Stacks',
            'DISPLAY_CALL_NO': 'BTZ 708 .S25',
            'CHRON': None
        },
        {
            'ITEM_ENUM': None,
            'ITEM_STATUS': 12,
            'ITEM_STATUS_DATE': datetime.datetime(1995, 6, 8, 0, 0),
            'TEMPLOCATION': None,
            'ITEM_STATUS_DESC': 'Missing',
            'BIB_ID': 681520,
            'ITEM_ID': 667707,
            'PERMLOCATION':
            'CU: Mullen Library Stacks',
            'DISPLAY_CALL_NO': 'BTZ 708 .S25',
            'CHRON': None
        }
    ]

    def test_missing_item(self):
        i = 0
        for item in self.items:
            v.remove_duplicate_items(i, self.items)
            if i == 1:
                "the second item should not have a REMOVE field"
                self.assertNotIn('REMOVE', item)
            if i == 0:
                "the first item should have a REMOVE field set to True"
                self.assertTrue(item['REMOVE'])
            i = i + 1
        for item in self.items[:]:
            if item.get('REMOVE'):
                self.items.remove(item)
        self.assertEqual(len(self.items), 1)
