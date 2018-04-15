
## accept

SYSCALL_DEFINE4(accept4, int, fd, struct sockaddr __user *, upeer_sockaddr, int __user *, upeer_addrlen, int, flags)

    sock = sockfd_lookup_light(fd, &err, &fput_needed)
    newsock = sock_alloc()
    newsock->type = sock->type
    newsock->ops = sock->ops
    newfd = get_unused_fd_flags(flags)
    newfile = sock_alloc_file(newsock, flags, sock->sk->sk_prot_creator->name);
    security_socket_accept(sock, newsock)
    sock->ops->accept(sock, newsock, sock->file->f_flags)
    if upeer_sockaddr != NULL:
        newsock->ops->getname(newsock, (struct sockaddr *)&address, &len, 2)
        move_addr_to_user(&address, len, upeer_sockaddr, upeer_addrlen)
    fd_install(newfd, newfile);
    fput_light(sock->file, fput_needed);
    return new_fd

主要步骤

1. 找到 fd 对应的 file(current->files->fdt[fd])
2. 从 file 定位到 sock(file->private_data)
3. 创建一个新的 sock new_sock, 并且 new_sock->ops 为 sock->ops
4. 调用对应协议的 accept 函数(目前面向流的协议为 inet_accept, 其他协议不支持 accept)
5. 以 newfd 为索引，把 newfile 加入 current->files 中

问题: 为什么 accept 要创建一个新的 sock

## 关键函数

int inet_accept(struct socket *sock, struct socket *newsock, int flags)

    struct sock *sk1 = sock->sk
    struct sock *sk2 = sk1->sk_prot->accept(sk1, flags, &err)
    sock_rps_record_flow(sk2)
    sock_graft(sk2, newsock)
    newsock->state = SS_CONNECTED
    err = 0
    return err

1. 调用对应协议的 accept 函数. 对应 tcp 为 inet_csk_accept
2. rps_sock_flow_table->ents[sk2->sk_rxhash & rps_sock_flow_table->mask] = sk2->sk_rxhash & ~rps_cpu_mask | raw_smp_processor_id()
3. 把 sock 和 newsock 嫁接起来，让它们能相互索引, 具体参见下面.
4. newsock 状态为 CONNECTED

sk2 与 newsock 的关系

    sk2->sk_wq = newsock->wq
    newsock->sk = sk2
    sk2->sk_tx_queue_mapping = -1
    sk2->sk_socket = newsock

struct sock *inet_csk_accept(struct sock *sk, int flags, int *err)
    struct inet_connection_sock *icsk = inet_csk(sk)
    struct request_sock_queue *queue = &icsk->icsk_accept_queue
    if (reqsk_queue_empty(queue))
        long timeo = sock_rcvtimeo(sk, flags & O_NONBLOCK)
        if (!timeo)
            error = -EAGAIN
            return NULL
        inet_csk_wait_for_connect(sk, timeo)
    req = reqsk_queue_remove(queue, sk)
        req = queue->rskq_accept_head
        sk->sk_ack_backlog++
        queue->rskq_accept_head = req->dl_next
    newsk = req->sk
    if (sk->sk_protocol == IPPROTO_TCP && tcp_rsk(req)->tfo_listener)
        if (tcp_rsk(req)->tfo_listener)
            req->sk = NULL
            req = NULL
    return newsk

如果非阻塞, 立即返回, 如果阻塞, 就一直等接受队列不为空, 从接受队列中取一个元素, 返回之, 如果设置了超时, 超时, 队列仍然为空, 返回空.

1. 如果 inet_csk(sk)->icsk_accept_queue 为空并且 flags 包含 O_NONBLOCK, 立即返回. 错误代码 EAGAIN
2. 如果 inet_csk(sk)->icsk_accept_queue 为空并且 flags 不包含 O_NONBLOCK, 阻塞等待.
3. 如果步骤 2 超时收到没有连接, 释放 sk, 返回 NULL.
   如果步骤 2 超时之前收到连接, 从 icsk->icsk_accept_queue 链表中取(删除)一个 request_sock, sk->sk_ack_backlog 计数器减一; 返回删除的 request_sock


关于阻塞等待:

阻塞是进程的状态, 当没有收到连接时, 会将 sock->wq->wait 加入名为 wati 的等待任务链表
并设置当前等待任务是可以响应中断. 之后调用该 accept 的进程进入睡眠, 只有超时或者收到
信号才被唤醒, 唤醒之后, 该 sock->wq->wait 从等待任务列表中删除, 继续后续处理.

需要注意的是如果唤醒之后, 还是没有收到 socket 该进程仍然会调用 accept 系统调用, 并
再次进入休眠.

##附录

### accept 阻塞等待分析


```
struct __wait_queue {
        unsigned int            flags;
        void                    *private;   /* 指向当前的进程控制块 */
        wait_queue_func_t       func;       /* 唤醒函数 */
        struct list_head        task_list;  /* 保持 sock->wq->wait */
};
typedef struct __wait_queue wait_queue_t;
typedef int (*wait_queue_func_t)(wait_queue_t *wait, unsigned mode, int flags, void *key);

#define DEFINE_WAIT_FUNC(name, function)                                \
        wait_queue_t name = {                                           \
                .private        = current,                              \
                .func           = function,                             \
                .task_list      = LIST_HEAD_INIT((name).task_list),     \
        }

#define DEFINE_WAIT(name) DEFINE_WAIT_FUNC(name, autoremove_wake_function)

//kernel/sched/core.c
int default_wake_function(wait_queue_t *curr, unsigned mode, int wake_flags,
                          void *key)
{
        return try_to_wake_up(curr->private, mode, wake_flags);
}

int autoremove_wake_function(wait_queue_t *wait, unsigned mode, int sync, void *key)
{
        int ret = default_wake_function(wait, mode, sync, key);

        if (ret)
                list_del_init(&wait->task_list);
        return ret;
}


prepare_to_wait_exclusive(wait_queue_head_t *q, wait_queue_t *wait, int state)
{
        unsigned long flags;
        /* 这个标志表示一次只唤醒一个等待任务，避免惊群现象 */
        wait->flags |= WQ_FLAG_EXCLUSIVE;
        spin_lock_irqsave(&q->lock, flags);
        if (list_empty(&wait->task_list))
                __add_wait_queue_tail(q, wait);
        set_current_state(state); /* 设置当前进程的状态 */
        spin_unlock_irqrestore(&q->lock, flags);
}

static inline wait_queue_head_t *sk_sleep(struct sock *sk)
{
        BUILD_BUG_ON(offsetof(struct socket_wq, wait) != 0);
        return &rcu_dereference_raw(sk->sk_wq)->wait;
}

static inline int signal_pending(struct task_struct *p)
{
        return unlikely(test_tsk_thread_flag(p,TIF_SIGPENDING));
}

static inline int sock_intr_errno(long timeo)
{
        return timeo == MAX_SCHEDULE_TIMEOUT ? -ERESTARTSYS : -EINTR;
}

/**
 * finish_wait - clean up after waiting in a queue
 * @q: waitqueue waited on
 * @wait: wait descriptor
 *
 * Sets current thread back to running state and removes
 * the wait descriptor from the given waitqueue if still
 * queued.
 */
void finish_wait(wait_queue_head_t *q, wait_queue_t *wait)
{
        unsigned long flags;

        __set_current_state(TASK_RUNNING);
        /*
         * We can check for list emptiness outside the lock
         * IFF:
         *  - we use the "careful" check that verifies both
         *    the next and prev pointers, so that there cannot
         *    be any half-pending updates in progress on other
         *    CPU's that we haven't seen yet (and that might
         *    still change the stack area.
         * and
         *  - all other users take the lock (ie we can only
         *    have _one_ other CPU that looks at or modifies
         *    the list).
         */
        if (!list_empty_careful(&wait->task_list)) {
                spin_lock_irqsave(&q->lock, flags);
                list_del_init(&wait->task_list);
                spin_unlock_irqrestore(&q->lock, flags);
        }
}


/*
 * Wait for an incoming connection, avoid race conditions. This must be called
 * with the socket locked.
 */
static int inet_csk_wait_for_connect(struct sock *sk, long timeo)
{
        struct inet_connection_sock *icsk = inet_csk(sk);
        DEFINE_WAIT(wait);
        int err;

        /*
         * True wake-one mechanism for incoming connections: only
         * one process gets woken up, not the 'whole herd'.
         * Since we do not 'race & poll' for established sockets
         * anymore, the common case will execute the loop only once.
         *
         * Subtle issue: "add_wait_queue_exclusive()" will be added
         * after any current non-exclusive waiters, and we know that
         * it will always _stay_ after any new non-exclusive waiters
         * because all non-exclusive waiters are added at the
         * beginning of the wait-queue. As such, it's ok to "drop"
         * our exclusiveness temporarily when we get woken up without
         * having to remove and re-insert us on the wait queue.
         */
        for (;;) {
                prepare_to_wait_exclusive(sk_sleep(sk), &wait,
                                          TASK_INTERRUPTIBLE);
                release_sock(sk);
                if (reqsk_queue_empty(&icsk->icsk_accept_queue))
                        timeo = schedule_timeout(timeo);   //kernel/time/timer.c
                sched_annotate_sleep();
                lock_sock(sk);
                err = 0;
                if (!reqsk_queue_empty(&icsk->icsk_accept_queue))
                        break;
                err = -EINVAL;
                if (sk->sk_state != TCP_LISTEN)
                        break;
                err = sock_intr_errno(timeo);
                if (signal_pending(current))
                        break;
                err = -EAGAIN;
                if (!timeo)
                        break;
        }
        finish_wait(sk_sleep(sk), &wait);
        return err;
}
```

1. 将 sock->wq->wait 加入名为 wait 的等待任务链表, 并设置当前等待任务是可以响应中断.
2. 调用该 accept 的进程进入睡眠, 只有超时或者收到信号才被唤醒
3. 唤醒之后, 该 sock->wq->wait 从等待任务列表中删除
4. 继续后续处理.

超时之后重新循环的条件:

1. icsk->icsk_accept_queue 为空
2. timeo 超时没有到达
3. 没有收到信号
4. sk->sk_state == TCP_LISTEN

破坏以上任意条件即可退出 accept


