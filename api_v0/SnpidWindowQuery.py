#Some of these imports may not be needed
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status 
from django.core.exceptions import ObjectDoesNotExist
from AtsnpExceptions import *
#from django.core.exceptions import  
import requests
import re
import json

#Change the name of that file.
from ElasticsearchURL import ElasticsearchURL, ElasticsearchResult
from ElasticsearchQuery import ElasticsearchAtsnpQuery
from DataReconstructor import DataReconstructor
from GenomicLocationQuery import GenomicLocationQuery

class SnpidWindowQuery(GenomicLocationQuery):
    def prepare_json_for_query(self):
        #Must get coordinates to search with.
        #use a try/catch here.
        #region   #Adds the window size into play.
        region = self.setup_region_around_snpid()
        query = self.setup_gl_query(region)
        return query 

    def setup_region_around_snpid(self):
        coords = self.get_coordinate_for_snpid()
        #print "coords in setup_region" + repr(coords)
        return self.apply_window_around_snpid_location(coords)

    def apply_window_around_snpid_location(self, coords):
        window = self.request.data.get('window_size')
        if window > 1000000:
            msg = "Window is too big. Put this number into a config file."
            raise InvalidQueryError(msg)
        print "coords " + repr(coords)
        coords['start_pos'] = max(coords['start_pos'] - window, 0)
        coords['end_pos'] += window
        return coords

    def get_coordinate_for_snpid(self):
        one_snpid = self.request.data.get('snpid')
        numeric_snpid = one_snpid.replace('rs', '') 
        print "searching for this numeric snpid " + str(numeric_snpid)
        #to rebuild the reduced data.
        #TODO: Throw exception if SNPid is blank.
        if numeric_snpid is None: 
            #print "no numeric snpid found!"
            #return Response('No snpid specified.', 
            #                 status = status.HTTP_400_BAD_REQUEST)
            msg = 'No snpid specified.'
            raise InvalidQueryError(msg)
        coord = self.get_snpid_coord(numeric_snpid)
        #if coord is None: 
        #    raise EmptyResultSet('No data for snpid ' + one_snpid + '.')
        #    #return None
        #    #return Response('No data for snpid ' + one_snpid + '.', 
        #    #            status = status.HTTP_204_NO_CONTENT)
        return coord 

    def get_snpid_coord(self, numeric_snpid):
        snpid_data = self.get_snpid_data(numeric_snpid)
        print "got snpid data" + repr(snpid_data)
        #if snpid_data is None:
        #    print "no snpid data"
        #    return None
        snpid_data['chr'] = snpid_data['chr'].replace('ch', '') #Account for minimized data
        gl_coords = { 'chromosome' : snpid_data['chr'],
                      'start_pos'  : snpid_data['pos'],          # - window_size,
                      'end_pos'    : snpid_data['pos']           # + window_size
                     }
        return gl_coords 
 
    def get_snpid_data(self, numeric_snpid):
        es_url = ElasticsearchURL('atsnp_output', page_size=1).get_url() #only 1 result needed.
        print "trying to pull data from this url " + es_url
        es_query = json.dumps({"query":{"match":{"snpid":numeric_snpid }}})
        print "here's the query "  + json.dumps(es_query)
        rasin_bran = requests.post(es_url, data=es_query)
        #es_result = ElasticsearchResult(requests.post(es_url, data=es_query))
        print "what comes out of the post? " + repr(rasin_bran)
        es_result = ElasticsearchResult(rasin_bran)
        hits = es_result.get_result()
        print "hits: " + repr(hits)
        if hits['hitcount'] == 0:
            raise NoDataFoundError('No location available for SNPid ' +\
                                      numeric_snpid + '.')
            #return None
        return hits['data'][0]
 
    #@api_view(['POST'])
    #def search_by_window_around_snpid(request):
    #    one_snpid = request.data.get('snpid')
    #    numeric_snpid = one_snpid.replace('rs', '') #to compensate for our optimizations
    #    window_size = request.data.get('window_size')
    #    pvalue_dict = get_pvalue_dict(request)
    #    

    #    #This URL is for looking up the genomic location of a SNPid. 
    #    #has to be re-prepared for pageable search.
    #    es_url = prepare_es_url('atsnp_output') 



    #    #if elasticsearch is down, find out now. 
    #    if es_url is None:
    #        return Response('Elasticsearch is down, please contact admins.', 
    #                         status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #    #query_for_snpid_location = {"query":{"match":{"snpid":one_snpid }}}
    #    query_for_snpid_location = {"query":{"match":{"snpid":numeric_snpid }}}
    #    es_query = json.dumps(query_for_snpid_location)
    #    es_result = requests.post(es_url, data=es_query, timeout=100)
    #    records_for_snpid = get_data_out_of_es_result(es_result)

    #    if len(records_for_snpid['data']) == 0: 
    #        return Response('No data for snpid ' + one_snpid + '.', 
    #                        status = status.HTTP_204_NO_CONTENT)

    #    record_to_pick = records_for_snpid['data'][0]
    #    record_to_pick['chr'] = record_to_pick['chr'].replace('ch', '') #Account for minimized data
    #    gl_coords = { 'chromosome' :  record_to_pick['chr'],
    #                  'start_pos'  :  record_to_pick['pos'] - window_size,
    #                  'end_pos'    :  record_to_pick['pos'] + window_size
    #                 }
    #    if gl_coords['start_pos'] < 0:
    #        #: TODO consider adding a warning here if this happens?
    #        gl_coords['start_pos'] = 0

    #    #TRY ADDING THE DIRECTIONAL HERE?
    #    
    #    es_query = prepare_json_for_gl_query_multi_pval(gl_coords, pvalue_dict)
    #    #print "es query for snpid window search " + es_query
    #   
    #    es_params = { 'page_size' : request.data.get('page_size'),
    #                  'from_result' : request.data.get('from_result') }
    #    #This probably isn't the right place to put the from result
    #    return query_elasticsearch(es_query, es_params)
