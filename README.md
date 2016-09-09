# kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)

This script is meant to interact with a local/remote libvirt daemon and to easily deploy from templates ( optionally using cloudinit).
It started cos i switched from ovirt and needed a tool similar to [ovirt.py](https://github.com/karmab/ovirt)

## installation
```
pip install kcli
```
You will also need to grab mkisofs for cloudinit isos to get generated


## configuration

If you want to only use your local libvirt daemon, no extra configuration is needed.
Otherwise you will have to declare your settings in ~/kcli.yml. For instance,

```
default:
 client: twix
 numcpus: 2
 diskthin1: true
 memory: 512
 disksize1: 10
 protocol: ssh
 cloudinit: true
 net1: private1

twix:
 host: 192.168.0.6
 pool: images
```

replace with your own client in default section and indicate host and protocol in the corresponding client section.
Note that most of the parameters are actually optional, and can be overriden in the profile section ( or in a plan file)

## profile configuration

You can use the file ~/kvirt_profiles.yml to specify profiles (number of cpus, memory, size of disk,network,....) to use when deploying a vm.

The samples directory contains examples to get you started

## Using plans

You can define your own plan files in yaml with a list of vms to create.

You can point at an existing profile within your plans, define all parameters for the vms, or combine both approaches.

Specific script and ip1, ip2, ip3 and ip4 can be used directly in the plan file.

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




##cloudinit stuff

if cloudinit is enabled (it is by default), a custom iso is generated on the fly for your vm ( using mkisofs) and uploaded to your kvm instance ( using the API).

```
mkisofs  -o x.iso --volid cidata --joliet --rock user-data meta-data
```
Also note that if you use cloudinit and dont specify ssh keys to inject, the default ~/.ssh/id_rsa.pub will be used, if present.

## demo

 You can find one [here](https://asciinema.org/a/31k7y6eu95ylhxnfyrqcx3qtj)

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

- *profile* name of one of your profile
- *scripts* path of a custom script to inject with cloudinit. Note that it will override cmds part. You can either specify a full path or relative to where you're running kcli
- *ip1* Primary ip
- *ip2* Secondary ip
- *ip3* Third ip
- *ip4* Fourth ip

## TODO

- ansible dynamic inventory 
- ansible_playbook in deployment to apply to the deployment of a plan
- progress bar when applicable
- extra cloudinit variables if usefull
- update memory,cpu feature
- add disk feature
- create disk3 and disk4 
- unit tests

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

and for static networking and multiple nics
```
virt-customize -a centos7.qcow2 --run-command 'sed -i "s/dhcp/static/" /etc/sysconfig/network-scripts/ifcfg-eth0'
virt-customize -a centos7.qcow2 --run-command 'cp /etc/sysconfig/network-scripts/ifcfg-eth0 /etc/sysconfig/network-scripts/ifcfg-eth1'
virt-customize -a centos7.qcow2 --run-command 'sed -i "s/eth0/eth1/" /etc/sysconfig/network-scripts/ifcfg-eth1'
```


##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
