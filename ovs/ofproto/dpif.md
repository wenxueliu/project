
### dpif->handlers 与 dpif_netlink->handlers 的关系

    dpif_handler handler = &dpif->handlers[dpif->handlers[i]->handler_id];

    handler 属于 dpif
    handler->channels 中每一个 channels 对应到一个端口

### userspace 收 datapath 数据流程

每个 handler 接受所有端口的数据, 每次收一个端口的数据, 每次只接受一个消息 64 个消息

dpif_recv(udpif->dpif, handler->handler_id, upcall, buf)
    dpif->dpif_class->recv(udpif->dpif, handler->handler_id, upcall, buf)
        dpif_netlink_recv(udpif->dpif, handler->handler_id, upcall, buf)
            dpif_netlink_recv__(udpif->dpif, handler->handler_id, upcall, buf);
                handler = &dpif->handlers[handler_id]
                if (handler->event_offset >= handler->n_events)
                    handler->event_offset = handler->n_events = 0;
                    do {
                        retval = epoll_wait(handler->epoll_fd, handler->epoll_events,
                                            dpif->uc_array_size, 0);
                    } while (retval < 0 && errno == EINTR);
                    handler->n_events = retval;
                while (handler->event_offset < handler->n_events)
                    int idx = handler->epoll_events[handler->event_offset].data.u32;
                    struct dpif_channel *ch = &dpif->handlers[handler_id].channels[idx];
                    handler->event_offset++;
                    for (;;)
                        if (++read_tries > 50)
                            return EAGAIN;
                        nl_sock_recv(ch->sock, buf, false);
                        ch->last_poll = time_msec();
                        if (error)
                            if (error == EAGAIN)
                                break;
                            return error;
                        //用 buf 初始化 &dp_ifindex 和 upcall
                        parse_odp_packet(dpif, buf, upcall, &dp_ifindex);
                        if (!error && dp_ifindex == dpif->dp_ifindex)
                            return 0;
                        else if (error)
                            return error;
                return EAGAIN;






### 全局变量

/* Incremented whenever tnl route, arp, etc changes. */
struct seq *tnl_conf_seq;

### ofgroup 与 group_dpif 的关系

    CONTAINER_OF(group, struct group_dpif, up)

    group_dpif->up 为 ofgroup

### ofproto 与 ofproto_dpif 的关系

    ofproto_dpif->up 为 ofproto

### dpif 与 dpif_netlink 的关系

    dpif_netlink *dpif = CONTAINER_OF(dpif, struct dpif_netlink, dpif);

## dpif 与 dp_netdev 的关系

    dpif_netdev *dp_netdev = CONTAINER_OF(dpif, struct dpif_netdev, dpif)->dp

### 核心实现

void dpif_register_upcall_cb(struct dpif *dpif, upcall_callback *cb, void *aux)

    type=netdev: 用 aux 初始化 dpif->upcall_aux, 用 cb 初始化 dpif->cb
    type=system: 什么也不做

void dp_enumerate_types(struct sset *types)

int dp_enumerate_names(const char *type, struct sset *names)

    @type  : 目前为 system 或 netdev
    @names : 目前 type=system, 包含内核所有 dpif_netlink_dp 的 name. dp_netdevs 中 type 对应的 dp_netdev 的 name

    将 type 的 dpif_class 的 name 加入 names

    1. 如果 没有初始化, 先初始化(参考 dp_initialize)
    2. 在 dpif_classes 中查找 type 对应的 dpif_class;
    3. 调用 dpif_class->enumerate 初始化 names

    注:
    步骤 3
        type=netdev 对应 dpif_netdev_class
        type=system 对应 dpif_netlink_class

    步骤 4
    type=netdev : 从 dp_netdevs 中找到 class = dpif_class 的 dp_netdev 对象, 将 dp_netdev->name 保存在 all_dps 中
    type=system : 遍历查询内核中的所有 dpif_netlink_dp 对象, 将其 name 加入 all_dps


static void dp_initialize(void)

    1. 注册命令
    2. 将 base_dpif_classes 中的 dpif_netdev_class, dpif_netlink_class 加入 dpif_classes 并初始化

    其中, 注册命令

        dpctl/add-dp              dpctl_add_dp
        dpctl/del-dp              dpctl_del_dp
        dpctl/add-if              dpctl_add_if
        dpctl/del-if              dpctl_del_if
        dpctl/set-if              dpctl_set_if
        dpctl/dump-dps            dpctl_dump_dps
        dpctl/show                dpctl_show
        dpctl/dump-flows          dpctl_dump_flows
        dpctl/add-flow            dpctl_add_flow
        dpctl/mod-flow            dpctl_mod_flow
        dpctl/get-flow            dpctl_get_flow
        dpctl/del-flow            dpctl_del_flow
        dpctl/del-flows           dpctl_del_flows
        dpctl/help                dpctl_help
        dpctl/list-commands       dpctl_list_commands
        dpctl/parse-actions       dpctl_parse_actions
        dpctl/normalize-actions   dpctl_normalize_actions
        tnl/ports/show            tnl_port_show
        tnl/arp/show                tnl_arp_cache_show
        tnl/arp/flush               tnl_arp_cache_flush
        ovs/route/add               ovs_router_add
        ovs/route/show              ovs_router_show
        ovs/route/del               ovs_router_del
        ovs/route/lookup            ovs_router_lookup_cmd
        dpif-netdev/pmd-stats-show  dpif_netdev_pmd_info
        dpif-netdev/pmd-stats-clear dpif_netdev_pmd_info

    2. 调用 base_dpif_classes 中元素的 init() 方法并加入 dpif_classes
    (dpif_netdev_class->init(), dpif_netlink_class->init() 并将 dpif_netdev_class
    与 dpif_netlink_class 加入 dpif_classes)

    ###dpif_netdev_class->init()

    注册
          dpif-netdev/pmd-stats-show    dpif_netdev_pmd_info
          dpif-netdev/pmd-stats-clear   dpif_netdev_pmd_info
    命令

    ###dpif_netlink_class->init()

    什么也不做

    //1. 与内核建立 NETLINK_GENERIC 协议连接, 发送请求获取 name (genl_family->name) 对应的 number(genl_family->id)
    //2. 将 OVS_DATAPATH_FAMILY, OVS_VPORT_FAMILY, OVS_FLOW_FAMILY 加入 genl_families
    //3. 确保 OVS_VPORT_FAMILY 中存在 OVS_VPORT_MCGROUP 对应 ID 的 ovs_vport_mcgroup

    //genl_family:
    //      id                 name
    //OVS_DATAPATH_FAMILY ovs_datapath_family
    //OVS_VPORT_FAMILY    ovs_vport_family
    //OVS_FLOW_FAMILY     ovs_flow_family
    //OVS_PACKET_FAMILY   ovs_packet_family

    //                  CTRL_ATTR_MCAST_GRP_NAME CTRL_ATTR_MCAST_GRP_ID
    //OVS_VPORT_FAMILY     OVS_VPORT_FAMILY         ovs_vport_mcgroup


int dp_register_provider(const struct dpif_class *new_class)

    @new_class : 待注册的 dpif_class, 实际为 dpif_netlink_class, dpif_netdev_class

    0. 检查 new_class 是否已经加入 dpif_classes 或 dpif_blacklist, 如果加入返回, 否则继续步骤 1
    1. 调用 new_class->init() (实际调用 dpif_netlink_class->init() 和 dpif_netdev_class->init())
    2. 将 new_class 加入 dpif_classes(将 dpif_netdev_class 和 dpif_netlink_class 加入 dpif_classes)

    注意: 在 dpif_classes 中每个 new_class->type 是唯一的

static int dp_register_provider__(const struct dpif_class *new_class)

    @new_class : 待注册的 dpif_class, 实际为 dpif_netlink_class, dpif_netdev_class

    1. 检查 new_class 如果加入 dpif_classes 返回 EEXIST, 如果加入 dpif_blacklist 返回 EINVAL, 否则继续步骤 1
    2. 调用 new_class->init() (实际调用 dpif_netlink_class->init() 和 dpif_netdev_class->init())
    3. 将 new_class 加入 dpif_classes(将 dpif_netdev_class 和 dpif_netlink_class 加入 dpif_classes)

    注意: 在 dpif_classes 中每个 new_class->type 是唯一的

