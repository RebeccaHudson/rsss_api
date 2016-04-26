from django.shortcuts import render

# Create your views here.

from api_v0.models import ScoresRow 
from api_v0.serializers import ScoresRowSerializer
from rest_framework import generics
from django.contrib.auth.models import User

#from rest_framework.decorators import api_view
#from rest_framework.response import Response
#from rest_framework.reverse import reverse
#from rest_framework import renderers 
from rest_framework import viewsets
from rest_framework.decorators import api_view 
from rest_framework import serializers
from rest_framework.response import Response

from rest_framework.views import APIView
#from rest_framework import mixins 


#this works, leave it as an example...
class ScoresRowList(APIView):
  """
   this should ultimately take a list of snpIDs
  """
  def get(self, request, format=None):
    scores_rows = ScoresRow.objects.all()[:3] #change this later...
    serializer = ScoresRowSerializer(scores_rows, many=True)
    return Response(serializer.data)



class OneScoresRow(APIView):
  def get_object_by_id(self, pk):
    try:
      return ScoresRow.objects.get(pk = pk)
    except ScoresRow.DoesNotExist:
      raise Http404

  def get(self, request, pk, format = None):
    scores_row = self.get_object_by_id(pk)
    serializer = ScoresRowSerializer(scores_row)
    return Response(serializer.data) 



@api_view(['GET', 'POST'])
def dummy(request):
  if request.method == 'GET':
    serializer = serializers.Serializer("this is some text") 
    return Response(serializer.data) #does this work?
  else: 
    return Response('not the right response', status=status.HTTP_400_BAD_REQUEST)
