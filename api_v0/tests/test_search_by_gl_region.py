from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.db import connection
from django.conf import settings
import json
import os

#This is supposed to test all of the cases for API requests to search by genomic location. 
#From an actual form POST. 
class GenomicLocationSearchTests(APITestCase):

    def test_nomatch_response_for_gl_search(self):
        print("testing nomatch response for genomic location search")

        req_headers = { 'content-type' : 'application/json' }
        #The following are not expected to match any snpids in the database
        #in the current set of test data, the last numberd position is 869793
        chromosome = 'ch1';   start_pos = 999999999 ; end_pos = start_pos + 10  
        request_data = { 'chromosome' : 'ch1',
                         'start_pos' : 999999999, 
                         'end_pos' : start_pos + 10 }
        response = self.client.post(reverse('api_v0:gl-search'), request_data , format='json')
        self.assertEqual(response.data, 'No matches.')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_malformed_request_response_for_gl_search(self):
        req_headers = { 'content-type' : 'application/json' }
        url = reverse('api_v0:gl-search')
        missing_arg_msg = 'Must include chromosome, start, and end position.'

        # End position is less than start position.
        request_data = { 'chromosome' : 'ch1', 'start_pos' : 4500, 'end_pos' : 4000 }
        response = self.client.post(url, request_data, format = 'json')
        self.assertEqual(response.data, 'Start position is less than end position.')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
   

        # TODO Make sure that start position and end position are > 0 

        # Requested region is too large; test data is a little hardcoded here.
        request_data = { 'chromosome' : 'ch1', 'start_pos' : 150, 
                         'end_pos' : 500 + settings.HARD_LIMITS['MAX_BASES_IN_GL_REQUEST'],
                         'pvalue_rank' : 0.05 }
        response = self.client.post(url, request_data, format = 'json')
        self.assertTrue('Requested region is too large' in response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


        # Chromosome is not specified; reject.
        
        response = self.client.post(url, {'start_pos' : 150, 'end_pos' : 239 }, format = 'json' )
        self.assertEqual(response.data, missing_arg_msg)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Start or end position is missing. Reject if either is missig.   
        response = self.client.post(url,{'chromosome':'ch1','end_pos':239}, format = 'json')
        self.assertEqual(response.data, missing_arg_msg)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(url,{'chromosome':'ch1','start_pos':239}, format = 'json')
        self.assertEqual(response.data, missing_arg_msg)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # The chromosome is specified, but it's invalid. Go to hell!       
        # TODO: Write this test once I have a set of valid chromosome.



    def test_gl_search(self):
        url = reverse('api_v0:gl-search')
        request_data = { 'chromosome' : 'ch1', 
                         'start_pos' : 10257,
                         'end_pos' : 10357, 'pvalue_rank' : 0.05 }
        response = self.client.post(url, request_data, format='json')
        #self.write_response_to_appropriate_testfile(json.loads(response.content),'test_scores_row_list_for_three_snpids')
        print("RESPONSE: "  + str(response.data))
        #self.compare_response(json.loads(response.content),'test_scores_row_list_for_three_snpids')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_gl_search_for_200_bases(self):
        url = reverse('api_v0:gl-search')
        request_data = { 'chromosome' : 'ch1', 
                         'start_pos' : 13528,
                         'end_pos' : 13528 + 200, 'pvalue_rank' : 1 }
        response = self.client.post(url, request_data, format='json')
        print("RESPONSE: "  + str(response.data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)





  #TODO: Add tests for unexpected and/or malformed requests.
"""
  Some should be these:
  HTTP_500_INTERNAL_SERVER_ERROR
  HTTP_501_NOT_IMPLEMENTED
  HTTP_502_BAD_GATEWAY
  HTTP_503_SERVICE_UNAVAILABLE
  HTTP_504_GATEWAY_TIMEOUT
  HTTP_505_HTTP_VERSION_NOT_SUPPORTED
  HTTP_511_NETWORK_AUTHENTICATION_REQUIRED
"""
