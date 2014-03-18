import re
import logging
from urlparse import urlparse

import bibjsontools
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.utils import DatabaseError
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.utils import simplejson as json
from django.views.decorators.cache import cache_page

from ui import voyager, apis, marc, summon
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
            show_ill_link = display_ill_link(holdings)
            ours, theirs, shared = splitsort(callnumsort(enumsort(holdings)))
            holdings = elecsort(holdsort(templocsort(availsort(ours)))) \
                + elecsort(holdsort(templocsort(availsort(shared)))) \
                + libsort(elecsort(holdsort(templocsort(availsort(theirs))),
                                   rev=True))
        else:
            show_ill_link = False

        # extract details for easy display in a separate tab
        details = []
        for name, display_name, specs in marc.mapping:
            if name in bib and len(bib[name]) > 0:
                details.append((display_name, bib[name]))
        bibs = voyager.get_all_bibs(bib['BIB_ID_LIST'])
        bib['RELATED_ISBN_LIST'] = list(set(voyager.get_related_isbns(bibs)))
        return render(request, 'item.html', {
            'bibid': bibid,
            'bib': bib,
            'holdings': holdings,
            'link': bib.get('LINK', [])[9:],
            'show_ill_link': show_ill_link,
            'non_wrlc_item': False,
            'details': details,
        })
    except:
        logger.exception('unable to render bibid: %s' % bibid)
        return error500(request)


def display_ill_link(holdings):
    y = 0
    for holding in holdings:
        for loc in settings.INELIGIBLE_ILL_LOCS:
            if loc.lower() in\
                    holding.get('LOCATION_DISPLAY_NAME', '').lower():
                y = y + 1
    if y == len(holdings):
        return False
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
                  'show_ill_link': True
                  })


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def gtitem(request, gtbibid):
    try:
        bibid = voyager.get_wrlcbib_from_gtbib(gtbibid)
        if bibid:
            return redirect('item', bibid=bibid)
        else:
            bib = voyager.get_z3950_bib_data(gtbibid[1:], 'GT')
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
            bib_data = voyager.get_z3950_bib_data('b' + gtbibid[1:], 'GT')
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
        openurl = _openurl_dict(request)
        if bibid:
            url = '%s?%s' % (reverse('item', args=[bibid]),
                             openurl['query_string_encoded'])
            return redirect(url)
        return non_wrlc_item(request, num=oclc, num_type='oclc')
    except DatabaseError:
        return redirect('error503')


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


def search(request):
    params = request.GET
    q = params.get('q', '')
    page = params.get('page', 1)
    fmt = params.get('format', 'html')
    raw = params.get('raw', False)

    try:
        page = int(page)
    except ValueError:
        raise Http404

    # summon can't return results for pages > 50 with page size of 20
    max_pages = 20
    page_size = 50
    if page > max_pages:
        raise Http404

    api = summon.Summon(settings.SUMMON_ID, settings.SUMMON_SECRET_KEY)
    kwargs = {
        "hl": False,
        "pn": page,
        "ps": page_size,
        "fq": ['SourceType:("Library Catalog")'],
        "ff": [
            'ContentType,or',
            'Author,or',
            'Language,or',
            'SubjectTerms,or',
            'Genre,or',
            'Institution,or',
        ],
        "ho": "f",
        "light": "t",
        "raw": raw,
    }

    # add selected facets to the query
    for facet in params.getlist('facet'):
        if ':' not in facet:
            continue
        facet_field, facet_value = facet.split(':', 2)
        facet_value = facet_value.replace(',', '\\,')
        if 'fvf' not in kwargs:
            kwargs['fvf'] = []
        kwargs['fvf'].append('%s,%s,false' % (facet_field, facet_value))
    
    if fmt == "html":
        kwargs['for_template'] = True

    # TODO: catch Summon API errors here?
    search_results = api.search(q, **kwargs)

    # json-ld
    if fmt == "json":
        return HttpResponse(
            json.dumps(search_results, indent=2),
            content_type='application/json'
        )

    # raw summon results
    elif raw:
        if settings.DEBUG:
            return HttpResponse(
                json.dumps(search_results, indent=2),
                content_type='application/json'
            )
        else:
            # don't serve as a Summon proxy in production!
            return HttpResponse('Unauthorized', status=401)

    # default to a regular html web page
    else:
        # TODO: pull out page link generation so it can be tested
        # how many pagination links to display
        page_links = 5

        # the first page number in the pagination links
        page_range_start = ((page - 1) / page_links) * page_links + 1

        # the last page number + 1 in the pagination links
        # this is used in a range() below so it is offset by 1
        page_range_end = page_range_start + page_links

        # don't display page links that we can't get
        actual_pages = search_results['totalResults'] / page_size + 1
        if actual_pages <= page_range_end:
            page_range_end = actual_pages + 1

        # build page links as a list of tuples (page number, url)
        page_range = []
        page_query = request.GET.copy()
        for n in range(page_range_start, page_range_end):
            page_query['page'] = n
            page_range.append((n, page_query.urlencode()))

        # create links for going to the next set of page results
        next_page_range = prev_page_range = None
        if actual_pages > max_pages and page_range_end - 1 < max_pages:
            page_query['page'] = page_range_end
            next_page_range = page_query.urlencode()
        if page_range_start > page_links:
            page_query['page'] = page_range_start - 1
            prev_page_range = page_query.urlencode()

        # massage facets a bit before passing them off to the template
        # to make them easier to process there
        facet_query = request.GET.copy()
        facet_query['page'] = 1
        for f in search_results['facets']:
            for fc in f['counts']:
                # add a url that preserves the state of the query in case
                # the user wants to select the facet. we create the link
                # using the un-modified names because summon api requires it
                # http://api.summon.serialssolutions.com/help/api/search/parameters/facet-value-filter
                facet_query['facet'] = "%s:%s" % (f['name'], fc['name'])
                fc['url'] = facet_query.urlencode()

                # make sure the facet name is capitalized
                # "bazzocchi, marco antonio" -> "Bazzocchi, Marco Antonio"
                fc['name'] = fc['name'].title()

            # add space to the name: "ContentType" -> "Content Type"
            f['name'] = re.sub(r'(.)([A-Z])', r'\1 \2', f['name'])

        return render(request, 'search.html', {
            "q": q,
            "page": page,
            "page_range": page_range,
            "next_page_range": next_page_range,
            "prev_page_range": prev_page_range,
            "search_results": search_results,
            "debug": settings.DEBUG,
            "json_url": request.get_full_path() + "&format=json",
            "raw_url": request.get_full_path() + "&raw=true",
        })
