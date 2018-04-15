
socket

    sk_backlog : 循环链表
    sk_backlog.len : 每收到一个 skb, 加 skb->truesize

tcp_data_queue
    tcp_event_data_recv

tcp_v4_rcv
    __inet_lookup_skb
        __inet_lookup
            sk =  __inet_lookup_established
                从 hashinfo->ehash[slot] 中查找
            if sk == null:
                sk = __inet_lookup_listener
                    从链表 hashinfo->listening_hash[hash] 中查找
    tcp_v4_do_rcv
        if  sk->sk_state == TCP_ESTABLISHED:
            tcp_rcv_established
            返回 0
        elif sk->sk_state == TCP_LISTEN
            tcp_v4_hnd_req
                在 inet_csk(sk)->icsk_accept_queue.listen_opt->syn_table 和 tcp_hashinfo->ehash[slot] 中查找
                如果找到:
                    sock_rps_save_rxhash(sk, skb);
                    tcp_child_process(sk, nsk, skb)
                如果没有找到
                    tcp_rcv_state_process
        else
            tcp_rcv_state_process

tcp_rcv_synsent_state_process
    tcp_ack
        tcp_cong_avoid

tcp_rcv_established
    tcp_ack
        tcp_cong_avoid

tcp_rcv_state_process
    tcp_ack
        tcp_cong_avoid

tcp_rcv_established
    快路径:
        tcp_event_data_recv
    慢路径:
        tcp_data_queue(sk, skb);

                tcp_event_data_recv


快路径条件:

    0. tp->pred_flags 与 tcp 头选项部分的值一致
    1. 收到的 sock 的 seq 就是期望接收的下一个 seq; skb->seq == tp->rcv_nxt
    2. 要发送的 seq 就是 sock ACK 的 seq ; skb->ack_seq, tp->snd_nxt
    3. 收到的包包含 时间戳
    4. tp->rx_opt.rcv_tsval - tp->rx_opt.ts_recent >= 0

static void tcp_event_data_recv(struct sock *sk, struct sk_buff *skb)

static int tcp_queue_rcv(struct sock *sk, struct sk_buff *skb, int hdrlen, bool *fragstolen)

    将 skb 与 sk->sk_receive_queue 的最后一个包尽量合并,
    如果合并成功, 返回 true
    如果合并失败, 将 skb 加入 sk->sk_receive_queue, 返回 false;

static bool tcp_try_coalesce(struct sock *sk, struct sk_buff *to, struct sk_buff *from, bool *fragstolen)

    满足一定条件, 将 from 包合并到 to 中.

    1. from 不是 fin 包
    2. to 期望的下一个包是 from(即 seq 连续)
    3. from, to 没有 frags 为 0
    4. skb_shinfo(to)->nr_frags + skb_shinfo(from)->nr_frags >= MAX_SKB_FRAGS
