from __future__ import unicode_literals

from django.db import models
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model


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
  chr = columns.Text(primary_key=True)
  pos = columns.Integer(primary_key=True)
  class Meta:
    managed = False
    #db_table = 'snp_scores_2'  #this doesn't do anything, apparently

class PlottingData(models.Model):
  snpid = columns.Text(primary_key=True, index=True) 
  motif = columns.Text() 
  ref_seq = columns.Text()
  snp_seq = columns.Text()
  motif_len = columns.Integer()
  log_lik_ref = columns.Float()  
  log_lik_snp = columns.Float() 
  log_lik_ratio =columns.Float() 
  log_enhance_odds =columns.Float() 
  log_reduce_odds =columns.Float()
  iupac = columns.Text()
  ref_match_seq = columns.Text()
  snp_match_seq = columns.Text()
  ref_seq_snp_match = columns.Text()
  snp_seq_ref_match = columns.Text()
  snp_ref_start = columns.Integer()
  snp_ref_end = columns.Integer() 
  snp_ref_length = columns.Integer()
  ref_aug_match_seq_forward = columns.Text()
  ref_aug_match_seq_reverse = columns.Text()
  snp_aug_match_seq_forward = columns.Text()
  snp_aug_match_seq_reverse = columns.Text()
  ref_location = columns.Integer()
  snp_location = columns.Integer()
  ref_extra_pwm_left = columns.Float()
  ref_extra_pwm_right = columns.Float()
  snp_extra_pwm_left = columns.Float()
  snp_extra_pwm_right = columns.Float() 
  ref_start=columns.Integer()
  snp_start=columns.Integer() 
  ref_end =columns.Integer() 
  snp_end = columns.Integer()
  ref_strand = columns.Text() 
  snp_strand = columns.Text() 
  class Meta:
    managed = False



