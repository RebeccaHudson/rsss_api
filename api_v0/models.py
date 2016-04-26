from __future__ import unicode_literals

from django.db import models

# Create your models here.
class ScoresRow(models.Model):
  id = models.AutoField(primary_key=True)
  snpid = models.CharField(max_length=40)
  motif = models.CharField(max_length=20)
  motif_len = models.IntegerField(default=0)
  log_lik_ref = models.FloatField(default=0)
  log_lik_snp = models.FloatField (default=0)
  log_lik_ratio = models.FloatField (default=0)
  log_enhance_odds = models.FloatField (default=0)
  log_reduce_odds  = models.FloatField (default=0)
  ref_start = models.IntegerField(default=0)
  snp_start = models.IntegerField(default=0)
  ref_end = models.IntegerField(default=0)
  snp_end = models.IntegerField(default=0)
  ref_strand = models.CharField(max_length=1, default="")
  snp_strand = models.CharField(max_length=1, default="")
  #There should be some way to determine from the data in this model 
  #What transcription factors are involved for this row
  #eg: what's the threshold for each column to say that it's involved.
  class Meta:
    managed = False
    db_table = 'snp_scores_1'

