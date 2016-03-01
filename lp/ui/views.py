import datetime
import json
import logging
import re
import time
import urlparse

import bibjsontools

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.utils import DatabaseError
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_page

import requests

from forms import PrintRequestForm

from ui import voyager, apis, marc, summon, db
from ui.sort import libsort, availsort, elecsort, templocsort, \
    splitsort, enumsort, callnumsort, strip_bad_holdings, holdsort


logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'home.html', {
        'title': 'launchpad home',
    })


def advanced_search(request):
    return render(request, 'advanced_search.html', {
        'title': 'Advanced Search',
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
            'max_periodicals': settings.MAX_PERIODICALS,
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
                components = urlparse.urlparse(marc856['u'])
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


def request_print(request, bibid):
    if request.method == 'POST':  # If the form has been submitted...
        form = PrintRequestForm(request.POST)
        if form.is_valid():
            requests.post('https://docs.google.com/a/email.gwu.edu/forms/d/1uNlorJm4j5A6cn6BT2cofaanCQcIAvtKGqz0bHlWmQ8/formResponse', data=request.POST)
            bibid = bibid
            return redirect('confirmation', bibid=bibid)
        else:
            citation = {'isbn': request.POST.get('isbn'),
                        'title': request.POST.get('title')}
            return render(request, 'request-print.html', {'form': form,
                                                          'bibid': bibid,
                                                          'citation': citation})
    else:
        isbn = request.GET.get('isbn', '').split(' ', 1)[0]
        title = request.GET.get('title', '')
        title_info = request.GET.get('title', '') + ' BIBID: ' + str(bibid)
        form = PrintRequestForm(initial={'entry_994442820': title_info,
                                         'entry_1457763040': isbn,
                                         'entry_1537829419': bibid,
                                         'title': title,
                                         'isbn': isbn})
        citation = {'isbn': isbn, 'title': title}
        return render(request, 'request-print.html', {'form': form,
                                                      'bibid': bibid,
                                                      'citation': citation})


def confirmation(request, bibid):
    return render(request, 'confirmation.html', {'bibid': bibid})


@cache_page(settings.ITEM_PAGE_CACHE_SECONDS)
def non_wrlc_item(request, num, num_type):
    bib = apis.get_bib_data(num=num, num_type=num_type)
    if not bib:
        return render(request, '404.html', {'num': num,
                      'num_type': num_type.upper()}, status=404)
    bib['openurl'] = _openurl_dict(request)
    bib['citation_json'] = citation_json(request)
    bib['ILLIAD_LINK'] = voyager.get_illiad_link(bib)
    try:
        bib['REFWORKS_LINK'] = voyager.get_refworks_link(bib)
    except:
        bib['REFWORKS_LINK'] = ''
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
        bibid = db.get_bibid_from_gtid(gtbibid)
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
        bibid = db.get_bibid_from_gtid(gtbibid)
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
        bibid = db.get_bibid_from_gmid(gmbibid)
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
                try:
                    linkval = bib.get('LINK', [])[9:]
                except:
                    linkval = ''
            return render(request, 'item.html', {
                'bibid': bibid,
                'bib': bib,
                'holdings': holdings,
                'link': linkval,
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
        bibid = voyager.get_bibid_from_gmid(gmbibid)
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
    online = params.get('online', False)
    page_size = params.get('page_size', 20)

    try:
        page = int(page)
        page_size = int(page_size)
    except ValueError:
        raise Http404

    # summon can't return results for pages > 50 with page size of 20
    max_pages = 50
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
            'Genre,or',
            'Institution,or',
            'Discipline,or',
            'SubjectTerms,or',
            'TemporalSubjectTerms,or',
            'GeographicLocations,or',
        ],
        "ho": "t",
        "light": "t",
        "raw": raw,
    }

    q, kwargs = _filter_by_pubdate(q, kwargs)

    # add to the query if they want online resources only
    if online:
        if q:
            q += " AND"
        q += " lccallnum:('gw electronic' OR 'shared+electronic'" + \
            " OR 'e-resources' OR 'e-govpub' OR 'streaming')"

    # add selected facets to the query
    for facet in params.getlist('facet'):
        if ':' not in facet:
            continue
        facet_field, facet_value = facet.split(':', 1)

        if 'fvf' not in kwargs:
            kwargs['fvf'] = []

        # TODO: maybe summoner should do these escapes somehow?
        def escape(m):
            return '\\' + m.group(1)
        facet_value = re.sub('([,:\()${}])', escape, facet_value)

        kwargs['fvf'].append('%s,%s,false' % (facet_field, facet_value))

        # add Library facet field if user is faceting by Institution
        if facet_field == 'Institution' and 'Library,or' not in kwargs['ff']:
            kwargs['ff'].append('Library,or')

    if fmt == "html":
        kwargs['for_template'] = True

    # catch and retry up to MAX_ATTEMPTS times if we get errors
    # from the Summon API?
    retries = 0
    while True:
        try:
            search_results = api.search(q, **kwargs)
            break
        except HTTPError as error:
            retries += 1
            if retries <= settings.SER_SOL_API_MAX_ATTEMPTS:
                time.sleep(1)
                continue
            else:
                logger.exception('unable to search Summon (3 tries): %s' %
                                 error)
                return error500(request)

    if not raw:
        search_results = _remove_facets(search_results)
        search_results = _reorder_facets(search_results)
        search_results = _remove_active_facets(request, search_results)
        search_results = _format_facets(request, search_results)

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
        if page_range_end - 1 < actual_pages \
                and page_range_end - 1 < max_pages:
            page_query['page'] = page_range_end
            next_page_range = page_query.urlencode()
        if page_range_start > page_links:
            page_query['page'] = page_range_start - 1
            prev_page_range = page_query.urlencode()

        return render(request, 'search.html', {
            "q": params.get('q'),
            "original_facets": params.getlist('facet'),
            "active_facets": _get_active_facets(request),
            "page": page,
            "page_range": page_range,
            "next_page_range": next_page_range,
            "prev_page_range": prev_page_range,
            "search_results": search_results,
            "debug": settings.DEBUG,
            "online": online,
            "json_url": request.get_full_path() + "&format=json",
            "raw_url": request.get_full_path() + "&raw=true",
            "max_subjects": settings.MAX_SUBJECTS,
        })


def _filter_by_pubdate(q, q_options):
    """
    Summon API doesn't support passing in PublicationDate directly in the
    query. But it does support querying PublicationDate using a range filter.
    This function accepts a query string and the query options and removes
    PublicationDate query into the query options. Allowing the
    PublicationDate to be expressed in launchpad query lets people play
    with it directly in the query form.
    """
    new_q = q
    new_q_options = q_options.copy()
    p = ' *(and)? *publicationdate:\[(\d+)?-(\d+)?]'
    for m in re.finditer(p, q, flags=re.IGNORECASE):
        start = m.group(2)
        end = m.group(3)
        if start is None:
            start = 1000
        if end is None:
            end = datetime.datetime.now().year
        new_q = q.replace(m.group(0), '')
        new_q_options["rf"] = "PublicationDate,%s:%s" % (start, end)
    return new_q, new_q_options


def availability(request):
    """
    API call for getting the availability for a particular bibid.
    """
    bibid = request.GET.get('bibid')
    if not bibid:
        raise Http404
    return HttpResponse(
        json.dumps(db.get_availability(bibid), indent=2),
        content_type='application/json'
    )


def related(request):
    """
    API call for getting related bibids.
    """
    bibid = request.GET.get('bibid')
    if not bibid:
        raise Http404()
    bibid = db.get_bibid_from_summonid(bibid)
    item = db.get_item(bibid)
    bibids = db.get_related_bibids(item)
    return HttpResponse(
        json.dumps(bibids, indent=2),
        content_type='application/json'
    )


def tips(request):
    return render(request, 'tips.html', {'title': 'search tips'})


def _remove_facets(search_results):
    to_delete = [
        'ContentType:Journal Article',
        'Genre:electronic books',
        'ContentType:Book Chapter',
        'ContentType:Book Review'
    ]
    for facet in search_results['facets']:
        new_counts = []
        for count in facet['counts']:
            s = "%s:%s" % (facet['name'], count['name'])
            if s not in to_delete:
                new_counts.append(count)
        facet['counts'] = new_counts
    return search_results


def _remove_active_facets(request, search_results):
    facets = request.GET.getlist('facet', [])
    for facet in search_results['facets']:
        new_counts = []
        for count in facet['counts']:
            if "%s:%s" % (facet['name'], count['name']) not in facets:
                new_counts.append(count)
        facet['counts'] = new_counts
    return search_results


def _reorder_facets(search_results):
    # facets can come back in different order from summon
    # this function makes sure we always display them in the same order
    facets_order = ['Institution', 'Library', 'ContentType', 'Author',
                    'Discipline', 'SubjectTerms', 'TemporalSubjectTerms',
                    'GeographicLocations', 'Genre', 'Language']
    new_facets = []
    for facet_name in facets_order:
        for facet in search_results['facets']:
            # only add facet if there are more than one values for it
            if facet['name'] == facet_name and len(facet['counts']) > 1:
                new_facets.append(facet)
    search_results['facets'] = new_facets
    return search_results


def _format_facets(request, search_results):
    # massage facets a bit before passing them off to the template
    # to make them easier to process there
    for f in search_results['facets']:
        for fc in f['counts']:

            # add a url property to each facet to activate facet
            fq = request.GET.copy()
            fq.update({'facet': "%s:%s" % (f['name'], fc['name'])})
            fq['page'] = 1
            fc['url'] = fq.urlencode()
            fc['name'] = _normalize_facet_name(f['name'], fc['name'])

        # add spaces to the facet name: "ContentType" -> "Content Type"
        f['name'] = re.sub(r'(.)([A-Z])', r'\1 \2', f['name'])

        # convert certain API facet names -> friendly labels
        if f['name'] == 'Subject Terms':
            f['name'] = 'Subjects'
        if f['name'] == 'Temporal Subject Terms':
            f['name'] = 'Time Period'
        if f['name'] == 'Geographic Locations':
            f['name'] = 'Region'

    return search_results


def _get_active_facets(request):
    active_facets = []

    for facet in request.GET.getlist('facet'):
        if ':' not in facet:
            continue
        name, value = facet.split(':', 1)

        remove_link = request.GET.copy()
        removed_facets = list(
            set(remove_link.getlist('facet')) - set([facet])
        )
        remove_link.setlist('facet', removed_facets)

        active_facets.append({
            "name": name,
            "value": _normalize_facet_name(name, value),
            "remove_link": "?" + remove_link.urlencode()
        })
    return active_facets


def _normalize_facet_name(f_name, fc_name):
    if f_name == 'ContentType':
        if fc_name == 'Audio Recording':
            fc_name = 'Audio'
        elif fc_name == 'Video Recording':
            fc_name = 'Video'
    elif f_name == 'Institution':
        fc_name = re.sub('\(.+\)$', '', fc_name)
    if f_name not in ('Library', 'Institution'):
        fc_name = fc_name.title()

    return fc_name
