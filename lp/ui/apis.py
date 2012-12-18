from django.conf import settings

import json
from urllib2 import urlopen

from pymarc import marcxml


def get_bib_data(num, num_type):
    for api in settings.API_LIST:
        bib = globals()[api['name']](num=num, num_type=num_type,
            url=api.get('url', ''), key=api.get('key', ''))
        if bib:
            return bib
    return None


def googlebooks(num, num_type, url, key):
    url = url % (num_type, num)
    response = urlopen(url)
    json_data = json.loads(response.read())
    if json_data['totalItems'] == 0 or len(json_data.get('items', [])) == 0:
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
        std_nums.update([num, ])
        for std_num in volinfo['industryIdentifiers']:
            if num_type.upper() in std_num['type']:
                std_nums.update([std_num['identifier']])
        bib['DISPLAY_%s_LIST' % num_type.upper()] = list(std_nums)
    bib['PUBLISHER_DATE'] = volinfo.get('publishedDate', '')
    bib['IMPRINT'] = '%s %s' % (bib['PUBLISHER'], bib['PUBLISHER_DATE'])
    bib['BIB_FORMAT'] = 'as' if num_type == 'issn' else 'am'
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
    bib['AUTHORS'] = [entry.format_field() for entry in record.addedentries()]
    bib['AUTHOR'] = record.author() if record.author() else ''
    if bib['AUTHOR']:
        bib['AUTHORS'].insert(0, bib['AUTHOR'])
    bib['PUBLISHER'] = record.publisher() if record.publisher() else ''
    bib['PUBLISHER_DATE'] = record.pubyear() if record.pubyear() else ''
    bib['IMPRINT'] = '%s %s' % (bib['PUBLISHER'], bib['PUBLISHER_DATE'])
    bib['BIB_FORMAT'] = 'as' if num_type == 'issn' else 'am'
    return bib


def openlibrary(num, num_type, force=False, as_holding=True):
    assert num_type.upper() in ('ISBN', 'OCLC', 'LCCN', 'OLID')
    assert num_type.upper() != 'ISBN' or len(num) in (10, 13)
    params = '%s:%s' % (num_type, num)
    url = 'http://openlibrary.org/api/books?format=json&jscmd=data' + \
        '&bibkeys=%s' % params
    response = urlopen(url)
    json_data = json.loads(response.read())
    book = json_data.get(params, {})
    for ebook in book.get('ebooks', []):
        if ebook.get('availability', '') == 'full':
            return make_openlib_holding(book) if as_holding else book
    if not force:
        return {}    
    return make_openlib_holding(book) if as_holding else book


def make_openlib_holding(book):
    holding = {
        'LIBRARY_NAME': 'IA',
        'LOCATION_NAME': 'OL',
        'LOCATION_DISPLAY_NAME': 'OL: Open Library',
        'MFHD_DATA': {
            "marc866list": [],
            "marc856list": [
                {"3": "",
                "z": "",
                "u": ""}],
            "marc852": ""
        },
        'MFHD_ID': None,
        'ITEMS': [
            {'ITEM_ENUM': None,
            'ITEM_STATUS': None,
            'TEMPLOCATION': None,
            "ITEM_STATUS_DESC": None,
            "ITEM_ID": 0,
            "PERMLOCATION": None,
            "LIBRARY_FULL_NAME": "Internet Archive",
            "ELIGIBLE": False,
            "TRIMMED_LOCATION_DISPLAY_NAME": "Open Library",
            "CHRON": None,
            "DISPLAY_CALL_NO": None,
            "BIB_ID": None},
        ],
        'ELIGIBLE': False,
        'LIBRARY_FULL_NAME': 'Internet Archive',
        'TRIMMED_LOCATION_DISPLAY_NAME': 'Open Library',
        'ELECTRONIC_DATA': {},
        'LIBRARY_HAS': [],
        'LOCATION_ID': None,
        'AVAILABILITY': {},
        'DISPLAY_CALL_NO': None,
        'BIB_ID': None,
        }
    if book.keys():
        holding['ITEMS'][0]['DISPLAY_CALL_NO'] = \
            book.get('identifiers', {}).get('openlibrary', [])[0]
        holding['MFHD_DATA']['marc856list'][0]['u'] = book.get('url', '')
    return holding
