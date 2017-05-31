#All queries that ultimately search by genomic location inherit from this?
import re
import json
from django.conf import settings
from AtsnpExceptions import *
from ElasticsearchQuery import ElasticsearchAtsnpQuery

class GenomicLocationQuery(ElasticsearchAtsnpQuery): 

    def check_and_aggregate_gl_search_params(self):
        if not all (k in self.request.data.keys() for k in ("chromosome","start_pos", "end_pos")):
            raise InvalidQueryError('Must include chromosome, start, and end position.')

        gl_coords =  {}
        gl_coords['start_pos'] = self.request.data['start_pos']
        gl_coords['end_pos'] = self.request.data['end_pos']
        gl_coords['chromosome'] =  self.request.data['chromosome']  # TODO: check for invlaid chromosome
        #Chromosomes are numeric as stored in the minimized data set.
        gl_coords['chromosome'] = gl_coords['chromosome'].replace('ch', '') 
    
        if not gl_coords['chromosome'].isdigit():   #could be pulled out into another function.
            non_numeric_chromosomes = { 'X' : 23, 'Y': 24, 'M': 25, 'MT': 25 }
            gl_coords['chromosome'] = non_numeric_chromosomes[gl_coords['chromosome']]
    
        if gl_coords['end_pos'] < gl_coords['start_pos']:
            raise InvalidQueryError('Start position is less than end position.')
        if gl_coords['end_pos'] - gl_coords['start_pos'] > settings.HARD_LIMITS['MAX_BASES_IN_GL_REQUEST']:
            raise InvalidQueryError('Requested region is too large.')
        return gl_coords

    def setup_gl_query(self, gl_coords):
        j_dict = {"must" : [
                    { "range": {
                           "pos" : {  "from" : gl_coords['start_pos'], 
                                        "to" : gl_coords['end_pos'] }
                       }
                    },
                    { "term" : { "chr" : gl_coords['chromosome'] } }
                 ] 
              }
        return j_dict

    #returns the 'must' key of the query dict to build.
    def prepare_json_for_query(self):
        gl_coords_or_error_response = self.check_and_aggregate_gl_search_params()
        if not gl_coords_or_error_response.__class__.__name__  == 'dict':
            return gl_coords_or_error_response 
        gl_coords = gl_coords_or_error_response
        j_dict = self.setup_gl_query(gl_coords)
        return j_dict

    #Shared by SNPid window and gene name searches. 
    def apply_window_around_coordinates(self, coords):
        window = self.request.data.get('window_size')
        if window > 1000000:
            msg = "Window is too big. Put this number into a config file."
            raise InvalidQueryError(msg)
        coords['start_pos'] = max(coords['start_pos'] - window, 0)
        coords['end_pos'] += window
        return coords
