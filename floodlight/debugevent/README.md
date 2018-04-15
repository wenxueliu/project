
#概述

一个 DebugEvent 由 eventInfo 和 List< Event> 组成, eventInfo 是 List< Event> 的元数据, 
eventInfo 中的 eventId 来唯一标志, 包括 DebugEventHistory 和 LocalEventHistory 分别代表
全局(多线程)的和本地的(当前线程) 的 debugEvent. LocalEventHistory 通过 flush* 方法刷新本地到
全局

* EventInfoResource : EventInfo 和 List<EventResource> 类构建
* DebugEventAppender : 一个使用 DebugEventService 的实例类
* DebugEventService : 实际提供服务的类. 因为实现了 IDebugEventService 接口

#使用案例

    //模块定义
    IDebugEventService debugEventService;
    IEventCategory<DirectLinkEvent> eventCategory

    //模块 init() 初始化
    debugEventService = context.getServiceImpl(IDebugEventService.class);
    registerLinkDiscoveryDebugEvents() {
        eventCategory = debugEventService.buildEvent(DirectLinkEvent.class)
                            .setModuleName(PACKAGE)
                            .setEventName("linkevent")
                            .setEventDescription("Direct OpenFlow links discovered or timed-out")
                            .setEventType(EventType.ALWAYS_LOG)
                            .setBufferCapacity(100)
                            .register();
    }    

    //具体方法中调用 
    eventCategory.newEventNoFlush(new DirectLinkEvent(lt.getSrc(),
                lt.getSrcPort(), lt.getDst(), lt.getDstPort(), "direct-link-added::rcvd LLDP"))

    eventCategory.newEventNoFlush(new DirectLinkEvent(lt.getSrc(),
                lt.getSrcPort(), lt.getDst(), lt.getDstPort(),"link-port-state-updated::rcvd LLDP"))

    eventCategory.newEventWithFlush(new DirectLinkEvent(lt.getSrc(),
                lt.getSrcPort(), lt.getDst(), lt.getDstPort(),
                "link-deleted::" + reason));

    public class DirectLinkEvent {
        @EventColumn(name = "srcSw", description = EventFieldType.DPID)
        DatapathId srcDpid;
        
        @EventColumn(name = "srcPort", description = EventFieldType.PRIMITIVE)
        OFPort srcPort;
        
        @EventColumn(name = "dstSw", description = EventFieldType.DPID)
        DatapathId dstDpid;

        @EventColumn(name = "dstPort", description = EventFieldType.PRIMITIVE)
        OFPort dstPort;

        @EventColumn(name = "reason", description = EventFieldType.STRING)
        String reason;

        public DirectLinkEvent(DatapathId srcDpid, OFPort srcPort, DatapathId dstDpid,        
                    OFPort dstPort, String reason) {
            this.srcDpid = srcDpid;
            this.srcPort = srcPort;
            this.dstDpid = dstDpid;
            this.dstPort = dstPort;
            this.reason = reason;
        }
    }

#EventResource.java

##class EventResource

用于记录 Event 的信息

    final Date timestamp;
    final long threadId
    final String threadName
    final String moduleEventName
    final ImmutableList<Metadata> dataFields
    final String dataString
    long eventInstanceId
    boolean acked

###class EventResourceBuilder

用于构建 EventResource 的 help 函数

    Date timestamp;
    long threadId
    String threadName
    String moduleEventName
    ImmutableList<Metadata> dataFields
    long eventInstanceId
    boolean acked

###static class Metadata

    final String eventClass
    final String eventData

#Event.java

##class Event

主要记录 Event 的所有信息

    final long eventInstanceId
    volatile boolean acked
    final long timeMs
    final long threadId
    final String threadName
    final Object eventData

###EventResource getFormattedEvent(Class<?> eventClass,String moduleEventName)

    当需要从获取某个 Event 的消息时, 通过该方法格式化信息. 即通过 EventResourceBuilder 和 customFormat 构造 EventResource。

###void customFormat(Class<?> clazz, Object eventData,EventResourceBuilder eventDataBuilder)

    通过 Annotations 来格式化类的输出,类似与 toString() 的功能. 即
    遍历 clazz 所有 Fields，找到出现 @EventColumn 的 Fields，从 DebugEventService.customFormatter 获取
    Fields 中声明 EventColumn 的 description 类型，调用对应的方法。 如 CustomFormatterPrimitive， 调用 
    CustomFormatterPrimitive.customFormat(obj, ec.name(), eventDataBuilder) 方法， 将 obj, ec.name 构造
    为 metadata，增加到 eventDataBuilder.dataFields.add(metadata)


#CustomFormatters.java

    主要是Event 的 customFormat() 方法中用, 作为解析 Annotations 的 help 类

##class CustomFormatterCollectionAttachmentPoint

###void customFormat(@Nullable Collection<SwitchPort> aps2, String name,EventResourceBuilder edb)

    将 aps2 变为 String apsStr2, 调用 edb.dataFields.add(new Metadata(name, apsStr2.toString()))

以下类类似

    class CustomFormatterCollectionIpv4
    class CustomFormatterCollectionObject
    class CustomFormatterDpid
    class CustomFormatterIpv4
    class CustomFormatterMac
    class CustomFormatterObject
    class CustomFormatterPrimitive
    class CustomFormatterSrefCollectionObject
    class CustomFormatterSrefObject
    class CustomFormatterString

#DebugEventAppender.java

    一个 DebugEventService 使用的实例

##功能概述 

1. 初始化创建一个 daemon thread， 调用 start() thread 开始执行， 但是只是空循环
2. 当调用 setDebugEventServiceImpl 后, 初始化 debugEvent 
3. 线程下次执行,发现 debugEvent 不为 NULL, 调用 registerDebugEventQueue() 后结束. 其中registerDebugEventQueue() 通过 debugEvent 构造 evWarnError. 并将其更新到 DebugEventService 的 allEvents currentEvents 中, 其他模块就可以通过 IDebugEventService 其他接口(如 getAllEventHistory())就可以获取当前 Event 的信息
4. 之后如果需要, 通过调用 append 就能将一个对象加入 LocalEventHistory 和 DebugEventHistory

##class DebugEventAppender.java

###关键变量

    static IDebugEventService debugEvent
    static IEventCategory<WarnErrorEvent> evWarnError
    static final Thread debugEventRegistryTask

###void setDebugEventServiceImpl(IDebugEventService debugEvent)

    初始化 debugEvent 变量, 对于当前工程来书只能是 DebugEventService 的实例化对象

###void append(E eventObject)
    
    每次调用该方法, 都将 eventObject 格式化为 WarnErrorEvent 的格式, 添加新的 Event 到 LocalEventHistory 并刷新到 DebugEventHistory. 

###static void registerDebugEventQueue()

    通过 debugEvent 构造 evWarnError, 并且注册到 DebugEventService 的全局事件中. 其他接口
    (如 getAllEventHistory()) 就可以获取当前 Event 的信息

###class WarnErrorEvent

    对 ch.qos.logback.classic.spi.ILoggingEvent 的格式化

####关键变量 

    String message
    Level level
    String threadName
    String logger


#class DebugEventResource.java
    
    主要用于获取 Event 信息的时候的 help 类

##class DebugEventResource

    final String MODULE_NAME_PREDICATE = "module-name"
    final String EVENT_NAME_PREDICATE = "event-name"
    final String LAST_PREDICATE = "num-of-events"
    final String EVENT_ID = "event-id"
    final String EVENT_INSTANCE_ID = "event-instance-id"
    final String ACKED = "acked"

##class EventInfoResource

    int eventId
    boolean enabled
    int bufferCapacity
    EventType etype
    String eventDesc
    String eventName
    String moduleName
    int numOfEvents
    boolean ackable
    ImmutableList<EventResource> events

记录 EventResource 和 EventInfo 的关系， 来源于 DebugEventHistory

#DebugEventService.java

通过 register 注册 Event, 通过 newEvent 初始化 LocalEventHistory,然后通 flush* 接口刷新到 DebugEventHistory

* eventIdCounter 构造全局唯一的 EventId 来标记 Event。
* allEvents 记录所有的全局 EventId 与 DebugEventHistory 的映射关系
* moduleEvents 记录所有的 module，eventName, eventId 的映射关系
* currentEvents 记录所有 enable 为 True（即EventType 为 ALWAYS_LOG） 的EventId.
* ModuleEvent 保存了所有的的 (module,event,eventId) 映射关系
* EventInfo 记录事件的元信息
* DebugEventHistory 存储所有的全局 EventInfo 及 List< Event >。
* LocalEventHistory 存储局部的 Event。
* threadlocalEvents 存储本线程的 eventId，LocalEventHistory 的映射关系
* threadlocalCurrentEvents 存储本线程的 eventId
* EventCategory 通过 EventId 创建 LocalEventHistory。
* EventCategoryBuilder 通过 register() 来初始化 allEvent，currentEvents, EventCategory. 也可以认为是 
buildEvent() 方法的 help 方法.
* 通过 newEvent() 创建存在于 allEvent 但不存在于 threadlocalEvents.get() 的 LocalEventHistory。
* 通过 flushEvent() 或 flushLocalToGlobal() 刷新 LocalEventHistory 到 DebugEventHistory。 

##class DebugEventService

    final AtomicInteger eventIdCounter = new AtomicInteger()
    final AtomicLong eventInstanceId = new AtomicLong(Long.MAX_VALUE)
    
    final ImmutableMap<EventFieldType, CustomFormatter<?>> customFormatter
    final ConcurrentHashMap<Integer, DebugEventHistory> allEvents : 存储所有是 Event
    final ConcurrentHashMap<String, ConcurrentHashMap<String, Integer>> moduleEvents <moduleName,<eventName，eventID>

    final Set<Integer> currentEvents = Collections.newSetFromMap(new ConcurrentHashMap<Integer, Boolean>())
 
    //Thread local event buffers used for maintaining event history local to a
    //thread. Eventually this locally maintained information is flushed into
    //the global event buffers.
    final ThreadLocal<Map<Integer, LocalEventHistory>> threadlocalEvents
    final ThreadLocal<Set<Integer>> threadlocalCurrentEvents //Thread local cache for event-ids that are currently active (enable == true)


###EventCategoryBuilder<T> buildEvent(Class<T> evClass)
    
    调用 EventCategoryBuilder<T>(evClass)  

###void flushLocalToGlobal(int eventId, LocalEventHistory le)

    bug: le.size 大于 DebugEventHistory 的容量会发生异常 removeFirst 可能抛出异常, 但由于只在 newEvent 创建 LocalEventHistory  限制不会大于 DebugEventHistory的容量，所以，目前不会出现这个问题。

    从 allEvents.get(eventId) 取出对应的 DebugEventHistory de， 

    如果 de.info.enable 为 true， 将 LocalEventHistory 加入到 DebugEventHistory， 如果 DebugEventHistory 的容量不够，就从队列头删除一部分，然后加入 LocalEventHistory。
    否则 le.enable = false, threadlocalCurrentEvents.get().remove(eventId)

###void newEvent(int eventId, boolean flushNow, Object eventData)

    如果 eventId 不存在于 threadlocalEvents.get()，但存在于 allEvents， 加入 threadlocalEvents.get() = thishist，创建对应的 Event，如果 thishist 中的 LocalEventHistory 满了或 flushNow 是 True， 调用 flushLocalToGlobal() 刷新到 DebugEventHistory。
    如果两者都不存在，抛异常
    
###void flushEvents()

    如果 this.threadlocalCurrentEvents.get() 中的 eventId, 如果在 this.threadlocalEvents.get() 中，调用
    flushLocalToGlobal() 刷新到 DebugEventHistory。

###List<EventInfoResource> getAllEventHistory()

    遍历 moduleEvents 所有 module 中的所有 eventId, 如果存在与 allevent 中，遍历对应 evenId 的 Event, 增加到存储
    EventInfoResource 的 moduleEventList

###List<EventInfoResource> getModuleEventHistory(String moduleName)

    类似 getAllEventHistory()，只是得到指定 module 的所有 evenId

###EventInfoResource getSingleEventHistory(String moduleName, String eventName,int numOfEvents)

    类似 getAllEventHistory()，只是得到指定 module 的制定 eventName 指定数量 numOfEvents
    
###void resetAllEvents()

    遍历 moduleEvents 所有 module 中的所有 eventId, 清除里面是 Event

###void resetAllModuleEvents(String moduleName)

    类似 resetAllEvents() 限定了 module

###void resetSingleEvent(String moduleName, String eventName)

    类似 resetAllEvents() 限定了 module 和 event

###void setAck(int eventId, long eventInstanceId, boolean ack)

    设置 allEvents 中的制定 eventId 中 Event.EventInstancId == eventInstanceId 的 ack

##class ShutdownListenenerDelegate

###void floodlightIsShuttingDown()

    调用 getAllEventHistory() 日志记录所有事件的信息。

###class EventInfo

    记录事件的元信息

    final int eventId
    final boolean enabled // True 即 etype = EventType.ALWAYS_LOG
    final int bufferCapacity
    int numOfEvents
    final EventType etype
    final String eventDesc
    final String eventName
    final String moduleName
    final String moduleEventName
    final Class<?> eventClass
    final boolean ackable

###class DebugEventHistory

    EventInfo einfo
    LinkedBlockingDeque<Event> circularEventBuffer

###class LocalEventHistory 

    boolean enabled
    int capacity
    ArrayList<Event> eventList

###class EventCategory<T>
    
    已经注册的 eventId

    final int eventId

####void newEventNoFlush(Object event)
    
    调用 newEvent(eventId, false, event)

####void newEventWithFlush(Object event)

    调用 newEvent(eventId, true, event)

###class EventCategoryBuilder<T>

    int eventId
    String moduleName
    String eventName
    String eventDescription
    EventType eventType
    Class<T> eventClass //A user defined class that annotates the fields with @EventColumn.
    int bufferCapacity
    boolean ackable

####EventCategory<T> register()

    moduleEvents.putIfAbsent(moduleName,new ConcurrentHashMap<String, Integer>())
    Integer eventExists = moduleEvents.get(moduleName).putIfAbsent(eventName, eventId)
    如果 eventExists 不为 Null，表面重复注册了已经存在的事件， 返回 new EventCategory<T>(eventExists)
    否则 构造 DebugEventHistory()， 将其放入 allEvent, 如果 enable 是true， 放入 currentEvents.put(eventId) 返回  new EventCategory<T>(this.eventId)