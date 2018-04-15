

struct in_band {
    struct ofproto *ofproto;
    int queue_id;               /* default -1 */

    /* Remote information. */
    time_t next_remote_refresh;     //下次唤醒时间, 单位 second
    struct in_band_remote *remotes;
    size_t n_remotes;

    time_t next_local_refresh;      //下次唤醒时间, 单位 second
    uint8_t local_mac[ETH_ADDR_LEN]; /* Current MAC. */
    struct netdev *local_netdev;     /* Local port's network device. */

    /* Flow tracking. */
    struct hmap rules;          /* Contains "struct in_band_rule"s. */
};



## 核心实现

bool in_band_run(struct in_band *ib)

    TODO

void in_band_wait(struct in_band *in_band)

    设置当前线程 poll_loop 的唤醒时间为 MIN(in_band->next_remote_refresh, in_band->next_local_refresh)

int in_band_create(struct ofproto *ofproto, const char *local_name, struct in_band **in_bandp)

    初始化 in_band 各个数据成员. 其中 local_name 为 internal 类型的网卡名

    注
    1. local_netdev 的类型是 internal
    2. 借助 in_band_set_remotes 初始化 remotes, n_remotes


void in_band_destroy(struct in_band *ib)

    销毁 ib

static bool any_addresses_changed(struct in_band *ib, const struct sockaddr_in *addresses, size_t n)

    如果 ib->remotes 与 addresses 完全一样, 返回 true
    如果 ib->remotes 与 addresses 存在不一样, 返回 false

void in_band_set_remotes(struct in_band *ib, const struct sockaddr_in *addresses, size_t n)

    清除旧的 remotes, 用 addresses 初始化 in_band 的 remotes
    设置下一次刷新时间为当前

void in_band_set_queue(struct in_band *ib, int queue_id)

    ib->queue_id = queue_id;

