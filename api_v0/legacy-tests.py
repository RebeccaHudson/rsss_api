from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 

from django.db import connection
import django_cassandra_engine
import json
import os

#TODO spilt this up into smaller, shorter files.
#TODO parameterize the names of tables and databases, use the stuff in settings/models?
class ScoresRowTests(APITestCase):

    def setUp(self):
      connection.cursor().db.set_rollback(False)  
       
      c = connection.cursor()
      insa = c.db.connection.cluster.metadata.keyspaces['test_rsnp_data'].tables
      if c.db.connection.cluster.metadata.keyspaces.has_key('test_rsnp_data'):
        print("There is a test database 'keyspace' called test_rsnp_data alreadly setup.")
      print(dir(insa))
      print(str(insa))

      if u'snp_scores_2' in c.db.connection.cluster.metadata.keyspaces['test_rsnp_data'].tables.keys():
        print "snp_scores_2 test table already setup.. skipping that setup"
        return 
      self.setup_table_in_testdb(c)
      self.read_cql_into_testdb(c)
            
    def setup_table_in_testdb(self, cursor):
      cql="""CREATE TABLE snp_scores_2 (
         snpid VARCHAR,  
         motif VARCHAR,
         motif_len INT,
         log_lik_ref FLOAT, log_lik_snp FLOAT, log_lik_ratio FLOAT,
         log_enhance_odds FLOAT, log_reduce_odds FLOAT, 
         ref_start INT, snp_start INT,
         ref_end INT, snp_end INT,
         ref_strand VARCHAR, snp_strand VARCHAR,
         pval_ref FLOAT, pval_snp FLOAT, pval_cond_ref FLOAT, pval_cond_snp FLOAT,
         pval_diff FLOAT, pval_rank FLOAT, chr VARCHAR, pos INT,
         PRIMARY KEY( (snpid), chr, pos, motif, pval_rank)
         );"""
      cursor.execute(cql)

    def read_cql_into_testdb(self, cursor):
        sql_input = os.path.join(os.path.dirname(__file__), 
                                'cql_test_data', 'cql_out_test_data-0.cql')
        with open(sql_input, 'r') as f:
          for line in f:
            cursor.execute(line)
   
    def compare_response(self, response_data, name_of_expected_output_file):
      with open (os.path.join( os.path.dirname(__file__), 
                               'test_outputs',
                                name_of_expected_output_file + ".json"),
                 'r') as data_file:
          expected_output = json.load(data_file)
      self.assertEqual(response_data, expected_output)
   
    # There is not any way to do this with the cassandra data model. 
    #def test_retrieve_one_row_by_id(self):
    #  url = reverse('api_v0:one-scores', args=(23,))
    #  response = self.client.get(url) 
    #  self.compare_response(response.data, 'test_retrieve_one_row')
    #  self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_retrieve_one_row_by_snpid(self):
      #the line below returns the snp: 'rs561784591'
      url = reverse('api_v0:one-scores-snpid', args=(201336010,))
      response = self.client.get(url) 
      #an ordered dict comes out of the .filter call and the .data is an
      jr = json.loads(response.content) 
      self.assertEqual(len(jr), 1)
      self.assertEqual(len(jr[0].keys()), 21)
      #self.compare_response(json.loads(response.content), 'test_retrieve_row_by_snpid')
      self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nomatch_response_for_retrieve_one_row_by_snpid(self):
      url = reverse('api_v0:one-scores-snpid', args=(6666666666,))
      response = self.client.get(url)
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_nomatch_response_for_scores_row_list(self):
      req_headers = { 'content-type' : 'application/json' }

      #The following are not expected to match any snpids in the database
      snpid_list = [ "rs111111111", "rs11111111111", "rs11111111111"]

      url = reverse('api_v0:search')
      response = self.client.post(url, snpid_list, format='json')
      print("response: " + str(response) )
      #self.compare_response(response.data,'test_scores_row_list_for_three_snpids')
      self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_scores_row_list_for_three_snpids(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list = [ "rs376997626", "rs575624833", "rs189241347"]
      url = reverse('api_v0:search')
      response = self.client.post(url, snpid_list, format='json')
      self.compare_response(response.data,'test_scores_row_list_for_three_snpids')
      self.assertEqual(response.status_code, status.HTTP_200_OK)


    #return data for which there are matching records.
    def test_partial_match_response_for_scores_row_list(self):
      req_headers = { 'content-type' : 'application/json' }
      snpid_list = [ "rs376997626", "rs575624833", "rs111111111",  "rs11111111111" ]
      url = reverse('api_v0:search') 
      response = self.client.post(url, snpid_list, format='json')
      self.compare_response(response.data,'test_scores_row_list_partial_match')
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
