
本文基于 2.3.2 版本


## handler 线程

线程名为 "hander{hander->handler_id}", 比如 handler13, hander14
每个 handler 每次最多处理 FLOW_MISS_MAX_BATCH 条消息, 调整该值是否可以提高性能?

数据结构

    /* A thread that reads upcalls from dpif, forwards each upcalls packet,
     * and possibly sets up a kernel flow as a cache. */
    struct handler {
        struct udpif *udpif;               /* Parent udpif. */
        pthread_t thread;                  /* Thread ID. */
        uint32_t handler_id;               /* Handler id. */
    };

    struct flow_miss {
        struct hmap_node hmap_node;
        struct ofproto_dpif *ofproto;

        struct flow flow;
        const struct nlattr *key;
        size_t key_len;
        enum dpif_upcall_type upcall_type;
        struct dpif_flow_stats stats;
        odp_port_t odp_in_port;

        uint64_t slow_path_buf[128 / 8];
        struct odputil_keybuf mask_buf;

        struct xlate_out xout;

        bool put;
    };

    struct dpif_upcall {
        /* All types. */
        enum dpif_upcall_type type;
        struct ofpbuf packet;       /* Packet data. */
        struct nlattr *key;         /* Flow key. */
        size_t key_len;             /* Length of 'key' in bytes. */

        /* DPIF_UC_ACTION only. */
        struct nlattr *userdata;    /* Argument to OVS_ACTION_ATTR_USERSPACE. */
    };

    struct upcall {
        struct flow_miss *flow_miss;    /* This upcall's flow_miss. */

        /* Raw upcall plus data for keeping track of the memory backing it. */
        struct dpif_upcall dpif_upcall; /* As returned by dpif_recv() */
        struct ofpbuf upcall_buf;       /* Owns some data in 'dpif_upcall'. */
        uint64_t upcall_stub[512 / 8];  /* Buffer to reduce need for malloc(). */
    };

udpif_upcall_handler(handler)
        n_upcalls = read_upcalls(handler, upcalls, miss_buf, &misses);
            for (i = 0; i < FLOW_MISS_MAX_BATCH; i++)
                dpif_recv(udpif->dpif, handler->handler_id, &upcall->dpif_upcall, &upcall->upcall_buf);
                    dpif->dpif_class->recv(dpif, handler_id, upcall, buf);
                        dpif_linux_recv(dpif, handler_id, upcall, buf)
                            dpif_linux_recv__(dpif, handler_id, upcall, buf)
                                if (handler->event_offset >= handler->n_events)
                                   handler->n_events = epoll_wait(handler->epoll_fd, handler->epoll_events, dpif->uc_array_size, 0);
                                while (handler->event_offset < handler->n_events)
                                    nl_sock_recv(ch->sock, buf, false);
                                    parse_odp_packet(buf, upcall, &dp_ifindex);
                xlate_receive(udpif->backer, packet, dupcall->key, dupcall->key_len, &flow, &ofproto, &ipfix, &sflow, NULL, &odp_in_port);
                    odp_flow_key_to_flow(dupcall->key, dupcall->key_len, flow)
                type = classify_upcall(upcall);
                if (type == MISS_UPCALL)
                    struct pkt_metadata md = pkt_metadata_from_flow(&flow);
                    flow_extract(packet, &md, &miss->flow);
                    hash = flow_hash(&miss->flow, 0);
                    existing_miss = flow_miss_find(misses, ofproto, &miss->flow, hash);
                    if (!existing_miss)
                        hmap_insert(misses, &miss->hmap_node, hash);
                    else
                        miss = existing_miss;
                    upcall->flow_miss = miss;
                switch (type)
                case SFLOW_UPCALL:
                    dpif_sflow_received(sflow, packet, &flow, odp_in_port, &cookie);
                    break;
                case IPFIX_UPCALL:
                    dpif_ipfix_bridge_sample(ipfix, packet, &flow);
                    break;
                case FLOW_SAMPLE_UPCALL:
                        dpif_ipfix_flow_sample(ipfix, packet, &flow, cookie.flow_sample.collector_set_id, cookie.flow_sample.probability, cookie.flow_sample.obs_domain_id, cookie.flow_sample.obs_point_id);
                case BAD_UPCALL:
                    break;
                case MISS_UPCALL:
                    OVS_NOT_REACHED();

                return n_upcalls; //总共 upcall 的数量
        handle_upcalls(handler, &misses, upcalls, n_upcalls);
            HMAP_FOR_EACH (miss, hmap_node, misses)
                xlate_in_init(&xin, miss->ofproto, &miss->flow, NULL, miss->stats.tcp_flags, NULL);
                xlate_actions(&xin, &miss->xout);
                    xlate_actions__(xin, miss->xout);
                        ctx.table_id = rule_dpif_lookup(ctx.xbridge->ofproto, flow, !xin->skip_wildcards ? wc : NULL, &rule, ctx.xin->xcache != NULL);
                            verdict = rule_dpif_lookup_from_table(ofproto, flow, wc, true, &table_id, rule, take_ref);
                                *rule = rule_dpif_lookup_in_table(ofproto, *table_id, flow, wc, take_ref);
                                    cls_rule = classifier_lookup(cls, flow, wc);
                                    rule = rule_dpif_cast(rule_from_cls_rule(cls_rule));
                        if (ofpbuf_size(&ctx.action_set))
                            xlate_action_set(&ctx);
                                do_xlate_actions(ofpbuf_data(ctx->action_set), ofpbuf_size(ctx->action_set), ctx);
                                    OFPACT_FOR_EACH (a, ofpbuf_data(ctx->action_set), ofpbuf_size(ctx->action_set))
                                        case OFPACT_CONTROLLER:
                                            controller = ofpact_get_CONTROLLER(a);
                                            execute_controller_action(ctx, controller->max_len, controller->reason, controller->controller_id);
            for (i = 0; i < n_upcalls; i++)
                struct upcall *upcall = &upcalls[i];
                struct flow_miss *miss = upcall->flow_miss;
                if (miss->xout.slow)
                    xlate_in_init(&xin, miss->ofproto, &miss->flow, NULL, 0, packet);
                    xlate_actions_for_side_effects(&xin);
            if (fail_open)
                for (i = 0; i < n_upcalls; i++)
                    ofproto_dpif_send_packet_in(miss->ofproto, pin);
            dpif_operate(udpif->dpif, opsp, n_ops);
                if (dpif->dpif_class->operate)
                    if (chunk)
                        dpif->dpif_class->operate(dpif, ops, chunk);
                    else
                        dpif_execute(dpif, &op->u.execute);
                else
                    for (i = 0; i < n_ops; i++)
                        struct dpif_op *op = ops[i];
                        switch (op->type) {
                        case DPIF_OP_FLOW_PUT:
                            dpif_flow_put__(dpif, &op->u.flow_put);
                                dpif->dpif_class->flow_put(dpif, put);
                            break;
                        case DPIF_OP_FLOW_DEL:
                            dpif_flow_del__(dpif, &op->u.flow_del);
                                dpif->dpif_class->flow_del(dpif, del);
                            break;

                        case DPIF_OP_EXECUTE:
                            dpif_execute(dpif, &op->u.execute);
                                (execute->needs_help || nl_attr_oversized(execute->actions_len) ? dpif_execute_with_help(dpif, execute) : dpif->dpif_class->execute(dpif, execute));

1. 从通过 netlink 从内核接受 TABLE_MISS 的包, 解析 netlink 消息转换为 flow
2. 解析 upcall 类型, 如果是 MISS_UPCALL, 将封装一个 flow_miss 对象加入一个 FLOW_MISS_MAX_BATCH 的数组, 如果是其他类型(SFLOW, IPFIX, FLOW_SAMPLE), 暂时忽略
3. 检查当前流表数是否已经超过限制
4. 查询流表, 并执行对应的 action, 对于 table miss, 发送 PACKET_IN 给控制器
5. 遍历 upcalls, 将 flow 和 action 保持在 ops 数组
6. 遍历 ops 执行对应的 action

注:

1. 如果重复的 table miss netlink 消息进来, 只更新包的状态
2. cfm, bfd, lacp 都对性能有影响, 参考 process_special

static void * udpif_upcall_handler(void *arg)

    监听 handler 所属 dpif 的每个端口的 POLLIN 事件:

    如果收到数据, 解析后处理, 如果收到的数据包不为 0, 立即唤醒当前线程的 poll_loop

    如果没有收到数据, 将 dpif->handlers[handler->handler_id]->epoll_fd 加入当前线程的 poll_loop,
    并监听 POLLIN 事件; 此外, 将 handler->udpif->exit_latch[0] 加入当前线程的 poll_loop,
    监听自己是否退出的消息.

    一次接受 FLOW_MISS_MAX_BATCH 个数据包, 查找, 匹配, 执行


## revalidator 线程

线程名为 "revalidator{revalidator->id}", 比如 revalidator13, revalidator14

revalidators 中第一个 revalidator 是 leader

数据结构

/* A thread that processes datapath flows, updates OpenFlow statistics, and
 * updates or removes them if necessary. */
struct revalidator {
    struct udpif *udpif;               /* Parent udpif. */
    pthread_t thread;                  /* Thread ID. */
    unsigned int id;                   /* ovsthread_id_self(). */
    struct hmap *ukeys;                /* Points into udpif->ukeys for this
                                          revalidator. Used for GC phase. */
};

    udpif->ukeys = xmalloc(sizeof *udpif->ukeys * n_revalidators);
    hmap_init(&udpif->ukeys[i].hmap);
    ovs_mutex_init(&udpif->ukeys[i].mutex);
    revalidator->ukeys = &udpif->ukeys[i].hmap;

static void * udpif_revalidator(void *arg)

    for (;;)
        if (leader)
            dpif->dpif_class->flow_dump_start(dpif, &dump->iter);
        ovs_barrier_block(&udpif->reval_barrier); //等待所有的 revalidator 执行到此
        revalidate(revalidator);
            dpif_flow_dump_state_init(udpif->dpif, &state);
                dpif->dpif_class->flow_dump_state_init(&state)
                    dpif_linux_flow_dump_state_init(&state)
            ret = dpif_flow_dump_next(&udpif->dump, state, &key, &key_len, &mask, &mask_len, &actions, &actions_len, &stats)
                dpif->dpif_class->flow_dump_next(udpif->dump->dpif, udpif->dump->iter, state, key, key_len, mask, mask_len, actions, actions_len, stats);
                    dpif_linux_flow_dump_next(udpif->dump->dpif, udpif->dump->iter, state, key, key_len, mask, mask_len, actions, actions_len, stats);
                        nl_dump_next(&iter->dump, &buf, &state->buffer)
                            nl_sock_recv__(iter->dump->sock, state->buffer, false)
                                iov[0].iov_base = ofpbuf_base(state->buffer);
                                iov[0].iov_len = state->buffer->allocated;
                                iov[1].iov_base = tail;
                                iov[1].iov_len = sizeof tail;

                                memset(&msg, 0, sizeof msg);
                                msg.msg_iov = iov;
                                msg.msg_iovlen = 2;
                                retval = recvmsg(iter->dump->sock->fd, &msg, wait ? 0 : MSG_DONTWAIT);
                            nlmsghdr = nl_msg_next(state->buffer, buf);
                                struct nlmsghdr *nlmsghdr = nl_msg_nlmsghdr(state->buffer);
                                size_t len = nlmsghdr->nlmsg_len;
                                ofpbuf_use_const(state->buffer, nlmsghdr, len);
                                ofpbuf_pull(state->buffer, len);
                        dpif_linux_flow_from_ofpbuf(&state->flow, &buf); //buf 初始化 state->flow
                        actions = state->flow.actions;
                        actions_len = state->flow.actions_len;
                        key = state->flow.key;
                        key_len = state->flow.key_len;
                        mask = state->flow.mask;
                        mask_len = state->flow.mask ? state->flow.mask_len : 0;
                        dpif_linux_flow_get_stats(&state->flow, &state->stats);
                        stats = &state->stats;
            while (ret)
                hash = hash_bytes(key, key_len, udpif->secret);
                ukey = ukey_lookup(udpif, key, key_len, hash);
                    ukey = ukey_lookup__(udpif, key, key_len, hash);
                if (!ukey)
                    ukey = ukey_create(key, key_len, used);
                    udpif_insert_ukey(udpif, ukey, hash)
                if ((used && used < now - max_idle) || n_flows > flow_limit * 2) //流应该被删除
                    mark = false; //mask 为 false 表示流表应该被删除
                else
                    mark = revalidate_ukey(udpif, ukey, mask, mask_len, actions, actions_len, stats);
                ukey->mark = ukey->flow_exists = mark;
                if (!mark) //需要删除的流, 增加到 ops 中
                    dump_op_init(&ops[n_ops++], key, key_len, ukey);
                        ops[n_ops++]->ukey = ukey;
                        ops[n_ops++]->op.type = DPIF_OP_FLOW_DEL;
                        ops[n_ops++]->op.u.flow_del.key = key;
                        ops[n_ops++]->op.u.flow_del.key_len = key_len;
                        ops[n_ops++]->op.u.flow_del.stats = &op->stats;
                may_destroy = dpif_flow_dump_next_may_destroy_keys(&udpif->dump, state);
                if (n_ops == REVALIDATE_MAX_BATCH || (n_ops && may_destroy))
                    push_dump_ops__(udpif, ops, n_ops);
                        struct dpif_op *opsp[REVALIDATE_MAX_BATCH];
                        for (i = 0; i < n_ops; i++) opsp[i] = &ops[i].op;
                        dpif_operate(udpif->dpif, opsp, n_ops);
                            if (dpif->dpif_class->operate)
                                while (n_ops > 0)
                                    size_t chunk;
                                    for (chunk = 0; chunk < n_ops; chunk++)
                                        if (op->type == DPIF_OP_EXECUTE && op->u.execute.needs_help) break;
                                    if (chunk)
                                        dpif->dpif_class->operate(dpif, opsp, chunk)
                                            dpif_linux_operate(dpif, opsp, chunk)
                                                while (n_ops > 0)
                                                    size_t chunk = dpif_linux_operate__(dpif, ops, n_ops);
                                                        for (i = 0; i < n_ops; i++)
                                                            dpif_linux_init_flow_del(dpif, del, &flow);
                                                            dpif_linux_flow_to_ofpbuf(&flow, &aux->request);
                                                    ops += chunk;
                                                    n_ops -= chunk;
                                    else
                                        dpif_execute(dpif, &op->u.execute);
                            else
                                for (i = 0; i < n_ops; i++)
                                    switch (op->type)
                                        case DPIF_OP_FLOW_PUT: dpif_flow_put__(dpif, &op->u.flow_put);
                                        case DPIF_OP_FLOW_DEL: dpif_flow_del__(dpif, &op->u.flow_del);
                                        case DPIF_OP_EXECUTE: dpif_execute(dpif, &op->u.execute);
                        stats = op->op.u.flow_del.stats;
                        if (op->ukey)
                            push = &push_buf;
                            ovs_mutex_lock(&op->ukey->mutex);
                            push->used = MAX(stats->used, op->ukey->stats.used);
                            push->tcp_flags = stats->tcp_flags | op->ukey->stats.tcp_flags;
                            push->n_packets = stats->n_packets - op->ukey->stats.n_packets;
                            push->n_bytes = stats->n_bytes - op->ukey->stats.n_bytes;
                            ovs_mutex_unlock(&op->ukey->mutex);
                        else
                            push = stats;

                        if (push->n_packets || netflow_exists())
                            may_learn = push->n_packets > 0;
                            if (op->ukey)
                                if (op->ukey->xcache)
                                    xlate_push_stats(op->ukey->xcache, may_learn, push);
                                    continue;
                            if (!xlate_receive(udpif->backer, NULL, op->op.u.flow_del.key, op->op.u.flow_del.key_len, &flow, &ofproto, NULL, NULL, &netflow, NULL))
                                struct xlate_in xin;
                                xlate_in_init(&xin, ofproto, &flow, NULL, push->tcp_flags, NULL);
                                xin.resubmit_stats = push->n_packets ? push : NULL;
                                xin.may_learn = may_learn;
                                xin.skip_wildcards = true;
                                xlate_actions_for_side_effects(&xin);
                    n_ops = 0;
            if (n_ops)
                push_dump_ops__(udpif, ops, n_ops); //
            dpif_flow_dump_state_uninit(udpif->dpif, state);
                dpif->dpif_class->flow_dump_state_uninit(state);
                    dpif_linux_flow_dump_state_uninit(state)
        ovs_barrier_block(&udpif->reval_barrier); //等待所有的 revalidator 执行到此
        revalidator_sweep(revalidator);
            revalidator_sweep__(revalidator, false); //删除满足条件的 flow
        ovs_barrier_block(&udpif->reval_barrier); //等待所有的 revalidator 执行到此
        if (leader)
            dpif_flow_dump_done(&udpif->dump);


处于 leader 的 revalidator 会做一些额外的工作: 检查是否需要退出, 是否配置被更改, 及 flow 的状态统计,
遍历所有流锁需要的时间

1. 遍历内核流表, 从内核接受内核应答消息, 将其转换成 flow, 获取 flow 的 key, mask, action, stats
2. 从 udpif->ukeys[hash % udpif->n_revalidators].hmap 查找 key 对应的对应的 ukey, 如果 ukey 不存在, 将 ukey 加入 udpif->ukeys[idx]->hmap
3. 根据流回收条件对需要回收的流进行标记
4. 对于需要删除的流表, 进行批量删除

流表项被回收的条件(满足任意即可):

1. 当前流表项数量大于 flow_limt, 且流表项上次被使用的时间在 100 ms 以前
2. 当前流表的数量大于 2 倍 flow_limit
3. 遍历所有流耗时超过 200 且处理每个包的时间大于 200ms 并且配置被修改过?
4. 用户态的 actions 与内核态的 actions 不一样, 或 用户态的 mask 与内核的 mask 不一样
5. 遍历 revalidator->ukeys:
    如果 ukey->flow_exists == true
        if (ukey->mask == false && revalidator->udpif->need_revalidate && ukey 对应的流不在内核中, 就将其删除或在内核但是revalidate_ukey 返回 false) 加入删除列表, 等待删除
    如果 ukey->flow_exists == false, 将 ukey 从 revalidator->ukeys 中删除

注: dump 参考 dpif-linux.c 文件的 flow_dump_xxxx

static bool should_revalidate(const struct udpif *udpif, uint64_t packets, long long int used)

    遍历流表用时小于 200 ms 或单个包用时小于 200 ms

## 流表限制的工作机制

revalidator 每次运行会 dump 所有 flow, 需要时间 during 秒, 当前 datapath 有流表 N 条

如果 during 超过 2s, 则 flow_limit /= during
如果 during 大于 1.3 s, 则 flow_limit = flow_limit * 0.75
如果 during < 1s && N > 2000 && flow_limit < N / during 则 flow_limit += 1000;

最后 flow_limit = MIN(ofproto_flow_limit, MAX(flow_limit, 1000));

其中 ofproto_flow_limit 为 200000;

因此, 实际的 flow_limit 值为系统每秒可以 dump 的流表数



## 流表的过期删除

过期流表保存在 ofproto->up.expirable

由 rule_expire(struct rule_dpif *rule) 完成, 它会遍历所有 rule, 计算 rule 是
hard timeout 还是 idle timeout,

如果没有过期, 就什么也不做;

如果过期,
1. 创建一个 ofopgroup 对象 group
    2. 首先根据配置决定是否将流表删除消息发送给控制器
    3. 创建一个 ofoperation 对象 op, 将 op 加入 group, 如果是主动删除流表, 将 op 加入 ofproto->deletions
    4. 将 rule 从 ofproto->tables, ofproto->cookies, rule->eviction_group->rules 中删除, 如果 rule->eviction_group->rules 没有元素, 就将 rule->eviction_group
       从 table 的 eviction_groups_by_id 和 eviction_groups_by_size 中删除
    5. 将 rule->expirable, rule->meter_list_node 从所属 list 删除
    6. 将 group->ops 中 op 发送给 ofmonitor
    7. 将 op 从 ofproto->deletions 中删除, op 从 group 中删除
    8. 将 group 从所属的 group->ofproto_node, group->ofconn_node 从所属 list 删除
    9. 将 group 加入 group->ofproto->pending


LIST_FOR_EACH_SAFE (rule, next_rule, expirable, &ofproto->up.expirable)
    rule_expire(rule)
        ofproto_rule_expire(&rule->up, reason);
            ofproto_rule_delete__(ofproto, rule, reason);
                group = ofopgroup_create_unattached(ofproto);
                delete_flow__(rule, group, reason);
                    ofproto_rule_send_removed(rule, reason); 只有流表配置删除时发送给控制器, 就将流表的删除消息发送给控制器
                    ofoperation_create(group, rule, OFOPERATION_DELETE, reason);
                    oftable_remove_rule(rule);
                        oftable_remove_rule__(rule->ofproto, rule);
                            classifier_remove(ofproto->tables[rule->table_id].cls, CONST_CAST(struct cls_rule *, &rule->cr));
                            cookies_remove(ofproto, rule);
                            eviction_group_remove_rule(rule);
                            if (!list_is_empty(&rule->expirable)) list_remove(&rule->expirable);
                            if (!list_is_empty(&rule->meter_list_node))
                                list_remove(&rule->meter_list_node);
                                list_init(&rule->meter_list_node);
                    ofproto->ofproto_class->rule_delete(rule);
                        rule_delete(rule) //ofproto_dpif.c
                            complete_operation(rule);
                                ofproto->backer->need_revalidate = REV_FLOW_TABLE;
                                ofoperation_complete(rule->up.pending, 0);
                                    ofopgroup_complete(group);
                ofopgroup_submit(group);

注:
    1. 在删除过期流表时会加锁
    2. 如果是显示删除流表, 会将该 rule 构造的 ofoperation 加入 ofproto->deletions


### upcall 过程中与 flow 相关的数据结构变化




### 哪些操作会影响性能

coverage 统计信息

    xlate_actions_oversize : action 太长导致 netlink 属性无法直接发送给内核
    xlate_actions_too_many_output : action 太多
    upcall_duplicate_flow : 多个 revalidator dump 发生 flow 重复问题
