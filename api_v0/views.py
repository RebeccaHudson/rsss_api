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
from django.http import Http404

from rest_framework import status 

#this works, leave it as an example...
class ScoresRowList(APIView):
  """
   this should ultimately take a list of snpIDs
  """
  def get(self, request, format=None):
    scores_rows = ScoresRow.objects.all()[:3] #change this later...
    serializer = ScoresRowSerializer(scores_rows, many=True)
    return Response(serializer.data)


#This is the only view that returns ONLY one row of data.
class OneScoresRow(APIView):
  def get_object_by_id(self, pk):
    try:
      return ScoresRow.objects.get(pk = pk)
    except ScoresRow.DoesNotExist:
      return Response('Nothing with that ID',
                       status=status.HTTP_204_NO_CONTENT) 

  def get(self, request, pk, format = None):
    scores_row = self.get_object_by_id(pk)
    serializer = ScoresRowSerializer(scores_row)
    return Response(serializer.data) 


class OneScoresRowSnp(APIView):
  def get(self, request, snp, format = None):
    rsnp = 'rs' + str(snp)
    scores_rows = ScoresRow.objects.filter(snpid=rsnp)

    if len(scores_rows) == 0:
      return Response('No data for that SNPid',
                    status=status.HTTP_204_NO_CONTENT) 
    serializer = ScoresRowSerializer(scores_rows, many=True)
    return Response(serializer.data) 


#require properly formatted URLs
#@api_view(['GET', 'POST'])
@api_view(['POST'])
def scores_row_list(request):
  if request.method == 'POST': 
    print str(request.data)  #expect this to be a list of quoted strings...
    scoresrows_to_return = []
    for one_snpid in request.data:
      print "one snp: " + one_snpid
      #the line below should REALLY be get. 
      #It looks like there's snp duplicates for some reason
      one_scoresrow = None
      try:
        one_scoresrow = ScoresRow.objects.get(snpid=one_snpid)
      except ScoresRow.DoesNotExist:
        pass #just return the rows that match          

      if one_scoresrow is not None:
        scoresrows_to_return.append(one_scoresrow) 
    if len(scoresrows_to_return) == 0:
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
    serializer = ScoresRowSerializer(scoresrows_to_return, many = True)
    return Response(serializer.data)
  else:
    #I may eventually be able to remove this case.
    return Response('not the right response', status=status.HTTP_400_BAD_REQUEST)






