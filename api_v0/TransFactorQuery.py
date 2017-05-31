#Some of these imports may not be needed
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status 
import requests
import re
import json
from ElasticsearchQuery import ElasticsearchAtsnpQuery

class TransFactorQuery(ElasticsearchAtsnpQuery):

    def prepare_json_for_query(self):
        #use a try/catch here.
        return self.get_query_for_correct_tf_library()

    #should throw an Exception up if something is bad.
    def get_query_for_correct_tf_library(self):
        if self.request.data.get('tf_library') == 'encode':
            return self.query_for_encode()
        return self.query_for_jaspar()

    def query_for_jaspar(self):
        motif_str = self.prepare_motif_list() 
        j_dict = { "must" : {
                     "match" : {
                         "motif" : { "query": motif_str }
                      }
                    }
                 }
        return j_dict
         
    #This can have length > 1, but usually = 1.
    #This should spit by throwing an Exception.
    def prepare_motif_list(self):
        one_or_more_motifs = self.request.data.get('motif')
        if one_or_more_motifs is None: 
            return Response('No motif specified!', 
                            status = status.HTTP_400_BAD_REQUEST)    
        for motif in one_or_more_motifs: 
            test_match = re.match(r'M(\w+[.])+\w+', motif )
            if test_match is None: 
                return InvalidQueryError('No well-formed motifs.')
        return " ".join(one_or_more_motifs)
 
    #ENCODE TF searches specify only a prefix, not the whole motif name. 
    def query_for_encode(self):
        encode_prefix = self.request.data.get('motif')
        q =  {"must" : {
               "match_phrase_prefix" : { "motif" :   encode_prefix }
                }
             }
        return q 
