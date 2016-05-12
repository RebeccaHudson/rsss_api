from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 

from django.db import connection
import json
import os

#TODO spilt this up into smaller, shorter files.

class ScoresRowTests(APITestCase):

    def setUp(self):
      connection.cursor().db.set_rollback(False)  
      c = connection.cursor()
      c.execute('SHOW TABLES')
      resp = c.fetchall() 
      if (u'snp_scores_2',) in resp:
        print "snp_scores_2 test table already setup.. skipping that setup"
        return 
      self.setup_table_in_testdb(c)
      self.read_sql_into_testdb(c)
            
    def setup_table_in_testdb(self, cursor):
      sql = """
        CREATE TABLE snp_scores_2 (
         id INTEGER PRIMARY KEY AUTO_INCREMENT,
         snpid VARCHAR(20),  
         motif VARCHAR(15),
         motif_len INTEGER,
         log_lik_ref FLOAT, log_lik_snp FLOAT, log_lik_ratio FLOAT,
         log_enhance_odds FLOAT, log_reduce_odds FLOAT, 
         ref_start INTEGER, snp_start INTEGER,
         ref_end INTEGER, snp_end INTEGER,
         ref_strand CHAR(1), snp_strand CHAR(1),
         pval_ref FLOAT, pval_snp FLOAT, pval_cond_ref FLOAT, pval_cond_snp FLOAT,
         pval_diff FLOAT, pval_rank FLOAT, chromosome VARCHAR(10), pos INTEGER);
         """
      cursor.execute(sql)

    def read_sql_into_testdb(self, cursor):
        sql_input = os.path.join(os.path.dirname(__file__), 
                                'sql_test_data', 'sql_out_test_data-2.sql')
        with open(sql_input, 'r') as f:
          for line in f:
            cursor.execute(line)

    #writing up new test data after every migration is a real mother.
    #Check sufficiently what this writes out to avoid automating error propogation. 
    def write_response_to_appropriate_testfile(self, response_data, name_of_expected_output_file):
      with open (os.path.join ( os.path.dirname(__file__),
                                 'test_outputs',
                                 name_of_expected_output_file  + '.json'),
                                 'w') as data_file:
        json.dump(response_data, data_file) 
        print("just dumped out the following:\n" + str(response_data))

 
    def compare_response(self, response_data, name_of_expected_output_file):
      with open (os.path.join( os.path.dirname(__file__), 
                               'test_outputs',
                                name_of_expected_output_file + ".json"),
                 'r') as data_file:
          expected_output = json.load(data_file)
      self.assertEqual(response_data, expected_output)
    
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
