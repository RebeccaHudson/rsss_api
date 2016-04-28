from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api_v0.models import ScoresRow 

from django.db import connection

class ScoresRowTests(APITestCase):
    #fixtures = ['one-row-data.json']
    def setUp(self):
      pass

    def test_retrieve_one_row_by_id(self):
        """
        Ensure that we can actually retreive one row of snp data.
        """
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
       
        connection.cursor().execute(sql)
        sql='INSERT INTO snp_scores_1 (snpid, motif, motif_len, log_lik_ref, log_lik_snp, log_lik_ratio, log_enhance_odds, log_reduce_odds, ref_start, snp_start, ref_end, snp_end, ref_strand, snp_strand) VALUES ( "rs548905050", "MA0002.2", 11,  -11.471,  -11.4598, -0.0112177, 2.7832, 2.97911, 24, 22, 34, 32, "+", "+" )'
        connection.cursor().execute(sql)
        url = reverse('api_v0:dummy-scores')
        #url = reverse('api_v0:one-scores', args=(99999,))
        response = self.client.get(url) 
        print(str(response))  
        #self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        #self.assertEqual(ScoresRow.objects.count(), 1)
        #self.assertEqual(ScoresRow.objects.get().name, 'DabApps')

  #  def test_retrieve_one_row_by_snpid(self):
  #    pass


  #  def test_scores_row_list_snpids(self):
  #   pass
  #   #There is some post data handled down here... 
  #   # data = {'name': 'DabApps'}
  #   # response = self.client.post(url, data, format='json')
  #   # self.assertEqual(response.status_code, status.HTTP_201_CREATED)
  #   # self.assertEqual(Account.objects.count(), 1)
  #   # self.assertEqual(Account.objects.get().name, 'DabApps')
