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

import re


from cassandra import ConsistencyLevel
from cassandra.query import SimpleStatement

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
 
def chunk(input, size):
  return map(None, *([iter(input)] * size))


# TODO: return an error if a p-value input is invalid.
def get_p_value(request):
  if request.data.has_key('pvalue_rank'):
    # consider some validation here...
    # if the user specifies a bad p-value, we
    # should probably just use a default.
    return request.data['pvalue_rank']
  return settings.DEFAULT_P_VALUE


def setup_in_clause(list_chunk, stringify=False, quote=False):
  if not stringify and not quote:
    raise ValueError("Must specify to stringify or quote.")
  items_to_query = []
  if stringify:
    items_to_query = [ str(x) for x in list_chunk if x is not None]
  if quote:
    items_to_query = [ repr(x.encode('ascii')) for x in list_chunk if x is not None]
  in_clause = "(" + ", ".join(items_to_query)   + ")"  
  return in_clause


#require properly formatted URLs
@api_view(['POST'])
def scores_row_list(request):
  snpids_in_one_in_clause = 4

  if request.method == 'POST': 
    print str(request.data)  #expect this to be a list of quoted strings...
    scoresrows_to_return = []
    cursor = connection.cursor()  # yep, manual SQL neded here too.

    pval_rank = get_p_value(request) 
    snpid_list = request.data['snpid_list']
    chunked_snpid_list = chunk(snpid_list, snpids_in_one_in_clause) 

    for one_chunk  in chunked_snpid_list:
      #scoresrows = ScoresRow.objects.filter(snpid=one_snpid)
      in_clause = setup_in_clause(one_chunk, quote=True)
      
      cql = 'SELECT * from ' +                                       \
            settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_SNPID_QUERY']+ \
            ' where snpid in ' + in_clause                         + \
            ' and pval_rank <= ' + str(pval_rank) + ' ALLOW FILTERING;'
      # existing where clause before using IN
      # ' where snpid = ' + repr(one_snpid.encode('ascii'))    + \

      #print("CQL: " + cql)
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


def check_and_aggregate_gl_search_params(request):
  print("here's the keys in the request data"  + str(request.data.keys()) )
  if not all (k in request.data.keys() for k in ("chromosome","start_pos", "end_pos")):
    return Response('Must include chromosome, start, and end position.',
                     status = status.HTTP_400_BAD_REQUEST)
  gl_coords =  {}
  gl_coords['start_pos'] = request.data['start_pos']
  gl_coords['end_pos'] = request.data['end_pos']
  gl_coords['chromosome'] = request.data['chromosome']  # TODO: check for invlaid chromosome
  gl_coords['pval_rank'] = get_p_value(request)

  if gl_coords['end_pos'] < gl_coords['start_pos']:
    return Response('Start position is less than end position.',
                    status = status.HTTP_400_BAD_REQUEST)
 
  if gl_coords['end_pos'] - gl_coords['start_pos'] > settings.HARD_LIMITS['MAX_BASES_IN_GL_REQUEST']:
    return Response('Requested region is too large', 
                     status=status.HTTP_400_BAD_REQUEST)
  return gl_coords



def process_search_by_genomic_location(gl_coords):
  cql = ' select * from '                                                 + \
      settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_GL_REGION_QUERY']         + \
      ' where chr = ' + repr(gl_coords['chr'].encode('ascii'))     + \
      ' and pos <='   + str(gl_coords['end_pos'])                         + \
      ' and pos >= '      + str(gl_coords['start_pos'])                   + \
      ' ALLOW FILTERING;' 
  cursor = connection.cursor()
  scoresrows = cursor.execute(cql).current_rows  
  return filter_by_pvalue(scoresrows, gl_coords['pval_rank']) 




@api_view(['POST'])
def search_by_genomic_location(request):
  gl_chunk_size = 100   # TODO: parametrize chunk size in the settings file.
  gl_coords_or_error_response = check_and_aggregate_gl_search_params(request)
  if not gl_coords_or_error_response.__class__.__name__  == 'dict':
      return gl_coords_or_error_response 

  pvalue = get_p_value(request) #use a default if an invalid value is requested.
  gl_coords = gl_coords_or_error_response

  # this is now sure to be a dict with the search temrs in it.
  #int_range = list(range(gl_coords['start_pos'], gl_coords['end_pos']))
  #chunked_gl_segments = chunk(int_range, gl_chunk_size)
  #scoresrows_to_return = []  

  #for one_chunk in chunked_gl_segments:
  #      in_clause = setup_in_clause(one_chunk, stringify=True)
  #      cql = ' select * from '                                                 + \
  #          settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_GL_REGION_QUERY']         + \
  #          ' where chr = ' + repr(gl_coords['chromosome'].encode('ascii'))     + \
  #          ' and pos <='   + str(gl_coords['end_pos'])                         + \
  #          ' and pos >= '      + str(gl_coords['start_pos'])                   + \
  #          ' ALLOW FILTERING;' 
  #      print(cql)
  #      # original version without using the IN clause..
  #      #' and (pos, pval_rank) >= ('+ str(gl_coords['start_pos']) + ',' + str(0)        +')' + \
  #      #' and (pos, pval_rank) <= ('+ str(gl_coords['end_pos'])   + ',' + str(gl_coords['pval_rank'])+')' + \
  #      cursor = connection.cursor()
  #      query = SimpleStatement(cql, consistency_level=ConsistencyLevel.LOCAL_SERIAL)
  #      #scoresrows = cursor.execute(cql).current_rows  
  #      scoresrows = cursor.execute(query).current_rows  
  #      scoresrows_to_return.extend(scoresrows) 
  #  
  #scoresrows = scoresrows_to_return

  scoresrows = process_search_by_genomic_location(gl_coords) 
  #factored out this logic to simplify coding other range-based searches.
  if scoresrows is None or len(scoresrows) == 0:
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)

  scoresrows = order_rows_by_genomic_location(scoresrows)
  serializer = ScoresRowSerializer(scoresrows, many = True)
  return Response(serializer.data, status=status.HTTP_200_OK )


# this can be > 1, but is usually = 1.
def check_and_return_motif_value(request):
    one_or_more_motifs = request.data.get('motif')
    print("type of motif param: " + str(type(one_or_more_motifs)))
    print("one or more motifs: " + str(one_or_more_motifs))
    if one_or_more_motifs is None: 
        return Response('No motif specified!', 
                        status = status.HTTP_400_BAD_REQUEST)    
    for motif in one_or_more_motifs: 
        test_match = re.match(r'M(\w+[.])+\w+', motif )
        if test_match is None: 
            return Response('No well-formed motifs.', 
                          status = status.HTTP_400_BAD_REQUEST) 
    return one_or_more_motifs 

#  Web interface translates motifs to transcription factors and vice-versa
#  this API expects motif values. 
@api_view(['POST'])
def search_by_trans_factor(request):
    motif_or_error_response = check_and_return_motif_value(request)
    print('motif or error response is : ' + str(type(motif_or_error_response)))
    if not type(motif_or_error_response) == list:
        return motif_or_error_response   #it's an error response    

    pvalue = get_p_value(request)
    motif_list = motif_or_error_response # above established this is a motif. 
    #motif_str = ", ".join([ repr(x.encode('ascii')) for x in motif])
    #in_clause = " in (" + motif_str + ")"
    # This may need some actual paging going on for this...
    scoresrows_to_return = []

    for one_motif in motif_list:
        cql = ' select * from '                                    +\
              settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_TF_QUERY'] +\
              ' where motif = ' + repr(one_motif.encode('ascii'))  +\
              ' and pval_rank <= ' + str(pvalue)                   +\
              ' allow filtering;' 
        print(cql)
        cursor = connection.cursor()
        scoresrows = cursor.execute(cql).current_rows
        scoresrows_to_return.extend(scoresrows)

    if scoresrows_to_return is None or len(scoresrows_to_return) == 0:
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
      
    scoresrows_to_return = order_rows_by_genomic_location(scoresrows_to_return)
    serializer = ScoresRowSerializer(scoresrows_to_return, many = True)
    
    return Response(serializer.data, status=status.HTTP_200_OK )

def get_position_of_gene_by_name(gene_name):
    cursor = connection.cursor()
    location_of_gene = cursor.execute(cql).current_rows
    return location_of_gene    #TODO: handle the case where a non-existing gene is specified.
    #chromosome = location_of_gene['chr']
    #start_pos = location_of_gene['start_pos']
    #end_pos = locatoin_of_gene['end_pos']   
     
@api_view(['POST'])
def search_by_gene_name(request):
    gene_name = request.data.get('gene_name')
    pvalue = get_p_value(request)
    if gene_name is None:
        return Response('No gene name specified.', 
                        status = status.HTTP_400_BAD_REQUEST)
    window_size = 0  #just select the feature
    gl_parameters = get_position_of_gene_by_name(gene_name)
    matches = process_search_by_genomic_location(gene_name) 
    if matches is None or len(matches) == 0:
        return Response('Nothing for that gene.', status = status.HTTP_204_NO_CONTENT)
    serializer = ScoresRowSerializer(



























@api_view(['POST'])
def get_plotting_data_for_snpid(request):
    #the plotting data will not have pvalues on it...
    # TODO probably change this to include the motif in the lookup?
    snpid_requested = request.data.get('snpid')
    if snpid_requested is None:
        return Response('No snpid specified.', 
                          status = status.HTTP_400_BAD_REQUEST) 
    snpid_requested = snpid_requested.encode('ascii')
    cql = 'select * from '                                    +\
    settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_PLOTTING_DATA'] +\
    ' where snpid = ' + repr(snpid_requested)+';'
>>>>>>> Stashed changes
    cursor = connection.cursor()
    location_of_gene = cursor.execute(cql).current_rows
    return location_of_gene    #TODO: handle the case where a non-existing gene is specified.
    #chromosome = location_of_gene['chr']
    #start_pos = location_of_gene['start_pos']
    #end_pos = locatoin_of_gene['end_pos']   
     
@api_view(['POST'])
def search_by_gene_name(request):
    gene_name = request.data.get('gene_name')
    pvalue = get_p_value(request)
    if gene_name is None:
        return Response('No gene name specified.', 
                        status = status.HTTP_400_BAD_REQUEST)
    window_size = 0  #just select the feature
    gl_parameters = get_position_of_gene_by_name(gene_name)
    matches = process_search_by_genomic_location(gene_name) 
    if matches is None or len(matches) == 0:
        return Response('Nothing for that gene.', status = status.HTTP_204_NO_CONTENT)
    serializer = ScoresRowSerializer(
































