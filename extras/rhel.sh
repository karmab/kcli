#!/bin/bash

pip="pip"
if [ "$( grep -q "7." /etc/redhat-release)" == "0" ] ; then
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum -y install epel-release libxml2-devel openssl-devel python34-virtualenv.noarch gcc git libvirt-devel genisoimage qemu-kvm nmap-ncat python-pip openssh-clients curl-devel 
virtualenv-3.4 venv
else
yum -y install python36 python36-pip libxml2-devel openssl-devel gcc git libvirt-devel genisoimage qemu-kvm nmap-ncat openssh-clients curl-devel 
pip="pip3"
fi
source venv/bin/activate
$pip install libvirt-python
$pip install --no-cache-dir git+https://github.com/karmab/kcli.git
