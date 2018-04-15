
## 数据结构

ofproto_dpif_class

ofproto_dpif 保存在 all_ofproto_dpifs


其中 packet_in 数据包保存在 ofproto_dpif->pins

### ofproto 与 ofproto_dpif 的关系

ofproto 通过 CONTAINER_OF(ofproto, struct ofproto_dpif, up) 定位到 ofproto_dpif

ofproto_dpif 通过 up 定位到 ofproto

## 全局变量

static struct hmap all_ofproto_dpifs


flow_restore_wait : 为 true, 恢复后不删除流表, 为 false, 恢复后删除流表


## 数据结构

rule_dpif 与 rule 的关系

    rule = rule_dpif->up

    rule_dpif = CONTAINER_OF(rule, struct rule_dpif, up)



## 核心实现

static void init(const struct shash *iface_hints)

    1. 将 iface_hints 加入 全局变量 init_ofp_ports
    2. 注册 ofproto/trace, fdb, mdb, dpif 命令
    3. 注册 upcall 命令

static void enumerate_types(struct sset *types)

    1. 注册命令, 并将 dpif_netdev_class, dpif_netlink_class 加入 dpif_classes, 并初始化
    2. 将 dpif_classes 中每个元素 type 加入 types

    注: 步骤 2 目前实现实际为 system(dpif_netlink_class->type) 和 dpif_netdev_class->type


    2. 调用 dpif_netlink_class 和 dpif_netdev_class 的 init(), 将其加入 dpif_classes
       将 base_dpif_classes 中的每个元素的 type 加入 types
       (实际上 types 包含 dpif_netlink_class->type(system), dpif_netdev_class->type(netdev) 两个元素)
    3. dpif_classes 中的元素加入 types

    ###dpif_netdev_class->init()

    注册
          dpif-netdev/pmd-stats-show
          dpif-netdev/pmd-stats-clear
    命令

    ###dpif_netlink_class->init()

    1. 与内核建立 NETLINK_GENERIC 协议连接, 发送请求获取 name (genl_family->name) 对应的 number(genl_family->id)
    2. 将 OVS_DATAPATH_FAMILY, OVS_VPORT_FAMILY, OVS_FLOW_FAMILY 加入 genl_families
    3. 确保 OVS_VPORT_FAMILY 中存在 OVS_VPORT_MCGROUP 对应 ID 的 ovs_vport_mcgroup

    genl_family:
          id                 name
    OVS_DATAPATH_FAMILY ovs_datapath_family
    OVS_VPORT_FAMILY    ovs_vport_family
    OVS_FLOW_FAMILY     ovs_flow_family
    OVS_PACKET_FAMILY   ovs_packet_family

                      CTRL_ATTR_MCAST_GRP_NAME CTRL_ATTR_MCAST_GRP_ID
    OVS_VPORT_FAMILY     OVS_VPORT_FAMILY         ovs_vport_mcgroup


static int enumerate_names(const char *type, struct sset *names)

    遍历 all_ofproto_dpifs 中的元素 ofproto, 如果 ofproto.up.type == type, 将 ofproto.up.name 加入 names


static void set_tables_version(struct ofproto *ofproto_, cls_version_t version)

    通过 ofproto_ 定位到 ofproto_dpif, 设置 tables_version = version


static struct ofproto * alloc(void)

    分配 ofproto_dpif 内存.

static int construct(struct ofproto *ofproto_)

    1. 初始化 ofproto_ 对应的 ofproto_dpif 数据成员
    2. 将其加入 all_ofproto_dpifs
    3. 初始化 ofproto_ 的 tables
    4. 增加内部流表(隐藏的, 只读的)

static int open_dpif_backer(const char *type, struct dpif_backer **backerp)

    1. recirc_init();
    2. 从 all_dpif_backers 中查找 type 对应的 dpif_backer, 如果找到, backerp 指向该 dpif_backer, 返回 0. 否则继续
    3. 创建并初始化 backer
    4. 将 backer-dpif 中不在初始化配置的所有端口加入 garbage_list 中, 之后将 garbage_list 中的端口从 backer-dpif 删除
    5. 将 backer 加入 all_dpif_backers
    6. 测试系统对 backer->support 中的特性支持程度并初始化 backer->support
    7.
        如果 backer->dpif->dpif_class = dpif_netlink_class
             如果 backer->recv_set_enable = true; dpif->handlers != NULL, 返回 0
             如果 backer->recv_set_enable = true; dpif->handlers = NULL, 刷新所有的 channels
             如果 backer->recv_set_enable = false; dpif->handlers = NULL, 返回 0
             如果 backer->recv_set_enable = false; dpif->handlers != NULL, 删除所有 channels
        如果 backer->dpif->dpif_class = dpif_netdev_class
     　　   什么也不做
    8. 设置 backer->udpif 的 handler_thread 和 revalidator_thread 数量


int dpif_create_and_open(const char *name, const char *type, struct dpif **dpifp)

    在 dpif_classes 根据 type 找到注册的 dpif_class, 调用 dpif_class->dpif_class->open() 方法, dpifp 指向创建的对象

    如果 type = system 调用 dpif_netlink_class->open(dpif_netlink_class,name,create,dpifp)
    如果 type = netdev 调用 dpif_netdev_class->open(dpif_netlink_class,name,create,dpifp)


int dpif_create(const char *name, const char *type, struct dpif **dpifp)

    在 dpif_classes 根据 type 找到注册的 dpif_class, 调用 dpif_class->dpif_class->open() 方法

    如果 type = system 调用 dpif_netlink_class->open(dpif_netlink_class,name,false,dpifp) : 向内核发送创建 datapath 的消息, 并用内核应答初始化一个 dpif_netlink 对象. dpifp 指向该对象
    如果 type = netdev 调用 dpif_netdev_class->open(dpif_netlink_class,name,false,dpifp) : 在 dp_netdevs 中创建 name 对应的 dp_netdev 对象, 并初始化, dpifp 指向该对象

int dpif_open(const char *name, const char *type, struct dpif **dpifp)

    在 dpif_classes 根据 type 找到注册的 dpif_class, 调用 dpif_class->dpif_class->open() 方法

    NOTE
    如果 type = system 调用 dpif_netlink_class->open(dpif_netlink_class,name,false,dpifp) : 向内核发送创建 datapath 的消息, 并用内核应答初始化一个 dpif_netlink 对象. dpifp 指向该对象
    如果 type = netdev 调用 dpif_netdev_class->open(dpif_netlink_class,name,false,dpifp) : 在 dp_netdevs 中创建 name 对应的 dp_netdev 对象, 并初始化, dpifp 指向该对象


static int do_open(const char *name, const char *type, bool create, struct dpif **dpifp)

    @type   : 目前为 system, netdev
    @create : 是否创建
    @dpifp  : dpif_classes 中 type 对应的 dpif_class

    在 dpif_classes 根据 type 找到注册的 dpif_class, 调用 dpif_class->dpif_class->open() 方法

    如果 type = system 调用 dpif_netlink_class->open(dpif_netlink_class,name,create,dpifp)

        由 create, name 构造一个 NETLINK_GENERIC 协议请求消息, 向内核发送请求创建或设置 datapath, 并根据应答消息初始化一个 dpif_netlink 对象

        1. 将 OVS_DATAPATH_FAMILY, OVS_VPORT_FAMILY, OVS_FLOW_FAMILY 加入 genl_families
        2. 确保 OVS_VPORT_FAMILY 对应的组属性中存在 OVS_VPORT_MCGROUP
        3. 由 create, name 构造一个创建或设置 datapath 的 NETLINK 请求消息
        4. 由 3 构造 NETLINK_GENERIC 协议消息, 发送请求, 根据应答消息初始化一个 dpif_netlink 对象

        其中 3:
          如果 create = true
             dp_request.cmd = OVS_DP_CMD_NEW;
             dp_request.upcall_pid = 0;
             dp_request.name = name;
             dp_request.user_features = OVS_DP_F_UNALIGNED | OVS_DP_F_VPORT_PIDS;
          否则
             dp_request.cmd = OVS_DP_CMD_SET;
             dp_request.upcall_pid = 0;
             dp_request.name = name;
             dp_request.user_features = OVS_DP_F_UNALIGNED | OVS_DP_F_VPORT_PIDS;

    如果 type = netdev 调用 dpif_netdev_class->open(dpif_netdev_class,name,create,dpifp)

        检查 name, class 对应的 dp_netdev 是否存在, 如果不存在创建, 如果存在, create = false,
        返回 0, 否则返回错误值

        如果 name 在 dp_netdevs 并且 dp->class = class && create = true, 返回 EEXIST
        如果 name 在 dp_netdevs 并且 dp->class = class && create = false,  返回 0
        如果 name 在 dp_netdevs 并且 dp->class != class,  返回 EINVAL
        如果 name 不在 dp_netdevs 并且 create = true,  dp_netdevs 增加 name 的 dp_netdev 对象并初始化该对象, dpifp 指向新的 dp_netdev
        如果 name 不在 dp_netdevs 并且 create = false, 返回 ENODEV


static int run(struct ofproto *ofproto_)

    1. 如果 !ofproto_get_flow_restore_wait(), 将 ofproto->pins 中的包以
    PACKET_IN 发送给控制器

    if (ofproto->netflow) netflow_run(ofproto->netflow);
    if (ofproto->sflow) dpif_sflow_run(ofproto->sflow);
    if (ofproto->ipfix) dpif_ipfix_run(ofproto->ipfix);
    if ofproto->change_seq 发生变化, 遍历所有端口, 调用 port_run(ofport);
    if (ofproto->lacp_enabled || ofproto->has_bonded_bundles) 遍历所有 ofproto->bundles, 调用 bundle_run(bundle);
    stp_run(ofproto);
    mac_learning_run(ofproto->ml)
    if ofproto->backer->udpif->dump_seq != ofproto->dump_seq, 遍历 ofproto->up.expirable 所有 rule, 调用 rule_expire(rule_dpif_cast(rule));
    if (ofproto->has_bonded_bundles) 遍历 ofproto->bundles, 调用 bond_rebalance(bundle->bond);
