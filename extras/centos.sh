#!/bin/bash

yum -y install epel-release libxml2-devel openssl-devel python34-virtualenv.noarch
virtualenv-3 venv
source venv/bin/activate
pip install libvirt-python
export PYCURL_SSL_LIBRARY=openssl
pip install --no-cache-dir pycurl
pip install --no-cache-dir git+https://github.com/karmab/kcli.git
# pip3 install --no-cache-dir -e git+https://github.com/karmab/kcli.git#egg=kcli[all]
curl  https://raw.githubusercontent.com/karmab/kcli/master/extras/klist.py > /usr/bin/klist.py
chmod o+x /usr/bin/klist.py
sed -i 's@.*env python.*@/#!/bin/python3.6@' /usr/bin/klist.py
