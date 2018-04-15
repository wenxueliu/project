
## 概念

* Channel
* EventLoop
* Promise
* Future
* inBound, outBound

## 理解 netty 的关键

1. 一个连接对应一个 Channel
2. 作为服务端，通过 accept 创建一个连接(Channel), 之后, 客户端和服务端通过该
   Channel 通信
3. 作为客户端，通过 connect 创建一个连接(Channel), 之后, 客户端和服务端通过该 Channel 通信

系统初始化，对于 Server 端会有一个父 channel, 该 channel 负责接收
客户端的请求, 当接受到客户端请求后, 创建一个新的 Channel 专门用于
与特定客户端通信;

数据从接受到发送需要一系列处理器, 此外各个处理器应该按照某种顺序依次执行,
对于收到的包处理为 ChannelInboundHandler, 对于发送出去的包处理为 ChannelOutboundHandler
处理器的顺序由 ChannelPipeline 定义, 管理 ChannelHandler 的增加，删除，替换.
代理都到数据和发送数据各个事件的处理.

ChannelPipeline 维护一个双向链表, 链表头为 HeadContext, 链表尾为 TailContext,
每个元素类型是 AbstractChannelHandlerContext, 每个 AbstractChannelHandlerContext
包含 name, EventExecutorGroup, ChannelHandler.

支持从链表头，尾，中间增加或删除 AbstractChannelHandlerContext
每次增加触发 HandlerAdd 回调, 删除触发 HandlerRemove 回调

每当一个 Inbound 事件触发, 就会从链表头依次向后遍历调用每个
ChannelInboundHandler 事件对应的方法; 每当一个
Outbound 事件触发, 就会从链表尾依次向前遍历调用每个
ChannelOutboundHandler 事件对应的方法。每个执行 ChannelHandler
的线程由 AbstractChannelHandlerContext 的 executor 来决定.

需要注意的是, 在链表遍历过程中完全可能新添加元素到链表中，
在事件执行时, 只有 AbstractChannelHandlerContext 执行完 HandlerAdd 回调,
事件对应的方法才会执行.

还有一个关键点, 对于 Outbound 事件, 优先调用各个 handler 的方法,
最后调用 HeadContext 的 ChannelOutboundHandler 对应的方法; 对于
Inbound 事件, 优先调用 HeadContext 中 ChannelInboundHandler 的方法,
之后才调用各个 handler 的方法; 因此, 对于 Outbound 事件, 最后才
执行具体的消息读写，连接建立或绑定

注: HeadContext 调用 ChannelOutboundHandler 的方法为 channel.unsafe.xxxx 方法,

每当收到包就调用 pipeline 中指定的线程池 ChannelInboundHandler 对应的方法,
每当发送数据之前，都会在指定的线程池执行 ChannelOutboundHandler 对应的方法,
各个 handler 都执行对应的方法由 ChannelHandlerContext 来保证, 对应 Inbound
,不同的事件会触发对应方法的调用, ChannelHandlerContext 会依次调用各个 handler
对应的方法, Outbound 情况类似. 其中 Inbound 会将链表头传递给
ChannelHandlerContext, 每个处理器的 ChannelHandlerContext 会自动调用下一个
处理的对应方法; 类似 Outbound 将链表尾传递给 ChannelHandlerContext, 每个
处理器会依次调用上一个处理器的对应方法.

pipeline, context, handler, channel, eventloop 之间的关系

NioEventLoopGroup 的 newChild() 创建 NioEventLoop
每个 NioEventLoop 通过 register 将 channel 与 group 关联, 并且与 Selector, SelectionKey, SelectableChannel 关联起来

服务端通过 bind 监听 accept 事件, 开始对外提供服务, 客户端通过 connect 与远程建立连接;



## netty 可重用的类

* NetUtil : 网卡, 系统参数等等
* DefaultChannelId : 全局唯一 id 生成器
* SocketUtil : Socket 类的封装

## netty 中的设计模式

0. 单例模式

DefaultSelectStrategyFactory
DefaultChannelId

1. 工厂模式

interface ChannelFactory<T extends Channel>
interface ChannelFactory<T extends Channel> extends io.netty.bootstrap.ChannelFactory<T>
class ReflectiveChannelFactory<T extends Channel> implements ChannelFactory<T>

public class NioServerSocketChannel extends AbstractNioMessageChannel implements io.netty.channel.socket.ServerSocketChannel {

2. Builder 模式

ServerBootstrap

3. 委托模式

DelegatingHandle

## 问题

1. eventLoop 是如何与 Channel 关联的?

通过 register 操作

2. SelectableChannel 如何与 Channel 关联的?

通过 AbstractNioChannel 的构造函数参数传入

3. SelectionKey 如何与 Channel 关联

通过 doRegister 的 SelectableChannel.register(eventLoop.unwrappedSelector(), 0, this) 操作

4. newUnsafe() 事实上实现?

AbstractNioMessageChannel 中的 new NioMessageUnsafe()

AbstractNioByteChannel 中的 new NioByteUnsafe()

5. pipeline 与 channel 的关系, 与 ChannelHandlerContext 的关系

Channel 与 pipeline 通过 pipeline 的构造函数关联, 参考 AbstractChannel

ChannelHandlerContext 与 Channel 通过 pipeline 关联, 参考 DefaultChannelPipeline

6. Selector 在 netty 中对应什么 ?

SelectedSelectionKeySetSelector 是 Selector 的简单封装

7. 将 EventExecutorGroup 与 Channel 如何关联起来的?

通过 EventExecutorGroup  将一个 Channel 注册到 EventExecutorGroup

8. EventExecutor 与 EventExecutorGroup 的关系

EventExecutor 的 parent() 为 EventExecutorGroup
SocketChannel 的 parent() 为 ServerSocketChannel
EventLoop 的 parent() 为 EventLoopGroup
DefaultEventExecutor 的 parent() 为 DefaultEventExecutorGroup, 后者通过 newChild 调用前者
NioEventLoop 的 parent() 为 NioEventLoopGroup, 后者通过 newChild 调用前者
DefaultEventLoop 的 parent 为 DefaultEventLoopGroup, 后者通过 newChild 调用前者

9. ServerBootstrap 的 childxxx 和 xxx 的关系(当 xxx 为 group, option, attr, handler)?

## 启动器

abstract class AbstractBootstrapConfig
final class ServerBootstrapConfig extends AbstractBootstrapConfig

## AbstractBootstrap

    EventLoopGroup group;
    ChannelFactory<? extends C> channelFactory;
    SocketAddress localAddress;
    Map<ChannelOption<?>, Object> options = new LinkedHashMap<ChannelOption<?>, Object>();
    Map<AttributeKey<?>, Object> attrs = new LinkedHashMap<AttributeKey<?>, Object>();
    ChannelHandler handler;

1. 设置, 获取以上属性
2. 必须设置 group, channelFactory, childHandler, childGroup
3. bind : 异步或同步将 localAddress 绑定到 channel, 并监听

## ServerBootstrap extends AbstractBootstrap

属性

* config : 具体属性由 ServerBootstrap 的其他属性代理
* group : EventLoopGroup, 目前有 NioEventLoop
* handler : 需要用户去实现
* options : 数组, 协议选项
* attrs 数组
* channelFactory :

* childGroup
* childHandler
* childOptions
* childAttrs

group, childGroup 都依赖外部参数

    Map<ChannelOption<?>, Object> childOptions = new LinkedHashMap<ChannelOption<?>, Object>(); worker channel 中的 options
    Map<AttributeKey<?>, Object> childAttrs = new LinkedHashMap<AttributeKey<?>, Object>(); woker channel 总的 Attrs
    ServerBootstrapConfig config = new ServerBootstrapConfig(this);
    EventLoopGroup childGroup;  管理 worker 中的 channel
    ChannelHandler childHandler; worker 的 handler

bind(localAddress)
doBind(localAddress)
    ChannelFuture regFuture = initAndRegister
        channel = channelFactory.newChannel()
            channel = NioServerSocketChannel
        init(channel)
            p.addLast(new ChannelInitializer<Channel>() {
                public void initChannel(final Channel ch) {
                    ChannelPipeline p = channel.pipeline();
                    ChannelHandler handler = config.handler();
                    pipeline.addLast(new ServerBootstrapAcceptor(ch, currentChildGroup, currentChildHandler, currentChildOptions, currentChildAttrs));
                }
        ChannelFuture regFuture = config().group().register(channel)
            EventLoopGroup.register(channel)
                EventExecutor[] children = new EventExecutor[nThreads];
                EventExecutorChooserFactory.EventExecutorChooser  chooser = chooserFactory.newChooser(children);
                chooser.next().register(channel)
                EventLoop.register(channel)
                    EventLoopGroup.register(channel)
                    SingleThreadEventLoop.register(new DefaultChannelPromise(channel, this))
                        DefaultChannelPromise(channel, this).channel().unsafe().register(this, promise)
                            DefaultPromise(channel, this).channel().unsafe().register(this, promise)
                                channel.unsafe().register(this, promise)
                                NioServerSocketChannel.unsafe().register(this, promise)
                                    AbstractChannel.unsafe.register(this, promise)
                                        new NioMessageUnsafe().register(this, promise)
                                            AbstractUnsafe.register(this, promise)
                                                AbstractNioChannel.doRegister()
                                                    selectionKey = javaChannel().register(eventLoop().unwrappedSelector(), 0, this)
                                                        selectionKey = SelectableChannel.register(eventLoop().unwrappedSelector(), 0, this)
                                                            selectionKey = SelectableChannel.register(provider.openSelector(), 0, this)

        return regFuture
    Channel channel = regFuture.channel()
    ChannelPromise promise = channel.newPromise()
    doBind0(regFuture, channel, localAddress, promise)
        channel.bind(localAddress, promise).addListener(ChannelFutureListener.CLOSE_ON_FAILURE)
            AbstractChannel.bind()
                pipeline.bind()
                    DefaultChannelPipeline.bind()
                        TailContext.bind()
                            AbstractChannelHandlerContext.bind()
                            AbstractChannelHandlerContext.invokeBind()
                                unsafe.bind(localAddress, promise)
                                pipeline.channel().unsafe().bind()
                                    AbstractChannel.bind()
                                        NioServerSocketChannel.doBind()
                                            SelectableChannel.bind()

group : 主要用于 accept 新的连接
childGroup : worker 用于处理机新的连接

服务端每 accept 就创建一个 channel, 该 channel 会加入 childHandler, 设置 childOptions, childAttrs,
并且将该 channel 注册到 childGroup, 当该 channel 创建成果就队客户端提供服务,
如果失败就关闭该 channel

EventLoopGroup : 注册 channel
EventLoop : 一个单线程的事件循环 默认线程数是处理器的两倍

io 操作有 SelectableChannel

## 执行器

1. 循环执行

一个 EventExecutorGroup 包含多个 EventExecutor, 可以通过 next 或迭代器遍历, 优雅关闭, 可提交任务, 固定间隔执行任务
一个 EventExecutor 创建一个异步任务，检查线程(包括当前线程)是否在 EventLoop, 获取所属 EventExecutorGroup
一个 EventLoopGroup 包含多个 EventLoop 的数组
一个 EventLoop 一次处理一个或多个 Channel 的所有 io 操作

interface EventExecutorGroup extends ScheduledExecutorService
interface EventLoopGroup extends EventExecutorGroup
interface EventExecutor extends EventExecutorGroup
interface OrderedEventExecutor extends EventExecutor
interface EventLoop extends OrderedEventExecutor, EventLoopGroup

abstract class AbstractEventExecutorGroup implements EventExecutorGroup
abstract class MultithreadEventExecutorGroup extends AbstractEventExecutorGroup
class DefaultEventExecutorGroup extends MultithreadEventExecutorGroup
class MultithreadEventLoopGroup extends MultithreadEventExecutorGroup implements EventLoopGroup
class DefaultEventLoopGroup extends MultithreadEventLoopGroup
class NioEventLoopGroup extends MultithreadEventLoopGroup

interface ExecutorService extends Executor
abstract class AbstractExecutorService implements ExecutorService
abstract class AbstractEventExecutor extends AbstractExecutorService implements EventExecutor
abstract class AbstractScheduledEventExecutor extends AbstractEventExecutor
abstract class SingleThreadEventExecutor extends AbstractScheduledEventExecutor implements OrderedEventExecutor
final class DefaultEventExecutor extends SingleThreadEventExecutor
abstract class SingleThreadEventLoop extends SingleThreadEventExecutor implements EventLoop
class NioEventLoop extends SingleThreadEventLoop

AbstractEventExecutor :  不支持 schedule
AbstractScheduledEventExecutor : 将任务加入 PriorityQueue, 在 AbstractEventExecutor 基础上提供任务取消，固定时间执行
SingleThreadEventExecutor : 任务队列由 PriorityQueue 为 LinkedBlockingQueue, 更加完整的任务管理
MultithreadEventExecutorGroup : 多个 EventExecutor 的数组, 每次选择一个, 基于索引, 提供只读迭代器
SingleThreadEventLoop : 继承了 SingleThreadEventExecutor 的任务执行, 实现了 EventLoop 的Channel 注册
NioEventLoop : 处理 IO 事件, 主要实现
AbstractEventExecutorGroup : 任务调度相关(提交任务到队列, 定时执行任务)
MultithreadEventLoopGroup : 继承了 MultithreadEventExecutorGroup 的任务执行, 实现了 EventLoopGroup 的注册, Channel 注册到哪个 EventExecutor 由 EventExecutorChooserFactory 决定

### SingleThreadEventExecutor

两个队列 taskQueue(待执行的任务队列), scheduledTaskQueue(周期性执行任务队列), 线程执行支持
ThreadFactory 和 Executor; shutdownHooks 保存关闭之前执行的任务；

### SingleThreadEventLoop

在 SingleThreadEventExecutor 基础上，增加 tailTask 队列

### NioEventLoop

processSelectedKeys();
runAllTasks();

## Channel

                                                     I/O Request
                                                via {@link Channel} or
                                            {@link ChannelHandlerContext}
                                                          |
      +---------------------------------------------------+---------------+
      |                           ChannelPipeline         |               |
      |                                                  \|/              |
      |    +---------------------+            +-----------+----------+    |
      |    | Inbound Handler  N  |            | Outbound Handler  1  |    |
      |    +----------+----------+            +-----------+----------+    |
      |              /|\                                  |               |
      |               |                                  \|/              |
      |    +----------+----------+            +-----------+----------+    |
      |    | Inbound Handler N-1 |            | Outbound Handler  2  |    |
      |    +----------+----------+            +-----------+----------+    |
      |              /|\                                  .               |
      |               .                                   .               |
      | ChannelHandlerContext.fireIN_EVT() ChannelHandlerContext.OUT_EVT()|
      |        [ method call]                       [method call]         |
      |               .                                   .               |
      |               .                                  \|/              |
      |    +----------+----------+            +-----------+----------+    |
      |    | Inbound Handler  2  |            | Outbound Handler M-1 |    |
      |    +----------+----------+            +-----------+----------+    |
      |              /|\                                  |               |
      |               |                                  \|/              |
      |    +----------+----------+            +-----------+----------+    |
      |    | Inbound Handler  1  |            | Outbound Handler  M  |    |
      |    +----------+----------+            +-----------+----------+    |
      |              /|\                                  |               |
      +---------------+-----------------------------------+---------------+
                      |                                  \|/
      +---------------+-----------------------------------+---------------+
      |               |                                   |               |
      |       [ Socket.read() ]                    [ Socket.write() ]     |
      |                                                                   |
      |  Netty Internal I/O Threads (Transport Implementation)            |
      +-------------------------------------------------------------------+

AbstractNioMessageChannel : 接受消息, 并调用 pipeline 中的每个 handler, 将 ChannelOutboundBuffer 中的消息写出去

interface ChannelFactory
interface ChannelFactory extends io.netty.bootstrap.ChannelFactory
class ReflectiveChannelFactory implements ChannelFactory

interface ChannelConfig
interface SocketChannelConfig extends ChannelConfig
interface OioSocketChannelConfig extends SocketChannelConfig
interface ServerSocketChannelConfig extends ChannelConfig
interface OioServerSocketChannelConfig extends ServerSocketChannelConfig
interface DatagramChannelConfig extends ChannelConfig

class DefaultChannelConfig implements ChannelConfig
class DefaultServerSocketChannelConfig extends DefaultChannelConfig implements ServerSocketChannelConfig
class DefaultSocketChannelConfig extends DefaultChannelConfig implements SocketChannelConfig
class DefaultDatagramChannelConfig extends DefaultChannelConfig implements DatagramChannelConfig
class DefaultOioSocketChannelConfig extends DefaultSocketChannelConfig implements OioSocketChannelConfig
class DefaultOioServerSocketChannelConfig extends DefaultServerSocketChannelConfig implements OioServerSocketChannelConfig

class NioSocketChannelConfig  extends DefaultSocketChannelConfig
class NioDatagramChannelConfig extends DefaultDatagramChannelConfig

interface ChannelOutboundInvoker
interface Channel extends AttributeMap, ChannelOutboundInvoker, Comparable<Channel>
interface DatagramChannel extends Channel
interface DuplexChannel extends Channel
interface SocketChannel extends DuplexChannel
interface ServerChannel extends Channel
interface ServerSocketChannel extends ServerChannel
abstract class AbstractChannel extends DefaultAttributeMap implements Channel
abstract class AbstractNioChannel extends AbstractChannel
abstract class AbstractNioMessageChannel extends AbstractNioChannel
abstract class AbstractNioByteChannel extends AbstractNioChannel

class NioServerSocketChannel extends AbstractNioMessageChannel implements ServerSocketChannel
class NioSocketChannel extends AbstractNioByteChannel implements SocketChannel

class OioServerSocketChannel extends AbstractOioMessageChannel implements ServerSocketChannel
class OioDatagramChannel extends AbstractOioMessageChannel implements DatagramChannel

class OioSocketChannel extends OioByteStreamChannel implements SocketChannel

其中 SocketChannel 通过 parent() 与 ServerSocketChannel 关联

### Channel

1. 代表一个连接
2. 通过注册与一个 EventLoop 绑定
3. 与一个 ChannelPipeline 关联
4. 有层级结构, 有父 Channel
5. 元数据，属性，地址
6. 分配 ByteBuf
7. 通过 Unsafe 进行 Socket 操作

### AbstractChannel

    Channel parent;
    ChannelId id;
    Unsafe unsafe;
    DefaultChannelPipeline pipeline;
    VoidChannelPromise unsafeVoidPromise = new VoidChannelPromise(this, false);
    CloseFuture closeFuture = new CloseFuture(this);

    SocketAddress localAddress;
    SocketAddress remoteAddress;
    EventLoop eventLoop;
    boolean registered;

    boolean strValActive;
    String strVal;

主要实现代理给 pipeline 和 unsafe

pipeline = new DefaultChannelPipeline
unsafe = newUnsafe()

1. 真正的 IO 操作, 由 doXXXX 执行(doClose, doBind等等)

### AbstractNioChannel

* SelectableChannel ch : 系统默认
* int readInterestOp : 
* SelectionKey selectionKey : 
* boolean readPending

void doRegister()

    将当前 channel 注册到 eventLoop 的 slector

void doDeregister()

    将注册的 SelectionKey 从 eventLoop 中取消

void doBeginRead()

    如果还没有关注 readInterestOp, 设置当前 selectionKey 关注 readInterestOp 事件

abstact boolean doConnect(SocketAddress remoteAddress, SocketAddress localAddress)

abstact void doFinishConnect()

void doClose()

    取消 connectPromise 和 connectTimeoutFuture
    connectPromise 设置为 null
    connectTimeoutFuture 设置为 null

### AbstractNioMessageChannel

* SelectableChannel ch : 系统默认
* int readInterestOp : 关注读操作标志
* SelectionKey selectionKey :
* boolean readPending

doWrite

    将 ChannelOutboundBuffer 中取出 config().getWriteSpinCount() 条消息调用 doWriteMessage

abstract boolean doWriteMessage(Object msg, ChannelOutboundBuffer in)
abstract int doReadMessages(List<Object> buf)

### AbstractNioByteChannel

doWrite

    将 ChannelOutboundBuffer 中取出 config().getWriteSpinCount() 条消息
    如果消息是 ByteBuf 调用 doWriteBytes
    如果消息是 FileRegion 调用 doWriteFileRegion

filterOutboundMessage

    如果是 ByteBuf 且是 direct的, 或者是 FileRegion, 直接返回

setOpWrite

    关注写事件

clearOpWrite

    不关注写事件

abstract long doWriteFileRegion(FileRegion region)
abstract int doReadBytes(ByteBuf buf)
abstract int doWriteBytes(ByteBuf buf)

### NioServerSocketChannel

* SelectableChannel ch : 系统默认
* config : DefaultServerSocketChannelConfig

构造函数默认关注 Accept 事件

isActive : 等于 SelectableChannel.socket().isBond()
doBind : SelectableChannel.bind()
doClose : SelectableChannel.close()
doConnect, doFinishConnect, doDisconnect, doWriteMessage, filterOutboundMessage 抛出不支持异常
doReadMessages(buf) : 将 accept 返回的 SocketChannel 加入当前 buf 中, 后调用 pipeline.fireChannelRead

ByteBufAlloc : PooledByteBufAlloc
WriteBufferWaterMark(16k, 32k)
defaultMaxMessagesPerRead : 16

### NioSocketChannel

isActive : 等于 SelectableChannel.isOpen() && SelectableChannel.isConnected()
shutdownInput : SelectableChannel.shutdownInput()
shutdownOutput : SelectableChannel.shutdownOutput()
shutdown : SelectableChannel.shutdownOutput() 之后 SelectableChannel.shutdownInput()
doBind : SelectableChannel.bind()
doConnect : SelectableChannel.connect(), 关注 OP_CONNECT 事件
doFinishConnect : SelectableChannel.finishConnect()
doDisconnect : doClose
doClose : SelectableChannel.close()
doReadByte : byteBuf.writeBytes(javaChannel(), allocHandle.attemptedBytesRead())
doWriteBytes : buf.readBytes(javaChannel(), buf.readableBytes())
doWriteFileRegion : region.transferTo(javaChannel(), position)
doWrite : 如果 in.count 为 0, 调用父类的 doWrite, 否则调用
SelectableChannel.write 将消息写出去

                 +--------------+
                 |    Unsafe    |
                 +-^------------>
                   |            |
    +--------------+-+         ++-----------+
    | AbstractUnsafe |         | NioUnsafe  |
    +--------------^-+         +-^----------+
                   |             |
                 +-+-------------+---+
                 | AbstractNioUnsafe |
                 +-^-------------^---+
                   |             |
    +--------------+---+        ++--------------+
    | NioMessageUnsafe |        | NioByteUnsafe |
    +------------------+        +-------^-------+
                                        |
                              +---------+--------------+
                              | NioSocketChannelUnsafe |
                              +------------------------+
interface Unsafe
interface NioUnsafe extends Unsafe
abstract class AbstractUnsafe implements Unsafe
abstract class AbstractNioUnsafe extends AbstractUnsafe implements NioUnsafe
class NioMessageUnsafe extends AbstractNioUnsafe
class NioByteUnsafe extends AbstractNioUnsafe
class NioSocketChannelUnsafe extends NioByteUnsafe

### interface Unsafe

* RecvByteBufAllocator.Handle recvBufAllocHandle();
* SocketAddress localAddress()
* SocketAddress remoteAddress()
* void register(EventLoop eventLoop, ChannelPromise promise)
* void bind(SocketAddress localAddress, ChannelPromise promise)
* void connect(SocketAddress remoteAddress, SocketAddress localAddress, ChannelPromise promise)
* void disconnect(ChannelPromise promise)
* void close(ChannelPromise promise)
* void closeForcibly()
* void deregister(ChannelPromise promise)
* void beginRead()
* void write(Object msg, ChannelPromise promise)
* void flush()
* ChannelPromise voidPromise()
* ChannelOutboundBuffer outboundBuffer()

### interface NioUnsafe extends Unsafe

* SelectableChannel ch()
* void finishConnect()
* void read()
* void forceFlush()

### abstract class AbstractUnsafe

ChannelOutboundBuffer outboundBuffer = new ChannelOutboundBuffer(AbstractChannel.this);
RecvByteBufAllocator.Handle recvHandle;
boolean inFlush0 : 是否已经刷新
boolean neverRegistered = true;

register :

    1. 将 eventLoop 赋值给 AbstractChannel.this.eventLoop
    2. 调用 doRegister
    3. 调用 pipeline.invokeHandlerAddedIfNeeded()
    4. 调用 pipeline.fireChannelRegistered()
    5. 如果是第一次注册, 调用 pipeline.fireChannelActive(), 否则调用 beginRead() -> doBeginRead()

bind :

    1. 调用 doBind()
    2. 如果 doBind() 前后的 isActive() 不一样, 调用 pipeline.fireChannelActive()

disconnect:

    1. 调用 doDisconnect()
    2. 如果 doDisconnect() 前后的 isActive() 不一样, 调用 pipeline.fireChannelInactive()
    3. closeIfClosed() -> close()

close

    1. 设置 outboundBuffer 为 null;
    2. doClose()
    3. 调用 deregister -> doDeregister
    4. pipeline.fireChannelInactive()
    5. pipeline.fireChannelUnregistered()

deregister

    1. 调用 doDeregister
    2. pipeline.fireChannelInactive()
    3. pipeline.fireChannelUnregistered()

beginRead

    1. 调用 doBeginRead()

write

    1. 过滤消息 filterOutboundMessage
    2. 获取消息大小 pipeline.estimatorHandle()
    3. 将消息增加到 outboundBuffer 的 Entry 中

flush

    1. 将 outboundBuffer 中 unflushedEntry 的指针指向 null
    2. doWrite

voidPromise

    new VoidChannelPromise(this, false);
    inFlush0 = false;


### AbstractNioUnsafe

void removeReadOp()

    SelectionKey 删除 readInterestOp 事件

SelectableChannel ch()

    返回 SelectableChannel

void connect(SocketAddress remoteAddress, SocketAddress localAddress, ChannelPromise promise)

    doConnect(remoteAddress, localAddress)

void finishConnect()

    doFinishConnect()
    2. 如果 doFinishConnect() 前后的 isActive() 不一样, 调用 pipeline.fireChannelActive()

void flush0()

    如果当前 selectionKey 对写感兴趣, 直接返回; 否则调用 super.flush0()

void forceFlush()

    super.flush0()

doXX 主要都在 AbstractNioChannel 中实现

### NioMessageUnsafe

read

    1. 调用 doReadMessages, 将收到的消息对象保持在 buf
    1. pipeline.fireChannelRead 传递给后续的所有 handler
    2. pipeline.fireChannelReadComplete 传递给后续的所有 handler
    3. 清除 buf 内容
    4. 删除关注读事件

### NioByteUnsafe

read

    1. 调用 doReadBytes，将收到的消息保存在 allocHandle
    1. pipeline.fireChannelRead 传递给后续的所有 handler
    2. pipeline.fireChannelReadComplete 传递给后续的所有 handler
    4. 删除关注读事件

## Pipeline

顺序

invokeHandlerAddedIfNeeded
fireChannelRegistered
fireChannelActive
fireChannelInactive
fireChannelUnregistered


fireUserEventTriggered
fireChannelRead
fireChannelReadComplete
fireChannelWritabilityChanged

### ChannelPipeline


    +----------------------+       +---------------------+
    |ChannelOutboundInvoker|       |ChannelInboundInvoker|
    +-------------------^--+       +--^------------------+
                        |             |
                      +-+-------------+-+
                      | ChannelPipeline |
                      +--------^--------+
                               |
                    +----------+-----------+
                    |DefaultChannelPipeline|
                    +----------------------+

interface ChannelOutboundInvoker
interface ChannelInboundInvoker
interface ChannelPipeline extends ChannelInboundInvoker, ChannelOutboundInvoker, Iterable<Entry<String, ChannelHandler>>
class DefaultChannelPipeline implements ChannelPipeline

问题:

1. Inbound 和 Outbound 的区别
2. pipeline 的 handler 支持动态增删(线程安全)
3. Inbound 和 Outbound 在 Pipeline 中的顺序 findContextInbound, findContextOutbound

DefaultChannelPipeline

1. channel 通过构造函数传入
2. 包含 headConetext 和 tailContext 与 AbstractChannelHandlerContext 关联

功能:

1. 修改(CRUD) Pipeline 中的 Handler
2. 保持 Context 在后面用
3. 存储状态信息
4. 一个 handler 可以有多个 Pipeline, 因此一个 ChannelHandler 可以有多个 Context
5. inBoundHandler 中的方法从 head -> tail 执行, outBoundHandler 中的方法从 tail -> head 执行
6. 如果不在当前 EventLoop 的任务加入 pendingHandlerCallbackHead

将各个 Handler 串联起来

### ChannelHandlerContext

                +--------------------+         +----------------------+
                |ChannelInboundInvoke|         |ChannelOutboundInvoker|
                +-----------------^--+         +----^-----------------+
                                  |                 |
                                +-+-----------------+-+
                                |ChannelHandlerContext|
                                +----------^----------+
                                           |
    +---------------------+  +-------------+---------------+   +---------------------+
    |ChannelInboundHandler|  |AbstractChannelHandlerContext|   |ChannelInboundHandler|
    +------------------^--+  +---^---------^----------^----+   +^--------------------+
                       |         |         |          |         |
                      ++---------++        |         ++---------++     +----------------------+
                      |TailContext|        |         |HeadContext+----->ChannelOutboundHandler|
                      +-----------+        |         +-----------+     +----------------------+
                                           |
                                           |
                              +------------+---------------+
                              |DefaultChannelHandlerContext|
                              +----------------------------+


interface ChannelHandlerContext extends AttributeMap, ChannelInboundInvoker, ChannelOutboundInvoker
abstract class AbstractChannelHandlerContext extends DefaultAttributeMap implements ChannelHandlerContext, ResourceLeakHint
class DefaultChannelHandlerContext extends AbstractChannelHandlerContext
class TailContext extends AbstractChannelHandlerContext implements ChannelInboundHandler
class HeadContext extends AbstractChannelHandlerContext implements ChannelOutboundHandler, ChannelInboundHandler

以双链表的形式保存 AbstractChannelHandlerContext 元素, 每个 AbstractChannelHandlerContext
是对 Executor, Handler, name 的一个抽象, 每个 AbstractChannelHandlerContext 都包含一个
Executor, 一个 Handler;

调用 firexxx 都会自动调用链表后面每个元素中 handler 的 channelxxx;

1. findContextInbound 自动找下一个元素, findContextOutbound 自动找上一个元素;
2. 实现 ChannelInboundInvoker 的方法(firexxx) 调用 findContextInbound 唤醒下一个 ChannelHandlerContext 的 handler 的 xxx 事件
3. 实现 ChannelOutboundInvoker 的方法(connect, bind, disconnect 等)调用 findContextOutbound 唤醒上一个 ChannelHandlerContext 的 handler 的对应方法, 因此, 真正做实事的是 handler, handler 是构造函数传递进来的, 事实上, handler 是通过 DefaultChannelPipeline 的 addXXX 方法的外部参数传递进来
4. 当前 ChannelHandlerContext 的 handler 与下一个 ChannelHandlerContext 的 hander 可能在不同的线程
5. IO 操作代理给 handler -> pipeline().channel().unsafe() -> newUnsafe() -> AbstractUnsafe
6. handler 是业务代码主要需要做的地方;

通过 DefaultChannelPipeline 中双向链表的元素是 DefaultChannelHandlerContext

## handler

                                                   +--------------+
                       +--------------------------->ChannelHandler<---------------------------+
                       |                           +------^-------+                           |
                       |                                  |                                   |
             +---------+-----------+           +----------+----------+            +-----------+----------+
             |ChannelInboundHandler|           |ChannelHandlerAdapter|            |ChannelOutboundHandler|
             +-------------^-------+           +-^-------------------+            +----------^-----------+
                           |                     |                                           |
                      +----+---------------------+-+                               +---------+-------------------+
                      |ChannelInboundHandlerAdapter|                               |ChannelOutboundHandlerAdapter|
                      +----^---------------------^-+                               +--^-------------------^------+
                           |                     |                                    |                   |
       +-------------------+--+        +---------+-------------+     +----------------+---+       +-------+---------------+
       | ByteToMessageDecoder |        |MessageToMessageDecoder|     |MessageToByteEncoder|       |MessageToMessageEncoder|         r
       +----------^-----------+        +----------^------------+     +----^-------------^-+       +--^--------------^-----+
                  |                               |                       |             |            |              |
    +-------------+--------------+       +--------+-------+           +---+---+        ++------------+--+     +-----+--------------+
    |LengthFieldBasedFrameDecoder|       |ByteArrayDecoder|           |Encoder|        |ByteArrayEncoder|     |LengthFieldPrepender|
    +----------------------------+       +----------------+           +-------+        +----------------+     +--------------------+



@startuml
interface ChannelHandler

abstract class ChannelHandlerAdapter implements ChannelHandler

interface ChannelInboundHandler extends ChannelHandler
class ChannelInboundHandlerAdapter extends ChannelHandlerAdapter implements ChannelInboundHandler
class ServerBootstrapAcceptor extends ChannelInboundHandlerAdapter
abstract class ByteToMessageDecoder extends ChannelInboundHandlerAdapter
class LengthFieldBasedFrameDecoder extends ByteToMessageDecoder
abstract class ChannelInitializer extends ChannelInboundHandlerAdapter
abstract class MessageToMessageDecoder extends ChannelInboundHandlerAdapter
class ByteArrayDecoder extends MessageToMessageDecoder

interface ChannelOutboundHandler extends ChannelHandler
class ChannelOutboundHandlerAdapter extends ChannelHandlerAdapter implements ChannelOutboundHandler
abstract class MessageToByteEncoder extends ChannelOutboundHandlerAdapter
abstract class MessageToMessageEncoder extends ChannelOutboundHandlerAdapter
class LengthFieldPrepender extends MessageToMessageEncoder
class ByteArrayEncoder extends MessageToMessageEncoder
class Encoder extends MessageToByteEncoder

class ChannelDuplexHandler extends ChannelInboundHandlerAdapter implements ChannelOutboundHandler
class CombinedChannelDuplexHandler extends ChannelDuplexHandler
class ChunkedWriteHandler extends ChannelDuplexHandler
class HttpServerCodec extends CombinedChannelDuplexHandler
@enduml

1. 只有标记为 isSharable 的 handler 才能被添加到多个 Pipeline

DefaultAttributeMap : 数组+链表

### ChannelOutboundBuffer

消息存放在 Entry, 分 tailEntry, flushedEntry, unflushedEntry, 其中
unflushedEntry 指向未写的第一个消息, tailEntry 指向最后增加的消息,
flushedEntry 指向 每次刷新开始的位置(AddFlush) 调用的 entry, Entry
是可回收的;

incrementPendingOutboundBytes 增加可写的 byte 数, 当大于配置的写的
高水位，同步或异步设置当前 channel 不可写；decrementPendingOutboundBytes
减少可写的 bytes, 当小于配置的写的低水位，同步或异步设置当前 Channel 可写.

每次删除消息从 flushedEntry 开始删除(remove)

### config

WRITE_SPIN_COUNT : 每次写尝试的次数
