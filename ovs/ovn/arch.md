


## 架构

                                         CMS
                                          |
                                          |
                            +-------------|-------------+
                            |             |             |
                            |       OVN/CMS Plugin      |
                            |             |             |
                            |             |             |
                            |     OVN Northbound DB     |
                            |             |             |
                            |             |             |
                            |         ovn-northd        |
                            |             |             |
                            +-------------|-------------+
                                          |
                                          |
                                +-----------------------+
                                |  OVN Southbound DB    |
                                |                       |
                                |                       |
                                |  [Physical Network]   |
                                |  [ Binding tables ]   |
                                |  [Logical Network ]   |
                                +-----------------------+
                                          |
                                          |
                       +------------------+------------------+
                       |                  |                  |
         HV 1          |                  |    HV n          |
       +---------------|---------------+  .  +---------------|---------------+
       |               |               |  .  |               |               |
       |        ovn-controller         |  .  |        ovn-controller         |
       |         |          |          |  .  |         |          |          |
       |         |          |          |     |         |          |          |
       |  ovs-vswitchd   ovsdb-server  |     |  ovs-vswitchd   ovsdb-server  |
       |                               |     |                               |
       +-------------------------------+     +-------------------------------+

sw0-port1 and sw0-port2 on separate hosts:

    +--------------------------------------+
    |                                      |
    |             Host A                   |
    |                                      |
    |   +---------+                        |
    |   |sw0-port1| --> ingress pipeline   |
    |   +---------+           ||           |
    |                         ||           |
    +-------------------------||-----------+
                              ||
                              \/
                         geneve tunnel
                              ||
                              ||
    +-------------------------||-----------+
    |                         ||           |
    |             Host B      ||           |
    |                         ||           |
    |   +---------+           \/           |
    |   |sw0-port2| < -- egress pipeline   |
    |   +---------+                        |
    |                                      |
    +--------------------------------------+

sw0-port1 and sw0-port2 on the same host:

    +--------------------------------------------------------------------------+
    |                                                                          |
    |                               Host A                                     |
    |                                                                          |
    |   +---------+                                              +---------+   |
    |   |sw0-port1| --> ingress pipeline --> egress pipeline --> |sw0-port2|   |
    |   +---------+                                              +---------+   |
    |                                                                          |
    +--------------------------------------------------------------------------+












## 概念

Gateway : tunnel-based logical  network  into a physical network by bidirectionally forwarding packets between tunnels and a physical Ethernet port.
chassis : 包括 Hypervisors 和 gateways.
integration bridge
VIF : vif-id, mac

状态信息从南到北流动, 配置信息从北到南流动

### Life Cycle of a VIF


### 逻辑网络

逻辑网络与物理网络通过 tunnel 或其他封装隔离, 可用理解为
VPC, 逻辑网络可以有自己的 IP (可以和物理网络的 IP 重叠)

* Logical Port :
* Logical Switch : the  logical  version  of  Ethernet switches.
* Logical Route : logical version of IP routers
* Logical Datapath : logical version of an  OpenFlow switch
* Localnet ports : 连接逻辑网络与物理网络(通过 OVS patch 端口)
* Logical patch ports : 联通逻辑交换机与逻辑路由器

### 涉及的表

OVN Northbound : Logical_Switch_Port
Binding table : chassis, parent_port
OVN Southbound database : Logical_Flow

### 虚拟机网络

1. 每个虚拟机的一个网卡对应一个 VIF

### 容器网络

1. 一个 VIF 对应多个 CIF
2. 每个 CIF 属于不同的 VLAN, 通过 vlan id 来区别不同的容器
3. 容器内的包出去的时候加 VLAN ID, 进去的时候去 VLAN ID

### 物理网络

虚拟网络中的包被封装后在物理网络中传输, 封装包括 STT, Geneve, VXLAN


tunnel key : logical datapath field, logical input port field, logical output port field

Table 0 : 物理网络到逻辑网络的转换, 依赖 logical datapath field, logical input port
table 65 : 逻辑网络到物理网络的转换
egress pipeline  : 包出去执行, 48 - 63
ingress pipeline : 包进来时执行 32 - 47
table 32 : remote hypervisors
table 33 : local hypervisor
Logical_Flow tables : 0 through 15
OpenFlow  tables : 16 through 31
logical ingress pipeline : 16
logical egress pipeline : 33
table 34 : whether packets whose logical ingress and egress port are the same should be discarded.
table 64 : OpenFlow loopback

### VTEP 网关

* VTEP logical switch
* OVN logical network
* VTEP gateway : 注册到 VTEP database
* VTEP physical-switch

multiple VTEP gateways can attach to the same VTEP logical switch.


## 术语

逻辑 Datapath : Logical Datapath
逻辑路由器: Logical Route
逻辑交换机: Logical Switch
逻辑端口: Logical Port
逻辑网络: logical network
物理网络: physical network
CIF : container interface


## 参考

https://blog.russellbryant.net/2016/11/11/ovn-logical-flows-and-ovn-trace/
