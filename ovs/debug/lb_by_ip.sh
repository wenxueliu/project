#!/bin/bash

dst_server=(10.2.1.40 10.2.1.41 10.2.1.42 10.2.1.43 10.2.1.44)
declare -A ip_port
declare -A ip_mac
ip_port["10.2.1.40"]=6
ip_port["10.2.1.41"]=5
ip_port["10.2.1.42"]=4
ip_port["10.2.1.43"]=1
ip_port["10.2.1.44"]=10
ip_mac["10.2.1.40"]="00:50:11:e0:13:a7"
ip_mac["10.2.1.41"]="00:18:27:e1:01:8b"
ip_mac["10.2.1.42"]="00:18:27:e1:01:af"
ip_mac["10.2.1.43"]="00:18:27:e1:01:b5"
ip_mac["10.2.1.44"]="00:e0:27:e0:0a:73"

nw_vip=10.2.1.200
nw_vport=9999
nw_vmac="42:35:0A:02:01:C8"
dst_port=80


function add_flows_by_client() {
    for src_ip in {100..149}; do
        local in_port=11
        local nw_src=10.2.1.${src_ip}
        local server_index=$(( $src_ip % ${#dst_server[@]} ))
        local nw_dst=${dst_server[$server_index]}
        local out_port=${ip_port[$nw_dst]}
        local dl_dst=${ip_mac[$nw_dst]}
        ovs-ofctl add-flow a5 "table=0,priority=20,tcp,idle_timeout=0,in_port=${in_port},nw_src=${nw_src},nw_dst=${nw_vip},tp_dst=${nw_vport} action=mod_dl_dst=${dl_dst},mod_nw_dst=${nw_dst},mod_tp_dst=${dst_port},output=${out_port}" -O OpenFlow13
        ovs-ofctl add-flow a5 "table=0,priority=20,tcp,idle_timeout=0,in_port=${out_port},nw_src=${nw_dst},nw_dst=${nw_src},tp_src=${dst_port} action=mod_dl_src=${nw_vmac},mod_nw_src=${nw_vip},mod_tp_src=${nw_vport},output=${in_port}" -O OpenFlow13
    done

    for src_ip in {150..199}; do
        local in_port=12
        local nw_src=10.2.1.${src_ip}
        local server_index=$(( $src_ip % ${#dst_server[@]} ))
        local nw_dst=${dst_server[$server_index]}
        local out_port=${ip_port[$nw_dst]}
        local dl_dst=${ip_mac[$nw_dst]}
        ovs-ofctl add-flow a5 "table=0,priority=20,tcp,idle_timeout=0,in_port=${in_port},nw_src=${nw_src},nw_dst=${nw_vip},tp_dst=${nw_vport} action=mod_dl_dst=${dl_dst},mod_nw_dst=${nw_dst},mod_tp_dst=${dst_port},output=${out_port}" -O OpenFlow13
        ovs-ofctl add-flow a5 "table=0,priority=20,tcp,idle_timeout=0,in_port=${out_port},nw_src=${nw_dst},nw_dst=${nw_src},tp_src=${dst_port} action=mod_dl_src=${nw_vmac},mod_nw_src=${nw_vip},mod_tp_src=${nw_vport},output=${in_port}" -O OpenFlow13
    done
}

add_flows_by_client
