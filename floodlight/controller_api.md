core 模块
--------------------

/wm/core/module/all/json

* 概述: 获取所有模块，包括模块实现的接口，依赖，是否加载
* 方法: GET

/wm/core/module/loaded/json

* 概述: 获取所有加载的模块，包括模块实现的接口，依赖，是否加载
* 方法: GET

/wm/core/switch/{switchId}/role/json

* 概述: 交换机dpid 为 switchId 的角色信息
* 方法: GET

/wm/core/switch/all/{statType}/json

* 概述: 获取所有交换机的统计信息, statType 可选为 port, flow, queue,aggregate,desc,table,features
* 方法: GET
* 例子: GET http://10.0.0.1:8080/wm/core/switch/all/table/json 查看连接到当前控制器的所有交换机支持的流表数量和已经使用的数量

/wm/core/switch/{switchId}/{statType}/json

* 概述: 获取dpid 为 switchId 的统计信息，statType  port, flow, queue,aggregate,desc,table,features
* 方法: GET
* 例子: GET http://10.0.0.1:8080/wm/core/switch/00:00:00:1e:08:09:20:00/table/json
查看连接到当前控制器的 dpid 为 00:00:00:1e:08:09:20:00 的交换机支持的流表数量和已经使用的数量

/wm/core/controller/switches/json 

* 概述: 获取连接到当前控制器的所有交换机的详细信息
* 方法: GET

/wm/core/counter/{counterTitle}/json

* 概述:
* 方法:

/wm/core/counter/{switchId}/{counterName}/json

* 概述:
* 方法:

/wm/core/counter/categories/{switchId}/{counterName}/{layer}/json

* 概述:
* 方法:

/wm/core/memory/json

* 概述: 控制器内存使用情况
* 方法: GET

/wm/core/packettrace/json

* 概述: 依赖 facebook Thrift, 目前不可用
* 方法: GET

/wm/core/storage/tables/json

* 概述: 控制器目前的内存数据库表的信息
* 方法: GET

/wm/core/controller/summary/json

* 概述: 控制器的概述，交换机，主机数，链路等信息
* 方法: GET

/wm/core/role/json

* 概述: 控制器的角色信息
* 方法: GET

/wm/core/health/json

* 概述: 还没有实现，但是可以做一些工作，进行控制器的健康进行深度检查
* 方法: GET

/wm/core/system/uptime/json

* 概述: 控制器启动的时间
* 方法: GET

debugCounter 模块
--------------------

/wm/debugcounter/{param1}/{param2}/{param3}/{param4}/

/wm/debugcounter/{param1}/{param2}/{param3}/{param4}

/wm/debugcounter/{param1}/{param2}/{param3}/

/wm/debugcounter/{param1}/{param2}/{param3}

/wm/debugcounter/{param1}/{param2}/

/wm/debugcounter/{param1}/{param2}

/wm/debugcounter/{param1}/

/wm/debugcounter/{param1}

/wm/debugcounter/

/wm/debugcounter

* 概述: 计数调试信息,比如 packet_in 的数量
* 方法: GET POST

其中 {param1} 为 null(=all), all, 或具体的模块名()
     {param2}/{param3}/{param4} : 为具体模块的层级

此外, 通过 POST 可以 enable 或 disable 一个模块的计数器
     {\"reset\":true}   重置 {param1} 计数器
     {\"enable\":true}  enable {param1}计数器
     {\"enable\":false} disable {param1}计数器

其中, enable 和 disable 只能是 CounterType.ON_DEMAND 类型的计数器.
关于计数器类型可以是 ON_DEMAND 或 ALWAYS_COUNT

POST: 可以重置所有的计数器, 一个模块的计数器, 一个模块具体拓扑的计数器
      可以 enable ON_DEMAND 类型计数器, disable ON_DEMAND 类型计数器

* 举例:

curl http://{controller}:{port}/wm/debugcounter/all : 获取所有计数器
curl http://{controller}:{port}/wm/debugcounter/net.floodlightcontroller.devicemanager.internal/: 获取模块 devicemanager 所有计数器
curl http://{controller}:{port}/wm/debugcounter/net.floodlightcontroller.devicemanager.internal/all : 获取模块所有计数器及信息

curl -X POST -d "{\"reset\":true}" http://{controller}:{port}/wm/debugcounter/all : 重置所有计数器

curl -X POST -d "{\"reset\":true}" http://{controller}:{port}/wm/debugcounter/DeivceManage: 重置所有计数器

curl -X POST -d "{\"enable\":true}" http://{controller}:{port}/wm/debugcounter/all
curl -X POST -d "{\"enable\":false}" http://{controller}:{port}/wm/debugcounter/all

debugEvent 模块
--------------------

/wm/debugevent/{param1}/{param2}/

/wm/debugevent/{param1}/{param2}

/wm/debugevent/{param1}/

/wm/debugevent/{param1}

/wm/debugevent/

* 概述: 有关事件的调试信息,比如 packet_in 事件, 其中 {param1} 可选为 all, moduleName, 如果 param1 不为空，param2 可以为该模块下的具体事件
* 方法: GET
* 举例:

linkdiscovery 模块
--------------------

/wm/linkdiscovery/autoportfast/{state}/json

* 概述: 设置 autoportfast, state 可以为 true,enable 或 false,diable, 这里违背了restful GET 的语义
* 方法: GET
* 举例: GET http://10.1.1.1:8080/wm/linkdiscovery/autoportfast/{state}/json

loadbalancer 模块
--------------------

/pools
/pools/
/pools/{id}
/pools/{id}/
/pools/{id}/{bkid}
/pools/{id}/{bkid}/

* 概述: 对虚拟 pool 的操作
* 方法: GET,POST, PUT, DELETE, 都支持 GET, PUT, DELETE, 只有 /pools 支持 POST

/bkservers
/bkservers/
/bkservers/{id}
/bkservers/{id}/

* 概述: 对虚拟 pool 下 bkserver 的操作
* 方法: GET,POST, PUT, DELETE, 都支持 GET, PUT, DELETE, 只有 /bkservers 支持 POST

/vlans
/vlans/
/vlans/{id}
/vlans/{id}/
/vlans/{id}/{bkid}
/vlans/{id}/{bkid}/

* 概述: 对虚拟 vlan 的操作
* 方法: GET,POST, PUT, DELETE, 都支持 GET, PUT, DELETE, 只有 /vlans 支持 POST

/topology/
/topology

* 概述: 用于同步 mysql 中逻辑拓扑, 其中逻辑拓扑为 pool, bkservers 构建的拓扑
* 方法: GET 获取拓扑信息; PUT 拓扑与 mysql 全同步; POST 拓扑与mysql的增量同步

/flows/{swid}/json

* 概述: 对流表的操作，如果获取，修改，删除, 创建等.
* 方法: GET POST PUT DELETE

/cache/{cachedid}/json
/cache/json

* 概述: 流表缓存信息
* 方法: GET


/pools POST

    {
        "id": "7215",
        "name": "",
        "vip": "10.1.1.100",
        "lbMethod": "1",
        "isactive": "0",
        "protocol": "1",
        "clusterId" : "1234"
        "port": "100"
    }

/bkservers POST

    {
        "id": "0215",
        "name": "",
        "ip": "10.1.1.1",
        "priority": "1",
        "isactive": "1",
        "status": "true",
        "port": "80"
    }

monitor 模块
--------------------

/wm/monitor/hosts/json
/wm/monitor/hosts/{hostid}/json

* 概述: 扫描主机端口的状态信息, 目前只扫描加入 pool 中的 bkserver
* 方法: GET

performance 模块
-------------------

/wm/performance/data/json

* 概述:　获取 packet_in 的能力，如平均处理时间，最大处理时间，最小处理时间
* 方法:  GET

/wm/performance/{perfmonstate}/json

* 概述:　修改 packet_in, perfmonstate 支持 reset, enable,true, false,disable
* 方法:  GET

staticflowentry 模块
-------------------

/wm/staticflowentrypusher/json

* 概述: 静态流表，这里创建的流表都是没有过期时间的
* 方法: POST 创建一条流表; DELETE 删除所有流表
* 举例: 见附录


/wm/staticflowentrypusher/store/json

* 概述: 同上, 操作静态流表，这里创建的流表都是没有过期时间的
* 方法: POST 创建一条流表; DELETE 删除所有流表
* 举例: 见附录

/wm/staticflowentrypusher/delete/json

* 概述: 删除静态流表
* 方法: POST 删除指定 name 流表
* 举例: 见附录

/wm/staticflowentrypusher/clear/{switch}/json

* 概述: 删除静态流表
* 方法: GET 删除指定交换机 dpid 的流表, switch 可以为 all 或交换机的 dpid
* 举例: GET http://10.1.1.1:8080/wm/staticflowentrypusher/clear/all/json

/wm/staticflowentrypusher/list/{switch}/json

* 概述: 列出静态流表, 有 bug
* 方法: GET 列出指定交换机 dpid 的流表, switch 可以为 all 或交换机的 dpid
* 举例: GET http://10.1.1.1:8080/wm/staticflowentrypusher/list/all/json

storage 模块
---------------------

/wm/storage/notify/json

* 概述: 待完成
* 方法: POST

topology模块
---------------------

/wm/topology/links/json

* 概述: 返回全部的物理链路,包括 directed-links 和 external-links, tunnellinks
* 方法: GET

/wm/topology/directed-links/json

* 概述: 返回 directed-links 和 tunnel-links 的物理链路
* 方法: GET

/wm/topology/external-links/json

* 概述: 返回 external-links 的物理链路
* 方法: GET

/wm/topology/tunnellinks/json

* 概述: 返回 tunnel 交换和端口列表
* 方法: GET

/wm/topology/switchclusters/json

* 概述: 返回所属集群交换机列表
* 方法: GET

/wm/topology/broadcastdomainports/json

* 概述: 返回广播域交换机和端口列表
* 方法: GET

/wm/topology/enabledports/json

* 概述: 返回正在连接的交换机和端口列表
* 方法: GET

/wm/topology/blockedports/json

* 概述: 返回阻塞的交换机和端口列表
* 方法: GET

/wm/topology/route/{src-dpid}/{src-port}/{dst-dpid}/{dst-port}/json

* 概述: 返回路由信息
* 方法: GET



ACL 模块
-------------------------

/wm/acl/rules/json
/wm/acl/rules/{switch}/json
/wm/acl/rules/{switch}/{entry}/json

* 概述: 获取访问控制相关流表
* 方法: GET,POST,DELET, 其中所有都支持 GET,DELETE, 只有 /wm/acl/rules/json 支持 POST

* 获取所有规则

/wm/acl/rules/json GET    Content-Type:application/json

* 获取所有 deny 规则

/wm/acl/rules/allSwitch/deny/json GET    Content-Type:application/json

* 获取所有 allow 规则

/wm/acl/rules/allSwitch/allow/json GET    Content-Type:application/json

* 获取所有 allow 满足协议为 ip 的规则

/wm/acl/rules/allSwitch/allow/json?eth_type=ip GET    Content-Type:application/json

* 获取所有 allow 满足协议为 ip, src_ip 不为空的规则

/wm/acl/rules/allSwitch/allow/json?eth_type=ip&only_src_ip=true GET    Content-Type:application/json

* 获取所有 allow 满足协议为 ip, dst_ip 不为空的规则

/wm/acl/rules/allSwitch/allow/json?eth_type=ip&only_dst_ip=true GET    Content-Type:application/json

* 允许 ip 访问

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "ip":"10.1.2.16",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=ip&ip=10.1.2.16

* 禁止 ip 访问

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "ip":"10.1.2.16",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=ip&ip=10.1.2.16

* 允许 arp 访问 10.1.2.16

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "arp",
    "ip":"10.1.2.16",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=arp&ip=10.1.2.16

* 禁止 arp 访问 10.1.2.16

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "arp",
    "ip":"10.1.2.16",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=arp&ip=10.1.2.16

* 允许 icmp 访问 10.1.2.16

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "icmp",
    "ip":"10.1.2.16",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=icmp&ip=10.1.2.16

* 禁止 icmp 访问 10.1.2.16

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "icmp",
    "ip":"10.1.2.16",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=icmp&ip=10.1.2.16

* 允许 tcp 源 10.1.2.16 8000

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "tcp",
    "src_ip": "10.1.2.16",
    "src_port" : "8000",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=ip&protocol=tcp&src_ip=10.1.2.16&src_port=8000

* 禁止源 tcp 10.1.2.16 8000 的流

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "tcp",
    "src_ip": "10.1.2.16",
    "src_port" : "8000",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=ip&protocol=tcp&src_ip=10.1.2.16&src_port=8000

* 允许 目的 tcp 10.1.2.16 8000 的流进入

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "tcp",
    "dst_ip": "10.1.2.16",
    "dst_port" : "8000",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=ip&protocol=tcp&dst_ip=10.1.2.16&dst_port=8000

* 禁止目的 tcp 10.1.2.16 8000 的流进入

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "tcp",
    "dst_ip": "10.1.2.16",
    "dst_port" : "8000",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=ip&protocol=tcp&dst_ip=10.1.2.16&dst_port=8000

* 允许源 udp 10.1.2.16 8000 的流进入

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "udp",
    "src_ip": "10.1.2.16",
    "src_port" : "8000",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=ip&protocol=udp&src_ip=10.1.2.16&src_port=8000

* 禁止源 udp 10.1.2.16 8000 的流进入

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "udp",
    "src_ip": "10.1.2.16",
    "src_port" : "8000",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=ip&protocol=udp&src_ip=10.1.2.16&src_port=8000

* 允许目的 udp 10.1.2.16 8000 的流进入

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "udp",
    "dst_ip": "10.1.2.16",
    "dst_port" : "8000",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=ip&protocol=udp&dst_ip=10.1.2.16&dst_port=8000

* 禁止目的 udp 10.1.2.16 8000 的流进入

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "udp",
    "dst_ip": "10.1.2.16",
    "dst_port" : "8000",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=ip&protocol=udp&dst_ip=10.1.2.16&dst_port=8000

* 允许 tcp 10.1.2.16 9000 -> 10.1.2.17 9000 的流

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "tcp",
    "src_ip": "10.1.2.16",
    "src_port" : "9000",
    "dst_ip": "10.1.2.17",
    "dst_port": "9000",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=ip&protocol=tcp&src_ip=10.1.2.16&src_port=9000&dst_ip=10.1.2.17&dst_port=9000

* 禁止 tcp 10.1.2.16 9000 -> 10.1.2.17 9000 的流

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "tcp",
    "src_ip": "10.1.2.16",
    "src_port" : "9000",
    "dst_ip": "10.1.2.17",
    "dst_port": "9000",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=ip&protocol=tcp&src_ip=10.1.2.16&src_port=9000&dst_ip=10.1.2.17&dst_port=9000

* 允许 tcp 10.1.2.16 9000 -> 10.1.2.17 9000 的流

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "udp",
    "src_ip": "10.1.2.16",
    "src_port" : "9000",
    "dst_ip": "10.1.2.17",
    "dst_port": "9000",
    "actions":"allow"
    }

DELETE /wm/acl/rules/allSwitch/allow/json?eth_type=ip&protocol=tcp&src_ip=10.1.2.16&src_port=9000&dst_ip=10.1.2.17&dst_port=9000

* 禁止 tcp 10.1.2.16 9000 -> 10.1.2.17 9000 的流

/wm/acl/rules/json POST   Content-Type:application/json

    {
    "eth_type": "ip",
    "protocol": "udp",
    "src_ip": "10.1.2.16",
    "src_port" : "9000",
    "dst_ip": "10.1.2.17",
    "dst_port": "9000",
    "actions":"deny"
    }

DELETE /wm/acl/rules/allSwitch/deny/json?eth_type=ip&protocol=udp&src_ip=10.1.2.16&src_port=9000&dst_ip=10.1.2.17&dst_port=9000


附录
--------------------------

POST http://192.168.0.132:8080/wm/staticflowentrypusher/json

    {
        "name": "flow1",
        "switch": "00:00:00:1e:08:09:20:00",
        "active": "1",
        "idle-timeout": "0",
        "hard-timeout": "0",
        "priority": "65532",
        "cookie": "0",
        "ingress-port": "1",
        "src-mac": "00:00:00:00:00:01",
        "dst-mac": "00:00:00:00:00:02",
        "vlan-id": "1",
        "vlan-priority": "0",
        "ether-type": "2048",
        "tos-bits" : "0",
        "protocol" : "6",
        "src-ip": "10.1.1.1/28",
        "dst-ip": "10.1.1.2/28",
        "src-port": "11",
        "dst-port": "12",
        "actions": "output=2"
    }


* "name": "flow1" 必须, 任意字符串
* "switch": "00:00:00:1e:08:09:20:00", 必须,交换机dpid, 如果不存在,只在内存中，待交换机连接到控制器后，下发到交换机
* "active": "true", true|false, 如果为false, 不会下发到交换机
* "idle-timeout": "0", 可选, 统一为 0
* "hard-timeout": "0", 可选, 统一为 0
* "priority": "65532", 可选, 默认为 0
* "cookie": "0", 可选，默认为 0
* "ingress-port": "1",
* "src-mac": "00:00:00:00:00:01",
* "dst-mac": "00:00:00:00:00:02",
* "vlan-id": "1",
* "vlan-priority": "0",
* "ether-type": "2048",
* "tos-bits" : "0",
* "protocol" : "6",
* "src-ip": "10.1.1.1/28",
* "dst-ip": "10.1.1.2/28",
* "src-port": "11",
* "dst-port": "12",
* "actions": "output=2"

不需要所有字段都指定, 指定需要的字段即可．例外:当指定 protocol 或 src-ip,
dst-ip, tos-bits 时, ether-type 必须为 2048

DELETE http://192.168.0.132:8080/wm/staticflowentrypusher/json

    {
        "name": "flow1"
    }

POST http://192.168.0.132:8080/wm/acl/rules/json

    {
        "switch_id": "00:00:12:6a:ae:82:9e:4d",
        "name": "flow1",
        "in_port": 0,
        "src_mac": "00:00:00:00:00:00",
        "dst_mac": "00:00:00:00:00:00",
        "src_ip": "0.0.0.0/0",
        "dst_ip": "0.0.0.0/0",
        "protocol": "TCP",
        "src_port": 0,
        "dst_port": 0,
        "actions": "DENY"
    }

POST http://192.168.0.132:8080/vm/lb/flows/00:00:12:6a:ae:82:9e:4d/json

    {
        "in_port": 5,
        "idle_timeout": "10",
        "hard_timeout": "50",
        "src_mac": "00:00:00:00:00:01",
        "dst_mac": "00:00:00:00:00:02",
        "src_ip": "10.1.2.1/32",
        "dst_ip": "10.1.2.2/32",
        "protocol": "6",
        "src_port": "11",
        "dst_port": "12",
        "actions": "output=13"
    }

PUT http://192.168.0.132:8080/vm/lb/flows/00:00:12:6a:ae:82:9e:4d/json

    {
        "in_port": 5,
        "idle_timeout": "10",
        "hard_timeout": "50",
        "src_mac": "00:00:00:00:00:01",
        "dst_mac": "00:00:00:00:00:02",
        "src_ip": "10.1.2.1/32",
        "dst_ip": "10.1.2.2/32",
        "protocol": "6",
        "src_port": "11",
        "dst_port": "12",
        "actions": "output=13"
    }

DELETE http://192.168.0.132:8080/vm/lb/flows/00:00:12:6a:ae:82:9e:4d/json

    {
        "in_port": 5,
        "idle_timeout": "10",
        "hard_timeout": "50",
        "src_mac": "00:00:00:00:00:01",
        "dst_mac": "00:00:00:00:00:02",
        "src_ip": "10.1.2.1/32",
        "dst_ip": "10.1.2.2/32",
        "protocol": "6",
        "src_port": "11",
        "dst_port": "12",
        "actions": "output=13"
    }


GET http://192.168.0.132:8080/wm/device/

显示所有连接到交换机的主机列表信息.

    [
       {
           "entityClass": "DefaultEntityClass",
           "mac":
           [
               "00:15:c5:7c:28:68"   主机 MAC 地址
           ],
           "ipv4":
           [
               "10.1.2.11"           主机 IP 地址
           ],
           "vlan":
           [                         主机所属 VLAN
           ],
           "attachmentPoint":        主机所属交换机的 id, 端口, 错误状态
           [
               {
                   "switchDPID": "00:00:2c:53:4a:01:8f:b8",   
                   "port": 2,
                   "errorStatus": null
               }
           ],
           "lastSeen": 1438657621164 主机上次通过交换机的时间
       },
       {
           "entityClass": "DefaultEntityClass",
           "mac":
           [
               "e0:3f:49:b9:ca:cd"
           ],
           "ipv4":
           [
               "192.168.0.73",       主机开启路由, 广播包通过连接的该交换机的端口
               "10.1.2.25"
           ],
           "vlan":
           [
           ],
           "attachmentPoint":
           [
           ],
           "lastSeen": 1438654813486
       },
       {
           "entityClass": "DefaultEntityClass",
           "mac":
           [
               "00:1c:23:fc:c8:80"
           ],
           "ipv4":
           [                      该主机还没有 3 层包经过交换机
           ],
           "vlan":
           [
           ],
           "attachmentPoint":
           [
               {
                   "switchDPID": "00:00:2c:53:4a:01:8f:b8",
                   "port": 3,
                   "errorStatus": null
               }
           ],
           "lastSeen": 1438654794655
       }
    ]



GET http://192.168.0.132:8080/wm/monitor/hosts/json

主机健康检查模块信息. 主要用于主机的某个端口是否可用. 目前主要用于负载均衡模块后端服务器健康检查.

    {
       "code": 0,                    返回状态, 0 表示正常
       "body":
       [
           {
               "id": "99041634676",  主机id, 目前为负载均衡模块后端服务器 id
               "name": "S1",         主机名, 目前为负载均衡模块后端服务器名
               "ip": "10.0.1.1",     主机ip, 目前为负载均衡模块后端服务器 ip
               "port": "80",         主机port, 目前为负载均衡模块后端服务器 port
               "protocol": "TCP",    主机协议, 目前为负载均衡模块后端服务器的协议
               "status": "0"         主机状态, 0 表示该主机的 ip:port 不能连接. 1 表示可以连接. 目前为负载均衡模块后端服务器状态
           },
           {
               "id": "95797522161",
               "name": "p2_b3",
               "ip": "10.1.3.13",
               "port": "8000",
               "protocol": "TCP",
               "status": "0"
           }
       ]
    }



GET  http://192.168.1.3:8080/wm/core/controller/summary/json

    {
       "# Switches": 2,            连接到当前控制器的交换机个数
       "# hosts": 3,               连接到当前控制器的主机个数
       "# quarantine ports": 0,    屏蔽的转发端口个数
       "# inter-switch links": 0   交换机之间连接的链路数
    }


GET  http://192.168.0.132:8080/wm/core/controller/switches/json 

    [
       {
           "harole": "MASTER",                       交换机的角色 MASTER, SLAVE
           "description":                            交换机的描述信息,如果软件版本
           {
               "software": "2.3.1",
               "hardware": "Open vSwitch",
               "manufacturer": "Nicira, Inc.",
               "serialNum": "None",
               "datapath": "None"
           },
           "inetAddress": "/192.168.1.2:56462",
           "ports":
           [
               {
                   "portNumber": 65534,
                   "hardwareAddress": "32:39:bc:2e:c3:42",
                   "name": "ovs-s0",
                   "config": 1,
                   "state": 1,
                   "currentFeatures": 0,
                   "advertisedFeatures": 0,
                   "supportedFeatures": 0,
                   "peerFeatures": 0
               },
               {
                   "portNumber": 1,
                   "hardwareAddress": "1a:1a:dc:6d:b4:93",
                   "name": "veth1pl22985",
                   "config": 0,
                   "state": 0,
                   "currentFeatures": 192,
                   "advertisedFeatures": 0,
                   "supportedFeatures": 0,
                   "peerFeatures": 0
               },
               {
                   "portNumber": 5,
                   "hardwareAddress": "a6:0d:e9:24:d1:9a",
                   "name": "veth1pl24008",
                   "config": 0,
                   "state": 0,
                   "currentFeatures": 192,
                   "advertisedFeatures": 0,
                   "supportedFeatures": 0,
                   "peerFeatures": 0
               },
               {
                   "portNumber": 2,
                   "hardwareAddress": "3e:d1:83:c4:c3:d4",
                   "name": "veth1pl23135",
                   "config": 0,
                   "state": 0,
                   "currentFeatures": 192,
                   "advertisedFeatures": 0,
                   "supportedFeatures": 0,
                   "peerFeatures": 0
               },
               {
                   "portNumber": 3,
                   "hardwareAddress": "a6:bc:b1:3a:e8:68",
                   "name": "veth1pl23283",
                   "config": 0,
                   "state": 0,
                   "currentFeatures": 192,
                   "advertisedFeatures": 0,
                   "supportedFeatures": 0,
                   "peerFeatures": 0
               }
           ],
           "buffers": 256,
           "capabilities": 199,
           "connectedSince": 1438590575427,
           "dpid": "00:00:32:39:bc:2e:c3:42",
           "actions": 4095,
           "attributes":
           {
               "supportsOfppFlood": true,
               "supportsNxRole": true,
               "FastWildcards": 4194303,
               "supportsOfppTable": true
           }
       },
       {
           "harole": "MASTER",
           "description":
           {
               "software": "2.3.1",
               "hardware": "Open vSwitch",
               "manufacturer": "Nicira, Inc.",
               "serialNum": "None",
               "datapath": "None"
           },
           "inetAddress": "/192.168.1.2:56461",
           "ports":
           [
               {
                   "portNumber": 1,
                   "hardwareAddress": "2c:53:4a:01:8f:b8",
                   "name": "p4p1",
                   "config": 0,
                   "state": 0,
                   "currentFeatures": 648,
                   "advertisedFeatures": 1711,
                   "supportedFeatures": 1711,
                   "peerFeatures": 0
               },
               {
                   "portNumber": 2,
                   "hardwareAddress": "2c:53:4a:01:8f:b9",
                   "name": "p4p2",
                   "config": 0,
                   "state": 0,
                   "currentFeatures": 648,
                   "advertisedFeatures": 1711,
                   "supportedFeatures": 1711,
                   "peerFeatures": 0
               },
               {
                   "portNumber": 3,
                   "hardwareAddress": "2c:53:4a:01:8f:ba",
                   "name": "p4p3",
                   "config": 0,
                   "state": 0,
                   "currentFeatures": 648,
                   "advertisedFeatures": 1711,
                   "supportedFeatures": 1711,
                   "peerFeatures": 0
               },
               {
                   "portNumber": 65534,
                   "hardwareAddress": "2c:53:4a:01:8f:b8",
                   "name": "test",
                   "config": 1,
                   "state": 1,
                   "currentFeatures": 0,
                   "advertisedFeatures": 0,
                   "supportedFeatures": 0,
                   "peerFeatures": 0
               }
           ],
           "buffers": 256,
           "capabilities": 199,
           "connectedSince": 1438590575430,
           "dpid": "00:00:2c:53:4a:01:8f:b8",
           "actions": 4095,
           "attributes":
           {
               "supportsOfppFlood": true,
               "supportsNxRole": true,
               "FastWildcards": 4194303,
               "supportsOfppTable": true
           }
       }
    ]


集群管理

* /clusters   GET POST
* /clusters/  GET POST
* /clusters/{id}      GET, PUT, DELETE
* /clusters/{id}/     POST, PUT, DELETE
* /clusters/{id}/{a5id}   POST PUT, DELETE
* /clusters/{id}/{a5id}/  POST PUT, DELETE

POST /wm/cluster/clusters/

    {
        "id": "126",
        "name": "cluster1",
        "type": "CLUSTER",
        "adminState":"OFF",
        "state": "ACTIVE"
    }

* type : 包含 CLUSTER HA
* adminState : 包含 OFF, ON
* state: 包含 ACTIVE INACTIVE

GET /wm/cluster/clusters/

GET /wm/cluster/clusters/126

    [
        {
            "id":
            {
                "id": "126"
            },
            "name": "cluster1",
            "version":
            {
                "major": 1,
                "minor": 0,
                "patch": 0
            },
            "state": "ACTIVE",
            "adminState":"OFF",
            "type": "HA",
            "a5Nodes":
            [
            ]
        }
    ]

PUT /wm/cluster/clusters/126

    {
        "id": "126",
        "name": "cluster4",
        "type": "HA",
        "adminState":"ON",
        "state": "INACTIVE"
    }

id 不可修改, PUT 方法的 body 中 id 被忽略

DELETE /wm/cluster/clusters/126

/a5nodes
/a5nodes/
/a5nodes/{id}
/a5nodes/{id}/

POST /wm/cluster/a5nodes/

    {
        "id": "027",
        "state" : "INACTIVE",
        "type": "FOLLOWER",
        "ip": "10.1.1.2"
    }

* type : 包含 LEADER FOLLOWER
* state: 包含 ACTIVE INACTIVE

GET /wm/cluster/a5nodes/

GET /wm/cluster/a5nodes/127

PUT /wm/cluster/a5nodes/127

    {
        "id": "027",
        "name": "a5node2",
        "state" : "ACTIVE",
        "type": "LEADER",
        "ip": "10.1.1.1"
    }

a5nodes 可以属于多个 cluster
一个 cluster 可以最多包含两个 Type 为 CLUSTER A5Node


POST /wm/cluster/clusters/126/027 其中 027 是 127 在 cluster 126 中的节点 id

    {
        "id": "127",
        "adminState" : "OFF"
    }

其中 adminState 可省略(默认为 OFF)

GET /wm/cluster/clusters/126/027 其中 027 是 127 在cluster 126 中的 id

    [
        {
            "id":
            {
                "id": "027"
            },
            "name": "a1",
            "version":
            {
                "major": 1,
                "minor": 0,
                "patch": 0
            },
            "state": "INACTIVE",
            "type": "FOLLOWER",
            "clusterIds":
            {
                "126": "ON"
            },
            "ip":
            {
                "address": 167837954
            }
        }
    ]


PUT /wm/cluster/clusters/126/027 其中 027 是 127 在cluster 126 中的 id

    {
        "id": "127",
        "adminState" : "ON"
    }

