#!/bin/sh

NIC={{ sno_nic or 'enp1s0' }}
IP={{ '2620:52:0:1309::10' if ipv6|default(False) else '192.168.7.10' }}
NETMASK={{ 128 if ipv6|default(False) else 32 }}

nmcli connection modify "Wired connection 1" +ipv4.addresses $IP/$NETMASK ipv4.method auto
nmcli device reapply $NIC
