from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.utils import simplejson as json
from django.views.decorators.cache import cache_page

from ui import voyager
from ui.sort import libsort, availsort, elecsort, splitsort

NON_GW_SCHOOLS = ['GT', 'DA', 'GM', 'HU', 'HS', 'HL', 'AL', 'JB', 'HI']

def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'settings': settings,
        })

@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item(request, bibid):
    bib = voyager.get_bib_data(bibid)
    if not bib:
        raise Http404
    holdings = voyager.get_holdings(bib)
    ours, theirs, shared = splitsort(holdings)
    holdings = availsort(elecsort(ours)) + availsort(elecsort(shared)) + libsort(elecsort(availsort(theirs), rev=True))
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

@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item_json(request, bibid):
    bib_data = voyager.get_bib_data(bibid)
    bib_data['holdings'] = voyager.get_holdings(bib_data)
    return HttpResponse(json.dumps(bib_data, default=_date_handler, indent=2), 
        content_type='application/json')


def gtitem(request, gtbibid):
    bibid = voyager.get_wrlcbib_from_gtbib(gtbibid)
    if bibid:
        return redirect('item', bibid=bibid)
    raise Http404


def gtitem_json(request, gtbibid):
    bibid = voyager.get_wrlcbib_from_gtbib(gtbibid)
    if bibid:
        return redirect('item_json', bibid=bibid)
    raise Http404


def isbn(request, isbn):
    bibid = voyager.get_primary_bibid(num=isbn, num_type='isbn')
    if bibid:
        return redirect('item', bibid=bibid)
    raise Http404

def issn(request, issn):
    bibid = voyager.get_primary_bibid(num=issn, num_type='issn')
    if bibid:
        return redirect('item', bibid=bibid)
    raise Http404

def oclc(request, oclc):
    bibid = voyager.get_primary_bibid(num=oclc, num_type='oclc')
    if bibid:
        return redirect('item', bibid=bibid)
    raise Http404

def error500(request):
    return render(request, '500.html', {
        'title': 'error',
        }, status=500)

