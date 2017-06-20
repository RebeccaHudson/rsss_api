from rest_framework import serializers
from api_v0.models import ScoresRow

#for whatever reason, this does NOT want to be a ListSerializer, 
#I get info that says 'child is a required element'

# dropped fields:       'ref_start', 'snp_start', 'ref_end', 'snp_end',
class ScoresRowSerializer(serializers.ModelSerializer):
  class Meta:
    model = ScoresRow
    fields = ('chr', 'pos', 
              'snpid', 'motif',  
              'log_lik_ref', 'log_lik_snp', 'log_lik_ratio', 
              'log_enhance_odds', 'log_reduce_odds',
              'ref_strand', 'snp_strand',
              'pval_ref', 'pval_snp',
              'pval_cond_ref', 'pval_cond_snp', 
              'pval_diff', 'pval_rank', 'refAllele', 'snpAllele',
               'snp_aug_match_seq', 'snp_extra_pwm_off',
               'ref_aug_match_seq', 'ref_extra_pwm_off',
               'motif_bits',)

