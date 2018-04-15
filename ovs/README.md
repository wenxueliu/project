openvswitch note



### PACKET_IN 的数据流向


1. ofproto->pins 移动到临时变量 pins
2. 遍历 pins, 对于 ofproto->up.connmgr->all_conns 中满足发送 PACKET_IN 条件的 ofconn:
    1) 如果配置速率限制, 保存在 ofproto->up.connmgr->schedulers[0]->queues 中, 等待发送
    2) 如果没有配置速率限制, 保存在临时变量 txq 中, 之后遍历 txq 将其加入 ofconn->rconn->txq 中, 等待发送

注:

对于原因时 OFPR_NO_MATCH 的 PACKET_IN 保存在 ofproto->up.connmgr->schedulers[0],
其他保存在 ofproto->up.connmgr->schedulers[1]

如果 ofconn 有 monitors 还会将 pin 发送给每个 ofconn 的所有 monitor

ofconn_run 方法中:

1. 如果配置速率限制, 在满足满足发送条件后, 会从 ofproto->up.connmgr->schedulers[i]->queues 的每个 pinqueue 中取一个元素, 加入 ofconn->rconn->txq 中. 每次最多取 50 个.
之所以最多是因为 1. ps->queues 可能总共没有 50 个包; 2. 已经达到速率限制, 不允许继续给 txq 增加包

2. 将 ofconn->rconn->txq 中的数据发送给控制器


##run

bridge_run(void)
    ovsrec_open_vswitch_init(&null_cfg);
    ovsdb_idl_run(idl);
    if_notifier_run();
    if (ovsdb_idl_is_lock_contended(idl))
        HMAP_FOR_EACH_SAFE (br, next_br, node, &all_bridges)
            bridge_destroy(br);
        system_stats_enable(false);
        return;
    else if (!ovsdb_idl_has_lock(idl) || !ovsdb_idl_has_ever_connected(idl))
        return;
    cfg = ovsrec_open_vswitch_first(idl);
    bridge_init_ofproto(cfg);
    if (cfg && ofproto_get_flow_restore_wait()) {
        ofproto_set_flow_restore_wait(smap_get_bool(&cfg->other_config, "flow-restore-wait", false));
    bridge_run__();
        sset_init(&types);
        ofproto_enumerate_types(&types);
        SSET_FOR_EACH (type, &types)
            ofproto_type_run(type);
        HMAP_FOR_EACH (br, node, &all_bridges)
            ofproto_run(br->ofproto);
                br->ofproto->ofproto_class->run(p);
                run_rule_executes(p);
                if (br->ofproto->eviction_group_timer < time_msec())
                    br->ofproto->eviction_group_timer = time_msec() + 1000;
                    for (i = 0; i < br->ofproto->n_tables; i++)
                        CLS_FOR_EACH (rule, cr, &table->cls)
                            if (rule->idle_timeout || rule->hard_timeout)
                                if (!rule->eviction_group)
                                    eviction_group_add_rule(rule);
                                else
                                    //rule->evg_node->priority = rule_eviction_priority(p, rule)
                                    heap_raw_change(&rule->evg_node, rule_eviction_priority(p, rule));
                        HEAP_FOR_EACH (evg, size_node, &table->eviction_groups_by_size)
                            heap_rebuild(&evg->rules);
                if (br->ofproto->ofproto_class->port_poll)
                    while ((error = br->ofproto->ofproto_class->port_poll(p, &devname)) != EAGAIN)
                        process_port_change(p, error, devname)
                new_seq = seq_read(connectivity_seq_get())
                if (new_seq != br->ofproto->change_seq)
                    struct sset devnames;
                    HMAP_FOR_EACH (ofport, hmap_node, &br->ofproto->ports)
                        port_change_seq = netdev_get_change_seq(ofport->netdev);
                        if (ofport->change_seq != port_change_seq)
                            ofport->change_seq = port_change_seq;
                            sset_add(&devnames, netdev_get_name(ofport->netdev));
                    SSET_FOR_EACH (devname, &devnames)
                        update_port(p, devname);
                    br->ofproto->change_seq = new_seq;
                TODO 以上

                connmgr_run(br->ofproto->connmgr, handle_openflow);
                    if (br->ofproto->connmgr->in_band)
                        in_band_run(br->ofproto->connmgr->in_band)
                    LIST_FOR_EACH_SAFE (ofconn, next_ofconn, node, &br->ofproto->connmgr->all_conns)
                        ofconn_run(ofconn, handle_openflow)
                            for (i = 0; i < N_SCHEDULERS; i++)
                                pinsched_run(ofconn->schedulers[i], &txq);
                                do_send_packet_ins(ofconn, &txq);
                            rconn_run(ofconn->rconn);
                            for (i = 0; i < 50 && ofconn_may_recv(ofconn); i++) {
                                if (br->ofproto->connmgr->fail_open)
                                    fail_open_maybe_recover(br->ofproto->connmgr->fail_open);
                                handle_openflow(ofconn, of_msg);
                    ofmonitor_run(br->ofproto->connmgr);
                    if (br->ofproto->connmgr->fail_open)
                        fail_open_run(br->ofproto->connmgr->fail_open);
                    HMAP_FOR_EACH (ofservice, node, &br->ofproto->connmgr->services) {
                        retval = pvconn_accept(ofservice->pvconn, &vconn);
                        if (!retval)
                            rconn = rconn_create(ofservice->probe_interval, 0, ofservice->dscp, vconn_get_allowed_versions(vconn));
                            rconn_connect_unreliably(rconn, vconn, name);
                            ofconn = ofconn_create(br->ofproto->connmgr, rconn, OFCONN_SERVICE, ofservice->enable_async_msgs);
                    for (i = 0; i < br->ofproto->connmgr->n_snoops; i++)
                        retval = pvconn_accept(br->ofproto->connmgr->snoops[i], &vconn);
                        if (!retval)
                            add_snooper(br->ofproto->connmgr, vconn);

    if (cfg && cfg->ssl)
        stream_ssl_set_key_and_cert(ssl->private_key, ssl->certificate)
        stream_ssl_set_ca_cert_file(ssl->ca_cert, ssl->bootstrap_ca_cert)
    vlan_splinters_changed = false;
    if (vlan_splinters_enabled_anywhere)
        HMAP_FOR_EACH (br, node, &all_bridges)
            if (ofproto_has_vlan_usage_changed(br->ofproto))
                break;
    if (ovsdb_idl_get_seqno(idl) != idl_seqno || vlan_splinters_changed || ifaces_changed)
        idl_seqno = ovsdb_idl_get_seqno(idl);
        txn = ovsdb_idl_txn_create(idl);
        bridge_reconfigure(cfg ? cfg : &null_cfg);
        if (cfg)
            ovsrec_open_vswitch_set_cur_cfg(cfg, cfg->next_cfg);
            discover_types(cfg);
        if (initial_config_done)
            status_txn_try_again = true;
            ovsdb_idl_txn_commit(txn);
            ovsdb_idl_txn_destroy(txn);
        else
            initial_config_done = true;
            daemonize_txn = txn;

    if (daemonize_txn)
        enum ovsdb_idl_txn_status status = ovsdb_idl_txn_commit(daemonize_txn);
        if (status != TXN_INCOMPLETE)
            ovsdb_idl_txn_destroy(daemonize_txn);
            daemonize_txn = NULL;
            daemonize_complete();
    run_stats_update();
    run_status_update();
    run_system_stats();

##wait

bridge_wait(void)
    ovsdb_idl_wait(idl);
    if (daemonize_txn)
        ovsdb_idl_txn_wait(daemonize_txn);
    if_notifier_wait();
    if (ifaces_changed)
        poll_immediate_wake();
    sset_init(&types);
    ofproto_enumerate_types(&types);
    SSET_FOR_EACH (type, &types)
        ofproto_type_wait(type)
    if (!hmap_is_empty(&all_bridges))
        HMAP_FOR_EACH (br, node, &all_bridges)
            ofproto_wait(struct ofproto *p)
                p->ofproto_class->wait(p);
                if (p->ofproto_class->port_poll_wait)
                    p->ofproto_class->port_poll_wait(p);
                seq_wait(connectivity_seq_get(), p->change_seq);
                connmgr_wait(p->connmgr);
                    LIST_FOR_EACH (ofconn, node, &mgr->all_conns)
                        ofconn_wait(ofconn);
                            for (i = 0; i < N_SCHEDULERS; i++)
                                pinsched_wait(ofconn->schedulers[i]);
                            rconn_run_wait(ofconn->rconn);
                            if (ofconn_may_recv(ofconn))
                                rconn_recv_wait(ofconn->rconn);
                            if (ofconn->next_op_report != LLONG_MAX)
                                poll_timer_wait_until(ofconn->next_op_report);
                    ofmonitor_wait(mgr)
                    if (mgr->in_band)
                        in_band_wait(mgr->in_band);
                    if (mgr->fail_open)
                        fail_open_wait(mgr->fail_open);
                    HMAP_FOR_EACH (ofservice, node, &mgr->services)
                        pvconn_wait(ofservice->pvconn);
                    for (i = 0; i < mgr->n_snoops; i++)
                        pvconn_wait(mgr->snoops[i]);
            stats_update_wait();
            status_update_wait();
    system_stats_wait();
