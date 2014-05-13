import re
import summoner


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
        summon_response = self._summon.search(q, *args, **kwargs)

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

        for doc in summon_response['documents']:
            item = self._convert(doc)
            if item:
                if for_template:
                    item['id'] = item.pop('@id')
                    item['type'] = item.pop('@type')
                response['results'].append(item)

        return response

    def _convert(self, doc):
        i = {}

        # must have an id and a type
        if 'ExternalDocumentID' not in doc or 'ContentType' not in doc:
            return None

        id = doc['ExternalDocumentID'][0]
        i['@id'] = '/item/' + doc['ExternalDocumentID'][0]
        i['@type'] = self._get_type(doc)

        # TODO: add summon to json-ld context document once there is one
        i['summon'] = doc['ExternalDocumentID'][0]

        if doc.get('Title'):
            i['name'] = doc['Title'][0]
            if doc.get('Subtitle'):
                i['name'] += " : " + doc['Subtitle'][0]

        i['author'] = []
        for name in doc.get('Author_xml', []):
            i['author'].append({'name': name['fullname']})
        for alt_name in doc.get('Author_FL_xml', []):
            pos = int(alt_name['sequence']) - 1
            if pos < len(i['author']):
                i['author'][pos]['alternateName'] = alt_name['fullname']

        i['about'] = []
        for subject in doc.get('SubjectTermsDisplay', []):
            subject = subject.strip('.')
            i['about'].append({'name': subject})

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

        if doc.get('Institution'):
            i['offers'] = []
            inst = doc.get('Institution')[0]
            inst = re.sub(' \(.+\)', '', inst)
            i['offers'].append({
                'seller': inst,
                'serialNumber': id
            })

            # George Mason and Georgetown load into Summon with their own ids.
            # Launchpad handles these with the the m & b prefixes

            # TODO: make @id into absolute URL?
            if inst  == 'George Mason University':
                i['@id'] = '/item/m' + id
                # make sure summon id starts with 'm'
                if not id.startswith('m'):
                    i['summon'] = 'm' + i['summon']
            elif inst == 'Georgetown':
                i['@id'] = '/item/b' + id

        return i

    def _get_type(self, doc):
        content_type = doc['ContentType'][0]
        if content_type == "Book":
            return 'Book'
        elif content_type == "Audio Recording":
            return 'AudioObject'
        elif content_type == 'Map':
            return 'Map'
        elif content_type == 'Journal':
            return 'Periodical'
        elif content_type == 'eBook':
            return 'Book'
        elif content_type == 'Video Recording':
            return 'VideoObject'
        elif content_type == 'Web Resource':
            return 'WebPage'
        else:
            return 'Book'
