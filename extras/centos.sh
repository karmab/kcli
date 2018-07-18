#!/bin/bash

yum -y install epel-release https://centos7.iuscommunity.org/ius-release.rpm 
yum -y install gcc git libvirt-devel genisoimage qemu-kvm nmap-ncat python-pip openssh-clients curl-devel python36u python36u-libs python36u-devel python36u-pip openssl-devel libxml2-devel
pip3.6 install -U --no-cache-dir ipaddress
export PYCURL_SSL_LIBRARY=openssl
pip3.6 install --no-cache-dir git+https://github.com/karmab/kcli.git
curl  https://raw.githubusercontent.com/karmab/kcli/master/extras/klist.py > /usr/bin/klist.py
chmod o+x /usr/bin/klist.py
sed -i 's@.*env python.*@/#!/bin/python3.6@' /usr/bin/klist.py
