from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 
from api_v0.tests.painstaking_manual_test_setup import RSSS_APITestCase
from django.db import connection
import json
import os

#Basic, miscellaneous tests for ScoresRow model itself.
class ScoresRowTests(RSSS_APITestCase): 
    def test_retrieve_one_row_by_id(self):
      url = reverse('api_v0:one-scores', args=(23,))
      response = self.client.get(url) 
      self.compare_response(response.data, 'test_retrieve_one_row')
      #self.write_response_to_appropriate_testfile(response.data, 'test_retrieve_one_row')
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

    def test_nomatch_response_for_retrieve_one_row_by_snpid(self):
      url = reverse('api_v0:one-scores-snpid', args=(6666666666,))
      response = self.client.get(url)
      self.assertEqual(response.data, 'No data for that SNPid')
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)





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
