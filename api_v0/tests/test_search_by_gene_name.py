from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.db import connection
from django.conf import settings
import json
import os
import sys

#This is supposed to test all of the cases for API requests to search by genomic location. 
#From an actual form POST. 
class SearchByGeneNameTests(APITestCase):

    def test_nomatch_response_for_gene_name_search(self):
      print("testing nomatch response for genomic location search")
      req_headers = { 'content-type' : 'application/json' }
      request_data = { 'gene_name' : 'fake1', 'pvalue_rank': 0.2 }
      response = self.client.post(reverse('api_v0:gene-name-search'), 
                                  request_data , format='json')
      print(str(response))
      self.assertEqual(response.data, 'Gene name not found in database.')
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_malformed_request_response_for_gene_name_search(self):
      req_headers = { 'content-type' : 'application/json' }
      url = reverse('api_v0:gene-name-search')
      missing_gene_name_msg = 'No gene name specified.'

      #  No gene name specified
      request_data = { 'chromosome' : 'ch1', 'start_pos' : 4500, 'end_pos' : 4000 }
      #inappropriate request data.
      response = self.client.post(url, request_data, format = 'json')
      self.assertEqual(response.data, missing_gene_name_msg) 
      self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

      #gene name does not match a reasonable regex for gene names

      # No p-value is specified, include a warning that a default p-value is specified?



    def test_valid_gene_name_search(self):
      url = reverse('api_v0:gene-name-search')
      req_headers = { 'content-type' : 'application/json' }
      request_data = { 'gene_name' : 'NR_132739', #corresponds to: chr1    1702383 1724565
                       'pvalue_rank' : 0.05 }
      #print "CAN YOU SEE THIS?" 
      response = self.client.post(url, request_data, format='json')
      print("RESPONSE: "  + str(response.data))
      #self.assertEqual(response.status_code, status.HTTP_200_OK)
      #add assertions about response data


     #TODO: Add tests for other valid requests, along with assertions about the correct
     # data being returned.
     
"""
  Some should be these:
  HTTP_500_INTERNAL_SERVER_ERROR ? (when should API respond w/ this?)
  HTTP_501_NOT_IMPLEMENTED
"""
