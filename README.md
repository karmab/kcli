# kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)
[![](https://images.microbadger.com/badges/image/karmab/kcli.svg)](https://microbadger.com/images/karmab/kcli "Get your own image badge on microbadger.com")

![Screenshot](kcli.jpg)

This script is meant to interact with a local/remote libvirt daemon and to easily deploy from templates (optionally using cloudinit).
It will also report ips for any vm connected to a dhcp-enabled libvirt network and generally for every vm deployed from this client.

It started because I switched from ovirt and needed a tool similar to [ovirt.py](https://github.com/karmab/ovirt)

##  Wouldnt it be cool to:

- Interact with libvirt without XML
- Declare all your objects(vm, containers, networks, ansible,...) in a single yaml file!
- Easily grab and share those files from github
- Easily Test all Redhat Infrastructure products, and their upstream counterpart
- Easily share private keys between your vms
- Inject all configuration with cloudinit
- Use the default cloud images
- Optionally use a web UI for all of this!


## Demo!

[![asciicast](https://asciinema.org/a/3p0cn60p0c0j9wd3hzyrs4m0f.png)](https://asciinema.org/a/3p0cn60p0c0j9wd3hzyrs4m0f?autoplay=1)

## Installation

1. Install requirements. you will also need to grab *genisoimage* (or *mkisofs* on OSX) for cloudinit isos to get generated
Console access is based on remote-viewer
For instance if using a RHEL based distribution:

```bash
yum -y install gcc libvirt-devel python-devel genisoimage qemu-kvm nmap-ncat python-pip
```

On Fedora, you' will need an additional package 

```Shell
yum -y install redhat-rpm-config
```


If using a Debian based distribution:

```Shell
apt-get -y install python-pip pkg-config libvirt-dev genisoimage qemu-kvm netcat libvirt-bin python-dev libyaml-dev
```

2. Install kcli from pypi

```Shell
pip install kcli
```

To deploy from templates, grab images at [openstack](http://docs.openstack.org/image-guide/obtain-images.html)

## I use docker, I'm cool

Pull the latest image:

```Shell
docker pull karmab/kcli
```

If running locally, launch it with:

```Shell
docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/.ssh:/root/.ssh karmab/kcli
```

If using a remote hypervisor, launch it with a local kcli.yml file pointing to this hypervisor and providing your ssh keys too

`docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/.ssh:/root/.ssh karmab/kcli`

In both cases, you can also provide a kcli_profiles.yml (and you could also use a dedicated plan directory)

```Shell
docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/kcli_profiles.yml:/root/kcli_profiles.yml  -v ~/.ssh:/root/.ssh karmab/kcli
```

```Shell
docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/kcli_profiles.yml:/root/kcli_profiles.yml -v ~/.ssh:/root/.ssh karmab/kcli
```

The entrypoint is defined as kcli, so you can type commands directly as:

```Shell
docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/kcli_profiles.yml:/root/kcli_profiles.yml -v ~/.ssh:/root/.ssh karmab/kcli list
```

As a bonus, you can alias kcli and run kcli as if it is installed locally instead a Docker container:

```Shell
alias kcli = "docker run --rm -v ~/kcli.yml:/root/kcli.yml -v ~/kcli_profiles.yml:/root/kcli_profiles.yml -v ~/.ssh:/root/.ssh karmab/kcli"
```

For web access, you can use this line instead:

```Shell
ali
as kweb = "docker run --rm -p 9000:9000  -v ~/kcli.yml:/root/kcli.yml -v ~/kcli_profiles.yml:/root/kcli_profiles.yml -v ~/.ssh:/root/.ssh --entrypoint=/usr/bin/kweb karmab/kcli"
```

## Configuration

If you only want to use your local libvirt daemon, no configuration is needed.

Otherwise you will have to declare your settings in ~/kcli.yml. For instance,

```YAML
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
  - default

twix:
 host: 192.168.0.6
 pool: images

bumblefoot:
 host: 192.168.0.4
 pool: images
```

Replace with your own client in default section and indicate host and protocol in the corresponding client section.
Note that most of the parameters are actually optional, and can be overridden in the default, host or profile section (or in a plan file)


If you want to generate a basic settings file, you can use the following command:

```Shell
kcli bootstrap -f
```

You can also go through wizard

```Shell
kcli bootstrap
```

And for advanced bootstrapping, you can specify a target name, host, a pool with a path, and have centos cloud image downloaded

```Shell
kcli bootstrap -a -n twix -H 192.168.0.6 --pool vms --poolpath /home/vms -t
```

Or even use an existing disk for LVM based images (note that the disk will be made into an LVM physical volume, so it should be empty):

```Shell
kcli bootstrap -a -n twix -H 192.168.0.6 --pool vms --poolpath /dev/vdb --pooltype lvm
```

You can add an additional storage pool with:

```Shell
kcli pool -f -t logical -p /dev/sda ssd
```

And define additional networks with:

```Shell
kcli network -c 10.0.1.0/24 private11 --dhcp
```

And download a fedora template:

```Shell
kcli host --download -t fedora
```


## Available parameters for a hypervisor

- *host* Defaults to 127.0.0.1
- *port*
- *user* Defaults to root
- *protocol* Defaults to ssh
- *url* can be used to specify an exotic qemu url
- *insecure* get rid of annoying ssh man in the middle messages

## Available parameters for profile/plan files

- *numcpus* Defaults to 2
- *memory* Defaults to 512M
- *guestid* Defaults to guestrhel764
- *pool* Defaults to default
- *template* Should point to your base cloud image(optional). You can either specify short name or complete path. Note that if you omit the full path and your image lives in several pools, the one from last (alphabetical) pool will be used.
- *disksize* Defaults to 10GB
- *diskinterface* Defaults to virtio. You can set it to ide if using legacy operating systems
- *diskthin* Defaults to True
- *disks* Array of disks to define. For each of them, you can specify pool, size, thin (as boolean), interface (either ide or virtio) and a wwn.If you omit parameters, default values will be used from config or profile file (You can actually let the entire entry blank or just indicate a size number directly)
- *iso* (optional)
- *nets* (optional)
- *gateway* (optional)
- *dns* (optional) Dns servers
- *domain* (optional) Dns search domain
- *start* Defaults to true
- *vnc* Defaults to false (use spice instead)
- *cloudinit* Defaults to true
- *reserveip* Defaults to false
- *reservedns* Defaults to false
- *keys* (optional). Array of ssh public keys to inject
- *cmds* (optional). Array of commands to run
- *profile* name of one of your profile. Only checked in plan file
- *scripts* array of paths of custom script to inject with cloudinit. Note that it will override cmds part. You can either specify full paths or relative to where you're running kcli. Only checked in profile or plan file
- *nested* Defaults to True
- *tunnel* Defaults to False. Setting it to true will make kcli use tunnels for console and for ssh access. You want that if you only open ssh port to your hypervisor!
- *sharedkey* Defaults to False. Set it to true so that a private/public key gets shared between all the nodes of your plan. Additionally, root access will be allowed
- *files* (optional)- Array of files to inject to the vm. For ecach of the them , you can specify path, owner ( root by default) , permissions (600 by default ) and either origin or content to gather content data directly or from specified origin

## Profiles configuration

You can use the file *~/kcli_profiles.yml* to specify profiles (number of CPUS, memory, size of disk, network,....) to use when deploying a vm.

To use a different profiles file, you can use the key profiles in the default section of *~/kcli.yml* and put desired path

The [samples directory](https://github.com/karmab/kcli/tree/master/samples) contains examples to get you started with profiles

## How to use

- Get info on your kvm setup
 - `kcli host --report`
- Switch active client to bumblefoot
  - `kcli host --switch bumblefoot`
- List vms, along with their private ip (and plan if applicable)
 - `kcli list` or (`kcli vm -l`)
- List templates (Note that it will find them out based on their qcow2 extension...)
 - `kcli list -t`
- Create vm from profile base7
 - `kcli vm -p base7 myvm`
- Delete vm
 - `kcli delete vm1`
- Get detailed info on a specific vm
 - `kcli vm -i vm1`
- Start vm
 - `kcli start vm1` (or `kcli vm --start vm1`) 
- Stop vm
 - `kcli stop vm1` (or `kcli vm --stop vm1`)
- Get remote-viewer console
 - `kcli console vm1`
- Get serial console (over tcp!!!). Note that it will only work with vms created with kcli and will require netcat client to be installed on host
 - `kcli console -s vm1`
- Deploy multiple vms using plan x defined in x.yml file
 - `kcli plan -f x.yml x`
- Delete all vm from plan x
  - `kcli plan -d x`
- Add 5GB disk to vm1, using pool named vms
  - `kcli disk -s 5 -p vms vm1`
- Delete disk named vm1_2.img from vm1
  - `kcli disk -d -n vm1_2.img  vm1`
- Update to 2GB memory  vm1
  - `kcli update -m 2048 vm1`
- Update internal ip (useful for ansible inventory over existing bridged vms)
  - `kcli update -1 192.168.0.40 vm1`
- Clone vm1 to new vm2
  - `kcli clone -b vm1 vm2`
- Connect by ssh to the vm (retrieving ip and adjusting user based on the template)
  - `kcli ssh vm1`
- Add a new network
  - `kcli network -c 192.168.7.0/24 --dhcp mynet`
- Add a new nic from network default
 - `kcli nic -n default myvm`
- Delete nic eth2 from vm
 - `kcli nic -di eth2 myvm`

## Web UI

Launch *kweb* and browse at port 9000

You will probably want to tweak the reportdir. Also note that when downloading plans from the web UI , they are stored on the directory where you started kweb


## Multiple hypervisors

If you have multiple hypervisors, you can generally use the flag *-C $CLIENT* to temporarily point to a specific one.

You can also use the following to list all you vms :
 
`kcli -C all list`  


## Templates

Templates should be in the same storage pool as the vm, in order to benefit from the Copy-on-Write mechanism.

For a regular file-backed storage pool, download the image you want, and put it in the backing store directory.

For an LVM-backed storage pool, convert the image to raw format, and upload it to the pool. Assuming a volume group with name `vms`, do:

```Shell
TEMPLATE=xenial-server-cloudimg-amd64-disk1.img
qemu-img convert -f qcow2 -O raw $TEMPLATE ${TEMPLATE}.raw
TSIZE=`ls -l ${TEMPLATE}.raw | tr -s ' ' | cut -d' ' -f5`
virsh vol-create-as vms $TEMPLATE $TSIZE
virsh vol-upload --pool vms $TEMPLATE ${TEMPLATE}.raw
```

Note that disks based on a LVM template always have the same size as the template disk! The code above creates a template-disk that is only just big enough to match the size of the (raw) template. You may want to grow this disk to a reasonable size before creating vm's that use it! Alternatively, you can set the TSIZE parameter above to a static value, rather than using the size of the image.

Note also that kcli uses the default ssh_user according to the different [cloud images](http://docs.openstack.org/image-guide/obtain-images.html).
To guess it, kcli checks the template name. So for example, your centos image MUST contain the term "centos" in the file name,
otherwise the default user "root" will be used. 

## Cloudinit stuff

If cloudinit is enabled (it is by default), a custom iso is generated on the fly for your vm (using mkisofs) and uploaded to your kvm instance (using the libvirt API, not using ssh commands, pretty cool, huh?).
The iso handles static networking configuration, hostname setting, injecting ssh keys and running specific commands and entire scripts, and copying entire files

Also note that if you use cloudinit but dont specify ssh keys to inject, the default ~/.ssh/id_rsa.pub will be used, if present.

## Using plans

You can also define plan files in yaml with a list of profiles, vms, disks, and networks and vms to deploy (look at the sample) and deploy it with kcli plan.
The following type can be used within a plan:

- vm ( this is the type used when none is specified)
- network
- disk
- container
- profile
- ansible


For instance, to define a network named mynet:

```YAML
mynet:
 type: network
 cidr: 192.168.95.0/24
```

You can also use the boolean keyword dhcp (mostly to disable it) and isolated . Note that when not specified, dhcp and nat will be enabled

To define a shared disk named shared1.img between two vms (that typically would be defined within the same plan):

```YAML
share1.img:
 type: disk
 size: 5
 pool: vms
 vms:
  - centos1
  - centos2
```

Regarding vms, You can point at an existing profile in your plans, define all parameters for the vms, or combine both approaches. You can even add your own profile definitions in the plan file and reference them within the same plan:

```YAML
big:
  type: profile
  template: CentOS-7-x86_64-GenericCloud.qcow2
  memory: 6144
  numcpus: 1
  disks:
   - size: 45
  nets:
   - default
  pool: default

myvm:
  profile: big
```


Specific scripts and IPS arrays can be used directly in the plan file (or in profiles one).

The samples directory contains examples to get you started.

Note that the description of the vm will automatically be set to the plan name, and this value will be used when deleting the entire plan as a way to locate matching vms.

When launching a plan, the plan name is optional. If not is provided, a random generated keyword will be used.
This keyword will be a fun name based on this cool project: [name generator](https://github.com/shamrin/namesgenerator).

If a file with the plan isnt specified with -f , the file kcli_plan.yml in the current directory will be used, if available.

Also note that when deleting a plan, the network of the vms will also be deleted if no other vm are using them. You can prevent this by using the keep (-k) flag

For an advanced use of plans along with scripts, you can check the [plans](plans/README.md) page to deploy all upstream projects associated with Red Hat Cloud Infrastructure products (or downstream versions too).

## Sharing plans

You can use the following to retrieve plans from a github repo:

```YAML
kcli plan --get kcli plan -g github.com/karmab/kcli/plans -p karmab_plans
```
The url can also be in:

- an arbitary url ( github api is not used in this case)
- raw github format to retrieve a single file
- a github link

## Disk parameters

You can add disk this way in your profile or plan files

```YAML
disks:
 - size: 20
   pool: vms
 - size: 10
   thin: False
   format: ide
```

Within a disk section, you can use the word size, thin and format as keys

- *diskthin* Value used when not specified in the disk entry. Defaults to true
- *diskinterface* Value used when not specified in the disk entry. Defaults to virtio. Could also be ide, if vm lacks virtio drivers
- *nets* Array of networks. Defaults to ['default']. You can mix simple strings pointing to the name of your network and more complex information provided as hash. For instance:

```YAML
nets:
 - default
 - name: private
   nic: eth1
   ip: 192.168.0.220
   mask: 255.255.255.0
   gateway: 192.168.0.1
```

Within a net section, you can use name, nic, IP, mac, mask and gateway as keys.
Note that up to 8 IPS can also be provided on command line when creating a single vm (with the flag -1, -2, -3,-4,...)

## IP and DNS Reservations

if you set *reserveip*  to True, a reservation will be made if the corresponding network has dhcp and when the provided IP belongs to the network range.

You can also set *reservedns* to True to create a DNS entry for the host in the corresponding network ( Only done for the first nic)

## Docker support

Docker support is mainly enabled as a commodity to launch some containers along vms in plan files. Of course, you will need docker installed on the hypervisor. So the following can be used in a plan file to launch a container:

```YAML
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

```YAML
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

vm will be grouped by plan, or put in the kvirt group if they dont belong to any plan.

Interesting thing is that the script will try to guess the type of vm based on its template, if present, and populate ansible_user accordingly

Try it with:

```Shell
python extra/klist.py --list
ansible all -i extra/klist.py -m ping
```

Additionally, there is an ansible kcli/kvirt module under extras, with a sample playbook

You can also use the key ansible within a profile

```YAML
ansible:
 - playbook: frout.yml
   verbose: true
   variables:
    - x: 8
    - z: 12
```

In a plan file, you can also define additional sections with the ansible type and point to your playbook, optionally enabling verbose and using the key hosts to specify a list of vms to run the given playbook instead. You wont define variables in this case, as you can leverage host_vars and groups_vars directory for this purpose

```YAML
myplay:
 type: ansible
 verbose: false
 playbook: prout.yml
```


Note that when leveraging ansible this way, an inventory file will be generated on the fly for you and let in */tmp/$PLAN.inv* 

## Testing

Basic testing can be run with pytest. If using a remote hypervisor, you ll want to set the *KVIRT_HOST* and *KVIRT_USER* environment variables so that it points to your host with the corresponding user.

## Issues found with cloud images

- Note that you need to install python-simplejson (actually bringing python2.7) to allow ansible to work on Ubuntu
- Debian/Archlinux images are missing the NoCloud datasource for cloud-init. Edit them with guestfish to make them work with cloud-init.

## TODO

- Plans metadata
- Shared profiles
- Scaling Plan
- Plan View (Vagrant Style)
- Multiple Hypervisors in kcli list/ Random hypervisor vm creation
- Add basic validation of IPS, netmasks, macs,...  within plan file
- Check memory and size available when creating a vm
- Present built in plans and use a PLANPATH
- Present built in profiles

## Contributors

See contributors on [GitHub](https://github.com/karmab/kcli/graphs/contributors).

## Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!
