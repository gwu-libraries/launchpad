from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()

@register.filter
@stringfilter
def clean_isbn(value):
    isbn, sep, remainder = value.strip().partition(' ')
    if len(isbn) < 10:
        return ''
    isbn = isbn.replace('-', '')
    isbn = isbn.replace(':', '')
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
    if len(value) < 8:
        return ''
    return ''.join([c for c in value if c.isdigit()])

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

