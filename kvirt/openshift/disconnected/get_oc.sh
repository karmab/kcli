#!/usr/bin/env bash

mkdir /root/bin
cd /root/bin/
curl https://mirror.openshift.com/pub/openshift-v4/clients/oc/4.4/linux/oc.tar.gz > oc.tar.gz
tar zxf oc.tar.gz
rm -rf oc.tar.gz
chmod +x oc
