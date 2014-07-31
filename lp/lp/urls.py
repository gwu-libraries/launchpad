from django.conf import settings
from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from ui import views
from django.views.decorators.cache import cache_page


handler500 = 'ui.views.error500'
cache_time = settings.ITEM_PAGE_CACHE_SECONDS

urlpatterns = patterns('ui.views',
    url(r'^$', views.home, name='home'),
    url(r'^item/(?P<bibid>\d{2,8})$', cache_page(cache_time)(views.item),
        name='item'),
    url(r'^item/(?P<bibid>\d{2,8}).json$', 
        cache_page(cache_time)(views.item_json), name='item_json'),
    url(r'^item/(?P<bibid>\d{2,8})/marc.json$', 
        cache_page(cache_time)(views.item_marc), name='item_marc'),
    url(r'^item/\.?(?P<gtbibid>b\d{2,8}x?)$', 
        cache_page(cache_time)(views.gtitem), name='gtitem'),
    url(r'^item/\.?(?P<gtbibid>b\d{2,8}x?).json$', 
        cache_page(cache_time)(views.gtitem_json), name='gtitem_json'),
    url(r'^item/m(?P<gmbibid>\d{2,8})$', 
        cache_page(cache_time)(views.gmitem), name='gmitem'),
    url(r'^item/m(?P<gmbibid>\d{2,8}).json$', 
        cache_page(cache_time)(views.gmitem_json), name='gmitem_json'),
    url(r'^issn/(?P<issn>\d{4}-?\d{3}[0-9Xx])$', views.issn, name='issn'),
    url(r'^isbn/(?P<isbn>[0-9-xX]+)$', views.isbn, name='isbn'),
    url(r'^isbn/(?P<isbn>[0-9-xX]+) .*$', views.isbn),
    url(r'^oclc/\(OCoLC\)oc[mn](?P<oclc>\d{6,10})$', views.oclc),
    url(r'^oclc/\(OCoLC\)(?P<oclc>\d{6,10})$', views.oclc),
    url(r'^oclc/\(OCoLC\)on(?P<oclc>\d{6,10})$', views.oclc),
    url(r'^oclc/oc[mn](?P<oclc>\d{6,10})$', views.oclc),
    url(r'^oclc/on(?P<oclc>\d{6,10})$', views.oclc),
    url(r'^oclc/\(Safari\)(?P<oclc>\d{6,10})$', views.oclc),
    url(r'^oclc/(?P<oclc>\d{6,10})$', views.oclc, name='oclc'),
    url(r'^about/', TemplateView.as_view(template_name='about.html'),
        name='about'),
    url(r'^api/', TemplateView.as_view(template_name='api.html'),
        name='api'),
    url(r'^robots.txt$', views.robots, name='robots'),
    url(r'^503.html$', views.error503, name='error503'),
    url(r'^search$', views.search, name='search'),
    url(r'^availability$', views.availability, name='availability'),
    url(r'^related$', views.related, name='related')
)

if settings.ENABLE_HUMANS:
    urlpatterns += patterns('ui.views',
        url(r'^humans.txt$', views.humans, name='humans'),
    )
