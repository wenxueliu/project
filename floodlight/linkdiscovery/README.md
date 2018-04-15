##链路建立过程

首先 controller 会定期要求交换对所有端口发送 LLDP 包, 以两台交换机为例, 这样如果两台交换机的某些端口直连, 
Controller 就能从两个交换机分别收到对方的 LLDP 包, 这样就能知道这两台交换机的哪些端口是直连的. 对于没有直连
的端口, 由于一方收不到另一方发送的 LLDP 包, 这样就需要发送 BDDP 包. BDDP 包可以跨交换机. 由于两个设备的链接
信息包含了是直连还是间接连, 我们就可以知道所有的连接信息. 也就能知道两台 openflow 交换机的拓扑

##模块概述

* 模块启动的时候, 订阅数据库表表名为　controller_topologyconfig 和　controller_switchconfig　的表的修改和删除消息．
* 模块启动的时候, 订阅交换机　PACKET_IN 消息
* 模块启动的时候, 订阅控制器角色转换消息
* 模块启动的时候, 订阅交换机改变消息, 将交换机的改变增加到更新事件列表中, 然后将本模块的事件更新通知给其他模块(订阅该模块消息的模块)

模块一旦启动,

* 启动一个新的线程运行链路更新(1s)和链路发现任务(15s).
* 启动一个新的线程运行 bddp 任务(间隔 100ms)
* 启动一个新的线程运行发布链路更新消息线程

之后, 订阅 switch 的 PACKET_IN 事件, 解析 LLDP 和 BDDP 包,

对于 LLDP 包或 BDDP 包

如果当前交换机收到由当前 controller 从其他交换机发送的, 说明通过 remoteSwitch 的 remotePort 能够到达
 currentSwitch 的 currentPort, 那么这是一条合法的连接, 如果已经存在该连接, 那么,当前连接是否更新了, 如果没有更新,
更新之. 如果不存在, 创建一条连接. 将该连接保持起来, 并写入数据库. 之后检查该链路的反向链接是否存在, 如果是 LLDP 包,
且反向链接不存在, isReverse = false, 且当前链接没有过期, 那么就发送反向链接的 LLDP 包; 如果是 BDDP 包, 直接创
建反向链接

对于非 LLDP 或 BDDP 包,

检查 DstMAC, 如果是 0x0180c2000000L , 阻止该包被后续处理;
检查 srcMAC, 如果在 ignoreMACSet 中, 阻止该包被后续处理;
检查 sw,port,如果在 quarantineQueue 中, 阻止该包处理

否则该包继续被后续订阅者处理

###对外支持的功能

* 获取端口的流信息(当前端口转发多少条流经过)
* 获取具体流的统计信息()
* 忽略指定源 MAC 的包
* (增加, 删除或获取)禁止指定端口转发 LLDP, BDDP 包
* 增加隔离端口
* AutoPortFeature 特性(默认不支持)
* 获取连接类型
* 是否是 Tunnel 端口

###支持的配置选项

event-history-size : 默认 1024
latency-history-size : 默认 10
latency-update-threshold :默认 0.5

###数据存储

创建表结构

* TOPOLOGY_TABLE_NAME
* LINK_TABLE_NAME

监听表结构

* SWITCH_CONFIG_TABLE_NAME
* TOPOLOGY_TABLE_NAME

###运行的服务

* 链路发现任务 discoveryTask
* Bddp 任务

###监听的消息

* PACKET_IN
* PORT_STATUS
* 交换机更新
* HA 切换


##ILinkDiscovery.java

    记录基本数据结构

###DatapathId 用于标记一个设备, 如交换机

    long rawValue

###OFPort

    端口号, 在 1.0 版本为 short, 1.1 版本之后为 int

###SwitchType

    BASIC_SWITCH, CORE_SWITCH 

###UpdateOperation

    LINK_UPDATED("Link Updated")
    LINK_REMOVED("Link Removed")
    SWITCH_UPDATED("Switch Updated")
    SWITCH_REMOVED("Switch Removed")
    PORT_UP("Port Up")
    PORT_DOWN("Port Down")
    TUNNEL_PORT_ADDED("Tunnel Port Added")
    TUNNEL_PORT_REMOVED("Tunnel Port Removed")    

###LinkType

    INVALID_LINK("invalid")    
    DIRECT_LINK("internal")
    MULTIHOP_LINK("external")
    TUNNEL("tunnel")

###LinkDirection

    UNIDIRECTIONAL("unidirectional")
    BIDIRECTIONAL("bidirectional")

###LDUpdate

变量

    DatapathId src
    OFPort srcPort
    DatapathId dst
    OFPort dstPort
    SwitchType srcType
    LinkType type
    UpdateOperation operation

#Linkinfo.java

##Linkinfo

    记录连接信息

###关键变量

    Date firstSeenTime
    Date lastLldpReceivedTime  //Standard LLLDP received time
    Date lastBddpReceivedTime  //Modified LLDP received time

###LinkType getLinkType()

    如果 lastLldpReceivedTime 不为 null(通过 LLDP 建立的 Link), 为 直连(LinkType.DIRECT_LINK); 
    如果 lastBddpReceivedTime 不为空(通过 BDDP 建立的 Link), 多跳连接; 
    否则为无效连接类型

###Date getUnicastValidTime()

    即 lastLldpReceivedTime

###Date getMulticastValidTime()

    即 lastBddpReceivedTime

#ILinkDiscoveryService.java

##Link

    DatapathId src  //src-switch
    OFPort srcPort  //src-port
    DatapathId dst  //dst-switch
    OFPort dstPort  //dst-port

##NodePortTuple

    DatapathId nodeId // switch DPID
    OFPort portId     // switch port id

##ILinkDiscoveryService

* boolean isTunnelPort(DatapathId sw, OFPort port)
* Map<Link, LinkInfo> getLinks()
* LinkInfo getLinkInfo(Link link)
* ILinkDiscovery.LinkType getLinkType(Link lt, LinkInfo info)
* generateLLDPMessage(DatapathId sw, OFPort port, boolean isStandard,boolean isReverse)
* Map<DatapathId, Set<Link>> getSwitchLinks()
* void addListener(ILinkDiscoveryListener listener)
* Set<NodePortTuple> getSuppressLLDPsInfo()
* void AddToSuppressLLDPs(DatapathId sw, OFPort port)
* void RemoveFromSuppressLLDPs(DatapathId sw, OFPort port)
* Set<OFPort> getQuarantinedPorts(DatapathId sw)
* boolean isAutoPortFastFeature()
* void setAutoPortFastFeature(boolean autoPortFastFeature)
* Map<NodePortTuple, Set<Link>> getPortLinks()
* void addMACToIgnoreList(MacAddress mac, int ignoreBits)


#LinkDiscovery.java

##class LinkDiscoveryManager 

###关键变量

    Map<Link, LinkInfo> links;  维护两个交换机的连接信息，表明目前已经建立的连接
    Map<DatapathId, Set<Link>> switchLinks; 
    维护与每个交换机关联的 Link，可以通过DatapathId查到与之关联的正反两个方向的连接, 如 link (src,srcPort, dst, dstPort), 既保存了 switchLinks.get(src).get(link), 又保存switchLinks.get(dst).get(link) 

    Map<NodePortTuple, Set<Link>> portLinks; 
    维护 NodePortTuple(sw,port) 之关联的 Link，可以通过 NodePortTuple 查到与之关联的正反两个方向的连接. 如 link (src,srcPort, dst, dstPort), srcNt = NodePortTuple(src, srcPort), dstNt = NodePortTuple(dst, dstPort) 既保存了 portLinks.get(srcNt).get(link) 也保持了 portLinks.get(dstNt).get(link)


####LLDP 协议 BDDP协议
    
    byte[] LLDP_STANDARD_DST_MAC_STRING = HexString.fromHexString("01:80:c2:00:00:0e")
    long LINK_LOCAL_MASK = 0xfffffffffff0L;
    long LINK_LOCAL_VALUE = 0x0180c2000000L;
    int EVENT_HISTORY_SIZE = 1024;

    byte TLV_DIRECTION_TYPE = 0x73;
    short TLV_DIRECTION_LENGTH = 1;
    byte TLV_DIRECTION_VALUE_FORWARD[] = { 0x01 };
    byte TLV_DIRECTION_VALUE_REVERSE[] = { 0x02 };

    LLDPTLV forwardTLV = new LLDPTLV().setType(TLV_DIRECTION_TYPE)
                                .setLength(TLV_DIRECTION_LENGTH)
                                .setValue(TLV_DIRECTION_VALUE_FORWARD);

    LLDPTLV reverseTLV = new LLDPTLV().setType(TLV_DIRECTION_TYPE)
                                .setLength(TLV_DIRECTION_LENGTH)
                                .setValue(TLV_DIRECTION_VALUE_REVERSE);

    LLDPTLV controllerTLV = new LLDPTLV().setType((byte) 0x0c)
            .setLength((short) controllerTLVValue.length)
            .setValue(controllerTLVValue);

    lldpTimeCount = 0;  //无用
    
    isStandard ： True - LLDP包   False - BDDP 包
    isReverse  ： True - 不产生反向 Link 探测包  False - 产生反向 Link 包

    //链路发现
    SingletonTask discoveryTask;  
    DISCOVERY_TASK_INTERVAL = 1;

    LLDP_TO_ALL_INTERVAL = 15; //LLDP 发送频率 15s 一次
    long lldpClock = 0  //与 LLDP_TO_ALL_INTERVAL 配合使用

    LINK_TIMEOUT = 35  // 链路有效时间 35 s 这个时间一定要大于 LLDP_TO_ALL_INTERVAL, 否则, 导致 link 不断地在更新
    int LLDP_TO_KNOWN_INTERVAL = 20;  //LLDP 发送频率, 20s 一次, 但实际是 LLDP_TO_ALL_INTERVAL 来决定

    //链路更新
    ArrayList<ILinkDiscoveryListener> linkDiscoveryAware; 保存所有的链路发现, 所有实现 ILinkDiscoveryListener的类, 可以通过调用 linkDiscoveryUpdate 处理更新操作

    BlockingQueue<LDUpdate> updates; 保存所有的 LDUpdate 更新事件
    Thread updatesThread : 链路更新线程

####BDDP
    
    String LLDP_BSN_DST_MAC_STRING = "ff:ff:ff:ff:ff:ff";
    SingletonTask bddpTask;  //bddp 任务线程
    final int BDDP_TASK_INTERVAL = 100 //BDDP 任务间隔    
    final int BDDP_TASK_SIZE = 10  // 每次 BDDP 任务执行的粒度, 即每次认为更新 quarantineQueue 和 maintenanceQueue 中元素个数

####配置选项
    
    boolean AUTOPORTFAST_DEFAULT = false;  //
    boolean autoPortFastFeature = AUTOPORTFAST_DEFAULT;

    volatile boolean shuttingDown = false;

####其他模块相关

    HARole role  //角色管理, HARole.ACTIVE 
    IHAListener haListener;  
    protected IEventCategory<DirectLinkEvent> eventCategory; //事件分类服务
    IShutdownService shutdownService;  //服务关闭管理服务
    IDebugEventService debugEventService; // 事件调试服务
    IDebugCounterService debugCounterService; //统计计数服务
    IRestApiService restApiService;  //RestAPI 服务
    IThreadPoolService threadPoolService; //线程池服务
    IStorageSourceService storageSourceService; //数据库服务
    IOFSwitchService switchService; //交换机服务
    IFloodlightProviderService floodlightProviderService; 

####MACRange

    MacAddress baseMAC
    int ignoreBits    

####访问控制相关

    ReentrantReadWriteLock lock //并发可重入锁
    Set<NodePortTuple> suppressLinkDiscovery; 屏蔽(不发送也不接受) LLDP 和 BDDP 的包的(通过交换机:端口标记)

    LinkedBlockingQueue<NodePortTuple> quarantineQueue; 只允许 LLDP 和 BDDP 的设备(通过交换机:端口标记)
    每次交换机端口交换机有新的端口增加或者新的交换增加, 就增加对应的设备(sw:port标记)到 quarantineQueue 中.
    在 bddpTask 中, 每隔 BDDP_TASK_INTERVAL(100ms),  从中取出 BDDP_TASK_SIZE(10) 个, 调用 generateSwitchPortStatusUpdate 更新之

    这里真正的意思是表达了当前的 NodePortTuple 还不能用, 因为没有对应的 Link 存在.(该队列保存了新增加的,但还没有通知给控制器订阅者的NodePortTuple)

    LinkedBlockingQueue<NodePortTuple> maintenanceQueue:
    在链路发现线程中, 发送一次 LLDP 包的 NodePortTuple(sw,port) 都会将其增加到该队列, 在 bddpTask 线程中,
    每隔 BDDP_TASK_INTERVAL(100ms),  从中取出 BDDP_TASK_SIZE(10) 个, 调用 generateSwitchPortStatusUpdate 更新之

    这里真正要表达的意思这些NodePortTuple 的 LLDP 探测包已经发送出去了.  但还没有被 BDDP 任务更新.

    LinkedBlockingQueue<NodePortTuple> toRemoveFromQuarantineQueue; 所有已经建立链接的 NodePortTuple
    LinkedBlockingQueue<NodePortTuple> toRemoveFromMaintenanceQueue; 所有已经建立链接的 NodePortTuple

    Set<MACRange> ignoreMACSet: 忽略的 Mac 地址, 即凡是 mac 在 ignoreMACSet 中的主机, 直接Drop

####调试相关

    IDebugCounter ctrQuarantineDrops //
    IDebugCounter ctrIgnoreSrcMacDrops //
    IDebugCounter ctrIncoming  //
    IDebugCounter ctrLinkLocalDrops //
    IDebugCounter ctrLldpEol //

##链路更新线程与发现 

discoveryTask 线程, 每隔 DISCOVERY_TASK_INTERVAL(1) 秒执行一次 timeoutLinks() 链路更新, 
判断 link 的过期时间, 如果都过期, 则删除 link, 如果有一个过期, 则更新 link; 每隔 
LLDP_TO_ALL_INTERVAL(15) 秒调用 discoverOnAllPorts 执行一次全部端口的链路发现

###void discoverLinks() 
    
每调用一次执行 timeoutLinks(); 每调用 LLDP_TO_ALL_INTERVAL 次, 执行一次 discoverOnAllPorts().

###void timeoutLinks()  //每隔 DISCOVERY_TASK_INTERVAL(1) 秒执行一次

遍历 this.links 的所有 link， 检查 link 是否 timeout, 
如果 LLDP 包过期(指定时间内没有更新 LinkInfo 的 lastLldpReceivedTime), 就设置 UnicastValidTime(lastLldpReceivedTime) 为 null
如果 BDDP 包过期(指定时间内没有更新 LinkInfo 的 lastBddpReceivedTime), 就设置 MulticastValidTime(lastBddpReceivedTime) 为 null,
如没有过期, 什么也不做

如果 LLDP 和 BDDP 都过期, 就删除该 Link(实际为将链路删除实际增加到 updates 中等待被处理).
如果 只是 LLDP 过期就由单播(lldp)转为多播(bddp), 实际为将链路更新事件加入 updates 中等待被处理

如果由 Link 被删除, 调用 deleteLinks

###void deleteLinks(List<Link> links, String reason,List<LDUpdate> updateList)

1. 如果 links 中的元素存在于 switchLinks, portLinks, links 中, 从中删除对应的元素
2. 对于 links 中的元素以 LINK_REMOVED 事件增加到 updates 中, 等待被更新
3. 调用 removeLinkFromStorage(lt) 从 storageSourceService 中删除 links 中的元素

###void discoverOnAllPorts()  //每隔 DISCOVERY_TASK_INTERVAL(1) * 15 秒执行一次

遍历所有交换机, 对每个交换机的 enable 端口， 如果 (sw，port) 不在 suppressLinkDiscovery 中，
调用 sendDiscoveryMessage(sw, port, true, false) 发送 LLDP 消息。并增加 (sw, port) 到 maintenanceQueue

问题: 这里 suppressLinkDiscovery 的检查是不必要的, 因为 sendDiscoveryMessage 也做了检查

###void sendDiscoveryMessage(DatapathId sw, OFPort port,boolean isStandard, boolean isReverse)

向 sw 的 port 发送 LLDP 消息
* 调用 isOutgoingDiscoveryAllowed() 检查 sw, of 是否是发送输出消息的合法端口
* 调用 generateLLDPMessage(sw, port, isStandard, isReverse) 生成 LLDP 包
* action 为 OUTPUT

###boolean isOutgoingDiscoveryAllowed(DatapathId sw, OFPort port,boolean isStandard,boolean isReverse)

参数校验, 确保 sw, port 存在且不为 null, 而且是否允许向外发送链路发现的节点 (sw,port)

* 调用 isLinkDiscoverySuppressed(sw,of) 检查是否是 在 suppressLinkDiscovery中, 如果存在, 显然返回 false.
* 检查 DatapathId sw 是否存在于 switchService.getSwitch(sw) 如果不存在, 显然返回 false
* 检查 port 是否是 OFPort.LOCAL , 如果是, 显然返回 false.
* 检查 port 是否存在与 sw 中, 如果不存在, 显然返回 false

###OFPacketOut generateLLDPMessage(DatapathId sw, OFPort port,boolean isStandard, boolean isReverse)

发送 PACKET_OUT 消息到交换机, 使其发送 LLDP(isStandard = true) 包或 BDDP(isStandard = false) 包到 port 端口.

其中 LLDP 是单播, 而 BDDP 是广播

LLDP协议可以参考[LLDP 协议]()

####构造的 lldp 包

lddp 包含 3 个必选的 TLV  chassisId portId ttlValue, 分别存取了发送端的 mac 地址, 端口号, 存活时间 ;
2 个OptionalTVL:

    dpidTLVValue  openflow OUI 00-26-E1
    controllerTLV 当前控制器 TLV, 由当前的时间, iface 的 hashCode 以及 prime 值, 用于标记不同的 Controller，但是这不能确保唯一性，如果两个 Controller 上的时间不一致，可能会存在问题．
    reverseTLV 保留 TLV  T:73 L:1 V:02  // isReverse == true
    forwardTLV 转发 TLV  T:73 L:1 V:01  // isReverse == false

```java

    byte[] chassisId = new byte[] { 4, 0, 0, 0, 0, 0, 0 } // chassisId 后 6 bytes 是交换机 DataPathId 的后面 6 个 bytes
    byte[] portId = new byte[] { 2, 0, 0 }   // portId 后 2 byte 是端口号
    byte[] ttlValue = new byte[] { 0, 0x78 } // TTL 值 120 s
    //OpenFlow OUI - 00-26-E1-00
    byte[] dpidTLVValue = new byte[] { 0x0, 0x26, (byte) 0xe1, 0, 0, 0,
        0, 0, 0, 0, 0, 0 }  // 4-8 byte 是 dpid 前 4 个byte
    LLDPTLV dpidTLV = new LLDPTLV().setType((byte) 127)
                        .setLength((short) dpidTLVValue.length)
                        .setValue(dpidTLVValue);

    LLDPTLV reverseTLV = new LLDPTLV().setType(0x73)
                        .setLength(1)
                        .setValue(0x02);
    LLDPTLV forwardTLV = new LLDPTLV().setType(0x73)
                        .setLength(1)
                        .setValue(0x01);

    lldp.setChassisId(new LLDPTLV().setType((byte) 1)
                        .setLength((short) chassisId.length)
                        .setValue(chassisId));
    lldp.setPortId(new LLDPTLV().setType((byte) 2)
                        .setLength((short) portId.length)
                        .setValue(portId));
    lldp.setTtl(new LLDPTLV().setType((byte) 3)
                        .setLength((short) ttlValue.length)
                        .setValue(ttlValue));
    lldp.getOptionalTLVList().add(dpidTLV);

    controllerTLVValue = bb.get((System.nanoTime() * 7867
                        + ifaces.hashCode()) & (0x0fffffffffffffffL)，0，8)
    // controller type 是 12 value 是随机数字,用于区别不同的 Controller
    controllerTLV = new LLDPTLV().setType((byte) 0x0c)
                        .setLength((short) controllerTLVValue.length)
                        .setValue(controllerTLVValue);
    lldp.getOptionalTLVList().add(controllerTLV);
    if (isReverse) {
        lldp.getOptionalTLVList().add(reverseTLV);
    } else {
        lldp.getOptionalTLVList().add(forwardTLV);
    }

```

* 构造 Ethernet frame

    if (isStandard) {
        String LLDP_STANDARD_DST_MAC_STRING = "01:80:c2:00:00:0e";
        ethernet = new Ethernet().setSourceMACAddress(ofpPort.getHwAddr())
                    .setDestinationMACAddress(LLDP_STANDARD_DST_MAC_STRING)
                    .setEtherType(Ethernet.TYPE_LLDP); //Ethernet.TYPE_LLDP
        ethernet.setPayload(lldp);
    } else {
        String LLDP_BSN_DST_MAC_STRING = "ff:ff:ff:ff:ff:ff";
        BSN bsn = new BSN(BSN.BSN_TYPE_BDDP);
        bsn.setPayload(lldp);
        ethernet = new Ethernet().setSourceMACAddress(ofpPort.getHwAddr())
                    .setDestinationMACAddress(LLDP_BSN_DST_MAC_STRING)
                    .setEtherType(Ethernet.TYPE_BSN);  //Ethernet.TYPE_BSN
        ethernet.setPayload(bsn);
    }

* PacketOut

```
    byte[] data = ethernet.serialize();
    OFPacketOut.Builder pob = switchService.getSwitch(sw).getOFFactory().buildPacketOut();
    pob.setBufferId(OFBufferId.NO_BUFFER);
    pob.setInPort(OFPort.ANY);
    pob.setData(data);
    pob.setAction(actions.add(sw.getOFFactory().actions().buildOutput().setPort(port)))
```

## BDDP 任务线程

每隔 BDDP_TASK_INTERVAL(100ms), 找到所有已经发送 LLDP 包的设备(sw:port), 如果该设备还没有建立过连接, 就发送
BDDP 包; 找到所有新增加的设备(sw:port), 如果该设备还没有建立连接, 就发送 BDDP 包; 之后,对本次遍历的设备, 进行更新.

这很好理解, 如果一个交换机有的端口没有直连另一个交换的端口, 当向该交换机端口发送 LLDP 包后, 能在 maintenanceQueue
中找到该设备, 但其端口显然不能收到 LLDP包, 也就不能在toRemoveFromMaintenanceQueue 中 找到该设备, 对于这样的端口
当然应该发送 BDDP包;

如果由新的交换机增加, 或交换机增加了一个端口, 但该设备的端口没有与另一个交换的端口直连, 虽然能在 quarantineQueue 中找到该
设备, 但是该设备收不到 LLDP 包, 也就不能在 toRemoveFromQuarantineQueue 中找到该设备, 对于这样的设备, 我们也应该发送
BDDP 包;

###void processBDDPLists()

每隔 BDDP_TASK_INTERVAL(100ms), 从 quarantineQueue 和 maintenanceQueue 中取出 BDDP_TASK_SIZE(10) 个,
如果不在对应的 toRemoveFromMaintenanceQueue 或 toRemoveFromQuarantineQueue 发送 BDDP 发现包, 之后调
用 generateSwitchPortStatusUpdate() 更新之

这里其实要表达的意思是 在 quarantineQueue 和 maintenanceQueue 中的端口, 如果还没有收到对应的应答. 就重新发送之.

从 quarantineQueue 取出的元素 ntp

    不在 toRemoveFromQuarantineQueue 中,调用 sendDiscoveryMessage( npt.getNodeId(), npt.getPortId(),false,false,) 发送 BDDP 消息, 将 ntp 加入 nptList
    否则直接将 ntp 加入 nptList

从 maintenanceQueue 取出的元素 ntp

    不在 toRemoveFromMaintenanceQueue 中, 调用 sendDiscoveryMessage(npt.getNodeId(), npt.getPortId(),false,false,) 发送 BDDP 消息, 将 ntp 加入 nptList
    否则直接将 ntp 加入 nptList

对于 nptList 的每个元素调用 generateSwitchPortStatusUpdate()

这里 toRemoveFromMaintenanceQueue 和 toRemoveFromQuarantineQueue 主要的作用是防止 LLDP 的重复发送. 因为每当既那里链路, 都会将 Link 加入 toRemoveFromMaintenanceQueue
和 toRemoveFromQuarantineQueue 中

###void generateSwitchPortStatusUpdate(DatapathId sw, OFPort port)

如果端口 port 不是 STP_BLOCK 的状态，增加到 LDUpdate(sw, port, PORT_UP) 到 updates 中; 否则 增加 LDUpdate(sw, port, PORT_DOWN) 到 updates 中


## 链路更新线程

###void doUpdatesThread()

updates 是阻塞队列(BlockingQueue), 所以直到 updates 不为 null 的时候, 该线程才开始运行, 将 updates
中的元素依次取出, 加入局部变量 updateList, linkDiscoveryAware 维护了所有监听 linkDiscovery 的类, 如果
linkDiscoveryAware 不为 null, 将 updateList 加入每个监听 linkDiscovery 消息的类. 这样每个监听的类,
可以选择如果处理这些更新事件.


##OFMessage Listener 消息订阅

###public Command receive(IOFSwitch sw, OFMessage msg,FloodlightContext cntx)

只处理 PACKET_IN 包，当收到 PACKET_IN 消息， 调用 handlePacketIn 函数。

###protected Command handlePacketIn(DatapathId sw, OFPacketIn pi,FloodlightContext cntx)

如果 payload 是 BSN 调用 handleLldp((LLDP) bsn.getPayload(), sw, inPort, false, cntx)
如果 payload 是 LLDP 类型，调用 handleLldp((LLDP) eth.getPayload(), sw, inPort, true, cntx)
如果 payload 长度小于 1500，且 destMac =  0x0180c2000000L , 停止对包的处理
如果 NodePortTuple(sw, inPort) 在 quarantineQueue 中, 停止对包的处理
如果 srcMac 在 ignoreMACSet 中， 停止对包的处理
否则，包继续被其他模块处理。

问题, 参数没有校验

###boolean ignorePacketInFromSource(MacAddress srcMAC)

检查 srcMAC 是否在 MAC 忽略列表里面

###Command handleLldp(LLDP lldp, DatapathId sw, OFPort inPort, boolean isStandard, FloodlightContext cntx)

解析 LLDP 或 BDDP 包包,

如果收到的包不是当前控制器发送的

* 如果 isStandard　== true, 那么, 说明是LLDP 包, 该包停止处理
* 如果 myId < otherID, 那么包是 BDDP 包, 继续被处理．//这里myId < otherID 为什么?
* 否则该包停止处理

如果收到的包是当前控制器发送的

校验发送包信息
* 接收到 LLDP 包不是连接到当前 controller 的控制的交换机发送的，停止处理
* remoteSwitch 的 remotePort 已经 down 了， 停止处理
* 该 NodePortTuple 已经在 suppressLinkDiscovery 中， 停止处理
* PACKET_IN 的 sw 的 inPort 已经不 Enable, 停止处理

通过校验,说明远程交换机和 sw 是连通的, 创建两个交换机的 Link, 调用 addOrUpdateLinkklt, newLinkInfo) 增加或更新
Link.

检查 this.links 是否存在该 link, 如果存在, 且该包是 LLDP 包, isReverse == false, 检查反向链接是否存在, 如果
不存在, 且该链接没有过期, 发送 LLDP 包

如果是 BDDP 包, 直接创建反向链接, 调用 addOrUpdateLink(reverseLink, reverseInfo)更新之

最后将 NodePortTuple(srcDpid, srcPort) NodePortTuple(dstDpid, dstPort) 都加入 toRemoveFromMaintenanceQueue
和 toRemoveFromQuarantineQueue 中.

* 校验输入数据，必须满足以下全部条件

    sw 和　inPort 不能为 NULL；
    inPort 是 sw 的端口；
    inPort 不能为 OFPort.LOCAL
    NodePortTuple(sw, inPort) 不在 suppressLinkDiscovery 内;
    lldp.getPortId() 不为 null 并且 lldp.getPortId().length = 3;

* 解析包

    portID             srcPort
    getOptionalTLVList 中 Type = 127， length = 12， 0x 12 00 26 e1 00 得到 srcSwitch
    inPort             dstPort
    sw                 dstSwitch

对于 lldp.getOptionalTLVList 中 LLDPTLV

如果 Type = 127， length = 12， 0x 12 00 26 e1 00 表明是 openflow 交换机

如果 Type = 12， length = 8  检查是否是当前 controller 发出的 LLDP 或 BDDP 包. 

###void discover(NodePortTuple npt)

调用 discover(DatapathId sw, OFPort port)

###void discover(DatapathId sw, OFPort port)

调用 sendDiscoveryMessage(sw, port, true, false)

###boolean isLinkAllowed(DatapathId src, OFPort srcPort,DatapathId dst, OFPort dstPort)

直接返回 true

###boolean addLink(Link lt, LinkInfo newInfo)

检查 lt 是否存在 switchLink 和 portLink, 如果不存在,就增加之

###boolean updateLink(Link lt, LinkInfo oldInfo, LinkInfo newInfo)

1 oldInfo 既不是 LLDP 也不是 BDDP, newInfo 是 BDDP， 那么发生变化, 返回 true
2 oldInfo 是 BDDP 不是 LLDP， newInfo 是 LLDP， 那么发生变化，返回 true
3 oldInfo 是 LLDP(不关心是否是 BDDP)， newInfo 是 BDDP， 忽略该信息(不更新), 没有发生变化, 返回 false
4 如果 lt 的延迟与 oldInfo 的延迟不一样, 返回 true

如果 newInfo 不为空, 就更新 oldInfo 的 LLDP 和 BDDP 时间


###boolean addOrUpdateLink(Link lt, LinkInfo newInfo)

* 检查 lt 是否已经存在 links, 如果存在, 更新 linkInfo, 如果不存在, 直接增加之
* 如果之前不存在该 Link,调用 addLink(lt, newInfo) 将 lt 更新到 switchLink 和 portLink
* 如果之前存在该 Link, 调用 updateLink 检查是否 link 被更新.
* 将当前 Link 信息写入数据库 writeLinkToStorage
* 如果 Link 更新了,那么增加到 updates 中

###UpdateOperation getUpdateOperation(OFPortState srcPortState, OFPortState dstPortState)

如果 srcPortState, dstPortState 都不是 OFPortState.STP_BLOCK, 则说明是 LINK_UPDATED, 否则是 LINK_REMOVED

###UpdateOperation getUpdateOperation(OFPortState srcPortState)

如果 srcPortState 不是 OFPortState.STP_BLOCK, 则说明是  PORT_UP, 否则是 PORT_DOWN

##实现ILinkDiscoveryService 接口

这里的公共方法都缺少对入口参数的校验,尤其是 null, 此外如果支持多线程, 那么,也许某些接口, 缺少对 多线程的支持

###boolean isTunnelPort(DatapathId sw, OFPort port)

目前,不支持, 所以直接返回 false

###Map<Link, LinkInfo> getLinks()  //links 是 hashMap 

考虑的多线程的情况, 加了读锁(readLock), 返回的是 links 的拷贝

###LinkInfo getLinkInfo(Link link)

考虑的多线程的情况, 加了读锁(readLock), 返回的是 links.get(link) 的拷贝

问题, 此处是否需要 try finally 来包装

###ILinkDiscovery.LinkType getLinkType(Link lt, LinkInfo info)

* 如果 info.getUnicastValidTime() != null, 返回 ILinkDiscovery.LinkType.DIRECT_LINK
* 如果 info.getMulticastValidTime() != null, 返回 ILinkDiscovery.LinkType.MULTIHOP_LINK;
* 否则 返回 ILinkDiscovery.LinkType.INVALID_LINK

###Map<DatapathId, Set<Link>> getSwitchLinks()

return this.switchLinks

问题, switchLinks 是 HashMap() 此处是否需要加入 readLock 并通过 try finally 来包装

###void addListener(ILinkDiscoveryListener listener)

linkDiscoveryAware.add(listener) (ArrayList)

问题, 此处是否需要加入 readLock 并通过 try finally 来包装, 目前来说不必要, 原因是更新频率很低. 而且即使出现竞争也没关系.

###boolean isLinkDiscoverySuppressed(DatapathId sw, OFPort portNumber)

    是否 suppressLinkDiscovery 中

###Set<NodePortTuple> getSuppressLLDPsInfo()

return suppressLinkDiscovery

suppressLinkDiscovery是 Collections.synchronizedSet , 无需加 readLock

###void AddToSuppressLLDPs(DatapathId sw, OFPort port)

this.suppressLinkDiscovery.add(new NodePortTuple(sw, port))

deleteLinksOnPort(npt, "LLDP suppressed.")

###void deleteLinksOnPort(NodePortTuple npt, String reason)

遍历 portLinks 中与 npt 关联的 Link, 调用 deleteLinks 从 switchLinks, links, portLinks 及数据库中删除之, 并发布删除给订阅者

###void RemoveFromSuppressLLDPs(DatapathId sw, OFPort port)

this.suppressLinkDiscovery.remove(new NodePortTuple(sw, port));

discover(npt);  //调用 sendDiscoveryMessage(sw, port, true, false); 发送 LLDP 包

###Set<OFPort> getQuarantinedPorts(DatapathId sw)

得到 quarantineQueue 中 iter.getNodeId() == sw 的 portId Set 的复制

###boolean isAutoPortFastFeature()

return autoPortFastFeature(false) 

###void setAutoPortFastFeature(boolean autoPortFastFeature)

this.autoPortFastFeature = autoPortFastFeature;

###Map<NodePortTuple, Set<Link>> getPortLinks()

return portLinks

###void addMACToIgnoreList(MacAddress mac, int ignoreBits)

ignoreMACSet.add(MACRange(mac, ignoreBits))

##class HAListenerDelegate implements IHAListener

* 当发现 Controller 从 Standby 转换到 Active 的时候, 调用transitionToActive;
* 当发现 Controller 从 Active 转换到 Standby 的时候, 什么也不做
* 当发现 Controller IP 改变的时候, 什么也不做

###void transitionToActive()

* 设置 LinkDiscoveryManager 的 role 为 HARole.ACTIVE
* 从存储服务中删除所有的表 controller_link(记录所有Link 信息) 的所有记录
* 设置 LinkDiscoveryManager.autoPortFastFeature 的值
* 重新启动 link 发现的任务

###void controllerNodeIPsChanged(Map<String, String> curControllerNodeIPs,
            Map<String, String> addedControllerNodeIPs,
            Map<String, String> removedControllerNodeIPs)

什么也不做


###public void transitionToStandby()

什么也不做


###protected boolean addOrUpdateLink(Link lt, LinkInfo newInfo)

    LinkInfo oldInfo = links.put(lt, newInfo); //检查 (lt, newInfo) 是否在 links 中
    if oldInfo == NULL
        更新 时间戳
        增加 (lt,newInfo) 到 links 中
        LinkType linkType = getLinkType(lt, newInfo) 得到 LinkType
        if linkType == ILinkDiscovery.LinkType.DIRECT_LINK
            eventCategory.newEventNoFlush 发送通知
        notifier.postNotification()
    else
        linkChanged = updateLink(lt, oldInfo, newInfo); //检查 link 是否改变了
        if linkChanged
            if linkType == ILinkDiscovery.LinkType.DIRECT_LINK
                eventCategory.newEventNoFlush 发送通知
            notifier.postNotification()
    writeLinkToStorage(lt, newInfo)//写入存储

##实现 IOFSwitchListener

###void switchAdded(DatapathId switchId)

    什么也不做

###void switchRemoved(DatapathId switchId)

    如果 switchId 存在与 switchLinks 中, 调用 deleteLinks 更新该 switchId 中的所有 link(即从 portLink Links, switchLinks 删除之). 并将 SWITCH_REMOVED 增加到 updates 中
    否则, 直接增加到 updates 中.

###void switchActivated(DatapathId switchId)

    从 sw = switchService.getSwitch(switchId), 
    如果 sw 中存在 Enabled 端口, 遍历 Enable 端口, 发送 LLDP 包, 并将 SWITCH_UPDATED 增加到 updates 中.
    否则, 直接将 SWITCH_UPDATED 增加到 updates 中.

###void switchPortChanged(DatapathId switchId,OFPortDesc port,PortChangeType type)

    根据 type 调用相应的处理函数
    UP: 调用 processNewPort(switchId, port.getPortNo())
    DELETE, DOWN: handlePortDown(switchId, port.getPortNo())
    OTHER_UPDATE: case ADD: 什么也不做

###void processNewPort(DatapathId sw, OFPort p)

    如果 sw,p 在 this.suppressLinkDiscovery 中, 直接返回,
    否则 从 sw, p 发送 LLDP 包, 增加到 quarantineQueue
    (该队列保存了新增加的,但还没有通知给控制器订阅者的NodePortTuple)

###void handlePortDown(DatapathId switchId, OFPort portNumber)

    调用 deleteLinksOnPort(npt, "Port Status Changed") 更新所有 links, portLinks, swithLinks
    调用 LDUpdate(switchId, portNumber, PORT_DOWN) 将该更新操作增加到 this.updates 中, 
    注: 没有对多线程支持

###void switchChanged(DatapathId switchId)

    什么也不做


##实现 IStorageSourceListener

###void setStorageSource(IStorageSourceService storageSourceService)

    设置 this.storageSourceService 

###IStorageSourceService getStorageSource()

    获取 this.storageSourceService 

###void rowsModified(String tableName, Set<Object> rowKeys)

    此方法还没有实现 

###void rowsDeleted(String tableName, Set<Object> rowKeys)

    此方法还没有实现


##内部方法

###void readTopologyConfigFromStorage()

    通过查 storageSourceService 数据库的 TOPOLOGY_TABLE_NAME 表, 来决定 this.autoPortFastFeature 的值

    问题: 这样的实现没有问题么？

###void clearAllLinks()

从 storageSourceService 数据库中删除 LINK_TABLE_NAME 表

###void writeLinkToStorage(Link lt, LinkInfo linkInfo)

将 Link 信息写入数据库

问题: linkInfo 与 lt 无关,怎么办?

###void removeLinkFromStorage(Link lt)

从 storageSourceService 数据库中删除 id 与 lt 匹配的记录

###Long readLinkValidTime(Link lt)

从 storageSourceService 数据库中读取 id 与 lt 匹配的记录的有效时间

###String getLinkId(Link lt)

从 lt 中获取 id, 格式为 srcDpid-srcPort-dstDpid-dstPort

###问题

数据成员与数据库同步内容问题

多线程支持完备性

controllerTLV 的初始化在 lddp 链路发现协议线程的后面进行,可能导致 this.controllerTLV 没有来得及初始化.

processNewPort() 不应该增加事件到 updates 么？ 已经加

(myId < otherId) 判断的依据是什么，其他控制器的Value 就不能大于当前控制器的 Value


###Bug
        public LDUpdate(LDUpdate old) {
            this.src = old.src;
            this.srcPort = old.srcPort;
            this.dst = old.dst;
            this.dstPort = old.dstPort;
            this.srcType = old.srcType;
            this.type = old.type;
            this.operation = old.operation;
        }

应该为

        public LDUpdate(LDUpdate old) {
            this.src = old.getSrc();
            this.srcPort = old.getSrcPort();
            this.dst = old.getDst();
            this.dstPort = old.getDstPort();
            this.srcType = old.getSrcType;
            this.type = old.getType;
            this.operation = old.getPeration;
        }
