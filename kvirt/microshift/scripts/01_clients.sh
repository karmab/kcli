#!/usr/bin/env bash

TAG={{ tag }}
subscription-manager repos --enable rhocp-$TAG-for-rhel-8-$(uname -i)-rpms --enable fast-datapath-for-rhel-8-$(uname -i)-rpms
dnf -y install openshift-clients lvm2 podman
test -f /root/auth.json && podman login registry.redhat.io --authfile /root/auth.json
DEVICE=/dev/$(lsblk -o name | tail -1)
pvcreate $DEVICE
vgcreate rhel $DEVICE
