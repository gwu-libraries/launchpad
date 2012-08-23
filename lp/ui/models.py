import pycountry

from django.conf import settings

import pymarc


class Bib(object):

    def __init__(self, metadata={}, raw_marc=None, holdings=[]):

        '''
        self.metadata is used for indexed metadata in catalog databases as well
        as metadata gathered from various bibliographic APIs such as Worldcat
        and Google Books. It should be a dictionary using the following key
        names (note that no field is required, this list is provided only to
        ensure the key names match:
            bibid           (catalog record)
            related_bibids  (list of related catalog records)
            title
            author          (primary)
            addedentries    (additional authors and editors, etc.)
            edition
            isbn            (the primary isbn associated with this item)
            related_isbns   (a list of related isbns)
            issn            (primary)
            related_issns   (related)
            oclc
            publisher
            pubplace
            pubyear
            langcode
            libcode
            formatcode
        '''
        super(Bib, self).__setattr__('metadata', {})
        super(Bib, self).__setattr__('holdings', [])
        super(Bib, self).__setattr__('marc', None)
        if metadata:
            self.load_metadata(metadata)
        if holdings:
            self.load_holdings(holdings)
        if raw_marc:
            self.load_marc(raw_marc)

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
    '''
    Initial loading functions, provided as conveniences. This data can be
    loaded during object creation. These functions overwrite previous data.
    '''
    def load_marc(self, raw_marc):
        try:
            self.marc = pymarc.record.Record(data=raw_marc)
        except:
            self.marc = None
            #TODO: throw error

    def load_holdings(self, holdings):
        self.holdings = []
        self.add_holdings(holdings)

    def load_metadata(self, metadata):
        try:
            for key in metadata:
                self.metadata[key] = metadata[key]
        except:
            self.metadata = {}
            #TODO: throw error

    '''
    getter, setter, and adder functions
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
    def add_holdings(self, new_holdings):
        #TODO: add type checking
        ids = [holding.id for holding in self.holdings]
        for new_holding in new_holdings:
            if new_holding.id not in ids:
                self.holdings.append(new_holding)
                ids.append(new_holding.id)

    def get_bibids(self):
        bibids = [self.bibid] if self.bibid else []
        bibids.extend(self.metadata.get('related_bibids', []))
        return bibids

    def add_bibids(self, new_bibids):
        new_bibids = [nb for nb in new_bibids if nb not in self.get_bibids()]
        self.metadata['related_bibids'].extend(new_bibids)

    def add_addedentries(self, new_names):
        new_names = [nn for nn in new_names if nn not in self.get_added_entries() and not nn == self.author]
        self.metadata['addedentries'].extend(new_names)

    def get_authors(self):
        authors = [self.author] if self.author else []
        authors.extend(self.get_added_entries())
        return authors

    def add_isbns(self, new_isbns):
        isbns = self.metadata.get('related_isbns', [])
        new_isbns = [ni for ni in new_isbns if not ni == self.isbn and ni not in isbns]
        self.metadata['related_isbns'] = isbns.extend(new_isbns)

    def get_isbns(self):
        isbns = [self.isbn] if self.isbn else []
        isbns.extend(self.metadata.get('related_isbns', []))
        return isbns

    def add_issns(self, new_issns):
        issns = self.metadata.get('related_issns', [])
        new_issns = [ni for ni in new_issns if not ni == self.issn and ni not in issns]
        self.metadata['related_issns'] = issns.extend(new_issns)

    def get_issns(self):
        issns = [self.issn] if self.issn else []
        issns.extend(self.metadata.get('related_issns', []))
        return issns

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

    def get_altscripts(self, asdict=False):
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

    def get_openurl(self):
        pass


class Holding(object):

    def __init__(self, metadata={}, raw_marc='', items=[]):

        '''
        self.metadata should be a dictionary containing the following keys:
            bibid
            mfhdid
            libcode
            locid
            loc
            callnum
        '''
        super(Holding, self).__setattr__('metadata', {})
        super(Holding, self).__setattr__('items', [])
        super(Holding, self).__setattr__('marc', None)
        if metadata:
            self.load_metadata(metadata)
        if items:
            self.load_items(items)
        if raw_marc:
            self.load_marc(raw_marc)

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

    def load_marc(self, raw_marc):
        try:
            self.marc = pymarc.record.Record(data=raw_marc)
        except:
            #TODO: flesh out error catching
            pass

    def load_items(self, items):
        #TODO: add error catching
        self.items = items

    def load_metadata(self, metadata):
        #TODO:add error catching
        self.metadata = metadata

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


class Item(object):

    def __init__(self, metadata={}):
        
        '''
        self.metadata is a dictionary with the following keys:
            itemid
            mfhdid
            bibid
            enum
            status
            statuscode
            statusdate
            temploc
            permloc
            libcode
            chron
        '''
        super(Item, self).__setattr__('metadata', {})

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

    def get_loc(self):
        loc = self.temploc if self.temploc else self.permloc
        if loc[2] == ':':
            loc = loc[3:].strip()
        return loc

    def get_eligible(self):
        if self.metadata.get('eligible', None):
            return self.metadata['metadata']
        if 'Law' in self.permloc:
            return False
        if self.libcode in settings.INELIGIBLE_LIBRARIES:
            return False
        for loc in settings.INELIGIBLE_PERM_LOCS:
            if loc in perm_loc:
                return False
        if 'WRLC' in self.temploc or 'WRLC' in self.permloc:
            return True
        for loc in settings.INELIGIBLE_TEMP_LOCS:
            if loc in self.temp_loc:
                return False
        for status in settings.INELIGIBLE_STATUS:
            if status == self.status[:len(status)]:
                return False
        return True
