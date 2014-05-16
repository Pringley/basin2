from django.conf.urls import include, url
from django.shortcuts import redirect
from django.contrib import admin
from docstore import urls as doc_urls

admin.autodiscover()

urlpatterns = [
    url(r'^$', lambda r: redirect('/doc/')),
    url(r'^doc(/|$)', include(doc_urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^admin/', include(admin.site.urls)),
]
