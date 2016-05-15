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
from django.conf import settings

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
@api_view(['POST'])
def scores_row_list(request):
  if request.method == 'POST': 
    print str(request.data)  #expect this to be a list of quoted strings...
    scoresrows_to_return = []
    for one_snpid in request.data:
      scoresrows = ScoresRow.objects.filter(snpid=one_snpid)
      for matching_row_of_data in scoresrows:
        scoresrows_to_return.append(matching_row_of_data)
    if len(scoresrows_to_return) == 0:
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
    serializer = ScoresRowSerializer(scoresrows_to_return, many = True)
    return Response(serializer.data)
  else:
    #I may eventually be able to remove this case.
    return Response('not the right response', status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def search_by_genomic_location(request):
  #Run some checks...
  if not all (k in request.data.keys() for k in ("chromosome","start_pos", "end_pos")):
    return Response('Must include chromosome, start, and end position.',
                     status = status.HTTP_400_BAD_REQUEST)

  start_pos = request.data['start_pos']
  end_pos = request.data['end_pos']
  chromosome = request.data['chromosome']  # TODO: check for invlaid chromosome

  if end_pos < start_pos:
    return Response('Start position is less than end position.',
                    status = status.HTTP_400_BAD_REQUEST)

  if end_pos - start_pos > settings.HARD_LIMITS['MAX_BASES_IN_GL_REQUEST']:
    return Response('Requested region is too large', 
                     status=status.HTTP_400_BAD_REQUEST)
   
  #refer to: https://docs.djangoproject.com/en/1.9/ref/models/querysets/#id4 
  scoresrows = ScoresRow.objects.filter(chromosome=chromosome, 
                                        pos__gte=start_pos, pos__lte=end_pos) 
  if len(scoresrows) == 0:
    return Response('No data in specified range.', status=status.HTTP_204_NO_CONTENT)
  
  serializer = ScoresRowSerializer(scoresrows, many = True)
  return Response(serializer.data, status=status.HTTP_200_OK )


