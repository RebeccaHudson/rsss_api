import json
#A class from which all of our queries inherits.

class ElasticsearchAtsnpQuery(object):

    def __init__(self, request):   
        self.request = request
        self.query = self.setup_query()
    
    def get_query(self):
        return self.query

    #possible to put the Pvalue stuff into its own class?
    def setup_pvalue_filter(self):
        pvd = self.get_pvalue_dict()
        return self.prepare_json_for_pvalue_filter_directional(pvd)

    def get_pvalue_dict(self):
        pv_dict = {}
        #print "request " + str(request.data)
        for pv_name in ['rank', 'ref', 'snp']:
            key  = "_".join(['pvalue', pv_name])
            if self.request.data.has_key(key):
                pv_dict[key] = self.request.data[key]
        if 'pvalue_rank' not in pv_dict:
            pv_dict[key] = settings.DEFAULT_P_VALUE
        if self.request.data.has_key('pvalue_snp_direction'):
           pv_dict['pvalue_snp_direction'] = self.request.data['pvalue_snp_direction'] 
        if self.request.data.has_key('pvalue_ref_direction'):
           pv_dict['pvalue_ref_direction'] = self.request.data['pvalue_ref_direction']

        return pv_dict     

    def prepare_json_for_pvalue_filter_directional(self, pvalue_dict):
       #pvalue_snp is missing at this point..
       #print "prior to processing " + str(pvalue_dict)
       dict_for_filter = { "filter": [
         {
           "range" : {
               "pval_rank": {
                   "lte":  str(pvalue_dict['pvalue_rank']) 
               }
           }
         }
       ]
       }
       if 'pvalue_ref' in  pvalue_dict:
           pvalue_ref_direction = pvalue_dict['pvalue_ref_direction']
           if pvalue_ref_direction == 'lt' and pvalue_dict['pvalue_ref'] == 0:
               pvalue_ref_direction = 'lte' 
           #either lte or gte
           dict_for_filter['filter'].append({
               "range" : {
                   "pval_ref": {
                       pvalue_ref_direction:  str(pvalue_dict['pvalue_ref']) 
                   }
               }
           })
       if 'pvalue_snp' in pvalue_dict:  
           pvalue_snp_direction = pvalue_dict['pvalue_snp_direction']
           if pvalue_snp_direction == 'lt' and pvalue_dict['pvalue_snp'] == 0:
               pvalue_snp_direction = 'lte' #don't exclude records w/ pvalue = 0
           dict_for_filter['filter'].append({
           "range" : {
               "pval_snp": {
                   pvalue_snp_direction:  str(pvalue_dict['pvalue_snp']) 
                          }
                     }
           })
       return dict_for_filter 

    #For sort, 'coordinate' means 'chr' and 'pos'
    #Replace coordinate with the fields chr and pos, in that order.
    def prepare_json_for_custom_sort(self, sort_orders):
        so = sort_orders['sort']
        for i, x  in enumerate(so):
            if x.keys()[0] == 'coordinate':
                print "translating" #  x['coordinate']
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

    def elasticsearch_base_query(self, query_data, pvalue_filter):
        q = {"query":
              {"bool": 
                { "must" : query_data["must"],   
                  "filter" : pvalue_filter['filter']
                }
              }
            }
        return q

    #handle blanks for all fields.
    def setup_query(self):
        j_dict = self.setup_sort()

        query_data = self.prepare_json_for_query() 
        #TODO: use a try-catch thing for this.
        #contents of the ES query's 'must' key.
        #will return an error if bad cordinates.            
        pvalue_filter =  self.setup_pvalue_filter()

        base_query = self.elasticsearch_base_query(query_data, pvalue_filter)
        j_dict.update(base_query) 
        json_out = json.dumps(j_dict)
        return json_out

