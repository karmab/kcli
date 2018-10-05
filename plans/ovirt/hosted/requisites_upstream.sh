#!/usr/bin/env bash
yum -y install http://plain.resources.ovirt.org/pub/yum-repo/ovirt-release41.rpm
sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config
systemctl restart sshd
PASSWORD="[[ password ]]"
echo $PASSWORD | passwd --stdin root
