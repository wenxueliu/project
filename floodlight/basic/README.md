###LDDP 协议

最基本的模块是链路发现模块。这个模块可以说是作为SDN控制器的一个非常基础的模块。链路发现模块的作用是为了形成全网拓扑，
这个拓扑信息包括网络中OpenFlow交换机的连接关系，形成全网视图，为OpenFlow流表下发而服务的。本文先介绍以下OpenFlow控制
器如何得到全网的拓扑信息，形成全网的拓扑视图。

首先介绍一下，OpenFlow协议中的首包上传的功能。在OpenFlow交换机中，如果从某个接口接收到一个报文，而在交换机的流表项中
找不到匹配项的时候，会把该报文的信息打成Pack_in报文，发送到控制器。由控制器对信息作出判断，下发流表到交换机，指挥交换机对该报文进行转发。

顺便再介绍一下LLDP（Link Layer Discovery Protocol,链路层发现协议）报文，该报文与OpenFlow协议完全没有关系，不是OpenFlow
协议中规定的报文，最早是IETF针对网管控制规定的链路层发现协议。两个路由器或者交换机相连的时候，一端的网络设备可以向另外
一端的网络设备发送LLDP报文，包括自己发送端口的一些信息包括物理地址、VLAN id等等的一些信息，对端网络设备收到该报文之后，
只是默默的把信息记录在自己的MIB信息库中，让网管服务器来通过SNMP或者NETCONF来读取该信息，不对该报文做任何回复，另外LLDP
报文不能穿透网桥，也就是只能在两个直连的交换机之间生存。

在OpenFlow控制器的工作机制中，OpenFlow控制器会定时的发送一个Packet_out报文给交换机，要求该OpenFlow交换机从某个端口发送
LLDP报文。如果两个OpenFlow交换机是直连的，那么对端交换机就一定能收到报文了。但是由于没有OpenFlow流表规定这个报文应该怎
么处理，于是这个接收到的LLDP报文就发送到控制器了。控制器接收到报文之后，就能判断这两个路由器直连。

以上是纯OpenFlow交换机的环境。对于网络环境中夹杂着非OpenFlow交换机的时候，OpenFlow控制器定时要求OpenFlow交换机从所有的
端口发送BDDP报文，BDDP报文是LLDP报文的广播版本，BDDP报文能够在一个广播域内存活。如果对端的OpenFlow交换机收到了BDDP报文，
但是没有收到LLDP报文，则认为这两个控制器之间存在非OpenFlow交换机。

通过以上的两个报文，就能知道OpenFlow控制器是如何获得全网视图，但是对于由于SDN控制器对于网络拓扑结构的链路状态具有非常高
的实时性要求，所以LLDP报文和BDDP报文的发送频率在SDN控制器中也是值得探讨的问题，目前在FloodLight控制器中是每5秒发送一次
LLDP报文和BDDP报文。

###模块加载器

###基于事件驱动的发布订阅者模式

发布者通过反射获取所有的订阅者，在事件发生后，将消息发送给各个订阅者．订阅者实现发布者的接口，自己决定如何处理订阅的消息．

###单例模式的线程池服务


###Netty 使用

	public void bootstrapNetty() {
		try {
			final ServerBootstrap bootstrap = createServerBootStrap();

			bootstrap.setOption("reuseAddr", true);
			bootstrap.setOption("child.keepAlive", true);
			bootstrap.setOption("child.tcpNoDelay", true);
			bootstrap.setOption("child.sendBufferSize", Controller.SEND_BUFFER_SIZE);

			ChannelPipelineFactory pfact = useSsl ? new OpenflowPipelineFactory(this, floodlightProvider.getTimer(), this, debugCounterService, keyStore, keyStorePassword) :
				new OpenflowPipelineFactory(this, floodlightProvider.getTimer(), this, debugCounterService);

			bootstrap.setPipelineFactory(pfact);
			InetSocketAddress sa = new InetSocketAddress(floodlightProvider.getOFPort());
			final ChannelGroup cg = new DefaultChannelGroup();
			cg.add(bootstrap.bind(sa));

			log.info("Listening for switch connections on {}", sa);
		} catch (Exception e) {
			throw new RuntimeException(e);
		}
	}

    private ServerBootstrap createServerBootStrap() {
        if (workerThreads == 0) {
            return new ServerBootstrap(
                    new NioServerSocketChannelFactory(
                            Executors.newCachedThreadPool(),
                            Executors.newCachedThreadPool()));
        } else {
            return new ServerBootstrap(
                    new NioServerSocketChannelFactory(
                            Executors.newCachedThreadPool(),
                            Executors.newCachedThreadPool(), workerThreads));
        }
    }

    public class OpenflowPipelineFactory
        @Override
        public ChannelPipeline getPipeline() throws Exception {
            ChannelPipeline pipeline = Channels.pipeline();
            OFChannelHandler handler = new OFChannelHandler(switchManager,
                    connectionListener,
                    pipeline,
                    debugCounters,
                    timer);

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
            return pipeline;
        }
