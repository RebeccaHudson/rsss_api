from __future__ import unicode_literals

from django.db import models


# Create your models here.
class ScoresRow(models.Model):
  snpid = models.CharField(max_length=30)
  motif = models.CharField(max_length=30) 
  motif_len = models.IntegerField()
  log_lik_ref = models.FloatField()  
  log_lik_snp = models.FloatField() 
  log_lik_ratio =models.FloatField() 
  log_enhance_odds =models.FloatField() 
  log_reduce_odds =models.FloatField()
  ref_start=models.IntegerField()
  snp_start=models.IntegerField() 
  ref_end =models.IntegerField() 
  snp_end = models.IntegerField()
  ref_strand = models.CharField(max_length=3) 
  snp_strand = models.CharField(max_length=3) 
  pval_ref = models.FloatField()
  pval_snp = models.FloatField()
  pval_cond_ref = models.FloatField()
  pval_cond_snp = models.FloatField()
  pval_diff = models.FloatField()
  pval_rank = models.FloatField() 
  chr = models.CharField(max_length=10)
  pos = models.IntegerField()
  class Meta:
    managed = False
    db_table = 'snp_scores_2'
