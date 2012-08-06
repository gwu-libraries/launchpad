from django.conf import settings

import json
from urllib2 import urlopen

from pymarc import marcxml

def get_bib_data(num, num_type):
    for api in settings.API_LIST:
        bib = globals()[api['name']](num=num, num_type=num_type,
            url=api.get('url',''), key=api.get('key',''))
        if bib:
            return bib
    return None


def googlebooks(num, num_type, url, key):
    url = url % (num_type, num)
    response = urlopen(url)
    json_data = json.loads(response.read())
    if json_data['totalItems'] == 0:
        return None
    item = json_data['items'][0]
    if not item['volumeInfo']:
        return None
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
    bib['PUBLISHER_DATE'] = volinfo.get('publishedDate', '')
    bib['IMPRINT'] = '%s %s' % (bib['PUBLISHER'], bib['PUBLISHER_DATE'])
    bib['BIB_FORMAT'] = 'as' if num_type=='issn' else 'am'
    return bib


def worldcat(num, num_type, url, key):
    url = url % (num_type, num, key)
    records = marcxml.parse_xml_to_array(urlopen(url))
    if not records:
        return None
    record = records[0]
    bib = {}
    bib[num_type.upper()] = num
    bib['TITLE'] = record.uniformtitle()
    if not bib['TITLE']:
        bib['TITLE'] = record.title() if record.title() else ''
    bib['TITLE_ALL'] = bib['TITLE']
    bib['AUTHORS'] = record.addedentries() if record.addedentries() else []
    bib['AUTHOR'] = record.author() if record.author() else ''
    if bib['AUTHOR']:
        bib['AUTHORS'].insert(0, bib['AUTHOR'])
    bib['PUBLISHER'] = record.publisher() if record.publisher() else ''
    bib['PUBLISHER_DATE'] = record.pubyear() if record.pubyear() else ''
    bib['IMPRINT'] = '%s %s' % (bib['PUBLISHER'], bib['PUBLISHER_DATE'])
    bib['BIB_FORMAT'] = 'as' if num_type=='issn' else 'am'
    return bib

