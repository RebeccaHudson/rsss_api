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
        snp_list = self.setup_snpid_list()
        return self.setup_snpid_query(snp_list)
      
    def setup_snpid_query(self, snp_list): 
        j_dict = { "must": {
                   "terms": { "snpid" : snp_list }
                 }}
        return j_dict

    def setup_snpid_list(self):
        snpid_list = self.request.data['snpid_list'] #why is .get not used here?
        snp_list = [ int(m.replace('rs', '')) for m in snpid_list]
        #TODO: raise an error if no properly formatted SNPids are present.
        return snp_list
