

def _dictfetchall(cursor):
    desc = cursor.description
    return dict(zip([col[0] for col in desc], cursor.fetchone()))

def get_bib_data(bibid):
    from django.db import connection, transaction
    cursor = connection.cursor()
    cursor.execute("SELECT bib_text.bib_id, title, author, edition, isbn, issn, network_number,publisher, pub_place, imprint, bib_format, language, library_name, RTRIM(wrlcdb.GetMarcField(%s,0,0,'856','','u',1)) FROM bib_text, bib_master, library WHERE bib_text.bib_id=%s AND bib_text.bib_id=bib_master.bib_id AND bib_master.library_id=library.library_id AND bib_master.suppress_in_opac='N'", [bibid, bibid])
    return _dictfetchall(cursor)
