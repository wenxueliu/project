
监控所有订阅 PACKET_IN 模块的包, 记录所有模块和每个模块, 所有 PACKET_IN 的每个包的总个数, 总时间, 平均时间, 单个包的最大处理时间, 
单个包的最小处理时间, 以及方差和标准差

##PktInProcessingTime

    PACKET_IN 消息监控类, 其他模块必须调用该类来实现监控

###关键变量

    IFloodlightProviderService floodlightProvider
    IRestApiService restApi

    long ptWarningThresholdInNano : 处理一次 PACKET_IN 的时间阈值, 可以在配置文件中配置
    boolean isEnabled = false
    boolean isInited = false
    long lastPktTime_ns
    CumulativeTimeBucket ctb = null

    int ONE_BUCKET_DURATION_SECONDS = 10
    long ONE_BUCKET_DURATION_NANOSECONDS = ONE_BUCKET_DURATION_SECONDS * 1000000000


###void bootstrap(List<IOFMessageListener> listeners)

listeners 初始化 ctb = new CumulativeTimeBucket(listeners)

###boolean isEnabled()

    是否已经开启监控

###void setEnabled(boolean enabled)

    设置是否开启监控, 如果为 true, 调用 bootstrap 添加所有订阅 PACKET_IN 的模块

###CumulativeTimeBucket getCtb()

    获取 ctb

###void recordStartTimeComp(IOFMessageListener listener)

    设置 startTimeCompNs 为当前时间, 这里是 PACKET_IN 到达 listener 模块的时间

###void recordEndTimeComp(IOFMessageListener listener)

    设置模块 listener 处理完一次 PACKET_IN 包的结束时间, 并更新平均时间, 单包最大处理时间, 单包最小处理时间, 

###void recordStartTimePktIn()

    设置 startTimePktNs 为当前时间, 这里是一个 PACKET_IN 刚到的时间

###void recordEndTimePktIn(IOFSwitch sw, OFMessage m, FloodlightContext cntx)

    设置一个 PACKET_IN 包被所有模块处理完成的结束时间, 并更新平均时间, 单包最大处理时间, 单包最小处理时间


##CumulativeTimeBucket

记录一次 PACKET_IN 消息被所有模块处理的统计信息

###关键变量

    long startTime_ns;
    Map<Integer, OneComponentTime> compStats
    long totalPktCnt
    long totalProcTimeNs
    long sumSquaredProcTimeNs2
    long maxTotalProcTimeNs
    long minTotalProcTimeNs
    long avgTotalProcTimeNs
    long sigmaTotalProcTimeNs

###long getStartTimeNs()
###long getTotalPktCnt()
###long getAverageProcTimeNs()
###long getMinTotalProcTimeNs()
###long getMaxTotalProcTimeNs()
###long getTotalSigmaProcTimeNs()
###int getNumComps()
###Collection<OneComponentTime> getModules()

###CumulativeTimeBucket(List<IOFMessageListener> listeners)
    
    构造函数, 初始化 compStats, 设置 startTime_ns 为当前时间

###void updateSquaredProcessingTime(long curTimeNs)

    更新 sumSquaredProcTimeNs2 的值

###void reset()

    重设所有计数器, 包括各个模块的

###void computeSigma()

    计算标准差(公式是否有问题)

###void computeAverages()

    计算总的平均时间, 以及各个模块的平均时间

###void updatePerPacketCounters(long procTimeNs)

    一次 PACKET_IN 消息被处理完之后, 更新各个计数器

###void updateOneComponent(IOFMessageListener l, long procTimeNs)

    一次 PACKET_IN 在 l 模块处理完之后, 更新该模块的各个计数器


##OneComponentTime

    int compId                    : 模块的hashCode
    String compName               : 模块名
    int pktCnt                    : 包的个数
    long totalProcTimeNs          : 总的处理时间
    long sumSquaredProcTimeNs2    : 总平方
    long maxProcTimeNs            : 单包最大处理时间间隔
    long minProcTimeNs            : 单包最小处理时间间隔
    long avgProcTimeNs            : 平均处理时间
    long sigmaProcTimeNs          : 

###OneComponentTime(IOFMessageListener module)


###void resetAllCounters()
###String getCompName()
###int getPktCnt()
###long getSumProcTimeNs()
###long getMaxProcTimeNs()
###long getMinProcTimeNs()
###long getAvgProcTimeNs()
###long getSigmaProcTimeNs()
###long getSumSquaredProcTimeNs()
###void increasePktCount()
###void updateTotalProcessingTime(long procTimeNs)
###void updateAvgProcessTime()
###void updateSquaredProcessingTime(long procTimeNs)
###void calculateMinProcTime(long curTimeNs)
###void calculateMaxProcTime(long curTimeNs)
###void computeSigma()
###void updatePerPacketCounters(long procTimeNs)
###int hashCode()







