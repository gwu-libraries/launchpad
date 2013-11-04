"""
Extracts selected MARC data to a friendly Python dictionary.
"""

# a machine readable version of
# https://github.com/gwu-libraries/launchpad/wiki/MARC-Extraction
# note: the order of each rule controls the display order

mapping = (
    ('STANDARD_TITLE', 'Standard Title', ['240']),
    ('OTHER_TITLE', 'Other Title', ['130', '242', '246', '730', '740', '247']),
    ('OTHER_AUTHORS', 'Other Authors', ['700', '710', '711']),
    ('EARLIER_TITLE', 'Earlier Title', ['247', '780']),
    ('TITLE_CHANGED_TO', 'Title Changed To', ['785']),
    ('SUBJECTS', 'Subjects', ['650', '600', '610', '630', '651']),
    ('SERIES', 'Series', ['440', '800', '810', '811', '830']),
    ('DESCRIPTION', 'Description', ['300', '516', '344', '345', '346', '347']),
    ('COPYRIGHT_DATE', 'Copyright Date', [('245', None, 2, 'c')]),
    ('NOTES', 'Notes', ['500', '501', '504', '507', '530', '546', '547',
                        '550', '586', '590']),
    ('SUMMARY', 'Summary', ['520']),
    ('CURRENT_FREQUENCY', 'Current Frequency', ['310', '321', '362']),
    ('PUBLICATION_HISTORY', 'Publication History', ['362']),
    ('IN_COLLECTION', 'In Collection', ['773']),
    ('THESIS_DISSERTATION', 'Thesis/Dissertation', ['502']),
    ('CONTENTS', 'Contents', ['505']),
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
    ('CATALOGING_SOURCE', 'Cataloging Source', ['040']),
    ('GEOGRAPHIC_AREA', 'Geographic Area', ['043']),
    ('OCLC_CODE', 'OCLC Code', ['049']),
    ('DDC', 'Dewey Decimal Classification', ['082']),
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
                        d[name].append(field.format_field())
                    else:
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
    "Tests an indicator rule"
    if expected is None:
        return True
    elif expected == found:
        return True
    else:
        return False
