from django.conf.urls import patterns, url
from django.views.generic import TemplateView


handler500 = 'ui.views.error500'

urlpatterns = patterns('ui.views',
    url(r'^$', 'home', name='home'),
    url(r'^item/(?P<bibid>\.?b?\d{6,8})$', 'item', name='item'),
    url(r'^item/(?P<bibid>\.?b?\d{6,8}).json$', 'item_json', name='item_json'),
    url(r'^issn/(?P<issn>\d{4}-?\d{3}[0-9Xx])$', 'issn', name='issn'),
    url(r'^isbn/(?P<isbn>[0-9-xX]+)$', 'isbn', name='isbn'),
    url(r'^oclc/(?P<oclc>\d{8,9})$', 'oclc', name='oclc'),
    url(r'^oclc/\(OCoLC\)oc[mn](?P<oclc>\d{8,10})$', 'oclc', name='oclc'),
    url(r'^oclc/\(OCoLC\)(?P<oclc>\d{8,10})$', 'oclc', name='oclc'),
    url(r'^oclc/oc[mn](?P<oclc>\d{8,10})$', 'oclc', name='oclc'),
    url(r'^oclc/\(Safari\)(?P<oclc>\d{8,10})$', 'oclc', name='oclc'),
    url(r'^about/', TemplateView.as_view(template_name='about.html'), 
        name='about'),
    url(r'^api/', TemplateView.as_view(template_name='api.html'), 
        name='api'),
)

