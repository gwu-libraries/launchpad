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
