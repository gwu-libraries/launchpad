import pycountry

from django.db import models
from django.conf import settings


class Bib(object):

    def __init__(self):
    
        self.fields = {}
        self.holdings = []
    
    def __getitem__(self, key):
        try:
            return self.fields[key]
        except:
            return None
            
    def __setitem__(self, key, value):
        self.fields[key] = value
        
    def title(self, raw_marc=False):
        if raw_marc:
            return self['marc245']
        try:
            return ' '.join([subfield[1:].rstrip(' /') for subfield in self.fields['marc245'].split('$')[1:] if subfield[0] in ('a','b')])
        except:
            return self['title']
    
    def bibids(self, include_primary=True):
        bibids = [self['bibid']] if self['bibid'] and include_primary else []
        if self['related_bibids']:
            bibids.extend(self['related_bibids'])
        return bibids
    
    def authors(self, include_primary=True):
        authlist = [self['author']] if self['author'] and include_primary else []
        for field in ('marc700', 'marc710', 'marc711'):
            if self[field]:
                authlist.extend([auth.rstrip(' .') for auth in self[field].split(' // ')])
        return authlist

    def isbns(self, include_primary=True):
        isbns = [self['isbn']] if self['isbn'] and include_primary else []
        if self['related_isbns']:
            isbns.extend(self['related_isbns'])
        return isbns
    
    def issns(self, include_primary=True):
        issns = [self['issn']] if self['issn'] and include_primary else []
        if self['related_issns']:
            issns.extend(self['related_issns'])
        return issns
    
    def oclcs(self, include_primary=True):
        oclcs = [self['isbn']] if self['isbn'] and include_primary else []
        if self['related_oclcs']:
            oclcs.extend(self['related_oclcs'])
        return oclcs
    
    def language(self):
        try:
            language = pycountry.languages.get(bibliographic=self['language_code'])
            return language.name
        except:
            return self['language_code']
            
    def library(self):
        try:
            return settings.LIB_LOOKUP[self['library_code']]
        except:
            return self['library_code']
    
    def imprint(self):
        if self['imprint']:
            return self['imprint']
        return ' '.join([self[f].strip() for f in ('publisher_place', 'publisher', 'publisher_date') if self[f]])
    
    def altscripts(self, asdict=False):
        try:
            tags = self['marc880'].split(' // ')
            if asdict:
                d = {}
                for tag in tags:
                            d[tag[:3]] = tag[8:].rstrip()
            else:
                d = [tag[8:].rstrip() for tag in tags]
            return d
        except:
            return None
    
    def openurl(self):
        pass
        

