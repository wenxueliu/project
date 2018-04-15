  转发控制分离
  开放 API
  集中化管理


不是解决传统解决不了的问题,而是更快,更好得完成
不是让控制器做一切,而是让控制器控制用户想控制的部分

组网方式

* VLAN
* Tunnel

##openstack

* DVR (distribute Virtual Route)成熟
* 数据校验不严谨
* FwaaSS VPNaaSS Security Group 支持有限
* DVR agent 与 L3 agent　　通过　namespace 低效

##虚拟三层路由转发

* 集中式虚拟网关
 OpenStack Juno 之前

* 分布式虚拟网关
	OpenStack Juno
	NSX Contrail Centec

* 半分布式虚拟网关
	CloudStack

分布式只管东西三层, 南北向还是需要集中网关


##OVN (open Virtual Network)

##Arp Proxy Dhcp Proxy Flow Learning

##vlan --> Tunnel

VTEP

##术语

NvGRE
VxLan
STT
Geneves

offload


VxLAN

OVN

zookeeper 网络拓扑
nosql 实时状态信息

offland 架构
VPC


##部署建议

* 交换机的 dpid 不能有相同的
* 控制器 id 非常重要

##模块阅读顺序建议

* 阅读的是 LinkDiscovery 模块
* 阅读 Topology 模块(仅仅依赖 LinkDiscovery).
* 阅读 devicemanager 模块
* 阅读 routing 模块

##基本网元

###NodePortTuple

    DatapathId nodeId; // switch DPID
    OFPort portId; // switch port id

    网络中有两种, 一种是属于交换机之间的连接, 被成为 inter 连接, 一种被成为
    AttachmentPoint 即与主机或非 OF 交换机连接.
###Link

    DatapathId src;
    OFPort srcPort;
    DatapathId dst;
    OFPort dstPort;
    U64 latency; /* we intentionally exclude the latency from hashcode and equals */

###LinkInfo

	Date firstSeenTime;
	Date lastLldpReceivedTime; /* Standard LLDP received time */
	Date lastBddpReceivedTime; /* Modified LLDP received time  */
	U64 currentLatency;
	ArrayDeque<U64> latencyHistory;
	int latencyHistoryWindow;
	double latencyUpdateThreshold;

###ignoreMACSet

源 MAC 是该列表中的 MAC 地址, 丢弃

###TunnelPort

###AutoPortFastFeature

###QuarantinedPorts

    从该列表中收到的包之间丢弃, 但 LLDP 和 BDDP 除外.

###SuppressPort

    不发送 LLDP 和 BDDP 消息的交换机端口

###LLDP 协议

https://en.wikipedia.org/wiki/Link_Layer_Discovery_Protocol

注：

一个 NodePortTuple 可以对应多个 Link

一个 Link 对应一个 LinkInfo

##SwitchPort

    交换机:端口映射类

    DatapathId switchDPID  : 交换机 ID
    OFPort port            : 交换端口
    ErrorStatus errorStatus: 错误状态

##AttachmentPoint

    这里最直观的理解就是交换机与其上一个端口组成一个挂载点.
    一个设备可以有多个端口,因此有多个挂载点.

    DatapathId   sw
    OFPort       port
    Date         activeSince
    Date         lastSeen

##Entity

    网络中的实体, 实体依赖 AttachmentPoint. 每个 AttachmentPoint 可以包含多个 Entity.
    比如一个 AttachmentPoint (交换机的某一个端口)可能有多个主机的数据包通过, 那么一个
    Entity 就记录了 AttachmentPoint 经过的一个主机.

    MacAddress     macAddress
    IPv4Address    ipv4Address
    VlanVid        vlan
    DatapathId     switchDPID  : 所属交换机的 DPID
    OFPort         switchPort  : 所属交换机的端口
    Date           lastSeenTimestamp : 实体在网络中上次观察到的时间
    Date           activeSince       : 实体创建时间
    int ACTIVITY_TIMEOUT = 30000  ms : 激活的超时时间
    lastSeenTimestamp - activeSince > ACTIVITY_TIMEOUT 之后, activeSince 才可变 lastSeenTimestamp

    只有 lastSeenTimestamp 是可变的, 其他一旦创建便不可变

####网络链路建立过程:

每当控制器新增一个端口, 就发送 LLDP 探测包. 并将其加入 quarantineQueue
每当控制器删除一个端口, 就将 PORT_DOWN 的消息发送给所有订阅 linkDiscovery 的模块.
每当新的交换机激活, 遍历交换机所有可用端口, 发送 LLDP 探测包. 并将其加入 quarantineQueue

* 接受交换机的的单播包(LLDP)或多播包(BSN):

    1. 发送该包的端口已经配置为不发送 LLDP 的端口, 丢弃
    2. 发送该包的交换机的端口已经宕掉, 丢弃
    3. 发送该包的端口是交换机的 LOCAL 端口, 丢弃
    4. 该包是 LLDP 单播包但不是当前控制器发送的, 丢弃
    5. 该包是 LLDP 广播包但 id 大于当前控制器 id, 转发, 否则丢弃
    6. 该包不包含发送源交换机 dpid, 丢弃
    7. 该包源交换机的端口已经宕掉, 丢弃
    8. PACKET_IN 该包的交换机的端口已经宕掉, 丢弃
    9. 根据<发送该包的交换机, 发送该包交换机的端口, 接受该包的交换机,
        接受该包的交换机的端口> 建立一个生成 Link, LinkInfo 信息, 更新已有 Link 信息
    10. 如果接受到的是 LLDP 单播包, 新建 Link 的反向 Link 不存在, 发送 LLDP 广播(BDDP)探测包.
    11. 如果接受到的是 LLDP 广播包, 直接增加一个反向 Link

* 过滤(丢弃)一些端口和源 MAC 的包.
* 收到目标 MAC 为 0x0180c2000000 的包, 丢弃
* 收到网卡类型小于 17 的包, 丢弃.
* 收到其他类型的包, 等待其他模块处理

####网络链路维护:

控制器每隔 DISCOVERY_TASK_INTERVAL(1) 秒检查当前已知的每一个 Link, 该 Link 在过去
35 秒是否收到 LLDP和 BDDP 消息.

如果收到 LDDP 消息, 也收到 BDDP 消息, 什么也不做.
如果收到 LDDP 消息, 没有收到 BDDP 消息, 什么也不做.
如果没有收到 LDDP 消息, 但收到了 BDDP 消息, 发送链路更新事件加入更新事件列表等待处理.
如果没有收到 LDDP 消息, 也没有收到 BDDP 消息, 将链路删除事件加入更新事件列表等待处理.

控制每隔 15 秒遍历所有交换机的所有端口, 给每一个可用端口发送 LLDP 链路发现探测消息.

综合以上两点, 在一个正常的网络下, 交换机每个端口如果是正常的话, 每隔 15 s 应该能收
到对端发送的 LLDP 消息. 如果没有收到 LLDP 收到 BDDP 消息说明链路更新, 如果既没有收到
LLDP 也没有收到 BDDP 说明链路断开了.

此外, 一个单独的线程会将每个 Link 发生改变的消息发送给每个监听链路更新的订阅者, 订阅者
可以根据自己的需要对不同的事件进行不同的处理.

####网络拓扑建立过程

1. 根据 DFS 算法将整个拓扑划分为多个 Cluster
2. 更加 dijkstra 算法建立每个节点及其他节点到该节点的广播树.  根据广播数提供路由.

####网络拓扑维护过程

订阅 switch, Link 及 port 的更新事件, 及时调整拓扑
