

1. xbridge->xports xcfg->ports xbundles->xports 之间的关系

xport 在 xbundle 中以 list 保存, 在 xbridge, xcfg->ports 中以 hash_map 保存

2. xport 与 xbundle 的关系

一个 xbundle 包含一组 xport

3. ofp_port_t, odp_port_t, ofp11_port_t

    ofp_port_t : the port number of a OpenFlow switch.
    odp_port_t : the port number on the datapath.
    ofp11_port_t : the OpenFlow-1.1 port number.

    ofp_port_t 与 odp_port_t 通过 xport 关联

    xbridge->xports 通过 ofp_port 找到 xport
    xport->odp_port 为 odp_port_t

4. group 如何选择 bucket, group 支持那些操作

    group 选择 bucket 的时候默认时选择最合适的 bucket,
    也支持根据 hash 结果选择 bucket, 参见 xlate_select_group

    case OFPGT11_ALL:
    case OFPGT11_INDIRECT:
    case OFPGT11_SELECT:
    case OFPGT11_FF:

5. xbridge, mbridge, bridge

    mbridge : 与 mirror 有关的 bridge
    xbridge : 包含 mbridge

6. 收到包后哪些包将被丢弃 ?

    1. Drop malformed frames.
    2. Drop frames on bundles reserved for mirroring.
    3. input vid is not valid
    4. when packets in 'flow' within 'xbridge' should be dropped.

7. cfm, bfd, lacp, stp, lldp 协议在哪里被处理?

    process_special 函数

8. 用户态给内核发送流表的函数是什么?

    ofproto_dpif_execute_actions
        dpif_execute(ofproto->backer->dpif, &execute);
            op.type = DPIF_OP_EXECUTE;
            op.u.execute = *execute;
            opp = &op;
            dpif_operate(dpif, &opp, 1)
                dpif->dpif_class->operate(dpif, ops, chunk);

9. 指向 action 的流程

    do_xlate_actions(ofpacts, ofpacts_len, &ctx);
        case OFPACT_OUTPUT:
            xlate_output_action(ctx, ofpact_get_OUTPUT(a)->port, ofpact_get_OUTPUT(a)->max_len, true);
                switch (port)
                    case OFPP_IN_PORT: compose_output_action(ctx, ctx->xin->flow.in_port.ofp_port, NULL);
                    case OFPP_TABLE: xlate_table_action(ctx, ctx->xin->flow.in_port.ofp_port, 0, may_packet_in, true);
                    case OFPP_NORMAL: xlate_normal(ctx);
                    case OFPP_FLOOD: flood_packets(ctx,  false);
                    case OFPP_ALL: flood_packets(ctx, true);
                    case OFPP_CONTROLLER: execute_controller_action(ctx, max_len, (ctx->in_group ? OFPR_GROUP : ctx->in_action_set ? OFPR_ACTION_SET : OFPR_ACTION), 0);
                    case OFPP_NONE: 什么也不做
                    case OFPP_LOCAL:
                    default:
                            if (port != ctx->xin->flow.in_port.ofp_port) compose_output_action(ctx, port, NULL);
        case OFPACT_GROUP:
            group = group_dpif_lookup(ctx->xbridge->ofproto, group_id, &group);
            if (group)
                xlate_group_action(ctx, ofpact_get_GROUP(a)->group_id)
                    case OFPGT11_ALL:
                    case OFPGT11_INDIRECT:
                        xlate_all_group(ctx, group);
                            group_dpif_get_buckets(group, &buckets);
                            LIST_FOR_EACH (bucket, list_node, buckets)
                                xlate_group_bucket(ctx, bucket);
                    case OFPGT11_SELECT:
                        xlate_select_group(ctx, group);
                            const char *selection_method = group_dpif_get_selection_method(group);
                            if (selection_method[0] == '\0')
                                xlate_default_select_group(ctx, group);
                                    basis = flow_hash_symmetric_l4(&ctx->xin->flow, 0);
                                    flow_mask_hash_fields(&ctx->xin->flow, wc, NX_HASH_FIELDS_SYMMETRIC_L4);
                                    bucket = group_best_live_bucket(ctx, group, basis);
                                    if (bucket)
                                        xlate_group_bucket(ctx, bucket);
                            else if (!strcasecmp("hash", selection_method))
                                xlate_hash_fields_select_group(ctx, group);
                                    fields = group->up.props.fields
                                    basis = hash_uint64(group->up.props.selection_method_param);
                                    bucket = group_best_live_bucket(ctx, group, basis);
                                    if (bucket)
                                        xlate_group_bucket(ctx, bucket);
                    case OFPGT11_FF:
                        xlate_ff_group(ctx, group);
                            bucket = group_first_live_bucket(ctx, group, 0);
                            if (bucket)
                                xlate_group_bucket(ctx, bucket);
        case OFPACT_CONTROLLER: execute_controller_action(ctx, controller->max_len, controller->reason, controller->controller_id);
        case OFPACT_ENQUEUE: xlate_enqueue_action(ctx, ofpact_get_ENQUEUE(a));
        case OFPACT_SET_VLAN_VID: flow->vlan_tci |= (htons(ofpact_get_SET_VLAN_VID(a)->vlan_vid) | htons(VLAN_CFI));
        case OFPACT_SET_VLAN_PCP: flow->vlan_tci |= htons((ofpact_get_SET_VLAN_PCP(a)->vlan_pcp << VLAN_PCP_SHIFT) | VLAN_CFI);
        case OFPACT_STRIP_VLAN: flow->vlan_tci = htons(0);
        case OFPACT_PUSH_VLAN: flow->vlan_tci = htons(VLAN_CFI);
        case OFPACT_SET_ETH_SRC: memcpy(flow->dl_src, ofpact_get_SET_ETH_SRC(a)->mac, ETH_ADDR_LEN);
        case OFPACT_SET_ETH_DST: memcpy(flow->dl_dst, ofpact_get_SET_ETH_DST(a)->mac, ETH_ADDR_LEN);
        case OFPACT_SET_IPV4_SRC: flow->nw_src = ofpact_get_SET_IPV4_SRC(a)->ipv4;
        case OFPACT_SET_IPV4_DST: flow->nw_dst = ofpact_get_SET_IPV4_DST(a)->ipv4;
        case OFPACT_SET_IP_DSCP: flow->nw_tos |= ofpact_get_SET_IP_DSCP(a)->dscp;
        case OFPACT_SET_IP_ECN: flow->nw_tos |= ofpact_get_SET_IP_ECN(a)->ecn;
        case OFPACT_SET_IP_TTL: flow->nw_ttl = ofpact_get_SET_IP_TTL(a)->ttl;
        case OFPACT_SET_L4_SRC_PORT: flow->tp_src = htons(ofpact_get_SET_L4_SRC_PORT(a)->port);
        case OFPACT_SET_L4_DST_PORT: flow->tp_dst = htons(ofpact_get_SET_L4_DST_PORT(a)->port);
        case OFPACT_RESUBMIT: xlate_ofpact_resubmit(ctx, ofpact_get_RESUBMIT(a));
        case OFPACT_SET_TUNNEL: flow->tunnel.tun_id = htonll(ofpact_get_SET_TUNNEL(a)->tun_id);
        case OFPACT_SET_QUEUE: xlate_set_queue_action(ctx, ofpact_get_SET_QUEUE(a)->queue_id);
        case OFPACT_POP_QUEUE: flow->skb_priority = ctx->orig_skb_priority;
        case OFPACT_REG_MOVE: nxm_execute_reg_move(ofpact_get_REG_MOVE(a), flow, wc);
        case OFPACT_SET_FIELD: TODO
        case OFPACT_STACK_PUSH: nxm_execute_stack_push(ofpact_get_STACK_PUSH(a), flow, wc, &ctx->stack);
        case OFPACT_STACK_POP: nxm_execute_stack_pop(ofpact_get_STACK_POP(a), flow, wc, &ctx->stack);
        case OFPACT_PUSH_MPLS: compose_mpls_push_action(ctx, ofpact_get_PUSH_MPLS(a));
        case OFPACT_POP_MPLS: compose_mpls_pop_action(ctx, ofpact_get_POP_MPLS(a)->ethertype);
        case OFPACT_SET_MPLS_LABEL: compose_set_mpls_label_action( ctx, ofpact_get_SET_MPLS_LABEL(a)->label);
        case OFPACT_SET_MPLS_TC: compose_set_mpls_tc_action(ctx, ofpact_get_SET_MPLS_TC(a)->tc);
        case OFPACT_SET_MPLS_TTL: compose_set_mpls_ttl_action(ctx, ofpact_get_SET_MPLS_TTL(a)->ttl);
        case OFPACT_DEC_MPLS_TTL: compose_dec_mpls_ttl_action(ctx))
        case OFPACT_DEC_TTL: compose_dec_ttl(ctx, ofpact_get_DEC_TTL(a)))
        case OFPACT_NOTE:
        case OFPACT_MULTIPATH: multipath_execute(ofpact_get_MULTIPATH(a), flow, wc);
        case OFPACT_BUNDLE: xlate_bundle_action(ctx, ofpact_get_BUNDLE(a));
        case OFPACT_OUTPUT_REG: xlate_output_reg_action(ctx, ofpact_get_OUTPUT_REG(a));
        case OFPACT_LEARN: xlate_learn_action(ctx, ofpact_get_LEARN(a));
        case OFPACT_CONJUNCTION:
        case OFPACT_EXIT:
        case OFPACT_UNROLL_XLATE:
            struct ofpact_unroll_xlate *unroll = ofpact_get_UNROLL_XLATE(a);
            ctx->table_id = unroll->rule_table_id;
            ctx->rule_cookie = unroll->rule_cookie;
        case OFPACT_FIN_TIMEOUT:
            xlate_fin_timeout(ctx, ofpact_get_FIN_TIMEOUT(a));
        case OFPACT_CLEAR_ACTIONS:
            ofpbuf_clear(&ctx->action_set);
            ctx->xin->flow.actset_output = OFPP_UNSET;
            ctx->action_set_has_group = false;
        case OFPACT_WRITE_ACTIONS: xlate_write_actions(ctx, a);
        case OFPACT_WRITE_METADATA: flow->metadata |= metadata->metadata & metadata->mask;
        case OFPACT_METER:
        case OFPACT_GOTO_TABLE: xlate_table_action(ctx, ctx->xin->flow.in_port.ofp_port, ogt->table_id, true, true);
        case OFPACT_SAMPLE: xlate_sample_action(ctx, ofpact_get_SAMPLE(a));
        case OFPACT_DEBUG_RECIRC: ctx_trigger_recirculation(ctx);

10. xlate_in 与 xlate_out 的关系

它们通过 xlate_ctx 关联起来





### PACKET_IN 的路径

    execute_controller_action(struct xlate_ctx *ctx, int len, enum ofp_packet_in_reason reason, uint16_t controller_id)
        odp_execute_actions(NULL, &packet, 1, false, ctx->odp_actions->data, ctx->odp_actions->size, NULL);
        ofproto_dpif_send_packet_in(ctx->xbridge->ofproto, pin);



## 设计

以 ofproto_dpif 来索引 xbridge, xbridge 包含多个 xbundle, xport; xbundle 包含
多个 xport, xport 属于 xbridge, xbundle

本文件主要功能

1. xbridge, xbundle, xport 的 CRUD 已经查询
2. rstp, stp 收到包如何处理
3. group 如何选择 bucket
4. mbridge, mbundle

## 数据结构

static OVSRCU_TYPE(struct xlate_cfg *) xcfgp = OVSRCU_INITIALIZER(NULL); //当前配置
static struct xlate_cfg *new_xcfg = NULL; //当更改配置时, 新的配置保存在

注:

* xcfgp->xbridges 中以 hash_pointer(xbridge->ofproto, 0) 来唯一索引 xbridge
* xcfg->xbundles 中以 hash_pointer(xbundle->ofbundle, 0) 索引 xbundle
* xcfg->xport 中以 hash_pointer(xport->ofport, 0) 索引 xport
* xport->xbridge->xports 中以 hash_ofp_port(xport->ofp_port) 索引 xport
* xport->peer 以 xport->peer->ofport 为索引, xport->peer->peer = xport
* xport->skb_priorities 以 hash_int(pdscp->skb_priority, 0) 为索引
* mbridge->mbundles 以 hash_pointer(ofbundle, 0) 为索引


struct xlate_out {
    enum slow_path_reason slow; /* 0 if fast path may be used. */
    bool fail_open;             /* Initial rule is fail open? */

    /* Recirculation IDs on which references are held. */
    unsigned n_recircs;
    union {
        uint32_t recirc[2];   /* When n_recircs == 1 or 2 */
        uint32_t *recircs;    /* When 'n_recircs' > 2 */
    };
};

struct xlate_in {
    struct ofproto_dpif *ofproto;

    /* Flow to which the OpenFlow actions apply.  xlate_actions() will modify
     * this flow when actions change header fields. */
    struct flow flow;

    /* The packet corresponding to 'flow', or a null pointer if we are
     * revalidating without a packet to refer to. */
    const struct dp_packet *packet;

    /* Should OFPP_NORMAL update the MAC learning table?  Should "learn"
     * actions update the flow table?
     *
     * We want to update these tables if we are actually processing a packet,
     * or if we are accounting for packets that the datapath has processed, but
     * not if we are just revalidating. */
    bool may_learn; //是否应该尝试更新 ml 表

    /* The rule initiating translation or NULL. If both 'rule' and 'ofpacts'
     * are NULL, xlate_actions() will do the initial rule lookup itself. */
    struct rule_dpif *rule;

    /* The actions to translate.  If 'rule' is not NULL, these may be NULL. */
    const struct ofpact *ofpacts;
    size_t ofpacts_len;

    /* Union of the set of TCP flags seen so far in this flow.  (Used only by
     * NXAST_FIN_TIMEOUT.  Set to zero to avoid updating updating rules'
     * timeouts.) */
    uint16_t tcp_flags;

    /* If nonnull, flow translation calls this function just before executing a
     * resubmit or OFPP_TABLE action.  In addition, disables logging of traces
     * when the recursion depth is exceeded.
     *
     * 'rule' is the rule being submitted into.  It will be null if the
     * resubmit or OFPP_TABLE action didn't find a matching rule.
     *
     * 'recurse' is the resubmit recursion depth at time of invocation.
     *
     * This is normally null so the client has to set it manually after
     * calling xlate_in_init(). */
    void (*resubmit_hook)(struct xlate_in *, struct rule_dpif *rule,
                          int recurse);

    /* If nonnull, flow translation calls this function to report some
     * significant decision, e.g. to explain why OFPP_NORMAL translation
     * dropped a packet.  'recurse' is the resubmit recursion depth at time of
     * invocation. */
    void (*report_hook)(struct xlate_in *, int recurse,
                        const char *format, va_list args);

    /* If nonnull, flow translation credits the specified statistics to each
     * rule reached through a resubmit or OFPP_TABLE action.
     *
     * This is normally null so the client has to set it manually after
     * calling xlate_in_init(). */
    const struct dpif_flow_stats *resubmit_stats;

    /* If nonnull, flow translation populates this cache with references to all
     * modules that are affected by translation. This 'xlate_cache' may be
     * passed to xlate_push_stats() to perform the same function as
     * xlate_actions() without the full cost of translation.
     *
     * This is normally null so the client has to set it manually after
     * calling xlate_in_init(). */
    struct xlate_cache *xcache;

    /* If nonnull, flow translation puts the resulting datapath actions in this
     * buffer.  If null, flow translation will not produce datapath actions. */
    struct ofpbuf *odp_actions;

    /* If nonnull, flow translation populates this with wildcards relevant in
     * translation.  Any fields that were used to calculate the action are set,
     * to allow caching and kernel wildcarding to work.  For example, if the
     * flow lookup involved performing the "normal" action on IPv4 and ARP
     * packets, 'wc' would have the 'in_port' (always set), 'dl_type' (flow
     * match), 'vlan_tci' (normal action), and 'dl_dst' (normal action) fields
     * set. */
    struct flow_wildcards *wc;

    /* The recirculation context related to this translation, as returned by
     * xlate_lookup. */
    const struct recirc_id_node *recirc;
};

struct xbridge {
    struct hmap_node hmap_node;   /* Node in global 'xbridges' map. */
    struct ofproto_dpif *ofproto; /* Key in global 'xbridges' map. */

    struct ovs_list xbundles;     /* Owned xbundles. */
    struct hmap xports;           /* Indexed by ofp_port. */

    char *name;                   /* Name used in log messages. */
    struct dpif *dpif;            /* Datapath interface. */
    struct mac_learning *ml;      /* Mac learning handle. */
    struct mcast_snooping *ms;    /* Multicast Snooping handle. */
    struct mbridge *mbridge;      /* Mirroring. */
    struct dpif_sflow *sflow;     /* SFlow handle, or null. */
    struct dpif_ipfix *ipfix;     /* Ipfix handle, or null. */
    struct netflow *netflow;      /* Netflow handle, or null. */
    struct stp *stp;              /* STP or null if disabled. */
    struct rstp *rstp;            /* RSTP or null if disabled. */

    bool has_in_band;             /* Bridge has in band control? */
    bool forward_bpdu;            /* Bridge forwards STP BPDUs? */

    /* Datapath feature support. */
    struct dpif_backer_support support;
};


struct xbundle {
    struct hmap_node hmap_node;    /* In global 'xbundles' map. */
    struct ofbundle *ofbundle;     /* Key in global 'xbundles' map. */

    struct ovs_list list_node;     /* In parent 'xbridges' list. */
    struct xbridge *xbridge;       /* Parent xbridge. */

    struct ovs_list xports;        /* Contains "struct xport"s. */

    char *name;                    /* Name used in log messages. */
    struct bond *bond;             /* Nonnull iff more than one port. */
    struct lacp *lacp;             /* LACP handle or null. */

    enum port_vlan_mode vlan_mode; /* VLAN mode. */
    int vlan;                      /* -1=trunk port, else a 12-bit VLAN ID. */
    unsigned long *trunks;         /* Bitmap of trunked VLANs, if 'vlan' == -1.
                                    * NULL if all VLANs are trunked. */
    bool use_priority_tags;        /* Use 802.1p tag for frames in VLAN 0? */
    bool floodable;                /* No port has OFPUTIL_PC_NO_FLOOD set? */
};

struct xport {
    struct hmap_node hmap_node;      /* Node in global 'xports' map. */
    struct ofport_dpif *ofport;      /* Key in global 'xports map. */

    struct hmap_node ofp_node;       /* Node in parent xbridge 'xports' map. */
    ofp_port_t ofp_port;             /* Key in parent xbridge 'xports' map. */

    odp_port_t odp_port;             /* Datapath port number or ODPP_NONE. */

    struct ovs_list bundle_node;     /* In parent xbundle (if it exists). */
    struct xbundle *xbundle;         /* Parent xbundle or null. */

    struct netdev *netdev;           /* 'ofport''s netdev. */

    struct xbridge *xbridge;         /* Parent bridge. */
    struct xport *peer;              /* Patch port peer or null. */

    enum ofputil_port_config config; /* OpenFlow port configuration. */
    enum ofputil_port_state state;   /* OpenFlow port state. */
    int stp_port_no;                 /* STP port number or -1 if not in use. */
    struct rstp_port *rstp_port;     /* RSTP port or null. */

    struct hmap skb_priorities;      /* Map of 'skb_priority_to_dscp's. */

    bool may_enable;                 /* May be enabled in bonds. */
    bool is_tunnel;                  /* Is a tunnel port. */

    struct cfm *cfm;                 /* CFM handle or null. */
    struct bfd *bfd;                 /* BFD handle or null. */
    struct lldp *lldp;               /* LLDP handle or null. */
};

struct xlate_ctx {
    struct xlate_in *xin;
    struct xlate_out *xout;

    const struct xbridge *xbridge;

    /* Flow tables version at the beginning of the translation. */
    cls_version_t tables_version;

    /* Flow at the last commit. */
    struct flow base_flow;

    /* Tunnel IP destination address as received.  This is stored separately
     * as the base_flow.tunnel is cleared on init to reflect the datapath
     * behavior.  Used to make sure not to send tunneled output to ourselves,
     * which might lead to an infinite loop.  This could happen easily
     * if a tunnel is marked as 'ip_remote=flow', and the flow does not
     * actually set the tun_dst field. */
    ovs_be32 orig_tunnel_ip_dst;

    /* Stack for the push and pop actions.  Each stack element is of type
     * "union mf_subvalue". */
    struct ofpbuf stack;

    /* The rule that we are currently translating, or NULL. */
    struct rule_dpif *rule;

    /* Flow translation populates this with wildcards relevant in translation.
     * When 'xin->wc' is nonnull, this is the same pointer.  When 'xin->wc' is
     * null, this is a pointer to uninitialized scratch memory.  This allows
     * code to blindly write to 'ctx->wc' without worrying about whether the
     * caller really wants wildcards. */
    struct flow_wildcards *wc;

    /* Output buffer for datapath actions.  When 'xin->odp_actions' is nonnull,
     * this is the same pointer.  When 'xin->odp_actions' is null, this points
     * to a scratch ofpbuf.  This allows code to add actions to
     * 'ctx->odp_actions' without worrying about whether the caller really
     * wants actions. */
    struct ofpbuf *odp_actions;

    /* Resubmit statistics, via xlate_table_action(). */
    int recurse;                /* Current resubmit nesting depth. */
    int resubmits;              /* Total number of resubmits. */
    bool in_group;              /* Currently translating ofgroup, if true. */
    bool in_action_set;         /* Currently translating action_set, if true. */

    uint8_t table_id;           /* OpenFlow table ID where flow was found. */
    ovs_be64 rule_cookie;       /* Cookie of the rule being translated. */
    uint32_t orig_skb_priority; /* Priority when packet arrived. 在 OFPACT_POP_QUEUE 时使用
    uint32_t sflow_n_outputs;   // 包输出到多少个端口
    odp_port_t sflow_odp_port;  // 包输出的端口, 与 xbridge->sflow->ports 中的一个端口对应
    ofp_port_t nf_output_iface; /* Output interface index for NetFlow. */
    bool exit;                  /* No further actions should be processed. */
    mirror_mask_t mirrors;      /* Bitmap of associated mirrors. */

   /* These are used for non-bond recirculation.  The recirculation IDs are
    * stored in xout and must be associated with a datapath flow (ukey),
    * otherwise they will be freed when the xout is uninitialized.
    *
    *
    * Steps in Recirculation Translation
    * ==================================
    *
    * At some point during translation, the code recognizes the need for
    * recirculation.  For example, recirculation is necessary when, after
    * popping the last MPLS label, an action or a match tries to examine or
    * modify a field that has been newly revealed following the MPLS label.
    *
    * The simplest part of the work to be done is to commit existing changes to
    * the packet, which produces datapath actions corresponding to the changes,
    * and after this, add an OVS_ACTION_ATTR_RECIRC datapath action.
    *
    * The main problem here is preserving state.  When the datapath executes
    * OVS_ACTION_ATTR_RECIRC, it will upcall to userspace to get a translation
    * for the post-recirculation actions.  At this point userspace has to
    * resume the translation where it left off, which means that it has to
    * execute the following:
    *
    *     - The action that prompted recirculation, and any actions following
    *       it within the same flow.
    *
    *     - If the action that prompted recirculation was invoked within a
    *       NXAST_RESUBMIT, then any actions following the resubmit.  These
    *       "resubmit"s can be nested, so this has to go all the way up the
    *       control stack.
    *
    *     - The OpenFlow 1.1+ action set.
    *
    * State that actions and flow table lookups can depend on, such as the
    * following, must also be preserved:
    *
    *     - Metadata fields (input port, registers, OF1.1+ metadata, ...).
    *
    *     - Action set, stack
    *
    *     - The table ID and cookie of the flow being translated at each level
    *       of the control stack (since OFPAT_CONTROLLER actions send these to
    *       the controller).
    *
    * Translation allows for the control of this state preservation via these
    * members.  When a need for recirculation is identified, the translation
    * process:
    *
    * 1. Sets 'recirc_action_offset' to the current size of 'action_set'.  The
    *    action set is part of what needs to be preserved, so this allows the
    *    action set and the additional state to share the 'action_set' buffer.
    *    Later steps can tell that setup for recirculation is in progress from
    *    the nonnegative value of 'recirc_action_offset'.
    *
    * 2. Sets 'exit' to true to tell later steps that we're exiting from the
    *    translation process.
    *
    * 3. Adds an OFPACT_UNROLL_XLATE action to 'action_set'.  This action
    *    holds the current table ID and cookie so that they can be restored
    *    during a post-recirculation upcall translation.
    *
    * 4. Adds the action that prompted recirculation and any actions following
    *    it within the same flow to 'action_set', so that they can be executed
    *    during a post-recirculation upcall translation.
    *
    * 5. Returns.
    *
    * 6. The action that prompted recirculation might be nested in a stack of
    *    nested "resubmit"s that have actions remaining.  Each of these notices
    *    that we're exiting (from 'exit') and that recirculation setup is in
    *    progress (from 'recirc_action_offset') and responds by adding more
    *    OFPACT_UNROLL_XLATE actions to 'action_set', as necessary, and any
    *    actions that were yet unprocessed.
    *
    * The caller stores all the state produced by this process associated with
    * the recirculation ID.  For post-recirculation upcall translation, the
    * caller passes it back in for the new translation to execute.  The
    * process yielded a set of ofpacts that can be translated directly, so it
    * is not much of a special case at that point.
    */
    int recirc_action_offset;   /* Offset in 'action_set' to actions to be
                                 * executed after recirculation, or -1. */
    int last_unroll_offset;     /* Offset in 'action_set' to the latest unroll
                                 * action, or -1. */

    /* True if a packet was but is no longer MPLS (due to an MPLS pop action).
     * This is a trigger for recirculation in cases where translating an action
     * or looking up a flow requires access to the fields of the packet after
     * the MPLS label stack that was originally present. */
    bool was_mpls;

    /* OpenFlow 1.1+ action set.
     *
     * 'action_set' accumulates "struct ofpact"s added by OFPACT_WRITE_ACTIONS.
     * When translation is otherwise complete, ofpacts_execute_action_set()
     * converts it to a set of "struct ofpact"s that can be translated into
     * datapath actions. */
    bool action_set_has_group;  /* Action set contains OFPACT_GROUP? */
    struct ofpbuf action_set;   /* Action set. */
};

/* A controller may use OFPP_NONE as the ingress port to indicate that
 * it did not arrive on a "real" port.  'ofpp_none_bundle' exists for
 * when an input bundle is needed for validation (e.g., mirroring or
 * OFPP_NORMAL processing).  It is not connected to an 'ofproto' or have
 * any 'port' structs, so care must be taken when dealing with it. */
static struct xbundle ofpp_none_bundle = {
    .name      = "OFPP_NONE",
    .vlan_mode = PORT_VLAN_TRUNK
};

struct skb_priority_to_dscp {
    struct hmap_node hmap_node; /* Node in 'ofport_dpif''s 'skb_priorities'. */
    uint32_t skb_priority;      /* Priority of this queue (see struct flow). */

    uint8_t dscp;               /* DSCP bits to mark outgoing traffic with. */
};


enum xc_type {
    XC_RULE,
    XC_BOND,
    XC_NETDEV,
    XC_NETFLOW,
    XC_MIRROR,
    XC_LEARN,
    XC_NORMAL,
    XC_FIN_TIMEOUT,
    XC_GROUP,
    XC_TNL_ARP,
};


struct xc_entry {
    enum xc_type type;
    union {
        struct rule_dpif *rule;
        struct {
            struct netdev *tx;
            struct netdev *rx;
            struct bfd *bfd;
        } dev;
        struct {
            struct netflow *netflow;
            struct flow *flow;
            ofp_port_t iface;
        } nf;
        struct {
            struct mbridge *mbridge;
            mirror_mask_t mirrors;
        } mirror;
        struct {
            struct bond *bond;
            struct flow *flow;
            uint16_t vid;
        } bond;
        struct {
            struct ofproto_dpif *ofproto;
            struct ofputil_flow_mod *fm;
            struct ofpbuf *ofpacts;
        } learn;
        struct {
            struct ofproto_dpif *ofproto;
            struct flow *flow;
            int vlan;
        } normal;
        struct {
            struct rule_dpif *rule;
            uint16_t idle;
            uint16_t hard;
        } fin;
        struct {
            struct group_dpif *group;
            struct ofputil_bucket *bucket;
        } group;
        struct {
            char br_name[IFNAMSIZ];
            ovs_be32 d_ip;
        } tnl_arp_cache;
    } u;
};

struct xlate_cache {
    struct ofpbuf entries;
};

/* Xlate config contains hash maps of all bridges, bundles and ports.
 * Xcfgp contains the pointer to the current xlate configuration.
 * When the main thread needs to change the configuration, it copies xcfgp to
 * new_xcfg and edits new_xcfg. This enables the use of RCU locking which
 * does not block handler and revalidator threads. */
struct xlate_cfg {
    struct hmap xbridges;
    struct hmap xbundles;
    struct hmap xports;
};

struct xlate_bond_recirc {
    uint32_t recirc_id;  /* !0 Use recirculation instead of output. */
    uint8_t  hash_alg;   /* !0 Compute hash for recirc before. */
    uint32_t hash_basis;  /* Compute hash for recirc before. */
};

## 核心实现

static inline void xlate_out_add_recirc(struct xlate_out *xout, uint32_t id)

    给 xout->recirc 增加一个元素, 值为 id

static inline const uint32_t * xlate_out_get_recircs(const struct xlate_out *xout)

    返回 xout 的 recirc

static inline void xlate_out_take_recircs(struct xlate_out *xout)

    释放 xout 的 recirc

static inline void xlate_out_free_recircs(struct xlate_out *xout)

    释放 xout 中 recirc 对应的 recirc_id_node

static void ctx_trigger_recirculation(struct xlate_ctx *ctx)

    ctx->exit = true;
    ctx->recirc_action_offset = ctx->action_set.size;

static bool ctx_first_recirculation_action(const struct xlate_ctx *ctx)

    return ctx->recirc_action_offset == ctx->action_set.size;

static inline bool exit_recirculates(const struct xlate_ctx *ctx)

    return ctx->recirc_action_offset >= 0;

static void xlate_report(struct xlate_ctx *ctx, const char *format, ...)

    报告目前 action 指向情况. 调用 ctx->xin->report_hook

static void xlate_report_actions(struct xlate_ctx *ctx, const char *title, const struct ofpact *ofpacts, size_t ofpacts_len)

    报告目前 action 指向情况. 调用 ctx->xin->report_hook

static void xlate_xbridge_init(struct xlate_cfg *xcfg, struct xbridge *xbridge)

    初始化 xbridge, 并加入 xcfg->xbridge

static void xlate_xbundle_init(struct xlate_cfg *xcfg, struct xbundle *xbundle)

    将 xbundle 加入 xcfg->xbundles, xcfg->xbridge->xbundles

static void xlate_xport_init(struct xlate_cfg *xcfg, struct xport *xport)

    将 xport 加入 xcfg->xport, xcfg->xbridge->xports

static void xlate_xbridge_set(struct xbridge *xbridge,
                  struct dpif *dpif,
                  const struct mac_learning *ml, struct stp *stp,
                  struct rstp *rstp, const struct mcast_snooping *ms,
                  const struct mbridge *mbridge,
                  const struct dpif_sflow *sflow,
                  const struct dpif_ipfix *ipfix,
                  const struct netflow *netflow,
                  bool forward_bpdu, bool has_in_band,
                  const struct dpif_backer_support *support)

    重新配置 xbridge

static void xlate_xbundle_set(struct xbundle *xbundle,
                  enum port_vlan_mode vlan_mode, int vlan,
                  unsigned long *trunks, bool use_priority_tags,
                  const struct bond *bond, const struct lacp *lacp,
                  bool floodable)

    重新配置 xbundle

static void xlate_xport_set(struct xport *xport, odp_port_t odp_port,
                const struct netdev *netdev, const struct cfm *cfm,
                const struct bfd *bfd, const struct lldp *lldp, int stp_port_no,
                const struct rstp_port* rstp_port,
                enum ofputil_port_config config, enum ofputil_port_state state,
                bool is_tunnel, bool may_enable)

    重新配置 xport

static void xlate_xbridge_copy(struct xbridge *xbridge)

    将 xbridge 拷贝给 new_xbridge, 并将 new_xbridge 加入 new_cfg

static void xlate_xbundle_copy(struct xbridge *xbridge, struct xbundle *xbundle)

    将 xbundle 拷贝给 new_xbundle, 并将 new_xbundle 加入 new_cfg

static void xlate_xport_copy(struct xbridge *xbridge, struct xbundle *xbundle, struct xport *xport)

    将 xport 拷贝给 new_xport, 并将 new_xport 加入 new_cfg, 如果 xbundle 不为空,
    将 new_xport 加入 xbundles->xports

void xlate_txn_commit(void)

    用 new_cfg 代替原来的 xcfgp

void xlate_txn_start(void)

    将 cfgp 拷贝给 new_xcfg

static void xlate_xcfg_free(struct xlate_cfg *xcfg)

    销毁 xcfg

void xlate_ofproto_set(struct ofproto_dpif *ofproto, const char *name,
                  struct dpif *dpif,
                  const struct mac_learning *ml, struct stp *stp,
                  struct rstp *rstp, const struct mcast_snooping *ms,
                  const struct mbridge *mbridge,
                  const struct dpif_sflow *sflow,
                  const struct dpif_ipfix *ipfix,
                  const struct netflow *netflow,
                  bool forward_bpdu, bool has_in_band,
                  const struct dpif_backer_support *support)

    设置 new_cfg->xbridges 中  ofproto 对应的 xbridge

static void xlate_xbridge_remove(struct xlate_cfg *xcfg, struct xbridge *xbridge)

    销毁 xbridge

void xlate_remove_ofproto(struct ofproto_dpif *ofproto)

    销毁 ofproto 对应的 xbridge

void xlate_bundle_set(struct ofproto_dpif *ofproto, struct ofbundle *ofbundle,
                 const char *name, enum port_vlan_mode vlan_mode, int vlan,
                 unsigned long *trunks, bool use_priority_tags,
                 const struct bond *bond, const struct lacp *lacp,
                 bool floodable)

    设置 new_cfg->xbundles 中  ofbundle 对应的 xbundle

static void xlate_xbundle_remove(struct xlate_cfg *xcfg, struct xbundle *xbundle)

    销毁 xbundle

void xlate_bundle_remove(struct ofbundle *ofbundle)

    销毁 ofbundle 对应的 xbundle

void xlate_ofport_set(struct ofproto_dpif *ofproto, struct ofbundle *ofbundle,
                 struct ofport_dpif *ofport, ofp_port_t ofp_port,
                 odp_port_t odp_port, const struct netdev *netdev,
                 const struct cfm *cfm, const struct bfd *bfd,
                 const struct lldp *lldp, struct ofport_dpif *peer,
                 int stp_port_no, const struct rstp_port *rstp_port,
                 const struct ofproto_port_queue *qdscp_list, size_t n_qdscp,
                 enum ofputil_port_config config,
                 enum ofputil_port_state state, bool is_tunnel,
                 bool may_enable)

    设置 new_cfg->xports 中 ofport 对应的 xport

static void xlate_xport_remove(struct xlate_cfg *xcfg, struct xport *xport)

    销毁 xport

void xlate_ofport_remove(struct ofport_dpif *ofport)

    销毁 ofport 对应的 xport

static struct ofproto_dpif * xlate_lookup_ofproto_(const struct dpif_backer *backer, const struct flow *flow,
                      ofp_port_t *ofp_in_port, const struct xport **xportp)

    从 xcfgp->xports 找到 flow 对应的 xport

    1. 如果 flow 是 tunnel 类型, 以 flow 对应 tnl_port 为索引, 从 xcfgp->xports 找到对应的 xport.
    2. 如果 flow 不是 tunnel 类型, 以 buckets[hash_odp_port[flow->in_port.odp_port]] 为索引, 从 xcfgp->xports 找到对应的 xport.

    其中 ofp_in_port 为 xport->ofp_port, xportp 为 xport

struct ofproto_dpif * xlate_lookup_ofproto(const struct dpif_backer *backer, const struct flow *flow,
                     ofp_port_t *ofp_in_port)

    从 xcfgp->xports 找到 flow 对应的 xport

    其中 ofp_in_port 为 xport->ofp_port, xportp 为 xport

int xlate_lookup(const struct dpif_backer *backer, const struct flow *flow,
             struct ofproto_dpif **ofprotop, struct dpif_ipfix **ipfix,
             struct dpif_sflow **sflow, struct netflow **netflow,
             ofp_port_t *ofp_in_port)

    从 xcfgp->xports 找到 flow 对应的 xport

    其中
    ofprotop = xport->xbridge->ofproto
    ipfix = xport ? xport->xbridge->ipfix : NULL
    sflow = xport ? xport->xbridge->sflow : NULL
    netflow = xport ? xport->xbridge->netflow : NULL

static struct xbridge * xbridge_lookup(struct xlate_cfg *xcfg, const struct ofproto_dpif *ofproto)

    在 xcfg->xbridges 中找到 ofproto 对应的 xbridge. 找不到返回 NULL

static struct xbundle * xbundle_lookup(struct xlate_cfg *xcfg, const struct ofbundle *ofbundle)

    在 xcfg->xbundle 中查找 ofbundle 对应的 xbundle, 找不到返回 NULL

static struct xport * xport_lookup(struct xlate_cfg *xcfg, const struct ofport_dpif *ofport)

    在 xcfg->xports 中查找 ofport 对应的 xport. 找不到返回 NULL

static struct stp_port * xport_get_stp_port(const struct xport *xport)

    返回 xport->xbridge->stp->ports[xport->stp_port_no]

static bool xport_stp_learn_state(const struct xport *xport)

    返回 (xport->xbridge->stp->ports[xport->stp_port_no]->state & (STP_LEARNING | STP_FORWARDING)) != 0;

static bool xport_stp_forward_state(const struct xport *xport)

    返回 (xport->xbridge->stp->ports[xport->stp_port_no]->state & (STP_FORWARDING)) != 0;

static bool xport_stp_should_forward_bpdu(const struct xport *xport)

    返回 (xport->xbridge->stp->ports[xport->stp_port_no]->state & (STP_DISABLED | STP_LISTENING | STP_LEARNING | STP_FORWARDING)) != 0;

static bool stp_should_process_flow(const struct flow *flow, struct flow_wildcards *wc)

    如果 flow->dl_dst == 01:80:C2:00:00:00 并且 flow->dl_type == 0x5ff, 返回 true,
    否则返回 false

static void stp_process_packet(const struct xport *xport, const struct dp_packet *packet)

    如果 xport 没有配置 stp, 或配置了 stp, 但是 stp 时 disable, 什么也不做, 直接返回
    否则, 解析 packet, 根据 stp 头的不同类型做不同处理.

    header->bpdu_type
        case STP_TYPE_CONFIG: stp_received_config_bpdu(stp, p, bpdu);
        case STP_TYPE_TCN: stp_received_tcn_bpdu(stp, p);

static enum rstp_state xport_get_rstp_port_state(const struct xport *xport)

    返回 xport->rstp_port ? xport->rstp_port->rstp_state : RSTP_DISABLED

static bool xport_rstp_learn_state(const struct xport *xport)

    return xport->xbridge->rstp && xport->rstp_port
        ? rstp_learn_in_state(xport_get_rstp_port_state(xport))
        : true;

static inline bool rstp_learn_in_state(enum rstp_state state)

    return (state == RSTP_LEARNING || state == RSTP_FORWARDING);

static bool xport_rstp_forward_state(const struct xport *xport)

    return xport->xbridge->rstp && xport->rstp_port
        ? rstp_forward_in_state(xport_get_rstp_port_state(xport))
        : true;

static inline bool rstp_forward_in_state(enum rstp_state state)

    return (state == RSTP_FORWARDING);

static bool xport_rstp_should_manage_bpdu(const struct xport *xport)

    return rstp_should_manage_bpdu(xport_get_rstp_port_state(xport));

static inline bool rstp_should_manage_bpdu(enum rstp_state state)

    return (state == RSTP_DISCARDING || state == RSTP_LEARNING ||
            state == RSTP_FORWARDING);

static void rstp_process_packet(const struct xport *xport, const struct dp_packet *packet)

    xport 收到 rstp 包后处理流程, 与 rstp 协议相关

static struct xport * get_ofp_port(const struct xbridge *xbridge, ofp_port_t ofp_port)

    从 xbridge->xports 中找到 xport->ofp_port = ofp_port 的 xport

static odp_port_t ofp_port_to_odp_port(const struct xbridge *xbridge, ofp_port_t ofp_port)

    从 xbridge->xports 中找到 xport->ofp_port = ofp_port 的 xport->odp_port 或 ODPP_NONE

static bool odp_port_is_alive(const struct xlate_ctx *ctx, ofp_port_t ofp_port)

    从 ctx->xbridge->xports 中找到 xport->ofp_port = ofp_port 的 xport

    return xport && xport->may_enable;

static bool group_is_alive(const struct xlate_ctx *ctx, uint32_t group_id, int depth)

    如下任一条件返回 false
    1. ctx->xbridge->ofproto->up->groups 中找不到 group_id 对应的 ofgroup
    2. ctx->xbridge->ofproto->up->groups 中找不到 group_id 对应的 ofgroup, 但 ofgroup.buckets 中如果存在 bucket 满足如下条件

        (!ofputil_bucket_has_liveness(bucket)
            || (bucket->watch_port != OFPP_ANY
               && odp_port_is_alive(ctx, bucket->watch_port))
            || (bucket->watch_group != OFPG_ANY
               && group_is_alive(ctx, bucket->watch_group, depth + 1)));

    否则返回 true

static bool bucket_is_alive(const struct xlate_ctx *ctx, struct ofputil_bucket *bucket, int depth)

    return (!ofputil_bucket_has_liveness(bucket)
            || (bucket->watch_port != OFPP_ANY
               && odp_port_is_alive(ctx, bucket->watch_port))
            || (bucket->watch_group != OFPG_ANY
               && group_is_alive(ctx, bucket->watch_group, depth + 1)));

static struct ofputil_bucket * group_first_live_bucket(const struct xlate_ctx *ctx, const struct group_dpif *group, int depth)

    LIST_FOR_EACH (bucket, list_node, group.up->buckets)
        if (bucket_is_alive(ctx, bucket, depth))
            return bucket;
    return NULL;

static struct ofputil_bucket * group_best_live_bucket(const struct xlate_ctx *ctx, const struct group_dpif *group, uint32_t basis)

    LIST_FOR_EACH (bucket, list_node, group.up->buckets)
        if (bucket_is_alive(ctx, bucket, 0))
            uint32_t score = (hash_int(i, basis) & 0xffff) * bucket->weight;
            if (score >= best_score)
                best_bucket = bucket;
                best_score = score;
        i++;

    return best_bucket;

static bool xbundle_trunks_vlan(const struct xbundle *bundle, uint16_t vlan)

    return (bundle->vlan_mode != PORT_VLAN_ACCESS
            && (!bundle->trunks || bitmap_is_set(bundle->trunks, vlan)));

static bool xbundle_includes_vlan(const struct xbundle *xbundle, uint16_t vlan)

    return vlan == xbundle->vlan || xbundle_trunks_vlan(xbundle, vlan);

static mirror_mask_t xbundle_mirror_out(const struct xbridge *xbridge, struct xbundle *xbundle)

    从 mbridge 找到 ofbundle->mbundles 对应的 mbundle, 返回 mbundle->mirror_out

    return xbundle != &ofpp_none_bundle
        ? mirror_bundle_out(xbridge->mbridge, xbundle->ofbundle)
        : 0;

static mirror_mask_t xbundle_mirror_src(const struct xbridge *xbridge, struct xbundle *xbundle)

    从 xbridge->mbridge->mbundles 中找到 xbundle->ofbundle 对应的 mbundle, 返回 mbundle->src_mirrors

mirror_mask_t mirror_bundle_dst(struct mbridge *mbridge, struct ofbundle *ofbundle)

    从 mbridge 找到 ofbundle->mbundles 对应的 mbundle, 返回 mbundle->dst_mirrors

static struct xbundle * lookup_input_bundle(const struct xbridge *xbridge, ofp_port_t in_port, bool warn, struct xport **in_xportp)

    从 xbridge->xports 找到 in_port 对应的 xport, 返回 xport->xbundle. 其中
    in_xportp 指向 xport

static void mirror_packet(struct xlate_ctx *ctx, struct xbundle *xbundle, mirror_mask_t mirrors)

    1. 更新 ctx->xbridge->mbridge->mirrors 中 mirrors(mirrors =& ~ctx->mirrors) 对应的 mirror 的状态
    2. 给 ctx->xin->xcache->entries 中增加一个 XC_MIRROR 类型的 entry
    3. 如果 mirror 输出端口不为空, TODO
       包进入端口的 vlan 与输出的 vlan 不一样, TODO

static void mirror_ingress_packet(struct xlate_ctx *ctx)

    1. 从 ctx->xbridge 找到 ctx->xin->flow.in_port.ofp_port 对应的 xbundle
    2. 从 ctx->xbridge->mbridge->mbundles 中找到 xbundles->ofbundle 对应的 mbundle
    3. 根据 mbundle->src_mirrors 将 xin 中收到的包镜像到其他端口 TODO

static uint16_t input_vid_to_vlan(const struct xbundle *in_xbundle, uint16_t vid)

    switch (in_xbundle->vlan_mode)
    case PORT_VLAN_ACCESS:
        return in_xbundle->vlan;
        break;

    case PORT_VLAN_TRUNK:
        return vid;

    case PORT_VLAN_NATIVE_UNTAGGED:
    case PORT_VLAN_NATIVE_TAGGED:
        return vid ? vid : in_xbundle->vlan;

static bool input_vid_is_valid(uint16_t vid, struct xbundle *in_xbundle, bool warn)

    检查 vid 是否有效 TODO

static uint16_t output_vlan_to_vid(const struct xbundle *out_xbundle, uint16_t vlan)

    switch (out_xbundle->vlan_mode)
    case PORT_VLAN_ACCESS:
        return 0;

    case PORT_VLAN_TRUNK:
    case PORT_VLAN_NATIVE_TAGGED:
        return vlan;

    case PORT_VLAN_NATIVE_UNTAGGED:
        return vlan == out_xbundle->vlan ? 0 : vlan;

static void output_normal(struct xlate_ctx *ctx, const struct xbundle *out_xbundle, uint16_t vlan)

    如果 out_xbundle->xports 为空, 直接返回
    如果 out_xbundle->xports 不为空, 但是 out_xbundle->bond 为空, 找到 xport
    如果 out_xbundle->xports 不为空, 并且 out_xbundle->bond 不为空, 根据算法从 out_xbundle->bond 中
    找到合适的 xport, TODO

static bool is_gratuitous_arp(const struct flow *flow, struct flow_wildcards *wc)

    TODO

static bool is_admissible(struct xlate_ctx *ctx, struct xport *in_port, uint16_t vlan)

    如果包应该被丢弃, 返回 false
    如果包应该被转发, 返回 true

    丢弃的情况(任一条件即可):
    1. in_port 所属 xbridge 不转发 stp 包(xbridge->forward_bpdu 为 false)
    2. in_port->xbundle->bond 找不到 in_port->ofport 对应的 bond_slave. (后续 slave 即表明找到 bond_slave)
    3. slave->enable == false && in_port->xbundle->bond->lacp_status == LACP_NEGOTIATED
    4. in_port->xbundle->bond->lacp_status == LACP_CONFIGURED && in_port->xbundle->bond->lacp_fallback_ab == false
    5. in_port->xbundle->bond->lacp_status == LACP_DISABLED
    6. flow->dl_dst 是多播包, in_port->xbundle->bond->active_slave != slave
    7. bond->balance == BM_TCP && !bond->lacp_fallback_ab
    8. bond->balance == BM_AB && in_port->xbundle->bond->active_slave != slave
    9. bond->balance == BM_SLB && mac_learning_lookup(xbridge->ml, flow->dl_src, vlan)
        && mac_entry_get_port(xbridge->ml, mac) != in_xbundle->ofbundle
        (!is_gratuitous_arp(flow, ctx->wc) || mac_entry_is_grat_arp_locked(mac)))

static bool is_mac_learning_update_needed(const struct mac_learning *ml, const struct flow *flow, struct flow_wildcards *wc, int vlan, struct xbundle *in_xbundle)

    是否需要更新 ml 表

    需要更新的条件(任一即可):
    1. ml->table 中 flow->dl_src 对应的 mac 为空或已经过期
    2. ml->table 中 flow->dl_src 对应的端口与 in_xbundle->ofbundle 不一样

static void update_learning_table__(const struct xbridge *xbridge, const struct flow *flow, struct flow_wildcards *wc, int vlan, struct xbundle *in_xbundle)

    如果需要更新 xbridge->ml->table,  将 flow, vlan 插入 xbridge->ml->table

static void update_learning_table(const struct xbridge *xbridge, const struct flow *flow, struct flow_wildcards *wc, int vlan, struct xbundle *in_xbundle)

    如果需要更新 xbridge->ml->table,  将 flow, vlan 插入 xbridge->ml->table

static void update_mcast_snooping_table4__(const struct xbridge *xbridge,
                               const struct flow *flow,
                               struct mcast_snooping *ms, int vlan,
                               struct xbundle *in_xbundle,
                               const struct dp_packet *packet)

    根据 flow->tp_src, 加入 ms

static void update_mcast_snooping_table6__(const struct xbridge *xbridge,
                               const struct flow *flow,
                               struct mcast_snooping *ms, int vlan,
                               struct xbundle *in_xbundle,
                               const struct dp_packet *packet)

    根据 flow->tp_src, 加入 ms

static void update_mcast_snooping_table(const struct xbridge *xbridge,
                            const struct flow *flow, int vlan,
                            struct xbundle *in_xbundle,
                            const struct dp_packet *packet)

    Updates multicast snooping table 'ms' given that a packet matching 'flow' was received on 'in_xbundle' in 'vlan'.

    遍历 xbridge->ms->fport_list 中每个元素 fport,
    如果 xcfgp->xbundles 中没有找到与 fport 匹配的 mcast_xbundle, 或找到了但是 mcast_xbundle != in_xbundle,
    根据 flow->dl_type 更新 xbridge->ms

static void xlate_normal_mcast_send_group(struct xlate_ctx *ctx,
                              struct mcast_snooping *ms OVS_UNUSED,
                              struct mcast_group *grp,
                              struct xbundle *in_xbundle, uint16_t vlan)

    send the packet to ports having the multicast group learned

    遍历 grp->bundle_lru 中每个元素 xbundle,
    如果 xcfgp->xbundles 中没有找到与 xbundle->port 匹配的 mcast_xbundle, 或找到了但是
    mcast_xbundle != in_xbundle, 转发, 否则报错

static void xlate_normal_mcast_send_mrouters(struct xlate_ctx *ctx,
                                 struct mcast_snooping *ms,
                                 struct xbundle *in_xbundle, uint16_t vlan)

    send the packet to ports connected to multicast routers

    遍历 ms->mrouter_lru 中每个元素 mrouter,
    如果 xcfgp->xbundles 中没有找到与 mrouter->port 匹配的 mcast_xbundle,
    或找到了但是 mcast_xbundle != in_xbundle, 转发, 否则报错

static void xlate_normal_mcast_send_fports(struct xlate_ctx *ctx,
                               struct mcast_snooping *ms,
                               struct xbundle *in_xbundle, uint16_t vlan)

    send the packet to ports flagged to be flooded

    遍历 ms->fport_list 中每个元素 fport,
    如果 xcfgp->xbundles 中没有找到与 fport 匹配的 mcast_xbundle, 或找到了但是 mcast_xbundle != in_xbundle,
    转发, 否则报错

static void xlate_normal_mcast_send_rports(struct xlate_ctx *ctx,
                               struct mcast_snooping *ms,
                               struct xbundle *in_xbundle, uint16_t vlan)

    forward the Reports to configured ports

    遍历 ms->fport_list 中每个元素 rport,
    如果 xcfgp->xbundles 中没有找到与 rport->port 匹配的 mcast_xbundle, 或找到了但是 mcast_xbundle != in_xbundle,
    转发, 否则报错

static void xlate_normal_flood(struct xlate_ctx *ctx, struct xbundle *in_xbundle, uint16_t vlan)

    将包 flood 出去

    遍历 ctx->xbridge->xbundles 所有 xbundle, 如果同时满足如下条件:
    1. xbundle 不等于 xbundle
    2. xbundle 在 vlan 属于同一 vlan
    3. xbundle 配置可以 flood
    4. ctx->xbridge->mbridge 找到 xbundle->ofbundle->mbundles 对应的 mbundle
    将包发送到 xbundle 端口

static void xlate_normal(struct xlate_ctx *ctx)

    如果时广播包, 安装广播包处理, 否则正常的交换转发

    1. 从 ctx->xbridge 找到 ctx->xin->flow->in_port.ofp_port 对应的 in_xbundle
    2. 如果 ctx->xin->may_learn 为 true, 尝试更新 ctx->xbridge->ml
    3. 将当前 ctx->xin->xcache 加入类型为 XC_NORMAL 的 xc_entry
    4. ctx->xbridge->ms 不为空, 并且不是广播但是多播 IP 包, TODO,
       否则, 从 ctx->xbridge->ml 查找 flow->dl_dst 对应的端口,
            如果找到对应的端口且端口不是 in_xbundle, 转发出去, 否则丢弃.
            如果没有找到对应的端口, 广播.

static size_t compose_sample_action(struct xlate_ctx *ctx,
                      const uint32_t probability,
                      const union user_action_cookie *cookie,
                      const size_t cookie_size,
                      const odp_port_t tunnel_out_port,
                      bool include_actions)

    构造 OVS_ACTION_ATTR_USERSPACE 类型的 NETLINK 消息存放在 ctx->odp_actions.
    如果 cookie != NULL, 返回数据的大小, 否则返回 0

    OVS_ACTION_ATTR_SAMPLE
        OVS_SAMPLE_ATTR_PROBABILITY : probability
        OVS_SAMPLE_ATTR_ACTIONS
            OVS_ACTION_ATTR_USERSPACE
                 OVS_USERSPACE_ATTR_PID : pid
                 OVS_USERSPACE_ATTR_USERDATA : cookie
                 OVS_USERSPACE_ATTR_EGRESS_TUN_PORT: tunnel_out_port
                 OVS_USERSPACE_ATTR_ACTIONS : NULL (如果 include_actions == true)

    其中 pid = ctx->xbridge->dpif->handlers[hash % dpif->n_handlers]->channels[port_no].sock->pid

static size_t compose_sflow_action(struct xlate_ctx *ctx)

    构造 OVS_ACTION_ATTR_USERSPACE 类型的 NETLINK 消息存放在 ctx->odp_actions.
    如果 cookie != NULL, 返回数据的大小, 否则返回 0

    OVS_ACTION_ATTR_SAMPLE
        OVS_SAMPLE_ATTR_PROBABILITY : sflow->probability
        OVS_SAMPLE_ATTR_ACTIONS
            OVS_ACTION_ATTR_USERSPACE
                 OVS_USERSPACE_ATTR_PID : pid
                 OVS_USERSPACE_ATTR_USERDATA : cookie
                 OVS_USERSPACE_ATTR_ACTIONS : NULL

    其中 pid = ctx->xbridge->dpif->handlers[hash % dpif->n_handlers]->channels[port_no].sock->pid
        cookie = {
            .type = USER_ACTION_COOKIE_SFLOW
            .sflow = {
                .vlan_tci = ctx->base_flow->vlan_tci
                .output = 0x40000000 | 256
                .output = dpif_sflow_odp_port_to_ifindex(ctx->xbridge->sflow, ctx->sflow_odp_port)
                .output = 0x80000000 | ctx->sflow_n_outputs;
            }
        };

    ctx->sflow_n_outputs == 0 : .output = 0x40000000 | 256
    ctx->sflow_n_outputs == 1 : .output = dpif_sflow_odp_port_to_ifindex(ctx->xbridge->sflow, ctx->sflow_odp_port)
    ctx->sflow_n_outputs 为其他值 : .output = 0x80000000 | ctx->sflow_n_outputs;


static void compose_ipfix_action(struct xlate_ctx *ctx, odp_port_t output_odp_port)

    构造 OVS_ACTION_ATTR_USERSPACE 类型的 NETLINK 消息存放在 ctx->odp_actions.
    如果 cookie != NULL, 返回数据的大小, 否则返回 0

    OVS_ACTION_ATTR_SAMPLE
        OVS_SAMPLE_ATTR_PROBABILITY : ctx->xbridge->ipfix->bridge_exporter.probability
        OVS_SAMPLE_ATTR_ACTIONS
            OVS_ACTION_ATTR_USERSPACE
                OVS_USERSPACE_ATTR_PID : pid
                OVS_USERSPACE_ATTR_USERDATA : cookie
                OVS_USERSPACE_ATTR_EGRESS_TUN_PORT : di->tunnel_ports 找到 output_odp_port 对应的 dpif_ipfix_port


    其中 pid = ctx->xbridge->dpif->handlers[hash % dpif->n_handlers]->channels[port_no].sock->pid
        cookie = {
            .ipfix = {
                .type = USER_ACTION_COOKIE_IPFIX,
                .output_odp_port = output_odp_port,
            }
        };

static bool process_special(struct xlate_ctx *ctx, const struct xport *xport)

    如果 ctx->xin->packet 被处理(cfm, bfd, lacp, stp, lldp), 返回 true, 否则返回 false

static int tnl_route_lookup_flow(const struct flow *oflow, ovs_be32 *ip, struct xport **out_port)

    从 cls 中查找 flow->tunnel.ip_dst 对应的网桥名, 端口, 初始化 ip, out_port

static int xlate_flood_packet(struct xbridge *xbridge, struct dp_packet *packet)

    构造 PACKOUT 类型的 Netlink 消息, 发送给内核, 要求内核执行将包 flood 给所有端口

static void tnl_send_arp_request(const struct xport *out_dev, const uint8_t eth_src[ETH_ADDR_LEN], ovs_be32 ip_src, ovs_be32 ip_dst)

    用参数构造 arp 请求包, 之后构造 PACKOUT 类型的 Netlink 消息, 发送给内核,
    要求内核执行将 arp 请求包 flood 给所有端口

static int build_tunnel_send(struct xlate_ctx *ctx, const struct xport *xport, const struct flow *flow, odp_port_t tunnel_odp_port)

    1. 根据 flow->ip_dst 查找要输出的网卡, 及网管 ip
    2. 获取网卡的 ip, mac
    3. 根据网关的 ip 查找网关的 mac(如果找不到发送 arp 请求)
    4. ctx->xin->xcache 增加 XC_TNL_ARP 类型的 xc_entry
    5. 根据之前的信息构造 tunnel 包
    6. 将构造的 tunnel 包加入 ctx->odp_actions. 类型为 OVS_ACTION_ATTR_TUNNEL_PUSH

static void compose_output_action__(struct xlate_ctx *ctx, ofp_port_t ofp_port, const struct xlate_bond_recirc *xr, bool check_stp)

    TODO

static void compose_output_action(struct xlate_ctx *ctx, ofp_port_t ofp_port,

    TODO

static void xlate_recursively(struct xlate_ctx *ctx, struct rule_dpif *rule)

static void xlate_table_action(struct xlate_ctx *ctx, ofp_port_t in_port, uint8_t table_id, bool may_packet_in, bool honor_table_miss)

    1. 如果时 mpls 包, 设置 ctx->exit = true; ctx->recirc_action_offset = ctx->action_set.size;
    2. 从 ctx->xbridge->ofproto->up.tables[table_id].cls 找 flow 匹配的 rule,
       如果找到, ctx->xin->xcache 加入 XC_RULE 类型的 xc_entry, 解析执行对应的 action, 如果找不到, 返回

static bool may_receive(const struct xport *xport, struct xlate_ctx *ctx)

    如果 xport 的 stp 端口配置不转发 stp, rstp, stp learn, rstp learn 消息或收到的 stp 包但是 xport->config 配置不接受 stp 包, 返回 false;
    否则返回 true

struct rule_dpif * rule_dpif_lookup_from_table(struct ofproto_dpif *ofproto,
                            cls_version_t version, struct flow *flow,
                            struct flow_wildcards *wc, bool take_ref,
                            const struct dpif_flow_stats *stats,
                            uint8_t *table_id, ofp_port_t in_port,
                            bool may_packet_in, bool honor_table_miss)

    1. 从 ofproto->up.tables[table_id].cls 找 flow 匹配的 rule;
    2. 如果 honor_table_miss 配置为 true, 并且表配置中指定继续查下一张表, 会继续遍历下一张表
    3. 如果 may_packet_in 配置为 true, 当步骤 1 查不断合适的 rule 时, rule 为 ofproto->miss_rule
    4. 否则 rule = ofproto->no_packet_in_rule;

static void flood_packets(struct xlate_ctx *ctx, bool all)

    将包转发到除进入端口之外的所有端口

static void execute_controller_action(struct xlate_ctx *ctx, int len, enum ofp_packet_in_reason reason, uint16_t controller_id)


static void xlate_all_group(struct xlate_ctx *ctx, struct group_dpif *group)

    对 group 中的每一个 bucket, 执行 xlate_group_bucket(ctx, bucket)

    group_dpif_get_buckets(group, &buckets);
    LIST_FOR_EACH (bucket, list_node, buckets)
        xlate_group_bucket(ctx, bucket);

static void xlate_ff_group(struct xlate_ctx *ctx, struct group_dpif *group)

    bucket = group_first_live_bucket(ctx, group, 0);
    if (bucket)
        xlate_group_bucket(ctx, bucket);

static void xlate_default_select_group(struct xlate_ctx *ctx, struct group_dpif *group)

    basis = flow_hash_symmetric_l4(&ctx->xin->flow, 0);
    flow_mask_hash_fields(&ctx->xin->flow, wc, NX_HASH_FIELDS_SYMMETRIC_L4);
    bucket = group_best_live_bucket(ctx, group, basis);
    if (bucket)
        xlate_group_bucket(ctx, bucket);

static void xlate_hash_fields_select_group(struct xlate_ctx *ctx, struct group_dpif *group)

    fields = group_dpif_get_fields(group);
    basis = hash_uint64(group_dpif_get_selection_method_param(group));
    bucket = group_best_live_bucket(ctx, group, basis);
    if (bucket)
        xlate_group_bucket(ctx, bucket);

static void xlate_select_group(struct xlate_ctx *ctx, struct group_dpif *group)

    if (selection_method[0] == '\0')
        xlate_default_select_group(ctx, group);
    else if (!strcasecmp("hash", selection_method))
        xlate_hash_fields_select_group(ctx, group);

static void xlate_group_action__(struct xlate_ctx *ctx, struct group_dpif *group)

    根据 group 的类型指向对应的 action.

    case OFPGT11_ALL:
    case OFPGT11_INDIRECT:
        xlate_all_group(ctx, group);
    case OFPGT11_SELECT:
        xlate_select_group(ctx, group);
    case OFPGT11_FF:
        xlate_ff_group(ctx, group);

static bool xlate_group_action(struct xlate_ctx *ctx, uint32_t group_id)

    从 ctx->xbridge->ofproto->up->groups 查找 group_id 对应的 group,
    找到执行对应的 action(参考 xlate_group_action__)

static void xlate_output_action(struct xlate_ctx *ctx, ofp_port_t port, uint16_t max_len, bool may_packet_in)

    根据 port 的类型执行对应的 action

    switch (port)
        case OFPP_IN_PORT: compose_output_action(ctx, ctx->xin->flow.in_port.ofp_port, NULL);
        case OFPP_TABLE: xlate_table_action(ctx, ctx->xin->flow.in_port.ofp_port, 0, may_packet_in, true);
        case OFPP_NORMAL: xlate_normal(ctx);
        case OFPP_FLOOD: flood_packets(ctx,  false);
        case OFPP_ALL: flood_packets(ctx, true);
        case OFPP_CONTROLLER: execute_controller_action(ctx, max_len, (ctx->in_group ? OFPR_GROUP : ctx->in_action_set ? OFPR_ACTION_SET : OFPR_ACTION), 0);

static void do_xlate_actions(const struct ofpact *ofpacts, size_t ofpacts_len, struct xlate_ctx *ctx)

    遍历 ofpacts 的每个元素, 根据元素类型执行对应的 action

static void execute_controller_action(struct xlate_ctx *ctx, int len, enum ofp_packet_in_reason reason, uint16_t controller_id)

    1. 解析 ctx->odp_actions->data 中的每一个元素. 根据元素的 type 对 packets 中的每个包执行相应的 action
    3. 构造 PACKET_IN 包
    4. 将 pin 加入 ofproto->pins 队列. 通知 ofproto->pins_seq 发生变化

static void xlate_enqueue_action(struct xlate_ctx *ctx, const struct ofpact_enqueue *enqueue)

    1. 根据 enqueue->queue 获取队列优先级, 如果出错, 回滚到正常的 output action
    2. TODO

static void xlate_ofpact_resubmit(struct xlate_ctx *ctx, const struct ofpact_resubmit *resubmit)

    如果是 resubmit 来自一个 internal 表(第 254 号表), 仍然允许给控制发送 PACKET_IN

    1. 如果时 mpls 包, 设置 ctx->exit = true; ctx->recirc_action_offset = ctx->action_set.size;
    2. 从 ctx->xbridge->ofproto->up.tables[resubmit->table_id].cls 找 flow 匹配的 rule,
       如果找到, ctx->xin->xcache 加入 XC_RULE 类型的 xc_entry, 解析执行对应的 action, 如果找不到, 返回

static void xlate_set_queue_action(struct xlate_ctx *ctx, uint32_t queue_id)

    设置 ctx->xin->flow.skb_priority 优先级为 queue_id 对应的优先级

static void compose_mpls_push_action(struct xlate_ctx *ctx, struct ofpact_push_mpls *mpls)

    TODO
