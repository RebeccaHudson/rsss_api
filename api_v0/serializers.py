from rest_framework import serializers
from api_v0.models import ScoresRow
from api_v0.models import PlottingData
#for whatever reason, this does NOT want to be a ListSerializer, 
#I get info that says 'child is a required element'
class ScoresRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoresRow
        fields = ('chr', 'pos', 
                  'snpid', 'motif', 'motif_len', 
                  'log_lik_ref', 'log_lik_snp', 'log_lik_ratio', 'log_enhance_odds', 'log_reduce_odds',
                  'ref_start', 'snp_start', 'ref_end', 'snp_end',
                  'ref_strand', 'snp_strand',
                  'pval_ref', 'pval_snp',
                  'pval_cond_ref', 'pval_cond_snp', 
                  'pval_diff', 'pval_rank',)

class PlottingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlottingData
        fields = ('snpid','motif','ref_seq','snp_seq','motif_len','ref_start',
                 'ref_end','ref_strand','snp_start','snp_end','snp_strand',
                 'log_lik_ref','log_lik_snp','log_lik_ratio','log_enhance_odds',
                  'log_reduce_odds','iupac','ref_match_seq','snp_match_seq',
                  'ref_seq_snp_match','snp_seq_ref_match','snp_ref_start','snp_ref_end',
                  'snp_ref_length','ref_aug_match_seq_forward','ref_aug_match_seq_reverse',
                  'snp_aug_match_seq_forward','snp_aug_match_seq_reverse','ref_location',
                  'snp_location','ref_extra_pwm_left','ref_extra_pwm_right','snp_extra_pwm_left'
                  ,'snp_extra_pwm_right',)

