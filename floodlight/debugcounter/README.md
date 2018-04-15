
一个计数器由 moduleName(模块) counterHierarchy(所属节点) counterValue(计数值)组成. 即可以在一个模块下创建一棵树,
每个节点都有一个计数值. 我们可以对增加多个模块,每个模块增加多个计数器,对具体的一个节点的计数器进行增加,重置,获取. 
具体支持的操作可以参考接口 IDebugCounterService. 

使用非常简单, 首先调用 registerModule 注册模块, 然后调用 registerCounter() 注册属于这个模块的具体功能的计数器, 
之后调用 increment 来增加计数. 例如

    //模块开始定义
    IDebugCounterService debugCounterService;
    IDebugCounter ctrIncoming
    IDebugCounter ctrIgnoreSrcMacDrops;
    IDebugCounter ctrQuarantineDrops;
    IDebugCounter ctrLinkLocalDrops;
    IDebugCounter ctrLldpEol;

    //模块的 init() 方法初始化
    debugCounterService = context.getServiceImpl(IDebugCounterService.class)
    
    //模块的 init() 方法注册需要的计数器
    registerLinkDiscoveryDebugCounters();
        debugCounterService.registerModule(PACKAGE);
        ctrIncoming = debugCounterService.registerCounter(PACKAGE, "incoming",
                     "All incoming packets seen by this module");
        ctrLldpEol  = debugCounterService.registerCounter(PACKAGE, "lldp-eol",
                     "End of Life for LLDP packets");
        ctrLinkLocalDrops = debugCounterService.registerCounter(PACKAGE, "linklocal-drops",
                    "All link local packets dropped by this module");
        ctrIgnoreSrcMacDrops = debugCounterService.registerCounter(PACKAGE, "ignore-srcmac-drops",
                    "All packets whose srcmac is configured to be dropped by this module");    
        ctrQuarantineDrops = debugCounterService.registerCounter(PACKAGE, "quarantine-drops",
                    "All packets arriving on quarantined ports dropped by this module", IDebugCounterService.MetaData.WARN);

    //在具体的方法中调用 increment() (增加计数),reset()(重置计数)等操作


# IDebugCounter.java
#interface IDebugCounter 

对外接口

* void increment()
* void add(long incr)
* long getCounterValue()
* long getLastModified()
* void reset()

#IDebugCounterService.java

##interface IDebugCounterService

对外接口

* boolean registerModule(String moduleName)
* public IDebugCounter registerCounter(String moduleName, String counterHierarchy, ..)
* public boolean resetCounterHierarchy(String moduleName, String counterHierarchy);
* public void resetAllCounters()
* public boolean resetAllModuleCounters(String moduleName)
* public boolean removeCounterHierarchy(String moduleName, String counterHierarchy)
* public List<DebugCounterResource> getCounterHierarchy(String moduleName, String counterHierarchy)
* public List<DebugCounterResource> getAllCounterValues()
* public List<DebugCounterResource> getModuleCounterValues(String moduleName)

#DebugCounterImpl.java

##class DebugCounterImpl

###功能说明

    主要是对一个计数器的操作, 包括增加,重设,提取计数值,上次修改时间.

###变量说明

    final String moduleName : 模块名
    final String counterHierarchy : 所属节点
    final String description : 节点描述
    final ImmutableSet<IDebugCounterService.MetaData> metaData : 节点元数据
    final AtomicLong value = new AtomicLong() : 节点值
    final Date lastModified = new Date() : 节点上次修改

###方法实现

    所有方法参考 IDebugCounter, 实现非常简单, 故略. 

#CounterNode.java

##功能说明

    描述了 DebugCount 的一个节点, 每个节点都是一个 CounterNode，每个节点都包含从根节点到当前节点的层次(hierarchy)，
    及其列表（hierarchyElements）,当前节点的计数器，从当前节点开始的树

    该模块还是一个典型的 TreeMap 数据结构 iterable 和 iterator 的实现

##class CounterNode

##变量说明

    final String hierarchy               : null 表面是 root， 没有包含 "/" 的字符串是模块名(moduleName)
    final List<String> hierarchyElements : 将 hierarchy 以 "/" 分割后的列表（List）
    final DebugCounterImpl counter       : 当前节点计数器, 对于 root 和 moduleName 是 null
    final TreeMap<String, CounterNode> children = new TreeMap<>() : 当前节点开始的层次树

##方法实现分析

###void resetHierarchy()    
    
    调用迭代对象,重设每一个节点的计数器. 

###List<String> getHierarchyElements(String moduleName, String counterHierarchy)

    可能的问题: counterHierarchy 包含非期望的 "/"

    将 moduleNamel + (counterHierarchy 以"/" 分割后的列表) 组成的数组

###CounterNode newTree()

    初始化空的 CounterNode, 即树的初始化.

###CounterNode lookup(List<String> hierarchyElements)

    遍历 hierarchyElements 的元素，如果在 children 中不存在，返回 NULL， 否则返回最后一个叶子节点。

    例如 moduel/packet/drop 存在， 首先在 children 这棵树上查找 module 存在与否，之后，在module 
    的基础上查询 packet 是否存在，之后在 packet 基础上查询 drop 是否存储  

###CounterNode remove(List<String> hierarchyElements)      

    首先检查 hierarchyElements 是否存在与children 中， 如果存在，从 children 中删除 hierarchyElements 
    的最后一个元素，即删除层次树的某一个叶子节点。

    例如 moduel/packet/drop  存在， hierarchyElements 为 (module，packet，drop) 其中 drop 将被删除。

    这里要确保没有其他节点引用要删除的节点,否则会由问题.


###boolean addModule(String moduleName)

    如果 moduleName 存在，就重置该模块，否则，增加新模块 moduleName

###DebugCounterImpl addCounter(@Nonnull DebugCounterImpl counter)

    从 counter 获取它的 moduleName, 和层次结构，检查 counter 父节点是否存在与当前节点的子树中,如果存在,
    检查counter 是否存在,如果存在重置已经存在的，返回已经存在的。否则增加 counter 到层次树,返回 null


###static class CounterIterator implements Iterator<DebugCounterImpl> iterator()

    一个 TreeMap 数据结构的 Iterator 实现

#DebugCounterResource

##功能说明

    描述一个计数器的所有属性, 关键属性如 moduleName(模块名) counterHierarchy(当前计数器所属层次) metadata(元数据)
    counterValue(计数值) lastModified(上次更新时间)

##变量说明

    final Long counterValue
    final Long lastModified
    final String counterDesc
    final String counterHierarchy
    final String moduleName
    final ImmutableSet<MetaData> metadata
    final String metadataString

#DebugCounterServiceImpl

##变量说明

    final CounterNode root = CounterNode.newTree()
    final ReentrantReadWriteLock lock = new ReentrantReadWriteLock()

##方法说明


###boolean registerModule(String moduleName)

    root.addModule(module)    

###IDebugCounter registerCounter(@Nonnull String moduleName，@Nonnull String counterHierarchy,@Nonnull String counterDescription,@Nonnull MetaData... metaData)

    Bug : counterHierarchy 中如果包含 "/" 将引入 bug

    检查入口参数，构造 DebugCounterImpl conter 调用 root.addCount(counter), 如果已经存在,就返回原来的, 不存在返回新
    创建的 counter

###boolean resetInternal(List<String> hierarchyElements)   --BUG  hierarchyElements 为 NULL

    如果 hierarchyElements 中的每一个元素都存在与 root 中，对最后一个元素的子树调用 resetHierarchy() 重置之. 

    如果 hierarchyElements = {linkdisver, drop} drop 下的所有计数器都会重置
 
###boolean removeInternal(List<String> hierarchyElements)

    如果 hierarchyElements 存在于 root 中， 调用 root.remove(hierarchyElements) 删除最后一个元素


###boolean resetCounterHierarchy(String moduleName,String moduleName)
    
    调用 resetInternal(CounterNode.getHierarchyElements(moduleName, counterHierarchy))

###boolean resetAllModuleCounters(String moduleName)    

    调用 resetInternal(Collections.singletonList(moduleName))   

###void resetAllCounters()

    调用 root.resetHierarchy();

###removeCounterHierarchy(String moduleName, String counterHierarchy)

    调用 removeInternal(CounterNode.getHierarchyElements(moduleName, counterHierarchy))

###List<DebugCounterResource> getCountersFromNode(CounterNode node)

    遍历 node.getCountersInHierarchy() 所有元素，增加到 List 后返回 

###getCounterHierarchy(String moduleName, String counterHierarchy)

    getCountersFromNode(root.lookup(CounterNode.getHierarchyElements(moduleName, counterHierarchy)))

###List<DebugCounterResource> getAllCounterValues()

    getCountersFromNode(root)    

###List<DebugCounterResource> getModuleCounterValues(String moduleName)

    getCountersFromNode(root.lookup(Collections.singletonList(node)))       
