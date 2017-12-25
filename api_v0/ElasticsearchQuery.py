import json
from rest_framework.response import Response
from rest_framework import status
from AtsnpExceptions import * 
from django.conf import settings
#A class from which all of our queries inherit.

class ElasticsearchAtsnpQuery(object):

    def __init__(self, request):   
        self.request = request
        self.query = self.setup_query()

    def get_query(self):
        print "************************  " + repr(self.query)
        return self.query

    #possible to put the Pvalue stuff into its own class?
    def setup_pvalue_filter(self):
        pvd = self.get_pvalue_dict()
        if len(pvd.keys()) == 1:
            print "detected DEFAULT mode p-value rank is the only one specified."
            return self.prepare_json_for_pvalue_filter_default(pvd)
        return self.prepare_json_for_pvalue_filter_directional(pvd)

    #TODO: find out if > 1 pvalue is required.
    def get_pvalue_dict(self):
        pv_dict = {}
        #print "request " + str(request.data)
        for pv_name in ['rank', 'ref', 'snp']:
            key  = "_".join(['pvalue', pv_name])
            if self.request.data.has_key(key):
                pv_dict[key] = self.request.data[key]
                #if that p-value is included, check for its direction.
                key = '_'.join(['pvalue', pv_name, 'direction'])    
                if self.request.data.has_key(key):
                    pv_dict[key] = self.request.data[key] 

        #if no p-values are included, set rank from defaults.
        #(should not be triggered by that atSNP web interface)
        if not pv_dict:
            pv_dict['pvalue_rank'] = settings.DEFAULT_P_VALUE
        return pv_dict     

    #Don't require less zero if the direction is < 
    def fix_lte_for_zero_pvalues(self, operator, pvalue):
        if operator == 'lt' and pvalue == 0:
            return 'lte'        
        return operator 

    #(The terms direction and operator are used synonomously here)
    def prepare_json_for_pvalue_filter_directional(self, pvalue_dict):
       #pvalue_snp is missing at this point..
       #print "prior to processing " + str(pvalue_dict)
       dict_for_filter = { "filter" : [] }
       #pvalue rank always gets less than or equal to.
       for one_pv in ['rank', 'ref', 'snp']:
           pvalue_name = '_'.join(['pvalue', one_pv])
           direction = None
           if pvalue_name in pvalue_dict: 
               pvalue = pvalue_dict[pvalue_name]
               if one_pv == 'rank':
                   direction = 'lte'
               else: 
                   which_direction = '_'.join([pvalue_name, 'direction'])
                   direction = \
                    self.fix_lte_for_zero_pvalues(pvalue_dict[which_direction],
                                                  pvalue)
               pvalue_name_in_index = '_'.join(['pval', one_pv])
               dict_for_filter['filter'].append({
                   "range" : {
                       pvalue_name_in_index : { direction : str(pvalue) }
                    }
                })
       return dict_for_filter 




    def setup_range_clause(self, pvalue, clause_info):
        pv = str(clause_info['cutoff'])
        operator = clause_info["operator"] 
        clause = { "range" : { pvalue : { operator: pv } } }  
        return clause

    def setup_one_pval_case(self, gain_or_loss): 
        which_case = settings.GAIN_AND_LOSS_DEFS[gain_or_loss]
        one_case = { "bool":{ "must" : [] } }
        for one_pval in [ "pval_ref", "pval_snp"]:
            clause_info = which_case[one_pval]
            rc = self.setup_range_clause(one_pval, clause_info) 
            one_case["bool"]["must"].append(rc)
        return one_case

    #SHOULD BE REFACTORED.
    #(The terms direction and operator are used synonomously here)
    def prepare_json_for_pvalue_filter_default(self, pvalue_dict):
       #pvalue_snp is missing at this point..
       dict_for_filter = { "filter" : [] }
       dict_for_filter['filter'].append({
           "range" : {
               'pval_rank' : { 'lte': str(pvalue_dict['pvalue_rank']) }
            }
       })
       compound_filter = {"bool": {"minimum_should_match" : 1, "should":[] }}
       gain_condition = self.setup_one_pval_case("gain")
       compound_filter["bool"]["should"].append(gain_condition)  
       #compound_filter["bool"]["should"].append(
       #  { "bool" : { "must" : [
       #                        { "range": { "pval_ref": { "lte": "0.002" } } },
       #                        { "range": { "pval_snp": { "lte": "0.002" } } }
       #                      ]
       #             }
       #  })

       loss_condition = self.setup_one_pval_case("loss")
       compound_filter["bool"]["should"].append(loss_condition)  
       #compound_filter["bool"]["should"].append(
       #  { "bool" : { "must" : [
       #                        { "range": { "pval_ref": { "gte": "0.002" } } },
       #                        { "range": { "pval_snp": { "gte": "0.002" } } }
       #                      ]
       #             }
       #  })
       dict_for_filter["filter"].append(compound_filter) 
       return dict_for_filter 
 
  



       #pvalue rank always gets less than or equal to.
       for one_pv in ['rank', 'ref', 'snp']:
           pvalue_name = '_'.join(['pvalue', one_pv])
           direction = None
           if pvalue_name in pvalue_dict: 
               pvalue = pvalue_dict[pvalue_name]
               if one_pv == 'rank':
                   direction = 'lte'
               else: 
                   which_direction = '_'.join([pvalue_name, 'direction'])
                   direction = \
                    self.fix_lte_for_zero_pvalues(pvalue_dict[which_direction],
                                                  pvalue)
               pvalue_name_in_index = '_'.join(['pval', one_pv])
               dict_for_filter['filter'].append({
                   "range" : {
                       pvalue_name_in_index : { direction : str(pvalue) }
                    }
                })
       return dict_for_filter 






       #For query with extra conditions added: 
       #try to use this twice -> 
   

       #in setup_pvalue_filter, check the p-values for the condition where:
       #     p-value rank is set and the other 2 are not. 
       #     if this condition is present:
       #         create 2 pvalue-dicts based on the one that was provided by self.get_pvalue_dict()
       #         use prepare_json_for_pvalue_filter_directional on each of them. 
       #         bool them together using proper Elasticsearch query syntax.
       #prepare 2 p-value filters, 'or' them.
       #     if this condition is not present:
       #       do exactly what has been done up until now.








    #For sort, 'coordinate' means 'chr' and 'pos'
    #Replace coordinate with the fields chr and pos, in that order.
    def prepare_json_for_custom_sort(self, sort_orders):
        so = sort_orders['sort']
        for i, x  in enumerate(so):
            if x.keys()[0] == 'coordinate':
                #print "translating" #  x['coordinate']
                #get a copy of the order dict
                x[u'chr'] = x['coordinate']
                pos = { u'pos' : x['coordinate'] }
                where_to_put = i + 1
                del x['coordinate']
                break
        so.insert(where_to_put, pos)
        sort_orders['sort'] = so
        return sort_orders

    def setup_sort(self):
        sort_order = self.request.data.get('sort_order')
        return self.prepare_json_for_custom_sort(sort_order)

    def setup_paging_parameters(self):
        params = {}
        for one_key in ['from_result', 'page_size']:
            params[one_key] = self.request.data.get(one_key)     
        return params

    #This is the format we want the compound DEFAULT query to fit into.
    def elasticsearch_base_query(self, query_data, pvalue_filter):
        q = {"query":
              {"bool": 
                { "must" : query_data["must"],   
                  "filter" : pvalue_filter['filter']
                }
              }
            }
        return q

    #which values should be an array of numbers between 1 and 4.
    def append_motif_ic_filter(self, dict_for_filter, which_values):
        ic_int_values = [ int(x) for x in which_values ]
        dict_for_filter['filter'].append({
        "terms" : {
            "motif_ic": ic_int_values
                  }
               })
   
    #Filter by information content if
    # 1. The field is not missing AND
    # 2. Not all information content levels are included.
    def does_ic_filter_apply(self):
        if self.request.data.get('ic_filter') is None \
          or len(self.request.data.get('ic_filter')) == 4:
            #print "No need to apply a filter by motif information content."
            return False
        return True
        
    #handle blanks for all fields.
    def setup_query(self):
        j_dict = self.setup_sort()
        query_data = self.prepare_json_for_query() 
        #TODO: use a try-catch thing for this.
        #contents of the ES query's 'must' key.
        #will return an error if bad cordinates.            
        pvalue_filter =  self.setup_pvalue_filter()
        if self.does_ic_filter_apply():
            #If this search turns up empty, check if it wouldn't be without the 
            #information content filtering.
            motif_ic_values = self.request.data.get('ic_filter')
            self.append_motif_ic_filter(pvalue_filter, motif_ic_values)
            
        base_query = self.elasticsearch_base_query(query_data, pvalue_filter)
        j_dict.update(base_query) 
        json_out = json.dumps(j_dict)
        return json_out

