#!/bin/sh

NIC={{ sno_nic or 'enp1s0' }}
IP=192.168.7.10
NETMASK=32

nmcli connection modify "Wired connection 1" +ipv4.addresses $IP/$NETMASK ipv4.method auto
nmcli device reapply $NIC
