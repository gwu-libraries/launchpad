from itertools import chain
import pymarc

from django.conf import settings
from ui.records.holding import Holding


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
    'oclc': '',
}


class Bib(object):

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
        self._metadata = META_TEMPLATE_BIB
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
                if META_TEMPLATE_BIB.get(key) and \
                    isinstance(META_TEMPLATE_BIB[key], list):
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
        self._metadata = META_TEMPLATE_BIB

    @property
    def marc(self):
        return self._marc

    @marc.setter
    def marc(self, new_marc):
        assert isinstance(marc, pymarc.record.Record), \
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
        return self.marc.title() if self.marc else self.metadata['title']

    def trunctitle(self):
        trunc = self.title()[:252]
        while brief[-1] != ' ':
            brief = brief[:-1]
        return '%s...' % brief

    def alttitle(self):
        return self._altmeta.get('title', '')

    def author(self):
        return self.marc.author() if self.marc else self.metadata['author']

    def altauthor(self):
        return self._altmeta.get('author', '')

    def addedentries(self):
        return self.marc.addedentries() if self.marc \
            else self.metadata['addedentries']

    def altaddedentries(self):
        return self._altmeta.get('addedentries', '')

    def isbn(self):
        return self.marc.isbn() if self.marc else self.metadata['isbn']

    def isbns(self):
        return self.metadata['isbns']

    def issn(self):
        return self.marc['022']['a'] if self.marc else self.metadata['issn']

    def issns(self):
        return self.metadata['issns']

    def oclc(self):
        return self.metadata['oclc']

    def subjects(self):
        return self.marc.subjects() if self.marc else []

    def uniformtitle(self):
        return self.marc.uniformtitle() if self.marc else ''

    def publisher(self):
        return self.marc.publisher() if self.marc else self.metadata['publisher']

    def altpublisher(self):
        return self._altmeta.get('publisher', '')

    def pubyear(self):
        return self.marc.pubyear() if self.marc else self.metadata['pubyear']

    def altpubyear(self):
        return self._altmeta.get('pubyear', '')

    def pubplace(self):
        return self.marc['260']['a'] if self.marc else self.metadata['pubplace']

    def altpubplace(self):
        return self._altmeta.get('pubplace', '')

    def formatcode(self):
        return self.metadata['formatcode']

    def langcode(self):
        return self.metadata['langcode']

    def language(self):
        try:
            language = pycountry.languages.get(bibliographic=self.langcode())
            return language.name
        except:
            return self.langcode

    def libcode(self):
        return self.metadata['libcode']

    def library(self):
        return settings.LIBRARIES[self.libcode()]

    def microdatatype(self):
        output = 'http://schema.org/%s'
        if self.formatcode() == 'am' or len(self.isbns()) > 0:
            return output % 'Book'
        else:
            return output % 'CreativeWork'
