
## 问题

1. barrier 的工作原理?

    一方面
    1. 每个线程调用 ovs_barrier_block 时, 记录当前的 barrier->seq, 并将 barrier->count 加 1
    2. 当 barrier->count != barrier->size, 阻塞在 ovs_barrier_block, 监听并轮询检查 barrier->seq 是否改变.

    另一方面
    1. 当所有线程都调用 ovs_barrier_block 时, barrier->count == barrier->size,
       此时, 改变 barrier->seq
    2. 监听 barrier->seq 的线程发现 barrier->seq 被改变, 程序继续处理 ovs_barrier_block 之后的代码



## 数据结构

struct ovs_barrier {
    uint32_t size;            //需要 barrier 的线程个数
    atomic_count count;       //当前有多少个线程等待在 barrier 状态
    struct seq *seq;          //继续 barrier 调用次数, 已经是否进行下一个
};

## 核心实现

void ovs_barrier_init(struct ovs_barrier *barrier, uint32_t size)

    初始化 ovs_barrier

void ovs_barrier_destroy(struct ovs_barrier *barrier)

    销毁 ovs_barrier

void ovs_barrier_block(struct ovs_barrier *barrier)

    一方面
    1. 每个线程调用 ovs_barrier_block 时, 记录当前的 barrier->seq, 并将 barrier->count 加 1
    2. 当 barrier->count != barrier->size, 阻塞在 ovs_barrier_block, 监听并轮询检查 barrier->seq 是否改变.

    另一方面
    1. 当所有线程都调用 ovs_barrier_block 时, barrier->count == barrier->size,
       此时, 改变 barrier->seq
    2. 监听 barrier->seq 的线程发现 barrier->seq 被改变, 程序继续处理 ovs_barrier_block 之后的代码
