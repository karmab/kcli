#!/usr/bin/env bash
yum -y install glusterfs-server glusterfs-ganesha glusterfs glusterfs-geo-replication glusterfs-cli samba
systemctl start glusterd
systemctl enable glusterd
systemctl start smb
systemctl enable smb
systemctl start nmb
systemctl enable nmb
#tuned-adm profile rhgs-random-io
tuned-adm profile throughput-performance
pvcreate /dev/vdb
pvcreate /dev/vdc
