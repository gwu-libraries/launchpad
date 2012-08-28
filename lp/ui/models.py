import pycountry

from django.conf import settings

import pymarc


class Bib(object):

    def __init__(self, metadata={}, raw_marc='', holdings=[]):

        super(Bib, self).__setattr__('metadata', {})
        super(Bib, self).__setattr__('holdings', [])
        super(Bib, self).__setattr__('marc', None)
        self.set_metadata(metadata)
        if holdings:
            self.set_holdings(holdings)
        if raw_marc:
            self.set_marc(raw_marc)

    '''
    The following methods allow for convenient access to bibliographic metadata
    using the dot operator (ex: mybib.title). This will first attempt to use a
    local method of producing the metadata on the fly if one exists, otherwise
    it will use the value stored in the indexed metadata dictionary. If no data
    exists it returns None.
    '''
    def __getattr__(self, name):
        if name.startswith('get_'):
            return None
        if getattr(self, 'get_' + name, None) is not None:
            return getattr(self, 'get_' + name)()
        if getattr(self.marc, name, None) is not None:
            return getattr(self.marc, name)()
        try:
            return self.metadata[name]
        except:
            return None
            #TODO: do something on error

    def __setattr__(self, name, value):
        if name in self.__dict__:
            super(Bib, self).__setattr__(name, value)
        else:
            fname = 'set_' + name
            function = getattr(self, fname, None)
            if function is not None:
                function(value)
            else:
                self.metadata[name] = value

    def set_marc(self, raw_marc):
        try:
            self.marc = pymarc.record.Record(data=raw_marc)
        except:
            raise
            #TODO: do something with error

    def set_holdings(self, new_holdings):
        for h in new_holdings:
            if not isinstance(h, Holding):
                return None
                #TODO: raise exception
        self.holdings = new_holdings

    def add_holdings(self, new_holdings):
        holdings = self.holdings.extend(new_holdings)
        self.set_holdings(holdings)

    def set_metadata(self, new_metadata):
        '''self.metadata is used for indexed metadata in catalog databases as
        well as metadata gathered from various bibliographic APIs such as
        Worldcat and Google Books.'''
        template = {
            'bibid': '',
            'related_bibids': [],
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
            'related_stdnums': {'isbn': [], 'issn': [], 'oclc': []}
            }
        '''related_stdnums is a dictionary of related isbn, issn and oclc
        numbers, with both normalized and display formats. Each has the
        following structure:
            'isbn':[{'norm':'1234', 'disp':'1234'},
                    {'norm':'4567', 'disp':'4567 (cloth)}]'''
        try:
            for key in new_metadata:
                if new_metadata[key]:
                    template[key] = new_metadata[key]
            self.metadata = template
        except:
            raise
            #TODO: do something with error

    '''
    getter, setter, and adder functions for metadata
    The getter and setter functions are called simply using the object's dot
    operator (ex: mybib.bibids or mybib.isbns = ['1234','3450','6294']).
    The adder functions ensure no duplicates when adding to a list attribute.
    Note that list attributes like isbn and bibid often have two components:
    the primary number and the list of related numbers. Thus there are three
    methods of accessing the combination of the two:
        mybib.bibid             (primary only)
        mybib.bibids            (primary at front of list)
        mbbib.related_bibids    (list does not include primary)
    '''
    def get_bibids(self):
        bibids = self.metadata['related_bibids']
        if self.bibid not in bibids:
            bibids[:0] = [self.bibid]
        return bibids

    def set_bibids(self, new_bibids):
        new_bibids = set(new_bibids)
        self.metadata['related_bibids'] = list(new_bibids)

    def add_bibids(self, new_bibids):
        bibids = set(self.metadata['related_bibids'])
        bibids.update(new_bibids)
        self.metadata['related_bibids'] = list(bibids)

    def add_addedentries(self, new_names):
        new_names = [nn for nn in new_names
            if nn not in self.addedentries
            and not nn == self.author]
        self.metadata['addedentries'].extend(new_names)

    def get_addedentries(self):
        if self.metadata['addedentries']:
            return self.metadata['addedentries']
        return [x.value() for x in self.marc.addedentries()]

    def get_authors(self):
        authors = [self.author] if self.author else []
        authors.extend(self.addedentries)
        return authors

    def get_brief_title(self):
        brief = self.title[:252]
        while brief[-1] != ' ':
            brief = brief[:-1]
        return '%s...' % brief.rstrip()

    def add_isbns(self, new_isbns):
        isbns = set(self.isbns)
        isbns.update([n for n in new_isbns if n != self.isbn])
        self.isbns = list(isbns)

    def get_isbns(self):
        isbns = set()
        if self.metadata.get('related_stdnums', {}).get('isbn', []):
            isbns.update([i['disp'] for i in self.related_stdnums['isbn']])
        else:
            isbns.update(self.metadata.get('isbns', []))
        isbns = list(isbns)
        if self.isbn and self.isbn not in isbns:
            isbns[:0] = [self.isbn]
        return isbns

    def add_issns(self, new_issns):
        issns = set(self.issns)
        issns.update([n for n in new_issns if n != self.issn])
        self.issns = list(issns)

    def get_issns(self):
        issns = set()
        if self.metadata.get('related_stdnums', {}).get('issn', []):
            issns.update([i['disp'] for i in self.related_stdnums['issn']])
        else:
            issns.update(self.metadata.get('issns', []))
        issns = list(issns)
        if self.issn and self.issn not in issns:
            issns[:0] = [self.issn]
        return issns

    def get_oclcs(self):
        oclcs = set()
        oclcs.update([i['disp'] for i in
            self.metadata.get('related_stdnums', {}).get('oclc', [])])
        oclcs = list(oclcs)
        if self.oclc and self.oclc not in oclcs:
            oclcs[:0] = [self.oclc]
        return oclcs

    def get_language(self):
        try:
            language = pycountry.languages.get(bibliographic=self.langcode)
            return language.name
        except:
            return self.langcode

    def get_library(self):
        try:
            return settings.LIB_LOOKUP[self.libcode]
        except:
            return self.libcode

    def get_altscripts(self, as_list=True):
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
        if not as_list:
            return [alts[key] for key in alts]
        return alts

    def get_openurl(self):
        #TODO
        pass

    def get_microdata_type(self):
        output = 'http://schema.org/%s'
        if self.formatcode == 'am' or len(self.isbns) > 0:
            return output % 'Book'
        else:
            return output % 'CreativeWork'


class Holding(object):

    def __init__(self, metadata={}, raw_marc=None, items=[]):

        super(Holding, self).__setattr__('metadata', {})
        super(Holding, self).__setattr__('items', [])
        super(Holding, self).__setattr__('marc', None)
        self.set_metadata(metadata)
        self.set_items(items)
        if raw_marc:
            self.set_marc(raw_marc)

    def __getattr__(self, name):
        if name.startswith('get_'):
            return None
        if getattr(self, 'get_' + name, None) is not None:
            return getattr(self, 'get_' + name)()
        try:
            return self.metadata[name]
        except:
            return None

    def __setattr__(self, name, value):
        if name in self.__dict__:
            super(Holding, self).__setattr__(name, value)
        else:
            fname = 'set_' + name
            function = getattr(self, fname, None)
            if function is not None:
                function(value)
            else:
                self.metadata[name] = value

    def set_marc(self, raw_marc):
        try:
            self.marc = pymarc.record.Record(data=raw_marc)
        except:
            #TODO: flesh out error catching
            raise

    def set_items(self, items):
        for i in items:
            if not isinstance(i, Item):
                return None
                #TODO: raise error
        self.items = items

    def add_items(self, new_items):
        for item in new_items:
            if not isinstance(item, Item):
                return None
            #TODO: raise error
        self.items.append(new_items)

    def set_metadata(self, new_metadata):
        '''self.metadata is a dictionary containing the following keys'''
        template = {
            'bibid': '',
            'mfhdid': '',
            'libcode': '',
            'locid': '',
            'loc': '',
            'callnum': ''}
        for key in new_metadata:
            if new_metadata[key]:
                template[key] = new_metadata[key]
        self.metadata = template

    # 852 $z data (possibly repeatable, but unlikely, so using first hit)
    def get_pubnote(self):
        try:
            return self.marc['852']['z']
        except:
            return ''

    # 856 $u,z,3 data (repeatable field)
    def get_links(self):
        try:
            links = []
            for field in self.marc.get_fields('856'):
                # each subfield is repeatable, but unlikely, so using 1st hit
                link = {'url': field['u'],
                        'note': field['z'],
                        'material': field['3']}
                links.append(link)
            return links
        except:
            return []

    #866 $a data (repeatable)
    def get_textual(self):
        try:
            # subfield $a is non-repeatable
            return [field['a'] for field in self.marc.get_fields('866')]
        except:
            return []

    def get_library(self):
        try:
            return settings.LIB_LOOKUP[self.libcode]
        except:
            return self.libcode


class Item(object):

    def __init__(self, metadata={}):

        super(Item, self).__setattr__('metadata', {})
        self.set_metadata(metadata)

    def __getattr__(self, name):
        if name.startswith('get_'):
            return None
        if getattr(self, 'get_' + name, None) is not None:
            return getattr(self, 'get_' + name)()
        try:
            return self.metadata[name]
        except:
            return ''

    def __setattr__(self, name, value):
        if name in self.__dict__:
            super(Item, self).__setattr__(name, value)
        else:
            fname = 'set_' + name
            function = getattr(self, fname, None)
            if function is not None:
                function(value)
            else:
                self.metadata[name] = value

    def set_metadata(self, metadata):
        ''' self.metadata is a dictionary with the following keys'''
        template = {
            'itemid': '',
            'mfhdid': '',
            'bibid': '',
            'enum': '',
            'status': '',
            'statuscode': '',
            'statusdate': '',
            'temploc': '',
            'permloc': '',
            'libcode': '',
            'chron': ''}
        try:
            for key in metadata:
                if metadata[key]:
                    template[key] = metadata[key]
            self.metadata = template
        except:
            raise
            #TODO: do something with error

    def get_loc(self):
        loc = self.temploc if self.temploc else self.permloc
        if loc and loc[2] == ':':
            loc = loc[3:].strip()
        return loc

    def get_eligible(self):
        if self.metadata.get('eligible', None):
            return self.metadata['metadata']
        if self.libcode in settings.INELIGIBLE_LIBRARIES:
            return False
        for loc in settings.FORCE_ELIGIBLE_LOCS:
            if loc in self.permloc or loc in self.temploc:
                return True
        for loc in settings.INELIGIBLE_PERM_LOCS:
            if loc in self.permloc:
                return False
        for loc in settings.INELIGIBLE_TEMP_LOCS:
            if loc in self.temploc:
                return False
        for status in settings.INELIGIBLE_STATUS:
            if status == self.status[:len(status)]:
                return False
        return True
