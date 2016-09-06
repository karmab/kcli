###kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Code Climate](https://codeclimate.com/github/karmab/kcli/badges/gpa.svg)](https://codeclimate.com/github/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)

This script is meant to interact with a local/remote libvirt daemon and to easily deploy from templates ( using cloudinit)

# prepare base template
ROOTPW="unix1234"
wget http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
qemu-img create -f qcow2 centos7.qcow2 40G
virt-resize --expand /dev/sda1 CentOS-7-x86_64-GenericCloud.qcow2 centos7.qcow2
virt-customize -a centos7.qcow2 --root-password password:$ROOTPW
virt-customize -a centos7.qcow2 --run-command 'sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config'
virt-customize -a centos7.qcow2 --run-command 'sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config'

#cloudinit stuff
# you can also use genisoimage
mkisofs  -o x.iso --volid cidata --joliet --rock user-data meta-data

## demos
https://asciinema.org/a/31k7y6eu95ylhxnfyrqcx3qtj


##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
