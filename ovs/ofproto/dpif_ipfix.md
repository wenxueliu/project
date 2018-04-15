struct ofproto_ipfix_bridge_exporter_options {
    struct sset targets;
    uint32_t sampling_rate;
    uint32_t obs_domain_id;  /* Bridge-wide Observation Domain ID. */
    uint32_t obs_point_id;  /* Bridge-wide Observation Point ID. */
    uint32_t cache_active_timeout;
    uint32_t cache_max_flows;
    bool enable_tunnel_sampling;    //是否对 tunnel 进行采样
    bool enable_input_sampling;     //是否对输入端口采样 ipfix 使用该标志
    bool enable_output_sampling;
};

struct dpif_ipfix_bridge_exporter {
    struct dpif_ipfix_exporter exporter;
    struct ofproto_ipfix_bridge_exporter_options *options;
    uint32_t probability;
};

struct dpif_ipfix {
    struct dpif_ipfix_bridge_exporter bridge_exporter;
    struct hmap flow_exporter_map;  /* dpif_ipfix_flow_exporter_map_node. */
    struct hmap tunnel_ports;       /* Contains "struct dpif_ipfix_port"s.
                                     * It makes tunnel port lookups faster in
                                     * sampling upcalls. */
    struct ovs_refcount ref_cnt;
};
