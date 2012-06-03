from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'lp.views.home', name='home'),
    # url(r'^lp/', include('lp.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns('ui.views',
    url(r'^$', 'home', name='home'),
    url(r'^item/(?P<bibid>\.?b?\d{6,8})$', 'item', name='item'),
    url(r'^issn/(?P<issn>\d{4}-?\d{3}[0-9Xx])$', 'issn', name='issn'),
    url(r'^isbn/(?P<isbn>\d{10,13})$', 'isbn', name='isbn'),
    url(r'^oclc/\(OCoLC\)(?P<oclc>\d{8,9})$', 'oclc', name='oclc'),
    url(r'^oclc/ocn(?P<oclc>\d{8,9})$', 'oclc', name='oclc'),
    url(r'^oclc/(?P<oclc>\d{8,9})$', 'oclc', name='oclc'),
    url(r'^dump/(?P<bibid>\.?b?\d{6,8})$', 'dump', name='dump'),
)

