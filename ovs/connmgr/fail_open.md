
## 数据结构

struct fail_open {
    struct ofproto *ofproto;
    struct connmgr *connmgr;
    int last_disconn_secs;          //fo->connmgr 中 ofconn 断开最短时间; 该值为不为 0 时, 表明在 fail_open 模式
    long long int next_bogus_packet_in; //下一个发送虚拟 PACKET_IN 的时间点
    struct rconn_packet_counter *bogus_packet_counter;
    bool fail_open_active;
};

### fail_open 模式

0. 只有与控制器建立连接的过程中才可能存在 fail_open 模式
1. 如果与任一控制器有连接, 会以 2 秒间隔发送虚假 PACKET_IN 消息
2. 如果没有与任一控制器连接, 不发送 PACKET_IN 消息.
4. 如果 fail_open 模式期间任一控制器, 被任一控制器控制, 就退出 fail_open 模式

## 核心实现

static int trigger_duration(const struct fail_open *fo)

    激活 fail_open 的时间间隔,
    如果与没有与任一控制连接, 永远不激活
    如果与任一控制连接, 为 fo->connmgr->controller 中所有 ofconn->rconn 的最多 probe_interval 三倍

bool fail_open_is_active(const struct fail_open *fo)

    当前处于 fail_open 模式, 返回 true
    当前没有处于 fail_open 模式, 返回 false

static void send_bogus_packet_ins(struct fail_open *fo)

    构造虚拟 PACKET_IN 消息, 加入与控制器的所有连接的发送队列, 等待发送

void fail_open_run(struct fail_open *fo)

    如果 fo 所属 br 与所有控制器断开连接的时间超过了 probe_interval 的 3 倍,
        1. 还没有处于 fail_open 模式, 进入 fail_open 模式, 删除所有流表
        2. 处于 fail_open 模式, 与任一控制器连接:
            设置 last_disconn_secs.
            达到发送 PACKET_IN 的时间点, 发送虚假 PACKET_IN, 设置下一次发送 PACKET_IN 时间为 2 sec 后
        3. 处于 fail_open 模式, 没有与任一控制器连接, 停止发送虚假 PACKET_IN

void fail_open_maybe_recover(struct fail_open *fo)

    如果当前处于 fail_open 模式, 但是被控制器管理, 那么, 就退出 fail_open 模式.

static void fail_open_recover(struct fail_open *fo)

    退出 fail_open 模式

void fail_open_wait(struct fail_open *fo)

    如果 fo 下一次发送 PACKET_IN 的时间不为 LLONG_MAX, 设置当前线程的 poll_loop 唤醒时间为 fo->next_bogus_packet_in.

    if (fo->next_bogus_packet_in != LLONG_MAX)
        poll_timer_wait_until(fo->next_bogus_packet_in);

void fail_open_flushed(struct fail_open *fo)

    如果 fo 所属 br 与控制器断开连接的时间超过了 probe_interval 的 3 倍, 进入 fail_open 模式, 创建 action 为 normal 的流表, 设置 fail_open_active 为 false;
    否则仅设置 fail_open_active 为 false

int fail_open_count_rules(const struct fail_open *fo)

    return fo->fail_open_active != 0;

struct fail_open * fail_open_create(struct ofproto *ofproto, struct connmgr *mgr)

    创建并初始化 fail_open 对象

void fail_open_destroy(struct fail_open *fo)

    销毁 fail_open
