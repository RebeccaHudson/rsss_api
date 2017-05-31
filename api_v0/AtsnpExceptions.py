class InvalidQueryError(Exception):
    #Indicates bad input on the part of the user.
    pass


class NoDataFoundError(Exception):
    #Indicates that a valid query came up empty. 
    #Can't proceed with the query as expected.
    pass
