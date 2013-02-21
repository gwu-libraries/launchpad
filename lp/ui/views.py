from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_page

from ui import utils, voyager, apis
from ui.catalogs import wrlc


def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
        'settings': settings,
        })


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item(request, bibid, expand=True):
    recset = wrlc.build_record_set(bibid,
        openurl=utils.openurl_dict(request.GET))
    if not recset:
        return render(request, '404.html', {'num': bibid,
            'num_type': 'BIB ID'}, status=404)
    recset.schoolsort()
    return render(request, 'item.html', {
        'bibid': bibid,
        'recordset': recset,
        'settings': settings,
        })


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item_json(request, bibid):
    recset = wrlc.build_record_set(bibid,
        openurl=utils.openurl_dict(request.GET))
    if not recset:
        return HttpResponse('{}', content_type='application_json',
            status_code=404)
    return HttpResponse(recset.dump_json(), content_type='application/json')


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
    bibid = wrlc.bibid(num=isbn, num_type='isbn')
    if bibid:
        openurl = utils.openurl_dict(request.GET)
        url = '%s?%s' % (reverse('item', args=[bibid]),
            openurl['query_string_encoded'])
        return redirect(url)
    return non_wrlc_item(request, num=isbn, num_type='isbn')


def issn(request, issn):
    bibid = wrlc.bibid(num=issn, num_type='issn')
    if bibid:
        openurl = utils.openurl_dict(request.GET)
        url = '%s?%s' % (reverse('item', args=[bibid]),
            openurl['query_string_encoded'])
        return redirect(url)
    return non_wrlc_item(request, num=issn, num_type='issn')


def oclc(request, oclc):
    bibid = wrlc.bibid(num=oclc, num_type='oclc')
    if bibid:
        openurl = utils.openurl_dict(request.GET)
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
