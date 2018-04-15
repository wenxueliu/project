##Learnswitch

这个模块实现了 ILearningSwitchService, 继承 IOFMessageListener 消息，通过 receive 监听 PACKET_IN FLOW_REMOVED 消息。

###关键变量

    macVlanToSwitchPortMap  Map<IOFSwitch, Map<MacVlanPair, OFPort>>  

对每一个主机

    Map< 交换机，Map< Map< MAC地址，VLAN ID >, 输入端口>>
    Map< 交换机，Map< Map< MAC地址，VLAN ID >, 输出端口>>

与传统交换机类似，相当于一个交换机内维护一张 < < 目的端口，VLAN> 转发端口 > 的表。

###入口函数 

    public Command receive(IOFSwitch sw, OFMessage msg, FloodlightContext cntx)
        switch (msg.getType()) {
            case PACKET_IN:
                // 监听到 PACKET_IN 调用 processPacketInMessage()
                return this.processPacketInMessage(sw, (OFPacketIn) msg, cntx);
            case FLOW_REMOVED:
                // 监听到 FLOW_REMOVED 调用 processFlowRemovedMessage()
                return this.processFlowRemovedMessage(sw, (OFFlowRemoved) msg);
            case ERROR:
                log.info("received an error {} from switch {}", msg, sw);
                return Command.CONTINUE;
            default:
                break;
        }
        log.error("received an unexpected message {} from switch {}", msg, sw);
        return Command.CONTINUE;
    }   


###处理 PACKET_IN 事件

    processPacketInMessage(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx)

* 取出 OFPacketIn 中 Math 中的 destMac 和 VlanVid
* 如果 sourceMac 是 unicast 地址，增加 key 为 < destMac VlanVid >  value in_port 到 macVlanToSwitchPortMap
* 检查 macVlanToSwitchPortMap 中是否由存在 key 为 < destMac VlanVid > 对应的端口
* 如果不存在，发送　PACKET_OUT 消息， action 是 OUTPUT， flood 给全部交换机端口
* 如果是包进入　in_port 端口，什么也不做
* 否则， 发送　PACKET_OUT 消息，action 是 OUTPUT，转发给指定端口，并修改输入流表的 match，
cookie，idle_timeout,hard_timeout,priority,bufferid，output，flag 和 action。使得
后续请求转发到指定端口；修改反向流表的 match 和 ouput。其中 cookie 是  LearningSwitch.LEARNING_SWITCH_COOKIE

**注意**

如果交换机支持 buffer_id 那么，PACKET_OUT 消息的 buffer_id 就用 PACKE_IN 的 buffer_id,
否则，就是是 NO_BUFFER。

如果是 OUTPUT 是 FLOOD，那么 交换机是否支持 buffer_id 是否就不重要了。否则，writePacketOutForPacketIn 实现较 pushPacket 存在一些问题，完全可以用后者代替。


###处理 FLOW_REMOVED 事件

    processFlowRemovedMessage(IOFSwitch sw, OFFlowRemoved flowRemovedMessage)

* 从 macVlanToSwitchPortMap 删除 key 为 < destMac VlanVid > 
* 删除反向的流表。


### bug

getFromPortMap vlan = VlanVid.FULL_MASK; 这里是否由问题？ 应该为 vlan = VlanVid.ofVlan(0)。