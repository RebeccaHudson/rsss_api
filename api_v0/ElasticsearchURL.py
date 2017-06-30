from rest_framework.response import Response
from api_v0.serializers import ScoresRowSerializer
from DataReconstructor import DataReconstructor
from django.conf import settings
import requests
import random
import json

#make all the stuff in views.py use this class.
#NOTE: if it turns out that making a query to check if a server is response is 
#TOO overhead-intensive, use the following algorithm:
#  Fully formulate the URL as it would be used (randomly shuffle the ES boxes)
#     make the request as-is, and try/catch to detect timeout and/or connection errors.
#  If there's a dropped request; then pop the next machine off of the shuffled list of
#     available ES nodes; try that URL. 
#  Either end up returning the result set; or a 500 status Response with a descriptive
#  message about Elasticsearch being down.
class ElasticsearchURL(object):
    def __init__(self, data_type, operation="_search", 
                 from_result=None, page_size=None):

         url_base  = self.find_working_es_url()
         name_of_index = None

         if data_type == 'atsnp_output':
             name_of_index = settings.ES_INDEX_NAMES['ATSNP_DATA']
         elif data_type == 'gencode_gene_symbols':
             name_of_index = settings.ES_INDEX_NAMES['GENE_NAMES']
         #elif data_type == 'sequence':
         #    name_of_index = settings.ES_INDEX_NAMES['SNP_INFO']

         url = "/".join([url_base, name_of_index, data_type, operation])

         if page_size is None:
             page_size  =   settings.ELASTICSEARCH_PAGE_SIZE

         url = url + "?size=" + str(page_size)

         if from_result is not None:
             url = url + "&from=" + str(from_result) 
         self.url = url

    def find_working_es_url(self):
       machines_to_try = settings.ELASTICSEARCH_URLS[:]
       random.shuffle(machines_to_try)
       while len(machines_to_try) > 0:
           machine_to_try = machines_to_try.pop()
           url_to_try = '/'.join([machine_to_try,
                                  settings.ES_INDEX_NAMES['ATSNP_DATA'],
                                  'atsnp_output','_search?size=1'])
           es_check_response = None
           try:
               es_check_response = requests.get(url_to_try, timeout=50)  
           except requests.exceptions.Timeout:
               print "request for search at : " + url_to_try +  " timed out."  
           except requests.exceptions.ConnectionError:
               print "request for " + url_to_try + " has been refused"
           else:        
               return machine_to_try
           return None

    def get_url(self):
        return self.url

class ElasticsearchResult(object):
    #returns a Response OR the data.
    def __init__(self, es_result):        
        es_data = es_result.json()
        #print "es_data " + repr(es_data)
        if 'hits' in es_data.keys():
            data =  [ x['_source'] for x in es_data['hits']['hits'] ]
            data_w_id = []
            for one_hit in es_data['hits']['hits']:
                one_hit_data = one_hit['_source']
                one_hit_data['id'] = one_hit['_id']
                if 'ref_and_snp_strand' in one_hit_data:
                    one_hit_data = DataReconstructor(one_hit_data).get_reconstructed_record()
                data_w_id.append(one_hit_data) 
            hitcount = es_data['hits']['total']
            self.result = { 'data':data_w_id, 'hitcount': hitcount}
        else:
            self.result = { 'data' : None, 'hitcount': 0 }

    def get_result(self):
        return self.result

    def get_data_out_of_es_result(self, result):
        if data_returned['hitcount'] == 0:
            return Response('No matches.', status=status.HTTP_204_NO_CONTENT)
        if len(data_returned['data']) == 0:
            return Response('Done paging all ' + \
                          str(data_returned['hitcount']) + 'results.',
                          status=status.HTTP_204_NO_CONTENT)

        serializer = ScoresRowSerializer(data_returned['data'], many = True)
        data_returned['data'] = serializer.data

        return Response(data_returned, status=status.HTTP_200_OK)
