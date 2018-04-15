问题:

ovs-ofctl add-flow 如何配置通过 tcp 远程下发流表

OVS 应该关闭网卡的 LRO 功能

##配置

    Open_vSwitch : other_config :

        flow-limit : 默认 20 万
        max-idle : 10 s
        n-dpdk-rxqs : 默认 0
        pmd-cpu-mask :
        n-handler-threads :
        n-revalidator-threads :
        stats-update-interval : 单位 ms, 最小 50000 ms

    Bridge : other_config
        hwaddr : 网桥硬件地址
        stp-system-id : mac 地址
        stp-priority : 默认 32768
        stp-hello-time : 默认 2000
        stp-max-age : 默认 20000
        stp-forward-delay : 默认 15000

        rstp-address
        rstp-priority : 默认 32768
        rstp-ageing-time : 默认 300
        rstp-force-protocol-version : 默认 2
        rstp-max-age : 默认 20
        rstp-forward-delay : 默认 15
        rstp-transmit-hold-count : 默认 6

        mac-aging-time : 默认 300 sec
        mac-table-size : 默认 2048

        mcast-snooping-aging-time : 默认 300 sec
        mcast-snooping-table-size : 默认 2048
        mcast-snooping-disable-flood-unregistered : 默认 false

        enable-statistics : true | false(default)

        disable-in-band : true | false(default)
        in-band-queue : queue id
        dp-sec :

    Port : other_config
        stp-enable : true | false port
        stp-port-num :
        stp-path-cost :
        stp-port-priority :

        rstp-enabled : true | false
        rstp-port-num :
        rstp-path-cost
        rstp-port-priority
        rstp-admin-p2p-mac
        rstp-admin-port-state : true(default) | false
        rstp-port-admin-edge : true | false(default)
        rstp-port-auto-edge : true(default) | false
        rstp-port-mcheck : true | false(default)

        mcast-snooping-flood : true | false(default)
        mcast-snooping-flood-reports : true | false(default)

        lacp-system-id : 配置 lacp id(当前选项没有配置时, 为 port 所属 br 的 mac)
        lacp-system-priority : 默认 0
        lacp-time : fast
        lacp-fallback-ab : true | false(default)

        bond-miimon-interval : 200
        bond-detect-mode : carrier | miimon
        bond-hash-basis : 0(default)
        bond-rebalance-interval : [1000, ) 10000(default)

        realdev

    Controller : other_config
        dscp : 最多 [0,63]

    Interface : other_config
        cfm_interval : 1000(default)
        cfm_ccm_vlan : 0 | random
        cfm_ccm_pcp : 0
        cfm_extended : false
        cfm_demand : false
        cfm_opstate : up
        enable-vlan-splinters: false(default)

VLAN

    output_port 和 output_vlan 只能配置其一, 而且必须配置其一

更多参考 man ovs-vswitch.conf.db

ovs-vsctl --no-wait set Open_vSwitch . other_config:max-idle=50000

##基本概念

参考 ofproto-provider.h

### 有用的监控信息

ovs-appctl memory/show

handlers:5 ofconns:1 ports:12 revalidators:3 rules:239968 udpif keys:6

    ports: ofproto->ports
    ops : ofproto->n_pending + hmap_count(&ofproto->deletions)
    rules : 所有表的流表项数目
    ofconns : mgr->all_conns
    packets : 与控制器连接当前还没有发送出去的包的数量
    handlers : thread-handler
    revalidators : thread-revalidators
    udpif keys :

ovs-appctl time/stop
ovs-appctl time/warp  large_msec msec

ovs-appctl converage/show

coverage

    poll_zero_timeout : 由于超时时间为0, 导致被唤醒


ovs-appctl ofproto/list
ovs-appctl ofproto/trace
ovs-appctl ofproto/trace-packet-out
ovs-appctl fdb/show
ovs-appctl fdb/flush
ovs-appctl mdb/show
ovs-appctl mdb/flush
ovs-appctl dpif/dump-dps
ovs-appctl dpif/dump-flows  dump 所有流表, 与 ovs-ofctl dump-flows 类似，但流表更加全面
ovs-appctl ofproto/tnl-push-pop
ovs-appctl upcall/disable-megaflows
ovs-appctl upcall/enable-megaflows
ovs-appctl upcall/disable-ufid
ovs-appctl upcall/enable-ufid
ovs-appctl upcall/set-flow-limit 200000 设置流表限制
ovs-appctl upcall/show : 查看流表数量
ovs-vsctl --no-wait set Open_vSwitch .  other_config:flow-limit=100000 与上面由什么区别？ 上面的设置不能超过这里的设置
ovs-vsctl list Open_VSwitch 查看 other_config:flow-limit 的值
ovs-appctl revalidator/wait
ovs-appctl revalidator/purge

ovs-vsctl list Controller 的 status 可以看到 PACKET_IN 的统计信息(2.3.5 以上版本)
ovs-tcpdump --db_sock unix:PATH -i S_PORT --mirror-to M_PORT --dump-cmd tcpdump -vv port 80 and host 10.1.1.1

将 S_PORT 的流量镜像到 M_PORT, 之后运行 tcpdump 在 M_PORT 抓包, 如果 --mirror-to 没有指定, 将创建名为 miS_PORT 的镜像端口
需要注意的这个镜像端口是一个 tap 设备

其中:
* dump-cmd 是抓包命令, 默认是 tcpdump
* db_sockt 默认为 unix:RUNDIR/db.sock

ovs-pipegen --size 100

创建 size 个流表项,
   priority=32768 metadata=0 %s,actions=load:1->OXM_OF_METADATA[],resubmit(,0)
   priority=1 metadata=0 %s,actions=load:1->OXM_OF_METADATA[],resubmit(,0)
   priority=32768 metadata=1 %s,actions=load:2->OXM_OF_METADATA[],resubmit(,0)
   priority=1 metadata=1 %s,actions=load:2->OXM_OF_METADATA[],resubmit(,0)
   priority=32768 metadata=2 %s,actions=load:3->OXM_OF_METADATA[],resubmit(,0)
   priority=1 metadata=2 %s,actions=load:3->OXM_OF_METADATA[],resubmit(,0)
   priority=32768 metadata=3 %s,actions=load:4->OXM_OF_METADATA[],resubmit(,0)
   priority=1 metadata=3 %s,actions=load:3->OXM_OF_METADATA[],resubmit(,0)

然后输出到标准输出

ovs-pcap

将 pcap 文件以 16 进制输出

ovs-dp-top : TODO

###ofproto 交换机链路聚合

ovs-vsctl add-br ovsbr1

ovs-vsctl add-bond <bridge name> <bond name> <list of interfaces>
ovs-appctl bond/show <bond name>
ovs-appctl lacp/show <bond name>
ovs-vsctl list port <bond name>
ovs-appctl bridge/dump-flows a5
ovs-dpctl dump-flows

**方法一**

ovs-vsctl add-bond ovsbr1 bond0 eth1 eth3
ovs-vsctl set port bond0 lacp=active

**方法二**

ovs-vsctl add-bond ovsbr1 bond0 eth1 eth3 lacp=active
ovs-appctl bond/show bond0
ovs-appctl lacp/show bond0
ovs-vsctl list port bond0

ovs-vsctl set Port bond0 bond_mode=balance-slb
ovs-vsctl set Port bond0 bond_mode=balance-tcp

ovs-vsctl add-bond a5 bond1 eth3 eth4 bond_mode=balance-tcp other_config:lacp-time=fast

###Ovs 与 namespace

ip netns add test_ns1
ovs-vsctl add-port test_br testif1 -- set interface testif1 type=internal
ip link set testif1 netns test_ns1
ip netns exec test_ns1 ip addr add 192.168.1.1/24 dev testif1
ip netns exec test_ns1 ip link set testif1 up

###OVS Bond

OVS(2.3.1)支持模式

* active-backup
* balance-slb : source MAC + vlan tag
* balance-tcp : L2/L3/L4 header 不同 connection 走不同链路. 注: 绑定的交换机必须配置 LACP

ovs-vsctl add-br my_test
ovs-vsctl add-bond my_test bond0 eth0 eth1 eth2
ovs-vsctl add-bond my_test bond0 eth0 eth1 eth2 bond_mode=balance-slb
ovs-vsctl set port my_test bond_mode=balance-slb
ovs-appctl bond/show bond0
ovs-appctl bond/list bond0
ovs-appctl bond/hash bond0
ovs-appctl bond/migrate


###ofport 端口

ovs-ofctl dump-ports ovs0

    OFPST_PORT reply (xid=0x2): 8 ports
      port LOCAL: rx pkts=1366873, bytes=462487719, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=28852724, bytes=2334930553, drop=0, errs=0, coll=0
      port  5: rx pkts=49425127, bytes=8122230011, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=90807573, bytes=16046207616, drop=0, errs=0, coll=0
      port  1: rx pkts=106886595, bytes=38991858694, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=135400145, bytes=14595057059, drop=0, errs=0, coll=0
      port  4: rx pkts=34392345, bytes=3074145124, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=30962095, bytes=2897800325, drop=0, errs=0, coll=0
      port  6: rx pkts=0, bytes=0, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=26072601, bytes=1984434045, drop=0, errs=0, coll=0
      port  7: rx pkts=0, bytes=0, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=26072601, bytes=1984434045, drop=0, errs=0, coll=0
      port  2: rx pkts=151805437, bytes=18752433580, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=170173374, bytes=42169459971, drop=0, errs=0, coll=0
      port  3: rx pkts=40831778, bytes=7006642394, drop=0, errs=0, frame=0, over=0, crc=0
               tx pkts=59534299, bytes=8273995081, drop=0, errs=0, coll=0

ovs-ofctl mod-ports ovs0 eth0

ovs-ofctl add-flow br0 "table=0, priority=0, actions=resubmit(,1)"

ovn-trace --minimal sw0 'inport == "sw0-port1" && eth.src == 00:00:00:00:00:01 && eth.dst == 00:00:00:00:00:02'

ovn-trace --summary sw0 'inport == "sw0-port1" && eth.src == 00:00:00:00:00:01 && eth.dst == 00:00:00:00:00:02'

ovn-trace --detailed sw0 'inport == "sw0-port1" && eth.src == 00:00:00:00:00:01 && eth.dst == 00:00:00:00:00:02'

ovs-appctl ofproto/trace br0 in_port=1,dl_dst=01:80:c2:00:00:10

ovs-appctl ofproto/trace br0 in_port=1,dl_dst=01:80:c2:00:00:05


ovs-vsctl set bridge $bridge other-config:hwaddr=00:00:00:00:00:01
ovs-vsctl add-br br0 -- set Bridge br0 fail-mode=secure
ovs-ofctl add-flow br0 "table=0, dl_src=01:00:00:00:00:00/01:00:00:00:00:00, actions=drop"
ovs-ofctl add-flow br0 "table=0, dl_dst=01:80:c2:00:00:00/ff:ff:ff:ff:ff:f0, actions=drop"
ovs-ofctl add-flow br0 "table=0, priority=0, actions=resubmit(,1)"
ovs-ofctl add-flow br0 "table=1, priority=0, actions=drop"
ovs-ofctl add-flow br0 "table=1, priority=99, in_port=1, actions=resubmit(,2)"
ovs-ofctl add-flows br0 - <<'EOF'
table=1, priority=99, in_port=2, vlan_tci=0, actions=mod_vlan_vid:20, resubmit(,2)
table=1, priority=99, in_port=3, vlan_tci=0, actions=mod_vlan_vid:30, resubmit(,2)
table=1, priority=99, in_port=4, vlan_tci=0, actions=mod_vlan_vid:30, resubmit(,2)
EOF

ovs-ofctl add-flow br0 \
    "table=2 actions=learn(table=10, NXM_OF_VLAN_TCI[0..11], \
                           NXM_OF_ETH_DST[]=NXM_OF_ETH_SRC[], \
                           load:NXM_OF_IN_PORT[]->NXM_NX_REG0[0..15]), \
                     resubmit(,3)"


ovs-appctl ofproto/trace br0 in_port=1,vlan_tci=20,dl_src=50:00:00:00:00:01 -generate
ovs-ofctl add-flow br0 "table=3 priority=50 actions=resubmit(,10), resubmit(,4)"
ovs-ofctl add-flow br0 "table=3 priority=99 dl_dst=01:00:00:00:00:00/01:00:00:00:00:00 actions=resubmit(,4)"
ovs-ofctl add-flow br0 "table=4 reg0=1 actions=1"
ovs-ofctl add-flows br0 - <<'EOF'
table=4 reg0=2 actions=strip_vlan,2
table=4 reg0=3 actions=strip_vlan,3
table=4 reg0=4 actions=strip_vlan,4
EOF

ovs-ofctl add-flows br0 - <<'EOF'
table=4 reg0=0 priority=99 dl_vlan=20 actions=1,strip_vlan,2
table=4 reg0=0 priority=99 dl_vlan=30 actions=1,strip_vlan,3,4
table=4 reg0=0 priority=50            actions=1
EOF

#限速

    "ingress_policing_rate": the maximum rate (in Kbps) that this VM should be allowed to send.
    "ingress_policing_burst": a parameter to the policing algorithm to indicate the maximum amount of data (in Kb) that this interface can send beyond the policing rate.

    ovs-vsctl -- set port tap0  qos=@newqos \
    -- --id=@newqos create qos type=linux-htb other-config:max-rate=100000000 queues=0=@q0,1=@q1 \
    -- --id=@q0 create queue other-config:min-rate=100000000 other-config:max-rate=100000000 \
    -- --id=@q1 create queue other-config:min-rate=500000000 \


    vs-vsctl -- set port s1-eth1 qos=@newqos -- --id=@newqos create qos type=linux-htb \
    queues=0=@q0,1=@q1 -- --id=@q0 create queue other-config:min-rate=200000000 \
    other-config:max-rate=800000000 -- --id=@q1 create queue other-config:min-rate=50000 \
    other-config:max-rate=50000000



ovs-vsctl set interface eth0 ingress_policing_rate=1000
ovs-vsctl set interface eth0 ingress_policing_burst=1000

ovs-vsctl list interface eth0
ovs-vsctl list qos
ovs-vsctl list queue

ovs-vsctl -- destroy QoS tap0 -- clear Port tap0 qos
ovs-vsctl -- destroy queue
ovs-vsctl -- destroy qos


ovs-vsctl --set bridge br0 mirrors=@m-- --id=@m create mirror name=mymirror \
    select-dst-port=id_1 \
    select-src-port=id_2 \
    output-port=id_3


ovs-vsctl set-manager ptcp:6640
ovs-vsctl get-manager

Open vSwitch uses the Linux "traffic-control" capability for rate-limiting. If you are not seeing
the configured rate-limit have any effect, make sure that your kernel is built with "ingress qdisc"
enabled, and that the user-space utilities (e.g., /sbin/tc) are installed.


Open vSwitch's rate-limiting uses policing, which does not queue packets. It drops any packets beyond
the specified rate. Specifying a larger burst size lets the algorithm be more forgiving, which is
important for protocols like TCP that react severely to dropped packets. Setting a burst size of less
than than the MTU (e.g., 10 kb) should be avoided.

For TCP traffic, setting a burst size to be a sizeable fraction (e.g., > 10%) of the overall policy rate
helps a flow come closer to achieving the full rate. If a burst size is set to be a large fraction of
the overall rate, the client will actually experience an average rate slightly higher than the specific
policing rate.

For UDP traffic, set the burst size to be slightly greater than the MTU and make sure that your performance
tool does not send packets that are larger than your MTU (otherwise these packets will be fragmented,
causing poor performance).


###rule 流表

ovs-ofctl dump-flows
ovs-ofctl add-flow a5 "priority=65535, nw_dst=10.1.4.100, tcp_dst=8080, tcp,tcp_flags=+syn, actions=controller" -O OpenFlow13
sudo ovs-ofctl add-flow ovs0 "tcp,tcp_flags=+rst, actions=controller" -O OpenFlow13
sudo ovs-ofctl add-flow ovs0 "tcp,tcp_flags=+syn, actions=controller" -O OpenFlow13
sudo ovs-ofctl add-flow ovs0 "priority=65535, tcp,tcp_flags=+fin, actions=controller" -O OpenFlow13

ovs-ofctl add-flow br-int "table=0, priority=10, in_port=1,dl_src=00:00:00:00:00:01,actions=resubmit(,1)"

//packets with a multicast source address are not valid, so we can add a flow to drop them at ingress to the switch with:
ovs-ofctl add-flow br0 "table=0, dl_src=01:00:00:00:00:00/01:00:00:00:00:00, actions=drop"

//A switch should also not forward IEEE 802.1D Spanning Tree Protocol (STP) packets
ovs-ofctl add-flow br0 "table=0, dl_dst=01:80:c2:00:00:00/ff:ff:ff:ff:ff:f0, actions=drop"

ovs-appctl ofproto/trace ovsbr0 in_port=3,tcp,nw_src=10.0.0.2,tcp_dst=22

###ofgroup


sudo ovs-ofctl add-group s11 group_id=1,type=select,selection_method=hash,fields(eth_dst,ip_dst,tcp_dst),bucket=output:10,bucket=output:11
sudo ovs-ofctl add-group s11 group_id=1236,type=select,selection_method=dp_hash,bucket=bucket_id:0,actions=output:10,bucket=bucket_id:1,actions=output:11
sudo ovs-ofctl add-group s11 group_id=1234,type=select,selection_method=hash,fields(eth_dst,ip_dst,tcp_dst),bucket=output:10,bucket=output:11
sudo ovs-ofctl add-group s11 group_id=1234,type=select,selection_method=hash,fields(eth_dst,ip_dst,tcp_dst),bucket=bucket_id:0,actions=output:10,bucket=bucket_id:1,actions=output:11
sudo ovs-ofctl add-group s11 group_id=8192,type=select,selection_method=hash,fields(ip_dst=255.255.255.0,nw_proto,tcp_src),bucket=bucket_id:0,weight:100,watch_port:1,actions=output:1,bucket=bucket_id:1,weight:200,watch_port:2,actions=output:2,bucket=bucket_id:2,weight:200,watch_port:3,actions=output:3
sudo ovs-ofctl add-group s11 group_id=2271560481,type=select,selection_method=hash,selection_method_param=7,bucket=bucket_id:0,weight:100,watch_port:1,actions=output:1,bucket=bucket_id:1,weight:200,watch_port:2,actions=output:2,bucket=bucket_id:2,weight:200,watch_port:3,actions=output:3
sudo ovs-ofctl add-group s11 group_id=1236,type=select,selection_method=dp_hash,bucket=output:10,bucket=output:11
注：以上命令需要 ovs-2.4及以上 openflow1.5 及以上

sudo ovs-ofctl add-group s11 group_id=1,type=select,bucket=output:1,bucket=output:2,bucket=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s11 ip,nw_src=10.1.1.10,nw_dst=10.1.2.10,priority=2,actions=group:1 -O OpenFlow13

sudo ovs-ofctl add-group s31 group_id=2,type=select,bucket=output:1,bucket=output:2,bucket=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s31 ip,nw_src=10.1.2.10,nw_dst=10.1.1.10,priority=2,actions=group:2 -O OpenFlow13


sudo ovs-ofctl add-flow s11 ip,nw_dst=10.1.2.10,priority=2,actions=group:1  -O OpenFlow13
sudo ovs-ofctl add-flow s11 ip,nw_dst=10.1.1.10,priority=2,actions=output:4  -O OpenFlow13

sudo ovs-ofctl add-flow s21 ip,nw_dst=10.1.2.11,priority=2,actions=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s21 ip,nw_dst=10.1.2.10,priority=2,actions=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s21 ip,nw_dst=10.1.1.10,priority=2,actions=output:1 -O OpenFlow13

sudo ovs-ofctl add-flow s22 ip,nw_dst=10.1.2.11,priority=2,actions=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s22 ip,nw_dst=10.1.2.10,priority=2,actions=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s22 ip,nw_dst=10.1.1.10,priority=2,actions=output:1 -O OpenFlow13

sudo ovs-ofctl add-flow s23 ip,nw_dst=10.1.2.11,priority=2,actions=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s23 ip,nw_dst=10.1.2.10,priority=2,actions=output:3 -O OpenFlow13
sudo ovs-ofctl add-flow s23 ip,nw_dst=10.1.1.10,priority=2,actions=output:1 -O OpenFlow13

sudo ovs-ofctl add-flow s31 "priority=2,ip,nw_dst=10.1.1.10,actions=group:2" -O OpenFlow13
sudo ovs-ofctl add-flow s31 "priority=2,ip,nw_dst=10.1.2.10,actions=output:4" -O OpenFlow13
sudo ovs-ofctl add-flow s31 "priority=2,ip,nw_dst=10.1.2.11,actions=output:5" -O OpenFlow13





$sudo ovs-ofctl --protocols=OpenFlow13 add-group s1 group_id=1,type=select,\
bucket=mod_dl_dst:00:00:00:00:00:02,mod_nw_dst:10.0.0.2,output:2,\
bucket=mod_dl_dst:00:00:00:00:00:03,mod_nw_dst:10.0.0.3,output:3,\
bucket=mod_dl_dst:00:00:00:00:00:04,mod_nw_dst:10.0.0.4,output:4

sudo ovs-ofctl --protocols=OpenFlow13 add-flow s1
ip,nw_dst=10.0.0.5,priority=32769,actions=group:1
$ sudo ovs-ofctl --protocols=OpenFlow13 add-flow s1
ip,actions=mod_dl_src:00:00:00:00:00:05,mod_nw_src:10.0.0.5,goto_table:1

$ sudo ovs-ofctl --protocols=OpenFlow13 add-flow s1
table=1,dl_type=0x800,nw_dst=10.0.0.1,actions=output:1
$ sudo ovs-ofctl --protocols=OpenFlow13 add-flow s1
table=1,dl_type=0x800,nw_dst=10.0.0.2,actions=output:2
$ sudo ovs-ofctl --protocols=OpenFlow13 add-flow s1
table=1,dl_type=0x800,nw_dst=10.0.0.3,actions=output:3
$ sudo ovs-ofctl --protocols=OpenFlow13 add-flow s1
table=1,dl_type=0x800,nw_dst=10.0.0.4,actions=output:4


基于 group 的负载均衡

client 10.2.1.41

server1 10.2.1.100 eth1 ovs-port 11
server2 10.2.1.100 eth1 ovs-port 2728

ovs-ofctl add-group a5 "group_id=1,type=select,bucket=output:2728,bucket=output:11" -O OpenFlow13
ovs-ofctl add-flow a5 "tcp,nw_dst=10.2.1.100,tp_dst=80,priority=65535,actions=group:1" -O OpenFlow13

其中 server1 和 server2 的 mac 地址必须相同 通过 ifconfig eth1 hw ehter
xxxxxxxxx 修改


## 流量采集

ovs−vsctl -- set Bridge br0 ipfix=@i -- --id=@i create IPFIX targets=\”10.10.10.10:2055\” obs_domain_id=123 obs_point_id=456

ovs-vsctl -- set Bridge s1 ipfix=@i -- --id=@i create IPFIX targets=\"10.0.0.1:4739\" obs_domain_id=123 obs_point_id=456 sampling=64 2d54982b-6cc5-4a8c-845c-cc7ef701da01

ovs-vsctl -- set Bridge s1 ipfix=@i -- --id=@i create IPFIX targets=\"10.0.0.1:4739\" obs_domain_id=123 obs_point_id=456 sampling=64

ovs−vsctl -- set Bridge br0 netflow=@nf -- --id=@nf create NetFlow targets=\"10.10.10.10:2055\" active−timeout=60

ovs−vsctl --id=@s create sFlow agent=eth1 target=\"10.10.10.10:2055\" header=128 sampling=64 polling=10 -- set Bridge br0 sflow=@s

ovs-vsctl -- set Bridge s1 sflow=@sflow -- --id=@sflow create sflow agent=eth0  target=\"10.0.0.1:6343\" header=128 sampling=32 polling=2 0df2b92b-8a83-4a63-acc4-fecf6f8f492f

sudo ovs-vsctl -- --id=@sflow create sflow agent=eth0  target=\"127.0.0.1:6343\" sampling=10 polling=20 -- -- set bridge s1 sflow=@sflow

ovs-vsctl -- set Port port0 ipfix=@i -- --id=@i create IPFIX \
         targets=\"10.24.122.72:4739\" sampling=1 obs_domain_id=123 \
         obs_point_id=456 cache_active_timeout=1 cache_max_flows=128 \
         other_config:enable-tunnel-sampling=true


配置

flow-restore-wait : true | false, false : 删除所有流表
flow-limit : 在flow table中flow entry的数量
stats-update-interval ：将统计信息写入数据库的间隔时间

flow-restore-wait :

 为hot-upgrade使用的，如果设为true则不处理任何的包。一般使用的过程为，先停掉ovs-vswitchd，然后将这个值设为true，启
 动ovs-vswitchd，这个时候不处理任何包，然后使用ovs-ofctl将flow table
 restore到一个正确的状态，最后设置这个值为false，开始处理包

enable-statistics 是否统计

    cpu: cpu 核数
    load_average: 1, 5, 15 minutes of load
    memory : 依次为 MemTotal, MemFree, Buffers, Cached, SwapTotal, SwapFree
    process_NAME : 依次为 Virtual size(KB), Resident set size(KB), since last (re)started by monitor(ms), crashes, monitor started(ms ), CPU used(ms)
    file_systems : mount point, total, used

ovs-vsctl set Open_vSwitch . other_config:enable-statistics=true
ovs-vsctl get Open_vSwitch . statistics

{   cpu="4",
    file_systems="/,31441920,11268184 /backup,31441920,32928 /data,52401156,876180",
    load_average="2.10,2.19,1.79",
    memory="7905040,5432496,2245784,0,0",
    process_ovs-vswitchd="784760,92708,4040,0,2851820,2851820",
    process_ovsdb-server="46604,2516,590,0,2851860,2851860"
}

MemTotal

ovs-vsctl del-port br0 eth-0-5
ovs-vsctl del-port br0 eth-0-6
ovs-vsctl add-bond br0 bond2 eth-0-5 eth-0-5 bond_mode=balance-slb -- set interface eth-0-5 type=switch -- set interface eth-0-6 type=switch

ovs-vsctl add bridge s1 flow_tables 0=@nam1 -- --id=@nam1 create flow_table flow_limit=1000
ovs-vsctl list flow_table
ovs-vsctl set flow_table 850342e5-8d93-4114-beeb-d42fdd0c5c88 flow_limit=10000

组表

n-revalidator-threads: Revalidation threads which read the datapath flow table and maintains them
n-handler-threads : An array of 'struct handler's for upcall handling and flow installation.

sudo ovs-vsctl list Controller
ovs-vsctl set Open_vSwitch . other-config:n-handler-threads=1 other-config:n-revalidator-threads=1
ovs-vsctl --no-wait set Open_vSwitch .  other_config:n-handler-threads=1
ovs-vsctl --no-wait set Open_vSwitch .  other_config:flow-limit=300000
ovs-vsctl get bridge br0  other-config:flow-eviction-threshold
ovs-dpctl show
top -p `pidof ovs-vswitch` -H

ovs-vsctl set Bridge br0 flow_tables:0=@N1 -- \
--id=@N1 create Flow_Table name=table0

ovs-vsctl set Bridge br0 flow_tables:1=@N1 -- \
--id=@N1 create Flow_Table name=table1

ovs-vsctl set Flow_Table table0 prefixes=ip_dst,ip_src
ovs-vsctl set Flow_Table table1 prefixes=[]

ovs-vsctl  -- --id=@t0 create Flow_Table name=main  flow-limit=10   --
--id=@t1 create Flow_Table flow-limit=5 overflow-policy=refuse  -- set
bridge br0 flow_tables={1=@t1,0=@t0}

ovs-vsctl add-port ovs-switch p0 -- set Interface p0 ofport_request=100

创建一个端口 p0，设置端口 p0 的 OpenFlow 端口编号为
100（如果在创建端口的时候没有指定 OpenFlow 端口编号，OVS 会自动生成一个）。

ovs-vsctl set Interface p0 type=internal

设置网络接口设备的类型为“internal”。对于 internal 类型的的网络接口，OVS 会同时在
Linux 系统中创建一个可以用来收发数据的模拟网络设备。我们可以为这个网络设备配置
IP 地址、进行数据监听等等。

ovs-vsctl list controller

ovs-dpctl show

system@ovs-system:
lookups: hit:12173 missed:712 lost:0
flows: 0
port 0: ovs-system (internal)
    port 1: ovs-switch (internal)
    port 2: p0 (internal)
    port 3: p1 (internal)
    port 4: p2 (internal)

ovs-ofctl add-flow ovs-switch "table=0,priority=65535,tcp,in_port=4,nw_src=10.1.2.25,nw_dst=10.1.2.100,tp_src=80 actions=output:4"

屏蔽所有进入 OVS 的以太网广播数据包

ovs-ofctl add-flow ovs-switch "table=0, dl_src=01:00:00:00:00:00/01:00:00:00:00:00, actions=drop"


屏蔽 STP 协议的广播数据包

ovs-ofctl add-flow ovs-switch "table=0, dl_dst=01:80:c2:00:00:00/ff:ff:ff:ff:ff:f0, actions=drop"

生成数据包

ovs-appctl ofproto/trace ovs-switch in_port=100,dl_src=66:4e:cc:ae:4d:20, dl_dst=46:54:8a:95:dd:f8 -generate

ovsdb-client dump

ovs-ofctl add-flow s1 "table=0,priority=65535,arp,arp_tpa=10.0.0.254 actions=LOCAL"

sudo ovs-vsctl -- --columns=name,ofport list Interface

监控通信

sudo ofctl snoop



配置
ovsdb-tool show-log /etc/openvswitch/conf.db

日志

ovs-appctl vlog/list
ovs-appctl vlog/set ofproto:file:dbg

http://openvswitch.org/pipermail/discuss/2014-December/015968.html


数据结构

Open_vSwitch
    Bridge
        name
        datapath_types
        protocols : 10,11,12,13,14,15
        fail_mode : standalone, secure
        status
        mcast_snooping_enable
        stp_enable
        rstp_enable
        rstp_status
        flow_tables
        Port
            Interface
                name
                type
                ingress_policing_rate
                ingress_policing_burst
                mac_in_use
                mac
                ifindex
                ofport
                ofport_request
                bfd
                bfd_status
                cfm_mpid
                cfm_remote_mpids
                cfm_flap_count
                cfm_fault
                cfm_fault_status
                cfm_remote_opstate: up, down
                cfm_health
                lacp_current
                lldp
                statistics
                status
                admin_state: up, down
                link_state
                link_resets
                link_speed
                duplex
                mtu
            vlan_mode : trunks, access, native-tagged, native-untagged
            Qos
                Queues
            mac
            bond_mode : balance-tcp, balance-slb, active-backup
            lacp      : active, passive, off
        Mirror
            name
            select_all
            select_src_port
            select_dst_port
            select_vlan
            output_port
            output_vlan
            statistics
        NetFlow
            targets
            engine_type
        sFlow
            targets
            sampling
            polling
            header
            agent
        IPFIX
            targets
            sampling
            obs_domain_id
            obs_point_id
            cache_max_flows
        Controller
            targets
            max_backoff
            inactivity_probe
            connection_mode : in-band, out-of-band
            local_ip
            local_netmask
            local_gateway
            enable_async_messages
            controller_rate_limit
            controller_burst_limit
            is_connected
            role : other, master, slave
            status

        Flow_Table : 0 ~ 254
            name
            flow_limit
            overflow_policy
            groups
            prefixes

        AutoAttach
            system_name
            system_description
            mappings

    Manager
        targets
        max_backoff
        inactivity_probe
        connection_mode
        is_connected
        status

    SSL
        private_key
        certificate
        ca_cert
        bootstrap_ca_cert

    Flow_Sample_Collector_Set
    IPFIX

运行顺序

    bridge_init()
        ovsdb_idl_create()

    bridge_run()
        ovsdb_idl_run(idl)
            jsonrpc_session_run(idl->session);
                jsonrpc_run(rpc)

        bridge_run__();
            ofproto_run(br->ofproto)

    unixctl_server_run(struct unixctl_server *server)
        run_connection(conn)
            jsonrpc_run(conn->rpc)
            jsonrpc_recv(conn->rpc, msg)
            process_command(conn, msg)

void bridge_init(const char *remote)

void bridge_run(void)

struct ovsdb_idl ovsdb_idl_create(request, class, true,true)

    初始化一个 ovsdb_idl 结构对象

void ovsdb_idl_run(struct ovsdb_idl *idl)

void jsonrpc_session_run(struct jsonrpc_session *s)
    1. s->pstream 不为空, ps->pstream 接受请求, 如果收到请求, 通过 s->reconnect
    确认链路是否连接, 初始化 s->rpc

void jsonrpc_run(struct jsonrpc *rpc)

    从 rpc->output 中取出元素, 发送到 rpc-stream

void unixctl_server_run(struct unixctl_server *server)

    pstream_accept() 接受请求, 初始化 10 个 server->conns
    对应每个 server->conns 元素, 接受请求,  处理请求

static init run_connection(struct unixctl_conn *conn)

static void process_command(struct unixctl_conn *conn, struct jsonrpc_msg *request)

    定义 struct unixctl_command *command;
    1. 从 request->params 中提取到 argv
    2. request->method 中初始化 command
    3. 调用 command->cb(conn, argv, argv.names, command->aux);


支持的命令

    unixctl_command_register("list-commands", "", 0, 0, unixctl_list_commands,
                             NULL);
    unixctl_command_register("version", "", 0, 0, unixctl_version, NULL);

    unixctl_command_register("qos/show", "interface", 1, 1,
                             qos_unixctl_show, NULL); unixctl_command_register("bridge/dump-flows", "bridge", 1, 1,
                             bridge_unixctl_dump_flows, NULL);
    unixctl_command_register("bridge/reconnect", "[bridge]", 0, 1,
                             bridge_unixctl_reconnect, NULL);

    //lacp_init()
    unixctl_command_register("lacp/show", "[port]", 0, 1,
                             lacp_unixctl_show, NULL);
    //bond_init()
    unixctl_command_register("bond/list", "", 0, 0, bond_unixctl_list, NULL);
    unixctl_command_register("bond/show", "[port]", 0, 1, bond_unixctl_show,
                             NULL);
    unixctl_command_register("bond/migrate", "port hash slave", 3, 3,
                             bond_unixctl_migrate, NULL);
    unixctl_command_register("bond/set-active-slave", "port slave", 2, 2,
                             bond_unixctl_set_active_slave, NULL);
    unixctl_command_register("bond/enable-slave", "port slave", 2, 2,
                             bond_unixctl_enable_slave, NULL);
    unixctl_command_register("bond/disable-slave", "port slave", 2, 2,
                             bond_unixctl_disable_slave, NULL);
    unixctl_command_register("bond/hash", "mac [vlan] [basis]", 1, 3,
                             bond_unixctl_hash, NULL);
    //cfm_init();
    unixctl_command_register("cfm/show", "[interface]", 0, 1, cfm_unixctl_show,
                             NULL);
    unixctl_command_register("cfm/set-fault", "[interface] normal|false|true",
                             1, 2, cfm_unixctl_set_fault, NULL);
    //bfd_init();
    unixctl_command_register("bfd/show", "[interface]", 0, 1,
                             bfd_unixctl_show, NULL);
    unixctl_command_register("bfd/set-forwarding",
                             "[interface] normal|false|true", 1, 2,
                             bfd_unixctl_set_forwarding_override, NULL);
    //ovs_numa_init();

    //stp_init()
    unixctl_command_register("stp/tcn", "[bridge]", 0, 1, stp_unixctl_tcn,
                             NULL);

    //lldp_init()
    unixctl_command_register("autoattach/status", "[bridge]", 0, 1,
                             aa_unixctl_status, NULL);
    unixctl_command_register("autoattach/show-isid", "[bridge]", 0, 1,
                             aa_unixctl_show_isid, NULL);
    unixctl_command_register("autoattach/statistics", "[bridge]", 0, 1,
                             aa_unixctl_statistics, NULL);



    unixctl_command_register("exit", "", 0, 0, ovs_vswitchd_exit, &exiting);

    unixctl_command_register("memory/show", "", 0, 0, memory_unixctl_show, NULL);


#加载模块：
insmod xt_IPID
insmod cls_u32                                                                                         
insmod cls_fw  
insmod sch_htb
insmod sch_sfq
insmod sch_prio
#启用IMQ虚拟网卡
ip link set imq0 up
ip link set imq1 up
#删除旧队列
tc qdisc del dev imq0 root
tc qdisc del dev imq1 root
#上传设置
#增加根队列，未标记数据默认走26
tc qdisc add dev imq0 root handle 1: htb default 26
#增加总流量规则
tc class add dev imq0 parent 1: classid 1:1 htb rate 350kbit
#增加子类
tc class add dev imq0 parent 1:1 classid 1:20 htb rate 80kbit ceil 250kbit prio 0
tc class add dev imq0 parent 1:1 classid 1:21 htb rate 80kbit ceil 250kbit prio 1
tc class add dev imq0 parent 1:1 classid 1:22 htb rate 80kbit ceil 250kbit prio 2
tc class add dev imq0 parent 1:1 classid 1:23 htb rate 80kbit ceil 250kbit prio 3
tc class add dev imq0 parent 1:1 classid 1:24 htb rate 80kbit ceil 250kbit prio 4
tc class add dev imq0 parent 1:1 classid 1:25 htb rate 50kbit ceil 250kbit prio 5
tc class add dev imq0 parent 1:1 classid 1:26 htb rate 50kbit ceil 150kbit prio 6
tc class add dev imq0 parent 1:1 classid 1:27 htb rate 50kbit ceil 100kbit prio 7
#为子类添加SFQ公平队列,每10秒重置
tc qdisc add dev imq0 parent 1:20 handle 20: sfq perturb 10
tc qdisc add dev imq0 parent 1:21 handle 21: sfq perturb 10
tc qdisc add dev imq0 parent 1:22 handle 22: sfq perturb 10
tc qdisc add dev imq0 parent 1:23 handle 23: sfq perturb 10
tc qdisc add dev imq0 parent 1:24 handle 24: sfq perturb 10
tc qdisc add dev imq0 parent 1:25 handle 25: sfq perturb 10
tc qdisc add dev imq0 parent 1:26 handle 26: sfq perturb 10
tc qdisc add dev imq0 parent 1:27 handle 27: sfq perturb 10
#添加过滤规则配合Iptables Mark标记
#tc filter add dev imq0 parent 1:0 protocol ip u32 match ip sport 22 0xffff flowid 1:10
#使用U32标记数据，下面使用Iptables mark，容易。
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 20 fw flowid 1:20
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 21 fw flowid 1:21
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 22 fw flowid 1:22
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 23 fw flowid 1:23
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 24 fw flowid 1:24
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 25 fw flowid 1:25
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 26 fw flowid 1:26
tc filter add dev imq0 parent 1:0 prio 0 protocol ip handle 27 fw flowid 1:27
#上传数据转入特定链
iptables -t mangle -N MYSHAPER-OUT
iptables -t mangle -A POSTROUTING -o pppoe-wan -j MYSHAPER-OUT
iptables -t mangle -A MYSHAPER-OUT -j IMQ --todev 0
#为特定数据打上标记配合之前过滤规则
#iptables -t mangle -I MYSHAPER-OUT -s 192.168.1.16 -j MARK --set-mark 27 #限制特定IP上传速度
#iptables -t mangle -I MYSHAPER-OUT -s 192.168.1.16 -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p tcp --tcp-flags SYN,RST,ACK SYN -j MARK --set-mark 20 #提高HTTP连接速度
iptables -t mangle -A MYSHAPER-OUT -p tcp --tcp-flags SYN,RST,ACK SYN -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p udp --dport 53 -j MARK --set-mark 20 #DNS查询
iptables -t mangle -A MYSHAPER-OUT -p udp --dport 53 -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p icmp -j MARK --set-mark 21 #ICMP数据
iptables -t mangle -A MYSHAPER-OUT -p icmp -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p tcp -m length --length :64 -j MARK --set-mark 21 #小数据包
iptables -t mangle -A MYSHAPER-OUT -p tcp -m length --length :64 -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p tcp --dport 22 -j MARK --set-mark 22 #SSH连接
iptables -t mangle -A MYSHAPER-OUT -p tcp --dport 22 -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p udp --dport 1194 -j MARK --set-mark 22 #VPN连接
iptables -t mangle -A MYSHAPER-OUT -p udp --dport 1194 -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p tcp --dport 80 -j MARK --set-mark 23 #HTTP连接
iptables -t mangle -A MYSHAPER-OUT -p tcp --dport 80 -j RETURN
iptables -t mangle -A MYSHAPER-OUT -p tcp --dport 443 -j MARK --set-mark 24 #HTTPS连接
iptables -t mangle -A MYSHAPER-OUT -p tcp --dport 443 -j RETURN
#上传设置完成
  
#下载设置
#增加根队列，未标记数据默认走24
tc qdisc add dev imq1 handle 1: root htb default 24
tc class add dev imq1 parent 1: classid 1:1 htb rate 3500kbit
#添加子类
tc class add dev imq1 parent 1:1 classid 1:20 htb rate 1000kbit ceil 1500kbit prio 0
tc class add dev imq1 parent 1:1 classid 1:21 htb rate 1500kbit ceil 2500kbit prio 1
tc class add dev imq1 parent 1:1 classid 1:22 htb rate 2000kbit ceil 3500kbit prio 2
tc class add dev imq1 parent 1:1 classid 1:23 htb rate 1000kbit ceil 1500kbit prio 3
tc class add dev imq1 parent 1:1 classid 1:24 htb rate 1000kbit ceil 1500kbit prio 4
#为子类添加SFQ公平队列
tc qdisc add dev imq1 parent 1:20 handle 20: sfq perturb 10
tc qdisc add dev imq1 parent 1:21 handle 21: sfq perturb 10
tc qdisc add dev imq1 parent 1:22 handle 22: sfq perturb 10
tc qdisc add dev imq1 parent 1:23 handle 23: sfq perturb 10
tc qdisc add dev imq1 parent 1:24 handle 24: sfq perturb 10
#过滤规则
tc filter add dev imq1 parent 1:0 prio 0 protocol ip handle 20 fw flowid 1:20
tc filter add dev imq1 parent 1:0 prio 0 protocol ip handle 21 fw flowid 1:21
tc filter add dev imq1 parent 1:0 prio 0 protocol ip handle 22 fw flowid 1:22
tc filter add dev imq1 parent 1:0 prio 0 protocol ip handle 23 fw flowid 1:23
tc filter add dev imq1 parent 1:0 prio 0 protocol ip handle 24 fw flowid 1:24
#下载数据转入特定链
iptables -t mangle -N MYSHAPER-IN
iptables -t mangle -A PREROUTING -i pppoe-wan -j MYSHAPER-IN
iptables -t mangle -A MYSHAPER-IN -j IMQ --todev 1
#分类标记数据
#iptables -t mangle -A MYSHAPER-IN -d 192.168.1.16 -j MARK --set-mark 23 #限制特定IP下载速度
#iptables -t mangle -A MYSHAPER-IN -d 192.168.1.16 -j RETURN
iptables -t mangle -A MYSHAPER-IN -p tcp -m length --length :64 -j MARK --set-mark 20 #小数据优先
iptables -t mangle -A MYSHAPER-IN -p tcp -m length --length :64 -j RETURN
iptables -t mangle -A MYSHAPER-IN -p icmp -j MARK --set-mark 20 #ICMP数据
iptables -t mangle -A MYSHAPER-IN -p icmp -j RETURN
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 22 -j MARK --set-mark 21 #SSH连接
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 22 -j RETURN
iptables -t mangle -A MYSHAPER-IN -p udp --sport 1194 -j MARK --set-mark 21 #VPN连接
iptables -t mangle -A MYSHAPER-IN -p udp --sport 1194 -j RETURN
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 443 -j MARK --set-mark 22 #HTTPS连接
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 443 -j RETURN
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 80 -j MARK --set-mark 22 #HTTP连接
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 80 -j RETURN
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 0:1024 -j MARK --set-mark 23 #系统服务端口连接
iptables -t mangle -A MYSHAPER-IN -p tcp --sport 0:1024 -j RETURN
#下载设置完成

## Cookie

# add a flow
ovs-ofctl add-flow br0 cookie=0xf,tcp,tcp_dst=22,actions=mod_nw_tos:128,normal

# To delte this flow
ovs-ofctl del-flows br0 cookie=0xf/-1,tcp,tcp_dst=22
# Or simply
ovs-ofctl del-flows br0 cookie=0xf/-1

# trace a flow
ovs-appctl ofproto/trace br0 tcp,tcp_dst=22


## port ranger

Another way is  to  look at the binary representations of 1000 and 1999, as follows:

    0011 1110 1000
    0111 1100 1111

and  then  to  transform  those into a series of bitwise matches that accomplish the same results:

    0011 1110 1xxx
    0011 1111 xxxx
    010x xxxx xxxx
    0110 xxxx xxxx
    0111 0xxx xxxx
    0111 10xx xxxx
    0111 1100 xxxx

which become the following when written in the  syntax  required by ovs-ofctl:

    tcp,tcp_src=0x03e8/0xfff8
    tcp,tcp_src=0x03f0/0xfff0
    tcp,tcp_src=0x0400/0xfe00
    tcp,tcp_src=0x0600/0xff00
    tcp,tcp_src=0x0700/0xff80
    tcp,tcp_src=0x0780/0xffc0
    tcp,tcp_src=0x07c0/0xfff0

0-63

    0000 0000 0000
    0000 0011 1111

    0000 00xx xxxx

    tcp,tcp_src=0x0/0xffc0

64-127

    0000 0100 0000
    0000 0111 1111

    0000 01xx xxxx

    tcp,tcp_src=0x0040/0xffc0

128-191

    0000 1000 0000
    0000 1011 1111

    0000 10xx xxxx

    tcp,tcp_src=0x0080/0xffc0

192-255

    0000 1100 0000
    0000 1111 1111

    0000 11xx xxxx

    tcp,tcp_src=0x00c0/0xffc0

256-319

    0001 0000 0000
    0001 0011 1111

    0001 00xx xxxx

    tcp,tcp_src=0x0100/0xffc0

320-383

    0001 0100 0000
    0001 0111 1111

    0001 01xx xxxx

    tcp,tcp_src=0x0140/0xffc0

## ip int to string

socket.inet_ntoa(struct.pack('!L', 167903528))
