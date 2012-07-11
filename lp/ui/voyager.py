import pycountry 
from PyZ3950 import zoom

from django.conf import settings
from django.db import connection, transaction

from ui.templatetags.launchpad_extras import cjk_info
from ui.templatetags.launchpad_extras import clean_isbn, clean_oclc, clean_issn


GW_LIBRARY_IDS = [7, 11, 18, 21]


def _make_dict(cursor, first=False):
    desc = cursor.description
    mapped = [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]
    # strip string values of trailing whitespace
    for d in mapped:
        for k, v in d.items():
            try:
                d[k] = v.strip()
            except:
                pass
    if first:
        if len(mapped) > 0:
            return mapped[0]
        return {}
    return mapped


def get_added_authors(bib):
    """Starting with the main author entry, build up a list of all authors."""
    query = """
SELECT bib_index.display_heading AS author
FROM bib_index
WHERE bib_index.bib_id = %s
AND bib_index.index_code IN ('700H', '710H', '711H')
        """
    cursor = connection.cursor()
    cursor.execute(query, [bib['BIB_ID']])
    authors = []
    if bib['AUTHOR']:
        authors.append(bib['AUTHOR'])
    row = cursor.fetchone()
    while row:
        authors.append(row[0])
        row = cursor.fetchone()
    # trim whitespace
    if not authors:
        return []
    for i in range(len(authors)):
        author = authors[i].strip()
        if author.endswith('.'):
            author = author[:-1]
        authors[i] = author
    # remove duplicates
    #for author in authors:
    #    while authors.count(author) > 1:
    #        authors.remove(author)
    return authors

def get_bib_data(bibid):
    query = """
SELECT bib_text.bib_id, title, author, edition, isbn, issn, network_number AS OCLC, 
       publisher, pub_place, imprint, bib_format, language, library_name, 
       RTRIM(wrlcdb.GetMarcField(%s,0,0,'856','','u',1)) as LINK,
       wrlcdb.GetAllBibTag(%s, '880', 1) as CJK_INFO,
       RTRIM(wrlcdb.GetMarcField(%s,0,0,'856','','z',1)) as MESSAGE 
FROM bib_text, bib_master, library
WHERE bib_text.bib_id=%s
AND bib_text.bib_id=bib_master.bib_id
AND bib_master.library_id=library.library_id
AND bib_master.suppress_in_opac='N'"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid, bibid, bibid, bibid])
    bib = _make_dict(cursor, first=True)
    # if bib is empty, there's no match -- return immediately
    if not bib:
        return None
    # ensure the NETWORK_NUMBER is OCLC
    if not bib.get('OCLC','') or not _is_oclc(bib.get('OCLC','')):
        bib['OCLC'] = ''
    # get additional authors; main entry is AUTHOR, all are AUTHORS
    bib['AUTHORS'] = get_added_authors(bib)
    # split up the 880 (CJK) fields/values if available
    if bib.get('CJK_INFO', ''):
        bib['CJK_INFO'] = cjk_info(bib['CJK_INFO'])
    try:
        language = pycountry.languages.get(bibliographic=bib['LANGUAGE'])
        bib['LANGUAGE_DISPLAY'] = language.name
    except:
        bib['LANGUAGE_DISPLAY'] = ''
    # get all associated standard numbers (ISBN, ISSN, OCLC)
    bibids = set([bib['BIB_ID']])
    for num_type in ['isbn','issn','oclc']:
        if bib.get(num_type.upper(),''):
            norm_set, disp_set = set(), set()
            std_nums = get_related_std_nums(bib['BIB_ID'], num_type)
            norm, disp = zip(*std_nums)
            norm_set.update(norm)
            disp_set.update([num.strip() for num in disp])
            bib['NORMAL_%s_LIST' % num_type.upper()] = list(norm_set)
            bib['DISPLAY_%s_LIST' % num_type.upper()] = list(disp_set)
            # use std nums to get related bibs
            bibids.update(get_related_bibids(norm, num_type))
    bib['BIB_ID_LIST'] = list(bibids)
    return bib
    

def _is_oclc(num):
    if num.find('OCoLC') >= 0:
        return True
    if num.find('ocn') >= 0:
        return True
    if num.find('ocm') >= 0:
        return True
    return False

    

def get_primary_bibid(num, num_type):
    num = _normalize_num(num, num_type)
    query = """
SELECT bib_index.bib_id, bib_master.library_id, library.library_name
FROM bib_index, bib_master, library 
WHERE bib_index.index_code IN """
    query += '(%s)' % _in_clause(settings.INDEX_CODES[num_type])
    query += """
AND bib_index.normal_heading = %s
AND bib_index.bib_id=bib_master.bib_id 
AND bib_master.library_id=library.library_id"""
    cursor = connection.cursor()
    cursor.execute(query, [num])
    bibs = _make_dict(cursor)
    for bib in bibs:
        if bib['LIBRARY_NAME'] == settings.PREF_LIB:
            return bib['BIB_ID']
    return bibs[0]['BIB_ID'] if bibs else None



def _normalize_num(num, num_type):
    if num_type == 'isbn':
        return clean_isbn(num)
    elif num_type == 'issn':
        return num.replace('-',' ')
    elif num_type == 'oclc':
        return clean_oclc(num)
    return num


def get_related_bibids(num_list, num_type):
    query = """
SELECT DISTINCT bib_index.bib_id, bib_index.display_heading
FROM bib_index
WHERE bib_index.index_code IN """
    query += '(%s)' % _in_clause(settings.INDEX_CODES[num_type])
    query += """
AND bib_index.normal_heading IN (
    SELECT bib_index.normal_heading
    FROM bib_index
    WHERE bib_id IN (
        SELECT DISTINCT bib_index.bib_id
        FROM bib_index
        WHERE bib_index.index_code IN """
    query += '(%s)' % _in_clause(settings.INDEX_CODES[num_type])
    query += """
        AND bib_index.normal_heading IN """
    query += '(%s)' % _in_clause(num_list)
    query += """
        )
    )
ORDER BY bib_index.bib_id"""
    cursor = connection.cursor()
    cursor.execute(query, [])
    results = cursor.fetchall()
    if num_type == 'oclc':
        tmp = []
        for pair in results:
            if _is_oclc(pair[1]):
                tmp.append(pair[0])
        return tmp
    return [row[0] for row in results]


def get_related_std_nums(bibid, num_type):
    query = """
SELECT normal_heading, display_heading
FROM bib_index
WHERE bib_index.index_code IN """
    query += "(%s)" % _in_clause(settings.INDEX_CODES[num_type])
    query += """
AND bib_id = %s
ORDER BY bib_index.normal_heading"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    results = cursor.fetchall()
    if num_type == 'oclc':
        tmp = []
        for pair in results:
            if _is_oclc(pair[1]):
                tmp.append(pair)
        results = tmp
    return results


def get_holdings(bib_data):
    query = """
SELECT bib_mfhd.bib_id, mfhd_master.mfhd_id, mfhd_master.location_id,
       mfhd_master.display_call_no, location.location_display_name,
       library.library_name
FROM bib_mfhd INNER JOIN mfhd_master ON bib_mfhd.mfhd_id = mfhd_master.mfhd_id,
     location, library
WHERE mfhd_master.location_id=location.location_id
AND bib_mfhd.bib_id IN """
    query += "(%s)" % _in_clause(bib_data['BIB_ID_LIST'])
    query += """
AND mfhd_master.suppress_in_opac !='Y'
AND location.library_id=library.library_id
ORDER BY library.library_name"""
    cursor = connection.cursor()
    cursor.execute(query, [])
    holdings = _make_dict(cursor)
    for holding in holdings:
        if holding['LIBRARY_NAME'] == 'GM' or holding['LIBRARY_NAME'] == 'GT':
            holding.update({'ELECTRONIC_DATA': get_z3950_holdings(holding['BIB_ID'],holding['LIBRARY_NAME'],'bib','electronic'),
                            'AVAILABILITY': get_z3950_holdings(holding['BIB_ID'],holding['LIBRARY_NAME'],'bib','availability')})
            if holding['AVAILABILITY']['PERMLOCATION'] == ''  and holding['AVAILABILITY']['DISPLAY_CALL_NO'] == '' and holding['AVAILABILITY']['ITEM_STATUS_DESC'] == '':
                holding['REMOVE'] = True
            else:
                holding['LOCATION_DISPLAY_NAME'] = holding['AVAILABILITY']['PERMLOCATION'] if holding['AVAILABILITY']['PERMLOCATION'] else holding['LIBRARY_NAME'] 
                holding['DISPLAY_CALL_NO'] = holding['AVAILABILITY']['DISPLAY_CALL_NO']
        else:
            holding.update({'ELECTRONIC_DATA': get_electronic_data(holding['MFHD_ID']), 
                            'AVAILABILITY': get_availability(holding['MFHD_ID'])})
        holding.update({'ELIGIBLE': is_eligible(holding)})
        holding.update({'LIBRARY_HAS': get_library_has(holding)})
        holding['LIBRARY_FULL_NAME'] = settings.LIB_LOOKUP[holding['LIBRARY_NAME']]
        holding['TRIMMED_LOCATION_DISPLAY_NAME'] = trim_display_name(holding)    
    return [h for h in holdings if not h.get('REMOVE', False)]


def trim_display_name(holding):
    index = holding['LOCATION_DISPLAY_NAME'].find(':')
    if index > -1:
        return holding['LOCATION_DISPLAY_NAME'][index+2:]
    return holding['LOCATION_DISPLAY_NAME']
    
def _in_clause(items):
    return ','.join(["'"+str(item)+"'" for item in items])


def get_electronic_data(mfhd_id):
    query = """
SELECT mfhd_master.mfhd_id,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','u')) as LINK856u,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','z')) as LINK856z,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','z')) as LINK852z,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','a')) as LINK852a,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'852','h')) as LINK852h,
       RTRIM(wrlcdb.GetAllTags(%s,'M','866',2)) as LINK866,
       RTRIM(wrlcdb.GetMfHDsubfield(%s,'856','3')) as LINK8563
FROM mfhd_master
WHERE mfhd_master.mfhd_id=%s"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id]*8)
    return _make_dict(cursor, first=True)
       


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
ORDER BY PermLocation, TempLocation, item_status_date desc"""
    cursor = connection.cursor()
    cursor.execute(query, [mfhd_id])
    return _make_dict(cursor, first=True)

def _get_z3950_connection(server):
    conn = zoom.Connection(server['SERVER_ADDRESS'], server['SERVER_PORT'])
    conn.databaseName = server['DATABASE_NAME']
    conn.preferredRecordSyntax = server['PREFERRED_RECORD_SYNTAX']
    return conn

def _get_gt_holdings(query,query_type,bib):
    res = []
    results = []
    values = status = location = callno = url = msg = ''
    item_status = 0
    arow= {}
    try:
        conn = _get_z3950_connection(settings.Z3950_SERVERS['GT'])
    except:
        if query_type == 'availability':
            availability = get_z3950_availability_data(bib,'GT','','','',item_status,False)
            return availability
        elif query_type == 'electronic':
            electronic = get_z3950_electronic_data('GT','','',False)
            return electronic
    try:
        res = conn.search(query)
    except:
        if query_type == 'availability':
            availability = get_z3950_availability_data(bib,'GT','','','',item_status,False)
            return availability
        elif query_type == 'electronic':
            electronic = get_z3950_electronic_data('GT','','',False)
        return electronic
    for r in res:
        values = str(r)
        lines = values.split('\n')
        for line in lines:
            ind = line.find('856 4')
            if ind !=-1:
                ind = line.find('$u')
                ind1 = line.find(' ',ind)
                url = line[ind+2:]
                item_status = 1
                status = 'Not Charged'
                ind = line.find('$z')
                ind1 = line.find('$u',ind)
                msg = line[ind+2:ind1]

            ind = line.find('publicNote')
            if ind != -1:
                ind = line.find(':')
                status = str(line[ind+2:]).strip(" '")
            if status == 'AVAILABLE':
                status = 'Not Charged'
                item_status = 1
            elif status[0:4] == 'DUE':
                status = 'Charged'
                item_status = 0
                
            ind = line.find('callNumber')
            if ind != -1:
                ind = line.find(':')
                chars = len(line)
                callno = line[ind+3:chars-1]
            
            ind = line.find('localLocation')
            if ind != -1:
                ind = line.find(':')
                chars = len(line)
                location = 'GT: '+ line[ind+3:chars-1].strip(' .-')
        arow = {'status':status, 'location':location, 'callno':callno,'LINK':url,'MESSAGE':msg}
        results.append(arow)
    conn.close()
    if query_type == 'availability':
        availability = get_z3950_availability_data(bib,'GT',location,status,callno,item_status)
        return availability
    elif query_type == 'electronic':
        electronic = get_z3950_electronic_data('GT',url,msg)
        return electronic



def get_z3950_holdings(id, school, id_type, query_type):
    holding_found = False
    if school == 'GM':
        results = []
        availability = {}
        electronic = {}
        item_status = 0
        values = status = location = callno = url = msg = ''
        arow= {}
        bib = get_gmbib_from_gwbib(id)
        try:
            conn = _get_z3950_connection(settings.Z3950_SERVERS['GM'])
        except:
            if query_type == 'availability':
                availability = get_z3950_availability_data(bib,'GM','','','',item_status,False)
                return availability
            elif query_type == 'electronic':
                electronic = get_z3950_electronic_data('GM','','', False)
                return electronic
     
        if len(bib) > 0:
            correctbib=''
            query = None
            for bibid in bib:
                ind = bibid.find(' ')
                if ind != -1:
                    continue
                correctbib = bibid
                break
            try:
                query = zoom.Query('PQF', '@attr 1=12 %s' % correctbib.encode('utf-8'))
            except:
                if query_type == 'availability':
                    availability = get_z3950_availability_data(correctbib,'GM','','','',item_status,False)
                    return availability
                elif query_type == 'electronic':
                    electronic = get_z3950_electronic_data('GM','','', False)
                    return electronic
    
            res = conn.search(query)
            for r in res:
                values = str(r)
                lines = values.split('\n')
                for line in lines:
                    ind = line.find('856 4')
                    if ind !=-1:
                        ind = line.find('$h')
                        ind1 = line.find(' ',ind)
                        url = line[ind:ind1]
                        location = 'GM: online'
                        item_status = 1
                        status = 'Not Charged'
                        ind = line.find('$z')
                        ind1 = line.find('$u',ind)
                        msg = line[ind+2:ind1]
                        
                    ind = line.find('availableNow')
                    if ind != -1:
                        ind = line.find(':')
                        status = line[ind+2:]
                        if status == 'True':
                            status = 'Not Charged'
                            item_status = 1
                        elif status == 'False':
                            status = 'Charged'
                            item_status = 0
                            
                    ind = line.find('callNumber')
                    if ind != -1:
                        ind = line.find(':')
                        ind1 = line.find('\\')
                        callno = line[ind+3:ind1]
                    
                    ind = line.find('localLocation')
                    if ind!= -1:
                        ind = line.find(':')
                        ind1 = line.find('\\')
                        location = 'GM: ' + line[ind+3:ind1].strip(' -.')
                        holding_found = True
                if holding_found == True:
                    arow = {'STATUS':status, 'LOCATION':location, 'CALLNO':callno,'LINK':url,'MESSAGE':msg}
                    results.append(arow)
                holding_found = False
            conn.close()
            if query_type == 'availability':
                availability = get_z3950_availability_data(bib,'GM',location,status,callno,item_status)
                return availability
            elif query_type == 'electronic':
                electronic = get_z3950_electronic_data('GM',url,msg)
                return electronic
        else:
            res = get_bib_data(id)
            if len(res)>0:
                ind= res['LINK'].find('$u')
                url = res['LINK'][ind+2:]
                ind = res['MESSAGE'].find('$z')
                msg = res['MESSAGE'][ind+2:]
                item_status = 1
                status = 'Not Charged'
                results.append({'STATUS':'', 'LOCATION':'', 'CALLNO':'','LINK':url,'MESSAGE':msg})
            if query_type == 'availability':
                availability = get_z3950_availability_data(bib,'GM',location,status,callno,item_status)
                return availability
            elif query_type == 'electronic':
                electronic = get_z3950_electronic_data('GM',url,msg)
                return electronic
    elif school=='GT':
        if id_type =='bib':
            bib = get_gtbib_from_gwbib(id)
            query = zoom.Query('PQF', '@attr 1=12 %s' % bib)
        if id_type == 'isbn':
            query = zoom.Query('PQF', '@attr 1=7 %s' % id)
        elif id_type == 'issn':
            query = zoom.Query('PQF', '@attr 1=8 %s' % id)
        elif id_type == 'oclc':
            query = zoom.Query('PQF', '@attr 1=1007 %s' % id)
        return _get_gt_holdings(query, query_type, bib)


def get_gmbib_from_gwbib(bibid):
    query = """
SELECT bib_index.normal_heading
FROM bib_index 
WHERE bib_index.bib_id = %s
AND bib_index.index_code ='035A'
AND bib_index.normal_heading=bib_index.display_heading"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    results = _make_dict(cursor)
    return [row['NORMAL_HEADING'] for row in results]


def get_gtbib_from_gwbib(bibid):
    query = """
SELECT LOWER(SUBSTR(bib_index.normal_heading,0,LENGTH(bib_index.normal_heading)-1))  \"NORMAL_HEADING\"
FROM bib_index 
WHERE bib_index.bib_id = %s
AND bib_index.index_code ='907A'"""
    cursor = connection.cursor()
    cursor.execute(query, [bibid])
    results = _make_dict(cursor)
    return [row['NORMAL_HEADING'] for row in results]


def get_wrlcbib_from_gtbib(gtbibid):
    query = """
SELECT bib_index.bib_id
FROM bib_index
WHERE bib_index.normal_heading = %s
AND bib_index.index_code = '907A'"""
    cursor = connection.cursor()
    cursor.execute(query, [gtbibid.upper()])
    results = _make_dict(cursor)
    return results[0]['BIB_ID'] if results else None


def get_wrlcbib_from_gmbib(gmbibid):
    query = """
SELECT bib_index.bib_id
FROM bib_index
WHERE bib_index.index_code = '035A'
AND bib_index.normal_heading=bib_index.display_heading
AND bib_index.normal_heading = %s"""
    cursor = connection.cursor()
    cursor.execute(query, [gmbibid])
    results = _make_dict(cursor)
    return results[0]['BIB_ID'] if results else None


def is_eligible(holding):
    perm_loc = ''
    temp_loc = ''
    status = ''
    if holding['AVAILABILITY']:
        if holding['AVAILABILITY']['PERMLOCATION']:
            perm_loc = holding['AVAILABILITY']['PERMLOCATION'].upper()
        if holding['AVAILABILITY']['TEMPLOCATION']:
            temp_loc = holding['AVAILABILITY']['TEMPLOCATION'].upper()
        if holding['AVAILABILITY']['ITEM_STATUS_DESC']:
            status = holding['AVAILABILITY']['ITEM_STATUS_DESC'].upper()
    else:
        return False
    if holding['LIBRARY_NAME'] == 'GM' and 'Law Library' in holding['AVAILABILITY']['PERMLOCATION']:
        return False
    if holding['LIBRARY_NAME'] in settings.INELIGIBLE_LIBRARIES:
        return False
    if 'WRLC' in temp_loc or 'WRLC' in perm_loc:
        return True
    for loc in settings.INELIGIBLE_PERM_LOCS:
        if loc in perm_loc:
            return False
    for loc in settings.INELIGIBLE_TEMP_LOCS:
        if loc in temp_loc:
            return False
    for stat in settings.INELIGIBLE_STATUS:
        if stat == status:
            return False
    return True

def get_z3950_availability_data(bib,school,location,status,callno,item_status,found = True):
    availability = {}
    catlink = ''
    if school == 'GT':
        catlink = 'Click on the following link to get the information about this item from GeorgeTown Catalog <br>'+ 'http://catalog.library.georgetown.edu/record='+'b'+bib[0]+'~S4'
    else:
        catlink = 'Click on the following link to get the information about this item from George Mason Catalog <br>'+ 'http://magik.gmu.edu/cgi-bin/Pwebrecon.cgi?BBID='+bib[0]
    if found :
        availability = { 'BIB_ID' : bib,
                     'CHRON' : None,
                     'DISPLAY_CALL_NO' : callno,
                     'ITEM_ENUM' : None,
                     'ITEM_ID' : None,
                     'ITEM_STATUS' : item_status,
                     'ITEM_STATUS_DATE' : '',
                     'ITEM_STATUS_DESC' : status,
                     'PERMLOCATION' : location,
                     'TEMPLOCATION' : None}
    else:
        availability = { 'BIB_ID' : bib,
                     'CHRON' : None,
                     'DISPLAY_CALL_NO' : callno,
                     'ITEM_ENUM' : None,
                     'ITEM_ID' : None,
                     'ITEM_STATUS' : item_status,
                     'ITEM_STATUS_DATE' : '',
                     'ITEM_STATUS_DESC' : status,
                     'PERMLOCATION' : catlink,
                     'TEMPLOCATION' : None}

    return availability

def get_z3950_electronic_data(school,link,message,Found = True):
    link852h = ''
    if link != '': 
        link852h = school+': Electronic Resource'
    electronic = {'LINK852A' : None ,
          'LINK852H' : link852h ,
          'LINK856Z' : message , 
          'LINK856U' : link ,
          'LINK866' : None,
          'MFHD_ID' : None}
    return electronic


def get_library_has(holding):
    if holding['ELECTRONIC_DATA'] and holding['ELECTRONIC_DATA']['LINK866']:
        lib_has =  holding['ELECTRONIC_DATA']['LINK866'].split('//')
        for i in range(len(lib_has)):
            line = lib_has[i]
            while line.find('$') > -1:
                line = line[line.index('$')+2:]
            lib_has[i] = line
        return lib_has
    else:
        return []
