
## pinsched

pinqueue 保存了 PACKET_IN 数据包, 每个 pinqueue 保存一个物理
端口进来的数据包

pinsched 在 pinqueue 的基础上增加了速率限制, 统计信息, 最重
要的是每个物理端口一个队列, 每个队列包含了该物理端口的所有 PACKET_IN

速率限制: 是指保存在 pinsched->queues 中所有物理端口的 PACKET_IN
的数据包数之和不能超过 token_bucket->burst 数量.
即所有端口中 PACKET_IN 的数量不能超过 token_bucket->burst

其中:

* pinsched_send 是将即将发送给控制器的包加入 pinsched->queues, 或直接加入 ofconn->rconn->txq
* pinsched_run 是从 pinsched->queues 取出一定数量的包发送给控制器
* pinsched_wait 是等待 pinsched 满足给控制器发送 PACKET_IN 的条件, 如果满足了立即返回, 如果不满足, 就设置当前线程 poll_loop 下一次唤醒时间后返回.

## 数据结构

struct pinqueue {
    struct hmap_node node;      //pinsched->queues 的元素
    ofp_port_t port_no;         //端口号
    struct ovs_list packets;    //元素是 ofpbuf
    int n;                      //packets 的元素个数
};

struct pinsched {
    struct token_bucket token_bucket;       //速率限制

    struct hmap queues;         //元素是 pinqueue, 每个物理端口一个 pinqueue
    unsigned int n_queued;      //queues 中每个元素 pinqueue 的 packets 个数之和.
    struct pinqueue *next_txq;  //下一个要加入 txq 的 pinqueue

    unsigned long long n_normal;        //没有配置速率限制时, 加入到 pinsched 的数据包个数
    unsigned long long n_limited;       //在配置速率限制后, 加入到 pinsched 的数据包的个数
    unsigned long long n_queue_dropped; //由于队列满了, 导致的丢包的个数
};

struct token_bucket {
    //配置信息
    unsigned int rate;          //每毫秒增加的令牌(tokens)数
    unsigned int burst;         //pinsched 的 n_queued 的最大值不能超过 burst

    //状态信息
    unsigned int tokens;        //目前的令牌(tokens)数量
    long long int last_fill;    //上一次增加令牌的时间戳
};


## 核心实现

static void advance_txq(struct pinsched *ps)

    将 ps->next_txq 轮询指向不同的 ps->queues 中的不同 pinqueue

    1. 如果 ps->next_txq 不为空, 返回 ps->next_txq 指向的 pinqueue
    2. 如果 ps->next_txq 为空, 从 ps->queues 找到下一个不为空的 pinqueue, 更新 ps->next_txq, 如 ps->queues 所有都为空, 返回 NULL

static struct ofpbuf * dequeue_packet(struct pinsched *ps, struct pinqueue *q)

    删除 q->packets 第一个数据. 返回被删除的数据包

static void adjust_limits(int *rate_limit, int *burst_limit)

    if ( *rate_limit <= 0)
        *rate_limit = 1000;
    if ( *burst_limit <= 0)
        *burst_limit = *rate_limit / 4;
    if ( *burst_limit < 1)
        *burst_limit = 1;

static void pinqueue_destroy(struct pinsched *ps, struct pinqueue *q)

    销毁 ps->queues 中的元素 q

static struct pinqueue * pinqueue_get(struct pinsched *ps, ofp_port_t port_no)

    从 ps 中获取端口 port_no 对应的 pinqueue, 如果不存在就创建一个

static void drop_packet(struct pinsched *ps)

    找到 ps->queues 中最长的队列(如果有多个一样长的,随机选择一个)删除该队列的一个包
    注: 如果多个队列长度一样, 随机选择的算法采用算法(Knuth algorithm 3.4.2R)

static struct ofpbuf * get_tx_packet(struct pinsched *ps)

    从 ps->next_txq 中取出一个数据包. 返回该数据包.
    该函数保证每次调用从不同的 pinqueue 队列取包, 保证各个端口取包的公平性.

static bool get_token(struct pinsched *ps)

    从 ps->token_bucket 取 1000 个令牌, 成功返回 true, 失败返回 false.
    (参考 token_bucket_withdraw)

void pinsched_send(struct pinsched *ps, ofp_port_t port_no, struct ofpbuf *packet, struct ovs_list *txq)

    如果没有配置速率限制, 将 packet 直接加入 ofconn->rconn->txq
    如果配置速率限制, 将 packet 加入 ps->queues 中 port_no 对应的 pinqueue

void pinsched_run(struct pinsched *ps, struct ovs_list *txq)

    如果 ps 不为空, 从 ps->queues 的各个队列轮询取最多 50 个包, 加入 txq.
    注: 之所以最多是因为 1. ps->queues 可能总共没有 50 个包; 2. 已经达到速率限制, 不允许继续给 txq 增加包

void pinsched_wait(struct pinsched *ps)

    如果速率没有达到临界值(即 pinsched 的所有 packet 少于 burst), 立即返回;
    否则, 计算需要等待的时间, 设置当前线程的 poll_loop 唤醒时间为需要等待的时间

struct pinsched * pinsched_create(int rate_limit, int burst_limit)

    创建并初始化一个 pinsched

void pinsched_destroy(struct pinsched *ps)

    销毁 pinsched

void pinsched_get_limits(const struct pinsched *ps, int *rate_limit, int *burst_limit)

    获取 ps 对应的 rate 与 burst 分别保存在 rate_limit 与 burst_limit

void pinsched_set_limits(struct pinsched *ps, int rate_limit, int burst_limit)

    设置 ps 的 rate 与 burse 分别为 rate_limit, burst_limit

void pinsched_get_stats(const struct pinsched *ps, struct pinsched_stats *stats)

    获取 ps 的统计信息保存在 stats 中

### token_bucket



bool token_bucket_withdraw(struct token_bucket *tb, unsigned int n)

    从 tb->tokens 取 n 个令牌(tb->tokens - n):
    如果 tb->tokens 大于 n, 返回 true, 表面取令牌成功.
    如果 tb->tokens 小于 n, 重新计算 tb->tokens 的令牌数, 此时 tb->tokens 大于 n, 返回 true(取令牌成功). tb->tokens 小于 n, 返回 false(取令牌失败)
