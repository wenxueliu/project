
默认是不开启的, 可以通过 RESTful 接口开启.
默认是所有包都 Drop
可以通过 RESTful 接口增加规则, 选择 allow 或 deny
缺点是 没有流量监控, PACKET_IN 过来的时候,才过滤. 显然如果遇到 DDOS 攻击, 基本上 Controller 会先挂掉, 
而不是防止 DDOS


##Firewall

IFloodlightProviderService floodlightProvider
IStorageSourceService storageSource
IRestApiService restApi

List<FirewallRule> rules  : 防火墙规则列表
boolean enabled           : 是否启用防火墙, 默认不启用
IPv4Address subnet_mask = IPv4Address.of("255.255.255.0")


###Command receive(IOFSwitch sw, OFMessage msg, FloodlightContext cntx)

如果 enable == false, 不启用防火墙, 跳出对 PACKET_IN 包的处理

如果 enable == true, 启用防火墙

1. 接受 PACKET_IN 消息
2. 获取 FloodlightContext 的 storage 中 key 为 "net.floodlightcontroller.routing.decision" 所对应的值为 decision
3. 调用 processPacketInMessage(sw, (OFPacketIn) msg, decision, cntx) 处理该消息

###processPacketInMessage(IOFSwitch sw, OFPacketIn pi, IRoutingDecision decision, FloodlightContext cntx)

1. 如果目的 MAC 是 FFFFFFFFFFFF, 创建 "MULTICAST" 路由
2. 如果目的 IP 是广播地址(即子网是*.*.*.255), 创建"Drop"路由
3. 如果 decision == null, 调用 matchWithRule(sw, pi, cntx) 获取 rule

        如果 rule 是 null 或 DROP, 就默认为 DROP
        否则 增加  RoutingDecision 为 FORWARD_OR_FLOOD

注: decision = contx.storage("net.floodlightcontroller.routing.decision") 为 decision

那么, 防火墙什么时候起作用呢 ?

在 Forwarding 中 的 Forwarding.java 中, 当接受到 PACKET_IN 消息的时候, 调用 Command processPacketInMessage(IOFSwitch sw, OFPacketIn pi, IRoutingDecision decision, FloodlightContext cntx)
起作用, 这里你会看到 ALLOW, DROP.


###RuleMatchPair matchWithRule(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx)

    rmp : RuleMatchPair 对象

    1. 遍历所有的 rules, 对每个 rule 调用 matchesThisPacket(sw,in_port,adp) 
    将 pi, sw 与 成员 dpid, in_port, dl_src, dl_dst, dl_type, 
    nw_src_prefix_and_mask, nw_dst_prefix_and_mask, 
    nw_proto, tp_src, tp_dst 比较, 是否匹配
    2. 如果匹配, 初始化 rmp.rule 为 match_rule , rmp.match 为 adp
       否则, 增加一条精确的匹配规则, 默认为 DROP, 

    返回 rmp


###readRulesFromStorage()

从 storageSource 读取所有的规则

