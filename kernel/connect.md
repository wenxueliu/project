
## connect

```
SYSCALL_DEFINE3(connect, int, fd, struct sockaddr __user *, uservaddr, int, addrlen)
{
        struct socket *sock;
        struct sockaddr_storage address;
        int err, fput_needed;

        sock = sockfd_lookup_light(fd, &err, &fput_needed);
        if (!sock)
                goto out;
        err = move_addr_to_kernel(uservaddr, addrlen, &address);
        if (err < 0)
                goto out_put;

        err =
            security_socket_connect(sock, (struct sockaddr *)&address, addrlen);
        if (err)
                goto out_put;

        err = sock->ops->connect(sock, (struct sockaddr *)&address, addrlen,
                                 sock->file->f_flags);
out_put:
        fput_light(sock->file, fput_needed);
out:
        return err;
}
```

主要步骤

1. 找到 fd 对应的 file(current->files->fdt[fd])
2. 从 file 定位到 sock(file->private_data)
3. 将要访问的用户地址传递到内核空间.
4. 调用对应协议的 connect 函数(目前面向流的协议为 inet_stream_connect, dgram 和 sockraw 为 inet_dgram_connect)


int __inet_stream_connect(struct socket *sock, struct sockaddr *uaddr, int addr_len, int flags)
        struct sock *sk = sock->sk;
        int err;
        long timeo;

        switch (sock->state)
        default:
                err = -EINVAL;
                goto out;
        case SS_CONNECTED:
                err = -EISCONN;
                goto out;
        case SS_CONNECTING:
                err = -EALREADY;
                /* Fall out of switch with err, set for this state */
                break;
        case SS_UNCONNECTED:
                err = -EISCONN;
                if (sk->sk_state != TCP_CLOSE)
                        goto out;

                err = sk->sk_prot->connect(sk, uaddr, addr_len);
                if (err < 0)
                        goto out;

                sock->state = SS_CONNECTING;

                /* Just entered SS_CONNECTING state; the only
                 * difference is that return value in non-blocking
                 * case is EINPROGRESS, rather than EALREADY.
                 */
                err = -EINPROGRESS;
                break;

        timeo = sock_sndtimeo(sk, flags & O_NONBLOCK);

        if ((1 << sk->sk_state) & (TCPF_SYN_SENT | TCPF_SYN_RECV))
                int writebias = (sk->sk_protocol == IPPROTO_TCP) &&
                                tcp_sk(sk)->fastopen_req &&
                                tcp_sk(sk)->fastopen_req->data ? 1 : 0;

                /* Error code is set above */
                if (!timeo || !inet_wait_for_connect(sk, timeo, writebias))
                        goto out;

                err = sock_intr_errno(timeo);
                if (signal_pending(current))
                        goto out;

        /* Connection was closed by RST, timeout, ICMP error
         * or another process disconnected us.
         */
        if (sk->sk_state == TCP_CLOSE)
                goto sock_error;

        /* sk->sk_err may be not zero now, if RECVERR was ordered by user
         * and error was received after socket entered established state.
         * Hence, it is handled normally after connect() return successfully.
         */

        sock->state = SS_CONNECTED;
        err = 0;
out:
        return err;

sock_error:
        err = sock_error(sk) ? : -ECONNABORTED;
        sock->state = SS_UNCONNECTED;
        if (sk->sk_prot->disconnect(sk, flags))
                sock->state = SS_DISCONNECTING;
        goto out;

int inet_stream_connect(struct socket *sock, struct sockaddr *uaddr,
                        int addr_len, int flags)
        int err;

        lock_sock(sock->sk);
        err = __inet_stream_connect(sock, uaddr, addr_len, flags);
        release_sock(sock->sk);
        return err;

1. 检查socket地址长度和使用的协议族
2. 如果当前 sock->state 为 SS_UNCONNECTED 并且 sock->sk_state 不是 TCP_CLOSE, 调用对应协议的 connect 函数(tcp 为 tcp_v4_connect)发送SYN包.
3. 设置当前 sock->state 为 SS_CONNECTING, 表示正在建立连接
4. 如果设置 O_NONBLOCK 标志时, 立即返回, 错误代码为 EINPROGRESS, 表示正在建立连接.
5. 如果没有设置 O_NONBLOCK 标志时, 调用 inet_wait_for_connect 通过睡眠来等待连接建立成功. 在以下三种情况下会被唤醒：
    (1) 使用SO_SNDTIMEO选项时，睡眠时间超过设定值，返回0。connect()返回错误码-EINPROGRESS。
    (2) 收到信号，返回剩余的等待时间。connect()返回错误码-ERESTARTSYS或-EINTR。
    (3) 三次握手成功，sock的状态从TCP_SYN_SENT或TCP_SYN_RECV变为TCP_ESTABLISHED，
   如果连接建立成功, 设置当前 sock->state 为 SS_CONNECTED
   如果连接建立失败(对端关闭连接sk->sk_state == TCP_CLOSE), 调用 disconnect 函数断开连接.失败原因包括超时, 对端发送 RST 等等.

int tcp_v4_connect(struct sock *sk, struct sockaddr *uaddr, int addr_len)
    rt = ip_route_connect(fl4, nexthop, inet->inet_saddr, RT_CONN_FLAGS(sk), sk->sk_bound_dev_if, IPPROTO_TCP, orig_sport, orig_dport, sk)
    tcp_set_state(sk, TCP_SYN_SENT)
    tp->write_seq = secure_tcp_sequence_number(inet->inet_saddr, inet->inet_daddr, inet->inet_sport, usin->sin_port)
    inet->inet_id = tp->write_seq ^ jiffies
    tcp_connect(sk)
        tcp_connect_init(sk)
        buff = sk_stream_alloc_skb(sk, 0, sk->sk_allocation, true)
        tcp_init_nondata_skb(buff, tp->write_seq++, TCPHDR_SYN)
        tcp_connect_queue_skb(sk, buff)
        tcp_ecn_send_syn(sk, buff)
        tp->fastopen_req ? tcp_send_syn_data(sk, buff) : tcp_transmit_skb(sk, buff, 1, sk->sk_allocation);
        tp->snd_nxt = tp->write_seq;
        tp->pushed_seq = tp->write_seq;
        inet_csk_reset_xmit_timer(sk, ICSK_TIME_RETRANS, inet_csk(sk)->icsk_rto, TCP_RTO_MAX)


1. 查找路由, 如果找不到或者是多播和广播, 返回错误.找到初始化四元组
2. 生成发送的序列号
3. 初始化 tcp_sock 相关属性, 分配 skb 内存, 将分配的 skb 加入 sk->sk_write_queue 队列等.
4. 

tcp_transmit_skb //添加 tcp 头
    icsk->icsk_af_ops->queue_xmit(sk, skb, &inet->cork.fl)
        ipv4_specific->queue_xmit(sk, skb, &inet->cork.fl)
            ip_queue_xmit(sk, skb, &inet->cork.fl) //添加 ip 头
                ip_local_out(net, sk, skb)
                    __ip_local_out(net, sk, skb) //netfilter hook
                    dst_output(net, sk, skb)
                        skb_dst(skb)->output(net, sk, skb)
                            ip_output(net, sk, skb)
                                ip_finish_output()
                                if gso : ip_finish_output_gso(net, sk, skb, mtu)
                                        if (IPCB(skb)->flags & IPSKB_FORWARDED): ip_finish_output2(net, sk, skb)
                                        else : ip_fragment(net, sk, segs, mtu, ip_finish_output2);
                                                ip_do_fragment(net, sk, skb, output)
                                if frags : ip_fragment(net, sk, skb, mtu, ip_finish_output2)
                                        ip_do_fragment(net, sk, skb, ip_finish_output2)
                                            ip_finish_output2(net, sk, skb)
                                else ip_finish_output2(net, sk, skb)
ip_finish_output2
    dst_neigh_output(dst, neigh, skb)


    tcp_enter_cwr(sk);
    net_xmit_eval(err)

    tcp_cong_list 中查找 dst_metric(dst, RTAX_CC_ALGO) 对应的 ca, 初始化 icsk->icsk_ca_ops = ca; icsk->icsk_ca_dst_locked = tcp_ca_dst_locked(dst)
    tp->window_clamp = dst_metric(dst, RTAX_WINDOW)
    if (tp->rx_opt.user_mss && tp->rx_opt.user_mss < tp->advmss) tp->advmss = tp->rx_opt.user_mss;
    inet_csk(sk)->icsk_ack.rcv_mss = min(tp->advmss, tp->mss_cache, tp->rcv_wnd / 2, TCP_MSS_DEFAULT, TCP_MIN_MSS)
    if (sk->sk_userlocks & SOCK_RCVBUF_LOCK && (tp->window_clamp > tcp_full_space(sk) || tp->window_clamp == 0)) tp->window_clamp = tcp_full_space(sk)
    tp->rx_opt.rcv_wscale = rcv_wscale
    tp->rcv_ssthresh = tp->rcv_wnd
    sk->sk_flags &= ~SOCK_DONE
    tp->snd_wnd = 0
    tp->snd_una = tp->write_seq
    tp->snd_sml = tp->write_seq
    tp->snd_up = tp->write_seq
    tp->snd_nxt = tp->write_seq
    tp->rcv_wup = tp->rcv_nxt
    tp->copied_seq = tp->rcv_nxt
    inet_csk(sk)->icsk_rto = TCP_TIMEOUT_INIT
    inet_csk(sk)->icsk_retransmits = 0
    tp->retrans_out = 0
    tp->lost_out = 0
    tp->undo_marker = 0
    tp->undo_retrans = -1
    tp->fackets_out = 0
    tp->sacked_out = 0
    tp->snd_wl1 = 0
    TCP_SKB_CB(skb)->tcp_flags = TCPHDR_SYN
    TCP_SKB_CB(skb)->sacked = 0
    TCP_SKB_CB(skb)->tcp_gso_segs = 1
    tp->retrans_stamp = tcp_time_stamp
    TCP_SKB_CB(skb)->seq = tp->write_seq
    TCP_SKB_CB(skb)->end_seq = tp->write_seq + skb->len
    skb 加入 sk->sk_write_queue
    sk->sk_wmem_queued += skb->truesize
    if !sk->sk_prot->memory_allocated: sk->sk_forward_alloc -= skb->truesize
    tp->write_seq = tcb->end_seq;
    tp->packets_out += TCP_SKB_CB(skb)->tcp_gso_segs
    tp->ecn_flags = 0
    if sock_net(sk)->ipv4.sysctl_tcp_ecn == 1 ||  inet_csk(sk)->icsk_ca_ops->flags & TCP_CONG_NEEDS_ECN:
        TCP_SKB_CB(skb)->tcp_flags |= TCPHDR_ECE | TCPHDR_CWR
        tp->ecn_flags = TCP_ECN_OK
    tp->pushed_seq = tp->write_seq

    skb->sk = sk;
    skb->destructor = skb_is_tcp_pure_ack(skb) ? sock_wfree : tcp_wfree;
    skb->l4_hash = 1;
    skb->hash = sk->sk_txhash;
    sk->sk_wmem_alloc += skb->truesize

    th->source              = inet->inet_sport;
    th->dest                = inet->inet_dport;
    th->seq                 = htonl(tcb->seq);
    th->ack_seq             = htonl(tp->rcv_nxt);
    skb_shinfo(skb)->gso_segs = TCP_SKB_CB(skb)->tcp_gso_segs
    skb_shinfo(skb)->gso_size = TCP_SKB_CB(skb)->tcp_gso_size
    skb->tstamp.tv64 = 0

int inet_dgram_connect(struct socket *sock, struct sockaddr *uaddr, int addr_len, int flags)
        struct sock *sk = sock->sk;
        if (!inet_sk(sk)->inet_num && inet_autobind(sk))
                return -EAGAIN;
        return sk->sk_prot->connect(sk, uaddr, addr_len);


调用对应协议的 connect 函数.


##附录

### connect 阻塞等待分析

```
static inline long sock_sndtimeo(const struct sock *sk, bool noblock)
{
        return noblock ? 0 : sk->sk_sndtimeo;
}

/*
 * Note: we use "set_current_state()" _after_ the wait-queue add,
 * because we need a memory barrier there on SMP, so that any
 * wake-function that tests for the wait-queue being active
 * will be guaranteed to see waitqueue addition _or_ subsequent
 * tests in this thread will see the wakeup having taken place.
 *
 * The spin_unlock() itself is semi-permeable and only protects
 * one way (it only protects stuff inside the critical region and
 * stops them from bleeding out - it would still allow subsequent
 * loads to move into the critical region).
 */
void
prepare_to_wait(wait_queue_head_t *q, wait_queue_t *wait, int state)
{
        unsigned long flags;

        wait->flags &= ~WQ_FLAG_EXCLUSIVE;
        spin_lock_irqsave(&q->lock, flags);
        //避免再次循环中被重复添加.
        if (list_empty(&wait->task_list))
                __add_wait_queue(q, wait);
        set_current_state(state);
        spin_unlock_irqrestore(&q->lock, flags);
}

static long inet_wait_for_connect(struct sock *sk, long timeo, int writebias)
{
        DEFINE_WAIT(wait);

        /* 把等待任务加入到socket的等待队列头部，把进程的状态设为TASK_INTERRUPTIBLE */
        prepare_to_wait(sk_sleep(sk), &wait, TASK_INTERRUPTIBLE);
        sk->sk_write_pending += writebias;

        /* Basic assumption: if someone sets sk->sk_err, he _must_
         * change state of the socket from TCP_SYN_*.
         * Connect() does not allow to get error notifications
         * without closing the socket.
         */
        /* 完成三次握手后，状态就会变为TCP_ESTABLISHED，从而退出循环 */
        while ((1 << sk->sk_state) & (TCPF_SYN_SENT | TCPF_SYN_RECV)) {
                release_sock(sk);
                /* 进入睡眠，直到超时或收到信号，或者被I/O事件处理函数唤醒。
                 * 1. 如果是收到信号退出的，timeo 为剩余的 jiffies。
                 * 2. 如果使用了 SO_SNDTIMEO 选项，超时后退出，timeo为0。
                 * 3. 如果没有使用 SO_SNDTIMEO 选项，timeo 为无穷大，即 MAX_SCHEDULE_TIMEOUT，
                 *    那么返回值也是这个，而超时时间不定。为了无限阻塞，需要上面的 while 循环。
                 */
                timeo = schedule_timeout(timeo);
                lock_sock(sk);
                /* 如果进程有待处理的信号，或者 SO_SNDTIMEO 超时了，退出循环，之后会返回错误码 */
                if (signal_pending(current) || !timeo)
                        break;
                prepare_to_wait(sk_sleep(sk), &wait, TASK_INTERRUPTIBLE);
        }
        finish_wait(sk_sleep(sk), &wait);
        sk->sk_write_pending -= writebias;
        return timeo;
}

```

1. 将 sock->wq->wait 加入名为 wait 的等待任务链表, 并设置当前等待任务是可以响应中断.
2. 如果 sk->sk_state 为 TCPF_SYN_SENT 或 TCPF_SYN_RECV, 进程进入睡眠.
3. 进入睡眠，直到超时或收到信号，或者被I/O事件处理函数唤醒。
    1. 如果是收到信号退出的, 或者设置了 SO_SNDTIMEO 选项导致超时, 退出循环。
    2. 如果没有使用 SO_SNDTIMEO 选项, timeo 为无穷大，即 MAX_SCHEDULE_TIMEOUT，会重置设置 wait->flags, 设置 sk->state 并继续循环.

问题: sk->sk_state 后续状态变化在哪里处理?



三次握手中，当客户端收到 SYNACK、发出 ACK 后，连接就成功建立了。
此时连接的状态从 TCP_SYN_SENT 或 TCP_SYN_RECV 变为 TCP_ESTABLISHED，sock的状态发生变化，
会调用 sock_def_wakeup() 来处理连接状态变化事件，唤醒进程，connect() 就能成功返回了


##附录

/* This will initiate an outgoing connection. */
int tcp_v4_connect(struct sock *sk, struct sockaddr *uaddr, int addr_len)
{
	struct sockaddr_in *usin = (struct sockaddr_in *)uaddr;
	struct inet_sock *inet = inet_sk(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	__be16 orig_sport, orig_dport;
	__be32 daddr, nexthop;
	struct flowi4 *fl4;
	struct rtable *rt;
	int err;
	struct ip_options_rcu *inet_opt;

    //校验长度
	if (addr_len < sizeof(struct sockaddr_in))
		return -EINVAL;

    //校验协议族
	if (usin->sin_family != AF_INET)
		return -EAFNOSUPPORT;

	nexthop = daddr = usin->sin_addr.s_addr;
	inet_opt = rcu_dereference_protected(inet->inet_opt,
					     sock_owned_by_user(sk));
	if (inet_opt && inet_opt->opt.srr) { /* 如果使用源地址路由 */
		if (!daddr)
			return -EINVAL;
		nexthop = inet_opt->opt.faddr; /* 设置下一跳地址 */
	}

    //本端端口
	orig_sport = inet->inet_sport;
    //服务器端口
	orig_dport = usin->sin_port;
	fl4 = &inet->cork.fl.u.ip4;
    //查找路由缓存项
	rt = ip_route_connect(fl4, nexthop, inet->inet_saddr,
			      RT_CONN_FLAGS(sk), sk->sk_bound_dev_if,
			      IPPROTO_TCP,
			      orig_sport, orig_dport, sk);
	if (IS_ERR(rt)) {
		err = PTR_ERR(rt);
		if (err == -ENETUNREACH)
			IP_INC_STATS(sock_net(sk), IPSTATS_MIB_OUTNOROUTES);
		return err;
	}

    //多播或广播返回错误
	if (rt->rt_flags & (RTCF_MULTICAST | RTCF_BROADCAST)) {
		ip_rt_put(rt);
		return -ENETUNREACH;
	}

    //如果没有使用源路由选项
	if (!inet_opt || !inet_opt->opt.srr)
		daddr = fl4->daddr;

    //本端 IP 为空
	if (!inet->inet_saddr)
		inet->inet_saddr = fl4->saddr;
    //sk->sk_rcv_saddr = inet->inet_saddr
	sk_rcv_saddr_set(sk, inet->inet_saddr);

    //TODO
	if (tp->rx_opt.ts_recent_stamp && inet->inet_daddr != daddr) {
		/* Reset inherited state */
		tp->rx_opt.ts_recent	   = 0;
		tp->rx_opt.ts_recent_stamp = 0;
		if (likely(!tp->repair))
			tp->write_seq	   = 0;
	}

	if (tcp_death_row.sysctl_tw_recycle &&
	    !tp->rx_opt.ts_recent_stamp && fl4->daddr == daddr)
        /*设置
         * tp->rx_opt.ts_recent_stamp = tm->tcpm_ts_stamp;
         * tp->rx_opt.ts_recent = tm->tcpm_ts;
         */
		tcp_fetch_timewait_stamp(sk, &rt->dst);

	inet->inet_dport = usin->sin_port;
    //sk->sk_daddr = addr
	sk_daddr_set(sk, daddr);

	inet_csk(sk)->icsk_ext_hdr_len = 0;
	if (inet_opt)
		inet_csk(sk)->icsk_ext_hdr_len = inet_opt->opt.optlen;

    //TCP_MSS_DEFAULT = 536
	tp->rx_opt.mss_clamp = TCP_MSS_DEFAULT;

	/* Socket identity is still unknown (sport may be zero).
	 * However we set state to SYN-SENT and not releasing socket
	 * lock select source port, enter ourselves into the hash tables and
	 * complete initialization after this.
	 */
	tcp_set_state(sk, TCP_SYN_SENT);
    //TODO
	err = inet_hash_connect(&tcp_death_row, sk);
	if (err)
		goto failure;

    //sk->sk_txhash = net_tx_rndhash();
	sk_set_txhash(sk);

    //TODO
	rt = ip_route_newports(fl4, rt, orig_sport, orig_dport,
			       inet->inet_sport, inet->inet_dport, sk);
	if (IS_ERR(rt)) {
		err = PTR_ERR(rt);
		rt = NULL;
		goto failure;
	}
	/* OK, now commit destination to socket.  */
	sk->sk_gso_type = SKB_GSO_TCPV4;
    //TODO /* 根据路由缓存，设置网卡的特性 */
	sk_setup_caps(sk, &rt->dst);

    //根据四元组, 设置本端的初始序列号
	if (!tp->write_seq && likely(!tp->repair))
		tp->write_seq = secure_tcp_sequence_number(inet->inet_saddr,
							   inet->inet_daddr,
							   inet->inet_sport,
							   usin->sin_port);

	inet->inet_id = tp->write_seq ^ jiffies;

    //TODO
	err = tcp_connect(sk);

	rt = NULL;
	if (err)
		goto failure;

	return 0;

failure:
	/*
	 * This unhashes the socket and releases the local port,
	 * if necessary.
	 */
	tcp_set_state(sk, TCP_CLOSE);
	ip_rt_put(rt);
	sk->sk_route_caps = 0;
	inet->inet_dport = 0;
	return err;
}


void tcp_fetch_timewait_stamp(struct sock *sk, struct dst_entry *dst)
{
	struct tcp_metrics_block *tm;

	rcu_read_lock();
    /* 遍历 tcp_metrics_hash[hash].chain 找到 saddr, daddr, net 对应的 tcp_metrics_block
     * 如果不存在就创建之
     */
	tm = tcp_get_metrics(sk, dst, true);
	if (tm) {
		struct tcp_sock *tp = tcp_sk(sk);

		if ((u32)get_seconds() - tm->tcpm_ts_stamp <= TCP_PAWS_MSL) {
			tp->rx_opt.ts_recent_stamp = tm->tcpm_ts_stamp;
			tp->rx_opt.ts_recent = tm->tcpm_ts;
		}
	}
	rcu_read_unlock();
}


/*
 * Bind a port for a connect operation and hash it.
 */
int inet_hash_connect(struct inet_timewait_death_row *death_row,
		      struct sock *sk)
{
	u32 port_offset = 0;

	if (!inet_sk(sk)->inet_num)
		port_offset = inet_sk_port_offset(sk);
	return __inet_hash_connect(death_row, sk, port_offset,
				   __inet_check_established);
}

/* Build a SYN and send it off. */
int tcp_connect(struct sock *sk)
{
	struct tcp_sock *tp = tcp_sk(sk);
	struct sk_buff *buff;
	int err;

	tcp_connect_init(sk);

	if (unlikely(tp->repair)) {
		tcp_finish_connect(sk, NULL);
		return 0;
	}

	buff = sk_stream_alloc_skb(sk, 0, sk->sk_allocation, true);
	if (unlikely(!buff))
		return -ENOBUFS;

	tcp_init_nondata_skb(buff, tp->write_seq++, TCPHDR_SYN);
	tp->retrans_stamp = tcp_time_stamp;
	tcp_connect_queue_skb(sk, buff);
	tcp_ecn_send_syn(sk, buff);

	/* Send off SYN; include data in Fast Open. */
	err = tp->fastopen_req ? tcp_send_syn_data(sk, buff) :
	      tcp_transmit_skb(sk, buff, 1, sk->sk_allocation);
	if (err == -ECONNREFUSED)
		return err;

	/* We change tp->snd_nxt after the tcp_transmit_skb() call
	 * in order to make this packet get counted in tcpOutSegs.
	 */
	tp->snd_nxt = tp->write_seq;
	tp->pushed_seq = tp->write_seq;
	TCP_INC_STATS(sock_net(sk), TCP_MIB_ACTIVEOPENS);

	/* Timer for repeating the SYN until an answer. */
	inet_csk_reset_xmit_timer(sk, ICSK_TIME_RETRANS,
				  inet_csk(sk)->icsk_rto, TCP_RTO_MAX);
	return 0;
}


/* Do all connect socket setups that can be done AF independent. */
static void tcp_connect_init(struct sock *sk)
{
	const struct dst_entry *dst = __sk_dst_get(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	__u8 rcv_wscale;

	/* We'll fix this up when we get a response from the other end.
	 * See tcp_input.c:tcp_rcv_state_process case TCP_SYN_SENT.
	 */
	tp->tcp_header_len = sizeof(struct tcphdr) +
		(sysctl_tcp_timestamps ? TCPOLEN_TSTAMP_ALIGNED : 0);

#ifdef CONFIG_TCP_MD5SIG
	if (tp->af_specific->md5_lookup(sk, sk))
		tp->tcp_header_len += TCPOLEN_MD5SIG_ALIGNED;
#endif

	/* If user gave his TCP_MAXSEG, record it to clamp */
	if (tp->rx_opt.user_mss)
		tp->rx_opt.mss_clamp = tp->rx_opt.user_mss;
	tp->max_window = 0;
    //初始化 inet_csk(sk)->icsk_mtup
	tcp_mtup_init(sk);
    //设置MSS. tcp_sk(sk)->mss_cache 为 mss_now
	tcp_sync_mss(sk, dst_mtu(dst));

    /*
     * 从 tcp_cong_list 找到 dst_metric(dst, RTAX_CC_ALGO) 对应的 ca
     * 初始化:
     *  icsk->icsk_ca_ops = ca
     *  icsk->icsk_ca_dst_locked = tcp_ca_dst_locked(dst);
     */
	tcp_ca_dst_init(sk, dst);

	if (!tp->window_clamp)
		tp->window_clamp = dst_metric(dst, RTAX_WINDOW);
    //设置 tp->advmss = dst_metric_raw(dst, RTAX_ADVMSS) :? dst->ops->default_advmss(dst);
	tp->advmss = dst_metric_advmss(dst);
	if (tp->rx_opt.user_mss && tp->rx_opt.user_mss < tp->advmss)
		tp->advmss = tp->rx_opt.user_mss;

    /*
     * 设置 inet_csk(sk)->icsk_ack.rcv_mss 为
     *  max(min(tp->advmss, tp->mss_cache, tp->rcv_wnd / 2, TCP_MSS_DEFAULT), TCP_MIN_MSS)
     */
	tcp_initialize_rcv_mss(sk);

	/* limit the window selection if the user enforce a smaller rx buffer */
	if (sk->sk_userlocks & SOCK_RCVBUF_LOCK &&
	    (tp->window_clamp > tcp_full_space(sk) || tp->window_clamp == 0))
        /*
         * tp->window_clamp = sysctl_tcp_adv_win_scale<=0 ?
         * (sk->sk_rcvbuf>>(-sysctl_tcp_adv_win_scale)) :
         * sk->sk_rcvbuf - (space>>sysctl_tcp_adv_win_scale);
         */
		tp->window_clamp = tcp_full_space(sk);

    //TODO
	tcp_select_initial_window(tcp_full_space(sk),
				  tp->advmss - (tp->rx_opt.ts_recent_stamp ? tp->tcp_header_len - sizeof(struct tcphdr) : 0),
				  &tp->rcv_wnd,
				  &tp->window_clamp,
				  sysctl_tcp_window_scaling,
				  &rcv_wscale,
				  dst_metric(dst, RTAX_INITRWND));

	tp->rx_opt.rcv_wscale = rcv_wscale;
	tp->rcv_ssthresh = tp->rcv_wnd;

	sk->sk_err = 0;
    //清除 sk->sk_flags 的 SOCK_DONE 位
	sock_reset_flag(sk, SOCK_DONE);
	tp->snd_wnd = 0;
    // tp->snd_wl1 = 0
	tcp_init_wl(tp, 0);
	tp->snd_una = tp->write_seq;
	tp->snd_sml = tp->write_seq;
	tp->snd_up = tp->write_seq;
	tp->snd_nxt = tp->write_seq;

	if (likely(!tp->repair))
		tp->rcv_nxt = 0;
	else
		tp->rcv_tstamp = tcp_time_stamp;
	tp->rcv_wup = tp->rcv_nxt;
	tp->copied_seq = tp->rcv_nxt;

	inet_csk(sk)->icsk_rto = TCP_TIMEOUT_INIT;
	inet_csk(sk)->icsk_retransmits = 0;
    /*
	 * tp->retrans_out = 0;
	 * tp->lost_out = 0;
	 * tp->undo_marker = 0;
	 * tp->undo_retrans = -1;
	 * tp->fackets_out = 0;
	 * tp->sacked_out = 0;
     */
	tcp_clear_retrans(tp);
}

int __inet_hash_connect(struct inet_timewait_death_row *death_row,
		struct sock *sk, u32 port_offset,
		int (*check_established)(struct inet_timewait_death_row *,
			struct sock *, __u16, struct inet_timewait_sock **))
{
	struct inet_hashinfo *hinfo = death_row->hashinfo;
	struct inet_timewait_sock *tw = NULL;
	struct inet_bind_hashbucket *head;
	int port = inet_sk(sk)->inet_num;
	struct net *net = sock_net(sk);
	struct inet_bind_bucket *tb;
	u32 remaining, offset;
	int ret, i, low, high;
	static u32 hint;

	if (port) {
		head = &hinfo->bhash[inet_bhashfn(net, port,
						  hinfo->bhash_size)];
		tb = inet_csk(sk)->icsk_bind_hash;
		spin_lock_bh(&head->lock);
		if (sk_head(&tb->owners) == sk && !sk->sk_bind_node.next) {
			inet_ehash_nolisten(sk, NULL);
			spin_unlock_bh(&head->lock);
			return 0;
		}
		spin_unlock(&head->lock);
		/* No definite answer... Walk to established hash table */
		ret = check_established(death_row, sk, port, NULL);
		local_bh_enable();
		return ret;
	}

	inet_get_local_port_range(net, &low, &high);
	high++; /* [32768, 60999] -> [32768, 61000[ */
	remaining = high - low;
	if (likely(remaining > 1))
		remaining &= ~1U;

	offset = (hint + port_offset) % remaining;
	/* In first pass we try ports of @low parity.
	 * inet_csk_get_port() does the opposite choice.
	 */
	offset &= ~1U;
other_parity_scan:
	port = low + offset;
	for (i = 0; i < remaining; i += 2, port += 2) {
		if (unlikely(port >= high))
			port -= remaining;
		if (inet_is_local_reserved_port(net, port))
			continue;
		head = &hinfo->bhash[inet_bhashfn(net, port,
						  hinfo->bhash_size)];
		spin_lock_bh(&head->lock);

		/* Does not bother with rcv_saddr checks, because
		 * the established check is already unique enough.
		 */
		inet_bind_bucket_for_each(tb, &head->chain) {
			if (net_eq(ib_net(tb), net) && tb->port == port) {
				if (tb->fastreuse >= 0 ||
				    tb->fastreuseport >= 0)
					goto next_port;
				WARN_ON(hlist_empty(&tb->owners));
				if (!check_established(death_row, sk,
						       port, &tw))
					goto ok;
				goto next_port;
			}
		}

		tb = inet_bind_bucket_create(hinfo->bind_bucket_cachep,
					     net, head, port);
		if (!tb) {
			spin_unlock_bh(&head->lock);
			return -ENOMEM;
		}
		tb->fastreuse = -1;
		tb->fastreuseport = -1;
		goto ok;
next_port:
		spin_unlock_bh(&head->lock);
		cond_resched();
	}

	offset++;
	if ((offset & 1) && remaining > 1)
		goto other_parity_scan;

	return -EADDRNOTAVAIL;

ok:
	hint += i + 2;

	/* Head lock still held and bh's disabled */
	inet_bind_hash(sk, tb, port);
	if (sk_unhashed(sk)) {
		inet_sk(sk)->inet_sport = htons(port);
		inet_ehash_nolisten(sk, (struct sock *)tw);
	}
	if (tw)
		inet_twsk_bind_unhash(tw, hinfo);
	spin_unlock(&head->lock);
	if (tw)
		inet_twsk_deschedule_put(tw);
	local_bh_enable();
	return 0;
}
