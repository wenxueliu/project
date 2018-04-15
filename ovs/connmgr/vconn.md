##连接

与远程建立 OpenFlow 连接.

###名词解释

vconn: virtual connection

pvconn: passive virtual connection

###虚拟连接

####来源

    lib/vconn-provider.c
    lib/vconn-stream.c

##数据结构

### vconn 与 vconn_stream

    vconn_stream->vconn 定位到 vconn
    vconn 通过 CONTAINER_OF(vconn, struct vconn_stream, vconn) 定位 vconn_stream

### pvconn 与 pvconn_stream

    pvconn_stream->pvconn 定位到 pvconn
    pvconn 通过 CONTAINER_OF(pvconn, struct pvconn_stream, pvconn) 定位 vconn_stream

### stream 与 vconn_stream

    vconn_stream->stream 定位到 stream
    stream 通过 CONTAINER_OF(stream, struct vconn_stream, stream) 定位 vconn_stream

### pstream 与 pvconn_stream

    pvconn_stream->pstream 定位到 pstream
    pstream 通过 CONTAINER_OF(pstream, struct pvconn_stream, pstream) 定位 pvconn_stream

### stream 与 vconn 的关系

### stream_fd 与 stream 的关系

    stream_fd->stream 定位到 stream
    stream 通过 CONTAINER_OF(stream, struct stream_fd, stream) 定位到 stream_fd

### fd_pstream 与 pstream 的关系

    pstream 通过 CONTAINER_OF(pstream, struct fd_pstream, pstream) 定位到 fd_pstream


其中

stream-fd.c 是对 socket 的简单封装

vconn 是 virtual connect 的简称, 是主动发起连接的一端的 socket 抽象. 通过 vconn_class 屏蔽协议细节.
目前支持的协议有 tcp, unix, ssl.

stream 是面向流的协议的抽象, 是主动发起连接的一端的 socket 抽象. 通过 stream_class 屏蔽协议细节.
目前支持的协议有 tcp, unix, ssl

pvconn 是 passtive virtual connect 的简称, 是被动接受连接的一端的 socket 抽象.  通过 pvconn_class 屏蔽协议细节.
目前支持的协议有 tcp, unix, ssl.

pstream 是面向流的协议的抽象, 是被动接受连接的一端的 socket 抽象. 通过 pstream_class 屏蔽协议细节.
目前支持的协议有 tcp, unix, ssl

stream_fd 是基于 fd 流主动连接 socket 的封装.

fd_pstream 是基于 fd 流被动接受 socket 的封装

vconn 和 stream 通过 vconn_stream 关联

pvconn 和 pstream 通过 pvconn_pstream 关联

vconn -> vconn_stream -> stream -> stream_fd -> fd

pvconn -> pvconn_pstream -> pstream -> fd_pstream -> fd

需要注意的是所有主动连接的抽象中都包含 run, run_wait, wait

需要注意的是所有被动连接的抽象中都包含 wait

状态切换: VCS_CONNECTING -> VCS_SEND_HELLO -> VCS_RECV_HELLO -> VCS_CONNECTED -> VCS_DISCONNECTED

疑问:

为什么在 vconn, pvconn 中加入了 openflow 的协议细节?

一个关键点:

    所有的 vconn->class 都指向 stream_vconn_class
    所有的 stream->class 都指向 stream_fd_class
    所有 pvconn->class 都指向 pstream_pvconn_class
    所有 pstream->class 都指向 fd_pstream_class

------------------------------------------------------

struct vconn_stream
{
    struct vconn vconn;
    struct stream *stream;
    struct ofpbuf *rxbuf;
    struct ofpbuf *txbuf;
    int n_packets;
};

struct vconn {
    const struct vconn_class *vclass;
    int state;
    int error;

    /* OpenFlow versions. */
    uint32_t allowed_versions;  /* Bitmap of versions we will accept. */
    uint32_t peer_versions;     /* Peer's bitmap of versions it will accept. */
    enum ofp_version version;   /* Negotiated version (or 0). */
    bool recv_any_version;      /* True to receive a message of any version. */

    char *name;
};

struct vconn_class {
    const char *name;
    int (*open)(const char *name, uint32_t allowed_versions, char *suffix, struct vconn **vconnp, uint8_t dscp);
    void (*close)(struct vconn *vconn);
    int (*connect)(struct vconn *vconn);
    int (*recv)(struct vconn *vconn, struct ofpbuf **msgp);
    int (*send)(struct vconn *vconn, struct ofpbuf *msg);
    void (*run)(struct vconn *vconn);
    void (*run_wait)(struct vconn *vconn);
    void (*wait)(struct vconn *vconn, enum vconn_wait_type type);
};

static const struct vconn_class *vconn_classes[] = {
    &tcp_vconn_class,
    &unix_vconn_class,
#ifdef HAVE_OPENSSL
    &ssl_vconn_class,
#endif
};

const struct vconn_class tcp_vconn_class = STREAM_INIT("tcp");
const struct vconn_class unix_vconn_class = STREAM_INIT("unix");
const struct vconn_class ssl_vconn_class = STREAM_INIT("ssl");


/* Active stream connection.
 *
 * This structure should be treated as opaque by implementation. */
struct stream {
    const struct stream_class *class;
    int state;
    int error;
    char *name;
};

struct stream_class {
    /* Prefix for connection names, e.g. "tcp", "ssl", "unix". */
    const char *name;
    bool needs_probes;

    int (*open)(const char *name, char *suffix, struct stream **streamp, uint8_t dscp);
    void (*close)(struct stream *stream);
    int (*connect)(struct stream *stream);
    ssize_t (*recv)(struct stream *stream, void *buffer, size_t n);
    ssize_t (*send)(struct stream *stream, const void *buffer, size_t n);
    void (*run)(struct stream *stream);
    void (*run_wait)(struct stream *stream);
    void (*wait)(struct stream *stream, enum stream_wait_type type);
};

/* State of an active vconn.*/
enum vconn_state {
    /* This is the ordinary progression of states. */
    VCS_CONNECTING,             /* Underlying vconn is not connected. */
    VCS_SEND_HELLO,             /* Waiting to send OFPT_HELLO message. */
    VCS_RECV_HELLO,             /* Waiting to receive OFPT_HELLO message. */
    VCS_CONNECTED,              /* Connection established. */

    /* These states are entered only when something goes wrong. */
    VCS_SEND_ERROR,             /* Sending OFPT_ERROR message. */
    VCS_DISCONNECTED            /* Connection failed or connection closed. */
};

enum vconn_wait_type {
    WAIT_CONNECT,
    WAIT_RECV,
    WAIT_SEND
};

static const struct stream_class *stream_classes[] = {
    &tcp_stream_class,
#ifndef _WIN32
    &unix_stream_class,
#else
    &windows_stream_class,
#endif
#ifdef HAVE_OPENSSL
    &ssl_stream_class,
#endif
};

const struct stream_class tcp_stream_class = {
    "tcp",                      /* name */
    true,                       /* needs_probes */
    tcp_open,                   /* open */
    NULL,                       /* close */
    NULL,                       /* connect */
    NULL,                       /* recv */
    NULL,                       /* send */
    NULL,                       /* run */
    NULL,                       /* run_wait */
    NULL,                       /* wait */
};

const struct stream_class unix_stream_class = {
    "unix",                     /* name */
    false,                      /* needs_probes */
    unix_open,                  /* open */
    NULL,                       /* close */
    NULL,                       /* connect */
    NULL,                       /* recv */
    NULL,                       /* send */
    NULL,                       /* run */
    NULL,                       /* run_wait */
    NULL,                       /* wait */
};


const struct stream_class ssl_stream_class = {
    "ssl",                      /* name */
    true,                       /* needs_probes */
    ssl_open,                   /* open */
    ssl_close,                  /* close */
    ssl_connect,                /* connect */
    ssl_recv,                   /* recv */
    ssl_send,                   /* send */
    ssl_run,                    /* run */
    ssl_run_wait,               /* run_wait */
    ssl_wait,                   /* wait */
};

------------------------------------------------------

struct pvconn_pstream
{
    struct pvconn pvconn;
    struct pstream *pstream;
};

struct pvconn {
    const struct pvconn_class *pvclass;
    char *name;
    uint32_t allowed_versions;
};

struct pvconn_class {
    const char *name;
    int (*listen)(const char *name, uint32_t allowed_versions, char *suffix, struct pvconn **pvconnp, uint8_t dscp);
    void (*close)(struct pvconn *pvconn);
    int (*accept)(struct pvconn *pvconn, struct vconn **new_vconnp);
    void (*wait)(struct pvconn *pvconn);
};

static const struct pvconn_class *pvconn_classes[] = {
    &ptcp_pvconn_class,
    &punix_pvconn_class,
#ifdef HAVE_OPENSSL
    &pssl_pvconn_class,
#endif
};

const struct pvconn_class ptcp_pvconn_class = PSTREAM_INIT("ptcp");
const struct pvconn_class punix_pvconn_class = PSTREAM_INIT("punix");
const struct pvconn_class pssl_pvconn_class = PSTREAM_INIT("pssl");


/* Passive listener for incoming stream connections.
 *
 * This structure should be treated as opaque by stream implementations. */
struct pstream {
    const struct pstream_class *class;
    char *name;
    ovs_be16 bound_port;
};

struct pstream_class {
    const char *name;
    bool needs_probes;
    int (*listen)(const char *name, char *suffix, struct pstream **pstreamp, uint8_t dscp);
    void (*close)(struct pstream *pstream);
    int (*accept)(struct pstream *pstream, struct stream **new_streamp);
    void (*wait)(struct pstream *pstream);
};

static const struct pstream_class *pstream_classes[] = {
    &ptcp_pstream_class,
#ifndef _WIN32
    &punix_pstream_class,
#else
    &pwindows_pstream_class,
#endif
#ifdef HAVE_OPENSSL
    &pssl_pstream_class,
#endif
};

const struct pstream_class ptcp_pstream_class = {
    "ptcp",
    true,
    ptcp_open,
    NULL,
    NULL,
    NULL,
};

const struct pstream_class punix_pstream_class = {
    "punix",
    false,
    punix_open,
    NULL,
    NULL,
    NULL,
};

const struct pstream_class pssl_pstream_class = {
    "pssl",
    true,
    pssl_open,
    pssl_close,
    pssl_accept,
    pssl_wait,
};

----------------------------------------------------------------

struct stream_fd
{
    struct stream stream;
    int fd;
    int fd_type;
};

static const struct stream_class stream_fd_class = {
    "fd",                       /* name */
    false,                      /* needs_probes */
    NULL,                       /* open */
    fd_close,                   /* close */
    fd_connect,                 /* connect */
    fd_recv,                    /* recv */
    fd_send,                    /* send */
    NULL,                       /* run */
    NULL,                       /* run_wait */
    fd_wait,                    /* wait */
};

/* State of an active stream.*/
enum stream_state {
    SCS_CONNECTING,             /* Underlying stream is not connected. */
    SCS_CONNECTED,              /* Connection established. */
    SCS_DISCONNECTED            /* Connection failed or connection closed. */
};

enum stream_content_type {
    STREAM_UNKNOWN,
    STREAM_OPENFLOW,
    STREAM_SSL,
    STREAM_JSONRPC
};

enum stream_wait_type {
    STREAM_CONNECT,
    STREAM_RECV,
    STREAM_SEND
};


struct fd_pstream {
    struct pstream pstream;
    int fd;
    int (*accept_cb)(int fd, const struct sockaddr_storage *, size_t ss_len,
                     struct stream **);
    char *unlink_path;
};

static const struct pstream_class fd_pstream_class = {
    "pstream",
    false,
    NULL,
    pfd_close,
    pfd_accept,
    pfd_wait,
};

#define STREAM_INIT(NAME)                           \
    {                                               \
            NAME,                                   \
            vconn_stream_open,                      \
            vconn_stream_close,                     \
            vconn_stream_connect,                   \
            vconn_stream_recv,                      \
            vconn_stream_send,                      \
            vconn_stream_run,                       \
            vconn_stream_run_wait,                  \
            vconn_stream_wait,                      \
    }

#define PSTREAM_INIT(NAME)                          \
    {                                               \
            NAME,                                   \
            pvconn_pstream_listen,                  \
            pvconn_pstream_close,                   \
            pvconn_pstream_accept,                  \
            pvconn_pstream_wait                     \
    }

static const struct vconn_class stream_vconn_class = STREAM_INIT("stream");
static const struct pvconn_class pstream_pvconn_class = PSTREAM_INIT("pstream");

----------------------------------------------------------------

## 功能概述

### stream_fd

new_fd_stream(name, fd, connect_status, fd_type, streamp): 初始化 stream_fd 对象
stream_fd_cast(stream) : 从 stream 获取其所在的 stream_fd
fd_close(stream) : 关闭 stream 对应 fd 的连接
fd_connect(struct stream *stream) : 等等 stream 对应 fd 有事件发生(可读或可写)或超时.
fd_recv(stream, buffer, n) : 接受 n byte 的数据从 stream 对应 fd, 保存在 buffer.
fd_send(stream, buffer, n) : 将 n byte 保存在 buffer 的数据, 从 stream 对应 fd 发送出去.
fd_wait(stream, wait) :  如果 wait = STREAM_CONNECT | STREAM_SEND 监听 stream 对应 fd 的可写事件; 如果 wait = STREAM_RECV 监听 stream 对应 fd 的可写事件.
fd_pstream_cast(pstream) : 从 pstream 定位到其所在 fd_pstream 的 fd.
new_fd_pstream(name, fd, (accept_cb), unlink_path, pstreamp) : 初始化 fd_pstream 对象
pfd_close(pstream) :  关闭 pstream 对应 fd 的连接
pfd_accept(pstream, new_streamp) :  从 pstream 接受一个新的连接, 保存在 new_stream
pfd_wait(pstream) : 等待 pstream 对应 fd 的可读事件.

### stream

stream_init(stream, class, connect_status, name): 用后面参数初始化 vconn
stream_verify_name(name): 根据 name 找到指定的 class 类型, 确认 name 的参数合法
stream_open(name, streamp, dscp) : 初始化 stream, stream_fd, 并建立连接
stream_open_block(error, streamp) : 不断重试, 直到连接成功或发生错误
stream_close(struct stream *stream): 关闭连接, 释放内存
stream_connect(stream) : 确保 stream 对应 fd 连接完成或发生错误
stream_recv(stream, buffer, n): 从 stream 对应 fd 接受 n byte 数据, 保存在 buffer.
stream_send(stream, buffer, n): 将 n byte 保存在 buffer 的数据, 从 stream 对应 fd 发送出去.
stream_run(stream) : 什么也不做
stream_run_wait(stream) : 什么也不做
stream_wait(stream, wait): 根据 stream->state 或 wait, 注册 stream 对应 fd 的事件(可读, 可写)
stream_connect_wait(stream) : 注册 stream 对应 fd 的可写事件(stream_wait(stream, STREAM_CONNECT))
stream_recv_wait(stream) : 注册 stream 对应 fd 的可读事件(stream_wait(stream, STREAM_RECV))
stream_send_wait(stream) : 注册 stream 对应 fd 的可写事件(stream_wait(stream, STREAM_SEND))
stream_open_with_default_port(name_, default_port, streamp, dscp): 连接到 default_port

### pstream

pstream_init(pstream, class, name) : 根据后面的参数初始化 pvconn
pstream_verify_name(name) : 根据 name 找到指定的 class 类型, 确认 name 的参数合法
pstream_open(name, pstreamp, dscp) : 初始化 pstreamp, fd_pstream, 监听客户端的连接
pstream_close(pstream) : 关闭连接, 释放内存
pstream_accept(pstream, new_stream) : 从 pstream 接受一个新的连接, 保存在 new_stream
pstream_accept_block(pstream, new_stream) : 接受新的连接请求, 为其分配 stream 对象的 new_stream.
pstream_wait(struct pstream *pstream) : 注册 pstream 对应 fd 的可读事件
pstream_open_with_default_port(name_, default_port, pstreamp, dscp) : listen 监听 default_port

### vconn_stream

vconn_stream_new(stream, connect_status, allowed_versions) : 初始化 vconn_stream
vconn_stream_open(name, allowed_versions, suffix, vconnp, dscp): 初始化连接, 将连接保存在 vconnp
vconn_stream_close(struct vconn *vconn) : 关闭 vconn 对应 fd 的连接
vconn_stream_connect(struct vconn *vconn) : 建立连接
vconn_stream_recv__(s, rx_len) : 接受 rx_len 数据保存在 s->rxbuf
vconn_stream_recv(vconn, bufferp): 接受数据保存在 vconn 对应 vconn_stream->rxbuf
vconn_stream_send(vconn, buffer) : 将 buffer 中的数据发送出去
vconn_stream_run(vconn) : 将 vconn 对应 vconn_stream 的 txbuf 中的数据发送出去
vconn_stream_run_wait(vconn) : 监听 vconn 对应 vconn_stream 的数据可写事件
vconn_stream_wait(vconn, wait): 根据 wait 监听指定 vconn 的事件
pvconn_pstream_listen(name, allowed_versions, suffix, pvconnp, dscp) : 监听连接, 并初始化 pvconn_pstream
pvconn_pstream_close(pvconn) : 关闭连接
pvconn_pstream_accept(pvconn, new_vconnp) : 监听 pvcon 对应的连接, 并初始化 new_vconnp
pvconn_pstream_wait(pvconn) : 注册 pvconn 对应 pvconn_pstream 对应 fd 的可读事件

### vconn

vconn_open(name, allowed_versions, dscp,vconnp) : 与对端建立连接(对应 socket, connect), 并初始化 vconn_stream, vconn, stream
vconn_run(vconn): 将 vconn_->txbuf 的数据发送出去
vconn_run_wait(vconn) : 如果 vconn->txbuf 不为空, 就将当前 socke fd 注册到 poll, 监听可写事件. 否则直接返回
vconn_open_block() : 与对端建立连接(对应 socket, connect), 直到成功或错误
vconn_close(vconn) : 关闭连接
vconn_connect(vconn): 从当前状态开始建立连接, 如果连接建立成功, 返回 0, 否则发送错误消息给对端
vconn_recv(vconn, msgp) : 从 vconn 接受消息保存在 vconn_stream->rxbuf
vconn_send(vconn, msg) : 将 msg 加入 vconn 的发送队列
vconn_connect_block(vconn) : 建立连接, 成功或失败
vconn_send_block(vconn, msg) : 将 msg 加入 vconn 对应 vconn_stream, 直到成功或错误(超时会重试).
vconn_recv_block(vconn, msgp): 从 vconn 接受消息保存在 vconn_stream->rxbuf.  直到成功或出错(超时会重试)
vconn_recv_xid(vconn, xid, replyp) : 接受指定 id 的消息
vconn_transact(vconn, request, replyp) : 发送 request, 直到收到 request 的应答信息
vconn_transact_noreply(vconn, request, replyp): 发送 request, 发送 barrier 消息, 直到收到 barrier 的应答
vconn_transact_multiple_noreply(vconn, requests,replyp) : requests 每条消息都调用 vconn_transact_noreply

TODO
vconn_init(vconn, class, connect_status, name, allowed_versions) : 用后面参数初始化 vconn
vconn_bundle_transact(vconn, requests, flags...): 基于事务将 requests 的多条消息一起发送
vconn_wait(vconn, wait) : 根据 vconn->state 设置 wait, 注册 vconn 对应 fd 的事件(可读, 可写)
vconn_connect_wait(vconn) : vconn_wait(vconn, WAIT_CONNECT);
vconn_recv_wait(vconn): vconn_wait(vconn, WAIT_SEND);

pvconn_init(pvconn, class, name, allowed_versions) : 根据后面的参数初始化 pvconn
pvconn_verify_name(name): 根据 name 找到指定的 class 类型, 确认 name 的参数合法
pvconn_open(name, allowed_versions, dscp, pvconnp) : 根据 name 找到 合适的 class, 调用 class->listen(name, allowed_versions, suffix_copy, &pvconn, dscp)
pvconn_close(pvconn) : (pvconn->pvclass->close)(pvconn)
pvconn_accept(pvconn, new_vconn) : (pvconn->pvclass->accept)(pvconn, new_vconn)
pvconn_wait(pvconn) :  (pvconn->pvclass->wait)(pvconn)


## 使用流程

* 建立连接

vconn_open_block() 或 vconn_open() + vconn_connect_block()

* 发送数据

vconn_send(vconn, msg)
vconn_send_block(vconn, msg)

pvconn_open() + pvconn_accept()

* 接受数据

vconn_recv(vconn, msg)
vconn_recv_block(vconn, msgp)
vconn_recv_xid(vconn, xid, replyp)
               struct ofpbuf **replyp)
vconn_transact(vconn, request, replyp)
vconn_transact_noreply(vconn, request, replyp)
vconn_transact_multiple_noreply(vconn, requests,replyp)
vconn_bundle_transact(vconn, requests, flags...)

* 关闭连接

vconn_close(vconn) : 关闭连接
pvconn_close() : 关闭监听

## 核心实现

int vconn_open(const char *name, uint32_t allowed_versions, uint8_t dscp, struct vconn **vconnp)
    vconn_lookup_class(name, &class);
    class->open(name, allowed_versions, suffix_copy, &vconn, dscp);
        tcp_vconn_class->open(name, allowed_versions, suffix_copy, &vconn, dscp)
            vconn_stream_open(name, allowed_versions, suffix_copy, &vconn, dscp)
        unix_vconn_class->open(name, allowed_versions, suffix_copy, &vconn, dscp)
            vconn_stream_open(name, allowed_versions, suffix_copy, &vconn, dscp)
        ssl_vconn_class->open(name, allowed_versions, suffix_copy, &vconn, dscp)
            vconn_stream_open(name, allowed_versions, suffix_copy, &vconn, dscp)
    *vconnp = vconn;

static int vconn_stream_open(name, allowed_versions, suffix_copy, &vconn, dscp)
    struct stream *streamp
    stream_open_with_default_port(name, OFP_PORT, &streamp, dscp);
        stream_open(name, streamp, dscp)
            stream_lookup_class(name, class)
            class->open(name, suffix_copy, streamp, dscp)
                tcp_stream_class->open(name, suffix_copy, streamp, dscp)
                    tcp_open(name, suffix_copy, streamp, dscp)
                        error = inet_open_active(SOCK_STREAM, suffix_copy, 0, NULL, &fd, dscp)
                            fd = socket(ss.ss_family, style, 0);
                            set_nonblocking(fd);
                            set_dscp(fd, ss.ss_family, dscp);
                            error = connect(fd, (struct sockaddr *) &ss, ss_length(&ss)) == 0 ? 0 : sock_errno();
                            return error
                        new_tcp_stream(name, fd, error, streamp)
                            new_fd_stream(name, fd, connect_status, AF_INET, streamp)
                                struct stream_fd *s
                                s = xmalloc(sizeof *s)
                                stream_init(&s->stream, &stream_fd_class, connect_status, name)
                                    s->stream->class = stream_fd_class
                                    s->stream->state = (connect_status == EAGAIN ? SCS_CONNECTING : !connect_status ? SCS_CONNECTED : SCS_DISCONNECTED)
                                    s->stream->error = connect_status
                                    s->stream->name = xstrdup(name)
                                s->fd = fd
                                s->fd_type = fd_type
                                *streamp = &s->stream
                unix_stream_class->open(name, suffix_copy, &stream, dscp)
                    unix_open(name, suffix_copy, &stream, dscp)
                        fd = make_unix_socket(SOCK_STREAM, true, NULL, connect_path);
                        new_fd_stream(name, fd, check_connection_completion(fd), AF_UNIX, streamp);
                ssl_stream_class->open(name, suffix_copy, &stream, dscp)
                    ssl_open
            *streamp = stream
    stream_connect(streamp)
    *vconn = vconn_stream_new(streamp, error, allowed_versions);
        struct vconn_stream *s;
        s = xmalloc(sizeof *s);
        vconn_init(&s->vconn, &stream_vconn_class, connect_status, stream_get_name(streamp), allowed_versions);
            s->vconn->vclass = stream_vconn_class
            s->vconn->state = (connect_status == EAGAIN ? VCS_CONNECTING : !connect_status ? VCS_SEND_HELLO : VCS_DISCONNECTED)
            s->vconn->error = connect_status
            s->vconn->allowed_versions = allowed_versions
            s->vconn->name = xstrdup(name)
        s->stream = streamp;
        s->txbuf = NULL;
        s->rxbuf = NULL;
        s->n_packets = 0;
        return s->vconn
    return 0

由上可知, 初始化过程 stream -> stread_fd -> vconn -> vconn_stream

除 open 之外, 所有的 stream 对应到 stream_fd_class, 所有的 vconn 对应到 stream_vconn_class

void vconn_run(struct vconn *vconn)
    if (vconn->vclass->run)
        (vconn->vclass->run)(vconn)
            stream_vconn_class->run(vconn)
                vconn_stream_run(vconn)
                    struct vconn_stream *s = vconn_stream_cast(vconn)
                    stream_run(s->stream);
                    retval = stream_send(s->stream, s->txbuf->data, s->txbuf->size)
                        stream_connect(s->stream)
                        (s->stream->class->send)(s->stream, buffer, n)
                            stream_fd_class->send(s->stream, buffer, n)
                                struct stream_fd *s = stream_fd_cast(stream);
                                send(s->fd, buffer, n, 0);
                    ofpbuf_pull(s->txbuf, retval);

void vconn_run_wait(struct vconn *vconn)
    if (vconn->vclass->run_wait)
        (vconn->vclass->run_wait)(vconn)
            stream_vconn_class->run_wait(vconn)
                struct vconn_stream *s = vconn_stream_cast(vconn)
                    stream_run_wait(s->stream)
                    if (s->txbuf)
                        stream_send_wait(s->stream)
                            stream_wait(s->stream, STREAM_SEND)
                                switch (s->stream->state) {
                                case SCS_CONNECTING:
                                    wait = STREAM_CONNECT;
                                    break;

                                case SCS_DISCONNECTED:
                                    poll_immediate_wake();
                                    return;
                                }
                                (s->stream->class->wait)(stream, wait)
                                    stream_fd_class->wait(stream, wait)
                                        fd_wait(stream, wait)
                                            struct stream_fd *s = stream_fd_cast(stream);
                                            switch (wait) {
                                            case STREAM_CONNECT:
                                            case STREAM_SEND:
                                                poll_fd_wait(s->fd, POLLOUT);
                                                break;

                                            case STREAM_RECV:
                                                poll_fd_wait(s->fd, POLLIN);
                                                break;

                                            default:
                                                OVS_NOT_REACHED();
                                            }

int vconn_open_block(const char *name, uint32_t allowed_versions, uint8_t dscp, struct vconn **vconnp)
    vconn_open(name, allowed_versions, dscp, &vconn)
    vconn_connect_block(vconn)
        while ((error = vconn_connect(vconn)) == EAGAIN) {
            vconn_run(vconn);
            vconn_run_wait(vconn);
            vconn_connect_wait(vconn);
            poll_block();
        }
    *vconnp = vconn;

void vconn_close(struct vconn *vconn)
    (vconn->vclass->close)(vconn);
        stream_vconn_class->close(vconn)
            vconn_stream_close(vconn)
                struct vconn_stream *s = vconn_stream_cast(vconn);
                stream_close(s->stream);
                    (stream->class->close)(stream);
                        stream_fd_class->close(stream)
                            fd_close(stream)
                                struct stream_fd *s = stream_fd_cast(stream);
                                closesocket(s->fd);
                                    close(s->fd)

static void scs_connecting(struct stream *stream)
    (stream->class->connect)(stream);
        stream_fd_class->connect(stream)
            fd_connect(stream)
                struct stream_fd *s = stream_fd_cast(stream);
                int retval = check_connection_completion(s->fd);
                    pfd.fd = s->fd;
                    pfd.events = POLLOUT;
                    do {
                        retval = poll(&pfd, 1, 0);
                    } while (retval < 0 && errno == EINTR);
                if (retval == 0 && s->fd_type == AF_INET)
                    setsockopt_tcp_nodelay(s->fd);
                        setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &on, sizeof on);

    int retval = (stream->class->connect)(stream);
    if (!retval)
        stream->state = SCS_CONNECTED;
    else if (retval != EAGAIN)
        stream->state = SCS_DISCONNECTED;
        stream->error = retval;

static void vcs_connecting(struct vconn *vconn)
    (vconn->vclass->connect)(vconn);
        stream_vconn_class->connect(vconn)
            vconn_stream_connect(vconn)
                struct vconn_stream *s = vconn_stream_cast(vconn);
                stream_connect(s->stream)

int vconn_connect(struct vconn *vconn)

    do {
        last_state = vconn->state;
        switch (vconn->state) {
        case VCS_CONNECTING:
            vcs_connecting(vconn);
            break;

        case VCS_SEND_HELLO:
            vcs_send_hello(vconn);
            break;

        case VCS_RECV_HELLO:
            vcs_recv_hello(vconn);
            break;

        case VCS_CONNECTED:
            return 0;

        case VCS_SEND_ERROR:
            vcs_send_error(vconn);
            break;

        case VCS_DISCONNECTED:
            return vconn->error;

        default:
            OVS_NOT_REACHED();
        }
    } while (vconn->state != last_state);

int vconn_recv(struct vconn *vconn, struct ofpbuf **msgp)
    retval = vconn_connect(vconn)
        retval = do_recv(vconn, &msgp)
            (vconn->vclass->recv)(vconn, msgp)
                stream_vconn_class->recv(vconn, msgp)
                    vconn_stream_recv(vconn, msgp)
                        struct vconn_stream *s = vconn_stream_cast(vconn);
                            if (s->rxbuf == NULL)
                                s->rxbuf = ofpbuf_new(1564);
                            if (s->rxbuf->size < sizeof(struct ofp_header))
                                vconn_stream_recv__(s, sizeof(struct ofp_header));
                                    stream_recv(s->stream, ofpbuf_tail(rx), want_bytes);
                                        stream_connect(s->stream);
                                        (stream->class->recv)(s->stream, ofpbuf_tail(rx), want_bytes));
                                            stream_fd_class->recv(s->stream, ofpbuf_tail(rx), want_bytes)
                                                fd_recv(s->stream, ofpbuf_tail(rx), want_bytes)
                                                    struct stream_fd *s = stream_fd_cast(stream);
                                                    recv(s->fd, ofpbuf_tail(rx), want_bytes, 0);
                                    rx->size += retval;
                            oh = s->rxbuf->data;
                            rx_len = ntohs(oh->length);
                            vconn_stream_recv__(s, rx_len);
                                stream_recv(s->stream, ofpbuf_tail(rx), want_bytes);
                                    stream_connect(s->stream);
                                    (stream->class->recv)(s->stream, ofpbuf_tail(rx), want_bytes));
                                        stream_fd_class->recv(s->stream, ofpbuf_tail(rx), want_bytes)
                                            fd_recv(s->stream, ofpbuf_tail(rx), want_bytes)
                                                struct stream_fd *s = stream_fd_cast(stream);
                                                recv(s->fd, ofpbuf_tail(rx), want_bytes, 0);
                                rx->size += retval;
                            s->n_packets++;
                            *msgp = s->rxbuf;
                            s->rxbuf = NULL;
        成功:
        const struct ofp_header *oh = msg->data;
        if (oh->version != vconn->version)
        成功:
            if (ofptype_decode(&type, msg->data)
                || (type != OFPTYPE_HELLO &&
                    type != OFPTYPE_ERROR &&
                    type != OFPTYPE_ECHO_REQUEST &&
                    type != OFPTYPE_ECHO_REPLY))
            失败:
                发送错误版本信息给对端
    失败:
        *msgp = retval ? NULL : msg;

建立连接并接受对端的消息, 将消息保存在 msgp 中

int vconn_send(struct vconn *vconn, struct ofpbuf *msg)

    vconn_connect(vconn);
    do_send(vconn, msg);
    (vconn->vclass->send)(vconn, msg);
        stream_vconn_class->send(vconn, msg)
            vconn_stream_send(vconn, msg)
                struct vconn_stream *s = vconn_stream_cast(vconn)
                    stream_send(s->stream, msg->data, msg->size)
                        stream_connect(s->stream)
                        (s->stream->class->send)(s->stream, msg->data, msg->size)
                            stream_fd_class->send(s->stream, msg->data, msg->size)
                                fd_send(s->stream, msg->data, msg->size)
                                    struct stream_fd *s = stream_fd_cast(s->stream);
                                    send(s->fd, msg->data, msg->size, 0);
                    s->txbuf = msg->data;
                    ofpbuf_pull(msg->data, retval);


int vconn_connect_block(struct vconn *vconn)

    while ((error = vconn_connect(vconn)) == EAGAIN) {
        vconn_run(vconn);
        vconn_run_wait(vconn);
        vconn_connect_wait(vconn);
        poll_block();
    }

int vconn_send_block(struct vconn *vconn, struct ofpbuf *msg)

    while ((retval = vconn_send(vconn, msg)) == EAGAIN) {
        vconn_run(vconn);
        vconn_run_wait(vconn);
        vconn_send_wait(vconn);
        poll_block();
    }

int vconn_recv_block(struct vconn *vconn, struct ofpbuf **msgp)

    while ((retval = vconn_recv(vconn, msgp)) == EAGAIN) {
        vconn_run(vconn);
        vconn_run_wait(vconn);
        vconn_recv_wait(vconn);
        poll_block();
    }

void vconn_wait(struct vconn *vconn, enum vconn_wait_type wait)

    switch (vconn->state) {
    case VCS_CONNECTING:
        wait = WAIT_CONNECT;
        break;

    case VCS_SEND_HELLO:
    case VCS_SEND_ERROR:
        wait = WAIT_SEND;
        break;

    case VCS_RECV_HELLO:
        wait = WAIT_RECV;
        break;

    case VCS_CONNECTED:
        break;

    case VCS_DISCONNECTED:
        poll_immediate_wake();
        return;
    }
    (vconn->vclass->wait)(vconn, wait);
        stream_vconn_class->wait(vconn, wait)
            vconn_stream_wait(vconn, wait)
                struct vconn_stream *s = vconn_stream_cast(vconn);
                switch (wait) {
                case WAIT_CONNECT:
                    stream_connect_wait(s->stream);
                    break;

                case WAIT_SEND:
                    if (!s->txbuf) {
                        stream_send_wait(s->stream);
                    } else {
                        /* Nothing to do: need to drain txbuf first.
                         * vconn_stream_run_wait() will arrange to wake up when there room
                         * to send data, so there's no point in calling poll_fd_wait()
                         * redundantly here. */
                    }
                    break;

                case WAIT_RECV:
                    stream_recv_wait(s->stream);
                    break;

                default:
                    OVS_NOT_REACHED();
                }

void vconn_connect_wait(struct vconn *vconn)
    vconn_wait(vconn, WAIT_CONNECT);

void vconn_recv_wait(struct vconn *vconn)
    vconn_wait(vconn, WAIT_RECV);

void vconn_send_wait(struct vconn *vconn)
    vconn_wait(vconn, WAIT_SEND);

int pvconn_open(const char *name, uint32_t allowed_versions, uint8_t dscp, struct pvconn **pvconnp)

    pvconn_lookup_class(name, &class);
    class->listen(name, allowed_versions, suffix_copy, &pvconnp, dscp);
        tcp_vconn_class->listen(name, allowed_versions, suffix_copy, &pvconnp, dscp)
            pstream_pvconn_class->listen(name, allowed_versions, suffix_copy, &pvconnp, dscp)
                pvconn_pstream_listen(name, allowed_versions, suffix_copy, &pvconnp, dscp)
                    struct pvconn_pstream *ps;
                    struct pstream *pstream;
                    pstream_open_with_default_port(name, OFP_PORT, &pstream, dscp);
                        pstream_open(name, pstreamp, dscp);
                            struct pstream *pstream;
                            pstream_lookup_class(name, &class);
                            class->listen(name, suffix_copy, &pstream, dscp);
                                tcp_stream_class->listen(name, suffix_copy, &pstream, dscp)
                                    ptcp_open(name, suffix_copy, &pstream, dscp)
                                        new_pstream(suffix, NULL, pstreamp, dscp, NULL, true)
                                            fd = inet_open_passive(SOCK_STREAM, suffix, -1, &ss, dscp, kernel_print_port);
                                                fd = socket(ss.ss_family, SOCK_STREAM, 0);
                                                set_nonblocking(fd);
                                                setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes)
                                                bind(fd, (struct sockaddr *) &ss, ss_length(&ss)) < 0)
                                                set_dscp(fd, ss.ss_family, dscp);
                                                listen(fd, 10)
                                            port = ss_get_port(&ss)
                                            new_fd_pstream(conn_name, fd, ptcp_accept, unlink_path, pstreamp)
                                                struct fd_pstream *ps = xmalloc(sizeof *ps)
                                                pstream_init(&ps->pstream, &fd_pstream_class, name)
                                                    memset(pstream, 0, sizeof *pstream)
                                                    pstream->class = fd_pstream_class
                                                    pstream->name = xstrdup(name);
                                                ps->fd = fd;
                                                ps->accept_cb = ptcp_accept;
                                                ps->unlink_path = unlink_path
                                                *pstreamp = &ps->pstream
                                            pstream_set_bound_port(pstreamp, htons(port))
                                                pstream->bound_port = port
                                unix_stream_class->listen(name, suffix_copy, &pstream, dscp)
                                    punix_open(name, suffix_copy, &pstream, dscp)
                                        fd = make_unix_socket(SOCK_STREAM, true, bind_path, NULL);
                                        listen(fd, 64)
                                        new_fd_pstream(name, fd, punix_accept, bind_path, pstreamp);
                                ssl_stream_class->listen(name, suffix_copy, &pstream, dscp)
                                    pssl_open(name, suffix_copy, &pstream, dscp)
                            *pstreamp = pstream
                    ps = xmalloc(sizeof *ps)
                    pvconn_init(&ps->pvconn, &pstream_pvconn_class, name, allowed_versions)
                        pvconn->pvclass = pstream_pvconn_class
                        pvconn->name = xstrdup(name)
                        pvconn->allowed_versions = allowed_versions
                    ps->pstream = pstream
                    *pvconnp = &ps->pvconn
        unix_vconn_class->listen(name, allowed_versions, suffix_copy, &pvconnp, dscp)
            pstream_pvconn_class->listen(name, allowed_versions, suffix_copy, &pvconnp, dscp)
        ssl_vconn_class->listen(name, allowed_versions, suffix_copy, &pvconnp, dscp)
            pstream_pvconn_class->listen(name, allowed_versions, suffix_copy, &pvconnp, dscp)

void pvconn_close(struct pvconn *pvconn)
    (pvconn->pvclass->close)(pvconn)
        pstream_pvconn_class->close(pvconn)
            pvconn_pstream_close(pvconn)
                struct pvconn_pstream *ps = pvconn_pstream_cast(pvconn);
                pstream_close(ps->pstream)
                    (pstream->class->close)(pstream)
                        fd_pstream_class->close(pstream)
                            pfd_close(pstream)
                                struct fd_pstream *ps = fd_pstream_cast(pstream);
                                closesocket(ps->fd);
                                    close(ps->fd)
                                maybe_unlink_and_free(ps->unlink_path);

int pvconn_accept(struct pvconn *pvconn, struct vconn **new_vconnp)
    (pvconn->pvclass->accept)(pvconn, new_vconnp);
        pstream_pvconn_class->accept(pvconn)
            pvconn_pstream_accept(pvconn)
                struct pvconn_pstream *ps = pvconn_pstream_cast(pvconn);
                struct stream *new_streamp;
                pstream_accept(ps->pstream, &new_streamp);
                    (ps->pstream->class->accept)(ps->pstream, new_streamp);
                        fd_pstream_class->accept(ps->pstream, new_streamp)
                            pfd_accept(ps->pstream, new_streamp)
                                struct fd_pstream *fps = fd_pstream_cast(ps->pstream);
                                new_fd = accept(fps->fd, (struct sockaddr *) &ss, &ss_len);
                                set_nonblocking(new_fd);
                                fps->accept_cb(new_fd, &ss, ss_len, new_streamp)
                                    ptcp_accept(new_fd, &ss, ss_len, new_streamp)
                                        new_tcp_stream(name, fd, 0, new_streamp)
                                            new_fd_stream(name, fd, connect_status, AF_INET, new_streamp)
                                                struct stream_fd *s
                                                s = xmalloc(sizeof *s)
                                                stream_init(&s->stream, &stream_fd_class, connect_status, name)
                                                    s->stream->class = stream_fd_class
                                                    s->stream->state = (connect_status == EAGAIN ? SCS_CONNECTING : !connect_status ? SCS_CONNECTED : SCS_DISCONNECTED)
                                                    s->stream->error = connect_status
                                                    s->stream->name = xstrdup(name)
                                                s->fd = fd
                                                s->fd_type = fd_type
                                                *new_streamp = &s->stream
                                    punix_accept(new_fd, &ss, ss_len, new_streamp)
                                        new_fd_stream(name, fd, 0, AF_UNIX, streamp);
                *new_vconnp = vconn_stream_new(new_streamp, 0, pvconn->allowed_versions);
                    struct vconn_stream *s;
                    s = xmalloc(sizeof *s);
                    vconn_init(&s->vconn, &stream_vconn_class, connect_status, stream_get_name(stream), allowed_versions);
                        s->vconn->vclass = class;
                        s->vconn->state = (connect_status == EAGAIN ? VCS_CONNECTING : !connect_status ? VCS_SEND_HELLO : VCS_DISCONNECTED);
                        s->vconn->error = connect_status;
                        s->vconn->allowed_versions = allowed_versions;
                        s->vconn->name = xstrdup(name);
                    s->stream = new_streamp;
                    s->txbuf = NULL;
                    s->rxbuf = NULL;
                    s->n_packets = 0;
                    return &s->vconn;


void pvconn_wait(struct pvconn *pvconn)
    (pvconn->pvclass->wait)(pvconn);
        pstream_pvconn_class->wait(pvconn)
            pvconn_pstream_wait(pvconn)
                struct pvconn_pstream *ps = pvconn_pstream_cast(pvconn);
                pstream_wait(ps->pstream);
                    (pstream->class->wait)(pstream);
                        fd_pstream_class->wait(pstream)
                            pfd_wait(pstream)
                                struct fd_pstream *ps = fd_pstream_cast(pstream);
                                poll_fd_wait(ps->fd, POLLIN);

int stream_open_block(int error, struct stream **streamp)

    while ((error = stream_connect(stream)) == EAGAIN)
        stream_run(stream);
        stream_run_wait(stream);
        stream_connect_wait(stream);
        poll_block();

    *streamp = stream;

int stream_connect(struct stream *stream)

    do {
        last_state = stream->state;
        switch (stream->state) {
        case SCS_CONNECTING:
            scs_connecting(stream);
                (stream->class->connect)(stream);
                    stream_fd_class->connect(stream)
                        fd_connect(stream)
                            struct stream_fd *s = stream_fd_cast(stream);
                            int retval = check_connection_completion(s->fd);
                                pfd.fd = s->fd;
                                pfd.events = POLLOUT;
                                do {
                                    retval = poll(&pfd, 1, 0);
                                } while (retval < 0 && errno == EINTR);
                            if (retval == 0 && s->fd_type == AF_INET)
                                setsockopt_tcp_nodelay(s->fd);
                                    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &on, sizeof on);
                if (!retval)
                    stream->state = SCS_CONNECTED;
                else if (retval != EAGAIN)
                    stream->state = SCS_DISCONNECTED;
                    stream->error = retval;
            break;

        case SCS_CONNECTED:
            return 0;

        case SCS_DISCONNECTED:
            return stream->error;

        default:
            OVS_NOT_REACHED();
        }
    } while (stream->state != last_state);

void stream_run(struct stream *stream)
    目前 if 条件为 false
    if (stream->class->run)
        (stream->class->run)(stream)


void stream_run_wait(struct stream *stream)
    目前 if 条件为 false
    if (stream->class->run_wait)
        (stream->class->run_wait)(stream)

void stream_wait(struct stream *stream, enum stream_wait_type wait)

    switch (s->stream->state) {
    case SCS_CONNECTING:
        wait = STREAM_CONNECT;
        break;

    case SCS_DISCONNECTED:
        poll_immediate_wake();
        return;
    }
    (s->stream->class->wait)(stream, wait)
        stream_fd_class->wait(stream, wait)
            fd_wait(stream, wait)
                struct stream_fd *s = stream_fd_cast(stream);
                switch (wait) {
                case STREAM_CONNECT:
                case STREAM_SEND:
                    poll_fd_wait(s->fd, POLLOUT);
                    break;

                case STREAM_RECV:
                    poll_fd_wait(s->fd, POLLIN);
                    break;

                default:
                    OVS_NOT_REACHED();
                }

void stream_connect_wait(struct stream *stream)

    stream_wait(stream, STREAM_CONNECT);

void stream_recv_wait(struct stream *stream)

    stream_wait(stream, STREAM_RECV);

int pstream_accept_block(struct pstream *pstream, struct stream **new_stream)

    while ((error = pstream_accept(pstream, new_stream)) == EAGAIN) {
        pstream_wait(pstream);
            (pstream->class->wait)(pstream);
                fd_pstream_class->wait(pstream)
                    pfd_wait(pstream)
                        struct fd_pstream *ps = fd_pstream_cast(pstream);
                        poll_fd_wait(ps->fd, POLLIN);
        poll_block();
    }

void pstream_wait(struct pstream *pstream)
    (pstream->class->wait)(pstream);
        fd_pstream_class->wait(pstream)
            pfd_wait(pstream)
                struct fd_pstream *ps = fd_pstream_cast(pstream);
                poll_fd_wait(ps->fd, POLLIN);

## 附录

注: 这部分代码非常直观明了, 因此包含了精简后的源码.有时候比文字更好说明问题

static void check_vconn_classes(void)

    校验 vconn_classes 和 pvconn_classes 的每个元素

static int vconn_lookup_class(const char *name, const struct vconn_class **classp)

    从 vconn_classes 中解析出 name = vconn_classes[i]->name , 初始化 classp.
    其中 name 格式为 "TYPE:ARGS" 如 "tcp:192.168.1.1:6633"

    例子:
    vconn_lookup_class("tcp", class) class 指向 tcp_vconn_class
    vconn_lookup_class("udp", class) class 指向 NULL
    vconn_lookup_class("unix", class) class 指向 unix_vconn_class

int vconn_verify_name(const char *name)

    等于 vconn_lookup_class

    注: vconn->state 必须不是 VCS_CONNECTING 并且 vconn->vclass->connect 不能为 NULL

int vconn_get_status(const struct vconn *vconn)

    连接处于正常, 返回 0;
    如果错误, 返回正数;
    如果正常关闭,返回 EOF


void vconn_set_recv_any_version(struct vconn *vconn)

    vconn->recv_any_version = true;

    By default, a vconn accepts only OpenFlow messages whose version matches the
    one negotiated for the connection.  A message received with a different
    version is an error that causes the vconn to drop the connection.

    This functions allows 'vconn' to accept messages with any OpenFlow version.
    This is useful in the special case where 'vconn' is used as an rconn
    "monitor" connection (see rconn_add_monitor()), that is, where 'vconn' is
    used as a target for mirroring OpenFlow messages for debugging and
    troubleshooting.

    This function should be called after a successful vconn_open() or
    pvconn_accept() but before the connection completes, that is, before
    vconn_connect() returns success.  Otherwise, messages that arrive on 'vconn'
    beforehand with an unexpected version will the vconn to drop the
    connection.

static void vcs_send_hello(struct vconn *vconn)

    b = ofputil_encode_hello(vconn->allowed_versions);
    retval = do_send(vconn, b);
    成功:
        vconn->state = VCS_RECV_HELLO;
    失败
        if (retval != EAGAIN)
            vconn->state = VCS_DISCONNECTED;
            vconn->error = retval;

static char *version_bitmap_to_string(uint32_t bitmap)

    从 bitmap  解析 OF 的版本信息, 返回版本信息

static void vcs_recv_hello(struct vconn *vconn)

    接受 OFPT_HELLO 消息, 并确认两端的版本兼容, 最后设置 vconn->version; vconn->state = VCS_CONNECTED

    retval = do_recv(vconn, &b);
    成功:
        error = ofptype_decode(&type, b->data);
        成功:
            ofputil_decode_hello(b->data, &vconn->peer_versions))
            common_versions = vconn->peer_versions & vconn->allowed_versions;
            失败:
                vconn->version = leftmost_1bit_idx(vconn->peer_versions);
                输出错误消息
                vconn->state = VCS_SEND_ERROR;
            成功:
                vconn->version = leftmost_1bit_idx(common_versions);
                vconn->state = VCS_CONNECTED;

        失败:
            输出错误消息
            设置 retval = EPROTO

    失败
        vconn->state = VCS_DISCONNECTED;
        vconn->error = retval == EOF ? ECONNRESET : retval;


static void vcs_send_error(struct vconn *vconn)

    发送版本协商的错误信息

    local_s = version_bitmap_to_string(vconn->allowed_versions);
    peer_s = version_bitmap_to_string(vconn->peer_versions);
    snprintf(s, sizeof s, "We support %s, you support %s, no common versions.",
             local_s, peer_s);
    b = ofperr_encode_hello(OFPERR_OFPHFC_INCOMPATIBLE, vconn->version, s);
    retval = do_send(vconn, b);
    成功:
        ofpbuf_delete(b);
    失败
        if (retval != EAGAIN)
            vconn->state = VCS_DISCONNECTED;
            vconn->error = retval ? retval : EPROTO;

static int vconn_recv_xid__(struct vconn *vconn, ovs_be32 xid, struct ofpbuf **replyp, void (*error_reporter)(const struct ofp_header *))

    一直循环直到收到消息 data->xid = xid, 返回.

    for(;;)
        vconn_recv_block(vconn, &reply);
        成功:
            oh = reply->data;
            recv_xid = oh->xid;
            if (xid == recv_xid)
            成功:
                *replyp = reply;
                return 0;
            error = ofptype_decode(&type, oh);
        失败:
            *replyp = NULL;
            return error;


int vconn_recv_xid(struct vconn *vconn, ovs_be32 xid, struct ofpbuf **replyp)

    return vconn_recv_xid__(vconn, xid, replyp, NULL);

    Waits until a message with a transaction ID matching 'xid' is received on
    'vconn'.  Returns 0 if successful, in which case the reply is stored in
    '*replyp' for the caller to examine and free.  Otherwise returns a positive
    errno value, or EOF, and sets '*replyp' to null.

    'request' is always destroyed, regardless of the return value. */


static int vconn_transact__(struct vconn *vconn, struct ofpbuf *request, struct ofpbuf **replyp,
        void (*error_reporter)(const struct ofp_header *))

    发送一条消息, 阻塞直到收到应答.

    error = vconn_send_block(vconn, request);
    ovs_be32 send_xid = ((struct ofp_header *) request->data)->xid;
    成功:
        return vconn_recv_xid__(vconn, send_xid, replyp, error_reporter);
    失败:
        return error

int vconn_transact(struct vconn *vconn, struct ofpbuf *request,
               struct ofpbuf **replyp)

    发送一条消息, 阻塞直到收到应答.(同 vconn_transact__)


int vconn_transact_noreply(struct vconn *vconn, struct ofpbuf *request, struct ofpbuf **replyp)

    发送一条消息, 并且发送 barrier 消息, 直到收到的消息的 msg_xid 等于发送 barrier_xid

    request_xid = ((struct ofp_header *) request->data)->xid;
    error = vconn_send_block(vconn, request);
    失败: 返回 error

    barrier = ofputil_encode_barrier_request(vconn_get_version(vconn));
    barrier_xid = ((struct ofp_header *) barrier->data)->xid;
    error = vconn_send_block(vconn, barrier);
    失败: 返回 error

    for (;;)
        error = vconn_recv_block(vconn, &msg);
        失败: 退出循环
        直到 msg_xid == barrier_xid

    问题: msg_xid == request_xid 没有出现会有问题么?

int vconn_transact_multiple_noreply(struct vconn *vconn, struct ovs_list *requests, struct ofpbuf **replyp)

    遍历 requests 的每个元素 request, 调用 vconn_transact_noreply(vconn, request, replyp)

static enum ofperr vconn_bundle_reply_validate(struct ofpbuf *reply, struct ofputil_bundle_ctrl_msg *request, void (*error_reporter)(const struct ofp_header *))

    对 bundle 控制消息进行验证

    oh = reply->data;
    error = ofptype_decode(&type, oh);
    if (type == OFPTYPE_ERROR)
        return ofperr_decode_msg(oh, NULL);
    if (type != OFPTYPE_BUNDLE_CONTROL)
        return OFPERR_OFPBRC_BAD_TYPE;

    ofputil_decode_bundle_ctrl(oh, &rbc);
    if (rbc.bundle_id != request->bundle_id)
        return OFPERR_OFPBFC_BAD_ID;
    if (rbc.type != request->type + 1)
        return OFPERR_OFPBFC_BAD_TYPE;
    return 0;

static int vconn_bundle_control_transact(struct vconn *vconn, struct ofputil_bundle_ctrl_msg *bc, uint16_t type, void (*error_reporter)(const struct ofp_header *))

    对 bc 进行编码, 之后发送, 等收到应答后, 对应答 bundle 控制消息进行校验

    bc->type = type;
    request = ofputil_encode_bundle_ctrl_request(vconn->version, bc);
    vconn_transact__(vconn, request, &reply, error_reporter);
    vconn_bundle_reply_validate(reply, bc, error_reporter);


static void vconn_recv_error(struct vconn *vconn, void (*error_reporter)(const struct ofp_header *))

    专门接受消息类型为 OFPTYPE_ERROR 的消息, 直到收消息出错

static int vconn_bundle_add_msg(struct vconn *vconn, struct ofputil_bundle_ctrl_msg *bc, struct ofpbuf *msg,
                     void (*error_reporter)(const struct ofp_header *))


    发送一个 bundle_add 消息, 接受错误类型的消息直到接受错误消息出错.

    bam.bundle_id = bc->bundle_id;
    bam.flags = bc->flags;
    bam.msg = msg->data;
    request = ofputil_encode_bundle_add(vconn->version, &bam);
    error = vconn_send_block(vconn, request);
    成功:
        vconn_recv_error(vconn, error_reporter);
    return error

int vconn_bundle_transact(struct vconn *vconn, struct ovs_list *requests, uint16_t flags, void (*error_reporter)(const struct ofp_header *))

    以事务遍历 requests 每一个元素, 发送 bundle_add 消息

    memset(&bc, 0, sizeof bc);
    bc.flags = flags;
    vconn_bundle_control_transact(vconn, &bc, OFPBCT_OPEN_REQUEST, error_reporter);

    LIST_FOR_EACH (request, list_node, requests)
        error = vconn_bundle_add_msg(vconn, &bc, request, error_reporter);
        失败:
            break;

    成功:
        vconn_bundle_control_transact(vconn, &bc, OFPBCT_COMMIT_REQUEST,  error_reporter);
    失败
        vconn_bundle_control_transact(vconn, &bc, OFPBCT_DISCARD_REQUEST, error_reporter);

### pvconn

static int pvconn_lookup_class(const char *name, const struct pvconn_class **classp)

    根据 name 从 pvconn_classes 中找到合适的 pvconn_class , 其中 name 为 "TYPE:ARGS"

int pvconn_verify_name(const char *name)

    调用 pvconn_lookup_class(name)

int pvconn_accept(struct pvconn *pvconn, struct vconn **new_vconn)

    非阻塞调用 (pvconn->pvclass->accept)(pvconn, new_vconn)
    成功:
        将连接保持在 new_vconn
    失败:
        如果没有新的连接返回 EAGAIN

static struct vconn_stream * vconn_stream_cast(struct vconn *vconn)

    由 vconn 获取其所属 vconn_stream

static void vconn_stream_clear_txbuf(struct vconn_stream *s)

    ofpbuf_delete(s->txbuf);
    s->txbuf = NULL;

static struct pvconn_pstream * pvconn_pstream_cast(struct pvconn *pvconn)

    由 pvconn 定位到其所属 pvconn_pstream
