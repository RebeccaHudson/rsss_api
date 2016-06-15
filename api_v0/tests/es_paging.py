from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings
import json

class RSSS_APITestCase(APITestCase):

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


