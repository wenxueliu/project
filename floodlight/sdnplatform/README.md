##配置

FloodlightProvider

controllerid


如果配置文件中为空,　就从本地数据库的表 SYSTEM_UNSYNC_STORE 查找

KEY_STORE_PATH : keyStorePath
KEY_STORE_PASSWORD : keyStorePassword
AUTH_SCHEME : authScheme -> CHALLENGE_RESPONSE
SEEDS : ip:port,ip:port,ip:port

##说明

动态伸缩线程池 : 默认没有线程, 新任务来, 创建新线程, 如果所有线程执行超过 60 秒, 由新任务来,
创建新线程, 当没有任务, 已经完成任务的线程自动关闭. 这通过 Executors.newCachedThreadPool 实现

这里线程没有上限, 如果出现网络阻塞, 将会创建大量的线程, 后续根据需要调整, 可以加入监控.


定时清理并不靠谱, 应该还满足低负载情况, 否则, 由于锁, 清理工作在大量并发写的情况下或导致严重
的延迟, 而这是不允许的.  此外, 应该增加手动触发清理的接口.


##通信建立

1. 本地开启动态伸缩的线程池监听配置文件中 port 的请求
2. 与配置文件中的其他节点建立 keep-alive 连接. 并发送心跳保持连接.  除非网络出现问题.

##数据版本机制

基于版本的向量时钟.

每个 key 与 Versioned 关联.

每个 Versioned 由 VectorClock, T 组成

每个 VectorClock 以 versions(List<ClockEntry(nodeId, version)>) timestamp. 其中
versions 中以 nodeId 由小到大排序, version 是单调递增的.

每次 Versioned 的版本递增, 更新 VectorClock 的 nodeId 对应的 version 和 timestamp

##数据存储过程

DefaultStoreClient 调用 put 操作:

1. store, key, value 首先保持在本地的数据库(持久的或内存)
2. 如果 scope 不为 UNSYNCHRONIZED, 将其加入一个队列. 通知同步线程从该队列中取数据, 同步线程每次从队列中最多取 50 个, 发送给所有节点(满足条件: 非本节点并且非本 domainId 和 Scope 不是 LOCAL)
3. 发送过程, 如果与某个节点已经有 500 个数据还没有收到远端的应答, 新的同步操作将会阻塞(或超时), 直到没有收到远程应答完的同步的数据少于 500 的时候, 才将新的数据发送出去.

整个过程都是异步的, 其中数据更新通知由 HintWorker 完成. 网络发送由 RPCService 完成

##数据更新通知机制

对需要的表名通过 IStoreClient.addStoreListener 或 SyncManager.addListener 添加订阅

比如对应节点信息, 如果改变了节点信息, 由于 SyncStoreCCProvider
订阅了存储节点的表, 一旦该表被修改, 就会通知 SyncManager 更新配置

此外, 本地可以订阅远程的表, 如果该表发生变化, 远程通知本地节点取更新对应配置. TODO

##全量同步过程

1. 遍历所有的 store, 如果 store 的 scope 1) 不是 UNSYNCHRONIZED, 2) GLOBAL 或 LOCAL 并且 DomainId 与 localNodeId 的 DomainId 相同
2. 以每 50 条消息遍历当前节点的 store 的 key,value, 发送 SyncOffer 给 node.
3. 发送过程, 如果与某个节点已经有 500 个数据还没有收到远端的应答, 新的同步操作将会阻塞(或超时), 直到没有收到远程应答完的同步的数据少于 500 的时候, 才将新的数据发送出去.

##集群节点新节点加入

1. Node1 给发送 Node2 加入集群请求
2. 如果 Node1 发送消息没有设置节点 id, Node2 为 Node1 生成随机 NodeId 和 DomainId(与 NodeId 相同) 之后将新加入 NodeId 加入 Node2 的存储
(表名SYSTEM_NODE_STORE), 之后将 Node2 存储表SYSTEM_NODE_STORE的数据发送给 Node1, 发送集群加入应答消息.
3. 如果 Node1 发送消息设置节点 id, 将新加入 NodeId 加入 Node2 的存储 (表名SYSTEM_NODE_STORE), 之后将 Node2 存储表SYSTEM_NODE_STORE的数据发送给 Node1, 发送集群加入应答消息.
4. 如果 Node1 发送消息没有设置节点 id, Node1 将 Node2 发送的表 SYSTEM_NODE_STORE 的节点数据存在在本地的 SYSTEM_NODE_STORE, 并将 Node2 生成的节点 id 作为本机的 NodeId
5. 如果 Node1 发送消息设置节点 id, Node1 将 Node2 发送的表 SYSTEM_NODE_STORE 的节点数据存在在本地的 SYSTEM_NODE_STORE

##集群节点已经存在节点加入

1. Node1 给发送 Node2 加入集群请求
3. 如果 Node1 发送消息设置节点 id, 将新加入 NodeId 加入 Node2 的存储 (表名SYSTEM_NODE_STORE), 之后将 Node2 存储表SYSTEM_NODE_STORE的数据发送给 Node1, 发送集群加入应答消息.
5. 如果 Node1 发送消息设置节点 id, Node1 将 Node2 发送的表 SYSTEM_NODE_STORE 的节点数据存在在本地的 SYSTEM_NODE_STORE

##SyncManager

SyncManager(继承 AbstractSyncManager 实现 ISyncService) 调用 DefaultStoreClient(继承 AbstractStoreClient 实现 IStoreClient)
来实现同步存储

DefaultStoreClient 将存储过程与对象版本化解耦, 真正的存储通过 JackSonStore(实现 IStore) 来实现. 版本通过 Versioned(实现 IVersion)
来实现

JackSonStore 实际存储数据的存储由 StoreRegistry 注册(注册的存储引擎必须实现 IStore<ByteArray, byte[]> 接口)
JackSonStore 只是将 K 转为 ByteArray, V 转换为 byte, 之后委托给 SynchronizingStorageEngine 存储
如果是持久存储, SynchronizingStorageEngine(JavaDBStorageEngine(store), scope)
如果是不是持久存储,　SynchronizingStorageEngine(InMemoryStorageEngine(storeName), scope)

SynchronizingStorageEngine 继承了 ListenerStorageEngine , 而 ListenerStorageEngine 实现了 IStorageEngine<ByteArray, byte[]>,
IStorageEngine<ByteArray, byte[]> 实现了 IStore<ByteArray, byte[]>

SynchronizingStorageEngine 实际存储如果是持久化存储委托给 JavaDBStorageEngine, 如果不是持久化存储, 委托给 InMemoryStorageEngine

InMemoryStorageEngine 将 key, value 存储在 ConcurrentHashMap<K, List<Versioned<V>>> 中

NOTE: 数组作为 key 是必须避免的




###配置

dbPath      : 数据库路径
authScheme  : NO_AUTH, CHALLENGE_RESPONSE
keyStorePath :
keyStorePassword :
nodes : 多个节点 ? 格式 byte
thisNode : 本节点 ID, Short
persistenceEnabled : true, false
configProviders : FallbackCCProvider,PropertyCCProvider,StorageCCProvider , 可以略
manualStores : 全局, 非永久存储的 StoreName.

BOOT_CONFIG : /opt/bigswitch/run/boot-config 路径下  controller-id

增加 listenAddress 选项

如果 thisNode 发生变化, 那么, 整个 SyncManager 会重新初始化

问题: 目前 DelegatingCCProvider 如果有多个配置, 每次更新配置只要由一个成功, 其他
providers 就不管了. 这貌似不和常理.


###void init(FloodlightModuleContext context): 初始化集群配置, 调试计数器配置
###void startUp(FloodlightModuleContext context)

* void registerStore(String storeName, Scope scope) : 注册 storeName, scope 到本地内存数据库
* void registerPersistentStore(String storeName, Scope scope) : 注册 storeName, scope 到本地永久存储数据库


* ClusterConfig getClusterConfig() : 获取配置信息
* void cleanup() : 如果数据库中的数据在 tombstoneDeletion 没有更新, 就被删除.
* void antientropy() ; 获取集群中所有节点, 随机取一个节点, 给该节点发送 Sync Off 消息.
* void writeSyncValue(String storeName, Scope scope, boolean persist, byte[] key, Iterable<Versioned<byte[]>> values) : 如果 values 中有一个 (key,value) put 成功, 通知远程订阅者 key 已经修改

如果 scope 为 LOCAL，只保持在本节点
如果 scope 为 GLOBAL 保持在所有节点, 会将其同步到其他节点
如果 persist 为 true, 调用 JavaDBStorageEngine
如果 persist 为 false, 调用 InMemoryStorageEngine

boolean handleSyncOffer(String storeName, byte[] key, Iterable<VectorClock> versions): 如果 storeName, key 对应的在本地存储的 value 的版本比 versions 都新, 返回 false, 否则返回 true.
IStorageEngine<ByteArray, byte[]> getRawStore(String storeName) : 获取 storeName 对应的存储引擎
IThreadPoolService getThreadPool() : 获取线程池对象
void queueSyncTask(SynchronizingStorageEngine e, ByteArray key, Versioned<byte[]> value) : 将 e.getStore(), key, value, 加入队列, 通知同步线程将其取出, 发送给所有节点
void addListener(String storeName, MappingStoreListener listener) : storeName 增加对其操作的订阅者, 每次 put 操作通知 listener 数据改变
public void updateConfiguration() : 500 ms 后执行一次配置更新操作
Cursor getCursor(int cursorId) : cursorMap 中获取 cursorId 对应的 Cursor
Cursor newCursor(String storeName) : 将 storeName 的 values 保持在 cursorMap 中
void closeCursor(Cursor cursor) : cursorMap 中删除 cursor.getCursorId() 对应的 Cursor
IStore<ByteArray,byte[]> getStore(String storeName) : 从 StoreRegistry 中获取 storeName 对应的 IStore
short getLocalNodeId() : 获取当前节点的 id, 如果不存在, 返回 Short.MAX_VALUE
void shutdown() : 关闭远程同步服务
void doUpdateConfiguration() : 读取配置文件中的节点, 比较新旧配置区别, 将修改的节点, 已经删除的节点断开连接; 如果 thisNode 发生变化, 重新初始化同步服务 
注: 这里并没有对新加节点进行处理, 实际的工作在 RPCService 中的 ConnectTask 处理.
SynchronizingStorageEngine getStoreInternal(String storeName) : 从 StoreRegistry 中获取 storeName 对应的 IStore
void sendSyncOffer(short nodeId, SyncMessage bsm) : 将 bsm 封装成 SyncOfferMessage, 发送 SYNC_OFFER 给节点 nodeId


void antientropy(Node node)

1. 遍历所有的 store, 如果 store 的 scope 1) 不是 UNSYNCHRONIZED, 2) GLOBAL 或 LOCAL 并且 DomainId 与 localNodeId 的 DomainId 相同
2. 以每 50 条消息遍历当前节点的 store 的 key,value, 发送 SyncOffer 给 node.

###AntientropyTask

Gossip 的 Anti-Entropy 工作模式, 从配置中找到所有节点, 然后随机选择一个节点, 如果该节点的 Scope
是 GLOBAL 或是本地的且 DomainId 与 当前节点的 DomainId 一样, 将当前节点的存储与选中的节点进行全量同步

1. 遍历所有的 store, 如果 store 的 scope 1) 不是 UNSYNCHRONIZED, 2) GLOBAL 或 LOCAL 并且 DomainId 与 localNodeId 的 DomainId 相同
2. 以每 50 条消息遍历当前节点的 store 的 key,value, 发送 SyncOffer 给 node.
3. 发送过程, 如果与某个节点已经有 500 个数据还没有收到远端的应答, 新的同步操作将会阻塞(或超时), 直到没有收到远程应答完的同步的数据少于 500 的时候, 才将新的数据发送出去.

###HintWorker 

两个线程(如果线程执行超过 60 秒, 新任务来, 创建新线程, 当没有任务, 线程自动关闭, 实现动态伸缩), 每个线程取 50 条
storeName, key, value,  以 SYNC_VALUE 消息发送给所有节点(满足条件: 非本节点并且非本 domainId 和 Scope 不是 LOCAL),
注意这里发送消息有流控(参考 RPCService 的 waitForMessageWindow).

###UpdateConfigTask

每 10 秒执行一次, 可以加入手动配置间隔和手动要求更新配置接口

读取配置文件中的节点, 比较新旧配置区别, 将不一致的节点, 已经删除的节点断开连接, 断开连接; 如果 thisNode 发生变化,
那么, 整个 SyncManager 会重新初始化

###CleanupTask

每一小时左右(30 s) 执行一次清除工作, 将存储中超过 tombstoneDeletion 的数据删除.

数据在内存数据库或持久数据库 int tombstoneDeletion = 24 * 60 * 60 * 1000 ms; 没有更新, 就会被删除

IThreadPoolService threadPool;
IDebugCounterService debugCounter;

RPCService rpcService = null;

int CLEANUP_INTERVAL = 60 * 60;
SingletonTask cleanupTask;

int ANTIENTROPY_INTERVAL = 5 * 60;
SingletonTask antientropyTask;

int CONFIG_RESCAN_INTERVAL = 10;
SingletonTask updateConfigTask;

int SYNC_WORKER_POOL = 2;
ExecutorService hintThreadPool;

Map<Integer, Cursor> cursorMap
Cursor getCursor(int cursorId) {
Cursor newCursor(String storeName)
void closeCursor(Cursor cursor) {

boolean persistenceEnabled = true;

StoreRegistry storeRegistry ;



IClusterConfigProvider clusterConfigProvider;
ClusterConfig clusterConfig = new ClusterConfig();
ClusterConfig getClusterConfig() : 获取集群配置
void updateConfiguration()


void shutdown()

##配置管理

###ClusterConfig 

* HashMap<Short, Node> allNodes : 保存 NodeId 与 Node 的映射关系
* HashMap<Short, List<Node>> localDomains : 具有相同 DomainId 的节点的映射关系
* Node thisNode : 当前节点
* AuthScheme authScheme : 认证方式
* String keyStorePath : 密码存储路径
* String keyStorePassword : 密码
* String listenAddress : 监听的 IP

###IClusterConfigProvider

集群配置提供者


###DelegatingCCProvider

实现 IClusterConfigProvider 接口, 代理所有 实现 IClusterConfigProvider

* List<IClusterConfigProvider> providers : 所有的集群配置提供者
* void init(SyncManager syncManager, FloodlightModuleContext context) : providers 的所有节点调用 init() 方法
* ClusterConfig getConfig() : 遍历 providers 中的每一个元素 provider, 只有有一个 provider.getConfig() 成功, 返回

###FallbackCCProvider

实现 IClusterConfigProvider 接口

* void init(SyncManager syncManager, FloodlightModuleContext context) : 读取 SyncManager 的配置信息
* ClusterConfig getConfig() : 将本机加入为节点, 一个节点的端口默认为 6642

###PropertyCCProvider

实现 IClusterConfigProvider 接口

* Map<String, String> config
* ClusterConfig getConfig()

* void init(SyncManager syncManager, FloodlightModuleContext context) : 读取 SyncManager 的配置信息
* ClusterConfig getConfig() : 

###StorageCCProvider

实现 IClusterConfigProvider 接口

* private IStorageSourceService storageSource;
* String thisControllerID : 
* AuthScheme authScheme;
* String keyStorePath;
* String keyStorePassword;

其中 thisControllerID 来自 FloodlightProvider.controllerid 或 "/opt/bigswitch/run/boot-config" 中 controller-id

* void init(SyncManager syncManager, FloodlightModuleContext context) : 从 FloodlightProvider 和 SyncManager
* ClusterConfig getConfig() : 从 "/opt/bigswitch/run/boot-config" 读取配置, 


在内存数据库中

CONTROLLER_TABLE_NAME  :表名
CONTROLLER_ID  : ip 地址
CONTROLLER_SYNC_ID  : nodeId
CONTROLLER_SYNC_DOMAIN_ID  : domainId
CONTROLLER_SYNC_PORT  : port

CONTROLLER_INTERFACE_TABLE_NAME : Ethernet
CONTROLLER_INTERFACE_DISCOVERED_IP : 控制 IP
CONTROLLER_INTERFACE_CONTROLLER_ID : thisControllerID 相同
CONTROLLER_INTERFACE_NUMBER : 0

###SyncStoreCCProvider

实现 IClusterConfigProvider 接口

SYSTEM_NODE_STORE   : nodeStoreClient
SYSTEM_UNSYNC_STORE : unsyncStoreClient
SEEDS 
LOCAL_NODE_ID  : 从 SYSTEM_UNSYNC_STORE 表中
LOCAL_NODE_IFACE  : 网卡名
LOCAL_NODE_HOSTNAME : 主机名 如 10.1.1.1
LOCAL_NODE_PORT : 端口 6642
AUTH_SCHEME 
KEY_STORE_PATH 
KEY_STORE_PASSWORD 

Map<String, String> config : 从 SyncManager 读取配置信息

* void init(SyncManager syncManager, FloodlightModuleContext context) : 注册 SYSTEM_NODE_STORE, SYSTEM_UNSYNC_STORE, 并注册这两张表的变化, 一旦发生变化, 调用 SyncManager 更新配置.

* ClusterConfig getConfig()

1. 如果 SyncManager 的 keyStorePath, keyStorePassword, authScheme 配置为空, 从 SYSTEM_UNSYNC_STORE 中读取
2. 从 SYSTEM_UNSYNC_STORE 的 LOCAL_NODE_ID 读取 localNodeId, 如果为 null, 从 SYSTEM_UNSYNC_STORE 的 SEEDS 读取 seed

    从 unsyncStoreClient 读取非本地节点信息, 用 nodeStoreClient 保存
    的本地 NodeId, DomainId 更新 unsyncStoreClient 保存的本地节点信息 

* Short getLocalNodeId(short nodeId, short domainId) : 将 SYSTEM_UNSYNC_STORE 的 LOCAL_NODE_HOSTNAME, LOCAL_NODE_PORT 与 nodeId, domainId 组成 Node.
* void updateSeeds(ClusterConfig config) : 用所有 SyncManager 中 nodes 的 ip, port 以 , 分隔, 保存在 unsyncStoreClient 的 SEEDS 中
* Node getLocalNode(short nodeId, short domainId) : 查找 SYSTEM_UNSYNC_STORE 的 LOCAL_NODE_IFACE 的网卡名 ip 地址对应的 hostName
* String getLocalHostname() : 根据 unsyncStoreClient 的 LOCAL_NODE_IFACE 指定的网卡名找到本机 对应的 ip 地址


###RPCService

开启两个线程组:

第一个用于同步消息的 SYNC_MESSAGE_POOL 个 ExecutorService, 从 syncQueue 中取出消息,

如果与 nodeId 处于连接状态:
1. 一直直到等待消息窗口中未发送消息小于 MAX_PENDING_MESSAGES
2. 将 bsm 发送给 nodeId 对应的连接
3. 返回 true

如果与 nodeId 处于未连接状态,返回 false

当负载低的时候, 线程可以重用之前的线程, 当负载高的时候, 线程的数量可以动态增加 ?


第二个用于开启一个接受消息的服务端和发送消息的客户端

ServerBootStrap 服务端, 监听 "node" 配置的地址

ClientBootstrap 客户端读配置与所有 NodeID 小于当前 SyncManager.getLocalNodeId()(为什么?) 的节点建立连接,
如果连接失败, 报错


作为客户端通信过程

channelOpen : 将 channel 加入 RPCService.cg
channelConnected : 发送 Hello 消息(根据配置文件决定是否进行认证)
channelDisconnected : 标记连接断开, 清除 connections, messageWindows 与 node 相关的信息
channelIdle: 发送 Echo 请求
messageReceived :

处理收到的 HELLO, ECHO_REQUEST,GET_REQUEST,GET_RESPONSE,PUT_REQUEST,PUT_RESPONSE,DELETE_REQUEST,
DELETE_RESPONSE, SYNC_VALUE_RESPONSE, SYNC_VALUE, SYNC_OFFER, FULL_SYNC_REQUEST, SYNC_REQUEST,
CURSOR_REQUEST, CURSOR_RESPONSE, REGISTER_REQUEST, REGISTER_RESPONSE, CLUSTER_JOIN_REQUEST,
CLUSTER_JOIN_RESPONSE, ERROR, ECHO_REPLY, 返回

作为服务端通信过程

channelOpen : 将 channel 加入 RPCService.cg
channelConnected : 发送 Hello 消息(根据配置文件决定是否进行认证), 将本地 NodeId, 认证信息发送给对端
channelDisconnected : 标记连接断开, 清除 connections, messageWindows 与 node 相关的信息
channelIdle: 发送 Echo 请求
messageReceived :

处理收到的 HELLO, ECHO_REQUEST,GET_REQUEST,GET_RESPONSE,PUT_REQUEST,PUT_RESPONSE,DELETE_REQUEST,
DELETE_RESPONSE, SYNC_VALUE_RESPONSE, SYNC_VALUE, SYNC_OFFER, FULL_SYNC_REQUEST, SYNC_REQUEST,
CURSOR_REQUEST, CURSOR_RESPONSE, REGISTER_REQUEST, REGISTER_RESPONSE, CLUSTER_JOIN_REQUEST,
CLUSTER_JOIN_RESPONSE, ERROR, ECHO_REPLY, 返回


###RPCService 认证过程

1. Node1 生成 16 byte 随机数 Chanallenge1, 设置 chanallenge, 发送 localNodeId, Chanallenge1 给 Node2
2. Node2 收到将收到的随机数 Chanallenge1 作为种子, 读取当前节点 keyStorePath, keyStorePassword 生成 key2, 设置 Response, 把 key2, 与 localNodeId 以 Hello 的消息应答给 Node1
3. Node1 收到 Node2 的应答, 以 Chanallenge1 为种子, 读取当前节点 keyStorePath, keyStorePassword 生成 key1, 比较 key1 与 key2,
如果相同, 则认为认证成功. 修改 Node1 连接状态为 AUTHENTICATED, 发送 Hello 消息.

* 如果是 RPCService, 并向 Node2 发送全量同步请求.
* 如果是 bootStrap, 将当前节点信息以集群加入请求(CLUSTER_JOIN_REQUEST)消息发送给 Node2

4. Node2 收到集群加入




1. Node2 生成 16 byte 随机数 Chanallenge2, 发送 Chanallenge2 给 Node1
2. Node1 收到将收到的随机数 Chanallenge2 作为种子, 读取当前节点 keyStorePath, keyStorePassword 生成 key1, 把 key1 应答给 Node2
3. Node2 收到 Node1 的应答, 以 Chanallenge2 为种子, 读取当前节点 keyStorePath, keyStorePassword 生成 key2, 比较 key1 与 key2,
如果相同, 则认为认证成功. 修改 Node2 连接状态为 AUTHENTICATED, 并向 Node1 发送全量同步请求

如果任意一端认证失败, 断开连接

###非认证过程(不建议使用)

1. Node1 将 localNodeId 封装进 Hello 消息, 发送给 Node2
2. Node2 什么也不做

###心跳连接

Node1 发送 ECHO_REQUEST 给 Node2

Node2 发送 ECHO_REPLY 给 Node1

###GET 操作

Node1 发送 GET_REQUEST 请求
Node2 解析 Node1 请求信息, 将 transactionId 加入应答头, key 对应的 values 加入应答消息体, 应答 Node1 GET_RESPONSE 消息
Node1 收到 GET_RESPONSE 消息

###PUT 操作

Node1 发送 PUT_REQUEST 请求
Node2 解析 Node1 请求信息, 将 key 对应的 values 保持在 store, 将 transactionId 加入应答消息头, 应答 Node1 PUT_RESPONSE 消息
Node1 收到 PUT_RESPONSE 消息

###DELETE 操作

Node1 发送 DELETE_REQUEST 请求
Node2 解析 Node1 请求信息, 将 key 对应的 values 设置为 null, 将 transactionId 加入应答消息头, 应答 Node1 DELETE_RESPONSE 消息
Node1 收到 DELETE_RESPONSE 消息

注: 目前 DELETE_RESPONSE 都是成功的

###SYN 操作

把自己同步给对方

Node1 发送 SYNC_VALUE 请求
Node2 解析 Node1 请求信息, 调用 syncManager.writeSyncValue, 应答 Node1 SYNC_VALUE_RESPONSE 消息
Node1 收到 SYNC_VALUE_RESPONSE 消息, 将流控窗口大小减 1

###SYNC_OFFER 操作

要求对方同步自己, 在 antientropy 中调用

Node1 发送 SYNC_OFFER 请求
Node2 解析 Node1 请求信息, 如果请求中, key 对应 value 的版本比本地的新, 就将其加入应答体, 应答 Node1 SYNC_REQUEST 消息
Node1 解析 Node2 的 SYNC_REQUEST, 将 key 对应的 value 封装成 SYNC_VALUE消息加入 rpcService.syncQueue
Node2 解析 Node1 请求信息, 调用 syncManager.writeSyncValue, 应答 Node1 SYNC_VALUE_RESPONSE 消息
Node1 收到 SYNC_VALUE_RESPONSE 消息, 将流控窗口大小减 1

###FULL_SYNC_REQUEST

Node1 发送 FULL_SYNC_REQUEST 请求
Node2 收到请求后, 随机选择一个节点, 将当前节点的数据与对应的节点同步

###CURSOR

Node1 发送 CURSOR_REQUEST 请求
Node2 解析请求, 创建对应的 Cursor(如果 cursor 没有), 如果不是 closeCursor 请求, 最多取 50 条数据, 应答 CURSOR_RESPONSE 给 Node1
Node1 收到 CURSOR_RESPONSE 应答后, 调用 syncManager.dispatchReply

###Register Store

Node1 发送 REGISTER_REQUEST 请求
Node2 解析请求, SyncManager.registerStore 注册对应的 store, 应答 REGISTER_RESPONSE 给 Node1
Node1 收到 REGISTER_RESPONSE 应答后, 调用 syncManager.dispatchReply

###Cluster Join

BootstrapChannelHandler 

Node1 发送 CLUSTER_JOIN_REQUEST 请求, (在 bootstrap 连接建立完成之后)
Node2 解析请求中 node 信息(如果 node 的 ID 为 null, 生成节点 id)加入当前配置, 当前节点的所有 Node 信息以 CLUSTER_JOIN_RESPONSE 发送给 Node1.
Node1 收到 CLUSTER_JOIN_RESPONSE 应答后, 将 Node2 的所有节点信息写入 SYSTEM_NODE_STORE 表, 如果 Node1 第一步发送没有设置节点 id, 将 nodeID 加入 LOCAL_NODE_ID 表


int MAX_PENDING_MESSAGES = 500 : 流控的消息窗口大小
static final int SEND_BUFFER_SIZE = 4 * 1024 * 1024 : 发送消息的 Socket buffer
static final int CONNECT_TIMEOUT = 500 : 连接超时
ConcurrentHashMap<Short, MessageWindow> messageWindows : 保存节点与消息的窗口的映射关系
HashMap<Short, NodeConnection> connections : 保持节点与连接状态的关系


int getTransactionId() : 获取事务 ID
void disconnectNode(short nodeId) : 与 nodeId 断开连接
boolean isFullyConnected() : 是否已经与所有节点建立连接
boolean isConnected(short nodeId) : 与 nodeId 是否已经建立连接
MessageWindow getMW(short nodeId) : 获取 nodeId 对应的消息窗口, 如果不存在, 创建之. ()
void startServer(ChannelPipelineFactory pipelineFactory) : 开启服务端, 监听客户端连接
void nodeConnected(short nodeId, Channel channel) : 连接建立的时候, 更新与 nodeId 的连接状态为 CONNECTED
void startClients(ChannelPipelineFactory pipelineFactory) : 配置客户端连接参数, 读取配置, 与对应节点建立连接.
void doNodeConnect(Node n) : 如果 n.getNodeId() < SyncManager.getLocalNodeId() , 如果与节点 n 已经建立连接, 返回, 否则, 发送建立连接请求, 将连接信息保持在 connections 中
void startClientConnections() : 读取配置, 与对应节点建立连接.
void messageAcked(MessageType type, Short nodeId) : 减少流控窗口大小, 如果窗口阈值低于 MAX_PENDING_MESSAGES, 通知发送者继续发送
boolean waitForMessageWindow(MessageType type, short nodeId, long maxWait)

为每个节点建立一个流控窗口, 节点和流控窗口保存在 messageWindows 中.
waitForMessageWindow 与 messageAcked 相对应. 其中, waitForMessageWindow 让
流控窗口大小每次加 1, 当流控窗口大于 MAX_PENDING_MESSAGES. 就阻塞, 等待
messageAcked 的通知; messageAcked 每次让流控窗口大小每次减一, 当
流控窗口小于 MAX_PENDING_MESSAGES 就通知 waitForMessageWindow 可以继续
增加了. 当然 waitForMessageWindow 支持超时.

maxWait = 0, 表示一直直到等待消息窗口中未发送消息小于 MAX_PENDING_MESSAGES
如果 maxWait 不等于 0, 超时返回 false;

* boolean writeToNode(Short nodeId, SyncMessage bsm)

如果与 nodeId 处于连接状态:
一直直到等待流控窗口中未发送消息小于 MAX_PENDING_MESSAGES
将 bsm 发送给 nodeId 对应的连接
返回 true

如果与 nodeId 处于未连接状态,返回 false

###ConnectTask

当前节点作为客户端与其他节点建立连接的线程

与节点ID 小于当前节点 ID 的节点建立连接, 将连接信息保持在 connections 中

其中

ConnectCFListener : 检查连接完成后, 连接是否完成
void nodeConnected(short nodeId, Channel channel) : 标志连接已经建立
doNodeConnect(Node n) : 与具体的节点 n 建立连接
startClientConnections() : 调用 doNodeConnect 与所有节点建立建立连接.
NodeConnection : 维护建立连接状态信息

节点状态

    enum NodeConnectionState {
        NONE,
        PENDING,
        CONNECTED
    }


###MessageWindow

流控窗口

###NodeMessage

维护节点信息

###SyncMessageWorker

同步消息到远程的线程. 从 syncQueue 中取出一条消息, 发送给远程节点










###AbstractRPCChannelHandler

连接处理器

一旦建立连接, 两个节点相互发送发送 Hello 消息.

如果收到 Hello 消息, 根据 request.getAuthChallengeResponse() 生成认证应答.

* void channelConnected(ChannelHandlerContext ctx, ChannelStateEvent e)

 发送 Hello 消息(根据配置文件决定是否进行认证)

* void channelIdle(ChannelHandlerContext ctx, IdleStateEvent e)

当在一定时间没有读或写, 就发送 Echo 消息.

* void messageReceived(ChannelHandlerContext ctx,

接受消息, 并调用 handleSyncMessage 处理该接受到的消息

* void handleSyncMessage(SyncMessage bsm, Channel channel)

如果接收的是 Hello 消息, 开始握手
如果接受到的是 Echo 请求, 发送 Echo 应答
如果是认证信息, 就处理认证

* void handleSMAuthenticated(SyncMessage bsm, Channel channel) :
* String generateChallenge() : 生成一个 16 byte 的随机字节, 之后进行 Base64 编码
* abstract byte[] getSharedSecret() : 由 keyStorePath, keyStorePassword 进行 JCEKS 加密后生成 byte[] 密钥
* String generateResponse(String challenge) : 对生成应答加密应答字符串
* void handshake(HelloMessage request, Channel channel)


###RPCChannelHandler

继承 AbstractRPCChannelHandler


* void channelOpen(ChannelHandlerContext ctx, ChannelStateEvent e) : 将 cts.getChannel 加入 ChannelGroup
* void channelDisconnected(ChannelHandlerContext ctx, ChannelStateEvent e) : 断开连接
* void messageReceived(ChannelHandlerContext ctx, MessageEvent e) : 调用父类的 messageReceived
* void handleHello(HelloMessage hello, Channel channel) : 接受到 Hello 消息, 发送全同步请求
* void handleGetRequest(GetRequestMessage request, Channel channel) : 解析 request, 将 key 对应的 value 发送给客户端
* void handlePutRequest(PutRequestMessage request, Channel channel) : 解析 request, 更新到本地数据库后, 发送应答
* void handleDeleteRequest(DeleteRequestMessage request, Channel channel) : 解析 request, 递增版本号, 设置 key 对应的 value 为 null
* void handleSyncValue(SyncValueMessage request, Channel channel) : TODO 调用 syncManager.writeSyncValue 同步请求中的值.
* void handleSyncValueResponse(SyncValueResponseMessage message, Channel channel) : 收到服务端应答, 减少当前发送流控窗口
* void handleSyncOffer(SyncOfferMessage request, Channel channel) : 接受到 Syn Offer 消息, 发送 Sync 请求
* void handleSyncRequest(SyncRequestMessage request, Channel channel) : 收到服务端应答, 减少当前发送流控窗口, 将请求的 key 的对应的值加入应答消息, 放入 RPCService.syncQueue
注: 如果直到主动发送 Sync 请求还需要减少 Syn Offer 的滑动窗口吗?  还是规定只能通过 Sync Offer 发送 Sync 请求?
* void handleFullSyncRequest(FullSyncRequestMessage request, Channel channel) :
* void handleCursorRequest(CursorRequestMessage request, Channel channel) :　解析 request, 根据请求的 Cursor, 最多遍历 50 个元素加入应答消息
* void handleRegisterRequest(RegisterRequestMessage request, Channel channel) :　解析 request, 将注册对应的请求模块
* void handleClusterJoinRequest(ClusterJoinRequestMessage request, Channel channel) : 为新加节点分配随机 NodeId, 并将当前节点的所有节点信息发送给新加节点(node 不会为 null ?)
* Short getLocalNodeId() : syncManager.getLocalNodeId()
* Short getRemoteNodeId() : 每个 channel 都对应一个 RPCChannelHandler ?
* int getTransactionId() : 生成一个事务 id
* AuthScheme getAuthScheme() : 获取认证方式 syncManager.getClusterConfig().getAuthScheme()
* byte[] getSharedSecret() : 根据配置文件 keyStorePath, keyStorePassword 生成唯一 随机 byte
* void startAntientropy() : 开始一个反熵同步, 新开一个线程, 调用 syncManager.antientropy(remoteNode);












###JackSonStore

实现 IStore 并作为 DefaultStoreClient 的真实后端存储

将 key 转为 ByteArray, value 转为 byte[], 之后委托实现 SynchronizingStorageEngine(实现 IStore<ByteArray, byte[]>) 存储数据


##StoreRegistry

注册存储引擎

* SyncManager syncManager : SyncManager 的实例
* String dbPath : 配置文件 dbPath
* ConnectionPoolDataSource persistentDataSource : null
* HashMap<String,SynchronizingStorageEngine> localStores : 保存 storeName : SynchronizingStorageEngine 的映射关系
* InMemoryStorageEngine<HintKey,byte[]> hints : 每次调用 queueHint, 将 HintKey(storeName, key) : value 加入. 每次调用 takeHints 将 HintKey(storeName, key) : value 删除
* ArrayDeque<HintKey> hintQueue : 每次调用 queueHint 将 HintKey(storeName, key) 加入, 每次调用 takeHints 将 HintKey(storeName, key) 删除

* Lock hintLock = new ReentrantLock()
* Condition hintsAvailable = hintLock.newCondition()

* StoreRegistry(SyncManager syncManager, String dbPath) : 初始化 SyncManager, dbPath, hints
* SynchronizingStorageEngine get(String storeName)
* SynchronizingStorageEngine register(String storeName, Scope scope, boolean persistent) : 

    如果 persistent 为 true, 增加 localStores 为 storeName: SynchronizingStorageEngine(JavaDBStorageEngine(store), scope)
    如果 persistent 为 false,　增加 localStores 为 storeName: SynchronizingStorageEngine(InMemoryStorageEngine(storeName), scope)

* Collection<SynchronizingStorageEngine> values() : 所有的存储引擎列表 localStores.values()
* void queueHint(String storeName, ByteArray key, Versioned<byte[]> value) : storeName, key 增加到 hints 和 hintQueue 中, 并通知 hintQueue 队列不为空.
* void takeHints(Collection<Hint> c, int maxElements) : 从队列 hintQueue 和 hints 中取出元素添加到 c 中, 如果 hintQueue 为空, 阻塞, 最多取 maxElements 个. 这里增加 maxElements 是防止取阻塞存.
* void shutdown() : 清除 hints, hintQueue

###HintKey

* final String storeName
* final ByteArray key
* final short nodeId
* String getStoreName()
* ByteArray getKey()
* short getNodeId()

###Hint

* HintKey hintKey
* List<Versioned<byte[]>> values
* Hint(HintKey hintKey, List<Versioned<byte[]>> values)
* HintKey getHintKey()
* List<Versioned<byte[]>> getValues() {

###IStore

* List<Versioned<V>> get(K key) :
* IClosableIterator<Entry<K,List<Versioned<V>>>> entries(): 返回的迭代器非线程安全
* void put(K key, Versioned<V> value)
* List<IVersion> getVersions(K key)
* String getName();
* void close()


###IStorageEngine

继承 IStore 接口

* IClosableIterator<Entry<K,List<Versioned<V>>>> entries();
* IClosableIterator<K> keys() : 返回的迭代器非线程安全
* void truncate() throws SyncException;
* boolean writeSyncValue(K key, Iterable<Versioned<V>> values);
* void cleanupTask() throws SyncException;
* boolean isPersistent();
* void setTombstoneInterval(int interval)

###ListenerStorageEngine

实现 IStorageEngine<ByteArray, byte[]>, 将存储过程和通知监听者解耦. 实现存储过程的类, 实现 IStorageEngine 接口

个人觉得这里完全没有必要, 可以将此类与 SynchronizingStorageEngine 合并

* List<MappingStoreListener> listeners : ArrayList<MappingStoreListener>();
* IStorageEngine<ByteArray, byte[]> localStorage : 真正实现存储过程
* IDebugCounterService debugCounter : 调试计数器

* List<Versioned<byte[]>> get(ByteArray key) : localStores.get(key)
* IClosableIterator<Entry<ByteArray,List<Versioned<byte[]>>>> entries() : localStores.entries()
* void put(ByteArray key, Versioned<byte[]> value) : localStores.put(key,value), 更新计数器, 通知本地订阅者 key 已经修改
* IClosableIterator<ByteArray> keys() : localStores.keys()
* void truncate() : localStores.truncate()
* String getName() : localStores.getName()
* void close() : localStores.close()
* List<IVersion> getVersions(ByteArray key) : localStores.getVersions(key)
* boolean writeSyncValue(ByteArray key, Iterable<Versioned<byte[]>> values) : 如果 values 中有一个 (key,value) put 成功, 通知远程订阅者 key 已经修改
* void cleanupTask() : localStores.cleanupTask()
* boolean isPersistent() : localStores.isPersistent()
* void setTombstoneInterval(int interval) : localStores.setTombstoneInterval()
* void addListener(MappingStoreListener listener) : listeners.add(listener)
* void notifyListeners(ByteArray key, UpdateType type) : 遍历所有 listener, 调用 listener.notify(key, type)
* void notifyListeners(Iterator<ByteArray> keys, UpdateType type)
* void updateCounter(IDebugCounter counter)

注意 put 与 writeSyncValue 的区别

###MappingStoreListener

将 IStoreListener 与类型解耦


###UpdateType

    public enum UpdateType {
        /**
         * An update that originated from a write to the local store
         */
        LOCAL,
        /**
         * An update that originated from a value synchronized from a remote
         * node.  Note that it is still possible that this includes only
         * information that originated from the current node.
         */
        REMOTE
    };

###SynchronizingStorageEngine

继承 ListenerStorageEngine, 增加 syncManager 和 Scope.

SyncManager syncManager :
Scope scope :

void put(ByteArray key, Versioned<byte[]> value) : 将数据存入后, 将数据加入 hintQueue
void Scope getScope()

###Scope

    enum Scope {
        /**
         * Stores with this scope will be replicated to all nodes in the 
         * cluster
         */
        GLOBAL,
        /**
         * Stores with this scope will be replicated only to other nodes
         * within the writing node's local domain
         */
        LOCAL,
        /**
         * Stores with this scope will not be replicated and will be stored
         * locally only.
         */
        UNSYNCHRONIZED
    }

###InMemoryStorageEngine

实现 IStorageEngine<K, V> 接口, 由 JackSonStore 负责将其转换为 key 为 ByteArray, value 为 byte[]


* void close() : 什么也不做
* List<IVersion> getVersions(K key)
* List<Versioned<V>> get(K key)
* void put(K key, Versioned<V> value)
* boolean doput(K key, Versioned<V> value) : 将 value 与已经存在的 values 比较, 如果版本比 value 旧, 删除之, 如果比 value 新, 返回 false; 最后将 value 加入 map
* IClosableIterator<Entry<K,List<Versioned<V>>>> entries() : map.entries()
* IClosableIterator<K> keys() : map.keys()
* void truncate() : map.clear()
* String getName() : 返回 storeName
* boolean writeSyncValue(K key, Iterable<Versioned<V>> values) : values 中有一个 put 成功, 返回 true;
* void cleanupTask() : 遍历 map 的所有元素, 找到过期的 key, 删除之. 删除的条件是该 key 的 value 中的 timestamp 超过 tombstoneDeletion 的版本中, 如果有一个版本的比其他没有超过 timestamp 的版本都新, 就删除该元素
* boolean isPersistent() : 返回 false
* void setTombstoneInterval(int interval) : 设置 key 过期时间
* int size() : map.size()
* List<Versioned<V>> remove(K key) : 这里删除 key 有类似于自旋锁的意思. 但如果在 remove 之时, 有并发 put, 是否存在问题?
* boolean containsKey(K key) : 是否存在对应的 key


###StoreUtils

    public static <V> boolean canDelete(List<Versioned<V>> items, long tombstoneDeletion) : 决定是否删除 key. 如果存在待删的版本, 比其他不应该删的版本都新, 返回 true.








##SyncTorture

测试同步的 Syn 客户端同步速度

##AbstractSyncManager

abstract void shutdown();
abstract void addListener(String storeName, MappingStoreListener listener)
abstract short getLocalNodeId();
abstract IStore<ByteArray,byte[]> getStore(String storeName)

<K, V> IStoreClient<K, V> getStoreClient(String storeName, Class<K> keyClass,
                           TypeReference<K> keyType, Class<V> valueClass,
                           TypeReference<V> valueType, IInconsistencyResolver<Versioned<V>> resolver)
<K, V> IStoreClient<K, V> getStoreClient(String storeName,
                       Class<K> keyClass,
                       Class<V> valueClass,
                       IInconsistencyResolver<Versioned<V>> resolver)

<K, V> IStoreClient<K, V> getStoreClient(String storeName,
                       TypeReference<K> keyType,
                       TypeReference<V> valueType,
                       IInconsistencyResolver<Versioned<V>> resolver)
<K, V>IStoreClient<K, V> getStoreClient(String storeName,
                       TypeReference<K> keyType,
                       TypeReference<V> valueType)
<K, V> IStoreClient<K, V>  getStoreClient(String storeName,
                       Class<K> keyClass,
                       Class<V> valueClass)


###DefaultStoreClient<K, V> extends AbstractStoreClient<K, V>

* IStore<K, V> delegate;
* IInconsistencyResolver<Versioned<V>> resolver: ChainedResolver<Versioned<V>>(vcir, new TimeBasedInconsistencyResolver<V>());
* AbstractSyncManager syncManager;
* Class<K> keyClass;
* TypeReference<K> keyType;

DefaultStoreClient(IStore<K, V> delegate, IInconsistencyResolver<Versioned<V>> resolver,
            AbstractSyncManager syncManager, Class<K> keyClass, TypeReference<K> keyType)

Versioned<V> get(K key, Versioned<V> defaultValue) : delegate.get(key) 解决冲突后的 Versioned 或者defaultValue
IClosableIterator<Entry<K, Versioned<V>>> entries() : delegate.entries() 的迭代器
IVersion put(K key, Versioned<V> versioned) : versioned 的 version 加 1, timestamp 为当前时间, delegate.put(key, versioned)
void addStoreListener(IStoreListener<K> listener) : delegate.getName(), MappingStoreListener(keyType, keyClass, IStoreListener)
List<IVersion> getVersions(K key) : delegate.getVersion(key)
Versioned<V> defaultValue(Versioned<V> defaultValue) : 返回 defaultValue
Versioned<V> handleGet(K key, Versioned<V> defaultValue, List<Versioned<V>> raw) : raw 解决冲突后的 Versioned 或 defaultValue
Versioned<V> getItemOrThrow(K key, Versioned<V> defaultValue, List<Versioned<V>> items) : 返回 items.get(0) 或 defaultValue 或抛异常

###Version

long serialVersionUID = 1;

volatile VectorClock version;
volatile T value;

* Versioned(T object, IVersion version)
* Versioned(T object)
* IVersion getVersion()
* void increment(int nodeId, long time) : version.incremented(nodeId, time)
* T getValue()
* void setValue(T object)
* boolean deepEquals(Object o1, Object o2)
* Versioned<T> cloneVersioned()
* <S> Versioned<S> value(S s)
* <S> Versioned<S> value(S s, IVersion v)
* <S> Versioned<S> emptyVersioned()

###HappenedBeforeComparator<S> implements Comparator<Versioned<S>>

    int compare(Versioned<S> v1, Versioned<S> v2)

###IVersion

接口

Occurred compare(IVersion v);

###VectorClock implements IVersion, Serializable, Cloneable

List<ClockEntry> versions;
long timestamp;
int MAX_NUMBER_OF_VERSIONS = Short.MAX_VALUE;

VectorClock() {
VectorClock(long timestamp)
VectorClock(List<ClockEntry> versions, long timestamp)
VectorClock incremented(int nodeId, long time) : 如果 versions 中没有 nodeId, 增加之, 如果有, ClockEntry 的 version 加 1, 更新 timestamp
VectorClock clone() {
long getMaxVersion() : versions 中 ClockEntry 的 version 的最大值
VectorClock merge(VectorClock clock) : 将 this.versions 和 clock 合并, version 取较大值
Occurred compare(IVersion v)
Occurred compare(VectorClock v1, VectorClock v2) : 依次比较versions 的 nodeId, 如果 nodeId 数量一样, 比较 version, versions 数量多的值大
List<ClockEntry> getEntries()

###ClockEntry

short nodeId;
long version;

ClockEntry(short nodeId, long version)
short getNodeId()
long getVersion()
ClockEntry incremented() : version 加 1

##RemoteSyncManager





###RemoteIterator implements IClosableIterator<Entry<ByteArray, List<Versioned<byte[]>>>>

发送 CursorRequestMessage 消息, 并获取应答迭代器


##RemoteSyncManager

作为客户端根据配置连接到远程主机

发送请求包含一个滑动窗口, 大小为 MAX_PENDING_REQUESTS,

与 hostname:port 建立连接,
通过 sendRequest() 将 SyncMessage 发送给对端(如果当前未完成数量超过1000,就阻塞), 超时为 5 s
通过 doRegisterStore() 发送注册请求消息
通过 channelDisconnected() 遍历强制断开所有链接

###配置

* host
* port
* keyStorePath
* keyStorePassword

ConcurrentHashMap<Integer, RemoteSyncFuture> futureMap : 保存 请求事务 id 与远程应答, 最大为 MAX_PENDING_REQUESTS
Object futureNotify : 锁

void ensureConnected() : 确保已经建立连接
boolean connect(String hostname, int port) : 建立连接
Future<SyncReply> sendRequest(int xid, SyncMessage request) : 发送一个请求
void dispatchReply(int xid, SyncReply reply) : 从 futureMap 中删除 xid 对应的 future, 并设置 应答为 reply
void channelDisconnected(SyncException why) : 并将 futureMap 中应答为 null
void doRegisterStore(String storeName, Scope scope, boolean b) : 发送注册 Store 的请求到远程节点
IStore<ByteArray, byte[]> getStore(String storeName)


* ChannelGroup cg = new DefaultChannelGroup("Internal RPC");
* RemoteSyncPipelineFactory pipelineFactory : 见 netty
* ClientBootstrap clientBootstrap;
* ExecutorService bossExecutor : 见 netty
* ExecutorService workerExecutor: 见 netty
* volatile Channel channel:
* volatile int connectionGeneration = 0 : 记录所有建立连接的个数
* AtomicInteger transactionId = new AtomicInteger();
* Object readyNotify = new Object();
* volatile boolean ready = false;
* volatile boolean shutdown = false;
* Short remoteNodeId;
* String hostname = "localhost" : 从配置中, 默认 localhost
* int port = 6642 : 从配置中来, 默认 6642
* AuthScheme authScheme : 从配置中来, 默认 NO_AUTH
* String keyStorePath : 从配置中来, 默认 NO_AUTH
* String keyStorePassword : 从配置中来, 默认 NO_AUTH
* ConcurrentHashMap<Integer, RemoteSyncFuture> futureMap : 记录所有等待应答的标记
* Object futureNotify = new Object();
* static int MAX_PENDING_REQUESTS = 1000;

* void addListener(String storeName, MappingStoreListener listener) : 未实现
* IStore<ByteArray, byte[]> getStore(String storeName) : new RemoteStore(storeName, this)
* short getLocalNodeId() : 返回  remoteNodeId
* void init(FloodlightModuleContext context) : 读取配置, 初始化
* void startUp(FloodlightModuleContext context) : 初始化 clientBootStrap, pipelineFactory
* boolean connect(String hostname, int port) : 与 hostnam:port 建立连接, 直到 ready = true, 返回true
* void doRegisterStore(String storeName, Scope scope, boolean b)
* Future<SyncReply> sendRequest(int xid, SyncMessage request) : 将 request 发送到对端服务器
* void channelDisconnected(SyncException why) : 遍历 futureMap 强制断开所有链接
* int getTransactionId()
* void shutdown()
* short getLocalNodeId()
* IStore<ByteArray, byte[]> getStore(String storeName)
* void registerStore(String storeName, Scope scope)
* void registerPersistentStore(String storeName, Scope scope)
* void addListener(String storeName, MappingStoreListener listener)

###RemoteSyncFuture

实现接口 Future<SyncReply>, 主要是对 SyncReply 的一个异步包装

* final int xid;
* final int connectionGeneration;
* volatile SyncReply reply = null;
* Object notify = new Object();

* RemoteSyncFuture(int xid, int connectionGeneration)
* SyncReply get(long timeout, TimeUnit unit)
* SyncReply get()
* boolean cancel(boolean mayInterruptIfRunning)
* void setReply(SyncReply reply)
* int getConnectionGeneration()
* int getXid()
* boolean isDone()
* boolean isCancelled()

###RemoteSyncChannelHandler

* void channelOpen(ChannelHandlerContext ctx, ChannelStateEvent e)
* void channelDisconnected(ChannelHandlerContext ctx, ChannelStateEvent e)
* void handleHello(HelloMessage hello, Channel channel)
* void handleGetResponse(GetResponseMessage response, Channel channel): 解析 response， 删除 futureMap 中对应的. 并设置 reply
* void handlePutResponse(PutResponseMessage response, Channel channel) : 解析 response,设置应答成功
* void handleDeleteResponse(DeleteResponseMessage response, Channel channel) : 解析 response, 设置删除是否成功
* void handleCursorResponse(CursorResponseMessage response, Channel channel) : 解析 response, 这是游标
* void handleRegisterResponse(RegisterResponseMessage response, Channel channel) : 处理 response, 设置注册应答成功
* void handleError(ErrorMessage error, Channel channel)
* Short getRemoteNodeId()
* Short getLocalNodeId()
* String getLocalNodeIdString()
* int getTransactionId()
* AuthScheme getAuthScheme()
* byte[] getSharedSecret()

###SyncReply

* List<KeyedValues> keyedValues;
* List<Versioned<byte[]>> values;
* boolean success;
* SyncException error;
* int intValue;

###RemoteStore

实现 IStore<ByteArray, byte[]> , 辅助 RemoteSyncManager 类发送各种消息

* String storeName;
* RemoteSyncManager syncManager;

* List<Versioned<byte[]>> get(ByteArray key) : 构造并发送 GetRequestMessage, 返回应答
* IClosableIterator<Entry<ByteArray, List<Versioned<byte[]>>>> entries()
* void put(ByteArray key, Versioned<byte[]> value) : 构造并发送 PutRequestMessage
* List<IVersion> getVersions(ByteArray key) : 获取 key 的所有版本号
* String getName()
* SyncReply getReply(int xid, SyncMessage bsm) : 调用 RemoteSyncManager.sendRequest()


###Bootstrap

ChannelGroup cg;
AtomicInteger transactionId = new AtomicInteger();
SyncManager syncManager;
final AuthScheme authScheme;
final String keyStorePath;
final String keyStorePassword;

ExecutorService bossExecutor = null;
ExecutorService workerExecutor = null;
ClientBootstrap bootstrap = null;
BootstrapPipelineFactory pipelineFactory;

Node localNode;
volatile boolean succeeded = false;

void init() throws SyncException {
boolean bootstrap(HostAndPort seed, Node localNode) : 与 seed.getHost(), seed.getPort() 建立连接, 将当前节点加入的集群, 同步远端的集群当当前节点的 SYSTEM_NODE_STORE
void shutdown() : 关闭资源

###BootstrapChannelHandler

继承 AbstractRPCChannelHandler

连接一旦建立就开始认证(根据配置文件决定是否需要), 认证完成之后: 

1. Node1 发送 CLUSTER_JOIN_REQUEST 请求, (在 bootstrap 连接建立完成之后)
2. Node2 解析请求中 node 信息(如果 node 的 ID 为 null, 生成节点 id)加入当前配置, 当前节点的所有 Node 信息以 CLUSTER_JOIN_RESPONSE 发送给 Node1.
3. Node1 收到 CLUSTER_JOIN_RESPONSE 应答后, 将 Node2 的所有节点信息写入 SYSTEM_NODE_STORE 表, 如果 Node1 第一步发送没有设置节点 id, 将 nodeID 加入 LOCAL_NODE_ID 表, node1 与 node2 断开连接

* Bootstrap bootstrap;
* Short remoteNodeId;

* void channelOpen(ChannelHandlerContext ctx, ChannelStateEvent e) : 将 channel 加入 bootstrap.cg
* void handleHello(HelloMessage hello, Channel channel) : 构造 CLUSTER_JOIN_REQUEST 发送给连接的节点.
* void handleClusterJoinResponse(ClusterJoinResponseMessage response, Channel channel) :收到 CLUSTER_JOIN_RESPONSE 应答后, 将 Node2 的所有节点信息写入 SYSTEM_NODE_STORE 表, 如果 Node1 第一步发送没有设置节点 id, 将 nodeID 加入 LOCAL_NODE_ID 表, node1 与 node2 断开连接

* int getTransactionId() : 生成唯一事务 ID
* Short getRemoteNodeId() : 远程节点的 ID
* Short getLocalNodeId() : 返回 null
* AuthScheme getAuthScheme() : 返回认证方式
* byte[] getSharedSecret() : 根据 keyStorePath, keyStorePassword 生成 16 字节随机数

###BootstrapTask

配置更新线程

从读取 unsyncStoreClient 的 LOCAL_NODE_ID 为本节点 ID
从读取 unsyncStoreClient 的 SEEDS 为 seedStr

如果 seedStr 为 null, 返回.
如果 seedStr 为 "":

    如果 SYSTEM_UNSYNC_STORE 中 LOCAL_NODE_ID 不为 null,且其保存在 SYSTEM_NODE_STORE 中, localNodeId 与 SYSTEM_UNSYNC_STORE 中的 LOCAL_NODE_HOSTNAME, LOCAL_NODE_PORT 组成 Node 加入 SYSTEM_NODE_STORE
    如果 SYSTEM_UNSYNC_STORE 中 LOCAL_NODE_ID 不为 null,但不在 SYSTEM_NODE_STORE 中, localNodeId 与 SYSTEM_UNSYNC_STORE 中的 LOCAL_NODE_HOSTNAME, LOCAL_NODE_PORT  加入 SYSTEM_NODE_STORE
    如果 SYSTEM_UNSYNC_STORE 中 LOCAL_NODE_ID 为 null, 随机生成 NodeID 与 SYSTEM_UNSYNC_STORE 中的 LOCAL_NODE_HOSTNAME, LOCAL_NODE_PORT  加入 SYSTEM_NODE_STORE

否则 以 "," 分隔 seedStr 解析出 host, port, 调用 bootstrap 连接到 host, port, 将本地 nodeID 加入 host, port 的 SYSTEM_NODE_STORE 表中.

* Node setupLocalNode(Node localNode, Short localNodeId, boolean firstNode) : 设置 nodeId, domainId, 以 localNodeId 最优先, 之后是 localNode, 如果 firstNode 为 true, nodeId 为随机数

###Node

* String hostname;
* int port;
* short nodeId;
* short domainId;
