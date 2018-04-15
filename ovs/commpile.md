


对性能影响的因素

1. threads.h 中对 thread_local 的支持
2. stdatomic.h 的支持需要 4.9 c11
3. sse 指令对 hash 计算
4. coverage : 可以获取一些统计信息, 对于性能的损耗带来的好处更多



安装

./configure --prefix=/opt/ovs --datadir=/opt/ovs/data LIBS=-ljemalloc --enable-coverage CFLAGS="-g -O2 -march=native"
./configure --prefix=/opt/ovs --datadir=/opt/ovs/data LDFLAGS=-L/root/package/ovs/jemalloc-4.5.0 --enable-coverage CFLAGS="-g -O2 -march=native"
wget -c https://github.com/jemalloc/jemalloc/releases/download/4.5.0/jemalloc-4.5.0.tar.bz2


/opt/ovs/bin/ovsdb-tool create /opt/ovs/etc/openvswitch/conf.db vswitchd/vswitch.ovsschema
/opt/ovs/sbin/ovsdb-server --remote=punix:/opt/ovs/var/run/openvswitch/db.sock --remote=db:Open_vSwitch,Open_vSwitch,manager_options --pidfile --detach --log-file
/opt/ovs/bin/ovs-vsctl --no-wait init
/opt/ovs/sbin/ovs-vswitchd --pidfile --detach --log-file
