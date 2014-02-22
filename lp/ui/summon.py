import summoner

class Summon():
    """
    A wrapper for summoner.Summon which adds schema.org conversion. Maybe
    this could be pushed directly into summoner if it becomes comprehensive?
    """

    def __init__(self, summon_id, summon_key):
        self._summon = summoner.Summon(summon_id, summon_key)

    def status(self):
        return self._summon.status()

    def search(self, *args, **kwargs):
        response = self._summon.search(*args, **kwargs)
        results = []
        for doc in response['documents']:
            results.append(self._convert(doc))
        return results

    def _convert(self, doc):
        i = {}

        if 'DocumentTitleAlternate' in doc:
            i['name'] = doc['DocumentTitleAlternate'][0]
        elif 'Title' in doc:
            i['name'] = doc['Title'][0]
        else:
            i['name'] = '???'

        return i
