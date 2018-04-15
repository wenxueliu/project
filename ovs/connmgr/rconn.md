
对 vconn 进行状态维护, 使得具有稳定的连接, 也体现了分层的思想, vconn 专注连接, 而 rconn 进行连接的状态管理和统计

1. 进行链路保活(probe)
2. 断开重连(backoff)
3. 发送队列中的包计数器(包数, byte 数) rconn_packet_counter.
4. 链路监控(monitors)

### 数据结构

struct rconn {
    struct ovs_mutex mutex;

    enum state state;           //当前连接的状态
    time_t state_entered;       //处于当前状态的开始时间点

    struct vconn *vconn;
    char *name;                 /* Human-readable descriptive name. */
    char *target;               /* vconn name, passed to vconn_open(). */
    bool reliable;              // CONNECTING 设置为 true; ACTIVE 为 false

    struct ovs_list txq;        /* Contains "struct ofpbuf"s. */

    int backoff;                //当 state 处于 S_BACKOFF 时, 必须小于 max_backoff
    int max_backoff;
    time_t backoff_deadline;    //每次建立连接成功时设置为 time_now() + backoff; 失败时设置为 TIME_MAX
    time_t last_connected;      //当成功建立连接后为 state_entered
    time_t last_disconnected;
    unsigned int seqno;         //如果由 connected 变为 unconected, 或 unconected 变为 connected, 加 1
    int last_error;             //0: 主动断开连接; EOF:被对端断开连接; >0:错误

    bool probably_admitted;     //由 connected 的状态变为 unconnected 设置为 false. 连接已经建立 30 s 或收到 openflow 管理类消息设置 true
    time_t last_admitted;       //更新时机: 如果连接已经建立 30 s 或 收到 openflow 管理类消息, 或者 probably_admitted 为 ture

    unsigned int n_attempted_connections;       //每次建立连接 reconnect
    unsigned int n_successful_connections;      //已经成功建立连接的次数
    time_t creation_time;
    unsigned long int total_time_connected;     //当前连接已经建立连接时长

    int probe_interval;         //必须大于 5 sec 或 0
    time_t last_activity;       //上次发送或接受数据的时间, 用于 probe 探测

    uint8_t dscp;

#define MAXIMUM_MONITORS 8
    struct vconn *monitors[MAXIMUM_MONITORS];
    size_t n_monitors;

    uint32_t allowed_versions;
};

#### STATE 的转变条件

S_VOID: 没有开始连接
S_CONNECTING : 正在建立连接, 但还没有完成
S_ACTIVE : 已经建立连接, 距离上次数据交互, 但还没有超过 probe_interval
S_IDLE : 已经建立连接, 距离上次数据交互超过 probe_interval, 而且 ECHO Request 已经发出, 等待回应
S_BACKOFF: 对与非正常断开连接, 如果设置了 reliable, 那么就进入该状态, 该状态进行重连,每次递增 2*backoff, 直到重连成功或达到 max_backoff.
S_DISCONNECTED : 已经断开连接, 不能重试

处于 IDLE 或 ACTIVE 认为时连接已经建立


timeout_IDLE : rc->probe_interval;
timeout_CONNECTING : MAX(1, rc->backoff);
timeout_ACTIVE: MAX(rc->last_activity, rc->state_entered) + rc->probe_interval - rc->state_entered;
timeout_DISCONNECTED : UINT_MAX;
timeout_BACKOFF : return rc->backoff;

####使用范例

```
    retval = pvconn_accept(ofservice->pvconn, &vconn);
    if (!retval) {
        struct rconn *rconn;
        char *name;

        /* Passing default value for creation of the rconn */
        rconn = rconn_create(ofservice->probe_interval, 0, ofservice->dscp,
                             vconn_get_allowed_versions(vconn));
        name = ofconn_make_name(mgr, vconn_get_name(vconn));
        rconn_connect_unreliably(rconn, vconn, name);
        free(name);

        ovs_mutex_lock(&ofproto_mutex);
        ofconn = ofconn_create(mgr, rconn, OFCONN_SERVICE,
                               ofservice->enable_async_msgs);
        ovs_mutex_unlock(&ofproto_mutex);

        ofconn_set_rate_limit(ofconn, ofservice->rate_limit,
                              ofservice->burst_limit);
    } else if (retval != EAGAIN) {
        VLOG_WARN_RL(&rl, "accept failed (%s)", ovs_strerror(retval));
    }
```
```
    ofconn = ofconn_create(mgr, rconn_create(5, 8, dscp, allowed_versions),
                           OFCONN_PRIMARY, true);
    ofconn->pktbuf = pktbuf_create();
    rconn_connect(ofconn->rconn, target, name);
    hmap_insert(&mgr->controllers, &ofconn->hmap_node, hash_string(target, 0));
```

rconn_create(rc) : 创建并初始化一个可靠连接对象 rc
rconn_connect() : 进行可靠连接, 即如果遇到错误会进入 BACKOFF 状态重连
rconn_add_monitor() : 给 rc->monitors 增加一个元素

####核心函数简介

rconn_create(rc) : 创建并初始化一个可靠连接对象 rc
rconn_destroy(rc) : 销毁可靠连接对象 rc
rconn_connect() : 进行可靠连接, 即如果遇到错误会进入 BACKOFF 状态重连
rconn_connect_unreliably() : 进行不可靠连接, 即如果遇到错误直接断开
rconn_reconnect() : 如果从 ACTIVE 或 IDLE 状态进入 BACKOFF 状态
rconn_disconnect() : 如果从非 S_VOID 进入 S_VOID
rconn_run()  : 对应 rc->vconn, rc->monitors 运行 vconn_run, 之后根据 rc->state 调用其之后的状态
rconn_send() : 将一个数据包加入 rc->txq 队列中
run_ACTIVE() : 从 rc->txq 中取出一条消息发送出去
rconn_recv() : 从 rc->vconn 收消息
rconn_add_monitor() : 给 rc->monitors 增加一个元素
rconn_is_alive() : rc->state 不是 VOID 和 DISCONNECTED
rconn_is_connected(): rc->state 是 IDLE 或 ACTIVE
rconn_is_admitted() : rc->state 首先是 is_connected, 并且 rc->last_admitted > rc->last_connected
rconn_failure_duration() : 如果控制器一直监管交换机　返回 0; 如果当前控制器已经不再接管交换机, 返回上次管理时间到现在的时间
rconn_get_version() : rc->vconn 的版本
elapsed_in_this_state() : 处于当前状态的时间多久了
rconn_reconnect() : 如果是rc->reliable = true, rc->state 进入 BACKOFF 状态
timeout_$STATE : 获取各个状态的超时时间


run_$STATE : 各个状态需要的动作

    rc->state = S_VOID : run_VOID()
    rc->state = S_BACKOFF : run_BACKOFF()
    rc->state = S_CONNECTING: run_CONNECTING()
    rc->state = S_ACTIVE : run_ACTIVE()
    rc->state = S_IDLE : run_IDLE()
    rc->state = S_DISCONNECTED: run_DISCONNECTED()

注:

可靠连接和不可靠连接的主要区别: 可靠连接状态切换 S_VOID -> S_CONNECTING 或 S_VOID -> S_BACKOFF,
而不可靠连接状态切换 S_VOID -> S_ACTIVE. 因此, 可靠连接会在进行连接时进行验证, 而不可靠连接直接认为连接是可用的.

一次成功的连接需要 vconn_open --> vconn_connect

enum state {
    S_VOID = 1 << 0
    S_BACKOFF = 1 << 1
    S_CONNECTING = 1 << 2
    S_ACTIVE = 1 << 3
    S_IDLE = 1 << 4
    S_DISCONNECTED = 1 << 5
}

rconn 是 reliable connect 的缩写

struct rconn * rconn_create(int probe_interval, int max_backoff, uint8_t dscp, uint32_t allowed_versions)

    probe_interval: 如果 probe_interval 没有收到对端的消息发送 echo request, 如果再过 probe_interval 没有收到对端消息, 重连. 最少 5 s
    max_backoff : 从 1 s 没有收到对端请求, 之后 2 s 发送请求, 之后 4 s 发送请求... 直到 max_backoff
    allowed_versions : 允许的版本. 传 0 表示默认版本(1.1,1.2,1.3)

    初始化 rconn 的各个数据成员;

    没有显示初始化:
        struct vconn *monitors[MAXIMUM_MONITORS]; 为 NULL?
        int last_error;

void rconn_set_max_backoff(struct rconn *rc, int max_backoff)

    rc->max_backoff = MAX(1, max_backoff);
    如果 max_backoff 小于 rc->backoff, 那么, 就设置 rc->backoff = max_backoff;
    if (rc->state == S_BACKOFF && rc->backoff > max_backoff) {
        rc->backoff = max_backoff;
        if (rc->backoff_deadline > time_now() + max_backoff) {
            rc->backoff_deadline = time_now() + max_backoff;
        }
    }

void rconn_connect(struct rconn *rc, const char *target, const char *name)

    1. 首先 rc->state 恢复到 S_VOID
    2. 设置 target, name
    3. 初始化 rc->reliable = true
    4. 与 rc->target 建立连接, 如果成功状态进入 CONNECTING, 失败进入 BACKOFF

void rconn_connect_unreliably(struct rconn *rc, struct vconn *vconn, const char *name)

    1. rc->state 恢复到 S_VOID
    2. 设置 target, name
    3. rc->reliable = false; rc->vconn = vconn; rc->last_connected = time_now();
    4. 状态直接转变为 S_ACTIVE

void rconn_reconnect(struct rconn *rc)

    TODO
    对于处于 ACTIVE 或 IDLE 状态的连接, 如果 reliable 为 ture, 进入 BACKOFF
    状态; 如果 reliable 为 false, 进入 DISCONNECTED

static void rconn_disconnect__(struct rconn *rc)

    从非 S_VOID 状态恢复为 S_VOID

    rc->vconn = NULL;
    rc->target = "void"
    rc->name = "void"
    rc->reliable = false;
    rc->backoff = 0;
    rc->backoff_deadline = TIME_MIN;
    rc->state = S_VOID
    rc->state_entered = time_now()

void rconn_disconnect(struct rconn *rc)

    加锁版 rconn_disconnect__(rc)

void rconn_destroy(struct rconn *rc)

    销毁 rc

static unsigned int timeout_VOID(const struct rconn *rc OVS_UNUSED)

    return UINT_MAX;

static void run_VOID(struct rconn *rc OVS_UNUSED)

    /* Nothing to do. */

static void reconnect(struct rconn *rc)

    与 rc->target 建立连接
    如果成功, rc->state 进入 CONNECTING
    如果失败, rc->state 进入 BACKOFF

    注: 并没有断开连接后重连, 如果是正常的返回时间很慢是否会得到期望的结果

static unsigned int timeout_BACKOFF(const struct rconn *rc)

    return rc->backoff;

static void run_BACKOFF(struct rconn *rc)

    如果已经超时, 重新连接, 否则什么也不做

static unsigned int timeout_CONNECTING(const struct rconn *rc)

    return MAX(1, rc->backoff);

static void run_CONNECTING(struct rconn *rc)

    判断与对端连接建立情况:
    1. 如果成功建立连接, 设置状态为 ACTIVE
    2. 如果连接失败或超时, 断开连接设置为 BACKOFF 或 DISCONNECTED

    注: 与对端建立连接不仅仅是 socket 的连接建立, 包括 send hello, recvhello.

static void do_tx_work(struct rconn *rc)

    如果 rc->txq 不为空, 从 rc->txq 链表中依次取出数据包, 发送出去,
    如果发生错误, 退出.
    如果没有错误, 直到 txq 数据发送完.
    如果 rc->txq 中的数据发送完了, 立即调用 poll_immediate_wake() 唤醒当前线程的 poll 接受数据包

static unsigned int timeout_ACTIVE(const struct rconn *rc)

    返回几秒后进行 probe 的探测.

static void run_ACTIVE(struct rconn *rc)

    如果链路正常, 从 rc->txq 中依次取出数据包发送
    如果链路超时, 转到 IDLE 状态, 将 echo_request 探测报文加入 rc->txq 等待发送.

static void run_IDLE(struct rconn *rc)

    如果链路超时, 对于可靠的连接进入 BACKOFF 状态, 对应不可靠连接, 直接断开
    如果链路正常, 从 rc->txq 中取出一个数据包发送

static void run_DISCONNECTED(struct rconn *rc OVS_UNUSED)

    /* Nothing to do. */

void rconn_run(struct rconn *rc)

    rc->vconn 与 rc->monitors 都完成与对端的连接建立;

    运行 rc->state 之后的函数
    rc->state = S_VOID : run_VOID() 什么也不做
    rc->state = S_BACKOFF : run_BACKOFF() : 如果超时, 重连
    rc->state = S_CONNECTING: run_CONNECTING() :　查看连接情况, 连接建立成功或失败
    rc->state = S_ACTIVE : run_ACTIVE() : 从 txq 取数据发送出去, 直到全部数据发送出去或出错
    rc->state = S_IDLE : run_IDLE() : 超时断开连接, 没有超时, 从 txq 取数据发送出去
    rc->state = S_DISCONNECTED: run_DISCONNECTED(): 什么也不做

    注: 正常是在 rconn_connect 之后调用该函数, 之后会自动调用 run_CONNECTING
    完成连接, run_ACTIVE() 发送数据包

    注:正常情况 vconn_run()　保证 rc-vconn 已经建立连接, 并且发送 HELLO 请求和接受到 HELLO 应答

void rconn_run_wait(struct rconn *rc)

    保证连接已经完成, 其他什么也不做

    1. vconn 中注册数据可发送的事件到 poll(monitors 中注册数据可发送和可接受的事件)
    2. 等待数据可发送或 probe 超时时间到达.

struct ofpbuf * rconn_recv(struct rconn *rc)

    如果 rc->state 是 S_ACTIVE 或 S_IDLE,  接受数据
    成功: 拷贝 buffer 到所有的 rc->monitors, rc->state 变为 ACTIVE
    否则: 根据是否是可靠地连接, 断开或重连

void rconn_recv_wait(struct rconn *rc)

     如果 rc->vconn 不为 NULL, vconn 中注册数据可读的事件到 poll

static int rconn_send__(struct rconn *rc, struct ofpbuf *b, struct rconn_packet_counter *counter)

    如果 rc 处于 IDLE, ACTIVE 状态, rc->monitors 的每一个成员调用 vconn_send(rc->monitors[i], b),
        b->list_node 加入 rc->txq 链表尾, 如果　rc->txq 中只有 b, 直接发送
    否则 直接释放 b 的内存

int rconn_send(struct rconn *rc, struct ofpbuf *b, struct rconn_packet_counter *counter)

    加锁版的 rconn_send__()

int rconn_send_with_limit(struct rconn *rc, struct ofpbuf *b, struct rconn_packet_counter *counter, int queue_limit)

    如果 counter->packets < queue_limit, 将 b 加入 rc->txq 等待发送
    否则删除 b

void rconn_add_monitor(struct rconn *rc, struct vconn *vconn)

    将 vconn 加入 rc->monitors. 如果超过限制, 拒绝.

    注: 1. vconn 已经建立连接. 2. 最多支持 8 个 monitor

static bool rconn_is_admitted__(const struct rconn *rconn)

    判断当前 rconn 是否一直被控制器管理, 即 rconn 和对端已经建立连接, 并且上次接受控制消息的时间在建立连接之后

int rconn_failure_duration(const struct rconn *rconn)

    TODO
    如果建立连接之后接受控制消息, 返回 0;
    如果返回现在的时间减上次管理时间

    duration = (rconn_is_admitted__(rconn)
                ? 0
                : time_now() - rconn->last_admitted);

unsigned int rconn_count_txqlen(const struct rconn *rc)

    rc->rxq 链表长度

struct rconn_packet_counter * rconn_packet_counter_create(void)

    创建一个 rconn_packet_counter

void rconn_packet_counter_destroy(struct rconn_packet_counter *c)

    销毁 rconn_packet_counter

static int try_send(struct rconn *rc)

    从 rc->txq 中取出一个消息 msg, 调用发送,
    如果发送成功, 从 rc->txq 中删除该消息, 更新 rconn_packet_counter;
    如果失败, 将该消息重新放入 rc->txq 中

static void report_error(struct rconn *rc, int error)

    日志错误原因

static void disconnect(struct rconn *rc, int error)

    释放 rc->vconn
    如果是稳定链路(rc->reliable=true), 转换 rc->state 到 S_BACKOFF
    否则转换 rc->state 状态到 S_DISCONNECTED

    if (rc->reliable) {
        rc->backoff_deadline = now + rc->backoff;
        state_transition(rc, S_BACKOFF);
    } else {
        rc->last_disconnected = time_now();
        state_transition(rc, S_DISCONNECTED);
    }

static void flush_queue(struct rconn *rc)

    丢掉 rc->txq 中的所有数据包, 调用立即唤醒当前线程 poll

static unsigned int elapsed_in_this_state(const struct rconn *rc)

    当前连接已经建立时间长度

static unsigned int timeout(const struct rconn *rc)

    rc->state = S_VOID : UINT_MAX
    rc->state = S_BACKOFF : rc->backoff
    rc->state = S_CONNECTING: max(1,rc->backoff)
    rc->state = S_ACTIVE : rc->probe_interval ? MAX(rc->last_activity, rc->state_entered) + rc->probe_interval - rc->state_entered : UINT_MAX;
    rc->state = S_IDLE : rc->probe_interval
    rc->state = S_DISCONNECTED: UINT_MAX

static bool timed_out(const struct rconn *rc)

    rc 处于 rc->state 的时间是否超时;

    比如在 S_IDLE 状态, 如果 time_now() >= rc->state_entred + rc->probe_interval, 我们就认为处于 IDLE 的超时了
    再 S_ACTIVE, 如果 time_now() > rc->last_activity - rc->state_entered + rc->probe_interval 我们就认为处于 ACTIVE 超时了.

    return time_now() >= sat_add(rc->state_entered, timeout(rc));

static void state_transition(struct rconn *rc, enum state state)

    rc->state = state
    rc->state_entered = time_now()
    如果 rc 之前处于 connected, 更新 rc->total_time_connected
    如果 rc 之前处于 connected, 待更新的状态 state 不是 connected. rc->probably_admitted = false
    rc->seqno : 如果由 connected 变为 unconected, 或 unconected 变为 connected, 加 1

static void close_monitor(struct rconn *rc, size_t idx, int retval)

    关闭 rx->monitors[idx]

static void copy_to_monitor(struct rconn *rc, const struct ofpbuf *b)

    克隆数据包 b, 发送给每个一个 rc->monitors

static void run_BACKOFF(struct rconn *rc)

    处于任何 rc->state 的状态下超时, 都进行重连

    if (timed_out(rc)) reconnect(rc);

static bool is_admitted_msg(const struct ofpbuf *b)

    b 是否是控制器已经接管交换机的消息. 根据 b 的类型是否是已经建立连接后的消息来判断当前控制器是否已经接管交换机.

static bool rconn_logging_connection_attempts__(const struct rconn *rc)

    return rc->backoff < rc->max_backoff;

static void rconn_set_target__(struct rconn *rc, const char *target, const char *name)

    重置 rc->target, rc->name, 如果 name = NULL, rc->name = rc->target
