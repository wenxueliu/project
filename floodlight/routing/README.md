##BroadcastTree

    HashMap<DatapathId, Link> links
    HashMap<DatapathId, Integer> costs

##RoutingDecision

    RoutingAction action
    Match match
    short hardTimeout
    SwitchPort srcPort
    IDevice srcDevice
    List<IDevice> destDevices
    List<SwitchPort> broadcastIntertfaces


#ForwardingBase.java


##方法说明
###boolean pushRoute(Route route, Match match, OFPacketIn pi,
###                 DatapathId pinSwitch, U64 cookie, FloodlightContext cntx,
###                 boolean reqeustFlowRemovedNotifn, boolean doFlush,
###                 OFFlowModCommand flowModCommand)

    获取 route 的端口列表(交换机+交换机端口)，遍历端口列表
        根据 flowModCommand(ADD, DELETE, DELETE_STRICT, 
        MODIFY, MODIFY_STRICT) 命令来初始化对应类型的流表，match 基于 match 参数和 路由的源端口，
        action 是转发到目的端口
  
        此外，如果 route 某个端口对应的交换机与 pinSwitch 相同，调用 pushPacket() 构造 PACKET_OUT 消息转发到 packet_out 端口

    比如，flowModCommand 是 ADD， 那么增加增加一条流表， 匹配 match 的所有请求都转发到与路由器对应目的端口。

###void pushPacket(IOFSwitch sw, OFPacketIn pi, boolean useBufferId,OFPort outport, FloodlightContext cntx)

* 通过 pi 的 IN_PORT 与 outport 相同，直接返回
* 通过 pi，userBufferId, outport 构造 PacketOut 消息，即要求 sw 向 output 端口转发 pi.getData() 消息

###void packetOutMultiPort(byte[] packetData, IOFSwitch sw,OFPort inPort, Set<OFPort> outPorts, FloodlightContext cntx)

遍历 outPorts 的所有端口，通过 outPorts inPort packetData 构造 PacketOut 消息，即要求 sw 向 outPorts 所有端口转发 packetData 消息。

###boolean blockHost(IOFSwitchService switchService,SwitchPort sw_tup, MacAddress host_mac, short hardTimeout, U64 cookie)

要求向 sw_tup 关联的交换机增加一条流表，遇到进入交换机的端口是 sw_tup.getPort()， 源MAC是 host_mac 的数据包丢弃。

#Forwarding

##功能概述

    监听 PACKET_IN 事件。调用根据 decision 的 action 或 包的特性来转发或泛洪包。

##具体方法分析


###Command processPacketInMessage(IOFSwitch sw, OFPacketIn pi, IRoutingDecision decision, FloodlightContext cntx)

    如果 descision 不是 null， 根据 decision.getRoutingAction() 动作调用相应的动作。主要分为转发包，丢弃包，泛洪包。
    否则，根据 pi 中 网卡类型来转发包，如果 isBroadCast() 或 isMulticast() 就调用 doFlood(sw, pi, cntx)，否则调用 doForwardFlow(sw, pi, cntx, false)

###void doDropFlow(IOFSwitch sw, OFPacketIn pi, IRoutingDecision decision, FloodlightContext cntx)

    在 sw 上增加一条丢弃包流表，其中 match 的选择： 如果 decision.getMatch() 不为 null， 选择之，否则，用 pi.getMatch()

###void doForwardFlow(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx, boolean requestFlowRemovedNotifn)

    获取 目的设备(dstDevice） 
    如果 目的设备为(dstDevice) NULL，调用 doFlood() 泛洪。
    否则，如果 检查源设备或源集群是 null， 直接返回
         如果 源设备srcDevice 和目标设备dstDevice 的某个挂载点(attachmentPoint)
         1. 在同一集群的同一交换机，直接返回
         2. 在不同集群， 调用 doFlood() 泛洪后返回
         3. 在同一集群的不同交换机， 遍历源设备(srcDevice)和目的设备(dstDevice)的排序后挂载点(attachmentPoint)， 
            如果对应的挂载点在同一集群不同交换或不同端口并且路由引擎(RoutingEngineServer)存在两者之间的路由，
            从 decision 或 pi 构建路由匹配(routeMatch), 调用 pushRoute()  

###void doFlood(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx)

    从 pi 中得到 inPort, 
    如果 isIncomingBroadcastAllowed(sw,inPort) 是 false，返回
    否则 向 sw 发送 PACKET_OUT 消息，使其将包转发到所有端口（输入端口除外）
   
##IRouteService 

由 TopologyManage 实现
