
## listen

SYSCALL_DEFINE2(listen, int, fd, int, backlog)
    sock = sockfd_lookup_light(fd, &err, &fput_needed);
    security_socket_listen(sock, backlog);
    sock->ops->listen(sock, backlog)
        if TCP:
            inet_stream_ops->listen(sock, backlog)
                inet_listen(sock, backlog)
                    if sock->sk->sk_state != TCP_LISTEN:
                        inet_csk_listen_start(sk, backlog)
                    sk->sk_max_ack_backlog = backlog;
        elif UDP :
            inet_dgram_ops->listen(sock, backlog)
                sock_no_listen
        elif ICMP :
            inet_dgram_ops->listen(sock, backlog)
                sock_no_listen
        elif IP :
            inet_sockraw_ops->listen(sock, backlog)
                sock_no_listen

    fput_light(sock->file, fput_needed);

主要步骤

1. 找到 fd 对应的 file(current->files->fdt[fd])
2. 从 file 定位到 socket(file->private_data)
3. 调用对应协议的 listen 函数(只有 tcp 支持 listen). 如果当前 socket 已经处于 listen, 那么, 再次调用 listen 可以修改 backlog.

### fastopen


    /* Bit Flags for sysctl_tcp_fastopen */
    #define TFO_CLIENT_ENABLE       1
    #define TFO_SERVER_ENABLE       2
    #define TFO_CLIENT_NO_COOKIE    4

如果 sysctl_tcp_fastopen 打开 TFO_SERVER_ENABLE 和 TFO_SERVER_WO_SOCKOPT1 选项
    inet_csk(sk)->icsk_accept_queue->fastopenq.max_qlen = min(backlog, somaxconn)
如果 sysctl_tcp_fastopen 打开 TFO_SERVER_ENABLE 和 TFO_SERVER_WO_SOCKOPT2 选项
    inet_csk(sk)->icsk_accept_queue->fastopenq.max_qlen = min(sysctl_tcp_fastopen >> 16, somaxconn)
tcp_fastopen_init_key_once(true)

关键函数

int inet_csk_listen_start(struct sock *sk, int backlog)

    1. 初始化 inet_csk(sk)->icsk_accept_queue 的相关属性.
    2. 修改 sk->sk_state 为 TCP_LISTEN
    3. inet_csk(sk)->icsk_ack 清零
    4. 记录 sk 的端口可重用性
    5. 把 sock 链接入监听哈希表中 (sk->sk_prot->h.hashinfo->listening_hash[inet_sk_listen_hashfn(sk)])

    if (!sk->sk_prot->get_port(sk, inet->inet_num))
            inet->inet_sport = htons(inet->inet_num);
            //sk_dst_reset(sk);
            sk->sk_tx_queue_mapping = -1;
            sk->sk_dst_cache = NULL
            //sk->sk_prot->hash(sk);
            if TCP:
                inet_hash(sk)

int inet_hash(struct sock *sk)

    1. 如果支持端口重用: 将 sk 加入对应的 sock 重用组.
    遍历 hashinfo->listening_hash[inet_sk_listen_hashfn(sk)], 检查两个 sk
    是否满足端口重用条件, 如果满足, 将 sk->sk_reuseport_cb 加入对应的 sock_reuseport 组
    2. 将 sk 加入 sk->sk_prot->h.hashinfo->listening_hash[inet_sk_listen_hashfn(sk)]->head
    3. sock_net(sk)->core.inuse->val[sk->sk_prot->inuse_idx] += val 每个 cpu 变量

