
该模块根据依赖 linkDiscovery 模块建立的已有交换机和交换机之间的的连接, 通过深度优先的算法和 Tarjan
算法计算出整个网络中的所有集群. 通过广度遍历算法, 计算中每一个集群中的每一个节点到其关联节点的距离和链路

一个集群(Cluster) 中包含很多交换机, 交换机和集群的映射关系存储在 switchClusterMap 中, 目前的实现中,
OpenflowDomain 和 L2DomainId 是一样的. 都代表一个集群, 但理论上应该是不同的, 但后续实际需要更改.
如果一个交换机不存在于 switchClusterMap 中, 它仍然可以代表一个 OpenflowDomain 或 L2Domain

一个交换机和它的一个端口,组成一个节点(sw,port), 一个节点可以和很多其他节点连接, 每一个节点与它关联的所有
Link 存储在 switchPortLinks 中, 如果一个节点不存在于 switchPortLinks 那么它就是 AttachmentPointPort,
如果存在于 switchPortLinks 中就是一个 InternalToOpenflowDomain.

如果一个节点不在任何集群中那么它就是 IncomingBroadcast

如果一个节点存在于某一集群 c, 且存在于 clusterBroadcastNodePorts.get(c) 中, 那么就是  IncomingBroadcast

###核心概念

* 集群: 交换机的集合, 从一个交换机可以到达集群之内的任何其他交换机
* 集群广播树: 对于某一个集群, 存储任一交换机到其他交换机的最短距离和链路
* NodePortTuple : 节点, 由交换机和它的一个端口组成, 即 sw,port
* Link : 链路, (srcSw,srcPort, dstSw, dstPort) 组成, 不同的节点通过链路连接起来

###订阅的模块

    IRoutingService
    ILinkDiscovery
    
###拓扑更新线程

模块订阅 linkDiscovery 模块中的链路更新,模块启动,即开始拓扑更新线程, 当没有订阅中更新事件时, 一直阻塞; 当
订阅有更新事件时, 线程运行,更新模块中对应的变量; 拓扑更新线程,每次运行完后,隔 0.5s 继续运行, 如果没有拓扑改变, 该线程一直阻塞

###计算路由

根据已有的拓扑,建立路由,具体实现参见 buildRoute 方法


##基本数据结构

##Cluster

    存储集群信息, 包括节点以及与节点关联的 link.

###关键变量

    DatapathId id : links 中最低的节点 id
    Map<DatapathId, Set<Link>> links : 一个节点和它关联的连接

* Cluster()
* DatapathId getId()
* void setId(DatapathId id)
* Map<DatapathId, Set<Link>> getLinks()

###Set<DatapathId> getNodes()

    得到所有的节点ID

###void add(DatapathId n)

    增加节点 n 到 links, 更新 id

###void addLink(Link l)

    将 l 相连的两个节点加入 links, 并将 l 加入两个节点

##NodePair

###关键变量

    long min
    long max

###NodePair(long a, long b)

    较小者给 min, 较大者给 max

###long getNode()

    返回　min

###long getOtherNode()

    返回　max

##NodePortTuple

###关键变量

    DatapathId nodeId : 交换机 ID
    OFPort portId : 交换机端口

* NodePortTuple(DatapathId nodeId, OFPort portId)
* DatapathId getNodeId()
* void setNodeId(DatapathId nodeId)
* OFPort getPortId()
* void setPortId(OFPort portId)

##OrderedNodePair

###关键变量

    long src
    long dst

* OrderedNodePair(long s, long d)
* long getSrc()
* long getDst()

##ClusterDFS

    标记一个交换机在集群中的信息, 如交换机是否被访问过, 交换机的深度, 交换机的母节点

###关键变量

    long dfsIndex
    long parentDFSIndex
    long lowpoint
    boolean visited

###ClusterDFS()

    visited = false                : 该交换机是否被访问过
    dfsIndex = Long.MAX_VALUE      : 该交换机的深度
    parentDFSIndex = Long.MAX_VALUE: 该交换机母节点的深度
    lowpoint = Long.MAX_VALUE      : 保存该交换机周围所有节点的最低 index 值, 用于判断遍历结束

* long getDfsIndex()
* void setDfsIndex(long dfsIndex)
* long getParentDFSIndex()
* void setParentDFSIndex(long parentDFSIndex)
* long getLowpoint()
* void setLowpoint(long lowpoint)
* boolean isVisited()
* void setVisited(boolean visited)


##接口

##ITopologyListener

    发布 topoplogy 更新消息接口

* void topologyChanged(List<LDUpdate> linkUpdates)


##ITopologyService

Cluster
island : 目前 island 和 cluster 一样的, 但是未来应该不一样
L2Domain : 
OpenflowDomain
BroadcastDomain
InternalToOpenflowDomain
AttachmentPointPort

###接口

* void addListener(ITopologyListener listener)
* Date getLastUpdateTime()

* boolean isAttachmentPointPort(DatapathId switchid, OFPort port)
* boolean isAttachmentPointPort(DatapathId switchid, OFPort port,boolean tunnelEnabled)

* //两个 switch 是否在相同的集群
* boolean inSameOpenflowDomain(DatapathId switch1, DatapathId switch2)
* boolean inSameOpenflowDomain(DatapathId switch1, DatapathId switch2,boolean tunnelEnabled)

* DatapathId getOpenflowDomainId(DatapathId switchId)
* DatapathId getOpenflowDomainId(DatapathId switchId, boolean tunnelEnabled)

* Set<DatapathId> getSwitchesInOpenflowDomain(DatapathId switchDPID)
* Set<DatapathId> getSwitchesInOpenflowDomain(DatapathId switchDPID,boolean tunnelEnabled)

* //两个 switch 是否在相同的 island
* boolean inSameL2Domain(DatapathId switch1, DatapathId switch2);
* boolean inSameL2Domain(DatapathId switch1, DatapathId switch2,boolean tunnelEnabled)

* //交换机在 L2DomainId 的代号
* DatapathId getL2DomainId(DatapathId switchId)
* DatapathId getL2DomainId(DatapathId switchId, boolean tunnelEnabled)

* boolean isBroadcastDomainPort(DatapathId sw, OFPort port)
* boolean isBroadcastDomainPort(DatapathId sw, OFPort port,boolean tunnelEnabled)

* boolean isAllowed(DatapathId sw, OFPort portId);
* boolean isAllowed(DatapathId sw, OFPort portId, boolean tunnelEnabled)

* //在新交换机的挂载点和原交换机的挂载点是否一致
* boolean isConsistent(DatapathId oldSw, OFPort oldPort,DatapathId newSw, OFPort newPort)
* boolean isConsistent(DatapathId oldSw, OFPort oldPort,DatapathId newSw, OFPort newPort, boolean tunnelEnabled)

* //两个交换机的端口是否在相同的广播域
* boolean isInSameBroadcastDomain(DatapathId s1, OFPort p1,DatapathId s2, OFPort p2)
* boolean isInSameBroadcastDomain(DatapathId s1, OFPort p1,DatapathId s2, OFPort p2, boolean tunnelEnabled)

* //获取交换机端口列表
* Set<OFPort> getPortsWithLinks(DatapathId sw)
* Set<OFPort> getPortsWithLinks(DatapathId sw, boolean tunnelEnabled)

* Set<OFPort> getBroadcastPorts(DatapathId targetSw, DatapathId src, OFPort srcPort)
* Set<OFPort> getBroadcastPorts(DatapathId targetSw, DatapathId src, OFPort srcPort, boolean tunnelEnabled)

* boolean isIncomingBroadcastAllowed(DatapathId sw, OFPort portId)
* boolean isIncomingBroadcastAllowed(DatapathId sw, OFPort portId, boolean tunnelEnabled)

* NodePortTuple getOutgoingSwitchPort(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort)
* NodePortTuple getOutgoingSwitchPort(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort, boolean tunnelEnabled)

* NodePortTuple getIncomingSwitchPort(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort)
* NodePortTuple getIncomingSwitchPort(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort, boolean tunnelEnabled)

* NodePortTuple getAllowedOutgoingBroadcastPort(DatapathId src,OFPort srcPort,DatapathId dst,OFPort dstPort)
* NodePortTuple getAllowedOutgoingBroadcastPort(DatapathId src,OFPort srcPort,DatapathId dst,OFPort dstPort, boolean tunnelEnabled)

* NodePortTuple getAllowedIncomingBroadcastPort(DatapathId src,OFPort srcPort)
* NodePortTuple getAllowedIncomingBroadcastPort(DatapathId src,OFPort srcPort, boolean tunnelEnabled)

* Set<NodePortTuple> getBroadcastDomainPorts()
* Set<NodePortTuple> getTunnelPorts()
* Set<NodePortTuple> getBlockedPorts()

* //所有　enable 的端口, 不包括隔离端口
* Set<OFPort> getPorts(DatapathId sw)


##NodeDist

###关键变量

    DatapathId node
    int dist

###NodeDist(DatapathId node, int dist)

    this.node = node
    this.dist = dist

###TopologyInstance getOuterType()

    TopologyInstance.this

* DatapathId getNode()
* int getDist()



##PathCacheLoader

    路径缓存加载器

###关键变量

    TopologyInstance ti

###PathCacheLoader(TopologyInstance ti)

    this.ti = ti

###Route load(RouteId rid)

    调用  ti.buildroute(rid)


##TopologyInstance

    实现了 ITopologyService 接口, 通过 identifyOpenflowDomains() 建立集群(Cluster), 初始化每个集群(Cluster)中 链路(links) 的key; 通过 addLinksToOpenflowDomains() 将所有链路(link)加入集群(Cluster)

    问题: 存在很多空指针异常

##关键变量与数据结构 

    short LT_SH_LINK = 1
    short LT_BD_LINK = 2
    short LT_TUNNEL  = 3

    int MAX_LINK_WEIGHT = 10000
    int MAX_PATH_WEIGHT = Integer.MAX_VALUE - MAX_LINK_WEIGHT - 1
    int PATH_CACHE_SIZE = 1000

    Set<DatapathId> switches : 全部交换机列表, 与 switchPorts 存储一致. 完全依赖构造函数来初始化
    Map<DatapathId, Set<OFPort>> switchPorts      :  交换机端口列表即 (switchID : portList), 完全依赖构造函数来获取数据
    Set<NodePortTuple> blockedPorts               :  被阻塞的交换机端口列表即 (switchID,port), 完全依赖构造函数来获取数据
    Map<NodePortTuple, Set<Link>> switchPortLinks :  交换机每个端口关联的 Link 列表 即 ((switchID, Port), Link), 完全依赖构造函数来获取数据

    Set<Link> blockedLinks: 阻塞的 Link 列表, 目前没有任何实际用处,因为一直没有元素
    Set<NodePortTuple> broadcastDomainPorts       :  广播域的交换机端口列表, 当 NodePortTuple 包含多余两个 Link 就加入,
    Set<NodePortTuple> tunnelPorts                :  里面的权重比一般的交换机端口权重大,完全依赖构造函数来获取数据, tunnelPorts 里面的节点, 与其关联的链路 dist 都较大
    Set<Cluster> clusters                         :  集群列表, 当前拓扑中的强连通分量, 在 dfsTraverse 中获取数据
    Map<DatapathId, Cluster> switchClusterMap     :  交接机对应的集群, 强连通分量组成的交换机, 在 dfsTraverse 中获取数据
                                                     问题: 这里 switchClusterMap 貌似存在问题. 比如 s1,s2,s3 组成一个强连通集群. 而 switchClusterMap 保存的是 s1:s1, s2:s1,s2, s3:s1,s2,s3

    //目前如下三个变量存储相同的数据, 其中 destinationRootedTrees, clusterBroadcastTrees 完全相同, clusterBroadcastNodePorts中的 NodePortTuple 是 BroadcastTree 中所有的链路的节点
    Map<DatapathId, BroadcastTree> destinationRootedTrees         : 交换机 ID 和 广播树, 在 calculateShortestPathTreeInClusters() 获取数据, (交换机,与其关联所有交换机的最短距离和链路), 对路由的建立起至关重要的地位

    注: clusterBroadcastTrees 与 destinationRootedTrees 区别在于前者只记录集群中 id 最小的 switch 的广播树, 而后者记录所有 switch 的广播树.

    Map<DatapathId, Set<NodePortTuple>> clusterBroadcastNodePorts : 集群和它里面的所有节点, 在 calculateBroadcastNodePortsInClusters() 中获取数据
    Map<DatapathId, BroadcastTree> clusterBroadcastTrees          : 集群中 dpid 最小的 switch 和它里面的广播树, 在 calculateBroadcastTreeInClusters() 中获取数据
    PathCacheLoader pathCacheLoader : 路径缓存, 与 pathcache 关联, 如 Route = pathCacheLoader.loader(RouteId)
    LoadingCache<RouteId, Route> pathcache :

    protected Map<DatapathId, BroadcastTree> destinationRootedFullTrees : 保持全局的交换机和广播树映射关系.
    protected BroadcastTree finiteBroadcastTree : destinationRootedTrees 随机一个节点.

    protected Set<NodePortTuple> broadcastNodePorts : 保存了整个拓扑其中一个广播域的所有 NodePortTuple.
	protected Map<DatapathId, Set<OFPort>> allPorts : 保持所有的 switchId 和 OFPort 的映射关系
    protected Map<DatapathId, Set<OFPort>> broadcastPortMap : switch 和 OFPort 的映射关系, 包含交换机和主机直连的 NodePortTuple 和全局拓扑其中广播域的 NodePortTuple

    //DatepathId : String 例如 00:00:00:00:00:01
    //NodePortTuple : (nodeId,port)
    //Cluster : (DatapathId id, HashMap<DatapathId, Set<Link>> links)  : id，强连通分量组成的交换机，links  
    //BroadcastTree: (HashMap<DatapathId, Link> links,HashMap<DatapathId, Integer> costs)
    //Link: (src,srcPort, dst, dstPort),cost
    //NodeDist: (DatapathId node,int dist)
    //ClusterDFS : (long dfsIndex,long parentDFSIndex,long lowpoint,boolean visited)

###void compute()

* identifyOpenflowDomains()
* addLinksToOpenflowDomains()
* calculateShortestPathTreeInClusters()
* calculateBroadcastNodePortsInClusters()
* printTopology()

###void addLinksToOpenflowDomains()

    该函数主要初始化 Cluster 中所有的强连通链路(links), 至此, 每个 Cluster 中的 links 包含了该集群中的所有 Link

    遍历所有的 sw 所有 port 的所有 links, 如果 link 的 src 与 dst 是在同一个 Cluster 中， 将 sw，link 增加到 Cluster.

    这里存在一个问题: Cluster 中的 links, 每个 DatapathId 对应的 link 是正反两个 link. 比如 s1p1 <-> s2p1. 那么 links
    中 s1 对应 (s1p1,s2p1) 和 (s2p1,s1p1) 两个 Link, 而 s2 也包含 (s1p1, s2p1) (s2p1, s1p1) 这是否是期望的.

###void identifyOpenflowDomains()

    根据 switchs, switchPorts, switchPortLinks 的信息, 初始化 switchClusterMap, clusters; 并将网络划分为集群, 每个集群是一个强连通的组件,
    网络中可能包括一些单向的链接. 通过 dfsTraverse 函数执行深度优先算法形成集群. 其中强连通的计算基于 Tarjan 算法

    该函数主要功能:

    依据 switches 通过 Tarjan 算法
    1. 初始化 switchClusterMap 建立 switch 及其 Cluster 直接的映射关系
    2. 初始化 clusters

###long dfsTraverse (long parentIndex, long currIndex, DatapathId currSw,Map<DatapathId, ClusterDFS> dfsList, Set <DatapathId> currSet)

    [Tarjan 算法](http://zh.wikipedia.org/zh/Tarjan%E7%AE%97%E6%B3%95)的变种

    强连通域: 强连通域中的每个节点都可以达到该域中的任意一个节点.

    关键点
          ClusterDFS : index = Long.MAX_VALUE, lowIndex = Long.MAX_VALUE, visitet = False 存储 currSw 在集群中的信息
          Dfsindex : sw 遍历的索引
          lowIndex : 当前交换机所处周围所有交换机的 Dfsindex 最低的值
          visited  : 该节点是否被遍历过
          访问过的 ClusterDFS, 设置其 Visited 为 true, DfsIndex 为 currIndex, ParentDFSIndex 为 parentIndex;

    遍历 currSw 的每个端口的每条链路 link:
        忽略 dstSw == srcSw,  currSw 存在于  switchClusterMap 中,  isBlockedLink(link), isBroadcastDomainLink(link) 这四种情况. 获取链路的目的端的交换机 dstSw
        如果 dstSw 已经被访问过且索引大于 currSw, 继续遍历下一条链路
        如果 dstSw 已经被访问过且索引小于 currSw, 更新 currDFS.lowIndex
        如果 dstSw 没有被访问过, 调用 dfsTraverse(currIdex, currIdex+1, dstSw, dfsList, currSet); 之后,更新 currSw.lowIndex

    如果 currSw.lowIndex > currDfs.getParentDFSIndex() 建立一个新的集群.

    注: 理解本算法的最佳方式是假设有三个交换机互联和四个交换机互联的这两中情况来推断算法是正确的

###Set<NodePortTuple> getBlockedPorts()

    返回 this.blockedPorts

###Set<Link> getBlockedLinks()

    返回 this.blockedLinks

###boolean isBlockedLink(Link l)

    如果 l 的 NodePortTuple(Src, SrcPort) 或订阅的 NodePortTuple(Dst(), DstPort) 是 isBlockedPort,  返回 true; 否则返回 false

    问题: 既然已经有 blockedLinks 这个成员变量, 显然通过 blockedPorts 似乎就不太合适了.

###boolean isBlockedPort(NodePortTuple npt)

    如果 ntp 在 blockedPorts 中, 返回 true; 否则返回 false

###boolean isTunnelPort(NodePortTuple npt)

    如果 ntp 在 tunnelPorts 中, 返回 true; 否则返回 false

###boolean isTunnelLink(Link l)

    如果 l 的 NodePortTuple(Src, SrcPort) 或 NodePortTuple(Dst, DstPort) 是isTunnelPort, 返回 true; 否则返回 false 

###boolean isBroadcastDomainLink(Link l)

    只要 l 的 NodePortTuple(Src, SrcPort) 或 NodePortTuple(Dst, DstPort) 是 isBroadcastDomainPort, 返回true; 否则返回 false

###boolean isBroadcastDomainPort(NodePortTuple npt)

    如果 ntp 在 broadcastDomainPorts 中,返回 true; 否则 false;

##BroadcastTree clusterDijkstra(Cluster c, DatapathId root,Map<Link, Integer> linkCost,boolean isDstRooted)

    其中 listCost 记录了 TunnelPorts 中配置指定链路的权值. 在计算链路的 cost 的优先级很高.

    源交换机: root
    HashMap<DatapathId, Link> nexthoplinks = new HashMap<DatapathId, Link>(); 集群中的所有节点，
    HashMap<DatapathId, Integer> cost = new HashMap<DatapathId, Integer>(); 记录每个交换机到源交换机的距离
    HashMap<DatapathId, Boolean> seen = new HashMap<DatapathId, Boolean>(); 记录已经访问的节点
    PriorityQueue<NodeDist> nodeq = new PriorityQueue<NodeDist>() : 待访问的节点

    初始化广播树中所有节点和距离
    遍历每一个集群中每一个节点的所有链路:
        如果链路对端已经访问过或与当前交换机是同一交换机, 跳过该链路
        如果对端的距离到源交换机的距离大于当前交换机到源交换机的距离加1, 修改当前到源交换机的链路更新都广播树, 调整当前交换机到源交换机的距离更新到广播树

    默认每一个节点的 dist 是其与其周围节点的最小dist+1

    问题:  tunnelPorts 当前的作用还很基础,只是一个固定的值, 无法更加交换机直接的带宽来设置不同的距离, 需要进一步优化. 

###void calculateShortestPathTreeInClusters()

    为 clusters 每个节点计算它的广播树(BroadcastTree), 将其保存在 destinationRootedTrees  中

    广播树; 即集群中其他节点到该节点的 links 和 cost 值

    遍历 this.tunnelPorts， 遍历 this.switchPortLinks.get(npt)，初始化 listCost， 设置了所有的 link 的基础权重是一样的。
    遍历每个集群的所有节点, 调用 dijkstra(c, node, linkCost, true) 生成广播树(BroadcastTree), 加入 destinationRootedTrees(node, BroadcastTree) 构建广播树

###void calculateBroadcastTreeInClusters()

    遍历所有的集群, 将 destinationRootedTrees 中id 最小的 switch 对应的元素加入 clusterBroadcastTrees 中

    注: clusterBroadcastTrees 与 destinationRootedTrees 区别在于前者只记录集群中
    id 最小的 switch 的广播树, 而后者记录所有 switch 的广播树. 对于前者每个集群只有一个元素.

###void calculateBroadcastNodePortsInClusters()

    用 destinationRootedTrees 初始化 clusterBroadcastTrees, 将 clusterBroadcastTrees 中的 BroadcastTree 的所有节点加入 clusterBroadcastNodePorts 中

###void calculateAllShortestPaths()

    根据 allLinks, tunnelPorts 调用 dijkstra 算法, 初始化 destinationRootedFullTrees, finiteBroadcastTree

###BroadcastTree dijkstra(Map<DatapathId, Set<Link>> links, DatapathId root, Map<Link, Integer> linkCost, boolean isDstRooted)

    links : 通过 LLDP 探测到的所有的 links
    root  : 某个交换机 dpid
    linkCost : tunnelPorts 的 cost
    isDstRooted : root 为目的交换机

    通过 dijkstra 算法建立所有节点到 root 的广播树, 之后返回


###calculateAllBroadcastNodePorts();

    利用 finiteBroadcastTree 初始化 broadcastNodePorts



###Route buildroute(RouteId id)

    如果 destinationRootedTrees 为 null 或不存在 id.getDst() 返回 null
    如果 id.getSrc() 或 id.getDst() 不在 this.switchs, 返回 null
    如果 id.getSrc() 和 id.getDst() 都存在与 this.switchs, id.getSrc() == id.getDst() 返回 null
    destinationRootedFullTrees 中 id.getDst() 的链路 nexthoplinks, link = nexthoplinks.get(srcId) 不为 null,
    遍历  nexthoplinks 的 (s1p1 s2p1), (s2p2, s3p1), (s3p2, s4p1) ... 依次加到局部变量 switchPorts 中, 直到与 id.getDst() 相同, 返回新的路由

    最后 Route 为 (RouteId(id), (s1p1 s2p1), (s2p2, s3p1), (s3p2, s4p1))

    注: 这是路由的核心实现, 利用已经建立的拓扑, 实现路由.

    这里是但路由, 对于多路由实现思路需要调整.

###int getCost(DatapathId srcId, DatapathId dstId)

    从 destinationRootedTrees.get(dstId) 的广播树中获取链路权值

    问题: 如果 destinationRootedTrees == null, NULL 指针异常

###Set<Cluster> getClusters()

    返回所有集群,即 clusters

###BroadcastTree getBroadcastTreeForCluster(long clusterId)

    switchClusterMap 中获取 clusterId 对应的集群 c, 
    clusterBroadcastTrees.get(c.getId())

    问题: 如果 switchClusterMap 或 clusterBroadcastTrees 等于 null, NULL 指针异常


##实现 IRoutingService

这里获取路由是从 pathcache 中获取, 但判断路由是否存在是从 destinationRootedTrees 中判断, 感觉很迷惑.

###boolean routeExists(DatapathId srcId, DatapathId dstId)

    检查 dstId 所对应的广播树(BroadcastTree)的所有链路中是否存在 srcId

    问题: 如果 destinationRootedTrees == null, NULL 指针异常


###Route getRoute(ServiceChain sc, DatapathId srcId, OFPort srcPort,DatapathId dstId, OFPort dstPort, U64 cookie)

    如果 srcId == dstId 并且 srcPort == dstPort 那么是同一交换机同一端口, 直接返回 null
    如果 srcId,dstId 不在 pathcache 中, 且 srcId 和 dstId 是不同的交换机, 表明没有路由, 返回 null
    如果 srcId,dstId 在 pathcache 中 或 srcId 和 dstId 属于同一交换机, 增加 srcId 到 dstId 的路由

    问题: 如果 pathcache 不存在 srcId 到 dstId 的路由, 为什么要判断 srcId 和 dstId 是否是同一交换机?
    如果 pathcache 没有路由,但是同一交换机的不同端口, 直接创建路由即可, 如果是不同交换机, 显然不能直接创建路由

###Route getRoute(DatapathId srcId, DatapathId dstId, U64 cookie)

    从 pathcache 获取 RouteId(srcId, dstId) 对应的 Route

##实现 ITopologyService

###boolean isInternalToOpenflowDomain(DatapathId switchid, OFPort port)

    如果 NodePortTuple(switchid,port) 在 switchPortLinks 中, 返回 true; 否则直接返回 false;

    注: 一个 NodePortTuple(switchid,port) 不是 AttachmentPointPort 就是 InternalToOpenflowDomain, 这里端口直连的是主机, 而 InternalToOpenflowDomain 表明该端口直连的是交换机

###boolean isAttachmentPointPort(DatapathId switchid, OFPort port)

    如果 NodePortTuple(switchid,port) 在 switchPortLinks 中, 返回 false; 否则直接返回 true

###DatapathId getOpenflowDomainId(DatapathId switchId)

    如果 cluster = switchClusterMap.get(switchId) 不为 null, 返回 cluster.getID()
    否则 返回 switchId

###DatapathId getL2DomainId(DatapathId switchId)

    等同于 getOpenflowDomainId

###Set<DatapathId> getSwitchesInOpenflowDomain(DatapathId switchId) 

    从 switchClusterMap 获取集群 id 为 switchId 的所有节点ID, 如果 switchClusterMap 不存在, 直接返回 switchId 的集合

###boolean isAllowed(DatapathId sw, OFPort portId)

    直接返回 true

###boolean isIncomingBroadcastAllowedOnSwitchPort(DatapathId sw, OFPort portId)

    如果一个节点不在任何集群中那么它就是 IncomingBroadcast, 返回 true
    如果一个节点存在于某一集群c, 且存在于 clusterBroadcastNodePorts.get(c) 中, 那么就是  IncomingBroadcast, 返回 true

###boolean isConsistent(DatapathId oldSw, OFPort oldPort, DatapathId newSw,OFPort newPort)

    如果 isInternalToOpenflowDomain(newSw, newPort)
    否则比较 oldSw == newSw 和 oldPort == newPort

    待继续理解

###Set<NodePortTuple> getBroadcastNodePortsInCluster(DatapathId sw)

    调用　getOpenflowDomainId(targetSw)　获取 clusterID
    从　clusterBroadcastNodePorts　获取集群　ID 对应的端口列表,返回该端口列表

###boolean inSameBroadcastDomain(DatapathId s1, OFPort p1, DatapathId s2, OFPort p2)

    直接返回　false
    问题: 待继续理解

###boolean inSameOpenflowDomain(DatapathId switch1, DatapathId switch2)

    从　switchClusterMap 获取　switch1，switch2　对应的集群 c1, c2:
    如果两个集群都不为　null, 比较 c1.getId() 和 c2.getId() 
    否则, 直接比较 switch1，switch2 是否相同

###boolean inSameL2Domain(DatapathId switch1, DatapathId switch2)

    同　inSameOpenflowDomain(switch1, switch2)

###NodePortTuple getOutgoingSwitchPort(DatapathId src, OFPort srcPort,DatapathId dst, OFPort dstPort)

    用于重定向
    直接返回 new NodePortTuple(dst, dstPort)
    问题: 待继续理解

###NodePortTuple getIncomingSwitchPort(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort)

    如果需要，　可以用该函数从不同的端口重新注入
    直接返回 new NodePortTuple(src, srcPort)
    问题: 待继续理解

###Set<DatapathId> getSwitches()

    获取所有的交换机ID

###Set<OFPort> getPortsWithLinks(DatapathId sw)

    获取　sw 的所有端口


###Set<OFPort> getBroadcastPorts(DatapathId targetSw, DatapathId src, OFPort srcPort)

    调用　getOpenflowDomainId(targetSw)　获取 clusterID
    从　clusterBroadcastNodePorts　获取集群　ID 对应的端口列表,返回该端口列表

    即　clusterBroadcastNodePorts.get(getOpenflowDomainId(targetSw)) 每个元素的　port 组成的集合

###NodePortTuple　getAllowedOutgoingBroadcastPort(DatapathId src, OFPort srcPort, DatapathId dst,OFPort dstPort)

    未实现, 实现可以参考 isIncomingBroadcastAllowedOnSwitchPort 实现

###NodePortTuple　getAllowedIncomingBroadcastPort(DatapathId src, OFPort srcPort)

    未实现


##TopologyEventInfo

    拓扑信息暴露给 TopologyEvent

###关键变量

    int numOpenflowClustersWithTunnels
    int numOpenflowClustersWithoutTunnels
    Map<DatapathId, List<NodePortTuple>> externalPortsMap
    int numTunnelPorts

###TopologyEventInfo(int numOpenflowClustersWithTunnels, int numOpenflowClustersWithoutTunnels,Map<DatapathId, List<NodePortTuple>> externalPortsMap,int numTunnelPorts)

    this.numOpenflowClustersWithTunnels = numOpenflowClustersWithTunnels;
    this.numOpenflowClustersWithoutTunnels = numOpenflowClustersWithoutTunnels
    this.externalPortsMap = externalPortsMap
    this.numTunnelPorts = numTunnelPorts

##TopologyEvent

    拓扑事件

###关键变量

    String reason
    TopologyEventInfo topologyInfo

###TopologyEvent(String reason, TopologyEventInfo topologyInfo)

    this.reason = reason
    this.topologyInfo = topologyInfo

##TopologyManager

    负责维护网络拓扑,通过拓扑找到两个节点的路由, 主要做两件事情：1. 固定间隔运行 UpdateTopologyWorker， 更新拓扑； 2. 接受 packet_in 事件

##关键概念

    //其他模块
    HARole role
    IHAListener haListener
    ILinkDiscoveryService linkDiscoveryService
    IThreadPoolService threadPoolService
    IFloodlightProviderService floodlightProviderService
    IOFSwitchService switchService
    IRestApiService restApiService
    IDebugCounterService debugCounterService

    We expect every switch port to have at most two links.  Both these
    links must be unidirectional links connecting to the same switch port.
    If not, we will mark this as a broadcast domain port.

    Map<DatapathId, Set<OFPort>> switchPorts       : (交换机,交换机的端口)
    Map<NodePortTuple, Set<Link>> switchPortLinks  : (节点:节点的链路)
    Map<NodePortTuple, Set<Link>> directLinks      : switchPortLinks 的子集,只包括和 key 直连的链路
    Set<NodePortTuple> tunnelPorts                 : 所有 tunnelPort 的节点
    Map<NodePortTuple, Set<Link>> portBroadcastDomainLinks : 非直连的 link

    TopologyInstance currentInstance
    TopologyInstance currentInstanceWithoutTunnels
    SingletonTask newInstanceTask


    int TOPOLOGY_COMPUTE_INTERVAL_MS = 500         : 拓扑更新间隔 ms
    TopologyInstance currentInstance               : 目前的 TopologyInstance 实例
    TopologyInstance currentInstanceWithoutTunnels : 没有 tunnels 的实例
    IEventUpdater<TopologyEvent> evTopology        : 交换机事件更新器
    ArrayList<ITopologyListener> topologyAware     : 发布拓扑更新的模块


    BlockingQueue<LDUpdate> ldUpdates              : 保存 LinkDiscovery 模块的 Link 更新信息
    boolean linksUpdated                           : link 更新的的标志
    boolean dtLinksUpdated                         : 直连链路是否更新
    boolean tunnelPortsUpdated                     :
    Date lastUpdateTime                            : 上次更新时间

###int getTopologyComputeInterval()

    获取拓扑更新时间

###void setTopologyComputeInterval(int time_ms)

    设置拓扑更新时间

##void startUp()

    清除目前的拓扑, switchPorts，tunnelPorts，switchPortLinks，portBroadcastDomainLinks，directLinks
    创建 TopologyInstance() TopologyEventInfo()

##更新拓扑线程

    拓扑更新线程,每次运行完后,隔 0.5s 继续运行, 如果没有拓扑改变, 该线程一直阻塞

##void linkDiscoveryUpdate(List<LDUpdate> updateList)

    该模块监听 linskDiscovery 模块, 将更新事件列表 updateList 加入 ldUpdates

##void linkDiscoveryUpdate(LDUpdate update)

    该模块监听 linskDiscovery 模块, 将更新事件 update 加入 ldUpdates

##class UpdateTopologyWorker implements Runnable

    调用 updateTopology() 更新拓扑

###boolean updateTopology()

    重置 linksUpdated dtLinksUpdated tunnelPortsUpdated 标志为 false;
    调用 applyUpdates() 更新各种事件
    调用 createNewInstance() 重新计算拓扑
    informListeners() 通知订阅拓扑更新的订阅者
    返回 true

###List<LDUpdate> applyUpdates()

    遍历 ldUpdates 中的更新事件，如果 ldUpdates 为 null, 一直阻塞,不为 null 从中取出一个更新
    如果是 LINK_UPDATED, 调用 addOrUpdateLink(update.getSrc(), update.getSrcPort(),update.getDst(), update.getDstPort(),update.getType())
    如果是 LINK_REMOVED, 调用 removeLink(update.getSrc(), update.getSrcPort(),update.getDst(), update.getDstPort())
    如果是 SWITCH_UPDATED 调用 addOrUpdateSwitch(update.getSrc())
    如果是 SWITCH_REMOVED 调用 removeSwitch(update.getSrc())
    如果是 TUNNEL_PORT_ADDED 调用 addTunnelPort(update.getSrc(), update.getSrcPort())
    如果是 TUNNEL_PORT_REMOVED 调用 removeTunnelPort(update.getSrc(), update.getSrcPort())
    如果是 PORT_UP 或 PORT_DOWN 什么也不做

    返回所有的更新 update

###void addSwitch(DatapathId sid)

    this.switchPorts 增加 sid 的交换机

###void addPortToSwitch(DatapathId s, OFPort p)

    增加 s, p 到 this.switchPorts

###boolean addLinkToStructure(Map<NodePortTuple,Set<Link>> s, Link l)

    将 l 增加到 s 中

###boolean removeLinkFromStructure(Map<NodePortTuple, Set<Link>> s, Link l)

    如果 l 存在于 s 中, 将 l 从 s 中删除

###void addOrUpdateLink(long srcId, short srcPort, long dstId,short dstPort, LinkType type)

    将 link 增加到 switchPorts 中

    如果 link 类型是 MULTIHOP_LINK :
        将 (srcId,srcPort)(dstId, dstPort) 增加到 this.switchPorts 
        link 增加到 switchPortLinks 和 portBroadcastDomainLinks
        如果 link 存在于 directLinks, 从 directLinks 删除 link

    如果 link 类型是 DIRECT_LINK， 
        将 (srcId,srcPort)(dstId, dstPort) 增加到 this.switchPorts 
        将 link 增加到 switchPortLinks 和 directLinks， 
        如果 link 存在于 portBroadcastDomainLinks, 从 portBroadcastDomainLinks 删除 link，。

    如果 link 类型是 LinkType.TUNNEL
        addOrUpdateTunnelLink， **目前没有实现**。

###void removeLink(Link link)

    从 directLinks, portBroadcastDomainLinks, switchPortLinks 删除 link。

    如果 switchPortLinks 中的某个交换机的端口没有任何 link，就从 switchPorts 中删除这个交换机的端口。

    如果 switchPorts 中的某个交换机中没有任何端口，就删除该交换机。

###void removeLink(long srcId, short srcPort,long dstId, short dstPort)

    调用 removeLink(Link(srcId, srcPort, dstId, dstPort))

###void addOrUpdateSwitch(DatapathId sw)

    什么也不做

    这是因为如果一个交换机增加了,只有由端口启动建立链路才有意义, 而这些工作已经在 LINK_UPDATED
    事件中做了,因此这里没有必要, 当然将 sw 增加到 switchPortLinks ,switchPorts 也没有问题.

###void removeSwitch(long sid)

    从 tunnelPorts directLinks, portBroadcastDomainLinks, switchPortLinks 中删除所有交换机 sid 关联的元素

    问题: 这里依次删除 link 再删除交换机效率显然如直接删除 sid 对应的 key

###void addTunnelPort(DatapathId sw, OFPort port)

    将 NodePortTuple(sw, port) 增加到 tunnelPorts, 置位 tunnelPortsUpdated

###void removeTunnelPort(DatapathId sw, OFPort port)

    将 NodePortTuple(sw, port) 从 tunnelPorts 中删除, 置位 tunnelPortsUpdated

###Set<NodePortTuple> identifyBroadcastDomainPorts()

    如果 switchPortLinks 中的每个节点的对应的链路数多于 2 或节点数等于 2 但是不是对称的, 就认为是广播数链路, 加入 broadcastDomainPorts

    对称: link1(s1,p1, s2, p2) link2(s2,p2,s1,p1) link1 与 link2 认为是对称的.

###boolean createNewInstance(String reason)

    如果 linksUpdated 为 false, 返回 false

    重新计算 broadcastDomainPorts. 如果 switchPortLinks 中的每个节点的对应的链路数多于 2 或节点数等于2但是不是对称的, 就认为是广播数链路, 加入 broadcastDomainPorts

    openflowLinks 拷贝 switchPortLinks
    从 openflowLinks 删除 broadcastDomainPorts 中存在的节点
    从 openflowLinks 删除 tunnelPorts 中存在的节点

    allPorts 保存了 sw 和 sw 所有端口列表的映射关系

    创建 nt = TopologyInstance(switchPorts,blockedPorts, openflowLinks,broadcastDomainPorts,tunnelPorts, switchPortLinks, allPorts) 重新计算集群与集群链路信息

    返回 true

    问题: 这里 blockedPorts 为 null, 显然不是期望的,但也不存在严重问题.


###void informListeners(List<LDUpdate> linkUpdates)

    通过 topologyAware 获取所有的事件订阅者 listens， 每个订阅者调用 listens.topologyChanged(linkUpdates)

##PACKET_IN 事件

##Command receive(IOFSwitch sw, OFMessage msg, FloodlightContext cntx)

    接受 PACKET_IN 事件，如果包是 BSN 包，并且 payLoad 是 LDDP 调用 doFloodBDDP(sw.getId(), pi, cntx)
    否则调用 dropFilter(sw.getId(), pi, cntx)

###Command processPacketInMessage(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx)

    如果包是 BSN 包
        如果 payLoad 是 LDDP 调用 doFloodBDDP(sw.getId(), pi, cntx)
        如果 payLoad 不是 LDDP, 返回, 使得该包继续被其他订阅 PACKET_IN 的模块使用
    如果包不是 BSN 包 dropFilter(sw.getId(), pi, cntx)

###Set<OFPort> getPortsToEliminateForBDDP(DatapathId sid)

    获取链路发现模块中忽略(suppressed)的端口

###void doFloodBDDP(long pinSwitch, OFPacketIn pi, FloodlightContext cntx)

    集群 id 为 pinSwitch 中所有的交换机 switches
    遍历 switches 的每个 switch：
        获取每个 switch 的可用 ports，
        从 ports 删除 switch 中的所有非广播端口
        从 ports 删除 链路发现模块屏蔽的所有端口
        从 ports 删除包进入的端口
        调用 doMultiActionPacketOut， 向 switch 的所有 ports 中发送 PACKET_OUT 消息，消息内容为 pi.getPayload

###void doMultiActionPacketOut(byte[] packetData, IOFSwitch sw,Set<OFPort> ports,FloodlightContext cntx)

    向 switch 的所有 ports 中发送 PACKET_OUT 消息，消息内容为 pi.getPayload

###Command dropFilter(DatapathId sw, OFPacketIn pi,FloodlightContext cntx)

    检查 sw，pi.getInPort 是否是允许的，如果不允许停止包处理，否则，让包被后续监听器处理。

    bug: result = Command.STOP;

##订阅链路发现消息

###void linkDiscoveryUpdate(List<LDUpdate> updateList)

    将更新事件加入 ldUpdates

###void linkDiscoveryUpdate(LDUpdate update)

    将更新事件加入 ldUpdates


##订阅 IRoutingService

###Route getRoute(DatapathId src, DatapathId dst, U64 cookie)

    如果 src == dst 返回 null
    如果 src,dst 在缓存的路径中, 返回对应的路由, 如果不存在, 返回 null

###Route getRoute(DatapathId src, DatapathId dst, U64 cookie, boolean tunnelEnabled)

    如果 src == dst 返回 null
    根据拓扑建立所有路由, 如果存在对应的路由, 返回该路由, 如果不存在, 返回 null

###Route getRoute(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort, U64 cookie)

    如果 src == dst, srcPort == dstPort 返回 null
    经过拓扑计算后,
    如果src, dst是连接的起来, 返回 Route(RouteId(src,dst), {(src,srcPort), 已经存在路由,(dst,Port)})
    如果src, dst不是连接起来的
            如果 src 和 dst 不是同一交换机, 返回 null
            如果 src == dst srcPort != dstPort, 返回 Route(RouteId(src,dst), {(src,srcPort),(dst,Port)})

###Route getRoute(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort, U64 cookie,boolean tunnelEnabled)

    如果 src == dst, srcPort == dstPort 返回 null
    经过拓扑计算后,
    如果src, dst是连接的起来, 返回 Route(RouteId(src,dst), {(src,srcPort), 已经存在路由,(dst,Port)})
    如果src, dst不是连接起来的
            如果 src 和 dst 不是同一交换机, 返回 null
            如果 src == dst srcPort != dstPort, 返回 Route(RouteId(src,dst), {(src,srcPort),(dst,Port)})

    这里有一个问题: 如果 已经存在的路由的首节点正好是 (src,srcPort) 或 尾节点是 (dst,Port) 那么, 这就是不期望的了.

###boolean routeExists(DatapathId src, DatapathId dst)

    返回 src dst 之间是否已经建立路由

###boolean routeExists(DatapathId src, DatapathId dst, boolean tunnelEnabled)

    返回 src dst 之间是否已经建立路由

###ArrayList<Route> getRoutes(DatapathId srcDpid, DatapathId dstDpid,

##实现 IHAListener

##HAListenerDelegate

###void transitionToActive()

    一旦角色改变,立即启动拓扑更新线程

以下实现略

* void controllerNodeIPsChanged
* String getName()
* boolean isCallbackOrderingPrereq(HAListenerTypeMarker type, String name)
* boolean isCallbackOrderingPostreq(HAListenerTypeMarker type, String name)
* void transitionToStandby()


##实现 ITopoloeyService

tunnelPort 目前不起作用, 所以如下由 tunnelPort 参数的方法和没有 tunnelPort 的重载方法是完全一样的

###Date getLastUpdateTime()

    获取拓扑上次更新时间

###void addListener(ITopologyListener listener)

    增加拓扑更新的订阅者

###boolean isAttachmentPointPort(DatapathId switchid, OFPort port)

    isAttachmentPointPort(switchid, port, true)

###boolean isAttachmentPointPort(DatapathId switchid, OFPort port, boolean tunnelEnabled)

    首先端口不能是 链路发现的 tunnelPort
    不是拓扑中的挂载端口
    不是物理端口
    是交换机的有效端口

###DatapathId getOpenflowDomainId(DatapathId switchId)

    getOpenflowDomainId(switchId, true)

###DatapathId getOpenflowDomainId(DatapathId switchId, boolean tunnelEnabled)

    如果交换机在集群中, 获取交换机所在集群的 id, 否则, 返回 switchId

###DatapathId getOpenflowDomainId(DatapathId switchId, boolean tunnelEnabled)

    如果交换机在集群中, 获取交换机所在集群的 id, 否则, 返回 switchId

###DatapathId getL2DomainId(DatapathId switchId)

    如果交换机在集群中, 获取交换机所在集群的 id, 否则, 返回 switchId

###DatapathId getL2DomainId(DatapathId switchId, boolean tunnelEnabled)

    如果交换机在集群中, 获取交换机所在集群的 id, 否则, 返回 switchId

###boolean inSameOpenflowDomain(DatapathId switch1, DatapathId switch2)

    switch1 和 switch2 是否在同一集群

###boolean inSameOpenflowDomain(DatapathId switch1, DatapathId switch2,boolean tunnelEnabled)

    switch1 和 switch2 是否在同一集群

###boolean isAllowed(DatapathId sw, OFPort portId) 

    直接返回 true
    
###boolean isAllowed(DatapathId sw, OFPort portId, boolean tunnelEnabled)

    直接返回 true

###boolean isIncomingBroadcastAllowed(DatapathId sw, OFPort portId)

    如果 sw 的 port 直连是主机或交换机的广播域端口

###boolean isIncomingBroadcastAllowed(DatapathId sw, OFPort portId,boolean tunnelEnabled)

    如果 sw 的 port 是主机或交换机的广播域端口

###Set<OFPort> getPortsWithLinks(DatapathId sw)

    获取 sw 的所有端口    

###Set<OFPort> getPortsWithLinks(DatapathId sw, boolean tunnelEnabled)

    获取 sw 的所有端口 

###Set<OFPort> getBroadcastPorts(DatapathId targetSw,DatapathId src, OFPort srcPort)

    获取 targetSw 所在集群的广播域节点列表, 获取节点列表中的 Nodeid 与 targetSw 相同节点, 返回每个节点的端口组成的列表 
    文档: 获取挂载点 src,port 的主机发送的广播包到 targetSw 的端口列表

###Set<OFPort> getBroadcastPorts(DatapathId targetSw,DatapathId src, OFPort srcPort, boolean tunnelEnabled)

    获取 targetSw 所在集群的广播域节点列表, 获取节点列表中的 Nodeid 与 targetSw 相同节点, 返回每个节点的端口组成的列表 

    文档: 获取挂载点 src,port 的主机发送的广播包到 targetSw 的端口列表

###NodePortTuple getOutgoingSwitchPort(DatapathId src, OFPort srcPort,  DatapathId dst, OFPort dstPort)

    返回 NodePortTuple(dst,dstPort)
    
###NodePortTuple getOutgoingSwitchPort(DatapathId src, OFPort srcPort,  DatapathId dst, OFPort dstPort, boolean tunnelEnabled)

    返回 NodePortTuple(dst,dstPort)

###NodePortTuple getIncomingSwitchPort(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort)

    返回 NodePortTuple(src, srcPort)

###NodePortTuple getIncomingSwitchPort(DatapathId src, OFPort srcPort, DatapathId dst, OFPort dstPort,boolean tunnelEnabled)

    返回 NodePortTuple(src, srcPort)

###boolean isInSameBroadcastDomain(DatapathId s1, OFPort p1, DatapathId s2, OFPort p2)

    返回 (s1 集群 == s2 集群) 或 (s1 == s2)

###boolean isInSameBroadcastDomain(DatapathId s1, OFPort p1, DatapathId s2, OFPort p2, boolean tunnelEnabled)

    返回 (s1 集群 == s2 集群) 或 (s1 == s2)

###boolean isBroadcastDomainPort(DatapathId sw, OFPort port)

    NodePortTuple(sw, port) 是否在广播域节点集合中

###boolean isBroadcastDomainPort(DatapathId sw, OFPort port, boolean tunnelEnabled)

    NodePortTuple(sw, port) 是否在广播域节点集合中

###boolean isConsistent(DatapathId oldSw, OFPort oldPort, DatapathId newSw, OFPort newPort)

    如果 newSw,newPort 直连的是交换机, 直接返回 true
    否则, 检查 oldSw == newSw && oldPort == newPort

###boolean isConsistent(DatapathId oldSw, OFPort oldPort, DatapathId newSw, OFPort newPort, boolean tunnelEnabled)

    如果 newSw,newPort 直连的是交换机, 直接返回 true
    否则, 检查 oldSw == newSw && oldPort == newPort

###boolean inSameL2Domain(DatapathId switch1, DatapathId switch2)

    switch1 和 switch2 是否在同一集群

###boolean inSameL2Domain(DatapathId switch1, DatapathId switch2,boolean tunnelEnabled)

    switch1 和 switch2 是否在同一集群

###NodePortTuple getAllowedOutgoingBroadcastPort(DatapathId src,OFPort srcPort,DatapathId dst,OFPort dstPort)

    返回 null

###NodePortTuple getAllowedOutgoingBroadcastPort(DatapathId src,OFPort srcPort,DatapathId dst,OFPort dstPort, boolean tunnelEnabled)

    返回 null

###NodePortTuple getAllowedIncomingBroadcastPort(DatapathId src, OFPort srcPort)

    返回 null

###NodePortTuple getAllowedIncomingBroadcastPort(DatapathId src, OFPort srcPort)

    返回 null

###Set<DatapathId> getSwitchesInOpenflowDomain(DatapathId switchDPID)
    
    如果 switchDPID 在某一集群中, 返回该集群中的所有交换机集合, 否则返回 switchDPID

###Set<DatapathId> getSwitchesInOpenflowDomain(DatapathId switchDPID, boolean tunnelEnabled)

    如果 switchDPID 在某一集群中, 返回该集群中的所有交换机集合, 否则返回 switchDPID

###Set<NodePortTuple> getBroadcastDomainPorts() 

    返回广播域所有节点列表

###Set<NodePortTuple> getTunnelPorts()

    返回 TunnelPorts 的所有节点

###Set<NodePortTuple> getBlockedPorts()

    返回所有阻塞节点列表

###Set<OFPort> getPorts(DatapathId sw)

    返回交换机中所有　Enable 端口中去除 QuarantinedPort


* Map<DatapathId, Set<OFPort>> getSwitchPorts()
* Map<NodePortTuple, Set<Link>> getSwitchPortLinks()
* Map<NodePortTuple, Set<Link>> getPortBroadcastDomainLinks()
* TopologyInstance getCurrentInstance(boolean tunnelEnabled)
* TopologyInstance getCurrentInstance()


