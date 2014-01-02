import datetime

from django.test import TestCase

from ui import views


class IllLinkTest(TestCase):
    holdings = [
        {
            'LIBRARY_NAME': 'GW',
            'LOCATION_NAME': 'gwg ml',
            'LOCATION_DISPLAY_NAME': 'GW: GELMAN Media Lab',
            'MFHD_DATA':
            {
                'marc866list': [],
                'marc856list': [],
                'marc852': ''
            },
            'MFHD_ID': 15435748,
            'ITEMS':
            [
                {
                    'ITEM_ENUM': None,
                    'ELIGIBLE': True,
                    'ITEM_STATUS': 1,
                    'ITEM_STATUS_DATE': datetime.datetime(2013, 2, 6, 1, 1, 4),
                    'TEMPLOCATION': None,
                    'ITEM_STATUS_DESC': 'Not Charged',
                    'BIB_ID': 13237084,
                    'ITEM_ID': 9269135,
                    'LIBRARY_FULL_NAME': 'George Washington',
                    'PERMLOCATION': 'GW: GELMAN Media Lab',
                    'TRIMMED_LOCATION_DISPLAY_NAME': 'GELMAN Media Lab',
                    'DISPLAY_CALL_NO': None,
                    'CHRON': None
                }
            ],
            'ELIGIBLE': True,
            'LIBRARY_FULL_NAME': 'George Washington',
            'LinkResolverData': [],
            'TRIMMED_LOCATION_DISPLAY_NAME': ' GELMAN Media Lab',
            'ELECTRONIC_DATA': {},
            'LIBRARY_HAS': [],
            'LOCATION_ID': 1505,
            'AVAILABILITY': {},
            'DISPLAY_CALL_NO': None,
            'BIB_ID': 13237084,
        },
    ]

    def test_ill_link_removal(self):
        """issue 399 for removing ill link if item is from gw media lab"""
        show_wrlc_link = views.display_wrlc_link(self.holdings)
        self.assertFalse(show_wrlc_link)
