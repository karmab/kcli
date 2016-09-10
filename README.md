# kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)

This script is meant to interact with a local/remote libvirt daemon and to easily deploy from templates ( optionally using cloudinit).
It started cos i switched from ovirt and needed a tool similar to [ovirt.py](https://github.com/karmab/ovirt)

## installation
```
pip install kcli
```
You will also need to grab *mkisofs* for cloudinit isos to get generated
Console access is based on remote-viewer

To deploy from templates, grab images at [openstack](http://docs.openstack.org/image-guide/obtain-images.html)
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

##cloudinit stuff

if cloudinit is enabled (it is by default), a custom iso is generated on the fly for your vm ( using mkisofs) and uploaded to your kvm instance ( using the API).
the iso handles static networking configuration, hostname setting, inyecting ssh keys and running specific commands

Also note that if you use cloudinit but dont specify ssh keys to inject, the default ~/.ssh/id_rsa.pub will be used, if present.

## Using plans

you can also define plan files in yaml with a list of vms to deploy ( look at the sample) and deploy it with kcli plan

You can point at an existing profile within your plans, define all parameters for the vms, or combine both approaches.

Specific script and ip1, ip2, ip3 and ip4 can be used directly in the plan file.

The samples directory contains examples to get you started

Note that the description of the vm will automatically be set to the plan name, and this value will be used when deleting the entire plan as a way to locate matching vms.  

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
- *profile* name of one of your profile. Only checked in profile or plan file
- *scripts* path of a custom script to inject with cloudinit. Note that it will override cmds part. You can either specify a full path or relative to where you're running kcli. Only checked in profile or plan file


## additional parameters for plan files

- *ip1* Primary ip
- *ip2* Secondary ip
- *ip3* Third ip
- *ip4* Fourth ip

Note those ips can also be provided on command line when creating a single vm

## TODO

- extra cloudinit variables if usefull
- update memory, cpu feature
- add disk feature
- create disk3 and disk4 
- make sure forcing cpu fallback to Westmere doesnt impact features

## using dynamic inventory

you can check klist.py in the extra directory and use it as a dynamic inventory for ansible
The script uses sames conf that kcli ( and as such defaults to local hypervisor if no conf is present)

note you will only get ansible_ip for vm within private networks, not bridged one as they are not reported

vm will be grouped by plan, or put in the kvirt group if they dont belong to any plan.

Interesting thing is that the script will try to guess the type of vm based on its template, if present, and populate ansible_user accordingly

Try it with:

```
python extra/klist.py --list

ansible all -i extra/klist.py -m ping
```


##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
