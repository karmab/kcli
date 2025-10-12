#!/bin/bash

VIP="{{ api_ip }}/32"

if [ "$(curl -sLk https://127.0.0.1:6443/readyz)" == "ok" ] ; then
  if ! ip addr show dev lo | grep -q "$VIP"; then
    ip addr add $VIP dev lo
    echo "$(date): VIP added" >> /var/log/vip-monitor.log
  fi
else
  [ "$(hostname -s)" == "{{ cluster }}-bootstrap" ] &&  sleep 120
  if ip addr show dev lo | grep -q "$VIP"; then
    ip addr del $VIP dev lo
    echo "$(date): VIP removed" >> /var/log/vip-monitor.log
  fi
fi
