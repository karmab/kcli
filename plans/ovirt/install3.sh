#!/usr/bin/env bash
yum -y install rhevm-setup
sed -i "s/0000/`hostname -s`/" /root/answers.txt
service iptables stop
chkconfig iptables off
engine-setup --config-append=/root/answers.txt
