from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 

from django.db import connection
import json
import os

#All of this should be available to other tests...
class RSSS_APITestCase(APITestCase):

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
        sql_input = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
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
      with open (os.path.join( os.path.dirname(os.path.dirname(__file__)), 
                               'test_outputs',
                                name_of_expected_output_file + ".json"),
                 'r') as data_file:
          expected_output = json.load(data_file)
      self.assertEqual(response_data, expected_output)
