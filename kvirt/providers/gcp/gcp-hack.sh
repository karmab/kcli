#!/bin/bash

KUBESERVICE=kubelet

while true ; do
  ip route show dev ens4 table local proto 66 | while read route ; do
    ip route del $route
  done
  systemctl is-active --quiet $KUBESERVICE && exit 0
  sleep 10
done
