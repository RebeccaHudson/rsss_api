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
        sql_input = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'cql_test_data', 'cql_out_test_data-0.cql')
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
