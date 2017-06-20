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

from ElasticsearchURL import ElasticsearchURL




#pull the _id field here; put it in with the rest of the data.
def get_data_out_of_es_result(es_result, pull_motifs):
    es_data = es_result.json()
    #print("es result : " + str(es_data))
    #print "es ruesult keys: "  + str(es_data.keys())
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
        return { 'data':data_w_id, 'hitcount': hitcount}
    else:
        print "no hits..."
        print "es result : " + str(es_data)
    return { 'data' : None, 'hitcount': 0 } 

def return_any_hits(data_returned, pull_motifs):
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

#paging parameters are used on the ES URL.
def setup_paging_parameters(request):
    params = {}
    for one_key in ['from_result', 'page_size']:
        params[one_key] = request.data.get(one_key)
    return params

#TODO: factor this out into a 'helper' file, it's not strictly a view.
#es_params is a dict with from_result and page_size
#TODO: add a standard parametrized elasticsearch timeout from settings.
def query_elasticsearch(completed_query, es_params, pull_motifs):
    search_url = ElasticsearchURL('atsnp_output', 
                                  from_result = es_params['from_result'], 
                                  page_size = es_params['page_size']).get_url()
    try: 
        es_result = requests.post(search_url, 
                                  data = completed_query, 
                                  timeout = 100)
    except requests.exceptions.Timeout:
        print "machine at " + esNode + " timed out without response." 
    except requests.exceptions.ConnectionError:
        print "machine at " + esNode + " refused connection." 
    else: 
        data_back = get_data_out_of_es_result(es_result, pull_motifs) 
        return return_any_hits(data_back, pull_motifs)
   #Algorithm to save a few requests here and there is used for the deatil view.

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
    pull_motifs = check_for_download(request) #if True, get motif plotting data.
    return query_elasticsearch(es_query, es_params, pull_motifs)

def check_for_download(request):
    #print "dir(request)" + repr(dir(request))
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

def get_one_item_from_elasticsearch_by_id(index_name, doc_type, id_of_item):
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
            search_url = '/'.join([url_base, index_name, doc_type, id_of_item])
            #print "querying single item for detail view with url : " + search_url
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
    #print "these methods avaliable : " + repr(dir(data_returned))
    single_hit = data_returned['_source']    
    single_hit['id'] = data_returned['_id'] 
    es_result = DataReconstructor(single_hit).get_reconstructed_record()

    es_result['motif_bits'] = \
          grab_plotting_data_for_one_motif(id_to_get_data_for)

    #print "data_returned  " + repr(es_result)
    serializer = ScoresRowSerializer(es_result, many = False)
    data_to_return = serializer.data
    return Response(data_to_return, status=status.HTTP_200_OK)
