from django.db import connection, transaction


def _make_dict(cursor):
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def get_bib_data(bibid):
    query = """
SELECT bib_text.bib_id, title, author, edition, isbn, issn, network_number, 
       publisher, pub_place, imprint, bib_format, language, library_name, 
       RTRIM(wrlcdb.GetMarcField(%s,0,0,'856','','u',1)) as LINK 
FROM bib_text, bib_master, library
WHERE bib_text.bib_id=%s
AND bib_text.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid, bibid])
    return  _make_dict(cursor)[0]


def get_related_bibids(isbn='', issn='', oclc=''):
     if isbn:
         return get_bibids_from_isbn(isbn=isbn, subset='other')
     elif issn:
         return get_bibids_from_issn(issn=issn, subset='other')
     elif oclc:
         return get_bibids_from_oclc(oclc=oclc, subset='other')


def get_bibids_from_isbn(isbn, subset='gw'):
    query = """
SELECT bib_index.bib_id, bib_master.library_id, 
       library_name, normal_heading, display_heading 
FROM bib_index, bib_master, library 
WHERE bib_index.index_code=%s 
AND bib_index.normal_heading like %s 
AND bib_index.bib_id=bib_master.bib_id 
AND bib_master.library_id=library.library_id""" 
    code = 'ISB3' if len(isbn) == 13 else '020A' 
    cursor = connection.cursor()
    cursor.execute(query, [code,isbn])
    data = _make_dict(cursor)
    if subset == 'gw':
        return [item['BIB_ID'] for item in data if item['LIBRARY_ID'] in [7,11,18,21]]
    elif subset == 'other':
        return [item['BIB_ID'] for item in data if item['LIBRARY_ID'] not in [7,11,18,21]]
    elif subset == 'all':
        return [item['BIB_ID'] for item in data]


def get_bibids_from_issn(issn, subset='gw'):
    query = """
SELECT bib_index.bib_id, bib_master.library_id, library.library_name
FROM bib_index,bib_master,library
WHERE bib_index.index_code='022A'
AND bib_index.display_heading=%s
AND bib_index.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id"""
    cursor = connection.cursor()
    cursor.execute(query, [issn])
    data = _make_dict(cursor)
    if subset == 'gw':
        return [item['BIB_ID'] for item in data if item['LIBRARY_ID'] in [7,11,18,21]]
    elif subset == 'other':
        return [item['BIB_ID'] for item in data if item['LIBRARY_ID'] not in [7,11,18,21]]
    elif subset == 'all':
        return [item['BIB_ID'] for item in data]


def get_bibid_from_oclc(oclc):
    query = """
SELECT bib_index.bib_id, bib_index.index_code, bib_index.normal_heading, 
       bib_index.display_heading, bib_master.library_id, library.library_name
FROM bib_index, bib_master, library
WHERE bib_index.index_code='035A'
AND bib_index.normal_heading=%s
AND bib_master.bib_id=bib_index.bib_id
AND bib_master.library_id=library.library_id"""
    cursor = connection.cursor()
    cursor.execute(query, [oclc])
    data = _make_dict(cursor)
    if subset == 'gw':
        return [item['BIB_ID'] for item in data if item['LIBRARY_ID'] in [7,11,18,21]]
    elif subset == 'other':
        return [item['BIB_ID'] for item in data if item['LIBRARY_ID'] not in [7,11,18,21]]
    elif subset == 'all':
        return [item['BIB_ID'] for item in data]


def get_holdings_data(bib_data):
    bibids = [bib_data['BIB_ID']]
    if bib_data['ISBN']:
        bibids.append(get_related_bibids(isbn=bib_data['ISBN']))
    elif bib_data['ISSN']:
        bibids.append(get_related_bibids(issn=bib_data['ISSN']))
    elif bib_data['NETWORK_NUMBER']:
        bibids.append(get_related_bibids(oclc=bib_data['NETWORK_NUMBER']))
    holdings_list = []
    for bibid in bibids:
        query = """
SELECT bib_mfhd.bib_id, mfhd_master.mfhd_id, mfhd_master.location_id,
       mfhd_master.display_call_no, location.location_display_name,
       library.library_name
FROM bib_mfhd INNER JOIN mfhd_master ON bib_mfhd.mfhd_id = mfhd_master.mfhd_id,
     location, library
WHERE mfhd_master.location_id=location.location_id
AND bib_mfhd.bib_id=%s
AND mfhd_master.suppress_in_opac !='Y'
AND location.library_id=library.library_id
ORDER BY library.library_name"""
        cursor = connection.cursor()
        cursor.execute(query, [bib_data['BIB_ID']])
    holdings_list += _make_dict(cursor)
    for holding in holdings_list:
        holding.update({'ELECTRONIC_DATA': get_electronic_data(holding['MFHD_ID']),
                        'AVAILABILITY': get_availability(holding['MFHD_ID'])})
    return holdings_list


def get_electronic_data(mfhd_id):
    query = """
SELECT mfhd_master.mfhd_id,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','u')) as LINK856u,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','z')) as LINK856z,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','z')) as LINK852z,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','a')) as LINK852a,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','h')) as LINK852h,
       RTRIM(wrlcdb.GetAllTags(%s,'M','866',2)) as LINK866
FROM mfhd_master
WHERE mfhd_master.mfhd_id=%s"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id]*7)
    return _make_dict(cursor)[0]
       


def get_availability(mfhd_id):
    query = """
SELECT DISTINCT display_call_no, item_status_desc, item_status.item_status,
       permLocation.location_display_name as PermLocation,
       tempLocation.location_display_name as TempLocation,
       mfhd_item.item_enum, mfhd_item.chron, item.item_id, item_status_date,
       bib_master.bib_id
FROM bib_master
JOIN library ON library.library_id = bib_master.library_id
JOIN bib_text ON bib_text.bib_id = bib_master.bib_id
JOIN bib_mfhd ON bib_master.bib_id = bib_mfhd.bib_id
JOIN mfhd_master ON mfhd_master.mfhd_id = bib_mfhd.mfhd_id
JOIN mfhd_item on mfhd_item.mfhd_id = mfhd_master.mfhd_id
JOIN item ON item.item_id = mfhd_item.item_id
JOIN item_status ON item_status.item_id = item.item_id
JOIN item_status_type on item_status.item_status = item_status_type.item_status_type
JOIN location permLocation ON permLocation.location_id = item.perm_location
LEFT OUTER JOIN location tempLocation ON tempLocation.location_id = item.temp_location
WHERE bib_mfhd.mfhd_id = %s
ORDER BY PermLocation, TempLocation"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id])
    return _make_dict(cursor)[0]

def get_nongw_holdings_data(bib_data):
    bibids = [bib_data['BIB_ID']]
    if bib_data['ISBN']:
        bibids.append(get_related_bibids(isbn=bib_data['ISBN']))
    elif bib_data['ISSN']:
        bibids.append(get_related_bibids(issn=bib_data['ISSN']))
    elif bib_data['NETWORK_NUMBER']:
        bibids.append(get_related_bibids(oclc=bib_data['NETWORK_NUMBER']))
    holdings_list = []
    for bibid in bibids:
        query = """
SELECT bib_mfhd.bib_id, mfhd_master.mfhd_id, mfhd_master.location_id,
       mfhd_master.display_call_no, location.location_display_name,
       library.library_name
FROM bib_mfhd INNER JOIN mfhd_master ON bib_mfhd.mfhd_id = mfhd_master.mfhd_id,
     location, library
WHERE mfhd_master.location_id=location.location_id
AND bib_mfhd.bib_id=%s
AND mfhd_master.suppress_in_opac !='Y'
AND location.library_id=library.library_id
ORDER BY library.library_name"""
        cursor = connection.cursor()
        cursor.execute(query, [bib_data['BIB_ID']])
    holdings_list += _make_dict(cursor)
    for holding in holdings_list:
        holding.update({'ELECTRONIC_DATA': get_electronic_data(holding['MFHD_ID'])})
    return holdings_list

