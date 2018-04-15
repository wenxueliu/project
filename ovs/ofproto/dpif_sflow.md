

## sflow 实现原理


struct dpif_sflow {
    struct collectors *collectors;
    SFLAgent *sflow_agent;
    struct ofproto_sflow_options *options;
    time_t next_tick;
    size_t n_flood, n_all;
    struct hmap ports;          /* Contains "struct dpif_sflow_port"s. */
    uint32_t probability;     0 表示不采样任何包, UINT32_MAX 表示采样所有包.
    struct ovs_refcount ref_cnt;
};

