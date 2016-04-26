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


#specify one snpid and lookup one scoresrow
class OneScoresRowSnp(APIView):
  def get_object_by_snpid(self, rsnp):
    try:
      rsnp = 'rs' + str(rsnp)
      return ScoresRow.objects.get(snpid=rsnp)
    except ScoresRow.DoesNotExist:
      raise Http404
  def get(self, request, snp, format = None):
    scores_row = self.get_object_by_snpid(snp)
    serializer = ScoresRowSerializer(scores_row)
    return Response(serializer.data) 

#The class below might be useful for a CBV approach.
#But I'm going to start with something more minimal for now.
"""
class ScoresRowList(APIView):
  def get_scores_by_snpid(self, snp_ids):
    scoresrows_to_return = []
    for one_snpid in snp_ids:
      one_scoresrow = ScoresRow.objects.get(snpid=one_snpid)
      scoresrows_to_return.push(one_scoresrow) 


  #look up each of the scores, list and return them 
"""

@api_view(['GET', 'POST'])
def scores_row_list(request):
  if request.method == 'GET':
    serializer = serializers.Serializer("this is some text") 
    return Response(serializer.data) #does this work?
  elif request.method == 'POST': 
    print "watch out!" 
    print str(request.data)  #expect this to be a list of quoted strings...
    scoresrows_to_return = []
    for one_snpid in request.data:
      print "one snp: " + one_snpid
      one_scoresrow = ScoresRow.objects.filter(snpid=one_snpid) #do I already have dupes?
      print(str(one_scoresrow.first()))
      scoresrows_to_return.append(one_scoresrow.first()) 
    serializer = ScoresRowSerializer(scoresrows_to_return, many = True)
    return Response(serializer.data)
  else:
    return Response('not the right response', status=status.HTTP_400_BAD_REQUEST)






