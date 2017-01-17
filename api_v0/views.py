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
import signal
import requests
import re
import json
import random

# TODO: add an actual window size to each of the window-range searches.


def chunk(input, size):
  chunked =  map(None, *([iter(input)] * size))
  chunks_back = []
  #print "chunked " + str(chunked)
  for one_chunk in chunked:
      if one_chunk is not None:
          chunks_back.append([ x.encode("ascii") for x in one_chunk if x is not None])
  #print "chunks back  " + str(chunks_back)
  return chunks_back

# TODO: return an error if a p-value input is invalid.
def get_p_value(request):
  if request.data.has_key('pvalue_rank'):
    return request.data['pvalue_rank']
  return settings.DEFAULT_P_VALUE


def get_data_out_of_es_result(es_result):
    es_data = es_result.json()
    #print("es result : " + str(es_data))
    #print "es ruesult keys: "  + str(es_data.keys())
    if 'hits' in es_data.keys():
        data =  [ x['_source'] for x in es_data['hits']['hits'] ]
        hitcount = es_data['hits']['total']
        return { 'data':data, 'hitcount': hitcount}
    else:
        print "no hits, then what is it? "
        print "es result : " + str(es_data)
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

def prepare_json_for_sort():
    dict_for_sort = {
                      "sort" : [ { "pval_rank" : { "order" : "asc" } }, 
                                 { "chr"       : { "order" : "asc" } },
                                 { "pos"       : { "order" : "asc" } } ]
                    }
    return dict_for_sort

def prepare_snpid_search_query_from_snpid_chunk(snpid_list, pvalue_rank):
    snp_list = snpid_list 
    filter_dict = prepare_json_for_pvalue_filter(pvalue_rank)
    sort = prepare_json_for_sort()
    query_dict = {
      "sort" : sort["sort"],
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





#sometimes one of the ES urls is non-responsive.
#detect and respond to this situation appropriately.
def find_working_es_url():
    found_working = False
    i = 0 
    while found_working is False:
        #TODO: change back to main data store. (atsnp_data_tiny -> atsnp_data)
        url_to_try = settings.ELASTICSEARCH_URLS[i] + \
                      '/atsnp_data_tiny/atsnp_output/_search?size=1'
        print "trying this url " + url_to_try
        es_check_response = None
        try:
            es_check_response = requests.get(url_to_try, timeout=300)  
        except requests.exceptions.Timeout:
            print "request for search at : " + url_to_try +  " timed out."  
        except requests.exceptions.ConnectionError:
            print "request for " + url_to_try + " has been refused"
        else:        
            #print "url " + url_to_try + " es_check_response" + str(json.loads(es_check_response.text))
            es_check_data = json.loads(es_check_response.text)
            return settings.ELASTICSEARCH_URLS[i]
        i += 1
        if i > 2: 
            return None

#prepares elasticsearch urls
#from result should just be passed in from whatever is using this API.
#we'll have to ensure that any such user has sufficient information to do so.


#TODO: Make this not place unneeded requests on ES. Only hit > 1 URL
#if a connection is rejected / times out
#TODO: successfuly complete deprecating this method
def prepare_es_url(data_type, operation="_search", from_result=None, 
                   page_size=None):
     url_base = find_working_es_url()
     if url_base == None:
         return None
     #TODO: change back to main data store. (atsnp_data_tiny -> atsnp_data)
     url = url_base     + "/atsnp_data_tiny/" \
                        + data_type      \
                        + "/" + operation
     if page_size is None:
         page_size  =   settings.ELASTICSEARCH_PAGE_SIZE
     url = url + "?size=" + str(page_size)

     if from_result is not None:
         url = url + "&from=" + str(from_result) 
     print "es_url : " + url
     return url

#does not sniff out if the URL works, just constructs it based on 
#a pre-selected base URL.
def setup_es_url(data_type, url_base, operation="_search", 
                 from_result=None, page_size=None):
     url = url_base     + "/atsnp_data_tiny/" \
                        + data_type      \
                        + "/" + operation
     if page_size is None:
         page_size  =   settings.ELASTICSEARCH_PAGE_SIZE
     url = url + "?size=" + str(page_size)
     if from_result is not None:
         url = url + "&from=" + str(from_result) 
     return url


#a refactor of scrores_row_list
@api_view(['POST'])
def alternate_search_by_snpid(request):
    #print str(request.data)  #expect this to be a list of quoted strings...
    pval_rank = get_p_value(request) 
    snpid_list = request.data['snpid_list']

    es_query = prepare_snpid_search_query_from_snpid_chunk(snpid_list, pval_rank)  
    es_params = { 'from_result' : request.data.get('from_result'),
                  'page_size'   : request.data.get('page_size')}
    return query_elasticsearch(es_query, es_params)
  

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


#try to use 'filter' queries to speed this up.
def prepare_json_for_gl_query(gl_coords, pval_rank):
    pvalue_filter = prepare_json_for_pvalue_filter(pval_rank)
    sort = prepare_json_for_sort()
    j_dict = {   
        "sort" : sort["sort"], 
        "query":
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
    #j_dict = { "filtered" : j_dict }
    #j_dict = { "query" : j_dict }
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
    print "called return any hits..."
    return Response(data_returned, status=status.HTTP_200_OK)


#refactor this one first.
@api_view(['POST'])
def alternate_search_by_genomic_location(request):
    #TODO: completely remove 'GL chunk size' this is here because I was trying
    # to use Cassandra for this.
    gl_coords_or_error_response = check_and_aggregate_gl_search_params(request)
    if not gl_coords_or_error_response.__class__.__name__  == 'dict':
        return gl_coords_or_error_response 

    pvalue = get_p_value(request) #use a default if an invalid value is requested.
    gl_coords = gl_coords_or_error_response
    from_result = request.data.get('from_result')
    page_size = request.data.get('page_size')

    # The following code was copied into the bottom of search_by_snpid_window
    # TODO: consider DRYing up this part of the code
    es_query = prepare_json_for_gl_query(gl_coords, pvalue)
    es_params = { 'from_result' : from_result, 
                  'page_size'   : page_size }

    #url stuff is handled in query_elasticsearch.
    return query_elasticsearch(es_query, es_params)


#TODO: factor this out into a 'helper' file, it's not strictly a view.
#es_params is a dict with from_result and page_size
#TODO: add a standard parametrized elasticsearch timeout from settings.
def query_elasticsearch(completed_query, es_params):
    #prepare es_url should be something that we pass a machine-to-try into
    #make a copy of the list to shuffle
    machinesToTry = settings.ELASTICSEARCH_URLS[:]      
    random.shuffle(machinesToTry)   #try machines in different order. 
    keepTrying = True
    while keepTrying is True:
        if machinesToTry:
            esNode = machinesToTry.pop()
        else: 
            keepTrying = False
            return Response('No Elasticsearch machines responded. Contact Admins.', 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            continue #stop looping...
        #esNode specifies the elasticSearch node we will attempt to search.
        search_url = setup_es_url('atsnp_output', esNode,
                               from_result = es_params['from_result'], 
                               page_size = es_params['page_size'])
        try: 
            es_result = requests.post(search_url, 
                                      data = completed_query, 
                                      timeout = 100)
        except requests.exceptions.Timeout:
            print "machine at " + esNode + " timed out without response." 
        except requests.exceptions.ConnectionError:
            print "machine at " + esNode + " refused connection." 
        else: 
            data_back = get_data_out_of_es_result(es_result) 
            return return_any_hits(data_back)
                                      

# this can be > 1, but is usually = 1.
def check_and_return_motif_value(request):
    one_or_more_motifs = request.data.get('motif')
    #print("type of motif param: " + str(type(one_or_more_motifs)))
    #print("one or more motifs: " + str(one_or_more_motifs))
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
    sort = prepare_json_for_sort()
    motif_str = " ".join(motif_list)
    j_dict={
        "sort" : sort["sort"],
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
    return json.dumps(j_dict)

def prepare_json_for_encode_tf_query(encode_prefix, pval_rank):
    pvalue_filter = prepare_json_for_pvalue_filter(pval_rank)
    sort = prepare_json_for_sort()
    j_dict={
        "sort" : sort["sort"],
        "query" : {
            "bool" : {
                 "must" : {
                   "match_phrase_prefix" : {
                       "motif" :   encode_prefix 
                    }
                   
                  },
                 "filter" : pvalue_filter["filter"]
            } 
        }
    } 
    return json.dumps(j_dict)


#  Web interface translates motifs to transcription factors and vice-versa
#  this API expects motif values. 
@api_view(['POST'])
def alternate_search_by_trans_factor(request):
    pvalue = get_p_value(request)

    #If we're suppsoed to check for a valid ENCODE motif, we'll see the flag:
    #    request.data.get('tf_library') == 'encode':
    #    return search_by_encode_trans_factor(request, es_url, pvalue)

    #currently specific to JASPAR.
    motif_or_error_response = check_and_return_motif_value(request)
    if not type(motif_or_error_response) == list:
        return motif_or_error_response   #it's an error response    

    motif_list = motif_or_error_response       # above established this is a motif. 
    es_query = prepare_json_for_tf_query(motif_list, pvalue)
    
    es_params = { 'from_result' : request.data.get('from_result'),
                  'page_size' : request.data.get('page_size') }
    return query_elasticsearch(es_query, es_params)



#There is no ENCODE data right now...
#TODO: thorough testing with actual ENCODE data.
#This is here to avoid reworking the logic in search_by_trans_factor
def search_by_encode_trans_factor(request, es_url,  pvalue):
    motif_prefix = request.data.get('motif')
    es_query = prepare_json_for_encode_tf_query(motif_prefix, pvalue) 
    print "query for encode TF : " + es_query
    try:
        es_result = requests.post(es_url, data=es_query, timeout=100)
    except requests.exceptions.Timeout:
        return Response('Elasticsearch timed out. Contact admins.',
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    data_back = get_data_out_of_es_result(es_result)
    return return_any_hits(data_back)



def get_position_of_gene_by_name(gene_name):
    j_dict = { "query" : {
                   "match" : {
                       "gene_symbol" : gene_name    
                   }
                }
             } 
    json_query = json.dumps(j_dict)
    es_url = prepare_es_url('gencode_gene_symbols') 
    #print "query : " + json_query
    es_result = requests.post(es_url, data=json_query, timeout=50) 
    gene_coords = get_data_out_of_es_result(es_result)
    if gene_coords['hitcount'] == 0: 
         return None
    gc = gene_coords['data'][0]
    gl_coords = { 'chromosome': gc['chr'].replace('hr', 'h') ,
                  'start_pos' : gc['start_pos'] ,
                  'end_pos'   : gc['end_pos']     }
    return gl_coords 
     


@api_view(['POST'])
def alternate_search_by_gene_name(request):
    gene_name = request.data.get('gene_name')
    window_size = request.data.get('window_size')
    pvalue = get_p_value(request)

    if window_size is None:
        window_size = 0

    if gene_name is None:
        return Response('No gene name specified.', 
                        status = status.HTTP_400_BAD_REQUEST)

    es_params = {   'page_size' :   request.data.get('page_size'),
                    'from_result' : request.data.get('from_result') }

    #TODO: refactor the way that this checks for gene names in ES.
    gl_coords = get_position_of_gene_by_name(gene_name)
    if gl_coords is None: 
        return Response('Gene name not found in database.', 
                        status = status.HTTP_400_BAD_REQUEST)
    #print "continued gene name search after Respnose.."

    gl_coords['start_pos'] = int(gl_coords['start_pos']) - window_size
    gl_coords['end_pos'] = int(gl_coords['end_pos']) + window_size

    es_query = prepare_json_for_gl_query(gl_coords, pvalue)
    return query_elasticsearch(es_query, es_params)


@api_view(['POST'])
def alternate_search_by_window_around_snpid(request):
    one_snpid = request.data.get('snpid')
    window_size = request.data.get('window_size')
    pvalue = get_p_value(request)



    if window_size is None:
        window_size = 0
 
    if one_snpid is None: 
        return Response('No snpid specified.', 
                         status = status.HTTP_400_BAD_REQUEST)

    #This URL is for looking up the genomic location of a SNPid. 
    #has to be re-prepared for pageable search.
    es_url = prepare_es_url('atsnp_output') 

    #if elasticsearch is down, find out now. 
    if es_url is None:
        return Response('Elasticsearch is down, please contact admins.', 
                         status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    query_for_snpid_location = {"query":{"match":{"snpid":one_snpid }}}
    es_query = json.dumps(query_for_snpid_location)
    es_result = requests.post(es_url, data=es_query, timeout=100)
    records_for_snpid = get_data_out_of_es_result(es_result)

    if len(records_for_snpid['data']) == 0: 
        return Response('No data for snpid ' + one_snpid + '.', 
                        status = status.HTTP_204_NO_CONTENT)

    record_to_pick = records_for_snpid['data'][0]
    gl_coords = { 'chromosome' :  record_to_pick['chr'],
                  'start_pos'  :  record_to_pick['pos'] - window_size,
                  'end_pos'    :  record_to_pick['pos'] + window_size
                 }
    if gl_coords['start_pos'] < 0:
        #: TODO consider adding a warning here if this happens?
        gl_coords['start_pos'] = 0

    es_query = prepare_json_for_gl_query(gl_coords, pvalue)
    #print "es query for snpid window search " + es_query
   
    es_params = { 'page_size' : request.data.get('page_size'),
                  'from_result' : request.data.get('from_result') }
    #This probably isn't the right place to put the from result
    return query_elasticsearch(es_query, es_params)


