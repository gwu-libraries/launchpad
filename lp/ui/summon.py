import re
import logging
import summoner

from urllib import urlencode
from datetime import datetime
from django.core.urlresolvers import reverse


class Summon():
    """
    A wrapper for summoner.Summon which massages the Summon response format
    into schema.org flavored JSON-LD. Maybe this could be pushed into
    summoner if it is general purpose enough.
    """

    def __init__(self, summon_id, summon_key):
        self._summon = summoner.Summon(summon_id, summon_key)

    def search(self, q, *args, **kwargs):
        """
        Performs the search and massages data into schema.org JSON-LD. If
        you pass in raw=True you will get the raw summon response instead.
        """
        t = datetime.now()
        summon_response = self._summon.search(q, *args, **kwargs)
        elapsed = datetime.now() - t
        logging.debug("summon %s: %s: %s - %s", q, args, kwargs, elapsed)

        # calculate some things to include in our response that Summon
        # responses don't explicitly include
        total_results = summon_response['recordCount']
        page = kwargs.get("pn", 1)
        items_per_page = kwargs.get("ps", 10)
        start_index = (page * items_per_page) - items_per_page

        # return raw Summon response if that's what they want
        if kwargs.get("raw", False):
            return summon_response

        # django templates don't use @ prefixed parameters from json-ld
        for_template = kwargs.get('for_template', False)

        response = {
            "query": q,
            "totalResults": total_results,
            "itemsPerPage": items_per_page,
            "startIndex": start_index,
            "results": []
        }

        # summarize facets
        if 'facetFields' in summon_response:
            response['facets'] = []
            for ff in summon_response['facetFields']:
                facet = {'name': ff['displayName'], 'counts': []}
                for c in ff['counts']:
                    facet['counts'].append({
                        'name': c['value'],
                        'count': c['count']
                    })
                response['facets'].append(facet)

        seen = {}
        for doc in summon_response['documents']:
            item = self._convert(doc)
            if item:
                # only include items that are held by a library
                if len(item['offers']) == 0:
                    continue
                # sometimes (rarely) the same item appears more than once?
                # e.g. search for "statistics"
                if item['@id'] in seen:
                    continue
                seen[item['@id']] = True
                if for_template:
                    item['id'] = item.pop('@id')
                    item['type'] = item.pop('@type')
                response['results'].append(item)

        return response

    def _convert(self, doc):
        i = {}

        # must have an id and a type
        id = self._id(doc)
        if id is None or 'ContentType' not in doc:
            return None

        i['wrlc'] = id
        i['@id'] = '/item/' + id
        i['@type'] = self._get_type(doc)

        if doc.get('Title'):
            i['name'] = doc['Title'][0]
            if doc.get('Subtitle'):
                i['name'] += " : " + doc['Subtitle'][0]

        if 'Author_xml' in doc:
            i['author'] = []
            for name in doc.get('Author_xml', []):
                if 'fullname' in name:
                    q = ('Author:"%s"' % name['fullname']).encode('utf8')
                    i['author'].append({
                        'name': name['fullname'],
                        'url': reverse('search') + '?' + urlencode({'q': q})
                    })
            for alt_name in doc.get('Author_FL_xml', []):
                if 'fullname' in alt_name:
                    p = int(alt_name['sequence']) - 1
                    if p < len(i['author']):
                        i['author'][p]['alternateName'] = alt_name['fullname']

        if 'SubjectTermsDisplay' in doc:
            i['about'] = []
            for subject in doc.get('SubjectTermsDisplay', []):
                subject = subject.strip('.')
                q = ('SubjectTerms:"%s"' % subject).encode('utf8')
                i['about'].append({
                    'name': subject,
                    'url': reverse('search') + '?' + urlencode({'q': q})
                })

        if doc.get('PublicationYear'):
            i['datePublished'] = doc['PublicationYear'][0]

        if doc.get('Publisher'):
            i['publisher'] = {'name': doc['Publisher'][0]}
            if 'PublicationPlace' in doc:
                i['publisher']['address'] = doc['PublicationPlace'][0]

        if doc.get('thumbnail_m', []):
            i['thumbnailUrl'] = doc['thumbnail_m'][0]

        if doc.get('ISBN'):
            i['isbn'] = doc['ISBN']

        if doc.get('ISSN'):
            i['issn'] = doc['ISSN']

        if doc.get('Edition'):
            i['bookEdition'] = doc['Edition'][0].strip('.')

        if doc.get('DocumentTitle_FL'):
            i['alternateName'] = doc.get('DocumentTitle_FL')[0]

        i['offers'] = []
        offer = self._get_offer(doc)
        if offer:
            i['offers'].append(offer)
        for peer_doc in doc.get('peerDocuments', []):
            offer = self._get_offer(peer_doc)
            if offer:
                i['offers'].append(offer)
        i = self._rewrite_ids(i)

        return i

    def _get_offer(self, doc):
        offer = None
        id = self._id(doc)
        if doc.get('Institution'):
            inst = doc.get('Institution')[0]
            inst = re.sub(' \(.+\)', '', inst)
            offer = {
                'seller': inst,
                'serialNumber': id
            }
        elif doc.get('LCCallNum') == ['Shared Electronic Book']:
            offer = {
                'seller': 'WRLC',
                'serialNumber': id
            }

        return offer

    def _rewrite_ids(self, item):
        # launchpad urls need to be massaged when the primary holding
        # (the first) for the item is from George Mason and Georgetown
        #
        # Both institutions loaded into Summon using their own ILS
        # record identifiers, which we can look up, but are not
        # Voygager bibids that we can look up directly. The 'm' and 'b'
        # prefixes to the ids are an indicator to launchpad to look them
        # up indirectly.

        if len(item['offers']) == 0:
            return item

        # rewrite @id based on the first offer's institution
        offer = item['offers'][0]
        if offer['seller'] == 'George Mason University':
            # sometimes they have the 'm' prefix sometimes they don't
            if not item['wrlc'].startswith('m'):
                item['wrlc'] = 'm' + item['wrlc']
            item['@id'] = '/item/' + item['wrlc']
        elif offer['seller'] == 'Georgetown University':
            if not item['wrlc'].startswith('b'):
                item['@id'] = '/item/b' + item['wrlc']

        # rewrite offer serialNumbers which are used to look up holdings
        for offer in item['offers']:
            seller = offer.get('seller')
            sn = offer.get('serialNumber')

            if seller == 'George Mason University' and not sn.startswith('m'):
                offer['serialNumber'] = 'm' + sn
            elif seller == 'Georgetown University' and not sn.startswith('b'):
                offer['serialNumber'] = 'b' + sn

        return item

    def _get_type(self, doc):
        content_type = doc['ContentType'][0]
        if content_type == "Book":
            return 'Book'
        elif content_type == "Audio Recording":
            return 'AudioObject'
        elif content_type == 'Map':
            return 'Map'
        elif content_type == 'Journal' or content_type == 'Newspaper':
            return 'Periodical'
        elif content_type == 'eBook':
            return 'Book'
        elif content_type == 'Video Recording':
            return 'VideoObject'
        elif content_type == 'Web Resource':
            return 'WebPage'
        elif content_type == 'Archival Material':
            return 'Manuscript'
        else:
            return 'Book'

    def _id(self, doc):
        """
        _id determines the Voyager id for a document which is used when
        linking to launchpad for a specific item. If the id cannot be
        determined None is returned.

        The id is determined using the availabilityId value. availaibilityId
        usually has a value like "Z6W 13691563", the second part of which is
        the Voyager record id.

        Occasionally the availiabilityId key isn't directly present in the
        document, in which case we fall back to looking for the
        availaibilityId found in the first document in the peerDocuments
        stanza, if one is available.

        Historical note: we initially used the first value in
        ExternalDocumentId but it was not entirely reliable.

        See: https://github.com/gwu-libraries/launchpad/issues/897
        """

        parts = doc.get('availabilityId', '').split(' ')
        if len(parts) == 2:
            return parts[1]
        if 'peerDocuments' in doc and len(doc['peerDocuments']) > 0:
            return self._id(doc['peerDocuments'][0])
        return None
