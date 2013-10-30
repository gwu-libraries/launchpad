"""
Extracts selected MARC data to a friendly Python dictionary.
"""

# a machine readable version of
# https://github.com/gwu-libraries/launchpad/wiki/MARC-Extraction

mapping = {
    'STANDARD_TITLE': ['240'],
    'OTHER_TITLE': ['130', '242', '246', '730', '740', '247'],
    'OTHER_AUTHORS': ['700', '710', '711'],
    'EARLIER_TITLE': ['247', '780'],
    'TITLE_CHANGED_TO': ['785'],
    'COPYRIGHT_DATE': [('245', None, 2, 'c')],
    'CURRENT_FREQUENCY': ['310', '321', '362'],
    'PUBLICATION_HISTORY': ['362'],
    'SERIES': ['440', '800', '810', '811', '830'],
    'SUBJECTS': ['650', '600', '610', '630', '651'],
    'DESCRIPTION': ['300', '516', '344', '345', '346', '347'],
    'IN_COLLECTION': ['773'],
    'THESIS_DISSERTATION':  ['502'],
    'CONTENTS': ['505'],
    'PRODUCTION_CREDITS': ['508'],
    'CITATION': ['510'],
    'PERFORMERS': ['511'],
    'SUMMARY': ['520'],
    'REPRODUCTION': ['533'],
    'ORIGINAL_VERSION': ['534'],
    'FUNDING_SPONSORS': ['536'],
    'SYSTEM_REQUIREMENTS': ['538'],
    'TERMS_OF_USAGE': ['540'],
    'COPYRIGHT': ['542'],
    'FINDING_AIDS': ['555'],
    'TITLE_HISTORY': ['580'],
    'SOURCE_DESCRIPTION': ['588'],
    'MANUFACTURE_NUMBERS': ['028'],
    'GENRE': [('655', None, None, 'a')],
    'OTHER_STANDARD_IDENTIFIER': ['024'],
    'PUBLISHER_NUMBER': ['028'],
    'CATALOGING_SOURCE': ['040'],
    'GEOGRAPHIC_AREA': ['043'],
    'OCLC_CODE': ['049'],
    'DDC': ['082'],
    'NOTES': ['500', '501', '504', '507', '530', '546', '547', '550', '586',
              '590'],
}


def extract(record, d={}):
    for name, specs in mapping.items():
        d[name] = []
        for spec in specs:

            # simple field specification
            if type(spec) == str:
                for field in record.get_fields(spec):
                    d[name].append(field.value())

            # complex field specification 
            else:
                tag, ind1, ind2, subfields = spec
                for field in record.get_fields(tag):
                    if ind(ind1, field.indicator1) and ind(ind2,
                       field.indicator2):
                        parts = []
                        for code, value in field:
                            if code in subfields:
                                parts.append(value)
                        if len(parts) > 0:
                            d[name].append(' '.join(parts))

    return d


def ind(expected, found):
    if expected is None:
        return True
    elif expected == found:
        return True
    else:
        return False


field_specs_count = 0
for name, specs in mapping.items():
    for spec in specs:
        field_specs_count += 1
