import pymarc

from django.conf import settings
from django.test import TestCase

from ui.templatetags.launchpad_extras import clean_isbn, clean_lccn
from ui.models import Item, Holding, Bib


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


class BibModelTestCase(TestCase):

    def setUp(self):
        self.metadata = {
            'bibid': '2262190',
            'title': 'Communications of the ACM.',
            'author': '',
            'addedentries': ['Association for Computing Machinery'],
            'edition': '',
            'publisher': 'Association for Computing Machinery',
            'pubplace': 'New York',
            'pubyear': '1959-',
            'langcode': 'eng',
            'libcode': 'GW',
            'formatcode': 'as',
            'isbn': '',
            'isbns': [],
            'issn': '0001-0782',
            'issns': ['0001-0782'],
            'oclc': '(OCoLC)ocm01514517'}

        self.marc1 = '''01683cas a2200433 a 4500001000800000005001700008006001900025007001500044008004100059010003100100035002300131040018500154016002000339019001200359022001400371030001100385032001700396050001600413060001800429082001800447049000900465210001600474222003000490245003100520246006200551246003300613260006200646300002500708310001200733362003200745530004100777650002800818710004100846770007400887776008500961780009601046850009501142994001201237\x1e2262190\x1e20130121191705.0\x1em        d        \x1ecr cn ---aaaaa\x1e750806c19599999nyumr p       0   a0eng d\x1e  \x1fa   61065941 \x1fzsc 76000456 \x1e  \x1fa(OCoLC)ocm01514517\x1e  \x1faMUL\x1fcMUL\x1fdNSD\x1fdDLC\x1fdNSD\x1fdOCL\x1fdDLC\x1fdNST\x1fdDLC\x1fdRCS\x1fdNST\x1fdDLC\x1fdAIP\x1fdDLC\x1fdAIP\x1fdNSD\x1fdAIP\x1fdNST\x1fdNSD\x1fdNST\x1fdNSD\x1fdNST\x1fdDLC\x1fdGUA\x1fdIUL\x1fdMYG\x1fdOCL\x1fdSYS\x1fdLYU\x1fdOCLCQ\x1fdWAU\x1fdNSD\x1fdCDS\x1fdLVB\x1fdCUS\x1fdDGW\x1e7 \x1faC32640000\x1f2DNLM\x1e  \x1fa2446101\x1e0 \x1fa0001-0782\x1e  \x1faCACMA2\x1e  \x1fa126160\x1fbUSPS\x1e00\x1faQA76\x1fb.A772\x1e0 \x1faZ 699.A1 C734\x1e0 \x1fa001.64/05\x1f219\x1e  \x1faDGWW\x1e0 \x1faCommun. ACM\x1e 0\x1faCommunications of the ACM\x1e00\x1faCommunications of the ACM.\x1e3 \x1faCommunications of the Association for Computing Machinery\x1e30\x1faCommunications of the A.C.M.\x1e  \x1fa[New York] :\x1fbAssociation for Computing Machinery,\x1fc1959-\x1e  \x1fav. :\x1fbill. ;\x1fc28 cm.\x1e  \x1faMonthly\x1e0 \x1faVol. 2, no. 11 (Nov. 1959)-\x1e  \x1faAlso available in an online version.\x1e 0\x1faComputers\x1fvPeriodicals.\x1e2 \x1faAssociation for Computing Machinery.\x1e0 \x1ftACMemberNet\x1fgJuly 1990-\x1fx1059-1192\x1fw(DLC)   96643236\x1fw(OCoLC)23369844\x1e1 \x1ftCommunications of the ACM (Online)\x1fx1557-7317\x1fw(DLC)sn 99034011\x1fw(OCoLC)38436103\x1e00\x1ftCommunications of the Association for Computing Machinery\x1fw(DLC)sf 84001031\x1fw(OCoLC)2103367\x1e  \x1faAzTeS\x1faCCC\x1faCaBVa\x1faCaOTM\x1faDLC\x1faFU\x1faGU\x1faICL\x1faINS\x1faInU\x1faMH-SD\x1faMMeT\x1faMWelC\x1faMoKU\x1faNSyU\x1faPPiD\x1e  \x1faC0\x1fbDGW\x1e\x1d'''

        self.marc2 = '''02314cam a2200517K  4500001000800000005001700008008004100025035002300066035001200089040002500101035002000126090001300146049000900159100006700168245006100235260004700296300001800343500030000361530014000661500007700801650004100878650004500919651005200964880006001016880004201076880006701118880003001185994001201215948003301227948003201260948003201292948003201324948003301356948003201389948003301421948003201454948003201486948003201518948003201550948003201582948003301614948003301647998003301680996003601713998004701749\x1e7590110\x1e20121003163637.0\x1e870707m19329999ua            000 0 ara d\x1e  \x1fa(OCoLC)ocm16137999\x1e  \x1fa7590110\x1e  \x1faWAU\x1fcWAU\x1fdOCLCG\x1fdDGW\x1e  \x1fa(OCoLC)16137999\x1e  \x1faD20\x1fb.I2\x1e  \x1faDGWW\x1e1 \x1f6880-01\x1faIbn Kathi\xcc\x84r, Isma\xcc\x84\xca\xbbi\xcc\x84l ibn \xca\xbbUmar,\x1fdca. 1301-1373.\x1e13\x1f6880-02\x1faal-Bida\xcc\x84yah wa-al-niha\xcc\x84yah fi\xcc\x84 al-ta\xcc\x84ri\xcc\x84kh.\x1e  \x1fa[Cairo]\x1fbMat\xcc\xa3ba\xca\xbbat al-Sa\xca\xbba\xcc\x84dah,\x1fc1932-\x1e  \x1fa14 v.\x1fc29 cm.\x1e  \x1faThis book is from the rare book collection originally held in the George Camp Keiser Library of the Middle East Institute (MEI), Washington DC. This collection, acquired in 2008 by the Gelman Library of The George Washington University, now forms part of the Special Collections Research Center.\x1e  \x1faAlso available online via GWU Cultural Imaginings Digitization Project (funded by the Institute for Museum and Library Services (IMLS))\x1e  \x1faNote in blue ink on t.p. of each v. except v. 8: Baghdad purchase  1954.\x1e 0\x1faIslam\x1fxHistory\x1fvEarly works to 1800.\x1e 0\x1faCaliphate\x1fxHistory\x1fvEarly works to 1800.\x1e 0\x1faDamascus (Syria)\x1fxHistory\x1fvEarly works to 1800.\x1e1 \x1f6100-01/r\x1fa\xd8\xa7\xd8\xa8\xd9\x86 \xd9\x83\xd8\xab\xd9\x8a\xd8\xb1\xd8\x8c \xd8\xa5\xd8\xb3\xd9\x85\xd8\xa7\xd8\xb9\xd9\x8a\xd9\x84 \xd8\xa8\xd9\x86 \xd8\xb9\xd9\x85\xd8\xb1.\x1e10\x1f6240-00/r\x1fa\xd8\xa8\xd8\xaf\xd8\xa7\xd9\x8a\xd8\xa9 \xd9\x88\xd8\xa7\xd9\x84\xd9\x86\xd9\x87\xd8\xa7\xd9\x8a\xd8\xa9\x1e12\x1f6245-02/r\x1fa\xd8\xa7\xd9\x84\xd8\xa8\xd8\xaf\xd8\xa7\xd9\x8a\xd8\xa9 \xd9\x88\xd8\xa7\xd9\x84\xd9\x86\xd9\x87\xd8\xa7\xd9\x8a\xd8\xa9 \xd9\x81\xd9\x8a \xd8\xa7\xd9\x84\xd8\xaa\xd8\xa7\xd8\xb1\xd9\x8a\xd8\xae.\x1e  \x1f6250-00/r\x1fa\xd8\xa7\xd9\x84\xd8\xb7\xd8\xa8\xd8\xb9\xd8\xa9 1.\x1e  \x1faC0\x1fbDGW\x1e  \x1faKirtas\x1fp32882019306656\x1ftv.13\x1e  \x1faKirtas\x1fp32882019307472\x1ftv.5\x1e  \x1faKirtas\x1fp32882019307456\x1ftv.3\x1e  \x1faKirtas\x1fp32882019307480\x1ftv.6\x1e  \x1faKirtas\x1fp32882019307498\x1ftv.10\x1e  \x1faKirtas\x1fp32882019307464\x1ftv.4\x1e  \x1faKirtas\x1fp32882019307621\x1ftv.12\x1e  \x1faKirtas\x1fp32882019307654\x1ftv.8\x1e  \x1faKirtas\x1fp32882019307662\x1ftv.7\x1e  \x1faKirtas\x1fp32882019306680\x1ftv.1\x1e  \x1faKirtas\x1fp32882019307639\x1ftv.9\x1e  \x1faKirtas\x1fp32882019070658\x1ftv.2\x1e  \x1faKirtas\x1fp32882019306649\x1ftv.14\x1e  \x1faKirtas\x1fp32882019307670\x1ftv.11\x1e  \x1fcKirtas ; gwjshieh 2010-03-17\x1e  \x1faAdd copy, elec ver ; 2012-06-20\x1e  \x1fcdSpace AWK url added ; gwjshieh 2012-06-20\x1e\x1d'''

        self.bib = Bib(metadata=self.metadata)

    def tearDown(self):
        pass

    def testmetadata(self):
        self.bib.metadata = self.metadata
        for key in self.metadata.keys():
            self.assertEqual(self.metadata[key], getattr(self.bib, key)())

    def testtrunctitle(self):
        titlewords = []
        for i in range(50):
            titlewords.append('word%02i' % i)
        testtitle = ' '.join(titlewords)
        self.bib.metadata['title'] = testtitle
        expected = ' '.join(titlewords[:36]) + '...'
        self.assertEqual(expected, self.bib.trunctitle())

    def testlanguage(self):
        self.assertEqual('English', self.bib.language())

    def testmicrodatatype(self):
        self.assertEqual(self.bib.microdatatype(),
            'http://schema.org/CreativeWork')
        self.bib.metadata['formatcode'] = 'am'
        self.assertEqual(self.bib.microdatatype(), 'http://schema.org/Book')
        self.bib.metadata['formatcode'] = 'as'
        self.bib.metadata['isbn'] = '1234567890'
        self.assertEqual(self.bib.microdatatype(), 'http://schema.org/Book')

    def testmarc(self):
        del self.bib.metadata
        self.bib.marc = pymarc.record.Record(data=self.marc1)
        for key in self.metadata.keys():
            if key not in ['langcode', 'bibid', 'libcode', 'formatcode']:
                self.assertEqual(self.metadata[key], getattr(self.bib, key)())
        self.assertEqual(self.bib.subjects(), ['Computers Periodicals.'])
        self.assertEqual(self.bib.uniformtitle(), None)

    def testholdings(self):
        pass

    def testitems(self):
        pass

    def testaltmeta(self):
        self.bib = Bib(marc=pymarc.record.Record(data=self.marc2))
        self.assertEqual(self.bib.altauthor(), '\xd8\xa7\xd8\xa8\xd9\x86 ' +
            '\xd9\x83\xd8\xab\xd9\x8a\xd8\xb1\xd8\x8c \xd8\xa5\xd8\xb3\xd9' +
            '\x85\xd8\xa7\xd8\xb9\xd9\x8a\xd9\x84 \xd8\xa8\xd9\x86 \xd8\xb9' +
            '\xd9\x85\xd8\xb1.')
        self.assertEqual(self.bib.alttitle(), '\xd8\xa7\xd9\x84\xd8\xa8\xd8' +
            '\xaf\xd8\xa7\xd9\x8a\xd8\xa9 \xd9\x88\xd8\xa7\xd9\x84\xd9\x86' +
            '\xd9\x87\xd8\xa7\xd9\x8a\xd8\xa9 \xd9\x81\xd9\x8a \xd8\xa7\xd9' +
            '\x84\xd8\xaa\xd8\xa7\xd8\xb1\xd9\x8a\xd8\xae.')

