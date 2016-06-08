from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 

from django.db     import connection
from django.conf   import settings
import json
import os


from cassandra import ConsistencyLevel
from cassandra.query import SimpleStatement

#All of this should be available to other tests...
class RSSS_APITestCase(APITestCase):

    def setUp(self):
      connection.cursor().db.set_rollback(False)  
      c = connection.cursor()
      # it could be possible to avoid re-creating all of the database stuff each time.
      tbl = settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_SNPID_QUERY'] 
      print("TABLES that exist in test keyspace: " +\
      ", ".join(c.db.connection.cluster.metadata.keyspaces['test_rsnp_data'].tables.keys()))
      if tbl in c.db.connection.cluster.metadata.keyspaces['test_rsnp_data'].tables.keys():
        print "test tables already setup.. skipping that setup"
        return 
      self.setup_tables_for_testdb(c)
      #self.setup_table_in_testdb(c)
      #self.read_cql_into_testdb(c)

    # each of these functions is responsible for loading its own data
    # (all of this data should be identical) 
    def setup_tables_for_testdb(self, cursor):
       self.setup_table_for_search_by_snpid_in_testdb(cursor)
       self.setup_table_for_search_by_gl_in_testdb(cursor)


    def setup_table_for_search_by_snpid_in_testdb(self, cursor):
      tbl = settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_SNPID_QUERY'] 
      cql="""CREATE TABLE """ + tbl + """ (
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
         PRIMARY KEY( (snpid), pval_rank, chr, pos)
         );"""
      cursor.execute(cql)
      self.read_cql_into_testdb(cursor, 'cql-data-3.txt')


    def setup_table_for_search_by_gl_in_testdb(self, cursor):
      tbl = settings.CASSANDRA_TABLE_NAMES['TABLE_FOR_GL_REGION_QUERY'] 
      cql="""CREATE TABLE """ + tbl + """ (
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
         PRIMARY KEY( (snpid), chr, pos, pval_rank)
         ); """
      cursor.execute(cql)
      self.read_cql_into_testdb(cursor, 'cql-data-4.txt')


    def read_cql_into_testdb(self, cursor, name_of_testdata_file):
        sql_input = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'cql_test_data', name_of_testdata_file)
        with open(sql_input, 'r') as f:
          for line in f:
            query = SimpleStatement(line, consistency_level = ConsistencyLevel.ANY)
            cursor.execute(query)

    #writing up new test data after every migration is a real mother.
    #Check sufficiently what this writes out to avoid automating error propogation. 
    def write_response_to_appropriate_testfile(self, response_data, name_of_expected_output_file):
      with open (os.path.join ( os.path.dirname(os.path.dirname(__file__)),
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
 
 
    # Check that there are the correct number of fields, and the expected number
    # of items in the response.
    #  expects what comes out of json.loads(response.content)

    # TODO: check that all of the expected fields have the expected names.
    def check_that_response_is_well_formed(self, response_data, expected_count):
      self.assertEqual(len(response_data), expected_count)
      expected_attrs_in_datarow = 22  #how many fields to expect 
      for one_item in response_data:      
        self.assertEqual(len(one_item.keys()), expected_attrs_in_datarow)
      print("Response: " + str(response_data) + " is well-formed.") 





