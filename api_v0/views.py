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
from SnpidQuery import SnpidQuery

#TRY to remove this.
# TODO: return an error if a p-value input is invalid.


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
    return setup_and_run_query(request, SnpidQuery)

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

@api_view(['POST'])
def search_by_gene_name(request):
    return setup_and_run_query(request, GeneNameQuery) 

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
    serializer = ScoresRowSerializer(es_result, many = False)
    data_to_return = serializer.data
    return Response(data_to_return, status=status.HTTP_200_OK)
