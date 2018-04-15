
    在 channelOpen 时设置 10s 的握手超时timer,  channelClosed 取消 timer,
    在 controller 与 switch 建立连接 10 s内没有握手成功, 抛出异常

1. Controller 创建 Channel 监听 6633(6635) 端口
2. 当 Channel 连接时, 初始化 Channel, 设置当前的 state 为 WaitHelloState(), 并发送 Hello 到交换机
3. 在接受到 switch Hello 应答时, 设置of 及 解码器的版本, 设置当前的状态为 WaitFeaturesReplyState(), 发送 OFFeatureRequest 消息
4. 在接受到 switch 的 FeatureReply 时, 初始化 featuresReply 变量, 设置当前状态为 CompleteState(), 初始化变量 connection, 实现 INewOFConnectionListener 者, 执行 connectionOpened() 方法
6. 当握手成功后, controller 继续监听 switch 的连接, 如果接受到的是 Echo 请求就是发送 Echo 应答, 如果是 Echo 应答, 什么也不做, 除此之外的消息, 都调用 connection.messageReceived()

注: 

Controller 接受到 交换的请求, 发送 Hello 消息, 默认是用的 V1.3 版本, 是否兼容 1.3 以前版本待考证, 缺少版本协商过程

v1.3 支持冗余链路, 如果是 FeatureReply 接受的冗余链路, 那么就会修改 pipeline
MAIN_IDLE 为 AUX_IDL 的 idleHandler

建议阅读顺序

1. OFSwitchManager : init() startUp() 控制器开始监听交换机的连接,
2. OpenflowPipelineFactory : channel pipeline
3. OFChannelHandler : 控制器与交换机握手
4. OFSwitchManager 交换机管理方法
5. 

##switch 与 Controller 握手过程

1. Controller 发送 Hello 给交换机, 交换机应答, 成功, 进入下一步
2. Controller 发送

具体见 OFChannelHandler 的分析


###更新事件:

SwitchUpdate

* ADDED : 交换机增加
* REMOVED : 交换机删除
* PORTCHANGED : 交换机端口改变
* ACTIVATED : 交换机变为 MASTER
* DEACTIVATED : 交换机变为 SLAVE
* OTHERCHANGE : 其他改变



##交换机

交换机，包括交换机的描述，交换机的特性，交换机的状态,交换机操作三大类信息;　其中前两类在　
 SwitchSyncRepresentation 中，第三类在 SwitchStatus 中; 第四类在　IOFSwitchBackend　中．

继承关系

IOFSwitchBackend extends IOFSwitch extends IOFMessageWriter

##SyncedPort

OFPortDesc 的代理类

###关键变量

* OFPortDesc port

###成员函数

* SyncedPort fromOFPortDesc(OFPortDesc ofpd)
* OFPortDesc toOFPortDesc(OFFactory factory)


##SwitchSyncRepresentation

交换机的身份信息

###关键变量
// From FeaturesReply
* DatapathId dpid;
* long buffers;
* short tables;
* Set<OFCapabilities> capabilities;
* Set<OFActionType> actions;
* List<SyncedPort> ports;

// From OFDescStatsReply
* String manufacturerDescription;
* String hardwareDescription;
* String softwareDescription;
* String serialNumber;
* String datapathDescription;

###成员函数

* SwitchSyncRepresentation(OFFeaturesReply fr, SwitchDescription d) {
* SwitchSyncRepresentation(IOFSwitch sw)
* List<SyncedPort> toSyncedPortList(Collection<OFPortDesc> ports)
* List<OFPortDesc> toOFPortDescList(OFFactory factory, Collection<SyncedPort> ports)
* OFFeaturesReply getFeaturesReply(OFFactory factory)
* SwitchDescription getDescription()
* DatapathId getDpid()
* long getBuffers()
* short getTables()
* Set<OFCapabilities> getCapabilities()
* Set<OFActionType> getActions()
* List<SyncedPort> getPorts()
* String getManufacturerDescription()
* String getHardwareDescription()
* String getSoftwareDescription()
* String getSerialNumber()
* String getDatapathDescription() {

##SwitchRepresentation

REST representation of an OF Switch. Stitches together data from different
areas of the platform to provide a complete, centralized representation.

* long buffers;
* Set<OFCapabilities> capabilities;
* Short tables;
* SocketAddress inetAddress;
* Collection<OFPortDesc> sortedPorts;
* boolean isConnected;
* Date connectedSince;
* DatapathId dpid;
* Map<Object, Object> attributes;
* boolean isActive;
* Collection<IOFConnection> connections;
* String handshakeState;
* String quarantineReason;

##IOFSwitchDriver

交换机接口类

* IOFSwitchBackend getOFSwitchImpl(SwitchDescription description, OFFactory factory);

##ISwitchDriverRegistry {

交换机接口类

* void addSwitchDriver(String manufacturerDescriptionPrefix,IOFSwitchDriver driver);
* IOFSwitchBackend getOFSwitchInstance(IOFConnectionBackend connection, SwitchDescription description, OFFactory factory, DatapathId datapathId);

##NaiveSwitchDriverRegistry

实现 ISwitchDriverRegistry , Driver 注册类

###关键变量

SortedSet<String> switchDescSorted : manufacturerDescriptionPrefix
Map<String,IOFSwitchDriver> switchBindingMap : manufacturerDescriptionPrefix,IOFSwitchDriver
IOFSwitchManager switchManager : OFSwitchManager

###成员函数

###void addSwitchDriver(String manufacturerDescPrefix, IOFSwitchDriver driver)

###IOFSwitchBackend getOFSwitchInstance(IOFConnectionBackend connection, SwitchDescription description, OFFactory factory, DatapathId id)

    如果 switchDescSorted 中存在 description 匹配的, 就从 switchBindingMap
    对应的 driver 中获取, 如果不存在,就新建 OFSwitch




##IOFConnectionListener

* void connectionClosed(IOFConnectionBackend connection);
* void messageReceived(IOFConnectionBackend connection, OFMessage m);
* boolean isSwitchHandshakeComplete(IOFConnectionBackend connection);

##OFSwitchHandshakeState

抽象类

boolean handshakeComplete;

void processOFBarrierReply(OFBarrierReply m) {
void processOFError(OFErrorMsg m) {
void processOFFlowRemoved(OFFlowRemoved m) {
void processOFGetConfigReply(OFGetConfigReply m) {
void processOFPacketIn(OFPacketIn m) {
void processOFPortStatus(OFPortStatus m) {
void processOFQueueGetConfigReply(OFQueueGetConfigReply m) {
void processOFStatsReply(OFStatsReply m) {
void processOFExperimenter(OFExperimenter m) {
void processPortDescStatsReply(OFPortDescStatsReply m) {
void processOFRoleReply(OFRoleReply m) {
void enterState(){
boolean isHandshakeComplete() {
void auxConnectionOpened(IOFConnectionBackend connection) {
String getSwitchStateMessage(OFMessage m,
void illegalMessageReceived(OFMessage m) {
void unhandledMessageReceived(OFMessage m) {
void logErrorDisconnect(OFErrorMsg error) {
OFControllerRole extractNiciraRoleReply(OFMessage vendorMessage) {
void handlePortStatusMessage(OFPortStatus m, boolean doNotify) {
void processOFMessage(OFMessage m) {

##InitState

    继承 OFSwitchHandshakeState

##WaitPortDescStatsReplyState

    继承 OFSwitchHandshakeState

###void enterState()

	sendPortDescRequest()

###void processPortDescStatsReply(OFPortDescStatsReply  m)

    portDescStats = m;
	setState(new WaitConfigReplyState());

##WaitConfigReplyState 

###void processOFGetConfigReply(OFGetConfigReply m)

###void enterState() {

	sendHandshakeSetConfig();

##OFSwitchHandshakeHandler

    实现 IOFConnectionListener

    这里的握手主要是处理 OF 不同协议直接的差别

##WaitAppHandshakeState

	Iterator<IAppHandshakePluginFactory> pluginIterator;
	OFSwitchAppHandshakePlugin plugin;

###public void enterState()

###void enterNextPlugin();

如果是 1.3 版本



如果小于 1.3 版本

发送 sendHandshakeSetConfig() 等待 GET_CONFIG_REPLY , 调用 processOFGetConfigReply() 设置状态为 WaitDescriptionStatReplyState
发送 sendHandshakeDescriptionStatsRequest() 等待 STATS_REPLY, 调用 processOFStatsReply() 设置初始化 sw, 并开始驱动握手 startDriverHandshake();
如果驱动握手完成,设置状态为 WaitAppHandshakeState(), 如果没有握手完成 WaitSwitchDriverSubHandshakeState()(实际不可能发生)
设置状态为 WaitInitialRoleState(), 发送角色请求

	private IOFSwitchBackend sw : 交换机信息, 在 processOFStatsReply 中初始化



###OFSwitchHandshakeHandler(IOFConnectionBackend connection,OFFeaturesReply featuresReply,IOFSwitchManager switchManager,RoleManager roleManager,Timer timer) {

    初始化数据成员
    设置 state 状态为 InitState()

###void SetState(OFSwitchHandshakeState state)

    state.logState()
    state.enterState()

###void beginHandshake()

    如果是 1.3 setState(new WaitPortDescStatsReplyState());
    如果小于 1.3 setState(new WaitConfigReplyState());


###void sendHandshakeSetConfig()

    1. 设置配置
    2. Barrier
    3. 获取配置请求

##SwitchUpdate

    实现 IUpdate

###关键变量

* DatapathId swId;
* SwitchUpdateType switchUpdateType;
* OFPortDesc port;
* PortChangeType changeType;

###成员函数

###void dispatch()

    将交换机的 ADDED,REMOVED, PORTCHANGED,ACTIVATED, DEACTIVATED, OTHERCHANGE
    分发到所有的订阅者

##IOFSwitchManager

    接口类

* void switchAdded(IOFSwitchBackend sw);
* void switchDisconnected(IOFSwitchBackend sw);
* void notifyPortChanged(IOFSwitchBackend sw, OFPortDesc port,PortChangeType type);
* IOFSwitchBackend getOFSwitchInstance(IOFConnectionBackend connection, SwitchDescription description,OFFactory factory,DatapathId datapathId);
* void handleMessage(IOFSwitchBackend sw, OFMessage m, FloodlightContext bContext);
* ImmutableList<OFSwitchHandshakeHandler> getSwitchHandshakeHandlers();
* void addOFSwitchDriver(String manufacturerDescriptionPrefix, IOFSwitchDriver driver);
* void switchStatusChanged(IOFSwitchBackend sw, SwitchStatus oldStatus,SwitchStatus newStatus);
* int getNumRequiredConnections();
* void addSwitchEvent(DatapathId switchDpid, String reason, boolean flushNow);
* List<IAppHandshakePluginFactory> getHandshakePlugins();
* SwitchManagerCounters getCounters();
* boolean isCategoryRegistered(LogicalOFMessageCategory category);
* void handshakeDisconnected(DatapathId dpid);

##IOFSwitchService

* Map<DatapathId, IOFSwitch> getAllSwitchMap();
* IOFSwitch getSwitch(DatapathId dpid);
* IOFSwitch getActiveSwitch(DatapathId dpid);
* void addOFSwitchListener(IOFSwitchListener listener);
* void addOFSwitchDriver(String manufacturerDescriptionPrefix, IOFSwitchDriver driver);
* void removeOFSwitchListener(IOFSwitchListener listener);
* void registerLogicalOFMessageCategory(LogicalOFMessageCategory category);
* void registerHandshakePlugin(IAppHandshakePluginFactory plugin): 在正式握手之前可以通过调用该函数注册握手插件
* List<SwitchRepresentation> getSwitchRepresentations();
* SwitchRepresentation getSwitchRepresentation(DatapathId dpid);
* Set<DatapathId> getAllSwitchDpids();
* List<OFSwitchHandshakeHandler> getSwitchHandshakeHandlers();

##INewOFConnectionListener

* void connectionOpened(IOFConnectionBackend connection, OFFeaturesReply featuresReply);

##OFSwitchManager

实现接口 IOFSwitchManager,INewOFConnectionListener,IHAListener,IFloodlightModule,IOFSwitchService,IStoreListener<DatapathId>

核心是对交换机的状态管理

* 通过 switchAdded, switchStatusChanged, notifyPortChanged 来管理. 并通过 addUpdateToQueue 和 SwitchUpdate 将对应事件发布给所有的订阅者
* 通过 addOFSwitchListener, removeOFSwitchListener 类管理订阅交换机事件的类
* 通过 createServerBootStrap(), bootstrapNetty() 开始监听物理交换机的连接请求,并建立链路
* 实现 connectionOpened() 当物理交换机连接 Controller 的时候, 利用 OFSwitchHandshakeHandlers 进行握手 
* 订阅的 IStoreListener 的 keysModified()
* 通过 addOFSwitchDriver() 增加交换机 Driver


###关键变量

* Set<IOFSwitchListener> switchListeners : 订阅交换机事件的对象
* ISwitchDriverRegistry driverRegistry : 交换机驱动 NaiveSwitchDriverRegistry
* volatile OFControllerRole role : 当前控制器角色
* String keyStorePassword : SSL 加密密码
* String keyStore : 存储路径
* boolean useSsl = false : 是否 ssl 加密
* ConcurrentHashMap<DatapathId, OFSwitchHandshakeHandler> switchHandlers : 交换机握手处理器
* ConcurrentHashMap<DatapathId, IOFSwitchBackend> switches : 所有交换机成员, 关联所有交换机的状态
* ConcurrentHashMap<DatapathId, IOFSwitch> syncedSwitches :

###成员函数

###void transitionToActive()
###void transitionToStandby()
###SwitchManagerCounters getCounters()
###void addUpdateToQueue(IUpdate iUpdate)

###void switchStatusChanged(IOFSwitchBackend sw, SwitchStatus oldStatus, SwitchStatus newStatus)

    sw.getId() 与 switches 对应的不是同一对象, 日志 warn 之.
    SwitchStatus 是 MASTER 但当前 Controller 不是 Master, 那么, 报错
    这里的 Status 主要指, visable 或 MASTER 或 SLAVE 的改变

###void switchAdded(IOFSwitchBackend sw)

如果 sw 的 dpid 存在与 switches 中, oldsw 与 sw 是同一对象, 日志 error, 否则,取消所有的请求, 增加到更新事件列表中,断开 oldsw
如果 sw 的 dpid 不存在于 switches 中, 增加 sw.getId(), sw 到 switches 中

###void switchDisconnected(IOFSwitchBackend sw) {

    如果 sw 与 switches.get(sw.getId()) 不同, 打 warn 日志, 否则,从 switches.remove(sw.getId())

###IOFSwitch getSwitch(DatapathId dpid)
###IOFSwitch getActiveSwitch(DatapathId dpid)

如果 dpid 对应的交换机的角色是 MASTER 返回之, 否则返回 null

###Iterable<IOFSwitch> getActiveSwitches()

获取 switches 中所有角色是 MASTER 的交换机

###Map<DatapathId, IOFSwitch> getAllSwitchMap(boolean showInvisible)

    showInvisible=true : 获取所有交换机
    showInvisible=false : 获取 visable 所有交换机

###Map<DatapathId, IOFSwitch> getAllSwitchMap() {

    getAllSwitchMap(true)

###Set<DatapathId> getAllSwitchDpids(boolean showInvisible)

    getAllSwitchMap(showInvisible).keySet();

###Set<DatapathId> getAllSwitchDpids() {

    getAllSwitchMap(true).keySet()


获取 MASTER 角色的 switch 迭代器

###void addSwitchEvent(DatapathId dpid, String reason, boolean flushNow)

    交换机调试事件

###void notifyPortChanged(IOFSwitchBackend sw,OFPortDesc port,PortChangeType changeType)

    将交换机端口改变信息加到 floodlightProvider 更新队列中 update

###void addOFSwitchDriver(String manufacturerDescriptionPrefix, IOFSwitchDriver driver)

    调用 NaiveSwitchDriverRegistry 的 addSwitchDriver()

###IOFSwitchBackend getOFSwitchInstance(IOFConnectionBackend connection, SwitchDescription description, OFFactory factory, DatapathId datapathId)

    调用 NaiveSwitchDriverRegistry 的 getOFSwitchInstance()

###void handleMessage(IOFSwitchBackend sw, OFMessage m, FloodlightContext bContext)

    调用 floodlightProvider.handleMessage(sw, m, bContext);

###ImmutableList<OFSwitchHandshakeHandler> getSwitchHandshakeHandlers()
###void handshakeDisconnected(DatapathId dpid)

###Set<LogicalOFMessageCategory> getLogicalOFMessageCategories()
###boolean isCategoryRegistered(LogicalOFMessageCategory category)
###void registerLogicalOFMessageCategory(LogicalOFMessageCategory category)
###int calcNumRequiredConnections()
###int getNumRequiredConnections() {

    建立冗余链路, 通过 registerLogicalOFMessageCategory 注册即可, 而且冗余ID
    的顺序必须从0或1开始,依次增加

###void removeOFSwitchListener(IOFSwitchListener listener)
###void addOFSwitchListener(IOFSwitchListener listener)


###List<SwitchRepresentation> getSwitchRepresentations()
###SwitchRepresentation getSwitchRepresentation(DatapathId dpid)

    RESTful 接口 OFSwitch 信息, 获取 sw 已经建立连接的所有交换机的信息

###void registerHandshakePlugin(IAppHandshakePluginFactory factory)
###List<IAppHandshakePluginFactory> getHandshakePlugins()

###void init(FloodlightModuleContext context)

    依赖,配置等初始化

###void startUp(FloodlightModuleContext context)

    startUpBase(context)
    bootstrapNetty()

    通过该函数调用, controller 已经监听了 6633 端口, 等待交换机的连接

###void startUpBase(FloodlightModuleContext context)

1. 从配置文件中获取初始化角色
2. 订阅控制器 IP 改变(HAControllerNodeIPUpdate) 消息
3. 从 logicalOFMessageCategories 加入 LogicalOFMessageCategory.MAIN

###void loadLogicalCategories()

    初始化 logicalOFMessageCategories 为 LogicalOFMessageCategory.MAIN

###int calcNumRequiredConnections()

    目前情况下,总是返回 0

###void registerLogicalOFMessageCategory(LogicalOFMessageCategory category)

    增加 category 到 logicalOFMessageCategories. 目前只用到 LogicalOFMessageCategory.MAIN


###void registerDebugEvents()

    注册 switch-event 

###void bootstrapNetty()

1. 启动 netty 服务
2. 设置选项, TODO 加入配置选项

    "reuseAddr", true
    "child.keepAlive", true
    "child.tcpNoDelay", true
    "child.sendBufferSize", 128 * 1024

3. 创建 OpenflowPipelineFactory 为 netty 的 pipelineFactory
4. bind() TODO : 这里只指明 port, 增加可选的 addr

###ServerBootstrap createServerBootStrap()

    new ServerBootstrap(new NioServerSocketChannelFactory(
                                            Executors.newCachedThreadPool(),
                                            Executors.newCachedThreadPool(),
                                            floodlightProvider.getWorkerThreads()))


###void connectionOpened(IOFConnectionBackend connection, OFFeaturesReply featuresReply) {

    如果 connection 是主链路, 那么, 删除之前的链路, 重新握手
    如果 connection 是同一交换机的冗余链路(1.3 支持), 那么, 建立冗余链路,如果冗余链路先与主链路到达,断开链路

###void controllerNodeIPsChanged(Map<String, String> curControllerNodeIPs, Map<String, String> addedControllerNodeIPs, Map<String, String> removedControllerNodeIPs)

    什么也不做

###void keysModified(Iterator<DatapathId> keys, UpdateType type)

    遍历 type 为 REMOTE 的 keys. 如果key 不存在, 调用 switchRemovedFromStore()
    删除之, 如果 key 于 storedSwitch 对应的 sw 的 dpid 相同, 就调用
    switchAddedToStore()


bug : storeClient 初始化被注释, 调用该函数将导致空指针异常
      key.equal 待优化

###synchronized void switchRemovedFromStore(DatapathId dpid) {

    如果当前 controller 是 master 角色.(standby 角色忽略)
    将 dpid 从 syncedSwitches 中删除, 将 sw 删除的事件放到 floodlightProvider 的更新队列中

###synchronized void switchAddedToStore(IOFSwitch sw)

    如果当前 controller 是 master 角色.(standby 角色忽略)
    将 sw 增加到 syncedSwitches 中, 如果与 sw 的 dpid 相同之前增加过, 发送通知.
    否则, 将 sw 增加的事件放到 controller 的更新队列中

##OpenflowPipelineFactory

    实现 ChannelPipelineFactory, ExternalResourceReleasable 接口
    设置 controller 与 switch 的 channelpipeline, 当链路断开时, 显示地释放 timer

    ReadTimeoutHandler(timer, 30)  : UpStreamHandler     当 30 s没有读数据, 抛 ReadTimeoutException 异常
    IdleStateHandler(timer, 6, 2,0) : UpStreamHandler   当 6s 没有读或 2s 没有写时, 唤起 IdleStateEvent
    HandshakeTimeoutHandler(handler,timer, 10): UpStreamHandler  当链路打开, 10s 内没有握手成功, 抛出异常
    OFChannelHandler() : UpStreamHandler : 根据 channel 的不同状态出发不同的事件,switch 与 Controller 通信的主要状态控制
                                        见 [SimpleChannelHandler](http://netty.io/3.10/api/index.html)

###关键变量

* IOFSwitchManager switchManager : OFSwitchManager 实现
* INewOFConnectionListener connectionListener; OFSwitchManager 实现
* Timer timer : HashWheelTimer()
* IdleStateHandler idleHandler :  IdleStateHandler(this.timer, 6, 2, 0)
* ReadTimeoutHandler readTimeoutHandler : ReadTimeoutHandler(this.timer, 30)
* IDebugCounterService debugCounters : 计数服务
* String keyStore :
* String keyStorePassword :


###关键方法

###ChannelPipeline getPipeline()

	pipeline.addLast(PipelineHandler.OF_MESSAGE_DECODER,
			new OFMessageDecoder());
	pipeline.addLast(PipelineHandler.OF_MESSAGE_ENCODER,
			new OFMessageEncoder());
	pipeline.addLast(PipelineHandler.MAIN_IDLE, idleHandler);
	pipeline.addLast(PipelineHandler.READ_TIMEOUT, readTimeoutHandler);
	pipeline.addLast(PipelineHandler.CHANNEL_HANDSHAKE_TIMEOUT,
			new HandshakeTimeoutHandler(
					handler,
					timer,
					PipelineHandshakeTimeout.CHANNEL));
	pipeline.addLast(PipelineHandler.CHANNEL_HANDLER, handler);

###public void releaseExternalResources() {

    timer.stop()

##OFMessageDecoder

    继承 FrameDecoder(ChannelUpstreamHandler), 实现二进制转为 java 对象

##OFMessageEncoder

    继承 OneToOneEncoder(ChannelDownstreamHandler), 实现 java 到二进制

##HandshakeTimeoutHandler

    在 channelOpen 时, 增加定时任务, 在 channelClosed 时取消定时任务
    定时任务: 在 controller 与 switch 建立连接 10s 内没有握手成功, 抛出异常.

###关键变量

* OFChannelHandler handshakeHandler : OFChannelHandler
* Timer timer : HashWheelTimer
* long timeoutNanos : timeoutSeconds 转为纳秒
* volatile Timeout timeout : timeout 定时任务

###关键方法

###public HandshakeTimeoutHandler(OFChannelHandler handshakeHandler, Timer timer, long timeoutSeconds)

    handshakeHandler : OFChannelHandler
    timeoutSeconds : 10 s
    timer = HashWheelTimer

###void channelOpen(ChannelHandlerContext ctx, ChannelStateEvent e)

    timer 加入一元素 HandshakeTimeoutTask

###void channelClosed(ChannelHandlerContext ctx, ChannelStateEvent e)

    timeout.close(), 从 timer 中删除 timeout

##HandshakeTimeoutTask

    实现 TimerTask

###void run(Timeout timeout)

    如果在 10s 的时间内, 握手没有成功, 调用该方法.抛出异常 Channels.fireExceptionCaught(ctx, EXCEPTION);

##NewOFConnectionListener

    接口, OFSwitchManager 实现该接口

* void connectionOpened(IOFConnectionBackend connection, OFFeaturesReply featuresReply);



##OFChannelHandler

    继承 IdleStateAwareChannelHandler, 一个状态机实现

1. Controller 创建 Channel 监听 6633(6635) 端口, 每次 触发 messageReceived() 时, 调用 processOFMessage()
2. 当 channelConnected() 连接时, 初始化 Channel, 设置当前的 state 为 WaitHelloState(), 并发送 Hello 到交换机
3. 在接受到 switch Hello 应答时, 设置解码器的版本, 设置当前的状态为 WaitFeaturesReplyState(), 发送 OFFeatureRequest 消息
4. 在接受到 switch 的 FeatureReply 时, 初始化 featuresReply 变量, 设置当前状态为 CompleteState(), 初始化变量 connection, 实现 INewOFConnectionListener 者 OFSwitchManager 执行 connectionOpened() 方法
6. 当握手成功后, controller 每隔 写一次 Echo 请求到交换机

注: v1.3 支持冗余链路, 如果是 FeatureReply 接受的冗余链路, 那么就会修改 pipeline
MAIN_IDLE 为 AUX_IDL _的 idleHandler

###关键变量

* ChannelPipeline pipeline :
* INewOFConnectionListener newConnectionListener : 具体实现在 OFSwitchManager
* SwitchManagerCounters counters :
* Channel channel : 在 Channel 连接的时候初始化
* Timer timer  : HashWheelTimer
* volatile OFChannelState state : 初始化为 InitState, 即 OFChannelState 的 channelHandshakeComplete 为 false
* OFFactory factory = OFFactories.getFactory(OFVersion.OF_13);
* OFFeaturesReply featuresReply : 交换机的特性应答消息
* volatile OFConnection connection :
* IDebugCounterService debugCounters :

###关键方法

OFChannelHandler handler = new OFChannelHandler(switchManager, connectionListener,
				pipeline, debugCounters, timer);

    switchManager : OFSwitchManager
    connectionListener : OFSwitchManager
    pipeline : Channels.pipeline()
    timer  : HashWheelTimer

OFChannelHandler(IOFSwitchManager switchManager, INewOFConnectionListener newConnectionListener,
        ChannelPipeline pipeline, IDebugCounterService debugCounters, Timer timer) {

* boolean isSwitchHandshakeComplete() {
* void notifyConnectionClosed(OFConnection connection){
* void sendMessageToConnection(OFMessage m) {
* void sendFeaturesRequest()
* void sendHelloMessage()
* void sendEchoRequest() {
* void sendEchoReply(OFEchoRequest request) {

###void channelConnected(ChannelHandlerContext ctx,

    设置状态为 WaitHelloState

###void channelDisconnected(ChannelHandlerContext ctx,

    connection 关闭, connection.getListener().connectionClosed(connection);

###void channelIdle(ChannelHandlerContext ctx, IdleStateEvent e)

    发送 Echo 请求消息
    问题: 调用时机???

###void messageReceived(ChannelHandlerContext ctx, MessageEvent e)

    如果 e.getMessage() 是 List, 调用 state.processOFMessage(ofm);

###void exceptionCaught(ChannelHandlerContext ctx, ExceptionEvent e)

* void setAuxChannelIdle() 设置 idleHandler
* void setSwitchHandshakeTimeout() 设置 HandshakeTimeoutHandler
* String getConnectionInfoString() 获取连接信息, RemoteAddress+dpid

###void setState(OFChannelState state)

    这是 state, 调用 state.enterState()


##OFChannelState

    抽象类

###关键变量

	boolean channelHandshakeComplete : 握手完成的状态

###关键方法

* OFChannelState(boolean handshakeComplete)
* void processOFHello(OFHello m)
* void processOFEchoRequest(OFEchoRequest m)
* void processOFEchoReply(OFEchoReply m)
* void processOFError(OFErrorMsg m) {
* void processOFExperimenter(OFExperimenter m) {
* void processOFFeaturesReply(OFFeaturesReply  m)
* void enterState()
* String getSwitchStateMessage(OFMessage m,
* void illegalMessageReceived(OFMessage m) {
* void unhandledMessageReceived(OFMessage m) {
* void logError(OFErrorMsg error) {
* void logErrorDisconnect(OFErrorMsg error) {

###void processOFMessage(OFMessage m)

    消息处理的状态机
    void processOFMessage(OFMessage m)
            throws IOException {
        // Handle Channel Handshake
        if (!state.channelHandshakeComplete) {
            switch(m.getType()) {
            case HELLO:
                processOFHello((OFHello)m);
                break;
            case ERROR:
                processOFError((OFErrorMsg)m);
                break;
            case FEATURES_REPLY:
                processOFFeaturesReply((OFFeaturesReply)m);
                break;
            case EXPERIMENTER:
                processOFExperimenter((OFExperimenter)m);
                break;
            default:
                illegalMessageReceived(m);
                break;
            }
        }
        else{
            switch(m.getType()){
            // Always handle echos at the channel level!
            // Echos should only be sent in the complete.
            case ECHO_REPLY:
                processOFEchoReply((OFEchoReply)m);
                break;
            case ECHO_REQUEST:
                processOFEchoRequest((OFEchoRequest)m);
                break;
                // Send to SwitchManager and thus higher orders of control
            default:
                sendMessageToConnection(m);
                break;
            }
        }
    }

##InitState

    继承 OFChannelState

###InitState()

    super(false);

##WaitHelloState

    继承 OFChannelState

###WaitHelloState()

    super(false)

###void processOFHello(OFHello m)

    OFVersion version = m.getVersion();
    factory = OFFactories.getFactory(version);
    OFMessageDecoder decoder = pipeline.get(OFMessageDecoder.class);
    decoder.setVersion(version);
    setState(new WaitFeaturesReplyState());

###void enterState()

    进入该状态, controller 发送 Hello 给 switch

###void sendHelloMessage()

	// Send initial hello message
	// FIXME:LOJI: Haven't negotiated version yet, assume 1.3
	OFHello.Builder builder = factory.buildHello()
			.setXid(handshakeTransactionIds--);
	// FIXME: Need to add code here to set the version bitmap hello element
	OFHello m = builder.build();
	channel.write(Collections.singletonList(m));


##WaitFeaturesReplyState

    继承 OFChannelState

###WaitFeaturesReplyState()

	super(false)

###void processOFFeaturesReply(OFFeaturesReply  m)

    featuresReply = m;

    // Mark handshake as completed
    setState(new CompleteState());

###void enterState() throws IOException {

    进入该状态, controller 发送 FeatureRequest 给 switch

###void sendFeaturesRequest()

		OFFeaturesRequest m = factory.buildFeaturesRequest()
				.setXid(handshakeTransactionIds--)
				.build();
		channel.write(Collections.singletonList(m));

##CompleteState

###CompleteState()

    super(true)

###void enterState()

    设置 switch 握手 timeout
    重置 connection, newConnectionListener

    IOFConnection IOFConnectionBackend OFConnection 见 core 章节

###void setSwitchHandshakeTimeout() {

    HandshakeTimeoutHandler handler = new HandshakeTimeoutHandler(
            this,
            this.timer,
            PipelineHandshakeTimeout.SWITCH);

    pipeline.replace(PipelineHandler.CHANNEL_HANDSHAKE_TIMEOUT,
            PipelineHandler.SWITCH_HANDSHAKE_TIMEOUT, handler);

###void notifyConnectionOpened(OFConnection connection){

	this.connection = connection;
	this.newConnectionListener.connectionOpened(connection, featuresReply);






##LogicalOFMessageCategory

    单例类, 用于 OFSwitchManager 类

###关键变量
    LogicalOFMessageCategory MAIN =  new LogicalOFMessageCategory("MAIN", OFAuxId.MAIN)

    String name      :  名称
    OFAuxId auxId    :  id

* LogicalOFMessageCategory(@Nonnull String name, int auxId)
* LogicalOFMessageCategory(@Nonnull String name, OFAuxId auxId)
* OFAuxId getAuxId()
* String getName()

##IOFMessageWriter

如下接口是　fire-and-forget　语义，即如果连接已经断掉，将丢弃要写的消息

* void write(OFMessage m)
* void write(Iterable<OFMessage> msglist)
* write(Iterable<OFMessage> msglist)

如下接口，异步请求，如果连接已经断掉，将抛　SwitchDisconnectedException　异常　

* < R extends OFMessage> ListenableFuture<R> writeRequest(OFRequest<R> request)
* <REPLY extends OFStatsReply> ListenableFuture<List<REPLY>> writeStatsRequest(OFStatsRequest<REPLY> request)


##SwitchStatus

    HANDSHAKE(false)      : 处于握手阶段
    SLAVE(true)           : 处于 slave 状态, 不能接受 controller 的控制消息
    MASTER(true)          : 处于 master 状态, 能接受 controller 的控制消息
    QUARANTINED(false)    : 隔离状态
    DISCONNECTED(false)   : 交换机已经断开连接, 将从交换机数据库中删除

    boolean visible       : 对于正常的操作是否可见, 从 false->true, 增加; 从 true->false 删除;

###SwitchStatus(boolean visible)
###boolean isVisible()
###boolean isControllable()

##IOFSwitch

    继承 IOFMessageWriter

* SwitchStatus getStatus()                   : 当前交换机的状态
* long getBuffers()                          : 从特性应答中获取特性
* void disconnect()                          : 断开所有和交换的的链路, 标记为 DISCONNECTED
* Set<OFActionType> getActions()
* Set<OFCapabilities> getCapabilities()
* short getTables()
* SwitchDescription getSwitchDescription()   : 当前交换机统计描述符
* SocketAddress getInetAddress()             : 对端交换机IP
* Collection<OFPortDesc> getEnabledPorts()   : 不同与特性应答中的交换机端口，而是从交换机的端口状态信息中找到所有可用的端口描述
* Collection<OFPort> getEnabledPortNumbers() : 不同与特性应答中的交换机端口，而是从交换机的端口状态信息中找到所有可用的端口
* OFPortDesc getPort(OFPort portNumber)      : 不同与特性应答中的交换机端口, 而是实时的端口的状态
* OFPortDesc getPort(String portName)        : 不同与特性应答中的交换机端口, 而是实时的端口的状态
* Collection<OFPortDesc> getPorts()          : 不同与特性应答中的交换机端口, 而是实时的端口的状态
* Collection<OFPortDesc> getSortedPorts()    : 
* boolean portEnabled(OFPort portNumber)     : 端口是否可用（没有配置为down, 链路没有断, 不是 spanning tree block port）
* boolean portEnabled(String portName)       : 端口是否可用（没有配置为down, 链路没有断, 不是 spanning tree block port）
* boolean isConnected()                      : 当前交换机和控制器是否是连通的
* Date getConnectedSince()                   : 控制器和当前交换机器链路建立的时间
* DatapathId getId()                         : 当前交换机的 id
* Map< Object, Object> getAttributes()       : 获取当前交换机的属性
* boolean isActive()                         : 当前交换机是否是激活的(与控制器连接,而且当前交换机是 MASTER 角色)
* OFControllerRole getControllerRole()       : 与目前交换机连接的控制器的角色
* boolean hasAttribute(String name)          : 当前交换机是否存在 name 属性
* Object getAttribute(String name)           : 获取当前交换机的属性
* boolean attributeEquals(String name, Object other) : 当前交换机的 name　属性的值是否和　other 相同
* void setAttribute(String name, Object value)       : 设置当前交换机的属性 name 为 value
* Object removeAttribute(String name)                : 删除当前交换机的属性　name
* OFFactory getOFFactory()                           : 返回的 OFFactory 可以用来创建 OpenFlow message
* void flush()                                       : 刷新目前线程中所有的 flow
* ImmutableList< IOFConnection> getConnections()      : 获取与当前交换机的所有链路
* void write(OFMessage m, LogicalOFMessageCategory category) : 写 OFMessage 到 具体的 catagory
* void write(Iterable< OFMessage> msglist, LogicalOFMessageCategory category) : 写 OFMessage 列表到具体的 catagory
* OFConnection getConnectionByCategory(LogicalOFMessageCategory category) : 根据 category 获取 OFConnection
* < REPLY extends OFStatsReply> ListenableFuture<List<REPLY>> writeStatsRequest(OFStatsRequest<REPLY> request, LogicalOFMessageCategory category)           : 写 request 到 category, 并注册到匹配的 REPLY 
* < R extends OFMessage> ListenableFuture<R> writeRequest(OFRequest<R> request, LogicalOFMessageCategory category)                                             : 写 request 到 category, 并注册到匹配的 REPLY 


##IOFSwitchBackend

    继承自 IOFSwitch

* void registerConnection(IOFConnectionBackend connection)  : 注册 connection 到　netty channel 
* void removeConnections()                                  : 删除所有与当前交换机关联的　netty channel 
* void removeConnection(IOFConnectionBackend connection)    : 删除 connection 关联的　netty channel 
* void setFeaturesReply(OFFeaturesReply featuresReply)      : 初始化握手中, 设置特性应答消息
* OrderedCollection<PortChangeEvent> processOFPortStatus(OFPortStatus ps) : 被控制器调用用于处理端口改变，不应该被其他应用处理
* OrderedCollection<PortChangeEvent> comparePorts(Collection<OFPortDesc> ports)
* OrderedCollection<PortChangeEvent> setPorts(Collection<OFPortDesc> ports)

以下方法可以根据具体的交换机类型进行设置
* void setSwitchProperties(SwitchDescription description) : 基于交换机的描述符, 设置交换机属性
* void setTableFull(boolean isFull)               : 设置交换机的 table full 标志
* void startDriverHandshake()　　　　　　　　　　 : 如果握手已经开始，抛异常, 否则设置 startDriverHandshakeCalled 
* boolean isDriverHandshakeComplete()             : 如果握手还没开始，抛异常
* void processDriverHandshakeMessage(OFMessage m) : 如果握手还没开始或已经结束，抛异常
* void setPortDescStats(OFPortDescStatsReply portDescStats)
* void cancelAllPendingRequests()
* void setControllerRole(OFControllerRole role)   : 设置交换机的角色
* void setStatus(SwitchStatus switchStatus)
* void updateControllerConnections(OFBsnControllerConnectionsReply controllerCxnsReply)
* boolean hasAnotherMaster()                      : 交换机是否与另外一个 master 角色的 controller 连接


##IOFSwitchDriver

* IOFSwitchBackend getOFSwitchImpl(SwitchDescription description, OFFactory factory)

##IOFSwitchListener

    交换机的生命周期

* void switchAdded(DatapathId switchId)
* void switchRemoved(DatapathId switchId)
* void switchActivated(DatapathId switchId)
* void switchPortChanged(DatapathId switchId,OFPortDesc port,PortChangeType type)
* void switchChanged(DatapathId switchId)


##IReadyForReconcileListener

    当控制器从 Slave -> Master 转换时，开始流表项的一致性

###void readyForReconcile()


##SwitchDescription

    交换机的描述信息, 该类通过 Builder 类来实现灵活的构造函数, 一旦构造，数据成员就不能再改变了．

###关键变量

    String manufacturerDescription
    String hardwareDescription
    String softwareDescription
    String serialNumber
    String datapathDescription

###static Builder builder()

    辅助构造函数

* String getManufacturerDescription()
* String getHardwareDescription()
* String getSoftwareDescription()
* String getSerialNumber()
* String getDatapathDescription()

##SyncedPort

    OFPortDesc port

###static SyncedPort fromOFPortDesc(OFPortDesc ofpd) 

    从 ofpd 初始化 SyncedPort

###OFPortDesc toOFPortDesc(OFFactory factory)     

    从 SyncedPort　利用 factory．buildPortDesc()  将　self.port 初始化 OFPortDesc

##SwitchSyncRepresentation

###关键变量

//FeatureReply
* DatapathId dpid
* long buffers
* short tables
* Set<OFCapabilities> capabilities
* Set<OFActionType> actions
* List<SyncedPort> ports

//描述(OFDescStateReply)
* String manufacturerDescription
* String hardwareDescription
* String softwareDescription
* String serialNumber
* String datapathDescription

* SwitchSyncRepresentation(DatapathId dpid,long buffers,short tables,Set<OFCapabilities> capabilities,Set<OFActionType> actions, List<SyncedPort> ports, String manufacturerDescription, String hardwareDescription, String softwareDescription, String serialNumber, String datapathDescription)
* SwitchSyncRepresentation(IOFSwitch sw)
* SwitchSyncRepresentation(OFFeaturesReply fr,SwitchDescription d)

###static List<SyncedPort> toSyncedPortList(Collection<OFPortDesc> ports)
   
     将 ports 中的每一个元素转为 SyncedPort

###static List<OFPortDesc> toOFPortDescList(OFFactory factory, Collection<SyncedPort> ports)
    
     将 ports 中的每一个元素转为 OFPortDesc

###OFFeaturesReply getFeaturesReply(OFFactory factory)

     根据 factory.buildFeaturesReply() 构建 OFFeaturesReply

###SwitchDescription getDescription()

    根据关键变量构建 SwitchDescription 对象并返回之

* DatapathId getDpid()
* long getBuffers()
* short getTables()
* Set<OFCapabilities> getCapabilities()
* Set<OFActionType> getActions()
* List<SyncedPort> getPorts()
* String getManufacturerDescription()
* String getHardwareDescription()
* String getSoftwareDescription()
* String getSerialNumber()
* String getDatapathDescription()


##SwitchDriverSubHandshakeAlreadyStarted

    继承自 SwitchDriverSubHandshakeException

##SwitchDriverSubHandshakeCompleted

    继承自 SwitchDriverSubHandshakeException

##SwitchDriverSubHandshakeException

    继承自 RuntimeException

##SwitchDriverSubHandshakeNotStarted

    继承自 SwitchDriverSubHandshakeException

##SwitchDriverSubHandshakeStateException

    继承自 SwitchDriverSubHandshakeException

##PortChangeEvent

###关键变量

    OFPortDesc port
    PortChangeType type

###PortChangeEvent(OFPortDesc port,PortChangeType type)

##PortChangeType

    ADD, OTHER_UPDATE, DELETE, UP, DOWN,

##PortManager

###关键变量

    ReentrantReadWriteLock lock
    List<OFPortDesc> portList
    List<OFPortDesc> enabledPortList
    List<OFPort> enabledPortNumbers
    Map<OFPort,OFPortDesc> portsByNumber
    Map<String,OFPortDesc> portsByName

###PortManager()

###void updatePortsWithNewPortsByNumber(Map<OFPort,OFPortDesc> newPortsByNumber)

    用 newPortsByNumber　初始化
    portsByName,　portsByNumber　存储所有　newPortsByNumber　元素
    enabledPortNumbers,　enabledPortNumbers　存储端口状态不为 LINK_DOWN, 配置不为　PORT_DOWN

###OrderedCollection<PortChangeEvent> handlePortStatusDelete(OFPortDesc delPort)

###OrderedCollection<PortChangeEvent> handlePortStatusMessage(OFPortStatus ps)

###OrderedCollection<PortChangeEvent> getSinglePortChanges(OFPortDesc newPort)

###OrderedCollection<PortChangeEvent>  comparePorts(Collection<OFPortDesc> newPorts)

###OrderedCollection<PortChangeEvent> updatePorts(Collection<OFPortDesc> newPorts)

###OrderedCollection<PortChangeEvent> compareAndUpdatePorts(Collection<OFPortDesc> newPorts,boolean doUpdate)

* OFPortDesc getPort(String name)
* OFPortDesc getPort(OFPort portNumber)
* List<OFPortDesc> getPorts()
* List<OFPortDesc> getEnabledPorts()
* List<OFPort> getEnabledPortNumbers()


##OFSwitch

    实现　IOFSwitchBackend 接口, 交换机的核心实现

    一个交换机和控制器可以由多条链路，但是只能由一条主链路，实际的通信只用主链路

###关键变量

    ConcurrentMap<Object, Object> attributes

    IOFSwitchManager switchManager

    Set<OFCapabilities> capabilities
    long buffers
    Set<OFActionType> actions
    short tables
    final DatapathId datapathId                    : 设备 id
    SwitchDescription description

    SwitchStatus status

    boolean startDriverHandshakeCalled = false     : 链路是否开始握手
    Map<OFAuxId, IOFConnectionBackend> connections : 所有的链路

    Map<URI, Map<OFAuxId, OFBsnControllerConnection>> controllerConnections : OFCon.getUri()(),(OFCon.getAuxiliaryId(),OFCon )

    OFFactory factory

    PortManager portManager
    volatile boolean connected                    : 链路状态
    volatile OFControllerRole role
    boolean flowTableFull = false

    final int OFSWITCH_APP_ID = ident(5)

    AppCookie.registerApp(OFSwitch.OFSWITCH_APP_ID, "switch")


OFSwitch(IOFConnectionBackend connection, OFFactory factory, IOFSwitchManager switchManager,　DatapathId datapathId)    



* OFFactory getOFFactory()

* boolean attributeEquals(String name, Object other)
* Object getAttribute(String name)
* this.attributes.put(name, value)
* void setAttribute(String name, Object value)
* Object removeAttribute(String name)
* boolean hasAttribute(String name)

* void registerConnection(IOFConnectionBackend connection)
* ImmutableList<IOFConnection> getConnections()
* void removeConnections()
* void removeConnection(IOFConnectionBackend connection): bug connection == null
* IOFConnection getConnection(OFAuxId auxId)
* IOFConnection getConnection(LogicalOFMessageCategory category)
* OFConnection getConnectionByCategory(LogicalOFMessageCategory category)

###void write(OFMessage m)

    connections.get(OFAuxId.MAIN).write(m)

###void write(OFMessage m, LogicalOFMessageCategory category)

    this.getConnection(category).write(m)

###<R extends OFMessage> ListenableFuture<R> writeRequest(OFRequest<R> request, LogicalOFMessageCategory category)

    getConnection(category).writeRequest(request)

###<R extends OFMessage> ListenableFuture<R> writeRequest(OFRequest<R> request)

    connections.get(OFAuxId.MAIN).writeRequest(request)

###void write(Iterable<OFMessage> msglist)

    connections.get(OFAuxId.MAIN).write(msglist)

###void disconnect()

    遍历　connections 的所有 valueSet(), 调用　diconnect()
    从 connection 中删除 keySet()

    问题:迭代器不会失效?

###void setFeaturesReply(OFFeaturesReply featuresReply)

    根据 featuresReply 设置　this.capabilities，this.buffers,this.actions,this.tables

//portManager
###void setPortDescStats(OFPortDescStatsReply reply)

    portManager.updatePorts(OFPortDescs)

* Collection<OFPortDesc> getEnabledPorts()
* Collection<OFPort> getEnabledPortNumbers()
* OFPortDesc getPort(OFPort portNumber)
* OFPortDesc getPort(String portName)
* Collection<OFPortDesc> getPorts()

###OrderedCollection<PortChangeEvent> processOFPortStatus(OFPortStatus ps)

    portManager.handlePortStatusMessage(ps)

###Collection<OFPortDesc> getSortedPorts()

    排序 portManager.getPorts()

###OrderedCollection<PortChangeEvent> comparePorts(Collection<OFPortDesc> ports)

    portManager.comparePorts(ports)

###OrderedCollection<PortChangeEvent> setPorts(Collection<OFPortDesc> ports)

    portManager.updatePorts(ports)

###boolean portEnabled(OFPort portNumber)

    端口状态不是 BLOCKED,LINK_DOWN,STP_BLOCK,才返回　true

    问题: 与前面初始化不一致

###boolean portEnabled(String portName)

* DatapathId getId()
* ConcurrentMap<Object, Object> getAttributes()

###Date getConnectedSince()

    获取主链路创建时间

###<REPLY extends OFStatsReply> ListenableFuture<List<REPLY>> writeStatsRequest(OFStatsRequest<REPLY> request)

    connections.get(OFAuxId.MAIN).writeStatsRequest(request)

###<REPLY extends OFStatsReply> ListenableFuture<List<REPLY>> writeStatsRequest(OFStatsRequest<REPLY> request, LogicalOFMessageCategory category)

    getConnection(category).writeStatsRequest(request)

###void cancelAllPendingRequests()

    this.connections 的 valueSet() 的每个元素调用 cancelAllPendingRequests()

###void flush()

    this.connections 的 valueSet() 的每个元素调用 flush()

* boolean isConnected()
* SocketAddress getInetAddress()

###boolean isActive()

    链路是通的，　角色是　MASTER

* OFControllerRole getControllerRole()
* void setControllerRole(OFControllerRole role)

//特性
* long getBuffers()
* Set<OFActionType> getActions()
* Set<OFCapabilities> getCapabilities()
* short getTables()
* SwitchDescription getSwitchDescription()


###void startDriverHandshake()

    如果握手开始，　抛　SwitchDriverSubHandshakeAlreadyStarted()
    如果握手没有开始，设置握手开始标志

###boolean isDriverHandshakeComplete()

    如果握手开始，返回 true
    如果握手没有开始，抛　SwitchDriverSubHandshakeNotStarted()

    问题: 这是期望的么？

###void processDriverHandshakeMessage(OFMessage m)

    如果握手开始，抛　SwitchDriverSubHandshakeCompleted(m)
    如果握手没有开始，抛　SwitchDriverSubHandshakeNotStarted()

    问题: 这是期望的么？

###void setSwitchProperties(SwitchDescription description)

    设置　this.description = description;

    问题: 这是期望的么？

* SwitchStatus getStatus()
* void setStatus(SwitchStatus switchStatus)

###void updateControllerConnections(OFBsnControllerConnectionsReply controllerCxnsReply)

    将　controllerCxnsReply 加入　this.controllerConnections

###boolean hasAnotherMaster()

    如果 this.getConnection(OFAuxId.MAIN)　为　null, 返回　false
    否则　this.getConnection(OFAuxId.MAIN)　不在　this.controllerConnections　中， 且　this.controllerConnections 的　valueSet() 的每个元素的　OFAuxId.MAIN　对应的状态为　.BSN_CONTROLLER_CONNECTION_STATE_CONNECTED, 角色为　ROLE_MASTER　返回 true
    其他情况, 返回 false


