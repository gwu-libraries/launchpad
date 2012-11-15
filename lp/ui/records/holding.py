import pymarc

from django.conf import settings
from ui.records.item import Item


META_TEMPLATE_HOLD = {
    'bibid': '',
    'mfhdid': '',
    'libcode': '',
    'locid': '',
    'loc': '',
    'callnum': ''
}


class Holding():

    def __init__(self, metadata={}, marc=None, items=[]):
        assert isinstance(marc, pymarc.record.Record), \
            'marc must be a pymarc Record object'
        assert isinstance(items, list), \
            'items must be a list of Item objects'
        assert all(isinstance(i, Item) for i in items), \
            'holdings must be a list of Item objects'
        assert isinstance(metadata, dict), 'metadata must be a dictionary'

        super(Holding, self).__init__()
        self._marc = marc
        self._metadata = META_TEMPLATE_HOLD
        self.metadata = metadata

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, new_meta):
        assert isinstance(new_meta, dict), 'new_meta must be a dictionary'
        #all values should be strings except for lists set in the template
        if __debug__:
            for key in new_meta:
                if META_TEMPLATE_HOLD.get(key) and \
                    isinstance(META_TEMPLATE_HOLD[key], list):
                    if not isinstance(new_meta[key], list):
                        raise AssertionError('%s must be a list' % key)
                elif not isinstance(new_meta[key], str):
                    raise AssertionError('%s must be a string' % key)
        # wipe out existing values first
        del self.metadata
        for key in new_meta:
            self._metadata[key] = new_meta[key]

    @metadata.deleter
    def metadata(self):
        # wipe out values but leave keys
        self._metadata = META_TEMPLATE_HOLD

    @property
    def marc(self):
        return self._marc

    @marc.setter
    def marc(self, new_marc):
        assert isinstance(marc, pymarc.record.Record), \
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
        return settings.LIBRARIES[self.libcode()]

    def locid(self):
        return self.metadata['locid']

    def location(self):
        return self.metadata('loc')

    def callnum(self):
        return self.metadata['callnum']