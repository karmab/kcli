#!/bin/bash

EPEL=""
if [ $(grep -q "7." /etc/redhat-release) == "0" ] ; then
EPEL="epel-release"
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
fi
yum -y install $EPEL libxml2-devel openssl-devel python34-virtualenv.noarch gcc git libvirt-devel genisoimage qemu-kvm nmap-ncat python-pip openssh-clients curl-devel 
virtualenv-3.4 venv
source venv/bin/activate
pip install libvirt-python
pip install --no-cache-dir git+https://github.com/karmab/kcli.git
