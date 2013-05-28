from copy import deepcopy
from itertools import chain
import json
import pycountry
import pymarc

from django.conf import settings
from ui import utils
from ui.datasources.linkresolvers import linkresolvers


class Bib(object):

    META_TEMPLATE_BIB = {
        'bibid': '',
        'title': '',
        'author': '',
        'addedentries': [],
        'edition': '',
        'publisher': '',
        'pubplace': '',
        'pubyear': '',
        'langcode': '',
        'libcode': '',
        'formatcode': '',
        'isbn': '',
        'isbns': [],
        'issn': '',
        'issns': [],
        'oclc': ''
    }

    def __init__(self, metadata={}, marc=None, holdings=[]):
        assert isinstance(marc, pymarc.record.Record) or marc is None, \
            'marc must be a pymarc Record object'
        assert isinstance(holdings, list), \
            'holdings must be a list of Holding objects'
        assert all(isinstance(h, Holding) for h in holdings), \
            'holdings must be a list of Holding objects'
        assert isinstance(metadata, dict), 'metadata must be a dictionary'

        super(Bib, self).__init__()
        self._marc = marc
        self._holdings = holdings
        self._metadata = deepcopy(self.__class__.META_TEMPLATE_BIB)
        self.metadata = metadata
        self._altmeta = self.altmeta()

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, new_meta):
        assert isinstance(new_meta, dict), 'new_meta must be a dictionary'
        #all values should be strings except for lists set in the template
        if __debug__:
            for key in new_meta:
                if isinstance(self.__class__.META_TEMPLATE_BIB.get(key, None),
                    list):
                    if not isinstance(new_meta[key], list):
                        raise AssertionError('%s must be a list' % key)
                elif not isinstance(new_meta[key], str) and \
                    not isinstance(new_meta[key], unicode) and \
                    not isinstance(new_meta[key], int) and \
                    new_meta[key] is not None:
                    raise AssertionError('%s must be a string, not %s.' % (key,
                        type(new_meta[key])))
        # wipe out existing values first
        del self.metadata
        for key in new_meta:
            if new_meta[key] is not None:
                if isinstance(new_meta[key], int):
                    self._metadata[key] = str(new_meta[key])
                else:
                    self._metadata[key] = new_meta[key]

    @metadata.deleter
    def metadata(self):
        # wipe out values but leave keys
        self._metadata = deepcopy(self.__class__.META_TEMPLATE_BIB)

    @property
    def marc(self):
        return self._marc

    @marc.setter
    def marc(self, new_marc):
        assert isinstance(new_marc, pymarc.record.Record), \
            'marc must be a pymarc Record object'
        self._marc = new_marc

    @marc.deleter
    def marc(self):
        self._marc = None

    @property
    def holdings(self):
        return self._holdings

    @holdings.setter
    def holdings(self, new_holds):
        assert isinstance(new_holds, list), 'holdings must be a list'
        assert all(isinstance(h, Holding) for h in new_holds), \
            'each holding must be a Holding object'
        self._holdings = new_holds

    @holdings.deleter
    def holdings(self):
        self._holdings = []

    def items(self):
        return list(chain.from_iterable(h.items for h in self.holdings))

    def altmeta(self):
        alts = {}
        if self.marc:
            fields = self.marc.get_fields('880')
            for field in fields:
                if field['6'] is None:
                    continue
                reltag = field['6'][:3]
                if reltag == '245':
                    alts['title'] = ' '.join(field.get_subfields('a', 'b'))
                elif reltag == '260':
                    alts['publisher'] = field['b']
                    alts['pubdate'] = field['c']
                elif reltag in ('100', '110', '111'):
                    alts['author'] = field['a']
                elif reltag in ('700', '710', '711', '720', '730', '740',
                    '752', '753', '754', '790', '791', '792', '793', '796',
                    '797', '798', '799'):
                    if not alts.get('addedentries', []):
                        alts['addedentries'] = []
                    alts['addedentries'].append(field['a'])
        return alts

    def bibid(self):
        return self.metadata['bibid']

    def title(self):
        if self.marc and self.marc['245']:
            a = self.marc['245']['a']
            b = self.marc['245']['b']
            if a:
                if b:
                    return '%s %s' % (a.strip(), b.strip())
                return a.strip()
        else:
            return self.metadata['title']

    def trunctitle(self):
        brief = self.title()[:252]
        while brief[-1] != ' ':
            brief = brief[:-1]
        return '%s...' % brief[:-1]

    def alttitle(self):
        return self._altmeta.get('title', '')

    def edition(self):
        if self.marc and self.marc['250']:
            a = self.marc['250']['a']
            b = self.marc['250']['b']
            if a:
                if b:
                    return '% %' % (a.strip(), b.strip())
                return a
        return self.metadata.get('edition', '')

    def author(self):
        if self.marc and self.marc.author():
            return self.marc.author()
        else:
            return self.metadata['author']

    def altauthor(self):
        return self._altmeta.get('author', '')

    def addedentries(self):
        if self.marc:
            return [ae['a'].strip(' .') for ae in self.marc.addedentries()]
        else:
            return self.metadata['addedentries']

    def altaddedentries(self):
        return self._altmeta.get('addedentries', '')

    def isbn(self):
        if self.marc and self.marc.isbn():
            return self.marc.isbn()
        else:
            return self.metadata['isbn']

    def isbns(self):
        if self.marc:
            fields = self.marc.get_fields('020')
            return [f['a'] for f in fields if f['a']]
        elif self.isbn():
            return [self.isbn()]
        return []

    def issn(self):
        if self.marc and self.marc['022']:
            return self.marc['022']['a']
        else:
            return self.metadata['issn']

    def issns(self):
        if self.marc:
            fields = self.marc.get_fields('022')
            return [f['a'] for f in fields if f['a']]
        elif self.issn():
            return [self.issn()]
        return []

    def oclc(self):
        if self.marc:
            fields = self.marc.get_fields('035')
            for field in fields:
                if field['a'] and field['a'].startswith('(OCoLC)'):
                    return field['a']
        return self.metadata['oclc']

    def subjects(self):
        return [s.value() for s in self.marc.subjects()] if self.marc else []

    def uniformtitle(self):
        return self.marc.uniformtitle() if self.marc else ''

    def publisher(self):
        if self.marc and self.marc.publisher():
            return self.marc.publisher().rstrip(',. ')
        else:
            return self.metadata['publisher']

    def altpublisher(self):
        return self._altmeta.get('publisher', '').rstrip(',. ')

    def pubyear(self):
        if self.marc and self.marc.pubyear():
            return self.marc.pubyear().rstrip('. ')
        else:
            return self.metadata['pubyear']

    def altpubyear(self):
        return self._altmeta.get('pubyear', '').rstrip(',. ')

    def pubplace(self):
        return self.marc['260']['a'].strip('[]: ') if self.marc \
            else self.metadata['pubplace']

    def altpubplace(self):
        return self._altmeta.get('pubplace', '').rstrip(',. ')

    def imprint(self):
        return self.metadata.get('imprint', '')

    def formatcode(self):
        return self.metadata['formatcode']

    def langcode(self):
        return self.metadata['langcode']

    def language(self):
        try:
            language = pycountry.languages.get(bibliographic=self.langcode())
            return language.name
        except:
            return self.langcode()

    def libcode(self):
        return self.metadata['libcode']

    def library(self):
        return settings.LIB_LOOKUP[self.libcode()]

    def microdatatype(self):
        output = 'http://schema.org/%s'
        if self.formatcode() == 'am' or len(self.isbns()) > 0:
            return output % 'Book'
        else:
            return output % 'CreativeWork'

    def links(self):
        out = []
        for holding in self.holdings:
            out.extend(holding.links())
        return out

    def fulltext(self):
        out = []
        for holding in self.holdings:
            out.extend(holding.fulltext())
        return out

    def dump_dict(self, include=True):
        data = {}
        for key in self.metadata.keys():
            data[key] = getattr(self, key)()
        atts = ['trunctitle', 'altmeta', 'isbns', 'issns', 'subjects',
            'uniformtitle', 'language', 'library', 'microdatatype']
        for key in atts:
            data[key] = getattr(self, key)()
        if self.marc:
            data['marc'] = self.marc.as_dict()
        if include:
            data['holdings'] = [h.dump_dict() for h in self.holdings]
        return data

    def dump_json(self, include=True):
        return json.dumps(self.dump_dict(include=include),
            default=utils.date_handler, indent=2)


class Holding(object):

    META_TEMPLATE_HOLD = {
        'bibid': '',
        'mfhdid': '',
        'libcode': '',
        'locid': '',
        'location': '',
        'callnum': ''
    }

    def __init__(self, metadata={}, marc=None, items=[]):
        assert marc is None or isinstance(marc, pymarc.record.Record), \
            'marc must be a pymarc Record object'
        assert isinstance(items, list), \
            'items must be a list of Item objects'
        assert all(isinstance(i, Item) for i in items), \
            'holdings must be a list of Item objects'
        assert isinstance(metadata, dict), 'metadata must be a dictionary'

        super(Holding, self).__init__()
        self._marc = marc
        self._metadata = deepcopy(self.__class__.META_TEMPLATE_HOLD)
        self.metadata = metadata
        self._fulltext = self._getfulltext() if self.marc else None

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, new_meta):
        assert isinstance(new_meta, dict), 'new_meta must be a dictionary'
        #all values should be strings except for lists set in the template
        if __debug__:
            for key in new_meta:
                if isinstance(self.__class__.META_TEMPLATE_HOLD.get(key, None),
                    list):
                    if not isinstance(new_meta[key], list):
                        raise AssertionError('%s must be a list' % key)
                elif not isinstance(new_meta[key], str) and \
                    not isinstance(new_meta[key], unicode) and \
                    not isinstance(new_meta[key], int) and \
                    new_meta[key] is not None:
                    raise AssertionError('%s must be a string, not %s: %s' %
                        (key, type(new_mtea[key]), new_meta[key]))
        # wipe out existing values first
        del self.metadata
        for key in new_meta:
            if new_meta[key] is not None:
                if isinstance(new_meta[key], int):
                    self._metadata[key] = str(new_meta[key])
                else:
                    self._metadata[key] = new_meta[key]

    @metadata.deleter
    def metadata(self):
        # wipe out values but leave keys
        self._metadata = deepcopy(self.__class__.META_TEMPLATE_HOLD)

    @property
    def marc(self):
        return self._marc

    @marc.setter
    def marc(self, new_marc):
        assert isinstance(new_marc, pymarc.record.Record), \
            'new_marc must be a pymarc Record object'
        self._marc = new_marc

    @marc.deleter
    def marc(self):
        self._marc = None

    def pubnote(self):
        '''
        Returns 856$z notes
        856 is repeatable, but not in practice, so only using 1st hit
        '''
        return self.marc['852']['z'] if self.marc else ''

    def links(self):
        '''
        Returns list of 856$u links with accompanying $z and $3 notes.
        Each subfield is repeatable, but very unlikely, so only using 1st hit
        '''
        links = []
        if self.marc:
            for field in self.marc.get_fields('856'):
                link = {'url': field['u'],
                        'note': field['z'],
                        'material': field['3']}
                links.append(link)
        return links

    def textual(self):
        '''
        Returns list of 866$a textual holdings notes
        Subfield $a is not repeatable
        '''
        if self.marc:
            return [field['a'] for field in self.marc.get_fields('866')]
        return []

    def bibid(self):
        return self.metadata['bibid']

    def mfhdid(self):
        return self.metadata['mfhdid']

    def libcode(self):
        return self.metadata['libcode']

    def library(self):
        return settings.LIB_LOOKUP[self.libcode()]

    def locid(self):
        return self.metadata['locid']

    def location(self):
        try:
            if self.metadata['location'][2] == ':':
                loc = self.metadata['location'][3:]
            else:
                loc = self.metadata['location']
        except:
            loc = self.metadata['location']
        return loc.strip()

    def callnum(self):
        return self.metadata['callnum']

    def dump_dict(self, include=True):
        data = {}
        for k in self.metadata.keys():
            data[k] = getattr(self, k)()
        atts = ['pubnote', 'links', 'textual', 'library', 'fulltext']
        for k in atts:
            data[k] = getattr(self, k)()
        if self.marc:
            data['marc'] = self.marc.as_dict()
        if include:
            data['items'] = [i.dump_dict() for i in self.items]
        return data

    def dump_json(self, include=True):
        return json.dumps(self.dump_dict(include=include),
            default=utils.date_handler, indent=2)

    def _getfulltext(self):
        api = linkresolvers.get_resolver()
        fields = self.marc.get_fields('856') if self.marc else []
        fulltext = []
        try:
            for field in fields:
                if field['u']:
                    url = field['u'].lower()
                    fulltext.extend(api.links(url))
        except:
            pass
        return fulltext

    def fulltext(self):
        '''
        Returns a list of full text link dictionaries from a Link Resolver API
        '''
        if self._fulltext is None:
            self._fulltext = self._getfulltext()
        return self._fulltext


class Item(object):

    META_TEMPLATE_ITEM = {
        'itemid': '',
        'mfhdid': '',
        'bibid': '',
        'callnum': '',
        'enum': '',
        'status': '',
        'statuscode': '',
        'statusdate': '',
        'temploc': '',
        'permloc': '',
        'libcode': '',
        'chron': ''
    }

    def __init__(self, metadata={}):
        assert isinstance(metadata, dict), 'metadata must be a dictionary'
        super(Item, self).__init__()
        self._metadata = deepcopy(self.__class__.META_TEMPLATE_ITEM)
        self.metadata = metadata
        self.metadata['eligible'] = self.eligible()

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, new_meta):
        assert isinstance(new_meta, dict), 'metadata must be a dictionary'
        # wipe out existing values first
        del self.metadata
        for key in new_meta:
            if new_meta[key] is not None:
                if isinstance(new_meta[key], int):
                    self._metadata[key] = str(new_meta[key])
                else:
                    self._metadata[key] = new_meta[key]

    @metadata.deleter
    def metadata(self):
        # wipe out values but leave keys
        self._metadata = deepcopy(self.__class__.META_TEMPLATE_ITEM)

    def itemid(self):
        return self.metadata['itemid']

    def mfhdid(self):
        return self.metadata['mfhdid']

    def bibid(self):
        return self.metadata['bibid']

    def callnum(self):
        return self.metadata['callnum']

    def enum(self):
        return self.metadata['enum']

    def status(self):
        return self.metadata['status']

    def statuscode(self):
        return self.metadata['statuscode']

    def statusdate(self):
        return self.metadata['statusdate']

    def temploc(self):
        return self.metadata['temploc']

    def permloc(self):
        return self.metadata['permloc']

    def location(self):
        loc = self.temploc() if self.temploc() else self.permloc()
        if loc and loc[2] == ':':
            loc = loc[3:].strip()
        return loc

    def libcode(self):
        return self.metadata['libcode']

    def library(self):
        try:
            return settings.LIB_LOOKUP[self.libcode()]
        except KeyError:
            return ''

    def chron(self):
        return self.metadata['chron']

    def eligible(self, refresh=False):
        if refresh:
            del self.metadata['eligible']
            self.metadata['eligible'] = self.eligible()
            return self.metadata['eligible']
        if self.metadata.get('eligible', None):
            return self.metadata['eligible']
        if self.libcode() in settings.INELIGIBLE_LIBRARIES:
            return False
        for loc in settings.FORCE_ELIGIBLE_LOCS:
            if loc in self.permloc() or loc in self.temploc():
                return True
        for loc in settings.INELIGIBLE_PERM_LOCS:
            if loc in self.permloc():
                return False
        for loc in settings.INELIGIBLE_TEMP_LOCS:
            if loc in self.temploc():
                return False
        for status in settings.INELIGIBLE_STATUS:
            if status == self.status()[:len(status)]:
                return False
        return True

    def dump_dict(self):
        data = {}
        for key in self.metadata.keys():
            data[key] = getattr(self, key)()
        atts = ['location', 'library', 'eligible']
        for key in atts:
            data[key] = getattr(self, key)()
        return data

    def dump_json(self):
        return json.dumps(self.dump_dict(), default=utils.date_handler,
            indent=2)


class RecordSet(object):

    def __init__(self, bibs=[], openurl=''):
        assert isinstance(bibs, list), 'bibs must be a list'
        assert all(isinstance(b, Bib) for b in bibs), \
            'each element in bibs must be a Bib object'
        super(RecordSet, self).__init__()
        self._bibs = []
        self.bibs = bibs
        self.openurl = openurl

    @property
    def bibs(self):
        return self._bibs

    @bibs.setter
    def bibs(self, new_bibs):
        assert isinstance(new_bibs, list), 'bibs must be a list'
        assert all(isinstance(b, Bib) for b in new_bibs), \
            'each element in bibs must be a Bib object'
        self._bibs = new_bibs

    @bibs.deleter
    def bibs(self):
        self._bibs = []

    def gtbibs(self):
        return [bib for bib in self.bibs if bib.libcode in settings.GTCODES]

    def gmbibs(self):
        return [bib for bib in self.bibs if bib.libcode in settings.GMCODES]

    def holdings(self):
        return list(chain.from_iterable([bib.holdings for bib in self.bibs]))

    def items(self):
        return list(chain.from_iterable([bib.items() for bib in self.bibs]))

    def marc(self):
        return self.bibs[0].marc if self.bibs else None

    def metadata(self):
        return self.bibs[0].metadata if self.bibs else {}

    def altmeta(self):
        return self.bibs[0].altmeta() if self.bibs else {}

    def bibids(self):
        return [bib.bibid() for bib in self.bibs]

    def title(self):
        return self.bibs[0].title() if self.bibs else ''

    def trunctitle(self):
        return self.bibs[0].trunctitle() if self.bibs else ''

    def alttitle(self):
        return self.bibs[0].alttitle() if self.bibs else ''

    def edition(self):
        return self.bibs[0].edition() if self.bibs else ''

    def author(self):
        return self.bibs[0].author() if self.bibs else ''

    def altauthor(self):
        return self.bibs[0].altauthor() if self.bibs else ''

    def addedentries(self):
        return self.bibs[0].addedentries() if self.bibs else []

    def altaddedentries(self):
        return self.bibs[0].altaddedentries() if self.bibs else []

    def isbn(self):
        return self.bibs[0].isbn() if self.bibs else ''

    def isbns(self):
        if self.bibs:
            isbns = set()
            for bib in self.bibs:
                isbns.update(bib.isbns())
            return list(isbns)
        return []

    def issn(self):
        return self.bibs[0].issn() if self.bibs else ''

    def issns(self):
        if self.bibs:
            issns = set()
            for bib in self.bibs:
                issns.update(bib.issns())
            return list(issns)
        return []

    def oclc(self):
        return self.bibs[0].oclc() if self.bibs else ''

    def subjects(self):
        return self.bibs[0].subjects() if self.bibs else []

    def uniformtitle(self):
        return self.bibs[0].uniformtitle() if self.bibs else ''

    def publisher(self):
        return self.bibs[0].publisher() if self.bibs else ''

    def altpublisher(self):
        return self.bibs[0].altpublisher() if self.bibs else ''

    def pubyear(self):
        return self.bibs[0].pubyear() if self.bibs else ''

    def altpubyear(self):
        return self.bibs[0].altpubyear() if self.bibs else ''

    def pubplace(self):
        return self.bibs[0].pubplace() if self.bibs else ''

    def altpubplace(self):
        return self.bibs[0].altpubplace() if self.bibs else ''

    def imprint(self):
        return self.bibs[0].imprint() if self.bibs else ''

    def formatcode(self):
        return self.bibs[0].formatcode() if self.bibs else ''

    def langcode(self):
        return self.bibs[0].langcode() if self.bibs else ''

    def language(self):
        return self.bibs[0].language() if self.bibs else ''

    def libcode(self):
        return self.bibs[0].libcode() if self.bibs else ''

    def library(self):
        return self.bibs[0].library() if self.bibs else ''

    def microdatatype(self):
        return self.bibs[0].microdatatype() if self.bibs else ''

    def links(self):
        out = []
        for bib in self.bibs:
            out.extend(bib.links())
        return out

    def fulltext(self):
        out = []
        for bib in self.bibs:
            out.extend(bib.fulltext())
        return out

    def dump_dict(self, include=True):
        data = {'openurl': self.openurl}
        if self.bibs:
            atts = self.bibs[0].dump_dict(include=False).keys()
            excludeatts = ['bibid', 'marc']
            for key in atts:
                if key not in excludeatts:
                    data[key] = getattr(self, key)()
            if include:
                data['bibs'] = [b.dump_dict() for b in self.bibs]
        return data

    def dump_json(self, include=True):
        return json.dumps(self.dump_dict(include=include),
            default=utils.date_handler, indent=2)

    '''Sorting Methods'''
    def schoolsort(self):
        ours, shared, theirs, bottom = [], [], [], []
        for bib in self.bibs:
            if bib.libcode() in settings.PREF_LIBCODES:
                ours.append(bib)
            elif bib.libcode() in settings.SHARED_LIBCODES:
                shared.append(bib)
            elif bib.libcode() in settings.BOTTOM_LIBCODES:
                bottom.append(bib)
            else:
                theirs.append(bib)
        self.bibs = ours + shared + theirs + bottom
