#!/bin/bash

#TYPE=$1
#NAME=$2
STATE=$3

case $STATE in
"MASTER")
  ip a l enp1s0f0 | grep -q {{ api_ip }}
  if [ "$?" == "0" ] ; then
    TOKEN="{{ config_auth_token }}"
    DEVICEID=$(curl -s https://metadata.packet.net/2009-04-04/meta-data/instance-id)
    #retrieve current assignment for api_vip
    ID=$(curl -sH "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" https://api.packet.net/devices/$DEVICEID/ips | sed 's@.*{{ api_ip }}","href":"/ips/\(.*\)".*@\1@' | cut -d, -f1 | sed 's/"}//')
    echo $ID | grep -q ip_address
    if [ "$?" != "0" ] ; then
      echo "Deleting assignment $ID"
      curl -H "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" -X DELETE https://api.packet.net/ips/$ID
    else
      echo "No assignments found"
    fi
    echo "Creating new assignment"
    curl -sH "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" -X POST -d "{\"address\": \"{{ api_ip }}/32\",\"manageable\": \"true\"}" https://api.packet.net/devices/$DEVICEID/ips
  fi
  exit 0
  ;;
"BACKUP")
  exit 0
  ;;
"FAULT")
  exit 0
  ;;
*)
  echo "unknown state"
  exit 1
  ;;
esac
