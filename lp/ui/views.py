from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import simplejson as json

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
    return render(request, 'item.html', {
        'bibid': bibid,
        'bib_data': bib_data, 
        'debug': settings.DEBUG,
        'holdings_data': holdings_data,
        'nongw': nonGwSchools,
        'link':bib_data['LINK'][9:]
        })

def _date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj

def item_json(request, bibid):
    bib_data = voyager.get_bib_data(bibid)
    bib_data['holdings'] = voyager.get_holdings_data(bib_data)
    return HttpResponse(json.dumps(bib_data, default=_date_handler), 
        content_type='application/json')

def isbn(request, isbn):
    bibid = voyager.get_bibid_from_isbn(isbn)
    return redirect('item', bibid=bibid)

def issn(request, issn):
    bibid = voyager.get_bibid_from_issn(issn)
    return redirect('item', bibid=bibid)

def oclc(request, oclc):
    bibid = voyager.get_bibid_from_oclc(oclc)
    return redirect('item', bibid=bibid)

def error500(request):
    return render(request, '500.html', {
        'title': 'error',
        }, status=500)
