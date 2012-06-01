from django.db import connection, transaction

def _make_dict(cursor):
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def get_bib_data(bibid):
    cursor = connection.cursor()
    query = """
SELECT bib_text.bib_id, title, author, edition, isbn, issn, network_number, 
       publisher, pub_place, imprint, bib_format, language, library_name, 
       RTRIM(wrlcdb.GetMarcField(%s,0,0,'856','','u',1))
FROM bib_text, bib_master, library
WHERE bib_text.bib_id=%s
AND bib_text.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'"""
    cursor.execute(query, [bibid, bibid])
    return _make_dict(cursor)[0]

def get_bibid_from_isbn(isbn):
    if len(isbn) == 13:
        code = 'ISB3'
    elif len(isbn) == 10:
        code = '020A'
    else:
        raise Exception
        #TODO:create more meaningful Exception
    cursor = connection.cursor()
    query = """
SELECT bib_index.bib_id, bib_master.library_id, 
       library_name, normal_heading, display_heading 
FROM bib_index, bib_master, library 
WHERE bib_index.index_code=%s 
AND bib_index.normal_heading like %s 
AND bib_index.bib_id=bib_master.bib_id 
AND bib_master.library_id=library.library_id""" 
#AND bib_master.library_id in (7,11,18,21)"""
    cursor.execute(query, [code,isbn])
    data = _make_dict(cursor)
    for item in data:
        if item['LIBRARY_ID'] in [7,11,18,21]:
            return item['BIB_ID']
    return data[0]['BIB_ID']


def get_bibid_from_issn(issn):
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
    for item in data:
        if item['LIBRARY_ID'] in [7,11,18,21]:
            return item['BIB_ID']
    return data[0]['BIB_ID']

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
    for item in data:
        if item['LIBRARY_ID'] in [7,11,18,21]:
            return item['BIB_ID']
    return data[0]['BIB_ID']
