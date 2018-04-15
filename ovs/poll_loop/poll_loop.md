
## poll-loop

```c

#define poll_fd_wait(fd, events) poll_fd_wait_at(fd, 0, events, SOURCE_LOCATOR)
#define poll_timer_wait(msec) poll_timer_wait_at(msec, SOURCE_LOCATOR)
#define poll_timer_wait_until(msec) poll_timer_wait_until_at(msec, SOURCE_LOCATOR)
#define poll_immediate_wake() poll_immediate_wake_at(SOURCE_LOCATOR)

struct poll_node {

    struct hmap_node hmap_node;
    struct pollfd pollfd;       /* Events to pass to time_poll(). */
    HANDLE wevent;              /* Events for WaitForMultipleObjects(). */
    const char *where;          /* Where poll_node was created. */

};

struct poll_loop {

    /* All active poll waiters. */
    struct hmap poll_nodes;
    
    /* Time at which to wake up the next call to poll_block(), LLONG_MIN to
     * wake up immediately, or LLONG_MAX to wait forever. */
    long long int timeout_when; /* In msecs as returned by time_msec(). */
    const char *timeout_where;  /* Where 'timeout_when' was set. */

};
```

1. 每个线程一个 poll_loop

2. 一个 poll_loop 包含多个 poll_node, 每个 poll_node 只属于一个 poll_loop

3. 每个 poll_node 与一个 pollfd 相关联

4. 每个 pollfd 由 fd 和 event 组成

5.  所有 seq 和 signal_fd 被所有线程的 poll_loop 的监听, 即对于任意 seq, 只要调用过 seq_wait 的线程, 就会监听该 seq 对应的管道的可读事件

      ​
所有调用 poll_fd_wait 的函数

1. fd_wait
2. pfd_wait
3. fatal_signal_wait
4. latch_wait_at
5. process_wait
6. nl_sock_wait
7. dpif_linux_recv_wait
8. netdev_linux_rxq_wait



    
                        	-> poll_node -> pollfd -> (fd, event)
                         	-> poll_node -> pollfd -> (fd, event)
    thread-1    poll_loop  	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)
    
                        	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)
    thread-2    poll_loop  	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)
    
                        	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)
    thread-3    poll_loop  	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)
                        	-> poll_node -> pollfd -> (fd, event)

总之

* 通过 poll_loop 创建当前线程的 poll_loop

* 通过 poll_timer_wait_xxx 设置当前线程的 poll_loop 的下次唤醒时间

* 通过 free_poll_loop 释放 poll_loop;

* 通过 free_poll_nodes 释放 poll_loop 的 所有 poll_node;

* 通过 find_poll_node 从 poll_loop 根据 fd 中查找对应的 poll_node

* 通过 poll_fd_wait_at 由 fd 找到 poll_node(如果不存在就创建), 设置 fd 关注的事件为 event

  ​

static struct poll_node * find_poll_node(struct poll_loop *loop, int fd, HANDLE wevent)

    从 poll_loop->poll_nodes 每个元素 node 中 找到 node->pollfd.fd = fd && node->wevent = wevent 的 node.返回之;


static struct poll_loop * poll_loop(void)

    定义线程局部变量 key, 保证只初始化一次. 每个线程的 key 与一个 poll_loop
    相关联, 如果当前线程的 poll_loop 不存在, 就创建之. 存在就返回 key 对应的
    poll_loop



static void free_poll_loop(void *loop_)

    释放 loop_ 变量


static void poll_create_node(int fd, HANDLE wevent, short int events, const char *where)

    将 fd 的 events 加入当前线程的 poll_loop, (如果 poll_loop 不存在就创建)
    注: fd 用于 linux, wevent 用于 windows, 两者不能通知设置. fd=0&&wevent!=0 或 fd!=0&&wevent=0


void poll_fd_wait_at(int fd, short int events, const char *where)

    当前线程的 poll_loop 中, 设置 fd 对应 poll_node 关注 events　（如果 poll_node 不存在，创建并加入当前线程的 poll_loop； 如果 poll_loop 不存在就创建)


void poll_timer_wait_at(long long int msec, const char *where)

    设置当前线程 poll_loop 的超时时间为 msec(如果 msec 小于 poll_loop->timeout_when, 最多为 LLONG_MAX 最小 LLONG_MIN)


void poll_timer_wait_until_at(long long int when, const char *where)

    设置当前线程 poll_loop 的超时时间为 when(如果 when 小于 poll_loop->timeout_when)


void poll_immediate_wake_at(const char *where)

    设置当前线程 poll_loop 的超时时间为 0, 即该线程 poll 会被立即唤醒


static void log_wakeup(const char *where, const struct pollfd *pollfd, int timeout)

    记录 pollfd 唤醒事件. 如果 cpu 大于 50 为 INFO, 否则为 DEBUG


static void free_poll_nodes(struct poll_loop *loop)

    从 loop->poll_nodes 删除每一个节点


void poll_block(void)

    1. 信号的管道的可读事件的 fd　加入当前线程的 poll_node 中．（如何需要会注册信号 SIGTERM, SIGINT, SIGHUP, SIGALRM 的处理函数（给管道发送空字符，并设置stored_sig_nr）,　详细参考信号机制部分）
    2. 将 timewarp_seq 的改变事件加入当前线程的 poll_node
    3. 将当前线程的 poll_loop 的 poll_nodes 转换为 pollfds 数组
    4. 计算 poll 的超时时间
    5. 如果当前线程没有处于 quiescent, 使其处于 quiescent
    6. 调用 poll 监听 pollfds 中的事件，或 poll 等待超时
    7. 结束当前线程的 quiescent
    8. 检查是否由超时发生，如果发生超时, 发送信号 SIGALRM
    9. 释放 poll_loop 的所有 poll_node, 
    10. 如果有信号需要处理，处理信号
    11. 读取当前线程 seq_thread_key 对于的 seq_thread 中所有 seq_waiter, 从所属的 seq->waiters 和 seq_thread->waiters 中删除
       这时当前线程没有任何 seq_waiter, 因此, 设置 seq_thread->waiting 为 false. 并清空管道中的消息.



导火索

1. 执行命令( ovs-vsctl, ovs-ofctl) 设置超时或用户发送 kill -n SIGNUM
2. 用户调用 ovs-appctl time/wrap MSEC
3.  调用 poll_fd_wait_at 之后的 fd 有事件要处理



以 timewarp_seq 为例

1. 线程 B, C 调用 poll_block
2. 线程 A 调用 time/warp TOTAL_MSEC(10000) MSEC(1000)

1)刚开始线程 B, C, 各增加一个 seq_waiter, 分别加入当前线程的 seq_thread->waiters 也加入 seq->waiters
并且监听管道一端的 POLLIN 事件, (当 timewarp_seq 的值发生变化时, 会通过管道的另一端发送 "", 这样监听
端就会收到 POLLIN 事件), 该事件构造 poll_node 加入各自线程的 poll_loop, B, C 线程一直阻塞, 直到收到 POLLIN

2)之后线程 A 调用 time/warp TOTAL_MSEC(10000), MSEC(1000). 线程 A 将 monotonic_clock->warp 每次增加
MSEC(1000), TOTAL_MSEC(10000) 减少 MSEC. 之后设置 timewarp_seq->value = seq_next.
给线程 B, C 发送""消息之后, 将 waiter 从 seq 和 seq_thread 中删除, 并释放
waiter.  最后休息 10s

3)在线程 A  发生 "" 之后, 线程 B, C 收到 POLLIN 事件, 两个线程各自从阻塞中返回. 从当前 poll_loop
中删除所有 poll_node 节点. 将当前线程的所有 waiters 从所属的 seq_thread 和 seq
中删除. 读完管道所有消息. thread->waiting 设置为 false

之后重新循环1),2),3). 直到 TOTAL_MSEC 和 MSEC 都减为 0

-----------------------------------------------------------



## 信号机制

```c
#define MAX_HOOKS 32

static struct hook hooks[MAX_HOOKS];　//收到信号后的回调函数个数

static size_t n_hooks;　//收到信号后的回调函数个数

static const int fatal_signals[] = { SIGTERM, SIGINT, SIGHUP, SIGALRM };　//需要处理的信号

static int signal_fds[2]; //发送信号的管道

static volatile sig_atomic_t stored_sig_nr = SIG_ATOMIC_MAX;　//多线程共享该变量

```



1.  创建一个管道
2.  当收到信号（SIGTERM, SIGINT, SIGHUP, SIGALRM）时,  给管道一端发送 ""
3.  管道另一端的调用 poll_block 的线程就会返回，收到有信号要处理，任何调用了 fatal_signal_run 的进程就会调用所有 hook （通过 fatal_signal_add_hook 增加）并退出．（任何从阻塞状态退出的函数都应该调用该函数，检查是否收到信号，如果收到就退出）



多个线程都会调用 poll_block, 该函数开始就会注册管道一段的读事件，之后，监听每个 fd 关注的事件，如果

某个线程的 poll 返回，发现 deadline < time_msec(),  那么就给管道发送消息，设置 stored_sig_nr 为 SIGALRM, 此时其他阻塞于 poll 的线程由于管道有可读事件而退出，继续运行 fatal_signal_run,  由于 stored_sig_nr 此时不为 SIG_ATOMIC_MAX, 因此, 调用所有 hook 函数, 并重新设置 SIGALRM 的处理函数为

默认处理函数，重新触发　SIGALRM　信号，  此时信号的处理函数就是进程退出．

目前修改 deadline 的地方就是执行 ovs-vsctl, ovs-appctl 等命令时设置了超时时间



void fatal_signal_init(void)

    1. 初始化管道, 管道的两端为 fatal_signals 的两个元素. 
    2. 保持 fatal_signals 中每个信号的状态, 并且重新设置每个信号的 handler 为  fatal_signal_handler
    3. 在当前进程退出是调用 atexit_handler



void fatal_signal_add_hook(void (*hook_cb)(void *aux), void (*cancel_cb)(void *aux), void *aux, bool run_at_exit)

    注册一个 hook 加入 hooks


void fatal_signal_handler(int sig_nr)

    fatal_signals 中信号的处理函数(在 fatal_signal_init 中注册),
    即将空字符串写入 signal_fds[1], 并保存当前信号到 stored_sig_nr



void fatal_signal_run(void)

    １．一旦收到 fatal_signals 里面的任一信号, 就调用对应的 hooks 中所有元素注册的 hook 函数, 
    ２．重新设置信号为默认处理函数，并重新发送信号（杀死进程）


void fatal_signal_wait(void)

    为 signal_fds[0] 注册一个 POLLIN 事件（ 一旦收到用户信号，触发信号, 当前线程的 poll_block 就会返回）


void fatal_ignore_sigpipe(void)

    忽略 pipe 信号


void fatal_signal_atexit_handler(void)

    调用 hooks 中只响应一次信号(run_at_exit != 0)的 hook


static void call_hooks(int sig_nr)

    遍历 hooks 所有 hook, 调用对于的 hook 函数


```c
static struct sset files = SSET_INITIALIZER(&files);

/* Has a hook function been registered with fatal_signal_add_hook() (and not

- cleared by fatal_signal_fork())? */
  static bool added_hook;

static void unlink_files(void *aux);

static void cancel_files(void *aux);

static void do_unlink_files(void);

```



void fatal_signal_add_file_to_unlink(const char *file)

    1. 给 hooks 增加一个元素. hook_cb 为 unlink_files, cancel_cb 为 cancel_files
    2. 将 file 加入 files



void fatal_signal_remove_file_to_unlink(const char *file)

    把 file 从 files 中删除


int fatal_signal_unlink_file_now(const char *file)

    将 file 对应的文件删除, 并将 file 从 files 中删除


static void unlink_files(void *aux)

    删除 files 中的所有文件


static void cancel_files(void *aux)

    清空 files 元素, 并重新设置 add_hook 为 false


static void do_unlink_files(void)

    删除 files 中的所有文件


void fatal_signal_fork(void)

    遍历 hooks 调用每个 hook 对应的 cancel_cb.


void fatal_signal_block(sigset_t *prev_mask)

    将 fatal_signals 所有信号屏蔽, 将之前屏蔽的信号加入 prev_mask


-----------------------------------------------------------

##  timewrap 机制

```c
/* Structure set by unixctl time/warp command. */

struct large_warp {
    struct unixctl_conn *conn; /* Connection waiting for warp response. */
    long long int total_warp; /* Total offset to be added to monotonic time. */
    long long int warp;      /* 'total_warp' offset done in steps of 'warp'. */
    unsigned int main_thread_id; /* Identification for the main thread. */
};

struct clock {
    clockid_t id;               /* CLOCK_MONOTONIC or CLOCK_REALTIME. */

    /* Features for use by unit tests.  Protected by 'mutex'. */
    struct ovs_mutex mutex;
    atomic_bool slow_path;             /* True if warped or stopped. */
    struct timespec warp OVS_GUARDED;  /* Offset added for unit tests. */
    bool stopped OVS_GUARDED;          /* Disable real-time updates if true. */
    struct timespec cache OVS_GUARDED; /* Last time read from kernel. */
    struct large_warp large_warp OVS_GUARDED; /* Connection information waiting
                                                 for warp response. */
};

/* Our clocks. */

static struct clock monotonic_clock; // 单调递增的时间，优先设置为 CLOCK_MONOTONIC
static struct clock wall_clock;      // 当时系统时间，CLOCK_REALTIME.
static long long int boot_time;      //　系统启动时间
static long long int deadline = LLONG_MAX; //超时时间
DEFINE_STATIC_PER_THREAD_DATA(uint64_t, last_seq, 0); //每线程对象, last_seq_key 对应的初始值为０
DEFINE_STATIC_PER_THREAD_DATA(long long int, last_wakeup, 0) //每线程对象, last_wakeup_key 对应的初始值为 0
static bool timewarp_enabled; //是否支持 time/wrap 命令
```



1. 定义了两个时钟　monotonic_clock(单调递增，不会被系统管理员修改时间影响)　wall_clock(系统时间，会被系统管理员修改时间影响)



static void init_clock(struct clock *c, clockid_t id)

    初始化 clock 对象 c


static void do_init_time(void)

    初始化 monotonic_clock, wall_clock, boot_time


static void time_init(void)

    确保 do_init_time 只调用一次


static void time_timespec__(struct clock *c, struct timespec *ts)

    １．如果 c->slow_path 为 false, 将当前时间保持在 ts
    ２．如果 c->slow_path 为 true 并且 c->stopped 为 false, 将 c->warp, c->cache 时间加起来, 保存在 ts
    ３．如果 c->slow_path 为 true 并且 c->stopped 为 ture, 将 c->warp, 与当前时间 加起来, 保存在 ts



void time_timespec(struct timespec *ts)

    time_timespec__(&monotonic_clock, ts)



void time_wall_timespec(struct timespec *ts)

    time_timespec__(&wall_clock, ts)



static time_t time_sec__(struct clock *c)

    time_timespec__(c, ts) 的秒部分（忽略纳秒部分）



time_t time_now(void)

    返回 monotonic_clock 时间, 单位 second　（即time_sec__(&monotonic_clock)）


time_t time_wall(void)

    返回 wall_clock 时间, 单位 second　（time_sec__(&wall_clock)）


static long long int time_msec__(struct clock *c)

    time_timespec__(c, ts) 转为 ms



long long int time_msec(void)

    返回 monotonic_clock 时间, 单位 millsecond(即　time_msec__(&monotonic_clock))


long long int time_wall_msec(void)

    返回 wall_clock 时间, 单位 millsecond(即 time_msec__(&wall_clock))


void time_alarm(unsigned int secs)

    设置 deadline 为  time_msec() + secs*1000 . 最多 LLONG_MAX
    
    注：在很多命令(ovs-appctl, ovs-dpctl, ovs_vsctl)中实现超时机制通过 -T 或 --timeout


int time_poll(struct pollfd *pollfds, int n_pollfds, HANDLE *handles OVS_UNUSED, long long int timeout_when, int *elapsed)

    1. time_msec() - timeout_when = time_left
    2. 如果不处于 quiescent, 使当前线程处于 quiescent
    3. 调用 poll 等待 pollfds 中有相应事件触发，或超时(过了 time_left)
    4. 如果不处于 quiescent 并且 time_left 不为 0, 结束 quiescent
    5. 如果 deadline < time_msec() 给管道另一端发送信号(阻塞在该管道另一端的 time＿poll 由于有可读事件，而退出， 继续运行 fatal_signal_run(), ), 退出函数
    6. 记录当次 time_poll 执行时间保存在 elapsed
    
    TODO



long long int timespec_to_msec(const struct timespec *ts)

    ts 转换为 ms


long long int timeval_to_msec(const struct timeval *tv)

    tv 转换为 ms


long long int time_boot_msec(void)

    返回 boot_time


void xgettimeofday(struct timeval *tv)

    返回当前时间保存在 tv


void xclock_gettime(clock_t id, struct timespec *ts)

    返回当前时间保存在 ts


static void msec_to_timespec(long long int ms, struct timespec *ts)

    ms 转换为 ts


static void timewarp_work(void)


    先将 monotonic_clock->large_warp.total_warp 以 monotonic_clock->large_warp.warp 为单位, 依次增加到 monotonic_clock->warp
    如果 monotonic_clock->large_warp.total_warp 为 0, 之后将 monotonic_clock->large_warp.warp 增加到 monotonic_clock->warp
    最后返回



void timewarp_run(void)

    如果当前线程没有调用 time/warp 命令(调用了 poll_block), 当前线程监听 timewarp_seq 的改变
    如果当前线程调用 time/warp 命令, 将 monotonic_clock->large_warp 时间叠加到 monotonic_clock->warp, 并给所有监听 timewarp_seq 的线程发送 timewarp_seq 变化的消息
    
    监听 timewarp_seq 的线程收到 POLLIN 消息, poll 返回或者再次执行到 timewarp_run 时, 发现 seq 被改变, 于是设置当前线程的 poll_loop 超时为 0.



static long long int timeval_diff_msec(const struct timeval *a, const struct timeval *b)

    a 和 b 的时间差


static void timespec_add(struct timespec *sum, const struct timespec *a, const struct timespec *b)

    将 a 和 b 的时间加起来保存在 sum


static bool is_warped(const struct clock *c)

    monotonic_clock.warp 是否为 0


static void timeval_stop_cb(struct unixctl_conn *conn, int argc OVS_UNUSED, const char *argv[] OVS_UNUSED, void *aux OVS_UNUSED)

    停止 monotonic_clock 的时间, 重新初始化, 对应 time/stop 命令


static void timeval_warp_cb(struct unixctl_conn *conn, int argc OVS_UNUSED, const char *argv[], void *aux OVS_UNUSED)

    time/wrap MSECS  : 将 monotonic_clock.warp 增加 MSECS, 给各个 waiters 发送 timewarp_seq 变化的通知
    time/wrap LARGE_MSECS MSECS : 将 monotonic_clock.warp 以单位 MSECS 增加 LARGE_MSECS+MSECS, 每次增加都给各个 waiters 发送 timewarp_seq 变化的通知

size_t strftime_msec(char *s, size_t max, const char *format, const struct tm_msec *tm)

struct tm_msec * localtime_msec(long long int now, struct tm_msec *result)

    用 localtime_r 获取时间, 返回 result


struct tm_msec * gmtime_msec(long long int now, struct tm_msec *result)

    用 gmtime_r 获取时间, 返回 result


static bool is_warped(const struct clock *c)

​    return monotonic_clock.warp.tv_sec || monotonic_clock.warp.tv_nsec



static void log_poll_interval(long long int last_wakeup)

  　　如果 time_msec() - last_wakeup ＞ 1000, 记录日志，表示该时间不合理



void timeval_dummy_register(void) 

​         将 time/stop, time/wrap 注册到 ovs-appctl 命令



static void　timeval_stop_cb(struct unixctl_conn *conn, ...)

​	ovs-appctl time/stop　monotonic_clock.slow_path 设置为 true, monotonic_clock.stopped = true, 更新 monotonic_clock.cache 为当前时间



static void timeval_warp_cb(struct unixctl_conn *conn,

        ovs-appctl time/wrap 1024 :  将 monotonic_clock.wrap 增加 1000 ms, monotonic_clock.slow_path 设置为 true        



## Seq

### seq 的工作原理

所有 seq 的 value 通过全局变量 seq_next 控制, 保证各个 seq 的 value 不会重复

每个线程一个 poll_loop, 与线程局部变量 key 关联;

一个 seq 包含多个 seq_waiter, 每个 seq_waiter 属于不同的线程.

每个线程创建一个管道(latch)为当前线程的所有 seq_waiter 共享,

某个线程调用 **seq_wait** 的时候(如果 seq 中不存在当前线程对应的 seq_waiter, 就会创建一个).
当前线程的 seq_waiter 监听(poll) 管道的 POLLIN 事件(seq 与 seq->waiters 中的元素通过管道来通信);

当调用 **seq_change** 的时候, seq 就会给 seq->waiters 的每一个元素所属线程的管道一端发送消息,
由于各个 waiter 所属线程的管道另一端就会阻塞并监听到 POLLIN 事件, 当收到 POLLIN
事件之后, 各个线程的 poll 就会退出, 此外, 调用 seq_change 的线程, 会将 seq
之前关联的 seq_waiter 从 seq_thread->waiters 和 seq->waiters 中删除. 因此,
seq_waiter 是与其所属 seq 的某个值关联的, 一旦该值发生变化, 与该值关联的 seq_waiter
都会被删除, 新的值需要各个线程调用 seq_wait 重新关联.

各个线程通过比较 waiter->value 与 seq->value 就可以知道自己所属 seq->value 被改变了. 
当前线程就好继续运行, 从而实现线程之间状态的同步.

各个线程都可用直接访问 seq. 每个线程都可以对 seq 进行读(seq_read)和写(seq_change)
每次触发一次消息, seq_waiter 就会从所属的 seq_thread 和 seq 中删除.
但 seq_thread 和 seq 不会删除, 除非显示地调用 seq_thread_exit 来
删除当前线程的 seq_thread, 和调用 seq_destroy 删除 seq.

### seq, seq_thread, seq_waiter 的关系

1. 每个 seq 为所有线程共享, 每个线程最多只会创建一个 seq_waiter 与 seq 关联, 遍历
  seq->waiters 就是遍历各个线程与该 seq 关联的 seq_waiter

2. 从 seq_waiter 可以知道其所属 seq_thread 和 seq

3. seq_thread 是每个线程一个, 与线程局部变量 seq_thread_key 关联;

每个 seq_thread 可以包含多个 seq_waiter(通过 seq_wait), 每个 seq_waiter 属于不同的 seq,
遍历 seq_thread->waiters 就是遍历各个 seq 的 seq_waiter;

每个 seq_thread 有一个 latch, 当前线程所有的 seq_waiter 都共享同一 latch. 当 seq_thread
所属线程有 seq_waiter 时(通过 seq_wait 创建), 就会监听 latch 的 POLLIN 事件, 并且
seq_thread->waiting 为 true

上面的 latch 就是一个管道, 每个线程的所有 seq_waiter 都监听该管道可读的一端,
任何线程都可以通过管道另外一端发送消息, 这样接收一端就可以收到可读事件.

3. 通过遍历 seq_thread->waiters 中的每个 seq_waiter 可以知道当前 seq_waiter 属于那个 seq

总之

对于 seq, 通过 seq_create 创建一个 seq; 通过 seq_destory 删除某个 seq;
通过 seq_wait 在调用该方法的线程创建 seq_waiter, 并注册 seq 的值发生变化事件到当前的 poll_loop;
通过 seq_change 通知各个线程某个 seq 的值发生变化, 各个线程就退出阻塞, 继续执行;
通过 seq_woke 在调用该方法的线程删除所有 seq_waiter;
通过 seq_wake_waiters 唤醒阻塞在 seq_wait 的线程, 并删除属于该 seq 的所有 seq_waiter

对于 seq_thread, 通过 seq_thread_get 创建 seq_thread; 通过 seq_thread_exit 删除
seq_thread; 通过 seq_thread_woke 删除 seq_thread(某个线程) 的所有 seq_waiter

对 seq 的理解还需要结合 latch 和 poll_loop

### seq 的用法实例

线程 A

    seq_create(timewarp_seq) //创建一个 seq 对象

线程 B

    *last_seq = seq_read(timewarp_seq);
    while(last_seq == seq_read(timewarp_seq)) {
        seq_wait(timewarp_seq, *last_seq); //创建当前线程的 seq_waiter, 关注 timewarp_seq 的当前值
        poll_block();
    }
    
    第一次调用会创建每线程对象 seq_waiter, seq_thread.
    seq_thread 所属线程的将管道的一端读事件加入当前
    线程的 poll-loop. 对管道的写操作(seq_change(timewarp_seq)),
    会被 poll-loop 接受到

线程 C

    *last_seq = seq_read(timewarp_seq);
    while(last_seq == seq_read(timewarp_seq)) {
        seq_wait(timewarp_seq, *last_seq); //创建当前线程的 seq_waiter, 关注 timewarp_seq 的当前值
        poll_block();
    }


线程 B, 线程 C 会持续监听 timewarp_seq 的值, 在线程 B, C 执行 last_seq 之后, 任意线程调用
seq_change(timewarp_seq), 线程 B, C 的 poll-loop 都会收到 POLLIN 事件, 此时, 发现
last_seq != seq_read(timewarp_seq) 线程 B, C 可以继续执行后续代码. 这样就实现了一个 barrier 的功能

需要注意是, while 循环之后, 如果各个线程还需要关注 timewarp_seq 的变化, 就需要在
该线程重新调用如下代码, 如下代码只能实现一次 barrier 的同步

    *last_seq = seq_read(timewarp_seq);
    while(last_seq == seq_read(timewarp_seq)) {
        seq_wait(timewarp_seq, *last_seq); //创建当前线程的 seq_waiter, 关注 timewarp_seq 的当前值
        poll_block();
    }


/* A sequence number object. */
struct seq {
    uint64_t value;             //seq 当前值, 每次被修改就会通知所有 waiters POLLIN 事件
    struct hmap waiters;        //当前 seq 关联的所有 seq_waiter
};

/* A thread waiting on a particular seq. */
struct seq_waiter {
    struct seq *seq;            //所属的 seq
    struct hmap_node hmap_node; //seq->waiters 的元素
    unsigned int ovsthread_id;  //所属线程 id, seq->waiters 基于该值哈希
    
    struct seq_thread *thread;  //所属线程的 seq_thread
    struct ovs_list list_node;  //seq_thread->waiters 的元素
    
    uint64_t value;             //当前 waiter 的 value
};

/* A thread that might be waiting on one or more seqs. */
struct seq_thread {
    struct ovs_list waiters;    //该 seq_thread 所属线程的所有 seq_waiter
    struct latch latch;         //与 seq 通信的管道
    bool waiting;               //当该 seq_thread 中 waiters 不为空时, 就设置为 true
};

static struct ovs_mutex seq_mutex = OVS_MUTEX_INITIALIZER; //当各个线程同时修改 seq 时, 需要加锁

static uint64_t seq_next = 1; //记录每个 seq 的 value, 每创建一个 seq, 加 1, 每次事件变化, 加 1

static pthread_key_t seq_thread_key; //线程私有变量. 与 seq_thread 关联

struct seq * seq_create(void)

    创建一个 seq

void seq_destroy(struct seq *seq)

    给所有 waiters 发送消息, 并销毁 seq
    问题: 多个线程同时调用是否存在问题

void seq_change(struct seq *seq)

    设置当前 seq->value 为 seq_next++, 给 seq->waiters 的所有 seq_thread
    发送消息, 并清空 seq->waiters

uint64_t seq_read(const struct seq *seq)

    读取 seq->value

static void seq_wait__(struct seq *seq, uint64_t value, const char *where)

    如果 seq->waiters 中 seq_waiter->value 改变, 设置当前 poll_loop 立即唤醒, 如果没有改变, 什么也不做
    如果 seq->waiters 中不存在当前线程对应的 seq_waiter, 创建 seq_waiter, 并确保 seq_waiter 所属线程加入当前线程的 poll_loop 中

void seq_wait_at(const struct seq *seq_, uint64_t value, const char *where)

    当 seq->value != value, 立即唤醒当前线程的 poll_loop
    当 seq->value == value,
        如果 seq->waiters 中某个 seq_waiter->value 不同于 value, 就唤醒 seq_waiter 所属线程的 poll_loop
    
    注:
        如果 seq->waiters 中不存在于当前线程的 seq_waiter, 创建 seq_waiter, 并确保 seq_waiter
        所属线程 seq_thread 的管道监听当前线程 poll_loop 的 POLLIN 事件

void seq_woke(void)

    唤醒当前线程的所有 watier
    注: 某个线程调用 seq_woke 之前应该调用 seq_wait, 不调用也不会有什么问题.
    
    1. 读取当前线程 seq_thread_key 对于的 seq_thread 中所有 seq_waiter, 从所属的 seq->waiters 和 seq_thread->waiters 中删除(此时当前线程没有任何 seq_waiter),
    2. 设置 seq_thread->waiting 为 false.
    3. 并清空管道中的消息.

static void seq_init(void)

    保证 seq_thread_key 被每个线程只初始化一次

static struct seq_thread *seq_thread_get(void)

    获取当前线程与 seq_thread_key 关联的 seq_thread, 如果不存在, 就创建一个新的

static void seq_thread_exit(void *thread_)

    将 thread_ 对象销毁

static void seq_thread_woke(struct seq_thread *thread)

    将 thread->waiters 中所有 seq_waiter 从所属的 seq->waiters 和 seq_thread->waiters 中删除
    之后, 读完 thread->latch 中的消息

static void seq_waiter_destroy(struct seq_waiter *waiter)

    waiter 从所属的 seq->waiters 和 seq_thread->waiters 中删除

static void seq_wake_waiters(struct seq *seq)

    给 seq->waiters 所有元素 seq_waiter 发送消息.
    之后将 waiter 从 seq->waiters 和 seq_thread->waiters 中删除



----------------------------------------------------------------

### latch

void latch_init(struct latch *latch)

    创建一个管道, 并设置为非阻塞模式

void latch_destroy(struct latch *latch)

    关闭管道

bool latch_poll(struct latch *latch)

    返回管道一端是否可读

void latch_set(struct latch *latch)

    给管道另外一段发送消息, 管道的另一端监听 POLLIN 事件的 poll-loop 就好返回

bool latch_is_set(const struct latch *latch)

    poll 直到 latch->fds[0] 可读, 可读返回 true, 不可读返回 false

void latch_wait_at(const struct latch *latch, const char *where)

    将 latch->fds[0] 加入当前线程, 并注册 POLLIN 事件

如果之前调用过 latch_set(与调用次数无关), 那么 latch_poll 返回 true

用法:

A 端

    latch_init(latch)
    while(true) {
        latch_wait_at(latch, "test")
        while(!latch_is_set(latch)) {
            //do other thing
        }
        //the pipe is readable now add handler
        latch_poll(latch) //read all message of the other side
    }
    latch_destroy(latch)

B 端

    latch_set(latch) //发送消息


----------------------------------------------------------------

## RCU

设计思想

多读少写的场景
新版本的写要等待所有的旧版的读操作都完成

1. 每个线程私有对象 perthread_key 对应一个 ovsrcu_perthread
  2



概念:

​     quiesce :  当前线程 perthread_key 关联的 ovsrcu_perthread 被销毁时, 就认为当前线程进入 quiesce 状态

​     grace period :  当所有的线程都处于 quiesce 时, 该时段叫 grace period, 在该阶段, 所有的线程的回调

函数会被调用



### 数据结构

```c
struct ovsrcu_cb {
    void (*function)(void *aux);
    void *aux;
};

struct ovsrcu_cbset {
    struct ovs_list list_node;
    //16 是线程专有回调函数刷入全局 flushed_cbsets 的阈值
    struct ovsrcu_cb cbs[16]; //为什么是 16 ?
    //实际 cbs 大小
    int n_cbs;
};

//线程私有对象

struct ovsrcu_perthread {
    struct ovs_list list_node;  /* In global list. */
    struct ovs_mutex mutex;
    uint64_t seqno;
    struct ovsrcu_cbset *cbset;
    char name[16];              /* This thread's name. */
};

static struct seq *global_seqno: 每个线程开始进入 quiesce 状态时都会改变该值, 标记旧版本操作完成(即线程的局部 cbset 刷新到全局 flushed_cbsets)

static pthread_key_t perthread_key: 线程专有数据

static struct ovs_list ovsrcu_threads: 保存所有线程专有数据 perthread_key 对应的 ovsrcu_perthread

static struct ovs_mutex ovsrcu_threads_mutex: ovsrcu_threads 的锁

static struct guarded_list flushed_cbsets: 保存各个线程的 ovsrcu_perthread->cbset

static struct seq *flushed_cbsets_seq: 记录每个线程 ovsrcu_perthread->cbset 将数据拷贝到 flushed_cbsets 的事件

#define ovsrcu_postpone(FUNCTION, ARG)                          \
    ((void) sizeof((FUNCTION)(ARG), 1),                         \
     (void) sizeof(*(ARG)),                                     \
     ovsrcu_postpone__((void (*)(void *))(FUNCTION), ARG))
```



### 单线程版本

void ovsrcu_quiesce_start(void)

    1. 确保当前线程的 ovsrcu_perthread 为空
    2. 如果 flushed_cbsets 中的元素不为空, 调用每个元素的回调函数, 并清空 flushed_cbsets

bool ovsrcu_is_quiescent(void)

    处于 ovsrcu_quiesce_start 和 ovsrcu_quiesce_end 直接返回 true,
    否则返回 false

void ovsrcu_quiesce(void)

    1. 将当前线程的 cbset 加入 flushed_cbsets, 设置 flushed_cbsets_seq, global_seqno
    2. 如果 flushed_cbsets 中的元素不为空, 调用每个元素的回调函数, 并清空 flushed_cbsets

void ovsrcu_quiesce_end(void)

    初始化当前线程的 ovsrcu_perthread

void ovsrcu_postpone__(void (*function)(void *aux), void *aux)

    将 function 加入当前线程 ovsrcu_perthread->cbset->cbs

#### 用法

    while(true) {
        ovsrcu_quiesce_start
        ovsrcu_quiesce_end
        ovsrcu_postpone__(function)
        ovsrcu_quiesce()
    }

### 多线程版本

任意线程调用 ovsrcu_quiesce_start 或 ovsrcu_synchronize, 就会
启动一个线程:

1. 如果 flushed_cbsets 为空, 就该线程监听 flushed_cbsets_seq 变化,

2. 如果 flushed_cbsets 为不空, 当所有线程(调用 ovsrcu_quiesce_end 的线程)
  都调用 ovsrcu_quiesce(或再次调用 ovsrcu_quiesce_start) 之后调用 ovsrcu_quiesce_end 时,
  调用 flushed_cbsets 中的回调函数

每个 thread 的 为了防止多个 thread 的累计太多回调函数, 限制每个线程最多 16
个回调函数


参考 timeval 的实现


线程1

    for(;;) {
        ovsrcu_quiesce_start()
        ovsrcu_quiesce_end()
    
        ovsrcu_postpone(func1)
        ovsrcu_postpone(func2)
        ...
        ovsrcu_quiesce()
    }

线程2

    for(;;) {
        ovsrcu_quiesce_start()
        ovsrcu_quiesce_end()
    
        ovsrcu_postpone(func3)
        ovsrcu_postpone(func4)
        ...
        ovsrcu_quiesce()
    }

线程3

    for(;;) {
        ovsrcu_quiesce_start()
        ovsrcu_quiesce_end()
        ovsrcu_postpone(func5)
        ovsrcu_postpone(func6)
        ...
        ovsrcu_quiesce()
    }

不管哪个线程先开始, 每次都是保证 func1~func5 执行完
在进行下一次 func1~func5 执行. func1~func5 只能保证每个线程
中的顺序是一致的, 各个线程的顺序是不定的.


ovsrcu_quiesce_start()

    当前线程进入 Quiescent 状态

ovsrcu_quiesce_end()

    当前线程退出 Quiescent 状态

ovsrcu_quiesce()

    当前线程试图退出 Quiescent 状态

ovsrcu_is_quiescent()

    当前线程是否处于 Quiescent 状态

ovsrcu_quiesced

    如果当前进程是单线程模式(没有调用过 pthread_create), 重新初始化 flushed_cbsets, 并调用 flushed_cbsets 的所有回调函数
    如果当前进程是多线程模式(调用过 pthread_create), 创建新的线程脱离当前线程,
    当所有线程都退出 Quiescent 后, 循环遍历 flushed_cbsets 中的每个元素, 并调用对应的回调函数

ovsrcu_synchronize()

    等待所有的线程都退出 Quiescent
    

ovsrcu_call_postponed()

    当前处于 Quiescent 状态, 返回 false, 不处于 Quiescent, 等待直到进入 Quiescent, 返回 true.




核心实现

ovsrcu_postpone_thread
```c
for (;;)
    seqno = seq_read(flushed_cbsets_seq);
    post = ovsrcu_call_postponed
        guarded_list_pop_all(&flushed_cbsets, &cbsets);
        if (list_is_empty(&cbsets)):
            seq_wait(flushed_cbsets_seq, seqno)
            poll_block()
        else
            ovsrcu_synchronize()
                if single_threaded
                    return
                target_seqno = seq_read(global_seqno);
                ovsrcu_quiesce_start();
                    perthread = pthread_getspecific(perthread_key);
                    if perthread:
                        ovsrcu_unregister__(perthread)
                            ovsrcu_flush_cbset(perthread)
                    ovsrcu_quiesced
                        if single_threaded
                            ovsrcu_call_postponed
                        else
                            ovsthread_once : ovs_thread_create("urcu", ovsrcu_postpone_thread, NULL);

                start = time_msec();
                for (;;):
                    done = true
                    cur_seqno = seq_read(global_seqno);
                    LIST_FOR_EACH (perthread, list_node, &ovsrcu_threads)
                        if (perthread->seqno <= target_seqno)
                            done = false;
                            break;
                    if (done)
                        break;
                    poll_timer_wait_until(start + warning_threshold);
                    if (time_msec() - start >= warning_threshold)
                        warning_threshold *= 2;
                    seq_wait(global_seqno, cur_seqno);
                    poll_block();
                ovsrcu_quiesce_end();
                    ovsrcu_perthread_get();
                        ovsrcu_init_module();
                        perthread = pthread_getspecific(perthread_key);
                        if (!perthread):
                            perthread = xmalloc(sizeof *perthread);
                            ovs_mutex_init(&perthread->mutex);
                            perthread->seqno = seq_read(global_seqno);
                            perthread->cbset = NULL;
                            ovs_strlcpy(perthread->name, name[0] ? name : "main", sizeof perthread->name);

                            ovs_mutex_lock(&ovsrcu_threads_mutex);
                            list_push_back(&ovsrcu_threads, &perthread->list_node);
                            ovs_mutex_unlock(&ovsrcu_threads_mutex);

                            pthread_setspecific(perthread_key, perthread);
                            LIST_FOR_EACH_POP (cbset, list_node, &cbsets):
                                for (cb = cbset->cbs; cb < &cbset->cbs[cbset->n_cbs]; cb++):
                                    cb->function(cb->aux)
                                free(cbset)
    if (!post)
        seq_wait(flushed_cbsets_seq, seqno);
        poll_block();
```



static struct ovsrcu_perthread * ovsrcu_perthread_get(void)

    获取线程专有数据 perthread_key 对应的 ovsrcu_perthread, 并返回 ovsrcu_perthread(如果不存在就创建)
    
    1. 初始化 ovsrcu_perthread 对象
    2. 将 ovsrcu_perthread 加入 ovsrcu_threads
    3. 将 perthread_key 与 ovsrcu_perthread 关联
    
    注: 在 perthread_key 没有通过 pthread_key_create() 创建, 或已经通
    过 pthread_key_delete() 删除, 调用 pthread_getspecific() 或
    pthread_setspecific() 是未定义的行为.


void ovsrcu_quiesce_end(void)

    获取线程专有数据 perthread_key 对应的 ovsrcu_perthread, 并返回 ovsrcu_perthread(如果不存在就创建)
    即 ovsrcu_perthread_get()



static void ovsrcu_quiesced(void)

    等待旧版本的所有线程都完成自己操作, 只有第一个调用该函数的线程执行如下操作, 后续调用该函数什么也不做
    1. 如果是单线程:
        如果 flushed_cbsets 为 null, 直接返回
        否则 调用 flushed_cbsets 的每个元素的回调函数
    2. 否则, 创建新的线程, 并且新的线程脱离主线程, 新线程的任务:
    不断调用每个线程的回调函数, 但需要注意的是步调, 当前所有线程
    都处于下一个新的版本时, 才调用所有旧版本的回调函数.


void ovsrcu_quiesce_start(void)

    将当前线程私有数据与 perthread_key 解绑, 销毁 perthread, 并发送 global_seqno 的变化的消息给所有的订阅者
    
    将当前线程私有数据与 perthread_key 解绑定, 并释放 ovsrcu_perthread 对象. 其中包括
     1) 当前线程私有数据与 perthread_key 解绑定
     2) 将线程私有数据 ovsrcu_perthread->cbset 加入 flushed_cbsets, 发送 flushed_cbsets_seq 改变消息给所有订阅者
     3) 将线程私有数据 ovsrcu_perthread 从 ovsrcu_threads 中删除, 发送 global_seqno 改变消息给所有订阅者



void ovsrcu_quiesce(void)

    只是想让程序继续进入下一版本, 并不想将当前线程的 cbset 被调用
    
    将 perthread->cbset 局部线程操作同步到 flushed_cbsets, 并通知 flushed_cbsets_seq ,global_seqno 变化
    之后创建一个新的线程, 之后创建子线程处理 flushed_cbsets
    
    1. 将线程局部数据 perthread->cbset 加入全局数据 flushed_cbsets. 并通知其他线程, flushed_cbsets 被更新了
    2. 通知当前线程 global_seqno 改变了
    3. 确保回调线程启动



bool ovsrcu_is_quiescent(void)

    当前线程的是否处于 quiesce 状态(即 perthread_key 是否为 NULL)


void ovsrcu_synchronize(void)

    等待所有的线程都退出 Quiescent
    1. 当其他线程在 target_seqno = seq_read(global_seqno) 之后, 调用 ovsrcu_quiesce() 或 ovsrcu_quiesce_start() 之后, 才退出.
    注: 存在某个线程的多次调用 ovsrcu_quiesce 或 ovsrcu_quiesce_start, 而某个线程一直没有调用 ovsrcu_quiesce_start 或 ovsrcu_quiesce, 导致数据版本的不是完全同步


void ovsrcu_postpone__(void (*function)(void *aux), void *aux)

    1. 为当前线程的 cbset 增加回调函数(如果 cbset 不存在就创建)
    2. 如果 perthread->cbset 实际数量多于 cbset->cbs 的大小, 将当前线程的 cbset
    加入全局的 flushed_cbsets. 并发送 flushed_cbsets 被更新的通知



static bool ovsrcu_call_postponed(void)

    1. 将 flushed_cbsets 元素移动到临时链表 cbsets, 重新初始化 flushed_cbsets
    2. 如果 cbsets 没有任何元素, 返回 false, 否则继续
    3. 等待所有线程都退出 Quiescent 状态
    3. 调用 flushed_cbsets 的每个元素的所有回调函数, 并销毁该对象, 返回 true

static void * ovsrcu_postpone_thread(void *arg OVS_UNUSED)

```
线程的执行函数

1. 如果 flushed_cbsets 为空,  等待 flushed_cbsets_seq 改变
2. 如果 flushed_cbsets 不为空，等待所有线程都退出 Quiescent 状态，调用 flushed_cbsets 的每个元素的所有回调函数, 并销毁该对象, 继续１
```

​	

static void ovsrcu_flush_cbset(struct ovsrcu_perthread *perthread)

    将线程局部数据 perthread->cbset 加入 flushed_cbsets. 清空 perthread->cbset,
    发送 flushed_cbsets_seq 改变消息给所有订阅者



static void ovsrcu_unregister__(struct ovsrcu_perthread *perthread)

    销毁 perthread, 并发送对应的消息给订阅者(并没有与当前 perthread_key 解绑)

    1. 将线程私有数据 ovsrcu_perthread->cbset 加入 flushed_cbsets, 发送 flushed_cbsets_seq 改变消息给所有订阅者
    2. 将线程私有数据 ovsrcu_perthread 从 ovsrcu_threads 中删除, 释放 ovsrcu_perthread 空间, 发送 global_seqno 改变消息给所有订阅者



static void ovsrcu_thread_exit_cb(void *perthread)

    线程专有数据 perthread_key 被删除时的回调函数


static void ovsrcu_cancel_thread_exit_cb(void *aux OVS_UNUSED)

    perthread_key 与当前线程 ovsrcu_perthread 解绑定(当收到信号(参考 fatal_signals.c)时调用.)


static void ovsrcu_init_module(void)

    保证线程专有数据和全局数据只被初始化一次
    global_seqno
    perthread_key
    flushed_cbsets
    flushed_cbsets_seq
