#!/usr/bin/env bash

set -euo pipefail

export PATH=/root/bin:$PATH
dnf -y install httpd
dnf -y install libguestfs-tools
dnf -y update libgcrypt
sed -i "s/Listen 80/Listen 8080/" /etc/httpd/conf/httpd.conf
systemctl enable --now httpd
cd /var/www/html
RHCOS_OPENSTACK_URI_FULL={{ openstack_uri }}
RHCOS_OPENSTACK_URI=$(basename $RHCOS_OPENSTACK_URI_FULL)
curl -L $RHCOS_OPENSTACK_URI_FULL > $RHCOS_OPENSTACK_URI

EXTRACTED_FILE=openstack.qcow2
gunzip -c $RHCOS_OPENSTACK_URI > $EXTRACTED_FILE
export LIBGUESTFS_BACKEND=direct
BOOT_DISK=$(virt-filesystems -a $EXTRACTED_FILE -l | grep boot | cut -f1 -d" ")
{% if ':' in api_ip and not dualstack %}
virt-edit -a $EXTRACTED_FILE -m $BOOT_DISK /boot/loader/entries/ostree-1-rhcos.conf -e "s/^options/options ip=dhcp6/"
{% else %}
virt-edit -a $EXTRACTED_FILE -m $BOOT_DISK /boot/loader/entries/ostree-1-rhcos.conf -e "s/^options/options ip=dhcp/"
{% endif %}
gzip -c $EXTRACTED_FILE > $RHCOS_OPENSTACK_URI
RHCOS_OPENSTACK_SHA_COMPRESSED=$(sha256sum $RHCOS_OPENSTACK_URI | cut -d " " -f1)
chown apache.apache  /var/www/html/*

export BAREMETAL_IP=$(ip -o addr show eth0 | head -1 | awk '{print $4}' | cut -d'/' -f1)
echo $BAREMETAL_IP | grep -q ':' && BAREMETAL_IP=[$BAREMETAL_IP]
echo "http://${BAREMETAL_IP}:8080/${RHCOS_OPENSTACK_URI}?sha256=${RHCOS_OPENSTACK_SHA_COMPRESSED}" > /root/clusterOSImage.txt
