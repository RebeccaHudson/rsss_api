#Some of these imports may not be needed
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status 
import requests
import re
import json

from ElasticsearchQuery import ElasticsearchAtsnpQuery
from DataReconstructor import DataReconstructor

class SnpidQuery(ElasticsearchAtsnpQuery):
    def prepare_json_for_query(self):
        #use a try/catch here.
        snp_list = self.setup_snpid_list()
        print "snp list before setting up query : " + repr(snp_list)
        return self.setup_snpid_query(snp_list)
      
    def setup_snpid_query(self, snp_list): 
        j_dict = { "must": {
                   "terms": { "snpid" : snp_list }
                 }}
        print "j_dict " + repr(j_dict)
        return j_dict

    def setup_snpid_list(self):
        snpid_list = self.request.data['snpid_list'] #why is .get not used here?
        print "snpid list " + repr(snpid_list)
        snp_list = [ int(m.replace('rs', '')) for m in snpid_list]
        return snp_list

##BEGIN STUFF FOR SNPID SEARCH
#    def prepare_snpid_search_query_from_snpid_chunk(snpid_list, pvalue_dict, sort_info=None):
#        #snp_list = snpid_list 
#
#        snp_list = [ int(m.replace('rs', '')) for m in snpid_list]
#        pvalue_filter = use_appropriate_pvalue_filter_function(pvalue_dict)
#        sort = prepare_json_for_sort()
#        if sort_info is not None:
#            print "using custom sort! " + repr(sort)
#            sort =  prepare_json_for_custom_sort(sort_info)
#        query_dict = {
#          "sort" : sort["sort"],
#          "query": {
#            "bool": {
#              "must": {
#                   "terms": { "snpid" : snp_list }
#              },
#              "filter" : pvalue_filter["filter"]
#            }
#          }
#        }
#        print("query " + json.dumps(query_dict) )
#        return json.dumps(query_dict) 
#
#
#        #a refactor of scrores_row_list
#        @api_view(['POST'])
#        def search_by_snpid(request):
#            pvalue_dict = get_pvalue_dict(request)
#            snpid_list = request.data['snpid_list']
#            sort_order = request.data.get('sort_order')
#            es_query = prepare_snpid_search_query_from_snpid_chunk(snpid_list,
#                                                                pvalue_dict, 
#                                                                sort_info=sort_order)  
#            es_params = { 'from_result' : request.data.get('from_result'),
#                          'page_size'   : request.data.get('page_size')}
#            return query_elasticsearch(es_query, es_params)
##END STUFF FOR SNPID SEARCH
