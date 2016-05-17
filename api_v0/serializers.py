from rest_framework import serializers
from api_v0.models import ScoresRow

#for whatever reason, this does NOT want to be a ListSerializer, 
#I get info that says 'child is a required element'
class ScoresRowSerializer(serializers.ModelSerializer):
  class Meta:
    model = ScoresRow
    fields = ('id', 'chromosome', 'pos', 
              'snpid', 'motif', 'motif_len', 
              'log_lik_ref', 'log_lik_snp', 'log_lik_ratio', 'log_enhance_odds', 'log_reduce_odds',
              'ref_start', 'snp_start', 'ref_end', 'snp_end',
              'ref_strand', 'snp_strand',
              'pval_ref', 'pval_snp',
              'pval_cond_ref', 'pval_cond_snp', 
              'pval_diff', 'pval_rank',)

