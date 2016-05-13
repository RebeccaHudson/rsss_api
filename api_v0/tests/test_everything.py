from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 
from api_v0.tests.painstaking_manual_test_setup import RSSS_APITestCase
from django.db import connection
import json
import os

#TODO spilt this up into smaller, shorter files.

#class ScoresRowTests(APITestCase):
class ScoresRowTests(RSSS_APITestCase): #idea is that this will inheit from API TestCase   
    def test_retrieve_one_row_by_id(self):
      url = reverse('api_v0:one-scores', args=(23,))
      response = self.client.get(url) 
      self.compare_response(response.data, 'test_retrieve_one_row')
      #self.write_response_to_appropriate_testfile(response.data, 'test_retrieve_one_row')
      self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_retrieve_one_row_by_snpid(self):
      #rs2691305
      #the line below returns the snp: 'rs561784591'
      url = reverse('api_v0:one-scores-snpid', args=(2691305,))
      response = self.client.get(url) 
      #an ordered dict comes out of the .filter call and the .data is an
      #self.write_response_to_appropriate_testfile(json.loads(response.content), 'test_retrieve_row_by_snpid')

      self.compare_response(json.loads(response.content), 'test_retrieve_row_by_snpid')
      self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nomatch_response_for_retrieve_one_row_by_snpid(self):
      url = reverse('api_v0:one-scores-snpid', args=(6666666666,))
      response = self.client.get(url)
      self.assertEqual(response.data, 'No data for that SNPid')
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_nomatch_response_for_scores_row_list(self):
      req_headers = { 'content-type' : 'application/json' }

      #The following are not expected to match any snpids in the database
      snpid_list = [ "rs111111111", "rs11111111111", "rs11111111111"]

      url = reverse('api_v0:search')
      response = self.client.post(url, snpid_list, format='json')
      self.assertEqual(response.data, 'No matches.')
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_scores_row_list_for_three_snpids(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list  = [ "rs371194064",    "rs10218527",   "rs189107123" ]
      url = reverse('api_v0:search')
      response = self.client.post(url, snpid_list, format='json')
      #self.write_response_to_appropriate_testfile(json.loads(response.content),'test_scores_row_list_for_three_snpids')
      self.compare_response(json.loads(response.content),'test_scores_row_list_for_three_snpids')
      self.assertEqual(response.status_code, status.HTTP_200_OK)


    #return data for which there are matching records.
    def test_partial_match_response_for_scores_row_list(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list = ["rs10218527",   "rs189107123","rs111111111",  "rs11111111111" ]
      url = reverse('api_v0:search') 
      response = self.client.post(url, snpid_list, format='json')
      #self.write_response_to_appropriate_testfile(json.loads(response.content), 'test_scores_row_list_partial_match') 
      self.compare_response(json.loads(response.content),'test_scores_row_list_partial_match')
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
