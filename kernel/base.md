## systemtap 关注点

需要注意的关注 __fd_install 中 fd resize 是否会成为瓶颈, 因为同时创建
大量文件, 进行 file 的 resize 会阻塞

int __sk_mem_schedule(struct sock *sk, int size, int kind) 存储分配



## 数据结构

net/ipv4/af_inet.c


static struct vfsmount *sock_mnt __read_mostly;

-----------------------------------------------------

static const struct net_proto_family __rcu *net_families[NPROTO] __read_mostly;

struct net_proto_family {
	int		family;
	int		(*create)(struct net *net, struct socket *sock,
				  int protocol, int kern);
	struct module	*owner;
};

static const struct net_proto_family inet_family_ops = {
        .family = PF_INET,
        .create = inet_create,
        .owner  = THIS_MODULE,
};

初始化在 sock_register 初始化. 其中, socket 为 inet_family_ops. 即 net_families[inet_family_ops->family] = inet_family_ops

-----------------------------------------------------

/* This is used to register socket interfaces for IP protocols.  */
struct inet_protosw {
        struct list_head list;

        /* These two fields form the lookup key.  */
        unsigned short   type;     /* This is the 2nd argument to socket(2). */
        unsigned short   protocol; /* This is the L4 protocol number.  */

        struct proto     *prot;
        const struct proto_ops *ops;

        unsigned char    flags;      /* See INET_PROTOSW_* below.  */
};

/* Upon startup we insert all the elements in inetsw_array[] into
 * the linked list inetsw.
 */
static struct inet_protosw inetsw_array[] =
{
         {
                 .type =       SOCK_STREAM,
                 .protocol =   IPPROTO_TCP,
                 .prot =       &tcp_prot,
                 .ops =        &inet_stream_ops,
                 .flags =      INET_PROTOSW_PERMANENT |
                               INET_PROTOSW_ICSK,
         },

         {
                 .type =       SOCK_DGRAM,
                 .protocol =   IPPROTO_UDP,
                 .prot =       &udp_prot,
                 .ops =        &inet_dgram_ops,
                 .flags =      INET_PROTOSW_PERMANENT,
        },

        {
                 .type =       SOCK_DGRAM,
                 .protocol =   IPPROTO_ICMP,
                 .prot =       &ping_prot,
                 .ops =        &inet_dgram_ops,
                 .flags =      INET_PROTOSW_REUSE,
        },

        {
                .type =       SOCK_RAW,
                .protocol =   IPPROTO_IP,        /* wild card */
                .prot =       &raw_prot,
                .ops =        &inet_sockraw_ops,
                .flags =      INET_PROTOSW_REUSE,
        }
};

#define INETSW_ARRAY_LEN ARRAY_SIZE(inetsw_array)

static struct list_head inetsw[SOCK_MAX];

inetsw 在 inet_register_protosw 中, 将 inetsw_array 全部加入 inetsw 中.

## OPS

### STREAM

const struct proto_ops inet_stream_ops = {
        .family            = PF_INET,
        .owner             = THIS_MODULE,
        .release           = inet_release,
        .bind              = inet_bind,
        .connect           = inet_stream_connect,
        .socketpair        = sock_no_socketpair,
        .accept            = inet_accept,
        .getname           = inet_getname,
        .poll              = tcp_poll,
        .ioctl             = inet_ioctl,
        .listen            = inet_listen,
        .shutdown          = inet_shutdown,
        .setsockopt        = sock_common_setsockopt,
        .getsockopt        = sock_common_getsockopt,
        .sendmsg           = inet_sendmsg,
        .recvmsg           = inet_recvmsg,
        .mmap              = sock_no_mmap,
        .sendpage          = inet_sendpage,
        .splice_read       = tcp_splice_read,
#ifdef CONFIG_COMPAT
        .compat_setsockopt = compat_sock_common_setsockopt,
        .compat_getsockopt = compat_sock_common_getsockopt,
        .compat_ioctl      = inet_compat_ioctl,
#endif
};
EXPORT_SYMBOL(inet_stream_ops);

### datagram

const struct proto_ops inet_dgram_ops = {
        .family            = PF_INET,
        .owner             = THIS_MODULE,
        .release           = inet_release,
        .bind              = inet_bind,
        .connect           = inet_dgram_connect,
        .socketpair        = sock_no_socketpair,
        .accept            = sock_no_accept,
        .getname           = inet_getname,
        .poll              = udp_poll,
        .ioctl             = inet_ioctl,
        .listen            = sock_no_listen,
        .shutdown          = inet_shutdown,
        .setsockopt        = sock_common_setsockopt,
        .getsockopt        = sock_common_getsockopt,
        .sendmsg           = inet_sendmsg,
        .recvmsg           = inet_recvmsg,
        .mmap              = sock_no_mmap,
        .sendpage          = inet_sendpage,
#ifdef CONFIG_COMPAT
        .compat_setsockopt = compat_sock_common_setsockopt,
        .compat_getsockopt = compat_sock_common_getsockopt,
        .compat_ioctl      = inet_compat_ioctl,
#endif
};
EXPORT_SYMBOL(inet_dgram_ops);

### Raw

/*
 * For SOCK_RAW sockets; should be the same as inet_dgram_ops but without
 * udp_poll
 */
static const struct proto_ops inet_sockraw_ops = {
        .family            = PF_INET,
        .owner             = THIS_MODULE,
        .release           = inet_release,
        .bind              = inet_bind,
        .connect           = inet_dgram_connect,
        .socketpair        = sock_no_socketpair,
        .accept            = sock_no_accept,
        .getname           = inet_getname,
        .poll              = datagram_poll,
        .ioctl             = inet_ioctl,
        .listen            = sock_no_listen,
        .shutdown          = inet_shutdown,
        .setsockopt        = sock_common_setsockopt,
        .getsockopt        = sock_common_getsockopt,
        .sendmsg           = inet_sendmsg,
        .recvmsg           = inet_recvmsg,
        .mmap              = sock_no_mmap,
        .sendpage          = inet_sendpage,
#ifdef CONFIG_COMPAT
        .compat_setsockopt = compat_sock_common_setsockopt,
        .compat_getsockopt = compat_sock_common_getsockopt,
        .compat_ioctl      = inet_compat_ioctl,
#endif
};

## Proto

其中 proto 定义在 include/net/sock.h


### ip 协议

    struct proto raw_prot = {
            .name              = "RAW",
            .owner             = THIS_MODULE,
            .close             = raw_close,
            .destroy           = raw_destroy,
            .connect           = ip4_datagram_connect,
            .disconnect        = udp_disconnect,
            .ioctl             = raw_ioctl,
            .init              = raw_init,
            .setsockopt        = raw_setsockopt,
            .getsockopt        = raw_getsockopt,
            .sendmsg           = raw_sendmsg,
            .recvmsg           = raw_recvmsg,
            .bind              = raw_bind,
            .backlog_rcv       = raw_rcv_skb,
            .release_cb        = ip4_datagram_release_cb,
            .hash              = raw_hash_sk,
            .unhash            = raw_unhash_sk,
            .obj_size          = sizeof(struct raw_sock),
            .h.raw_hash        = &raw_v4_hashinfo,
    #ifdef CONFIG_COMPAT
            .compat_setsockopt = compat_raw_setsockopt,
            .compat_getsockopt = compat_raw_getsockopt,
            .compat_ioctl      = compat_raw_ioctl,
    #endif
    };

### tcp 协议

    struct proto tcp_prot = {
            .name                   = "TCP",
            .owner                  = THIS_MODULE,
            .close                  = tcp_close,
            .connect                = tcp_v4_connect,
            .disconnect             = tcp_disconnect,
            .accept                 = inet_csk_accept,
            .ioctl                  = tcp_ioctl,
            .init                   = tcp_v4_init_sock,
            .destroy                = tcp_v4_destroy_sock,
            .shutdown               = tcp_shutdown,
            .setsockopt             = tcp_setsockopt,
            .getsockopt             = tcp_getsockopt,
            .recvmsg                = tcp_recvmsg,
            .sendmsg                = tcp_sendmsg,
            .sendpage               = tcp_sendpage,
            .backlog_rcv            = tcp_v4_do_rcv,
            .release_cb             = tcp_release_cb,
            .hash                   = inet_hash,
            .unhash                 = inet_unhash,
            .get_port               = inet_csk_get_port,
            .enter_memory_pressure  = tcp_enter_memory_pressure,
            .stream_memory_free     = tcp_stream_memory_free,
            .sockets_allocated      = &tcp_sockets_allocated,
            .orphan_count           = &tcp_orphan_count,
            .memory_allocated       = &tcp_memory_allocated,
            .memory_pressure        = &tcp_memory_pressure,
            .sysctl_mem             = sysctl_tcp_mem,
            .sysctl_wmem            = sysctl_tcp_wmem,
            .sysctl_rmem            = sysctl_tcp_rmem,
            .max_header             = MAX_TCP_HEADER,
            .obj_size               = sizeof(struct tcp_sock),
            .slab_flags             = SLAB_DESTROY_BY_RCU,
            .twsk_prot              = &tcp_timewait_sock_ops,
            .rsk_prot               = &tcp_request_sock_ops,
            .h.hashinfo             = &tcp_hashinfo,
            .no_autobind            = true,
    #ifdef CONFIG_COMPAT
            .compat_setsockopt      = compat_tcp_setsockopt,
            .compat_getsockopt      = compat_tcp_getsockopt,
    #endif
            .diag_destroy           = tcp_abort,
    };


### udp 协议

    struct proto udp_prot = {
            .name              = "UDP",
            .owner             = THIS_MODULE,
            .close             = udp_lib_close,
            .connect           = ip4_datagram_connect,
            .disconnect        = udp_disconnect,
            .ioctl             = udp_ioctl,
            .destroy           = udp_destroy_sock,
            .setsockopt        = udp_setsockopt,
            .getsockopt        = udp_getsockopt,
            .sendmsg           = udp_sendmsg,
            .recvmsg           = udp_recvmsg,
            .sendpage          = udp_sendpage,
            .backlog_rcv       = __udp_queue_rcv_skb,
            .release_cb        = ip4_datagram_release_cb,
            .hash              = udp_lib_hash,
            .unhash            = udp_lib_unhash,
            .rehash            = udp_v4_rehash,
            .get_port          = udp_v4_get_port,
            .memory_allocated  = &udp_memory_allocated,
            .sysctl_mem        = sysctl_udp_mem,
            .sysctl_wmem       = &sysctl_udp_wmem_min,
            .sysctl_rmem       = &sysctl_udp_rmem_min,
            .obj_size          = sizeof(struct udp_sock),
            .slab_flags        = SLAB_DESTROY_BY_RCU,
            .h.udp_table       = &udp_table,
    #ifdef CONFIG_COMPAT
            .compat_setsockopt = compat_udp_setsockopt,
            .compat_getsockopt = compat_udp_getsockopt,
    #endif
            .clear_sk          = sk_prot_clear_portaddr_nulls,
    };

### icmp 协议

    struct proto ping_prot = {
            .name =         "PING",
            .owner =        THIS_MODULE,
            .init =         ping_init_sock,
            .close =        ping_close,
             .connect =      ip4_datagram_connect,
             .disconnect =   udp_disconnect,
             .setsockopt =   ip_setsockopt,
             .getsockopt =   ip_getsockopt,
             .sendmsg =      ping_v4_sendmsg,
             .recvmsg =      ping_recvmsg,
             .bind =         ping_bind,
             .backlog_rcv =  ping_queue_rcv_skb,
             .release_cb =   ip4_datagram_release_cb,
             .hash =         ping_hash,
             .unhash =       ping_unhash,
             .get_port =     ping_get_port,
             .obj_size =     sizeof(struct inet_sock),
    };

-------------------------------------------------------------
/**
 * enum sock_type - Socket types
 * @SOCK_STREAM: stream (connection) socket
 * @SOCK_DGRAM: datagram (conn.less) socket
 * @SOCK_RAW: raw socket
 * @SOCK_RDM: reliably-delivered message
 * @SOCK_SEQPACKET: sequential packet socket
 * @SOCK_DCCP: Datagram Congestion Control Protocol socket
 * @SOCK_PACKET: linux specific way of getting packets at the dev level.
 *                For writing rarp and other similar things on the user level.
 *
 * When adding some new socket type please
 * grep ARCH_HAS_SOCKET_TYPE include/asm-* /socket.h, at least MIPS
 * overrides this enum for binary compat reasons.
 */
enum sock_type {
        SOCK_STREAM     = 1,
        SOCK_DGRAM      = 2,
        SOCK_RAW        = 3,
        SOCK_RDM        = 4,
        SOCK_SEQPACKET  = 5,
        SOCK_DCCP       = 6,
        SOCK_PACKET     = 10,
};

    #define SOCKWQ_ASYNC_NOSPACE    0
    #define SOCKWQ_ASYNC_WAITDATA   1
    #define SOCK_NOSPACE            2
    #define SOCK_PASSCRED           3
    #define SOCK_PASSSEC            4

struct socket_wq {
        /* Note: wait MUST be first field of socket_wq */
        wait_queue_head_t       wait;
        struct fasync_struct    *fasync_list;
        unsigned long           flags; /* %SOCKWQ_ASYNC_NOSPACE, etc */
        struct rcu_head         rcu;
} ____cacheline_aligned_in_smp;

typedef enum {
        SS_FREE = 0,                    /* not allocated                */
        SS_UNCONNECTED,                 /* unconnected to any socket    */
        SS_CONNECTING,                  /* in process of connecting     */
        SS_CONNECTED,                   /* connected to socket          */
        SS_DISCONNECTING                /* in process of disconnecting  */
} socket_state;

/**
 *  struct socket - general BSD socket
 *  @state: socket state (%SS_CONNECTED, etc)
 *  @type: socket type (%SOCK_STREAM, etc)
 *  @flags: socket flags (%SOCK_NOSPACE, etc)
 *  @ops: protocol specific socket operations
 *  @file: File back pointer for gc
 *  @sk: internal networking protocol agnostic socket representation
 *  @wq: wait queue for several uses
 */
struct socket {
    socket_state            state;  // scoket 状态机状态

    kmemcheck_bitfield_begin(type); // int type_begin[0]
    short                   type;
    kmemcheck_bitfield_end(type);   // int type_end[0]

    unsigned long           flags;  //

    struct socket_wq __rcu  *wq;    // 等待队列

    struct file             *file;  // Linux 一切都是文件, 所有 socket 也是文件.
    struct sock             *sk;    // 具体协议的 sock. 如果 tcp_sock, udp_sock
    const struct proto_ops  *ops;   // 如 inet_stream_ops, inet_dgram_ops, inet_sockraw_ops
};

-----------------------------------------------------------
struct sock_common {
        /* skc_daddr and skc_rcv_saddr must be grouped on a 8 bytes aligned
         * address on 64bit arches : cf INET_MATCH()
         */
        union {
                __addrpair      skc_addrpair;
                struct {
                        __be32  skc_daddr;
                        __be32  skc_rcv_saddr;
                };
        };
        union  {
                unsigned int    skc_hash;
                __u16           skc_u16hashes[2];
        };
        /* skc_dport && skc_num must be grouped as well */
        union {
                __portpair      skc_portpair;
                struct {
                        __be16  skc_dport;
                        __u16   skc_num;
                };
        };

        unsigned short          skc_family;
        volatile unsigned char  skc_state;
        unsigned char           skc_reuse:4;
        unsigned char           skc_reuseport:1;
        unsigned char           skc_ipv6only:1;
        unsigned char           skc_net_refcnt:1;
        int                     skc_bound_dev_if;
        union {
                struct hlist_node       skc_bind_node;
                struct hlist_nulls_node skc_portaddr_node;
        };
        struct proto            *skc_prot;
        possible_net_t          skc_net;

#if IS_ENABLED(CONFIG_IPV6)
        struct in6_addr         skc_v6_daddr;
        struct in6_addr         skc_v6_rcv_saddr;
#endif

        atomic64_t              skc_cookie;

        /* following fields are padding to force
         * offset(struct sock, sk_refcnt) == 128 on 64bit arches
         * assuming IPV6 is enabled. We use this padding differently
         * for different kind of 'sockets'
         */
        union {
                unsigned long   skc_flags;
                struct sock     *skc_listener; /* request_sock */
                struct inet_timewait_death_row *skc_tw_dr; /* inet_timewait_sock */
        };
        /*
         * fields between dontcopy_begin/dontcopy_end
         * are not copied in sock_copy()
         */
        /* private: */
        int                     skc_dontcopy_begin[0];
        /* public: */
        union {
                struct hlist_node       skc_node;
                struct hlist_nulls_node skc_nulls_node;
        };
        int                     skc_tx_queue_mapping;
        union {
                int             skc_incoming_cpu;
                u32             skc_rcv_wnd;
                u32             skc_tw_rcv_nxt; /* struct tcp_timewait_sock  */
        };

        atomic_t                skc_refcnt;
        /* private: */
        int                     skc_dontcopy_end[0];
        union {
                u32             skc_rxhash;
                u32             skc_window_clamp;
                u32             skc_tw_snd_nxt; /* struct tcp_timewait_sock */
        };
        /* public: */
};


/* This is the per-socket lock.  The spinlock provides a synchronization
 * between user contexts and software interrupt processing, whereas the
 * mini-semaphore synchronizes multiple users amongst themselves.
 */
typedef struct {
	spinlock_t		slock;
    /* 当该值不为0 时, 表示当前 sock 被其他用户使用, 在默认情况下, 如果已经
     * 被用户使用的 sock 时不能接收新来包的不能加入 sk_receive_queue, 只能加入
     * backlog 队列.
     */
	int			owned;          //当前 sock 是否被其他用户使用
	wait_queue_head_t	wq;     //等待队列
	/*
	 * We express the mutex-alike socket_lock semantics
	 * to the lock validator by explicitly managing
	 * the slock as a lock variant (in addition to
	 * the slock itself):
	 */
#ifdef CONFIG_DEBUG_LOCK_ALLOC
	struct lockdep_map dep_map;
#endif
} socket_lock_t;

下面的宏定义是为了方便 sock 访问 __sk_common 中的数据成员

struct sock {
        /*
         * Now struct inet_timewait_sock also uses sock_common, so please just
         * don't add nothing before this first member (__sk_common) --acme
         */
        struct sock_common      __sk_common;
/*
 * 通过 sk_add_node, sk_add_node_rcu 将所属 sock 加入一个链表, 目前实现将其加入
 *  net->packet.sklist
 */
#define sk_node                 __sk_common.skc_node
/* 通过 __sk_nulls_add_node_rcu, sk_nulls_add_node_rcu 将所属 sock 加入一个链表, 目前实现将其加入
 *  sk->sk_prot->h.hashinfo->ehash,
 *  sk->sk_prot->h.hashinfo->listening_hash->head
 *  sk->sk_prot->h.udp_table->hash
 *  tcp_death_row->hashinfo->ehash
 *  struct inet_timewait_death_row tcp_death_row = {
 * 	    .sysctl_max_tw_buckets = NR_FILE * 2,
 * 	    .hashinfo	= &tcp_hashinfo,
 *  };
 * struct inet_hashinfo tcp_hashinfo;
 */
#define sk_nulls_node           __sk_common.skc_nulls_node
#define sk_refcnt               __sk_common.skc_refcnt      //sk_node 加入 list 的数量
/* 与 XPS 相关, 由 get_xps_queue 设置
 * sk_tx_queue_set
 * sk_tx_queue_clear
 */
#define sk_tx_queue_mapping     __sk_common.skc_tx_queue_mapping

// sock_copy 中使用, 用于记录数据包位置
#define sk_dontcopy_begin       __sk_common.skc_dontcopy_begin
#define sk_dontcopy_end         __sk_common.skc_dontcopy_end
#define sk_hash                 __sk_common.skc_hash
#define sk_portpair             __sk_common.skc_portpair
#define sk_num                  __sk_common.skc_num
#define sk_dport                __sk_common.skc_dport
#define sk_addrpair             __sk_common.skc_addrpair
#define sk_daddr                __sk_common.skc_daddr
#define sk_rcv_saddr            __sk_common.skc_rcv_saddr
#define sk_family               __sk_common.skc_family      //协议族 AF_INET, AF_INET6, PF_INET, PF_INET6, PF_IEEE802154
/* 协议相关的状态
   如果 tcp 协议 : TCPF_LISTEN, TCP_NEW_SYN_RECV, TCPF_TIME_WAIT, TCPF_SYN_SENT,
   TCPF_SYN_RECV, TCP_CLOSE, TCP_ESTABLISHED
 */
#define sk_state                __sk_common.skc_state
/*
 * SK_NO_REUSE : 当 socketopt 选项 TCP_REPAIR = 0
 * SK_FORCE_REUSE : 当 socketopt 选项 TCP_REPAIR = 1
 * SK_CAN_REUSE : inetsw_array 中 flags 包含 INET_PROTOSW_REUSE. 目前仅 IP
 */
#define sk_reuse                __sk_common.skc_reuse           //复用地址, 当
        TCP RE
#define sk_reuseport            __sk_common.skc_reuseport       //
#define sk_ipv6only             __sk_common.skc_ipv6only
#define sk_net_refcnt           __sk_common.skc_net_refcnt
#define sk_bound_dev_if         __sk_common.skc_bound_dev_if    //绑定设备 id
#define sk_bind_node            __sk_common.skc_bind_node       //被加入 inet_bind_bucket 的 owners
#define sk_prot                 __sk_common.skc_prot            //协议函数表, 如 tcp_prot
#define sk_net                  __sk_common.skc_net             //所属网络命名空间
#define sk_v6_daddr             __sk_common.skc_v6_daddr
#define sk_v6_rcv_saddr __sk_common.skc_v6_rcv_saddr
#define sk_cookie               __sk_common.skc_cookie
#define sk_incoming_cpu         __sk_common.skc_incoming_cpu    //该 sk 所属 cpu, raw_smp_processor_id()
/*
 * SOCK_MEMALLOC: 通过 sk_set_memalloc 设置
 * SOCK_LINGER : sock_setsockopt
 */
#define sk_flags                __sk_common.skc_flags
#define sk_rxhash               __sk_common.skc_rxhash          //在 RPS 下 sk->hash

        socket_lock_t           sk_lock;
        struct sk_buff_head     sk_receive_queue;   //数据包接收队列, 循环队列
        /*
         * The backlog queue is special, it is always used with
         * the per-socket spinlock held and requires low latency
         * access. Therefore we special case it's implementation.
         * Note : rmem_alloc is in this structure to fill a hole
         * on 64bit arches, not because its logically part of
         * backlog.
         */
        struct {
                atomic_t        rmem_alloc;     //接收队列中数据包的字节数
                int             len;            //链表中所有 skb 的长度(skb->truesize)之后
                struct sk_buff  *head;          //链表首指针
                struct sk_buff  *tail;          //链表尾指针
        } sk_backlog;
#define sk_rmem_alloc sk_backlog.rmem_alloc
        /* TODO
         * 预分配缓存大小，是已经分配但尚未使用的部分
         * sk_mem_charge, sk_mem_uncharge
         */
        int                     sk_forward_alloc;

        //TODO
        __u32                   sk_txhash;
#ifdef CONFIG_NET_RX_BUSY_POLL
        unsigned int            sk_napi_id;    //skb->napi_id
        unsigned int            sk_ll_usec;    //当没有数据时, 读数据的时长(us); net.core.busy_read
#endif
        /*
         * 当满足以下任一条件:
         * 1. sk->sk_rmem_alloc > sk->sk_rcvbuf
         * 2. sk_rmem_schedule(sk, skb, skb->truesize) 返回 0
         * 3. sk->sk_backlog.len + sk->sk_rmem_alloc > sk->rcv_buf
         * 4. sk->pfmemalloc = true && sk->sk_flags 中 SOCK_MEMALLOC 为 0
         */
        atomic_t                sk_drops;
        int                     sk_rcvbuf;     //接收数据的缓存大小. rcv_buf - rmem_alloc = 剩余接收数据包的空间

        struct sk_filter __rcu  *sk_filter;
        union {
                struct socket_wq __rcu  *sk_wq;
                struct socket_wq        *sk_wq_raw;
        };
#ifdef CONFIG_XFRM
        struct xfrm_policy __rcu *sk_policy[2];
#endif
        struct dst_entry        *sk_rx_dst;
        struct dst_entry __rcu  *sk_dst_cache;      //路由缓存
        /* Note: 32bit hole on 64bit arches */
        atomic_t                sk_wmem_alloc;      //发送队列字节数, 累加skb->truesize
        /*
         * 通过 sock_kmalloc 给 sk 分配 size 内存, sk_omem_alloc += size
         * 最多不超过 net.core.optmem_max = 20480
         */
        atomic_t                sk_omem_alloc;      //可选字节数
        int                     sk_sndbuf;          //发送缓冲总长度
        struct sk_buff_head     sk_write_queue;     //数据包发送队列
        kmemcheck_bitfield_begin(flags);
        unsigned int            sk_shutdown  : 2,       //
                                sk_no_check_tx : 1,     //
                                sk_no_check_rx : 1,     //
                                sk_userlocks : 4,       //
                                sk_protocol  : 8,       //
                                sk_type      : 16;      //
#define SK_PROTOCOL_MAX U8_MAX
        kmemcheck_bitfield_end(flags);
        //发送 sk_snbuf 中可用空间, 当大于 sk_sndbuf 时, 表示没有可用内存空间
        int                     sk_wmem_queued;
        /*
         * 给 skb 分配内存的方式
         * GFP_ATOMIC : net->ipv4.tcp_sk 的分配方式
         * __GFP_MEMALLOC: 目前没有使用. 通过 sk_set_memalloc 设置.
         * GFP_KERNEL : 初始化时为该值
         */
        gfp_t                   sk_allocation;          //分配 skb 模式
        //通过 tcp_update_pacing_rate 设置.
        u32                     sk_pacing_rate; /* bytes per second */
        //通过 socket 选项. 通过 sock_setsockopt 设置.
        u32                     sk_max_pacing_rate;
        /* 路由器的能力
         * NETIF_F_HW_CSUM
         * NETIF_F_IP_CSUM
         * NETIF_F_IPV6_CSUM
         * NETIF_F_NOCACHE_COPY
         * NETIF_F_SG
         * NETIF_F_GSO
         * NETIF_F_GSO_SOFTWARE
         * NETIF_F_GSO_MASK
         */
        netdev_features_t       sk_route_caps;
        // sk_route_caps = ~sk_route_nocaps
        netdev_features_t       sk_route_nocaps;
        // tcp 的 gso 特性. SKB_GSO_TCPV4
        int                     sk_gso_type;
        // dev->gso_max_size
        unsigned int            sk_gso_max_size;
        // dev->gso_max_segs
        u16                     sk_gso_max_segs;
        //通过 sock_setsockopt 设置 SO_RCVLOWAT, 设置每次 recv 的最小长度.
        //即每次调用 recv 收到为 min(sk_rcvlowat, len) 的数据才返回
        int                     sk_rcvlowat;
        /*
         * 当不为 0 时, 表示断开连接时的 timeout 值.
         * 只有当 sock_setsockopt SO_LINGER 选项打开时才起作用
         */
        unsigned long           sk_lingertime;
        //TODO __skb_tstamp_tx, skb_tstamp_tx 调用
        struct sk_buff_head     sk_error_queue;
        struct proto            *sk_prot_creator;
        rwlock_t                sk_callback_lock;
        int                     sk_err,
                                sk_err_soft;
        /*
         * 由 sk_acceptq_added, sk_acceptq_removed 控制
         * 最多不能超过 sk_max_ack_backlog
         */
        u32                     sk_ack_backlog;
        // listen 系统调用 backlog 的值.
        u32                     sk_max_ack_backlog;
        // 通过 sock_setsockopt 设置 SO_PRIORITY 的值[0,6]. 设置 skb->priority
        __u32                   sk_priority;
        // 通过 sock_setsockopt 设置 SO_MARK 的值. 设置 skb->mark
        __u32                   sk_mark;
        //TODO
        struct pid              *sk_peer_pid;
        //TODO
        const struct cred       *sk_peer_cred;
        // 接收数据包的 timeout 值, 通过 sock_setsockopt 设置 SO_RCVTIMEO 的值.
        long                    sk_rcvtimeo;
        // 发生数据包的 timeout 值, 通过 sock_setsockopt 设置 SO_SNDTIMEO 的值.
        long                    sk_sndtimeo;
        // 发生数据包的 keepalive 定时器(绑定到 keepalive_handler)
        struct timer_list       sk_timer;
        // 时间戳; 通过 sock_get_timestamp, sock_get_timestampns 设置
        ktime_t                 sk_stamp;
        /*
         * 时间戳选项
         * 通过 sock_setsockopt 设置 SO_TIMESTAMPING 的值. 设置 skb->tsq_flags
         * SOF_TIMESTAMPING_RX_SOFTWARE
         * SOF_TIMESTAMPING_SOFTWARE
         * SOF_TIMESTAMPING_RAW_HARDWARE
         * SOF_TIMESTAMPING_OPT_CMSG
         * SOF_TIMESTAMPING_TX_ACK
         * SOF_TIMESTAMPING_TX_HARDWARE
         * SOF_TIMESTAMPING_TX_SOFTWARE
         * SOF_TIMESTAMPING_TX_SCHED
         * SOF_TIMESTAMPING_OPT_ID
         * SOF_TIMESTAMPING_OPT_TSONLY
         */
        u16                     sk_tsflags;
        /*
         * 如果是 TCP, 在设置 SO_TIMESTAMPING 时, 设置为 tcp_sk(sk)->snd_una
         * 否则为 0
         * if (cork->tx_flags & SKBTX_ANY_SW_TSTAMP && sk->sk_tsflags & SOF_TIMESTAMPING_OPT_ID) 加 1
         *
         * 主要设置 skb_shinfo(skb)->tskey 为 sk_tskey
         */
        u32                     sk_tskey;
        struct socket           *sk_socket;
        // tunnel 协议才有用
        void                    *sk_user_data;
        // 保存数据包的分片
        struct page_frag        sk_frag;
        // 待发送的第一个数据包, 从链表 sk->sk_write_queue 取出一个数据包
        struct sk_buff          *sk_send_head;
        // 通过 sk_peek_offset_bwd, sk_peek_offset_fwd 设置, 目前没有使用
        __s32                   sk_peek_off;
        //当前 sock 处于等待任务(当前 sock 处于阻塞状态)链表的数量
        int                     sk_write_pending;
#ifdef CONFIG_SECURITY
        void                    *sk_security;
#endif
        struct sock_cgroup_data sk_cgrp_data;
        struct mem_cgroup       *sk_memcg;
        void                    (*sk_state_change)(struct sock *sk);
        void                    (*sk_data_ready)(struct sock *sk);
        void                    (*sk_write_space)(struct sock *sk);
        void                    (*sk_error_report)(struct sock *sk);
        /* raw  :  raw_rcv_skb
         * tcp  : tcp_v4_do_rcv
         * udp  : __udp_queue_rcv_skb,
         * icmp : ping_queue_rcv_skb
         */
        int                     (*sk_backlog_rcv)(struct sock *sk,
                                                  struct sk_buff *skb);
        void                    (*sk_destruct)(struct sock *sk);
        struct sock_reuseport __rcu     *sk_reuseport_cb;
};

-------------------------------------------------------------

/* struct request_sock - mini sock to represent a connection request
 */
struct request_sock {
	struct sock_common		__req_common;
#define rsk_refcnt			__req_common.skc_refcnt
#define rsk_hash			__req_common.skc_hash
/* 在 reqsk_alloc 初始化 */
#define rsk_listener			__req_common.skc_listener
#define rsk_window_clamp		__req_common.skc_window_clamp
#define rsk_rcv_wnd			__req_common.skc_rcv_wnd

	struct request_sock		*dl_next;
	u16				mss;
	u8				num_retrans; /* number of retransmits */
	u8				cookie_ts:1; /* syncookie: encode tcpopts in timestamp */
	u8				num_timeout:7; /* number of timeouts */
	u32				ts_recent;
	struct timer_list		rsk_timer;
	const struct request_sock_ops	*rsk_ops;
	struct sock			*sk;
	u32				*saved_syn;
	u32				secid;
	u32				peer_secid;
};


/** struct request_sock_queue - queue of request_socks
 *
 * @rskq_accept_head - FIFO head of established children
 * @rskq_accept_tail - FIFO tail of established children
 * @rskq_defer_accept - User waits for some data after accept()
 * 系统调用 accept :
 *   如果非阻塞, 立即返回;
 *   如果阻塞, 就一直等接受队列不为空, 从接受队列中取一个元素, 返回之;
 *   如果设置了超时, 超时, 队列仍然为空, 返回空.
 *
 *  增加元素 : inet_csk_reqsk_queue_add
 *  删除元素 : reqsk_queue_removed
 */
struct request_sock_queue {
	spinlock_t		rskq_lock;
    /* 通过 sock_setsockopt 设置 TCP_DEFER_ACCEPT.
     * 计算方法参考 secs_to_retrans(val, TCP_TIMEOUT_INIT / HZ, TCP_RTO_MAX / HZ);
     * 大体思路是 1 + 2 + 4 + ... > val 时. 加法元素个数即该值, 取值范围 [0,255).
     */
	u8			rskq_defer_accept;

	u32			synflood_warned;
    /*
     * 最多 sk->sk_max_ack_backlog(listen 指定的 backlog).
     * 减 1 : reqsk_queue_removed
     * 加 1 : reqsk_queue_added
     */
	atomic_t		qlen;
    /*
     * 最多 sk->sk_max_ack_backlog(listen 指定的 backlog).
     * 减 1 : reqsk_queue_removed(与 qlen 的区别 req->num_timeout=0 时减少)
     * 加 1 : reqsk_queue_added
     */
	atomic_t		young;

	struct request_sock	*rskq_accept_head;
	struct request_sock	*rskq_accept_tail;
	struct fastopen_queue	fastopenq;  /* Check max_qlen != 0 to determine
					     * if TFO is enabled.
					     */
};

/*
 * 初始化 inet_bind_bucket_create
 */

struct inet_bind_bucket {
        possible_net_t          ib_net;      //sk 所属的网络命名空间.
        unsigned short          port;        //绑定的端口
        signed char             fastreuse;
        signed char             fastreuseport;
        kuid_t                  fastuid;
        int                     num_owners;  // owners 元素个数
        struct hlist_node       node;        // 属于链表 sk->sk_prot->h.hashinfo->bhash[inet_bhashfn(net, port,hinfo->bhash_size)]->chain
        /*
         * 保存 sk->sk_bind_node 节点
         * 增加元素 : sk_add_bind_node
         * 删除元素 : __sk_del_bind_node
         */
        struct hlist_head       owners;
};


const struct inet_connection_sock_af_ops ipv4_specific = {
	.queue_xmit	   = ip_queue_xmit,
	.send_check	   = tcp_v4_send_check,
	.rebuild_header	   = inet_sk_rebuild_header,
	.sk_rx_dst_set	   = inet_sk_rx_dst_set,
	.conn_request	   = tcp_v4_conn_request,
	.syn_recv_sock	   = tcp_v4_syn_recv_sock,
	.net_header_len	   = sizeof(struct iphdr),
	.setsockopt	   = ip_setsockopt,
	.getsockopt	   = ip_getsockopt,
	.addr2sockaddr	   = inet_csk_addr2sockaddr,
	.sockaddr_len	   = sizeof(struct sockaddr_in),
	.bind_conflict	   = inet_csk_bind_conflict,
#ifdef CONFIG_COMPAT
	.compat_setsockopt = compat_ip_setsockopt,
	.compat_getsockopt = compat_ip_getsockopt,
#endif
	.mtu_reduced	   = tcp_v4_mtu_reduced,
};


/** struct inet_sock - representation of INET sockets
 *
 * @sk - ancestor class
 * @pinet6 - pointer to IPv6 control block
 * @inet_daddr - Foreign IPv4 addr
 * @inet_rcv_saddr - Bound local IPv4 addr
 * @inet_dport - Destination port
 * @inet_num - Local port
 * @inet_saddr - Sending source
 * @uc_ttl - Unicast TTL
 * @inet_sport - Source port
 * @inet_id - ID counter for DF pkts
 * @tos - TOS
 * @mc_ttl - Multicasting TTL
 * @is_icsk - is this an inet_connection_sock?
 * @uc_index - Unicast outgoing device index
 * @mc_index - Multicast device index
 * @mc_list - Group array
 * @cork - info to build ip hdr on each ip frag while socket is corked
 */
struct inet_sock {
	/* sk and pinet6 has to be the first two members of inet_sock */
	struct sock		sk;
#if IS_ENABLED(CONFIG_IPV6)
	struct ipv6_pinfo	*pinet6;
#endif
	/* Socket demultiplex comparisons on incoming packets. */
#define inet_daddr		sk.__sk_common.skc_daddr
#define inet_rcv_saddr		sk.__sk_common.skc_rcv_saddr
#define inet_dport		sk.__sk_common.skc_dport
#define inet_num		sk.__sk_common.skc_num

	__be32			inet_saddr;
	__s16			uc_ttl;
	__u16			cmsg_flags;
	__be16			inet_sport;
	__u16			inet_id;

	struct ip_options_rcu __rcu	*inet_opt;
	int			rx_dst_ifindex;
	__u8			tos;
	__u8			min_ttl;
	__u8			mc_ttl;
	__u8			pmtudisc;
	__u8			recverr:1,
				is_icsk:1,
				freebind:1,
				hdrincl:1,
				mc_loop:1,
				transparent:1,
				mc_all:1,
				nodefrag:1;
	__u8			bind_address_no_port:1;
	__u8			rcv_tos;
	__u8			convert_csum;
	int			uc_index;
	int			mc_index;
	__be32			mc_addr;
	struct ip_mc_socklist __rcu	*mc_list;
	struct inet_cork_full	cork;
};

struct inet_connection_sock {
        /* inet_sock has to be the first member! */
        struct inet_sock          icsk_inet;
        /*
         * 在 accept 时从队列中删除元素, 收包时将元素加入队列
         * 初始化: reqsk_queue_alloc
         * 增加元素: inet_csk_reqsk_queue_add
         * 删除元素: reqsk_queue_remove
         */
        struct request_sock_queue icsk_accept_queue;
        struct inet_bind_bucket   *icsk_bind_hash;
        /*
         * 定时器超时绝对时间, 与 icsk_retransmit_timer 关联
         * inet_csk_reset_xmit_timer
         */
        unsigned long             icsk_timeout;
        //重传定时器
        struct timer_list         icsk_retransmit_timer;
        //延迟应答定时器
        struct timer_list         icsk_delack_timer;
        //初始化为 1. 最大不超过 TCP_RTO_MAX(120)
        __u32                     icsk_rto;
        //TODO
        __u32                     icsk_pmtu_cookie;
        /*
         * 从 tcp_cong_list 中找到 ca_key = dst_metric(dst, RTAX_CC_ALGO) 对应的 tcp_congestion_ops
         */
        const struct tcp_congestion_ops *icsk_ca_ops;
        //在 tcp_v4_init_sock 中初始化为 ipv4_specific
        const struct inet_connection_sock_af_ops *icsk_af_ops;
        //在 tcp_init_sock 中初始化为 tcp_sync_mss
        unsigned int              (*icsk_sync_mss)(struct sock *sk, u32 pmtu);
        /*
         * TCP_CA_Open
         * TCPF_CA_Disorder
         * TCP_CA_Loss
         * TCP_CA_CWR
         * TCP_CA_Recovery
         */
        __u8                      icsk_ca_state:6,
                                  icsk_ca_setsockopt:1,
                                  icsk_ca_dst_locked:1;
        //TODO 没有恢复的重传次数
        __u8                      icsk_retransmits;
        /*
         * ICSK_TIME_RETRANS
         * ICSK_TIME_PROBE0
         * ICSK_TIME_EARLY_RETRANS
         * ICSK_TIME_LOSS_PROBE
         * ICSK_TIME_PROBE0
         */
        __u8                      icsk_pending;
        __u8                      icsk_backoff;
        /*
         * 通过 sock_setsockopt 设置 TCP_SYNCNT, 最大 MAX_TCP_SYNCNT(127),
         * 优先级比 net.ipv4.tcp_synack_retries(5) 高
         */
        __u8                      icsk_syn_retries;
        /*
         * 初始为 0, 当大于 net.ipv4.tcp_retries2 时, 发生错误.
         * tcp_write_wakeup(sk, LINUX_MIB_TCPKEEPALIVE) 失败, 加 1
         */
        __u8                      icsk_probes_out;
        /*
         * 默认时 0, 当 inet_opt 不为 空时, 为 inet_opt->opt.optlen
         */
        __u16                     icsk_ext_hdr_len;
        /*
         * 延迟应答
         */
        struct {
                /*
	             *  ICSK_ACK_SCHED	= 1,
	             *  ICSK_ACK_TIMER  = 2,
	             *  ICSK_ACK_PUSHED = 4,
	             *  ICSK_ACK_PUSHED2 = 8
                 */
                __u8              pending;       /* ACK is pending                         */
                __u8              quick;         /* Scheduled number of quick acks         */
                /*
                 * 当设置 TCP_QUICKACK 值不为 0, 设置为 0; 当设置 TCP_QUICKACK 值不为 0, 设置为 0;
                 * now - icsk->icsk_ack.lrcvtime) < icsk->icsk_ack.ato 置 1
                 */
                __u8              pingpong;      /* 通过 sock_setsockopt 的 TCP_QUICKACK 设置. 如果为 1 为非快速应对模式 */
                __u8              blocked;       /* Delayed ACK was blocked by socket lock */
                // 当设置 TCP_QUICKACK 值不为 0, 设置为 TCP_ATO_MIN
                __u32             ato;           /* Predicted tick of soft clock           */
                //定时器绝对时间, 与 icsk_delack_timer 关联
                unsigned long     timeout;       /* Currently scheduled timeout            */
                __u32             lrcvtime;      /* timestamp of last received data packet */
                __u16             last_seg_size; /* Size of last incoming segment          */
                __u16             rcv_mss;       /* MSS used for delayed ACK decisions     */
        } icsk_ack;
        /*
         * MTU 探测控制块
         */
        struct {
                int               enabled;

                /* Range of MTUs to search */
                int               search_high;
                int               search_low;

                /* Information on the current probe. */
                int               probe_size;

                u32               probe_timestamp;
        } icsk_mtup;
        u32                       icsk_user_timeout;

        u64                       icsk_ca_priv[64 / sizeof(u64)];
#define ICSK_CA_PRIV_SIZE      (8 * sizeof(u64))
};

-------------------------------------------------------------

struct tcp_sack_block {
	u32	start_seq;
	u32	end_seq;
};

struct tcp_options_received {
/*	PAWS/RTTM data	*/
	long	ts_recent_stamp;/* Time we stored ts_recent (for aging) */
	u32	ts_recent;	/* Time stamp to echo next		*/
	u32	rcv_tsval;	/* Time stamp value             	*/
	u32	rcv_tsecr;	/* Time stamp echo reply        	*/
	u16 	saw_tstamp : 1,	/* Saw TIMESTAMP on last packet		*/
		tstamp_ok : 1,	/* TIMESTAMP seen on SYN packet		*/
		dsack : 1,	/* D-SACK is scheduled			*/
		wscale_ok : 1,	/* Wscale seen on SYN packet		*/
		sack_ok : 4,	/* SACK seen on SYN packet		*/
		snd_wscale : 4,	/* Window scaling received from sender	*/
		rcv_wscale : 4;	/* Window scaling to send to receiver	*/
	u8	num_sacks;	/* Number of SACK blocks		*/
	u16	user_mss;	/* mss requested by user in ioctl	*/
	u16	mss_clamp;	/* Maximal mss, negotiated at connection setup */
};


struct tcp_sock {
        /* inet_connection_sock has to be the first member of tcp_sock */
        struct inet_connection_sock     inet_conn;
        u16     tcp_header_len; /* Bytes of tcp header to send          */
        u16     gso_segs;       /* Max number of segs per GSO packet    */

/*
 *      Header prediction flags
 *      0x5?10 << 16 + snd_wnd in net byte order
 */
        __be32  pred_flags;

/*
 *      RFC793 variables by their proper names. This means you can
 *      read the code and the spec side by side (and laugh ...)
 *      See RFC793 and RFC1122. The RFC writes these in capitals.
 */
        u64     bytes_received; /* RFC4898 tcpEStatsAppHCThruOctetsReceived
                                 * sum(delta(rcv_nxt)), or how many bytes
                                 * were acked.
                                 */
        u32     segs_in;        /* RFC4898 tcpEStatsPerfSegsIn
                                 * total number of segments in.
                                 * 每次增加 skb_shinfo(skb)->gso_segs
                                 */
        u32     data_segs_in;   /* RFC4898 tcpEStatsPerfDataSegsIn
                                 * total number of data segments in.
                                 */
        u32     rcv_nxt;        /* What we want to receive next         */
        u32     copied_seq;     /* 已经拷贝给用户态的数据长度           */
        u32     rcv_wup;        /* rcv_nxt on last window update sent   */
        u32     snd_nxt;        /* Next sequence we send                */
        u32     segs_out;       /* RFC4898 tcpEStatsPerfSegsOut
                                 * The total number of segments sent.
                                 */
        u32     data_segs_out;  /* RFC4898 tcpEStatsPerfDataSegsOut
                                 * total number of data segments sent.
                                 */
        u64     bytes_acked;    /* RFC4898 tcpEStatsAppHCThruOctetsAcked
                                 * sum(delta(snd_una)), or how many bytes
                                 * were acked.
                                 */
        struct u64_stats_sync syncp; /* protects 64bit vars (cf tcp_get_info()) */

        u32     snd_una;        /* First byte we want an ack for        */
        u32     snd_sml;        /* Last byte of the most recently transmitted small packet */
        u32     rcv_tstamp;     /* timestamp of last received ACK (for keepalives) */
        u32     lsndtime;       /* timestamp of last sent data packet (for restart window) */
        u32     last_oow_ack_time;  /* timestamp of last out-of-window ACK */

        u32     tsoffset;       /* timestamp offset */

        struct list_head tsq_node; /* anchor in tsq_tasklet.head list */
        unsigned long   tsq_flags;

        /* Data for direct copy to user */
        struct {
                struct sk_buff_head     prequeue;   //
                struct task_struct      *task;      //所属进程
                struct msghdr           *msg;       //tcp 头信息
                int                     memory;     //prequeue 所有 skb 数据长度(skb->truesize) 之和
                int                     len;        //剩余的要拷贝到用户态的数据长度
        } ucopy;

        u32     snd_wl1;        /* Sequence for window update           */
        u32     snd_wnd;        /* The window we expect to receive      */
        u32     max_window;     /* Maximal window ever seen from peer   */
        u32     mss_cache;      /* Cached effective mss, not including SACKS */

        u32     window_clamp;   /* Maximal window to advertise          */
        u32     rcv_ssthresh;   /* Current window clamp                 */

        /* Information of the most recently (s)acked skb */
        struct tcp_rack {
                struct skb_mstamp mstamp; /* (Re)sent time of the skb */
                u8 advanced; /* mstamp advanced since last lost marking */
                u8 reord;    /* reordering detected */
        } rack;
        u16     advmss;         /* Advertised MSS                       */
        u8      unused;
        u8      nonagle     : 4,/* Disable Nagle algorithm?             */
                thin_lto    : 1,/* Use linear timeouts for thin streams */
                thin_dupack : 1,/* Fast retransmit on first dupack      */
                repair      : 1,
                frto        : 1;/* F-RTO (RFC5682) activated in CA_Loss */
        u8      repair_queue;
        u8      do_early_retrans:1,/* Enable RFC5827 early-retransmit  */
                syn_data:1,     /* SYN includes data */
                syn_fastopen:1, /* SYN includes Fast Open option */
                syn_fastopen_exp:1,/* SYN includes Fast Open exp. option */
                syn_data_acked:1,/* data in SYN is acked by SYN-ACK */
                save_syn:1,     /* Save headers of SYN packet */
                is_cwnd_limited:1;/* forward progress limited by snd_cwnd? */
        u32     tlp_high_seq;   /* snd_nxt at the time of TLP retransmit. */

/* RTT measurement */
        u32     srtt_us;        /* smoothed round trip time << 3 in usecs */
        u32     mdev_us;        /* medium deviation                     */
        u32     mdev_max_us;    /* maximal mdev for the last rtt period */
        u32     rttvar_us;      /* smoothed mdev_max                    */
        u32     rtt_seq;        /* sequence number to update rttvar     */
        struct rtt_meas {
                u32 rtt, ts;    /* RTT in usec and sampling time in jiffies. */
        } rtt_min[3];

        u32     packets_out;    /* Packets which are "in flight"        */
        u32     retrans_out;    /* Retransmitted packets out            */
        u32     max_packets_out;  /* max packets_out in last window */
        u32     max_packets_seq;  /* right edge of max_packets_out flight */

        u16     urg_data;       /* Saved octet of OOB data and control flags */
        u8      ecn_flags;      /* ECN status bits.                     */
        u8      keepalive_probes; /* num of allowed keep alive probes   */
        u32     reordering;     /* Packet reordering metric.            */
        u32     snd_up;         /* Urgent pointer               */

/*
 *      Options received (usually on last packet, some only on SYN packets).
 */
        struct tcp_options_received rx_opt;

/*
 *      Slow start and congestion control (see also Nagle, and Karn & Partridge)
 */
        u32     snd_ssthresh;   /* Slow start size threshold            */
        u32     snd_cwnd;       /* Sending congestion window            */
        u32     snd_cwnd_cnt;   /* Linear increase counter              */
        u32     snd_cwnd_clamp; /* Do not allow snd_cwnd to grow above this */
        u32     snd_cwnd_used;
        u32     snd_cwnd_stamp;
        u32     prior_cwnd;     /* Congestion window at start of Recovery. */
        u32     prr_delivered;  /* Number of newly delivered packets to
                                 * receiver in Recovery. */
        u32     prr_out;        /* Total number of pkts sent during Recovery. */
        u32     delivered;      /* Total data packets delivered incl. rexmits */

        u32     rcv_wnd;        /* Current receiver window              */
        u32     write_seq;      /* Tail(+1) of data held in tcp send buffer */
        u32     notsent_lowat;  /* TCP_NOTSENT_LOWAT */
        u32     pushed_seq;     /* Last pushed seq, required to talk to windows */
        u32     lost_out;       /* Lost packets                 */
        u32     sacked_out;     /* SACK'd packets                       */
        u32     fackets_out;    /* FACK'd packets                       */

        /* from STCP, retrans queue hinting */
        struct sk_buff* lost_skb_hint;
        struct sk_buff *retransmit_skb_hint;

        /* OOO segments go in this list. Note that socket lock must be held,
         * as we do not use sk_buff_head lock.
         */
        struct sk_buff_head     out_of_order_queue;

        /* SACKs data, these 2 need to be together (see tcp_options_write) */
        struct tcp_sack_block duplicate_sack[1]; /* D-SACK block */
        struct tcp_sack_block selective_acks[4]; /* The SACKS themselves*/

        struct tcp_sack_block recv_sack_cache[4];

        struct sk_buff *highest_sack;   /* skb just after the highest
                                         * skb with SACKed bit set
                                         * (validity guaranteed only if
                                         * sacked_out > 0)
                                         */

        int     lost_cnt_hint;
        u32     retransmit_high;        /* L-bits may be on up to this seqno */

        u32     prior_ssthresh; /* ssthresh saved at recovery start     */
        u32     high_seq;       /* snd_nxt at onset of congestion       */

        u32     retrans_stamp;  /* Timestamp of the last retransmit,
                                 * also used in SYN-SENT to remember stamp of
                                 * the first SYN. */
        u32     undo_marker;    /* snd_una upon a new recovery episode. */
        int     undo_retrans;   /* number of undoable retransmissions. */
        u32     total_retrans;  /* Total retransmits for entire connection */

        u32     urg_seq;        /* Seq of received urgent pointer */
        unsigned int            keepalive_time;   /* time before keep alive takes place */
        unsigned int            keepalive_intvl;  /* time interval between keep alive probes */

        int                     linger2;

/* Receiver side RTT estimation */
        struct {
                u32     rtt;
                u32     seq;
                u32     time;
        } rcv_rtt_est;

/* Receiver queue space */
        struct {
                int     space;      //上次拷贝的长度
                u32     seq;        //已经拷贝到用户空间的序列
                u32     time;       //上次拷贝时间
        } rcvq_space;

/* TCP-specific MTU probe information. */
        struct {
                u32               probe_seq_start;
                u32               probe_seq_end;
        } mtu_probe;
        u32     mtu_info; /* We received an ICMP_FRAG_NEEDED / ICMPV6_PKT_TOOBIG
                           * while socket was owned by user.
                           */

#ifdef CONFIG_TCP_MD5SIG
/* TCP AF-Specific parts; only used by MD5 Signature support so far */
        const struct tcp_sock_af_ops    *af_specific;

/* TCP MD5 Signature Option information */
        struct tcp_md5sig_info  __rcu *md5sig_info;
#endif

/* TCP fastopen related information */
        struct tcp_fastopen_request *fastopen_req;
        /* fastopen_rsk points to request_sock that resulted in this big
         * socket. Used to retransmit SYNACKs etc.
         */
        struct request_sock *fastopen_rsk;
        u32     *saved_syn;
};

struct inet_skb_parm {
        struct ip_options       opt;            /* Compiled IP options          */
        unsigned char           flags;

#define IPSKB_FORWARDED         BIT(0)
#define IPSKB_XFRM_TUNNEL_SIZE  BIT(1)
#define IPSKB_XFRM_TRANSFORMED  BIT(2)
#define IPSKB_FRAG_COMPLETE     BIT(3)
#define IPSKB_REROUTED          BIT(4)
#define IPSKB_DOREDIRECT        BIT(5)
#define IPSKB_FRAG_PMTU         BIT(6)

        u16                     frag_max_size;
};

struct tcp_skb_cb {
        __u32           seq;            /* Starting sequence number     */
        __u32           end_seq;        /* SEQ + FIN + SYN + datalen    */
        union {
                /* Note : tcp_tw_isn is used in input path only
                 *        (isn chosen by tcp_timewait_state_process())
                 *
                 *        tcp_gso_segs/size are used in write queue only,
                 *        cf tcp_skb_pcount()/tcp_skb_mss()
                 */
                __u32           tcp_tw_isn;
                struct {
                        u16     tcp_gso_segs; //分片数量, 每个分片一个包, 每个分片不会大于当前的 mss
                        u16     tcp_gso_size; //所有分片的 byte 长度
                };
        };
        __u8            tcp_flags;      /* TCP header flags. (tcp[13])  */

        __u8            sacked;         /* State flags for SACK/FACK.   */
#define TCPCB_SACKED_ACKED      0x01    /* SKB ACK'd by a SACK block    */
#define TCPCB_SACKED_RETRANS    0x02    /* SKB retransmitted            */
#define TCPCB_LOST              0x04    /* SKB is lost                  */
#define TCPCB_TAGBITS           0x07    /* All tag bits                 */
#define TCPCB_REPAIRED          0x10    /* SKB repaired (no skb_mstamp) */
#define TCPCB_EVER_RETRANS      0x80    /* Ever retransmitted frame     */
#define TCPCB_RETRANS           (TCPCB_SACKED_RETRANS|TCPCB_EVER_RETRANS| \
                                TCPCB_REPAIRED)

        __u8            ip_dsfield;     /* IPv4 tos or IPv6 dsfield     */
        /* 1 byte hole */
        __u32           ack_seq;        /* Sequence number ACK'd        */
        union {
                struct inet_skb_parm    h4;     //来自 (skb)->cb), 在 tcp_v4_rcv 时
#if IS_ENABLED(CONFIG_IPV6)
                struct inet6_skb_parm   h6;
#endif
        } header;       /* For incoming frames          */
};


-------------------------------------------------------------

struct request_sock {
	struct sock_common		__req_common;
#define rsk_refcnt			__req_common.skc_refcnt
#define rsk_hash			__req_common.skc_hash
#define rsk_listener			__req_common.skc_listener
#define rsk_window_clamp		__req_common.skc_window_clamp
#define rsk_rcv_wnd			__req_common.skc_rcv_wnd

	struct request_sock		*dl_next;
	u16				mss;
	u8				num_retrans; /* number of retransmits */
	u8				cookie_ts:1; /* syncookie: encode tcpopts in timestamp */
	u8				num_timeout:7; /* number of timeouts */
	u32				ts_recent;
	struct timer_list		rsk_timer;
	const struct request_sock_ops	*rsk_ops;
	struct sock			*sk;
	u32				*saved_syn;
	u32				secid;
	u32				peer_secid;
};

struct inet_request_sock {
	struct request_sock	req;
#define ir_loc_addr		req.__req_common.skc_rcv_saddr
#define ir_rmt_addr		req.__req_common.skc_daddr
#define ir_num			req.__req_common.skc_num
#define ir_rmt_port		req.__req_common.skc_dport
#define ir_v6_rmt_addr		req.__req_common.skc_v6_daddr
#define ir_v6_loc_addr		req.__req_common.skc_v6_rcv_saddr
#define ir_iif			req.__req_common.skc_bound_dev_if
#define ir_cookie		req.__req_common.skc_cookie
#define ireq_net		req.__req_common.skc_net
#define ireq_state		req.__req_common.skc_state
#define ireq_family		req.__req_common.skc_family

	kmemcheck_bitfield_begin(flags);
	u16			snd_wscale : 4,
				rcv_wscale : 4,
				tstamp_ok  : 1,
				sack_ok	   : 1,
				wscale_ok  : 1,
				ecn_ok	   : 1,
				acked	   : 1,
				no_srccheck: 1;
	kmemcheck_bitfield_end(flags);
	u32                     ir_mark;
	union {
		struct ip_options_rcu	*opt;
		struct sk_buff		*pktopts;
	};
};

-------------------------------------------------------------

/*
 * This is a TIME_WAIT sock. It works around the memory consumption
 * problems of sockets in such a state on heavily loaded servers, but
 * without violating the protocol specification.
 */
struct inet_timewait_sock {
	/*
	 * Now struct sock also uses sock_common, so please just
	 * don't add nothing before this first member (__tw_common) --acme
	 */
	struct sock_common	__tw_common;
#define tw_family		__tw_common.skc_family
#define tw_state		__tw_common.skc_state
#define tw_reuse		__tw_common.skc_reuse
#define tw_ipv6only		__tw_common.skc_ipv6only
#define tw_bound_dev_if		__tw_common.skc_bound_dev_if
#define tw_node			__tw_common.skc_nulls_node
#define tw_bind_node		__tw_common.skc_bind_node
#define tw_refcnt		__tw_common.skc_refcnt
#define tw_hash			__tw_common.skc_hash
#define tw_prot			__tw_common.skc_prot
#define tw_net			__tw_common.skc_net
#define tw_daddr        	__tw_common.skc_daddr
#define tw_v6_daddr		__tw_common.skc_v6_daddr
#define tw_rcv_saddr    	__tw_common.skc_rcv_saddr
#define tw_v6_rcv_saddr    	__tw_common.skc_v6_rcv_saddr
#define tw_dport		__tw_common.skc_dport
#define tw_num			__tw_common.skc_num
#define tw_cookie		__tw_common.skc_cookie
#define tw_dr			__tw_common.skc_tw_dr

	int			tw_timeout;
	volatile unsigned char	tw_substate;
	unsigned char		tw_rcv_wscale;

	/* Socket demultiplex comparisons on incoming packets. */
	/* these three are in inet_sock */
	__be16			tw_sport;
	kmemcheck_bitfield_begin(flags);
	/* And these are ours. */
	unsigned int		tw_kill		: 1,
				tw_transparent  : 1,
				tw_flowlabel	: 20,
				tw_pad		: 2,	/* 2 bits hole */
				tw_tos		: 8;
	kmemcheck_bitfield_end(flags);
	struct timer_list	tw_timer;
	struct inet_bind_bucket	*tw_tb;
};
-------------------------------------------------------------

struct inet_ehash_bucket {
	struct hlist_nulls_head chain;
};

struct inet_listen_hashbucket {
	spinlock_t		lock;
	struct hlist_nulls_head	head;
};

struct inet_bind_hashbucket {
	spinlock_t		lock;
	struct hlist_head	chain;
};

struct inet_hashinfo {
	/* This is for sockets with full identity only.  Sockets here will
	 * always be without wildcards and will have the following invariant:
	 *
	 *          TCP_ESTABLISHED <= sk->sk_state < TCP_CLOSE
	 *
	 */
	struct inet_ehash_bucket	*ehash;  //已经建立连接的哈希桶
	spinlock_t			*ehash_locks;
	unsigned int			ehash_mask;  //哈希桶的个数
	unsigned int			ehash_locks_mask; //哈希锁的个数

	/* Ok, let's try this, I give up, we do need a local binding
	 * TCP hash as well as the others for fast bind/connect.
	 */
	struct inet_bind_hashbucket	*bhash;

	unsigned int			bhash_size; //bhash 的元素个数
	/* 4 bytes hole on 64 bit */

	struct kmem_cache		*bind_bucket_cachep;

	/* All the above members are written once at bootup and
	 * never written again _or_ are predominantly read-access.
	 *
	 * Now align to a new cache line as all the following members
	 * might be often dirty.
	 */
	/* All sockets in TCP_LISTEN state will be in here.  This is the only
	 * table where wildcard'd TCP sockets can exist.  Hash function here
	 * is just local port number.
	 */
    /*
     * 哈希值 inet_lhashfn(net, hnum)
     *
	struct inet_listen_hashbucket	listening_hash[INET_LHTABLE_SIZE]
					____cacheline_aligned_in_smp;
};

----------------------------------------------------------

static struct timewait_sock_ops tcp_timewait_sock_ops = {
        .twsk_obj_size  = sizeof(struct tcp_timewait_sock),
        .twsk_unique    = tcp_twsk_unique,
        .twsk_destructor= tcp_twsk_destructor,
};

----------------------------------------------------------

static DEFINE_READ_MOSTLY_HASHTABLE(napi_hash, 8);

定义包含 256 个 元素的哈希链表

因此全局最多有 256 个 napi_struct

----------------------------------------------------------

struct inet_timewait_death_row {
	atomic_t		tw_count;

	struct inet_hashinfo 	*hashinfo ____cacheline_aligned_in_smp;
	int			sysctl_tw_recycle;
    // (tcp_hashinfo.ehash_mask + 1)/ 2
	int			sysctl_max_tw_buckets;
};

sysctl_tcp_max_orphans : tcp_hashinfo.ehash_mask + 1;

sysctl_max_syn_backlog = max(128, (tcp_hashinfo.ehash_mask + 1)/ 256);

dmesg | grep "Hash tables configured"

    [    0.404550] TCP: Hash tables configured (established 32768 bind 32768)

----------------------------------------------------------

## 数据结构关系


### sock 与 file 的关系

	file->private_data = sock;

### sock 与 inet_sock 的关系

    (inet_sock*)sock

### sock 与 inet_csk 的关系

    (struct inet_connection_sock *)sk

### sock 与 tcp_sock 的关系

    (struct tcp_sock *)sk;

### sock 与 socket 的关系

    socket->sk = sock
    sock->sk_socket

### sock 与 inet_sock 的关系

    inet_sock *inet = inet_sk(sk);

### inet_bind_hashbucket 与 inet_bind_bucket, inet_hashinfo 的关系

    inet_bind_hashbucket->chain 是一个链表头, 链表中保存 inet_bind_bucket 元素

    inet_bind_bucket 的内存来自 inet_hashinfo->bind_bucket_cachep

### request_sock_queue 与 request_sock

    request_sock_queue->head 指向 request_sock 链表的首指针

### inet_request_sock 与 request_sock

inet_request_sock *ireq = inet_rsk(req)

### skb 与 tcp 控制块的关系

#define TCP_SKB_CB(__skb)       ((struct tcp_skb_cb *)&((__skb)->cb[0]))

tcp_sock
    inet_connection_sock
        inet_sock
            sock
                sock_common

inet_request_sock
    request_sock
        sock_common


### 注意点

sk->sk_rcvbuf           =       sysctl_rmem_default;
sk->sk_sndbuf           =       sysctl_wmem_default;

如果是 tcp 协议:

sk->sk_sndbuf = sysctl_tcp_wmem[1];
sk->sk_rcvbuf = sysctl_tcp_rmem[1];
sk->sk_state = TCP_CLOSE;


全连接队列: min(backlog, net.core.somaxconn)
半连接队列: min(backlog, net.core.somaxconn, net.ipv4.tcp_max_syn_backlog)


int inet_csk_get_port(struct sock *sk, unsigned short snum)

    TODO
    1. 遍历 sk->sk_prot->h.hashinfo->bhash[inet_bhashfn(net, port,hinfo->bhash_size)]->chain 的所有元素,
    找到满足 tb->port = snum, ib_net(tb) = sock_net(sk) 的 inet_bind_bucket
    2. inet_bind_bucket->owners != NULL && sk->sk_reuse == SK_FORCE_REUSE

    inet_sk(sk)->inet_num = snum;
    sk->sk_bind_node 增加到 tb->owners //sk_add_bind_node(sk, &tb->owners);
    tb->num_owners++;
    inet_csk(sk)->icsk_bind_hash = tb;

    if TCP:
        sk->sk_prot->h.hashinfo 为 inet_hashinfo



## 附录

[TCP Repair](https://lwn.net/Articles/495304/)


### 关于端口重用

1) Sockets bound to different interfaces may share a local port.  Failing that, goto test 2.
2) If all sockets have sk->sk_reuse set, and none of them are in TCP_LISTEN state, the port may be shared.  Failing that, goto test 3.
3) If all sockets are bound to a specific inet_sk(sk)->rcv_saddr local address, and none of them are the same, the port may be shared.  

Failing all, the port cannot be shared.

tb->fastreuse = sk->sk_reuse && sk->sk_state != TCP_LISTEN
tb->fastreuseport = sk->sk_reuseport ? 1 : 0
tb->fastuid = sk->sk_reuseport ? uid : null

端口重用条件:

    TCP 协议:

    sk2 != sk && sk2->sk_family == sk->sk_family && ipv6_only_sock(sk2) == ipv6_only_sock(sk) &&
    sk2->sk_bound_dev_if == sk->sk_bound_dev_if && inet_csk(sk2)->icsk_bind_hash == tb &&
    sk2->sk_reuseport && uid_eq(uid, sock_i_uid(sk2)) && saddr_same(sk, sk2, false)
    其中 saddr_same 为 ipv4_rcv_saddr_equal

CONFIG_NET_RX_BUSY_POLL=y

