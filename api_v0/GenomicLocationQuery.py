#All queries that ultimately search by genomic location inherit from this?
import re
import json
from django.conf import settings
from ElasticsearchQuery import ElasticsearchAtsnpQuery

class GenomicLocationQuery(ElasticsearchAtsnpQuery): 

    #does this really get used?
    #YES. It does not handle anything with/about pvalues.
    def check_and_aggregate_gl_search_params(self):
        if not all (k in self.request.data.keys() for k in ("chromosome","start_pos", "end_pos")):
            return Response('Must include chromosome, start, and end position.',
                           status = status.HTTP_400_BAD_REQUEST)
        gl_coords =  {}
        gl_coords['start_pos'] = self.request.data['start_pos']
        gl_coords['end_pos'] = self.request.data['end_pos']
        gl_coords['chromosome'] =  self.request.data['chromosome']  # TODO: check for invlaid chromosome
        #Chromosomes are numeric as stored in the minimized data set.
        gl_coords['chromosome'] = gl_coords['chromosome'].replace('ch', '') 
        #does it explcitly need to be an int?
    
        if not gl_coords['chromosome'].isdigit():   #could be pulled out into another function.
            non_numeric_chromosomes = { 'X' : 23, 'Y': 24, 'M': 25, 'MT': 25 }
            gl_coords['chromosome'] = non_numeric_chromosomes[gl_coords['chromosome']]
    
        if gl_coords['end_pos'] < gl_coords['start_pos']:
            return Response('Start position is less than end position.',
                          status = status.HTTP_400_BAD_REQUEST)
       
        if gl_coords['end_pos'] - gl_coords['start_pos'] > settings.HARD_LIMITS['MAX_BASES_IN_GL_REQUEST']:
            return Response('Requested region is too large', 
                           status=status.HTTP_400_BAD_REQUEST)
        return gl_coords

    #returns the 'must' key of the query dict to build.
    def prepare_json_for_query(self):
        gl_coords_or_error_response = self.check_and_aggregate_gl_search_params()
        if not gl_coords_or_error_response.__class__.__name__  == 'dict':
            return gl_coords_or_error_response 
        gl_coords = gl_coords_or_error_response
        #base_dict  =  super(GenomicLocationQuery, self).prepare_json_for_query()
        #j_dict = {   
        #    "sort" : sort["sort"], 
        #    "query":
        #    {
        #        "bool" : {
        #            "must" : [
        #               {
        #                 "range": {
        #                      "pos" : {  "from" : gl_coords['start_pos'], 
        #                                   "to" : gl_coords['end_pos'] }
        #                  }
        #               },
        #               { "term" : { "chr" : gl_coords['chromosome'] } }
        #            ],
        #            "filter":  pvalue_filter["filter"]
        #        }
        #    }
        #what goes inside of the must.
        #return a dict with one key, 'must'
        j_dict = {"must" : [
                    { "range": {
                           "pos" : {  "from" : gl_coords['start_pos'], 
                                        "to" : gl_coords['end_pos'] }
                       }
                    },
                    { "term" : { "chr" : gl_coords['chromosome'] } }
                 ] 
              }
        #json_out = json.dumps(j_dict)
        return j_dict

    #try to use 'filter' queries to speed this up.
    def prepare_json_for_gl_query_multi_pval(gl_coords, pval_dict, sort_info=None):
        pvalue_filter = None
        #print "whole contents of pval_dict: " + repr(pval_dict)
        #THIS is temporary until I have directional on everything.
        #print "gl query: pval dict: " + repr(pval_dict)
        pvalue_filter = use_appropriate_pvalue_filter_function(pval_dict)

        sort = prepare_json_for_sort()
        if sort_info is not None:
            print "using custom sort! " + repr(sort)
            sort =  prepare_json_for_custom_sort(sort_info)

        j_dict = {   
            "sort" : sort["sort"], 
            "query":
            {
                "bool" : {
                    "must" : [
                       {
                         "range": {
                              "pos" : {  "from" : gl_coords['start_pos'], "to" : gl_coords['end_pos'] }
                          }
                       },
                       { "term" : { "chr" : gl_coords['chromosome'] } }
                    ],
                    "filter":  pvalue_filter["filter"]
                }
            }
        }
        json_out = json.dumps(j_dict)
        #print "dict before query : " + json_out
        return json_out
 
 
    #This is the calling code:
    #refactor this one first.
    #Set up a 'prepare_query' method that is overridden by other subclasses.
    #@api_view(['POST'])
    #def search_by_genomic_location(request):
    #    #TODO: completely remove 'GL chunk size' this is here because I was trying
    #    # to use Cassandra for this.
    #    gl_coords_or_error_response = check_and_aggregate_gl_search_params(request)
    #    if not gl_coords_or_error_response.__class__.__name__  == 'dict':
    #        return gl_coords_or_error_response 

    #    pvalue_dict = get_pvalue_dict(request)
    #    gl_coords = gl_coords_or_error_response
    #    from_result = request.data.get('from_result')
    #    page_size = request.data.get('page_size')
    #    sort_order = request.data.get('sort_order')

    #    # The following code was copied into the bottom of search_by_snpid_window
    #    # TODO: consider DRYing up this part of the code
    #    es_query = prepare_json_for_gl_query_multi_pval(gl_coords, pvalue_dict)
    #    es_params = { 'from_result' : from_result, 
    #                  'page_size'   : page_size }

    #    #url stuff is handled in query_elasticsearch.
    #    print "about to gl query elasticsearch " + repr(es_query)
    #    return query_elasticsearch(es_query, es_params)
