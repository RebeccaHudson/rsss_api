from django.core.urlresolvers import reverse
from api_v0.tests.painstaking_manual_test_setup import RSSS_APITestCase
from rest_framework import status
import json
import re

class TestPlottingDataRetrieval(RSSS_APITestCase):
    # TODO: consider writing a test that will spit on improperly formatted snpids

    def check_that_plotting_data_has_expected_fields(self, json_back):
        print("here's the json that came back " + str(json_back))
        print("The keys of the json: \n\n" + str(json_back[0].keys()) + "\n\n")
        return True


    def test_simple_valid_request_for_plotting_data(self):
        url = reverse('api_v0:plotting-data')
        snpid_to_get = 'rs376007522'
        response = self.client.post(url, {'snpid': snpid_to_get }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.content)
        self.check_that_plotting_data_has_expected_fields(response_json)

    def test_nomatch_request_for_plotting_data(self):
        url = reverse('api_v0:plotting-data')
        snpid_to_get = 'rs111111111111'
        response = self.client.post(url, {'snpid': snpid_to_get }, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
    def test_that_plotting_data_request_missing_snpid_is_rejected(self):
         url = reverse('api_v0:plotting-data')
         response = self.client.post(url, {'chr':2,'what?':'hey'},format='json')
         print("response : " + str(response))
         print "dir of response " + str(dir(response))
         print("data of response: " + response.data)
         self.assertEqual(response.data, 'No snpid specified.')
         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ##check that it fits the regular expression I have
    #def test_that_malformed_motif_value_is_rejected(self):
    #    bad_motif_value_example = 'M3k002--93.2' 
    #    url = reverse('api_v0:tf-search') 

    #    request_data = { 'motif' : [bad_motif_value_example]} 
    #    # a default p-value cutoff will be used here..
    #    response = self.client.post(url, request_data, format='json' )       
    #    
    #    self.assertEqual(response.data, 'No well-formed motifs.')
    #    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 
    #    #use this to test for a good motif value; edit later?
    #    #test_match = re.match(r'M(\w[.])+', bad_motif ) 
    #    
    ## TODO: extend this test when more motif values are present in the dataset.
    ## TODO: represent additional motifs in the dataset.  
