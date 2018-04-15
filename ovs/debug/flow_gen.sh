#!/bin/bash

# 100000 flow
#real	2m42.843s
#user	1m4.388s
#sys	1m43.718s


interval=1024
mask=$((interval - 1))
mask=$(( 0xffff & (0xffff - $mask) ))
mask=$(printf "%x" $mask)
echo $mask
num=$(( 65536 / $interval ))
echo $num

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

function add_flow_for_host() {
    local in_port=$1
    local nw_src=$2

    local port=0;
    for i in `seq 1 $num`; do
        # don't use `local src_port=$(printf "0x%x/0x$mask\n" $port)`, it is so slow
        printf -v src_port "0x%x/0x$mask\n" $port
        local server_index=$(( $i % ${#dst_server[@]} ))
        local nw_dst=${dst_server[$server_index]}
        local out_port=${ip_port[$nw_dst]}
        local dl_dst=${ip_mac[$nw_dst]}
        #ovs-ofctl add-flow a5 "table=0,priority=10,tcp,in_port=${in_port},nw_src=${nw_src},nw_dst=${nw_vip},tp_src=${src_port},tp_dst=${nw_vport} action=mod_dl_dst=${dl_dst},mod_nw_dst=${nw_dst},mod_tp_dst=${dst_port},output=${out_port}" -O OpenFlow13
        echo "table=0,priority=10,tcp,in_port=${in_port},nw_src=${nw_src},nw_dst=${nw_vip},tp_src=${src_port},tp_dst=${nw_vport} action=mod_dl_dst=${dl_dst},mod_nw_dst=${nw_dst},mod_tp_dst=${dst_port},output=${out_port}" -O OpenFlow13
        ##ovs-ofctl add-flow a5 "table=0,priority=10,tcp,in_port=${out_port},nw_src=${nw_dst},nw_dst=${nw_src},tp_src=${dst_port},tp_dst=${src_port} action=mod_nw_src=${nw_vip},mod_tp_src=${nw_vport},output=${in_port}" -O OpenFlow13
        #ovs-ofctl add-flow a5 "table=0,priority=10,tcp,in_port=${out_port},nw_src=${nw_dst},nw_dst=${nw_src},tp_src=${dst_port} action=mod_dl_src=${nw_vmac},mod_nw_src=${nw_vip},mod_tp_src=${nw_vport},output=${in_port}" -O OpenFlow13
        port=$((port + interval));
    done
}

#10.2.1.100-10.2.1.149 port 11
#10.2.1.150-10.2.1.199 port 11
function add_flow_for_hosts() {
    for src_ip in 10.2.1.{100..149}; do
    #for src_ip in 10.2.1.{100..120}; do
        add_flow_for_host 11 ${src_ip}
    done
    for src_ip in 10.2.1.{150..199}; do
    #for src_ip in 10.2.1.{150..170}; do
        add_flow_for_host 12 ${src_ip}
    done
}

#add_flow_for_hosts
add_flow_for_host 11 10.2.1.100
