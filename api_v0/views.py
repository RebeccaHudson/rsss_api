from django.shortcuts import render
from api_v0.serializers import ScoresRowSerializer
from rest_framework import generics
from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.decorators import api_view 
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404
from django.conf import settings
from rest_framework import status 
import requests
import re
import json


# TODO: add an actual window size to each of the window-range searches.

# TODO: DRY-up building of elasticsearch URLs

def order_rows_by_genomic_location(rows): 
  return sorted(rows, key=lambda row: row['pos'])   # sort by age

def chunk(input, size):
  chunked =  map(None, *([iter(input)] * size))
  chunks_back = []
  print "chunked " + str(chunked)
  for one_chunk in chunked:
      if one_chunk is not None:
          chunks_back.append([ x.encode("ascii") for x in one_chunk if x is not None])
  print "chunks back  " + str(chunks_back)
  return chunks_back

# TODO: return an error if a p-value input is invalid.
def get_p_value(request):
  if request.data.has_key('pvalue_rank'):
    return request.data['pvalue_rank']
  return settings.DEFAULT_P_VALUE


def get_data_out_of_es_result(es_result):
    es_data = es_result.json()
    print("es result : " + str(es_data))
    print "es ruesult keys: "  + str(es_data.keys())
    if 'hits' in es_data.keys():
        return [ x['_source'] for x in es_data['hits']['hits'] ]
    return [] 



#TODO: consider adding the additional p-values
def prepare_json_for_pvalue_filter(pvalue_rank):
   dict_for_filter = { "filter": {
       "range" : {
           "pval_rank": {
               "lt":  str(pvalue_rank) 
           }
       }
   }  }
   return dict_for_filter 


def prepare_snpid_search_query_from_snpid_chunk(snpid_list, pvalue_rank):
    snp_list = snpid_list 
    filter_dict = prepare_json_for_pvalue_filter(pvalue_rank)
    query_dict = {
      "query": {
        "bool": {
          "must": {
               "terms": { "snpid" : snp_list }
          },
          "filter" : filter_dict["filter"]
        }
      }
    }
    print("query " + json.dumps(query_dict) )
    return json.dumps(query_dict) 


@api_view(['POST'])
def scores_row_list(request):
    #print str(request.data)  #expect this to be a list of quoted strings...
    scoresrows_to_return = []

    pval_rank = get_p_value(request) 
    snpid_list = request.data['snpid_list']
    chunked_snpid_list = chunk(snpid_list, 50) #TODO: parameterize chunk size somehow.
    url = settings.ELASTICSEARCH_URL + "/atsnp_data/" + "_search"
   
    for one_chunk  in chunked_snpid_list:
      es_query = prepare_snpid_search_query_from_snpid_chunk(one_chunk, pval_rank)  
      es_result = requests.post(url, data=es_query)
      scoresrows_to_return.extend(get_data_out_of_es_result(es_result))

    if scoresrows_to_return is None or len(scoresrows_to_return) == 0:
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
    
    serializer = ScoresRowSerializer(scoresrows_to_return, many = True)
    return Response(serializer.data)


def check_and_aggregate_gl_search_params(request):
  #print("here's the keys in the request data"  + str(request.data.keys()) )
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

def prepare_json_for_gl_query(gl_coords, pval_rank):
    pvalue_filter = prepare_json_for_pvalue_filter(pval_rank)
    j_dict = {   "query":
        {
            "bool" : {
                "must" : [
                   {
                     "range": {
                          "pos" : {  "from" : gl_coords['start_pos'], "to" : gl_coords['end_pos'] }
                      }
                   },
                   { "term" : { "chr" : gl_coords['chromosome'] } }
                ],
                "filter":  pvalue_filter["filter"]
            }
        }
    }
    json_out = json.dumps(j_dict)
    return json_out



@api_view(['POST'])
def search_by_genomic_location(request):
    gl_chunk_size = 100   # TODO: parametrize chunk size in the settings file.
    gl_coords_or_error_response = check_and_aggregate_gl_search_params(request)

    if not gl_coords_or_error_response.__class__.__name__  == 'dict':
        return gl_coords_or_error_response 

    pvalue = get_p_value(request) #use a default if an invalid value is requested.

    gl_coords = gl_coords_or_error_response
    es_query = prepare_json_for_gl_query(gl_coords, pvalue)
   
    url = settings.ELASTICSEARCH_URL + "/atsnp_data/" + "_search"
    es_result = requests.post(url, data=es_query)
    scoresrows = get_data_out_of_es_result(es_result)

    if scoresrows is None or len(scoresrows) == 0:
        return Response('No matches.', status=status.HTTP_204_NO_CONTENT)

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


def prepare_json_for_tf_query(motif_list, pval_rank):
    pvalue_filter = prepare_json_for_pvalue_filter(pval_rank)
    shoulds = []
    for one_motif in motif_list:
       shoulds.append({ "match" : { "motif" : one_motif } })
    j_dict={
        "query" : {
            "bool" : {
                "should" : shoulds,
                "filter" : pvalue_filter["filter"]
            } 
        }
    } 
    print "query for tf search : " + json.dumps(j_dict)
    return json.dumps(j_dict)



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
    es_query = prepare_json_for_tf_query(motif_list, pvalue)
    url = settings.ELASTICSEARCH_URL + "/atsnp_data/" + "_search"
    es_result = requests.post(url, data=es_query)
    scoresrows = get_data_out_of_es_result(es_result)

    if scoresrows is None or len(scoresrows) == 0: 
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
      
    serializer = ScoresRowSerializer(scoresrows, many = True)
    
    return Response(serializer.data, status=status.HTTP_200_OK )


def get_position_of_gene_by_name(gene_name):
    j_dict = { "query" : {
                   "match" : {
                       "gene_name" : gene_name    
                   }
                }
             } 
    url = settings.ELASTICSEARCH_URL + "/atsnp_data/gene_names/" + "_search"
    json_query = json.dumps(j_dict)
    print "query : " + json_query
    es_result = requests.post(url, data=json_query)   #returns empty list if no matches.
    gene_coords = get_data_out_of_es_result(es_result)
    if len(gene_coords) == 0: 
       return None
    return gene_coords[0]
     
@api_view(['POST'])
def search_by_gene_name(request):
    gene_name = request.data.get('gene_name')
    window_size = request.data.get('window_size')
    pvalue = get_p_value(request)

    if window_size is None:
        window_size = 0

    if gene_name is None:
        return Response('No gene name specified.', 
                        status = status.HTTP_400_BAD_REQUEST)

    gl_coords = get_position_of_gene_by_name(gene_name)
    if gl_coords is None: 
        return Response('Gene name not found in database.', 
                        status = status.HTTP_204_NO_CONTENT)

    gl_coords['chromosome'] = gl_coords['chr']
    es_query = prepare_json_for_gl_query(gl_coords, pvalue)
   
    url = settings.ELASTICSEARCH_URL + "/atsnp_data/atsnp_output/" + "_search"
    es_result = requests.post(url, data=es_query)
    scoresrows = get_data_out_of_es_result(es_result)

    if scoresrows is None or len(scoresrows) == 0:
        return Response('No matches.', status=status.HTTP_204_NO_CONTENT)

    serializer = ScoresRowSerializer(scoresrows, many = True)
    return Response(serializer.data, status=status.HTTP_200_OK )

    if scoresrows is None or len(scoresrows) == 0:
        return Response('Nothing for that gene.', status = status.HTTP_204_NO_CONTENT)



@api_view(['POST'])
def search_by_window_around_snpid(request):
    one_snpid = request.data.get('snpid')
    window_size = request.data.get('window_size')
    if window_size is None:
        window_size = 0
 
    if one_snpid is None: 
        return Response('No snpid specified.', 
                         status = status.HTTP_400_BAD_REQUEST)
    query_for_snpid_location = {"query":{"match":{"snpid":one_snpid }}}
    url = settings.ELASTICSEARCH_URL + "/atsnp_data/atsnp_output/" + "_search"
    es_query = json.dumps(query_for_snpid_location)
    es_result = requests.post(url, data=es_query)
    records_for_snpid = get_data_out_of_es_result(es_result)
    if len(records_for_snpid) == 0: 
        return Response('No data for snpid.' + one_snpid, 
                        status = status.HTTP_204_NO_CONTENT)
    gl_coords = records_for_snpid[0] 
    print "gl coords for snpid search " + str(gl_coords)































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
    cursor = connection.cursor()
    location_of_gene = cursor.execute(cql).current_rows
    return location_of_gene    #TODO: handle the case where a non-existing gene is specified.
    #chromosome = location_of_gene['chr']
    #start_pos = location_of_gene['start_pos']
    #end_pos = locatoin_of_gene['end_pos']   
     
