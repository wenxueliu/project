
```
	at net.floodlightcontroller.core.internal.OFSwitch.getConnection(OFSwitch.java:813)
	at net.floodlightcontroller.core.internal.OFSwitch.getConnection(OFSwitch.java:820)
	at net.floodlightcontroller.core.internal.OFSwitch.write(OFSwitch.java:860)
	at net.floodlightcontroller.core.internal.OFSwitch.write(OFSwitch.java:850)
	at net.floodlightcontroller.core.internal.OFSwitch.write(OFSwitch.java:837)
	at net.floodlightcontroller.util.OFMessageDamper.write(OFMessageDamper.java:127)
	at net.floodlightcontroller.loadbalancer.LoadBalancer.pushPacket(LoadBalancer.java:1159)
	at net.floodlightcontroller.loadbalancer.LoadBalancer.processPacketIn(LoadBalancer.java:579)
	at net.floodlightcontroller.loadbalancer.LoadBalancer.receive(LoadBalancer.java:400)
	at net.floodlightcontroller.core.internal.Controller.handleMessage(Controller.java:477)
	at net.floodlightcontroller.core.internal.OFSwitchManager.handleMessage(OFSwitchManager.java:494)
	at net.floodlightcontroller.core.internal.OFSwitchHandshakeHandler.dispatchMessage(OFSwitchHandshakeHandler.java:1711)
	at net.floodlightcontroller.core.internal.OFSwitchHandshakeHandler.access$2200(OFSwitchHandshakeHandler.java:92)
	at net.floodlightcontroller.core.internal.OFSwitchHandshakeHandler$MasterState.processOFPacketIn(OFSwitchHandshakeHandler.java:1475)
	at net.floodlightcontroller.core.internal.OFSwitchHandshakeHandler$OFSwitchHandshakeState.processOFMessage(OFSwitchHandshakeHandler.java:867)
	at net.floodlightcontroller.core.internal.OFSwitchHandshakeHandler.processOFMessage(OFSwitchHandshakeHandler.java:1749)
	at net.floodlightcontroller.core.internal.OFSwitchHandshakeHandler.messageReceived(OFSwitchHandshakeHandler.java:1924)
	at net.floodlightcontroller.core.internal.OFConnection.messageReceived(OFConnection.java:398)
	at net.floodlightcontroller.core.internal.OFChannelHandler.sendMessageToConnection(OFChannelHandler.java:585)
	at net.floodlightcontroller.core.internal.OFChannelHandler.access$800(OFChannelHandler.java:59)
	at net.floodlightcontroller.core.internal.OFChannelHandler$OFChannelState.processOFMessage(OFChannelHandler.java:286)
	at net.floodlightcontroller.core.internal.OFChannelHandler.channelRead0(OFChannelHandler.java:709)
	at net.floodlightcontroller.core.internal.OFChannelHandler.channelRead0(OFChannelHandler.java:59)
	at io.netty.channel.SimpleChannelInboundHandler.channelRead(SimpleChannelInboundHandler.java:105)
	at io.netty.channel.AbstractChannelHandlerContext.invokeChannelRead(AbstractChannelHandlerContext.java:308)
	at io.netty.channel.AbstractChannelHandlerContext.fireChannelRead(AbstractChannelHandlerContext.java:294)
	at io.netty.channel.ChannelInboundHandlerAdapter.channelRead(ChannelInboundHandlerAdapter.java:86)
	at io.netty.channel.AbstractChannelHandlerContext.invokeChannelRead(AbstractChannelHandlerContext.java:308)
	at io.netty.channel.AbstractChannelHandlerContext.fireChannelRead(AbstractChannelHandlerContext.java:294)
	at io.netty.handler.timeout.ReadTimeoutHandler.channelRead(ReadTimeoutHandler.java:152)
	at io.netty.channel.AbstractChannelHandlerContext.invokeChannelRead(AbstractChannelHandlerContext.java:308)
	at io.netty.channel.AbstractChannelHandlerContext.fireChannelRead(AbstractChannelHandlerContext.java:294)
	at io.netty.handler.timeout.IdleStateHandler.channelRead(IdleStateHandler.java:266)
	at io.netty.channel.AbstractChannelHandlerContext.invokeChannelRead(AbstractChannelHandlerContext.java:308)
	at io.netty.channel.AbstractChannelHandlerContext.fireChannelRead(AbstractChannelHandlerContext.java:294)
	at io.netty.handler.codec.ByteToMessageDecoder.channelRead(ByteToMessageDecoder.java:244)
	at io.netty.channel.AbstractChannelHandlerContext.invokeChannelRead(AbstractChannelHandlerContext.java:308)
	at io.netty.channel.AbstractChannelHandlerContext.fireChannelRead(AbstractChannelHandlerContext.java:294)
	at io.netty.channel.DefaultChannelPipeline.fireChannelRead(DefaultChannelPipeline.java:846)
	at io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe.read(AbstractNioByteChannel.java:131)
	at io.netty.channel.nio.NioEventLoop.processSelectedKey(NioEventLoop.java:511)
	at io.netty.channel.nio.NioEventLoop.processSelectedKeysOptimized(NioEventLoop.java:468)
	at io.netty.channel.nio.NioEventLoop.processSelectedKeys(NioEventLoop.java:382)
	at io.netty.channel.nio.NioEventLoop.run(NioEventLoop.java:354)
	at io.netty.util.concurrent.SingleThreadEventExecutor$2.run(SingleThreadEventExecutor.java:112)
	at io.netty.util.concurrent.DefaultThreadFactory$DefaultRunnableDecorator.run(DefaultThreadFactory.java:137)
```


##FloodlightContext

    用于 FloodlightContextStore 类, floodlight 的订阅者可以注册和提取一个事件消息

###关键变量

    ConcurrentHashMap<String, Object> storage

###ConcurrentHashMap<String, Object> getStorage()

    获取 storage

##FloodlightContextStore<V>

    注意与FloodlightContext 的关系. 操作 bc 执行 get, put, remove

* V get(FloodlightContext bc, String key)
* void put(FloodlightContext bc, String key, V value)
* void remove(FloodlightContext bc, String key)

##IFloodlightProviderService

    定义了核心绑定用于和 switch 进行交换
    FloodlightContextStore<Ethernet> bcStore

###关键变量

    //获取包体
    String CONTEXT_PI_PAYLOAD = "net.floodlightcontroller.core.IFloodlightProvider.piPayload"

    //获取包体
    FloodlightContextStore<Ethernet> bcStore = new FloodlightContextStore<Ethernet>()

###关键方法
void addOFMessageListener(OFType type, IOFMessageListener listener)
void removeOFMessageListener(OFType type, IOFMessageListener listener)
Map<OFType, List<IOFMessageListener>> getListeners()
HARole getRole()
RoleInfo getRoleInfo()
Map<String,String> getControllerNodeIPs()
String getControllerId()
String getOFHostname()
int getOFPort()
void setRole(HARole role, String changeDescription)
void addUpdateToQueue(IUpdate update)
void addHAListener(IHAListener listener)
void removeHAListener(IHAListener listener)
void handleOutgoingMessage(IOFSwitch sw, OFMessage m)
void run()
void addInfoProvider(String type, IInfoProvider provider)
void removeInfoProvider(String type, IInfoProvider provider)
Map<String, Object> getControllerInfo(String type)
long getSystemStartTime()
Map<String, Long> getMemory()
Long getUptime()
Set<String> getUplinkPortPrefixSet()
void handleMessage(IOFSwitch sw, OFMessage m,FloodlightContext bContext)
Timer getTimer()
RoleManager getRoleManager()
ModuleLoaderState getModuleLoaderState()
int getWorkerThreads()


##Main

    floodlight 入口程序, 

1. 加载配置文件
2. 解析配置文件
3. 加载模块, 运行模块的 init() startUp() 方法
4. 运行 Restful 服务
5. 运行所有已配置（配置文件中配置）模块



##NullConnection

实现 IOFConnectionBackend, IOFMessageWriter 接口，提供默认行为




##ControllerId
     
    该类为 controller 提供唯一的 id 
    
    final short nodeId

###ControllerId(short nodeId)

    如果 nodeId = ClusterConfig.NODE_ID_UNCONFIGURED 会抛出异常.


##角色相关

ACTIVE : 当前运行的控制器的角色, 只应该由一个(但是当脑裂(split-brain)发生时, 就不能保证只有一个), 当一个　ACTIVE 控制器宕, STANDBY 角色控制中的一个变为　ACTIVE
STANDBY　: 热备控制器,以应对控制器的突然宕机,可以存在多个.

##HARole

    OFControllerRole 实际有三个值, ROLE_MASTER,ROLE_EQUAL,ROLE_SLAVE

###关键变量

    ACTIVE(OFControllerRole.ROLE_MASTER)
    STANDBY(OFControllerRole.ROLE_SLAVE)
    
    OFControllerRole ofRole  : 支持角色ROLE_MASTER, ROLE_SLAVE

###static HARole valueOfBackwardsCompatible(String roleString)

    为了向后兼容 of1.0 协议 

* HARole(OFControllerRole ofRole)  Bug: 应该和 ofOFRole 一样
* OFControllerRole getOFRole()
* static HARole ofOFRole(OFControllerRole role)

##IHAListener

    继承接口　IListener, 目前只监听 STANDBY 到 ACTIVE 的转变,不能监听 ACTIVE 到 STANDBY
    注: 目前只支持 STANDBY 到 ACTIVE 的转变, 不支持 ACTIVE 到 STANDBY 的转变?

* void transitionToActive() 当从 STANDBY 到 ACTIVE 到转变的时候调用
* void transitionToStandby() 当　ACTIVE　转为　STANDBY　时， floodlight 平台中断．
* void controllerNodeIPsChanged(Map<String, String> curControllerNodeIPs,Map<String, String> addedControllerNodeIPs,Map<String, String> removedControllerNodeIPs) 控制器集群中的控制器　IP　发送变化

##HAListenerTypeMarker

待实现

##RoleInfo

###关键变量

    HARole role
    String roleChangeDescription
    Date roleChangeDateTime

* RoleInfo(HARole role, String description, Date dt)
* HARole getRole()
* String getRoleChangeDescription()
* Date getRoleChangeDateTime()



##控制器与交换机的消息

##IOFMessageFilterManagerService

    继承　IFloodlightService, 消息过滤管理服务

* String setupFilter(String sid, ConcurrentHashMap<String, String> f,int deltaInMilliSeconds)


##IListener<T>

    enum Command {
        CONTINUE, 
        STOP
    }

* String getName()
* boolean isCallbackOrderingPrereq(T type, String name)
* boolean isCallbackOrderingPostreq(T type, String name)

##IOFMessageListener

    继承自 IListener 接口

* Command receive(IOFSwitch sw, OFMessage msg, FloodlightContext cntx)


##IOFMessageWriter

###void write(OFMessage m)
###void write(Iterable<OFMessage> msglist)

以上两个方法, 如果链路还没有建立, 将直接将消息丢掉

###<R extends OFMessage> ListenableFuture<R> writeRequest(OFRequest<R> request)
###<REPLY extends OFStatsReply> ListenableFuture<List<REPLY>> writeStatsRequest(OFStatsRequest<REPLY> request)

以上两个方法, 如果链路还没有建立, 将抛出 SwitchDisconnectedException 异常


##LogicalOFMessageCategory

###关键变量

    LogicalOFMessageCategory MAIN =  new LogicalOFMessageCategory("MAIN", OFAuxId.MAIN)
    String name
    OFAuxId auxId

###LogicalOFMessageCategory(@Nonnull String name, int auxId)
###LogicalOFMessageCategory(@Nonnull String name, OFAuxId auxId)
###OFAuxId getAuxId()
###String getName()


##controller-switch 消息

##IOFConnection

    继承自 IListener, 控制器与交换机建立连接信息

* Date getConnectedSince()               : 建立链路的时间
* void flush()                           : 刷新当前线程的连接
* DatapathId getDatapathId()             : 当前链路的远程交换机的　id
* OFAuxId getAuxId()                     : 当前冗余链路 id
* SocketAddress getRemoteInetAddress()   : 链路对端交换机 IP
* SocketAddress getLocalInetAddress()    : 
* OFFactory getOFFactory()               : 特性请求时用
* boolean isConnected()                  : 链路是否还在连接

##IOFConnectionBackend

    继承自 IOFConnection

* void disconnect()                                : 断开链路
* void cancelAllPendingRequests()                  : 取消全部等待的（未完成）请求
* boolean isWritable()                             : 是否可写
* void setListener(IOFConnectionListener listener) : 设置链路订阅者

##OFErrorMsgException

###关键变量

    long serialVersionUID = 1L
    OFErrorMsg errorMessage  : 错误消息

###OFErrorMsgException(final OFErrorMsg errorMessage)

    调用父类的构造方法, 初始化 errorMessage

###OFErrorMsg getErrorMessage()

    获取 errorMessage


##TimeOutDeliverable

    内部类

###关键变量

    long xid

###TimeOutDeliverable(long xid)

    初始化 xid

###run()

    从 xidDeliverableMap 中删除 xid, 并发送过期消息

##Deliverable< T >

接口类

* void deliver(T msg)
* void deliverError(Throwable cause)
* boolean isDone()
* boolean cancel(boolean mayInterruptIfRunning)

##DeliverableListenableFuture< T >

实现　Deliverable　接口，继承　com.google.common.util.concurrent.AbstractFuture

* void deliver(final T result)
* void deliverError(final Throwable cause)

##OFConnection

    实现 IOFConnection, IOFConnectionBackend

###关键变量

    DatapathId dpid                              : 当前连接的 dpid
    OFFactory factory                            : 
    Channel channel                              : 当前链路
    OFAuxId auxId                                : id
    Timer timer                                  : 定时器

    Date connectedSince                          : 链路建立时间
    Map<Long, Deliverable<?>> xidDeliverableMap  : xid 和 Deliverable(DeliverableListenableFuture)

    ThreadLocal<List<OFMessage>> localMsgBuffer  : 线程内的消息缓存

    OFConnectionCounters counters                : 计数器
    IOFConnectionListener listener               : 当前链路的订阅者

###OFConnection(@Nonnull DatapathId dpid, @Nonnull OFFactory factory, @Nonnull Channel channel, @Nonnull OFAuxId auxId, @Nonnull IDebugCounterService debugCounters, @Nonnull Timer timer)

###void write(OFMessage m)
    
    如果没有建立连接, 立即返回
    如果 m 的类型不是 PACKET_OUT FLOW_MOD 调用 this.write(ArrayList<OFMessage>(m))

###void write(Iterable<OFMessage> msglist)

    如果没有建立连接, 立即返回
    调用 this.channel.write(msglist)

###<R extends OFMessage> ListenableFuture<R> writeRequest(OFRequest<R> request)

    如果没有建立连接, 返回异常
    初始化 xidDeliverableMap, 调用 write(request)
    
###<REPLY extends OFStatsReply> ListenableFuture<List<REPLY>> writeStatsRequest(OFStatsRequest<REPLY> request)

    如果没有建立连接, 返回异常
    初始化 xidDeliverableMap, 调用 write(request)
    调用 timer 设置定时任务    

###void registerDeliverable(long xid, Deliverable<?> deliverable)
    
    xid, deliverable 增加到 xidDeliverableMap
    设置定时任务, 如果在 1 min 没有收到请求, 就发送错误消息
    

###boolean handleGenericDeliverable(OFMessage reply)

    获取 xidDeliverableMap.get(reply.getXid()) 根据 reply 类型来传递不同类型的消息, 如果传递完成, 从 xidDeliverableMap 删除reply.getXid()
    如果 replay.getXid() 存在于 xidDeliverableMap 返回 true
    否则返回 false

###void cancelAllPendingRequests()

    xidDeliverableMap 每个元素调用 cancel(true) 方法
    并清除 xidDeliverableMap

###boolean isConnected()

    this.channel 连接通道是否已经建立

###void flush()

    将还存在与 localMsgBuffer 中的消息发送出去

###SocketAddress getRemoteInetAddress()    

    channel.getRemoteAddress()

###SocketAddress getLocalInetAddress()

    channel.getLocalAddress()

###boolean deliverResponse(OFMessage m)

    同 handleGenericDeliverable

###boolean isWritable()

    channel.isWritable()

###DatapathId getDatapathId()
###OFAuxId getAuxId()
###OFFactory getOFFactory()
###IOFConnectionListener getListener()
###void setListener(IOFConnectionListener listener)
###Date getConnectedSince()

###Set<Long> getPendingRequestIds()

    返回 xidDeliverableMap.keySet() 的不可变对象

###void messageReceived(OFMessage m)

    如果 xidDeliverableMap 不含有 m.getXid(), 调用 listener.messageReceived(this, m)
    

###void disconnected()

    给 xidDeliverableMap 的每一个元素发送错误消息

###void disconnect()

    this.channel.disconnect()
    重置计数器    

##IOFConnectionListener

* void connectionClosed(IOFConnectionBackend connection)
* void messageReceived(IOFConnectionBackend connection, OFMessage m)
* boolean isSwitchHandshakeComplete(IOFConnectionBackend connection)


##NullConnectionListener

    实现　IOFConnectionListener　接口类

###void connectionClosed(IOFConnectionBackend connection)

    写日志

###void messageReceived(IOFConnectionBackend connection, OFMessage m)

    写日志

###boolean isSwitchHandshakeComplete(IOFConnectionBackend connection)

    返回　false

##OFConnectionCounters

    实现各种消息类型的计数功能

###关键变量

    COUNTER_MODULE = OFSwitchManager.class.getSimpleName()
    dpidAndConnIdString : dpid.toString() +":" + auxId.toString()
    debugCounterService : 调试计数服务

###OFConnectionCounters(IDebugCounterService counters,DatapathId dpid, OFAuxId auxId)

    初始化 dpidAndConnIdString
    注册各种类型的消息计数器
    
    COUNTER_MODULE, dpidAndConnIdString/
    COUNTER_MODULE, dpidAndConnIdString/write/
    COUNTER_MODULE, dpidAndConnIdString/write/messageType //实际的消息类型有多个
    COUNTER_MODULE, dpidAndConnIdString/read/
    COUNTER_MODULE, dpidAndConnIdString/read/messageType //实际的消息类型有多个
    

###void updateReadStats(OFMessage ofm)

    ofm 对应类型的消息的计数器加　１

###void updateWriteStats(OFMessage ofm)

    ofm 对应类型的消息的计数器加　１
    
####uninstallCounters()

    debugCounterService.removeCounterHierarchy(COUNTER_MODULE, dpidAndConnIdString)



##floodlight 中断服务

    通过　registerShutdownListener() 添加订阅者，在　terminate() 调用所有的订阅者的　floodlightIsShuttingDown() 方法(每个订阅者必须实现　IShutdownListener　接口)

##IShutdownService extends IFloodlightService

* void terminate(@Nullable String reason, int exitCode)
* void terminate(@Nullable String reason, @Nonnull Throwable e, int exitCode)
* void registerShutdownListener(@Nonnull IShutdownListener listener)

##IShutdownListener

   　订阅者在 floodlight 中断前执行的操作

* void floodlightIsShuttingDown()






##REST 相关

##IInfoProvider

    当 REST API 请求一个特定类型的时候调用

###Map<String, Object> getInfo(String type)
