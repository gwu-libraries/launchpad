from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter, urlencode


register = template.Library()


@register.filter
@stringfilter
def clean_isbn(value):
    isbn, sep, remainder = value.strip().partition(' ')
    if len(isbn) < 10:
        return ''
    for char in '-:.;':
        isbn = isbn.replace(char, '')
    return isbn


@register.filter
@stringfilter
def clean_issn(value):
    if len(value) < 9:
        return ''
    return value.strip().replace(' ', '-')


@register.filter
@stringfilter
def clean_oclc(value):
    return ''.join([c for c in value if c.isdigit()])


@register.filter
@stringfilter
def clean_lccn(value):
    """Following the logic/examples described at:
      http://lccn.loc.gov/lccnperm-faq.html#n9
      http://www.loc.gov/marc/lccn-namespace.html"""
    # remove all blanks
    value = value.replace(' ', '')
    # if there's a forward slash, remove it and all characters to its right
    if '/' in value:
        value = value[:value.index('/')]
    if '-' in value:
        # remove the hyphen
        left, sep, right = value.partition('-')
        # all chars in right should be digits, and len <= 6
        right = ''.join([c for c in right if c.isdigit()])
        if right:
            if len(right) > 6:
                return ''
            # left-pad with 0s until len == 6
            if len(right) < 6:
                right = '%06d' % int(right)
        value = '%s%s' % (left, right)
    if len(value) < 8 or len(value) > 12:
        return ''
    else:
        return value


@register.filter
@stringfilter
def cjk_info(value):
    fields = value.split(' // ')
    field_partitions = [f.partition(' ') for f in fields]
    cjk = {}
    for field, sep, val in field_partitions:
        if field.startswith('1'):
            cjk['AUTHOR'] = val
        elif field.startswith('245'):
            cjk['TITLE'] = val
        elif field.startswith('260'):
            cjk['IMPRINT'] = val
        elif field.startswith('600'):
            cjk['AUTHOR600'] = val
    return cjk


@register.filter
@stringfilter
def noscream(value):
    for scream, calm in settings.SCREAMING_LOCATIONS:
        if scream in value:
            value = value.replace(scream, calm)
    return value


@register.filter
def remove_empty_links(marc856list):
    return [link_dict for link_dict in marc856list if link_dict.get('u', None)]


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, '')


@register.assignment_tag
def assign_settings_value(name):
    return getattr(settings, name, '')


@register.filter
def citationlist(citation_json):
    snippets = []
    for key in ['type', 'author', 'title', 'journal', 'identifier',
                'publisher', 'volume', 'issue', 'year', 'pages']:
        if citation_json.get(key, None):
            snippets.append(listelement(key, citation_json))
    if not citation_json.get('pages') \
            and citation_json.get('start_page') \
            and citation_json.get('end_page'):
        snippets.append(listelement('start_page', citation_json))
        snippets.append(listelement('end_page', citation_json))
    html = '<dl class="dl-horizontal">%s</dl>' % ''.join(snippets)
    return html


@register.filter
def is_non_roman(s):
    # TODO: use of this can go away when we don't have to worry about
    # sending non-roman text at surveyor in item.html
    try:
        s.encode('iso-8859-1')
        return False
    except:
        return True


@register.simple_tag
def explore(value_type, value):
    target = getattr(settings, 'EXPLORE_TYPE', 'surveyor')
    v = urlencode(value)
    url = None

    if target not in ('summon', 'surveyor'):
        raise Exception("unknown EXPLORE_TYPE in settings: %s" % target)

    if value_type not in ('author', 'subject', 'series'):
        raise Exception("unknown explore value_type: %s" % value_type)

    if value_type == 'author':
        if target == 'surveyor':
            url = 'http://surveyor.gelman.gwu.edu/?q=author:%22' + v + '%22'
        elif target == 'summon':
            url = 'http://gw.summon.serialssolutions.com/search?s.q=Author:%22' + v + '%22'

    elif value_type == 'subject':
        if target == 'surveyor':
            url = 'http://surveyor.gelman.gwu.edu/?q=subject:%22' + v + '%22'
        elif target == 'summon':
            parts = ['subjectterms:"' + s + '"' for s in value.split(' -- ')]
            q = urlencode(' AND '.join(parts))
            url = 'http://gw.summon.serialssolutions.com/search?s.q=' + q

    elif value_type == 'series':
        if target == 'surveyor':
            url = 'http://surveyor.gelman.gwu.edu/?q=series:%22' + v + '%22'
        elif target == 'summon':
            url = 'http://gw.summon.serialssolutions.com/search?s.q=title:%22' + v + '%22'

    return url


def listelement(key, citation_json):
    value = citation_json[key]
    if key == 'journal':
        value = value['name']
    elif key == 'author':
        value = ', '.join([a['name'] for a in value])
    elif key == 'identifier':
        value = '; '.join(['%s: %s' % (i['type'], i['id']) for i in value])
    elif key == 'type':
        value = value.replace('inbook', 'chapter')
    elif 'page' in key:
        value = value.replace('EOA', '')
    return '<dt>%s</dt><dd>%s</dd>' % (key.replace('_', ' '), value)
