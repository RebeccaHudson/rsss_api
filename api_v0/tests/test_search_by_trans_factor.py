from django.core.urlresolvers import reverse
from django.conf import settings
from rest_framework.test import APITestCase
#from . import ESPaging
from rest_framework import status
import json
import re

class TranscriptionFactorSearchTests(APITestCase):

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
        print "length of valid response = " + str(len(response_json))

    # Is the hitcount coming back to the user?
    # keep hitting es w/ higher FROMs until it comes back 204
    def grab_pages_of_data(self, post_data, url):
        keep_going = True
        i = 0
        while keep_going is True:
            response = self.client.post(url, post_data, format='json')
            print "text of response" + repr(response)
            if response.status_code == status.HTTP_204_NO_CONTENT: 
                keep_going = False
            else:
                response_json = json.loads(response.content)
                i += 1 
                from_result = settings.ELASTICSEARCH_PAGE_SIZE * i
                print "got this much data: " + str(len(response_json['data'])) + " on page " + str(i) 
                print "hitcount claims to be: " + str(response_json['hitcount'])
                post_data['from_result'] = from_result


    def test_simple_valid_search_by_tf_pagination(self):
        url = reverse('api_v0:tf-search')
        motif_list = ['MA0002.2', 'MA00002.1']
        post_data = {'motif': motif_list,
                     'pvalue_rank' : 0.0 }
        self.grab_pages_of_data(post_data, url)
        print "stopping the test early. getting mechanincs in place." 
        return
        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.content)
        print "length of valid response = " + str(len(response_json))
        post_data['from_result'] = len(response_json)
        response = self.client.post(url, post_data, format='json')
        response_json = json.loads(response.content) 
        #make a loop that adds up the size of each page of results,
        #storing them all in memory is not really useful.

    def test_valid_nomatch_search_by_tf(self):
        url = reverse('api_v0:tf-search')
        response = self.client.post(url,
                                    {'motif':['MA0002.2'],
                                     'pvalue_rank' : -0.00000001 },
                                     format='json')
        #ensure no matches by making the pvalue negative
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
