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

from DataReconstructor import DataReconstructor
from GenomicLocationQuery import GenomicLocationQuery

#TRY to remove this.
# TODO: return an error if a p-value input is invalid.

def get_pvalue_dict(request):
    pv_dict = {}
    #print "request " + str(request.data)
    for pv_name in ['rank', 'ref', 'snp']:
        key  = "_".join(['pvalue', pv_name])
        if request.data.has_key(key):
            pv_dict[key] = request.data[key]

    if 'pvalue_rank'not in pv_dict:
        pv_dict[key] = settings.DEFAULT_P_VALUE
 
    if request.data.has_key('pvalue_snp_direction'):
       pv_dict['pvalue_snp_direction'] = request.data['pvalue_snp_direction'] 

    if request.data.has_key('pvalue_ref_direction'):
       pv_dict['pvalue_ref_direction'] = request.data['pvalue_ref_direction']

    return pv_dict     


#pull the _id field here; put it in with the rest of the data.
def get_data_out_of_es_result(es_result):
    es_data = es_result.json()
    #print("es result : " + str(es_data))
    #print "es ruesult keys: "  + str(es_data.keys())
    if 'hits' in es_data.keys():
        data =  [ x['_source'] for x in es_data['hits']['hits'] ]
        data_w_id = []
        for one_hit in es_data['hits']['hits']:
            one_hit_data = one_hit['_source']
            one_hit_data['id'] = one_hit['_id']
            if 'ref_and_snp_strand' in one_hit_data:
                one_hit_data = DataReconstructor(one_hit_data).get_reconstructed_record()
            data_w_id.append(one_hit_data) 
        #print "data w/ id " + repr(data_w_id)
        hitcount = es_data['hits']['total']
        #try this? data['_id'] = es_data[' 
        #how should I include the _id field?
        #print "data : " + repr(data)
        return { 'data':data_w_id, 'hitcount': hitcount}
    else:
        print "no hits, then what is it? "
        print "es result : " + str(es_data)
    return { 'data' : None, 'hitcount': 0 } 



def prepare_json_for_pvalue_filter(pvalue_rank):
   dict_for_filter = { "filter": {
       "range" : {
           "pval_rank": {
               "lte":  str(pvalue_rank) 
           }
       }
   }  }
   return dict_for_filter 

#TODO: make a copy of this function that can take the pvalue_snp_direction
#       and the pvalue_ref_direction and applies the filter directions.
#       ONLY apply the filter directions if the pvalue_ref and pvalue_snp 
#       values are defined in their respective inputs. (see code below)
def prepare_json_for_pvalue_filter_directional(pvalue_dict):
   #pvalue_snp is missing at this point..
   #print "prior to processing " + str(pvalue_dict)
   dict_for_filter = { "filter": [
     {
       "range" : {
           "pval_rank": {
               "lte":  str(pvalue_dict['pvalue_rank']) 
           }
       }
     }
   ]
   }
   if 'pvalue_ref' in  pvalue_dict:
       pvalue_ref_direction = pvalue_dict['pvalue_ref_direction']
       if pvalue_ref_direction == 'lt' and pvalue_dict['pvalue_ref'] == 0:
           pvalue_ref_direction = 'lte' 
       #either lte or gte
       dict_for_filter['filter'].append({
           "range" : {
               "pval_ref": {
                   pvalue_ref_direction:  str(pvalue_dict['pvalue_ref']) 
               }
           }
       })
   if 'pvalue_snp' in pvalue_dict:  
       pvalue_snp_direction = pvalue_dict['pvalue_snp_direction']
       if pvalue_snp_direction == 'lt' and pvalue_dict['pvalue_snp'] == 0:
           pvalue_snp_direction = 'lte' #don't exclude records w/ pvalue = 0
       dict_for_filter['filter'].append({
       "range" : {
           "pval_snp": {
               pvalue_snp_direction:  str(pvalue_dict['pvalue_snp']) 
                      }
                 }
       })
   #print "(changed) alternative pvalue_filter: " + str(dict_for_filter)
   return dict_for_filter 

def prepare_json_for_sort():
    dict_for_sort = {
                      "sort" : [ { "pval_rank" : { "order" : "asc" } }, 
                                 { "chr"       : { "order" : "asc" } },
                                 { "pos"       : { "order" : "asc" } } ]
                    }
    return dict_for_sort

#TODO: replace prepare_for_sort completely with the following method.
def prepare_json_for_custom_sort(sort_orders):
    print "sort order? " + repr(sort_orders)
    #'coordinate' means 'chr' and 'pos'
    so = sort_orders['sort']
    for i, x  in enumerate(so):
        print "i: " + str(i)
        print "x: " + str(x)
        if x.keys()[0] == 'coordinate':
            print "translating" #  x['coordinate']
            #get a copy of the order dict
            x[u'chr'] = x['coordinate']
            pos = { u'pos' : x['coordinate'] }
            where_to_put = i + 1
            del x['coordinate']
            print repr(so)
            break
    so.insert(where_to_put, pos)
    sort_orders['sort'] = so
    #sort_orders['sort']['coordinate']
    #any processing required?
    print "supposed to be completed sort order: " + repr(sort_orders)
    return sort_orders


def prepare_snpid_search_query_from_snpid_chunk(snpid_list, pvalue_dict, sort_info=None):
    #snp_list = snpid_list 

    snp_list = [ int(m.replace('rs', '')) for m in snpid_list]
    pvalue_filter = use_appropriate_pvalue_filter_function(pvalue_dict)
    sort = prepare_json_for_sort()
    if sort_info is not None:
        print "using custom sort! " + repr(sort)
        sort =  prepare_json_for_custom_sort(sort_info)
    query_dict = {
      "sort" : sort["sort"],
      "query": {
        "bool": {
          "must": {
               "terms": { "snpid" : snp_list }
          },
          "filter" : pvalue_filter["filter"]
        }
      }
    }
    print("query " + json.dumps(query_dict) )
    return json.dumps(query_dict) 





#sometimes one of the ES urls is non-responsive.
#detect and respond to this situation appropriately.
def find_working_es_url():
    found_working = False
    name_of_es_index = 'atsnp_reduced_test'
    i = 0 
    while found_working is False:
        #TODO: change back to main data store. (atsnp_data_tiny -> atsnp_data)
        url_to_try = settings.ELASTICSEARCH_URLS[i] + \
                      '/' + name_of_es_index  + '/atsnp_output/_search?size=1'
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
     url = url_base     + "/atsnp_reduced_test/" \
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
     #url = url_base     + "/atsnp_data_tiny/" \
     #                   + data_type      \
     #                   + "/" + operation
     url = url_base     + "/atsnp_reduced_test/" \
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
def search_by_snpid(request):
    pvalue_dict = get_pvalue_dict(request)
    snpid_list = request.data['snpid_list']
    sort_order = request.data.get('sort_order')
    es_query = prepare_snpid_search_query_from_snpid_chunk(snpid_list,
                                                        pvalue_dict, 
                                                        sort_info=sort_order)  
    es_params = { 'from_result' : request.data.get('from_result'),
                  'page_size'   : request.data.get('page_size')}
    return query_elasticsearch(es_query, es_params)
  
#does this really get used?
#YES. It does not handle anything with/about pvalues.
def check_and_aggregate_gl_search_params(request):
    if not all (k in request.data.keys() for k in ("chromosome","start_pos", "end_pos")):
        return Response('Must include chromosome, start, and end position.',
                       status = status.HTTP_400_BAD_REQUEST)
    gl_coords =  {}
    gl_coords['start_pos'] = request.data['start_pos']
    gl_coords['end_pos'] = request.data['end_pos']
    gl_coords['chromosome'] =  request.data['chromosome']  # TODO: check for invlaid chromosome
    #Chromosomes are numeric as stored in the minimized data set.
    gl_coords['chromosome'] = gl_coords['chromosome'].replace('ch', '') 
    #does it explcitly need to be an int?

    if not gl_coords['chromosome'].isdigit():   #could be pulled out into another function.
        non_numeric_chromosomes = { 'X' : 23, 'Y': 24, 'M': 25, 'MT': 25 }
        gl_coords['chromosome'] = non_numeric_chromosomes[gl_coords['chromosome']]

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
                          "pos" : {  "from" : gl_coords['start_pos'], 
                                       "to" : gl_coords['end_pos'] }
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




#try to use 'filter' queries to speed this up.
def prepare_json_for_gl_query_multi_pval(gl_coords, pval_dict, sort_info=None):
    pvalue_filter = None
    #print "whole contents of pval_dict: " + repr(pval_dict)
    #THIS is temporary until I have directional on everything.
    #print "gl query: pval dict: " + repr(pval_dict)
    pvalue_filter = use_appropriate_pvalue_filter_function(pval_dict)

    sort = prepare_json_for_sort()
    if sort_info is not None:
        print "using custom sort! " + repr(sort)
        sort =  prepare_json_for_custom_sort(sort_info)

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
    json_out = json.dumps(j_dict)
    #print "dict before query : " + json_out
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
    #print "called return any hits..."
    return Response(data_returned, status=status.HTTP_200_OK)


#refactor this one first.
@api_view(['POST'])
def search_by_genomic_location(request):
    #TODO: completely remove 'GL chunk size' this is here because I was trying
    # to use Cassandra for this.
    gl_coords_or_error_response = check_and_aggregate_gl_search_params(request)
    if not gl_coords_or_error_response.__class__.__name__  == 'dict':
        return gl_coords_or_error_response 

    pvalue_dict = get_pvalue_dict(request)
    gl_coords = gl_coords_or_error_response
    from_result = request.data.get('from_result')
    page_size = request.data.get('page_size')
    sort_order = request.data.get('sort_order')

    # The following code was copied into the bottom of search_by_snpid_window
    # TODO: consider DRYing up this part of the code
    es_query = prepare_json_for_gl_query_multi_pval(gl_coords, pvalue_dict)

    es_params = setup_paging_parameters(request) 
    es_query = GenomicLocationQuery(request).get_query()
    #print "this is the not-working query " + repr(es_query)
    #url stuff is handled in query_elasticsearch.
    #print "about to gl query elasticsearch " + repr(es_query)
    return query_elasticsearch(es_query, es_params)

#paging parameters are used on the ES URL.
def setup_paging_parameters(request):
    params = {}
    for one_key in ['from_result', 'page_size']:
        params[one_key] = request.data.get(one_key)
    return params

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

#Apply directions for the SNP and reference pvalue filters if present.
def use_appropriate_pvalue_filter_function(pval_dict):
    pvalue_filter = None 
    #directions always go in; even if the number is not present.
    pvalue_filter = prepare_json_for_pvalue_filter_directional(pval_dict)
    return pvalue_filter

def prepare_json_for_tf_query(motif_list, pval_dict, sort_info=None):

    pvalue_filter = use_appropriate_pvalue_filter_function(pval_dict)
    sort = prepare_json_for_sort()
    if sort_info is not None:
        print "using custom sort! " + repr(sort)
        sort =  prepare_json_for_custom_sort(sort_info)
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

def prepare_json_for_encode_tf_query(encode_prefix, pval_dict, sort_info=None):

    pvalue_filter = use_appropriate_pvalue_filter_function(pval_dict)
    sort = prepare_json_for_sort()
    if sort_info is not None:
        print "using custom sort! " + repr(sort)
        sort =  prepare_json_for_custom_sort(sort_info)
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
def search_by_trans_factor(request):
    pvalue_dict = get_pvalue_dict(request)

    #If we're suppsoed to check for a valid ENCODE motif, we'll see the flag:
    if request.data.get('tf_library') == 'encode':
        return search_by_encode_trans_factor(request,  pvalue_dict)

    #currently specific to JASPAR.
    motif_or_error_response = check_and_return_motif_value(request)
    if not type(motif_or_error_response) == list:
        return motif_or_error_response   #it's an error response    

    motif_list = motif_or_error_response       # above established this is a motif. 
  
    sort_order = request.data.get('sort_order')
    es_query = prepare_json_for_tf_query(motif_list, pvalue_dict, sort_info=sort_order)
    
    es_params = { 'from_result' : request.data.get('from_result'),
                  'page_size' : request.data.get('page_size') }
    return query_elasticsearch(es_query, es_params)



#There is no ENCODE data right now...
#TODO: thorough testing with actual ENCODE data.
#This is here to avoid reworking the logic in search_by_trans_factor
#add custom sorting!
def search_by_encode_trans_factor(request,  pvalue_dict):
    motif_prefix = request.data.get('motif')
    sort_order = request.data.get('sort_order')
    es_query = prepare_json_for_encode_tf_query(motif_prefix, pvalue_dict, sort_info=sort_order) 
    #print "query for encode TF : " + es_query
    es_params = { 'from_result' : request.data.get('from_result'),
                  'page_size'   : request.data.get('page_size')  }
    return query_elasticsearch(es_query, es_params)


#TODO: complete adapting this function; it should WORK.
def get_position_of_gene_by_name(gene_name):
    j_dict = { "query" : {
                   "match" : {
                       "gene_symbol" : gene_name    
                   }
                }
             } 

    json_query = json.dumps(j_dict)
    #es_url = prepare_es_url('gencode_gene_symbols') 
   
    url_base = find_working_es_url()
    operation = '_search'
    data_type = 'gencode_gene_symbols'
    es_url = url_base  + "/gencode_genes/" \
                        + data_type      \
                        + "/" + operation
    #should be just one result..
    #print "query : " + json_query
    #print "es url " + es_url
    es_result = requests.post(es_url, data=json_query, timeout=50) 
    gene_coords = get_data_out_of_es_result(es_result)
    if gene_coords['hitcount'] == 0: 
         #print "gene not found : " + gene_name
         return None
    gc = gene_coords['data'][0]
 
    gc['chr'] = gc['chr'].replace('chr', '')
    if not gc['chr'].isdigit():   #could be pulled out into another function.
        non_numeric_chromosomes = { 'X' : 23, 'Y': 24, 'M': 25, 'MT': 25 }
        gc['chr'] = non_numeric_chromosomes[gc['chr']]

    gl_coords = { 'chromosome': gc['chr'], #gc['chr'].replace('chr', ''), # gc['chr'].replace('hr', 'h') ,
                  'start_pos' : gc['start_pos'] ,
                  'end_pos'   : gc['end_pos']     }
    return gl_coords 
     


@api_view(['POST'])
def search_by_gene_name(request):
    gene_name = request.data.get('gene_name')
    window_size = request.data.get('window_size')
    pvalue_dict = get_pvalue_dict(request)
    sort_order = request.data.get('sort_order')

    print "sort order: " + repr(sort_order)
    #load as json? or is it already?

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

    #print "gl coordinates " + repr(gl_coords)
    es_query = prepare_json_for_gl_query_multi_pval(gl_coords, pvalue_dict, sort_info=sort_order)
    return query_elasticsearch(es_query, es_params)


@api_view(['POST'])
def search_by_window_around_snpid(request):
    one_snpid = request.data.get('snpid')
    numeric_snpid = one_snpid.replace('rs', '') #to compensate for our optimizations
    window_size = request.data.get('window_size')
    pvalue_dict = get_pvalue_dict(request)
    
    if window_size is None:
        window_size = 0
 
    if numeric_snpid is None: 
        return Response('No snpid specified.', 
                         status = status.HTTP_400_BAD_REQUEST)

    #This URL is for looking up the genomic location of a SNPid. 
    #has to be re-prepared for pageable search.
    es_url = prepare_es_url('atsnp_output') 



    #if elasticsearch is down, find out now. 
    if es_url is None:
        return Response('Elasticsearch is down, please contact admins.', 
                         status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #query_for_snpid_location = {"query":{"match":{"snpid":one_snpid }}}
    query_for_snpid_location = {"query":{"match":{"snpid":numeric_snpid }}}
    es_query = json.dumps(query_for_snpid_location)
    es_result = requests.post(es_url, data=es_query, timeout=100)
    records_for_snpid = get_data_out_of_es_result(es_result)

    if len(records_for_snpid['data']) == 0: 
        return Response('No data for snpid ' + one_snpid + '.', 
                        status = status.HTTP_204_NO_CONTENT)

    record_to_pick = records_for_snpid['data'][0]
    record_to_pick['chr'] = record_to_pick['chr'].replace('ch', '') #Account for minimized data
    gl_coords = { 'chromosome' :  record_to_pick['chr'],
                  'start_pos'  :  record_to_pick['pos'] - window_size,
                  'end_pos'    :  record_to_pick['pos'] + window_size
                 }
    if gl_coords['start_pos'] < 0:
        #: TODO consider adding a warning here if this happens?
        gl_coords['start_pos'] = 0

    #TRY ADDING THE DIRECTIONAL HERE?
    
    es_query = prepare_json_for_gl_query_multi_pval(gl_coords, pvalue_dict)
    #print "es query for snpid window search " + es_query
   
    es_params = { 'page_size' : request.data.get('page_size'),
                  'from_result' : request.data.get('from_result') }
    #This probably isn't the right place to put the from result
    return query_elasticsearch(es_query, es_params)


def get_one_item_from_elasticsearch_by_id(id_of_item):
    #copied verbatim from the above method; should be refactored.
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
        try: 
            #queries for single datum details use elasticsearch's GET API.
            url_base = esNode
            #search_url = url_base + "/atsnp_data_tiny/atsnp_output/" + id_of_item
            search_url = url_base + "/atsnp_reduced_test/atsnp_output/" + id_of_item
            #print "querying single item for detail view with url : " + search_url
            es_result = requests.get(search_url, timeout=100)
        except requests.exceptions.Timeout:
            print "machine at " + esNode + " timed out without response." 
        except requests.exceptions.ConnectionError:
            print "machine at " + esNode + " refused connection." 
        else: 
            return es_result

@api_view(['POST'])
def details_for_one(request):
    id_to_get_data_for = request.data.get('id_string')
    #print "querying details for ID =  " + id_to_get_data_for
    data_returned = get_one_item_from_elasticsearch_by_id(id_to_get_data_for)
    data_returned = data_returned.json()
   
    single_hit = data_returned['_source']    
    single_hit['id'] = data_returned['_id'] 
    es_result = DataReconstructor(single_hit).get_reconstructed_record()

    #print "data_returned  " + repr(es_result)
    #serializer = ScoresRowSerializer(data_returned['_source'], many = False)
    serializer = ScoresRowSerializer(es_result, many = False)
    data_to_return = serializer.data
    return Response(data_to_return, status=status.HTTP_200_OK)
