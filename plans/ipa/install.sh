#!/usr/bin/env bash
export PASSWORD="[[ password ]]"
export DOMAIN="[[ domain ]]"
export REALM="[[ domain | upper ]]"
echo `hostname -I` `hostname -s`.$DOMAIN `hostname -s` >> /etc/hosts
echo `hostname -s`.$DOMAIN > /etc/hostname
yum -y install freeipa-server bind bind-dyndb-ldap ipa-server-dns epel-release
yum -y install haveged
systemctl start haveged
ipa-server-install  --unattended --setup-dns --forwarder 8.8.8.8 --auto-reverse --ip-address `hostname -I` --hostname=`hostname`.$DOMAIN -a $PASSWORD -n $DOMAIN -p $PASSWORD  -r $REALM --idstart=8000 --idmax=10000
