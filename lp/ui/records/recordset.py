from itertools import chain
import json
from django.conf import settings
from ui import utils
from ui.records.bib import Bib


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
