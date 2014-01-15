import datetime

from django.test import TestCase

from ui import views, sort


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
    
    holdings_list =\
    [
        {
            'LIBRARY_NAME': 'AU',
            'LOCATION_NAME': 'auin wckb',
            'LOCATION_DISPLAY_NAME': 'AU: Electronic text',
            'MFHD_DATA':
            {
                'marc866list': [],
                'marc856list': [],
                'marc852': 'Remote access restricted to American University\
                authorized users. Check access URL for available holdings\
                dates single date entries for journals/periodicals are\
                typically available from listed date to the present.'
            },
            'MFHD_ID': 15497324,
            'ITEMS':
            [
                {
                    'ITEM_ENUM': None,
                    'ELIGIBLE': False,
                    'ITEM_STATUS': 1,
                    'ITEM_STATUS_DATE': datetime.datetime(2013, 10, 1, 1, 2, 1),
                    'TEMPLOCATION': None,
                    'ITEM_STATUS_DESC': 'Not Charged',
                    'BIB_D': 13298545,
                    'ITEM_ID': 9326165,
                    'LIBRARY_FULL_NAME': 'American',
                    'PERMLOCATION': 'AU: Electronic text',
                    'TRIMMED_LOCATION_DISPLAY_NAME': 'Electronic text',
                    'DISPLAY_CALL_NO': 'AU Electronic text',
                    'CHRON': None
                }
            ],
            'ELIGIBLE': False,
            'LIBRARY_FULL_NAME': 'American',
            'LinkResolverData': [],
            'TRIMMED_LOCATION_DISPLAY_NAME': ' Electronic text',
            'ELECTRONIC_DATA':
            {
                'LINK856Z': None,
                'MFHD_ID': 15497324,
                'LINK852Z': 'Remote access restricted to American University\
                authorized users. Check access URL for available holdings\
                dates single date entries for journals/periodicals are\
                typically available from listed date to the present.',
                'LINK856U': None,
                'LINK8563': None,
                'LINK852A': None,
                'bound_item': False,
                'LINK866': None,
                'LINK852H': 'AU Electronic text'
            },
            'LIBRARY_HAS': [],
            'LOCATION_ID': 1488,
            'AVAILABILITY':
            {
                'ITEM_ENUM': None,
                'ITEM_STATUS': 1,
                'ITEM_STATUS_DATE': datetime.datetime(2013, 10, 18, 1, 2, 1),
                'TEMPLOCATION': None,
                'ITEM_STATUS_DESC': 'Not Charged',
                'BIB_ID': 13298545,
                'ITEM_ID': 9326165,
                'PERMLOCATION': 'AU: Electronic text',
                'DISPLAY_CALL_NO': 'AU Electronic text',
                'CHRON': None
            },
            'DISPLAY_CALL_NO': 'AU Electronic text',
            'BIB_ID': 13298545
        },
        {
            'LIBRARY_NAME': 'AU',
            'LOCATION_NAME': 'auin alex',
            'LOCATION_DISPLAY_NAME': 'AU: Internet Resources',
            'MFHD_DATA':
            {
                'marc866list': [],
                'marc856list':
                [
                    {
                        '3': '',
                        'z': 'Click here to stream video.',
                        'u': 'http://proxyau.wrlc.org/login?url=\
                      http://www.aspresolver.com/aspresolver.asp?AHIV;1756429'
                    }
                ],
                'marc852': 'Remote access restricted to AU authorized users.'
            },
            'MFHD_ID': 14733567,
            'ITEMS':
            [
                {
                    'ITEM_ENUM': None,
                    'ELIGIBLE': False,
                    'ITEM_STATUS': 1,
                    'ITEM_STATUS_DATE': datetime.datetime(2013, 2, 2, 1, 5, 5),
                    'TEMPLOCATION': None,
                    'ITEM_STATUS_DESC': 'Not Charged',
                    'BIB_ID': 12600000,
                    'ITEM_ID': 8806630,
                    'LIBRARY_FULL_NAME': 'American',
                    'PERMLOCATION': 'AU: Internet Resources',
                    'TRIMMED_LOCATION_DISPLAY_NAME': 'Internet Resources',
                    'DISPLAY_CALL_NO': 'AU Streaming video',
                    'CHRON': None
                }
            ],
            'ELIGIBLE': False,
            'LIBRARY_FULL_NAME': 'American',
            'LinkResolverData': [],
            'TRIMMED_LOCATION_DISPLAY_NAME': ' Internet Resources',
            'ELECTRONIC_DATA':
            {
                'LINK856Z': 'Click here to stream video.',
                'MFHD_ID': 14733567,
                'LINK852Z': 'Remote access restricted\
                to American University authorized users.',
                'LINK856U': 'http://proxyau.wrlc.org/login?url=\
                http://www.aspresolver.com/aspresolver.asp?AHIV;1756429',
                'LINK8563': None,
                'LINK852A': None,
                'bound_item': False,
                'LINK866': None,
                'LINK852H': 'AU Streaming video'
            },
            'LIBRARY_HAS': [],
            'LOCATION_ID': 1462,
            'AVAILABILITY':
            {
                'ITEM_ENUM': None,
                'ITEM_STATUS': 1,
                'ITEM_STATUS_DATE': datetime.datetime(2013, 2, 26, 11, 50, 59),
                'TEMPLOCATION': None,
                'ITEM_STATUS_DESC': 'Not Charged',
                'BIB_ID': 12600000,
                'ITEM_ID': 8806630,
                'PERMLOCATION': 'AU: Internet Resources',
                'DISPLAY_CALL_NO': 'AU Streaming video',
                'CHRON': None
            },
            'DISPLAY_CALL_NO': 'AU Streaming video',
            'BIB_ID': 12600000
        }
    ]

    def test_ill_link_removal(self):
        """issue 399 for removing ill link if item is from gw media lab"""
        show_ill_link = views.display_ill_link(self.holdings)
        self.assertFalse(show_ill_link)
        holds = sort.strip_bad_holdings(self.holdings_list)
        show_ill_link = views.display_ill_link(holds)
        self.assertEqual(len(holds), 1)
        self.assertFalse(show_ill_link)
