# kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)
[![](https://images.microbadger.com/badges/image/karmab/kcli.svg)](https://microbadger.com/images/karmab/kcli "Get your own image badge on microbadger.com")

This script is meant to interact with a local/remote libvirt daemon and to easily deploy from templates (optionally using cloudinit).
It will also report IPS for any VM connected to a dhcp-enabled libvirt network and generally for every VM deployed from this client.

It started because I switched from ovirt and needed a tool similar to [ovirt.py](https://github.com/karmab/ovirt)

##  Why I use this instead of vagrant for kvm?

- Easy syntax to launch single or multiple VMS
- Cloudinit based customization, not over ssh
- No need of using custom images, the public ones will do
- Spice/VNC consoles and TCP serial ones

## Demo!

[![asciicast](https://asciinema.org/a/3p0cn60p0c0j9wd3hzyrs4m0f.png)](https://asciinema.org/a/3p0cn60p0c0j9wd3hzyrs4m0f?autoplay=1)

## Installation

1. Install requirements. you will also need to grab *genisoimage* (or *mkisofs* on OSX) for cloudinit isos to get generated
Console access is based on remote-viewer
For instance if using a RHEL based distribution:

```
yum -y install gcc libvirt-devel python-devel genisoimage qemu-kvm nmap-ncat python-pip
```

On Fedora, you' will need an additional package 

```
yum -y install redhat-rpm-config
```


If using a Debian based distribution:

```
apt-get -y install python-pip pkg-config libvirt-dev genisoimage qemu-kvm netcat libvirt-bin python-dev libyaml-dev
```

2. Install kcli from pypi

```
pip install kcli
```

To deploy from templates, grab images at [openstack](http://docs.openstack.org/image-guide/obtain-images.html)

## I use docker, I'm cool

Pull the latest image:

`docker pull karmab/kcli`

If running locally, launch it with:

`docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/.ssh:/root/.ssh karmab/kcli`

If using a remote hypervisor, launch it with a local kcli.yml file pointing to this hypervisor and providing your ssh keys too

`docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/.ssh:/root/.ssh karmab/kcli`

In both cases, you can also provide a kcli_profiles.yml (and you could also use a dedicated plan directory)

`docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/kcli_profiles.yml:/root/kcli_profiles.yml  -v ~/.ssh:/root/.ssh karmab/kcli`

`docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/kcli_profiles.yml:/root/kcli_profiles.yml -v ~/.ssh:/root/.ssh karmab/kcli`

The entrypoint is defined as kcli, so you can type commands directly as:

`docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/kcli_profiles.yml:/root/kcli_profiles.yml -v ~/.ssh:/root/.ssh karmab/kcli list`

As a bonus, you can alias kcli and run kcli as if it is installed locally instead a Docker container:

`alias kcli = "docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/kcli_profiles.yml:/root/kcli_profiles.yml -v ~/.ssh:/root/.ssh karmab/kcli"`

## Configuration

If you only want to use your local libvirt daemon, no configuration is needed.
If you want to generate a basic settings file, you can use the following command:

```
kcli bootstrap -f
```

You can also go through wizard

```
kcli bootstrap
```

And for advanced bootstrapping, you can specify a target name, host, a pool with a path, and have centos cloud image downloaded

```
kcli bootstrap -a -n twix -H 192.168.0.6 --pool vms --poolpath /home/vms -t
```

Or even use an existing disk for LVM based images (note that the disk will be made into an LVM physical volume, so it should be empty):

```
kcli bootstrap -a -n twix -H 192.168.0.6 --pool vms --poolpath /dev/vdb --pooltype lvm
```

You can add an additional storage pool with:

```
kcli pool -f -t logical -p /dev/sda ssd
```

And define additional networks with:

```
kcli network -c 10.0.1.0/24 private11 --dhcp
```

And download a fedora template:

```
kcli host --download -t fedora
```


Otherwise you will have to declare your settings in ~/kcli.yml. For instance,

```
default:
 client: twix
 numcpus: 2
 diskthin: true
 memory: 512
 disks:
  - size: 10
 protocol: ssh
 cloudinit: true
 reserveip: false
 nets:
  - private1

twix:
 host: 192.168.0.6
 pool: images

bumblefoot:
 host: 192.168.0.4
 pool: images
```

Replace with your own client in default section and indicate host and protocol in the corresponding client section.
Note that most of the parameters are actually optional, and can be overridden in the profile section (or in a plan file)

## Profile configuration

You can use the file ~/kcli_profiles.yml to specify profiles (number of CPUS, memory, size of disk, network,....) to use when deploying a VM.
To use a different profiles file, you can use the key profiles in the default section of ~/kcli.yml and put desired path

The [samples directory](https://github.com/karmab/kcli/tree/master/samples) contains examples to get you started

## How to use

- Get info on your kvm setup
 - `kcli host --report`
- List VMS, along with their private IP (and plan if applicable)
 - `kcli list` or (`kcli vm -l`)
- List templates (Note that it will find them out based on their qcow2 extension...)
 - `kcli list -t`
- Create VM from profile base7
 - `kcli vm -p base7 myvm`
- Delete VM
 - `kcli delete vm1`
- Get detailed info on a specific VM
 - `kcli vm -i vm1`
- Start VM
 - `kcli start vm1` (or `kcli vm --start vm1`) 
- Stop VM
 - `kcli stop vm1` (or `kcli vm --stop vm1`)
- Get remote-viewer console
 - `kcli console vm1`
- Get serial console (over TCP!!!). Note that it will only work with VMS created with kcli and will require netcat client to be installed on host
 - `kcli console -s vm1`
- Deploy multiple VMS using plan x defined in x.yml file
 - `kcli plan -f x.yml x`
- Delete all VM from plan x
  - `kcli plan -d x`
- Add 5GB disk to vm1, using pool named vms
  - `kcli disk -s 5 -p vms vm1`
- Delete disk named vm1_2.img from vm1
  - `kcli disk -d -n vm1_2.img  vm1`
- Update to 2GB memory  vm1
  - `kcli update -m 2048 vm1`
- Update internal IP (useful for ansible inventory over existing bridged VMS)
  - `kcli update -1 192.168.0.40 vm1`
- Clone vm1 to new vm2
  - `kcli clone -b vm1 vm2`
- Connect by ssh to the VM (retrieving IP and adjusting user based on the template)
  - `kcli ssh vm1`
- Switch active client to bumblefoot
  - `kcli host --switch bumblefoot`
- Add a new network
  - `kcli network -c 192.168.7.0/24 --dhcp mynet`
- Add a new nic from network private1
- - `kcli nic -n private1 myvm`
- Delete nic eth2 from VM
- - `kcli nic -di eth2 myvm`

## Templates

For templates to work with cloud-init, they require the "NoCloud" datasource to be enabled! Enable the datasource in the cloud-init configuration. For debian-based systems, you can find this configuration in `/etc/cloud/cloud.cfg.d/90\*`.

Templates should be in the same storage pool as the VM, in order to benefit from the Copy-on-Write mechanism.

For a regular file-backed storage pool, download the image you want, and put it in the backing store directory.

For an LVM-backed storage pool, convert the image to raw format, and upload it to the pool. Assuming a volume group with name `vms`, do:

```
TEMPLATE=xenial-server-cloudimg-amd64-disk1.img
qemu-img convert -f qcow2 -O raw $TEMPLATE ${TEMPLATE}.raw
TSIZE=`ls -l ${TEMPLATE}.raw | tr -s ' ' | cut -d' ' -f5`
virsh vol-create-as vms $TEMPLATE $TSIZE
virsh vol-upload --pool vms $TEMPLATE ${TEMPLATE}.raw
```

Note that disks based on a LVM template always have the same size as the template disk! The code above creates a template-disk that is only just big enough to match the size of the (raw) template. You may want to grow this disk to a reasonable size before creating VM's that use it! Alternatively, you can set the TSIZE parameter above to a static value, rather than using the size of the image.

Note also that kcli uses the default ssh_user according to the different [cloud images](http://docs.openstack.org/image-guide/obtain-images.html).
To infer It, kcli checks the template name. So for example, your centos image MUST contain the term "centos" in the file name,
otherwise the default user "root" will be used. 
You can nose around the code here [`kvirt/_init_.py`](https://github.com/karmab/kcli/blob/master/kvirt/__init__.py#L1240)

## Cloudinit stuff

If cloudinit is enabled (it is by default), a custom iso is generated on the fly for your VM (using mkisofs) and uploaded to your kvm instance (using the libvirt API, not using ssh commands, pretty cool, huh?).
The iso handles static networking configuration, hostname setting, injecting ssh keys and running specific commands

Also note that if you use cloudinit but dont specify ssh keys to inject, the default ~/.ssh/id_rsa.pub will be used, if present.

## Using plans

You can also define plan files in yaml with a list of VMS, disks, and networks and VMS to deploy (look at the sample) and deploy it with kcli plan.

For instance, to define a network named mynet:

```
mynet:
 type: network
 cidr: 192.168.95.0/24
```

You can also use the boolean keyword dhcp (mostly to disable it) and isolated . Note that when not specified, dhcp and nat will be enabled

To define a shared disk named shared1.img between two VMS (that typically would be defined within the same plan):

```
share1.img:
 type: disk
 size: 5
 pool: vms
 vms:
  - centos1
  - centos2
```

Regarding VMS, You can point at an existing profile within your plans, define all parameters for the VMS, or combine both approaches.

Specific scripts and IPS arrays can be used directly in the plan file (or in profiles one).

The samples directory contains examples to get you started.

Note that the description of the VM will automatically be set to the plan name, and this value will be used when deleting the entire plan as a way to locate matching VMS.

When launching a plan, the plan name is optional. If not is provided, the kvirt keyword will be used.

If a file with the plan isnt specified with -f , the file kcli_plan.yml in the current directory will be used, if available.

Also note that when deleting a plan, the network of the VMS will also be deleted if no other VM are using them. You can prevent this by using the keep (-k) flag

For an advanced use of plans along with scripts, you can check the [plans](plans/README.md) page to deploy all upstream projects associated with Red Hat Cloud Infrastructure products (or downstream versions too).

## Available parameters

Those parameters can be set either in your config, profile or plan files

- *numcpus* Defaults to 2
- *memory* Defaults to 512
- *guestid* Defaults to guestrhel764
- *pool* Defaults to default
- *template* Should point to your base cloud image(optional). You can either specify short name or complete path. Note that if you omit the full path and your image lives in several pools, the one from last (alphabetical) pool will be used.
- *disks* Array of disks to define. For each of them, you can specify pool, size, thin (as boolean) and interface (either ide or virtio).If you omit parameters, default values will be used from config or profile file (You can actually let the entire entry blank or just indicate a size number directly). For instance:

```
disks:
 - size: 20
   pool: vms
 - size: 10
   thin: False
   format: ide
```

Within a disk section, you can use the word size, thin and format as keys

- *diskthin* Value used when not specified in the disk entry. Defaults to true
- *diskinterface* Value used when not specified in the disk entry. Defaults to virtio. Could also be ide, if VM lacks virtio drivers
- *nets* Array of networks. Defaults to ['default']. You can mix simple strings pointing to the name of your network and more complex information provided as hash. For instance:

```
nets:
 - private1
 - name: private2
   nic: eth1
   ip: 192.168.0.220
   mask: 255.255.255.0
   gateway: 192.168.0.1
```

Within a net section, you can use name, nic, IP, mac, mask and gateway as keys.

Note that up to 8 IPS can also be provided on command line when creating a single VM (with the flag -1, -2, -3,-4,...)
Also note that if you set reserveip  to True , a reservation will be made if the corresponding network has dhcp and when the provided IP belongs to the network range.
You can also set reservedns to True to create a DNS entry for the host in the corresponding network ( Only done for the first nic)

- *iso* (optional)
- *netmasks* (optional)
- *gateway* (optional)
- *dns* (optional) Dns servers
- *domain* (optional) Dns search domain
- *vnc* Defaults to false (use spice instead)
- *cloudinit* Defaults to true
- *reserveip* Defaults to false
- *start* Defaults to true
- *keys* (optional). Array of public keys to inject
- *cmds* (optional). Array of commands to run
- *profile* name of one of your profile. Only checked in plan file
- *scripts* array of paths of custom script to inject with cloudinit. Note that it will override cmds part. You can either specify full paths or relative to where you're running kcli. Only checked in profile or plan file

## Docker support

Docker support is mainly enabled as a commodity to launch some containers along vms in plan files. Of course, you will need docker installed on the hypervisor. So the following can be used in a plan file to launch a container:

```
centos:
 type: container
  image: centos
  cmd: /bin/bash
  ports:
   - 5500
  volumes:
   - /root/coco
```

The following keywords can be used:

- *image* name of the image to pull ( You can alternatively use the keyword *template*
- *cmd* command to run within the container
- *ports* array of ports to map between host and container
- *volumes* array of volumes to map between host and container. You can alternatively use the keyword *disks*. You can also use more complex information provided as a hash

Within a volumes section, you can use path, origin, destination and mode as keys. mode can either be rw o ro and when origin or destination are missing, path is used and the same path is used for origin and destination of the volume. You can also use this typical docker syntax:

```
volumes:
 - /home/cocorico:/root/cocorico
```

Additionally, basic commands ( start, stop, console, plan, list) accept a *--container* flag.

Also note that while python sdk is used when connecting locally, commands are rather proxied other ssh when using a remote host ( reasons beeing to prevent mismatch of version between local and remote docker and because enabling remote access for docker is considered insecure and needs some uncommon additional steps )

Finally, note that if using the docker version of kcli against your local host , you'll need to pass a docker socket:

`docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/.ssh:/root/.ssh -v /var/run/docker.sock:/var/run/docker.sock karmab/kcli`

## Ansible support

You can check klist.py in the extra directory and use it as a dynamic inventory for ansible.

The script uses sames conf as kcli (and as such defaults to local hypervisor if no configuration file is found).

VM will be grouped by plan, or put in the kvirt group if they dont belong to any plan.

Interesting thing is that the script will try to guess the type of VM based on its template, if present, and populate ansible_user accordingly

Try it with:

```
python extra/klist.py --list
ansible all -i extra/klist.py -m ping
```

Additionally, there is an ansible kcli/kvirt module under extras, with a sample playbook

## Bash Completion

Create a file named kcli-complete.sh with the following content and source it ( in your bash profile for instance ) 

```
_KCLI_COMPLETE=source kcli
```

## Testing

Basic testing can be run with pytest. If using a remote hypervisor, you ll want to set the *KVIRT_HOST* and *KVIRT_USER* environment variables so that it points to your host with the corresponding user.

## Issues found with cloud images

- Note that you need to install python-simplejson (actually bringing python2.7) to allow ansible to work on Ubuntu
- Debian/Archlinux images are missing the NoCloud datasource for cloud-init. Edit them with guestfish to make them work with cloud-init.

## TODO

- Find a way to easily share the plan files (for instance, adding a list of urls in the conf and a fetch subcommand)
- Remove all the print for the kvirt module and only return data
- Change the try, except blocks for object checks with parsing of the list methods that libvirt provides for most object
- Add basic validation of IPS, netmasks, macs,...  within plan file

## Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
