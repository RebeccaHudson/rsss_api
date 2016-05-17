from __future__ import unicode_literals

from django.db import models
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model


## Create your models here.
#class ScoresRow(models.Model):
#  id = models.AutoField(primary_key=True)
#  snpid = models.CharField(max_length=40)
#  motif = models.CharField(max_length=20)
#  motif_len = models.IntegerField(default=0)
#  log_lik_ref = models.FloatField(default=0)
#  log_lik_snp = models.FloatField (default=0)
#  log_lik_ratio = models.FloatField (default=0)
#  log_enhance_odds = models.FloatField (default=0)
#  log_reduce_odds  = models.FloatField (default=0)
#  ref_start = models.IntegerField(default=0)
#  snp_start = models.IntegerField(default=0)
#  ref_end = models.IntegerField(default=0)
#  snp_end = models.IntegerField(default=0)
#  ref_strand = models.CharField(max_length=1, default="")
#  snp_strand = models.CharField(max_length=1, default="")
#  #There should be some way to determine from the data in this model 
#  #What transcription factors are involved for this row
#  #eg: what's the threshold for each column to say that it's involved.
#  class Meta:
#    managed = False
#    db_table = 'snp_scores_1'
#This is commented for reference as I try to make the switch to Cassandra.


# Create your models here.
class ScoresRow(models.Model):
  snpid = columns.Text(primary_key=True, index=True) 
  motif = columns.Text() 
  motif_len = columns.Integer()
  log_lik_ref = columns.Float()  
  log_lik_snp = columns.Float() 
  log_lik_ratio =columns.Float() 
  log_enhance_odds =columns.Float() 
  log_reduce_odds =columns.Float()
  ref_start=columns.Integer()
  snp_start=columns.Integer() 
  ref_end =columns.Integer() 
  snp_end = columns.Integer()
  ref_strand = columns.Text() 
  snp_strand = columns.Text() 
  pval_ref = columns.Float()
  pval_snp = columns.Float()
  pval_cond_ref = columns.Float()
  pval_cond_snp = columns.Float()
  pval_diff = columns.Float()
  pval_rank = columns.Float() 
  chromosome = columns.Text(primary_key=True)
  pos = columns.Integer(primary_key=True)
  #There should be some way to determine from the data in this model 
  #What transcription factors are involved for this row
  #eg: what's the threshold for each column to say that it's involved.
  class Meta:
    managed = False
    db_table = 'snp_scores_2'
