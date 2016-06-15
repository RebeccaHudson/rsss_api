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
    #print "es ruesult keys: "  + str(es_data.keys())
    if 'hits' in es_data.keys():
        data =  [ x['_source'] for x in es_data['hits']['hits'] ]
        hitcount = es_data['hits']['total']
        return { 'data':data, 'hitcount': hitcount}
    return { 'data' : None, 'hitcount': 0 } 



#TODO: consider adding the additional p-values
def prepare_json_for_pvalue_filter(pvalue_rank):
   dict_for_filter = { "filter": {
       "range" : {
           "pval_rank": {
               "lte":  str(pvalue_rank) 
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


#prepares elasticsearch urls
#from result should just be passed in from whatever is using this API.
#we'll have to ensure that any such user has sufficient information to do so.
def prepare_es_url(data_type, operation="_search", from_result=None):
     url = settings.ELASTICSEARCH_URL + "/atsnp_data/" \
                                      + data_type      \
                                      + "/" + operation

     url = url + "?size=" + str(settings.ELASTICSEARCH_PAGE_SIZE)
     if from_result is not None:
         url = url + "&from=" + str(from_result) 
     print "es_url : " + url
     return url





@api_view(['POST'])
def scores_row_list(request):
    #print str(request.data)  #expect this to be a list of quoted strings...
    scoresrows_to_return = []

    pval_rank = get_p_value(request) 
    snpid_list = request.data['snpid_list']
    chunked_snpid_list = chunk(snpid_list, 50) #TODO: parameterize chunk size somehow.
   
    for one_chunk  in chunked_snpid_list:
      es_query = prepare_snpid_search_query_from_snpid_chunk(one_chunk, pval_rank)  
      es_result = requests.post(prepare_es_url('atsnp_output'), data=es_query)
      scoresrows_to_return.extend(get_data_out_of_es_result(es_result))

    if scoresrows_to_return is None or len(scoresrows_to_return) == 0:
      return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
    
    serializer = ScoresRowSerializer(scoresrows_to_return, many = True)
    return Response(serializer.data)


def check_and_aggregate_gl_search_params(request):
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


def return_any_hits(data_returned):
    if data_returned['hitcount'] == 0:
        return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
    if len(data_returned['data']) == 0:
        return Response('Done paging all ' + \
                      str(data_returned['hitcount']) + 'results.',
                      status=status.HTTP_204_NO_CONTENT)
    serializer = ScoresRowSerializer(data_returned['data'], many = True)
    data_returned['data'] = serializer.data
    return Response(data_returned, status=status.HTTP_200_OK)

@api_view(['POST'])
def search_by_genomic_location(request):
    
    gl_chunk_size = 100   # TODO: parametrize chunk size in the settings file.
    gl_coords_or_error_response = check_and_aggregate_gl_search_params(request)

    if not gl_coords_or_error_response.__class__.__name__  == 'dict':
        return gl_coords_or_error_response 

    pvalue = get_p_value(request) #use a default if an invalid value is requested.

    gl_coords = gl_coords_or_error_response
    from_result = request.data.get('from_result')

    # The following code was copied into the bottom of search_by_snpid_window
    # TODO: consider DRYing up this part of the code
    es_query = prepare_json_for_gl_query(gl_coords, pvalue)
    es_result = requests.post(
                         prepare_es_url('atsnp_output', from_result=from_result),
                         data=es_query)
    data_back = get_data_out_of_es_result(es_result)
    return return_any_hits(data_back)

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
    motif_str = " ".join(motif_list)
    j_dict={
        "query" : {
            "bool" : {
                 "must" : {
                   "match" : {
                       "motif" : { "query": motif_str }
                   }
                  },
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
    if not type(motif_or_error_response) == list:
        return motif_or_error_response   #it's an error response    
    from_result = request.data.get('from_result')
    pvalue = get_p_value(request)
    motif_list = motif_or_error_response       # above established this is a motif. 

    es_query = prepare_json_for_tf_query(motif_list, pvalue)
    es_result = requests.post(prepare_es_url('atsnp_output', from_result=from_result),
                              data=es_query)
    data_back = get_data_out_of_es_result(es_result)
    return return_any_hits(data_back)


def get_position_of_gene_by_name(gene_name):
    j_dict = { "query" : {
                   "match" : {
                       "gene_name" : gene_name    
                   }
                }
             } 
    json_query = json.dumps(j_dict)
    #print "query : " + json_query
    es_result = requests.post(prepare_es_url('gene_names'), data=json_query) 
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
   
    es_result = requests.post(prepare_es_url('atsnp_output'), data=es_query)
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
    pvalue = get_p_value(request)

    if window_size is None:
        window_size = 0
 
    if one_snpid is None: 
        return Response('No snpid specified.', 
                         status = status.HTTP_400_BAD_REQUEST)

    query_for_snpid_location = {"query":{"match":{"snpid":one_snpid }}}
    es_query = json.dumps(query_for_snpid_location)
    es_result = requests.post(prepare_es_url('atsnp_output'), data=es_query)
    records_for_snpid = get_data_out_of_es_result(es_result)

    if len(records_for_snpid) == 0: 
        return Response('No data for snpid ' + one_snpid + '.', 
                        status = status.HTTP_204_NO_CONTENT)

    record_to_pick = records_for_snpid[0] 
    gl_coords = { 'chromosome' :  record_to_pick['chr'],
                  'start_pos'  :  record_to_pick['pos'] - window_size,
                  'end_pos'    :  record_to_pick['pos'] + window_size
                 }
    if gl_coords['start_pos'] < 0:
        #: TODO consider adding a warning here if this happens?
        gl_coords['start_pos'] = 0

    # Any other checks needed before search by snpid?

    # copied from the function to search by genomic location
    es_query = prepare_json_for_gl_query(gl_coords, pvalue)
   
    es_result = requests.post(prepare_es_url('atsnp_output'), data=es_query)
    scoresrows = get_data_out_of_es_result(es_result)

    if scoresrows is None or len(scoresrows) == 0:
        #Unlikely, since the snp had to be looked up for this query to be run.
        return Response('No matches.', status=status.HTTP_204_NO_CONTENT)

    serializer = ScoresRowSerializer(scoresrows, many = True)
    return Response(serializer.data, status=status.HTTP_200_OK )




# TODO: revive the potting code!!

@api_view(['POST'])
def get_plotting_data_for_snpid(request):
    pass
    #the plotting data will not have pvalues on it...
    # TODO probably change this to include the motif in the lookup?
    #snpid_requested = request.data.get('snpid')
    #if snpid_requested is None:
    #    return Response('No snpid specified.', 
    #                      status = status.HTTP_400_BAD_REQUEST) 
    #snpid_requested = snpid_requested.encode('ascii')
    #cql = 'select * from '                                    +\
    #settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_PLOTTING_DATA'] +\
    #' where snpid = ' + repr(snpid_requested)+';'
    #cursor = connection.cursor()
    #location_of_gene = cursor.execute(cql).current_rows
    #return location_of_gene    #TODO: handle the case where a non-existing gene is specified.
    #chromosome = location_of_gene['chr']
    #start_pos = location_of_gene['start_pos']
    #end_pos = locatoin_of_gene['end_pos']   
     
