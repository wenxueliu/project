


struct bond_entry {
    struct bond_slave *slave;   /* Assigned slave, NULL if unassigned. */
    uint64_t tx_bytes           /* Count of bytes recently transmitted. */
        OVS_GUARDED_BY(rwlock);
    struct ovs_list list_node;  /* In bond_slave's 'entries' list. */

    /* Recirculation.
     *
     * 'pr_rule' is the post-recirculation rule for this entry.
     * 'pr_tx_bytes' is the most recently seen statistics for 'pr_rule', which
     * is used to determine delta (applied to 'tx_bytes' above.) */
    struct rule *pr_rule;
    uint64_t pr_tx_bytes OVS_GUARDED_BY(rwlock);
};


struct bond_slave {
    struct hmap_node hmap_node; /* In struct bond's slaves hmap. */
    struct ovs_list list_node;  /* In struct bond's enabled_slaves list. */
    struct bond *bond;          /* The bond that contains this slave. */
    void *aux;                  /* Client-provided handle for this slave. */

    struct netdev *netdev;      /* Network device, owned by the client. */
    unsigned int change_seq;    /* Tracks changes in 'netdev'. */
    ofp_port_t  ofp_port;       /* OpenFlow port number. */
    char *name;                 /* Name (a copy of netdev_get_name(netdev)). */

    /* Link status. */
    long long delay_expires;    /* Time after which 'enabled' may change. */
    bool enabled;               /* May be chosen for flows? */
    bool may_enable;            /* Client considers this slave bondable. */

    /* Rebalancing info.  Used only by bond_rebalance(). */
    struct ovs_list bal_node;   /* In bond_rebalance()'s 'bals' list. */
    struct ovs_list entries;    /* 'struct bond_entry's assigned here. */
    uint64_t tx_bytes;          /* Sum across 'tx_bytes' of entries. */
};

struct bond {
    struct hmap_node hmap_node; /* In 'all_bonds' hmap. */
    char *name;                 /* Name provided by client. */
    struct ofproto_dpif *ofproto; /* The bridge this bond belongs to. */

    /* Slaves. */
    struct hmap slaves;

    /* Enabled slaves.
     *
     * Any reader or writer of 'enabled_slaves' must hold 'mutex'.
     * (To prevent the bond_slave from disappearing they must also hold
     * 'rwlock'.) */
    struct ovs_mutex mutex OVS_ACQ_AFTER(rwlock);
    struct ovs_list enabled_slaves OVS_GUARDED; /* Contains struct bond_slaves. */

    /* Bonding info. */
    enum bond_mode balance;     /* Balancing mode, one of BM_*. */
    struct bond_slave *active_slave;
    int updelay, downdelay;     /* Delay before slave goes up/down, in ms. */
    enum lacp_status lacp_status; /* Status of LACP negotiations. */
    bool bond_revalidate;       /* True if flows need revalidation. */
    uint32_t basis;             /* Basis for flow hash function. */

    /* SLB specific bonding info. */
    struct bond_entry *hash;     /* An array of BOND_BUCKETS elements. */
    int rebalance_interval;      /* Interval between rebalances, in ms. */
    long long int next_rebalance; /* Next rebalancing time. */
    bool send_learning_packets;
    uint32_t recirc_id;          /* Non zero if recirculation can be used.*/
    struct hmap pr_rule_ops;     /* Helps to maintain post recirculation rules.*/

    /* Store active slave to OVSDB. */
    bool active_slave_changed; /* Set to true whenever the bond changes
                                   active slave. It will be reset to false
                                   after it is stored into OVSDB */

    /* Interface name may not be persistent across an OS reboot, use
     * MAC address for identifing the active slave */
    uint8_t active_slave_mac[ETH_ADDR_LEN];
                               /* The MAC address of the active interface. */
    /* Legacy compatibility. */
    bool lacp_fallback_ab; /* Fallback to active-backup on LACP failure. */

    struct ovs_refcount ref_cnt;
};

static struct bond_slave * get_enabled_slave(struct bond *bond)

    if (list_is_empty(&bond->enabled_slaves))
        return NULL;
    node = list_pop_front(&bond->enabled_slaves);
    list_push_back(&bond->enabled_slaves, node);
    return CONTAINER_OF(node, struct bond_slave, list_node);

static struct bond_slave * choose_output_slave(const struct bond *bond, const struct flow *flow, struct flow_wildcards *wc, uint16_t vlan)

    如果 LACP 没有准备好, 并且回滚为 false, 返回 NULL
    如果 LACP 没有准备好, 并且回滚为 true, 返回 bond->active_slave
    如果 LACP 已经准备好, 根据 bond->balance, 选择合适的 bond_slave(如果 bond 不是 enable, 从 bond->enabled_slaves 中找出一个)

    目前支持的方法
    BM_AB : active-backup
    BM_TCP : bond->hash[bond_hash(bond, flow, vlan) & BOND_MASK] (bond_hash 根据 L2~L4 hash)
    BM_SLB : bond->hash[bond_hash(bond, flow, vlan) & BOND_MASK] (bond_hash 根据 mac 源地址 hash)


bool bond_may_recirc(const struct bond *bond, uint32_t *recirc_id, uint32_t *hash_bias)

    如果 bond->balance, 返回 true, 其中 recirc_id 为 bond->recirc_id, hash_bias 为 bond->hash_bias
    如果 bond->balance, 返回 false.

void bond_update_post_recirc_rules(struct bond* bond, const bool force)

    参考 bond_update_post_recirc_rules__

static void bond_update_post_recirc_rules__(struct bond* bond, const bool force)

    确保 bond->hash 每个元素 e 满足 e->slave || e->slave->enabled

    遍历 bond->hash 如果有元素满足: !e->slave || !e->slave->enabled, 从
    bond->slaves 随机找一个 bond_slave 初始化 e->slave, 如果 e->slave->enabled
    为 false, 设置 e->slave 为 bond->active_slave

static void update_recirc_rules(struct bond *bond)

    用 bond->hash 更新 bond->pr_rule_ops, 对于 bond->hash 不存在,
    从内部流表中的删除对应的流表, 存在对应的流表
