
## 全局变量

static int dpif_netlink_enumerate(struct sset *all_dps, const struct dpif_class *dpif_class OVS_UNUSED)

    遍历查询内核中的所有 dpif_netlink_dp 对象, 将其 name 加入 all_dps

    1. 将 OVS_DATAPATH_FAMILY, OVS_VPORT_FAMILY, OVS_FLOW_FAMILY 加入 genl_families
    2. 确保 OVS_VPORT_FAMILY 对应的组属性中存在 OVS_VPORT_MCGROUP
    3. 构造 OVS_DP_CMD_GET 的消息发送给 NETLINK_GENERIC 对应的 sock 的消息并初始化 dump.
       初始化后的 dump :
       1. dump->sock 为 NETLINK_GENERIC 对应的 sock
       2. dump->nl_seq 为 dump->sock->next_seq + 1;
       3. dump->status 为将 buf 发送给 NETLINK_GENERIC 对应的 sock 的状态
    4. 将接收内核的消息解析为 dpif_netlink_dp , 并将 dpif_netlink_dp 的 name 加入 all_dps

    注: 被 dpif.c/dp_enumerate_names 调用


const struct dpif_class dpif_netlink_class = {
    "system",
    NULL,                       /* init */
    dpif_netlink_enumerate,
    NULL,
    dpif_netlink_open,
    dpif_netlink_close,
    dpif_netlink_destroy,
    dpif_netlink_run,
    NULL,                       /* wait */
    dpif_netlink_get_stats,
    dpif_netlink_port_add,
    dpif_netlink_port_del,
    dpif_netlink_port_query_by_number,
    dpif_netlink_port_query_by_name,
    dpif_netlink_port_get_pid,
    dpif_netlink_port_dump_start,
    dpif_netlink_port_dump_next,
    dpif_netlink_port_dump_done,
    dpif_netlink_port_poll,
    dpif_netlink_port_poll_wait,
    dpif_netlink_flow_flush,
    dpif_netlink_flow_dump_create,
    dpif_netlink_flow_dump_destroy,
    dpif_netlink_flow_dump_thread_create,
    dpif_netlink_flow_dump_thread_destroy,
    dpif_netlink_flow_dump_next,
    dpif_netlink_operate,
    dpif_netlink_recv_set,
    dpif_netlink_handlers_set,
    NULL,                       /* poll_thread_set */
    dpif_netlink_queue_to_priority,
    dpif_netlink_recv,
    dpif_netlink_recv_wait,
    dpif_netlink_recv_purge,
    NULL,                       /* register_upcall_cb */
    NULL,                       /* enable_upcall */
    NULL,                       /* disable_upcall */
    dpif_netlink_get_datapath_version, /* get_datapath_version */
};
