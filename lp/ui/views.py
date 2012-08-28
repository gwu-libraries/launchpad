import urllib

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.utils import simplejson as json
from django.views.decorators.cache import cache_page

from ui import voyager, apis, models
from ui.catalogs import wrlc
from ui.sort import libsort, availsort, elecsort, splitsort


def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
        })


def _openurl_dict(params):
    """Split openurl params into a useful structure"""
    p = {}
    for k, v in dict(params).items():
        p[k] = ','.join(v)
    d = {'params':  p}
    d['query_string'] = '&'.join(['%s=%s' % (k, v) for k, v
        in params.items()])
    d['query_string_encoded'] = urllib.urlencode(params)
    return d


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item(request, bibid, expand=True):
    bib = wrlc.bib(bibid)
    if not bib:
        return render(request, '404.html', {'num': bibid,
            'num_type': 'BIB ID'}, status=404)
    bib.openurl = _openurl_dict(request.GET)
    if expand:
        bib.related_stdnums = wrlc.related_stdnums(bib.bibid)
        related_bibids = wrlc.related_bibids(bib.related_stdnums)
        bib.related_bibids = [b['bibid'] for b in related_bibids]
        #replace MARC with ours
        if bib.libcode != settings.PREF_LIB:
            for b in related_bibids:
                if b['libcode'] == settings.PREF_LIB:
                    bib.marc = str(wrlc.bibblob(b['bibid'])
                    break
    bib.holdings = wrlc.holdings(bib.bibids)
    for holding in bib.holdings:
        if holding.libcode in settings.Z3950_SERVERS:
            continue
            #TODO: add z39.50 item lookup 
        else:
            holding.items = wrlc.items(holding.mfhdid)
    #TODO: add sorting
    return render(request, 'item.html', {
        'bibid': bibid,
        'bib': bib,
        'debug': settings.DEBUG,
        'title_chars': settings.TITLE_CHARS,
        'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
        'link_resolver': settings.LINK_RESOLVER,
        'enable_humans': settings.ENABLE_HUMANS,
        })


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item_bib(request, bibid):
    bib = voyager.get_bib_data(bibid, expand_ids=False)
    if not bib:
        return render(request, '404.html', {'num': bibid,
            'num_type': 'BIB ID'}, status=404)
    # Don't bother expanding bibids; we don't need correct holdings
    return render(request, 'item.html', {
        'bibid': bibid,
        'bib': bib,
        'debug': settings.DEBUG,
        'title_chars': settings.TITLE_CHARS,
        'link': bib.get('LINK', '')[9:],
        'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
        'link_resolver': settings.LINK_RESOLVER,
        'enable_humans': settings.ENABLE_HUMANS,
        })


def _date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item_json(request, bibid):
    bib_data = voyager.get_bib_data(bibid)
    bib_data['holdings'] = voyager.get_holdings(bib_data)
    bib_data['openurl'] = _openurl_dict(request.GET)
    return HttpResponse(json.dumps(bib_data, default=_date_handler,
        indent=2), content_type='application/json')


def non_wrlc_item(request, num, num_type):
    bib = apis.get_bib_data(num=num, num_type=num_type)
    if not bib:
        return render(request, '404.html', {'num': num,
            'num_type': num_type.upper()}, status=404)
    bib['ILLIAD_LINK'] = voyager.get_illiad_link(bib)
    return render(request, 'item.html', {
       'bibid': '',
       'bib': bib,
       'debug': settings.DEBUG,
       'title_chars': settings.TITLE_CHARS,
       'holdings': [],
       'link': '',
       'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
       'link_resolver': settings.LINK_RESOLVER,
       })


def gtitem(request, gtbibid):
    bibid = voyager.get_wrlcbib_from_gtbib(gtbibid)
    if bibid:
        return redirect('item', bibid=bibid)
    return render(request, '404.html', {'num': gtbibid,
        'num_type': 'Georgetown BIB ID'}, status=404)


def gtitem_json(request, gtbibid):
    bibid = voyager.get_wrlcbib_from_gtbib(gtbibid)
    if bibid:
        return redirect('item_json', bibid=bibid)
    raise Http404


def gmitem(request, gmbibid):
    bibid = voyager.get_wrlcbib_from_gmbib(gmbibid)
    if bibid:
        return redirect('item', bibid=bibid)
    return render(request, '404.html', {'num': gmbibid,
        'num_type': 'George Mason BIB ID'}, status=404)


def gmitem_json(request, gmbibid):
    bibid = voyager.get_wrlcbib_from_gmbib(gmbibid)
    if bibid:
        return redirect('item_json', bibid=bibid)
    raise Http404


def isbn(request, isbn):
    bibid = voyager.get_primary_bibid(num=isbn, num_type='isbn')
    openurl = _openurl_dict(request.GET)
    if bibid:
        url = '%s?%s' % (reverse('item', args=[bibid]),
            openurl['query_string_encoded'])
        return redirect(url)
    return non_wrlc_item(request, num=isbn, num_type='isbn')


def issn(request, issn):
    bibid = voyager.get_primary_bibid(num=issn, num_type='issn')
    openurl = _openurl_dict(request.GET)
    if bibid:
        url = '%s?%s' % (reverse('item', args=[bibid]),
            openurl['query_string_encoded'])
        return redirect(url)
    return non_wrlc_item(request, num=issn, num_type='issn')


def oclc(request, oclc):
    bibid = voyager.get_primary_bibid(num=oclc, num_type='oclc')
    openurl = _openurl_dict(request.GET)
    if bibid:
        url = '%s?%s' % (reverse('item', args=[bibid]),
            openurl['query_string_encoded'])
        return redirect(url)
    return render(request, '404.html', {'num': oclc,
        'num_type': 'OCLC number'}, status=404)


def error500(request):
    return render(request, '500.html', {
        'title': 'error',
        'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
        }, status=500)


def robots(request):
    return render(request, 'robots.txt', {
        'enable_sitemaps': settings.ENABLE_SITEMAPS,
        'sitemaps_base_url': settings.SITEMAPS_BASE_URL,
        }, content_type='text/plain')


def humans(request):
    return render(request, 'humans.txt', {}, content_type='text/plain')
