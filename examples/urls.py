from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^wind/', include('wind.urls')),
    url(r'^echo/', include('examples.echo.urls')),
	url(r'^', include('examples.front.urls')),
)
