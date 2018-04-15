

## OVS 多线程基础设施

### 只初始化一次

bool ovsthread_once_start__(struct ovsthread_once *once)
ovsthread_once_done(struct ovsthread_once *once)

通过原子操作, 实现多个线程对一个变量只初始化一次


### 多线程创建



### Mutex 锁

### RCU 锁




### 读写锁

    #define L1_SIZE 1024
    #define L2_SIZE 1024
    #define MAX_KEYS (L1_SIZE * L2_SIZE)

struct ovsthread_key {
    struct list list_node;      /* In 'inuse_keys' or 'free_keys'. */
    void (*destructor)(void *); /* Called at thread exit. */

    /* Indexes into the per-thread array in struct ovsthread_key_slots.
     * This key's data is stored in p1[index / L2_SIZE][index % L2_SIZE]. */
    unsigned int index;
};

struct ovsthread_key_slots {
    struct list list_node;      /* In 'slots_list'. */
    void **p1[L1_SIZE];
};

typedef struct ovsthread_key *ovsthread_key_t;

static pthread_key_t tsd_key;
static struct ovs_mutex key_mutex = OVS_MUTEX_INITIALIZER;

static struct list inuse_keys OVS_GUARDED_BY(key_mutex) = LIST_INITIALIZER(&inuse_keys);
static struct list free_keys OVS_GUARDED_BY(key_mutex) = LIST_INITIALIZER(&free_keys);
static unsigned int n_keys OVS_GUARDED_BY(key_mutex);

static struct list slots_list OVS_GUARDED_BY(key_mutex) = LIST_INITIALIZER(&slots_list);

其中:

    tsd_key    每个线程专属的 pthread_key_t, 它对应的 value 为 ovsthread_key_slots
    key_mutex  保护多线程同时创建 ovsthread_key 和 设置 tsd_key
    inuse_keys 表示正在使用的 ovsthread_key
    free_keys  表示没有使用的 ovsthread_key
    n_keys     表示总共创建的 ovsthread_key
    slots_list 保存每个线程 tsd_key 对应的 ovsthread_key_slots

每个线程的 tsd_key 都对应一个 slot(类型为 ovsthread_key_slots), slot->p1 是一个
1024*1024 的二维数组属性, 每个 ovsthread_key_t 都保存在该二维数组中,
ovsthread_key_t->index 即数组索引, sloct->p1 的每一个元素保存一对线程专属的 key, value
通过 ovsthread_getspecific 和 ovsthread_setspecific 获取和设置


void ovsthread_key_create(ovsthread_key_t *keyp, void (*destructor)(void *))

创建一个 ovsthread_key_t

如果 free_keys 中有空余的, 就直接从 free_keys 中删除一个, 加入 inuse_keys;
如果 free_keys 没有, 就创建一个, n_keys 加1, 并加入 inuse_keys;

如果创建的 ovsthread_key_t 的数量超过 MAX_KEYS, 程序直接退出

void ovsthread_key_delete(ovsthread_key_t key)

删除一个 ovsthread_key_t

将 key 从  inuse_keys 中删除, 加入 free_keys; 并从所属 slots 中删除


static void * clear_slot(struct ovsthread_key_slots *slots, unsigned int index)

static void ovsthread_key_destruct__(void *slots_)


void * ovsthread_getspecific(ovsthread_key_t key)

获取 key 对应的 value

void ovsthread_setspecific(ovsthread_key_t key, const void *value)

设置 key 对应的 value

