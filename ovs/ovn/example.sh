
# route to route must by switch
# l3 gateway is a single point
# ecmp not support

CENTRAL_CONTROLLER=10.127.0.2
CENTRAL_PORT=6642
CHASSIS_HOSTS="10.127.0.3 10.127.0.4"
VM_MACS="02:ac:10:ff:00:11 02:ac:10:ff:00:22"
VM_HOSTS="vm1:172.16.255.11/24:02:ac:10:ff:00:11 vm2:172.16.255.22/24:02:ac:10:ff:00:22 vm3:172.16.255.33/24:02:ac:10:ff:00:33"


for host in ${CHASSIS_HOSTS}; do
    ovs-vsctl add-br br-int -- set Bridge br-int fail-mode=secure
    ovs-vsctl list-br
    ovs-vsctl set open . external-ids:ovn-remote=tcp:${CENTRAL_CONTROLLER}:${CENTRAL_PORT}
    ovs-vsctl set open . external-ids:ovn-encap-type=geneve
    ovs-vsctl set open . external-ids:ovn-encap-ip=${host}
    sleep 5
    netstat -antp | grep ${CENTRAL_PORT}
done


for vm_host in ${VM_HOSTS}; do
    local vm_name=`echo ${vm_host} | awk '{ print $1 }'`
    local vm_ip=`echo ${vm_host} | awk '{ print $2 }'`
    local vm_mac=`echo ${vm_host} | awk '{ print $3 }'`
    ip netns add ${vm_name}
    ovs-vsctl add-port br-int ${vm_name} -- set interface ${vm_name} type=internal
    ip link set ${vm_name} netns ${vm_name}
    ip netns exec ${vm_name} ip link set ${vm_name} address ${vm_mac}
    ip netns exec ${vm_name} ip addr add ${vm_ip} dev ${vm_name}
    ip netns exec ${vm_name} ip link set ${vm_name} up
    ovs-vsctl set Interface ${vm_name} external_ids:iface-id=ls1-vm1
    ip netns exec ${vm_name} ip addr show
done


# ---------------------------------------------------


# create the logical switch
ovn-nbctl ls-add ls1

# create logical port
int index=0
for vm_mac in ${VM_HOSTS}; do
    local vm_mac=`echo ${vm_host} | awk '{ print $3 }'`
    ovn-nbctl lsp-add ls1 ls1-vm${index}
    ovn-nbctl lsp-set-addresses ls1-vm${index} ${vm_mac}
    ovn-nbctl lsp-set-port-security ls1-vm${index} ${vm_mac}
    index=$((index+1))
done



# http://blog.spinhirne.com/2016/09/a-primer-on-ovn.html
