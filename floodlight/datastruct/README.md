#常用数据结构

##DatapathId

##OFPort

##Link 
    DatapathId src      : src-switch
     OFPort    srcPort  : src-port
    DatapathId dst      : dst-switch
    OFPort     dstPort  : dst-port

##NodePortTuple

    DatapathId nodeId
    OFPort portId

##Route

    RouteId  id
    List<NodePortTuple> switchPorts;
    int routeCount

##RouteId
    
    DatapathId src
    DatapathId dst
    U64 cookie

##RoutingDecision

    RoutingAction action
    Match match
    short hardTimeout
    SwitchPort srcPort
    IDevice srcDevice
    List<IDevice> destDevices
    List<SwitchPort> broadcastIntertfaces

