#Some of these imports may not be needed
from rest_framework.response import Response
from django.conf import settings
import requests
import re
import json

from AtsnpExceptions import *
from GenomicLocationQuery import GenomicLocationQuery
from ElasticsearchURL import ElasticsearchURL
from ElasticsearchResult import ElasticsearchResult

class GeneNameQuery(GenomicLocationQuery):
    def prepare_json_for_query(self):
        #use a try/catch here.
        region = self.setup_region_around_gene()
        query = self.setup_gl_query(region)
        return query 

    def setup_region_around_gene(self):
        coords = self.get_coordinate_for_gene()        
        return self.apply_window_around_coordinates(coords)

    def get_coordinate_for_gene(self):
        gene_name = self.request.data.get('gene_name')
        if gene_name is None:
            raise InvalidQueryError('No gene name specified.')

        #shares code with 'get_snpid_data' from snpid window search
        gene_data = self.get_gene_data(gene_name)
        print "gene data: " + repr(gene_data)
        gene_data['chr'] = gene_data['chr'].replace('chr', '')

        if not gene_data['chr'].isdigit():   #could be pulled out into another function.
            non_numeric_chromosomes = { 'X' : 23, 'Y': 24, 'M': 25, 'MT': 25 }
            gene_data['chr'] = non_numeric_chromosomes[gene_data['chr']]

        gene_coords = { 'chromosome': gene_data['chr'],
                        'start_pos' : int(gene_data['start_pos']),
                        'end_pos'   : int(gene_data['end_pos'])  }
        return gene_coords

    def get_gene_data(self, gene_name):
        j_dict = {"query":{"match":{"gene_symbol":gene_name}}} 
        json_query = json.dumps(j_dict)
        es_url = ElasticsearchURL('gencode_gene_symbols', page_size=1).get_url() 
        header = { 'Content-Type' : 'application/json' }
        es_result = ElasticsearchResult(requests.post(es_url, data=json_query, headers=header))
        hits = es_result.get_result() 
        if hits['hitcount'] == 0:
            print "gene name not found. unreported"
            raise MissingBackendDataError('Gene name not found.')
        return hits['data'][0]

