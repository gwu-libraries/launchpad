from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect
from ui import voyager

def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'settings': settings,
        })

def item(request, bibid):
    nonGwSchools = ['GT' , 'DA', 'GM', 'HU', 'HS', 'HL', 'AL', 'JB', 'HI']
    bib_data = voyager.get_bib_data(bibid)
    if bib_data['LIBRARY_NAME'] in nonGwSchools:
    	holdings_data = voyager.get_nongw_holdings_data(bib_data)
    else:
	holdings_data = voyager.get_holdings_data(bib_data)
    return render(request, 'item.html', {'bib_data':bib_data, 'holdings_data':holdings_data,'nongw':nonGwSchools,'link':bib_data['LINK'][9:]})

def isbn(request, isbn):
    bibid = voyager.get_bibid_from_isbn(isbn)
    return redirect('item', bibid=bibid)

def issn(request, issn):
    bibid = voyager.get_bibid_from_issn(issn)
    return redirect('item', bibid=bibid)

def oclc(request, oclc):
    bibid = voyager.get_bibid_from_oclc(oclc)
    return redirect('item', bibid=bibid)

def dump(request, bibid):
    bib_data = voyager.get_bib_data(bibid)
    holdings_data = voyager.get_holdings_data(bib_data)
    output = 'BIBLIOGRAPHIC DATA\n\n%s\n\n\nHOLDINGS DATA\n\n%s' % (bib_data, holdings_data)
    return HttpResponse(output, content_type='application/json')
