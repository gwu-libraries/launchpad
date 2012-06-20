from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.utils import simplejson as json

from ui import voyager
from ui.sort import libsort, availsort, elecsort, libsort_bottom_only

NON_GW_SCHOOLS = ['GT', 'DA', 'GM', 'HU', 'HS', 'HL', 'AL', 'JB', 'HI']

def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'settings': settings,
        })

def item(request, bibid):
    bib = voyager.get_bib_data(bibid)
    if not bib:
        raise Http404
    holdings = voyager.get_holdings_data(bib)
    holdings = availsort(libsort(elecsort(holdings)))
    return render(request, 'item.html', {
        'bibid': bibid,
        'bib': bib, 
        'debug': settings.DEBUG,
        'holdings': holdings,
        'nongw': NON_GW_SCHOOLS,
        'link': bib.get('LINK', '')[9:]
        })

def _date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj

def item_json(request, bibid):
    bib_data = voyager.get_bib_data(bibid)
    bib_data['holdings'] = voyager.get_holdings_data(bib_data)
    return HttpResponse(json.dumps(bib_data, default=_date_handler, indent=2), 
        content_type='application/json')

def isbn(request, isbn):
    bibids = voyager.get_bibids_from_isbn(isbn)
    if bibids:
        return redirect('item', bibid=bibids[0])
    raise Http404

def issn(request, issn):
    bibids = voyager.get_bibids_from_issn(issn)
    if bibids:
        return redirect('item', bibid=bibids[0])
    raise Http404

def oclc(request, oclc):
    bibids = voyager.get_bibids_from_oclc(oclc)
    if bibids:
        return redirect('item', bibid=bibids[0])
    raise Http404

def error500(request):
    return render(request, '500.html', {
        'title': 'error',
        }, status=500)
