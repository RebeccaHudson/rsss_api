from django.conf.urls import url, include


#from api_v0.views import ScoresRowViewSet
from api_v0 import views

#from api_v0.models import ScoresRow
from rest_framework.routers import DefaultRouter

#not sure if this is needed, but I'll use it anyway.
from rest_framework.urlpatterns import format_suffix_patterns

from . import views 

app_name = 'api_v0'

#router auto-urls as well as a hardcoded pattern...
urlpatterns = format_suffix_patterns([
  url(r'snpid-search/$', views.search_by_snpid, name='snpid-search'),
  url(r'search-by-gl/$', views.search_by_genomic_location, name='gl-search'),
  url(r'search-by-tf/$', views.search_by_trans_factor, name='tf-search'),
  url(r'search-by-gene-name/$', views.search_by_gene_name, name='gene-name-search'),
  url(r'search-by-window-around-snpid/$', views.search_by_window_around_snpid, name='snpid-window-search')
] )
