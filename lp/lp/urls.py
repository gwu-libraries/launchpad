from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'switchboard.views.home', name='home'),
    # url(r'^switchboard/', include('switchboard.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),                       
)

urlpatterns += patterns('nodes.views',
    
    url(r'^go/bibid/(?P<bibid>\.?b?\w{6,8})$', 'landing_page'),
    url(r'^go/isbn/(?P<isbn>\d{10,13})$', 'landing_page'),
    url(r'^go/issn/(?P<issn>\d{4}-\d{3}[0-9xX])$', 'landing_page'),
    url(r'^go/oclc/(?P<oclc>(?:\(OCoLC\))?(?:ocn)?\d{9})$', 'landing_page'),
                        
)
