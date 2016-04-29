from django.conf.urls import url, include


#from api_v0.views import ScoresRowViewSet
from api_v0 import views

from api_v0.models import ScoresRow
from rest_framework.routers import DefaultRouter

#not sure if this is needed, but I'll use it anyway.
from rest_framework.urlpatterns import format_suffix_patterns

from . import views 

app_name = 'api_v0'

#router auto-urls as well as a hardcoded pattern...
urlpatterns = format_suffix_patterns([
  url(r'scores/$', views.ScoresRowList.as_view(), name='dummy-scores'),
  url(r'scores_row_list/$', views.scores_row_list, name='search'),
  url(r'one-scores/(?P<pk>[0-9]+)/$', views.OneScoresRow.as_view(), name='one-scores'),
  url(r'one-scores-snpid/rs(?P<snp>[0-9]+)/$', views.OneScoresRowSnp.as_view(), name = 'one-scores-snpid'),
] )


