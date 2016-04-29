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
      c = connection.cursor()
      c.execute('SHOW TABLES')
      resp = c.fetchall() 
      if (u'snp_scores_1',) in resp:
        print "snp_scores_1 test table already setup.. skipping that setup"
        return 
      self.setup_table_in_testdb(c)
      self.read_sql_into_testdb(c)
      with open(os.path.join(
                 os.path.dirname(__file__), 'expected_test_outputs.json'),
               'r') as data_file:
         self.expected_output_data = json.load(data_file)
            
    def setup_table_in_testdb(self, cursor):
      sql = """CREATE TABLE snp_scores_1 (
           id INTEGER PRIMARY KEY AUTO_INCREMENT,
           snpid VARCHAR(20),  
           motif VARCHAR(15),
           motif_len INTEGER,
           log_lik_ref FLOAT, log_lik_snp FLOAT, log_lik_ratio FLOAT,
           log_enhance_odds FLOAT, log_reduce_odds FLOAT, 
           ref_start INTEGER, snp_start INTEGER,
           ref_end INTEGER, snp_end INTEGER,
           ref_strand CHAR(1), snp_strand CHAR(1)
         );""" 
      cursor.execute(sql)

    def read_sql_into_testdb(self, cursor):
        sql_input = os.path.join(os.path.dirname(__file__), 
                                'sql_test_data', 'sql_out_test_data-0.sql')
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
    
   def test_retrieve_one_row_by_id(self):
      url = reverse('api_v0:one-scores', args=(23,))
      response = self.client.get(url) 
      self.compare_response(response.data, 'test_retrieve_one_row')
    
    def test_retrieve_one_row_by_snpid(self):
      #the line below returns the snp: 'rs561784591'
      url = reverse('api_v0:one-scores-snpid', args=(561784591,))
      response = self.client.get(url) 
      self.compare_response(response.data, 'test_retrieve_row_by_snpid')
  #  def test_scores_row_list_snpids(self):
  #   pass
  #   #There is some post data handled down here... 
  #   # data = {'name': 'DabApps'}
  #   # response = self.client.post(url, data, format='json')
  #   # self.assertEqual(response.status_code, status.HTTP_201_CREATED)
  #   # self.assertEqual(Account.objects.count(), 1)
  #   # self.assertEqual(Account.objects.get().name, 'DabApps')



  #TODO: Add tests for unexpected and/or malformed requests.
