from django.conf.urls import url, include


from api_v0.views import ScoresRowViewSet
from api_v0 import views

from api_v0.models import ScoresRow
from rest_framework.routers import DefaultRouter

#not sure if this is needed, but I'll use it anyway.
from rest_framework.urlpatterns import format_suffix_patterns

#router auto-urls as well as a hardcoded pattern...
urlpatterns = format_suffix_patterns([
  url(r'scores/$', views.ScoresRowList.as_view()),
  url(r'dummy/$', views.dummy),
] )


