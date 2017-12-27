from rest_framework.response import Response
from api_v0.serializers import ScoresRowSerializer
from django.conf import settings
import requests
import random
import json

#make all the stuff in views.py use this class.
#NOTE: if it turns out that making a query to check if a server is response is 
#This is the way to do it.
#TOO overhead-intensive, use the following algorithm:
#  Fully formulate the URL as it would be used (randomly shuffle the ES boxes)
#     make the request as-is, and try/catch to detect timeout and/or connection errors.
#  If there's a dropped request; then pop the next machine off of the shuffled list of
#     available ES nodes; try that URL. 
#  Either end up returning the result set; or a 500 status Response with a descriptive
#  message about Elasticsearch being down.
class ElasticsearchURL(object):
    #if operation is None, id_to_get had better be there.
    #if scroll duration is included, this is a scrolling download.
    def __init__(self, data_type, operation="_search", 
                 from_result=None, page_size=None, id_to_get=None,
                 scroll_info=None):
         url_base  = self.get_base_es_url()
         name_of_index = None

         if data_type == 'atsnp_output':
             name_of_index = settings.ES_INDEX_NAMES['ATSNP_DATA']
         elif data_type == 'gencode_gene_symbols':
             name_of_index = settings.ES_INDEX_NAMES['GENE_NAMES']
         elif data_type == 'sequence':
             name_of_index = settings.ES_INDEX_NAMES['SNP_INFO']
         elif data_type == 'motif_bits':
             name_of_index = settings.ES_INDEX_NAMES['MOTIF_BITS']

         #print "url_base : " +  url_base
         #print "name_of_index: " +  name_of_index
         #print "data_type: " +  data_type
         #print "operation: " +  operation

         url_parts = [url_base, name_of_index, data_type]
         get_args = []

         if id_to_get is not None:
             #throw a nice exception if this is invalid?
             url_parts.append(id_to_get)
         else: 
             #this is a search.
             url_parts.append(operation)
             get_args.append(self.get_page_size(page_size))
             if scroll_info is not None:
                 if 'duration' in scroll_info:
                     get_args.append('scroll=' + scroll_info['duration'])
                 else:
                     #Use a bare URL to continue a scroll
                     get_args = []
                     url_parts = [url_base, operation]
                     url_parts.append('scroll')

             if from_result is not None:
                 get_args.append("from=" + str(from_result))

         bare_url = "/".join(url_parts)

         if len(get_args) > 0:
             self.url = '?'.join([bare_url,'&'.join(get_args)])
         else:
             self.url = bare_url
         #print "url created: " + self.url

    def setup_scroll_args(self, scroll_info):
        scroll_args = []
        if 'duration' in scroll_info:
            scroll_args.append('scroll=' + scroll_info['duration'])
        return scroll_args

    #for searches
    def get_page_size(self, page_size):
         if page_size is None:
             page_size = settings.ELASTICSEARCH_PAGE_SIZE
         return "size=" + str(page_size)

    def get_base_es_url(self):
       machines_to_try = settings.ELASTICSEARCH_URLS[:]
       random.shuffle(machines_to_try)
       return machines_to_try.pop()

    def get_url(self):
        return self.url

