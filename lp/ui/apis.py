from django.conf import settings

import json, urllib2


def get_bib_data(num, num_type):
    for api in settings.API_LIST:
        bib = globals()[api](num=num, num_type=num_type)
        if bib:
            return bib
    return None


def googlebooks(num, num_type):
    url = 'https://www.googleapis.com/books/v1/volumes?q=%s:%s' % (num_type, num)
    response = urllib2.urlopen(url)
    json_data = json.loads(response.read())
    if json_data['totalItems'] == 0:
        return None
    item = json_data['items'][0]
    if not item['volumeInfo']:
        return None
    else:
        volinfo = item['volumeInfo']
    bib = {}
    bib[num_type.upper()] = num
    bib['TITLE'] = volinfo.get('title', '')
    bib['TITLE_ALL'] = bib['TITLE']
    bib['AUTHORS'] = volinfo.get('authors', '')
    bib['PUBLISHER'] = volinfo.get('publisher', '')
    if volinfo['industryIdentifiers']:
        std_nums = set()
        std_nums.update([num,])
        for std_num in volinfo['industryIdentifiers']:
            if num_type.upper() in std_num['type']:
                std_nums.update([std_num['identifier']])
        bib['DISPLAY_%s_LIST' % num_type.upper()] = list(std_nums)
    bib['IMPRINT'] = volinfo.get('publishedDate', '')
    bib['PUBLISHER_DATE'] = bib['IMPRINT']
    return bib
