from itertools import chain
from ui.records.bib import Bib

class RecordSet(object):

    def __init__(self, bibs=[]):
        assert isinstance(bibs, list), 'bibs must be a list'
        assert all(isinstance(b, Bib) for b in bibs), \
            'each element in bibs must be a Bib object'
        super(RecordSet, self).__init__()
        self._bibs = []
        self.bibs = bibs

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
        return self.bibs[0].isbns() if self.bibs else []

    def issn(self):
        return self.bibs[0].issn() if self.bibs else ''

    def issns(self):
        return self.bibs[0].issns() if self.bibs else []

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
