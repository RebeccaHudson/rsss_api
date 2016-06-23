from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.db import connection
from django.conf import settings
import json
import os
import sys

class SearchBySnpidWindowTests(APITestCase):

    def test_nomatch_response_for_snpid_window_search(self):
        print("testing nomatch response for snpid window search")
        nonmatching_snpid = 'fake1'
        request_data = { 'snpid' : nonmatching_snpid, 'pvalue_rank': 0.2, 'window_size':3 }
        response = self.client.post(reverse('api_v0:snpid-window-search'), 
                                    request_data , format='json')
        print(str(response))
        self.assertEqual(response.data, 
                        'No data for snpid '+nonmatching_snpid +'.')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_malformed_request_response_for_snpid_window_search(self):
        url = reverse('api_v0:snpid-window-search')
        request_data = { 'something' : 'ch1', 
                         'window_size' : 4500,
                         'pval_rank' : .4000 }
        response = self.client.post(url, request_data, format = 'json')
        self.assertEqual(response.data, 'No snpid specified.')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        #what if snpid does not match a reasonable regex for snpids?
        #No p-value is specified, include a warning that a default p-value is specified?


    def test_valid_snpid_window_search(self):
      url = reverse('api_v0:snpid-window-search')
      req_headers = { 'content-type' : 'application/json' }
      request_data = { 'snpid' : 'rs371194064', #corresponds to: chr1    1702383 1724565
                       'pvalue_rank' : 0.05,
                        'window_size': 99999 }
      response = self.client.post(url, request_data, format='json')
      print "length of response : " + str(len(response.data)) 
      #self.assertEqual(response.status_code, status.HTTP_200_OK)
      #add assertions about response data

     #TODO: Add tests for other valid requests, along with assertions about the correct
     # data being returned.
     
"""
  Some should be these:
  HTTP_500_INTERNAL_SERVER_ERROR ? (when should API respond w/ this?)
  HTTP_501_NOT_IMPLEMENTED
"""
