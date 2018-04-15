##LogicalOFMessageCategory

###关键变量

    LogicalOFMessageCategory MAIN =  new LogicalOFMessageCategory("MAIN", OFAuxId.MAIN)
    String name
    OFAuxId auxId

###LogicalOFMessageCategory(@Nonnull String name, int auxId)
###LogicalOFMessageCategory(@Nonnull String name, OFAuxId auxId)
OFAuxId getAuxId()
String getName()
