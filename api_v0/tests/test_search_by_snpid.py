from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 
from api_v0.tests.painstaking_manual_test_setup import RSSS_APITestCase
from django.db import connection
import json
import os

#This is supposed to test all of the cases for API requests to search by SNPid,
#From an actual form POST. 
class SnpSearchTests(RSSS_APITestCase): #idea is that this will inheit from API TestCase   

    def test_nomatch_response_for_search_by_snpid(self):
      print("testing nomatch response for scores row list")
      req_headers = { 'content-type' : 'application/json' }

      #The following are not expected to match any snpids in the database
      snpid_list = [ "rs111111111", "rs11111111111", "rs11111111111"]
      request_data = { 'snpid_list' : snpid_list, 
                       'pvalue_rank': 0.05 }
      url = reverse('api_v0:snpid-search')
      response = self.client.post(url, request_data, format='json')
      self.assertEqual(response.data, 'No matches.')
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_search_by_snpid_for_three_snpids(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list  = ["rs371194064",    "rs10218527",   "rs189107123" ]
      url = reverse('api_v0:snpid-search')
      print("url " + url)
      request_data = { 'snpid_list' : snpid_list, 
                       'pvalue_rank': 0.05 }
      response = self.client.post(url, request_data, format='json')
      #self.write_response_to_appropriate_testfile(json.loads(response.content),'test_scores_row_list_for_three_snpids')
      print("RESPONSE: "  + str(response))
      # is there a need to do json.loads?
      response_json = json.loads(response.content)
      
      #  only 2 of the three snpids in the test data are below the 0.05
      #  cutoff  
      self.check_that_response_is_well_formed(response_json, 2)
 
      #self.compare_response(json.loads(response.content),'test_scores_row_list_for_three_snpids')
      self.assertEqual(response.status_code, status.HTTP_200_OK)


    #return data for which there are matching records.
    def test_partial_match_response_for_search_by_snpid(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list = ["rs10218527",   "rs189107123","rs111111111",  "rs11111111111" ]
      url = reverse('api_v0:snpid-search') 
      print("url " + url)
      request_data = { 'snpid_list' : snpid_list, 
                       'pvalue_rank': 0.05 }
      response = self.client.post(url, request_data, format='json')
      response_json = json.loads(response.content)
      
      #  only ONE match meets the default p-value cutoff of 0.05
      self.check_that_response_is_well_formed(response_json, 1)
      #self.write_response_to_appropriate_testfile(json.loads(response.content), 'test_scores_row_list_partial_match') 
      #self.compare_response(json.loads(response.content),'test_scores_row_list_partial_match')
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
