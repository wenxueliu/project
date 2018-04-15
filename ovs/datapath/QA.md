
## vport_ops 目前支持几种类型, 每种特点?

vport_ops 支持如下类型

* ovs_internal_vport_ops
* ovs_gre_vport_ops
* ovs_gre64_vport_ops
* ovs_netdev_vport_ops
* ovs_lisp_vport_ops
* ovs_stt_vport_ops
* ovs_vxlan_vport_ops
* ovs_geneve_vport_ops

不同的 vport_ops 以 type 进行区分, 通过 ovs_vport_ops_register 注册到链表 vport_ops_list 中

可以通过搜索 ovs_vport_ops_register 确认

通过 ovs_vport_lookup 从 vport_ops_list 中查询 vport_ops

## vport

存储在 dev_table 和 dp->ports 两个地方

其中 dev_table 是一个哈希表, 桶的大小为 1024, 通过 name, net 进行哈希

通过 ovs_vport_locate 从 dev_table 中查询 name, net 对应的 vport

vport 的属性完全依赖外部传参

## vport 是如何加入内核的

    通过 ovs_vport_add 加入内核, 参加 ovs_dp_cmd_new 的实现

    vport_add(parms) : 增加给定类型的 vport
    ovs_vport_lookup(parms)
        对于 ovs_internal_vport_ops : 类型 OVS_VPORT_TYPE_INTERNAL
            internal_dev_create
                vport = ovs_vport_alloc(sizeof(struct netdev_vport), &ovs_internal_vport_ops, parms);
                alloc_netdev
                register_netdevice
                dev_set_promiscuity
                netif_start_queue
        对于 ovs_netdev_vport_ops
            netdev_create
                vport = ovs_vport_alloc(sizeof(struct netdev_vport), &ovs_netdev_vport_ops, parms);
                dev_get_by_name(ovs_dp_get_net(vport->dp), parms->name);
                netdev_master_upper_dev_link(netdev_vport->dev, get_dpdev(vport->dp));
                netdev_rx_handler_register(netdev_vport->dev, netdev_frame_hook, vport);
                dev_set_promiscuity(netdev_vport->dev, 1);
                netdev_vport->dev->priv_flags |= IFF_OVS_DATAPATH;
            bucket = hash_bucket(ovs_dp_get_net(vport->dp), vport->ops->get_name(vport));
            hlist_add_head_rcu(&vport->hash_node, bucket);
    request_module("vport-type-%d", parms->type);
    ovs_vport_lookup : 确认已经添加

## vport 的统计是如何实现的

    vport 的统计信息放在每个 cpu 存一份. 在获取的时候, 将各个 cpu 的数据汇总

## vport 的收包是为如何实现的?

    创建 netdev_create(const struct vport_parms *parms) 的注册的 rx_handler_result_t netdev_frame_hook( pskb)



        对于 internal_dev
        internal_dev_xmit(skb, netdev)
	        ovs_vport_receive(internal_dev_priv(netdev)->vport, skb, NULL);
                ovs_flow_key_extract(NULL, skb, &key)
                    key_extract(skb, key)
                ovs_dp_process_packet(skb, &key)
                    flow = ovs_flow_tbl_lookup_stats(&dp->table, key, skb_get_hash(skb), &n_mask_hit)
                        true:
                            ovs_dp_upcall(dp, skb, key, upcall_info)
                                skb_is_gso(skb):
                                    queue_gso_packets(dp, skb, key, upcall_info)
                                !skb_is_gso(skb) :
                                    queue_userspace_packet(dp, skb, key, upcall_info)
                            n_lost++
                        false:
                            ovs_execute_actions(dp, skb, acts, key)
                            do_execute_actions(dp, skb, key, flow->sf_acts->actions, flow->sf_acts->actions_len)
        对于 netdev
        netdev_rx_handler_register
            netdev_frame_hook(pskb)
                netdev_frame_hook(skb)
	                vport = ovs_netdev_get_vport(skb->dev);
                    ovs_vport_receive(vport, skb, tun_info)
                        ovs_flow_key_extract(NULL, skb, &key)
                            key_extract(skb, key)
                        ovs_dp_process_packet(skb, &key)
                            flow = ovs_flow_tbl_lookup_stats(&dp->table, key, skb_get_hash(skb), &n_mask_hit)
                                true:
                                    ovs_dp_upcall(dp, skb, key, upcall_info)
                                        skb_is_gso(skb):
                                            queue_gso_packets(dp, skb, key, upcall_info)
                                        !skb_is_gso(skb) :
                                            queue_userspace_packet(dp, skb, key, upcall_info)
                                    n_lost++
                                false:
                                    ovs_execute_actions(dp, skb, acts, key)
                                    do_execute_actions(dp, skb, key, flow->sf_acts->actions, flow->sf_acts->actions_len)
        对于 gre, lisp, stt, vxlan, geneve
            ovs_vport_receive(vport, skb, tun_info)
                ovs_flow_key_extract(tun_info, skb, &key)
                    key_extract(skb, key)
                ovs_dp_process_packet(skb, &key)
                    flow = ovs_flow_tbl_lookup_stats(&dp->table, key, skb_get_hash(skb), &n_mask_hit)
                        if !flow:
		                    struct dp_upcall_info upcall;
		                    memset(&upcall, 0, sizeof(upcall));
		                    upcall.cmd = OVS_PACKET_CMD_MISS;
		                    upcall.portid = ovs_vport_find_upcall_portid(OVS_CB(skb)->input_vport, skb);
                            ovs_dp_upcall(dp, skb, key, upcall_info)
                                if skb_is_gso(skb):
                                    queue_gso_packets(dp, skb, key, upcall_info)
                                if !skb_is_gso(skb) :
                                    queue_userspace_packet(dp, skb, key, upcall_info)
                            n_lost++
                        if flow:
                            ovs_execute_actions(dp, skb, flow->sf_acts, key)
                                do_execute_actions(dp, skb, key, flow->sf_acts->actions, flow->sf_acts->actions_len)


    static const struct net_device_ops internal_dev_netdev_ops = {
        //开启发送数据给驱动
    	.ndo_open = internal_dev_open,
        //停止发送数据给驱动
    	.ndo_stop = internal_dev_stop,
        //开始接收
    	.ndo_start_xmit = internal_dev_xmit,
        //设置 MAC
    	.ndo_set_mac_address = eth_mac_addr,
        //设置 MTU
    	.ndo_change_mtu = internal_dev_change_mtu,
    #if LINUX_VERSION_CODE >= KERNEL_VERSION(2,6,36)
        //获取状态如接收,传输的包数, 错误和丢弃的包数
    	.ndo_get_stats64 = internal_dev_get_stats,
    #else
    	.ndo_get_stats = internal_dev_sys_stats,
    #endif
    };




## vport 是如何发包的

	int sent = vport->ops->send(vport, skb);

    对于 internal
	    internal_dev_recv(vport, skb)
	        netif_rx(skb);
    对于 netdev
        netdev_send(vport, skb)
	        skb->dev = netdev_vport_priv(vport)->dev;
	        dev_queue_xmit(skb);
    对于 gre
        gre_send
            _send
	            iptunnel_xmit(skb->sk, rt, skb, saddr,
			         tun_key->ipv4_dst, IPPROTO_GRE,
			         tun_key->ipv4_tos,
			         tun_key->ipv4_ttl, df, false);

    对于 gre64
        gre64_send
            _send
	            iptunnel_xmit(skb->sk, rt, skb, saddr,
			         tun_key->ipv4_dst, IPPROTO_GRE,
			         tun_key->ipv4_tos,
			         tun_key->ipv4_ttl, df, false);

    对于 lisp
        lisp_sen
	        udp_tunnel_xmit_skb(rt, skb, saddr, tun_key->ipv4_dst,
				       tun_key->ipv4_tos, tun_key->ipv4_ttl,
				       df, src_port, dst_port, false, true);

    对于 stt
        stt_tnl_send
	        stt_xmit_skb(skb, rt, saddr, tun_key->ipv4_dst,
	    		    tun_key->ipv4_tos, tun_key->ipv4_ttl,
	    		    df, sport, dport, tun_key->tun_id);

    对于 vxlan
        vxlan_tnl_send
	        vxlan_xmit_skb(vxlan_port->vs, rt, skb,
			     saddr, tun_key->ipv4_dst,
			     tun_key->ipv4_tos,
			     tun_key->ipv4_ttl, df,
			     src_port, dst_port,
			     &md, false, vxflags);

    对于 geneve
        geneve_tnl_send
	        geneve_xmit_skb(geneve_port->gs, rt, skb, saddr,
		        tun_key->ipv4_dst, tun_key->ipv4_tos,
		        tun_key->ipv4_ttl, df, sport, dport,
		        tun_key->tun_flags, vni, opts_len, opts,
		        !!(tun_key->tun_flags & TUNNEL_CSUM), false);
