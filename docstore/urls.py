from django.conf.urls import include, url
from docstore.views import document

urlpatterns = [
    url(r'^(.*)$', document),
]
