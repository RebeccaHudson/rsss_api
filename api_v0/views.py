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

#from elasticsearch import Elasticsearch, helpers

from AtsnpExceptions import *
from DataReconstructor import DataReconstructor
from GenomicLocationQuery import GenomicLocationQuery
from TransFactorQuery import TransFactorQuery
from SnpidWindowQuery import SnpidWindowQuery
from GeneNameQuery import GeneNameQuery
from SnpidQuery import SnpidQuery

from ElasticsearchURL import ElasticsearchURL


#pull the _id field here; put it in with the rest of the data.
def get_data_out_of_es_result(es_result, pull_motifs):
    es_data = es_result.json()
    print "keys in es data : " + repr(es_data.keys()) 
    if  'took' in es_data.keys():
        print "es took " + str(es_data['took'])
 
    if 'hits' in es_data.keys():
        motifs_pulled = {}
        data =  [ x['_source'] for x in es_data['hits']['hits'] ]
        data_w_id = []
        for one_hit in es_data['hits']['hits']:
            one_hit_data = one_hit['_source']
            one_hit_data['id'] = one_hit['_id']
            if 'ref_and_snp_strand' in one_hit_data:
                one_hit_data = \
                  DataReconstructor(one_hit_data).get_reconstructed_record()
            data_w_id.append(one_hit_data) 
            if pull_motifs:
                one_hit_data['motif_bits'] = \
                   grab_plotting_data_for_one_motif(one_hit['_id'], motifs_pulled )
                   #if pull_motifs is true, pull the motifs.
            else:
                one_hit_data['motif_bits'] = json.dumps({}) 
        hitcount = es_data['hits']['total']
        data_to_return = {'data' : data_w_id, 'hitcount': hitcount}
        if '_scroll_id' in es_data:   
            #send back a scroll id to continue a scroll in progress
            data_to_return['scroll_id'] = es_data['_scroll_id']
        return data_to_return 
    else:
        print "no hits..."
        print "es result : " + str(es_data)

    #The scroll_id will not be passed
    return { 'data' : None, 'hitcount': 0 } 

#Best to not jam this into the list comprehension below.
def is_this_the_motif_ic_filter(one_filter):
    if 'terms' in one_filter and 'motif_ic' in one_filter['terms']:
       return True 
    return False

def detect_and_remove_motif_ic_filter(query):
    #If motif_ic is there, remove it and return it as a string. 
    #otherwise, return  None
    if query.find('motif_ic') == -1:
        return None
    query = json.loads(query)
    filter_list = query['query']['bool']['filter']  
    new_filter = \
      [ one_filter for one_filter in filter_list if not \
         is_this_the_motif_ic_filter(one_filter) ] 
    query['query']['bool']['filter'] = new_filter
    return json.dumps(query) 
    

def return_any_hits(data_returned, pull_motifs, query=None):
    if data_returned['hitcount'] == 0:
        #if motif-ic is included; try a 1-element search without it.
        #Delete the key.
        query_minus_motif_ic_filter = detect_and_remove_motif_ic_filter(query)
        #Will be none if motif_ic filter was not included.
        if query is not None and query_minus_motif_ic_filter is not None:
           #if query contains the motif_ic filter key, then it will be deleted here.  
           peek_params = {'page_size':1, 'from_result': 0 }
           hits_without_ic_filtering = \
            query_elasticsearch(query_minus_motif_ic_filter, peek_params, False)
           if hits_without_ic_filtering.status_code is not 204:
               special_msg= 'INFO: No results match your query. However, if '+\
                        ' all of the levels of motif degeneracy '   +\
                     'were included, your search would return at least 1 result.'
               return Response(special_msg, status=207) 
        return Response('No matches.', status=status.HTTP_204_NO_CONTENT)

    if len(data_returned['data']) == 0:
        return Response('Done paging all ' + \
                      str(data_returned['hitcount']) + 'results.',
                      status=status.HTTP_204_NO_CONTENT)
    
    serializer = ScoresRowSerializer(data_returned['data'], many = True)
    data_returned['data'] = serializer.data
    return Response(data_returned, status=status.HTTP_200_OK)

#paging parameters are used on the ES URL.
def setup_paging_parameters(request):
    params = {}
    for one_key in ['from_result', 'page_size']:
        params[one_key] = request.data.get(one_key)
    return params


#Handle this without the Elasticsearch helpers
#Make sure the scroll ID gets passed back to the viewer app.
def setup_scrolling_download(search_url, complete_query):
    #print "complete query to setup scrolling download: " + str(complete_query)
    url = ElasticsearchURL('atsnp_output', page_size=1500,
                           scroll_info={'duration': '1m'}).get_url()
    url_to_use = url
    query_to_use = {'query' : json.loads(complete_query)['query'] }
    query_str = json.dumps(query_to_use) 
    pr = requests.post(url_to_use, data = query_str)   
    return pr 
     


#If there would be results, but there is not because of IC filtering, report this.
def query_elasticsearch(completed_query, es_params, pull_motifs):
    search_url = ElasticsearchURL('atsnp_output', 
                                  from_result = es_params['from_result'], 
                                  page_size = es_params['page_size']).get_url()
    es_result = None
    is_download = not pull_motifs   #TODO: explicitly add an is_download parameter..
    #if it is a download; call a function that streams the results.
    #if it's not a download: 
    try: 
        if is_download:
            es_result = setup_scrolling_download(search_url, completed_query) 
        else:
            es_result = requests.post(search_url, 
                                 data = completed_query, 
                                 timeout = 100)
    except requests.exceptions.Timeout:
        print "machine at " + esNode + " timed out without response." 
    except requests.exceptions.ConnectionError:
        print "machine at " + esNode + " refused connection." 
    else: 
        data_back = get_data_out_of_es_result(es_result, pull_motifs) 
        return return_any_hits(data_back, pull_motifs, completed_query)
   #Algorithm to save a few requests here and there is used for the deatil view.

def setup_and_run_query(request, query_class ):
    try:
        es_query = query_class(request).get_query()
    except InvalidQueryError as e:
        print "Responding with an Invalid query error: " + e.message
        return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
    except MissingBackendDataError as e:
        print "Missing Backend Data error: "  
        return Response("INFO: " + e.message, status=207 )
    #looks like no text responses can be sent with a 204
    except NoDataFoundError as e:
        print "Responding a No Data Found error: " + e.message
        return Response(e.message, status=status.HTTP_204_NO_CONTENT)
    es_params = setup_paging_parameters(request)  
    #print "  request to API " + repr(request.data) 
    pull_motifs = check_for_download(request) #if True, get motif plotting data.
    #pull motifs is false if this is a download.
    return query_elasticsearch(es_query, es_params, pull_motifs)

def check_for_download(request):
    if 'for_download' in request.data and request.data['for_download']:
        return False 
    return True 

@api_view(['POST'])
def search_by_trans_factor(request):
   return setup_and_run_query(request, TransFactorQuery)

@api_view(['POST'])
def search_by_gene_name(request):
    return setup_and_run_query(request, GeneNameQuery) 

@api_view(['POST'])
def search_by_window_around_snpid(request):
    return setup_and_run_query(request, SnpidWindowQuery) 

#a refactor of scrores_row_list
@api_view(['POST'])
def search_by_snpid(request):
    return setup_and_run_query(request, SnpidQuery)

@api_view(['POST'])
def search_by_genomic_location(request):
    return setup_and_run_query(request, GenomicLocationQuery)

#No query is needed here. Just get the scroll ID and go from there.
@api_view(['POST'])
def continue_scrolling_download(request):
    #Throw an error if scroll_id is not included.
    #No other parameters should be included with the scroll continuation.
    sid = request.data.get('scroll_id')

    #the continuing of a scroll isn't supposed to include a data type.
    url = ElasticsearchURL('atsnp_output', scroll_info={}).get_url()

    q = { 'scroll_id' : sid, 'scroll' : '3m' }
    q_str = json.dumps(q)
    es_result = requests.post(url, data = q_str) 
    pull_motifs = False  #This is for downloads; no need to include motifs.
    data_back = get_data_out_of_es_result(es_result, pull_motifs) 
    return return_any_hits(data_back, pull_motifs)



def get_one_item_from_elasticsearch_by_id(index_name, doc_type, id_of_item):
        try: 
            #queries for single datum details use elasticsearch's GET API.
            search_url = ElasticsearchURL(doc_type, id_to_get=id_of_item).get_url()
            es_result = requests.get(search_url, timeout=100)
        except requests.exceptions.Timeout:
            print "machine at " + esNode + " timed out without response." 
        except requests.exceptions.ConnectionError:
            print "machine at " + esNode + " refused connection." 
        else: 
            return es_result


#Motif is pulled from doc_id, if the motif to retireve is already present in
#the 'motifs pulled' dict, it will be retrieved from there, not from Elastic.
def grab_plotting_data_for_one_motif(for_doc_id, motifs_pulled=None):
    which_motif = for_doc_id.split('_rs')[0]
    if motifs_pulled is not None and which_motif in motifs_pulled:
        motif_data = motifs_pulled[which_motif]
    else: 
        motif_data = \
           get_one_item_from_elasticsearch_by_id('motif_plotting_data', 
                                                 'motif_bits', which_motif)
        motif_data = motif_data.json()

        motif_data = motif_data['_source']
        my_dict = motif_data
        motif_data = \
          {  str(k):(str(v) if             \
             isinstance(v, unicode) else v)\
             for k,v in my_dict.items()
          }
        motif_data = json.dumps(motif_data['plotting_bits'])
    
        if motifs_pulled is not None: 
            motifs_pulled['which_motif'] = motif_data
    return motif_data

#Motif bits should ALWAYS come with the detail view. 
@api_view(['POST'])
def details_for_one(request):
    id_to_get_data_for = request.data.get('id_string')
    
    data_returned =\
     get_one_item_from_elasticsearch_by_id(
          settings.ES_INDEX_NAMES['ATSNP_DATA'], 
          'atsnp_output', id_to_get_data_for)

    data_returned = data_returned.json()
    single_hit = data_returned['_source']    
    single_hit['id'] = data_returned['_id'] 
    es_result = DataReconstructor(single_hit).get_reconstructed_record()

    es_result['motif_bits'] = \
          grab_plotting_data_for_one_motif(id_to_get_data_for)

    serializer = ScoresRowSerializer(es_result, many = False)
    data_to_return = serializer.data
    return Response(data_to_return, status=status.HTTP_200_OK)
