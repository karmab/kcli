#!/bin/bash

systemctl is-active --quiet k3s && exit 0

while true ; do
  LB_IP=$(getent hosts api.sushyshop.gcp.devcluster.openshift.com api.{{ cluster }}.{{ domain }} | awk '{ print $1 }')
  ip route del table local proto 66 local $LB_IP scope host dev ens4
  systemctl is-active --quiet k3s && ip route add table local proto 66 local $LB_IP scope host dev ens4 && exit 0
  sleep 10
done
