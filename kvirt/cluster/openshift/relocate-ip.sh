#!/bin/sh

NIC=br-ex
IP={{ '2620:52:0:1309::10' if ipv6|default(False) else '192.168.7.10' }}
NETMASK={{ 128 if ipv6|default(False) else 32 }}

grep -q $IP /etc/NetworkManager/system-connections/* && exit 0

connection=$(nmcli -t -f NAME,DEVICE c s -a | grep $NIC | grep -v ovs-port | grep -v ovs-if | cut -d: -f1)
nmcli connection modify "$connection" +ipv4.addresses $IP/$NETMASK ipv4.method auto
ip addr add $IP/$NETMASK dev $NIC
echo -e "[Service]\nEnvironment=\"KUBELET_NODE_IP=$IP\" \"KUBELET_NODE_IPS=$IP\"" > /etc/systemd/system/kubelet.service.d/30-nodenet.conf
echo -e "[Service]\nEnvironment=\"CONTAINER_STREAM_ADDRESS=$IP\"" > /etc/systemd/system/crio.service.d/30-nodenet.conf
