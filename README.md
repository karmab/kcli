# kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)
[![Copr](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli)
[![](https://images.microbadger.com/badges/image/karmab/kcli.svg)](https://microbadger.com/images/karmab/kcli "Get your own image badge on microbadger.com")

![Screenshot](kcli.jpg)

This tool is meant to interact with a local/remote libvirt daemon and to easily deploy from templates (optionally using cloudinit).
It will also report IPS for any vm connected to a dhcp-enabled libvirt network and generally for every vm deployed from this client.

It started because I switched from ovirt and needed a tool similar to [ovirt.py](https://github.com/karmab/ovirt)

## [ChangeLog](changelog.md)

##  Wouldnt it be great to:

- Interact with libvirt without XML
- Declare all your objects(vm, containers, networks, ansible,...) in a single yaml file!
- Easily grab and share those files from github
- Easily Test all Redhat Infrastructure products, and their upstream counterpart
- Easily share private keys between your vms
- Inject all configuration with cloudinit
- Use the default cloud images
- Have a web UI to do it too!

## Demo!

[![asciicast](https://asciinema.org/a/3p0cn60p0c0j9wd3hzyrs4m0f.png)](https://asciinema.org/a/3p0cn60p0c0j9wd3hzyrs4m0f?autoplay=1)

## Requisites

If you dont have kvm installed on the target host, you can also use the following command to get you going ( not needed for ubuntu as it's done when installing kcli package)

```bash
yum -y install libvirt libvirt-daemon-driver-qemu qemu-kvm 
sudo usermod -aG qemu,libvirt YOUR_USER
```

For interaction with local docker, you might also need the following

```bash
sudo groupadd docker
sudo usermod -aG docker YOUR_USER
sudo systemctl restart docker
```

For ubuntu, you will also need the following hack:

```bash
export PYTHONPATH=/usr/lib/python2.7/site-packages
```

If not running as root, you'll also have to add your user to those groups

```bash
sudo usermod -aG qemu,libvirt YOUR_USER
```

for *centos*, check [here](centos.md)

for *macosx*, you'll want to check the docker installation section ( if planning to go against a remote kvm host ) or the dev section for virtualbox

## Installation

If using *fedora*, you can use this:

```bash
dnf -y copr enable karmab/kcli ; dnf -y install kcli
```

If using a debian based distribution, you can use this( example is for ubuntu zesty):

```bash
echo deb [trusted=yes] https://packagecloud.io/karmab/kcli/ubuntu/ zesty main > /etc/apt/sources.list.d/kcli.list ; apt-get update ; apt-get -y install kcli-all
```

## [Dev installation](dev.md)

## [I want to use docker, I'm cool](docker.md)

## Configuration

If you are starting from a completely clean kvm host, you might have to create default pool . You can do it with kcli actually 

```bash
sudo kcli pool -p /var/lib/libvirt/images default
sudo chmod g+rw /var/lib/libvirt/images
```

If you only want to use your local libvirt or virtualbox daemon, *no configuration* is needed.
On most distributions, default network and storage pool already exist.

You can add an additional storage pool with:

```Shell
kcli pool  -p /var/lib/libvirt/images default
```

You can also create a default network

```Shell
kcli network  -c 192.168.122.0/24 default
```

If you want to generate a settings file ( for tweaking or to add remote hosts), you can use the following command:

```Shell
kcli bootstrap
```
And for advanced bootstrapping, you can specify a target name, host, a pool with a path, and have centos cloud image downloaded

```Shell
kcli bootstrap -n twix -H 192.168.0.6 --pool vms --poolpath /home/vms
```

You can also edit directly ~/.kcli/config.yml. For instance,

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
 pool: whatever
```

Replace with your own client in default section and indicate host and protocol in the corresponding client section.

Note that most of the parameters are actually optional, and can be overridden in the default, host or profile section (or in a plan file)

## Ready to go 

Templates aim to typically be the source for your vms, using the existing cloud images from the different distributions. 
*kcli download* can be used to download a specific cloud image. for instance, centos7:

```Shell
kcli download centos7
```

at this point, you can actually deploy vms directly from the template, using default settings for the vm:

```Shell
kcli vm -p CentOS-7-x86_64-GenericCloud.qcow2 vm1
```

by default, your public key will be injected (using cloudinit) to the vm!

you can then access the vm using *kcli ssh*

Note also that kcli uses the default ssh_user according to the different [cloud images](http://docs.openstack.org/image-guide/obtain-images.html).
To guess it, kcli checks the template name. So for example, your centos image must contain the term "centos" in the file name,
otherwise the default user "root" will be used.

## Cloudinit stuff

If cloudinit is enabled (it is by default), a custom iso is generated on the fly for your vm (using mkisofs) and uploaded to your kvm instance (using the libvirt API, not using ssh commands).

The iso handles static networking configuration, hostname setting, injecting ssh keys and running specific commands and entire scripts, and copying entire files

Also note that if you use cloudinit but dont specify ssh keys to inject, the default *~/.ssh/id_rsa.pub* will be used, if present.


## Profiles configuration

Profiles are meant to help creating single vm with preconfigured settings (number of CPUS, memory, size of disk, network,whether to use a template,...)

You use the file *~/.kcli/profiles.yml* to declare your profiles.

Once created, you can use the following for instance to create a vm named myvm from profile centos7

```Shell
kcli vm -p centos7 myvm
```

The [samples directory](https://github.com/karmab/kcli/tree/master/samples) contains more examples to get you started


## Basic use

- Get info on your kvm setup
 - `kcli report`
- Switch active client to bumblefoot
  - `kcli host --switch bumblefoot`
- List vms, along with their private IP (and plan if applicable)
 - `kcli list`
- List templates (Note that it will find them out based on their qcow2 extension...)
 - `kcli list -t`
- Create vm from profile base7
 - `kcli vm -p base7 myvm`
- Delete vm
 - `kcli delete vm1`
- Get detailed info on a specific vm
 - `kcli infovm1`
- Start vm
 - `kcli start vm1` 
 - Stop vm
 - `kcli stop vm1`
- Get remote-viewer console
 - `kcli console vm1`
- Get serial console (over TCP!!!). Note that it will only work with vms created with kcli and will require netcat client to be installed on host
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
- Update internal IP (useful for ansible inventory over existing bridged vms)
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
- Create snapshot snap of vm:
 - `kcli snapshot -n vm1 snap1`
 
## How to use the web version

Launch the following command and access your machine at port 9000:

```Shell
kweb
```

## Multiple hypervisors

If you have multiple hypervisors, you can generally use the flag *-C $CLIENT* to temporarily point to a specific one.

You can also use the following to list all you vms :
 
`kcli -C all list`  


## Using plans

You can also define plan files in yaml with a list of profiles, vms, disks, and networks and vms to deploy (look at the sample) and deploy it with kcli plan.
The following type can be used within a plan:

- network
- template
- disk
- pool
- profile
- ansible
- container
- dns
- plan ( so you can compose plans from several url)
- vm ( this is the type used when none is specified )

Here are some examples of each type ( additional ones can be found in the [samples directory](https://github.com/karmab/kcli/tree/master/samples):

### network
```YAML
mynet:
 type: network
 cidr: 192.168.95.0/24
```
You can also use the boolean keyword dhcp (mostly to disable it) and isolated . Note that when not specified, dhcp and nat will be enabled

### template
```YAML
CentOS-7-x86_64-GenericCloud.qcow2:
 type: template
 url: http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
```
It will only be downloaded only if not present

Note that if you point to an url not ending in qcow2/qc2 ( or img), your browser will be opened for you to proceed.
Also note that you can specify a command with the cmd: key, so that virt-customize is used on the template once it s downloaded

### disk
```YAML
share1.img:
 type: disk
 size: 5
 pool: vms
 vms:
  - centos1
  - centos2
```
Note the disk is shared between two vms (that typically would be defined within the same plan):

### pool
```YAML
mypool:
  type: pool
  path: /home/mypool
```

### profile
```YAML
myprofile:
  type: profile
  template: CentOS-7-x86_64-GenericCloud.qcow2
  memory: 3072
  numcpus: 1
  disks:
   - size: 15
   - size: 12
  nets:
   - default
  pool: default
```

### ansible
```YAML
myplay:
 type: ansible
 verbose: false
 playbook: prout.yml
```
Note that an inventory will be created for you in /tmp and that *group_vars* and *host_vars* directory are taken into account.

### container
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
Look at the docker section for details on the parameters

### plan's plan ( Also known as inception style)

```YAML
ovirt:
  type: plan
  url: github.com/karmab/kcli/plans/ovirt
  file: upstream.yml
  run: true
```

### dns

```YAML
yyy:
 type: dns
 net: default
 ip: 192.168.1.35
```

### vms
You can point at an existing profile in your plans, define all parameters for the vms, or combine both approaches. You can even add your own profile definitions in the plan file and reference them within the same plan:

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

If a file with the plan isn't specified with -f , the file kcli_plan.yml in the current directory will be used, if available.

Also note that when deleting a plan, the network of the vms will also be deleted if no other vm are using them. You can prevent this by using the keep (-k) flag.

For an advanced use of plans along with scripts, you can check the [plans](plans/README.md) page to deploy all upstream projects associated with Red Hat Cloud Infrastructure products (or downstream versions too).

## Sharing plans

You can use the following to retrieve plans from a github repo:

```YAML
kcli plan --get github.com/karmab/kcli/plans -p karmab_plans
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

Within a net section, you can use name, nic, IP, mac, mask, gateway and alias as keys.

You can also use  *noconf: true* to only add the nic with no configuration done in the vm

Note that up to 8 IPS can also be provided on command line when creating a single vm (with the flag -1, -2, -3,-4,...)

## IP, DNS and HOST Reservations

If you set *reserveip*  to True, a reservation will be made if the corresponding network has dhcp and when the provided IP belongs to the network range.

You can also set *reservedns* to True to create a DNS entry for the host in the corresponding network ( only done for the first nic)

You can also set *reservehost* to True to create a HOST entry for the host in /etc/hosts ( only done for the first nic). It's done with sudo and the entry gets removed when you delete the host. Note you should use gnu-sed ( from brew ) instead of regular sed on macosx for proper deletion.

If you dont want to be asked for your sudo password each time, here are the commands that are escalated:

```Shell
 - echo .... # KVIRT >> /etc/hosts
 - sed -i '/.... # KVIRT/d' /etc/hosts
```

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


## ABOUT VIRTUALBOX SUPPORT

While the tool should pretty much work the same on this hypervisor, there are some issues:

- it's impossible to connect using ip, so port forwarding is used instead
- with NATnetworks ( not NAT!), guest addons are needed to gather ip of the vm so they are automatically installed for you. It implies an automatic reboot at the end of provisioning....
- when you specify an unknown network, NAT is used instead. The reason behind is to be able to seamlessly use simple existing plans which make use of the default network ( as found on libvirt)

## Specific parameters for a hypervisor

- *host* Defaults to 127.0.0.1
- *port*
- *user* Defaults to root
- *protocol* Defaults to ssh
- *url* can be used to specify an exotic qemu url
- *tunnel* Defaults to False. Setting it to true will make kcli use tunnels for console and for ssh access. You want that if you only open ssh port to your hypervisor!
- *planview* Defaults to False. Setting it to true will make kcli use the value specified in *~/.kcli/plan* as default plan upon starting and stopping plan. Additionally, vms not belonging to the set plan wont show up when listing

## Available parameters for hypervisor/profile/plan files

- *cpumodel* Defaults to Westmere
- *cpuflags* (optional). You can specify a list of strings with features to enable or use dict entries with *name* of the feature and *enable* either set to True or False. Note that the value for vmx is ignored, as it s handled by the nested flag
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
- *reservehost* Defaults to false
- *keys* (optional). Array of ssh public keys to inject to th vm
- *cmds* (optional). Array of commands to run
- *profile* name of one of your profile. Only checked in plan file
- *scripts* array of paths of custom script to inject with cloudinit. Note that it will override cmds part. You can either specify full paths or relative to where you're running kcli. Only checked in profile or plan file
- *nested* Defaults to True
- *sharedkey* Defaults to False. Set it to true so that a private/public key gets shared between all the nodes of your plan. Additionally, root access will be allowed
- *files* (optional)- Array of files to inject to the vm. For ecach of the them , you can specify path, owner ( root by default) , permissions (600 by default ) and either origin or content to gather content data directly or from specified origin
- *insecure* (optional) Handles all the ssh option details so you dont get any warnings about man in the middle

## TODO

- Read The docs
- Check on memory and disk space when creating vm
- Scaling Plan
- Random hypervisor vm creation
- Plan View (Vagrant Style)
- validation of ips, netmasks, macs,...  within plan file

## Contributors

See [contributors on GitHub](https://github.com/karmab/kcli/graphs/contributors)

## Copyright

Copyright 2017 Karim Boumedhel

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
