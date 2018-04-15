

in_band 与 Out-band 的区别 ?

##监控

packet in 计数 packete, byte

##优化

### packet in 优化

1. 检查 ofconn->packet_in_counter 数据包的数量(大于 100)来检查与控制器是否能正常处理大量 PACKET_IN. 如果存在峰值流量非常大, 可以上调该上限值
2. 每次从 PACKET_IN 队列中取 50 个包发送出去. 在大流量下也可以适当增加该值
3. 可以从日志看到 "dropping packet-in due to queue overflow" 字样, 表面 packet-in 数量已经超出系统可用承载的能力.
4. 从 converage 的 rconn_overflow 可用看出
5. 接受控制器消息, 执行动作, 如果需要返回应答控制器, 最多 50 个(如果给控制器的应答消息队列中数据包大于 100 会提前退出)
6. 非 PACKET_IN 发送的包加入 ofconn->rconn->txq 中
7. 其中 PACKET_IN 原因为 OFPR_NO_MATCH 的包加入 ofconn->schedulers[0].  其他原因的包加入 ofconn->schedulers[1].
8. schedule_packet_in 存在 PACKET_IN 的两次拷贝
9. connmgr_get_controller_info 获取与控制器连接状态

slave 角色只允许监听端口改变消息.

## 设计思路


### 核心组件

connmgr
    ofconn
        ofmonitor
        bundles : 1.4 支持的批量发送 PACKET_IN
    ofservice
    controller
    fail_open : fail_mode = OFPROTO_FAIL_STANDALONE 并且配置 controller 时才有用
    snoop : 创建 punix:${ovs_rundir}/${bridge}.snoop


#### Fail-open mode.

    In fail-open mode, the switch detects when the controller cannot be
    contacted or when the controller is dropping switch connections because the
    switch does not pass its admission control policy.  In those situations the
    switch sets up flows itself using the "normal" action.


1. ovs 与 controller 的一个连接对应一个 ofconn
2. ovs 与所有控制器的连接对应一个 connmgr, 因此 connmgr->all_conns 包含所有的 ofconn
3. 所有的 PACKET_IN 保存正在 pinsched 结构中. 每个 ofconn 包含两个 pinsched.  为什么是两个?
4. PACKET_IN 支持速率限制(burst_limit 表示 pinsched 中存在的最多的数据包数)
5. 一旦删除 ovs 的控制器由有变无或由无变有,都会删除所有流表
6. 判断控制器链路异常切换到 standalone 的时机, min(inactive) > 3 * max(probe_interval)

## 数据结构

1. ofconn 与 connmgr

    ofconn->connmgr

2. connmgr 与 ofproto


角色: 一个交换机与多个控制器连接, 当设置角色的时候, 实际
时对与控制器的连接的角色进行设置.


enum ofconn_type {
    OFCONN_PRIMARY,             // 主动连接
    OFCONN_SERVICE              // 被动连接
};

enum ofproto_band {
    OFPROTO_IN_BAND,            // 与控制器的连接是 In-band
    OFPROTO_OUT_OF_BAND         // 与控制器的连接是 Out-band
};

enum ofp12_controller_role {
    OFPCR12_ROLE_NOCHANGE,    /* Don't change current role. */
    OFPCR12_ROLE_EQUAL,       /* Default role, full access. */
    OFPCR12_ROLE_MASTER,      /* Full access, at most one master. */
    OFPCR12_ROLE_SLAVE,       /* Read-only access. */
};

enum nx_packet_in_format {
    NXPIF_OPENFLOW10 = 0,       /* Standard OpenFlow 1.0 compatible. */
    NXPIF_NXM = 1               /* Nicira Extended. */
};

struct ofconn {

    struct ovs_list node;       //connmgr->all_conns 的成员
    struct hmap_node hmap_node; //connmgr->controllers 的成员

    struct connmgr *connmgr;    /* Connection's manager. */
    struct rconn *rconn;        //实现 socket 连接, 发送, 接受
    enum ofconn_type type;      // 参考 ofconn_type
    enum ofproto_band band;     // 参考 ofproto_band
    bool enable_async_msgs;     // 是否是异步消息

    /* OpenFlow state. */
    enum ofp12_controller_role role;                /* Role. default OFPCR12_ROLE_EQUAL*/
    enum ofputil_protocol protocol;                 /* Current protocol variant. default OFPUTIL_P_NONE*/
    enum nx_packet_in_format packet_in_format;      /* OFPT_PACKET_IN format. default NXPIF_OPENFLOW10*/

    /* OFPT_PACKET_IN related data. */
    struct rconn_packet_counter *packet_in_counter; //处于发送队列, 但是还没有发送出去的包的数量.
#define N_SCHEDULERS 2
    struct pinsched *schedulers[N_SCHEDULERS];      //TODO
    struct pktbuf *pktbuf;                          //保存 OpenFlow Packet In 的 buffer
    /* 如果 table_miss 发送给 controller 的长度 ofconn->type == OFCONN_PRIMARY ? OFP_DEFAULT_MISS_SEND_LEN : 0*/
    int miss_send_len;
    uint16_t controller_id;                         /* Connection controller ID. default 0*/

#define OFCONN_REPLY_MAX 100
    struct rconn_packet_counter *reply_counter; //发送给控制器的消息数(需要控制器应答).

    /* Asynchronous message configuration in each possible roles.
     *
     * A 1-bit enables sending an asynchronous message for one possible reason
     * that the message might be generated, a 0-bit disables it. */
    uint32_t master_async_config[OAM_N_TYPES];      // master, other 角色发送异步消息给控制器的条件
    uint32_t slave_async_config[OAM_N_TYPES];       // slave 角色发送异步消息给控制器的条件

    int n_add, n_delete, n_modify;                  //对流表操作的计数器(增加, 删除, 修改)
    long long int first_op, last_op;                //第一次进行流表操作的时间, 和最新一次操作流表时间
    long long int next_op_report;                   //下一次将流表操作写入日志的时间点.
    long long int op_backoff;                       /* Earliest time to report ops again. defautl LLONG_MIN */

    struct hmap monitors; //监控 packet in 消息.
    uint64_t monitor_paused; //TODO
    struct rconn_packet_counter *monitor_counter;   //ofmonitor 消息计数器

    /* State of monitors for a single ongoing flow_mod.
     *
     * 'updates' is a list of "struct ofpbuf"s that contain
     * NXST_FLOW_MONITOR_REPLY messages representing the changes made by the
     * current flow_mod.
     *
     * When 'updates' is nonempty, 'sent_abbrev_update' is true if 'updates'
     * contains an update event of type NXFME_ABBREV and false otherwise.. */
    struct ovs_list updates;            //TODO
    bool sent_abbrev_update;            //TODO
    struct hmap bundles;                //TODO
};

/* A listener for incoming OpenFlow "service" connections. */
struct ofservice {
    struct hmap_node node;      /* In struct connmgr's "services" hmap. */
    struct pvconn *pvconn;      /* OpenFlow connection listener. */

    int probe_interval;         //当没有收到消息持续 probe_interval 时, 发送 echo request
    int rate_limit;             //对应到 token_bucket->rate
    int burst_limit;            //对应到 token_bucket->burst
    bool enable_async_msgs;     /* Initially enable async messages? */
    uint8_t dscp;               /* DSCP Value for controller connection */
    uint32_t allowed_versions;  /* OpenFlow protocol versions that may
                                 * be negotiated for a session. */
};

/* Connection manager for an OpenFlow switch. */
struct connmgr {
    //交换机
    struct ofproto *ofproto;
    char *name;
    char *local_port_name;                      //设置 in_band 的网卡名.(创建一个 ovs bridge, 就好默认创建一个 internal 的与 bridge 同名的 端口)

    /* OpenFlow connections. */
    struct hmap controllers;     //保留所有主动连接, 即 ovs 主动连接到控制器连接
    struct ovs_list all_conns;   /* All controllers. */
    uint64_t master_election_id;        //role 应答中设置的 id
    bool master_election_id_defined;    //目前实现, 始终是 false

    /* OpenFlow listeners. */
    struct hmap services;       //保留所有被动连接, TODO
    struct pvconn **snoops;
    size_t n_snoops;            /* the number of snoops */

    /* Fail open. */
    /* fail_mode 为 OFPROTO_FAIL_STANDALONE 并且与控制器连接时不为空,
     * 主要用于当与控制器连接发生错误(如网络不可达)时, 将以正常的交换机
     * 模式工作
     */
    struct fail_open *fail_open;
    enum ofproto_fail_mode fail_mode;   //OFPROTO_FAIL_SECURE 或 OFPROTO_FAIL_STANDALONE

    //即与 bridge 同名的 internal 类型的 port 配置信息. 来自 extra_in_band_remotes 与 controllers 中 OFPROTO_IN_BAND tcp ofconn
    struct in_band *in_band;
    struct sockaddr_in *extra_in_band_remotes;  //对应到 ovsdb 的 Open_vSwitch 中的 manager_options 中 in_band 的配置
    size_t n_extra_remotes;                     //extra_in_band_remotes 的元素个数
    int in_band_queue;                          //设置 in_band->queue_id
};

## 核心实现

struct connmgr * connmgr_create(struct ofproto *ofproto, const char *name, const char *local_port_name)

    初始化 connmgr 对象 mgr 并返回 mgr. 指针统一初始化为 NULL, 其他见 struct connmgr 定义
    注: 实际 name, local_port_name 为 datapath_name

void connmgr_destroy(struct connmgr *mgr)

    销毁 mgr

    遍历 mgr->all_conns 所有成员 ofconn, 调用 ofconn_destroy(ofconn);
    如果 mgr->controllers->buckets != mgr->controllers->one, free(mgr->controllers->buckets)
    遍历 mgr->services 所有成员 ofservice,  ofservice_destroy(mgr, ofservice);
    遍历 mgr->snoops 所有成员, 调用 pvconn_close(mgr->snoops[i])
    调用 fail_open_destroy(mgr->fail_open)

void connmgr_run(struct connmgr *mgr, void (*handle_openflow)(struct ofconn *, const struct ofpbuf *ofp_msg))

    TODO
    in_band_run(mgr->in_band)
    LIST_FOR_EACH_SAFE (ofconn, next_ofconn, node, &mgr->all_conns) {
        ofconn_run(ofconn, handle_openflow);
    }
    ofmonitor_run(mgr);
    if (mgr->fail_open)
        fail_open_run(mgr->fail_open);
    HMAP_FOR_EACH (ofservice, node, &mgr->services) {
        struct vconn *vconn;
        retval = pvconn_accept(ofservice->pvconn, &vconn);
        if (!retval)
            rconn = rconn_create(ofservice->probe_interval, 0, ofservice->dscp, vconn_get_allowed_versions(vconn));
            rconn_connect_unreliably(rconn, vconn, name);
            ofconn = ofconn_create(mgr, rconn, OFCONN_SERVICE, ofservice->enable_async_msgs);
            ofconn_set_rate_limit(ofconn, ofservice->rate_limit, ofservice->burst_limit);
    for (i = 0; i < mgr->n_snoops; i++) {
        retval = pvconn_accept(mgr->snoops[i], &vconn);
        if (!retval)
            add_snooper(mgr, vconn);



    最主要的就是将包发送出去, 然后调用回调函数处理应答. 此外, connmgr 中其他运行起来
    1. 更新 in_band 对象 TODO
    2. 遍历 all_conns 中每一个元素 ofconn, 将 ofconn->schedulers 中的包发送出去, 用 handle_openflow 处理对方应答
    3. 如果该 ofconn 的 monitor 有被设置为停止的, 唤醒.
    4. 如果激活而且有其他控制连接, 断了连接时间超过 next_bogus_packet_in, 发送伪造 PACKET_IN, 否则, 等待 2s; 否则设置不在发送伪造包
    5. 遍历 mgr->services, 如果有请求,　就创建对应的 ofconn 连接, 没有就跳过
    6. 遍历 mgr->n_snoops, 如果收到请求, 加入角色最高的 ofconn 的 monitor

void connmgr_wait(struct connmgr *mgr)

    LIST_FOR_EACH (ofconn, node, &mgr->all_conns) {
        ofconn_wait(ofconn);
    }
    ofmonitor_wait(mgr);
    if (mgr->in_band) {
        in_band_wait(mgr->in_band);
    }
    if (mgr->fail_open) {
        fail_open_wait(mgr->fail_open);
    }
    HMAP_FOR_EACH (ofservice, node, &mgr->services) {
        pvconn_wait(ofservice->pvconn);
    }
    for (i = 0; i < mgr->n_snoops; i++) {
        pvconn_wait(mgr->snoops[i]);
    }

void connmgr_get_memory_usage(const struct connmgr *mgr, struct simap *usage)

    计算当前 mgr 中的连接数和包数(已经发送, 未发送和在缓冲区(buffer_id)的)

bool connmgr_has_controllers(const struct connmgr *mgr)

    connmgr 是否与控制连接

void connmgr_get_controller_info(struct connmgr *mgr, struct shash *info)

    获取控制状态信息, 包括

    is_connected
    role
    last_error
    state
    sec_since_connect
    sec_since_disconnect

    packet-in-miss-backlog : stats.n_queued
    packet-in-miss-bypassed : stats.n_normal
    packet-in-miss-queued : stats.n_limited
    packet-in-miss-dropped : stats.n_queue_dropped

    packet-in-action-backlog : stats.n_queued
    packet-in-action-bypassed : stats.n_normal
    packet-in-action-queued : stats.n_limited
    packet-in-action-dropped : stats.n_queue_dropped

void connmgr_free_controller_info(struct shash *info)

    销毁 info

void connmgr_set_controllers(struct connmgr *mgr, const struct ofproto_controller *controllers, size_t n_controllers, uint32_t allowed_versions)

    1. 用 controllers 重置 mgr 的 controllers 或 ofservice(删除旧的 controller 以及 ofservice, 更新已经存在的)
    2. 用 mgr->controllers 和 mgr->extra_in_band_remotes　中解析出的 sockaddr_in 来初始化 mgr->in_band 对象
    3. 设置 mgr->fail_open(如果 mgr 配置 controller 而且 fail_mode = OFPROTO_FAIL_STANDALONE ; mgr->fail_open 才有意义; 否则 mgr->fail_open = NULL)
    4. 更新 mgr->controller 由 null 变为 nonull, 或 nonull 变为 null; 刷新所有流表

void connmgr_free_controller_info(struct shash *info)

    释放 info 中的统计信息

void connmgr_set_controllers(struct connmgr *mgr, const struct ofproto_controller *controllers, size_t n_controllers, uint32_t allowed_versions)

    遍历 controllers 中每个元素 controller, 加入 mgr 的 controllers 或 ofservice 中, 删除旧的 controller
    以及 ofservice.

void connmgr_reconnect(const struct connmgr *mgr)

    如果 mgr->ofconn 中的连接没有断开, 断开重连

int connmgr_set_snoops(struct connmgr *mgr, const struct sset *snoops)

    删除 mgr->snoops  中的旧元素, 将 snoops 增加进去

void connmgr_get_snoops(const struct connmgr *mgr, struct sset *snoops)

    将 mgr->snoops 中的 name 加入 snoops 中

bool connmgr_has_snoops(const struct connmgr *mgr)

    return mgr->n_snoops > 0;

static void add_controller(struct connmgr *mgr, const char *target, uint8_t dscp, uint32_t allowed_versions)

    增加一个新的 ofconn 到 mgr->controllers, 建立连接

static struct ofconn * find_controller_by_target(struct connmgr *mgr, const char *target)

    查找 mgr->controllers 中是否存在 target 的 ofconn

static void update_in_band_remotes(struct connmgr *mgr)

    用 mgr->controllers(ofconn->type = OFPROTO_IN_BAND) 和 mgr->extra_in_band_remotes　中解析出的 sockaddr_in 来初始化 mgr->in_band 对象

static void update_fail_open(struct connmgr *mgr)

    如果 mgr 配置 controller 而且 fail_mode = OFPROTO_FAIL_STANDALONE ; 创建 mgr->fail_open. 否则 删除 mgr->fail_open, mgr->fail_open = NULL
    注: 由上可知 mgr->fail_open 只有在 fail_mode = OFPROTO_FAIL_STANDALONE 并且配置 controller 时才有用

static int set_pvconns(struct pvconn ***pvconnsp, size_t *n_pvconnsp, const struct sset *sset)

    删除 pvonnsp 中的 n_pvconnsp 个旧元素, 将 sset 增加进去

static int snoop_preference(const struct ofconn *ofconn)

    返回 ofconn->role 的最大值

static void add_snooper(struct connmgr *mgr, struct vconn *vconn)

    从 connmgr->all_conns 的 ofconn 中找到 ofconn->type = OFCONN_PRIMARY 并且
    ofconn->role 最大(即权限越接近MASTER)的 ofconn. 将 vconn 加入 该 ofconn->monitors

enum ofconn_type ofconn_get_type(const struct ofconn *ofconn)

    获取 ofconn 连接类型 OFCONN_PRIMARY(主动连接, 交换机) OFCONN_SERVICE(被动连接, OVN)

bool ofconn_get_master_election_id(const struct ofconn *ofconn, uint64_t *idp)

    将 connmgr->master_election_id 保存在 idp, 返回是否开启 master_election_id_defined

enum ofp12_controller_role ofconn_get_role(const struct ofconn *ofconn)

    获取当前与控制器连接的角色

void ofconn_send_role_status(struct ofconn *ofconn, uint32_t role, uint8_t reason)

    构造 role status 消息(应答控制器的角色请求), 请求设置当前 ofconn 连接的角色为 role.(1.4 协议才支持)

void ofconn_set_role(struct ofconn *ofconn, enum ofp12_controller_role role)

    如果 role 是 MASTER 角色, 将已经存在的 MASTER 角色的 ofconn 设置为 SLAVE.
    否则直接设置 ofconn->role = role

void ofconn_set_invalid_ttl_to_controller(struct ofconn *ofconn, bool enable)

    当前 enable 为 true 时, 当出现 invaild ttl 时, 给控制器发送 PACKET_IN 消息
    当前 enable 为 false 时, 当出现 invaild ttl 时, 不给控制器发送 PACKET_IN 消息

bool ofconn_get_invalid_ttl_to_controller(struct ofconn *ofconn)

    当出现 invaild ttl 时, 是否给控制器发送 PACKET_IN 消息

enum ofputil_protocol ofconn_get_protocol(const struct ofconn *ofconn)

    获取当前 ofconn 的协议

void ofconn_set_protocol(struct ofconn *ofconn, enum ofputil_protocol protocol)

    设置当前 ofconn 的协议

enum nx_packet_in_format ofconn_get_packet_in_format(struct ofconn *ofconn)

    return ofconn->packet_in_format;

    获取 PACKET_IN 的格式, 包括 OpenFlow1.0 和 Nicira 扩展支持两种.


void ofconn_set_packet_in_format(struct ofconn *ofconn, enum nx_packet_in_format packet_in_format)

    ofconn->packet_in_format = packet_in_format;

    设置 PACKET_IN 的格式, 包括 OpenFlow1.0 和 Nicira 扩展支持两种.


void ofconn_set_controller_id(struct ofconn *ofconn, uint16_t controller_id)

    ofconn->controller_id = controller_id;

int ofconn_get_miss_send_len(const struct ofconn *ofconn)

    return ofconn->miss_send_len;

void ofconn_set_miss_send_len(struct ofconn *ofconn, int miss_send_len)

    ofconn->miss_send_len = miss_send_len;

void ofconn_set_async_config(struct ofconn *ofconn, const uint32_t master_masks[OAM_N_TYPES], const uint32_t slave_masks[OAM_N_TYPES])

    用 master_masks, slave_masks 设置发送 PACKET_IN 消息的条件

    memcpy(ofconn->master_async_config, master_masks, size);
    memcpy(ofconn->slave_async_config, slave_masks, size);

void ofconn_get_async_config(struct ofconn *ofconn, uint32_t *master_masks, uint32_t *slave_masks)

    获取发送 PACKET_IN 消息的条件, 保存在 master_masks, slave_masks

    memcpy(master_masks, ofconn->master_async_config, size);
    memcpy(slave_masks, ofconn->slave_async_config, size);

void ofconn_send_reply(const struct ofconn *ofconn, struct ofpbuf *msg)

    将 msg 发送给 ofconn 对应的控制器, 并更新应答计数器

void ofconn_send_replies(const struct ofconn *ofconn, struct ovs_list *replies)

    将 replies 中的所有消息, 依次发送给 ofconn 对应的控制器, 并更新应答计数器

void ofconn_send_error(const struct ofconn *ofconn, const struct ofp_header *request, enum ofperr error)

    由 error, request 构造消息, 发送给 ofconn 对应的控制器

enum ofperr ofconn_pktbuf_retrieve(struct ofconn *ofconn, uint32_t id, struct dp_packet **bufferp, ofp_port_t *in_port)

    从 PACKET_IN 的 buffer(ofconn->pkgbuf) 中取 id 对应的 packet. bufferp
    指向该 packet, in_port 指向包进入的端口

    如果 id >> PKTBUF_MASK 与 ofconn->pkgbuf 中的 cookie 对应, 那么

         bufferp = ofconn->pktbuf->packet[id & PKTBUF_MASK]->buff,
         in_port = ofconn->pktbuf->packet[id & PKTBUF_MASK]->in_port

    注: id 为 buffer_id, 低 0-7 位为 buffer number, 第 9-31 是 cookie id

void ofconn_report_flow_mod(struct ofconn *ofconn, enum ofp_flow_mod_command command)

    更新流表项修改操作计数器.

static inline uint32_t bundle_hash(uint32_t id)

    return hash_int(id, 0);

struct ofp_bundle * ofconn_get_bundle(struct ofconn *ofconn, uint32_t id)

    从 ofconn->bundles 中找到第一个匹配 id 的 bundle

enum ofperr ofconn_insert_bundle(struct ofconn *ofconn, struct ofp_bundle *bundle)

    将 bundle 插入 ofconn->bundles

enum ofperr ofconn_remove_bundle(struct ofconn *ofconn, struct ofp_bundle *bundle)

    将 bundle 从 ofconn->bundles 中删除

static void bundle_remove_all(struct ofconn *ofconn)

    将 ofconn->bundles 中的消息依次全部清除

static const char * ofconn_get_target(const struct ofconn *ofconn)

    获取 ofconn->rconn->target

static struct ofconn * ofconn_create(struct connmgr *mgr, struct rconn *rconn, enum ofconn_type type, bool enable_async_msgs)

    初始化 ofconn

static void ofconn_flush(struct ofconn *ofconn)

    重新初始化 ofconn 的各个成员

static void ofconn_destroy(struct ofconn *ofconn)

    销毁 ofconn

static void ofconn_reconfigure(struct ofconn *ofconn, const struct ofproto_controller *c)

    用控制器消息初始化 ofconn 相关属性

static bool ofconn_may_recv(const struct ofconn *ofconn)

    当 ofconn 发送队列中的数据包少于 100, 返回 true
    当 ofconn 发送队列中的数据包大于等于 100, 返回 false

static void ofconn_run(struct ofconn *ofconn, void (\*handle_openflow)(struct ofconn *, const struct ofpbuf *ofp_msg))

    1. 从 ofconn->schedulers 每个元素中取 50 个元素加入 ofconn->rconn->txq 中:
       如果 ofconn->packet_in_counter->n_packets < 100, 且 ofconn->rconn 处于连接状态, 遍历 ofconn->rconn->monitors 每个元素 monitor,
        1) 将包发送给 monitor 所对应的连接, 如果发送失败, 将对应的 monitor 删除;
        2) pin->list_node 加入 ofconn->rconn->txq 链表尾, 等待发送;
       否则, 将 pin 丢弃(即是否内存), 返回 EAGAIN
    2. 确保 rc->vconn 和 rc->monitors 都处于连接建立状态, 将 ofconn->rconn->txq 中的数据依次发送给控制器
    3. 接受控制器消息, 执行动作(由 handle_openflow 完成), (如果需要返回应答控制器, 最多 50 个; 如果给控制器的应答消息队列中数据包大于 100 会提前退出)
    4. 如果达到下一次写流表操作统计信息的时间点, 将流表操作统计信息写入日志

static void ofconn_wait(struct ofconn *ofconn)

    1. 如果 pinsched(ofconn->schedulers[i]->token_bucket) 超过 1000, 直接返回,
       否则设置当前线程的 pool-loop 下次唤醒时间为 pinsched->token_bucket->last_fill + (1000 - pinsched->token_bucket->token)/pinsched->token_bucket->rate + 1 ms
    2. vconn 中注册数据可发送的事件到 poll(monitors 中注册数据可发送和可接受的事件), 设置当前线程 pool-loop 唤醒时间为当前 ofconn 的超时时间
    3. 如果给控制器的应答消息队列中数据包小于 100, 将 ofconn 的可读事件注册到当前线程的 pool-loop
    4. 设置当前线程 pool-loop 唤醒时间为 ofconn->next_op_report

static void ofconn_log_flow_mods(struct ofconn *ofconn)

    将 ofconn 的流表项操作统计写入日志.

static bool ofconn_receives_async_msg(const struct ofconn *ofconn, enum ofputil_async_msg_type type, unsigned int reason)

    是否可以发送 type 类型的异步消息给控制器.

    给控制发送异步消息的条件:
    1. 已经与控制器建立连接
    2. 已经协商好协议版本
    3. 类型为 OFCONN_PRIMARY
    4. 类型为 OFCONN_SERVICE & miss_send_len != 0
    5. 如果角色为 slave, slave_async_config[type] & 1 << reason == 1
    5. 如果角色为 master, master_async_config[type] & 1 << reason == 1

static bool ofconn_wants_packet_in_on_miss(struct ofconn *ofconn, const struct ofproto_packet_in *pin)

    当 table-miss 时, 是否发送 PACKET_IN.

    不发送的条件:
    1. 已经协商协议版本
    2. 协议版本 >= 1.3
    3. ofconn->connmgr->ofproto->tables[pin->up.table_id].miss_config == OFPUTIL_TABLE_MISS_DEFAULT

bool connmgr_wants_packet_in_on_miss(struct connmgr *mgr) OVS_EXCLUDED(ofproto_mutex)

    连接管理(mgr)中是否存在 table_miss 的时候发送 PACKET_IN 的 ofconn

    满足发送 PACKET_IN 的条件(注: OpenFlow1.3 之后 table_miss 默认为 drop, OpenFlow1.3 之前默认 packet in controller):
    1. ofconn->controller_id = 0
    2. 没有制定协议版本, 版本小于 1.3

static char * ofconn_make_name(const struct connmgr *mgr, const char *target)

    return xasprintf("%s<->%s", mgr->name, target);

static void ofconn_set_rate_limit(struct ofconn *ofconn, int rate, int burst)

    设置 PACKET_IN 的 rate(平均) 与 burst(峰值) 速率

static void ofconn_send(const struct ofconn *ofconn, struct ofpbuf *msg,

    如果 ofconn->rconn 处于连接状态, 将 msg 拷贝给 ofconn->rconn->monitors 的每一个成员, msg->list_node 加入 ofconn->rconn->txq 链表尾
    否则 直接释放 b 的内存

void connmgr_send_port_status(struct connmgr *mgr, struct ofconn *source, const struct ofputil_phy_port *pp, uint8_t reason)

    遍历 mgr->all_conns 所有元素 ofconn, 如果可以发送 OAM_PORT_STATUS 类型的异步消息, 发送端口状态消息给所有控制器(ofconn->rconn->conn->version 小于 1.5 或 ofconn != source 除外)

void connmgr_send_flow_removed(struct connmgr *mgr, const struct ofputil_flow_removed *fr)

    遍历 mgr->all_conns 所有元素 ofconn, 如果可以发送 OAM_FLOW_REMOVED
    类型的异步消息, 发送流表删除状态消息给所有控制器, 并更新计数器(ofconn->rconn->conn->version 小于 1.5 或 ofconn != source 除外)

static enum ofp_packet_in_reason wire_reason(struct ofconn *ofconn, const struct ofproto_packet_in *pin)

    解析 pin, 获取发送 PACKET_IN 时的 reason

void connmgr_send_packet_in(struct connmgr *mgr, const struct ofproto_packet_in *pin)

    遍历  mgr->all_conns 每个元素 ofconn, 如果 ofconn 满足发送 PACKET_IN 条件,
    用 pin 构造 PACKET_IN 加入 ofconn->rconn->txq 队列

    满足 PACKET_IN 条件:

    1. pin->miss_type == OFPROTO_PACKET_IN_MISS_WITHOUT_FLOW, 协议
    2. pin.controller_id = ofconn->controller_id
    3. 支持发送 OAM_PACKET_IN 给控制器
    4. 不满足如下全部的条件:
        1. 协议版本 >= 1.3
        2. ofconn 的表(pin->up.table_id) 的 miss_config 是 OFPUTIL_TABLE_MISS_DEFAULT
        3. pin->miss_type 由于没有匹配的流


static void do_send_packet_ins(struct ofconn *ofconn, struct ovs_list *txq)

    将 txq 列表每个元素加入 ofconn->rconn->txp 中, 等待发送

    1. 遍历 txq 每个元素 pin
    2. 如果 ofconn->packet_in_counter->n_packets < 100, 且 ofconn->rconn 处于连接状态, 遍历 ofconn->rconn->monitors 每个元素 monitor, 
        将 pin 发送给 monitor 所对应的连接, 如果发送失败, 将对应的 monitor 删除,
        更新 counter 之后保持在 pin->header, pin->list_node 加入 ofconn->rconn->txq 链表尾, 等待发送
    3. 否则, 将 pin 丢弃(即是否内存), 返回 EAGAIN


static void schedule_packet_in(struct ofconn *ofconn, struct ofproto_packet_in pin, enum ofp_packet_in_reason wire_reason)

    1. 构造一个 PACKET_IN 消息 packet,

    2. 将 packet 加入临时队列

        对于保存 PACKET_IN 的 pinsched(ofconn->schedulers[pin.up.reason == OFPR_NO_MATCH ? 0 : 1])

        如果 pinsched 为 NULL, 将 packet 加入临时队列 txq
        如果 pinqueue->n_queued = 0 && pinsched->token_bucket->tokens > 100, 表明不进行速率限制, 将 pinsched->n_normal++, packet 加入临时队列 txq
        否则, 进行速率限制, 将 packet 加入 pinsched->queues 中 port_no 对应的 pinqueue.

    3. 将 txq 列表每个元素加入 ofconn->rconn->txq 中, 等待发送

        遍历 txq 每个元素 pin
        如果 ofconn->packet_in_counter->n_packets < 100, 且 ofconn->rconn 处于连接状态, 遍历 ofconn->rconn->monitors 每个元素 monitor,
        将 pin 发送给 monitor 所对应的连接, 如果发送失败, 将对应的 monitor 删除, 更新 counter 之后保持在 pin->header,
        pin->list_node 加入 rc->txq 链表尾, 等待发送
        否则, 将 pin 丢弃(即是否内存), 返回 EAGAIN

    TODO 这里存在包的两次拷贝. 是否可以优化?

enum ofproto_fail_mode connmgr_get_fail_mode(const struct connmgr *mgr)

    获取 fail_mode, 目前支持
    OFPROTO_FAIL_SECURE : 保留 flow table, 如果 packet 没有匹配的流, 依赖控制器, 如果控制器宕机, 丢掉.
    OFPROTO_FAIL_STANDALONE : 如果 packet 没有匹配的流, 作为普通的交换机转发

void connmgr_set_fail_mode(struct connmgr *mgr, enum ofproto_fail_mode fail_mode)

    1. 设置 ngr 的 mgr->fail_mode
    2. 配置 mgr 的 fail_open
        如果 mgr 配置 controller 而且 fail_mode = OFPROTO_FAIL_STANDALONE ; 创建 mgr->fail_open.
        否则 删除 mgr->fail_open, mgr->fail_open = NULL
        注: 由上可知 mgr->fail_open 只有在 fail_mode = OFPROTO_FAIL_STANDALONE 才有用
    3. 如果没有控制器, 删除所有流表项

int connmgr_get_max_probe_interval(const struct connmgr *mgr)

    返回 mgr->controllers 所有 ofconn 中 probe_interval 最大值

int connmgr_failure_duration(const struct connmgr *mgr)

    如果找到控制器和交换机一直连接, 返回 INT_MAX
    如果 mgr 没有控制连接, 返回 0
    如果控制器和交换机失去连接, mgr->controllers 的 ofconn 中找到上次失去连接到现在的最短时间
    TODO: 如果一直保持连接与没有控制器都返回 0, 似乎矛盾

bool connmgr_is_any_controller_connected(const struct connmgr *mgr)

    mgr 是否与任一控制器连接

bool connmgr_is_any_controller_admitted(const struct connmgr *mgr)

    mgr 中存在 ofconn->rconn 满足:
        rconn 是否一直被控制器管理, 即 rconn 和对端已经建立连接, 并且上次接受控制消息的时间在建立连接之后

void connmgr_set_extra_in_band_remotes(struct connmgr *mgr, const struct sockaddr_in *extras, size_t n)

    如果mgr->extra_in_band_remotes 与 extras 没有改变, 直接返回
    否则, 清空 mgr->extra_in_band_remotes, 新 extras 初始化 mgr->extra_in_band_remotes, 并更新 mgr->in_band

void connmgr_set_in_band_queue(struct connmgr *mgr, int queue_id)

    如果 mgr->in_band 与 queue_id 相同, 直接返回
    否则, 重置 mgr->in_band_queue 为 queue_id, 并更新 mgr->in_band

static bool any_extras_changed(const struct connmgr *mgr, const struct sockaddr_in *extras, size_t n)

    检查 mgr->extra_in_band_remotes 与参数 extras 是否相同. 如果相同, 说明被改变了, 返回 true, 否则返回 false

    即如果 mgr->n_extra_remotes = n && mgr->extra_in_band_remotes = extras, 返回 false, 否则返回 true

bool connmgr_has_in_band(struct connmgr *mgr)

    return mgr->in_band != NULL;

void connmgr_flushed(struct connmgr *mgr)

    决定是否切换到 standalone 模式
    1. 如果与控制器连接, 但是与控制器连接达到认为连接异常的条件, 切换到 standalone 模式
    2. 如果没有与控制器连接, 并且时 OFPROTO_FAIL_STANDALONE 模式, 切换到 standalone 模式

    注: 连接异常条件: min(与所有控制器没有消息传递时间) > max(所有控制器 probe_interval) * 3

int connmgr_count_hidden_rules(const struct connmgr *mgr)

    计算隐藏流表的个数(mgr->in_band + mgr->fail_open 的元素个数之和)

static int ofservice_create(struct connmgr *mgr, const char *target, uint32_t allowed_versions, uint8_t dscp)

    根据 target 监听客户端连接, 并初始化 ofservice, 分配 ofservice 对象, 之后加入 mgr->services

static void ofservice_destroy(struct connmgr *mgr, struct ofservice *ofservice)

    从 mgr->services 中删除 ofservice, 关闭 ofservice->pvconn

static void ofservice_reconfigure(struct ofservice *ofservice, const struct ofproto_controller *c)

    用 c 重新配置 ofservice

static struct ofservice * ofservice_lookup(struct connmgr *mgr, const char *target)

    遍历 mgr->services 找到 pvconn->name 为 target 的 ofservice

enum ofperr ofmonitor_create(const struct ofputil_flow_monitor_request *request, struct ofconn *ofconn, struct ofmonitor **monitorp)

    初始化 ofmonitor

struct ofmonitor * ofmonitor_lookup(struct ofconn *ofconn, uint32_t id)

    遍历 ofconn->monitors 中 id 对应的 ofmonitor

void ofmonitor_destroy(struct ofmonitor *m)

    销毁 ofmonitor

void ofmonitor_report(struct connmgr *mgr, struct rule *rule, enum nx_flow_update_event event, enum ofp_flow_removed_reason reason, const struct ofconn *abbrev_ofconn, ovs_be32 abbrev_xid, const struct rule_actions *old_actions)

    TODO
    遍历 mgr->all_conns 的每一个 ofconn 中

    如果存在 ofmonitor 与 rule 匹配, 在满足一定条件的情况下, 将 rule 对应的 ofputil_flow_update 加入
    ofconn->updates 中

    满足一定的条件:
    1. ofconn->sent_abbrev_update = false
    2. flags & NXFMF_OWN || ofconn != abbrev_ofconn || ofconn->monitor_paused

void ofmonitor_flush(struct connmgr *mgr)

    遍历 mgr->all_conns 中的每一个 ofconn, 对每个 ofconn->updates 中的 msg,
    如果 ofconn->rconn 处于连接状态, 将 msg 拷贝给 ofconn->rconn->monitors 的每一个成员, msg->list_node 加入 ofconn->rconn->txq 链表尾, 等待发送
    如果 ofconn->monitor_counter->n_bytes 大于 128 * 1024, 构造 pause 消息, 记录 monitor_seqno, 将 pause 拷贝给 ofconn->rconn->monitors 的每一个成员, pause->list_node 加入 ofconn->rconn->txq 链表尾.

static void ofmonitor_resume(struct ofconn *ofconn)

    遍历 ofconn->monitors 的每个 monitor, 根据 monitor->table 找到流表, 根据
    monitor->match 找到对应的 rules, 将 rules 加入 ofconn->rconn->txq 中等待发送
    1. 遍历 ofconn->monitors 中的每一个 ofmonitor 对象 m
    2. 在 m->ofconn->connmgr->ofproto 中找到 table_id = m->table_id  的 table
       遍历 table->cls 表的每一条流表项, rule 为对应的流表项在 m->flags 的监控范围, 加入 rules
    3. 遍历 rules 每个元素加入 msgs 中
    4. 遍历 msgs 中的每一个元素 msg, 如果 ofconn 处于连接状态, 将 msg 拷贝给 ofconn->rconn->monitors
      的每一个成员, msg->list_node 加入 ofconn->rconn->txq 链表尾, 等待发送

static bool ofmonitor_may_resume(const struct ofconn *ofconn)

    ofconn->monitor_paused != 0 && ofconn->monitor_counter->n_packets = 0

static void ofmonitor_run(struct connmgr *mgr)

    遍历 mgr->all_conns 的所有 ofconn:

    如果该 ofconn 的 monitor 应该唤醒(ofconn->monitor_paused != 0 && ofconn->monitor_counter->n_packets = 0), 唤醒.
    否则什么也不做

    其中唤醒操作包括:
    遍历 ofconn->monitors 的每个 monitor, 根据 monitor->table 找到流表, 根据
    monitor->match 找到对应的 rules, 将 rules 加入 ofconn->rconn->txq 中等待发送

static void ofmonitor_wait(struct connmgr *mgr)

    遍历 mgr->all_conns 的所有 ofconn:

    如果该 ofconn 的 monitor 应该唤醒(ofconn->monitor_paused != 0 && ofconn->monitor_counter->n_packets = 0), 唤醒.
    否则什么也不做

    其中唤醒操作包括:
    将当前线程的 poll_loop 的下一次运行时间设置为 now
