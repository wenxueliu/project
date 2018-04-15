
整个项目的启动过程:

* 加载模块, 并进行模块初始化后
* 调用本模块的 run() 方法. 而 run() 主要的工作就是从更新队列取出更新事件调用对应的 dispatch() 方法分发更新到各个订阅者.

关键模块初始化说明:

* OFSwitchManager 的 starUp() 调用之后, 开始监听 6633 (或 6653), 等待交换机的连接

###模块初始化和启动顺序

JythonDebugInterface
    实现 无
    依赖 无

RestApiServer
    实现 IRestApiService
    依赖 无

ShutdownServiceImpl 
    实现 IShutdownService
    依赖 无

DebugCounterServiceImpl 
    实现 IDebugCounterService
    依赖 ShutdownServiceImpl

MemoryStorageSource
    实现 IStorageSourceService
    依赖 IRestApiService, IDebugCounterService

PktInProcessingTime
    实现 IPktInProcessingTimeService    
    依赖 IFloodlightProviderService, IRestApiService

DebugEventService
    实现 IDebugEventService    
    依赖 IShutdownService

ThreadPool
    实现 IThreadPoolService
    依赖 无

SyncManager
    实现 ISyncService
    依赖 IThreadPoolService,IStorageSourceService, IDebugCounterService

OFSwitchManager
    实现 IOFSwitchService
    依赖 IFloodlightProviderService, IDebugEventService, IDebugCounterService,ISyncService

net.floodlightcontroller.core.internal.FloodlightProvider
    实现 IFloodlightProviderService
    依赖 IPktInProcessingTimeService,IStorageSourceService,IRestApiService, IDebugCounterService
        IDebugEventService, IOFSwitchService, IThreadPoolService,ISyncService

net.floodlightcontroller.staticflowentry.StaticFlowEntryPusher
    实现 IStaticFlowEntryPusherService
    依赖 IFloodlightProviderService, IOFSwitchService, IStorageSourceService, IRestApiService

net.floodlightcontroller.linkdiscovery.internal.LinkDiscoveryManager
    实现 ILinkDiscoveryService
    依赖 IFloodlightProviderService, IStorageSourceService, IThreadPoolService, 
        IRestApiService, IShutdownService

net.floodlightcontroller.topology.TopologyManager
    实现 IRoutingService, ITopologyService
    依赖 ILinkDiscoveryService, IThreadPoolService, IFloodlightProviderService, IOFSwitchService,
        IDebugCounterService, IDebugEventService, IRestApiService

net.floodlightcontroller.devicemanager.internal.DefaultEntityClassifier
    实现 IEntityClassifierService.class,
    依赖 无

net.floodlightcontroller.devicemanager.internal.DeviceManagerImpl
    实现 IDeviceService
    依赖 IFloodlightProviderService, IStorageSourceService, ITopologyService, IRestApiService
        IThreadPoolService, IEntityClassifierService, ISyncService

net.floodlightcontroller.forwarding.Forwarding
    实现 无
    依赖 IFloodlightProviderService, IDeviceService, IRoutingService,
        ITopologyService, IDebugCounterService

net.floodlightcontroller.ui.web.StaticWebRoutable
    实现 无
    依赖 IRestApiService

net.floodlightcontroller.loadbalancer.LoadBalancer
    实现 ILoadBalancerService
    依赖 IFloodlightProviderService, IRestApiService, IOFSwitchService, IDeviceService, 
        IDebugCounterService,ITopologyService, IRoutingService, IStaticFlowEntryPusherService

net.floodlightcontroller.firewall.Firewall
    实现 IFirewallService
    依赖 IFloodlightProviderService, IStorageSourceService, IRestApiService


net.floodlightcontroller.accesscontrollist.ACL
    实现 IACLService
    依赖 IRestApiService, IDeviceService


###所有更新事件

HAControllerNodeIPUpdate:  : 控制器 IP 改变事件
SwitchUpdate               : 交换机更新时间
HARoleUpdate               : HA 角色更新
SwitchRoleUpdate           : 交换机角色更新


###FloodlightProvider

依赖 Controller.java 实现功能

* void init(FloodlightModuleContext context)
* void startUp(FloodlightModuleContext context)
* void run()


###Controller

实现 IFloodlightProviderService, IStorageSourceListener, IInfoProvider 接口,
主要工作是模块初始化, 之后运行更新服务

HAControllerNodeIPUpdate : 订阅控制器 IP 改变事件
NotificationSwitchListener : 订阅交换机更新事件

####关键变量

ThreadLocal<Stack<FloodlightContext>> flcontext_cache : 缓存空闲的 FloodlightContext

ConcurrentMap<OFType, ListenerDispatcher<OFType,IOFMessageListener>> messageListeners　: 消息订阅者
ListenerDispatcher<HAListenerTypeMarker,IHAListener> haListeners　: HA 角色的订阅者
HashMap<String, String> controllerNodeIPsCache　: 控制器ID : IP, 主要用于控制器 IP 变化的情况
BlockingQueue<IUpdate> updates : 更新队列
Map<String, List<IInfoProvider>> providerMap : 
volatile HARole notifiedRole : HA 角色, 对应于配置选项 core.internal.FloodlightProvider.role=ACTIVE
int workerThreads = 0 : 默认为 0. 对应于配置选项 core.internal.FloodlightProvider.role=2
IShutdownService shutdownService : 
RoleManager roleManager : 角色管理
Timer timer :  定时任务， 主要用于在 controller 与 swithc 通信的 channel 中,详见 OpenflowPipelineFactory.java

IStorageSourceService storageSourceService
IOFSwitchService switchService : 该变量在　FloodlightProvider 的　init() 中初始化，实际为 OFSwitchManager 
IDebugCounterService　debugCounterService
IDebugEventService debugEventService
IRestApiService restApiService
IPktInProcessingTimeService pktinProcTimeService
IThreadPoolService threadPoolService
ISyncService syncService

ControllerCounters counters : 对 controller 模块进行计数统计
LoadMonitor loadmonitor : 负载监控
Set<String> uplinkPortPrefixSet

###方法实现
* Set<String> getUplinkPortPrefixSet()
* void setUplinkPortPrefixSet(Set<String> prefixSet)

* void setStorageSourceService(IStorageSourceService storageSource)
* IStorageSourceService getStorageSourceService()
* IShutdownService getShutdownService()
* void setShutdownService(IShutdownService shutdownService)
* public void setDebugEvent(IDebugEventService debugEvent)
* void setDebugCounter(IDebugCounterService debugCounters)
* IDebugCounterService getDebugCounter()
* void setSyncService(ISyncService syncService)
* void setPktInProcessingService(IPktInProcessingTimeService pits)
* void setRestApiService(IRestApiService restApi)
* void setThreadPoolService(IThreadPoolService tp)
* IThreadPoolService getThreadPoolService()
* void setSwitchService(IOFSwitchService switchService)
* IOFSwitchService getSwitchService()
* int getWorkerThreads()
* HARole getRole() 
* RoleInfo getRoleInfo()
* void setRole(HARole role, String changeDescription)
* void reassertRole(OFSwitchHandshakeHandler ofSwitchHandshakeHandler, HARole role)
* String getControllerId()
* String getOFHostname()
* int getOFPort()

* ModuleLoaderState getModuleLoaderState()
* void resetModuleState()
* void setModuleLoaderStateForTesting(ModuleLoaderState state)

* void removeInfoProvider(String type, IInfoProvider provider)
* void removeInfoProvider(String type, IInfoProvider provider)
* Timer getTimer()

* void addInfoProvider(String type, IInfoProvider provider)
* void removeInfoProvider(String type, IInfoProvider provider)

* void removeHAListener(IHAListener listener)
* void addHAListener(IHAListener listener)
* Map<OFType, List<IOFMessageListener>> getListeners()

* ControllerCounters getCounters()
* Optional<ControllerId> getId()
* RoleManager getRoleManager()
* void setNotifiedRole(HARole newRole)
* Map<String, Object> getInfo(String type)
* Map<String, Object> getControllerInfo(String type)

* Map<String, String> getControllerNodeIPs()

* void addUpdateToQueue(IUpdate update)

* void rowsModified(String tableName, Set<Object> rowKeys)
* void rowsDeleted(String tableName, Set<Object> rowKeys)

* long getSystemStartTime()
* Map<String, Long> getMemory()
* Long getUptime()


###setConfigParams(Map<String, String> configParams)

    配置　openflowPort, workerthreads 两个配置
    TODO:　openflowPort　应该参数校验; 这里 workerthreads　应该捕获异常，而且　workerthreads　必须合理范围之内.


###ModuleLoaderState

记录模块状态

* INIT      : 初始化, 调用　init()　时处于该状态
* STARTUP   : 开始，　调用　startupComponents() 时处于该状态
* COMPLETE  : 完成,  调用　run() 处于该状态

public enum ModuleLoaderState {
   INIT, STARTUP, COMPLETE
}

###void init(Map<String, String> configParams)

    模块变量初始化, 具体见关键变量说明

###void startupComponents(FloodlightModuleLoader floodlightModuleLoader)

    初始化工作，如　RestApiService SynService 

###void run()

    运行更新服务， 从 update 中取数据,调用对应的 dispatch() 方法

####void handleMessage(IOFSwitch sw, OFMessage m,FloodlightContext bContext)

    1. 当前角色是 MASTER
    2. 如是 PACKET_IN 事件, 解包
    3. 遍历 messageListeners 类型为 m.getType() 的所有订阅者, 如果某个订阅者不希望处理该消息, 返回

####void addOFMessageListener(OFType type, IOFMessageListener listener)

    将 type, listener 加入 messageListeners

####void removeOFMessageListener(OFType type, IOFMessageListener listener)

    从 messageListeners 删除 type, listener  

####void removeOFMessageListeners(OFType type)

    从 messageListeners 删除 type

####Map<OFType, List<IOFMessageListener>> getListeners()

    获取所有的 messageListeners

####void handleOutgoingMessage(IOFSwitch sw, OFMessage m)

    获取 messageListeners 中所有与 m.getType() 相同的订阅者, 如果 listerner.receive(sw, m,bc) 为 Command.STOP, 
    亭子循环


####FloodlightContext flcontext_alloc()

    如果 flcontext_cache 不为空,  flcontext_cache 中 pop 一个后返回, 否则返回新创建的 FloodlightContext()


###HARole getInitialRole(Map<String, String> configParams)

    1.0 以前默认是　MASTER 而 1.0 以后默认是 STANDBY, 因此, 1.0 以后强制必须在配置文件指定 role

###readFlowPriorityConfigurationFromStorage

    已经没有实际用处了

###void handleControllerNodeIPChanges()

    从存储中搜寻每一行与　controllerNodeIPsCache　比较，记录没有变化的，增加的和删除的
    更新　controllerNodeIPsCache，　如果　removedControllerNodeIPs或　addedControllerNodeIPs　不为空
，加入更新队列

    TODO: 这的模块是主要查看 eth0 的情况


##NotificationSwitchListener

实现接口 IOFSwitchListener, 交换机增加,删除和端口改变的时候, 调用 notifier 发送通知


##IUpdate

    接口类

* public void dispatch()


##HAControllerNodeIPUpdate

实现 IUpdate 接口,  通过调用 dispatch() 方法, 通知所有的 IHAListener, 调用 controllerNodeIPsChanged() 
获取拓扑改变消息



##厂商信息注册

###abstract class OFVendorId

* static Map<Integer, OFVendorId> mapping = new HashMap<Integer, OFVendorId>();
* int id;

* //与 mapping 相关
* static void registerVendorId(OFVendorId vendorId)
* static OFVendorId lookupVendorId(int id)

* OFVendorId(int id)
* public int getId()
* abstract OFVendorDataType parseVendorDataType(ChannelBuffer data, int length);

###OFBasicVendorId extends OFVendorId

* int dataTypeSize; 只能是 1,2,4,8
* Map<Long, OFBasicVendorDataType> dataTypeMap

    dataTypeMap :
        10: OFRoleReplyVendorData()
        11: OFRoleRequestVendorData()


* OFBasicVendorId(int id, int dataTypeSize)
* int getDataTypeSize()

* void registerVendorDataType(OFBasicVendorDataType vendorDataType)
* OFVendorDataType lookupVendorDataType(int vendorDataType)
* OFVendorDataType parseVendorDataType(ChannelBuffer data, int length)
    从 data 中读取 length 数据作为 dataTypeMap key 返回对应的 value, 如果
    dataTypeMap 不存在对应的 value, 初始化 OFBasicVendorDataType()

###OFVendorDataType

* Instantiable<OFVendorData> instantiable;
* OFVendorDataType()
* OFVendorDataType(Instantiable<OFVendorData> instantiable)
* OFVendorData newInstance() // Instantiable.instantiate()

* Instantiable<OFVendorData> getInstantiable()
* void setInstantiable(Instantiable<OFVendorData> instantiable)

###OFBasicVendorDataType extends OFVendorDataType

* long type;
* OFBasicVendorDataType()
* OFBasicVendorDataType(long type, Instantiable<OFVendorData> instantiator) {
* long getTypeValue()
* void setTypeValue(long type)

###interface OFVendorData

* int getLength();
* void readFrom(ChannelBuffer data, int length);
* void writeTo(ChannelBuffer data);

###OFByteArrayVendorData implements OFVendorData

* protected byte[] bytes;

* OFByteArrayVendorData()
* OFByteArrayVendorData(byte[] bytes)
* byte[] getBytes()
* void setBytes(byte[] bytes)
* int getLength()
* void readFrom(ChannelBuffer data, int length)
* void writeTo(ChannelBuffer data)

###OFNiciraVendorData implements OFVendorData

* static int NX_VENDOR_ID = 0x00002320;
* int dataType

* OFNiciraVendorData()
* OFNiciraVendorData(int dataType)
* int getDataType()
* void setDataType(int dataType)
* int getLength()
* void readFrom(ChannelBuffer data, int length)
* void writeTo(ChannelBuffer data)

###OFRoleVendorData extends OFNiciraVendorData

* //indicating that the controller role.
* public static final int NX_ROLE_OTHER = 0;
* public static final int NX_ROLE_MASTER = 1;
* public static final int NX_ROLE_SLAVE = 2;

* OFRoleVendorData() //super()
* OFRoleVendorData(int dataType)
* OFRoleVendorData(int dataType, int role)
* int getRole()
* void setRole(int role)
* int getLength()
* void readFrom(ChannelBuffer data, int length)
* void writeTo(ChannelBuffer data)

###OFRoleReplyVendorData extends OFRoleVendorData

    static Instantiable<OFVendorData> instantiable =
            new Instantiable<OFVendorData>() {
                public OFVendorData instantiate() {
                    return new OFRoleReplyVendorData();
                }
            };
* static final int NXT_ROLE_REPLY = 11;
* static Instantiable<OFVendorData> getInstantiable() {
* OFRoleReplyVendorData() //super(NXT_ROLE_REPLY);
* OFRoleReplyVendorData(int role) // super(NXT_ROLE_REPLY, role); role 为 NX_ROLE_OTHER, NX_ROLE_MASTER or NX_ROLE_SLAVE.

###OFRoleRequestVendorData extends OFRoleVendorData

    static Instantiable<OFVendorData> instantiable =
            new Instantiable<OFVendorData>() {
                public OFVendorData instantiate() {
                    return new OFRoleRequestVendorData();
                }
            };

* static Instantiable<OFVendorData> getInstantiable()
* static final int NXT_ROLE_REQUEST = 10;
* OFRoleRequestVendorData() //super(NXT_ROLE_REPLY);
* OFRoleRequestVendorData(int role) //super(NXT_ROLE_REPLY, role); role 为 NX_ROLE_OTHER, NX_ROLE_MASTER or NX_ROLE_SLAVE.


###OFNiciraVendorExtensions

    boolean initialized = false;
```java
    static synchronized void initialize() { //Vendor 初始化的工作都这里
        if (initialized)
            return;

        // Configure openflowj to be able to parse the role request/reply
        // vendor messages.
        OFBasicVendorId niciraVendorId =
                new OFBasicVendorId(OFNiciraVendorData.NX_VENDOR_ID, 4);
        OFVendorId.registerVendorId(niciraVendorId);
        OFBasicVendorDataType roleRequestVendorData =
                new OFBasicVendorDataType(OFRoleRequestVendorData.NXT_ROLE_REQUEST,
                        OFRoleRequestVendorData.getInstantiable());
        niciraVendorId.registerVendorDataType(roleRequestVendorData);
        OFBasicVendorDataType roleReplyVendorData =
                new OFBasicVendorDataType(OFRoleReplyVendorData.NXT_ROLE_REPLY,
                        OFRoleReplyVendorData.getInstantiable());
        niciraVendorId.registerVendorDataType(roleReplyVendorData);

        initialized = true;
    }
```
所有的解释,看上文类结构即可


###OFVendorActions

    //核心代码块
    public static final void registerStandardVendorActions() {
        OFVendorActionRegistry registry = OFVendorActionRegistry.getInstance();
        registry.register(OFActionBigSwitchVendor.BSN_VENDOR_ID, new OFBigSwitchVendorActionFactory());
        registry.register(OFActionNiciraVendor.NICIRA_VENDOR_ID, new OFNiciraVendorActionFactory());
    }

###OFVendorActionRegistry

    private static class InstanceHolder {
        private final static OFVendorActionRegistry instance = new OFVendorActionRegistry();
    }

    Map <Integer, OFVendorActionFactory> vendorActionFactories;

    public static OFVendorActionRegistry getInstance()
    public OFVendorActionRegistry() //初始化 vendorActionFactories
    public OFVendorActionFactory register(int vendorId, OFVendorActionFactory factory)
    public OFVendorActionFactory get(int vendorId)

###interface OFVendorActionFactory

    /** parse the data from the wire, create and return a vendor-specific action.
     *
     * @param data contains a serialized vendor action at the current readerPosition.
     *    The full message is guaranteed to be available in the buffer.
     *
     * @return upon success returns a newly allocated vendor-specific
     *   action instance, and advances the readerPosition in data for the
     *   entire length. Upon failure, returns null and leaves the readerPosition
     *   in data unmodified.
     */
    OFActionVendor readFrom(ChannelBuffer data);

###OFBigSwitchVendorActionFactory implements OFVendorActionFactory

    static class OFActionBigSwitchVendorDemux extends OFActionBigSwitchVendor {
        OFActionBigSwitchVendorDemux() {
            super((short) 0); //subtype=0:
        }
    }

```
    OFActionVendor readFrom(ChannelBuffer data) {
        data.markReaderIndex();
        OFActionBigSwitchVendor demux = new OFActionBigSwitchVendorDemux();
        demux.readFrom(data); //从网络读出的数据初始化 subtype 1,2
        data.resetReaderIndex();

        switch(demux.getSubtype()) {
            case OFActionMirror.BSN_ACTION_MIRROR:
                OFActionMirror mirrorAction = new OFActionMirror((short) 0);
                mirrorAction.readFrom(data);
                return mirrorAction;
            case OFActionTunnelDstIP.SET_TUNNEL_DST_SUBTYPE:
                OFActionTunnelDstIP tunnelAction = new OFActionTunnelDstIP();
                tunnelAction.readFrom(data);
                return tunnelAction;
            default:
                logger.error("Unknown BSN vendor action subtype: "+demux.getSubtype());
                return null;
        }
    }
```



###OFAction implements Cloneable

    /**
     * Note the true minimum length for this header is 8 including a pad to 64
     * bit alignment, however as this base class is used for demuxing an
     * incoming Action, it is only necessary to read the first 4 bytes.  All
     * Actions extending this class are responsible for reading/writing the
     * first 8 bytes, including the pad if necessary.
     */
    public static int MINIMUM_LENGTH = 4;
    public static int OFFSET_LENGTH = 2;
    public static int OFFSET_TYPE = 0;

    protected OFActionType type;
    protected short length;

    public short getLength()
    public int getLengthU()
    public OFAction setLength(short length)
    public OFActionType getType()
    public void setType(OFActionType type)
    public void readFrom(ChannelBuffer data)
    public void writeTo(ChannelBuffer data)

###abstract class OFActionVendor extends OFAction
    public static int MINIMUM_LENGTH = 8;
    protected int vendor;

    public OFActionVendor()
    public int getVendor()
    public void setVendor(int vendor)
    public void writeTo(ChannelBuffer data)
    public void readFrom(ChannelBuffer data)
    String toString()
        ("ofaction;t={};l={}; vendor={}",
            this.getType(),
            this.getLength(),
            this.getVendor())

###abstract class OFActionBigSwitchVendor extends OFActionVendor

    public static int MINIMUM_LENGTH = 12;
    static int BSN_VENDOR_ID = OFBigSwitchVendorData.BSN_VENDOR_ID;
    protected int subtype;

    OFActionBigSwitchVendor(int subtype)
    public int getSubtype() {
    public void setSubtype(int subtype) {
    public void readFrom(ChannelBuffer data)
    public void writeTo(ChannelBuffer data)
    String toString()
        ("ofaction;t={};l={}; vendor={}; subtype={}",
            this.getType(),
            this.getLength(),
            this.getVendor(),
            this.getSubtype())

###OFActionMirror extends OFActionBigSwitchVendor
    static int MINIMUM_LENGTH = 12;
    static int BSN_ACTION_MIRROR = 1; // 初始化 OFActionBigSwitchVendor.subtype
    int destPort;
    int vlanTag;
    byte copyStage;
    byte pad0;
    byte pad1;
    byte pad2;

    OFActionMirror(short portNumber)
    int getDestPort()
    void setDestPort(int destPort)
    int getVlanTag()
    void setVlanTag(int vlanTag)
    byte getCopyStage()
    void setCopyStage(byte copyStage)
    void readFrom(ChannelBuffer data)
    void writeTo(ChannelBuffer data)

    String toString()
        ("ofaction;t={};l={}; vendor={}; subtype={}
            [BSN-MIRROR, Dest Port: {}, Vlan: {}, Copy Stage: {}]",
            this.getType(),
            this.getLength(),
            this.getVendor(),
            this.getSubtype(),
            this.getDestPort(),
            this.getVlanTag(),
            this.getCopyStage())

###OFActionTunnelDstIP extends OFActionBigSwitchVendor

    public final static int MINIMUM_LENGTH_TUNNEL_DST = 16;
    public  final static int SET_TUNNEL_DST_SUBTYPE = 2;// 初始化 OFActionBigSwitchVendor.subtype
    protected int dstIPAddr;

    OFActionTunnelDstIP()
    OFActionTunnelDstIP(int dstIPAddr)
    int getTunnelDstIP()
    void setTunnelDstIP(int ipAddr)
    void readFrom(ChannelBuffer data)
    void writeTo(ChannelBuffer data)
    String toString()
        ("ofaction;t={};l={}; vendor={}; subtype={}
            [BSN-SET-TUNNEL-DST-IP, IP: {}]",
            this.getType(),
            this.getLength(),
            this.getVendor(),
            this.getSubtype(),
            this.getTunnelDstIP())

###OFNiciraVendorActionFactory implements OFVendorActionFactory

    static class OFActionNiciraVendorDemux extends OFActionNiciraVendor {
        OFActionNiciraVendorDemux() {
            super((short) 0);
        }
    }

```
    public OFActionVendor readFrom(ChannelBuffer data) {
        data.markReaderIndex();
        OFActionNiciraVendorDemux demux = new OFActionNiciraVendorDemux();
        demux.readFrom(data);
        data.resetReaderIndex();

        switch(demux.getSubtype()) {
            case OFActionNiciraTtlDecrement.TTL_DECREMENT_SUBTYPE:
                OFActionNiciraTtlDecrement ttlAction = new OFActionNiciraTtlDecrement();
                ttlAction.readFrom(data);
                return ttlAction;
            default:
                logger.error("Unknown Nicira vendor action subtype: "+demux.getSubtype());
                return null;
        }
    }
```

###OFActionNiciraVendor extends OFActionVendor

    public static int MINIMUM_LENGTH = 16;
    public static int NICIRA_VENDOR_ID = OFNiciraVendorData.NX_VENDOR_ID;
    protected short subtype;
    protected OFActionNiciraVendor(short subtype) {

###OFActionNiciraTtlDecrement extends OFActionNiciraVendor

    static int MINIMUM_LENGTH_TTL_DECREMENT = 16;
    static final short TTL_DECREMENT_SUBTYPE = 18; //初始化 OFActionNiciraVendor subtype
    OFActionNiciraTtlDecrement()
    void readFrom(ChannelBuffer data) //多读 6 Byte
    void writeTo(ChannelBuffer data)  //多写 6 个 0 Byte
    String toString()
        ("ofaction;t={};l={}; vendor={}; subtype={}[NICIRA-TTL-DECR]",
            this.getType(),
            this.getLength(),
            this.getVendor(),
            this.getSubtype())




###OFBigSwitchVendorExtensions
    private static boolean initialized = false;

```
    public static synchronized void initialize() {
        if (initialized)
            return;

        OFBasicVendorId bsnVendorId =
                new OFBasicVendorId(OFBigSwitchVendorData.BSN_VENDOR_ID, 4);
        OFVendorId.registerVendorId(bsnVendorId);

        // register data types used for big tap
        OFBasicVendorDataType setEntryVendorData =
                new OFBasicVendorDataType(
                         OFNetmaskSetVendorData.BSN_SET_IP_MASK_ENTRY,
                         OFNetmaskSetVendorData.getInstantiable());
        bsnVendorId.registerVendorDataType(setEntryVendorData);

        OFBasicVendorDataType getEntryVendorDataRequest =
                new OFBasicVendorDataType(
                         OFNetmaskGetVendorDataRequest.BSN_GET_IP_MASK_ENTRY_REQUEST,
                         OFNetmaskGetVendorDataRequest.getInstantiable());
        bsnVendorId.registerVendorDataType(getEntryVendorDataRequest);

        OFBasicVendorDataType getEntryVendorDataReply =
                new OFBasicVendorDataType(
                         OFNetmaskGetVendorDataReply.BSN_GET_IP_MASK_ENTRY_REPLY,
                         OFNetmaskGetVendorDataReply.getInstantiable());
        bsnVendorId.registerVendorDataType(getEntryVendorDataReply);

        // register data types used for tunneling
        OFBasicVendorDataType getIntfIPVendorDataRequest =
                new OFBasicVendorDataType(
                          OFInterfaceIPRequestVendorData.BSN_GET_INTERFACE_IP_REQUEST,
                          OFInterfaceIPRequestVendorData.getInstantiable());
        bsnVendorId.registerVendorDataType(getIntfIPVendorDataRequest);

        OFBasicVendorDataType getIntfIPVendorDataReply =
                new OFBasicVendorDataType(
                          OFInterfaceIPReplyVendorData.BSN_GET_INTERFACE_IP_REPLY,
                          OFInterfaceIPReplyVendorData.getInstantiable());
        bsnVendorId.registerVendorDataType(getIntfIPVendorDataReply);
    }
```

###OFBigSwitchVendorData implements OFVendorData

* int BSN_VENDOR_ID = 0x005c16c7;
* protected int dataType;

* OFBigSwitchVendorData(int dataType)
* int getDataType()
* void setDataType(int dataType)
* int getLength()
* void readFrom(ChannelBuffer data, int length)
* void writeTo(ChannelBuffer data)

###OFBsnL2TableVendorData extends OFBigSwitchVendorData

    boolean l2TableEnabled;
    short l2TablePriority;

    OFBsnL2TableVendorData(int dataType)
    OFBsnL2TableVendorData(int dataType, boolean l2TableEnabled, short l2TablePriority)
    boolean isL2TableEnabled()
    short getL2TablePriority()
    void setL2TableEnabled(boolean l2TableEnabled)
    void setL2TablePriority(short l2TablePriority)
    int getLength()
    void readFrom(ChannelBuffer data, int length)
    void writeTo(ChannelBuffer data)

###OFBsnL2TableSetVendorData extends OFBsnL2TableVendorData

    protected static Instantiable<OFVendorData> instantiableSingleton =
        new Instantiable<OFVendorData>() {
            public OFVendorData instantiate() {
                return new OFBsnL2TableSetVendorData();
            }
        };

    public static final int BSN_L2_TABLE_SET = 12;

    public static Instantiable<OFVendorData> getInstantiable()
    public OFBsnL2TableSetVendorData()
    public OFBsnL2TableSetVendorData(boolean l2TableEnabled, short l2TablePriority)

###OFBsnPktinSuppressionSetRequestVendorData extends OFBigSwitchVendorData

    protected static Instantiable<OFVendorData> instantiableSingleton =
            new Instantiable<OFVendorData>() {
                @Override
                public OFVendorData instantiate() {
                    return new OFBsnL2TableSetVendorData();
                }
            };

    static Instantiable<OFVendorData> getInstantiable()
    int BSN_PKTIN_SUPPRESSION_SET_REQUEST = 11; //dataType
    protected boolean suppressionEnabled;
    protected short idleTimeout;
    protected short hardTimeout;
    protected short priority;
    protected long cookie;
    public OFBsnPktinSuppressionSetRequestVendorData()

###OFInterfaceIPReplyVendorData extends OFBigSwitchVendorData
    protected List<OFInterfaceVendorData> interfaces;
    protected int length;

    protected static Instantiable<OFVendorData> instantiable =
            new Instantiable<OFVendorData>() {
                public OFVendorData instantiate() {
                    return new OFInterfaceIPReplyVendorData();
                }
    };

    public static Instantiable<OFVendorData> getInstantiable()
    public static final int BSN_GET_INTERFACE_IP_REPLY = 10;
    public OFInterfaceIPReplyVendorData()
    public int getLength()
    public void setLength(int length)
    public List<OFInterfaceVendorData> getInterfaces()
    public void setInterfaces(List<OFInterfaceVendorData> intfs)
    public void readFrom(ChannelBuffer data, int length)
    public void writeTo(ChannelBuffer data)

###OFInterfaceIPRequestVendorData extends OFBigSwitchVendorData

    protected static Instantiable<OFVendorData> instantiable =
            new Instantiable<OFVendorData>() {
                public OFVendorData instantiate() {
                    return new OFInterfaceIPRequestVendorData();
                }
    };

    public static Instantiable<OFVendorData> getInstantiable()
    public static final int BSN_GET_INTERFACE_IP_REQUEST = 9;
    public OFInterfaceIPRequestVendorData()
    public int getLength()
    public void readFrom(ChannelBuffer data, int length)
    public void writeTo(ChannelBuffer data)

###OFInterfaceVendorData

    public static int MINIMUM_LENGTH = 32;
    private static int OFP_ETH_ALEN = 6;
    private static int OFP_MAX_PORT_NAME_LEN = 16;

    protected byte[] hardwareAddress;
    protected String name;
    protected int ipv4Addr;
    protected int ipv4AddrMask;

    public byte[] getHardwareAddress()
    public void setHardwareAddress(byte[] hardwareAddress)
    public int getIpv4Addr()
    public void setIpv4Addr(int ipv4Addr)
    public void setIpv4AddrMask(int ipv4AddrMask)
    public String getName()
    public void setName(String name)
    public void writeTo(ChannelBuffer data)
    public void readFrom(ChannelBuffer data)

###OFNetmaskVendorData extends OFBigSwitchVendorData

    protected byte tableIndex;
    protected byte pad1;
    protected byte pad2;
    protected byte pad3;
    protected int  netMask;

    public OFNetmaskVendorData(int dataType)
    public OFNetmaskVendorData(int dataType, byte table_index, int netmask)
    public byte getTableIndex()
    public void setTableIndex(byte tableIndex)
    public int getNetMask()
    public void setNetMask(int netMask)
    public int getLength()
    public void readFrom(ChannelBuffer data, int length)
    public void writeTo(ChannelBuffer data)


###OFMirrorGetVendorDataReply extends OFNetmaskVendorData

    protected static Instantiable<OFVendorData> instantiable =
        new Instantiable<OFVendorData>() {
        public OFVendorData instantiate() {
            return new OFMirrorGetVendorDataReply();
        }
    };
    static Instantiable<OFVendorData> getInstantiable()
    static final int BSN_GET_MIRRORING_REPLY = 5;
    OFMirrorGetVendorDataReply()
    OFMirrorGetVendorDataReply(byte tableIndex, int netMask)

###OFMirrorGetVendorDataRequest extends OFNetmaskVendorData


    protected static Instantiable<OFVendorData> instantiable =
        new Instantiable<OFVendorData>() {
        public OFVendorData instantiate() {
            return new OFMirrorGetVendorDataRequest();
        }
    };

    static Instantiable<OFVendorData> getInstantiable() {
    static final int BSN_GET_MIRRORING_REQUEST = 4;
    OFMirrorGetVendorDataRequest() {
    OFMirrorGetVendorDataRequest(byte tableIndex, int netMask) {

###OFMirrorSetVendorData extends OFBigSwitchVendorData
    public static final int BSN_SET_MIRRORING = 3;
    protected byte reportMirrorPorts;
    protected byte pad1;
    protected byte pad2;
    protected byte pad3;

    public OFMirrorSetVendorData()
    public byte getReportMirrorPorts()
    public void setReportMirrorPorts(byte report)
    public int getLength()
    public void readFrom(ChannelBuffer data, int length)
    public void writeTo(ChannelBuffer data)

###OFNetmaskGetVendorDataReply extends OFNetmaskVendorData
    protected static Instantiable<OFVendorData> instantiable =
        new Instantiable<OFVendorData>() {
        public OFVendorData instantiate() {
            return new OFNetmaskGetVendorDataReply();
        }
    };

    static Instantiable<OFVendorData> getInstantiable()
    static final int BSN_GET_IP_MASK_ENTRY_REPLY = 2;
    OFNetmaskGetVendorDataReply()
    OFNetmaskGetVendorDataReply(byte tableIndex, int netMask)

###OFNetmaskGetVendorDataRequest extends OFNetmaskVendorData
    protected static Instantiable<OFVendorData> instantiable =
        new Instantiable<OFVendorData>() {
        public OFVendorData instantiate() {
            return new OFNetmaskGetVendorDataRequest();
        }
    };

    public static Instantiable<OFVendorData> getInstantiable()
    public static final int BSN_GET_IP_MASK_ENTRY_REQUEST = 1;
    public OFNetmaskGetVendorDataRequest()
    public OFNetmaskGetVendorDataRequest(byte tableIndex, int netMask)

###OFNetmaskSetVendorData extends OFNetmaskVendorData

    protected static Instantiable<OFVendorData> instantiable =
        new Instantiable<OFVendorData>() {
        public OFVendorData instantiate() {
            return new OFNetmaskSetVendorData();
        }
    };

    static Instantiable<OFVendorData> getInstantiable()
    public static final int BSN_SET_IP_MASK_ENTRY = 0;
    public OFNetmaskSetVendorData()
    public OFNetmaskSetVendorData(byte tableIndex, int netMask)

