import json
import requests
from django.conf import settings
import random

#The purpose of this class is to work all of the space-saving data
#transformations backwards.
#Needs to lookup snp_info from Elasticsearch. (Might be a little slower, but this makes it more feasible.)
#
#  Takes the minified record as an argument to the constructor. 
#  The resuting object has a reconstructed_data() method that returnes the 
#  actual reconstructed data.
#  To use, feed the record to the consturctor.
#  if the constructor succeeds, the reconstructed record can be pulled
#  w/ get_reconstructed_record.
class DataReconstructor(object):

    def __init__(self, record):
        #print "keys in record prior to processing: " + repr(record.keys())
        doc_id = record['id'] 
        #record = record['_source']
        self.rebuilt = \
          self.reconstruct_reduced_record(record, doc_id)

    def get_reconstructed_record(self):    
        return self.rebuilt 

    def reconstruct_reduced_record(self, red, doc_id): 
        #print "keys in record during reconstruction: " + repr(red.keys())
        #doc_id = red['_id']   use when the _id field is added to the _source.
        red.update(self.unbox_strand_info(red['ref_and_snp_strand']))
        red['snpid'] = self.rebuild_snpid(red['snpid'])
        snp_info = self.grab_snp_info_from_es(red['snpid'])
        ref_seq = self.get_ref_seq(snp_info, red)
        snp_seq = self.get_snp_seq(ref_seq, red, doc_id)
        red['snp_aug_match_seq'] = snp_seq
        red['ref_aug_match_seq'] = ref_seq
        #print "keys in record after reconstruction : " + repr(red.keys())
        red.update(self.reconstruct_alleles(red)) 
        red['chr'] = self.reconstruct_chromosome(red['chr'])
        return red 

    def grab_snp_info_from_es(self, snpid):
        machines_to_try = settings.ELASTICSEARCH_URLS[:]
        random.shuffle(machines_to_try) 
        #print "machines to try " + str(machines_to_try)
        base = machines_to_try.pop()
        url = '/'.join([ base,  settings.ES_INDEX_NAMES['SNP_INFO'],
                         'sequence', snpid])
        #select a basae url randomly.
        d = requests.get(url)
        r = json.loads(d.text)
        try :
            return r['_source']
        except KeyError:
            print "missing data for snpid : " + snpid
            print repr(r)
            exit(1)

    def rebuild_snpid(self, snpid):
        return 'rs' + str(snpid)

    def reconstruct_chromosome(self, ch):
         if ch < 23:
           return 'ch' + str(ch)
         non_numeric_chromosomes = \
          { 23: 'X', 24: 'Y', 25: 'M' }        
         return 'ch' + non_numeric_chromosomes[ch]

    def reconstruct_alleles(self, atsnp_data):
         pos = self.get_snp_position(atsnp_data) - 1
         rA = atsnp_data['ref_aug_match_seq'][pos]
         sA = atsnp_data['snp_aug_match_seq'][pos]
         #Complement the reference and SNP alleles if they're on '-' strands.
         if atsnp_data['ref_strand'] == '-':
             rA = self.comp(rA)
         if atsnp_data['snp_strand'] == '-':
             sA = self.comp(sA)
         return {'refAllele' :  rA, 'snpAllele' : sA }

    def numbersToBases(self, myInput):
        bases = ""
        base_map = { '1': 'A', '2': 'C',
                     '3': 'G', '4': 'T' }
        for i in range(0, len(myInput)):
            bases += base_map[myInput[i]]        
        return bases

    #takes the complement
    def comp(self, myInput):
        bases = ""
        base_map = { 'A': 'T', 'G': 'C',
                     'C': 'G', 'T': 'A' }
        for i in range(0, len(myInput)):
            bases += base_map[myInput[i]]
        return bases

    def unbox_strand_info(self, ref_and_snp):
        #This should be a number 1 to 4
        cipher = { 1 : '++', 2: '+-', 3: '-+', 4: '--' } 
        bits = cipher[ref_and_snp]
        return { 'ref_strand' : bits[0], 'snp_strand' : bits[1] }

    #Take a snpinfo and a datum and come up with the ref sequence
    #both arguments are already in JSON format, and are just the '_source'
    def get_ref_seq(self, snp_info, atsnp_data):
        #snp_start and snp_end, as well as ref_start 
        #and ref_end are distilled down to these:
        start_slot = atsnp_data['seq_start']
        end_slot = atsnp_data['seq_end']

        sequence_mat = snp_info['sequence_matrix']
        ref_offset = int(atsnp_data['ref_extra_pwm_off']) 

        ref_seq = sequence_mat[start_slot - 1: end_slot]
        ref_seq = self.numbersToBases(ref_seq)
        if atsnp_data['ref_strand'] == '-':
            #complement the REF strand.
            ref_seq = self.comp(ref_seq)
        return ref_seq

    def get_snp_seq(self, ref_seq, atsnp_data, doc_id):
        snp_pos = self.get_snp_position(atsnp_data)
        snp_seq = ref_seq
        if atsnp_data['ref_strand'] != atsnp_data['snp_strand']:        
            snp_seq = self.comp(snp_seq) 

        #SNP allele is the last letter in the document's ID.
        sub_base = doc_id[len(doc_id) - 1]

        #substitute the refAllele for the SNPAllele,
        #complement the snpAllele IFF snp_strand is '-'
        if atsnp_data['snp_strand'] == '-':
            sub_base = self.comp(sub_base)    

        snp_seq = list(snp_seq)
        snp_seq[snp_pos - 1] = sub_base 
        snp_seq = ''.join(snp_seq)
        return snp_seq 

    #getting the SNP sequence.
    def get_snp_position(self, atsnp_data):
        #actual_start = min(int(atsnp_data['snp_start']), int(atsnp_data['ref_start']))
        actual_start = atsnp_data['seq_start']
        snp_pos = 31 - (actual_start - 1)
        return snp_pos
    
    #takes the complement
    def comp(self, myInput):
        bases = ""
        base_map = { 'A': 'T', 'G': 'C',
                     'C': 'G', 'T': 'A' }
    
        for i in range(0, len(myInput)):
            bases += base_map[myInput[i]]
    
        return bases
