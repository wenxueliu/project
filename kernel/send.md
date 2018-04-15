

* MTU
* MSS
1. MSS 的大小如何确定?
2. 怎样避免中间网络可能出现的分片呢？

通过IP头部的DF标志位，这个标志位是告诉IP报文所途经的所有IP层代码：不要对这个报文分片。如果一个IP报文太大必须要分片，则直接返回一个ICMP错误，说明必须要分片了，且待分片路由器网络接受的MTU值。这样，连接上的发送方主机就可以重新确定MSS。

3. Nagle

Nagle算法的初衷是这样的：应用进程调用发送方法时，可能每次只发送小块数据，造成这台机器发送了许多小的TCP报文。对于整个网络的执行效率来说，小的TCP报文会增加网络拥塞的可能，因此，如果有可能，应该将相临的TCP报文合并成一个较大的TCP报文（当然还是小于MSS的）发送。

Nagle算法要求一个TCP连接上最多只能有一个发送出去还没被确认的小分组，在该分组的确认到达之前不能发送其他的小分组。
内核中是通过 tcp_nagle_test方法实现该算法的。

### 原理

把用户需要发送的用户态内存中的数据，拷贝到内核态内存中，不依赖于用户态内存，也使得进程可以快速释放发送数据占用的用户态内存。

但这个拷贝操作并不是简单的复制，而是把待发送数据，按照MSS来划分成多个尽量达到MSS大小的分片报文段，复制到内核中的sk_buff结构来存放，同时把这些分片组成队列，放到这个TCP连接对应的tcp_write_queue发送队列中。

无论是使用阻塞还是非阻塞套接字，发送方法成功返回时（无论全部成功或者部分成功），既不代表TCP连接的另一端主机接收到了消息，也不代表本机把消息发送到了网络上，只是说明，内核将会试图保证把消息送达对方。



## send

## 用户态

应用层可以使用以下 Socket 函数来发送数据：

ssize_t write(int fd, const void *buf, size_t count);

ssize_t send(int s, const void *buf, size_t len, int flags);

ssize_t sendto(int s, const void *buf, size_t len, int flags, const struct sockaddr *to, socklen_t tolen);

ssize_t sendmsg(int s, const struct msghdr *msg, int flags);

int sendmmsg(int s, struct mmsghdr *msgvec,  unsigned int vlen, unsigned int flags);

这些发送函数有什么区别呢？

当 flags 为 0 时，send() 和 write() 功能相同。

send(s, buf, len, flags) 和 sendto(s, buf, len, flags, NULL, 0) 功能相同。

write() 和 send() 在套接字处于连接状态时可以使用，而 sendto()、sendmsg() 和 sendmmsg() 在任何时候都可用。


## 内核态

SYSCALL_DEFINE6(sendto, int, fd, void __user *, buff, size_t, len, unsigned int, flags, struct sockaddr __user *, addr, int, addr_len)
    import_single_range(WRITE, buff, len, &iov, &msg.msg_iter);
        iov->iov_base = buf
        iov->iov_len = len
        msg.msg_iter->type = WRITE
        msg.msg_iter->iov = iov
        msg.msg_iter->nr_segs = 1
        msg.msg_iter->iov_offset = 0
        msg.msg_iter->count = len
    sock = sockfd_lookup_light(fd, &err, &fput_needed);
    if addr : move_addr_to_kernel(addr, addr_len, &address)
        msg.msg_name = (struct sockaddr *)&address
        msg.msg_namelen = addr_len
    if (sock->file->f_flags & O_NONBLOCK)
        flags |= MSG_DONTWAIT
    msg.msg_flags = flags;
    sock_sendmsg(sock, &msg)
        security_socket_sendmsg(sock, msg, msg_data_left(msg));
            call_int_hook(socket_sendmsg, 0, sock, msg, size)
        sock_sendmsg_nosec(sock, msg)
            sock->ops->sendmsg(sock, msg, msg_data_left(msg))
            SOCK_STREAM
                inet_stream_ops->sendmsg(sock, msg, msg_data_left(msg))
                    inet_sendmsg(sock, msg, msg_data_left(msg))
            SOCK_DGRAM
                inet_dgram_ops->sendmsg(sock, msg, msg_data_left(msg))
                    inet_sendmsg(sock, msg, msg_data_left(msg))
            SOCK_DGRAM
                inet_dgram_ops->sendmsg(sock, msg, msg_data_left(msg))
                    inet_sendmsg(sock, msg, msg_data_left(msg))
            SOCK_RAW
                inet_sockraw_ops->sendmsg(sock, msg, msg_data_left(msg))
                    inet_sendmsg(sock, msg, msg_data_left(msg))
    fput_light(sock->file, fput_needed)

int inet_sendmsg(struct socket *sock, struct msghdr *msg, size_t size)
    struct sock *sk = sock->sk;
    sock_rps_record_flow(sk);  //rps_sock_flow_table->ents[sk->sk_rxhash] = raw_smp_processor_id()
    sk->sk_prot->sendmsg(sk, msg, size)
    if RAW:
        raw_sendmsg
    if TCP:
        tcp_sendmsg
    if UDP:
        udp_sendmsg
    if ICMP:
        ping_v4_sendmsg

主要步骤

1. 找到 fd 对应的 file(current->files->fdt[fd])
2. 初始化消息头
3. 如果地址不为空, 把套接字地址从用户空间拷贝到内核空间
4. 设置发送标志(是否为非阻塞).
5.  调用对应协议的 sendmsg 函数发送数据.


int tcp_sendmsg(struct sock *sk, struct msghdr *msg, size_t size)

1. 分配 skb, 加入发送队列(sk->sk_write_queue)
2. 将用户态要发送的数据拷贝到发送队列(sk->sk_write_queue)的最后一个 skb.

注:

* 如果发送队列的 skb 都用完了, 就重新分配 skb 加入发送队列
* 发送的数据优先拷贝到已有的发送队列的最后一个元素, 要优先将数据加入最后一个元素的空间.
* 数据优先拷贝到线性空间, 如果不够, 就拷贝到分片空间
* 如果发送队列已经占用的内存超过限制, 会等等内存空间够, 在等待之前会优先将数据发送出去
* 如果发送队列的数据都发送完了, 是否会将发送队列缩容?


1. 如果不能发送消息(连接还没有建立或者处于 CLOSE_WAIT), 进入睡眠, 满足以下任一条件唤醒.
   1) 发生错误
   2) sk->sk_state 没有处于 TCPF_SYN_SENT | TCPF_SYN_RECV
   3) 收到信号.
   4) 超时(如果设置了超时)
   5) sk_wait_event(sk, timeo_p, !sk->sk_err && !((1 << sk->sk_state) & ~(TCPF_ESTABLISHED | TCPF_CLOSE_WAIT))) 返回 ture
   如果连接有错误，或者不允许发送数据了，那么返回-EPIPE

2. 获取当前的 MSS, 计算支持的最大发送数据长度(TODO)。如果支持 GSO，最大包是 MSS 的 tp->gro_segs 倍


3. 如果用户态有数据没有发送出去:

    3.1 从 sk 的写队列(sk_write_queue)中取一个 skb.

    3.2 如果当前 sk->sk_send_head 不为空(即当前有数据正在发送), 即 skb 正在被发送,
        重新计算要拷贝到 skb 队列尾的数据长度copy(size_goal - skb->len). 继续到步骤 4

    3.3 如果当前 sk->sk_send_head 为空(即当前有数据正在发送), 继续到步骤 4

    3.4 如果可拷贝到发送队列的数据长度小于等于 0:

        3.4.1 如果发送队列的总大小(sk->sk_wmem_queued) 大于等于发送缓存空间 (sk->sk_sndbuf)，
              或者发送缓存中尚未发送的数据量超过了用户的设置值，就进入等待。

        3.4.2 申请一个skb，其线性数据区的大小为:
            通过 select_size() 得到的线性数据区中 TCP 负荷的大小 + 最大的协议头长度。
            如果申请 skb 失败了，或者虽然申请skb成功，但是从系统层面判断此次申请不合法，
            那么就进入睡眠，等待内存。

        3.4.3. 将 skb 加入 sk->sk_write_queue, 并设置 sk->sk_send_head, sk->highest_sack
        3.4.4. 设置 copy = max = size_goal

    3.5 如果可拷贝到发送队列的数据长度大于用户空间要发送的数据长度, 设置可拷贝到发送队列的数据长度为用户空间要发送的数据长度

    3.6 如果 skb 的线性数据区还有剩余空间，将用户数据先复制到 skb 的线性数据区。

    3.7 如果 skb 的线性数据区已经用完了，那么就使用分页区

        3.7.1. 检查分页是否有可用空间，如果没有就申请新的 page, 如果申请失败，说明系统内存不足。
            之后会设置 TCP 内存压力标志，减小发送缓冲区的上限，睡眠等待内存。

        3.7.2. 判断能否往最后一个分页追加数据, 如果不能追加时，检查分页数是否达到了上限，
            或者网卡不支持分散聚合, 就为此 skb 设置 PSH 标志，尽快地发送出去。
            然后申请新的skb，来继续填装数据。

        3.7.3 如果能追加就将数据追加到之前的分片

        3.7.4 如果不能追加就将数据追加到新的分片

        3.7.5. 拷贝 msg->msg_iter 的数据到 skb 的分片. 更新 skb 的长度字段，更新 sock 的发送队列大小和预分配缓存。

4. 如果最大发送数据长度小于 skb 长度(skb->len), 从 skbuff_fclone_cache 中分配一个 skb, 加入 sk->sk_write_queue

5. 如果最大发送数据长度大于 skb 长度(skb->len), 并且 skb 的线性数据区空间不为空, 拷贝用户空间数据到 skb 的 tailroom. 继续循环

6. 如果最大发送数据长度大于 skb 长度(skb->len), 并且 skb 的线性数据区空间为空:

    6.1 检查分页是否有可用空间，如果没有就申请新的page。如果申请失败，说明系统内存不足。
        之后会设置TCP内存压力标志，减小发送缓冲区的上限，睡眠等待内存。
    6.2 判断能否往最后一个分页追加数据。不能追加时，检查分页数是否达到了上限、
        或网卡不支持分散聚合。如果是的话，就为此skb设置PSH标志。然后申请新的skb，来继续填装数据。
    6.3 拷贝用户空间数据到 skb 的 frags, 更新skb的长度字段, 更新sock的发送队列大小和预分配缓存

7. 拷贝成功后更新相关序列号

8. 如果所有的数据都加入了发送队列, 尽可能的将发送队列中的 skb 发送出去

注: 暂不考虑 fastopen, tcp repair 选项

tcp_sendmsg
    __tcp_push_pending_frames(sk, mss_now, TCP_NAGLE_PUSH)
        tcp_write_xmit(sk, cur_mss, nonagle, 0, sk_gfp_mask(sk, GFP_ATOMIC)
            tcp_transmit_skb(sk, tcp_send_head(sk), 1, GFP_ATOMIC)
    tcp_push_one(sk, mss_now)
        tcp_write_xmit(sk, mss_now, TCP_NAGLE_PUSH, 1, sk->sk_allocation)
    tcp_push(sk, flags & ~MSG_MORE, mss_now, TCP_NAGLE_PUSH, size_goal)
        __tcp_push_pending_frames(sk, mss_now, nonagle)
            tcp_write_xmit(sk, cur_mss, nonagle, 0, sk_gfp_mask(sk, GFP_ATOMIC)
                tcp_transmit_skb(sk, tcp_send_head(sk), 1, GFP_ATOMIC)


需要注意的是

tcp 写序列的增加, 并不能保证发送到对端, 仅仅表示写到 sock 的发送队列.

TODO:

1. tcp 发送 mss 的计算方法?
2. 数据从用户态拷贝到 tcp 发送队列的过程.


###附录

include/linux/socket.h

```
static inline long sock_sndtimeo(const struct sock *sk, bool noblock)
{
        return noblock ? 0 : sk->sk_sndtimeo;
}

/*
 *      As we do 4.4BSD message passing we use a 4.4BSD message passing
 *      system, not 4.3. Thus msg_accrights(len) are now missing. They
 *      belong in an obscure libc emulation or the bin.
 */

struct msghdr {
        void            *msg_name;      /* ptr to socket address structure */
        int             msg_namelen;    /* size of socket address structure */
        struct iov_iter msg_iter;       /* data */
        void            *msg_control;   /* ancillary data */
        __kernel_size_t msg_controllen; /* ancillary data buffer length */
        unsigned int    msg_flags;      /* flags on received message */
        struct kiocb    *msg_iocb;      /* ptr to iocb for async requests */
};

struct iovec
{
        void __user *iov_base;  /* BSD uses caddr_t (1003.1g requires void *) */
        __kernel_size_t iov_len; /* Must be size_t (1003.1g) */
};

int import_single_range(int rw, void __user *buf, size_t len,
                 struct iovec *iov, struct iov_iter *i)
{
        if (len > MAX_RW_COUNT)
                len = MAX_RW_COUNT;
        if (unlikely(!access_ok(!rw, buf, len)))
                return -EFAULT;

        iov->iov_base = buf;
        iov->iov_len = len;
        iov_iter_init(i, rw, iov, 1, len);
        return 0;
}
EXPORT_SYMBOL(import_single_range);

struct socket *sock_from_file(struct file *file, int *err)
{
        if (file->f_op == &socket_file_ops)
                return file->private_data;      /* set in sock_map_fd */

        *err = -ENOTSOCK;
        return NULL;
}
EXPORT_SYMBOL(sock_from_file);

static struct socket *sockfd_lookup_light(int fd, int *err, int *fput_needed)
{
        struct fd f = fdget(fd);
        struct socket *sock;

        *err = -EBADF;
        if (f.file) {
                sock = sock_from_file(f.file, err);
                if (likely(sock)) {
                        *fput_needed = f.flags;
                        return sock;
                }
                fdput(f);
        }
        return NULL;
}

/*
 *      Send a datagram to a given address. We move the address into kernel
 *      space and check the user space data area is readable before invoking
 *      the protocol.
 */

SYSCALL_DEFINE6(sendto, int, fd, void __user *, buff, size_t, len,
                unsigned int, flags, struct sockaddr __user *, addr,
                int, addr_len)
{
        struct socket *sock;
        struct sockaddr_storage address;
        int err;
        struct msghdr msg; //消息头
        struct iovec iov;  //缓冲区数据
        int fput_needed;

        err = import_single_range(WRITE, buff, len, &iov, &msg.msg_iter);
        if (unlikely(err))
                return err;
        sock = sockfd_lookup_light(fd, &err, &fput_needed);
        if (!sock)
                goto out;

        msg.msg_name = NULL;
        msg.msg_control = NULL;
        msg.msg_controllen = 0;
        msg.msg_namelen = 0;
        if (addr) { //如果指定了 socket 地址, 将其从用户态拷贝到内核态
                err = move_addr_to_kernel(addr, addr_len, &address);
                if (err < 0)
                        goto out_put;
                msg.msg_name = (struct sockaddr *)&address;
                msg.msg_namelen = addr_len;
        }
        if (sock->file->f_flags & O_NONBLOCK)
                flags |= MSG_DONTWAIT;
        msg.msg_flags = flags;
        err = sock_sendmsg(sock, &msg);

out_put:
        fput_light(sock->file, fput_needed);
out:
        return err;
}

/*
 *      Send a datagram down a socket.
 */

SYSCALL_DEFINE4(send, int, fd, void __user *, buff, size_t, len,
                unsigned int, flags)
{
        return sys_sendto(fd, buff, len, flags, NULL, 0);
}

#define sk_wait_event(__sk, __timeo, __condition)                       \
        ({      int __rc;                                               \
                release_sock(__sk);                                     \
                __rc = __condition;                                     \
                if (!__rc) {                                            \
                        *(__timeo) = schedule_timeout(*(__timeo));      \
                }                                                       \
                sched_annotate_sleep();                                         \
                lock_sock(__sk);                                        \
                __rc = __condition;                                     \
                __rc;                                                   \
        })


/**
 * sk_stream_wait_connect - Wait for a socket to get into the connected state
 * @sk: sock to wait on
 * @timeo_p: for how long to wait
 *
 * Must be called with the socket locked.
 */
int sk_stream_wait_connect(struct sock *sk, long *timeo_p)
{
        struct task_struct *tsk = current;
        DEFINE_WAIT(wait); /* 初始化等待任务 */
        int done;

        do {
                int err = sock_error(sk);
                /* 连接发生错误 */
                if (err)
                        return err;
                /* 此时连接没有处于 SYN_SENT 或 SYN_RECV 的状态 */
                if ((1 << sk->sk_state) & ~(TCPF_SYN_SENT | TCPF_SYN_RECV))
                        return -EPIPE;
                /* 如果是非阻塞的，或者等待时间耗尽了，直接返回 */
                if (!*timeo_p)
                        return -EAGAIN;
                /* 如果进程有待处理的信号，返回 */
                if (signal_pending(tsk))
                        return sock_intr_errno(*timeo_p);

                /* 把等待任务加入到socket等待队列头部，把进程的状态设为TASK_INTERRUPTIBLE */
                prepare_to_wait(sk_sleep(sk), &wait, TASK_INTERRUPTIBLE);
                sk->sk_write_pending++; /* 更新写等待计数 */
                /*
                 * 进入睡眠，返回值为真的条件： 连接没有发生错误，且状态为 ESTABLISHED 或 CLOSE_WAIT。
                 */
                done = sk_wait_event(sk, timeo_p,
                                     !sk->sk_err &&
                                     !((1 << sk->sk_state) &
                                       ~(TCPF_ESTABLISHED | TCPF_CLOSE_WAIT)));
                /* 把等待任务从等待队列中删除，把当前进程的状态设为TASK_RUNNING */
                finish_wait(sk_sleep(sk), &wait);
                sk->sk_write_pending--; /* 更新写等待计数 */
        } while (!done);
        return 0;
}
EXPORT_SYMBOL(sk_stream_wait_connect);

/* Bound MSS / TSO packet size with the half of the window */
static inline int tcp_bound_to_half_wnd(struct tcp_sock *tp, int pktsize)
{
        int cutoff;

        /* When peer uses tiny windows, there is no use in packetizing
         * to sub-MSS pieces for the sake of SWS or making sure there
         * are enough packets in the pipe for fast recovery.
         *
         * On the other hand, for extremely large MSS devices, handling
         * smaller than MSS windows in this way does make sense.
         */
        if (tp->max_window >= 512)
                cutoff = (tp->max_window >> 1);
        else
                cutoff = tp->max_window;

        if (cutoff && pktsize > cutoff)
                return max_t(int, cutoff, 68U - tp->tcp_header_len);
        else
                return pktsize;
}

static unsigned int tcp_xmit_size_goal(struct sock *sk, u32 mss_now,
                                       int large_allowed)
{
        struct tcp_sock *tp = tcp_sk(sk);
        u32 new_size_goal, size_goal;

        if (!large_allowed || !sk_can_gso(sk))
                return mss_now;

        /* Note : tcp_tso_autosize() will eventually split this later */
        new_size_goal = sk->sk_gso_max_size - 1 - MAX_TCP_HEADER;
        //new_size_goal 最大为 tp->max_window/2, 最小为 68U - tp->tcp_header_len
        new_size_goal = tcp_bound_to_half_wnd(tp, new_size_goal);

        /* We try hard to avoid divides here */
        size_goal = tp->gso_segs * mss_now;
        if (unlikely(new_size_goal < size_goal ||
                     new_size_goal >= size_goal + mss_now)) {
                tp->gso_segs = min_t(u16, new_size_goal / mss_now,
                                     sk->sk_gso_max_segs);
                size_goal = tp->gso_segs * mss_now;
        }

        return max(size_goal, mss_now);
}

static inline void tcp_slow_start_after_idle_check(struct sock *sk)
{
        struct tcp_sock *tp = tcp_sk(sk);
        s32 delta;

        if (!sysctl_tcp_slow_start_after_idle || tp->packets_out)
                return;
        delta = tcp_time_stamp - tp->lsndtime;
        if (delta > inet_csk(sk)->icsk_rto)
                tcp_cwnd_restart(sk, delta);
}

static inline bool sk_has_account(struct sock *sk)
{
        /* return true if protocol supports memory accounting */
        return !!sk->sk_prot->memory_allocated;
}

static inline void sk_mem_charge(struct sock *sk, int size)
{
        if (!sk_has_account(sk))
                return;
        sk->sk_forward_alloc -= size;
}

static inline void __tcp_add_write_queue_tail(struct sock *sk, struct sk_buff *skb)
{
        __skb_queue_tail(&sk->sk_write_queue, skb);
}

static inline void tcp_add_write_queue_tail(struct sock *sk, struct sk_buff *skb)
{
        __tcp_add_write_queue_tail(sk, skb);

        /* Queue it, remembering where we must start sending. */
        if (sk->sk_send_head == NULL) {
                sk->sk_send_head = skb;

                if (tcp_sk(sk)->highest_sack == NULL)
                        tcp_sk(sk)->highest_sack = skb;
        }
}

static void skb_entail(struct sock *sk, struct sk_buff *skb)
{
        struct tcp_sock *tp = tcp_sk(sk);
        struct tcp_skb_cb *tcb = TCP_SKB_CB(skb);

        skb->csum    = 0;
        tcb->seq     = tcb->end_seq = tp->write_seq;
        tcb->tcp_flags = TCPHDR_ACK;
        tcb->sacked  = 0;
        __skb_header_release(skb);
        tcp_add_write_queue_tail(sk, skb);
        sk->sk_wmem_queued += skb->truesize;
        sk_mem_charge(sk, skb->truesize);
        if (tp->nonagle & TCP_NAGLE_PUSH)
                tp->nonagle &= ~TCP_NAGLE_PUSH;

        /*
         * 检查是否开始慢启动, 慢启动的条件:
         * 1. 当前时间 - 上次发送时间 > RTO
         */
        tcp_slow_start_after_idle_check(sk);
}

static int tcp_send_mss(struct sock *sk, int *size_goal, int flags)
{
        int mss_now;

        mss_now = tcp_current_mss(sk);
        *size_goal = tcp_xmit_size_goal(sk, mss_now, !(flags & MSG_OOB));

        return mss_now;
}

static inline bool sk_stream_memory_free(const struct sock *sk)
{
        if (sk->sk_wmem_queued >= sk->sk_sndbuf)
                return false;

        return sk->sk_prot->stream_memory_free ?
                sk->sk_prot->stream_memory_free(sk) : true;
}

/**
 * sk_stream_wait_memory - Wait for more memory for a socket
 * @sk: socket to wait for memory
 * @timeo_p: for how long
 */
int sk_stream_wait_memory(struct sock *sk, long *timeo_p)
{
        int err = 0;
        long vm_wait = 0;
        long current_timeo = *timeo_p;
        bool noblock = (*timeo_p ? false : true);
        DEFINE_WAIT(wait); /* 初始化等待任务 */

        if (sk_stream_memory_free(sk))
                current_timeo = vm_wait = (prandom_u32() % (HZ / 5)) + 2;

        while (1) {
                sk_set_bit(SOCKWQ_ASYNC_NOSPACE, sk);

                prepare_to_wait(sk_sleep(sk), &wait, TASK_INTERRUPTIBLE);

                /* 连接发生错误 */
                if (sk->sk_err || (sk->sk_shutdown & SEND_SHUTDOWN))
                        goto do_error;
                /* 超时或非阻塞 */
                if (!*timeo_p) {
                        if (noblock)
                                set_bit(SOCK_NOSPACE, &sk->sk_socket->flags);
                        goto do_nonblock;
                }
                /* 如果进程有待处理的信号，返回 */
                if (signal_pending(current))
                        goto do_interrupted;

                sk_clear_bit(SOCKWQ_ASYNC_NOSPACE, sk);
                if (sk_stream_memory_free(sk) && !vm_wait)
                        break;

                set_bit(SOCK_NOSPACE, &sk->sk_socket->flags);
                sk->sk_write_pending++;
                sk_wait_event(sk, &current_timeo, sk->sk_err ||
                                                  (sk->sk_shutdown & SEND_SHUTDOWN) ||
                                                  (sk_stream_memory_free(sk) &&
                                                  !vm_wait));
                sk->sk_write_pending--;

                if (vm_wait) {
                        vm_wait -= current_timeo;
                        current_timeo = *timeo_p;
                        if (current_timeo != MAX_SCHEDULE_TIMEOUT &&
                            (current_timeo -= vm_wait) < 0)
                                current_timeo = 0;
                        vm_wait = 0;
                }
                *timeo_p = current_timeo;
        }
out:
        finish_wait(sk_sleep(sk), &wait);
        return err;

do_error:
        err = -EPIPE;
        goto out;
do_nonblock:
        err = -EAGAIN;
        goto out;
do_interrupted:
        err = sock_intr_errno(*timeo_p);
        goto out;
}
EXPORT_SYMBOL(sk_stream_wait_memory);

static inline int select_size(const struct sock *sk, bool sg)
{
        const struct tcp_sock *tp = tcp_sk(sk);
        int tmp = tp->mss_cache;  //初始化 536

        if (sg) {
                if (sk_can_gso(sk)) {
                        /* Small frames wont use a full page:
                         * Payload will immediately follow tcp header.
                         */
                        tmp = SKB_WITH_OVERHEAD(2048 - MAX_TCP_HEADER);
                } else {
                        int pgbreak = SKB_MAX_HEAD(MAX_TCP_HEADER);

                        if (tmp >= pgbreak &&
                            tmp <= pgbreak + (MAX_SKB_FRAGS - 1) * PAGE_SIZE)
                                tmp = pgbreak;
                }
        }

        return tmp;
}

static inline int skb_availroom(const struct sk_buff *skb)
{
        /* skb->data_len不为零，表示有非线性的数据区 */
        if (skb_is_nonlinear(skb))
                return 0;

        /* data room的大小 */
        return skb->end - skb->tail - skb->reserved_tailroom;
}

/**
 * skb_page_frag_refill - check that a page_frag contains enough room
 * @sz: minimum size of the fragment we want to get
 * @pfrag: pointer to page_frag
 * @gfp: priority for memory allocation
 *
 * Note: While this allocator tries to use high order pages, there is
 * no guarantee that allocations succeed. Therefore, @sz MUST be
 * less or equal than PAGE_SIZE.
 */
bool skb_page_frag_refill(unsigned int sz, struct page_frag *pfrag, gfp_t gfp)
{
        if (pfrag->page) {
                if (page_ref_count(pfrag->page) == 1) {
                        pfrag->offset = 0;
                        return true;
                }
                if (pfrag->offset + sz <= pfrag->size)
                        return true;
                put_page(pfrag->page);
        }

        pfrag->offset = 0;
        if (SKB_FRAG_PAGE_ORDER) {
                /* Avoid direct reclaim but allow kswapd to wake */
                pfrag->page = alloc_pages((gfp & ~__GFP_DIRECT_RECLAIM) |
                                          __GFP_COMP | __GFP_NOWARN |
                                          __GFP_NORETRY,
                                          SKB_FRAG_PAGE_ORDER);
                if (likely(pfrag->page)) {
                        pfrag->size = PAGE_SIZE << SKB_FRAG_PAGE_ORDER;
                        return true;
                }
        }
        pfrag->page = alloc_page(gfp);
        if (likely(pfrag->page)) {
                pfrag->size = PAGE_SIZE;
                return true;
        }
        return false;
}
EXPORT_SYMBOL(skb_page_frag_refill);

static inline void sk_enter_memory_pressure(struct sock *sk)
{
        if (!sk->sk_prot->enter_memory_pressure)
                return;

        sk->sk_prot->enter_memory_pressure(sk);
}

static inline void sk_stream_moderate_sndbuf(struct sock *sk)
{
        if (!(sk->sk_userlocks & SOCK_SNDBUF_LOCK)) {
                sk->sk_sndbuf = min(sk->sk_sndbuf, sk->sk_wmem_queued >> 1);
                sk->sk_sndbuf = max_t(u32, sk->sk_sndbuf, SOCK_MIN_SNDBUF);
        }
}

bool sk_page_frag_refill(struct sock *sk, struct page_frag *pfrag)
{
        //检查 pfrag 包含足够的空间
        if (likely(skb_page_frag_refill(32U, pfrag, sk->sk_allocation)))
                return true;

        //进入内存压力
        sk_enter_memory_pressure(sk);
        //减少 sk->sk_sndbuf
        sk_stream_moderate_sndbuf(sk);
        return false;
}
EXPORT_SYMBOL(sk_page_frag_refill);


size_t copy_from_iter(void *addr, size_t bytes, struct iov_iter *i)
{
        char *to = addr;
        if (unlikely(bytes > i->count))
                bytes = i->count;

        if (unlikely(!bytes))
                return 0;

        iterate_and_advance(i, bytes, v,
                __copy_from_user((to += v.iov_len) - v.iov_len, v.iov_base,
                                 v.iov_len),
                memcpy_from_page((to += v.bv_len) - v.bv_len, v.bv_page,
                                 v.bv_offset, v.bv_len),
                memcpy((to += v.iov_len) - v.iov_len, v.iov_base, v.iov_len)
        )

        return bytes;
}
EXPORT_SYMBOL(copy_from_iter);

static inline int skb_do_copy_data_nocache(struct sock *sk, struct sk_buff *skb,
                                           struct iov_iter *from, char *to,
                                           int copy, int offset)
{
        /* 需要TCP自己计算校验和 */
        if (skb->ip_summed == CHECKSUM_NONE) {
                __wsum csum = 0;
                /* 拷贝用户空间的数据到内核空间，同时计算用户数据的校验和 */
                if (csum_and_copy_from_iter(to, copy, &csum, from) != copy)
                        return -EFAULT;
                skb->csum = csum_block_add(skb->csum, csum, offset);
        } else if (sk->sk_route_caps & NETIF_F_NOCACHE_COPY) {
                if (copy_from_iter_nocache(to, copy, from) != copy)
                        return -EFAULT;
        } else if (copy_from_iter(to, copy, from) != copy) //拷贝长度为 copy 的空间到 from
                return -EFAULT;

        return 0;
}

static inline int skb_add_data_nocache(struct sock *sk, struct sk_buff *skb,
                                       struct iov_iter *from, int copy)
{
        int err, offset = skb->len;

        /* 拷贝用户空间的数据到内核空间.
           即给 skb 腾出大小为 copy 的空间, 从 from 拷贝 copy 到 skb_put(skb, * copy) 开始的地址. */
        err = skb_do_copy_data_nocache(sk, skb, from, skb_put(skb, copy),
                                       copy, offset);
        /* 如果拷贝失败，恢复skb->len和data room的大小 */
        if (err)
                __skb_trim(skb, offset); //出错, 将数据块还原

        return err;
}

static inline int skb_copy_to_page_nocache(struct sock *sk, struct iov_iter *from,
                                           struct sk_buff *skb,
                                           struct page *page,
                                           int off, int copy)
{
        int err;

        /* 拷贝用户空间的数据到内核空间.
           即给 skb 腾出大小为 copy 的空间, 从 from 拷贝长度为 copy 到 page_address(page) + off 开始的地址.
         */
        err = skb_do_copy_data_nocache(sk, skb, from, page_address(page) + off,
                                       copy, skb->len);
        if (err)
                return err;

        skb->len             += copy;
        skb->data_len        += copy;
        skb->truesize        += copy;
        sk->sk_wmem_queued   += copy;
        sk_mem_charge(sk, copy);
        return 0;
}

static void tcp_tx_timestamp(struct sock *sk, struct sk_buff *skb)
{
        if (sk->sk_tsflags) {
                struct skb_shared_info *shinfo = skb_shinfo(skb);

                sock_tx_timestamp(sk, &shinfo->tx_flags);
                if (shinfo->tx_flags & SKBTX_ANY_TSTAMP)
                        shinfo->tskey = TCP_SKB_CB(skb)->seq + skb->len - 1;
        }
}



struct sk_buff *sk_stream_alloc_skb(struct sock *sk, int size, gfp_t gfp,
                                    bool force_schedule)
{
        struct sk_buff *skb;

        /* The TCP header must be at least 32-bit aligned.  */
        size = ALIGN(size, 4);

        if (unlikely(tcp_under_memory_pressure(sk)))
                sk_mem_reclaim_partial(sk);

        //从 skbuff_fclone_cache 分配一个 skb, 没有 headroom, tailroom 至少为 size + sk->sk_prot->max_header.
        skb = alloc_skb_fclone(size + sk->sk_prot->max_header, gfp);
        if (likely(skb)) {
                bool mem_scheduled;

                if (force_schedule) {
                        mem_scheduled = true;
                        sk_forced_mem_schedule(sk, skb->truesize);
                } else {
                        mem_scheduled = sk_wmem_schedule(sk, skb->truesize);
                }
                if (likely(mem_scheduled)) {
                        skb_reserve(skb, sk->sk_prot->max_header);
                        /*
                         * Make sure that we have exactly size bytes
                         * available to the caller, no more, no less.
                         */
                        skb->reserved_tailroom = skb->end - skb->tail - size;
                        return skb;
                }
                __kfree_skb(skb);
        } else {
                sk->sk_prot->enter_memory_pressure(sk);
                sk_stream_moderate_sndbuf(sk);
        }
        return NULL;
}

/* Push out any pending frames which were held back due to
 * TCP_CORK or attempt at coalescing tiny packets.
 * The socket must be locked by the caller.
 */
void __tcp_push_pending_frames(struct sock *sk, unsigned int cur_mss,
                               int nonagle)
{
        /* If we are closed, the bytes will have to remain here.
         * In time closedown will finish, we empty the write queue and
         * all will be happy.
         */
        if (unlikely(sk->sk_state == TCP_CLOSE))
                return;

        if (tcp_write_xmit(sk, cur_mss, nonagle, 0,
                           sk_gfp_mask(sk, GFP_ATOMIC)))
                tcp_check_probe_timer(sk);
}

int tcp_sendmsg(struct sock *sk, struct msghdr *msg, size_t size)
{
    struct tcp_sock *tp = tcp_sk(sk);
    struct sk_buff *skb;
    int flags, err, copied = 0;
    int mss_now = 0, size_goal, copied_syn = 0;
    bool sg;
    long timeo;

    lock_sock(sk);

    flags = msg->msg_flags;

    /*
     * 根据调用者传入的标志位，判断是否启用了快速开启(Fast Open)。
     * 关于Fast Open的讨论，详见 RFC 7413
     */
    if (flags & MSG_FASTOPEN) {
        err = tcp_sendmsg_fastopen(sk, msg, &copied_syn, size);
        if (err == -EINPROGRESS && copied_syn > 0)
            goto out;
        else if (err)
            goto out_err;
    }

    timeo = sock_sndtimeo(sk, flags & MSG_DONTWAIT);

    /* Wait for a connection to finish. One exception is TCP Fast Open
     * (passive side) where data is allowed to be sent before a connection
     * is fully established.
     */
    /*
     * 如果连接没有处于 TCPF_ESTABLISHED, TCPF_CLOSE_WAIT
     * 就等待连接完成(暂不考虑 fastopen)
     *
     * 为什么只有这两个状态?
     * 有一点处于这两个状态的 sock, 都没有发送 FIN, 因此认为
     * 仍然处于连接状态
     */
    if (((1 << sk->sk_state) & ~(TCPF_ESTABLISHED | TCPF_CLOSE_WAIT)) &&
        !tcp_passive_fastopen(sk)) {
        err = sk_stream_wait_connect(sk, &timeo);
        if (err != 0)
            goto do_error;
    }

    /* TCP repair是Linux3.5引入的新补丁，它能够实现容器在不同的物理主机间迁移。
     * 它能够在迁移之后，将TCP连接重新设置到之前的状态。
     */
    if (unlikely(tp->repair)) {
        if (tp->repair_queue == TCP_RECV_QUEUE) {
            copied = tcp_send_rcvq(sk, msg, size);
            goto out_nopush;
        }

        err = -EINVAL;
        if (tp->repair_queue == TCP_NO_QUEUE)
            goto out_err;

        /* 'common' sending to sendq */
    }

    /* This should be in poll */
    // 清除使用异步情况下，发送队列满了的标志。
    sk_clear_bit(SOCKWQ_ASYNC_NOSPACE, sk);

    /*
     * 获取当前的 MSS, 计算支持的最大数据长度(size_goal)。
     * 如果支持 GSO，最大包是 MSS 的 tp->gro_segs 倍
     */
    mss_now = tcp_send_mss(sk, &size_goal, flags);

    /* Ok commence sending. */
    //已经拷贝到发送队列的(sk->sk_write_queue)长度
    copied = 0;

    err = -EPIPE;
    if (sk->sk_err || (sk->sk_shutdown & SEND_SHUTDOWN))
        goto out_err;

    sg = !!(sk->sk_route_caps & NETIF_F_SG); //路由是否支持分段

    while (msg_data_left(msg)) { //msg->msg_iter->count != 0
        //可拷贝到发送队列(sk->sk_write_queue)的数据长度
        int copy = 0;
        int max = size_goal;

        //skb 指向 sk->sk_write_queue 链表最后一个元素
        skb = tcp_write_queue_tail(sk);
        //sk->sk_send_head != NULL 还有未发送的数据，说明该skb还未发送
        if (tcp_send_head(sk)) {
            /* 如果网卡不支持检验和计算，那么 skb 的最大长度为MSS，即不能使用GSO */
            if (skb->ip_summed == CHECKSUM_NONE)
                max = mss_now;
            copy = max - skb->len; /* 此 skb 可追加的数据长度 */
        }

        if (copy <= 0) {
new_segment:
            /* Allocate new segment. If the interface is SG,
             * allocate skb fitting to single page.
             */
            /* 如果发送队列的总大小(sk->sk_wmem_queued) 大于等于发送缓存空间 (sk->sk_sndbuf)，
             * 或者发送缓存中尚未发送的数据量超过了用户的设置值，就进入等待。
             */
            if (!sk_stream_memory_free(sk))
                goto wait_for_sndbuf;

            /*
             * 申请一个skb，其线性数据区的大小为：
             * 通过 select_size() 得到的线性数据区中 TCP 负荷的大小 + 最大的协议头长度。
             * 如果申请 skb 失败了，或者虽然申请skb成功，但是从系统层面判断此次申请不合法，
             * 那么就进入睡眠，等待内存。
             */
            skb = sk_stream_alloc_skb(sk, select_size(sk, sg), sk->sk_allocation,
                        skb_queue_empty(&sk->sk_write_queue));
            if (!skb)
                goto wait_for_memory;

            /*
             * Check whether we can use HW checksum.
             */
            /* 如果网卡支持校验和的计算，那么由硬件计算报头和首部的校验和。*/
            if (sk_check_csum_caps(sk))
                skb->ip_summed = CHECKSUM_PARTIAL;

            /*
             * 更新 skb 的 TCP 控制块字段，把 skb 加入到 sock 发送队列(sk_write_queue)的尾部，
             * 如果 sk->sk_send_head 为 NULL, 更新  sk->sk_send_head = skb
             * 如果 tcp_sk(sk)->highest_sack 为 NULL, 更新 tcp_sk(sk)->highest_sack = skb
             *      sk->sk_wmem_queued += skb->truesize,
             *      sk->sk_forward_alloc -= size;
             */
            skb_entail(sk, skb);
            copy = size_goal;
            max = size_goal;

            /* All packets are restored as if they have
             * already been sent. skb_mstamp isn't set to
             * avoid wrong rtt estimation.
             */
            if (tp->repair) /* 如果使用了TCP REPAIR选项，那么为skb设置"发送时间"。*/
                TCP_SKB_CB(skb)->sacked |= TCPCB_REPAIRED;
        }

        /* Try to append data to the end of skb. */
        if (copy > msg_data_left(msg))
            copy = msg_data_left(msg);

        /* Where to copy to? */
        /* 如果 skb 的线性数据区还有剩余空间，将用户数据先复制到 skb
         * 的线性数据区。
         */
        if (skb_availroom(skb) > 0) {
            /* We have some space in skb head. Superb! */
            copy = min_t(int, copy, skb_availroom(skb));
            //从 msg->msg_iter 开始拷贝长度为 copy 的数据到 skb。
            err = skb_add_data_nocache(sk, skb, &msg->msg_iter, copy);
            if (err)
                goto do_fault;
        } else { /* 如果skb的线性数据区已经用完了，那么就使用分页区 */
            bool merge = true;
            int i = skb_shinfo(skb)->nr_frags; /* 分页数 */
            struct page_frag *pfrag = sk_page_frag(sk); /* 上次缓存的分页 */

            /*
             * 检查分页是否有可用空间，如果没有就申请新的 page。
             * 如果申请失败，说明系统内存不足。
             * 之后会设置 TCP 内存压力标志，减小发送缓冲区的上限，睡眠等待内存。
             */
            if (!sk_page_frag_refill(sk, pfrag))
                goto wait_for_memory;

            /* 判断能否往最后一个分页追加数据 */
            if (!skb_can_coalesce(skb, i, pfrag->page, pfrag->offset)) {
                /*
                 * 不能追加时，检查分页数是否达到了上限，或者网卡不支持分散聚合。
                 * 如果是的话，就为此 skb 设置 PSH 标志，尽快地发送出去。
                 * 然后跳转到 new_segment 处申请新的skb，来继续填装数据。
                 */
                if (i == sysctl_max_skb_frags || !sg) {
                    tcp_mark_push(tp, skb);
                    goto new_segment;
                }
                merge = false;
            }

            copy = min_t(int, copy, pfrag->size - pfrag->offset);

            if (!sk_wmem_schedule(sk, copy)) /* 从系统层面判断发送缓存的申请是否合法 */
                goto wait_for_memory;

            /*
             * 拷贝 msg->msg_iter 的数据到 skb 的分片.
             * 更新 skb 的长度字段，更新 sock 的发送队列大小和预分配缓存。
             */
            err = skb_copy_to_page_nocache(sk, &msg->msg_iter, skb, pfrag->page,
                                           pfrag->offset, copy);
            if (err)
                goto do_error;

            /* Update the skb. */
            if (merge) {
                // skb_shinfo(skb)->frags[i-1]->size += copy;
                skb_frag_size_add(&skb_shinfo(skb)->frags[i - 1], copy);
            } else {
                skb_fill_page_desc(skb, i, pfrag->page, pfrag->offset, copy);
                get_page(pfrag->page);
            }
            pfrag->offset += copy;
        }

        /* 如果这是第一次拷贝，取消PSH标志 */
        if (!copied)
            TCP_SKB_CB(skb)->tcp_flags &= ~TCPHDR_PSH;

        tp->write_seq += copy;
        TCP_SKB_CB(skb)->end_seq += copy;
        //TCP_SKB_CB(skb)->tcp_gso_segs = 0;
        tcp_skb_pcount_set(skb, 0);

        copied += copy;
        //没有数据要发送, 就设置时间戳, 退出
        if (!msg_data_left(msg)) {
            tcp_tx_timestamp(sk, skb);
            goto out;
        }

        if (skb->len < max || (flags & MSG_OOB) || unlikely(tp->repair))
            continue;

        /* 如果需要设置PSH标志 */

        if (forced_push(tp)) { //after(tp->write_seq, tp->pushed_seq + (tp->max_window >> 1))
            //TCP_SKB_CB(skb)->tcp_flags |= TCPHDR_PSH;
            //tp->pushed_seq = tp->write_seq
            tcp_mark_push(tp, skb);
            /* 尽可能的将发送队列中的 skb 发送出去，禁用 nalge */
            __tcp_push_pending_frames(sk, mss_now, TCP_NAGLE_PUSH);
        } else if (skb == tcp_send_head(sk))
            /* 将发送队列中的 skb 发送出去，禁用 nalge */
            tcp_push_one(sk, mss_now); /* 只发送一个skb */
        continue;

wait_for_sndbuf:
        /* 设置同步发送时，发送缓存不够的标志 */
        set_bit(SOCK_NOSPACE, &sk->sk_socket->flags);
wait_for_memory:
        if (copied)
            /* 如果已经有数据复制到发送队列了，就尝试立即发送 */
            tcp_push(sk, flags & ~MSG_MORE, mss_now, TCP_NAGLE_PUSH, size_goal);

        /* 分两种情况：
         * 1. sock的发送缓存不足。等待 sock 有发送缓存可写事件，或者超时。
         * 2. TCP层内存不足，等待 2~202ms 之间的一个随机时间。
         */
        err = sk_stream_wait_memory(sk, &timeo);
        if (err != 0)
            goto do_error;

        mss_now = tcp_send_mss(sk, &size_goal, flags);
    }

out:
    if (copied)
        /* 如果已经有数据复制到发送队列了，就尝试立即发送 */
        tcp_push(sk, flags, mss_now, tp->nonagle, size_goal);
out_nopush:
    release_sock(sk);
    return copied + copied_syn;

do_fault:
    if (!skb->len) { /* 如果skb没有负荷 */
        tcp_unlink_write_queue(skb, sk); /* 把skb从发送队列中删除 */
        /* It is the one place in all of TCP, except connection
         * reset, where we can be unlinking the send_head.
         */
        tcp_check_send_head(sk, skb);  /* 是否要撤销sk->sk_send_head */
        sk_wmem_free_skb(sk, skb);     /* 更新发送队列的大小和预分配缓存，释放skb */
    }

do_error:
    if (copied + copied_syn)
        goto out;
out_err:
    err = sk_stream_error(sk, flags, err);
    /* make sure we wake any epoll edge trigger waiter */
    if (unlikely(skb_queue_len(&sk->sk_write_queue) == 0 && err == -EAGAIN))
        sk->sk_write_space(sk);
    release_sock(sk);
    return err;
}
EXPORT_SYMBOL(tcp_sendmsg);


/* This routine writes packets to the network.  It advances the
 * send_head.  This happens as incoming acks open up the remote
 * window for us.
 *
 * LARGESEND note: !tcp_urg_mode is overkill, only frames between
 * snd_up-64k-mss .. snd_up cannot be large. However, taking into
 * account rare use of URG, this is not a big flaw.
 *
 * Send at most one packet when push_one > 0. Temporarily ignore
 * cwnd limit to force at most one packet out when push_one == 2.

 * Returns true, if no segments are in flight and we have queued segments,
 * but cannot send anything now because of SWS or another problem.
 */
static bool tcp_write_xmit(struct sock *sk, unsigned int mss_now, int nonagle,
			   int push_one, gfp_t gfp)
{
	struct tcp_sock *tp = tcp_sk(sk);
	struct sk_buff *skb;
	unsigned int tso_segs, sent_pkts;
	int cwnd_quota;
	int result;
	bool is_cwnd_limited = false;
	u32 max_segs;

	sent_pkts = 0;

	if (!push_one) {
		/* Do MTU probing. */
		result = tcp_mtu_probe(sk);
		if (!result) {
			return false;
		} else if (result > 0) {
			sent_pkts = 1;
		}
	}

    /*
     * bytes = min(sk->sk_pacing_rate >> 10, sk->sk_gso_max_size - 1 - MAX_TCP_HEADER);
     * 返回 min(max(bytes / mss_now, sysctl_tcp_min_tso_segs), sk->sk_gso_max_segs)
     */
	max_segs = tcp_tso_autosize(sk, mss_now);
    //如果 sk->sk_write_queue 队列中有数据, 就一直循环, 将数据发送出去.
	while ((skb = tcp_send_head(sk))) {
		unsigned int limit;

        /*
         * 如果 skb->len < mss_now, 那么就一个分片
         * 如果 skb->len > mss_now, 那么就一个 skb->len / mss_now 个分片
         */
		tso_segs = tcp_init_tso_segs(skb, mss_now);
		BUG_ON(!tso_segs);

		if (unlikely(tp->repair) && tp->repair_queue == TCP_SEND_QUEUE) {
			/* "skb_mstamp" is used as a start point for the retransmit timer */
			skb_mstamp_get(&skb->skb_mstamp);
			goto repair; /* Skip network transmission */
		}

        /*
         * 检查正在网络中的数据是否超过拥塞窗口
         *
         * 如果当前在网络中传输的数据 len 满足 0.5*snd_cwnd < len < snd_cwnd,返回 snd_cwnd-len
         * 如果当前在网络中传输的数据大于一个发送窗口长度, 返回 0
         * 如果当前在网络中传输的数据 len 满足 len < 0.5*snd_cwnd, 返回 0.5*snd_cwnd
         */
		cwnd_quota = tcp_cwnd_test(tp, skb);
        //如果当前在网络中传输的数据大于一个发送窗口长度, 退出循环
		if (!cwnd_quota) {
			if (push_one == 2)
				/* Force out a loss probe pkt. */
				cwnd_quota = 1;
			else
				break;
		}

        //待发送的 skb 的结束序列是否在发送窗口之内.
		if (unlikely(!tcp_snd_wnd_test(tp, skb, mss_now)))
			break;

		if (tso_segs == 1) {
            //如果 Nagle 算法不能启用的话(包可以发送), 退出循环
			if (unlikely(!tcp_nagle_test(tp, skb, mss_now,
						     (tcp_skb_is_last(sk, skb) ?
						      nonagle : TCP_NAGLE_PUSH))))
				break;
		} else {
            //应该延迟发送的话, 退出循环
			if (!push_one &&
			    tcp_tso_should_defer(sk, skb, &is_cwnd_limited,
						 max_segs))
				break;
		}

		limit = mss_now;
		if (tso_segs > 1 && !tcp_urg_mode(tp))
            /*
             * 发送窗口大小: window = tp->snd_una + tp->snd_wnd - TCP_SKB_CB(skb)->seq;
             * max_len = mss_now * max_segs
             * 返回拥塞窗口和滑动窗口的最小值 min(skb->len, window, max_len)
             */
			limit = tcp_mss_split_point(sk, skb, mss_now,
						    min_t(unsigned int,
							  cwnd_quota,
							  max_segs),
						    nonagle);

		if (skb->len > limit &&
		    unlikely(tso_fragment(sk, skb, limit, mss_now, gfp)))
			break;

		/* TCP Small Queues :
		 * Control number of packets in qdisc/devices to two packets / or ~1 ms.
		 * This allows for :
		 *  - better RTT estimation and ACK scheduling
		 *  - faster recovery
		 *  - high rates
		 * Alas, some drivers / subsystems require a fair amount
		 * of queued bytes to ensure line rate.
		 * One example is wifi aggregation (802.11 AMPDU)
		 */
		limit = max(2 * skb->truesize, sk->sk_pacing_rate >> 10);
		limit = min_t(u32, limit, sysctl_tcp_limit_output_bytes);

		if (atomic_read(&sk->sk_wmem_alloc) > limit) {
			set_bit(TSQ_THROTTLED, &tp->tsq_flags);
			/* It is possible TX completion already happened
			 * before we set TSQ_THROTTLED, so we must
			 * test again the condition.
			 */
			smp_mb__after_atomic();
			if (atomic_read(&sk->sk_wmem_alloc) > limit)
				break;
		}

        //TODO
		if (unlikely(tcp_transmit_skb(sk, skb, 1, gfp)))
			break;

repair:
		/* Advance the send_head.  This one is sent out.
		 * This call will increment packets_out.
		 */
		tcp_event_new_data_sent(sk, skb);

		tcp_minshall_update(tp, mss_now, skb);
		sent_pkts += tcp_skb_pcount(skb);

		if (push_one)
			break;
	}

	if (likely(sent_pkts)) {
		if (tcp_in_cwnd_reduction(sk))
			tp->prr_out += sent_pkts;

		/* Send one loss probe per tail loss episode. */
		if (push_one != 2)
			tcp_schedule_loss_probe(sk);
		is_cwnd_limited |= (tcp_packets_in_flight(tp) >= tp->snd_cwnd);
		tcp_cwnd_validate(sk, is_cwnd_limited);
		return false;
	}
	return !tp->packets_out && tcp_send_head(sk);
}

static int tcp_transmit_skb(struct sock *sk, struct sk_buff *skb, int clone_it,
			    gfp_t gfp_mask)
{
	const struct inet_connection_sock *icsk = inet_csk(sk);
	struct inet_sock *inet;
	struct tcp_sock *tp;
	struct tcp_skb_cb *tcb;
	struct tcp_out_options opts;
	unsigned int tcp_options_size, tcp_header_size;
	struct tcp_md5sig_key *md5;
	struct tcphdr *th;
	int err;

	BUG_ON(!skb || !tcp_skb_pcount(skb));

	if (clone_it) {
		skb_mstamp_get(&skb->skb_mstamp);

		if (unlikely(skb_cloned(skb)))
			skb = pskb_copy(skb, gfp_mask);
		else
			skb = skb_clone(skb, gfp_mask);
		if (unlikely(!skb))
			return -ENOBUFS;
	}

	inet = inet_sk(sk);
	tp = tcp_sk(sk);
	tcb = TCP_SKB_CB(skb);
	memset(&opts, 0, sizeof(opts));

    //设置 tcp 选项
	if (unlikely(tcb->tcp_flags & TCPHDR_SYN))
		tcp_options_size = tcp_syn_options(sk, skb, &opts, &md5);
	else
		tcp_options_size = tcp_established_options(sk, skb, &opts,
							   &md5);
    //计算头长度
	tcp_header_size = tcp_options_size + sizeof(struct tcphdr);

	/* if no packet is in qdisc/device queue, then allow XPS to select
	 * another queue. We can be called from tcp_tsq_handler()
	 * which holds one reference to sk_wmem_alloc.
	 *
	 * TODO: Ideally, in-flight pure ACK packets should not matter here.
	 * One way to get this would be to set skb->truesize = 2 on them.
	 */
    //设置 skb 相关字段
	skb->ooo_okay = sk_wmem_alloc_get(sk) < SKB_TRUESIZE(1);

	skb_push(skb, tcp_header_size);
	skb_reset_transport_header(skb);

    /*
     * skb->destructor(skb)
     * skb->destructor = NULL
     * skb->sk		= NULL;
     */
	skb_orphan(skb);
	skb->sk = sk;
	skb->destructor = skb_is_tcp_pure_ack(skb) ? sock_wfree : tcp_wfree;
	skb_set_hash_from_sk(skb, sk);
	atomic_add(skb->truesize, &sk->sk_wmem_alloc);

	/* Build TCP header and checksum it. */
    //设置 skb 对应 tcp 相关字段
	skb->ooo_okay = sk_wmem_alloc_get(sk) < SKB_TRUESIZE(1);
	th = tcp_hdr(skb);
	th->source		= inet->inet_sport;
	th->dest		= inet->inet_dport;
	th->seq			= htonl(tcb->seq);
	th->ack_seq		= htonl(tp->rcv_nxt);
	*(((__be16 *)th) + 6)	= htons(((tcp_header_size >> 2) << 12) |
					tcb->tcp_flags);

	if (unlikely(tcb->tcp_flags & TCPHDR_SYN)) {
		/* RFC1323: The window in SYN & SYN/ACK segments
		 * is never scaled.
		 */
		th->window	= htons(min(tp->rcv_wnd, 65535U));
	} else {
		th->window	= htons(tcp_select_window(sk));
	}
	th->check		= 0;
	th->urg_ptr		= 0;

	/* The urg_mode check is necessary during a below snd_una win probe */
	if (unlikely(tcp_urg_mode(tp) && before(tcb->seq, tp->snd_up))) {
		if (before(tp->snd_up, tcb->seq + 0x10000)) {
			th->urg_ptr = htons(tp->snd_up - tcb->seq);
			th->urg = 1;
		} else if (after(tcb->seq + 0xFFFF, tp->snd_nxt)) {
			th->urg_ptr = htons(0xFFFF);
			th->urg = 1;
		}
	}

	tcp_options_write((__be32 *)(th + 1), tp, &opts);
	skb_shinfo(skb)->gso_type = sk->sk_gso_type;
	if (likely((tcb->tcp_flags & TCPHDR_SYN) == 0))
		tcp_ecn_send(sk, skb, tcp_header_size);

#ifdef CONFIG_TCP_MD5SIG
	/* Calculate the MD5 hash, as we have all we need now */
	if (md5) {
		sk_nocaps_add(sk, NETIF_F_GSO_MASK);
		tp->af_specific->calc_md5_hash(opts.hash_location,
					       md5, sk, skb);
	}
#endif

    //调用 tcp_v4_send_check
	icsk->icsk_af_ops->send_check(sk, skb);

	if (likely(tcb->tcp_flags & TCPHDR_ACK))
		tcp_event_ack_sent(sk, tcp_skb_pcount(skb));

	if (skb->len != tcp_header_size) {
		tcp_event_data_sent(tp, sk);
		tp->data_segs_out += tcp_skb_pcount(skb);
	}

	if (after(tcb->end_seq, tp->snd_nxt) || tcb->seq == tcb->end_seq)
		TCP_ADD_STATS(sock_net(sk), TCP_MIB_OUTSEGS,
			      tcp_skb_pcount(skb));

	tp->segs_out += tcp_skb_pcount(skb);
	/* OK, its time to fill skb_shinfo(skb)->gso_{segs|size} */
	skb_shinfo(skb)->gso_segs = tcp_skb_pcount(skb);
	skb_shinfo(skb)->gso_size = tcp_skb_mss(skb);

	/* Our usage of tstamp should remain private */
	skb->tstamp.tv64 = 0;

	/* Cleanup our debris for IP stacks */
	memset(skb->cb, 0, max(sizeof(struct inet_skb_parm),
			       sizeof(struct inet6_skb_parm)));

    //调用 ip_queue_xmit(sk, skb, inet->cork.fl)
	err = icsk->icsk_af_ops->queue_xmit(sk, skb, &inet->cork.fl);

	if (likely(err <= 0))
		return err;

	tcp_enter_cwr(sk);

    //err == NET_XMIT_CN ? 0 : (e)
	return net_xmit_eval(err);
}

static void tcp_push(struct sock *sk, int flags, int mss_now,
                     int nonagle, int size_goal)
{
    struct tcp_sock *tp = tcp_sk(sk);
    struct sk_buff *skb;

    //如果 sk->sk_send_head 为空, 即没有数据要发送
    if (!tcp_send_head(sk))
        return;

    //获取 sk->sk_write_queue 最后一个 skb
    skb = tcp_write_queue_tail(sk);
    /* 如果接下来没有更多的数据需要发送，或者距离上次PUSH后又有比较多的数据，
     * 那么就需要设置PSH标志，让接收端马上把接收缓存中的数据提交给应用程序。
     */
    if (!(flags & MSG_MORE) || forced_push(tp))
        /*
         * TCP_SKB_CB(skb)->tcp_flags |= TCPHDR_PSH
         * tp->pushed_seq = tp->write_seq
         */
        tcp_mark_push(tp, skb);

    /* if (flags & MSG_OOB) tp->snd_up = tp->write_seq */
    tcp_mark_urg(tp, flags);

    /* 必须满足如下全部条件: 返回 true
     * 1. skb 数据小于 size_goal
     * 2. sysctl_tcp_autocorking != 0
     * 3. sk->sk_write_queue 不为空, 即后续还有数据
     * 4. sk->sk_wmem_alloc > skb->truesize
     *
     * 总结起来就是,
     * 1. MSS 大于skb 长度;
     * 2. 用户配置可以将小数据包合并成大数据包
     * 3. 发送队列还有数据要发送
     * 4. 发送可用内存大于 skb 长度
     */
    if (tcp_should_autocork(sk, skb, size_goal)) {

        /* avoid atomic op if TSQ_THROTTLED bit is already set */
        /* 设置阻塞标志位, 设置 TSQ_THROTTLED 的标志的作用就是
         * 将 sk 加入 per_cpu 队列 tsq_tasklet
         */
        if (!test_bit(TSQ_THROTTLED, &tp->tsq_flags)) {
            NET_INC_STATS(sock_net(sk), LINUX_MIB_TCPAUTOCORKING);
            set_bit(TSQ_THROTTLED, &tp->tsq_flags);
        }
        /* It is possible TX completion already happened
         * before we set TSQ_THROTTLED.
         */
        if (atomic_read(&sk->sk_wmem_alloc) > skb->truesize)
            return;
    }

    /* 如果之后还有更多的数据，那么使用 TCP CORK，显式地阻塞发送 */
    if (flags & MSG_MORE)
        nonagle = TCP_NAGLE_CORK;

    /* 尽可能地把发送队列中的skb发送出去。
     * 如果发送失败，检查是否需要启动零窗口探测定时器。
     */
    __tcp_push_pending_frames(sk, mss_now, nonagle);
}

```



