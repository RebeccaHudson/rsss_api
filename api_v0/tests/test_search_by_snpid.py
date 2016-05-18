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

    def test_nomatch_response_for_scores_row_list(self):
      print("testing nomatch response for scores row list")
      req_headers = { 'content-type' : 'application/json' }

      #The following are not expected to match any snpids in the database
      snpid_list = [ "rs111111111", "rs11111111111", "rs11111111111"]

      url = reverse('api_v0:search')
      response = self.client.post(url, snpid_list, format='json')
      self.assertEqual(response.data, 'No matches.')
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_scores_row_list_for_three_snpids(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list  = ["rs371194064",    "rs10218527",   "rs189107123" ]
      url = reverse('api_v0:search')
      print("url " + url)
      response = self.client.post(url, snpid_list, format='json')
      #self.write_response_to_appropriate_testfile(json.loads(response.content),'test_scores_row_list_for_three_snpids')
      print("RESPONSE: "  + str(response))
      # is there a need to do json.loads?
      response_json = json.loads(response.content)
      self.check_that_response_is_well_formed(response_json, 3)
      #self.compare_response(json.loads(response.content),'test_scores_row_list_for_three_snpids')
      self.assertEqual(response.status_code, status.HTTP_200_OK)


    #return data for which there are matching records.
    def test_partial_match_response_for_scores_row_list(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list = ["rs10218527",   "rs189107123","rs111111111",  "rs11111111111" ]
      url = reverse('api_v0:search') 
      print("url " + url)
      response = self.client.post(url, snpid_list, format='json')
      response_json = json.loads(response.content)
      #print("RESPONSE: "  + str(response_json))
      self.check_that_response_is_well_formed(response_json, 2)
      #self.write_response_to_appropriate_testfile(json.loads(response.content), 'test_scores_row_list_partial_match') 
      #self.compare_response(json.loads(response.content),'test_scores_row_list_partial_match')
      self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_retrieve_one_row_by_snpid(self):
      #the line below returns the snp: 'rs561784591'
      url = reverse('api_v0:one-scores-snpid', args=(201336010,))
      response = self.client.get(url)
      #an ordered dict comes out of the .filter call and the .data is an
      jr = json.loads(response.content)
      self.assertEqual(len(jr), 1)
      self.assertEqual(len(jr[0].keys()), 21)
      print(jr)
      #self.compare_response(json.loads(response.content), 'test_retrieve_row_by_snpid')
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
