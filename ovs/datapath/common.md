
一些通用的函数

flow.c 中由很多可以参考

计算时间间隔

    ovs_flow_used_time

获取所属 numa 节点 id

    numa_node_id()

遍历每个 numa 节点

	int node;
	for_each_node(node) {
    }

每个 cpu 的状态

    struct vport {
	    struct pcpu_sw_netstats __percpu *percpu_stats;
    }

    初始化

    vport->percpu_stats = netdev_alloc_pcpu_stats(struct pcpu_sw_netstats);


    struct ovs_vport_stats *stats
	int i;
	for_each_possible_cpu(i) {
		const struct pcpu_sw_netstats *percpu_stats;
		struct pcpu_sw_netstats local_stats;
		unsigned int start;

		percpu_stats = per_cpu_ptr(vport->percpu_stats, i);

		do {
			start = u64_stats_fetch_begin_irq(&percpu_stats->syncp);
			local_stats = *percpu_stats;
		} while (u64_stats_fetch_retry_irq(&percpu_stats->syncp, start));

		stats->rx_bytes		+= local_stats.rx_bytes;
		stats->rx_packets	+= local_stats.rx_packets;
		stats->tx_bytes		+= local_stats.tx_bytes;
		stats->tx_packets	+= local_stats.tx_packets;
    }


    更新
	stats = this_cpu_ptr(vport->percpu_stats);
	u64_stats_update_begin(&stats->syncp);
	stats->rx_packets++;
	stats->rx_bytes += skb->len + (skb_vlan_tag_present(skb) ? VLAN_HLEN : 0);
	u64_stats_update_end(&stats->syncp);


    static inline void u64_stats_update_begin(struct u64_stats_sync *syncp)
    {
    #if BITS_PER_LONG==32 && defined(CONFIG_SMP)
    	write_seqcount_begin(&syncp->seq);
    #endif
    }

    static inline void u64_stats_update_end(struct u64_stats_sync *syncp)
    {
    #if BITS_PER_LONG==32 && defined(CONFIG_SMP)
    	write_seqcount_end(&syncp->seq);
    #endif
    }

    #if !defined this_cpu_ptr
    #define this_cpu_ptr(ptr) per_cpu_ptr(ptr, smp_processor_id())
    #endif
