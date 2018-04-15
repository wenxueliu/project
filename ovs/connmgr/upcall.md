
## 问题

1. 父线程时如何优雅地关闭子线程的?

1) 父线程与子线程通过管道关联, 当父线程需要关闭子线程的时候, 发送消息给子线程, 并 join 子线程;
2) 子线程监听管道的可读事件, 如果管道可读, 做完收尾工作, 停止当前线程.
3) 父线程读完管道的消息, 此时子线程已经退出.

2. udpif->ukeys 与 revalidator 的关系

    udpif->ukeys 总共为 N_UMAPS 个元素, 均匀地分配给 n_revalidators 个.
    每个 N_UMAPS/n_revalidators. 而且, ukeys[i + n * n_revalidators] 属于
    第 i 个 revalidator. 其中 0 <= i <= n_revalidators-1;

3. handler 和 revalidator 线程分别工作是什么?

handler 线程工作:

监听 handler 所属 dpif 的每个端口的 POLLIN 事件:

如果收到数据, 解析后处理, 如果收到的数据包不为 0, 立即唤醒当前线程的 poll_loop

如果没有收到数据, 将 dpif->handlers[handler->handler_id]->epoll_fd 加入当前线程的 poll_loop,
并监听 POLLIN 事件; 此外, 将 handler->udpif->exit_latch[0] 加入当前线程的 poll_loop,
监听自己是否退出的消息.


4. dpif, udpif, dpif_backer 的关系 ?

5. ukey, flow 的关系

    收到内核的消息 buf -> dpif_upcall -> upcall -> flow(upcall->packet, upcall->key)

6. PACKET_IN 包的流向

 buf -> dupcall->packet(struct dp_packet) -> upcall->packet(struct dp_packet) -> pin(struct ofproto_packet_in) -> ofproto->pins

7. xlate_in, xlate_out, xlate_ctx 的关系

8. xbridge 与 bridge 的关系, port 与 xport 的关系

##调优

调大 REVALIDATE_MAX_BATCH 是否会降低 revalidator 的 cpu 利用率

当 flow 数量大于 flow_limitr*2, 会删除所有 flow

should_revalidate 中的魔数是否可以降低 revalidator 的 cpu 利用率

调整 N_UMAPS 是否会降低 revalidator 的 cpu 利用率

调整 UPCALL_MAX_BATCH 是否会影响 handler 的性能

##设计

每个 handler 对应 udpif_upcall_handler
每个 revalidator 对应 udpif_revalidator, 第一个 revalidator 控制所有 revalidator 的状态

数据流向

flow   ->
upcall -> udpif_key -> ukey_op
                    -> xlate_in

##数据结构


static struct ovs_list all_udpifs = OVS_LIST_INITIALIZER(&all_udpifs);


struct handler {
    struct udpif *udpif;               //所属 udpif
    pthread_t thread;                  //所属线程, udpif_upcall_handler
    uint32_t handler_id;               //第几个 handler
};

struct revalidator {
    struct udpif *udpif;               //所属 udpif
    pthread_t thread;                  //所属线程, udpif_revalidator
    unsigned int id;                   //revalidator 所属线程的 id. ovsthread_id_self().
};

struct udpif {
    struct ovs_list list_node;         /* In all_udpifs list. */

    struct dpif *dpif;                 /* Datapath handle. */
    struct dpif_backer *backer;        /* Opaque dpif_backer pointer. */

    struct handler *handlers;          /* Upcall handlers. */
    size_t n_handlers;

    struct revalidator *revalidators;  /* Flow revalidators. */
    size_t n_revalidators;

    struct latch exit_latch;           //通知子线程关闭的管道

    /* Revalidation. */
    struct seq *reval_seq;             /* Incremented to force revalidation. */
    bool reval_exit;                   //当前 revalidator 是否应该停止, 当监听到 exit_latch 的可读事件时, 设置为 true
    struct ovs_barrier reval_barrier;  //revalidator 线程中, 控制 flow 操作的步调

    struct dpif_flow_dump *dump;       /* DPIF flow dump state. */
    long long int dump_duration;       /* Duration of the last flow dump. */
    struct seq *dump_seq;              /* Increments each dump iteration. */
    atomic_bool enable_ufid;           /* If true, skip dumping flow attrs. */

    /* These variables provide a mechanism for the main thread to pause
     * all revalidation without having to completely shut the threads down.
     * 'pause_latch' is shared between the main thread and the lead
     * revalidator thread, so when it is desirable to halt revalidation, the
     * main thread will set the latch. 'pause' and 'pause_barrier' are shared
     * by revalidator threads. The lead revalidator will set 'pause' when it
     * observes the latch has been set, and this will cause all revalidator
     * threads to wait on 'pause_barrier' at the beginning of the next
     * revalidation round. */
    bool pause;                        /* Set by leader on 'pause_latch. */
    struct latch pause_latch;          /* Set to force revalidators pause. */
    struct ovs_barrier pause_barrier;  /* Barrier used to pause all */
                                       /* revalidators by main thread. */


    /*
     * udpif->ukeys 总共为 N_UMAPS 个元素, 均匀地分配给 n_revalidators 个.
     * 每个 N_UMAPS/n_revalidators. 而且, ukeys[i + n * n_revalidators] 属于
     * 第 i 个 revalidator. 其中 0 <= i <= n_revalidators-1;
     *
     * During the flow dump phase, revalidators insert into these with a random
     * distribution. During the garbage collection phase, each revalidator
     * takes care of garbage collecting a slice of these maps. */
     */
    struct umap *ukeys;

    /* Datapath flow statistics. */
    unsigned int max_n_flows;
    unsigned int avg_n_flows;

    /* Following fields are accessed and modified by different threads. */
    atomic_uint flow_limit;            /* Datapath flow hard limit. */

    /* n_flows_mutex prevents multiple threads updating these concurrently. */
    atomic_uint n_flows;               //当前 udpif 对应的 datapath 中的流表数目
    atomic_llong n_flows_timestamp;    //上一次更新 n_flows 值的时间
    struct ovs_mutex n_flows_mutex;    //保护 n_flows, n_flows_timestamp 的锁

    /* Following fields are accessed and modified only from the main thread. */
    struct unixctl_conn **conns;       /* Connections waiting on dump_seq. */
    uint64_t conn_seq;                 /* Corresponds to 'dump_seq' when
                                          conns[n_conns-1] was stored. */
    size_t n_conns;                    /* Number of connections waiting. */
};

exit, exit_latch 控制 handler 和 revalidator 的退出.


/* Ukeys must transition through these states using transition_ukey(). */
enum ukey_state {
    UKEY_CREATED = 0,
    UKEY_VISIBLE,       /* Ukey is in umap, datapath flow install is queued. */
    UKEY_OPERATIONAL,   /* Ukey is in umap, datapath flow is installed. */
    UKEY_EVICTING,      /* Ukey is in umap, datapath flow delete is queued. */
    UKEY_EVICTED,       /* Ukey is in umap, datapath flow is deleted. */
    UKEY_DELETED,       /* Ukey removed from umap, ukey free is deferred. */
};


struct ukey_op {
    struct udpif_key *ukey;
    struct dpif_flow_stats stats; /* Stats for 'op'. */
    struct dpif_op dop;           /* Flow operation. */
};

struct dpif_op {
    enum dpif_op_type type;
    int error;
    union {
        struct dpif_flow_put flow_put;
        struct dpif_flow_del flow_del;
        struct dpif_execute execute;
        struct dpif_flow_get flow_get;
    } u;
};



void udpif_init(void)

    初始化 udpif 支持的操作
    upcall/show                 目前的流表项数目, ufid, revalidator 统计信息
    upcall/disable-megaflows    设置 megaflows 为 true
    upcall/enable-megaflows     设置 megaflows 为 true
    upcall/disable-ufid         设置 enable_ufid 为 false
    upcall/enable-ufid          设置 enable_ufid 为 true
    upcall/set-flow-limit       设置每个 udpif 的 flow_limit
    revalidator/wait            udpif->conns 增加一个元素
    revalidator/purge           调用每个 revalidator 的 revalidator_purge

struct udpif * udpif_create(struct dpif_backer *backer, struct dpif *dpif)

    初始化 udpif

void udpif_run(struct udpif *udpif)

    应答所有没有处理的 upcall 命令

void udpif_destroy(struct udpif *udpif)

    销毁 udpif

static void udpif_stop_threads(struct udpif *udpif)

    停止所有的 handler 和 revalidator 线程

    1. 通过 exit_latch 发送停止消息
    2. 等待 handler 和 revalidator 线程结束
    3. handler 和 revalidator 会监听 exit_latch 管道的消息, 当发现有可读事件时会将当前线程停止.
    4. 对于 dpif_netlink, 什么也不做; 对于 dpif_netdev, fat_rwlock_wrlock(&dp->upcall_rwlock);
    5. 遍历所有的 dpif->ukeys, 如果 ukey 存在, 就给内核发送删除对应流表消息, 如果 ukey 不存在, 就删除对应的 ukey
    6. 读取 exit_latch 管道的消息
    7. 释放 handler 和 revalidator 的内存

static void udpif_start_threads(struct udpif *udpif, size_t n_handlers, size_t n_revalidators)

    重新初始化 udpif  中与 revalidator 和 handler 相关参数

    1. 初始化 udpif->handlers, udpif->revalidators
    2. 更新 udpif->ufid_enabled
    3. fat_rwlock_unlock(get_dp_netdev(udpif->dpif)->dp->upcall_rwlock)
    4. udpif->reval_exit = false
    5. 初始化 udpif->reval_barrier

void udpif_set_threads(struct udpif *udpif, size_t n_handlers, size_t n_revalidators)

    如果 udpif 的 n_handlers, n_revalidators 与参数不一致, 重新设置 handler 和 revalidator 的数量

    1. 停止所有的 handler, revalidator
    2. 开始所有的 handler, revalidator

    handler 与 dpif-netlink 相关; 参考 dpif_netlink_handlers_set

void udpif_synchronize(struct udpif *udpif)

    强制重新设置 handler 和 revalidator

void udpif_revalidate(struct udpif *udpif)

    seq_change(udpif->reval_seq);

struct seq * udpif_dump_seq(struct udpif *udpif)

    return udpif->dump_seq;

void udpif_get_memory_usage(struct udpif *udpif, struct simap *usage)

    将 handler, revalidator, udpif keys 信息加入 usage

void udpif_flush(struct udpif *udpif)

    强制重新设置 udpif 的  handler 和 revalidator, 并删除所有流表

static void udpif_flush_all_datapaths(void)

    强制重新设置 all_udpifs 中每一个 udpif 的 handler 和 revalidator, 并删除所有流表

static bool udpif_use_ufid(struct udpif *udpif)

    检查 ufid 是否可用

static unsigned long udpif_get_n_flows(struct udpif *udpif)

    将 datapath 的流表数更新 udpif->n_flows, udpif->n_flows_timestamp. 最少每
    200 ms 更新一次.

static void * udpif_upcall_handler(void *arg)

    监听 handler 所属 dpif 的每个端口的 POLLIN 事件:

    如果收到数据, 解析后处理, 如果收到的数据包不为 0, 立即唤醒当前线程的 poll_loop

    如果没有收到数据, 将 dpif->handlers[handler->handler_id]->epoll_fd 加入当前线程的 poll_loop,
    并监听 POLLIN 事件; 此外, 将 handler->udpif->exit_latch[0] 加入当前线程的 poll_loop,
    监听自己是否退出的消息.

static size_t recv_upcalls(struct handler *handler)

    从 handler 所对应的端口收数据
    根据 upcall 不同类型进行不同的处理.

    upcall 的类型
        MISS_UPCALL
        SFLOW_UPCALL
        IPFIX_UPCALL
        FLOW_SAMPLE_UPCALL
        BAD_UPCALL

static void upcall_xlate(struct udpif *udpif, struct upcall *upcall, struct ofpbuf *odp_actions, struct flow_wildcards *wc)

static void delete_op_init__(struct udpif *udpif, struct ukey_op *op, const struct dpif_flow *flow)

    初始化 flow delete 类型的 op

static void delete_op_init(struct udpif *udpif, struct ukey_op *op, struct udpif_key *ukey)

    初始化 flow delete 类型的 op

static void put_op_init(struct ukey_op *op, struct udpif_key *ukey, enum dpif_flow_put_flags flags)

    初始化 flow put 类型的 op

### ukey

static struct udpif_key * ukey_lookup(struct udpif *udpif, const ovs_u128 *ufid, const unsigned pmd_id)

    根据 ufid, pmd_id 的哈希值 idx, 在 udpif->ukeys[idx].cmap 中查找 ukey->ufid
    与 ufid 相同的 ukey, 找不到返回 NULL

static void ukey_get_actions(struct udpif_key *ukey, const struct nlattr **actions, size_t *size)

    找到 ukey->actions 保存在 actions 和 size 中

static void ukey_set_actions(struct udpif_key *ukey, const struct ofpbuf *actions)

    ofpbuf_delete(ukey->action) 加入当前线程的 perthread->cbsets
    设置 ukeys->actions = actions

static struct udpif_key * ukey_create__(const struct nlattr *key, size_t key_len, const struct nlattr *mask, size_t mask_len, bool ufid_present, const ovs_u128 *ufid, const unsigned pmd_id, const struct ofpbuf *actions, uint64_t dump_seq, uint64_t reval_seq, long long int used, uint32_t key_recirc_id, struct xlate_out *xout)

    初始化 udpif_key 对象

static struct udpif_key * ukey_create_from_upcall(struct upcall *upcall, struct flow_wildcards *wc)

    用 upcall 初始化 udpif_key

static int ukey_create_from_dpif_flow(const struct udpif *udpif, const struct dpif_flow *flow, struct udpif_key **ukey)

    用 flow 初始化 udpif_key.

static bool try_ukey_replace(struct umap *umap, struct udpif_key *old_ukey, struct udpif_key *new_ukey)

    如果 old_ukey->state == UKEY_EVICTED, 用 umap->cmap 中的 new_ukey 替代 old_ukey

static bool ukey_install__(struct udpif *udpif, struct udpif_key *new_ukey)

    将 new_ukey 加入 udpif->ukeys[new_ukey->hash % N_UMAPS], 并设置 new_ukey->state 为 UKEY_VISIBLE

    异常: new_ukey 与已经存在的 ukey 的 ufid 相同, 但是 ukey->key 或 ukey->key_len 不同

static bool ukey_install(struct udpif *udpif, struct udpif_key *ukey)

    将 new_ukey 加入 udpif->ukeys[new_ukey->hash % N_UMAPS], 并设置 new_ukey->state 为 UKEY_VISIBLE

static void transition_ukey(struct udpif_key *ukey, enum ukey_state dst)

    如果满足条件, 将 ukey->state 设置为 dst.

    满足条件:
    (ukey->state == dst - 1 || (ukey->state == UKEY_VISIBLE && dst < UKEY_DELETED))

static int ukey_acquire(struct udpif *udpif, const struct dpif_flow *flow, struct udpif_key **result, int *error)

    如果 flow 对应的 ukey 存在, 尝试加锁
    如果 flow 对应的 ukey 不存在, 根据 flow 创建 ukey, 并加入 udpif->ukeys 中

static void ukey_delete__(struct udpif_key *ukey)

    释放 ukey


static void ukey_delete(struct umap *umap, struct udpif_key *ukey)

    将 ukey 中的元素从 umap 中删除, 并将 ukey_delete__(ukey) 加入当前线程的 perthread->cbsets 中延后 ukey 的清理工作, 设置 ops[i].ukey->state 为 UKEY_DELETED


static bool should_revalidate(const struct udpif *udpif, uint64_t packets, long long int used)

    是否应该 revalidator ukey.
    满足一下任意的条件:
    1. used == 0
    2. udpif->dump_duration < 200
    3. (now - used)/packets < 200

static int xlate_key(struct udpif *udpif, const struct nlattr *key, unsigned int len, const struct dpif_flow_stats *push, struct reval_context *ctx)

    初始化 xlate_in

static int xlate_ukey(struct udpif *udpif, const struct udpif_key *ukey, uint16_t tcp_flags, struct reval_context *ctx)

    用 ukey 初始化 xlate_in

static int populate_xcache(struct udpif *udpif, struct udpif_key *ukey, uint16_t tcp_flags)

    用 ukey 初始化 xlate_in

static enum reval_result revalidate_ukey__(struct udpif *udpif, const struct udpif_key *ukey, uint16_t tcp_flags, struct ofpbuf *odp_actions, struct recirc_refs *recircs, struct xlate_cache *xcache)

    TODO

static void dp_purge_cb(void *aux, unsigned pmd_id)

    将 udpif->ukeys[i] 中 pmd_id 对应的 ukey, 加入当前线程的 cbsets,
    待删除的元素个数超过 REVALIDATE_MAX_BATCH, 执行对应的操作, 最后
    调用每个线程的 cbsets 对应的函数

static void compose_slow_path(struct udpif *udpif, struct xlate_out *xout, const struct flow *flow, odp_port_t odp_in_port, struct ofpbuf *buf)

    构造一个 OVS_ACTION_ATTR_USERSPACE 类型 action  的 netlink 保存在 buf 中

static void push_dp_ops(struct udpif *udpif, struct ukey_op *ops, size_t n_ops)

    执行 ops 中的操作, 对于 DPIF_OP_FLOW_DEL 类型的 TODO

    对于 ops 具体实现在 dpif_netdev_operate 和 dpif_netlink_operate 中.

static void push_ukey_ops(struct udpif *udpif, struct umap *umap, struct ukey_op *ops, size_t n_ops)

    执行 ops 中的操作, 并将 ops[i].ukey 中的元素从 umap 中删除, 并将 ukey_delete__(ops[i].ukey)
    加入当前线程的 perthread->cbsets 中延后ukey 的清理工作, 设置 ops[i].ukey->state 为 UKEY_DELETED

static void reval_op_init(struct ukey_op *op, enum reval_result result, struct udpif *udpif, struct udpif_key *ukey, struct recirc_refs *recircs, struct ofpbuf *odp_actions)

    如果 result 为 UKEY_DELETE, 初始化 op 为 DPIF_OP_FLOW_DEL 类型
    如果 result 为 UKEY_MODIFY, 初始化 op 为 DPIF_FP_MODIFY 类型

static void revalidator_sweep__(struct revalidator *revalidator, bool purge)

    如果 purge == true && ukey_state == UKEY_OPERATIONAL && (ukey_state == UKEY_VISIBLE && purge); 删除 udpif->ukeys[i]
    如果 purge == false && ukey_state == UKEY_OPERATIONAL && (ukey_state == UKEY_VISIBLE && purge)
         bool seq_mismatch = (ukey->dump_seq != dump_seq && ukey->reval_seq != reval_seq);
