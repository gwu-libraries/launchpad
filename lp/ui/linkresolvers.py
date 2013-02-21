import sys
from lxml import etree
from urllib2 import urlopen

from django.conf import settings


def get_resolver():
    '''
    This function uses the settings file to determine which link resolver
    class the current instance of launchpad should be using and returns
    an instantiation of it.
    '''
    try:
        mod = sys.modules[__name__]
        args = settings.LINK_RESOLVER
        return getattr(mod, args['name'])(args['api_url'], args['stubs'],
            args['max_attempts'])
    except:
        raise


class LinkResolver():

    def __init__(self, api_url, stubs, max_attempts):
        self.api_url = api_url
        self.stubs = stubs
        self.max_attempts = max_attempts


class SerSol360Link(LinkResolver):

    def _extract(self, url856):
        '''
        Extracts out the ISSN or ISBN from a URL in the MARC 856$u
        '''
        for stub in self.stubs:
            if url856.startswith(stub):
                for num_type in ('issn', 'isbn'):
                    start = url856.lower().find('%s=' % num_type)
                    if start > -1:
                        num = url856[start + 5:]
                        stop = num.find('&')
                        num = num[:stop] if stop > -1 else num
                        return num, num_type
        return None, None

    def links(self, url856, count=0):
        '''
        Given a link from a MARC 856$u this function will return a list of
        direct links to full-text access sites. Each link is a dictionary
        with information about starting and ending coverage dates, the
        database name, provider name, and journal name.
        '''
        output = []
        num, num_type = self._extract(url856)
        if not num or not num_type:
            return output
        count += 1
        full_url = '%s&%s=%s' % (self.api_url, num_type, num)
        res = urlopen(full_url)
        tree = etree.fromstring(res.read())
        ns = 'http://xml.serialssolutions.com/ns/openurl/v1.0'
        openurls = tree.xpath('/sso:openURLResponse/sso:results/sso:result/' +
            'sso:linkGroups/sso:linkGroup[@type="holding"]',
            namespaces={'sso': ns})
        if not openurls and count < self.max_attempts:
            return self.links(num, num_type, count)
        for openurl in openurls:
            dbid = openurl.xpath('sso:holdingData/sso:databaseId',
                namespaces={'sso': ns})
            if not dbid:
                continue
            dbid = dbid[0]
            if dbid.text != 'TN5':
                data = {}
                start = openurl.xpath('sso:holdingData/sso:startDate',
                    namespaces={'sso': ns})
                data['start'] = start[0].text if start else ''
                end = openurl.xpath('sso:holdingData/sso:endDate',
                    namespaces={'sso': ns})
                data['end'] = end[0].text if end else ''
                dbname = openurl.xpath('sso:holdingData/sso:databaseName',
                    namespaces={'sso': ns})
                data['dbname'] = dbname[0].text if dbname else ''
                source = openurl.xpath('sso:url[@type="source"]',
                    namespaces={'sso': ns})
                data['source'] = source[0].text if source else ''
                journal = openurl.xpath('sso:url[@type="journal"]',
                    namespaces={'sso': ns})
                data['journal'] = journal[0].text if journal else ''
                output.append(data)
        return output

'''
The rest of this module should be fleshed out with classes for other link
resolvers. For example:

class SFX(LinkResolver):

    def links(self, url856, count=0):
        pass
'''
