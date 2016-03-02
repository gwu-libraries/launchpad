import json
from lxml import etree

from urllib2 import urlopen

from pymarc import marcxml

from django.conf import settings

from ui.templatetags.launchpad_extras import clean_isbn


def get_bib_data(num, num_type):
    for api in settings.API_LIST:
        bib = globals()[api['name']](num=num, num_type=num_type,
                                     url=api.get('url', ''),
                                     key=api.get('key', ''))
        if bib:
            return bib
    return None


def googlebooks(num, num_type, url, key):
    url = url % (num_type, num)
    try:
        response = urlopen(url)
        json_data = json.loads(response.read())
    except:
        return None
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
    bib['SUBTITLE'] = volinfo.get('subtitle', '')
    if bib['SUBTITLE']:
    	bib['TITLE_ALL'] = '%s %s %s' % (bib['TITLE'], ' / ', bib['SUBTITLE'])
    bib['AUTHORS'] = volinfo.get('authors', '')
    bib['PUBLISHER'] = volinfo.get('publisher', '')
    if 'industryIdentifiers' in volinfo:
        std_nums = set()
        std_nums.update([num, ])
        for std_num in volinfo['industryIdentifiers']:
            if num_type.upper() in std_num['type']:
                std_nums.update([std_num['identifier']])
        bib['DISPLAY_%s_LIST' % num_type.upper()] = list(std_nums)
    bib['PUBLISHER_DATE'] = volinfo.get('publishedDate', '')
    bib['EDITION'] = '%s %s' % (bib['PUBLISHER'], bib['PUBLISHER_DATE'])
    bib['PAGES'] = volinfo.get('pageCount', '')
    if bib['PAGES']:
	bib['EDITION'] += '%s %s' % (" Pages: ", bib['PAGES'])
    bib['GOOGLE_MESSAGE'] = 'Information provided below was retrieved from Google Books.'
    bib['GOOGLE_REVIEW'] = volinfo.get('description', '')
    bib['GOOGLE_LINK'] = volinfo.get('infoLink', '')
    return bib


def worldcat(num, num_type, url, key):
# e.g., /oclc/34473395  /oclc/34474496
    url = url % (num, key)
    try:
        records = marcxml.parse_xml_to_array(urlopen(url))
        if not records:
            return None
        record = records[0]
    except:
        return None
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
    try:
    	bib['PUBLISH_DATE'] = record.pubyear() 
    except:
	bib['PUBLISH_DATE'] = ''
    bib['IMPRINT'] = '%s %s' % (bib['PUBLISHER'], bib['PUBLISH_DATE'])
    bib['BIB_FORMAT'] = 'as' if num_type == 'issn' else 'am'
    bib['ISBN'] = record.isbn()
    try:
	physical = [entry.format_field() for entry in record.physicaldescription()]
    	bib['DESC'] = physical[0]
    except:
	bib['DESC'] = ''
    try:
	notes = [entry.format_field() for entry in record.notes()]
    	bib['NOTES'] = notes[0]
    except:
	bib['NOTES'] = ''
    try:
	subjects = [entry.format_field() for entry in record.subjects()]
    	bib['SUBJECTS'] = subjects[0]
    except:
	bib['SUBJECTS'] = ''
    # identify worldcat response for the item.html block
    bib['WORLDCAT_RESPONSE'] = num
    bib['WORLDCAT_MESSAGE'] = 'This page contains information from the OCLC WorldCat catalog.'
    bib['WORLDCAT_SEARCH'] = '<a href=http://www.worldcat.org/search?q={{ bib.TITLE }}\
				>Search OCLC Worldcat</a>'
    return bib


def openlibrary(num, num_type, force=False, as_holding=True):
    # ensure we're dealing with a proper identifier type and value
    try:
        if num_type.upper() not in ('ISBN', 'OCLC', 'LCCN', 'OLID'):
            raise
        if num_type.upper() == 'ISBN':
            num = clean_isbn(num)
            if len(num) not in (10, 13):
                raise
    except:
        return {}
    params = '%s:%s' % (num_type, num)
    url = 'http://openlibrary.org/api/books?format=json&jscmd=data' + \
        '&bibkeys=%s' % params
    try:
        response = urlopen(url)
        json_data = json.loads(response.read())
        book = json_data.get(params, {})
        for ebook in book.get('ebooks', []):
            if ebook.get('availability', '') == 'full':
                return make_openlib_holding(book) if as_holding else book
        if not force:
            return {}
        return make_openlib_holding(book) if as_holding else book
    except:
        return {}


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


def hathitrust(num, num_type):
    # ensure we're dealing with a proper identifier type and value
    try:
        if num_type.upper() not in ('ISBN', 'OCLC', 'LCCN', 'OLID'):
            raise
        if num_type.upper() == 'ISBN':
            num = clean_isbn(num)
            if len(num) not in (10, 13):
                raise
    except:
        return {}
    params = '%s/%s' % (num_type, num)
    url = 'http://catalog.hathitrust.org/api/volumes/brief/%s.json' % params
    try:
        response = urlopen(url)
        json_data = json.loads(response.read())
        for item in json_data.get('items', []):
            if item.get('usRightsString', '') == 'Full view':
                return make_hathi_holding(item.get('itemURL', ''),
                                          item.get('fromRecord', ''))
    except:
        return {}


def make_hathi_holding(url, fromRecord):
    # use library name IA
    # add dummy elements to conform with holding model
    holding = {
        'LIBRARY_NAME': 'IA',
        'LOCATION_NAME': 'HT',
        'LOCATION_DISPLAY_NAME': 'HT: Hathi Trust',
        'MFHD_DATA': {
            "marc866list": [],
            "marc856list": [
                {"3": "",
                 "z": "",
                 "u": url}],
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
             "LIBRARY_FULL_NAME": "Hathi Trust",
             "ELIGIBLE": False,
             "TRIMMED_LOCATION_DISPLAY_NAME": "Hathi Trust Digital Library",
             "CHRON": None,
             "DISPLAY_CALL_NO": fromRecord,
             "BIB_ID": None},
        ],
        'ELIGIBLE': False,
        'LIBRARY_FULL_NAME': 'Hathi Trust',
        'TRIMMED_LOCATION_DISPLAY_NAME': 'Hathi Trust Digital Library',
        'ELECTRONIC_DATA': {},
        'LIBRARY_HAS': [],
        'LOCATION_ID': None,
        'AVAILABILITY': {},
        'DISPLAY_CALL_NO': 'Record ' + fromRecord,
        'BIB_ID': None,
    }
    return holding

def sersol360link(num, num_type, count=0):
    try:
        count += 1
        url = '%s&%s=%s' % (settings.SER_SOL_API_URL, num_type, num)
        response = urlopen(url)
        tree = etree.fromstring(response.read())
    except:
        return []
    output = []
    ns = 'http://xml.serialssolutions.com/ns/openurl/v1.0'
    openurls = tree.xpath('/sso:openURLResponse/sso:results/sso:result/sso' +
                          ':linkGroups/sso:linkGroup[@type="holding"]',
                          namespaces={'sso': ns})
    if not openurls and count < settings.SER_SOL_API_MAX_ATTEMPTS:
        return sersol360link(num, num_type, count)
    for openurl in openurls:
        dbid = openurl.xpath('sso:holdingData/sso:databaseId',
                             namespaces={'sso': ns})
        if not dbid:
            continue
        dbid = dbid[0]
        if dbid.text != settings.SER_SOL_DBID_TEXT:
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
