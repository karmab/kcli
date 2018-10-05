#!/usr/bin/env bash
mkdir /isos
mkdir /vms
mkdir /hosted
echo '/vms *(rw)'  >>  /etc/exports
echo '/isos *(rw)'  >>  /etc/exports
echo '/hosted *(rw)'  >>  /etc/exports
exportfs -r
chown 36:36 /vms
chown 36:36 /isos
chown 36:36 /hosted
systemctl start nfs ; systemctl enable nfs-server
