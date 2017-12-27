class InvalidQueryError(Exception):
    #Indicates bad input on the part of the user.
    pass


class NoDataFoundError(Exception):
    #Indicates that a valid query came up empty. 
    #Can't proceed with the query as expected.
    pass



class MissingBackendDataError(Exception):
    #Indicates that we don't have data for a Gene or other
    #entity that needs to be found to facilitilate another query.
    pass
