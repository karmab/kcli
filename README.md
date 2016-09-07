# kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)

This script is meant to interact with a local/remote libvirt daemon and to easily deploy from templates ( optionally using cloudinit).
It started cos i switched from ovirt and needed the same tool [ovirt.py](https://github.com/karmab/ovirt)

## installation
```
pip install kcli
```
You will also need to grab mkisofs for cloudinit isos to get generated


## configuration
You need to declare two configuration files

- ~/kvirt.yml : Use this file to specify default settings, client and for every client, indicate connection details and specific settings
- ~/kvirt_profiles.yml : Use this file to specify profiles (number of cpus, memory, size of disk,network,....) to use when deploying a vm

Note that you can specify settings either in default section, client section or within your profile.

The samples directory contains examples to get you started

## How to use

- get info on your kvm setup
 - `kcli report`
- list vms, along with their private ip ( and plan if applicable)
 - `kcli list`
- list templates
 - `kcli list -t`
- create vm from profile base7
 - `kcli create -p base7 myvm`
- delete vm
 - `kcli delete vm1`
- get detailed info on a specific vm
 - `kcli info vm1` 
- start vm
 - `kcli start vm1` 
- stop vm
 - `kcli start vm1` 
- deploy multiple vms using plan x defined in x.yml file 
 - `kcli plan -f x.yml x`
- delete all vms from plan x
  - `kcli plan -d x` 

## about deploying plans

you can also define a yaml file with a list of vms to deploy ( look at the sample) and deploy it with kcli plan

Note that the description of the vm will automatically be set to the plan name, and this value will be used when deleting the entire plan as a way to locate matching vms.  



## optional: prepare base template

Not needed if you plan to use cloudinit built in feature but here are some indicative steps to tune your template

```
ROOTPW="unix1234"
wget http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
qemu-img create -f qcow2 centos7.qcow2 40G
virt-resize --expand /dev/sda1 CentOS-7-x86_64-GenericCloud.qcow2 centos7.qcow2
virt-customize -a centos7.qcow2 --root-password password:$ROOTPW
virt-customize -a centos7.qcow2 --run-command 'sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config'
virt-customize -a centos7.qcow2 --run-command 'sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config'
```

##cloudinit stuff

if cloudinit is enabled (it is by default), a custom iso is generated on the fly for your vm ( using mkisofs) and uploaded to your kvm instance ( using the API).

```
mkisofs  -o x.iso --volid cidata --joliet --rock user-data meta-data
```
Also note that if you use cloudinit and dont specify ssh keys to inject, the default ~/.ssh/id_rsa.pub will be used, if present.

## demos

[here](https://asciinema.org/a/31k7y6eu95ylhxnfyrqcx3qtj)

## available parameters
those parameters can be set either in your config, profile or plan files

- *numcpus* Defaults to 2
- *memory* Defaults to 512
- *guestid* Defaults to guestrhel764
- *pool* Defaults to default
- *disksize1* Defaults to 10
- *template* Should point to your base cloud image(optional)
- *diskthin1* Defaults to true
- *diskinterface1* Defaults to virtio
- *disksize2* Defaults to 0( not created by default)
- *diskthin2* Defaults to true
- *diskinterface2* Defaults to virtio  
- *net1* Defaults to default
- *net2* (optional)
- *net3* (optional)
- *net4* (optional)
- *iso* ( optional)
- *vnc* Defaults to false (use spice instead)
- *cloudinit* Defaults to true
- *start* Defaults to true
- *keys* (optional)
- *cmds* (optional)


## additional parameters for plan files

TODO


##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
