#Some of these imports may not be needed
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status 
from AtsnpExceptions import *
import requests
#import re
import json

#Change the name of that file.
from ElasticsearchURL import ElasticsearchURL 
from ElasticsearchResult import ElasticsearchResult
from ElasticsearchQuery import ElasticsearchAtsnpQuery
from DataReconstructor import DataReconstructor
from GenomicLocationQuery import GenomicLocationQuery

class SnpidWindowQuery(GenomicLocationQuery):
    def prepare_json_for_query(self):
        region = self.setup_region_around_snpid()
        query = self.setup_gl_query(region)
        return query 

    def setup_region_around_snpid(self):
        coords = self.get_coordinate_for_snpid()
        return self.apply_window_around_coordinates(coords)

    def get_coordinate_for_snpid(self):
        one_snpid = self.request.data.get('snpid')
        numeric_snpid = one_snpid.replace('rs', '') 
        if numeric_snpid is None: 
            msg = 'No snpid specified.'
            raise InvalidQueryError(msg)
        coord = self.get_snpid_coord(numeric_snpid)
        return coord 

    def get_snpid_coord(self, numeric_snpid):
        snpid_data = self.get_snpid_data(numeric_snpid)
        #Need to handle non-numeric chromosomes.
        snpid_data['chr'] = snpid_data['chr'].replace('ch', '') 
        gl_coords = { 'chromosome' : snpid_data['chr'],
                      'start_pos'  : snpid_data['pos'],          
                      'end_pos'    : snpid_data['pos']           
                     }
        return gl_coords 
 
    def get_snpid_data(self, numeric_snpid):
        es_url = ElasticsearchURL('atsnp_output', page_size=1).get_url() 
        es_query = json.dumps({"query":{"match":{"snpid":numeric_snpid }}})
        es_result = ElasticsearchResult(requests.post(es_url, data=es_query))
        hits = es_result.get_result()
        if hits['hitcount'] == 0:
            raise NoDataFoundError('No location available for SNPid ' +\
                                    'rs' + numeric_snpid + '.')
        return hits['data'][0]
