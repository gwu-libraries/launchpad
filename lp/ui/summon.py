import summoner


class Summon():
    """
    A wrapper for summoner.Summon which adds schema.org conversion. Maybe
    this could be pushed into summoner if it becomes generalized.
    """

    def __init__(self, summon_id, summon_key):
        self._summon = summoner.Summon(summon_id, summon_key)

    def search(self, *args, **kwargs):
        """
        Performs the search and massages data into schema.org JSON-LD. If
        you pass in raw=True you will get the raw summon response instead.
        """
        summon_response = self._summon.search(*args, **kwargs)

        # return raw Summon response if that's what they want
        if kwargs.get("raw", False):
            return summon_response

        # django templates don't use @ prefixed parameters from json-ld
        for_template = kwargs.get('for_template', False)

        response = {"results": []}
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

        # must have a bibid and a type
        if 'ExternalDocumentID' not in doc or 'ContentType' not in doc:
            return None

        i['@id'] = '/item/' + doc['ExternalDocumentID'][0]
        i['@type'] = self._get_type(doc)

        if doc.get('Title'):
            i['name'] = doc['Title'][0]
            if doc.get('Subtitle'):
                i['name'] += " : " + doc['Subtitle'][0]

        i['author'] = []
        for name in doc.get('Author', []):
            i['author'].append({'name': name})

        if doc.get('PublicationYear'):
            i['datePublished'] = doc['PublicationYear'][0]

        if doc.get('Publisher'):
            i['publisher'] = {'name': doc['Publisher'][0]}
            if 'PublicationPlace' in doc:
                i['publisher']['address'] = doc['PublicationPlace'][0]

        if doc.get('thumbnail_m', []):
            i['thumbnailUrl'] = doc['thumbnail_m'][0]

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
        else:
            return 'Book'
