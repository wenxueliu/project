

1. 应用程序调用 read、recv 等方法时，socket套接字可以设置为阻塞或者非阻塞，这两种方式是如何工作的？
2. 若socket为默认的阻塞套接字，此时recv方法传入的len参数，是表示必须超时（SO_RCVTIMEO）或者接收到len长度的消息，recv方法才会返回吗？
3. socket 上可以设置一个属性叫做 SO_RCVLOWAT, 它会与 len 产生什么样的交集, 又是决定 recv 等接收方法什么时候返回？
4. 应用程序开始收取TCP消息，与程序所在的机器网卡上接收到网络里发来的TCP消息，这是两个独立的流程。它们之间是如何互相影响的？例如，应用程序正在收取消息时，内核通过网卡又在这条TCP连接上收到消息时，究竟是如何处理的？若应用程序没有调用read或者recv时，内核收到TCP连接上的消息后又是怎样处理的？
5. recv 这样的接收方法还可以传入各种flags，例如MSG_WAITALL、MSG_PEEK、MSG_TRUNK等等。它们是如何工作的？
5、1 个 socket 套接字可能被多个进程在使用, 出现并发访问时, 内核是怎么处理这种状况的？
6、linux 的 sysctl 系统参数中，有类似 tcp_low_latency 这样的开关，默认为 0 或者配置为 1 时是如何影响TCP消息处理流程的？


## 术语

* 数据包: 对应内核的 skb, 其中四个队列中的每个元素都是一个个数据包(skb)


## 接收数据

###四个队列

* packets in flight

	tp->packets_out - (tp->sacked_out + tp->lost_out) + tp->retrans_out;

### receive_queue

该队列中的数据不包含 tcp 报文头

正常情况下, 只有当前 sock 没有被占用(即用户调用 recv)时, 才能接受新包, 新的包会加入 receive_queue.

此外

### prequeue

如果 tcp_v4_rcv 收包时, 没有用户没有占用 sock (调用 recv)时, 则包加入 prequeue

该队列主要时决定在没有用户没有占用 sock (调用 recv)时, 包的处理策略, 加入
prequeue 之后唤醒睡眠的进程, 还是加入 sk_receive_queue

如果进程在读包的时候, 没有收到足够的数据睡眠时, 新到的数据会加入 prequeue,
如果 prequeue 队列的数据为 1, 就中断唤醒睡眠的进程, 请求其读数据, 否则, 直到
prequeue 队列数据大于 sk_rcvbuf 时, 将其拷贝到 sk_receive_queue 或直接发送给
用户态.

如果用户没有调用 recv, 那么 prequeue 队列中的数据很快就会满了, 这时会将
prequeue 的数据拷贝到 receive_queue(如果需要会发送应答给对端)并发送信号唤醒睡眠的进程.


### backlog

如果 tcp_v4_rcv 收包时, 有用户在占用 sock(调用 recv), 则包加入 backlog.
backlog 队列的存在主要的目的时当前 sock 被用户使用时(即调用 recv), 新的包不能加入
sk_receive_queue, 因此新增加了 backlog, 当 recv 收包执行完之后, 会将 backlog 队列
的包移动到 sk_receive_queue

### out_of_order_queue

收到的包不是下一个待接受的数据包, 就会加入该队列

## recv 的实现

假设:

1. MSG_TRUNC, MSG_PEEK 没有设置. 关于该选项后面会详细讨论
2. sysctl_tcp_low_latency 为 0, 也是系统默认值. 关于该选项后面会详细讨论
3. 不考虑 tcp_repair
4. 不考虑 busy loop

步骤

0. 如果收到紧急数据, 跳到步骤 3
1. 遍历 receive_queue 队列中数据 skb,

1.1. 如果找到的 skb->seq 大于下一个要拷贝到用户态的数据 seq, 到步骤 3

1.2. 如果找到的 skb 包含用户态下一个待收的数据 seq, 将数据包拷贝到用户态,

    1) 如果当前 skb 包含数据长度大于 recv 接收的长度 len, 只拷贝需要的部分到用户态, 跳到步骤 3.
    2) 如果当前 skb 包含数据长度小于等于 recv 接受数据 len, 将该 skb 内容拷贝到用户态:
        如果 skb 包含 FIN 标志, 该 skb 从 receive_queue 中删除, 跳到步骤 3
        否则将该 skb 从 receive_queue 中删除, 跳到步骤 1, 继续

2. 如果遍历 receive_queue 没有收到 recv 待收的数据长度:

2.1 如果拷贝给用户态的数据包长度大于等于(min(len, sk->sk_rcvlowat)), 并且 sk->backlog 也是空的, 跳到步骤 3

2.2 如果拷贝给用户态的数据包长度大于等于(min(len, sk->sk_rcvlowat)), 并且 sk->backlog 不为空, 跳到步骤 4

2.3 如果拷贝给用户态的数据包长度小于(min(len, sk->sk_rcvlowat)),  跳到步骤 4

3. 根据条件发送 ack 给对端, 释放数据包内存之后, 返回已经拷贝到用户态的数据长度.

4 辅助步骤

4.1 遇到异常, 跳到步骤 3
4.2 决定是否发送 ack 给对端, 如果需要发送 ack 给对端
4.3 如果 prequeue 队列不为空, 遍历 prequeue 队列, 如果是待收的数据将其直接拷贝到用户态, 如果不是, 就加入 receive_queue, 跳到步骤 5
4.4 如果 prequeue 队列为空:
    4.4.1 如果拷贝的数据长度已经够 len:
        4.4.1.1 如果 backlog 队列不为空, 遍历 backlog 队列, 如果是待收的数据将其直接拷贝到用户态, 如果不是, 就加入 receive_queue, 之后跳到步骤 4
         4.4.1.2 如果 backlog 队列为空, 释放 skb, 之后跳到步骤 5
    4.4.2 如果拷贝的数据长度不够 len, 当前进程阻塞. 等待被唤醒(sk->sk_receive_queue 不为空, 或超时, 或信号), 之后跳到步骤 1

5. 如果拷贝到用户态的数据没有够 len, 之后跳到步骤 1
   如果拷贝到用户态的数据已经够 len, 之后跳到步骤 3

异常包括:

    1. sk->flags 包含 SOCK_DONE
    2. 发生错误
    3. shutdown 关闭了 socket
    4. 处于 TCP_CLOSE
    5. 非阻塞
    6. 收到信号

recv 退出条件:

1. 遇到错误
2. 收到足够长的数据
3. 收到紧急数据

例子:

1. recv 待收的数据包在 receive_queue 中一个数据包中
2. recv 待收的数据包在 receive_queue 中多个数据包中
3. recv 待收的数据包只有部分在 receive_queue 中, 但 prequeue 包含余下的包
4. recv 待收的数据包只有部分在 receive_queue 中, 但 prequeue 也没有包含余下的包
5. recv 待收的数据包没有任何数据在 receive_queue 中, 但 prequeue 包含余下的包
6. recv 待收的数据包没有任何数据在 receive_queue 中, 但 prequeue 也没有包含余下的包
7. receive_queue 中包含 FIN 数据数据包

该队列满的条件:

    sk->sk_backlog.len + sk->sk_rmem_alloc > sk->sk_rcvbuf + sk->sk_sndbuf

只有满足如下任意条件, 在收到不足 len 的数据包时, 仍然可能返回:

1. 发生错误
2. shutdown 关闭了 socket
3. 处于 TCP_CLOSE
4. 非阻塞
5. 收到信号

## recv 上半部分

SYSCALL_DEFINE6(recvfrom, int, fd, void __user *, ubuf, size_t, size, unsigned int, flags, struct sockaddr __user *, addr, int __user *, addr_len)
    import_single_range(READ, ubuf, size, &iov, &msg.msg_iter)
    sock = sockfd_lookup_light(fd, &err, &fput_needed)
    msg.msg_control = NULL;
    msg.msg_controllen = 0;
    /* Save some cycles and don't copy the address if not needed */
    msg.msg_name = addr ? (struct sockaddr *)&address : NULL;
    /* We assume all kernel code knows the size of sockaddr_storage */
    msg.msg_namelen = 0;
    msg.msg_iocb = NULL;
    if (sock->file->f_flags & O_NONBLOCK)
            flags |= MSG_DONTWAIT;
    sock_recvmsg(sock, &msg, iov_iter_count(&msg.msg_iter), flags);
        security_socket_recvmsg(sock, msg, size, flags)
        sock_recvmsg_nosec(sock, msg, size, flags)
            sock->ops->recvmsg(sock, msg, size, flags)
            SOCK_STREAM
                inet_recvmsg(sock, msg, size, flags)
            SOCK_DGRAM
                inet_recvmsg(sock, msg, size, flags)
            SOCK_RAW
                inet_recvmsg(sock, msg, size, flags)
    if addr != NULL:
        move_addr_to_user(&address, msg.msg_namelen, addr, addr_len);
    fput_light(sock->file, fput_needed)

inet_recvmsg(sock, msg, size, flags)
    sock_rps_record_flow(sk); //rps_sock_flow_table->ents[sk->sk_rxhash] = raw_smp_processor_id()
    sk->sk_prot->recvmsg(sk, msg, size, flags & MSG_DONTWAIT, flags & ~MSG_DONTWAIT, &addr_len)
    if RAW:
        raw_recvmsg(sock, msg, size, flags)
    if TCP:
        tcp_recvmsg(sock, msg, size, flags)
    if UDP:
        udp_recvmsg(sock, msg, size, flags)
    if ICMP:
        ping_recvmsg(sock, msg, size, flags)
    msg->msg_namelen = addr_len

1. 找到 fd 对应的 file(current->files->fdt[fd])
2. 初始化消息头
3. 如果地址不为空, 把套接字地址从用户空间拷贝到内核空间
4. 设置发送标志(是否为非阻塞).
5. 调用对应协议的 recvmsg 函数发送数据.


## 附录

int sock_recvmsg(struct socket *sock, struct msghdr *msg, size_t size,
                 int flags)
{
        int err = security_socket_recvmsg(sock, msg, size, flags);

        return err ?: sock_recvmsg_nosec(sock, msg, size, flags);
}
EXPORT_SYMBOL(sock_recvmsg);

/*
 *      Receive a frame from the socket and optionally record the address of the
 *      sender. We verify the buffers are writable and if needed move the
 *      sender address from kernel to user space.
 */

SYSCALL_DEFINE6(recvfrom, int, fd, void __user *, ubuf, size_t, size,
                unsigned int, flags, struct sockaddr __user *, addr,
                int __user *, addr_len)
{
        struct socket *sock;
        struct iovec iov;
        struct msghdr msg;
        struct sockaddr_storage address;
        int err, err2;
        int fput_needed;

        err = import_single_range(READ, ubuf, size, &iov, &msg.msg_iter);
        if (unlikely(err))
                return err;
        sock = sockfd_lookup_light(fd, &err, &fput_needed);
        if (!sock)
                goto out;

        msg.msg_control = NULL;
        msg.msg_controllen = 0;
        /* Save some cycles and don't copy the address if not needed */
        msg.msg_name = addr ? (struct sockaddr *)&address : NULL;
        /* We assume all kernel code knows the size of sockaddr_storage */
        msg.msg_namelen = 0;
        msg.msg_iocb = NULL;
        if (sock->file->f_flags & O_NONBLOCK)
                flags |= MSG_DONTWAIT;
        err = sock_recvmsg(sock, &msg, iov_iter_count(&msg.msg_iter), flags);

        if (err >= 0 && addr != NULL) {
                err2 = move_addr_to_user(&address,
                                         msg.msg_namelen, addr, addr_len);
                if (err2 < 0)
                        err = err2;
        }

        fput_light(sock->file, fput_needed);
out:
        return err;
}

/*
 *      Receive a datagram from a socket.
 */

SYSCALL_DEFINE4(recv, int, fd, void __user *, ubuf, size_t, size,
                unsigned int, flags)
{
        return sys_recvfrom(fd, ubuf, size, flags, NULL, NULL);
}

/*
 *      Set a socket option. Because we don't know the option lengths we have
 *      to pass the user mode parameter for the protocols to sort out.
 */

int tcp_recvmsg(struct sock *sk, struct msghdr *msg, size_t len, int nonblock,
                int flags, int *addr_len)
{
    struct tcp_sock *tp = tcp_sk(sk);
    //已经拷贝到用户态数据的长度
    int copied = 0;
    //开启 MSG_PEEK 时, 收到的数据包的 seq.
    u32 peek_seq;
    u32 *seq;
    unsigned long used;
    int err;
    int target;             /* Read at least this many bytes */
    long timeo;
    struct task_struct *user_recv = NULL;
    struct sk_buff *skb, *last;
    u32 urg_hole = 0;

    if (unlikely(flags & MSG_ERRQUEUE))
        return inet_recv_error(sk, msg, len, addr_len);

    if (sk_can_busy_loop(sk) && skb_queue_empty(&sk->sk_receive_queue) &&
        (sk->sk_state == TCP_ESTABLISHED))
        sk_busy_loop(sk, nonblock);

    //锁住 socket，防止多进程并发访问 TCP 连接，告知软中断目前 socket 在进程上下文中
    lock_sock(sk);

    err = -ENOTCONN;
    if (sk->sk_state == TCP_LISTEN)
        goto out;

    //如果 socket 是阻塞套接字, 则取出 SO_RCVTIMEO 作为读超时时间; 若为非阻塞, 则 timeo 为0.
    timeo = sock_rcvtimeo(sk, nonblock);

    /* Urgent data needs to be handled specially. */
    //MSG_OOB 表示可以接受 out-of-band 的数据
    if (flags & MSG_OOB)
        goto recv_urg;

    if (unlikely(tp->repair)) {
        err = -EPERM;
        if (!(flags & MSG_PEEK))
            goto out;

        if (tp->repair_queue == TCP_SEND_QUEUE)
            goto recv_sndq;

        err = -EINVAL;
        if (tp->repair_queue == TCP_NO_QUEUE)
            goto out;

        /* 'common' recv queue MSG_PEEK-ing */
    }

    /*
     * 下一个拷贝到用户态的序列号
     * 注意：seq的定义为u32 *seq; 它是32位指针. 为何? 因为下面每向用户态内存拷贝后，会更新seq的值，这时就会直接更改套接字上的copied_seq
     */
    seq = &tp->copied_seq;
    //当 flags 参数有 MSG_PEEK 标志位时, 意味着这次拷贝的内容不会被释放, 当再次读取 socket 时(比如另一个进程)还能再次读到
    if (flags & MSG_PEEK) {
        /* 因为 seq 指向临时变量, 修改 seq 只是修改临时变量 peek_seq, 所以不会更新 copied_seq
         * 当然, 下面会看到也不会删除报文, 不会从 receive 队列中移除报文
         */
        peek_seq = tp->copied_seq;
        seq = &peek_seq;
    }

    /* 如果 flags 包含 MSG_WAITALL, 则意味着必须等到读取到 len 长度的消息才能返回(除了收到信号,错误,断开连接等异常), 正常情况下返回 len;
     * 否则 返回 min(len, sk->sk_rcvlowat);
     * 如果 len == sk->sk_rcvlowat == 0, 那么, 返回 1;
     */
    target = sock_rcvlowat(sk, flags & MSG_WAITALL, len);

    do {
        u32 offset;

        /* Are we at urgent data? Stop if we have read anything or have SIGURG pending. */
        /*
         * 当有紧急数据需要收的时候, 如果 copied 不为 0, 立即收数据, 如果
         * copied 为 0, 检查是否收到 SIGURG 信号, 如果是, copied 为错误代码.
         */
        if (tp->urg_data && tp->urg_seq == *seq) {
            if (copied)
                break;
            if (signal_pending(current)) {
                copied = timeo ? sock_intr_errno(timeo) : -EAGAIN;
                break;
            }
        }

        /* Next get a buffer. */

        /*
         * last 指向 sk->sk_receive_queue 队列尾, 即第一个元素的前一个元素.
         * last = sk->sk_receive_queue->prev
         */
        last = skb_peek_tail(&sk->sk_receive_queue);
        /*
         * 从 sk->sk_receive_queue 头开始遍历
         * for (skb = (sk->sk_receive_queue)->next;
         *      skb != (struct * sk_buff *)(sk->sk_receive_queue);
         *      skb = skb->next)
         */
        skb_queue_walk(&sk->sk_receive_queue, skb) {
            last = skb;
            /* Now that we have two receive queues this
             * shouldn't happen.
             */
            //保证收到的 skb->seq 必须时已经拷贝到用户态 seq 之前.
            if (WARN(before(*seq, TCP_SKB_CB(skb)->seq),
                     "recvmsg bug: copied %X seq %X rcvnxt %X fl %X\n",
                     *seq, TCP_SKB_CB(skb)->seq, tp->rcv_nxt,
                     flags))
                    break;

            //offset是待拷贝序号在当前这个报文中的偏移量, 只有因为用户内存不足以接收完 1 个报文时才为非 0
            offset = *seq - TCP_SKB_CB(skb)->seq;
            //有些时候，三次握手的SYN包也会携带消息内容的，此时seq是多出1的（SYN占1个序号），所以offset减1
            if (unlikely(TCP_SKB_CB(skb)->tcp_flags & TCPHDR_SYN)) {
                    pr_err_once("%s: found a SYN, please report !\n", __func__);
                    offset--;
            }
            /*
             * 如果下一个读的序列号在当前 skb, 跳转到找到 skb 处, 收包
             */
            if (offset < skb->len)
                    goto found_ok_skb;
            /*
             * 如果当前 skb 包含 FIN, 即该 skb 是最后一个包, 跳转到
             * FIN 处理的地方
             */
            if (TCP_SKB_CB(skb)->tcp_flags & TCPHDR_FIN)
                    goto found_fin_ok;
            WARN(!(flags & MSG_PEEK),
                 "recvmsg bug 2: copied %X seq %X rcvnxt %X fl %X\n",
                 *seq, TCP_SKB_CB(skb)->seq, tp->rcv_nxt, flags);
        }

        /* Well, if we have backlog, try to process it now yet. */

        /*
         * 到此, 表示 sk->sk_receive_queue 没有找到满足条件的包
         * 但是 copied 的数据 已经达到传给用户态的条件,
         * 并且 sk->backlog 为空. 则可以返回用户态了
         */
        if (copied >= target && !sk->sk_backlog.tail)
            break;

        if (copied) {
            /* 拷贝了部分字节(copied < target), 如果满足如下任一条件
             * 1. 发生错误
             * 2. shutdown 关闭了 socket
             * 3. 处于 TCP_CLOSE
             * 4. 非阻塞
             * 5. 收到信号
             * 直接返回
             */
            if (sk->sk_err ||
                sk->sk_state == TCP_CLOSE ||
                (sk->sk_shutdown & RCV_SHUTDOWN) ||
                !timeo ||
                signal_pending(current))
                    break;
        } else {
            /* 一个字节都没拷贝到, 如果满足如下任一条件
             * 1. sk->flags 包含 SOCK_DONE
             * 2. 发生错误
             * 3. shutdown 关闭了 socket
             * 4. 处于 TCP_CLOSE
             * 5. 非阻塞
             * 6. 收到信号
             * 直接返回
             */
            if (sock_flag(sk, SOCK_DONE))
                break;

            if (sk->sk_err) {
                copied = sock_error(sk);
                break;
            }

            if (sk->sk_shutdown & RCV_SHUTDOWN)
                break;

            if (sk->sk_state == TCP_CLOSE) {
                if (!sock_flag(sk, SOCK_DONE)) {
                        /* This occurs when user tries to read
                         * from never connected socket.
                         */
                        copied = -ENOTCONN;
                        break;
                }
                break;
            }

            if (!timeo) {
                copied = -EAGAIN;
                break;
            }

            if (signal_pending(current)) {
                copied = sock_intr_errno(timeo);
                break;
            }
        }

        //决定是否发送 ack 给对端, 如果需要发送 ack 给对端
        tcp_cleanup_rbuf(sk, copied);

        //tcp_low_latency 默认是 0, 优先将数据包放入 prequeue 队列
        if (!sysctl_tcp_low_latency && tp->ucopy.task == user_recv) {
            /* Install new reader */
            if (!user_recv && !(flags & (MSG_TRUNC | MSG_PEEK))) {
                    user_recv = current;
                    tp->ucopy.task = user_recv;
                    tp->ucopy.msg = msg;
            }

            //待拷贝到用户态的数据的长度
            tp->ucopy.len = len;

            WARN_ON(tp->copied_seq != tp->rcv_nxt &&
                    !(flags & (MSG_PEEK | MSG_TRUNC)));

            /* Ugly... If prequeue is not empty, we have to
             * process it before releasing socket, otherwise
             * order will be broken at second iteration.
             * More elegant solution is required!!!
             *
             * Look: we have the following (pseudo)queues:
             *
             * 1. packets in flight
             * 2. backlog
             * 3. prequeue
             * 4. receive_queue
             *
             * Each queue can be processed only if the next ones
             * are empty. At this point we have empty receive_queue.
             * But prequeue _can_ be not empty after 2nd iteration,
             * when we jumped to start of loop because backlog
             * processing added something to receive_queue.
             * We cannot release_sock(), because backlog contains
             * packets arrived _after_ prequeued ones.
             *
             * Shortly, algorithm is clear --- to process all
             * the queues in order. We could make it more directly,
             * requeueing packets from backlog to prequeue, if
             * is not empty. It is more elegant, but eats cycles,
             * unfortunately.
             */
            /* 由于在 lock 当前 sock 之前数据包都对加入 prequeue
             * 因此, 应该首先检查 prequeue 队列中是否有数据
            if (!skb_queue_empty(&tp->ucopy.prequeue))
                    goto do_prequeue;

            /* __ Set realtime policy in scheduler __ */
        }

        //如果已经拷贝了的字节数超过了最低阀值
        if (copied >= target) {
            /* Do not sleep, just process backlog. */
            /* 如果 backlog 队列不为空, 遍历 backlog 队列:
             * 如果是待收的数据将其直接拷贝到用户态;
             * 如果不是, 就加入 receive_queue
             */
            release_sock(sk);
            lock_sock(sk);
        } else {
            /*
             * 等待 sk->sk_receive_queue 队列尾部收到数据或异常(超时,
             * 收到信号)退出
             *
             * 与 sock_def_readable 相对应.
             */
            sk_wait_data(sk, &timeo, last);
        }

        if (user_recv) {
            int chunk;

            /* __ Restore normal policy in scheduler __ */

            chunk = len - tp->ucopy.len;
            if (chunk != 0) {
                NET_ADD_STATS_USER(sock_net(sk), LINUX_MIB_TCPDIRECTCOPYFROMBACKLOG, chunk);
                len -= chunk;
                copied += chunk;
            }

            /*
             * prequeue 中数据正好时, 下一个要接受的序列, 并且
             * prequeue 数据不为空
             */
            if (tp->rcv_nxt == tp->copied_seq &&
                !skb_queue_empty(&tp->ucopy.prequeue)) {
do_prequeue:
                tcp_prequeue_process(sk);

                chunk = len - tp->ucopy.len;
                //如果有数据直接拷贝到用户态, 则 chunk 不为 0. 因为默认 len = tp->ucopy.len
                if (chunk != 0) {
                    NET_ADD_STATS_USER(sock_net(sk), LINUX_MIB_TCPDIRECTCOPYFROMPREQUEUE, chunk);
                    len -= chunk;
                    copied += chunk;
                }
            }
        }
        if ((flags & MSG_PEEK) &&
            (peek_seq - copied - urg_hole != tp->copied_seq)) {
            net_dbg_ratelimited("TCP(%s:%d): Application bug, race in MSG_PEEK\n",
                                current->comm,
                                task_pid_nr(current));
            peek_seq = tp->copied_seq;
        }
        continue;

    found_ok_skb:
        /* Ok so how much can we use? */
        used = skb->len - offset;
        if (len < used)
            used = len;

        /* Do we have urgent data here? */
        if (tp->urg_data) {
            u32 urg_offset = tp->urg_seq - *seq;
            //紧急数据的偏移在当前 skb 内.
            if (urg_offset < used) {
                if (!urg_offset) {
                    if (!sock_flag(sk, SOCK_URGINLINE)) {
                        ++*seq;
                        urg_hole++;
                        offset++;
                        used--;
                        if (!used)
                            goto skip_copy;
                    }
                } else
                    used = urg_offset;
            }
        }

        /*
         * 这里不需要检查 rcvnxt = skb->seq, 因为 receive_queue 中数据已经按 seq
         * 排序.
         */
        //设置 MSG_TRUNC 将返回真正收到的包的长度而不是指定的 len
        if (!(flags & MSG_TRUNC)) {
            //将数据从内核拷贝到用户
            err = skb_copy_datagram_msg(skb, offset, msg, used);
            if (err) {
                /* Exception. Bailout! */
                if (!copied)
                    copied = -EFAULT;
                break;
            }
        }

        /*
         * 如果 seq 指向 tp->copied_seq 会更新 tp->copied_seq;
         * 如果 seq 指向临时遍历, 就不会更新 tp->copied_seq,
         * 这是有没有设置 MSG_PEEK 的区别所在
         */
        *seq += used;
        //更新已经拷贝到用户数据的长度
        copied += used;
        //更新待拷贝到用户数据的长度
        len -= used;

        tcp_rcv_space_adjust(sk);

skip_copy:
        //紧急数据已经全部接收
        if (tp->urg_data && after(tp->copied_seq, tp->urg_seq)) {
            tp->urg_data = 0;
            tcp_fast_path_check(sk);
        }
        //当前skb 数据还没有接收完
        if (used + offset < skb->len)
            continue;

        if (TCP_SKB_CB(skb)->tcp_flags & TCPHDR_FIN)
            goto found_fin_ok;
        /*
         * 当前 skb 已经接受完, 并且没有指定 MSG_PEEK 标志, 将
         * skb 从 sk->sk_receive_queue 删除, 之后释放 skb 内存
         */
        if (!(flags & MSG_PEEK))
            sk_eat_skb(sk, skb);
        continue;

    found_fin_ok:
        /* Process the FIN. */
        ++*seq;
        /*
         * 当前 skb 已经接受完, 并且没有指定 MSG_PEEK 标志, 将
         * skb 从 sk->sk_receive_queue 删除, 之后释放 skb 内存
         */
        if (!(flags & MSG_PEEK))
            sk_eat_skb(sk, skb);
        break;
    } while (len > 0);

    //这里主要时处理由于有紧急数据导致提前退出循环, 因此需要首先处理 prequeue
    if (user_recv) {
        if (!skb_queue_empty(&tp->ucopy.prequeue)) {
            int chunk;

            tp->ucopy.len = copied > 0 ? len : 0;

            tcp_prequeue_process(sk);

            if (copied > 0 && (chunk = len - tp->ucopy.len) != 0) {
                NET_ADD_STATS_USER(sock_net(sk), LINUX_MIB_TCPDIRECTCOPYFROMPREQUEUE, chunk);
                len -= chunk;
                copied += chunk;
            }
        }

        tp->ucopy.task = NULL;
        tp->ucopy.len = 0;
    }

    /* According to UNIX98, msg_name/msg_namelen are ignored
     * on connected socket. I was just happy when found this 8) --ANK
     */

    /* Clean up data we have read: This will do ACK frames. */
    tcp_cleanup_rbuf(sk, copied);

    /* 如果 backlog 队列不为空, 遍历 backlog 队列:
     * 如果是待收的数据将其直接拷贝到用户态;
     * 如果不是, 就加入 receive_queue
     */
    release_sock(sk);
    return copied;

out:
    /* 如果 backlog 队列不为空, 遍历 backlog 队列:
     * 如果是待收的数据将其直接拷贝到用户态;
     * 如果不是, 就加入 receive_queue
     */
    release_sock(sk);
    return err;

recv_urg:
    err = tcp_recv_urg(sk, msg, len, flags);
    goto out;

recv_sndq:
    err = tcp_peek_sndq(sk, msg, len);
    goto out;
}
EXPORT_SYMBOL(tcp_recvmsg);

1. 如果 flags 包含 MSG_OOB, 表明有乱序数据收到, 立即收数据.
2. 获取下一个要读的 seq.
3. 如果有紧急数据要接受, 立即从 buffer 读数据.
4. 遍历 sk->sk_receive_queue 找到下一个要读的 seq 对应的 skb(该 skb 已经保存在 last 中) 或遇到 FIN 的 skb
5. 如果遍历完 sk->sk_receive_queue, 仍然没有找到期望的 seq. 就等待直到 sk->sk_receive_queue 收到数据或超时
   如果收到正常的数据包:
    1) 将数据拷贝到用户空间, 调整 tcp 头

   如果收到 FIN 数据包:
6. 返回收到的数据长度

/*
 * 遍历 tp->ucopy.prequeue 调用 tcp_v4_do_rcv:
 *      如果是待收的数据将其直接拷贝到用户态, 如果不是, 就加入 receive_queue
 * 注: 该函数返回之后, tp->ucopy.len 会减去直接拷贝到用户态的数据长度
 */
static void tcp_prequeue_process(struct sock *sk)
{
	struct sk_buff *skb;
	struct tcp_sock *tp = tcp_sk(sk);

	NET_INC_STATS_USER(sock_net(sk), LINUX_MIB_TCPPREQUEUED);

	/* RX process wants to run with disabled BHs, though it is not
	 * necessary */
	local_bh_disable();
	while ((skb = __skb_dequeue(&tp->ucopy.prequeue)) != NULL)
		sk_backlog_rcv(sk, skb);
	local_bh_enable();

	/* Clear memory counter. */
	tp->ucopy.memory = 0;
}

/* 如果 backlog 队列不为空, 遍历 backlog 队列,
 * 如果是待收的数据将其直接拷贝到用户态, 如果不是, 就加入 receive_queue,
 * 之后跳到步骤 1
 */
static void __release_sock(struct sock *sk)
	__releases(&sk->sk_lock.slock)
	__acquires(&sk->sk_lock.slock)
{
	struct sk_buff *skb = sk->sk_backlog.head;

	do {
		sk->sk_backlog.head = sk->sk_backlog.tail = NULL;
		bh_unlock_sock(sk);

		do {
			struct sk_buff *next = skb->next;

			prefetch(next);
			WARN_ON_ONCE(skb_dst_is_noref(skb));
			skb->next = NULL;
			sk_backlog_rcv(sk, skb);

			/*
			 * We are in process context here with softirqs
			 * disabled, use cond_resched_softirq() to preempt.
			 * This is safe to do because we've taken the backlog
			 * queue private:
			 */
			cond_resched_softirq();

			skb = next;
		} while (skb != NULL);

		bh_lock_sock(sk);
	} while ((skb = sk->sk_backlog.head) != NULL);

	/*
	 * Doing the zeroing here guarantee we can not loop forever
	 * while a wild producer attempts to flood us.
	 */
	sk->sk_backlog.len = 0;
}

static void tcp_cleanup_rbuf(struct sock *sk, int copied)
{
        struct tcp_sock *tp = tcp_sk(sk);
        bool time_to_ack = false;

        //如果链表不为空, 返回 skb = sk->sk_receive_queue->next, 否则返回 NULL
        struct sk_buff *skb = skb_peek(&sk->sk_receive_queue);

        WARN(skb && !before(tp->copied_seq, TCP_SKB_CB(skb)->end_seq),
             "cleanup rbuf bug: copied %X seq %X rcvnxt %X\n",
             tp->copied_seq, TCP_SKB_CB(skb)->end_seq, tp->rcv_nxt);

        // inet_csk(sk)->icsk_ack.pending & ICSK_ACK_SCHED
        if (inet_csk_ack_scheduled(sk)) {
                const struct inet_connection_sock *icsk = inet_csk(sk);
                   /* Delayed ACKs frequently hit locked sockets during bulk
                    * receive. */
                if (icsk->icsk_ack.blocked ||
                    /* Once-per-two-segments ACK was not sent by tcp_input.c */
                    tp->rcv_nxt - tp->rcv_wup > icsk->icsk_ack.rcv_mss ||
                    /*
                     * If this read emptied read buffer, we send ACK, if
                     * connection is not bidirectional, user drained
                     * receive buffer and there was a small segment
                     * in queue.
                     */
                    (copied > 0 &&
                     ((icsk->icsk_ack.pending & ICSK_ACK_PUSHED2) ||
                      ((icsk->icsk_ack.pending & ICSK_ACK_PUSHED) &&
                       !icsk->icsk_ack.pingpong)) &&
                      !atomic_read(&sk->sk_rmem_alloc)))
                        time_to_ack = true;
        }

        /* We send an ACK if we can now advertise a non-zero window
         * which has been raised "significantly".
         *
         * Even if window raised up to infinity, do not send window open ACK
         * in states, where we will not receive more. It is useless.
         */
        if (copied > 0 && !time_to_ack && !(sk->sk_shutdown & RCV_SHUTDOWN)) {
                __u32 rcv_window_now = tcp_receive_window(tp);

                /* Optimize, __tcp_select_window() is not cheap. */
                if (2*rcv_window_now <= tp->window_clamp) {
                        __u32 new_window = __tcp_select_window(sk);

                        /* Send ACK now, if this read freed lots of space
                         * in our buffer. Certainly, new_window is new window.
                         * We can advertise it now, if it is not less than current one.
                         * "Lots" means "at least twice" here.
                         */
                        if (new_window && new_window >= 2 * rcv_window_now)
                                time_to_ack = true;
                }
        }
        if (time_to_ack)
                //分配 skb 空间, 发送 ack 给对端
                tcp_send_ack(sk);
}

void tcp_send_ack(struct sock *sk)
{
        struct sk_buff *buff;

        /* If we have been reset, we may not send again. */
        if (sk->sk_state == TCP_CLOSE)
                return;

        tcp_ca_event(sk, CA_EVENT_NON_DELAYED_ACK);

        /* We are not putting this on the write queue, so
         * tcp_transmit_skb() will set the ownership to this
         * sock.
         */
        buff = alloc_skb(MAX_TCP_HEADER,
                         sk_gfp_mask(sk, GFP_ATOMIC | __GFP_NOWARN));
        if (unlikely(!buff)) {
                inet_csk_schedule_ack(sk);
                inet_csk(sk)->icsk_ack.ato = TCP_ATO_MIN;
                inet_csk_reset_xmit_timer(sk, ICSK_TIME_DACK,
                                          TCP_DELACK_MAX, TCP_RTO_MAX);
                return;
        }

        /* Reserve space for headers and prepare control bits. */
        skb_reserve(buff, MAX_TCP_HEADER);
        //初始化 skb tcp 控制块(tcp_skb_cb)信息
        tcp_init_nondata_skb(buff, tcp_acceptable_seq(sk), TCPHDR_ACK);

        /* We do not want pure acks influencing TCP Small Queues or fq/pacing
         * too much.
         * SKB_TRUESIZE(max(1 .. 66, MAX_TCP_HEADER)) is unfortunately ~784
         * We also avoid tcp_wfree() overhead (cache line miss accessing
         * tp->tsq_flags) by using regular sock_wfree()
         */
        //buff->truesize = 2
        skb_set_tcp_pure_ack(buff);

        /* Send it off, this clears delayed acks for us. */
        /*
         * 设置时间戳
         * buff->skb_mstamp->stamp_us = local_clock() / 1000
         * buff->stamp_jiffies = (u32)jiffies
         */
        skb_mstamp_get(&buff->skb_mstamp);
        //发送 buff 信息给对端
        tcp_transmit_skb(sk, buff, 0, (__force gfp_t)0);
}

/* SND.NXT, if window was not shrunk.
 * If window has been shrunk, what should we make? It is not clear at all.
 * Using SND.UNA we will fail to open window, SND.NXT is out of window. :-(
 * Anything in between SND.UNA...SND.UNA+SND.WND also can be already
 * invalid. OK, let's make this for now:
 */
static inline __u32 tcp_acceptable_seq(const struct sock *sk)
{
        const struct tcp_sock *tp = tcp_sk(sk);

        //tp->snd_una + tp->snd_wnd >= tp->snd_nxt
        if (!before(tcp_wnd_end(tp), tp->snd_nxt))
                return tp->snd_nxt;
        else
                return tcp_wnd_end(tp);
}

static void tcp_init_nondata_skb(struct sk_buff *skb, u32 seq, u8 flags)
{
        skb->ip_summed = CHECKSUM_PARTIAL;
        skb->csum = 0;

        TCP_SKB_CB(skb)->tcp_flags = flags;
        TCP_SKB_CB(skb)->sacked = 0;

        tcp_skb_pcount_set(skb, 1);

        TCP_SKB_CB(skb)->seq = seq;
        if (flags & (TCPHDR_SYN | TCPHDR_FIN))
                seq++;
        TCP_SKB_CB(skb)->end_seq = seq;
}



## recv 下部分

tcp_v4_rcv
    TCP_ESTABLISHED
        tcp_v4_do_rcv(sk, skb)
    TCP_LISTEN
        tcp_v4_do_rcv(sk, skb)
    TCP_TIME_WAIT
    TCP_NEW_SYN_RECV
        tcp_check_req(sk, skb, req, false);
            tcp_v4_syn_recv_sock

tcp_v4_do_rcv(sk, skb)
    TCP_ESTABLISHED
        tcp_rcv_established(sk, skb, tcp_hdr(skb), skb->len);
            直接拷贝到用户态或加入 sk_receive_queue

    tcp_rcv_state_process(sk, skb)

int tcp_v4_rcv(struct sk_buff *skb)
{
    const struct iphdr *iph;
    const struct tcphdr *th;
    struct sock *sk;
    int ret;
    struct net *net = dev_net(skb->dev);

    /*
     * #define PACKET_HOST		0
     * #define PACKET_BROADCAST	1
     * #define PACKET_MULTICAST	2
     * #define PACKET_OTHERHOST	3
     * #define PACKET_OUTGOING  4
     * #define PACKET_LOOPBACK  5
     * #define PACKET_FASTROUTE	6
     */
    if (skb->pkt_type != PACKET_HOST)
        goto discard_it;

    /* Count it even if it's bad */
    TCP_INC_STATS_BH(net, TCP_MIB_INSEGS);

    /*
     * 检查头部长度是否够 tcp 头
     * 如果 skb_headlen(skb) > sizeof(struct tcphdr), 继续
     * 如果 skb->len < sizeof(struct tcphdr), 包丢掉
     * 如果 skb_headlen(skb) < sizeof(struct tcphdr) < skb->len, TODO
     */

    if (!pskb_may_pull(skb, sizeof(struct tcphdr)))
        goto discard_it;

    th = tcp_hdr(skb);

    //检验头长度
    if (th->doff < sizeof(struct tcphdr) / 4)
        goto bad_packet;
    //检验skb 可用长度是否能容纳 tcp 包
    if (!pskb_may_pull(skb, th->doff * 4))
        goto discard_it;

    /* An explanation is required here, I think.
     * Packet length and doff are validated by header prediction,
     * provided case of th->doff==0 is eliminated.
     * So, we defer the checks. */

    if (skb_checksum_init(skb, IPPROTO_TCP, inet_compute_pseudo))
            goto csum_error;

    th = tcp_hdr(skb);
    iph = ip_hdr(skb);
    /* This is tricky : We move IPCB at its correct location into TCP_SKB_CB()
     * barrier() makes sure compiler wont play fool^Waliasing games.
     */
    memmove(&TCP_SKB_CB(skb)->header.h4, IPCB(skb),
            sizeof(struct inet_skb_parm));
    barrier();

    //用 tcp 头初始化 skb 的 tcp 控制信息
    TCP_SKB_CB(skb)->seq = ntohl(th->seq);
    TCP_SKB_CB(skb)->end_seq = (TCP_SKB_CB(skb)->seq + th->syn + th->fin +
                                skb->len - th->doff * 4);
    TCP_SKB_CB(skb)->ack_seq = ntohl(th->ack_seq);
    TCP_SKB_CB(skb)->tcp_flags = tcp_flag_byte(th);
    TCP_SKB_CB(skb)->tcp_tw_isn = 0;
    TCP_SKB_CB(skb)->ip_dsfield = ipv4_get_dsfield(iph);
    TCP_SKB_CB(skb)->sacked  = 0;

lookup:
    /* 找到 skb 对应的 sock.
     * 如 skb->sk 为不为空, 返回 skb->sk.
     * 否则在所属网络命名空间的网卡上, 遍历
     * tcp_hashinfo->ehash[hash]->chain 或 tcp_hashinfo->listening_hash[]->head 查找匹配根据四元组
     */
    sk = __inet_lookup_skb(&tcp_hashinfo, skb, __tcp_hdrlen(th), th->source,
                           th->dest);
    if (!sk)
        goto no_tcp_socket;

process:
    /*
     * TODO
     * 如果对端发送了重传 FIN, 发送 ACK
     * 如果对端发送的包不合法发送 RST, 关闭连接
     */
    if (sk->sk_state == TCP_TIME_WAIT)
        goto do_time_wait;

    if (sk->sk_state == TCP_NEW_SYN_RECV) {
            struct request_sock *req = inet_reqsk(sk);
            struct sock *nsk;

            sk = req->rsk_listener;
            if (unlikely(tcp_v4_inbound_md5_hash(sk, skb))) {
                    reqsk_put(req);
                    goto discard_it;
            }
            if (unlikely(sk->sk_state != TCP_LISTEN)) {
                    inet_csk_reqsk_queue_drop_and_put(sk, req);
                    goto lookup;
            }
            sock_hold(sk);
            //调用 tcp_v4_syn_recv_sock
            nsk = tcp_check_req(sk, skb, req, false);
            if (!nsk) {
                    reqsk_put(req);
                    goto discard_and_relse;
            }
            if (nsk == sk) {
                    reqsk_put(req);
            } else if (tcp_child_process(sk, nsk, skb)) {
                    tcp_v4_send_reset(nsk, skb);
                    goto discard_and_relse;
            } else {
                    sock_put(sk);
                    return 0;
            }
    }
    if (unlikely(iph->ttl < inet_sk(sk)->min_ttl)) {
        NET_INC_STATS_BH(net, LINUX_MIB_TCPMINTTLDROP);
        goto discard_and_relse;
    }

    if (!xfrm4_policy_check(sk, XFRM_POLICY_IN, skb))
        goto discard_and_relse;

    if (tcp_v4_inbound_md5_hash(sk, skb))
        goto discard_and_relse;

    nf_reset(skb);

    if (sk_filter(sk, skb))
        goto discard_and_relse;

    skb->dev = NULL;

    if (sk->sk_state == TCP_LISTEN) {
        ret = tcp_v4_do_rcv(sk, skb);
        goto put_and_return;
    }

    sk_incoming_cpu_update(sk);

    bh_lock_sock_nested(sk);
    // tp->segs_in += max(1, skb_shinfo(skb)->gso_segs);
    tcp_segs_in(tcp_sk(sk), skb);
    ret = 0;
    /*
     * 是否有进程正在使用这个 sock
     * 在 tcp_recvmsg 里，执行 lock_sock 后只能进入 else，而 release_sock 后会进入if
     */
    if (!sock_owned_by_user(sk)) {
        //如果报文放在 prequeue 队列，即表示延后处理，不占用软中断过长时间
        if (!tcp_prequeue(sk, skb))
                ret = tcp_v4_do_rcv(sk, skb);
    } else if (unlikely(sk_add_backlog(sk, skb,
                                   sk->sk_rcvbuf + sk->sk_sndbuf))) { //有进程占用 sock, 将其加入 backlog
        /*
         * 到这里表面 recv 队列满或内存空间不够
         * 其中队列满即: sk->sk_backlog.len + sk->sk_rmem_alloc > sk->sk_rcvbuf + sk->sk_sndbuf
         */
        bh_unlock_sock(sk);
        NET_INC_STATS_BH(net, LINUX_MIB_TCPBACKLOGDROP);
        goto discard_and_relse;
    }
    bh_unlock_sock(sk);

put_and_return:
        sock_put(sk);

        return ret;

no_tcp_socket:
        if (!xfrm4_policy_check(NULL, XFRM_POLICY_IN, skb))
                goto discard_it;

        if (tcp_checksum_complete(skb)) {
csum_error:
                TCP_INC_STATS_BH(net, TCP_MIB_CSUMERRORS);
bad_packet:
                TCP_INC_STATS_BH(net, TCP_MIB_INERRS);
        } else {
                tcp_v4_send_reset(NULL, skb);
        }

discard_it:
        /* Discard frame. */
        kfree_skb(skb);
        return 0;

discard_and_relse:
        sock_put(sk);
        goto discard_it;

do_time_wait:
        if (!xfrm4_policy_check(NULL, XFRM_POLICY_IN, skb)) {
                inet_twsk_put(inet_twsk(sk));
                goto discard_it;
        }

        if (tcp_checksum_complete(skb)) {
                inet_twsk_put(inet_twsk(sk));
                goto csum_error;
        }
        switch (tcp_timewait_state_process(inet_twsk(sk), skb, th)) {
        case TCP_TW_SYN: {
                struct sock *sk2 = inet_lookup_listener(dev_net(skb->dev),
                                                        &tcp_hashinfo, skb,
                                                        __tcp_hdrlen(th),
                                                        iph->saddr, th->source,
                                                        iph->daddr, th->dest,
                                                        inet_iif(skb));
                if (sk2) {
                        inet_twsk_deschedule_put(inet_twsk(sk));
                        sk = sk2;
                        goto process;
                }
                /* Fall through to ACK */
        }
        case TCP_TW_ACK:
                tcp_v4_timewait_ack(sk, skb);
                break;
        case TCP_TW_RST:
                tcp_v4_send_reset(sk, skb);
                inet_twsk_deschedule_put(inet_twsk(sk));
                goto discard_it;
        case TCP_TW_SUCCESS:;
        }
        goto discard_it;
}

如果处于 TCP_LISTEN 调用 tcp_v4_do_rcv
如果处于 TCP_NEW_SYN_RECV 调用 tcp_v4_syn_recv_sock
如果处于 TCP_TIME_WAIT 发送 ACK 或发送 reset 或丢弃
如果处于 TCP_ESTABLISHED :
    如果不使用 prequeue 或者没有用户进程读 socket 时,
    如果进程正在操作套接字, 就把 skb 指向的 TCP 报文插入到 backlog 队列


bool tcp_prequeue(struct sock *sk, struct sk_buff *skb)
{
	struct tcp_sock *tp = tcp_sk(sk);

    // tcp_low_latency = 1，表示不使用 prequeue 队列。tp->ucopy.task 为 0, 表示没有进程启动了拷贝TCP消息的流程
	if (sysctl_tcp_low_latency || !tp->ucopy.task)
		return false;

	if (skb->len <= tcp_hdrlen(skb) &&
	    skb_queue_len(&tp->ucopy.prequeue) == 0)
		return false;

	/* Before escaping RCU protected region, we need to take care of skb
	 * dst. Prequeue is only enabled for established sockets.
	 * For such sockets, we might need the skb dst only to set sk->sk_rx_dst
	 * Instead of doing full sk_rx_dst validity here, let's perform
	 * an optimistic check.
	 */
	if (likely(sk->sk_rx_dst))
		skb_dst_drop(skb);
	else
		skb_dst_force_safe(skb);

    //到这里，通常是用户进程读数据时没读到指定大小的数据, 休眠了. 直接将报文插入 prequeue 队列的末尾, 延后处理
	__skb_queue_tail(&tp->ucopy.prequeue, skb);
	tp->ucopy.memory += skb->truesize;
    //当然, 虽然通常是延后处理, 但如果TCP的接收缓冲区不够用了, 就会立刻处理 prequeue 队列里的所有报文
	if (tp->ucopy.memory > sk->sk_rcvbuf) {
		struct sk_buff *skb1;

		BUG_ON(sock_owned_by_user(sk));

		while ((skb1 = __skb_dequeue(&tp->ucopy.prequeue)) != NULL) {
			sk_backlog_rcv(sk, skb1);
			NET_INC_STATS_BH(sock_net(sk),
					 LINUX_MIB_TCPPREQUEUEDROPPED);
		}

		tp->ucopy.memory = 0;
	} else if (skb_queue_len(&tp->ucopy.prequeue) == 1) {
        // prequeue 里有报文了, 唤醒正在休眠等待数据的进程, 让进程在它的上下文中处理这个 prequeue 队列的报文
		wake_up_interruptible_sync_poll(sk_sleep(sk),
					   POLLIN | POLLRDNORM | POLLRDBAND);
		if (!inet_csk_ack_scheduled(sk))
			inet_csk_reset_xmit_timer(sk, ICSK_TIME_DACK,
						  (3 * tcp_rto_min(sk)) / 4,
						  TCP_RTO_MAX);
	}
	return true;
}

int tcp_v4_do_rcv(struct sock *sk, struct sk_buff *skb)
{
	struct sock *rsk;

	if (sk->sk_state == TCP_ESTABLISHED) { /* Fast path */
		struct dst_entry *dst = sk->sk_rx_dst;

		//sk->sk_rxhash = skb->hash;
		sock_rps_save_rxhash(sk, skb);
        //sk->sk_napi_id = skb->napi_id
		sk_mark_napi_id(sk, skb);
		if (dst) {
			if (inet_sk(sk)->rx_dst_ifindex != skb->skb_iif ||
			    !dst->ops->check(dst, 0)) {
				dst_release(dst);
				sk->sk_rx_dst = NULL;
			}
		}
        //建立连接处理方法
		tcp_rcv_established(sk, skb, tcp_hdr(skb), skb->len);
		return 0;
	}

	if (tcp_checksum_complete(skb))
		goto csum_err;

	if (sk->sk_state == TCP_LISTEN) {
		struct sock *nsk = tcp_v4_cookie_check(sk, skb);

		if (!nsk)
			goto discard;
		if (nsk != sk) {
		    //sk->sk_rxhash = skb->hash;
			sock_rps_save_rxhash(nsk, skb);
            //sk->sk_napi_id = skb->napi_id
			sk_mark_napi_id(nsk, skb);
			if (tcp_child_process(sk, nsk, skb)) {
				rsk = nsk;
				goto reset;
			}
			return 0;
		}
	} else
		sock_rps_save_rxhash(sk, skb);

	if (tcp_rcv_state_process(sk, skb)) {
		rsk = sk;
		goto reset;
	}
	return 0;

reset:
	tcp_v4_send_reset(rsk, skb);
discard:
	kfree_skb(skb);
	/* Be careful here. If this function gets more complicated and
	 * gcc suffers from register pressure on the x86, sk (in %ebx)
	 * might be destroyed here. This current version compiles correctly,
	 * but you have been warned.
	 */
	return 0;

csum_err:
	TCP_INC_STATS_BH(sock_net(sk), TCP_MIB_CSUMERRORS);
	TCP_INC_STATS_BH(sock_net(sk), TCP_MIB_INERRS);
	goto discard;
}


void tcp_rcv_established(struct sock *sk, struct sk_buff *skb,
			 const struct tcphdr *th, unsigned int len)
{
	struct tcp_sock *tp = tcp_sk(sk);

	if (unlikely(!sk->sk_rx_dst))
		inet_csk(sk)->icsk_af_ops->sk_rx_dst_set(sk, skb);
	/*
	 *	Header prediction.
	 *	The code loosely follows the one in the famous
	 *	"30 instruction TCP receive" Van Jacobson mail.
	 *
	 *	Van's trick is to deposit buffers into socket queue
	 *	on a device interrupt, to call tcp_recv function
	 *	on the receive process context and checksum and copy
	 *	the buffer to user space. smart...
	 *
	 *	Our current scheme is not silly either but we take the
	 *	extra cost of the net_bh soft interrupt processing...
	 *	We do checksum and copy also but from device to kernel.
	 */

	tp->rx_opt.saw_tstamp = 0;

	/*	pred_flags is 0xS?10 << 16 + snd_wnd
	 *	if header_prediction is to be made
	 *	'S' will always be tp->tcp_header_len >> 2
	 *	'?' will be 0 for the fast path, otherwise pred_flags is 0 to
	 *  turn it off	(when there are holes in the receive
	 *	 space for instance)
	 *	PSH flag is ignored.
	 */

	if ((tcp_flag_word(th) & TCP_HP_BITS) == tp->pred_flags &&
	    TCP_SKB_CB(skb)->seq == tp->rcv_nxt &&
	    !after(TCP_SKB_CB(skb)->ack_seq, tp->snd_nxt)) {
		int tcp_header_len = tp->tcp_header_len;

		/* Timestamp header prediction: tcp_header_len
		 * is automatically equal to th->doff*4 due to pred_flags
		 * match.
		 */

		/* Check timestamp */
		if (tcp_header_len == sizeof(struct tcphdr) + TCPOLEN_TSTAMP_ALIGNED) {
			/* No? Slow path! */
			if (!tcp_parse_aligned_timestamp(tp, th))
				goto slow_path;

			/* If PAWS failed, check it more carefully in slow path */
			if ((s32)(tp->rx_opt.rcv_tsval - tp->rx_opt.ts_recent) < 0)
				goto slow_path;

			/* DO NOT update ts_recent here, if checksum fails
			 * and timestamp was corrupted part, it will result
			 * in a hung connection since we will drop all
			 * future packets due to the PAWS test.
			 */
		}

		if (len <= tcp_header_len) {
			/* Bulk data transfer: sender */
			if (len == tcp_header_len) {
				/* Predicted packet is in window by definition.
				 * seq == rcv_nxt and rcv_wup <= rcv_nxt.
				 * Hence, check seq<=rcv_wup reduces to:
				 */
				if (tcp_header_len ==
				    (sizeof(struct tcphdr) + TCPOLEN_TSTAMP_ALIGNED) &&
				    tp->rcv_nxt == tp->rcv_wup)
					tcp_store_ts_recent(tp);

				/* We know that such packets are checksummed
				 * on entry.
				 */
				tcp_ack(sk, skb, 0);
				__kfree_skb(skb);
				tcp_data_snd_check(sk);
				return;
			} else { /* Header too small */
				TCP_INC_STATS_BH(sock_net(sk), TCP_MIB_INERRS);
				goto discard;
			}
		} else {
            //表示当前数据已经拷贝到用户态
			int eaten = 0;
			bool fragstolen = false;

            /*
             * 正好当前正在拷贝, 并且下一个需要接受的就是当前 skb,
             * 那么就设置当前进程为 RUNING, 直接将数据拷贝到用户态.
             */
			if (tp->ucopy.task == current &&
			    tp->copied_seq == tp->rcv_nxt &&
			    len - tcp_header_len <= tp->ucopy.len &&
			    sock_owned_by_user(sk)) {
				__set_current_state(TASK_RUNNING);

				if (!tcp_copy_to_iovec(sk, skb, tcp_header_len)) {
					/* Predicted packet is in window by definition.
					 * seq == rcv_nxt and rcv_wup <= rcv_nxt.
					 * Hence, check seq<=rcv_wup reduces to:
					 */
					if (tcp_header_len ==
					    (sizeof(struct tcphdr) +
					     TCPOLEN_TSTAMP_ALIGNED) &&
					    tp->rcv_nxt == tp->rcv_wup)
						tcp_store_ts_recent(tp);

					tcp_rcv_rtt_measure_ts(sk, skb);

					__skb_pull(skb, tcp_header_len);
					tcp_rcv_nxt_update(tp, TCP_SKB_CB(skb)->end_seq);
					NET_INC_STATS_BH(sock_net(sk), LINUX_MIB_TCPHPHITSTOUSER);
                    //表示当前数据已经拷贝到用户态
					eaten = 1;
				}
			}
            //如果数据没有被拷贝到用户态就加入 sk_receive_queue
			if (!eaten) {
				if (tcp_checksum_complete_user(sk, skb))
					goto csum_error;

				if ((int)skb->truesize > sk->sk_forward_alloc)
					goto step5;

				/* Predicted packet is in window by definition.
				 * seq == rcv_nxt and rcv_wup <= rcv_nxt.
				 * Hence, check seq<=rcv_wup reduces to:
				 */
				if (tcp_header_len ==
				    (sizeof(struct tcphdr) + TCPOLEN_TSTAMP_ALIGNED) &&
				    tp->rcv_nxt == tp->rcv_wup)
					tcp_store_ts_recent(tp);

				tcp_rcv_rtt_measure_ts(sk, skb);

				NET_INC_STATS_BH(sock_net(sk), LINUX_MIB_TCPHPHITS);

				/* Bulk data transfer: receiver */
                /*
                 * 如果 skb 可以合并到 sk->sk_receive_queue 队列的尾元素, 则合并进去,
                 * 如果 sk 不能合并进去, 加入 sk->sk_receive_queue
                 */
				eaten = tcp_queue_rcv(sk, skb, tcp_header_len,
						      &fragstolen);
			}

			tcp_event_data_recv(sk, skb);

			if (TCP_SKB_CB(skb)->ack_seq != tp->snd_una) {
				/* Well, only one small jumplet in fast path... */
				tcp_ack(sk, skb, FLAG_DATA);
				tcp_data_snd_check(sk);
				if (!inet_csk_ack_scheduled(sk))
					goto no_ack;
			}

			__tcp_ack_snd_check(sk, 0);
no_ack:
			if (eaten)
				kfree_skb_partial(skb, fragstolen);
            //实际调用 sock_def_readable(sk), 会发送信号唤醒睡眠的进程
			sk->sk_data_ready(sk);
			return;
		}
	}

slow_path:
	if (len < (th->doff << 2) || tcp_checksum_complete_user(sk, skb))
		goto csum_error;

	if (!th->ack && !th->rst && !th->syn)
		goto discard;

	/*
	 *	Standard slow path.
	 */

	if (!tcp_validate_incoming(sk, skb, th, 1))
		return;

step5:
	if (tcp_ack(sk, skb, FLAG_SLOWPATH | FLAG_UPDATE_TS_RECENT) < 0)
		goto discard;

	tcp_rcv_rtt_measure_ts(sk, skb);

	/* Process urgent data. */
	tcp_urg(sk, skb, th);

	/* step 7: process the segment text */
	tcp_data_queue(sk, skb);

	tcp_data_snd_check(sk);
	tcp_ack_snd_check(sk);
	return;

csum_error:
	TCP_INC_STATS_BH(sock_net(sk), TCP_MIB_CSUMERRORS);
	TCP_INC_STATS_BH(sock_net(sk), TCP_MIB_INERRS);

discard:
	__kfree_skb(skb);
}
EXPORT_SYMBOL(tcp_rcv_established);


static void sock_def_readable(struct sock *sk)
{
	struct socket_wq *wq;

	rcu_read_lock();
	wq = rcu_dereference(sk->sk_wq);
	if (skwq_has_sleeper(wq))
		wake_up_interruptible_sync_poll(&wq->wait, POLLIN | POLLPRI |
						POLLRDNORM | POLLRDBAND);
	sk_wake_async(sk, SOCK_WAKE_WAITD, POLL_IN);
	rcu_read_unlock();
}


快路径被禁止的条件:

- A zero window was announced from us - zero window probing
      is only handled properly in the slow path.
- Out of order segments arrived.
- Urgent data is expected.
- There is no buffer space left
- Unexpected TCP flags/window values/header lengths are received
  (detected by checking the TCP header against pred_flags)
- Data is sent in both directions. Fast path only supports pure senders
  or pure receivers (this means either the sequence number or the ack
  value must stay constant)
- Unexpected TCP option.


static void tcp_data_queue(struct sock *sk, struct sk_buff *skb)
{
	struct tcp_sock *tp = tcp_sk(sk);
	int eaten = -1;
	bool fragstolen = false;

    //零窗口包, 丢弃
	if (TCP_SKB_CB(skb)->seq == TCP_SKB_CB(skb)->end_seq)
		goto drop;

    //skb->_skb_refdst = 0U
	skb_dst_drop(skb);
	__skb_pull(skb, tcp_hdr(skb)->doff * 4);

	tcp_ecn_accept_cwr(tp, skb);

	tp->rx_opt.dsack = 0;

	/*  Queue data for delivery to the user.
	 *  Packets in sequence go to the receive queue.
	 *  Out of sequence packets to the out_of_order_queue.
	 */
	if (TCP_SKB_CB(skb)->seq == tp->rcv_nxt) {
		if (tcp_receive_window(tp) == 0)
			goto out_of_window;

		/* Ok. In sequence. In window. */
		if (tp->ucopy.task == current &&
		    tp->copied_seq == tp->rcv_nxt && tp->ucopy.len &&
		    sock_owned_by_user(sk) && !tp->urg_data) {
			int chunk = min_t(unsigned int, skb->len,
					  tp->ucopy.len);

			__set_current_state(TASK_RUNNING);

			local_bh_enable();
            //直接将报文内容拷贝到用户态内存中
			if (!skb_copy_datagram_msg(skb, 0, tp->ucopy.msg, chunk)) {
                //如果拷贝到用户态成功
				tp->ucopy.len -= chunk;
				tp->copied_seq += chunk;
				eaten = (chunk == skb->len);
				tcp_rcv_space_adjust(sk);
			}
			local_bh_disable();
		}

		if (eaten <= 0) {
queue_and_out:
            //拷贝到用户态的数据 chunk 少于 skb->len, 加入 sk->sk_receive_queue
			if (eaten < 0) {
				if (skb_queue_len(&sk->sk_receive_queue) == 0)
					sk_forced_mem_schedule(sk, skb->truesize);
				else if (tcp_try_rmem_schedule(sk, skb, skb->truesize)) //尽力将 skb 合并到 sk->sk_receive_queue 的最后一个元素中
					goto drop;
			}
            /*
             * 如果 skb 可以合并到 sk->sk_receive_queue 队列的尾元素, 则合并进去,
             * 如果 sk 不能合并进去, 加入 sk->sk_receive_queue
             */
			eaten = tcp_queue_rcv(sk, skb, 0, &fragstolen);
		}
		tcp_rcv_nxt_update(tp, TCP_SKB_CB(skb)->end_seq);
		if (skb->len)
			tcp_event_data_recv(sk, skb);
		if (TCP_SKB_CB(skb)->tcp_flags & TCPHDR_FIN)
            //处理包中 FIN 为 1
			tcp_fin(sk);

		if (!skb_queue_empty(&tp->out_of_order_queue)) {
            //将 sk->out_of_order_queue 的包合并到 sk->sk_receive_queue
			tcp_ofo_queue(sk);

			/* RFC2581. 4.2. SHOULD send immediate ACK, when
			 * gap in queue is filled.
			 */
            //如果 out_of_order_queue 全部合并到 sk->sk_receive_queue, 立即发
			if (skb_queue_empty(&tp->out_of_order_queue))
				inet_csk(sk)->icsk_ack.pingpong = 0;
		}

        //如果 tcp 的选择应答队列不为空, 清除tcp->selective_acks 中已经应答的元素
		if (tp->rx_opt.num_sacks)
			tcp_sack_remove(tp);

        //检查 fast path 满足, 设置 tcp->pred_flags
		tcp_fast_path_check(sk);

		if (eaten > 0)
			kfree_skb_partial(skb, fragstolen);
		if (!sock_flag(sk, SOCK_DEAD))
			sk->sk_data_ready(sk);
		return;
	}

	if (!after(TCP_SKB_CB(skb)->end_seq, tp->rcv_nxt)) {
		/* A retransmit, 2nd most common case.  Force an immediate ack. */
		NET_INC_STATS_BH(sock_net(sk), LINUX_MIB_DELAYEDACKLOST);
		tcp_dsack_set(sk, TCP_SKB_CB(skb)->seq, TCP_SKB_CB(skb)->end_seq);

out_of_window:
		tcp_enter_quickack_mode(sk);
		inet_csk_schedule_ack(sk);
drop:
		__kfree_skb(skb);
		return;
	}

	/* Out of window. F.e. zero window probe. */
    //收到的 skb 在接受窗口之外.
	if (!before(TCP_SKB_CB(skb)->seq, tp->rcv_nxt + tcp_receive_window(tp)))
		goto out_of_window;

	tcp_enter_quickack_mode(sk);

	if (before(TCP_SKB_CB(skb)->seq, tp->rcv_nxt)) {
		/* Partial packet, seq < rcv_next < end_seq */
		SOCK_DEBUG(sk, "partial packet: rcv_next %X seq %X - %X\n",
			   tp->rcv_nxt, TCP_SKB_CB(skb)->seq,
			   TCP_SKB_CB(skb)->end_seq);

        //设置 tcp->duplicate_sack
		tcp_dsack_set(sk, TCP_SKB_CB(skb)->seq, tp->rcv_nxt);

		/* If window is closed, drop tail of packet. But after
		 * remembering D-SACK for its head made in previous line.
		 */
		if (!tcp_receive_window(tp))
			goto out_of_window;
		goto queue_and_out;
	}

    /*
     * 将 skb 加入 sk->out_of_order_queue, 检查 skb 与 sk->out_of_order_queue
     * 最后一个元素的顺序性, 如何可以合并, 会合并. 此外. out_of_order_queue 中
     * 包时安装 seq 顺序保存的.
     */
	tcp_data_queue_ofo(sk, skb);
}

/*
 * 如果 skb 可以合并到 sk->sk_receive_queue 队列的尾元素, 则合并进去, 返回 1
 * 如果 sk 不能合并进去, 加入 sk->sk_receive_queue, 返回 0
 */
static int __must_check tcp_queue_rcv(struct sock *sk, struct sk_buff *skb, int hdrlen,
		  bool *fragstolen)
{
	int eaten;
	struct sk_buff *tail = skb_peek_tail(&sk->sk_receive_queue);

	__skb_pull(skb, hdrlen);
    //如果可以将 skb 合并到 tail 中, 返回 1, 不能合并返回 0
	eaten = (tail &&
		 tcp_try_coalesce(sk, tail, skb, fragstolen)) ? 1 : 0;
    /*
     * tp->rcv_nxt = seq;
     * tp->bytes_received += delta;
     */
	tcp_rcv_nxt_update(tcp_sk(sk), TCP_SKB_CB(skb)->end_seq);
	if (!eaten) {
		__skb_queue_tail(&sk->sk_receive_queue, skb);
		skb_set_owner_r(skb, sk);
	}
	return eaten;
}

/*
 * 将 sk->out_of_order_queue 的包合并到 sk->sk_receive_queue
 */
static void tcp_ofo_queue(struct sock *sk)
{
	struct tcp_sock *tp = tcp_sk(sk);
	__u32 dsack_high = tp->rcv_nxt;
	struct sk_buff *skb, *tail;
	bool fragstolen, eaten;

	while ((skb = skb_peek(&tp->out_of_order_queue)) != NULL) {
		if (after(TCP_SKB_CB(skb)->seq, tp->rcv_nxt))
			break;

		if (before(TCP_SKB_CB(skb)->seq, dsack_high)) {
			__u32 dsack = dsack_high;
			if (before(TCP_SKB_CB(skb)->end_seq, dsack_high))
				dsack_high = TCP_SKB_CB(skb)->end_seq;
			tcp_dsack_extend(sk, TCP_SKB_CB(skb)->seq, dsack);
		}

		__skb_unlink(skb, &tp->out_of_order_queue);
        //如果包中全部数据都已经收到, 丢弃该包
		if (!after(TCP_SKB_CB(skb)->end_seq, tp->rcv_nxt)) {
			SOCK_DEBUG(sk, "ofo packet was already received\n");
			__kfree_skb(skb);
			continue;
		}
		SOCK_DEBUG(sk, "ofo requeuing : rcv_next %X seq %X - %X\n",
			   tp->rcv_nxt, TCP_SKB_CB(skb)->seq,
			   TCP_SKB_CB(skb)->end_seq);

        /* 如果 skb 可以合并到 sk->sk_receive_queue 合并之, 不行, 加入
         * sk->sk_receive_queue 尾部.
         */
		tail = skb_peek_tail(&sk->sk_receive_queue);
		eaten = tail && tcp_try_coalesce(sk, tail, skb, &fragstolen);
		tcp_rcv_nxt_update(tp, TCP_SKB_CB(skb)->end_seq);
		if (!eaten)
			__skb_queue_tail(&sk->sk_receive_queue, skb);
        //如果 out_of_order_queue 中的包有 FIN 标志, 立即处理 FIN.
		if (TCP_SKB_CB(skb)->tcp_flags & TCPHDR_FIN)
			tcp_fin(sk);
		if (eaten)
			kfree_skb_partial(skb, fragstolen);
	}
}

#define sk_wait_event(__sk, __timeo, __condition)			\
	({	int __rc;						\
        /* 如果 backlog 队列不为空, 遍历 backlog 队列:
         * 如果是待收的数据将其直接拷贝到用户态;
         * 如果不是, 就加入 receive_queue
         */
		release_sock(__sk);					\
		__rc = __condition;					\
        /*
         * 如果没有收到任何数据, 此时 sk->sk_receive_queue 仍然为空,
         * 就休眠 __timeo
         */
		if (!__rc) {						\
			*(__timeo) = schedule_timeout(*(__timeo));	\
		}							\
		sched_annotate_sleep();						\
		lock_sock(__sk);					\
		__rc = __condition;					\
		__rc;							\
	})

int sk_wait_data(struct sock *sk, long *timeo, const struct sk_buff *skb)
{
	int rc;
	DEFINE_WAIT(wait);

	prepare_to_wait(sk_sleep(sk), &wait, TASK_INTERRUPTIBLE);
	sk_set_bit(SOCKWQ_ASYNC_WAITDATA, sk);
    //sk->sk_wait_event 不为空或超时
	rc = sk_wait_event(sk, timeo, skb_peek_tail(&sk->sk_receive_queue) != skb);
	sk_clear_bit(SOCKWQ_ASYNC_WAITDATA, sk);
	finish_wait(sk_sleep(sk), &wait);
	return rc;
}

## 参考

http://taohui.org.cn/high_perf_network_3.html
