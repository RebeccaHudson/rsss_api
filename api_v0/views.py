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

from django.db import connection  #needed for manual queries with cassandra
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
  #does not make sense with cassandra
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

#deprecated for production; p-value cutoff not added.
class OneScoresRowSnp(APIView):
  def get(self, request, snp, format = None):
    rsnp = 'rs' + str(snp)
    #scores_rows = ScoresRow.objects.filter(snpid=rsnp)
    cursor = connection.cursor()
    scores_rows = cursor.execute('SELECT * from '+settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_SNPID_QUERY']+' where snpid = '+repr(rsnp) )
    scores_rows = scores_rows.current_rows
    if len(scores_rows) == 0:
      return Response('No data for that SNPid',
                    status=status.HTTP_204_NO_CONTENT) 
    serializer = ScoresRowSerializer(scores_rows, many=True)
    return Response(serializer.data) 

def order_rows_by_genomic_location(rows): 
  return sorted(rows, key=lambda row: row['pos'])   # sort by age
 


def get_p_value(request):
  if request.data.has_key('pvalue_rank'):
    # consider some validation here...
    # if the user specifies a bad p-value, we
    # should probably just use a default.
    return request.data['pvalue_rank']
  return settings.DEFAULT_P_VALUE



#require properly formatted URLs
@api_view(['POST'])
def scores_row_list(request):
  if request.method == 'POST': 
    print str(request.data)  #expect this to be a list of quoted strings...
    scoresrows_to_return = []
    cursor = connection.cursor()  # yep, manual SQL neded here too.

    pval_rank = get_p_value(request) 
    snpid_list = request.data['snpid_list']

    for one_snpid in snpid_list:
      #scoresrows = ScoresRow.objects.filter(snpid=one_snpid)
      cql = 'SELECT * from ' +                                       \
            settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_SNPID_QUERY']+ \
            ' where snpid = ' + repr(one_snpid.encode('ascii'))    + \
            ' and pval_rank < ' + str(pval_rank) + ' ALLOW FILTERING;'
      #print("CQL: " + cql)
      # example: :select snpid, chr, pos from snp_scores_3 where snpid = 'rs757310325' and pval_rank < 0.05 allow filtering;
     
      scoresrows = cursor.execute(cql).current_rows
                                   
      for matching_row_of_data in scoresrows:
        scoresrows_to_return.append(matching_row_of_data)
    if scoresrows_to_return is None or len(scoresrows_to_return) == 0:
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
    #execution should not reach this point if no data will be returned.
    scoresrows_to_return = order_rows_by_genomic_location(scoresrows_to_return)
    serializer = ScoresRowSerializer(scoresrows_to_return, many = True)
    return Response(serializer.data)
  else:
    #I may eventually be able to remove this case.
    return Response('not the right response', status=status.HTTP_400_BAD_REQUEST)

# TODO: cassandra should be handling this right now.
# filter by p-value:
def filter_by_pvalue(data_in, pvalue):
  to_return = [] 
  for one_row in data_in:
    if one_row['pval_rank'] <= pvalue:
     to_return.append(one_row)
  return to_return 

@api_view(['POST'])
def search_by_genomic_location(request):
  #Run some checks...
  if not all (k in request.data.keys() for k in ("chromosome","start_pos", "end_pos")):
    return Response('Must include chromosome, start, and end position.',
                     status = status.HTTP_400_BAD_REQUEST)

  start_pos = request.data['start_pos']
  end_pos = request.data['end_pos']
  chromosome = request.data['chromosome']  # TODO: check for invlaid chromosome
  pval_rank = get_p_value(request)

  if end_pos < start_pos:
    return Response('Start position is less than end position.',
                    status = status.HTTP_400_BAD_REQUEST)
 
  if end_pos - start_pos > settings.HARD_LIMITS['MAX_BASES_IN_GL_REQUEST']:
    return Response('Requested region is too large', 
                     status=status.HTTP_400_BAD_REQUEST)

   #'{:06.2f}'.format(3.141592653589793)  this would be a nice thing to do..
  cql = ' select * from '        +                                               \
        settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_GL_REGION_QUERY']            + \
        ' where chr = ' + repr(chromosome.encode('ascii'))                     + \
        ' and (pos, pval_rank) >= ('+ str(start_pos) + ',' + str(0)        +')' + \
        ' and (pos, pval_rank) <= ('+ str(end_pos)   + ',' + str(pval_rank)+')' + \
        ' ALLOW FILTERING;' 
          #consider adding a HARD LIMIT for general use.
          #does this actually work?
  print(cql)
  cursor = connection.cursor()
  scoresrows = cursor.execute(cql).current_rows  

  if scoresrows is None or len(scoresrows) == 0:
    return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
  else:
    scoresrows = filter_by_pvalue(scoresrows, pval_rank) 
    scoresrows = order_rows_by_genomic_location(scoresrows)
  serializer = ScoresRowSerializer(scoresrows, many = True)
  return Response(serializer.data, status=status.HTTP_200_OK )


