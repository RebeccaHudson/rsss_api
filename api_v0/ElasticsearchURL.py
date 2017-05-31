from rest_framework.response import Response
from api_v0.serializers import ScoresRowSerializer
from DataReconstructor import DataReconstructor
from django.conf import settings
import requests
import json
#make all the stuff in views.py use this class.
class ElasticsearchURL(object):
    #def prepare_es_url(self, data_type, operation="_search", from_result=None, 
    #                   page_size=None):
    #     url_base = find_working_es_url()
    #     if url_base == None:
    #         return None
    #     #TODO: change back to main data store. (atsnp_data_tiny -> atsnp_data)
    #     url = url_base     + "/atsnp_reduced_test/" \
    #                        + data_type      \
    #                        + "/" + operation
    #     if page_size is None:
    #         page_size  =   settings.ELASTICSEARCH_PAGE_SIZE
    #     url = url + "?size=" + str(page_size)

    #     if from_result is not None:
    #         url = url + "&from=" + str(from_result) 
    #     print "es_url : " + url
    #     return url

    #does not sniff out if the URL works, just constructs it based on 
    #a pre-selected base URL.
    #def setup_es_url(self, data_type, url_base, operation="_search", 
    #                 from_result=None, page_size=None):
    #     #url = url_base     + "/atsnp_data_tiny/" \
    #     #                   + data_type      \
    #     #                   + "/" + operation
    #     url = url_base     + "/atsnp_reduced_test/" \
    #                        + data_type      \
    #                        + "/" + operation
    #     if page_size is None:
    #         page_size  =   settings.ELASTICSEARCH_PAGE_SIZE
    #     url = url + "?size=" + str(page_size)
    #     if from_result is not None:
    #         url = url + "&from=" + str(from_result) 
    #     return url
    def __init__(self, data_type, operation="_search", from_result=None, page_size=None):
         url_base  = self.find_working_es_url()
         url = url_base     + "/atsnp_reduced_test/" \
                            + data_type      \
                            + "/" + operation
         if page_size is None:
             page_size  =   settings.ELASTICSEARCH_PAGE_SIZE
         url = url + "?size=" + str(page_size)
         if from_result is not None:
             url = url + "&from=" + str(from_result) 
         self.url = url


    def find_working_es_url(self):
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

    def get_url(self):
        return self.url


class ElasticsearchResult(object):
    #returns a Response OR the data.
    def __init__(self, es_result):        
        es_data = es_result.json()
        print "es_data " + repr(es_data)
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

    # def get_data_out_of_es_result(es_result):
    #     es_data = es_result.json()
    #     #print("es result : " + str(es_data))
    #     #print "es ruesult keys: "  + str(es_data.keys())
    #     if 'hits' in es_data.keys():
    #         data =  [ x['_source'] for x in es_data['hits']['hits'] ]
    #         data_w_id = []
    #         for one_hit in es_data['hits']['hits']:
    #             one_hit_data = one_hit['_source']
    #             one_hit_data['id'] = one_hit['_id']
    #             if 'ref_and_snp_strand' in one_hit_data:
    #                 one_hit_data = DataReconstructor(one_hit_data).get_reconstructed_record()
    #             data_w_id.append(one_hit_data) 
    #         #print "data w/ id " + repr(data_w_id)
    #         hitcount = es_data['hits']['total']
    #         #try this? data['_id'] = es_data[' 
    #         #how should I include the _id field?
    #         #print "data : " + repr(data)
    #         return { 'data':data_w_id, 'hitcount': hitcount}
    #     else:
    #         print "no hits, then what is it? "
    #         print "es result : " + str(es_data)
    #     return { 'data' : None, 'hitcount': 0 }

    def get_data_out_of_es_result(self, result):
        print "result  " + repr(result)
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

    #This may not be appropriate inside of this class.
    #def return_any_hits(self, data_returned):
    #    if data_returned['hitcount'] == 0:
    #        self.result = Response('No matches.', status=status.HTTP_204_NO_CONTENT)
    #    if len(data_returned['data']) == 0:
    #        self.result = Response('Done paging all ' + \
    #                      str(data_returned['hitcount']) + 'results.',
    #                      status=status.HTTP_204_NO_CONTENT)

    #    serializer = ScoresRowSerializer(data_returned['data'], many = True)
    #    data_returned['data'] = serializer.data
    #    #print "called return any hits..."
    #    self.result = Response(data_returned, status=status.HTTP_200_OK)
    #    return self.result
