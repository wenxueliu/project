
## 版本

2.3.5 较 2.3.2 的变化

1. 增加 ufid, 提高 revalidator 性能;
2. 加强日志
3. 增加 per_cpu 的 action_fifo
4. 增加 mpls, geneve 的协议支持

参考
[1](https://mail.openvswitch.org/pipermail/ovs-dev/2014-November/292309.html)
[2](https://mail.openvswitch.org/pipermail/ovs-dev/2014-November/292299.html)
[3](https://mail.openvswitch.org/pipermail/ovs-dev/2014-November/292317.html)
[4](https://mail.openvswitch.org/pipermail/ovs-dev/2014-November/292760.html)
[5](https://mail.openvswitch.org/pipermail/ovs-dev/2015-January/294043.html)

优化点

2. 对于大量流表, 且流表变化频繁, 增加 TBL_MIN_BUCKETS 值, 可以减少扩容次数, 潜在的释放旧的流表需要时间更长


## 内核预备知识

* 模块编译
* seqlock : 统计信息
* rcu :
* mutex :
* percpu
* netlink
* flex_array
* 常用宏 offsetof, CONTAINER_OF, FIELD_SIZEOF
* skb, net_device
* 内核内存模型
* hlist

## systemtap 监控点

1. 流表是否均衡均衡分布在各个 bucket 中
2. dp 的 dp_stats_percpu 数据, ovs_dp_stats 保存了所有 cpu 的 dp_stats_percpu; 通过 get_dp_stats 获取. 命令 ovs-dpctl show 可以获取信息, 但不要频繁获取, 因为需要加锁.
3. sw_flow->stats 每条流的统计信息


## datapath 需要解决的问题

* 内核模块的构建过程
* datapath 如何收到包
* key 的生成
* 流表的匹配
* actions 的执行
* 流表不匹配的时候, upcall 的具体实现, 会将包数据完整发送给 vswitchd 么? 会
* 如何与用户空间的 vswitchd 交互, 支持哪些交换操作
* 如何保证 upcall 的包的顺序, 有哪些实现方式? 目前的实现方式是什么?
* 如果端口宕掉, 会发生什么? 对 vswitch 和 controller 有什么影响

## vswitch 需要解决的问题

* 如何接受 datapath 的消息
* 如何与 controller 交互, 发送什么, 接受什么
* 如何向 datapath 发送消息, 包括被动应答, 主动发送
* 如何与 ovsdb 交互
* 当 table_miss 后, vswitch 是如何决断的
* 当 table_miss 后, 是否可以直接将包发送出去还是, 必须通过 datapath 发送, 如果发送, 方式是怎么样的 ?


## 执行流程

1. 内核模块 openvswitch 初始化
2. bridge 的每个端口监听收到的数据, 对每个收到的包查找对应的流表，如果没有匹配的流表, 发送到用户态的 vswitchd.
3. 通过 netlink 接受用户态的命令, 创建网桥, 流表等等


## 各个关键数据结构的内存布局

struct dp_upcall_info
	u8 cmd;
	const struct sw_flow_key *key;
	const struct nlattr *userdata;
	u32 portid;

datapath
    table
        mask_cache : 256
        mask_array
            mask_array   : 1
            sw_flow_mask : 16
        ti: 1
            buckets: 1024 hlist_head
    ports
        head_list : 1024

vport
    vport : ALIGN(sizeof(vport), VPORT_ALIGN)
        upcall_portids: sizeof *vport_portids + nla_len(ids)
    netdev_vport : 1
        dev : sizeof(internal_dev) 该设备注册到内核中. 并通知内核可以传输数据

    net_device
        private: internal_dev

    vport 的私有部分为 netdev_vport
    netdev_vport->dev 为 internal_dev
    interal_dev 又与 net_device 关联
    internal_dev->vport = vport
    通过 net_device 可以定位到 internal_dev, vport 可以定位到 internal_dev
    internal_dev 可以定位到 vport.

internal vport 对应 ovs 为 internal 类型的 port
netdev vport 对应 ovs 为非 internal 类型的 port

/* List of statically compiled vport implementations.  Don't forget to also
 * add yours to the list at the bottom of vport.h. */
static const struct vport_ops *vport_ops_list[] = {
	&ovs_netdev_vport_ops,
	&ovs_internal_vport_ops,
#if IS_ENABLED(CONFIG_NET_IPGRE_DEMUX)
	&ovs_gre_vport_ops,
	&ovs_gre64_vport_ops,
#endif
	&ovs_vxlan_vport_ops,
	&ovs_lisp_vport_ops,
};

sw_flow_key
    tun_opts
    tun_opts_len
    ovs_key_ipv4_tunnel tun_key
    phy
    ovs_flow_hash
    recirc_id
    eth
    mpls 或 ip
    tp : tcp, sctp, udp
    ipv4 | ipv6

sw_flow_match
    sw_flow_key
    sw_flow_key_range
    sw_flow_mask

sw_flow
    rcu_head
    flow_table
    ufid_table
    stats_last_writer
    sw_flow_key
    sw_flow_id
    sw_flow_mask
    sw_flow_actions
    flow_stats

flow_table

    mask_cache : 每个 cpu MC_HASH_ENTRIES(256) 条 mask_cache_entry
    mask_array : sizeof(struct mask_array) + sizeof(struct sw_flow_mask *) * max(MASK_ARRAY_SIZE_MIN, size);
    table_instance : kmalloc(sizeof(*ti), GFP_KERNEL)
        buckets : flex_array_alloc(sizeof(struct hlist_head), TBL_MIN_BUCKETS, GFP_KERNEL);

其中:

    MASK_ARRAY_SIZE_MIN = 16
    MC_HASH_ENTRIES = 256
    TBL_MIN_BUCKETS = 1024

flow : 在全局 flow_cache 中
    stats[0] : sizeof(flow_stats_cache)
    sw_flow_actions *sfa
    a[OVS_FLOW_ATTR_ACTIONS] : 最大 32*1024

skb

    OVS_CB(skb)->tun_key
    OVS_CB(skb)->input_vport

## Bridge 的设计思路

每个 bridge 有一张 table, 每张 table 有 1024 个 bucket 哈希桶
每个 bridge 有一组 ports (1024 个哈希桶) 存储 vport. 以 vport 的端口号为索引, 每个 vport 都会注册到内核, 开启混杂模式,
每个 bridge 都会加入其所属的命名空间的 ovs_net, 因此可以通过 ovs_net 中查找对应的 bridage
每个 vport 都加入 dev_table 和 dp->ports 的索引中, 因此, 可以通过 dev_table 或 bridge 以 O(1) 查询端口
每个 vport 的命名空间与其所属的 bridge 在同一命名空间

每个 bridge 的多个 eth 可以属于不同的 namespace

## 流表的设计思路:

问题

1. 流表从哪里分配, 初始大小是多少? flow_cache 中分配, 初始化大小 1024 个 buckets
2. 是否支持自动扩容与缩容, 扩容时机? 缩容时机?

    自动扩容的时机是: 如果没有用 ufid 当插入一条新的流表时, 如果 flow_table->ti->n_buckets 小于流表数 flow_table->count, 扩容为原来的二倍
                      如果用 ufid, 当插入一条新的流表时, 如果 flow_table->ufid_ti->n_buckets 小于流表数 flow_table->ufid_count, 扩容为原来的二倍
    扩容会将旧的流表插入到新的流表, 因此, 流表在某个时间点总数是扩容前的 3 倍

    此外, 流表还会定期重新 hash, 间隔为 REHASH_INTERVAL(除非重新编译, 否则不可改变)

3. flow_table 与 sw_flow 如何关联在一起?

如果使用 ufid : flow->ufid_table.node[ti->node_ver] 加入 flow_table->ufid_ti->buckets[jhash_1word(flow_table->ufid_ti->hash_seed, flow->ufid_table.hash)]
如果没有使用 ufid : flow->flow_table.node[ti->node_ver] 加入 flow_table->ti->buckets[jhash_1word(jhash(flow->key, flow->mask->range->end -
               flow->mask->range->start, 0), flow_table->ti->hash_seed) & (flow_table->ti->n_buckets - 1)] 的链表中

4. 流表查询是如何实现的?

    对流表的增删改查的情况:
    流表查询支持根据 key, match, ufid 三种查询方式分别对应
    ovs_flow_tbl_lookup_ufid, ovs_flow_tbl_lookup 和 ovs_flow_tbl_lookup_exact 的实现细节

    如果支持 ufid, 直接根据 ufid 查询, 如果不支持 ufid,

        1. 计算 hash
        2. 找到 bucket
        3. 遍历 bucket, 比较 ufid

    算法复杂度大大简化

    如果不支持 ufid

        1. 遍历所有的 mask_array 所有元素 mask
        2. mask 与 match->key 掩码之后 masked_key
        3. 计算 hash
        4. 找到 bucket, 遍历对应的 bucket
        5. 比较 masked_key 与 key 及 hash, mask

    算法复杂度与 mask_array 大小相关;

    ovs_flow_tbl_lookup_exact
        masked_flow_lookup

    如果根据 key 查询, 与非 ufid 一样;

    ovs_flow_tbl_lookup
        flow_lookup
            masked_flow_lookup

    对包进入 ovs 的情况:

    ovs_flow_tbl_lookup_stats
        flow_lookup : 对 masked_flow_lookup 的一个简单优化, 即优先从 mask_array 的某个索引查
            masked_flow_lookup


    1) mask 的查询就是遍历数组所有元素
    2) mask 的删除也会遍历所有 mask


5. 流表插入是如何实现的, 复杂度如何? 与 hash map 类似, 根据 hash 找到 bucket, 加入 bucket 的头部(O(1)), 一旦发生扩容就变为 O(n)

6. 流是如何进行比较的?

    ovs_flow_cmp
        if flow->id->ufid_len : flow_cmp_masked_key
        else : ovs_flow_cmp_unmasked_key

0. 新建的流表项 sw_flow 从 flow_cache(kmem_cache 中 sw_flow) 中分配. 而 sw_flow->stats 是从 flow_stats_cache 中分配
1. flow_table->ti->buckets 和 flow_table->ufid_ti 初始分别分配 TBL_MIN_BUCKETS(1024) 个 bucket, 每个 bucket 是一个 rcu 链表. 该链表中保持 sw_flow
2. flow_table->mask_array 也支持自动扩容和缩容, 初始 16 个, 每次扩容, 增加 16 项, 缩容时机是总数大于 32 且已用数量小于总量的 1/3
6. mask_array 中元素每次增加 MASK_ARRAY_SIZE_MIN(16), 新增加的元素, 遍历 mask_array->marks, 找到第一个没有使用的空间
8. mask_cache 加速进入 ovs 的包的对应流表的查询

### 流表状态更新是如何实现的 ?

    首先流表状态 sw_flow->stats 在每个 numa 节点都存一份,
    更新操作运行在哪个节点, 就在该节点直接更新; 如果
    不存在该节点的, 就为该节点的创建一份.

    在获取状态时, 将 numa 各个节点的数据汇总

    在清除状态时, 将 numa 各个节点的数据依次清除

    在状态获取,清除都会加锁, 因此, 避免频繁操作

    事实上, 锁的范围是 flow 级别的, 即获取流表状态的时候, 修改流表就需要等待,
    锁的粒度还是很大的. 使用的锁是 ovs_lock();




## 各个关键数据结构关系

### net 与 ovs_net

	struct ovs_net *ovs_net = net_generic(dnet, ovs_net_id);

### net 与 net_device

通过 ifindex 关联, 通过 net, ifindex 定位 net_device

net->dev_index_head[ifindex & (NETDEV_HASHENTRIES - 1)] 下保存了 net_device
列表, 找到 dev->ifindex == ifindex 对应的 net_device

### net_device 与 vport

通过 net_device 的私有数据关联

netdev_priv(netdev)->vport = vport

net_device 的私有数据可以参考内核接口 alloc_netdev_mqs()

注: net_device 之于 datapath 的 OVSP_LOCAL vport 关联

### vport 与 datapath

直接关联, 通过 vport 定位 dp

vport->dp = datapath

通常在创建 vport 的时候直接指定 dp, 因为 vport 必须属于一个 datapath

### net 与 datapath

   net -> net_device -> vport -> datapath

### vport 与 netdev_vport

通过私有数据关联, 通过 vport 定位 netdev_vport

	(u8 *)(uintptr_t)vport + ALIGN(sizeof(struct vport), VPORT_ALIGN);

### vport 与 net_device

通过 vport 的私有数据关联, vport 通过 netdev_vport 间接定位 net_device

	vport_priv(vport) = (u8 *)(uintptr_t)vport + ALIGN(sizeof(struct vport), VPORT_ALIGN);
    net_device = vport_priv(vport)->dev

注: net_device 之于 datapath 的 OVSP_LOCAL vport 关联

### datapath 与 vprot

直接关联, 通过 dp 定位 vport

datapath->ports[port_no % DP_VPORT_HASH_BUCKETS] = vport (vport 在 datapath 中的 port_no 的端口号)

通常在创建 vport 的时候将 vport->dp_hash_node 加入 datapath->ports[vport->port_no % DP_VPORT_HASH_BUCKETS] 中

### dev_table 与 vport

链表 dev_table[jhash(name,strlen(name), net) & (VPORT_HASH_BUCKETS - 1)] 保持 vport

其中:

    net = vport->dp->net
    name = vport->ops->get_name(vport)

NOTE:通常在创建 vport 的时候将 vport 加入 dev_table

因此, 既可以通过 net, name 就可以找到 vport, datapath, 也可以通过 dev_table 可以找到 vport, datapath

### skb 与 vport

    OVS_CB(skb)->input_vport
    OVS_CB(skb)->pkt_key
    OVS_CB(skb)->flow

    struct ovs_skb_cb {
    	struct sw_flow		*flow;
    	struct sw_flow_key	*pkt_key;
    	struct ovs_key_ipv4_tunnel  *tun_key;
    	struct vport	*input_vport;
    };
    #define OVS_CB(skb) ((struct ovs_skb_cb *)(skb)->cb)

### dp 的 name 就是 OVSP_LOCAL 对应 vport 的 name

### dp 的 ifindex 就是 dp 中 OVSP_LOCAL(vport)对应的 net_device 的 ifindex

### 总结

* net->dev_index_head 通过 ifindex 找到 net_device
* netdev_priv(net_device) 找到 vport
* vport 找到 datapath
* vport_priv(vport) 找到 net_device
* datapath->ports 找到 vport
* skb 找到 vport

注: 其中 hash 表是整个内核数据结构最为关键的


## 预备知识

基本的 makefile 语法见[跟我一起写 Makefile](http://blog.csdn.net/haoel/article/details/2886/)

##编译

为了区别 Kbuild Makefile 和 Normal Makefile

```
    ifeq ($(KERNELRELEASE),)
    # We're being called directly by running make in this directory.
    include Makefile.main
    else
    # We're being included by the Linux kernel build system
    include Kbuild
    endif
```

首先执行 Makefile.main.in 然后执行 Kbuild.in

###Makefile.main.in

####@var@

    export builddir = @abs_builddir@
    export srcdir = @abs_srcdir@
    export top_srcdir = @abs_top_srcdir@
    export KSRC = @KBUILD@
    export VERSION = @VERSION@

@var@ 首先包含这种变量的文件一般以in 为后缀. 在运行 ./configure 的时候, 文件的
in 后缀被去掉, 该变量被替换为 ./configure 配置指定的变量

###foreach

    $(foreach var,list,text)


这个函数的意思是, 把参数 list 中的单词逐一取出放到参数 var 所指定的变量中, 然后再执行 text 所包含的表达式.
每一次 text 会返回一个字符串, 循环过程中 text 的所返回的每个字符串会以空格分隔, 最后当整个循环结束时,
text 所返回的每个字符串所组成的整个字符串(以空格分隔)将会是 foreach 函数的返回值。

###eval

```
    define module_template
    $(1)-y = $$(notdir $$(patsubst %.c,%.o,$($(1)_sources)))
    endef

    $(foreach module,$(build_multi_modules),$(eval $(call module_template,$(module))))
```
如果 module = openvswitch, 结果

openvswitch-y= *.c //*.c 为 openvswitch_sources 下的所有 *.c 文件

###Kbuild.in

ccflags-y：$(CC)的编译选项添加这里，宏开关也在这里添加


编译 TIPS:

    CONFIG_NET_NS : 网桥支持命名空间

## 核心实现

## 内核模块初始化

1. 初始化 flow_cache, flow_stats_cache, dev_table

为 flow_cache, flow_stats_cache 分配内核内存空间, 由于都是小对象,
并且会频繁创建和释放, 因此通过 slab 分配.  分配和使用情况可以通过 /proc/slabinfo 查看

为 dev_table 分配 VPORT_HASH_BUCKETS 个 struct hlist_head 大小的对象.


2. 注册网络命名空间

每个　register_pernet_device 注册的函数, 在每个命名空间创建的时候, 都会调用对应的 init 函数,
命名空间删除的时候调用 exit 函数

3. 注册设备通知事件

当 vport 注销的时候做一些清理工作

4. 注册 netlink, 用于与用户态的 vswitchd 通信

```
static struct genl_family *dp_genl_families[] = {
	&dp_datapath_genl_family,
	&dp_vport_genl_family,
	&dp_flow_genl_family,
	&dp_packet_genl_family,
};
```

由上可见与 vswitchd 通信主要包括四类信息, datapath 配置(即 bridge 的 CRUD),
vport(bridge 中 port 的 CRUD), flow(流表的 CRUD), packet(对给定的 packete
执行号一个动作 actions, 参照 openflow 协议的 actions)

通过以上初始化, 内核已经准备好， 之后通过态通过 netlink 创建一个 bridge, 再
创建一个端口, 创建的端口监听该端口的数据包，之后查询匹配流表，如果找到匹配的，
直接执行对应的 actions 对包进行处理, 如果没有对应的流表匹配, 根据配置是发送
到用户态还是丢弃.

## 内核初始化

static struct pernet_operations ovs_net_ops = {
	.init = ovs_init_net,
	.exit = ovs_exit_net,
	.id   = &ovs_net_id,
	.size = sizeof(struct ovs_net),
};

### 初始化

dp_init(void)

	ovs_flow_init();
	ovs_vport_init();
	register_pernet_device(&ovs_net_ops);
	register_netdevice_notifier(&ovs_dp_device_notifier);
	ovs_netdev_init();
	dp_register_genl();

### 退出

dp_cleanup(void)

    dp_unregister_genl(ARRAY_SIZE(dp_genl_families));
	ovs_netdev_exit();
	unregister_netdevice_notifier(&ovs_dp_device_notifier);
	unregister_pernet_device(&ovs_net_ops);
	rcu_barrier();
	ovs_vport_exit();
	ovs_flow_exit();
	ovs_internal_dev_rtnl_link_unregister();
	action_fifos_exit();


module_init(dp_init);
module_exit(dp_cleanup);

MODULE_DESCRIPTION("Open vSwitch switching datapath");
MODULE_LICENSE("GPL");
MODULE_VERSION(VERSION);


## 网络初始化

ovs_init_net(struct net *net)

	struct ovs_net *ovs_net = net_generic(net, ovs_net_id);
	INIT_LIST_HEAD(&ovs_net->dps);
	INIT_WORK(&ovs_net->dp_notify_work, ovs_dp_notify_wq);

    其中 ovs_dp_notify_wq 所做的工作是遍历当前网络命名空间
    所有的 datapath, 将类型为 OVS_VPORT_TYPE_NETDEV 的端口
    的删除操作, 多播给用户态

ovs_exit_net(struct net *dnet)

	struct ovs_net *ovs_net = net_generic(dnet, ovs_net_id);
	list_for_each_entry_safe(dp, dp_next, &ovs_net->dps, list_node)
		__dp_destroy(dp);
	for_each_net(net)
		list_vports_from_net(net, dnet, &head);


1. 遍历所有的 net, 将每个 net 所有 datapath 删除
2. 每个 net 的 所有为 dp 中 vport 类型为 OVS_VPORT_TYPE_INTERNAL 加入 vport->detach_list 中
3. 删除 detach_list 中端口

## 创建一个网桥

### 流程

ovs_dp_cmd_new(struct sk_buff *skb, struct genl_info *info)

	struct datapath *dp;
	reply = ovs_dp_cmd_alloc_info(info);
	    genlmsg_new_unicast(ovs_dp_cmd_msg_size(), info, GFP_KERNEL);
    dp = kzalloc(sizeof(dp), GFP_KERNEL)
	ovs_dp_set_net(dp, hold_net(sock_net(skb->sk)));

    ovs_flow_tbl_init(dp->table)
	dp->stats_percpu = alloc_percpu(struct dp_stats_percpu);
	dp->ports = kmalloc(DP_VPORT_HASH_BUCKETS * sizeof(struct hlist_head), GFP_KERNEL);
	parms.name = nla_data(a[OVS_DP_ATTR_NAME]);
	parms.type = OVS_VPORT_TYPE_INTERNAL;
	parms.options = NULL;
	parms.dp = dp;
	parms.port_no = OVSP_LOCAL;
	parms.upcall_portids = a[OVS_DP_ATTR_UPCALL_PID];
    vport = new_vport(parms)
        ovs_vport_add : 增加给定类型的 vport
            ovs_internal_vport_ops : 类型 OVS_VPORT_TYPE_INTERNAL
                internal_dev_create
                    ovs_vport_alloc
                    alloc_netdev
                    register_netdevice
                    dev_set_promiscuity
                    netif_start_queue
            hash_bucket :
	ovs_dp_cmd_fill_info(dp, reply, info->snd_portid, info->snd_seq, 0, OVS_DP_CMD_NEW);
	ovs_net = net_generic(ovs_dp_get_net(dp), ovs_net_id);
	list_add_tail_rcu(&dp->list_node, &ovs_net->dps);
	ovs_notify(&dp_datapath_genl_family, &ovs_dp_datapath_multicast_group, reply, info);

1. kzalloc 分配一个 struct datapath* 内存空间;
2. 设置 bridge 命名空间
3. 分配 datapath->table 空间, 其中 mask_cache : 256
4. 分配 datapath->vport 空间, 为 DP_VPORT_HASH_BUCKETS(1024) 个链表头
5. 根据传递参数设置 dp->user_features
6. 根据传递参数创建 OVS_VPORT_TYPE_INTERNAL 类型的 vport
7. 生成应答信息
8. 将 dp->list_node 加入 bridage 所属网络命名空间的私有数据 dps 中
7. 发送应答给请求者并通知多播组


## 删除一个网桥

### 流程

ovs_dp_cmd_del(struct sk_buff *skb, struct genl_info *info)

	reply = ovs_dp_cmd_alloc_info(info);
    dp = lookup_datapath(sock_net(skb->sk), info->userhdr, info->attrs)
    ovs_dp_cmd_fill_info(dp, reply, info->snd_portid, info->snd_seq, 0, OVS_DP_CMD_DEL)
    __dp_destroy(dp)
	    for (i = 0; i < DP_VPORT_HASH_BUCKETS; i++)
		    hlist_for_each_entry_safe(vport, n, &dp->ports[i], dp_hash_node)
		    	if (vport->port_no != OVSP_LOCAL)
		    		ovs_dp_detach_port(vport);
    	list_del_rcu(&dp->list_node);
    	ovs_dp_detach_port(ovs_vport_ovsl(dp, OVSP_LOCAL));
    	    hlist_del_rcu(&p->dp_hash_node);
    	    ovs_vport_del(p);
	            hlist_del_rcu(&vport->hash_node);
	            vport->ops->destroy(vport);
    ovs_notify(&dp_datapath_genl_family, &ovs_dp_datapath_multicast_group, reply, info)


1. 从 dev_table 查找 bridge 对应的 vport, 由 vport 找到 bridge
2. 生成应答信息
3. 删除网桥, 先删除非 OVSP_LOCAL 的所有 port, 再删除 OVSP_LOCAL port
4. 释放内存
5. 发送应答信息, 并通知给多播组


## 配置一个网桥

### 流程

ovs_dp_cmd_set(struct sk_buff *skb, struct genl_info *info)

	reply = ovs_dp_cmd_alloc_info(info);
    lookup_datapath(sock_net(skb->sk), info->userhdr, info->attrs);
    ovs_dp_change(dp, info->attrs);
    	dp->user_features = nla_get_u32(a[OVS_DP_ATTR_USER_FEATURES]);
    ovs_dp_cmd_fill_info(dp, reply, info->snd_portid, info->snd_seq, 0, OVS_DP_CMD_NEW);
    ovs_notify(&dp_datapath_genl_family, &ovs_dp_datapath_multicast_group, reply, info);

1. 查找网桥
2. 修改属性
3. 生成应答信息
4. 发送应答信息, 并通知给多播组

修改网桥只是修改 user_features 字段

## 获取一个网桥

### 流程

ovs_dp_cmd_get(struct sk_buff *skb, struct genl_info *info)

	reply = ovs_dp_cmd_alloc_info(info);
	dp = lookup_datapath(sock_net(skb->sk), info->userhdr, info->attrs);
	err = ovs_dp_cmd_fill_info(dp, reply, info->snd_portid, info->snd_seq, 0, OVS_DP_CMD_NEW);
	return genlmsg_reply(reply, info);

1. 从 net 查找 info->attrs[OVS_DP_ATTR_NAME] 对应的 dp
4. 发送应答信息

## 输出一个网桥

ovs_dp_cmd_dump(struct sk_buff *skb, struct netlink_callback *cb)

	struct ovs_net *ovs_net = net_generic(sock_net(skb->sk), ovs_net_id);
	int skip = cb->args[0];
	list_for_each_entry(dp, &ovs_net->dps, list_node)
		if (i >= skip &&
		    ovs_dp_cmd_fill_info(dp, skb, NETLINK_CB(cb->skb).portid,
					 cb->nlh->nlmsg_seq, NLM_F_MULTI,
					 OVS_DP_CMD_NEW) < 0)
			break;
		i++;


##给网桥增加一个端口

###流程

ovs_vport_cmd_new(struct sk_buff *skb, struct genl_info *info)

	port_no = a[OVS_VPORT_ATTR_PORT_NO] ? nla_get_u32(a[OVS_VPORT_ATTR_PORT_NO]) : 0;
	reply = ovs_vport_cmd_alloc_info();
    dp = get_dp(sock_net(skb->sk), ovs_header->dp_ifindex)
	if (port_no):
        ovs_vport_ovsl(dp, port_no) //确保 dp 中 port_no 对应的 vport 不存在
	else:
		for (port_no = 1; ; port_no++) {
			if (port_no >= DP_MAX_PORTS) {
				err = -EFBIG;
				goto exit_unlock_free;
			}
            //在 dp->ports[port_no % DP_VPORT_HASH_BUCKETS] 中找到端口号为 port_no 的 vport, 找不到返回 NULL
			vport = ovs_vport_ovsl(dp, port_no);
			if (!vport)
				break;
		}

	parms.name = nla_data(a[OVS_VPORT_ATTR_NAME]);
	parms.type = nla_get_u32(a[OVS_VPORT_ATTR_TYPE]);
	parms.options = a[OVS_VPORT_ATTR_OPTIONS];
	parms.dp = dp;
	parms.port_no = port_no;
	parms.upcall_portids = a[OVS_VPORT_ATTR_UPCALL_PID];
    new_vport(&parms)
        ovs_vport_add(parms) : 增加给定类型的 vport
            ovs_vport_lookup(parms)
                对于 ovs_internal_vport_ops : 类型 OVS_VPORT_TYPE_INTERNAL
                internal_dev_create
                    vport = ovs_vport_alloc(sizeof(struct netdev_vport), &ovs_internal_vport_ops, parms);
                    alloc_netdev
                    register_netdevice
                    dev_set_promiscuity
                    netif_start_queue
                对于 ovs_netdev_vport_ops
                netdev_create
                    vport = ovs_vport_alloc(sizeof(struct netdev_vport), &ovs_netdev_vport_ops, parms);
                    dev_get_by_name(ovs_dp_get_net(vport->dp), parms->name);
                    netdev_master_upper_dev_link(netdev_vport->dev, get_dpdev(vport->dp));
                    netdev_rx_handler_register(netdev_vport->dev, netdev_frame_hook, vport);
                    dev_set_promiscuity(netdev_vport->dev, 1);
                    netdev_vport->dev->priv_flags |= IFF_OVS_DATAPATH;
                bucket = hash_bucket(ovs_dp_get_net(vport->dp), vport->ops->get_name(vport));
                hlist_add_head_rcu(&vport->hash_node, bucket);
            request_module("vport-type-%d", parms->type);
            ovs_vport_lookup : 确认已经添加
		struct hlist_head *head = vport_hash_bucket(dp, vport->port_no);
		hlist_add_head_rcu(&vport->dp_hash_node, head);
	if (a[OVS_VPORT_ATTR_STATS])
		ovs_vport_set_stats(vport, nla_data(a[OVS_VPORT_ATTR_STATS]));
    ovs_vport_cmd_fill_info(vport, reply, info->snd_portid, info->snd_seq, 0, OVS_VPORT_CMD_NEW)
    ovs_notify(&dp_vport_genl_family, &ovs_dp_vport_multicast_group, reply, info)

1. 获取端口要增加的网桥
2. 如果指定端口号, 如果端口已经存在，返回错误; 如果没有指定端口号, 从 1 开始找到没有使用的端口号(0 预留给 OVSP_LOCAL)
3. 根据端口类型创建指定端口类型的端口, 并将 port 加入 dp->ports 和 dev_table 两个哈希表中，方便后续查找
4. 生成应答信息
5. 发送应答信息, 并通知给多播组

创建端口必须指定 name, type, upcall_id, 可选指定 port_no

###增加 internal 端口

internal_dev_create

    vport = ovs_vport_alloc(sizeof(struct netdev_vport), &ovs_internal_vport_ops, parms);
    alloc_netdev
    register_netdevice
    dev_set_promiscuity
    netif_start_queue

1. 分配一个 vport 对象, 并初始化部分数据成员, 其中私有数据为 struct netdev_vport
2. 为 vport 关联的内核设备分配一个 net_device 对象, 其中的私有数据为 struct internal_dev
3. 将端口注册到内核
4. 设置混杂模式
5. 允许上层设备调用 netdev_vport 的 hard_start_xmit routine(dev->tx[0]->state 的 __QUEUE_STATE_DRV_XOFF 清零)

###增加 netdev 端口

netdev_create

    vport = ovs_vport_alloc(sizeof(struct netdev_vport), &ovs_netdev_vport_ops, parms);
    dev_get_by_name(ovs_dp_get_net(vport->dp), parms->name);
    netdev_master_upper_dev_link(netdev_vport->dev, get_dpdev(vport->dp));
    netdev_rx_handler_register(netdev_vport->dev, netdev_frame_hook, vport);
    dev_set_promiscuity(netdev_vport->dev, 1);
    netdev_vport->dev->priv_flags |= IFF_OVS_DATAPATH;

1. 分配 vport 内存
2. 校验网卡(只支持非 loopback, 并且网卡类型为 ARPHRD_ETHER)
3. 设置端口的 upper Linke 为 internal 端口
4. 注册该端口的 rx_handler 为 netdev_frame_hook
5. 设置端口私有标志 IFF_OVS_DATAPATH.(加入 bridage 的 port 所特有, 但当收到的包所属的设备包加入 bridge 时, 包才会接受)

由内核代码可知, 当收到包时, 内核调用 __netif_receive_skb_core, 而
__netif_receive_skb_core 会调用 rx_hander(vport) 即 netdev_frame_hook.

```
/**
 *      netdev_rx_handler_register - register receive handler
 *      @dev: device to register a handler for
 *      @rx_handler: receive handler to register
 *      @rx_handler_data: data pointer that is used by rx handler
 *
 *      Register a receive hander for a device. This handler will then be
 *      called from __netif_receive_skb. A negative errno code is returned
 *      on a failure.
 *
 *      The caller must hold the rtnl_mutex.
 *
 *      For a general description of rx_handler, see enum rx_handler_result.
 */
int netdev_rx_handler_register(struct net_device *dev,
                               rx_handler_func_t *rx_handler,
                               void *rx_handler_data)
{
        ASSERT_RTNL();

        if (dev->rx_handler)
                return -EBUSY;

        /* Note: rx_handler_data must be set before rx_handler */
        rcu_assign_pointer(dev->rx_handler_data, rx_handler_data);
        rcu_assign_pointer(dev->rx_handler, rx_handler);

        return 0;
}
EXPORT_SYMBOL_GPL(netdev_rx_handler_register);



位于 /net/core/dev.c

    rx_handler = rcu_dereference(skb->dev->rx_handler);
    if (rx_handler) {
            if (pt_prev) {
                    ret = deliver_skb(skb, pt_prev, orig_dev);
                    pt_prev = NULL;
            }
            switch (rx_handler(&skb)) {
            case RX_HANDLER_CONSUMED:
                    ret = NET_RX_SUCCESS;
                    goto unlock;
            case RX_HANDLER_ANOTHER:
                    goto another_round;
            case RX_HANDLER_EXACT:
                    deliver_exact = true;
            case RX_HANDLER_PASS:
                    break;
            default:
                    BUG();
            }
    }
```

## 修改端口属性

### 流程

ovs_vport_cmd_set(struct sk_buff *skb, struct genl_info *info)

	reply = ovs_vport_cmd_alloc_info();
    vport = lookup_vport(sock_net(skb->sk), info->userhdr, a);
	if (a[OVS_VPORT_ATTR_OPTIONS])
        ovs_vport_set_options(vport, a[OVS_VPORT_ATTR_OPTIONS]);
	        vport->ops->set_options(vport, options);
	if (a[OVS_VPORT_ATTR_STATS])
	    ovs_vport_set_stats(vport, nla_data(a[OVS_VPORT_ATTR_STATS]));
	        vport->offset_stats = *stats;
	if (a[OVS_VPORT_ATTR_UPCALL_PID])
	    ovs_vport_set_upcall_portids(vport, a[OVS_VPORT_ATTR_UPCALL_PID]);
	ovs_vport_cmd_fill_info(vport, reply, info->snd_portid, info->snd_seq, 0, OVS_VPORT_CMD_NEW);
	ovs_notify(&dp_vport_genl_family, &ovs_dp_vport_multicast_group, reply, info);

1. 根据端口名或端口号在 ovs_net 中查找对应的 port
2. 设置端口选项
3. 设置端口状态
4. 设置端口 upcall_pid
5. 生成应答信息
6. 发送应答信息, 并通知给多播组

## 从网桥删除一个端口

### 流程

ovs_vport_cmd_del(struct sk_buff *skb, struct genl_info *info)

	reply = ovs_vport_cmd_alloc_info();
	vport = lookup_vport(sock_net(skb->sk), info->userhdr, a)
	ovs_vport_cmd_fill_info(vport, reply, info->snd_portid, info->snd_seq, 0, OVS_VPORT_CMD_DEL)
	ovs_dp_detach_port(vport)
	    hlist_del_rcu(&p->dp_hash_node);
	    ovs_vport_del(p)
	        hlist_del_rcu(&vport->hash_node);
	        module_put(vport->ops->owner);
	        vport->ops->destroy(vport);
	ovs_notify(&dp_vport_genl_family, &ovs_dp_vport_multicast_group, reply, info);

1. 根据端口名或端口号在 ovs_net 中查找对应的 port
2. 生成应答信息
3. 从网桥删除端口, 从 dp->ports 中删除当前端口, 从 dev_table 中删除当前端口, 调用端口的 destory 函数
4. 发送应答信息, 并通知给多播组

OVSP_LOCAL 端口不可删除, 与网桥同生同灭


## 获取一个端口

### 流程

ovs_vport_cmd_get(struct sk_buff *skb, struct genl_info *info)

	reply = ovs_vport_cmd_alloc_info();
	vport = lookup_vport(sock_net(skb->sk), ovs_header, a);
	ovs_vport_cmd_fill_info(vport, reply, info->snd_portid, info->snd_seq, 0, OVS_VPORT_CMD_NEW);
	genlmsg_reply(reply, info);

## 输出端口

ovs_vport_cmd_dump(struct sk_buff *skb, struct netlink_callback *cb)

	dp = get_dp(sock_net(skb->sk), ovs_header->dp_ifindex);
	for (i = bucket; i < DP_VPORT_HASH_BUCKETS; i++)
		hlist_for_each_entry_rcu(vport, &dp->ports[i], dp_hash_node)
			if (j >= skip &&
			    ovs_vport_cmd_fill_info(vport, skb,
						    NETLINK_CB(cb->skb).portid,
						    cb->nlh->nlmsg_seq,
						    NLM_F_MULTI,
						    OVS_VPORT_CMD_NEW) < 0)
				goto out;

			j++;


## 收到包后的处理逻辑:

netdev_rx_handler_register

netif_receive_skb
__netif_receive_skb
__netif_receive_skb_core
skb->dev->rx_handler
    netdev_frame_hook
        ovs_netdev_get_vport
        netdev_port_receive(vport, skb)
            ovs_vport_receive(vport, skb, NULL)
                ovs_dp_process_received_packet(vport, skb)
                    ovs_flow_key_extract(skb, &key)
                        key_extract(skb, key)
                    ovs_dp_process_packet_with_key(skb, &key, false) : 3.5 变为 ovs_dp_process_packet
                        flow = ovs_flow_tbl_lookup_stats(&dp->table, pkt_key, skb_get_hash(skb), &n_mask_hit)
                            skb_get_hash(skb) == true:
                                flow_lookup(tbl, ti, ma, key, n_mask_hit, &mask_index);
                                    flow = masked_flow_lookup(ti, key, mask, n_mask_hit);
                                        ovs_flow_mask_key(&masked_key, unmasked, mask);
                                        hash = flow_hash(&masked_key, key_start, key_end);
                                        head = find_bucket(ti, hash);
                                        flow_cmp_masked_key(flow, &masked_key, key_start, key_end))
                        flow == null:
                            ovs_dp_upcall(dp, skb, &upcall)
                                skb_is_gso(skb) == false:
                                    queue_userspace_packet(dp, skb, upcall_info)
                                        user_skb = genlmsg_new_unicast(len, &info, GFP_ATOMIC)
                                        upcall = genlmsg_put(user_skb, 0, 0, &dp_packet_genl_family, 0, upcall_info->cmd)
                                        upcall->dp_ifindex = get_dpifindex(dp)
                                        genlmsg_unicast(ovs_dp_get_net(dp), user_skb, upcall_info->portid)
                                skb_is_gso(skb) == true:
                                    queue_gso_packets(dp, skb, upcall_info)
                                        segs = __skb_gso_segment(skb, NETIF_F_SG, false);
                                        for skb in segs:
                                            queue_userspace_packet(dp, skb, upcall_info)
                                                user_skb = genlmsg_new_unicast(len, &info, GFP_ATOMIC)
                                                upcall = genlmsg_put(user_skb, 0, 0, &dp_packet_genl_family, 0, upcall_info->cmd)
                                                genlmsg_unicast(ovs_dp_get_net(dp), user_skb, upcall_info->portid)
                        if flow != null:
                            ovs_flow_stats_update(OVS_CB(skb)->flow, pkt_key->tp.flags, skb);
                            ovs_execute_actions(dp, skb, recirc)
                                do_execute_actions(dp, skb, acts->actions, acts->actions_len)
                                    do_output(dp, skb_clone(skb, GFP_ATOMIC), prev_port)
                                        //在 dp->ports[port_no % DP_VPORT_HASH_BUCKET ] 中找到端口号为 port_no 的 vport, 找不到返回 NULL
                                        vport = ovs_vport_rcu(dp, out_port)
                                        ovs_vport_send(vport, skb)
                                            int sent = vport->ops->send(vport, skb)
                                    output_userspace(dp, skb, a)
                                        ovs_dp_upcall(dp, skb, &upcall)
                                            queue_userspace_packet(dp, skb, upcall_info)
                                                user_skb = genlmsg_new_unicast(len, &info, GFP_ATOMIC)
                                                upcall = genlmsg_put(user_skb, 0, 0, &dp_packet_genl_family, 0, upcall_info->cmd)
                                                genlmsg_unicast(ovs_dp_get_net(dp), user_skb, upcall_info->portid)
                                            queue_gso_packets(dp, skb, upcall_info)
                                                queue_userspace_packet(dp, skb, upcall_info)
                                                    user_skb = genlmsg_new_unicast(len, &info, GFP_ATOMIC)
                                                    upcall = genlmsg_put(user_skb, 0, 0, &dp_packet_genl_family, 0, upcall_info->cmd)
                                                    genlmsg_unicast(ovs_dp_get_net(dp), user_skb, upcall_info->portid)
                                    execute_hash(skb, a)
                                        OVS_CB(skb)->pkt_key->ovs_flow_hash = hash
                                    execute_recirc(dp, skb, a)
                                        ovs_flow_key_extract_recirc(nla_get_u32(a), OVS_CB(skb)->pkt_key, skb, &recirc_key)
                                            recirc_key->recirc_id = recirc_id
                                            key_extract(skb, recirc_key)
                                        ovs_dp_process_packet_with_key(skb, &recirc_key, true) : 参考前述
                                            push_vlan(skb, nla_data(a))
                                            pop_vlan(skb)
                                            execute_set_action(skb, nla_data(a)) : 修改 skb 各个属性
                                            sample(dp, skb, a)
                                                output_userspace(dp, skb, a)
                                                do_execute_actions(dp, skb, a, rem) : 参考前述


1. skb 携带了 vport 和 flow key. 从 vport 所属 datapath 的 table 中查找 key 对应的流表
2. 如果找到, 执行对应的 action
3. 如果没有找到, 发送 upcall


要点:

1. 从 packet 提取 flow 保存 skb->cb 中
2. 流表中 actions 解析过程中, 一旦遇到 output action 立即执行
3. 如果 recirc 不是最后一个 action, 拷贝 skb 之后执行. recirc 即将包回炉
4. 流表查询算法: skb->hash 每 8 位依次在 dp->tbl->mask_cache[skb->hash]->mask_index 中查找


##创建一条流表

###流程

ovs_flow_cmd_new(struct sk_buff *skb, struct genl_info *info)

    new_flow = ovs_flow_alloc
    	flow = kmem_cache_alloc(flow_cache, GFP_KERNEL);
    	stats = kmem_cache_alloc_node(flow_stats_cache, GFP_KERNEL | __GFP_ZERO, 0);
    	RCU_INIT_POINTER(flow->stats[0], stats);
    	for_each_node(node)
    			RCU_INIT_POINTER(flow->stats[node], NULL);
	ovs_match_init(&match, &new_flow->unmasked_key, &mask);
	ovs_nla_get_match(&match, a[OVS_FLOW_ATTR_KEY], a[OVS_FLOW_ATTR_MASK]);
	    parse_flow_nlattrs(key, a, &key_attrs); //提取 key 属性到 a
	    ovs_key_from_nlattrs(match, key_attrs, a, false);
		parse_flow_mask_nlattrs(mask, a, &mask_attrs);
		ovs_key_from_nlattrs(match, mask_attrs, a, true);
	    match_validate(match, key_attrs, mask_attrs))
	ovs_flow_mask_key(&new_flow->key, &new_flow->unmasked_key, &mask);

	acts = ovs_nla_alloc_flow_actions(nla_len(a[OVS_FLOW_ATTR_ACTIONS]));
	ovs_nla_copy_actions(a[OVS_FLOW_ATTR_ACTIONS], &new_flow->key, 0, &acts);
	    copy_action(a, sfa);

	ovs_flow_cmd_alloc_info(acts, info, false);
	dp = get_dp(sock_net(skb->sk), ovs_header->dp_ifindex);
	flow = ovs_flow_tbl_lookup(&dp->table, &new_flow->unmasked_key);
        flow_lookup(tbl, ti, ma, key, &n_mask_hit, &index);
		    flow = masked_flow_lookup(ti, key, mask, n_mask_hit);
	    flow == null:
            ovs_flow_tbl_insert(&dp->table, new_flow, &mask);
	            flow_mask_insert(table, flow, mask);
	                mask = flow_mask_find(tbl, new);
	            table_instance_insert(ti, flow);
			ovs_flow_cmd_fill_info(new_flow, ovs_header->dp_ifindex, reply, info->snd_portid, info->snd_seq, 0, OVS_FLOW_CMD_NEW);
                ovs_nla_put_identifier(flow, skb);
                ovs_nla_put_masked_key(flow, skb);
                ovs_nla_put_mask(flow, skb);
                ovs_flow_cmd_fill_stats(flow, skb);
                ovs_flow_cmd_fill_actions(flow, skb, skb_orig_len);
        flow != null:
            ovs_flow_cmp_unmasked_key(flow, &match) == false:
                flow = ovs_flow_tbl_lookup_exact(&dp->table, &match);
		    rcu_assign_pointer(flow->sf_acts, acts);
			ovs_flow_cmd_fill_info(flow, ovs_header->dp_ifindex, reply, info->snd_portid, info->snd_seq, 0, OVS_FLOW_CMD_NEW);
                ovs_nla_put_identifier(flow, skb);
                ovs_nla_put_masked_key(flow, skb);
                ovs_nla_put_mask(flow, skb);
                ovs_flow_cmd_fill_stats(flow, skb);
                ovs_flow_cmd_fill_actions(flow, skb, skb_orig_len);
	ovs_notify(&dp_flow_genl_family, &ovs_dp_flow_multicast_group, reply, info);

1. 为流表分配内存, 并初始化 new_flow.
2. 用 info->attrs[OVS_FLOW_ATTR_KEY] 初始化 match->key, 用 info->attrs[OVS_FLOW_ATTR_MASK] 初始化 match->mask
3. 用 new_flow->unmasked_key 和 mask 进行数学操作"与", 用结果初始化 new_flow->key
4. 为流表 actions 分配空间, 用 info->attrs[OVS_FLOW_ATTR_ACTIONS] 初始化 flow->sf_acts
5. 从网桥的 table 中查找与 flow->unmasked_key 对应的 flow.
7. 如果不存在, 发送对应的信息
8. 如果存在, 如果新的流的 key 与旧的流的 key 不同, 返回错误; 如果相同, 用新 flow 的 actions 代替旧的 actions.
7. 发送应答给请求者并通知多播组

## 查询一条流表

### 流程

ovs_flow_cmd_get(struct sk_buff *skb, struct genl_info *info)

	ufid_present = ovs_nla_get_ufid(&ufid, a[OVS_FLOW_ATTR_UFID], log);
	ovs_match_init(&match, &key, NULL);
	ovs_nla_get_match(&match, a[OVS_FLOW_ATTR_KEY], NULL);
	dp = get_dp(sock_net(skb->sk), ovs_header->dp_ifindex);
	if (ufid_present)
		flow = ovs_flow_tbl_lookup_ufid(&dp->table, &ufid);
	else
		flow = ovs_flow_tbl_lookup_exact(&dp->table, &match);
	reply = ovs_flow_cmd_build_info(flow, ovs_header->dp_ifindex, info, OVS_FLOW_CMD_NEW, true);
	return genlmsg_reply(reply, info);

1. 初始化流表的 match
2. 从 dp->table 查找 match 对应的流表
3. 如果找到, 返回找到的 flow. 没有找到返回错误


### 流表查询

struct sw_flow *ovs_flow_tbl_lookup_stats(struct flow_table *tbl, const struct sw_flow_key *key, u32 skb_hash, u32 *n_mask_hit)

    情况一: 对于 skb_hash 为 0 的情况, 退化为 flow_lookup 的全表(从索引 0 开始遍历 mask_array 每个元素)查询
    情况二: 对于 skb_hash 不为 0 的情况, 从 根据 skb_hash 从 tbl->mask_cache 当前 cpu 的 entries 中, 如果 entries[hash] == skb_hash, 优先从 mask_array[entries[hash]->mask_index] 中查找
    情况三: 对于从 tbl->mask_cache 中都没有找到对应的流, 从 entries 的最小索引开始, 进行全表查询

    1. 将 key 与 dp->table->mask_array 中的每一个元素掩码之后, 计算 hash 值
    2. 从 dp->table->ti->buckets 中查找 hash 对应的列表的头指针
    3. 遍历 2 的列表, 找到 mask, hash, 掩码之后 key 都相同的流



### 流表插入

1. 流的 mask 是否存在与 dp->table->mask_array 中
2. 如果不存在, 创建一个 mask 并插入 dp->table->mask_array(如果 mask 已经满了会进行重分配)
3. 如果存在, 计数器加 1
4. 在 dp->table 中查找 flow->hash 对应的 bucket, 将 flow 加入该 bucket

注意点:

    如果 flow 数量超过 bucket, 将 bucket 扩展 2 倍并进行重哈希
    如果超过 600 Hz 也会进行重新哈希

由于很多流共享 mask 因此, 通过 mask 可以减少存储消耗

流表重哈希间隔 600 Hz

## 修改一条流表项

### 流程

ovs_flow_cmd_set(skb, info)

    ovs_match_init(&match, &key, &mask);
    ovs_nla_get_match(&match, info->attr[OVS_FLOW_ATTR_KEY], info->attr[OVS_FLOW_ATTR_MASK]);
    if (info->attrs[OVS_FLOW_ATTR_ACTIONS])
        acts = ovs_nla_alloc_flow_actions(nla_len(a[OVS_FLOW_ATTR_ACTIONS]));
        ovs_flow_mask_key(&masked_key, &key, &mask);
        ovs_nla_copy_actions(a[OVS_FLOW_ATTR_ACTIONS], &masked_key, 0, &acts);
    reply = ovs_flow_cmd_alloc_info(acts, info, false);
	dp = get_dp(sock_net(skb->sk), ovs_header->dp_ifindex);
	ufid_present = ovs_nla_get_ufid(&sfid, a[OVS_FLOW_ATTR_UFID], log);
	if (ufid_present)
		flow = ovs_flow_tbl_lookup_ufid(&dp->table, &sfid);
	else
		flow = ovs_flow_tbl_lookup_exact(&dp->table, &match);
    acts != null:
		rcu_assign_pointer(flow->sf_acts, acts);
        ovs_flow_cmd_fill_info(flow, ovs_header->dp_ifindex, reply, info->snd_portid, info->snd_seq, 0, OVS_FLOW_CMD_NEW);
            ovs_nla_put_identifier(flow, skb);
            ovs_nla_put_masked_key(flow, skb);
            ovs_nla_put_mask(flow, skb);
            ovs_flow_cmd_fill_stats(flow, skb);
            ovs_flow_cmd_fill_actions(flow, skb, skb_orig_len);
    acts == null:
    	reply = ovs_flow_cmd_build_info(flow, ovs_header->dp_ifindex, info, OVS_FLOW_CMD_NEW, false);
            skb = ovs_flow_cmd_alloc_info(ovsl_dereference(flow->sf_acts), info, false);
                skb = genlmsg_new_unicast(ovs_flow_cmd_msg_size(acts), info, GFP_KERNEL);
            ovs_flow_cmd_fill_info(flow, dp_ifindex, skb, info->snd_portid, info->snd_seq, 0, cmd);
                ovs_nla_put_identifier(flow, skb);
                ovs_nla_put_masked_key(flow, skb);
                ovs_nla_put_mask(flow, skb);
                ovs_flow_cmd_fill_stats(flow, skb);
                ovs_flow_cmd_fill_actions(flow, skb, skb_orig_len);
	if (info->attrs[OVS_FLOW_ATTR_CLEAR]):
		ovs_flow_stats_clear(flow);
    ovs_notify(&dp_flow_genl_family, &ovs_dp_flow_multicast_group, reply, info);

1. 用 info->attrs[OVS_FLOW_ATTR_KEY] 初始化流表 match
2. 从 tbl->mask_array 中查找 match 对应的 flow
3. 如果 actions 不为 null, 新的 action 代替旧的 action
7. 发送应答给请求者并通知多播组


## 删除一条流表

### 流程

ovs_flow_cmd_del(struct sk_buff *skb, struct genl_info *info)

	ufid_present = ovs_nla_get_ufid(&ufid, a[OVS_FLOW_ATTR_UFID], log);
    info->[OVS_FLOW_ATTR_KEY] != null :
        ovs_match_init(&match, &key, NULL);
        ovs_nla_get_match(&match, a[OVS_FLOW_ATTR_KEY], NULL);
	dp = get_dp(sock_net(skb->sk), ovs_header->dp_ifindex);
    info->[OVS_FLOW_ATTR_KEY] == null && !ufid_present:
		err = ovs_flow_tbl_flush(&dp->table);
	if (ufid_present)
		flow = ovs_flow_tbl_lookup_ufid(&dp->table, &ufid);
	else
		flow = ovs_flow_tbl_lookup_exact(&dp->table, &match);
	ovs_flow_tbl_remove(&dp->table, flow);
	reply = ovs_flow_cmd_alloc_info((const struct sw_flow_actions __force *)flow->sf_acts, info, false);
	    skb = genlmsg_new_unicast(ovs_flow_cmd_msg_size(acts), info, GFP_KERNEL);
    if (replay && !IS_ERR(replay)):
	    ovs_flow_cmd_fill_info(flow, ovs_header->dp_ifindex, reply, info->snd_portid, info->snd_seq, 0, OVS_FLOW_CMD_DEL);
	    ovs_notify(&dp_flow_genl_family, &ovs_dp_flow_multicast_group, reply, info);

1. 如果没有给定匹配字段，默认删除所有流表
2. 如果给定匹配字段, 从流表中查询对应的流表项, 从流表中删除
3. 发送应答给请求者并通知多播组

## 输出匹配流表

### 流程

ovs_flow_cmd_dump(struct sk_buff *skb, struct netlink_callback *cb)

	struct nlattr *a[__OVS_FLOW_ATTR_MAX];
	genlmsg_parse(cb->nlh, &dp_flow_genl_family, a, OVS_FLOW_ATTR_MAX, flow_policy);
	ufid_flags = ovs_nla_get_ufid_flags(a[OVS_FLOW_ATTR_UFID_FLAGS]);
	dp = get_dp_rcu(sock_net(skb->sk), ovs_header->dp_ifindex);
	ti = rcu_dereference(dp->table.ti);
	for (;;)
		bucket = cb->args[0];
		obj = cb->args[1];
		flow = ovs_flow_tbl_dump_next(ti, &bucket, &obj);
		if (!flow)
			break;
		if (ovs_flow_cmd_fill_info(flow, ovs_header->dp_ifindex, skb,
					   NETLINK_CB(cb->skb).portid,
					   cb->nlh->nlmsg_seq, NLM_F_MULTI,
					   OVS_FLOW_CMD_NEW) < 0)
           break


## 对给定的包执行一个 action

ovs_packet_cmd_execute(skb, info)
	struct sk_buff *packet;
    struct nlattr **a = info->attrs;
    len = nla_len(a[OVS_PACKET_ATTR_PACKET]);
    //分配并初始化 packet
    packet = __dev_alloc_skb(NET_IP_ALIGN + len, GFP_KERNEL);
    skb_reserve(packet, NET_IP_ALIGN);
    nla_memcpy(__skb_put(packet, len), a[OVS_PACKET_ATTR_PACKET], len);
    //分配并初始化 flow
    flow = ovs_flow_alloc();
    ovs_flow_key_extract_userspace(a[OVS_PACKET_ATTR_KEY], packet, &flow->key);
	    ovs_nla_get_flow_metadata(attr, key, log);
	    key_extract(skb, key);
    //分配 action
    ovs_nla_copy_actions(a[OVS_PACKET_ATTR_ACTIONS], &flow->key, &acts, log);
        acts = ovs_nla_alloc_flow_actions(nla_len(a[OVS_PACKET_ATTR_ACTIONS]));
        __ovs_nla_copy_actions(a[OVS_PACKET_ATTR_ACTIONS], flow->key, 0, acts, flow->key->eth.type, flow->key->eth.tci, log);
    flow->sf_acts = acts
    OVS_CB(packet)->flow = flow;
    OVS_CB(packet)->pkt_key = &flow->key;
    packet->priority = flow->key.phy.priority;
    packet->mark = flow->key.phy.skb_mark;
    dp = get_dp(sock_net(skb->sk), ovs_header->dp_ifindex);
    //找到输入端口
    input_vport = ovs_vport_rcu(dp, flow->key.phy.in_port); # 在 dp->ports[port_no % DP_VPORT_HASH_BUCKET ] 中找到端口号为 port_no 的 vport, 找不到返回 NULL
    OVS_CB(packet)->input_vport = input_vport;
    // 根据 sf_acts 中的 actions 对 packet 进行修改, 然后发送到 sf_acts 中指定的出口
    ovs_execute_actions(dp, packet, flow->sf_acts, false);

1. 初始化 packet 内存
2. 将传入 info->attrs[OVS_PACKET_ATTR_PACKET] 参数保存到 packet
3. 为 flow 分配内存, 用 info->attrs[OVS_PACKET_ATTR_KEY] 和 packet 初始化 flow->key
4. 为 action 分配内存, 用 info->attrs[OVS_PACKET_ATTR_ACTIONS] 初始化 flow->sf_acts
6. 调用 ovs_execute_actions(dp, packet, false) 执行 packet 对应的 action

### 从数据包中提取 key

    ovs_flow_key_extract(skb, &key)

##数据结构

DP_VPORT_HASH_BUCKETS : 大小是否会影响速率

struct datapath {
	struct rcu_head rcu;
	struct list_head list_node;

	/*
     * Flow table.
     * 每个 datapath 有 255 张 table
     */
	struct flow_table table;

	/* Switch ports. */
	struct hlist_head *ports;

	/* Stats. */
	struct dp_stats_percpu __percpu *stats_percpu;

#ifdef CONFIG_NET_NS
	/* Network namespace ref. */
	struct net *net;
#endif

	u32 user_features;  // 什么意思待理解
};


/**
 * struct vport - one port within a datapath
 * @rcu: RCU callback head for deferred destruction.
 * @dp: Datapath to which this port belongs.
 * @upcall_portids: RCU protected 'struct vport_portids'.
 * @port_no: Index into @dp's @ports array.
 * @hash_node: Element in @dev_table hash table in vport.c.
 * @dp_hash_node: Element in @datapath->ports hash table in datapath.c.
 * @ops: Class structure.
 * @percpu_stats: Points to per-CPU statistics used and maintained by vport
 * @err_stats: Points to error statistics used and maintained by vport
 * @detach_list: list used for detaching vport in net-exit call.
 */
struct vport {
	struct rcu_head rcu;
	struct datapath	*dp;
	struct vport_portids __rcu *upcall_portids;
	u16 port_no;

	struct hlist_node hash_node;
	struct hlist_node dp_hash_node; --> datapath->vport->first
	const struct vport_ops *ops;

	struct pcpu_sw_netstats __percpu *percpu_stats;

	struct vport_err_stats err_stats;
	struct list_head detach_list;
};

/**
 * struct vport_ops - definition of a type of virtual port
 *
 * @type: %OVS_VPORT_TYPE_* value for this type of virtual port.
 * @create: Create a new vport configured as specified.  On success returns
 * a new vport allocated with ovs_vport_alloc(), otherwise an ERR_PTR() value.
 * @destroy: Destroys a vport.  Must call vport_free() on the vport but not
 * before an RCU grace period has elapsed.
 * @set_options: Modify the configuration of an existing vport.  May be %NULL
 * if modification is not supported.
 * @get_options: Appends vport-specific attributes for the configuration of an
 * existing vport to a &struct sk_buff.  May be %NULL for a vport that does not
 * have any configuration.
 * @get_name: Get the device's name.
 * @send: Send a packet on the device.  Returns the length of the packet sent,
 * zero for dropped packets or negative for error.
 * @get_egress_tun_info: Get the egress tunnel 5-tuple and other info for
 * a packet.
 */
struct vport_ops {
	enum ovs_vport_type type;

	/* Called with ovs_mutex. */
	struct vport *(*create)(const struct vport_parms *);
	void (*destroy)(struct vport *);

	int (*set_options)(struct vport *, struct nlattr *);
	int (*get_options)(const struct vport *, struct sk_buff *);

	/* Called with rcu_read_lock or ovs_mutex. */
	const char *(*get_name)(const struct vport *);

	int (*send)(struct vport *, struct sk_buff *);
	int (*get_egress_tun_info)(struct vport *, struct sk_buff *,
				   struct ovs_tunnel_info *);

	struct module *owner;
	struct list_head list; //连接所有的 vport_ops
};

/**
 * struct vport_portids - array of netlink portids of a vport.
 *                        must be protected by rcu.
 * @rn_ids: The reciprocal value of @n_ids.
 * @rcu: RCU callback head for deferred destruction.
 * @n_ids: Size of @ids array.
 * @ids: Array storing the Netlink socket pids to be used for packets received
 * on this port that miss the flow table.
 */
struct vport_portids {
	struct reciprocal_value rn_ids;
	struct rcu_head rcu;
	u32 n_ids;
	u32 ids[];
};

struct flow_table {
	struct table_instance __rcu *ti;
	struct table_instance __rcu *ufid_ti;
    //每个 CPU 都有的流表的缓存, 只有三条, 索引为 skb->hash & 3
	struct mask_cache_entry __percpu *mask_cache;
    //内核流表项缓存
	struct mask_array __rcu *mask_array;
	unsigned long last_rehash;
	unsigned int count;  // table 中的 flow 数量
	unsigned int ufid_count;
};

//table_instance　的每个 buckets 中保存 sw_flow.
struct table_instance {
	struct flex_array *buckets;
	unsigned int n_buckets;
	struct rcu_head rcu;
	int node_ver;           //flow->hash_node 的索引
	u32 hash_seed;
	bool keep_flows;
};

struct flex_array {
	union {
		struct {
			int element_size;
			int total_nr_elements;
			int elems_per_part;
			struct reciprocal_value reciprocal_elems;
			struct flex_array_part *parts[];
		};
		/*
		 * This little trick makes sure that
		 * sizeof(flex_array) == PAGE_SIZE
		 */
		char padding[FLEX_ARRAY_BASE_SIZE]; //#define FLEX_ARRAY_BASE_SIZE PAGE_SIZE
	};
};

struct mask_cache_entry {
	u32 skb_hash;
	u32 mask_index;   //在查询流表状态时, 对应 key 的 mask 最可能在 mask_array 的索引
};

struct mask_array {
	struct rcu_head rcu;
	int count;              //
    int max;                //最大索引
	struct sw_flow_mask __rcu *masks[];
};

struct sw_flow_mask {
	int ref_count;
	struct rcu_head rcu;
	struct sw_flow_key_range range;
	struct sw_flow_key key;
};

//key 匹配的范围
struct sw_flow_key_range {
	unsigned short int start;
	unsigned short int end;
};



struct flex_array_part {
    char elements[FLEX_ARRAY_PART_SIZE];
}

struct sw_flow {
	struct rcu_head rcu;
	struct {
		struct hlist_node node[2];
		u32 hash;               /* 查找所属 table_instance->buckets 的 hash; flow_hash(&flow->key, &flow->mask->range); */
	} flow_table, ufid_table;
	int stats_last_writer;		/* NUMA-node id of the last writer on 'stats[0]' */
	struct sw_flow_key key;
	struct sw_flow_id id;
	struct sw_flow_mask *mask;
	struct sw_flow_actions __rcu *sf_acts;
	struct flow_stats __rcu *stats[]; /* One for each NUMA node.  First one
					   * is allocated at flow creation time,
					   * the rest are allocated on demand
					   * while holding the 'stats[0].lock'.
					   */
};

struct sw_flow_key {
	u8 tun_opts[255];
	u8 tun_opts_len;
	struct ovs_key_ipv4_tunnel tun_key;  /* Encapsulating tunnel key. */
	struct {
		u32	priority;	/* Packet QoS priority. */
		u32	skb_mark;	/* SKB mark. */
		u16	in_port;	/* Input switch port (or DP_MAX_PORTS). */
	} __packed phy; /* Safe when right after 'tun_key'. */
	u32 ovs_flow_hash;		/* Datapath computed hash value.  */
	u32 recirc_id;			/* Recirculation ID.  */
	struct {
		u8     src[ETH_ALEN];	/* Ethernet source address. */
		u8     dst[ETH_ALEN];	/* Ethernet destination address. */
		__be16 tci;		/* 0 if no VLAN, VLAN_TAG_PRESENT set otherwise. */
		__be16 type;		/* Ethernet frame type. */
	} eth;
	union {
		struct {
			__be32 top_lse;	/* top label stack entry */
		} mpls;
		struct {
			u8     proto;	/* IP protocol or lower 8 bits of ARP opcode. */
			u8     tos;	    /* IP ToS. */
			u8     ttl;	    /* IP TTL/hop limit. */
			u8     frag;	/* One of OVS_FRAG_TYPE_*. */
		} ip;
	};
	struct {
		__be16 src;		/* TCP/UDP/SCTP source port. */
		__be16 dst;		/* TCP/UDP/SCTP destination port. */
		__be16 flags;		/* TCP flags. */
	} tp;
	union {
		struct {
			struct {
				__be32 src;	/* IP source address. */
				__be32 dst;	/* IP destination address. */
			} addr;
			struct {
				u8 sha[ETH_ALEN];	/* ARP source hardware address. */
				u8 tha[ETH_ALEN];	/* ARP target hardware address. */
			} arp;
		} ipv4;
		struct {
			struct {
				struct in6_addr src;	/* IPv6 source address. */
				struct in6_addr dst;	/* IPv6 destination address. */
			} addr;
			__be32 label;			/* IPv6 flow label. */
			struct {
				struct in6_addr target;	/* ND target address. */
				u8 sll[ETH_ALEN];	/* ND source link layer address. */
				u8 tll[ETH_ALEN];	/* ND target link layer address. */
			} nd;
		} ipv6;
	};
} __aligned(BITS_PER_LONG/8); /* Ensure that we can do comparisons as longs. */

struct sw_flow_actions {
	struct rcu_head rcu;
	u32 actions_len;
	struct nlattr actions[];
};

/**
 * struct ovs_net - Per net-namespace data for ovs.
 * @dps: List of datapaths to enable dumping them all out.
 * Protected by genl_mutex.
 * @vport_net: Per network namespace data for vport.
 */
struct ovs_net {
	struct list_head dps;
	struct work_struct dp_notify_work;
	struct vport_net vport_net;
};

--------------------------------------------------------

###static int ovs_dp_cmd_new(struct sk_buff *skb, struct genl_info *info)

    1. 为一个 struct sk_buff 对象 reply 分配内存, 并根据 info 初始化该对象
    2. 为一个 struct datapath 对象 dp 分配内存, 并初始化
    3. 将 info 修改 replay 对象属性, 并将消息应答给发消息者 vswitchd

    其中2:
        dp->net = skb->sk->sk_net
        dp->table = ovs_flow_tbl_init(table)
        dp->stats_percpu 初始化
        dp->ports = kmalloc(DP_VPORT_HASH_BUCKETS * sizeof(struct hlist_head),GFP_KERNEL)
        初始化每个 dp->ports[i] (i=0,DP_VPORT_HASH_BUCKETS)
        dp->user_features = nla_get_u32(a[OVS_DP_ATTR_USER_FEATURES]);
        dp->list_node  加入链表 dp->net[ovs_net_id - 1]


    其中3 返回给 vswitch 的信息包含

        ovs_header->dp_ifindex = 0
        OVS_DP_ATTR_NAME  : ovs_vport_ovsl_rcu(dp, OVSP_LOCAL)->ops->get_name(ovs_vport_ovsl_rcu(dp, OVSP_LOCAL))
        OVS_DP_ATTR_STATS : dp_stats
        OVS_DP_ATTR_MEGAFLOW_STATS : dp_megaflow_stats
        OVS_DP_ATTR_USER_FEATURES  : dp->user_features
        其中
        dp_megaflow_stats->n_masks = dp->table->mask_array->count
        dp_megaflow_stats->n_mask_hit = 所有 cpu 的 n_mask_hit
        dp_stats->n_flows = dp->table
        dp_stats->n_hist : 所有 cpu 的 n_hit
        dp_stats->n_missed : 所有 cpu 的 n_missed
        dp_stats->n_lost : 所有 cpu 的 n_lost

###static int ovs_dp_cmd_del(struct sk_buff *skb, struct genl_info *info)

    通过 skb->sk->net info->userhdr, info->attrs 找到待删除的 dp
    销毁 dp 下的每个端口
    向发送者通知删除操作

static struct datapath *lookup_datapath(struct net *net,
					const struct ovs_header *ovs_header,
					struct nlattr *a[OVS_DP_ATTR_MAX + 1])

    如果 info->attrs[OVS_DP_ATTR_NAME] = NULL
        遍历 net->dev_index_head[info->userhdr->ifindex & (NETDEV_HASHENTRIES - 1)] 所有元素,
        找到 dev->ifindex = ifindex 的 dev, 返回 netdev_priv(dev)->vport->dp
    否则
        遍历 dev_table[jhash(name, strlen(name), (unsigned long) net) & (VPORT_HASH_BUCKETS - 1)] 的所有 vport,
        找到 vport->ops->get_name(vport）= name, vport->dp->net = net 的 vport, 返回 vport->dp

static int ovs_dp_cmd_set(struct sk_buff *skb, struct genl_info *info)

    通过 skb->sk->net info->userhdr, info->attrs 找到待删除的 dp
    只能修改 dp->user_features
    向发送者通知统计消息


int ovs_flow_tbl_init(struct flow_table *table)

    初始化 flow_table 结构体

    具体:
	table->mask_cache = __alloc_percpu(sizeof(struct mask_cache_entry) *
					  MC_HASH_ENTRIES, __alignof__(struct mask_cache_entry));

    //TBL_MIN_BUCKETS=1024
    table->ti = kmalloc(sizeof(*ti), GFP_KERNEL);
    table->ti->buckets = alloc_buckets(TBL_MIN_BUCKETS)
	table->ti->n_buckets = TBL_MIN_BUCKETS;
	table->ti->node_ver = 0;
	table->ti->keep_flows = false;
	get_random_bytes(&table->ti->hash_seed, sizeof(u32));

    //TBL_MIN_BUCKETS=1024
    table->ufid_ti = kmalloc(sizeof(*ti), GFP_KERNEL)
	table->ufid_ti->buckets = alloc_buckets(new_size);
	table->ufid_ti->n_buckets = TBL_MIN_BUCKETS;
	table->ufid_ti->node_ver = 0;
	table->ufid_ti->keep_flows = false;
	get_random_bytes(&table->ufid_ti->hash_seed, sizeof(u32));

    //MASK_ARRAY_SIZE_MIN=16
    table->mask_array = new  kzalloc(sizeof(struct mask_array) +
		      sizeof(struct sw_flow_mask *) * MASK_ARRAY_SIZE_MIN, GFP_KERNEL);
	table->mask_array->count = 0
	table->mask_array->max = MASK_ARRAY_SIZE_MIN

    table->last_rehash = jiffies
	table->count = 0;
	table->ufid_count = 0;


//待完善, 具体参考内核
struct flex_array *rpl_lex_array_alloc(int element_size, unsigned int
        total,gfp_t flags)

    element_size   : sizeof(struct hlist_head)
    n_buckets      : 1024
    elems_per_part : PAGE_SIZE/element_size  : 每页可以放多少个 hlist_head,
                    elems_per_part 即 part 中元素个数

    FLEX_ARRAY_NR_BASE_PTRS : 一页中除去 element_size, total_nr_elements,
    elems_per_part, reciprocal_value 剩余的空间可以存储多少个 part
    max_size = FLEX_ARRAY_NR_BASE_PTRS * elems_per_part 为

    关系: elems_per_part * element_size = PAGE_SIZE
          element_size * n_buckets =

每个 table 分配了 element_size 个 hlist_head.

static int ovs_dp_cmd_fill_info(struct datapath *dp, struct sk_buff *skb,
				u32 portid, u32 seq, u32 flags, u8 cmd)

	get_dp_stats(dp, &dp_stats, &dp_megaflow_stats);

	ovs_header = genlmsg_put(skb, portid, seq, &dp_datapath_genl_family,
				   flags, cmd);
	ovs_header->dp_ifindex = get_dpifindex(dp);
	nla_put_string(skb, OVS_DP_ATTR_NAME, ovs_dp_name(dp));
    nla_put(skb, OVS_DP_ATTR_STATS, sizeof(struct ovs_dp_stats),&dp_stats)
    nla_put(skb, OVS_DP_ATTR_MEGAFLOW_STATS, sizeof(struct ovs_dp_megaflow_stats), &dp_megaflow_stats)
    nla_put_u32(skb, OVS_DP_ATTR_USER_FEATURES, dp->user_features)
	genlmsg_end(skb, ovs_header);

--------------------------------------------------------

--------------------------------------------------------

###static int ovs_vport_cmd_new(struct sk_buff *skb, struct genl_info *info)

    1. 确保 vport 所在的 datapath 存在
    2. 如果没有给定端口号, 从头开始找到空闲的端口号 port_no.
        如果给定端口号, 确保端口号 port_no 与已有的端口号 port_no 不存在.
    3. 创建一个 vport 并初始化各个数据成员, 包括私有数据
    4. 将信息应答给请求者(vswitchd)

    创建 vport 的参数

        parms.name = nla_data(a[OVS_VPORT_ATTR_NAME]);
        parms.type = nla_get_u32(a[OVS_VPORT_ATTR_TYPE]);
        parms.options = a[OVS_VPORT_ATTR_OPTIONS];
        parms.dp = dp;
        parms.port_no = port_no;
        parms.upcall_portids = a[OVS_VPORT_ATTR_UPCALL_PID];

static int ovs_vport_cmd_set(struct sk_buff *skb, struct genl_info *info)

    设置 vport 的属性, 包括:

    OVS_VPORT_ATTR_OPTIONS : info->attrs[OVS_VPORT_ATTR_OPTIONS]
    OVS_VPORT_ATTR_UPCALL_PID : info->attrs[OVS_VPORT_ATTR_UPCALL_PID]


static int ovs_vport_cmd_del(struct sk_buff *skb, struct genl_info *info)

    1. 从 net,name 找到 dp, 进而找到 vport 或 从 net,dpifindex 找到 dp, 进而找到 vport
    2. 删除 vport (OVSP_LOCAL 的端口不可以删除)
    3. 发送消息给发送者(vswitchd)

static int ovs_vport_cmd_get(struct sk_buff *skb, struct genl_info *info)

    获取指定 vport 的属性信息, 应答给请求者(vswitchd)

static int ovs_vport_cmd_dump(struct sk_buff *skb, struct netlink_callback *cb)

    数字 dp->ports[] 索引 cb->agrs[0] 开始, 跳过前 cb->args[1] 个 vport,
    剩余的 vport 属性信息(见下)写入 skb

    OVS_VPORT_ATTR_PORT_NO : vport->port_no
    OVS_VPORT_ATTR_TYPE : vport->ops->type
    OVS_VPORT_ATTR_NAME : vport->ops->get_name(vport)
    OVS_VPORT_ATTR_STATS : vport_stats
    OVS_VPORT_ATTR_UPCALL_PID:ids->n_ids * sizeof(u32), (void *) ids->ids
    OVS_VPORT_ATTR_OPTIONS:vport->ops->get_options(vport, skb)

--------------------------------------------------------

u32 ovs_vport_find_upcall_portid(const struct vport *vport, struct sk_buff *skb)

如果 vport->upcall_portids 为只有一个, 且 id 为 0, 返回 0
否则 对 skb hash 后获取索引(细节待考)

--------------------------------------------

static int queue_userspace_packet(struct datapath *dp, struct sk_buff *skb,
				  const struct sw_flow_key *key,
				  const struct dp_upcall_info *upcall_info)

upcall 核心实现

dp = (ovs_skb_cb*)(skb->cb)->input_vport->dp;

upcall_info info = {
    .cmd = OVS_PACKET_CMD_MISS
    .portid = ovs_vport_find_upcall_portid(p, skb)
}

len = upcall_msg_size(upcall_info, hlen); //计算

//调用 skb_alloc() 分配 skb 空间 user_skb
user_skb = genlmsg_new_unicast(len, &info, GFP_ATOMIC);

/*
 * nlms_put 填充 user_skb->data 为 nlmsghdr
 * nlmsghdr->payload 为 genlmsghdr
 * 返回 nlmsghdr->family->attributes 的头指针
 * 具体可以参考 netlink.h 的结构体
 */
upcall = genlmsg_put(user_skb, 0, 0, &dp_packet_genl_family,
			     0, upcall_info->cmd);


//将 key 打包到 nlamsg 属性里面
ovs_nla_put_key(key, key, OVS_PACKET_ATTR_KEY, false, user_skb);

之后将 upcall_info 的 userdata, egress_tun_info, actions 打包到 user_skb

//将 user_skb 发送给 upcall_info->portid 对应的 netlink
genlmsg_unicast(ovs_dp_get_net(dp), user_skb, upcall_info->portid);

--------------------------------------------
static inline struct sk_buff *genlmsg_new_unicast(size_t payload,
						  struct genl_info *info,
						  gfp_t flags)
{
	return genlmsg_new(payload, flags);
}

--------------------------------------------

#define skb_zerocopy_headlen rpl_skb_zerocopy_headlen

unsigned int rpl_skb_zerocopy_headlen(const struct sk_buff *from)

如果 (struct skb_shared_info *)(from->end)->frag_list != null 返回 from->len

如果 from->head_fags = false 或 from->tail - from->tail < L1_CACHE_BYTES 或 (from->end)->nr_frags >= MAX_SKB_FRAGS
返回 from->tail - from->tail

否则 返回 0

-------------------------------------
static size_t upcall_msg_size(const struct dp_upcall_info *upcall_info,
			      unsigned int hdrlen)

返回
    ovs_header + hdrlen + ovs_key_attr_size()
    + upcall_info->userdata->nla_len
    + nla_total_size(upcall_info->actions_len)
    + nla_total_size(ovs_tun_key_attr_size())
-------------------------------------

## Netlink

### 数据结构

来源 /datapath/linux/compat/include/linux/openvswitch.h

核心实现 /datapath/datapath.c 中的 queue_userspace_packet()

/**
 * struct dp_upcall - metadata to include with a packet to send to userspace
 * @cmd: One of %OVS_PACKET_CMD_*.
 * @userdata: If nonnull, its variable-length value is passed to userspace as
 * %OVS_PACKET_ATTR_USERDATA.
 * @portid: Netlink portid to which packet should be sent.  If @portid is 0
 * then no packet is sent and the packet is accounted in the datapath's @n_lost
 * counter.
 * @egress_tun_info: If nonnull, becomes %OVS_PACKET_ATTR_EGRESS_TUN_KEY.
 */
struct dp_upcall_info {
	const struct ovs_tunnel_info *egress_tun_info;
	const struct nlattr *userdata;
	const struct nlattr *actions;
	int actions_len;
	u32 portid;
	u8 cmd;
};

struct nlattr {
    uint16_t nla_len;
    uint16_t nla_type;
};

/**
 * struct ovs_header - header for OVS Generic Netlink messages.
 * @dp_ifindex: ifindex of local port for datapath (0 to make a request not
 * specific to a datapath).
 *
 * Attributes following the header are specific to a particular OVS Generic
 * Netlink family, but all of the OVS families use this header.
 */

struct ovs_header {
	int dp_ifindex;
};

enum ovs_datapath_cmd {
	OVS_DP_CMD_UNSPEC,
	OVS_DP_CMD_NEW,
	OVS_DP_CMD_DEL,
	OVS_DP_CMD_GET,
	OVS_DP_CMD_SET
};

enum ovs_datapath_attr {
	OVS_DP_ATTR_UNSPEC,
	OVS_DP_ATTR_NAME,		/* name of dp_ifindex netdev */
	OVS_DP_ATTR_UPCALL_PID,		/* Netlink PID to receive upcalls */
	OVS_DP_ATTR_STATS,		/* struct ovs_dp_stats */
	OVS_DP_ATTR_MEGAFLOW_STATS,	/* struct ovs_dp_megaflow_stats */
	OVS_DP_ATTR_USER_FEATURES,	/* OVS_DP_F_*  */
	__OVS_DP_ATTR_MAX
};

enum ovs_packet_cmd {
	OVS_PACKET_CMD_UNSPEC,

	/* Kernel-to-user notifications. */
	OVS_PACKET_CMD_MISS,    /* Flow table miss. */
	OVS_PACKET_CMD_ACTION,  /* OVS_ACTION_ATTR_USERSPACE action. */

	/* Userspace commands. */
	OVS_PACKET_CMD_EXECUTE  /* Apply actions to a packet. */
};


enum ovs_vport_cmd {
	OVS_VPORT_CMD_UNSPEC,
	OVS_VPORT_CMD_NEW,
	OVS_VPORT_CMD_DEL,
	OVS_VPORT_CMD_GET,
	OVS_VPORT_CMD_SET
};

enum ovs_vport_type {
	OVS_VPORT_TYPE_UNSPEC,
	OVS_VPORT_TYPE_NETDEV,   /* network device */
	OVS_VPORT_TYPE_INTERNAL, /* network device implemented by datapath */
	OVS_VPORT_TYPE_GRE,      /* GRE tunnel. */
	OVS_VPORT_TYPE_VXLAN,	 /* VXLAN tunnel. */
	OVS_VPORT_TYPE_GENEVE,	 /* Geneve tunnel. */
	OVS_VPORT_TYPE_GRE64 = 104, /* GRE tunnel with 64-bit keys */
	OVS_VPORT_TYPE_LISP = 105,  /* LISP tunnel */
	OVS_VPORT_TYPE_STT = 106, /* STT tunnel */
	__OVS_VPORT_TYPE_MAX
};

enum ovs_vport_attr {
	OVS_VPORT_ATTR_UNSPEC,
	OVS_VPORT_ATTR_PORT_NO,	/* u32 port number within datapath */
	OVS_VPORT_ATTR_TYPE,	/* u32 OVS_VPORT_TYPE_* constant. */
	OVS_VPORT_ATTR_NAME,	/* string name, up to IFNAMSIZ bytes long */
	OVS_VPORT_ATTR_OPTIONS, /* nested attributes, varies by vport type */
	OVS_VPORT_ATTR_UPCALL_PID, /* array of u32 Netlink socket PIDs for */
				/* receiving upcalls */
	OVS_VPORT_ATTR_STATS,	/* struct ovs_vport_stats */
	__OVS_VPORT_ATTR_MAX
};

enum {
	OVS_VXLAN_EXT_UNSPEC,
	OVS_VXLAN_EXT_GBP,      /* Flag or __u32 */
	__OVS_VXLAN_EXT_MAX,
};

enum {
	OVS_TUNNEL_ATTR_UNSPEC,
	OVS_TUNNEL_ATTR_DST_PORT, /* 16-bit UDP port, used by L4 tunnels. */
	OVS_TUNNEL_ATTR_EXTENSION,
	__OVS_TUNNEL_ATTR_MAX
};

enum ovs_flow_cmd {
	OVS_FLOW_CMD_UNSPEC,
	OVS_FLOW_CMD_NEW,
	OVS_FLOW_CMD_DEL,
	OVS_FLOW_CMD_GET,
	OVS_FLOW_CMD_SET
};

enum ovs_key_attr {
	OVS_KEY_ATTR_UNSPEC,
	OVS_KEY_ATTR_ENCAP,	/* Nested set of encapsulated attributes. */
	OVS_KEY_ATTR_PRIORITY,  /* u32 skb->priority */
	OVS_KEY_ATTR_IN_PORT,   /* u32 OVS dp port number */
	OVS_KEY_ATTR_ETHERNET,  /* struct ovs_key_ethernet */
	OVS_KEY_ATTR_VLAN,	/* be16 VLAN TCI */
	OVS_KEY_ATTR_ETHERTYPE,	/* be16 Ethernet type */
	OVS_KEY_ATTR_IPV4,      /* struct ovs_key_ipv4 */
	OVS_KEY_ATTR_IPV6,      /* struct ovs_key_ipv6 */
	OVS_KEY_ATTR_TCP,       /* struct ovs_key_tcp */
	OVS_KEY_ATTR_UDP,       /* struct ovs_key_udp */
	OVS_KEY_ATTR_ICMP,      /* struct ovs_key_icmp */
	OVS_KEY_ATTR_ICMPV6,    /* struct ovs_key_icmpv6 */
	OVS_KEY_ATTR_ARP,       /* struct ovs_key_arp */
	OVS_KEY_ATTR_ND,        /* struct ovs_key_nd */
	OVS_KEY_ATTR_SKB_MARK,  /* u32 skb mark */
	OVS_KEY_ATTR_TUNNEL,    /* Nested set of ovs_tunnel attributes */
	OVS_KEY_ATTR_SCTP,      /* struct ovs_key_sctp */
	OVS_KEY_ATTR_TCP_FLAGS,	/* be16 TCP flags. */
	OVS_KEY_ATTR_DP_HASH,   /* u32 hash value. Value 0 indicates the hash
				   is not computed by the datapath. */
	OVS_KEY_ATTR_RECIRC_ID, /* u32 recirc id */
	OVS_KEY_ATTR_MPLS,      /* array of struct ovs_key_mpls.
				 * The implementation may restrict
				 * the accepted length of the array. */

#ifdef __KERNEL__
	/* Only used within kernel data path. */
	OVS_KEY_ATTR_TUNNEL_INFO,  /* struct ovs_tunnel_info */
#endif
	__OVS_KEY_ATTR_MAX
};

enum ovs_tunnel_key_attr {
	OVS_TUNNEL_KEY_ATTR_ID,                 /* be64 Tunnel ID */
	OVS_TUNNEL_KEY_ATTR_IPV4_SRC,           /* be32 src IP address. */
	OVS_TUNNEL_KEY_ATTR_IPV4_DST,           /* be32 dst IP address. */
	OVS_TUNNEL_KEY_ATTR_TOS,                /* u8 Tunnel IP ToS. */
	OVS_TUNNEL_KEY_ATTR_TTL,                /* u8 Tunnel IP TTL. */
	OVS_TUNNEL_KEY_ATTR_DONT_FRAGMENT,      /* No argument, set DF. */
	OVS_TUNNEL_KEY_ATTR_CSUM,               /* No argument. CSUM packet. */
	OVS_TUNNEL_KEY_ATTR_OAM,                /* No argument. OAM frame.  */
	OVS_TUNNEL_KEY_ATTR_GENEVE_OPTS,        /* Array of Geneve options. */
	OVS_TUNNEL_KEY_ATTR_TP_SRC,		/* be16 src Transport Port. */
	OVS_TUNNEL_KEY_ATTR_TP_DST,		/* be16 dst Transport Port. */
	OVS_TUNNEL_KEY_ATTR_VXLAN_OPTS,		/* Nested OVS_VXLAN_EXT_* */
	__OVS_TUNNEL_KEY_ATTR_MAX
};

enum ovs_frag_type {
	OVS_FRAG_TYPE_NONE,
	OVS_FRAG_TYPE_FIRST,
	OVS_FRAG_TYPE_LATER,
	__OVS_FRAG_TYPE_MAX
};

enum ovs_flow_attr {
	OVS_FLOW_ATTR_UNSPEC,
	OVS_FLOW_ATTR_KEY,       /* Sequence of OVS_KEY_ATTR_* attributes. */
	OVS_FLOW_ATTR_ACTIONS,   /* Nested OVS_ACTION_ATTR_* attributes. */
	OVS_FLOW_ATTR_STATS,     /* struct ovs_flow_stats. */
	OVS_FLOW_ATTR_TCP_FLAGS, /* 8-bit OR'd TCP flags. */
	OVS_FLOW_ATTR_USED,      /* u64 msecs last used in monotonic time. */
	OVS_FLOW_ATTR_CLEAR,     /* Flag to clear stats, tcp_flags, used. */
	OVS_FLOW_ATTR_MASK,      /* Sequence of OVS_KEY_ATTR_* attributes. */
	OVS_FLOW_ATTR_PROBE,     /* Flow operation is a feature probe, error
				  * logging should be suppressed. */
	OVS_FLOW_ATTR_UFID,      /* Variable length unique flow identifier. */
	OVS_FLOW_ATTR_UFID_FLAGS,/* u32 of OVS_UFID_F_*. */
	__OVS_FLOW_ATTR_MAX
};

enum ovs_sample_attr {
	OVS_SAMPLE_ATTR_UNSPEC,
	OVS_SAMPLE_ATTR_PROBABILITY, /* u32 number */
	OVS_SAMPLE_ATTR_ACTIONS,     /* Nested OVS_ACTION_ATTR_* attributes. */
	__OVS_SAMPLE_ATTR_MAX,
};

enum ovs_userspace_attr {
	OVS_USERSPACE_ATTR_UNSPEC,
	OVS_USERSPACE_ATTR_PID,	      /* u32 Netlink PID to receive upcalls. */
	OVS_USERSPACE_ATTR_USERDATA,  /* Optional user-specified cookie. */
	OVS_USERSPACE_ATTR_EGRESS_TUN_PORT,  /* Optional, u32 output port
					      * to get tunnel info. */
	OVS_USERSPACE_ATTR_ACTIONS,   /* Optional flag to get actions. */
	__OVS_USERSPACE_ATTR_MAX
};

enum ovs_action_attr {
	OVS_ACTION_ATTR_UNSPEC,
	OVS_ACTION_ATTR_OUTPUT,	      /* u32 port number. */
	OVS_ACTION_ATTR_USERSPACE,    /* Nested OVS_USERSPACE_ATTR_*. */
	OVS_ACTION_ATTR_SET,          /* One nested OVS_KEY_ATTR_*. */
	OVS_ACTION_ATTR_PUSH_VLAN,    /* struct ovs_action_push_vlan. */
	OVS_ACTION_ATTR_POP_VLAN,     /* No argument. */
	OVS_ACTION_ATTR_SAMPLE,       /* Nested OVS_SAMPLE_ATTR_*. */
	OVS_ACTION_ATTR_RECIRC,       /* u32 recirc_id. */
	OVS_ACTION_ATTR_HASH,	      /* struct ovs_action_hash. */
	OVS_ACTION_ATTR_PUSH_MPLS,    /* struct ovs_action_push_mpls. */
	OVS_ACTION_ATTR_POP_MPLS,     /* __be16 ethertype. */
	OVS_ACTION_ATTR_SET_MASKED,   /* One nested OVS_KEY_ATTR_* including
				       * data immediately followed by a mask.
				       * The data must be zero for the unmasked
				       * bits. */

#ifndef __KERNEL__
	OVS_ACTION_ATTR_TUNNEL_PUSH,   /* struct ovs_action_push_tnl*/
	OVS_ACTION_ATTR_TUNNEL_POP,    /* u32 port number. */
#endif
	__OVS_ACTION_ATTR_MAX,	      /* Nothing past this will be accepted
				       * from userspace. */

#ifdef __KERNEL__
	OVS_ACTION_ATTR_SET_TO_MASKED, /* Kernel module internal masked
					* set action converted from
					* OVS_ACTION_ATTR_SET. */
#endif
};

--------------------------------------------------------------

int ovs_nla_put_actions(const struct nlattr *attr, int len, struct sk_buff *skb)

    遍历 attr 的每个属性, 根据属性类型增加对应的 data

--------------------------------------------------------------

static void do_output(struct datapath *dp, struct sk_buff *skb, int out_port)

    如果从 dp 中找到 port_no = out_port 的 vport, 调用 ovs_vport_send(vport, skb);
    否则释放 skb

--------------------------------------------------------------

int ovs_vport_send(struct vport *vport, struct sk_buff *skb)

调用 vport->pos->send(vport, skb), 发送 skb 到 vport, 返回发送
的字节数

--------------------------------------------------------------
static int do_execute_actions(struct datapath *dp, struct sk_buff *skb,
			      struct sw_flow_key *key,
			      const struct nlattr *attr, int len)
    遍历 attr = key->sf_acts->actions,  判断每个 nla_type(attr)

    OVS_ACTION_ATTR_OUTPUT          : do_output(dp, out_skb, nla_get_u32(a));
    OVS_ACTION_ATTR_USERSPACE       : output_userspace(dp, skb, key, a, attr, len);
    OVS_ACTION_ATTR_HASH            : execute_hash(skb, key, a);
    OVS_ACTION_ATTR_PUSH_MPLS       : push_mpls(skb, key, nla_data(a));
    OVS_ACTION_ATTR_POP_MPLS        : pop_mpls(skb, key, nla_get_be16(a));
    OVS_ACTION_ATTR_PUSH_VLAN       : push_vlan(skb, key, nla_data(a));
    OVS_ACTION_ATTR_POP_VLAN        : pop_vlan(skb, key);
    OVS_ACTION_ATTR_RECIRC          : execute_recirc(dp, skb, key, a, rem);
	OVS_ACTION_ATTR_SET             : execute_set_action(skb, key, nla_data(a));
    OVS_ACTION_ATTR_SET_MASKED      : execute_masked_set_action(skb, key, nla_data(a));
    OVS_ACTION_ATTR_SET_TO_MASKED   : execute_masked_set_action(skb, key, nla_data(a));
    OVS_ACTION_ATTR_SAMPLE:         : sample(dp, skb, key, a, attr, len);

--------------------------------------------------------------

static int output_userspace(struct datapath *dp, struct sk_buff *skb,
			    struct sw_flow_key *key, const struct nlattr *attr,
			    const struct nlattr *actions, int actions_len)

初始化 upcall, 向用户空间发送 upcall 信息, 具体如下:

	struct dp_upcall_info upcall;
    upcall.cmd = OVS_PACKET_CMD_ACTION
    遍历 attr 的每个元素 a(显然这里的 attr 是一个内嵌 nla 属性), 如果 nla_type(a)

    OVS_USERSPACE_ATTR_USERDATA         : upcall.userdata = a;
    OVS_USERSPACE_ATTR_PID              : upcall.portid   = nla_get_u32(a)
	OVS_USERSPACE_ATTR_EGRESS_TUN_PORT  : upcall.egress_tun_info = info
	OVS_USERSPACE_ATTR_ACTIONS          : upcall.actions  = actions
                                          upcall.actions_len = actions_len;
    (info 来源于ovs_vport_get_egress_tun_info(vport, skb, &info))

	return ovs_dp_upcall(dp, skb, key, &upcall);

--------------------------------------------------------------

static void execute_hash(struct sk_buff *skb, struct sw_flow_key *key,
			 const struct nlattr *attr)
    初始化 key->ovs_flow_hash = jhash_1word(skb_get_hash(skb))

--------------------------------------------------------------

static int execute_recirc(struct datapath *dp, struct sk_buff *skb,
			  struct sw_flow_key *key,
			  const struct nlattr *a, int rem)

    待理解
--------------------------------------------------------------

static int execute_set_action(struct sk_buff *skb,
			      struct sw_flow_key *flow_key,
			      const struct nlattr *a)

    skb->cb->egress_tun_info = nal_data(a)


--------------------------------------------------------------

static int execute_masked_set_action(struct sk_buff *skb,
				     struct sw_flow_key *flow_key,
				     const struct nlattr *a)


    用 a 对应的值赋值给 flow_key
    判断 nla_type(a)

    //其中 nla_mask(a) 紧邻 nla_data(a) 之后存放, 而且 nla_mask(a) 与 nla_data(a) 类型完全一致, 因此可以做好掩码
	OVS_KEY_ATTR_PRIORITY
                            skb->priority = (nla_data(a) | skb->priority & nla_mask(a))
                            flow_key->phy.priority = skb->priority;
	OVS_KEY_ATTR_SKB_MARK
                            skb->mask = (nla_data(a) | skb->priority & nla_mask(a))
                            flow_key->phy.skb_mark = skb->mark

	OVS_KEY_ATTR_TUNNEL_INFO: err
	OVS_KEY_ATTR_ETHERNET   : set_eth_addr(skb, flow_key, nla_data(a), get_mask(a, struct ovs_key_ethernet *))
    OVS_KEY_ATTR_IPV4       : set_ipv4(skb, flow_key, nla_data(a), get_mask(a, struct ovs_key_ipv4 *))
    OVS_KEY_ATTR_IPV6       : set_ipv(skb, flow_key, nla_data(a), get_mask(a, struct ovs_key_ipv6 *))
    OVS_KEY_ATTR_TCP        : set_tcp(skb, flow_key, nla_data(a), get_mask(a, struct ovs_key_tcp *));
    OVS_KEY_ATTR_UDP        : set_udp(skb, flow_key, nla_data(a), get_mask(a, struct ovs_key_udp *));
    OVS_KEY_ATTR_SCTP       : set_sctp(skb, flow_key, nla_data(a), get_mask(a, struct ovs_key_sctp *));
    OVS_KEY_ATTR_MPLS       : set_mpls(skb, flow_key, nla_data(a), get_mask(a, __be32 *));




--------------------------------------------------------------

static int set_eth_addr(struct sk_buff *skb, struct sw_flow_key *flow_key,
			const struct ovs_key_ethernet *key,
			const struct ovs_key_ethernet *mask)

    //校验和
    skb->csum = csum_sub(skb->csum, csum_partial(start, len, 0));

    eth_hdr(skb)->h_source = key->eth_src & ~mask->eth_src
    eth_hdr(skb)->h_dest = key->eth_dst & ~mask->eth_dst

    //重新计算 skb->csum
    skb->csum = csum_add(skb->csum, csum_partial(start, len, 0))

    flow_key->eth_src = eth_hdr(skb)->h_source
    flow_key->eth_dst = eth_hdr(skb)->h_dest

--------------------------------------------------------------

static int set_ipv4(struct sk_buff *skb, struct sw_flow_key *flow_key,
		    const struct ovs_key_ipv4 *key,
		    const struct ovs_key_ipv4 *mask)

    #define MASKED(OLD, KEY, MASK) ((KEY) | ((OLD) & ~(MASK)))
	nh = ip_hdr(skb);
	new_addr = MASKED(nh->saddr, key->ipv4_src, mask->ipv4_src);

    new_addr = key->ipv4_src | (ip_hdr(skb)->saddr & ~mask->ipv4_src)
    ip_hdr(skb)->saddr = new_addr
    flow_key->ipv4.addr.src = new_addr

    new_addr = key->ipv4_dst | (ip_hdr(skb)->daddr & ~mask->ipv4_dst)
    ip_hdr(skb)->daddr = new_addr
	flow_key->ipv4.addr.dst = new_addr;

    ip_hdr(skb)->tos = key->ipv4_tos | (ip_hdr(skb)->tos & ~mask->ipv4_tos)
	flow_key->ip.tos = ip_hdr(skb)->tos;
	flow_key->ip.ttl = ip_hdr(skb)->ttl;

--------------------------------------------------------------

static int set_tcp(struct sk_buff *skb, struct sw_flow_key *flow_key,
		   const struct ovs_key_tcp *key,
		   const struct ovs_key_tcp *mask)

    tcp_hdr(skb)->source = key->tcp_src | (tcp_hdr(skb)->source & ~mask->tcp_src)
    flow_key->tp.src = tcp_hdr(skb)->source

    tcp_hdr(skb)->dest = key->tcp_dst | (tcp_hdr(skb)->dest & ~mask->tcp_dst)
    flow_key->tp.src = tcp_hdr(skb)->dest

--------------------------------------------------------------
static int sample(struct datapath *dp, struct sk_buff *skb,
		  struct sw_flow_key *key, const struct nlattr *attr,
		  const struct nlattr *actions, int actions_len)

    attr 是内嵌的 actions 内嵌的 nlattr

	const struct nlattr *acts_list = NULL;

    遍历 attr 的每个元素 a
    判断 nla_type(a)
    OVS_SAMPLE_ATTR_PROBABILITY :
    OVS_SAMPLE_ATTR_ACTIONS     :  acts_list = a

    判断 nla_type(nla_data(acts_list))
    OVS_ACTION_ATTR_USERSPACE   output_userspace(dp, skb, key, a, actions, actions_len);

--------------------------------------------------------------

struct ovs_gso_cb {
	struct ovs_skb_cb dp_cb;
	gso_fix_segment_t fix_segment;
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,11,0)
	__be16		inner_protocol;
#endif
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	unsigned int	inner_mac_header;
#endif
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,8,0)
	unsigned int	inner_network_header;
#endif
};
#define OVS_GSO_CB(skb) ((struct ovs_gso_cb *)(skb)->cb)

--------------------------------------------------------------

/**
 * struct ovs_skb_cb - OVS data in skb CB
 * @egress_tun_info: Tunnel information about this packet on egress path.
 * NULL if the packet is not being tunneled.
 * @input_vport: The original vport packet came in on. This value is cached
 * when a packet is received by OVS.
 */
struct ovs_skb_cb {
	struct ovs_tunnel_info  *egress_tun_info;
	struct vport		*input_vport;
};
#define OVS_CB(skb) ((struct ovs_skb_cb *)(skb)->cb)

--------------------------------------------------------------

void ovs_vport_receive(struct vport *vport, struct sk_buff *skb,
		       const struct ovs_tunnel_info *tun_info)

	OVS_CB(skb)->input_vport = vport;
	OVS_CB(skb)->egress_tun_info = NULL;
	ovs_flow_key_extract(tun_info, skb, &key);
	ovs_dp_process_packet(skb, &key);

--------------------------------------------------------------

int ovs_flow_key_extract(const struct ovs_tunnel_info *tun_info, struct sk_buff *skb, struct sw_flow_key *key)

    如果 tun_info 不为 null
        key->tun_key = tun_info->tunnel
        key->tun_opts = tun_info->options
        key->tun_opts_len = tun_info->options_len

    key->tun_key = {0}
	key->tun_opts_len = 0;
	key->phy.priority = skb->priority;
	key->phy.in_port = OVS_CB(skb)->input_vport->port_no;
	key->phy.skb_mark = skb->mark;
	key->ovs_flow_hash = 0;
	key->recirc_id = 0;
    其余见 key_extract()

--------------------------------------------------------------
static int key_extract(struct sk_buff *skb, struct sw_flow_key *key)

    此时 skb->data 必须指向 eth 头

    key->tp.flas = 0;
    eth = ethhdr(skb->head + skb->data)
    key->eth.src = eth->h_source
    key->eth.dst = eth->h_dest

    #define ETH_P_8021Q     0x8100

    key->eth.tci = 0 或 0x1000

    如果是 802.3 #define ETH_P_802_3     0x0001
        key->eth.type = (__be16)skb->data

    如果是 LLC 并且 LLC ethertype 为 802.3
        key->eth.type = (__be16)skb->data
    否则 #define ETH_P_802_2     0x0004
        key->eth.type = 0 或 0x0004

    //IPV4
    key->ipv4.addr.src = nh->saddr
	key->ipv4.addr.dst = nh->daddr;
	key->ip.proto = nh->protocol;
	key->ip.tos = nh->tos;
	key->ip.ttl = nh->ttl;
    key->ip.frag = OVS_FRAG_TYPE_FIRST 或 OVS_FRAG_TYPE_LATER 或 OVS_FRAG_TYPE_NONE
    //TCP
    key->tp.src = tcp->source
    key->tp.dst = tcp->dest
    key->tp.flags = tcp->words[3] & htons(0x0FFF)
    //UDP
    key->tp.src = udp->source
    key->tp.dst = udp->dest
    //SCTP
    key->tp.src = sctp->source
    key->tp.dst = sctp->dest
    //ICMP
    key->tp.src = htons(icmp->type)
    key->tp.dst = htons(icmp->code)

    //ARP RARP
    key->ip.proto = ntohs(arp->ar_op) 或 0
    key->ipv4.addr.src = arp->ar_sip
    key->ipv4.addr.dst = arp->ar_tip
    key->ipv4.arp.sha  = arp->ar_sha
    key->ipv4.arp.tha  = arp->ar_tha


--------------------------------------------------------------

#define VLAN_CFI_MASK           0x1000 /* Canonical Format Indicator */
#define VLAN_TAG_PRESENT        VLAN_CFI_MASK
#define skb_vlan_tag_present(__skb)     ((__skb)->vlan_tci & VLAN_TAG_PRESENT)

如果包含 VLAN, skb_vlan_tag_present 就不会为 0, 也即 skb->vlan_tci = 0x1000

-------------------------------------------------------------

-------------------------------------------------------------
struct sw_flow *ovs_flow_tbl_lookup_stats(struct flow_table *tbl,
					  const struct sw_flow_key *key,
					  u32 skb_hash,
					  u32 *n_mask_hit)

     skb_hash 唯一鉴别一条 flow, 不同的 flow 应该有不同的 hash, 相同的 flow 应该有相同的 hash

    如果 skb_hash = 0
	return flow_lookup(tbl, ti, ma, key, n_mask_hit, &mask_index);

    否则 先查 CPU 缓存, 再查内核缓存
        entries = tbl->mask_cache
        取 skb_hash 每个字节的低两位为 index
        如果 entries[index] = skb_hash 这 entries 是每个 CPU 缓存的流表; return flow_lookup(tbl, ti, ma, key, 0,&e->mask_index);
        否则 ce = (e->skb_hash 最小值) flow = flow_lookup(tbl, ti, ma, key, 0, &ce->mask_index);

-------------------------------------------------------------
static struct sw_flow *flow_lookup(struct flow_table *tbl,
				   struct table_instance *ti,
				   const struct mask_array *ma,
				   const struct sw_flow_key *key,
				   u32 *n_mask_hit,
				   u32 *index)

    充分利用 CPU 缓存
    如果 index < ma->max;  返回 masked_flow_lookup(ti, key, ma->mask[*index], n_mask_hit)
    否则 遍历 ma 数组所有元素 i, 如果 ma->masks[i] != 0; 返回 masked_flow_lookup(ti, key, ma->mask[i], n_mask_hit)

-------------------------------------------------------------
static struct sw_flow *masked_flow_lookup(struct table_instance *ti,
					  const struct sw_flow_key *unmasked,
					  const struct sw_flow_mask *mask,
					  u32 *n_mask_hit)

	struct sw_flow *flow;
	struct sw_flow_key masked_key;
	struct hlist_head *head;

    //从 mask unmasked 获取 masked_key
	ovs_flow_mask_key(&masked_key, unmasked, mask);

    //找到 ti 合适的 bucket
    hash = jhash2(masked_key+mask->range->start, (mask->ranger->end - mask->ranger->start)>>2, 0)
	head = flex_array_get(ti->buckets, jhash_1word(hash, ti->hash_seed) & (ti->n_buckets - 1));

    //遍历 ti 的每个 bucket 中的每条 sw_flow 直到找到满足如下条件的 flow
	hlist_for_each_entry_rcu(flow, head, flow_table.node[ti->node_ver])
		if (flow->mask == mask && flow->flow_table.hash == hash &&
		    flow_cmp_masked_key(flow, &masked_key, &mask->range))
			return flow;

-------------------------------------------------------------

void ovs_flow_mask_key(struct sw_flow_key *dst, const struct sw_flow_key *src,
		       const struct sw_flow_mask *mask)
    通过 mask->key 和 src 逻辑运算与, 获取 dst

-------------------------------------------------------------

static u32 flow_hash(const struct sw_flow_key *key,
		     const struct sw_flow_key_range *range)
    通过　jhash2 计算 hash
    jhash2(key+range->start, (ranger->end - ranger->start)>>2, 0)

-------------------------------------------------------------

static struct hlist_head *find_bucket(struct table_instance *ti, u32 hash)

	return flex_array_get(ti->buckets, jhash_1word(hash, ti->hash_seed) & (ti->n_buckets - 1));

-------------------------------------------------------------

## 各个文件的源码解析

### datapath.c

const char *ovs_dp_name(const struct datapath *dp)

    即 dp 中类型为 OVSP_LOCAL 的 vport->ops->get_name(vport)

static int get_dpifindex(const struct datapath *dp)

    dp 中 OVSP_LOCAL 对应 vport, 与 vport 关联的物理网卡的 ifindex

static void destroy_dp_rcu(struct rcu_head *rcu)

    销毁 rcu 对应的 datapath 的内存

static struct hlist_head *vport_hash_bucket(const struct datapath *dp, u16 port_no)

    返回 dp->ports[port_no & (DP_VPORT_HASH_BUCKETS - 1)];

struct vport *ovs_lookup_vport(const struct datapath *dp, u16 port_no)

    先定位 bucket, 然后遍历 bucket 找到对应的 vport

static struct vport *new_vport(const struct vport_parms *parms)

    先创建 vport, 之后将 vport 加入 datapath 的 ports 中

    1. 将 vport->hash_node 加入 dev_table
    2. vport->dp_hash_node 加入 dp->ports[vport->port_no & (DP_VPORT_HASH_BUCKETS - 1)]

void ovs_dp_detach_port(struct vport *p)

    将 vport 与 datapath 解除关系, 之后释放 vport 内存

void ovs_dp_process_packet(struct sk_buff *skb, struct sw_flow_key *key)

    从 skb 找到对应的 datapath, 查询 datapath->table 找到 key 对应的 flow.
    if (!flow) 发送到用户态
    else       执行对应的 action

int ovs_dp_upcall(struct datapath *dp, struct sk_buff *skb, const struct sw_flow_key *key, const struct dp_upcall_info *upcall_info)

    如果 gso 使能, offload 到硬件, 之后发送给用户态, 否则直接发送给用户态

static int queue_gso_packets(struct datapath *dp, struct sk_buff *skb, const struct sw_flow_key *key, const struct dp_upcall_info *upcall_info)

    将 skb 分片, 之后发送给用户态

static int queue_userspace_packet(struct datapath *dp, struct sk_buff *skb, const struct sw_flow_key *key, const struct dp_upcall_info *upcall_info)

    将 skb 以 netlink 方式发送给用户态

static int ovs_packet_cmd_execute(struct sk_buff *skb, struct genl_info *info)

    解析 info 将 skb 执行给定的 action

static void get_dp_stats(const struct datapath *dp, struct ovs_dp_stats *stats, struct ovs_dp_megaflow_stats *mega_stats)

    获取 datapath 的统计信息

static bool should_fill_key(const struct sw_flow_id *sfid, uint32_t ufid_flags)

	return ovs_identifier_is_ufid(sfid) && !(ufid_flags & OVS_UFID_F_OMIT_KEY);

static bool should_fill_mask(uint32_t ufid_flags)

	return !(ufid_flags & OVS_UFID_F_OMIT_MASK);

static bool should_fill_actions(uint32_t ufid_flags)

	return !(ufid_flags & OVS_UFID_F_OMIT_ACTIONS);

static int ovs_flow_cmd_fill_stats(const struct sw_flow *flow, struct sk_buff *skb)

    聚合所有 CPU 中 flow 的统计信息加入到 skb 中

static int ovs_flow_cmd_fill_actions(const struct sw_flow *flow, struct sk_buff *skb, int skb_orig_len)

    将 flow->sf_acts 加入到 skb

static int ovs_flow_cmd_fill_info(const struct sw_flow *flow, int dp_ifindex, struct sk_buff *skb, u32 portid, u32 seq, u32 flags, u8 cmd, u32 ufid_flags)

    构造一条 netlink 信息, 即将 flow 的各个属性加入 skb.

static struct sk_buff *ovs_flow_cmd_alloc_info(const struct sw_flow_actions *acts, const struct sw_flow_id *sfid, struct genl_info *info, bool always, uint32_t ufid_flags)

    根据输入参数生成一条单播 netlink 消息. 返回该消息.

static struct sk_buff *ovs_flow_cmd_build_info(const struct sw_flow *flow, int dp_ifindex, struct genl_info *info, u8 cmd, bool always, u32 ufid_flags)

    根据输入参数生成一条单播 netlink 消息. 并填充消息体, 返回该消息.

static int ovs_flow_cmd_new(struct sk_buff *skb, struct genl_info *info)

    1. 为新建流表项 new_flow 分配内存空间
    2. 初始化临时变量 match, key, mask, match->key = key, match->mask=mask
    3. a[OVS_FLOW_ATTR_KEY] 初始化 match->key, a[OVS_FLOW_ATTR_MASK] 初始化 match->mask
    4. 将 match->key 与 match->mask 掩码后的赋值给 new_flow->key
    5. 如果 a[OVS_FLOW_ATTR_UFID] 不为空, 用 a[OVS_FLOW_ATTR_UFID] 初始化 new_flow->id, 否则 flow->unmasked_key = match->key
    6. 用 a[OVS_FLOW_ATTR_ACTIONS] 初始化 acts
    7. 如果 new_flow->id->ufid_len != 0, 从 dp->table->ufid_ti->buckets 中查找 new_flow->id->ufid 对应的流表是否存在
    8. 如果 new_flow->id->ufid_len == 0, 遍历 dp->table->mask_array 中的每一个 mask, 从 dp->table->ti->buckets 中查找匹配 flow->key=key & mask, flow->mask = mask 的流表项
    9. 正常情况下, 新创建的流表是不存在的:
         * 将 mask 加入 table->mask_array 中
         * 将 flow->flow_table->node[table->ti->node_ver] 插入 table->ti->buckets 中的一个链表中
         * 如果 flow->id->ufid_len != 0 , 将 flow->ufid_table->node[table->ufid_ti->node_ver] 插入 table->ufid_ti->buckets 中的一个链表中
    10. 异常情况是, 新创建的流表已经存在
         * 如果配置中不允许重复的流表, 向发送者发送错误消息
         * 如果配置允许重复的流表, 如果是 ufid 重复, 发送错误消息, 如果是 key 重复, 简单的用新的 action 代替原来的 action

    解析 info 生成一条 flow, 在 dp->table 中查找是否存在对应的 flow,
    如果不存在, 将该 flow 加入 dp 的 table 中;
    如果存在, 用新的 actions 替代旧的 actions

    将 flow->flow_table->node[table->ti->node_ver] 插入 dp->table->ti->buckets
    将 flow->ufid_table->node[table->ufid_ti->node_ver] 插入 dp->table->ufid_ti->buckets


static struct sw_flow_actions *get_flow_actions(const struct nlattr *a, const struct sw_flow_key *key, const struct sw_flow_mask *mask, bool log)

    解析 a 中获取 action, 并返回该 action

static int ovs_flow_cmd_set(struct sk_buff *skb, struct genl_info *info)

    解析 info, 从 dp->table 的 ufid 表或全局查找对应的 flow, 用新的 action 代替旧的 action

static int ovs_flow_cmd_get(struct sk_buff *skb, struct genl_info *info)

    解析 info, 从 dp->table 的 ufid 表或全局查找对应的 flow

static int ovs_flow_cmd_del(struct sk_buff *skb, struct genl_info *info)

    解析 info, 从 dp->table 的 ufid 表或全局查找对应的 flow, 将 flow 与
    dp->table 解除关系, 并是否 flow 对应的内存

    1. 从 table->ti->bucket 中删除 flow->flow_table.node[table->ti->node_ver]
    2. 从 table->ufid_ti->bucket 中删除 flow->ufid_table.node[table->ufid_ti->node_ver]

static int ovs_flow_cmd_dump(struct sk_buff *skb, struct netlink_callback *cb)

    从 skb->sk->net, genlmsg_data(nlmsg_data(cb->nlh))->dp_ifindex 找到 dp,
    遍历 dp->table->ti->buckets, bucket 从 cb->args[0] 开始, 每个 bucket
    的索引从 cb->args[1] 开始, 直到遍历完所有的 flow, 每个 flow 都加入 skb

static size_t ovs_dp_cmd_msg_size(void)

    计算 datapath 的 netlink 消息体大小

static int ovs_dp_cmd_fill_info(struct datapath *dp, struct sk_buff *skb, u32 portid, u32 seq, u32 flags, u8 cmd)

    解析参数, 将 datapath 的相关属性加入 netlink 消息对应的 skb.

static struct sk_buff *ovs_dp_cmd_alloc_info(struct genl_info *info)

    生成一个 netlink 消息.

static struct datapath *lookup_datapath(struct net *net, const struct ovs_header *ovs_header, struct nlattr *a[OVS_DP_ATTR_MAX + 1])

    解析 a 找到对应的 datapath 并返回

static void ovs_dp_reset_user_features(struct sk_buff *skb, struct genl_info *info)

    找到对应的 datapath, 并设置 datapath->user_features = 0;

static void ovs_dp_change(struct datapath *dp, struct nlattr *a[])

    用 a[OVS_DP_ATTR_USER_FEATURES] 设置 dp->user_features

static int ovs_dp_cmd_new(struct sk_buff *skb, struct genl_info *info)

    解析 info 构造一个 datapath, 并初始化 datapath 的各个数据成员

static void __dp_destroy(struct datapath *dp)

    删除 datapath 并释放其内存

static int ovs_dp_cmd_del(struct sk_buff *skb, struct genl_info *info)

    通过 skb->sk->net info->userhdr, info->attrs 找到待删除的 dp
    销毁 dp 下的每个端口, 向发送者通知删除操作

static int ovs_dp_cmd_set(struct sk_buff *skb, struct genl_info *info)

    通过 skb, info 找到对应的 datapath, 修改其 user_features

    如果 info->attrs[OVS_DP_ATTR_NAME] = NULL
    遍历 skb->sk-net->dev_index_head[info->userhdr->ifindex & (NETDEV_HASHENTRIES - 1)] 所有元素,
    找到 dev->ifindex = ifindex 的 dev, 返回 netdev_priv(dev)->vport->dp

    否则
    遍历 dev_table[jhash(name, strlen(name), (unsigned long) net) & (VPORT_HASH_BUCKETS - 1)] 的所有 vport,
    找到 vport->ops->get_name(vport）= name, vport->dp->net = net 的 vport, 返回 vport->dp

static int ovs_dp_cmd_dump(struct sk_buff *skb, struct netlink_callback *cb)

    遍历 skb->sk->net->gen->ptr[ovs_net_id -1]->dps 中所有 dp, 将索引大于 cb->agrs[0] 的统计加入 skb

static int ovs_vport_cmd_fill_info(struct vport *vport, struct sk_buff *skb, u32 portid, u32 seq, u32 flags, u8 cmd)

    解析参数, 将 vport 的属性加入 skb.

static struct sk_buff *ovs_vport_cmd_alloc_info(void)

    初始化一个 netlink 消息

struct sk_buff *ovs_vport_cmd_build_info(struct vport *vport, u32 portid, u32 seq, u8 cmd)

    解析参数, 将 vport 的属性加入 netlink 消息. 返回该 netlink 消息

static struct vport *lookup_vport(struct net *net, const struct ovs_header *ovs_header, struct nlattr *a[OVS_VPORT_ATTR_MAX + 1])

    从 net,name 找到 dp, 进而找到 vport
        bucket = dev_table[jhash(name, strlen(name), (unsigned long) net) & (VPORT_HASH_BUCKETS - 1)]
        找到 name = vport->ops->get_name(vport) 并且　vport->dp->net = net 的 vport
    从 net,dpifindex 找到 dp, 进而找到 vport
        遍历 net->dev_index_head[ifindex & (NETDEV_HASHENTRIES - 1)] 所有元素,
        找到 dev->ifindex = ifindex 的 dev, 返回netdev_priv(dev)->vport->dp

static int ovs_vport_cmd_new(struct sk_buff *skb, struct genl_info *info)

    1. 从 skb->sk->net, ovs_header->dp_ifindex 定位到 datapath
    2. 如果没有给定端口号, 在 datapath 中从头开始找到空闲的端口号 port_no.
       如果给定端口号, 确保端口号 port_no 与已有的端口号 port_no 不冲突.
    3. 创建一个 vport 并初始化各个数据成员, 包括私有数据
    4. 如果端口创建成功, 将其加入 parms->dp->ports 中
    5. 将信息应答给请求者(vswitchd)

static int ovs_vport_cmd_set(struct sk_buff *skb, struct genl_info *info)

    从 net,name 找到 dp, 进而找到 vport 或 从 net,dpifindex 找到 dp, 进而找到 vport
    设置 vport 的属性, 包括:

    OVS_VPORT_ATTR_OPTIONS : info->attrs[OVS_VPORT_ATTR_OPTIONS]
    OVS_VPORT_ATTR_UPCALL_PID : info->attrs[OVS_VPORT_ATTR_UPCALL_PID]

static int ovs_vport_cmd_del(struct sk_buff *skb, struct genl_info *info)

    1. 从 net,name 找到 dp, 进而找到 vport 或 从 net,dpifindex 找到 dp, 进而找到 vport
    2. 删除 vport (OVSP_LOCAL 的端口不可以删除)
    3. 发送消息给发送者(vswitchd)

static int ovs_vport_cmd_get(struct sk_buff *skb, struct genl_info *info)

    从 net,name 找到 dp, 进而找到 vport 或 从 net,dpifindex 找到 dp, 进而找到 vport
    获取指定 vport 的属性信息, 应答给请求者(vswitchd)

static int ovs_vport_cmd_dump(struct sk_buff *skb, struct netlink_callback *cb)

    从数字 dp->ports[] 索引 cb->agrs[0] 开始, 跳过前 cb->args[1] 个 vport,
    将剩余的 vport 属性信息写入 skb

static void dp_unregister_genl(int n_families)

	for (i = 0; i < n_families; i++)
		genl_unregister_family(dp_genl_families[i]);

static int dp_register_genl(void)

	for (i = 0; i < ARRAY_SIZE(dp_genl_families); i++)
		genl_register_family(dp_genl_families[i]);

static int __net_init ovs_init_net(struct net *net)

    用 net->gen->ptr[ovs_net_id - 1] 初始化结构体 ovs_net

    1. 定义 ovs_net 指向 net->gen->ptr[ovs_net_id - 1]
    2. 初始化双向链表 ovs_net->dps
    3. 初始化 ovs_net->dp_notify_work

	INIT_WORK(&ovs_net->dp_notify_work, ovs_dp_notify_wq);
    其中 3:
        ovs_net->dp_notify_work->data = WORK_STRUCT_NO_POOL
        初始化双向循环链表 ovs_net->dp_notify_work->entry
        ovs_net->dp_notify_work->func = ovs_dp_notify_wq

    注: 没有初始化 ovs_net-> vport_net

static void __net_exit list_vports_from_net(struct net *net, struct net *dnet, struct list_head *head)

    遍历 vport = net->gen->ptr[ovs_net_id-1]->dps[i]->vport[j]
    如果 vport->ops->type != OVS_VPORT_TYPE_INTERNAL && netdev_vport_priv(vport)->dev->net = dnet
    将 vport->detach_list 加入 head


static void __net_exit ovs_exit_net(struct net *dnet)

    1. 遍历 dnet->gen->ptr[ovs_net_id - 1]->dps, 释放每一个 dps
    2. 遍历系统 net_namespace_list 中所有的命名空间对应的网络 struct net,
    遍历每个网络 net->gen->ptr[ovs_net_id - 1]->dps 中每个 dps 中的每个 vport,
    如果 vport->ops->type != OVS_VPORT_TYPE_INTERNAL && netdev_vport_priv(vport)->dev->net = dnet
    将 vport->deatch_list 增加到一个链表 head 中, 然后遍历 head 链表, 销毁对应的 vport.
    4. 取消 net->gen->ptr[ovs_net_id - 1]->dp_notify_work

    其中 3 包括:
    将 vport->deatch_list 从其对应的链表中删除;
    将 vport->dp_hash_node 从其对应的链表中删除;
    将 vport->hash_node 从其对应的链表中删除;
    递减 vport->ops->owner 的引用计数
    调用 vport->ops->destory(vport) 将其自身销毁

----------------------------------------------------------------------------

### flow.h

static inline bool ovs_identifier_is_ufid(const struct sw_flow_id *sfid)

	return sfid->ufid_len;

static inline bool ovs_identifier_is_key(const struct sw_flow_id *sfid)

	return !sfid->ufid_len;

### flow.c

u64 ovs_flow_used_time(unsigned long flow_jiffies)

    当前时间减去　flow_jiffies 对应的时间, 单位 ms

void ovs_flow_stats_update(struct sw_flow *flow, __be16 tcp_flags, const struct sk_buff *skb)

    更新 flow->stats[numa_node_id()] 的状态

void ovs_flow_stats_get(const struct sw_flow *flow, struct ovs_flow_stats *ovs_stats, unsigned long *used, __be16 *tcp_flags)

    将 flow 各个节点的状态聚合之后赋值给 ovs_stats 和 tcp_flags

void ovs_flow_stats_clear(struct sw_flow *flow)

    清除 flow 各个节点的状态

static int check_header(struct sk_buff *skb, int len)

    检查 skb 是否可以容纳 len 的数据

static bool arphdr_ok(struct sk_buff *skb)

    检查 skb 是否可以容纳 arp 包头

static int check_iphdr(struct sk_buff *skb)

    检查 skb 是否可以容纳 ip 头

static bool tcphdr_ok(struct sk_buff *skb)

    检查 skb 是否可以容纳 tcp 头

static bool udphdr_ok(struct sk_buff *skb)

    检查 skb 是否可以容纳 udp 头

static bool sctphdr_ok(struct sk_buff *skb)

    检查 skb 是否可以容纳 sctp 头

static bool icmphdr_ok(struct sk_buff *skb)

    检查 skb 是否可以容纳 icmp 头

static int parse_ipv6hdr(struct sk_buff *skb, struct sw_flow_key *key)

    解析 skb 的 ipv6 头, 初始化 key

static bool icmp6hdr_ok(struct sk_buff *skb)

    检查 skb 是否可以容纳 icmp6 头

static int parse_vlan(struct sk_buff *skb, struct sw_flow_key *key)

    解析 skb vlan 头, 初始化 key

static __be16 parse_ethertype(struct sk_buff *skb)

    解析网卡头

static int parse_icmpv6(struct sk_buff *skb, struct sw_flow_key *key, int nh_len)

    解析 skb 中的 icmpv6, 初始化　key

static int key_extract(struct sk_buff *skb, struct sw_flow_key *key)

    从 skb 中提取包信息初始化 key

        key->eth.src
        key->eth.dst
        key->ipv4.addr.src
        key->ipv4.addr.dst
        key->ip.proto
        key->ip.tos
        key->ip.ttl
        key->tp.src
        key->tp.dst
        key->tp.flags

int ovs_flow_key_update(struct sk_buff *skb, struct sw_flow_key *key)

    从 skb 中提取包信息初始化 key

    在 execute_recirc 中使用

int ovs_flow_key_extract_userspace(const struct nlattr *attr, struct sk_buff *skb, struct sw_flow_key *key, bool log)

    解析 attr 填充 key 的物理链路层属性, 解析 skb 填充 key 数据链路层以上的属性

    在 ovs_packet_cmd_execute 中使用

-------------------------------------------------------------------------

### flow_netlink.c

static bool match_validate(const struct sw_flow_match *match, u64 key_attrs, u64 mask_attrs)

其中:
    key_expected : 记录 match->key 出现的 ovs_key_attr
    mask_allowed : 如果 match->mask 对应 ovs_key_attr 全为 1, 设置对应的 mask_allowed 为 1

之后, 比较

	if ((key_attrs & key_expected) != key_expected) || ((mask_attrs & mask_allowed) != mask_attrs)
        return false
    else
        return true

static int __parse_flow_nlattrs(const struct nlattr *attr, const struct nlattr *a[], u64 *attrsp, bool nz)
static int __parse_flow_nlattrs(const struct nlattr *attr, const struct nlattr *a[], u64 *attrsp, bool log, bool nz)

    遍历 attr 所有 nla, 初始化 a

    其中 attrsp 记录出现的所有属性 ovs_key_attr, 如果出现属性 ovs_key_attr 重复出现, 返回错误

static int parse_flow_mask_nlattrs(const struct nlattr *attr, const struct nlattr *a[], u64 *attrsp)

    遍历 attr 所有 nla, 初始化 a(排除全部为 0 的属性)

    其中 attrsp 记录出现的所有属性 ovs_key_attr, 如果出现属性 ovs_key_attr 重复出现, 返回错误

static int parse_flow_nlattrs(const struct nlattr *attr, const struct nlattr *a[], u64 *attrsp)

    遍历 attr 所有 nla, 初始化 a(包括全部为 0 的属性)

    其中 attrsp 记录出现的所有属性, 如果出现属性重复出现, 返回错误

static int genev_tun_opt_from_nlattr(const struct nlattr *a, struct sw_flow_match *match, bool is_mask, bool log)

    TODO

static int vxlan_tun_opt_from_nlattr(const struct nlattr *a, struct sw_flow_match *match, bool is_mask, bool log)

    TODO


static int ipv4_tun_from_nlattr(const struct nlattr *attr, struct sw_flow_match *match, bool is_mask)
static int ipv4_tun_from_nlattr(const struct nlattr *attr, struct sw_flow_match *match, bool is_mask, bool log)

    遍历 attr 所有 nla
    如果 is_mask 为 true, 初始化 match->mask->key.tun_key;
    如果 is_mask 为 false, 初始化 match->key->tun_key;

        match->key->tun_key.tun_id = a[OVS_TUNNEL_KEY_ATTR_ID]
        match->key->tun_key.ipv4_src = a[OVS_TUNNEL_KEY_ATTR_IPV4_SRC]
        match->key->tun_key.ipv4_dst = a[OVS_TUNNEL_KEY_ATTR_IPV4_DST]
        match->key->tun_key.ipv4_tos = a[OVS_TUNNEL_KEY_ATTR_IPV4_TOS]
        match->key->tun_key.ipv4_ttl = a[OVS_TUNNEL_KEY_ATTR_IPV4_TTL]
        match->key->tun_key.tp_src   = a[OVS_TUNNEL_KEY_ATTR_TP_SRC]
        match->key->tun_key.tp_dst   = a[OVS_TUNNEL_KEY_ATTR_TP_DST]
        match->key->tun_key.tun_flags = TUNNEL_KEY | TUNNEL_DONT_FRAGMENT | TUNNEL_CSUM
                                     | TUNNEL_OAM | TUNNEL_GENEVE_OPT | TUNNEL_VXLAN_OPT

static int vxlan_opt_to_nlattr(struct sk_buff *skb, const void *tun_opts, int swkey_tun_opts_len)

    TODO

static int __ipv4_tun_to_nlattr(struct sk_buff *skb, const struct ovs_key_ipv4_tunnel *output, const void *tun_opts, int swkey_tun_opts_len)

    TODO


static int ipv4_tun_to_nlattr(struct sk_buff *skb, const struct ovs_key_ipv4_tunnel *tun_key, const struct ovs_key_ipv4_tunnel *output)
static int ipv4_tun_to_nlattr(struct sk_buff *skb, const struct ovs_key_ipv4_tunnel *output, const void *tun_opts, int swkey_tun_opts_len)

    将 output 成员加入 netlink 消息 skb 的 nested attribute 中

int ovs_nla_put_egress_tunnel_key(struct sk_buff *skb, const struct ovs_tunnel_info *egress_tun_info)

    TODO

static int metadata_from_nlattrs(struct sw_flow_match *match,  u64 *attrs, const struct nlattr **a, bool is_mask)
static int metadata_from_nlattrs(struct sw_flow_match *match,  u64 *attrs, const struct nlattr **a, bool is_mask, bool log)

    如果 attrs 相关 ovs_key_attr 属性位不为 0, 从 a 中获取对应属性初始化 match, 并将 attrs 相关位清零, 表明该属性已经被解析
    如果 is_mask 为 true, 初始化 match->mask-key 相关属性
    如果 is_mask 为 false, 初始化 match->key 相关属性

    match->key->ovs_flow_hash = a[OVS_KEY_ATTR_DP_HASH]
    match->key->ovs_flow_hash = a[OVS_KEY_ATTR_RECIRC_ID]
    match->key->phy.priority = a[OVS_KEY_ATTR_PRIORITY]
    match->key->phy.in_port = a[OVS_KEY_ATTR_IN_PORT]
    match->key->phy.skb_mark = a[OVS_KEY_ATTR_SKB_MARK]
    match->key->tun_key = ipv4_tun_from_nlattr()

    match->mask->key.ovs_flow_hash = a[OVS_KEY_ATTR_DP_HASH]
    match->mask->key.recirc_id = a[OVS_KEY_ATTR_RECIRC_ID]
    match->mask->key.phy.priority = a[OVS_KEY_ATTR_PRIORITY]
    match->mask->key.phy.in_port = a[OVS_KEY_ATTR_IN_PORT]
    match->mask->key.phy.skb_mark = a[OVS_KEY_ATTR_SKB_MARK]

    match->mask->tun_key = ipv4_tun_from_nlattr(a[OVS_KEY_ATTR_TUNNEL], match, is_mask, log)

static int ovs_key_from_nlattrs(struct sw_flow_match *match, u64 attrs, const struct nlattr **a, bool is_mask)
static int ovs_key_from_nlattrs(struct sw_flow_match *match, u64 attrs, const struct nlattr **a, bool is_mask, bool log)

    用 a 初始化 match;
    其中:
    1. attrs 记录要初始化哪些属性
    2. 如果 is_mask 为 true, 初始化 match->mask->key
    3. 如果 is_mask 为 false, 初始化 match->key


    match->key->eth.src = a[OVS_KEY_ATTR_ETHERNET]->eth_src
    match->key->eth.dst = a[OVS_KEY_ATTR_ETHERNET]->eth_dst
    match->key->eth.tci = a[OVS_KEY_ATTR_VLAN]
    match->key->eth.type = htons(ETH_P_802_2)

    //IPV4
    match->key->ip.proto = a[OVS_KEY_ATTR_IPV4]->ipv4_proto
    match->key->ip.tos = a[OVS_KEY_ATTR_IPV4]->ipv4_tos
    match->key->ip.ttl = a[OVS_KEY_ATTR_IPV4]->ipv4_ttl
    match->key->ip.frag = a[OVS_KEY_ATTR_IPV4]->ipv4_frag
    match->key->ip.addr.src = a[OVS_KEY_ATTR_IPV4]->ipv4_src
    match->key->ip.addr.dst = a[OVS_KEY_ATTR_IPV4]->ipv4_dst

    //IPV6
    match->key->ipv6_key->ipv6_label = a[OVS_KEY_ATTR_IPV6]->ipv6_label
    match->key->ipv6_key->ip.proto = a[OVS_KEY_ATTR_IPV6]->ipv6_proto
    match->key->ip.tos   = a[OVS_KEY_ATTR_IPV6]->ipv6_tclass
    match->key->ip.ttl   = a[OVS_KEY_ATTR_IPV6]->ipv6_hlimit
    match->key->ip.frag  = a[OVS_KEY_ATTR_IPV6]->ipv6_frag
    match->key->ipv6_key->ipv6.addr.src = a[OVS_KEY_ATTR_IPV6]->ipv6_src
    match->key->ipv6_key->ipv6.addr.dst = a[OVS_KEY_ATTR_IPV6]->ipv6_dst

    //ARP
    match->key->ipv4.addr.src = a[OVS_KEY_ATTR_ARP]->arp_sip
    match->key->ipv4.addr.dst = a[OVS_KEY_ATTR_ARP]->arp_tip
    match->key->ip.proto = a[OVS_KEY_ATTR_ARP]->arp_op
    match->key->ipv4.arp.sha = a[OVS_KEY_ATTR_ARP]->arp_sha
    match->key->ipv4.arp.tha = a[OVS_KEY_ATTR_ARP]->arp_tha

    //TCP
    match->key->mpls.top_lse = a[OVS_KEY_ATTR_MPLS]->mpls_lse
    match->key->tp.src = a[OVS_KEY_ATTR_TCP]->tcp_src
    match->key->tp.dst = a[OVS_KEY_ATTR_TCP]->tcp_dst
    match->key->tp.flags = a[OVS_KEY_ATTR_TCP_FLAGS]

    //UDP
    match->key->tp.src = a[OVS_KEY_ATTR_UDP]->udp_src
    match->key->tp.dst = a[OVS_KEY_ATTR_UDP]->udp_dst

    //SCTP
    match->key->tp.src = a[OVS_KEY_ATTR_SCTP]->sctp_src
    match->key->tp.dst = a[OVS_KEY_ATTR_SCTP]->sctp_dst

    //ICMP
    match->key->tp.src = a[OVS_KEY_ATTR_ICMP]->icmp_src
    match->key->tp.dst = a[OVS_KEY_ATTR_ICMP]->icmp_dst

    //ICMPV6
    match->key->tp.src = a[OVS_KEY_ATTR_ICMPV6]->icmpv6_type
    match->key->tp.dst = a[OVS_KEY_ATTR_ICMPV6]->icmpv6_code

    //
    match->key->ipv6.nd.target = a[OVS_KEY_ATTR_ND]->nd_target
    match->key->ipv6.nd.ssl = a[OVS_KEY_ATTR_ND]->nd_sll
    match->key->ipv6.nd.tll = a[OVS_KEY_ATTR_ND]->nd_tll

    match->mask->key.eth.src = a[OVS_KEY_ATTR_ETHERNET]->eth_src
    match->mask->key.eth.dst = a[OVS_KEY_ATTR_ETHERNET]->eth_dst
    match->mask->key.eth.tci = a[OVS_KEY_ATTR_VLAN]
    match->mask->key.eth.type = htons(0xffff)
    match->mask->key.ip.proto = a[OVS_KEY_ATTR_IPV4]->ipv4_proto
    match->mask->key.ip.tos = a[OVS_KEY_ATTR_IPV4]->ipv4_tos
    match->mask->key.ip.ttl = a[OVS_KEY_ATTR_IPV4]->ipv4_ttl
    match->mask->key.ip.frag = a[OVS_KEY_ATTR_IPV4]->ipv4_frag
    match->mask->key.ip.addr.src = a[OVS_KEY_ATTR_IPV4]->ipv4_src
    match->mask->key.ip.addr.dst = a[OVS_KEY_ATTR_IPV4]->ipv4_dst

    match->key->ovs_flow_hash = a[OVS_KEY_ATTR_DP_HASH]
    match->key->ovs_flow_hash = a[OVS_KEY_ATTR_RECIRC_ID]
    match->key->phy.priority = a[OVS_KEY_ATTR_PRIORITY]
    match->key->phy.in_port = a[OVS_KEY_ATTR_IN_PORT]
    match->key->phy.skb_mark = a[OVS_KEY_ATTR_SKB_MARK]
    match->key->tun_key = ipv4_tun_from_nlattr()

    match->mask->key.ovs_flow_hash = a[OVS_KEY_ATTR_DP_HASH]
    match->mask->key.recirc_id = a[OVS_KEY_ATTR_RECIRC_ID]
    match->mask->key.phy.priority = a[OVS_KEY_ATTR_PRIORITY]
    match->mask->key.phy.in_port = a[OVS_KEY_ATTR_IN_PORT]
    match->mask->key.phy.skb_mark = a[OVS_KEY_ATTR_SKB_MARK]

    match->mask->tun_key = ipv4_tun_from_nlattr(a[OVS_KEY_ATTR_TUNNEL], match, is_mask, log)


static void nlattr_set(struct nlattr *attr, u8 val, const struct ovs_len_tbl *tbl)

    TODO

static void mask_set_nlattr(struct nlattr *attr, u8 val)

    TODO


static void sw_flow_mask_set(struct sw_flow_mask *mask, struct sw_flow_key_range *range, u8 val)

    用 val 初始化 mask->range->start 到 mask->range->end

int ovs_nla_get_match(struct sw_flow_match *match, const struct nlattr *key, const struct nlattr *mask)
int ovs_nla_get_match(struct sw_flow_match *match, const struct nlattr *nla_key, const struct nlattr *nla_mask, bool log)

    1. 遍历 key 所有 nla, 保存到临时数组 a (包括全部为 0 的属性)中, 之后用 a 初始化 match->key
    2. 如果 mask 不为 NULL, 遍历 mask 所有 nla, 保存到临时数组 a (包括全部为 0 的属性)中, 之后用 a 初始化 match->mask->key
    3. 如果 mask 为 NULL, 设置 match->mask 从 match->range->start 到 match->range->end 每个字节为 ff
    4. 校验 match

    实际
    a[OVS_FLOW_ATTR_KEY] 初始化 match->key, a[OVS_FLOW_ATTR_MASK] 初始化 match->mask
    1. 解析 a[OVS_FLOW_ATTR_KEY] 保存在中间变量 tmp_key 中, 已经解析的 ovs_key_attr 标记保存在变量 key_attrs
    2. 将 key_attrs 中对应的 ovs_key_attr 从 tmp_key 中取出来赋值给 match->key
    3. 解析 a[OVS_FLOW_ATTR_MASK] 保存在中间变量 tmp_mask 中, 已经解析的 ovs_key_attr 标记保持变量 mask_attrs
    4. 将 mask_attrs 中对应的 ovs_key_attr 从 tmp_mask 中取出来赋值给 match->mask->key
    5. 对 match 进行有效性检查

static size_t get_ufid_len(const struct nlattr *attr, bool log)

	返回 nla_len(attr);

bool ovs_nla_get_ufid(struct sw_flow_id *sfid, const struct nlattr *attr,

    解析 attr 初始化 sfid->ufid_len, sfid->ufid

int ovs_nla_get_identifier(struct sw_flow_id *sfid, const struct nlattr *ufid, const struct sw_flow_key *key, bool log)

    计算 sw_flow->id 即 sfid
    如果 get_ufid_len(ufid) 不为 0
          new_flow->id->ufid_len = nla_len(a[OVS_FLOW_ATTR_UFID])
          new_flow->id->ufid = nla_data([OVS_FLOW_ATTR_UFID])
    否则 a[OVS_FLOW_ATTR_UFID] = NULL, sfid->unmasked_key = key

u32 ovs_nla_get_ufid_flags(const struct nlattr *attr)

	return attr ? nla_get_u32(attr) : 0;

int ovs_nla_get_flow_metadata(const struct nlattr *attr, struct sw_flow_key *key)

    1. 遍历 attr 所有 nla, 保存到临时数组 a(包括全部为 0 的属性)中.
    2. 用 a 初始化 key

    memset(key, 0, OVS_SW_FLOW_KEY_METADATA_SIZE);
    key->phy.in_port = DP_MAX_PORTS;
    key->ovs_flow_hash = a[OVS_KEY_ATTR_DP_HASH]
    key->ovs_flow_hash = a[OVS_KEY_ATTR_RECIRC_ID]
    key->phy.priority = a[OVS_KEY_ATTR_PRIORITY]
    key->phy.in_port = a[OVS_KEY_ATTR_IN_PORT]
    key->phy.skb_mark = a[OVS_KEY_ATTR_SKB_MARK]
    key->tun_key = ipv4_tun_from_nlattr()

static int __ovs_nla_put_key(const struct sw_flow_key *swkey, const struct sw_flow_key *output, bool is_mask, struct sk_buff *skb)

    TODO

int ovs_nla_put_key(const struct sw_flow_key *swkey, const struct sw_flow_key *output, int attr, bool is_mask, struct sk_buff *skb)

    TODO

int ovs_nla_put_identifier(const struct sw_flow *flow, struct sk_buff *skb)

	if (ovs_identifier_is_ufid(&flow->id))
		return nla_put(skb, OVS_FLOW_ATTR_UFID, flow->id.ufid_len, flow->id.ufid);

	return ovs_nla_put_key(flow->id.unmasked_key, flow->id.unmasked_key, OVS_FLOW_ATTR_KEY, false, skb);

int ovs_nla_put_masked_key(const struct sw_flow *flow, struct sk_buff *skb)

	return ovs_nla_put_key(&flow->key, &flow->key, OVS_FLOW_ATTR_KEY, false, skb);

int ovs_nla_put_mask(const struct sw_flow *flow, struct sk_buff *skb)

	return ovs_nla_put_key(&flow->key, &flow->mask->key, OVS_FLOW_ATTR_MASK, true, skb);

static struct sw_flow_actions *nla_alloc_flow_actions(int size, bool log)

    TODO


int ovs_nla_put_flow(const struct sw_flow_key *swkey, const struct sw_flow_key *output, struct sk_buff *skb)

    将 output 属性依次加入 netlink 消息体 skb 中

struct sw_flow_actions *ovs_nla_alloc_flow_actions(int size)

    给 sw_flow_actions 分配内存

static void rcu_free_acts_callback(struct rcu_head *rcu)

    由 rcu 定位到 sw_flow_actions, 并是否内存

void ovs_nla_free_flow_actions(struct sw_flow_actions *sf_acts)

    调用 sw_flow_actions 的 rcu 回调函数 rcu_free_acts_callback 释放 sw_flow_actions 内存

static struct nlattr *reserve_sfa_size(struct sw_flow_actions **sfa, int attr_len)
static struct nlattr *reserve_sfa_size(struct sw_flow_actions **sfa, int attr_len, bool log)

    sfa 的内存空间扩展 NLA_ALIGN(attr_len) byte, (如果 sfa 不够, 重新分配) 返回新的扩展空间首地址

    在 sfs 现有长度基础上增加 attr_len 长度:
    如果空间不够, 就将原来空间扩大 2 倍, 如果扩大 2 被超出了 action 的阈值, 检查 action 的阈值长度
    是否能满足要求
    如果空间足够返回 sfs 扩展首地址

static struct nlattr *__add_action(struct sw_flow_actions **sfa, int attrtype, void *data, int len, bool log)

    TODO

static int add_action(struct sw_flow_actions **sfa, int attrtype, void *data, int len)
static int add_action(struct sw_flow_actions **sfa, int attrtype, void *data, int len, bool log)

    sfa 增加新的 action. 类型为 attrtype, 数据为 data(长度为 len)

static inline int add_nested_action_start(struct sw_flow_actions **sfa, int attrtype)
static inline int add_nested_action_start(struct sw_flow_actions **sfa, int attrtype, bool log)

    给 sfa 增加 attrtype 的内置 action

static inline void add_nested_action_end(struct sw_flow_actions *sfa, int st_offset)

　　略

static int __ovs_nla_copy_actions(const struct nlattr *attr, const struct sw_flow_key *key, int depth, struct sw_flow_actions **sfa, __be16 eth_type, __be16 vlan_tci, bool log);

    遍历 attr 每个元素, 验证每个元素的有效性, 并初始化 eth_type, vlan_tci

static int validate_and_copy_sample(const struct nlattr *attr, const struct sw_flow_key *key, int depth, struct sw_flow_actions **sfa)
static int validate_and_copy_sample(const struct nlattr *attr, const struct sw_flow_key *key, int depth, struct sw_flow_actions **sfa, __be16 eth_type, __be16 vlan_tci, bool log)

    遍历 attr 所有元素, 初始化临时数组 attrs, 将 attrs[OVS_ACTION_ATTR_SAMPLE] 加入 sfa

    其中 depth 为了防止递归属性


static int copy_action(const struct nlattr *from, struct sw_flow_actions **sfa)
static int copy_action(const struct nlattr *from, struct sw_flow_actions **sfa, bool log)

    将 from 属性加入 sfa

void ovs_match_init(struct sw_flow_match *match, struct sw_flow_key *key, struct sw_flow_mask *mask)

    初始化 sw_flow_match

static int validate_geneve_opts(struct sw_flow_key *key)

    TODO

static int validate_and_copy_set_tun(const struct nlattr *attr, struct sw_flow_actions **sfa)
static int validate_and_copy_set_tun(const struct nlattr *attr, struct sw_flow_actions **sfa, bool log)

    遍历 attr 所有 nla, 初始化临时变量 match->key->tun_key
    给 sfa 内置属性 OVS_ACTION_ATTR_SET 增加 OVS_KEY_ATTR_IPV4_TUNNEL 属性

static int validate_set(const struct nlattr *a, const struct sw_flow_key *flow_key, struct sw_flow_actions **sfa, bool *set_tun)
static int validate_set(const struct nlattr *a, const struct sw_flow_key *flow_key, struct sw_flow_actions **sfa, bool *skip_copy, __be16 eth_type, bool masked, bool log)

    对于 OVS_KEY_ATTR_TUNNEL 设置 set_tun 为 true, 并设置 sfa 的 OVS_ACTION_ATTR_SET 属性
    对于其他属性, 仅校验属性

static bool validate_masked(u8 *data, int len)

	u8 *mask = data + len;

	while (len--)
		if (*data++ & ~*mask++)
			return false;

	return true;

static int validate_userspace(const struct nlattr *attr)

    解析 attr 到临时数组 a 来校验解析 attr 的 ovs_userspace_attr 属性是否有问题

int ovs_nla_copy_actions(const struct nlattr *attr, const struct sw_flow_key *key, int depth, struct sw_flow_actions **sfa)
int ovs_nla_copy_actions(const struct nlattr *attr, const struct sw_flow_key *key, struct sw_flow_actions **sfa, bool log)

    遍历 attr 所有属性, 加入 sfa

static int validate_tp_port(const struct sw_flow_key *flow_key)

    略

static int sample_action_to_attr(const struct nlattr *attr, struct sk_buff *skb)

    解析 attr 的 OVS_ACTION_ATTR_SAMPLE 加入 netlink 消息体 skb


static int set_action_to_attr(const struct nlattr *a, struct sk_buff *skb)

    解析 attr 的 OVS_ACTION_ATTR_SET 加入 netlink 消息体 skb

static int masked_set_action_to_set_action_attr(const struct nlattr *a, struct sk_buff *skb)

    TODO

int ovs_nla_put_actions(const struct nlattr *attr, int len, struct sk_buff *skb)

    遍历 attr 所有属性, 加入 netlink 消息体 skb


调用关系

    ovs_nla_put_actions
        set_action_to_attr
        sample_action_to_attr
            ovs_nla_put_actions

ovs_nla_copy_actions
    validate_userspace
    validate_set
        validate_and_copy_set_tun
            ovs_match_init
        validate_tp_port
    validate_and_copy_sample
        ovs_nla_copy_actions
            copy_action
                reserve_sfa_size
                    ovs_nla_alloc_flow_actions
        validate_and_copy_sample
            add_action
                reserve_sfa_size
                    ovs_nla_alloc_flow_actions

ovs_nla_get_match
    parse_flow_nlattrs
        __parse_flow_nlattrs
    parse_flow_mask_nlattrs
        __parse_flow_nlattrs
    ovs_key_from_nlattrs
        metadata_from_nlattrs
            ipv4_tun_from_nlattr
    match_validate

set_action_to_attr
    ipv4_tun_to_nlattr

ovs_nla_put_flow
    ipv4_tun_to_nlattr

ovs_nla_get_flow_metadata
    metadata_from_nlattrs
        ipv4_tun_from_nlattr



actions 的 netlink 消息属性结构


    OVS_ACTION_ATTR_SET
    OVS_ACTION_ATTR_SAMPLE
        OVS_SAMPLE_ATTR_PROBABILITY : nla_data(actions)
        OVS_SAMPLE_ATTR_ACTIONS     :
             递归了

-------------------------------------------------------------

## flow_table.c

static u16 range_n_bytes(const struct sw_flow_key_range *range)

    略

void ovs_flow_mask_key(struct sw_flow_key *dst, const struct sw_flow_key *src, const struct sw_flow_mask *mask)

    将 mask->key 与 src 从偏移 mask->ranger.start 开始进行与操作, 将结果存储在
    dst 偏移 mask->ranger.start 开始之后的位置
    注: 此时的 key, mask 已经是被 ovs_nla_get_match() 赋值的 key, mask

struct sw_flow *ovs_flow_alloc(void)

    从 flow_cache 中分配一个 sw_flow, 并初始化 sw_flow

int ovs_flow_tbl_count(struct flow_table *table)

    返回当前流表的流表项数量

static struct flex_array *alloc_buckets(unsigned int n_buckets)

    分配 n_buckets 个 hlist_head, 初始化每个 hlist_head. 返回 flex_array
    数组首指针

static void flow_free(struct sw_flow *flow)

    释放 sw_flow 内存

static void rcu_free_flow_callback(struct rcu_head *rcu)

    释放 sw_flow 空间

static void rcu_free_sw_flow_mask_cb(struct rcu_head *rcu)

    释放 sw_flow_mask 空间

void ovs_flow_free(struct sw_flow *flow, bool deferred)

    如果 deferred 为 true, 调用 rcu_free_flow_callback 是否 flow
    如果 deferred 为 false, 调用 flow_free 直接释放

static void free_buckets(struct flex_array *buckets)

    是否 buckets 内存

static void __table_instance_destroy(struct table_instance *ti)

    是否 ti->buckets 和 ti 内存

static struct table_instance *table_instance_alloc(int new_size)

    为 table_instance 分配内存并初始化, 其中 buckets 有 new_size 个

static void mask_array_rcu_cb(struct rcu_head *rcu)

    从 rcu 定位到所属 mask_array, 并释放 mask_array

static struct mask_array *tbl_mask_array_alloc(int size)

    为 mask_array 分配内存并初始化, 其中 sw_flow_mask 有 size 个

static int tbl_mask_array_realloc(struct flow_table *tbl, int size)

    重新分配并初始化 mask_array, 新的 mask_array 包含 size 个 sw_flow_mask,
    并将旧的 sw_flow_mask 拷贝到新的 mask_array

static void flow_tbl_destroy_rcu_cb(struct rcu_head *rcu)

    从 rcu 定位 table_instance, 销毁 table_instance

static void table_instance_destroy(struct table_instance *ti, bool deferred)

    遍历 table_instance 所有 buckets 的所有 sw_flow 并释放内存.

void ovs_flow_tbl_destroy(struct flow_table *table)

    释放 flow_table 的内存

struct sw_flow *ovs_flow_tbl_dump_next(struct table_instance *ti, u32 *bucket, u32 *last)

    找到当前所属 bucket 的第 last 个元素

static struct hlist_head *find_bucket(struct table_instance *ti, u32 hash)

    找到 ti->buckets[jhash_1word(hash, ti->hash_seed) & & (ti->n_buckets - 1)]
    的 bucket 的首元素

static void table_instance_insert(struct table_instance *ti, struct sw_flow *flow)

    将 flow->hash_node[ti->node_ver] 加入 ti->buckets[jhash_1word(flow->hash, ti->hash_seed) & & (ti->n_buckets - 1)] 的链表头

static void ufid_table_instance_insert(struct table_instance *ti, struct sw_flow *flow)

    将 flow->ufid_table.node[ti->node_ver] 加入 ti->buckets[jhash_1word(ti->hash_seed, flow->ufid_table.hash)] 中

static void flow_table_copy_flows(struct table_instance *old, struct table_instance *new)

    将 old 的所有 flow 插入 new

static struct table_instance *table_instance_rehash(struct table_instance *ti, int n_buckets)

    创建新的 table_instance new_ti, 并将 ti->buckets 的所有元素 插入 new_ti,
    返回 new_ti

int ovs_flow_tbl_flush(struct flow_table *flow_table)

    重新初始化 flow_table 的所有元素(删除旧的 flow_table->ti)

static u32 flow_hash(const struct sw_flow_key *key, int key_start, int key_end)

    对 key + key_start 与 (key_end - key_start) >> 2 进行哈希
    TODO: hash 算法

static int flow_key_start(const struct sw_flow_key *key)

    TODO

static bool cmp_key(const struct sw_flow_key *key1, const struct sw_flow_key *key2, int key_start, int key_end)

    比较 key1 和 key2 偏移从 key_start 到 key_end 的值是否相同

static bool flow_cmp_masked_key(const struct sw_flow *flow, const struct sw_flow_key *key, int key_start, int key_end)

    比较 flow->key 与 key 从 key_start 到 key_end 的值是否相同

bool ovs_flow_cmp_unmasked_key(const struct sw_flow *flow, struct sw_flow_match *match)

    比较 flow->unmasked_key 与 match->key 从 key_start 到 key_end 的值是否相同

static struct sw_flow *masked_flow_lookup(struct table_instance *ti, const struct sw_flow_key *unmasked, struct sw_flow_mask *mask, u32 *n_mask_hit)

    在 ti->buckets 中找到 flow->key = unmasked 掩码 mask 和 flow->mask = mask 的 flow.
    对 unmasked 用 mask 进行掩码之后存储在临时变量 masked_key,
    遍历 bucket = find_bucket(ti, flow_hash(&masked_key, key_start, key_end)]) 的所有元素
    找到 mask, hash, 与 masked_key 全都相等的 sw_flow.

    注: 将 flow 查找范围缩小到 bucket. 如果流表非常多, 遍历该 bucket 仍然是不小的负担.


static struct sw_flow *flow_lookup(struct flow_table *tbl, struct table_instance *ti, struct mask_array *ma, const struct sw_flow_key *key, u32 *n_mask_hit, u32 *index)

    优先在 ma->masks[index] 为 mask, 哈希之后对应的 ti 的 bucket 中查找,
    如果找不到遍历所有的 ma->masks, 查找对应的 flow

    其中:

    index : 保持 key 所在的 mask_array 的索引.
    n_mask_hit : 貌似有点问题, 应该找到之后更新, 而不是每查找一次 bucket 就更新

    要点:
    1. mask_array 保持所有的 mask
    2. mask 与 key 掩码之后的 masked_key
    3. 从 ti->buckets 中 masked_key 对应的 hash 中查找 与 key 的 hash, mask及内容 完全相同的 flow.
    TODO : 结合 flow 的插入分析


struct sw_flow *ovs_flow_tbl_lookup_stats(struct flow_table *tbl, const struct sw_flow_key *key, u32 skb_hash, u32 *n_mask_hit)

    1. 如果 skb_hash == 0, 直接全表查询
    2. 如果 skb_hash 不为 0
       1. 从 mask_cache 中找到 skb_hash & (MC_HASH_ENTRIES - 1) 对应 mask_cache_entry 缓存的 mask_index
       2. 从 mask_array[mask_index] 哈希之后对应的 bucket 查找
       3. 找不到全表查询.
    3. 如果还找不到, 全表查询.

    注: 实际 3 不会到达.

    TODO: 进一步详细分析

struct sw_flow *ovs_flow_tbl_lookup(struct flow_table *tbl, const struct sw_flow_key *key)

    全表查询 key 对应的 flow

struct sw_flow *ovs_flow_tbl_lookup_exact(struct flow_table *tbl, struct sw_flow_match *match)

    全表查询 match->key 对应的 flow

static u32 ufid_hash(const struct sw_flow_id *sfid)

	return jhash(sfid->ufid, sfid->ufid_len, 0);

static bool ovs_flow_cmp_ufid(const struct sw_flow *flow, const struct sw_flow_id *sfid)

    先比较长度, 再比较内容
	if (flow->id.ufid_len != sfid->ufid_len) return false;
	return !memcmp(flow->id.ufid, sfid->ufid, sfid->ufid_len);

bool ovs_flow_cmp(const struct sw_flow *flow, const struct sw_flow_match *match)

    如果 flow->id->ufid_len != 0, flow->key 与 match->key 是否完全一致
    否则 flow->unmasked_key 与 match->key 是否完全一致

    原因在于创建流表时, 配置 UFID 时, flow->key 被 match->key 初始化; 没有配置 UFID 时, flow->unmasked_key 被 match->key 初始化

struct sw_flow *ovs_flow_tbl_lookup_ufid(struct flow_table *tbl, const struct sw_flow_id *ufid)

    从 tbl->ufid_ti->buckets 中查找 ufid 对应的流表是否存在

    遍历 tbl->ufid_ti->buckets[jhash_1word(jhash(ufid->ufid, ufid->ufid_len, 0), ti->hash_seed)] 中每一个元素 flow, 
    找到满足 flow->ufid = ufid, 返回 flow; 找不到返回 NULL

int ovs_flow_tbl_num_masks(const struct flow_table *table)

    返回 table->mask_array 中 masks 的元素个数

static struct table_instance *table_instance_expand(struct table_instance *ti)

    将 ti 中 buckets 扩大一倍.

    注: 在 flow_key_insert 和 flow_ufid_insert 时会调用

static void tbl_mask_array_delete_mask(struct mask_array *ma, struct sw_flow_mask *mask)

    遍历 ma->masks  的所有元素, 找到 mask 匹配的 mask, 之后删除


static void flow_mask_remove(struct flow_table *tbl, struct sw_flow_mask *mask)

    如果 mask 不为 null, 并且引用计数已经为 0. 将其从 tbl->mask_array 中删除
    如果满足条件, 对 tbl->mask_array 进行压缩
    条件: mask_array 元素个数大于 32, 但实际元素个数小于 mask_array->max 的 1/3
    TODO: 结合 mask_array 重分配

    这里 MASK_ARRAY_SIZE_MIN  是否可以根据实际场景进行 tunning

void ovs_flow_tbl_remove(struct flow_table *table, struct sw_flow *flow)

    将 flow 从 table 中删除. 如果 flow->mask 引用计数为 0, flow->mask 从
    table->mask_array 中删除

static struct sw_flow_mask *mask_alloc(void)

    分配一个 sw_flow_mask

static bool mask_equal(const struct sw_flow_mask *a, const struct sw_flow_mask *b)

    比较 a, b 是否相等.

static struct sw_flow_mask *flow_mask_find(const struct flow_table *tbl, const struct sw_flow_mask *mask)

    从 tbl->mask_array 中查找与 mask 相同的 sw_flow_mask, 返回找到的 sw_flow_mask

static int flow_mask_insert(struct flow_table *tbl, struct sw_flow *flow, struct sw_flow_mask *new)

    从 tbl->mask_array 中找到 new 对应的 mask(sw_flow_mask)
    1. 如果找到 mask, mask 的引用计数加 1. flow->mask 为 mask
    2. 如果没有找到, 如果 mask_array 已经满了, 对 tbl->mask_array 进行扩容. 如果没有满, 从第一个元素开始找到空的位置, 将 mask 加入.

static void flow_key_insert(struct flow_table *table, struct sw_flow *flow)

    将 flow 插入 table->ti->buckets 中的一个链表中

    1. 初始化 flow->flow_table.hash
    2. flow->flow_table.node[ti->node_ver] 加入 ti->buckets
    3. 如果新插入流表数目导致 table->count 大于 table->ti->buckets, 对 table->ti 进行重分配
    4. 如果当前 jiffies 到 table->last_rehash 超过 600 HZ, 重分配
    5. 更新 table->count, table->last_rehash

static void flow_ufid_insert(struct flow_table *table, struct sw_flow *flow)

    将 flow 插入 table->ufid_ti->buckets 中的一个链表中

    1. 将 flow->ufid_table.node[table->ufid_ti->node_ver] 加入 table->ufid_ti->buckets[jhash_1word(table->ufid_ti->hash_seed, flow->ufid_table.hash)] 中
    2. 如果 table->ufid_count 大于 table->ufid_ti->n_buckets 重分配

int ovs_flow_tbl_insert(struct flow_table *table, struct sw_flow *flow, struct sw_flow_mask *mask)

    1. 将 mask 插入 table->mask_array, 并且 flow->mask = mask
    2. 将 flow->flow_table->node[table->ti->node_ver] 插入 table->ti->buckets 中的一个链表中
    3. 如果 flow->id 存在, 将 flow->ufid_table->node[table->ufid_ti->node_ver] 插入 table->ufid_ti->buckets 中的一个链表中

int ovs_flow_init(void)

    在 slab 分配内存给 flow_cache
    在 slab 分配内存给 flow_stats_cache

    从内核缓存区初始化 sw_flow sw_flow_stats 两块内存

    static struct kmem_cache *flow_cache;
    struct kmem_cache *flow_stats_cache __read_mostly;
	flow_cache = kmem_cache_create("sw_flow", sizeof(struct sw_flow)
				       + (nr_node_ids
					  * sizeof(struct flow_stats *)),
				       0, 0, NULL);
	flow_stats_cache
		= kmem_cache_create("sw_flow_stats", sizeof(struct flow_stats),
				    0, SLAB_HWCACHE_ALIGN, NULL);

    nr_node_ids = 1

void ovs_flow_exit(void)

    在 slab 清除 flow_cache, flow_stats_cache

ovs_flow_tbl_init
    tbl_mask_array_alloc
    table_instance_alloc

ovs_flow_tbl_insert
    flow_mask_insert
        flow_mask_find
            mask_equal
        mask_alloc
        tbl_mask_array_realloc
    table_instance_insert

    table_instance_expand
        table_instance_rehash
            table_instance_alloc
            flow_table_copy_flows
                table_instance_insert
    table_instance_rehash
        table_instance_alloc
        flow_table_copy_flows

ovs_flow_tbl_remove
    flow_mask_remove
        tbl_mask_array_delete_mask
        tbl_mask_array_realloc

ovs_flow_tbl_num_masks
ovs_flow_tbl_lookup_exact
    masked_flow_lookup
    ovs_flow_cmp_unmasked_key

ovs_flow_tbl_lookup
    flow_lookup
        masked_flow_lookup


问题:
    mask 查找和 mask 删除进行比较不一致?

    mask == ovsl_dereference(ma->masks[i]) VS mask_equal(mask, t)


流表查找算法:


table_instance_rehash
    flow_table_copy_flows

ovs_flow_tbl_flush
    table_instance_alloc

-------------------------------------------------------------

vport-internal.c

static const struct net_device_ops internal_dev_netdev_ops = {
	.ndo_open = internal_dev_open,
	.ndo_stop = internal_dev_stop,
	.ndo_start_xmit = internal_dev_xmit,
	.ndo_set_mac_address = eth_mac_addr,
	.ndo_change_mtu = internal_dev_change_mtu,
#if LINUX_VERSION_CODE >= KERNEL_VERSION(2,6,36)
	.ndo_get_stats64 = internal_dev_get_stats,
#else
	.ndo_get_stats = internal_dev_sys_stats,
#endif
};

static int internal_dev_xmit(struct sk_buff *skb, struct net_device *netdev)

    接受外部网络传来的数据并进行处理

static int internal_dev_open(struct net_device *netdev)

    通知上层可以传输数据(即将 dev->_tx[0]->state 中的 __QUEUE_STATE_DRV_XOFF
    位清零) 如果将 dev->_tx[0]->state 的 __QUEUE_STATE_DRV_XOFF 置位, 表示
    停止传输数据

```
static inline void netif_start_queue(struct net_device *dev)
{
        netif_tx_start_queue(netdev_get_tx_queue(dev, 0));
}
static inline void netif_tx_start_queue(struct netdev_queue *dev_queue)
{
        clear_bit(__QUEUE_STATE_DRV_XOFF, &dev_queue->state);
}
static inline struct netdev_queue *netdev_get_tx_queue(const struct net_device *dev, unsigned int index)
{
        return &dev->_tx[index];
}

static inline void netif_tx_stop_queue(struct netdev_queue *dev_queue)
{
        if (WARN_ON(!dev_queue)) {
                pr_info("netif_stop_queue() cannot be called before register_netdev()\n");
                return;
        }
        set_bit(__QUEUE_STATE_DRV_XOFF, &dev_queue->state);
}

/**
 *      netif_stop_queue - stop transmitted packets
 *      @dev: network device
 *
 *      Stop upper layers calling the device hard_start_xmit routine.
 *      Used for flow control when transmit resources are unavailable.
 */
static inline void netif_stop_queue(struct net_device *dev)
{
        netif_tx_stop_queue(netdev_get_tx_queue(dev, 0));
}
```

static int internal_dev_stop(struct net_device *netdev)

    通知上层可以传输数据(即将 dev->_tx[0]->state 中的 __QUEUE_STATE_DRV_XOFF
    位置位)

static void internal_dev_getinfo(struct net_device *netdev, struct ethtool_drvinfo *info)

    拷贝 openvswitch 到 info->driver

static int internal_dev_change_mtu(struct net_device *netdev, int new_mtu)

	netdev->mtu = new_mtu;

static void internal_dev_destructor(struct net_device *dev)

    释放 dev 对应的 vport 及 dev 的内存

const struct vport_ops ovs_internal_vport_ops = {
	.type		= OVS_VPORT_TYPE_INTERNAL,
	.create		= internal_dev_create,
	.destroy	= internal_dev_destroy,
	.get_name	= ovs_netdev_get_name,
	.send		= internal_dev_recv,
};

static void do_setup(struct net_device *netdev)

    初始化网卡特性

static struct vport *internal_dev_create(const struct vport_parms *parms)

    1. 分配 vport 内存, 其中私有部分为 netdev_vport, netdev_vport->dev = internal_dev
    2. internal_dev 关联的 net_device 分配内存
    3. 设置 internal_dev 的命名空间
    4. 将 internal_dev 对应 net_device 注册到内核空间
    5. 设置 internal_dev 对应 net_device 为混杂模式
    6. 打开处理上层传递数据开关


static void internal_dev_destroy(struct vport *vport)

    停止传输上层传来的数据
    停止混杂模式
    注销 internal_dev 对应的 net_device

static int internal_dev_recv(struct vport *vport, struct sk_buff *skb)

    将 skb 加入 cpu 的 softnet_data->input_pkt_queue 中

-------------------------------------------------------------

### vport-netdev


const struct vport_ops ovs_netdev_vport_ops = {
	.type		= OVS_VPORT_TYPE_NETDEV,
	.create		= netdev_create,
	.destroy	= netdev_destroy,
	.get_name	= ovs_netdev_get_name,
	.send		= netdev_send,
};

static rx_handler_result_t netdev_frame_hook(struct sk_buff **pskb)

    处理收到的 skb


static struct vport *netdev_create(const struct vport_parms *parms)

    1. 为 vport 分配内存, 其中私有部分为 netdev_vport, netdev_vport->dev
    为已经存在的网卡对应的 net_device
    2. 将该网卡的上联 net_device 置为为所属网桥的 local 端口所对应的 net_device
    3. 注册该网卡的收包回调函数
    4. 设置网卡为混杂模式


static void free_port_rcu(struct rcu_head *rcu)

    是否 rcu 对应的 vport 内存


void ovs_netdev_detach_dev(struct vport *vport)

    将网卡恢复原来的状态
    1. 清除网卡私有标记.
    2. 注销收包回调函数
    3. 删除上联设备关系
    4. 取消混杂模式.

static void netdev_destroy(struct vport *vport)

    如果 vport 关联到网卡, 将网卡恢复原来的状态
    释放 vport 内存

const char *ovs_netdev_get_name(const struct vport *vport)

    返回 vport 对应 net_device 的网卡名

static void netdev_port_receive(struct vport *vport, struct sk_buff *skb)

    处理收到的包

static int netdev_send(struct vport *vport, struct sk_buff *skb)

    发送 skb

int __init ovs_netdev_init(void)
{
    return ovs_vport_ops_register(&ovs_netdev_vport_ops);
}

int ovs_vport_ops_register(struct vport_ops *ops)

    将 ovs_netdev_vport_ops 加入 vport.c 中的全局变量 vport_ops_list 双向链表中
    每个 vport_ops 的 type 必须不一样

    其中
        static struct vport_ops ovs_netdev_vport_ops = {
            .type		= OVS_VPORT_TYPE_NETDEV,
            .create		= netdev_create,
            .destroy	= netdev_destroy,
            .get_name	= ovs_netdev_get_name,
            .send		= netdev_send,
        };

-------------------------------------------------------------

### vport.c

struct vport *ovs_vport_locate(struct net *net, const char *name)

    通过 net, name 定位 vport

struct vport *ovs_vport_alloc(int priv_size, const struct vport_ops *ops, const struct vport_parms *parms)

    分配 vport 内存并初始化, 具体为:

    初始化　struct vport 指针
    1. 为 vport  分配 sizeof(struct vport) + priv_size 内存, VPORT_ALIGN 对齐
    2. vport->dp = params->dp
    3. vport->port_no = parms->port_no
    4. vport->opst = ops;
    5. 初始化 hash 链表  vport->dp_hash_node
    6. 初始化 vport->upcall_portids : kmalloc 分配 vport_portids
    7. 初始化 vport->percpu_stats : 每个 cpu 分配一个

    其中
    vport->upcall_portids->n_ids = nla_len(ids) / sizeof(u32)
    vport->upcall_portids->rn_ids = reciprocal_value(vport->upcall_portids->n_ids)
    vport->upcall_portids->ids = params->upcall_portids

    vport->ops 包括:
        .type		= OVS_VPORT_TYPE_INTERNAL,
        .create		= internal_dev_create,
        .destroy	= internal_dev_destroy,
        .get_name	= ovs_netdev_get_name,
        .send		= internal_dev_recv,

    注:
    1. 对照 vport 数据结构发现: hash_node err_stats detach_list 没有初始化
    2. 对 vport 分配了私有数据 netdev_vport, 这内核 net_device 的惯例

void ovs_vport_free(struct vport *vport)

    是否 vport 内存

struct vport *ovs_vport_add(const struct vport_parms *parms)

    创建一个 parms->type 类型的 vport. 分配内存, 并加入 dev_table

int ovs_vport_set_options(struct vport *vport, struct nlattr *options)

    设置 vport 的选项

void ovs_vport_del(struct vport *vport)

    将 vport 从 dev_table 删除, 并销毁 vport

void ovs_vport_set_stats(struct vport *vport, struct ovs_vport_stats *stats)

	vport->offset_stats = *stats;

void ovs_vport_get_stats(struct vport *vport, struct ovs_vport_stats *stats)

    用 vport 状态初始化 stats

int ovs_vport_get_options(const struct vport *vport, struct sk_buff *skb)

    将 vport 的 option 加入 skb

static void vport_portids_destroy_rcu_cb(struct rcu_head *rcu)

    释放 vport_portids

int ovs_vport_set_upcall_portids(struct vport *vport,  struct nlattr *ids)

    用 ids 初始化 vport->upcall_portids

int ovs_vport_get_upcall_portids(const struct vport *vport, struct sk_buff *skb)

    将 vport 的 upcall_portids 加入 skb

u32 ovs_vport_find_upcall_portid(const struct vport *p, struct sk_buff *skb)

    找到 upcall_portids


int ovs_vport_send(struct vport *vport, struct sk_buff *skb)

    将包发送出去. 并更新 vport

static void free_vport_rcu(struct rcu_head *rcu)

    直接释放 rcu 对应 vport 内存

void ovs_vport_deferred_free(struct vport *vport)

    延迟 vport 内存释放动作

-------------------------------------------------------------

### 流表动作执行

	核心函数: ovs_execute_actions(dp, skb, flow->sf_acts, key);

## datapath 初始化

1 action_fifos_init();
2 ovs_internal_dev_rtnl_link_register();
3 ovs_flow_init();
4 ovs_vport_init();
5 register_pernet_device(&ovs_net_ops);
6 register_netdevice_notifier(&ovs_dp_device_notifier);
7 ovs_netdev_init();
8 dp_register_genl();

对应于

1 分配一个动态的　percpu 区域初始化 action_fifos
2 将 internal_dev_link_ops 加入 linux/rtnetlink.h 中 link_ops 双向链表中,
  将 ovs_internal_vport_ops 加入 vport.c 中的 vport_ops_list 双向链表中
3 从内核缓存区初始化 sw_flow, sw_flow_stats 两块内存
4 分配 1024 个 hlist_head(hash 桶的大小) 初始化 dev_table
5 将 ovs_net_ops 操作, 注册到所有命名空间
6 将 ovs_dp_device_notifier 注册一个网络通知
7 将 ovs_netdev_vport_ops 注册到所有命名空间
8 将 dp_genl_families  中所有元素注册到 generic netlink family


##action

###action_fifos_init()

分配一个动态的　percpu 区域初始化 action_fifos

static struct action_fifo __percpu *action_fifos;
action_fifos = alloc_percpu(struct action_fifo);

#define DEFERRED_ACTION_FIFO_SIZE 10
struct deferred_action {
	struct sk_buff *skb;
	const struct nlattr *actions;

	/* Store pkt_key clone when creating deferred action. */
	struct sw_flow_key pkt_key;
};

struct action_fifo {
	int head;
	int tail;
	/* Deferred action fifo queue storage. */
	struct deferred_action fifo[DEFERRED_ACTION_FIFO_SIZE];
};


##vport-internal_dev

----------------------------------------------

###int ovs_internal_dev_rtnl_link_register(void)

将 internal_dev_link_ops 加入 linux/rtnetlink.h 中 link_ops 双向链表中
将 ovs_internal_vport_ops 加入 vport.c 中的全局变量 vport_ops_list 双向链表中

实现机制:

    static struct rtnl_link_ops internal_dev_link_ops __read_mostly = {
        .kind = "openvswitch",
    };
    rtnl_link_register(&internal_dev_link_ops);

    static LIST_HEAD(vport_ops_list);
    static struct vport_ops ovs_internal_vport_ops = {
        .type		= OVS_VPORT_TYPE_INTERNAL,
        .create		= internal_dev_create,
        .destroy	= internal_dev_destroy,
        .get_name	= ovs_netdev_get_name,
        .send		= internal_dev_recv,
    };
    ovs_vport_ops_register(&ovs_internal_vport_ops);

int ovs_vport_ops_register(struct vport_ops *ops)

    将 ovs_internal_vport_ops 加入 vport.c 中的全局变量 vport_ops_list 双向链表中

    其中
        static struct vport_ops ovs_internal_vport_ops = {
            .type		= OVS_VPORT_TYPE_INTERNAL,
            .create		= internal_dev_create,
            .destroy	= internal_dev_destroy,
            .get_name	= ovs_netdev_get_name,
            .send		= internal_dev_recv,
        };


##vport

----------------------------------------------

int ovs_vport_init(void)

    分配 1024 个 hlist_head(hash 桶的大小) 初始化 dev_table

    static struct hlist_head *dev_table;
    #define VPORT_HASH_BUCKETS 1024
	dev_table = kzalloc(VPORT_HASH_BUCKETS * sizeof(struct hlist_head),
			    GFP_KERNEL);


int ovs_vport_ops_register(struct vport_ops *ops)

    将 ops 加入 vport_ops_list 中(前提是 vport_ops_list 中每个元素的 type 是唯一的)


int ovs_vport_set_upcall_portids(struct vport *vport, const struct nlattr *ids)

    初始化或更新 vport->upcall_portids
    1. 分配 sizeof(struct vport_portids) + nla_len(ids) 内存
    2. vport->upcall_portids->n_ids = nla_len(ids) / sizeof(u32)
    3. vport->upcall_portids->rn_ids = reciprocal_value(vport->upcall_portids->n_ids)
    4. vport->upcall_portids->ids = ids

----------------------------------------------

## net_namespace

static struct pernet_operations ovs_net_ops = {
	.init = ovs_init_net,
	.exit = ovs_exit_net,
	.id   = &ovs_net_id,
	.size = sizeof(struct ovs_net),
};

/**
 *      register_pernet_device - register a network namespace device
 *      @ops:  pernet operations structure for the subsystem
 *
 *      Register a device which has init and exit functions
 *      that are called when network namespaces are created and
 *      destroyed respectively.
 *
 *      When registered all network namespace init functions are
 *      called for every existing network namespace.  Allowing kernel
 *      modules to have a race free view of the set of network spaces.
 *
 *      When a new network namespace is created all of the init
 *      methods are called in the order in which they were registered.
 *
 *      When a network namespace is destroyed all of the exit methods
 *      are called in the reverse of the order with which they were
 *      registered.
 */
int register_pernet_device(struct pernet_operations *ops)

    将 ops->list 加入 linux/net_namespace.h pernet_list 双向链表中
    linux/net_namespace.h 从 net_namespace_list 开始遍历所有的 struct net
    1. 分配 ops->size 内存空间 data 并且 net->gen->ptr[id-1] = data
    2. 调用 ops->init(net)
    3. 将 net->exit_list 加入 net_exit_list 双向链表中

    注册一个 net namespace 设备, 当 net namespace 创建的时候调用
    ops->init 在 net namespace 销毁的时候调用 ops->exit

    NOTE: net_namespace_list, net_exit_list 都是 net_namespace.h 中 head_list 类型的全局变量,




----------------------------------------------

/**
 *      register_netdevice_notifier - register a network notifier
 *      @nb: notifier
 *
 *      Register a notifier to be called when network device events .
 *      The notifier passed is linked into the kernel structures and
 *      not be reused until it has been unregistered. A negative code
 *      is returned on a failure.
 *
 *      When registered all registration and up events are replayed
 *      to the new notifier to allow device to have a race free
 *      view of the network device list.
 */

int register_netdevice_notifier(&ovs_dp_device_notifier);

    struct notifier_block ovs_dp_device_notifier = {
        .notifier_call = dp_device_event
    };


static int dp_device_event(struct notifier_block *unused, unsigned long event,
			   void *ptr)

    如果 ptr->dev->netdev_ops != internal_dev_netdev_ops 直接返回
    如果 event 是 NETDEV_UNREGISTER, 将 ptr->dev->dp_notify_work 加入 system_wq

----------------------------------------------
int dp_register_genl(void)

    遍历 dp_genl_families, 对每个元素调用 genl_register_family(dp_genl_families[i]);
    其中 genl_register_family(dp_genl_families[i])


## 参考

http://blog.csdn.net/shallnet/article/details/47682383
http://blog.csdn.net/shallnet/article/details/47682593
http://blog.csdn.net/yuzhihui_no1/article/details/47284329
http://blog.csdn.net/yuzhihui_no1/article/details/47305361



##附录

```
/*
 * enqueue_to_backlog is called to queue an skb to a per CPU backlog
 * queue (may be a remote CPU queue).
 */
static int enqueue_to_backlog(struct sk_buff *skb, int cpu, unsigned int *qtail)
{
        struct softnet_data *sd;
        unsigned long flags;
        unsigned int qlen;

        sd = &per_cpu(softnet_data, cpu);

        local_irq_save(flags);

        rps_lock(sd);
        qlen = skb_queue_len(&sd->input_pkt_queue);
        if (qlen <= netdev_max_backlog && !skb_flow_limit(skb, qlen)) {
                if (skb_queue_len(&sd->input_pkt_queue)) {
enqueue:
                        __skb_queue_tail(&sd->input_pkt_queue, skb);
                        input_queue_tail_incr_save(sd, qtail);
                        rps_unlock(sd);
                        local_irq_restore(flags);
                        return NET_RX_SUCCESS;
                }

                /* Schedule NAPI for backlog device
                 * We can use non atomic operation since we own the queue lock
                 */
                if (!__test_and_set_bit(NAPI_STATE_SCHED, &sd->backlog.state)) {
                        if (!rps_ipi_queued(sd))
                                ____napi_schedule(sd, &sd->backlog);
                }
                goto enqueue;
        }

        sd->dropped++;
        rps_unlock(sd);

        local_irq_restore(flags);

        atomic_long_inc(&skb->dev->rx_dropped);
        kfree_skb(skb);
        return NET_RX_DROP;
}
static int netif_rx_internal(struct sk_buff *skb)
{
        int ret;

        /* if netpoll wants it, pretend we never saw it */
        if (netpoll_rx(skb))
                return NET_RX_DROP;

        net_timestamp_check(netdev_tstamp_prequeue, skb);

        trace_netif_rx(skb);
#ifdef CONFIG_RPS
        if (static_key_false(&rps_needed)) {
                struct rps_dev_flow voidflow, *rflow = &voidflow;
                int cpu;

                preempt_disable();
                rcu_read_lock();

                cpu = get_rps_cpu(skb->dev, skb, &rflow);
                if (cpu < 0)
                        cpu = smp_processor_id();

                ret = enqueue_to_backlog(skb, cpu, &rflow->last_qtail);

                rcu_read_unlock();
                preempt_enable();
        } else
#endif
        {
                unsigned int qtail;
                ret = enqueue_to_backlog(skb, get_cpu(), &qtail);
                put_cpu();
        }
        return ret;
}

/**
 *      netif_rx        -       post buffer to the network code
 *      @skb: buffer to post
 *
 *      This function receives a packet from a device driver and queues it for
 *      the upper (protocol) levels to process.  It always succeeds. The buffer
 *      may be dropped during processing for congestion control or by the
 *      protocol layers.
 *
 *      return values:
 *      NET_RX_SUCCESS  (no congestion)
 *      NET_RX_DROP     (packet was dropped)
 *
 */

int netif_rx(struct sk_buff *skb)
{
        trace_netif_rx_entry(skb);

        return netif_rx_internal(skb);
}
EXPORT_SYMBOL(netif_rx);
```

收到包, 如果没有开启 RPS, 那么, 包将发送给 CPU0, 扶开启, RPS, 将对包进行计算,
找到匹配的 CPU, 满足一定的条件, 将包加入对应的 CPU 的 softnet_data->input_pkt_queue
否则将包丢弃.

满足的条件:

1. softnet_data->input_pkt_queue 的长度小于 netdev_max_backlog
2. softnet_data->flow_limit 达到阈值
3. softnet_data->input_pkt_queue 不为 0

如果 softnet_data->input_pkt_queue 为 0, 开始 NAPI 收包之后, 重复上述动作

### 初始化网卡

```
/**
 *      alloc_netdev_mqs - allocate network device
 *      @sizeof_priv:   size of private data to allocate space for
 *      @name:          device name format string
 *      @setup:         callback to initialize device
 *      @txqs:          the number of TX subqueues to allocate
 *      @rxqs:          the number of RX subqueues to allocate
 *
 *      Allocates a struct net_device with private data area for driver use
 *      and performs basic initialization.  Also allocates subqueue structs
 *      for each queue on the device.
 */
struct net_device *alloc_netdev_mqs(int sizeof_priv, const char *name,
                void (*setup)(struct net_device *),
                unsigned int txqs, unsigned int rxqs)
{
        struct net_device *dev;
        size_t alloc_size;
        struct net_device *p;

        BUG_ON(strlen(name) >= sizeof(dev->name));

        if (txqs < 1) {
                pr_err("alloc_netdev: Unable to allocate device with zero queues\n");
                return NULL;
        }

#ifdef CONFIG_SYSFS
        if (rxqs < 1) {
                pr_err("alloc_netdev: Unable to allocate device with zero RX queues\n");
                return NULL;
        }
#endif

        alloc_size = sizeof(struct net_device);
        if (sizeof_priv) {
                /* ensure 32-byte alignment of private area */
                alloc_size = ALIGN(alloc_size, NETDEV_ALIGN);
                alloc_size += sizeof_priv;
        }
        /* ensure 32-byte alignment of whole construct */
        alloc_size += NETDEV_ALIGN - 1;

        p = kzalloc(alloc_size, GFP_KERNEL | __GFP_NOWARN | __GFP_REPEAT);
        if (!p)
                p = vzalloc(alloc_size);
        if (!p)
                return NULL;

        dev = PTR_ALIGN(p, NETDEV_ALIGN);
        dev->padded = (char *)dev - (char *)p;

        dev->pcpu_refcnt = alloc_percpu(int);
        if (!dev->pcpu_refcnt)
                goto free_dev;

        if (dev_addr_init(dev))
                goto free_pcpu;

        dev_mc_init(dev); //初始化多播地址
        dev_uc_init(dev); //初始化单播地址

        dev_net_set(dev, &init_net);  dev->nd_net = init_net

        dev->gso_max_size = GSO_MAX_SIZE;
        dev->gso_max_segs = GSO_MAX_SEGS;

        INIT_LIST_HEAD(&dev->napi_list);
        INIT_LIST_HEAD(&dev->unreg_list);
        INIT_LIST_HEAD(&dev->close_list);
        INIT_LIST_HEAD(&dev->link_watch_list);
        INIT_LIST_HEAD(&dev->adj_list.upper);
        INIT_LIST_HEAD(&dev->adj_list.lower);
        INIT_LIST_HEAD(&dev->all_adj_list.upper);
        INIT_LIST_HEAD(&dev->all_adj_list.lower);
        dev->priv_flags = IFF_XMIT_DST_RELEASE;
        setup(dev);

        dev->num_tx_queues = txqs;
        dev->real_num_tx_queues = txqs;
        if (netif_alloc_netdev_queues(dev))
                goto free_all;

#ifdef CONFIG_SYSFS
        dev->num_rx_queues = rxqs;
        dev->real_num_rx_queues = rxqs;
        if (netif_alloc_rx_queues(dev))
                goto free_all;
#endif

        strcpy(dev->name, name);
        dev->group = INIT_NETDEV_GROUP;
        if (!dev->ethtool_ops)
                dev->ethtool_ops = &default_ethtool_ops;
        return dev;

free_all:
        free_netdev(dev);
        return NULL;

free_pcpu:
        free_percpu(dev->pcpu_refcnt);
        netif_free_tx_queues(dev);
#ifdef CONFIG_SYSFS
        kfree(dev->_rx);
#endif

free_dev:
        netdev_freemem(dev);
        return NULL;
}
EXPORT_SYMBOL(alloc_netdev_mqs);
```


### 根据 name 获取 net_device

```
net/core/dev.c

/**
 *      dev_get_by_name_rcu     - find a device by its name
 *      @net: the applicable net namespace
 *      @name: name to find
 *
 *      Find an interface by name.
 *      If the name is found a pointer to the device is returned.
 *      If the name is not found then %NULL is returned.
 *      The reference counters are not incremented so the caller must be
 *      careful with locks. The caller must hold RCU lock.
 */

struct net_device *dev_get_by_name_rcu(struct net *net, const char *name)
{
        struct net_device *dev;
        struct hlist_head *head = dev_name_hash(net, name);

        hlist_for_each_entry_rcu(dev, head, name_hlist)
                if (!strncmp(dev->name, name, IFNAMSIZ))
                        return dev;

        return NULL;
}
EXPORT_SYMBOL(dev_get_by_name_rcu);

/**
 *      dev_get_by_name         - find a device by its name
 *      @net: the applicable net namespace
 *      @name: name to find
 *
 *      Find an interface by name. This can be called from any
 *      context and does its own locking. The returned handle has
 *      the usage count incremented and the caller must use dev_put() to
 *      release it when it is no longer needed. %NULL is returned if no
 *      matching device is found.
 */

struct net_device *dev_get_by_name(struct net *net, const char *name)
{
        struct net_device *dev;

        rcu_read_lock();
        dev = dev_get_by_name_rcu(net, name);
        if (dev)
                dev_hold(dev);
        rcu_read_unlock();
        return dev;
}
EXPORT_SYMBOL(dev_get_by_name);

static inline struct hlist_head *dev_name_hash(struct net *net, const char *name)
{
        unsigned int hash = full_name_hash(name, strnlen(name, IFNAMSIZ));

        return &net->dev_name_head[hash_32(hash, NETDEV_HASHBITS)];
}

```

每个命名空间中的 dev 都保存在 dev->dev_name_head 的数组中.

### 发送包

__dev_queue_xmit(skb, NULL)
    __dev_xmit_skb(skb, q, dev, txq)
    dev_hard_start_xmit(skb, dev, txq);


```
```
