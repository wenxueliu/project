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
   