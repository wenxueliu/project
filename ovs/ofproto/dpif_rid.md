
## 设计

### 创建

通过 ofproto 和 recirc_state 生成一个 recirc_id_node

### 查询

通过 id 和 recirc_state 索引

### 销毁

通过引用计数(recirc_id_node->refcount)来维护是否需要删除

目前被 bond 和 upcall 用到

## 数据结构

static struct cmap id_map; 包含 recirc_id_node, 通过 id 索引
static struct cmap metadata_map;

static struct ovs_list expiring; //保存引用计数为 0 的 recirc_id_node
static struct ovs_list expired;

static uint32_t next_id; //recirc_id_node 的 id, 全局单调递增

//由 flow 初始化
struct recirc_metadata {
    /* Metadata in struct flow. */
    struct flow_tnl tunnel;       /* Encapsulating tunnel parameters. */
    ovs_be64 metadata;            /* OpenFlow Metadata. */
    uint64_t regs[FLOW_N_XREGS];  /* Registers. */
    ofp_port_t in_port;           /* Incoming port. */
    ofp_port_t actset_output;     /* Output port in action set. */
};

struct recirc_state {
    /* Initial table for post-recirculation processing. */
    uint8_t table_id;

    /* Pipeline context for post-recirculation processing. */
    struct ofproto_dpif *ofproto; /* Post-recirculation bridge. */
    struct recirc_metadata metadata; /* Flow metadata. */
    struct ofpbuf *stack;         /* Stack if any. */
    mirror_mask_t mirrors;        /* Mirrors already output. */

    /* Actions to be translated on recirculation. */
    uint32_t action_set_len;      /* How much of 'ofpacts' consists of an
                                   * action set? */
    uint32_t ofpacts_len;         /* Size of 'ofpacts', in bytes. */
    struct ofpact *ofpacts;       /* Sequence of "struct ofpacts". */
};

struct recirc_id_node {
    /* Index data. */
    struct ovs_list exp_node OVS_GUARDED;
    struct cmap_node id_node;
    struct cmap_node metadata_node;
    uint32_t id;                        //唯一标记一个 recirc_id_node, 通过 next_id 设置
    uint32_t hash;                      //metadata_map 查找时的索引, 来自对 recirc_state 的哈希
    struct ovs_refcount refcount;       //该 recirc_id_node 被引用的次数

    /* Saved state.
     *
     * This state should not be modified after inserting a node in the pool,
     * hence the 'const' to emphasize that. */
    const struct recirc_state state;
};


### 核心实现

static inline bool recirc_id_node_try_ref_rcu(const struct recirc_id_node *n_)

    struct recirc_id_node *node = CONST_CAST(struct recirc_id_node *, n_);
    return node ? ovs_refcount_try_ref_rcu(&node->refcount) : false;

void recirc_init(void)

    初始化 recirc

void recirc_run(void)

    每 250 ms 将 expiring 移动到 expired, 将 expired 中元素从 id_map 中删除, 将待删除
    recirc_id_node 加入当前线程的 ovsrcu_perthread, 等待删除

static struct recirc_id_node * recirc_find__(uint32_t id)

    从 id_map 中找到 id 对应的 recirc_id_node

const struct recirc_id_node * recirc_id_node_find(uint32_t id)

    从 id_map 中找到 id 对应的 recirc_id_node

static uint32_t recirc_metadata_hash(const struct recirc_state *state)

   对 state 每个成员进行 hash, 返回哈希之后的值

static bool recirc_metadata_equal(const struct recirc_state *a, const struct recirc_state *b)

    比较两个 recirc_state 是否相同

static struct recirc_id_node * recirc_find_equal(const struct recirc_state *target, uint32_t hash)

    从 metadata_map 中找到 target 对应的 recirc_id_node

static struct recirc_id_node * recirc_ref_equal(const struct recirc_state *target, uint32_t hash)

    从 metadata_map 中找到 target 对应的 recirc_id_node, 且该 recirc_id_node 的引用计数不为 0

static void recirc_state_clone(struct recirc_state *new, const struct recirc_state *old)

    将 old 拷贝给 new

static struct recirc_id_node * recirc_alloc_id__(const struct recirc_state *state, uint32_t hash)

    创建并初始化一个 recirc_id_node.

uint32_t recirc_find_id(const struct recirc_state *target)

    在 metadata_map 中找到 target 对应的 recirc_id_node:
    如果找到, 返回 recirc_id_node->id
    如果没有找到, 返回 0

uint32_t recirc_alloc_id_ctx(const struct recirc_state *state)

    在 metadata_map 中 state 对应的 recirc_id_node, 且仍然在使用(recirc_id_node->refcount != 0)
    如果找到, 返回 recirc_id_node->id
    如果没有找到, 生成一个新的节点, 并返回节点的 id

uint32_t recirc_alloc_id(struct ofproto_dpif *ofproto)

   由 ofproto 生成一个 recirc_id_node, 返回分配 recirc_id_node->id

void recirc_id_node_unref(const struct recirc_id_node *node_)

   将 node_ 的引用计数减一, 如果引用计数减到 0, 从 metadata_map 中删除 node_, 并将其加入 expiring 列表 中

void recirc_free_id(uint32_t id)

    将 id 对应的 recirc_id_node 的引用计数减一, 如果引用计数减到 0, 从 metadata_map 中删除 node, 并将其加入 expiring 列表中

    从 id_map 找到 id 对应的 recirc_id_node 对象 node:
    1. 如果找不到, 打印错误日志.
    2. 如果找到, node 的引用计数减一, 如果引用计数减到 0, 从 metadata_map 中删除 node, 并将其加入 expiring 列表中

void recirc_free_ofproto(struct ofproto_dpif *ofproto, const char *ofproto_name)

    如果 ofproto 在 metadata_map 中, 打印错误日志
