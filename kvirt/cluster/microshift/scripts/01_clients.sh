#!/usr/bin/env bash

MAJOR={{ 8 if 'rhel8' in image else 9 }}
{% set tag_str = tag|string %}

{% if version in ['dev-preview', 'nightly'] %}
PREFIX={{ 'ocp-dev-preview' if nightly else 'ocp' }}
TAG={{ tag if tag_str.split('.')|length > 2 else "latest-" + tag_str }}
echo """[microshift-dev-preview]
name=Microshift Dev Preview
baseurl=https://mirror.openshift.com/pub/openshift-v4/x86_64/microshift/ocp-dev-preview/$TAG/el$MAJOR/os/
enabled=1
gpgcheck=0

[microshift-dev-preview-dependencies]
name=Microshift dependencies
baseurl=https://mirror.openshift.com/pub/openshift-v4/x86_64/dependencies/rpms/{{ tag }}-el$MAJOR-beta/
enabled=1
gpgcheck=0
skip_if_unavailable=0""" > /etc/yum.repos.d/microshift.repo
{% endif %}

TAG={{ tag }}
subscription-manager repos --enable rhocp-$TAG-for-rhel-$MAJOR-$(uname -i)-rpms --enable fast-datapath-for-rhel-$MAJOR-$(uname -i)-rpms
dnf -y install openshift-clients lvm2 podman

test -f /root/auth.json && podman login registry.redhat.io --authfile /root/auth.json

DEVICE=/dev/$(lsblk -o name | tail -1)
pvcreate $DEVICE
vgcreate rhel $DEVICE
