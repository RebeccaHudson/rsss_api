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

from AtsnpExceptions import *
from DataReconstructor import DataReconstructor
from GenomicLocationQuery import GenomicLocationQuery
from TransFactorQuery import TransFactorQuery
from SnpidWindowQuery import SnpidWindowQuery
from GeneNameQuery import GeneNameQuery

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


#Should be a class...

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

@api_view(['POST'])
def search_by_genomic_location(request):
    return setup_and_run_query(request, GenomicLocationQuery)

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

#Apply directions for the SNP and reference pvalue filters if present.
def use_appropriate_pvalue_filter_function(pval_dict):
    pvalue_filter = None 
    #directions always go in; even if the number is not present.
    pvalue_filter = prepare_json_for_pvalue_filter_directional(pval_dict)
    return pvalue_filter

def setup_and_run_query(request, query_class ):
    try:
        es_query = query_class(request).get_query()
    except InvalidQueryError as e:
        print "Responding with an Invalid query error: " + e.message
        return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
    except NoDataFoundError as e:
        print "Responding a No Data Found error: " + e.message
        return Response(e.message, status=status.HTTP_204_NO_CONTENT)
    es_params = setup_paging_parameters(request) 
    return query_elasticsearch(es_query, es_params)


#  Web interface translates motifs to transcription factors and vice-versa
#  this API expects motif values. 
@api_view(['POST'])
def search_by_trans_factor(request):
   return setup_and_run_query(request, TransFactorQuery)
   # es_query = TransFactorQuery(request).get_query()
   # es_params = setup_paging_parameters(request) 
   # return query_elasticsearch(es_query, es_params)

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
    return setup_and_run_query(request, GeneNameQuery) 
    #gene_name = request.data.get('gene_name')
    #window_size = request.data.get('window_size')
    #pvalue_dict = get_pvalue_dict(request)
    #sort_order = request.data.get('sort_order')

    #print "sort order: " + repr(sort_order)
    ##load as json? or is it already?

    #if window_size is None:
    #    window_size = 0

    #if gene_name is None:
    #    return Response('No gene name specified.', 
    #                    status = status.HTTP_400_BAD_REQUEST)

    #es_params = {   'page_size' :   request.data.get('page_size'),
    #                'from_result' : request.data.get('from_result') }

    ##TODO: refactor the way that this checks for gene names in ES.
    #gl_coords = get_position_of_gene_by_name(gene_name)
    #if gl_coords is None: 
    #    return Response('Gene name not found in database.', 
    #                    status = status.HTTP_400_BAD_REQUEST)
    ##print "continued gene name search after Respnose.."
    #gl_coords['start_pos'] = int(gl_coords['start_pos']) - window_size
    #gl_coords['end_pos'] = int(gl_coords['end_pos']) + window_size

    ##print "gl coordinates " + repr(gl_coords)
    #es_query = prepare_json_for_gl_query_multi_pval(gl_coords, pvalue_dict, sort_info=sort_order)
    #return query_elasticsearch(es_query, es_params)


@api_view(['POST'])
def search_by_window_around_snpid(request):
    return setup_and_run_query(request, SnpidWindowQuery) 

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
