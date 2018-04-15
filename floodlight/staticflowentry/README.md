
* 模块启动的时候, 订阅数据库表表名为　controller_staticflowtableentry　的表的修改和删除消息．当数据库中的表或记录更新, 就将起更新到本模块关联的的对象及交换机
* 模块启动的时候, 从数据库读取所有流表, 初始化 entriesFromStorage 和 entry2dpid. 
* 模块订阅流表删除消息,当流表删除后, 如果流表属于当前模块的, 就阻止其被后续其他订阅者处理.
* 模块订阅交换机更新消息, 每当有新的交换机增加到Controller, 就将对应交换机的流表下发到该交换机. 
* 模块订阅控制器变化消息, 当Controller 角色由 ACTIVE 转为 STANDBY 的时候, 删除所有流表; 当 
Controller 从 STANDBY 转换为 ACTIVE 的时候从数据库读取所有流表, 初始化 entriesFromStorage 
和 entry2dpid.


#IStaticFlowEntryPusherService.java

##IStaticFlowEntryPusherService

* void addFlow(String name, OFFlowMod fm, DatapathId swDpid)
* void deleteFlow(String name)
* void deleteFlowsForSwitch(DatapathId dpid)
* void deleteAllFlows()
* Map<String, Map<String, OFFlowMod>> getFlows()
* Map<String, OFFlowMod> getFlows(DatapathId dpid)

#StaticFlowEntries.java

##class StaticFlowEntries

###关键变量

int INFINITE_TIMEOUT = 0  //流表过期时间, 0 表示永远不过期

###static U64 computeEntryCookie(int userCookie, String name)

根据 name 和 StaticFlowEntryPusher.STATIC_FLOW_APP_ID 生成 cookie

###static void initDefaultFlowMod(OFFlowMod.Builder fmb, String entryName)

设置流表默认选项. 

###static String getEntryNameFromJson(String fmJson)

解析 json 获取流表名

问题: 此处 String 比较用 ==" 没有问题?

###static Map<String, Object> flowModToStorageEntry(OFFlowMod fm, String sw, String name)

将流表信息写入 HashMap<String, Object>() 结构中, 返回该 HashMap

###static Map<String, Object> jsonToStorageEntry(String fmJson)

解析 json 格式的流表信息为 HashMap 形式的流表信息


##StaticFlowEntryPusher

###关键变量

    int STATIC_FLOW_APP_ID = 10 //静态流表的 APP ID, 主要用来区别不同的
    TABLE_NAME = "controller_staticflowtableentry" //数据库中存取的流表的 table 名称

####其他模块

    IFloodlightProviderService floodlightProviderService
    IOFSwitchService switchService
    IStorageSourceService storageSourceService
    IRestApiService restApiService
    IHAListener haListener

    Map<String, Map<String, OFFlowMod>> entriesFromStorage //存取所有的流表项
    分别为 <dpid,  <entryname,  OFFlowMod>>, 其中 dpid = sw.getId.toString()  dpid= entry2dpid(entryname)

    Map<String, String> entry2dpid : <entry,dpid> //存取流表名与交换机的映射


###Command receive(IOFSwitch sw, OFMessage msg, FloodlightContext cntx)


###int countEntries()

统计流表数，　即entriesFromStorage的 size

###void sendEntriesToSwitch(long switchId)

将 entriesFromStorage 属于交换机　switchId 的流表写入该交换机. 即遍历 entriesFromStorage.get(switchId)
的所有流表，并按照 priority 排序，之后依次写到 ID 为 switchId 的交换机

TODO: 

如果 switchService 中　switchId 不存在, log.warn 
如果 entriesFromStorage 中  switchService.getSwitch(switchId).getId().toString() 不存在, log.warn  　　


###Map<String, String> computeEntry2DpidMap(Map<String, Map<String, OFFlowMod>> map))

主要用于初始化　entry2dpid. map 的格式为 Map< dpid, Map< entryName, OFFlowMod >> 建立与之对应的 
Map< entryName,dpid > 的映射. 

###Map<String, Map<String, OFFlowMod>> readEntriesFromStorage()

从数据库中读取表 TABLE_NAME("controller_staticflowtableentry") 的每条记录，调用parseRow()解析后,将其写入 
Map<dpid, Map<entryName, OFFlowMod>> 的 ConcurrentHashMap 中．　

###void parseRow(Map<String, Object> row, Map<String, Map<String, OFFlowMod>> entries)

将从数据库读出来的一条记录转换为 Map<dpid, Map<entryName, OFFlowMod>>, 存储到 entries


##订阅　IStorageSourceListener 消息

###void rowsModified(String tableName, Set<Object> rowKeys)

同步数据库更改操作到 entriesFromStorage 和 entry2dpid 及 交换机

* 由于模块只订阅了表　controller_staticflowtableentry　的消息，所以，这里　tableName　是确定的
* 从数据库中取出所有在 rowKeys 中的记录, 调用 parseRow() 存储到 HashMap 中. 
* 对于数据库中属于每台交换机的每条记录: 如果 entriesFromStorage 中存在, 就删除之. 
* 对于数据库中的 newFlowMod　与　entriesFromStorage 中对应的 oldFlowMod:

1 newFlowMod 和 oldFlowMod 都不为 null 

* 如果 Match, Cookie, Priority都一致, 将 newFlowMod 加入 entriesFromStorage, 更新 entry2dpid, 并将流表修改加入 outQueue
* 如果　newFlowMod 和 oldFlowMod 在同一交换机, 将 newFlowMod 加入 entriesFromStorage, 更新 entry2dpid, outQueue 增加删除旧流表, 增加新流表的操作; 
* 如果　newFlowMod 和 oldFlowMod 不在同一交换机, 将 newFlowMod 加入 entriesFromStorage, 更新 entry2dpid 后, 直接下发流表到不同的交换机 

2 newFlowMod 不为 null oldFlowMod 为 null

将 newFlowMod 加入 entriesFromStorage, 更新 entry2dpid, 并将流表新加操作加入 outQueue

3 newFlowMod 为 null

从 entriesFromStorage 删除 newFlowMod 对应的 entry, 并更新 entry2dpid

* 最后将 outQueue 中的消息, 发送给对应的交换机

问题: 

entriesFromStorage.get 操作可能抛出 nullPointerException 

entriesFromStorage.get(dpid).put(entry, addTmp) addTmp 是否会抛出异常. 因为类型不匹配

###void rowsDeleted(String tableName, Set<Object> rowKeys)

同步数据库删除操作到entriesFromStorage 和 entry2dpid 及 交换机, 即遍历 rowKeys, 调用 deleteStaticFlowEntry() 删除对应流表项, 

###void deleteStaticFlowEntry(String entryName)

从 entriesFromStorage 删除ID 为 entryName 的流表, 并同步到交换机. 

问题: 这里 entriesFromStorage 的参数校验不周全. 
TODO: 如果 entryName 不存在, log.wran


###void writeOFMessagesToSwitch(DatapathId dpid, List<OFMessage> messages)

将 message 发送给交换机(DatapathId 为 dpid)

###writeOFMessageToSwitch(DatapathId dpid, OFMessage message)

将 message 发送给交换机(DatapathId 为 dpid)

###writeFlowModToSwitch(DatapathId dpid, OFFlowMod flowMod)

调用 writeFlowModToSwitch() 将流表写入交换机(DatapathId 为 dpid)

###void writeFlowModToSwitch(IOFSwitch sw, OFFlowMod flowMod)

将 flowMod 流表写入交换机 sw



##订阅 IOFMessageListener 消息

###Command receive(IOFSwitch sw, OFMessage msg, FloodlightContext cntx)

接受流表删除消息后, 调用 handleFlowRemoved 处理.

###Command handleFlowRemoved(IOFSwitch sw, OFFlowRemoved msg, FloodlightContext cntx)

如果流表的 cookie 是 STATIC_FLOW_APP_ID, 该消息停止被后续处理.


##订阅 IOFSwitchListener　消息

###void switchAdded(DatapathId switchId)

每当有交换机增加, 调用　sendEntriesToSwitch(switchId) 将　entriesFromStorage 中属于交换机　
switchId　的流表下发到该交换机

###void switchRemoved(DatapathId switchId)

什么也不做

###void switchActivated(DatapathId switchId)

什么也不做

###void switchChanged(DatapathId switchId)

什么也不做

###void switchPortChanged(DatapathId switchId,OFPortDesc port,PortChangeType type)

什么也不做


##实现 IHAListener

###void transitionToActive()

从数据库读取所有流表, 初始化 entriesFromStorage 和 entry2dpid 两个变量

###void controllerNodeIPsChanged

什么也不做

###String getName()

返回 staticflowentry

###boolean isCallbackOrderingPrereq(HAListenerTypeMarker type,  String name)

返回 false

###boolean isCallbackOrderingPostreq(HAListenerTypeMarker type,  String name)

返回 false

###void transitionToStandby()

删除所有流表


##实现 IStaticFlowEntryPusherService

###void addFlow(String name, OFFlowMod fm, String swDpid)

解析 fm 为 fmMap =  Map<String, Object> 的格式, 之后调用 storageSourceService.insertRowAsync(TABLE_NAME, fmMap) 写入数据库

###void deleteFlow(String name)

调用 storageSourceService.deleteRowAsync(TABLE_NAME, name), 从数据库的表 TABLE_NAME 中删除名为 name 的记录

###void deleteAllFlows()

遍历 entry2dpid, 调用 deleteFlow(String name) 从数据库删除所有流表

###void deleteFlowsForSwitch(long dpid)

遍历 entry2dpid, 从数据库删除交换机 dpid 中的流表


##RESTFul 接口

支持流表查询, 添加, 删除

TODO:
StaticFlowEntryPusherResource 通过 IStaticFlowEntryPusherService 的 addFlow() 而不是直接操作数据库

##BUG

IStaticFlowEntryPusherService 的实现中,对流表的操作都是直接从数据库中操作, 没有更新 entriesFromStorage 和
entry2dpid, 这会导致与数据库中的数据不一致的问题. 只有等到模块重新启动或 Controller 角色变化才能使得数据同步.