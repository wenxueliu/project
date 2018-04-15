


##PacketStreamerServer

    int port = 9090                                             : 流服务默认端口
    PacketStreamerHandler handler
    PacketStreamer.Processor<PacketStreamerHandler> processor

###void main

    

    handler = new PacketStreamerHandler()
    processor = new PacketStreamer.Processor<PacketStreamerHandler>(handler)
    hshaServer(PacketStreamer.Processor<PacketStreamerHandler> processor)


##PacketStreamerHandler

    继承自 PacketStreamer.Iface

###关键变量   
     
    Map<String, SessionQueue> msgQueues


###List<ByteBuffer> getPackets(String sessionid)

    从 msgQueues 获取 sessionid 对应的 SessionQueue 列表, 如果不存在, 等待 100 ms, 如果等待100 次还没有,就返回空的列表, 如果存在, 直到 SessionQueue 有元素才返回,包含 session 的列表

###int pushMessageSync(Message msg)

    遍历 Message 的所有 sessiont ID, 
    sessionids = msg.getSessionIDs()

###void pushMessageAsync(Message msg)

    与 pushMessageSync(msg) 一样

###void terminateSession(String sessionid)

    msgQueues 中, sessionid 对应的 SessionQueue 不为 null, 从 msgQueues 中删除 key 为 sessionid 的元素


##SessionQueue

    PacketStreamerHandler 的内部类, 记录 session 消息

###关键变量

    BlockingQueue<ByteBuffer> pQueue : session 阻塞队列

* SessionQueue()
* BlockingQueue<ByteBuffer> getQueue()

