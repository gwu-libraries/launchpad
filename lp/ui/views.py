import logging

import bibjsontools
from urlparse import urlparse

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.utils import DatabaseError
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.utils import simplejson as json
from django.views.decorators.cache import cache_page

from ui import voyager, apis, marc
from ui.sort import libsort, availsort, elecsort, templocsort, \
    splitsort, enumsort, callnumsort, strip_bad_holdings, holdsort


logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
    })


def _openurl_dict(request):
    params = request.GET
    """Split openurl params into a useful structure"""
    p = {}
    for k, v in dict(params).items():
        p[k] = ','.join(v)
    d = {'params':  p}
    d['query_string'] = '&'.join(['%s=%s' % (k, v) for k, v
                        in params.items()])
    d['query_string_encoded'] = request.META.get('QUERY_STRING', '')
    return d


def citation_json(request):
    url = request.META.get('QUERY_STRING', '')
    return bibjsontools.from_openurl(url) if url else None


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item(request, bibid):
    bib = None
    try:
        bib = voyager.get_bib_data(bibid)
        if not bib:
            return render(request, '404.html', {'num': bibid,
                          'num_type': 'BIB ID'}, status=404)
        bib['openurl'] = _openurl_dict(request)
        bib['citation_json'] = citation_json(request)
        # Ensure bib data is ours if possible
        if not bib['LIBRARY_NAME'] == settings.PREF_LIB:
            for alt_bib in bib['BIB_ID_LIST']:
                if alt_bib['LIBRARY_NAME'] == settings.PREF_LIB:
                    return item(request, alt_bib['BIB_ID'])
        holdings = voyager.get_holdings(bib)
        if holdings:
            holdings = strip_bad_holdings(holdings)
            show_wrlc_link = display_wrlc_link(holdings)
            ours, theirs, shared = splitsort(callnumsort(enumsort(holdings)))
            holdings = elecsort(holdsort(templocsort(availsort(ours)))) \
                + elecsort(holdsort(templocsort(availsort(shared)))) \
                + libsort(elecsort(holdsort(templocsort(availsort(theirs))),
                                   rev=True))
        else:
            show_wrlc_link = False

        # extract details for easy display in a separate tab
        details = []
        for name, display_name, specs in marc.mapping:
            if name in bib and len(bib[name]) > 0:
                details.append((display_name, bib[name]))

        return render(request, 'item.html', {
            'bibid': bibid,
            'bib': bib,
            'holdings': holdings,
            'link': bib.get('LINK', [])[9:],
            'show_wrlc_link': show_wrlc_link,
            'non_wrlc_item': False,
            'details': details,
        })
    except:
        logger.exception('unable to render bibid: %s' % bibid)
        return error500(request)


def display_wrlc_link(holdings):
    x = 0
    for holding in holdings:
        if holding.get('MFHD_DATA', None):
            for marc856 in holding['MFHD_DATA']['marc856list']:
                components = urlparse(marc856['u'])
                if components.scheme and components.netloc:
                    x = x + 1
    if x == len(holdings):
        return False
    else:
        return True


def _date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item_json(request, bibid, z3950='False', school=None):
    try:
        bib_data = voyager.get_bib_data(bibid)
        if not bib_data:
            return HttpResponse('{}', content_type='application/json',
                                status=404)
        bib_data['openurl'] = _openurl_dict(request)
        bib_data['holdings'] = voyager.get_holdings(bib_data)
        bib_data['openurl'] = _openurl_dict(request)
        bib_data['citation_json'] = citation_json(request)
        bib_encoded = unicode_data(bib_data)
        return HttpResponse(json.dumps(bib_encoded, default=_date_handler,
                            indent=2), content_type='application/json')
    except DatabaseError:
        logger.exception('unable to render bibid json: %s' % bibid)
        return error500(request)


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def item_marc(request, bibid):
    rec = voyager.get_marc_blob(bibid)
    if not rec:
        return HttpResponse('{}', content_type='application/json',
                            status=404)
    return HttpResponse(rec.as_json(indent=2), content_type='application/json')


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def non_wrlc_item(request, num, num_type):
    bib = apis.get_bib_data(num=num, num_type=num_type)
    if not bib:
        return render(request, '404.html', {'num': num,
                      'num_type': num_type.upper()}, status=404)
    bib['openurl'] = _openurl_dict(request)
    bib['citation_json'] = citation_json(request)
    bib['ILLIAD_LINK'] = voyager.get_illiad_link(bib)
    bib['MICRODATA_TYPE'] = voyager.get_microdata_type(bib)
    holdings = []
    # get free electronic book link from open library
    for numformat in ('LCCN', 'ISBN', 'OCLC'):
        if bib.get(numformat):
            if numformat == 'OCLC':
                num = filter(lambda x: x.isdigit(), bib[numformat])
            else:
                num = bib[numformat]
            openlibhold = apis.openlibrary(num, numformat)
            if openlibhold:
                holdings.append(openlibhold)
                break
    return render(request, 'item.html', {
                  'bibid': '',
                  'bib': bib,
                  'non_gw': True,
                  'holdings': holdings,
                  'link': '',
                  })


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def gtitem(request, gtbibid):
    try:
        bibid = voyager.get_wrlcbib_from_gtbib(gtbibid)
        if bibid:
            return redirect('item', bibid=bibid)
        else:
            bib = voyager.get_z3950_bib_data(gtbibid[:-1], 'GT')
            if bib is None:
                return render(request, '404.html', {'num': gtbibid,
                              'num_type': 'BIB ID'}, status=404)
            bib['openurl'] = _openurl_dict(request)
            bib['citation_json'] = citation_json(request)
            # Ensure bib data is ours if possible
            if not bib['LIBRARY_NAME'] == settings.PREF_LIB:
                for alt_bib in bib['BIB_ID_LIST']:
                    if alt_bib['LIBRARY_NAME'] == settings.PREF_LIB:
                        return item(request, alt_bib['BIB_ID'])
            holdings = voyager.get_holdings(bib, 'GT', False)
            if holdings:
                holdings = strip_bad_holdings(holdings)
                show_wrlc_link = False
                ours, theirs, shared = splitsort(callnumsort(enumsort(
                    holdings)))
                holdings = elecsort(availsort(ours)) \
                    + elecsort(availsort(shared)) \
                    + libsort(elecsort(availsort(theirs), rev=True))
            return render(request, 'item.html', {
                'bibid': bibid,
                'bib': bib,
                'holdings': holdings,
                'link': bib.get('LINK', [])[9:],
                'show_wrlc_link': show_wrlc_link,
                'non_wrlc_item': True
            })
        return render(request, '404.html', {'num': gtbibid,
                      'num_type': 'Georgetown BIB ID'}, status=404)
    except DatabaseError:
        logger.exception('unable to render gtbibid: %s' % gtbibid)
        return error500(request)


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def gtitem_json(request, gtbibid):
    try:
        bibid = voyager.get_wrlcbib_from_gtbib(gtbibid)
        if bibid:
            return redirect('item_json', bibid=bibid)
        else:
            bib_data = voyager.get_z3950_bib_data('b' + gtbibid[:-1], 'GT')
            if not bib_data:
                return HttpResponse('{}', content_type='application/json',
                                    status=404)
            bib_data['holdings'] = voyager.get_holdings(bib_data, 'GT', False)
            bib_data['openurl'] = _openurl_dict(request)
            bib_data['citation_json'] = citation_json(request)
            bib_encoded = unicode_data(bib_data)
            return HttpResponse(json.dumps(bib_encoded, default=_date_handler,
                                           indent=2),
                                content_type='application/json')
        raise Http404
    except DatabaseError:
        logger.exception('unable to render gtbibid json: %s' % gtbibid)
        return error500(request)


def unicode_data(bib_data):
    bib_encoded = {}
    for k, v in bib_data.iteritems():
        if isinstance(v, basestring):
            if not isinstance(v, unicode):
                bib_encoded[k] = unicode(v, 'iso-8859-1')
            else:
                bib_encoded[k] = v
        elif isinstance(v, dict):
            bib_encoded[k] = unicode_data(v)
        elif isinstance(v, list):
            rows = []
            row = None
            for item in v:
                if isinstance(item, dict):
                    row = unicode_data(item)
                elif isinstance(item, basestring):
                    if not isinstance(item, unicode):
                        row = unicode(item, 'iso-8859-1')
                    else:
                        row = item
                rows.append(row)
            bib_encoded[k] = rows
        else:
            bib_encoded[k] = v
    return bib_encoded


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def gmitem(request, gmbibid):
    try:
        bibid = voyager.get_wrlcbib_from_gmbib(gmbibid)
        if bibid:
            return redirect('item', bibid=bibid)
        else:
            bib = voyager.get_z3950_bib_data(gmbibid, 'GM')
            if not bib:
                return render(request, '404.html', {'num': gmbibid,
                              'num_type': 'BIB ID'}, status=404)
            bib['openurl'] = _openurl_dict(request)
            bib['citation_json'] = citation_json(request)
            # Ensure bib data is ours if possible
            if not bib['LIBRARY_NAME'] == settings.PREF_LIB:
                for alt_bib in bib['BIB_ID_LIST']:
                    if alt_bib['LIBRARY_NAME'] == settings.PREF_LIB:
                        return item(request, alt_bib['BIB_ID'])
            holdings = voyager.get_holdings(bib, 'GM', False)
            if holdings:
                holdings = strip_bad_holdings(holdings)
                show_wrlc_link = False
                ours, theirs, shared = splitsort(callnumsort(enumsort(
                    holdings)))
                holdings = elecsort(availsort(ours)) \
                    + elecsort(availsort(shared)) \
                    + libsort(elecsort(availsort(theirs), rev=True))
            return render(request, 'item.html', {
                'bibid': bibid,
                'bib': bib,
                'holdings': holdings,
                'link': bib.get('LINK', [])[9:],
                'show_wrlc_link': show_wrlc_link,
                'non_wrlc_item': True
            })
        return render(request, '404.html', {'num': gmbibid,
                      'num_type': 'George Mason BIB ID'}, status=404)
    except DatabaseError:
        logger.exception('unable to render gmbibid: %s' % gmbibid)
        return error500(request)


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def gmitem_json(request, gmbibid):
    try:
        bibid = voyager.get_wrlcbib_from_gmbib(gmbibid)
        if bibid:
            return redirect('item_json', bibid=bibid)
        else:
            bib_data = voyager.get_z3950_bib_data(gmbibid, 'GM')
            if not bib_data:
                return HttpResponse('{}', content_type='application/json',
                                    status=404)
            bib_data['holdings'] = voyager.get_holdings(bib_data, 'GM', False)
            bib_data['openurl'] = _openurl_dict(request)
            bib_data['citation_json'] = citation_json(request)
            bib_encoded = unicode_data(bib_data)
            return HttpResponse(json.dumps(bib_encoded, default=_date_handler,
                                indent=2), content_type='application/json')
        raise Http404
    except DatabaseError:
        logger.exception('unable to render gmbibid json: %s' % gmbibid)
        return error500(request)


def isbn(request, isbn):
    try:
        bibid = voyager.get_primary_bibid(num=isbn, num_type='isbn')
        openurl = _openurl_dict(request)
        if bibid:
            url = '%s?%s' % (reverse('item', args=[bibid]),
                             openurl['query_string_encoded'])
            return redirect(url)
        return non_wrlc_item(request, num=isbn, num_type='isbn')
    except DatabaseError:
        logger.exception('unable to render isbn: %s' % isbn)
        return error500(request)


def issn(request, issn):
    try:
        bibid = voyager.get_primary_bibid(num=issn, num_type='issn')
        openurl = _openurl_dict(request)
        if bibid:
            url = '%s?%s' % (reverse('item', args=[bibid]),
                             openurl['query_string_encoded'])
            return redirect(url)
        return non_wrlc_item(request, num=issn, num_type='issn')
    except DatabaseError:
        logger.exception('unable to render issn: %s' % issn)
        return error500(request)


def oclc(request, oclc):
    try:
        bibid = voyager.get_primary_bibid(num=oclc, num_type='oclc')
    except DatabaseError:
        return redirect('error503')
    openurl = _openurl_dict(request)
    if bibid:
        url = '%s?%s' % (reverse('item', args=[bibid]),
                         openurl['query_string_encoded'])
        return redirect(url)
    return render(request, '404.html', {'num': oclc,
                  'num_type': 'OCLC number'}, status=404)


def error500(request):
    return render(request, '500.html', {
        'title': 'Sorry, system error',
    }, status=500)


def error503(request):
    return render(request, '503.html', {
        'title': 'Database Undergoing Maintenance',
    }, status=503)


def robots(request):
    return render(request, 'robots.txt', {
        'enable_sitemaps': settings.ENABLE_SITEMAPS,
        'sitemaps_base_url': settings.SITEMAPS_BASE_URL,
    }, content_type='text/plain')


def humans(request):
    return render(request, 'humans.txt', {}, content_type='text/plain')
