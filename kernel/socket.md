
## socket 创建

SYSCALL_DEFINE3(socket, int, family, int, type, int, protocol)
	sock_create(family, type, protocol, &sock)
	    __sock_create(current->nsproxy->net_ns, family, type, protocol, res, 0)
            security_socket_create(family, type, protocol, 0)
	        sock = sock_alloc()
            sock->type = type
	        net_families[family]->create(net, sock, protocol, 0)
                inet_family_ops->create(net, sock, protocol, 0)
                    inet_create(net, sock, protocol, 0)
                        sock->state = SS_UNCONNECTED;
                        if TCP:
                            sock->ops = inet_stream_ops
                        elif UDP :
                            sock->ops = inet_dgram_ops
                        elif ICMP :
                            sock->ops = inet_dgram_ops
                        elif IP :
                            sock->ops = inet_sockraw_ops
                        sk = sk_alloc(net, PF_INET, GFP_KERNEL, answer_prot, 0)
                            sk_prot_alloc(prot, priority | __GFP_ZERO, family)
                                if prot->slab != NULL:
                                    kmem_cache_alloc(slab, priority & ~__GFP_ZERO);
                                else
                                    kmalloc(prot->obj_size, priority)
                            if TCP:
                                sk->sk_prot = sk->sk_prot_creator = tcp_prot
                            elif UDP :
                                sk->sk_prot = sk->sk_prot_creator = udp_prot
                            elif ICMP :
                                sk->sk_prot = sk->sk_prot_creator = ping_prot
                            elif IP :
                                sk->sk_prot = sk->sk_prot_creator = raw_prot
                            sk->sk_net = net
                        sock_init_data(sock, sk);
                        if SOCK_RAW == sock->type:
                            sk->sk_prot->hash(sk);
                                if TCP:
                                    tcp_prot->hash(sk)
                                        inet_hash(sk)
                                elif UDP :
                                    udp_prot->hash(sk)
                                elif ICMP :
                                    ping_prot->hash(sk)
                                elif IP :
                                    raw_prot->hash(sk)
                        sk->sk_prot->init(sk)
                            if TCP:
                                tcp_prot->init(sk)
                                    tcp_v4_init_sock(sk)
                                        tcp_init_sock(sk)
                            elif UDP :
                                udp_prot->init(sk)
                            elif ICMP :
                                ping_prot->init(sk)
                            elif IP :
                                raw_prot->init(sk)
	        security_socket_post_create(sock, family, type, protocol, 0)
	sock_map_fd(sock, flags & (O_CLOEXEC | O_NONBLOCK))
	    int fd = get_unused_fd_flags(flags)
	    newfile = sock_alloc_file(sock, flags, NULL)
		fd_install(fd, newfile)
            __fd_install(current->files, fd, file);
                current->files->fdt[fd] = file

主要步骤

1. 为 sock 分配内存
2. 将 sock 与 inet_sock 和 socket 建立关联
3. sock 与具体协议建立关联, 并初始化对应协议
4. 将 sock 与 file 关联.

inet->inet_sport = htons(inet->inet_num);



## 关键函数

void sock_init_data(struct socket *sock, struct sock *sk)

    初始化 sk
    sk->sk_socket = sock
    sk->sk_rcvbuf           =       sysctl_rmem_default;
    sk->sk_sndbuf           =       sysctl_wmem_default;
    sk->sk_state            =       TCP_CLOSE;

    sk->sk_type             =       sock->type;
    sk->sk_wq               =       sock->wq;
    sock->sk                =       sk;

    sk->sk_destruct         =       sock_def_destruct;
    sk->sk_destruct         =       inet_sock_destruct;
    sk->sk_protocol         =       protocol;
    sk->sk_backlog_rcv      =       sk->sk_prot->backlog_rcv;
