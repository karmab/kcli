#!/usr/bin/env bash

PRIMARY_NIC=$(ls -1 /sys/class/net | head -1)
IP=$(ip -o addr show $PRIMARY_NIC | head -1 | awk '{print $4}' | cut -d'/' -f1)
NEW_NAME=$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io
hostnamectl set-hostname $NEW_NAME
