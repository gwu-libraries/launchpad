import pymarc

from django.conf import settings


META_TEMPLATE_ITEM = {
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
    'chron': ''
}


class Item():

    def __init__(self, metadata={}):
        assert isinstance(metadata, dict), 'metadata must be a dictionary'
        super(Item, self).__init__()
        self._metadata = META_TEMPLATE_ITEM
        self.metadata = metadata
        self.metadata['eligible'] = self.eligible()

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, new_meta):
        assert isinstance(new_meta, dict), 'metadata must be a dictionary'
        assert all(isinstance(new_meta[k], str) for k in new_meta), \
            'all metadata values must be strings'
        # wipe out existing values first
        del self.metadata
        for key in new_meta:
            self._metadata[key] = new_meta[key]

    @metadata.deleter
    def metadata(self):
        # wipe out values but leave keys
        self._metadata = META_TEMPLATE_ITEM

    def itemid(self):
        return self.metadata['itemid']

    def mfhdid(self):
        return self.metadata['mfhdid']

    def bibid(self):
        return self.metadata['bibid']

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
        loc = self.temploc if self.temploc else self.permloc
        if loc and loc[2] == ':':
            loc = loc[3:].strip()
        return loc

    def libcode(self):
        return self.metadata['libcode']

    def library(self):
        return settings.LIBRARIES[self.libcode()]

    def chron(self):
        return self.metadata['chron']

    def eligible(self):
        if self.metadata.get('eligible', None):
            return self.metadata['eligible']
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