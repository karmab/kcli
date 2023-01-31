#!/usr/bin/env bash

dnf -y install cri-o conntrack cri-tools
cp /root/auth.json /etc/crio/openshift-pull-secret
chmod 600 /etc/crio/openshift-pull-secret
systemctl enable --now crio
