import pymarc

from django.conf import settings
from django.test import TestCase

from ui.templatetags.launchpad_extras import clean_isbn, clean_lccn
from ui.models import Item, Holding


class CleanIsbnTest(TestCase):

    def test_bad_isbns(self):
        """ensure some odd cases come out right."""
        bad_isbn1 = '0080212472. 0080212464'
        self.assertEqual(clean_isbn(bad_isbn1), '0080212472')
        bad_isbn2 = '0679302603; 0679302611 (papbk)'
        self.assertEqual(clean_isbn(bad_isbn2), '0679302603')


class CleanLccnTest(TestCase):

    examples = [
            ('89-456', '89000456'),
            ('2001-1114', '2001001114'),
            ('gm 71-2450', 'gm71002450'),
            ('n 79-18774', 'n79018774'),
            ('sh 85026371', 'sh85026371'),
            ('sn2006058112', 'sn2006058112'),
            ('n 2011033569', 'n2011033569'),
            ('sh2006006990', 'sh2006006990'),
            ('n78-890351', 'n78890351'),
            ('n78-89035', 'n78089035'),
            ('n 78890351', 'n78890351'),
            (' 85000002', '85000002'),
            ('85-2', '85000002'),
            ('2001-000002', '2001000002'),
            ('75-425165//r75', '75425165'),
            (' 79139101 /AC/r932', '79139101'),
            ]

    def test_normalized_lccns(self):
        """ensure example cases are handled correctly"""
        for in_lccn, out_lccn in self.examples:
            self.assertEqual(clean_lccn(in_lccn), out_lccn)


class ItemModelTestCase(TestCase):

    def setUp(self):
        self.metadata = {
            'itemid': '2645155',
            'mfhdid': '3431230',
            'bibid': '2993218',
            'callnum': 'PS3572 .O5 C3',
            'enum': '',
            'status': 'Not Charged',
            'statuscode': '1',
            'statusdate': '2013-04-14T00:11:11+00:00',
            'temploc': '',
            'permloc': 'GW: GELMAN Stacks',
            'libcode': 'GW',
            'chron': ''}
        settings.INELIGIBLE_LIBRARIES.append('LPTEST0')
        settings.FORCE_ELIGIBLE_LOCS.append('LPTEST1')
        settings.INELIGIBLE_PERM_LOCS.append('LPTEST2')
        settings.INELIGIBLE_TEMP_LOCS.append('LPTEST3')
        settings.INELIGIBLE_STATUS.append('LPTEST4')
        self.item = Item(metadata=self.metadata)

    def tearDown(self):
        settings.INELIGIBLE_LIBRARIES.pop()
        settings.FORCE_ELIGIBLE_LOCS.pop()
        settings.INELIGIBLE_PERM_LOCS.pop()
        settings.INELIGIBLE_TEMP_LOCS.pop()
        settings.INELIGIBLE_STATUS.pop()

    def testmetadata(self):
        for key in self.metadata.keys():
            self.assertEqual(self.metadata[key], getattr(self.item, key)())
        del self.item.metadata
        self.item.metadata = self.metadata
        for key in self.metadata.keys():
            self.assertEqual(self.metadata[key], getattr(self.item, key)())
        self.assertEqual('GELMAN Stacks', self.item.location())
        self.assertEqual(settings.LIB_LOOKUP.get('GW', ''),
            self.item.library())

    def testeligibility(self):
        #test ineligible libcode
        self.item._metadata['libcode'] = 'LPTEST0'
        self.assertFalse(self.item.eligible(refresh=True))
        #test override of ineligible permloc with forced eligible loc
        self.item._metadata['libcode'] = ''
        self.item._metadata['permloc'] = 'LPTEST2'
        self.item._metadata['temploc'] = 'LPTEST1'
        self.assertTrue(self.item.eligible(refresh=True))
        #test ineligible permloc
        self.item._metadata['temploc'] = ''
        self.assertFalse(self.item.eligible(refresh=True))
        #test ineligible temploc
        self.item._metadata['permloc'] = ''
        self.item._metadata['temploc'] = 'LPTEST3'
        self.assertFalse(self.item.eligible(refresh=True))
        #test ineligible status
        self.item._metadata['temploc'] = ''
        self.item._metadata['status'] = 'LPTEST4'
        self.assertFalse(self.item.eligible(refresh=True))
        #test eligible by default
        self.item._metadata['status'] = ''
        self.assertTrue(self.item.eligible(refresh=True))


class HoldingItemTestCase(TestCase):

    def setUp(self):
        self.metadata = {
            'bibid': '2262190',
            'mfhdid': '8475265',
            'libcode': 'GW',
            'locid': '817',
            'location': 'GW: Online',
            'callnum': 'GW: Electronic Journal'}
        self.hold = Holding(metadata=self.metadata)
        self.marcstring = '''00449cx  a22000974  4500001000800000004000800008005001700016008003300033852013100066856015400197\x1e8475265\x1e2262190\x1e20130121191709.0\x1e0805154u    8   1001uu   0901128\x1e8 \x1fbgwg ej\x1fhGW: Electronic Journal\x1fzOff-campus access restricted to current George Washington University members - Login required.\x1e4 \x1fuhttp://sfx.wrlc.org/gw/OpenURL?sid=sfx:e_collection&issn=0001-0782&pid=serviceType=getFullTxt\x1fzClick here to access available issues of this journal.\x1e\x1d'''
        self.marc = pymarc.record.Record(data=self.marcstring)

    def tearDown(self):
        pass

    def testmetadata(self):
        for key in self.metadata.keys():
            if key != 'location':
                self.assertEqual(self.metadata[key], getattr(self.hold,
                    key)())
        del self.hold.metadata
        self.hold.metadata = self.metadata
        for key in self.metadata.keys():
            if key != 'location':
                self.assertEqual(self.metadata[key], getattr(self.hold,
                    key)())

    def testlocation(self):
        self.assertEqual('Online', self.hold.location())

    def testmarc(self):
        self.assertEqual(self.hold.pubnote(), '')
        self.assertEqual(self.hold.links(), [])
        self.assertEqual(self.hold.textual(), [])
        #test setter
        self.hold.marc = self.marc
        self.assertEqual(self.hold.marc.as_marc(), self.marcstring)
        #test pubnote
        self.assertEqual(self.hold.pubnote(), 'Off-campus access restricted' +
            ' to current George Washington University members - Login ' +
            'required.')
        #test links
        self.assertEqual(self.hold.links(), [
            {'url': 'http://sfx.wrlc.org/gw/OpenURL?sid=sfx:e_collection&' +
                'issn=0001-0782&pid=serviceType=getFullTxt',
            'note': 'Click here to access available issues of this journal.',
            'material': None}])
        #test textual
        self.assertEqual(self.hold.textual(), [])
