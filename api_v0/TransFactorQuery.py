#Some of these imports may not be needed
from rest_framework.response import Response
from rest_framework import status 
from ElasticsearchQuery import ElasticsearchAtsnpQuery

class TransFactorQuery(ElasticsearchAtsnpQuery):
    def prepare_json_for_query(self):
        #use a try/catch here.
        return self.query_for_tf()

    #This can have length > 1, but usually = 1.
    #This should spit by throwing an Exception.
    def prepare_motif_list(self):
        one_or_more_motifs = self.request.data.get('motif')
        if one_or_more_motifs is None: 
            return Response('No motif specified!', 
                            status = status.HTTP_400_BAD_REQUEST)    
        #There is not a great regex for motifs. 
        return one_or_more_motifs 

    def query_for_tf(self):
        motif_str = self.prepare_motif_list() 
        j_dict = {"must" :{"terms":{"motif": motif_str }}}
        return j_dict
 
