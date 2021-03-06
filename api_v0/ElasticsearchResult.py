from rest_framework.response import Response
from api_v0.serializers import ScoresRowSerializer
from DataReconstructor import DataReconstructor
from django.conf import settings
import requests
import random
import json

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
