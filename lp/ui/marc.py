"""
Extracts selected MARC data to a friendly Python dictionary.
"""

import os
import re
import json


# turn the 043 codes into human readable strings based on the table list at
# http://www.loc.gov/standards/codelists/gacs.xml

gacs_file = os.path.join(os.path.dirname(__file__), "gacs.json")
gacs_dict = json.loads(open(gacs_file).read())


def gacs(field):
    values = []
    for c, v in field:
        # only interested in subfield a
        if c == 'a':
            # strip trailing dashes from gacs code if present
            v = re.sub(r"-+$", "", v)
            # add the string for the gacs code if it is available
            values.append(gacs_dict.get(v, v))
    return values


# a machine readable version of
# https://github.com/gwu-libraries/launchpad/wiki/MARC-Extraction
# note: the order of each rule controls the display order
# note: the ones with 'json data only' are not displayed by item.html

mapping = (
    ('STANDARD_TITLE', 'Standard Title', ['240']),
    ('OTHER_TITLE', 'Other Title', [('130', None, None, 'a'), '242', '246', '730', '740', '247']),
    ('OTHER_AUTHORS', 'Other Authors', [('700', None, None, 'a,d'), ('710', None, None, 'a,b,c,d,g'), '711']),
    ('EARLIER_TITLE', 'Earlier Title', ['247', '780']),
    ('TITLE_CHANGED_TO', 'Title Changed To', ['785']),
    ('SUBJECTS', 'Subjects', ['650', '600', '610', '630', '651']),
    ('SERIES', 'Series', ['440', '800', '810', '811', '830']),
    ('DESCRIPTION', 'Description', ['300', '351', '516', '344', '345', '346', '347']),
    ('COPYRIGHT_DATE', 'Copyright Date', [('264', None, None, 'c')]),
    ('NOTES', 'Notes', ['500', '501', '504', '507', '521', '530', '546', '547',
                        '550', '586', '590', '541']),
    ('SUMMARY', 'Summary', ['520']),
    ('BIOGRAPHICAL NOTES', 'Biographical Notes', ['545']),
    ('CURRENT_FREQUENCY', 'Current Frequency', ['310', '321']),
    ('PUBLICATION_HISTORY', 'Publication History', ['362']),
    ('IN_COLLECTION', 'In Collection', [
        ('773', None, None, 'abdghikmnopqrstuwxyz')
    ]),
    ('THESIS_DISSERTATION', 'Thesis/Dissertation', ['502']),
    ('CONTENTS', 'Contents', ['505', '990']),
    ('PRODUCTION_CREDITS', 'Production Credits', ['508']),
    ('CITATION', 'Citation', ['510']),
    ('PERFORMERS', 'Performers', ['511']),
    ('REPRODUCTION', 'Reproduction', ['533']),
    ('ORIGINAL_VERSION', 'Original Version', ['534']),
    ('FUNDING_SPONSORS', 'Funding Sponsors', ['536']),
    ('SYSTEM_REQUIREMENTS', 'System Requirements', ['538']),
    ('TERMS_OF_USAGE', 'Terms of Usage', ['540']),
    ('COPYRIGHT', 'Copyright', ['542']),
    ('FINDING_AIDS', 'Finding Aids', ['555']),
    ('TITLE_HISTORY', 'Title History', ['580']),
    ('SOURCE_DESCRIPTION', 'Source Description', ['588']),
    ('MANUFACTURE_NUMBERS', 'Manufacture Numbers', ['028']),
    ('GENRE', 'Genre', [('655', None, None, 'a')]),
    ('OTHER_STANDARD_IDENTIFIER', 'Other Identifiers', ['024']),
    ('PUBLISHER_NUMBER', 'Publisher Numbers', ['028']),
    ('GEOGRAPHIC_AREA', 'Geographic Area', [('043', gacs)]),
    ('NETWORK_NUMBER', 'Network Numbers', [('035', None, None, 'a')]),
    ('URI_AUTHOR', 'json data only', [('100', None, None, 'a,0')]),
    ('URI_7XX', 'json data only', [('700', None, None, 'a,0'), ('710', None, None, 'a,0')]),
    ('URI_SUBJECTS','json data only', [('650', None, None, 'a,0'), ('651', None, None, 'a,0'), \
                                  ('600', None, None, 'a,0'), ('610', None, None, 'a,0'), \
                                  ('630', None, None, 'a,0')]),
    ('URI_GENRE', 'json data only', [('655', None, None, 'a,0')]),
    ('URI_WORKID','json data only',  [('787', None, None, 'n,o')]),
    ('URI_AUTHORID', 'json data only', [('100', None, None, 'a,0')]),
)


def extract(record, d={}):
    """
    Takes a pymarc.Record object and returns extracted information as a
    dictionary. If you pass in a dictionary the extracted information will
    be folded into it.
    """
    for name, display_name, specs in mapping:
        d[name] = []
        for spec in specs:

            # simple field specification
            if type(spec) == str:
                for field in record.get_fields(spec):
                    if field.is_subject_field():
                        d[name].append(subject(field))
                    else:
                        d[name].append(field.format_field())

            # complex field specification
            elif len(spec) == 4:
                tag, ind1, ind2, subfields = spec
                for field in record.get_fields(tag):
                    if ind(ind1, field.indicator1) and ind(ind2,
                       field.indicator2):
                        parts = []
                        for code, value in field:
                            # TODO: we purposefully ignore $6 for now since 
                            # it is used for linking alternate script 
                            # representations. Ideally some day we could 
                            # have a way to layer them into our data
                            # representation, or simply using the original
                            # character set as the default since our 
                            # web browsers can easily display them now.
                            if code != '6' and code in subfields:
                                parts.append(value)
                        if len(parts) > 0:
                            d[name].append(' '.join(parts))

            # function based specification
            elif len(spec) == 2:
                tag, func = spec
                for field in record.get_fields(tag):
                    d[name].extend(func(field))

            # uhoh, the field specification looks bad
            else:
                raise Exception("invalid mapping for %s" % name)

    # The URI set must be checked for http, converted to a dictionary
    # The first time a tag was retrieved we got the text (e.g., author), when we then 
    # retrieve the same tag for URI, we get the $0, if any (e.g., http://loc.gov.authorities.names/...) 
    # get_http_link_set makes sure there is an http in $0. In non-GW records, there will not be any.

    d['URI_SUBJECTS'] = get_http_link_set(d['URI_SUBJECTS'])
    d['URI_GENRE']    = get_http_link_set(d['URI_GENRE'])
    d['URI_AUTHOR']   = get_http_link_set(d['URI_AUTHOR'])
    d['URI_7XX']      = get_http_link_set(d['URI_7XX'])
    d['URI_WORKID']   = get_http_link_set(d['URI_WORKID'])
    # Calcuate the OCLC Identity URL
    d['URI_AUTHORID'] = make_identity_link(d['URI_AUTHORID'])
    return d

def get_http_link_set(values):
    # Given a list of values, return only the ones that have the string http in them.
    # Convert list to dictionary for easier parsing in item.html
    httpset = []
    parts   = {}
    for item in values:
        if 'http' in item:
           parts = get_uri_parts(item)
           httpset.append(parts)
    return httpset

def make_identity_link(a):
    # Convert an authorzed name link to an OCLC WorldCat Identities link. Use the 'n' value
    # and the Identities url prefix. convert to dictionary for easier parsing in item.html
    parts = {}
    identities = []
    atostring  = ''.join(a) 
    if 'http' in atostring:
        startpos   = atostring.index('http')
        namepart   = atostring[0:startpos] 
        authurl    = atostring[startpos:len(atostring)]
        prefix     = 'http://www.worldcat.org/wcidentities/lccn-'
        newurl     = prefix + authurl.split('/')[-1]
        parts      = {'linktext':namepart,'uri':newurl}
        identities.append(parts)
    return identities


def get_uri_parts(uri):
    # For a give URI label and http string, split into linktext and http uri.
    parts = {}
    uristring = ''.join(uri)
    if 'http' in uristring:
        startpos = uristring.index('http')
        namepart = uristring[0:startpos]
        linkpart = uristring[startpos:len(uristring)]
        parts    = {'linktext':namepart,'uri':linkpart}
        return parts

def ind(expected, found):
    "Tests an indicator rule"
    if expected is None:
        return True
    elif expected == found:
        return True
    else:
        return False


def subject(f):
    s = ''
    for code, value in f:
        if code in map(lambda x: str(x), list(range(0, 9, 1))):
            continue
        elif code not in ('v', 'x', 'y', 'z'):
            s += ' %s' % value
        else:
            s += ' -- %s' % value
    return s.strip()
