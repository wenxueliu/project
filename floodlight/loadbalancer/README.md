

一个 vip 下可以有多个 pool, 每个 pool 下可以有多个 member(即实际的服务器).


通过 vips 来做负载均衡, 每一个 vip 代表一个负载均衡服务器集群, 一个 vip 下可以有多个 pool, 外边访问 vip, 通过负载均衡, 
选择 vip 中的某一个pool 中 member 来处理外部请求. 目前每次都只取第一个 pool 下的某个 member, member 的选择策略是轮询

当交换机发来 PACKET_IN 请求的时候, 如果包的目的ip 在 vips 中, 那么就认为是请求某个负载均衡集群, 对于这样的包, 如果是
ARP 包, 就发送对应的 ARP 应答包.  如果是 IPv4 包, 从 vip 中选择某一个 member, 从所有的设备中选择包 srcIp 和 member ip
的设备, 如果存在对应的设备, 两个设备都属于同一设备集群的不同交换机或同一交换机的不同端口, 两个设备存在路由,就在交换机中增加
两条流表, 将源ip 为 srcIP 的包设置目的 ip 为 member ip , 将目的 ip 为 srcIP 的包, 设置其源 ip 为 vip.  否则, 



##关键变量

    HashMap<Integer, String> vipIpToId 存储 vip : vipId 
    IStaticFlowEntryPusherService sfpService : 流表服务

###Command receive(IOFSwitch sw, OFMessage msg, FloodlightContext cntx)

只处理 PACKET_IN 类型的消息. 调用 processPacketIn()

如果是 ARP 包, 且 ARP 包的目标 IP 地址是某一个 vip, 就发送 ARP 应答包. 并且停止包处理.

如果是 IPv4 包, 

    如果是 TCP 包, 
    如果是 UDP 包,

将 srcIP, srcPort, dstIP, dstPort 记录在 pinfo 中
调用 getBkServerForClient(pinfo,pools.get(pinfo.getDip()+":"+pinfo.getDport())) 获取 bkserver
调用 pushBidirectionalVipRoutes(sw,pi,cntx,pinfo,bkserver, poolMac)


###getBkServerForClient(PacketInfo pi, LBPool pool)

    调用 syncWithLoadBalancerData(client, pool) 更新缓存
    根据 pi, pool 及负载均衡算法获取 bkserver 的 "ip:port" 字符串

###syncWithLoadBalancerData(String client, LBPool pool)

    同步 clientServerMap 中的数据, 删除pool 或 bkserver 是空的或者 isactive == 0 的机器


###void pushBidirectionalVipRoutes(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx, PacketInfo pinfo, String bkserver, String vipMac)

遍历所有的已知设备内的实体(主机), 如果某个设备的实体(主机)的 IP 与 client 的 IP 匹配, 就设置该设备为 
srcDevice, 如果某个设备的 IP 与 bkserver 中的 IP 一样, 就设置该设备为 dstDevice

如果srcDevice 或 dstDevice 为null, 返回

如果 sw 与 dstDevice 某一个挂载点在不同集群, 输出错误日志, 指出两个设备不在同一集群

如果 sw 与 dstDevice 某一个挂载点在同一集群的同一挂载点, 输出错误日志,指出包进入的端口和包的目的端口是
同一交换机的同一端口,此时, 类似,交换机的某一个端口的 entity 多个的两个建立链路

如果 sw 与 dstDevice 某一个挂载点在同一集群的不同挂载点:
* 遍历 srcDevice 的所有挂载点,并以所属集群序列排序
* 遍历 dstDevice 的所有挂载点,并以所属集群序列排序
* 遍历 排序后的 srcDevice 和 dstDeivce 如果在同一集群, 且交换机或端口不同, 
就调用 pushStaticVipRoute 建立两个方向的路由

注: 这里检查 sw, dstDevice 是否在同一集群和同一交换机的同一端口, 是因为, sw 既然能收到 srcDevice 包,就说明 sw
和 srcDevice 之间是连通的, 因此只需要检查 sw 和 dstDevice 

###void pushStaticVipRoute(boolean inBound, Route route, PacketInfo pinfo, String bkserver, String mac, long pinSwitch)




------------------------------------------------------------------------

原版
=================

###Command processPacketIn(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx)

如果是广播或多播的 ARP 包, ARP 请求包的目的 IP 在 vipIpToId 中存在, 就认为与负载均衡相关, 调用 vipProxyArpReply(sw, pi, cntx, vipId) 响应 ARP 包

如果是 IPv4 包, 目的 IP 在 vipIpToId 中存在, 构造 client = new IPClient(), 根据 TCP UDP ICMP 不同类型设置 client 
的 srcPort 和 targetPort, 根据 负载均衡策略选择合适的 member, 调用 pushBidirectionalVipRoutes(sw, pi, cntx, client, memeber) 设置双向路由, 之后调用 pushPacket 写交换机流表.

###void vipProxyArpReply(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx, String vipId)

构造 ARP 包, 并且发生 PACKET_OUT 包到 ARP 包的进入交换机的端口. 


###void pushBidirectionalVipRoutes(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx, IPClient client, LBMember member)

遍历所有的已知设备内的实体(主机), 如果某个设备的实体(主机)的 IP 与 client 的 IP 匹配, 就设置该设备为 
srcDevice, 如果某个设备的 IP 与 member 的 IP 一样, 就设置该设备为 dstDevice, 并且设置 member MAC
地址为 dstDevice 的 MAC 地址.

* boolean on_same_island = false 标记是否 dstDevice 某一 AttachmentPoint 与发送 PACKET_IN 包的交换机属于同一 island
* boolean on_same_if = false 标记是否 dstDevice 某一 AttachmentPoints 与发送 PACKET_IN 包的交换机属于同一交换机的同一端口
* 查找发送 PACKET_IN 包的交换机的 srcIsland
* 遍历 dstDevice 的每个 AttachmentPoint 所对应的交换机的 dstIsland, 如果 dstIsland 与 srcIsland 相同就设置 on_same_island 为 true, 如果 on_same_if = true 就设置 on_same_if. 并退出循环, 否则遍历所有的 

* on_same_island = false , on_same_if = false : 直接返回
* on_same_island = true , on_same_if = true : 直接返回
* on_same_island = true , on_same_if = false : 对 srcDevice 和 dstDevice 的 AttachmentPoints 根据所属 island 排序, 如果是同一 island 的不同交换机, 调用 routingEngineService.getRoute() 检查是否已经存在对应方向的路由, 如果不存在,调用 pushStaticVipRoute() 添加路由


###void pushStaticVipRoute(boolean inBound, Route route, IPClient client, LBMember member, IOFSwitch pinSwitch)

根据 inBound 增加流表: 
    
    如果 inBound 为 true, 增加的流表执行如下功能: 如果 srcIp 是 client.ip, 协议是 IPv4, 
    输入端口是 path.get(i), 协议(TCP,UDP,SCTP)源端口是 client.srcPort, 设置其 dstIp 为 member.ip, dstMAC 为 member.macString 转发端口为 path.get(i+1)

    如果 inBound 为 false, 增加的流表执行如下功能: 如果 dstIp 是 client.ip, 协议是 IPv4,
    输入端口是 path.get(i), 协议(TCP,UDP,SCTP)目的端口是 client.srcPort, 设置其 srcIP 为 member对应的 vip, srcMac
为 vip.macstring , 转发端口为 path.get(i+1)


BUG: 如果没有匹配 srcDevice dstDevice 的设备, 
     如果有匹配 srcDevice dstDevice 的设备, 但是 topologyService 没有发送 PACKET_IN 包 sw 对应的 island, 
     如果有匹配 srcDevice dstDevice 的设备, topologyService 有发送 PACKET_IN 包 sw 对应的 island,
           1. on_same_island = false , on_same_if = false : 直接返回
           2 on_same_island = true , on_same_if = false :  继续
           3. on_same_island = true , on_same_if = true : 直接返回
     如果 srcDevice 或 dstDevice 的 AttachmentPoint 对应的 DatapathId 为空, Comparator<SwitchPort> clusterIdComparator 会抛出异常 , 所以 clusterIdComparator 需要修复

###void pushPacket(IPacket packet, IOFSwitch sw, OFBufferId bufferId, OFPort inPort, OFPort outPort, FloodlightContext cntx, boolean flush)

   构造 PACKET_OUT 包, 并发送出去

   将从 sw 进入的输入端口为 inPort 的包转发到 outPort






##链路聚合算法

整体思路就是将所有目的 IP 相同的客户端 IP 加入一个组中, 然后对该组的所有 IP 进行 IP 提取子网掩码进行聚合.

###关键变量
   
    ArrayList<String> routes : 保存所有的聚合后的路由

###void aggr(String dpid,Map<String, OFFlowMod> mf,IStorageSourceService sss,HashMap<String, LBPool> pools)

    hm = HashMap<String, OFFlowMod>() :   (ip:port, OFFlowMod) 键值对, (vip:vport, fm) 可能存在覆盖问题
    tlist = ArrayList<String>() : ip:port 列表, 所有 pool 的 ip:port 列表, 不重复
    ips = HashMap<String, ArrayList<Integer>> : (pool 的 ip:port, 请求该 pool 的所有源 ip)
    ops = HashMap<String, ArrayList<String>>() : (ip:port, 请求该 pool 的所有 action 列表) (可能覆盖,如果 port)
    tt =  ArrayList<Integer>() : 匹配的流表的所有源地址
    ttop = ArrayList<String>() : 匹配的流表的 action 不重复
    
    取出交换机 dpid 中所有 "outbound" 开头的流表,
    1. (poolIP:poolPort 列表), 所有的 poolIP:poolPort 列表
    2. (poolIP:poolPort, 所有流表修改对象) 存入 hm;(存在覆盖的bug?)
    3. (poolIP:poolPort, 目的地址是 poolIP:poolPort 的所有客户端 ip 列表) 存入 ips 中;
    4. (poolIP:poolPort, 目的地址是 poolIP:poolPort 的所有 action 列表) 存入 ops 中;

    遍历 poolIP:poolPort 列表所有元素
    1. 如果 poolIP:poolPort 在 pool 中, 以 ips.get(poolIP:poolPort) 调用 createBinTree() 创建二叉树, 
    遍历并进行 ip 聚合,返回聚合后的地址列表
    2. 如果聚合后与聚合前 ip 个数相同,说明没有聚合,否则认为聚合
    3. 如果聚合, 遍历聚合的所有 ip, 创建
       
问题:
1. 协议默认为 TCP, 显然是不合适的, 由的端口是 tcp 有的是 udp 协议
2. 流表 action 没有顺序, action 一定会存在问题, 因为 ip1 转向 port1, ip2 转向 port2 现在 ip1, ip2 聚合后, 
结果只有第一个 action 起作用, ip1 的转发到 port2 完全有可能.
3. 有的 action 只有 output, 所以 nw_dst tp_dst, dl_dst 完全有可能是 null

###Node insert(Node node, String str, int level)

    将 str 从第 level 个字符开始 构建为一颗二叉树, 返回树的根节点

    如果  str.charAt(level) 是 0, 调用 insert(node.leftChild, str,level)
    如果  str.charAt(level) 是 1, 调用 insert(node.rightChild, str,level)
    当 node 的左右节点都不为 null, 且 node 的左右值都为 1 时,当前值为 1.
    返回根节点

###void preOrderTraverse(Node node,String[] path,String value,int level)

    前序遍历树, 将左子节点的 path[level] 为 0, 右子节点的path[level] 为 1;
    遇到 node.value 为 1 时 将 path 转为 ip 地址并加入 this.routes.

###String bintoip(String bin)

    将 IP 的二进制转为点分十进制

###ArrayList<String> createBinTree(ArrayList<Integer> iplist)

    将 iplist 中的 ip 构造为 