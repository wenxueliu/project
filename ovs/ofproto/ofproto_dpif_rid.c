
## 全局变量

struct cmap id_map;
struct cmap metadata_map;

struct ovs_list expiring OVS_GUARDED_BY(mutex);
struct ovs_list expired OVS_GUARDED_BY(mutex);
