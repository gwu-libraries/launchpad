from django.conf import settings
from django.conf.urls import patterns, url
from django.views.generic import TemplateView


handler500 = 'ui.views.error500'

urlpatterns = patterns('ui.views',
    url(r'^$', 'home', name='home'),
    url(r'^item/(?P<bibid>\d{2,8})$', 'item', name='item'),
    url(r'^item/(?P<bibid>\d{2,8}).json$', 'item_json', name='item_json'),
    url(r'^item/(?P<bibid>\d{2,8})/marc.json$', 'item_marc', name='item_marc'),
    url(r'^item/\.?(?P<gtbibid>b\d{2,8}x?)$', 'gtitem', name='gtitem'),
    url(r'^item/\.?(?P<gtbibid>b\d{2,8}x?).json$', 'gtitem_json',
        name='gtitem_json'),
    url(r'^item/m(?P<gmbibid>\d{2,8})$', 'gmitem', name='gmitem'),
    url(r'^item/m(?P<gmbibid>\d{2,8}).json$', 'gmitem_json',
        name='gmitem_json'),
    url(r'^issn/(?P<issn>\d{4}-?\d{3}[0-9Xx])$', 'issn', name='issn'),
    url(r'^isbn/(?P<isbn>[0-9-xX]+)$', 'isbn', name='isbn'),
    url(r'^isbn/(?P<isbn>[0-9-xX]+) .*$', 'isbn'),
    url(r'^oclc/\(OCoLC\)oc[mn](?P<oclc>\d{6,10})$', 'oclc'),
    url(r'^oclc/\(OCoLC\)(?P<oclc>\d{6,10})$', 'oclc'),
    url(r'^oclc/\(OCoLC\)on(?P<oclc>\d{6,10})$', 'oclc'),
    url(r'^oclc/oc[mn](?P<oclc>\d{6,10})$', 'oclc'),
    url(r'^oclc/on(?P<oclc>\d{6,10})$', 'oclc'),
    url(r'^oclc/\(Safari\)(?P<oclc>\d{6,10})$', 'oclc'),
    url(r'^oclc/(?P<oclc>\d{6,10})$', 'oclc', name='oclc'),
    url(r'^about/', TemplateView.as_view(template_name='about.html'),
        name='about'),
    url(r'^api/', TemplateView.as_view(template_name='api.html'),
        name='api'),
    url(r'^robots.txt$', 'robots', name='robots'),
    url(r'^503.html$', 'error503', name='error503'),
)

if settings.ENABLE_HUMANS:
    urlpatterns += patterns('ui.views',
        url(r'^humans.txt$', 'humans', name='humans'),
    )
