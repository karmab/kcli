#!/bin/bash

pgrep -f "hyperkube kube-apiserver"
if [ "$?" == "0" ] ; then
  exit 0
fi
while true ; do
  ip route show dev ens4 table local proto 66 | while read route ; do
    ip route del $route
  done
  sleep 10
done
