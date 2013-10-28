"""
Extracts selected MARC data to a friendly Python dictionary.
"""

# a machine readable version of
# https://github.com/gwu-libraries/launchpad/wiki/MARC-Extraction

mapping = {
    'standard_title': ['240'],
    'other_title': ['130', '242', '246', '730', '740', '247'],
    'other_authors': ['700', '710', '711'],
    'earlier_title': ['247', '780'],
    'title_changed_to': ['785'],
    'copyright_date': [('245', None, 2, 'c')],
    'current_frequency': ['310', '321', '362'],
    'publication_history': ['362'],
    'series': ['440', '800', '810', '811', '830'],
    'subjects': ['650', '600', '610', '630', '651', '655'],
    'description': ['300', '516', '344', '345', '346', '347'],
    'in_collection': ['773'],
    'thesis_dissertation':  ['502'],
    'contents': ['505'],
    'production_credits': ['508'],
    'citation': ['510'],
    'performers': ['511'],
    'summary': ['520'],
    'reproduction': ['533'],
    'original_version': ['534'],
    'funding_sponsors': ['536'],
    'system_requirements': ['538'],
    'terms_of_usage': ['540'],
    'copyright': ['542'],
    'finding_aids': ['555'],
    'title_history': ['580'],
    'source_description': ['588'],
    'manufacture_numbers': ['028'],
    'genre': [('655', None, 4, 'a')],
    'other_standard_identifer': ['024'],
    'publisher_number': ['028'],
    'cataloging_source': ['040'],
    'geographic_area': ['043'],
    'oclc_code': ['049'],
    'ddc': ['082'],
    'notes': ['500', '501', '504', '507', '530', '546', '547', '550', '586',
              '590'],
}


def extract(record, d={}):
    for name, specs in mapping.items():
        d[name] = []
        for spec in specs:
            if type(spec) == str:
                for field in record.get_fields(spec):
                    d[name].append(field.value())
            # TODO: tuple
    return d

field_specs_count = 0
for name, specs in mapping.items():
    for spec in specs:
        field_specs_count += 1
