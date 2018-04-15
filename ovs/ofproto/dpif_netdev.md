
1. dpif_netdev_enable_upcall 与 dpif_netdev_disable_upcall 的作用时什么?

## 数据结构

dp_netdevs 保存所有的 dp_netdev


## 全局变量

static struct shash dp_netdevs

struct dpif_handler {
    struct dpif_channel *channels;  //对应一个端口
    struct epoll_event *epoll_events;
    int epoll_fd;                 //
    int n_events;                 //epoll_wait 返回的满足条件的事件个数
    int event_offset;             //已经处理的事件偏移
};

struct dpif_netlink {
    struct dpif dpif;
    int dp_ifindex;

    /* Upcall messages. */
    struct fat_rwlock upcall_lock;
    struct dpif_handler *handlers; //所有的 handler
    uint32_t n_handlers;           //handlers 的数量
    int uc_array_size;             // 与 'handler->channels' 和 'handler->epoll_events' 相同.

    /* Change notification. */
    struct nl_sock *port_notifier; /* vport multicast group subscriber. */
    bool refresh_channels;
};




void dpif_register_upcall_cb(struct dpif *dpif, upcall_callback *cb, void *aux)

    struct dp_netdev *dp = get_dp_netdev(dpif);
    dp->upcall_aux = aux;
    dp->upcall_cb = cb;


static int dpif_netdev_enumerate(struct sset *all_dps, const struct dpif_class *dpif_class)

    从 dp_netdevs 中找到 class == dpif_class 的 dp_netdev 对象, 将 dp_netdev->name 保存在 all_dps 中
    注: 被 dpif.c/dp_enumerate_names 调用


static int dpif_netdev_open(const struct dpif_class *class, const char *name, bool create, struct dpif **dpifp)

    检查 name, class 对应的 dp_netdev 是否存在于 dp_netdevs, 如果不存在创建, 如果存在, create = false,
    返回 0, 否则返回错误值

    如果 name 在 dp_netdevs 并且 dp->class = class && create = true, 返回 EEXIST
    如果 name 在 dp_netdevs 并且 dp->class = class && create = false,  返回 0
    如果 name 在 dp_netdevs 并且 dp->class != class,  返回 EINVAL
    如果 name 不在 dp_netdevs 并且 create = true, dp_netdevs 增加 name 的 dp_netdev 对象并初始化该对象, dpifp 指向新的 dp_netdev
    如果 name 不在 dp_netdevs 并且 create = false, 返回 ENODEV

static int dpif_netlink_open(const struct dpif_class *class OVS_UNUSED, const char *name, bool create, struct dpif **dpifp)

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
         dp_request.user_features |= OVS_DP_F_UNALIGNED | OVS_DP_F_VPORT_PIDS;
      否则
         dp_request.cmd = OVS_DP_CMD_SET;
         dp_request.upcall_pid = 0;
         dp_request.name = name;
         dp_request.user_features |= OVS_DP_F_UNALIGNED | OVS_DP_F_VPORT_PIDS;

    问题: 不管 create 最终都会导致 dpifp 指向一个新分配的 dpif_netlink, 这是否是期望的?


const struct dpif_class dpif_netdev_class = {
    "netdev",
    dpif_netdev_init,
    dpif_netdev_enumerate,
    dpif_netdev_port_open_type,
    dpif_netdev_open,
    dpif_netdev_close,
    dpif_netdev_destroy,
    dpif_netdev_run,
    dpif_netdev_wait,
    dpif_netdev_get_stats,
    dpif_netdev_port_add,
    dpif_netdev_port_del,
    dpif_netdev_port_query_by_number,
    dpif_netdev_port_query_by_name,
    NULL,                       /* port_get_pid */
    dpif_netdev_port_dump_start,
    dpif_netdev_port_dump_next,
    dpif_netdev_port_dump_done,
    dpif_netdev_port_poll,
    dpif_netdev_port_poll_wait,
    dpif_netdev_flow_flush,
    dpif_netdev_flow_dump_create,
    dpif_netdev_flow_dump_destroy,
    dpif_netdev_flow_dump_thread_create,
    dpif_netdev_flow_dump_thread_destroy,
    dpif_netdev_flow_dump_next,
    dpif_netdev_operate,
    NULL,                       /* recv_set */
    NULL,                       /* handlers_set */
    dpif_netdev_pmd_set,
    dpif_netdev_queue_to_priority,
    NULL,                       /* recv */
    NULL,                       /* recv_wait */
    NULL,                       /* recv_purge */
    dpif_netdev_register_upcall_cb,
    dpif_netdev_enable_upcall,
    dpif_netdev_disable_upcall,
    dpif_netdev_get_datapath_version,
};
