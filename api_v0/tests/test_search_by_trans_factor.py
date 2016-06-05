from django.core.urlresolvers import reverse
from api_v0.tests.painstaking_manual_test_setup import RSSS_APITestCase
from rest_framework import status
import json
import re

class TranscriptionFactorSearchTests(RSSS_APITestCase):
    # currently, web interface is required to handle translation between
    # motif value and names of transcription factors.
    def test_simple_valid_search_by_tf(self):
        url = reverse('api_v0:tf-search')
        motif_list = ['MA0002.2', 'MA00002.1']
        response = self.client.post(url, 
                                    {'motif': motif_list,
                                     'pvalue_rank' : 0.001 },
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.content)
        self.check_that_response_is_well_formed(response_json, 4)


    def test_valid_nomatch_search_by_tf(self):
        url = reverse('api_v0:tf-search')
        response = self.client.post(url,
                                    {'motif':['MA0002.2'],
                                     'pvalue_rank' : 0.00000001 },
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)



    def test_that_request_missing_tf_is_rejected(self):
        url = reverse('api_v0:tf-search') 
        response = self.client.post(url, {'pvalue_rank': 0.03}, format='json')
        self.assertEqual(response.data, 'No motif specified!')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 

       

    #check that it fits the regular expression I have
    def test_that_malformed_motif_value_is_rejected(self):
        bad_motif_value_example = 'M3k002--93.2' 
        url = reverse('api_v0:tf-search') 

        request_data = { 'motif' : [bad_motif_value_example]} 
        # a default p-value cutoff will be used here..
        response = self.client.post(url, request_data, format='json' )       
        
        self.assertEqual(response.data, 'No well-formed motifs.')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 
        #use this to test for a good motif value; edit later?
        #test_match = re.match(r'M(\w[.])+', bad_motif ) 
        
    # TODO: extend this test when more motif values are present in the dataset.
    # TODO: represent additional motifs in the dataset.  