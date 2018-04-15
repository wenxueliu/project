

通过 IDebugCounter 的 counterId 标记一个计数器, 和对计数器进行操作

局部计时器在更新时, 如果 enable 就更新计数器, 如果 disable 就不更新计数器.

最多支持三级拓扑, 比如 moduleName/counterHierarchy:

    switch/00:00:00:00:01:02:03:04/pktin/drops where
    moduleName ==> "switch"  and
    counterHierarchy of 3 ==> "00:00:00:00:01:02:03:04/pktin/drops"

#IDebugCounter

计时器的接口类, 凡是 Flush 的不要用于 OFMessage 处理过程中, NoFlush 方法可用于
OFMessage 处理过程

* void updateCounterWithFlush() : Increments the counter by 1 thread-locally, and immediately flushes to the global counter storage.
* void updateCounterNoFlush() : Increments the counter by 1 thread-locally.
* void updateCounterWithFlush(int incr) : Increments the counter thread-locally by the 'incr' specified, and immediately flushes to the global counter storage.
* void updateCounterNoFlush(int incr) : Increments the counter thread-locally by the 'incr' specified.
* long getCounterValue() : Retrieve the value of the counter from the global counter store

#IDebugCounterService 

调试计数器接口类

#DebugCounter

实现 IDebugCounterService 接口类

##关键变量

counterIdCounter  : registered counters need a counter id
DebugCounterInfo[] allCounters : Global debug-counter storage across all threads. These are updated from the local per thread counters by the flush counters method.
ConcurrentHashMap<String, ConcurrentHashMap<String, CounterIndexStore>> moduleCounters : per module counters, indexed by the module name and storing three levels of
                                                                                         Counter information in the form of CounterIndexStore
Set<Integer> currentCounters : fast global cache for counter ids that are currently active
ThreadLocal<LocalCounterInfo[]> threadlocalCounters : Thread local debug counters used for maintaining counters local to a thread.
ThreadLocal<Set<Integer>> threadlocalCurrentCounters : Thread local cache for counter ids that are currently active.


##核心方法

###IDebugCounter registerCounter(String moduleName, String counterHierarchy, String counterDescription, CounterType counterType, String... metaData)

　 将 counterHierarchy 类型为 CounterType 的计数器加入 moduleName　

###void updateCounter(int counterId, int incr, boolean flushNow)


1. 获取线程局部的计数器, 并检查 counterId 对应的计数器是否存在
   * 如果不存在, 但全局计数器存在, 创建局部计数器, 如果全局计数器 enable, 并从活跃计时器列表中加入当前 counterId
   * 如果不存在, 并且全局计数器也不存在, 打错误日志, 退出
   * 如果存在, 继续
2. 如果线程局部计数器 enable, 更新计数器, 并检查是否需要 flushNow
   * 如果不需要刷新, 完成
   * 如果需要刷新, 检查全局计数器是否 enabled, 如果 enabled, 刷新到全局计数器, 并清除当前线程计数器, 如果 disable, 线程局部计数器 disable, 并从活跃计时器列表中清除当前 counterId
3. 如果线程局部计数器 disable, 完成. TODO 这是否应该输出警告信息

注: 这里对线程局部活跃计数器(threadlocalCurrentCounters )的操作是必须的. 这种 Lazy 更新的机制值得学习

###void flushCounters()

   将局部计数器更新到全局计数器

   Bug: 1. 如果全局计数器是 null, 会导致空指针异常
        2. 应该先同步全局的 enable 到局部, 再更新

###void resetCounterHierarchy(String moduleName, String counterHierarchy) {

    将 moduleName 中 counterHierarchy 及以下所有计时器清零

###void resetAllCounters()

    将所有模块的计数器都清零

###void resetAllModuleCounters(String moduleName)

    将 moduleName 所有计数器清零

###void enableCtrOnDemand(String moduleName, String counterHierarchy)

    将 moduleName 中 counterHierarchy 的计数器 enable

###void disableCtrOnDemand(String moduleName, String counterHierarchy)

    将 moduleName 中 counterHierarchy 的计数器, 如果 ctype=COUNT_ON_DEMAND,  disable 之

###List<DebugCounterInfo> getCounterHierarchy(String moduleName, String counterHierarchy)

     返回 moduleName 中 counterHierarchy 及以下的所有计数器组成的 List

###List<DebugCounterInfo> getAllCounterValues()

    返回所有模块的所有计数器

###List<DebugCounterInfo> getModuleCounterValues(String moduleName)

    返回 moduleName 的所有计数器

###boolean containsModuleCounterHierarchy(String moduleName, String counterHierarchy)

    moduleName 是否包含 counterHierarchy 的计数器

###boolean containsModuleName(String moduleName) {

    是否存在 moduleName 的计数器

###List<String> getModuleList()

    返回计数器的所有模块

###List<String> getModuleCounterList(String moduleName) {

    返回moduleName 下的所有计数器拓扑信息

###RetCtrInfo getCounterId(String moduleName, String counterHierarchy)

    将 moduleCounters.get(moduleName) 层级的拓扑扁平化

    moduleCounters:
        test
            str1,CounterIndexStore1
                 index     : 1
                 nextLevel : str2,CounterIndexStore2
                     index : 2
                     nextLevel : str3,CounterIndexStore3
            tr1,CounterIndexStore1
                 index     : 1
                 nextLevel : tr2,CounterIndexStore2
                     index : 2
                     nextLevel : tr3,CounterIndexStore3

    如果
        moduleName : test
        counterHierarchy : str1/str2/str3

    返回

    RetCtrInfo
        foundUptoLevel 3
        allLevelsFound true
        levels[0] str1
        levels[1] str2
        levels[2] str3

        hierarchical true
        ctrIds[0] 1
        ctrIds[1] 2
        ctrIds[2] 3

    如果
        moduleName : test
        counterHierarchy : str1/tr1

    变为

    RetCtrInfo
        foundUptoLevel 1
        allLevelsFound false
        levels[0] str1
        levels[1] str2
        levels[2] str3

        hierarchical true
        ctrIds[0] 1
        ctrIds[1] -1
        ctrIds[2] -1

###void addToModuleCounterHierarchy(String moduleName, int counterId, RetCtrInfo rci)

    将 counterId 加入 moduleName 的 rci 的下一级. 比如 moduleName=test, rci=str1/str2/str3, counterId = 3
    最后将 <str3, CounterIndexStore(3,null)> 加入 moduleName 的计数器

###ArrayList<Integer> getHierarchyBelow(String moduleName, RetCtrInfo rci) {

    将 moduleCounters moduleName 中 rci 层级以下的所有 index (即 counterId) 加入 ArrayList 之后返回
    TODO: 如果 rci 是不存在的层级结构,存在空指针异常

###void getIdsAtLevel(Map<String, CounterIndexStore> hcy, ArrayList<Integer> retval, int level)

    将 hcy 所有层级加入 retval

###void printAllCounterIds() {

    答应所有的计数器 id


##内部类

###MutableLong

实现基本计数功能

long value = 0;

* void increment()
* void increment(long incr)
* long get()
* void set(long val)

###CounterInfo

保持计数器的元数据

    String moduleCounterHierarchy;
    String counterDesc;
    CounterType ctype;
    String moduleName;
    String counterHierarchy;
    int counterId;
    boolean enabled;
    String[] metaData;

###DebugCounterInfo

实现全局的计数器的功能, 跨越多个线程, 因此计数是原子的, 包含 CounterInfo

    CounterInfo cinfo;
    AtomicLong cvalue;

###CounterIndexStore

提供计数器的拓扑

    int index;
    Map<String, CounterIndexStore> nextLevel;

###LocalCounterInfo

线程局部计数器, 由于是线程局部的, 因此不需要加锁

    boolean enabled;
    MutableLong cvalue;

###CounterImpl

实现 IDebugCounter 接口

    int counterId : 唯一标记一个计数器, 0 ~ MAX_COUNTERS 之间.

* void updateCounterNoFlush() :
* void updateCounterWithFlush() :
* void updateCounterNoFlush(int incr) :
* void updateCounterNoFlush(int incr) :
* long getCounterValue() : 根据 allCounters[counterId].cvalue.get()
* boolean validCounterId() : counterId 是否有效

###class RetCtrInfo

    boolean allLevelsFound; // counter indices found all the way down the hierarchy
    boolean hierarchical; // true if counterHierarchy is hierarchical
    int foundUptoLevel;
    int[]  ctrIds;
    String[] levels;





#CounterStore

##变量

####pktinCounters

pktinCounters = new ConcurrentHashMap<CounterKeyTuple, List<ICounter>>()   packetin 计数

    //对于 PacketIn, 通过 msg_type dpid, 网卡类型，如果是 ipv4，还包括协议类型
    CounterKeyTuple{
        byte msgType;
        long dpid;
        short l3type;
        byte l4type;
    }

    ICounter :
        SimpleConter{
            Date date = new Date();
            CountValue.CounterType type = enum CountValue.CounterType{
                                LONG;
                                DOUBLE
            CountValue counter;
            Date samplingTime;
                            }
        }

每一次 createPacketInCounters 执行, 如果对应的 CounterKeyTuple 不存在, nameToCEIndex 增加如下对象

    <controllerCounterName,             <SimpleConter1, controllerCounterName>>
	<switchCounterName,                 <SimpleConter2, switchCounterName>>
	<controllerL2CategoryCounterName,   <SimpleConter3, controllerL2CategoryCounterName>>
	<switchL2CategoryCounterName,       <SimpleConter4, switchL2CategoryCounterName>>
	<controllerL3CategoryCounterName,   <SimpleConter5, controllerL3CategoryCounterName>>
	<switchL3CategoryCounterName,       <SimpleConter6, switchL3CategoryCounterName>>
	<controllerL4CategoryCounterName,   <SimpleConter7, controllerL4CategoryCounterName>>
	<switchL4CategoryCounterName,       <SimpleConter8, switchL4CategoryCounterName>>

    List<ICounter> = <<SimpleConter1> <SimpleConter2> ...>

####pktoutCounters

pktoutCounters = new ConcurrentHashMap<CounterKeyTuple, List<ICounter>>()  packetOut 计数

    //对于 PacketOut，通过 msg_type 和 交换机 dpid 来惟一标志一种类型
    CounterKeyTuple{
        byte msgType;
        long dpid;
        short l3type;
        byte l4type;
    }

    ICounter :
        SimpleConter{
            Date date = new Date();
            CountValue.CounterType type = enum CountValue.CounterType{
                                LONG;
                                DOUBLE
            CountValue counter;
            Date samplingTime;
                            }
        }

每一次 getPktOutFMCounters 执行， 如果对应的 CounterKeyTuple 不存在，nameToCEIndex 增加如下对象

    <controllerFMCounterName, <SimpleConter1, controllerFMCounterName>>
    <switchFMCounterName,     <SimpleConter2, switchFMCounterName>>

    List<ICounter> = <<SimpleConter1> <SimpleConter2>>

####pktin_local_buffer

pktin_local_buffer = new ThreadLocal<Map<CounterKeyTuple,MutableInt>>()

多线程共享，所有 packetin 表 <表的惟一标志，数目>

    //对于 PacketIn, 通过 msg_type dpid, 网卡类型，如果是 ipv4，还包括协议类型
    CounterKeyTuple{
        byte msgType;
        long dpid;
        short l3type;
        byte l4type;
    }

    MutableInt{
        int value
    }


####pktout_local_buffer

pktout_local_buffer = new ThreadLocal<Map<CounterKeyTuple,MutableInt>>()

多线程共享,多有 packetout 表

    //对于 PacketOut，通过 msg_type 和 交换机 dpid 来惟一标志一种类型
    CounterKeyTuple{
        byte msgType;
        long dpid;
        short l3type;
        byte l4type;
    }

    MutableInt{
        int value
    }

#### nameToCEIndex

nameToCEIndex =  new ConcurrentHashMap<String, CounterEntry>()

	nameToCEIndex {
		String key ;
		CounterEntry ce = CounterEntry {
								ICounter counter = SimpleConter{
														Date date;
														CountValue.CounterType type = enum CountValue.CounterType{
																			LONG;
																			DOUBLE
																		}
                                                        CountValue counter CountValue {
                                                                            CounterType type;
                                                                            long longValue;
                                                                            double doubleValue;
                                                                        };
                                                        Date samplingTime;//最近的更新时间
													}
								String title;
			}

	}

####layeredCategories

layeredCategories = new ConcurrentHashMap<NetworkLayer, Map<String, List<String>>> ()

    enum NetworkLayer{
         L2, L3, L4
    }
    Map<String,List<String>>
        String :  groupCounterName = switchID + TitleDelimitor + counterName
                groupCounterName = switchID + TitleDelimitor + portID + TitleDelimitor + counterName
        List<Stirng> : subCategory


##方法

####updatePktOutFMCounterStoreLocal(IOFSwitch sw, OFMessage m)

如果 sw m 构成的 CounterKeyTuple 存在，增加 pktout_local_buffer 的计数
如果 sw m 构成的 CounterKeyTuple 存在，加入 pktout_local_buffer

####updatePacketInCountersLocal(IOFSwitch sw, OFMessage m, Ethernet eth)

如果 sw m eth 构成的 CounterKeyTuple 存在，增加 pktin_local_buffer 的计数
如果 sw m eth 构成的 CounterKeyTuple 存在，加入 pktin_local_buffer

####updateFlush()

将 pktin_local_buffer 中的计数更新到 pktinCounters
将 pktout_local_buffer 中的计数更新到 pktoutCounters
