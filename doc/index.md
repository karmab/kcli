[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)
[![Copr](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli)
[![](https://images.microbadger.com/badges/image/karmab/kcli.svg)](https://microbadger.com/images/karmab/kcli "Get your own image badge on microbadger.com")

# About

This tool is meant to interact with existing virtualization providers (libvirt, kubevirt, ovirt, openstack, gcp and aws, vsphere) and to easily deploy and customize vms from cloud images.

You can also interact with those vms (list, info, ssh, start, stop, delete, console, serialconsole, add/delete disk, add/delete nic,...).

Futhermore, you can deploy vms using predefined profiles, several at once using plan files or entire products for which plans were already created for you.


# Installation

## Requisites

If you don't have libvirt installed on the target hypervisor, you can use the following command to get you going:

```bash
sudo yum -y install libvirt libvirt-daemon-driver-qemu qemu-kvm 
sudo usermod -aG qemu,libvirt $(id -un)
newgrp libvirt
```

(Optional) For interaction with your local docker daemon, you also need the following:

```bash
sudo groupadd docker
sudo usermod -aG docker YOUR_USER
sudo systemctl restart docker
```

If not running as root, you'll have to add your user to those groups

```bash
sudo usermod -aG qemu,libvirt YOUR_USER
```

## Quick install method

```Shell
curl https://raw.githubusercontent.com/karmab/kcli/master/install.sh | sh
```

## Container versus Package

- Both install methods are continuously updated
- The package version doesn't bundle the dependencies for anything else than libvirt, so you have to install the extra packages for each additional cloud platforms, which are listed in the *Provider specifics* section. This means that the package version is lightweight but needs extra works for other providers.
- The console/serial console functionality works better with the package version. In container mode, it only outputs the command to launch manually to get to the console.

## Container install method

In the commands below, use either docker or podman (if you don't want a big fat daemon)

Pull the latest image:

```Shell
docker pull karmab/kcli
```

To run it

```Shell
docker run --rm karmab/kcli
```

There are several recommended flags:

- `--net host` for kcli ssh
- `-v /var/run/libvirt:/var/run/libvirt -v /var/lib/libvirt/images:/var/lib/libvirt/images` if running against a local client.
- `-v  ~/.kcli:/root/.kcli` to use your kcli configuration (also profiles and repositories) stored locally.
- `-v ~/.ssh:/root/.ssh` to share your ssh keys. Alternatively, you can store your public and private key in the ~/.kcli directory.
- `--security-opt label=disable` if running with selinux.
- `-v $PWD:/workdir` to access plans below your current directory.
- `-v $HOME:/root` to share your entire home directory, useful if you want to share secret files, `~/register.sh` for instance).
- `-e HTTP_PROXY=your_proxy -e HTTPS_PROXY=your_proxy`
- `-v ~/.kube:/root/.kube` to share your kubeconfig.
- `-v /var/tmp:/ignitiondir` for ignition files to be properly processed.

For web access, you can switch with `-p 9000:9000 --entrypoint=/usr/bin/kweb` and thus accessing to port 9000.

As a bonus, you can use the following aliases:

```Shell
alias kcli='docker run --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli'
alias kclishell='docker run --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/bin/sh karmab/kcli'
alias kweb='docker run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli'
```

## Package install method

If using *fedora*, you can use this:

```bash
dnf -y copr enable karmab/kcli ; dnf -y install kcli
```

If using a debian based distribution, you can use this (example is for ubuntu cosmic):

```bash
echo deb [trusted=yes] https://packagecloud.io/karmab/kcli/ubuntu/ cosmic main > /etc/apt/sources.list.d/kcli.list ; apt-get update ; apt-get -y install python3-kcli
```

## Dev installation

### Generic platform

```Shell
pip install kcli
```

Or for a full install:

```
pip install -e git+https://github.com/karmab/kcli.git#egg=kcli[all]
```

# Configuration

If you only want to use your local libvirt, *no specific configuration* is needed.

kcli configuration is done in ~/.kcli directory, that you need to manually create. It will contain:

- config.yml generic configuration where you declare clients.
- profiles.yml stores your profiles where you combine things like memory, numcpus and all supported parameters into named profiles to create vms from.
- id_rsa/id_rsa.pub/id_dsa/id_dsa.pub You can store your default public and private keys in *.kcli* directory which will be the first place to look at them when connecting to a remote kvm hpervisor, virtual machine or when injecting your public key.

You can generate a default config file (with all parameters commented) pointing to your local host with:
    
```Shell
kcli create host kvm -H 127.0.0.1 local
```

Or indicate a different target host

```Shell
kcli create host -H 192.168.0.6 host1
```

On most distributions, default network and storage pool for libvirt are already defined.

If needed, you can create this default storage pool with this:

```Shell
kcli create pool -p /var/lib/libvirt/images default
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images
```

And default network:

```Shell
kcli create network  -c 192.168.122.0/24 default
```

For using several hypervisors, you can use the command *kcli create host* or simply edit your configuration file.

For instance, here's a sample `~/.kcli/config.yml` with two hypervisors:

```YAML
default:
 client: mycli
 pool: default
 numcpus: 2
 memory: 1024
 disks:
  - size: 10
 protocol: ssh
 nets:
  - default

mycli:
 host: 192.168.0.6
 pool: default

bumblefoot:
 host: 192.168.0.4
 pool: whatever
```

Replace with your own client in default section and indicate the relevant parameters in the corresponding client section, depending on your client/host type.

Most of the parameters are actually optional, and can be overridden in the default, client or profile section (or in a plan file).
You can find a fully detailed config.yml sample [here](https://github.com/karmab/kcli/tree/master/samples/config.yml)

# Provider specifics

## Libvirt

```
twix:
 type: kvm
 host: 192.168.1.6
```

Without configuration, libvirt provider tries to connect locally using qemu:///system.

Additionally, remote libvirt hypervisors can be configured by indicating either a host, a port and protocol or a custom qemu url.

When using the host, port and protocol combination, default protocol uses ssh and as such assumes you are able to connect without password to your remote libvirt instance.

If using tcp protocol instead, you will need to configure libvirtd in your remote libvirt hypervisor to accept insecure remote connections.

You will also likely want to indicate default libvirt pool to use (although as with most parameters, it can be done in the default section).

The following parameters are specific to libvirt:

- url custom qemu uri.
- session Defaults to False. If you want to use qemu:///session ( locally or remotely). Not recommended as it complicates access to the vm and is supposed to have lower performance.

## Gcp

```
gcp1:
 type: gcp
 credentials: ~/myproject.json
 project: myproject
 zone: europe-west1-b
```

The following parameters are specific to gcp:

- credentials (pointing to a json service account file). if not specified, the environment variable *GOOGLE_APPLICATION_CREDENTIALS* will be used
- project 
- zone

also note that gcp provider supports creation of dns records for an existing domain and that your home public key will be uploaded if needed

To gather your service account file:

- Select the "IAM" → "Service accounts" section within the Google Cloud Platform console.
- Select "Create Service account".
- Select "Project" → "Editor" as service account Role.
- Select "Furnish a new private key".
- Select "Save".

To Create a dns zone:

- Select the "Networking" → "Network Services" → "Cloud DNS".
- Select "Create Zone".
- Put the same name as your domain, but with '-' instead.

If accessing behind a proxy, be sure to set *HTTPS_PROXY* environment variable to `http://your_proxy:your_port`

To use this provider with kcli rpm, you'll need to install (from pip):

- *google-api-python-client*
- *google-auth-httplib2*
- *google-cloud-dns*

## Aws

```
aws:
 type: aws
 access_key_id: AKAAAAAAAAAAAAA
 access_key_secret: xxxxxxxxxxyyyyyyyy
 region: eu-west-3
 keypair: mykey
```

The following parameters are specific to aws:

- access_key_id
- access_key_secret
- region
- keypair 

To use this provider with kcli rpm, you'll need to install *python3-boto3* rpm

## Kubevirt

For kubevirt, you will need to define one ( or several !) sections with the type kubevirt in your *~/.kcli/config.yml*

Authentication is either handled by your local ~/.kubeconfig (kcli will try to connect to your current kubernetes/openshift context or with specific token:

```
kubevirt:
 type: kubevirt
```

You can use additional parameters for the kubevirt section:

- context: the k8s context to use.
- pool: your default storageclass. can also be set as blank, if no storage class should try to bind pvcs.
- host: k8s api node .Also used for tunneling ssh.
- port: k8s api port.
- ca_file: optional certificate path.
- token: token, either from user or service account.
- tags: additional list of tags in a key=value format to put to all created vms in their *nodeSelector*. Can be further indicated at profile or plan level in which case values are combined. This provides an easy way to force vms to run on specific nodes, by matching labels.
- multus: whether to create vms on multus backed networks. Defaults to true.
- cdi: whether to use cdi. Defaults to true. A check on whether cdi is actually present will be performed.

You can use the following indications to gather context, create a suitable service account and retrieve its associated token:

To list the context at your disposal
```
kubectl config view -o jsonpath='{.contexts[*].name}'
```

To create a service account and give it privileges to handle vms,

```
SERVICEACCOUNT=xxx
kubectl create serviceaccount $SERVICEACCOUNT -n default
kubectl create clusterrolebinding $SERVICEACCOUNT --clusterrole=cluster-admin --user=system:serviceaccount:default:$SERVICEACCOUNT
```

To gather a token (in /tmp/token):

```
SERVICEACCOUNT=xxx
SECRET=`kubectl get sa $SERVICEACCOUNT -o jsonpath={.secrets[0].name}`
kubectl get secret $SECRET -o jsonpath={.data.token} | base64 -d
```

on openshift, you can simply use

```
oc whoami -t
```

*kubectl* is currently a hard requirement for consoles

To use this provider with kcli rpm, you'll need to install *python3-kubernetes* rpm

## Ovirt

```
myovirt:
 type: ovirt
 host: ovirt.default
 user: admin@internal
 password: prout
 datacenter: Default
 cluster: Default
 pool: Default
 org: YourOrg
 ca_file: ~/ovirt.pem
 imagerepository: ovirt-image-repository
```

The following parameters are specific to ovirt:

- org Organization 
- ca_file Points to a local path with the cert of the ovirt engine host. It can be retrieved with 
`wget http://$HOST/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA`
- cluster  Defaults to Default
- datacenter Defaults to Default
- filtervms Defaults to True. Only list vms created by kcli. Useful for environments when you are superadmin and have a ton of vms!!!
- filteruser Defaults to False. Only list vms created by own user
- filtertag Defaults to None. Only list vms created by kcli with the corresponding filter=filtertag in their description. Useful for environments when you share the same user
- imagerepository (Optional). A Glance image provider repository to use to retrieve images. Defaults to `ovirt-image-repository`.

Note that pool in Ovirt context refers to storage domain.

To use this provider with kcli rpm, you'll need to install (from pip) *ovirt-engine-sdk-python*

On fedora, for instance, you can run the following:

```
dnf -y copr enable karmab/kcli
yum -y install kcli gcc redhat-rpm-config python3-devel openssl-devel libxml2-devel libcurl-devel
export PYCURL_SSL_LIBRARY=openssl
pip3 install ovirt-engine-sdk-python
```

On rhel, set PYCURL_SSL_LIBRARY to nss instead

If you install manually from pip, you might need to install pycurl manually with the following line (and get openssl-dev headers)

```
pip install --no-cache-dir --global-option=build_ext --global-option="-L/usr/local/opt/openssl/lib" --global-option="-I/usr/local/opt/openssl/include"  pycurl
```

## Openstack

```
myopenstack:
 type: openstack
 user: testk
 password: testk
 project: testk
 domain: Default
 auth_url: http://openstack:5000/v3
```

The following parameters are specific to openstack:

- auth_url
- project
- domain

To use this provider with kcli rpm, you'll need to install the following rpms 

- *python3-keystoneclient*
- *python3-glanceclient*
- *python3-cinderclient*
- *python3-neutronclient*
- *python3-novaclient*

## Vsphere

```
myvsphere:
 type: vsphere
 host: xxx-vcsa67.vcenter.e2e.karmalabs.com
 user: administrator@karmalabs.com
 password: mypassword
 datacenter: Madrid
 cluster: xxx
 filtervms: true
 pool: mysuperdatastore

```

The following parameters are specific to vsphere:

- cluster. 
- datacenter Defaults to Default
- filtervms Defaults to True. Only list vms created by kcli. Useful for environments when you are superadmin and have a ton of vms!!!

Note that pool in Vsphere context refers to datastore.

To use this provider with kcli rpm, you'll need to install *python3-pyvmomi*

Also note that kcli download will only upload OVAS, either from specified urls or gathering them in the case of rhcos/fcos.If not present, govc binary is downloaded on the fly in */var/tmp* to provide this functionality.

# Storing secrets

You can hide your secrets in *~/.kcli/config.yml* by replacing any value by *?secret*. You can then place the real value in *~/.kcli/secrets.yml* by using the same yaml hierarchy.

For instance, if you have the following in your config file:

```
xxx:
 password: ?secret
```

You would then put the real password in your secrets file this way:

```
xxx:
 password: mypassword
```


# Usage

Cloud Images from common distros aim to be the primary source for your vms
*kcli download image* can be used to download a specific cloud image. for instance, centos7:

```Shell
kcli download image centos7
```

at this point, you can deploy vms directly from the template, using default settings for the vm:

```Shell
kcli create vm -i centos7 vm1
```

By default, your public key will be injected (using cloudinit) to the vm.

You can then access the vm using *kcli ssh*.

Kcli uses the default ssh_user according to the different [cloud images](http://docs.openstack.org/image-guide/obtain-images.html).
To guess it, kcli checks the template name. So for example, your centos image must contain the term "centos" in the file name,
otherwise the default user "root" will be used.

Using parameters, you can tweak the vm creation. All keywords can be used. For instance:

```Shell
kcli create vm -i centos7 -P memory=2048 -P numcpus=2 vm1
```

You can also pass disks, networks, cmds (or any keyword, really):

```Shell
kcli create vm -i centos7 -P disks=[10,20] -P nets=[default,default] -P cmds=[yum -y install nc] vm1
```

You can use the following to get a list of available keywords, and their default value


```Shell
kcli get keyword
```

## Profiles configuration

Instead of passing parameters this way, you can use profiles.

Profiles are meant to help creating single vm with preconfigured settings (number of CPUS, memory, size of disk, network, whether to use a template, extra commands to run on start, whether reserving dns,....)

You use the file *~/.kcli/profiles.yml* to declare your profiles. Here's a snippet declaring the profile `centos`:

```
mycentos:
 image: CentOS-7-x86_64-GenericCloud.qcow2
 numcpus: 2
 disks:
  - size: 10
 reservedns: true
 nets:
  - name: default
 cmds:
  - echo unix1234 | passwd --stdin root
```

With this section, you can use the following to create a vm

```Shell
kcli create vm -p mycentos myvm
```

You can use the [profile file sample](https://github.com/karmab/kcli-plans/tree/master/samples/profiles.yml) to get you started

Note that when you download a given cloud image, a minimal associated profile is created for you.

## Cloudinit/Ignition support

Cloudinit is enabled by default and handles static networking configuration, hostname setting, injecting ssh keys and running specific commands and entire scripts, and copying entire files.

For vms based on coreos, ignition is used instead of cloudinit although the syntax is the same. If $name.ign or $plan.ign are found in the current directory, their content will be merged.

To ease openshift deployment, when a node has a name in the $cluster-role-$num, where role can either be master, worker or bootstrap, additional paths are searched, namely $cluster-$role.ign and clusters/$cluster/$role.ign

For ignition support on ovirt, you will need a version of ovirt >= 4.3.4. Note that this requires to use an openstack rhcos image.

A similar mechanism allows customization for other providers.

## Typical commands

- List vms
  - `kcli list vm`
- List cloud images
  - `kcli list images `
- Create vm from a profile named base7
  - `kcli create vm -p base7 myvm`
- Create vm from profile base7 on a specific client/host  named twix
  - `kcli -C twix create vm -p base7 myvm`
- Delete vm
  - `kcli delete vm vm1`
- Get detailed info on a specific vm
  - `kcli info vm vm1`
- Start vm
  - `kcli start vm vm1` 
- Stop vm
  - `kcli stop vm vm1`
- Switch active client/host to bumblefoot
  - `kcli switch host bumblefoot`
- Get remote-viewer console
  - `kcli console vm vm1`
- Get serial console (over TCP). It will only work with vms created with kcli and will require netcat client to be installed on hypervisor
  - `kcli console vm -s vm1`
- Deploy multiple vms using plan x defined in x.yml file
  - `kcli create plan -f x.yml x`
- Delete all vm from plan x
  - `kcli delete plan x`
- Add 5GB disk to vm1, using pool named images
  - `kcli create vm-disk -s 5 -p images vm1`
- Delete disk named vm1_2.img from vm1
  - `kcli create disk -d -n vm1_2.img  vm1`
- Update to 2GB memory  vm1
  - `kcli update vm -m 2048 vm1`
- Clone vm1 to new vm2
  - `kcli clone vm -b vm1 vm2`
- Connect by ssh to the vm
  - `kcli ssh vm vm1`
- Add a new network
  - `kcli create network -c 192.168.7.0/24 --dhcp mynet`
- Add a new pool
  - `kcli create pool -t dir -p /hom/images images`
- Add a new nic from network default
  - `kcli create nic -n default myvm`
- Delete nic eth2 from vm
  - `kcli delete nic -i eth2 myvm`
- Create snapshot snap of vm:
  - `kcli snapshot vm -n vm1 snap1`
- Get info on your kvm setup
  - `kcli info host`
- Export vm:
  - `kcli export vm vm1`

## Omitting vm's name
 
When you don't specify a vm, the last one created by kcli on the corresponding client is used (the list of the vms created is stored in *~/.kcli/vm*)

So for instance, you can simply use the following command to access your vm:

`kcli ssh vm`

## How to use the web version

Launch the following command and access your machine at port 9000:

```Shell
kweb
```

## Multiple clients

If you have multiple hypervisors/clients, you can generally use the flag *-C $CLIENT* to point to a specific one.

You can also use the following to list the vms of all your hosts/clients:
 
`kcli -C all list vm`

## Using plans

You can also define plan files in yaml with a list of profiles, vms, disks, and networks and vms to deploy and deploy it with kcli plan.
The following type can be used within a plan:

- network
- template
- disk
- pool
- profile
- ansible
- container
- dns
- plan ( so you can compose plans from several urls)
- vm ( this is the type used when none is specified )

Here are some examples of each type ( additional ones can be found in this [samples directory ](https://github.com/karmab/kcli-plans/tree/master/samples) ):

### network
```YAML
mynet:
 type: network
 cidr: 192.168.95.0/24
```
You can also use the boolean keyword *dhcp* (mostly to disable it) and isolated . When not specified, dhcp and nat will be enabled

### template
```YAML
CentOS-7-x86_64-GenericCloud.qcow2:
 type: template
 url: http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
```
It will only be downloaded only if not present

If you point to an url not ending in qcow2/qc2 ( or img), your browser will be opened for you to proceed.
Also note that you can specify a command with the *cmd* key, so that virt-customize is used on the template once it's downloaded

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

Here the disk is shared between two vms (that typically would be defined within the same plan):

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
 groups:
   nodes:
   - node1
   - node2
   masters:
   - master1
   - master2
   - master3
```

An inventory will be created for you in /tmp and that *group_vars* and *host_vars* directory are taken into account.
You can optionally define your own groups, as in this example.
The playbooks are launched in alphabetical order

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
Look at the container section for details on the parameters

### plan's plan ( Also known as inception style)

```YAML
ovirt:
  type: plan
  url: github.com/karmab/kcli-plans/ovirt/upstream.yml
  run: true
```

You can alternatively provide a file attribute instead of url pointing to a local plan file:

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

The [kcli-plans repo](https://github.com/karmab/kcli-plans) contains samples to get you started, along with plans for projects i often use (openshift, kubevirt,openstack, ovirt, ...) .

The description of the vm will automatically be set to the plan name, and this value will be used when deleting the entire plan as a way to locate matching vms.

When launching a plan, the plan name is optional. If not is provided, a random generated keyword will be used.

If a file with the plan isn't specified with -f , the file kcli_plan.yml in the current directory will be used, if available.

When deleting a plan, the network of the vms will also be deleted if no other vm are using them. You can prevent this by using the keep (-k) flag.

For an advanced use of plans, check the [kcli-plans](https://github.com/karmab/kcli-plans) repository to deploy all upstream/downstream projects associated with Red Hat Cloud Infrastructure products or [kcli-openshift4](https://github.com/karmab/kcli-openshift4) which leverages kcli to deploy openshift4 anywhere.

## Remote plans

You can use the following to execute a plan from a remote url:

```YAML
kcli create plan --url https://raw.githubusercontent.com/karmab/kcli-plans/master/ovirt/upstream.yml
```

## Disk parameters

You can add disk this way in your profile or plan files:

```YAML
disks:
 - size: 20
   pool: vms
 - size: 10
   thin: False
   interface: ide
```

Within a disk section, you can use the word size, thin and format as keys.

- *thin* Value used when not specified in the disk entry. Defaults to true
- *interface* Value used when not specified in the disk entry. Defaults to virtio. Could also be ide, if vm lacks virtio drivers

## Network parameters

You can mix simple strings pointing to the name of your network and more complex information provided as hash. For instance:

```YAML
nets:
 - default
 - name: private
   nic: eth1
   ip: 192.168.0.220
   mask: 255.255.255.0
   gateway: 192.168.0.1
```

Within a net section, you can use name, nic, IP, mac, mask, gateway and alias as keys. type defaults to virtio but you can specify anyone (e1000,....).

You can also use  *noconf: true* to only add the nic with no configuration done in the vmñ

Fore coreos based vms, You can also use  *etcd: true* to auto configure etcd on the corresponding nic.

the *ovs: true* allows you to create the nic as ovs port of the indicated bridge. Not that such bridges have to be created independently at the moment

You can provide network configuration on the command line when creating a single vm with *-P ip1=... -P netmask1=... -P gateway=...*

## ip, dns and host Reservations

If you set *reserveip*  to True, a reservation will be made if the corresponding network has dhcp and when the provided IP belongs to the network range.

You can set *reservedns* to True to create a dns entry for the vm in the corresponding network ( only done for the first nic).

You can set *reservehost* to True to create an entry for the host in /etc/hosts ( only done for the first nic). It's done with sudo and the entry gets removed when you delete the vm. On macosx, you should use gnu-sed ( from brew ) instead of regular sed for proper deletion.

If you dont want to be asked for your sudo password each time, here are the commands that are escalated:

```Shell
 - echo .... # KVIRT >> /etc/hosts
 - sed -i '/.... # KVIRT/d' /etc/hosts
```

## Docker/Podman support in plans

Docker/Podman support is mainly enabled as a commodity to launch some containers along vms in plan files. Of course, you will need docker or podman installed on the client. So the following can be used in a plan file to launch a container:

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

- *image* name of the image to pull ( You can alternatively use the keyword *template*).
- *cmd* command to run within the container.
- *ports* array of ports to map between host and container.
- *volumes* array of volumes to map between host and container. You can alternatively use the keyword *disks*. You can also use more complex information provided as a hash

Within a volumes section, you can use path, origin, destination and mode as keys. mode can either be rw o ro and when origin or destination are missing, path is used and the same path is used for origin and destination of the volume. You can also use this typical docker syntax:

```YAML
volumes:
 - /home/cocorico:/root/cocorico
```

Additionally, basic commands ( start, stop, console, plan, list) accept a *--container* flag.

Also note that while python sdk is used when connecting locally, commands are rather proxied other ssh when using a remote hypervisor ( reasons beeing to prevent mismatch of version between local and remote docker and because enabling remote access for docker is considered insecure and needs some uncommon additional steps ).

Finally, note that if using the docker version of kcli against your local hypervisor , you'll need to pass a docker socket:

`docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/.ssh:/root/.ssh -v /var/run/docker.sock:/var/run/docker.sock karmab/kcli`

## Ansible support

You can check klist.py in the extra directory and use it as a dynamic inventory for ansible.
It's also present at `/usr/share/doc/kcli/extras/klist.py` in the rpm and `/usr/bin/klist.py` in the container

The script uses sames conf as kcli (and as such defaults to local if no configuration file is found).

vm will be grouped by plan, or put in the kvirt group if they dont belong to any plan.

An interesting thing is that the script will try to guess the type of vm based on its template, if present, and populate ansible_user accordingly.

Try it with:

```Shell
python extras/klist.py --list
ansible all -i extras/klist.py -m ping
```

If you're using kcli as a container, you will have to create a script such as the following to properly call the inventory.

```
#!/bin/bash
docker run -it --security-opt label:disable -v ~/.kcli:/root/.kcli -v /var/run/libvirt:/var/run/libvirt --entrypoint=/usr/bin/klist.py karmab/kcli $@
```

Additionally, there are ansible kcli modules in [ansible-kcli-modules](https://github.com/karmab/ansible-kcli-modules) repository, with sample playbooks:

- kvirt_vm allows you to create/delete vm (based on an existing profile or a template)
- kvirt_plan allows you to create/delete a plan
- kvirt_product allows you to create/delete a product (provided you have a product repository configured)
- kvirt_info allows you to retrieve a dict of values similar to `kcli info` output. You can select which fields to gather

Those modules rely on python3 so you will need to pass `-e 'ansible_python_interpreter=path_to_python3'` to your ansible-playbook invocations ( or set it in your inventory) if your default ansible installation is based on python2.

Both kvirt_vm, kvirt_plan and kvirt_product support overriding parameters:

```
- name: Deploy fission with additional parameters
  kvirt_product:
    name: fission
    product: fission
    parameters:
     fission_type: all
     docker_disk_size: 10
```

Finally, you can use the key ansible within a profile:

```YAML
ansible:
 - playbook: frout.yml
   verbose: true
   variables:
    - x: 8
    - z: 12
```

In a plan file, you can also define additional sections with the ansible type and point to your playbook, optionally enabling verbose and using the key hosts to specify a list of vms to run the given playbook instead.

You wont define variables in this case, as you can leverage host_vars and groups_vars directory for this purpose.

```YAML
myplay:
 type: ansible
 verbose: false
 playbook: prout.yml
```

When leveraging ansible this way, an inventory file will be generated on the fly for you and let in */tmp/$PLAN.inv*.

You can set the variable yamlinventory to True at default, host or profile level if you want the generated file to be yaml based. In this case, it will be named */tmp/$PLAN.inv.yaml*.

## Using products

To easily share plans, you can make use of the products feature which leverages them:

### Repos

First, add a repo containing a KMETA file with yaml info about products you want to expose. For instance, mine

```
kcli create repo -u https://github.com/karmab/kcli-plans karmab
```

You can also update later a given repo, to refresh its KMETA file ( or all the repos, if not specifying any)

```
kcli update repo REPO_NAME
```

You can delete a given repo with

```
kcli delete repo REPO_NAME
```

### Product

Once you have added some repos, you can list available products, and get their description

```
kcli list products 
```

You can also get direct information on the product (memory and cpu used, number of vms deployed and all parameters that can be overriden)

```
kcli info product YOUR_PRODUCT 
```

And deploy any product. Deletion is handled by deleting the corresponding plan.

```
kcli create product YOUR_PRODUCT
```

## Running on kubernetes/openshift 

You can run the container on those platforms and either use the web interface or log in the pod to run `kcli` commandline

On openshift, you'll need to run first those extra commands:

```
oc new-project kcli
oc adm policy add-scc-to-user anyuid system:serviceaccount:kcli:default
oc expose svc kcli
```

Then:

```
kubectl create configmap kcli-config --from-file=~/.kcli
kubectl create configmap ssh-config --from-file=~/.ssh
kubectl create -f https://raw.githubusercontent.com/karmab/kcli/master/extras/k8sdeploy.yml
```

Alternatively, look at [https://github.com/karmab/kcli-controller](https://github.com/karmab/kcli-controller) for a controller/operator handling vms and plans as crds and creating the corresponding assets with kcli/kvirt library.

## Testing

Basic testing can be run with pytest, which leverages your existing kcli config:

# Specific parameters for a client

- *host* Defaults to 127.0.0.1
- *port*
- *user* Defaults to root
- *protocol* Defaults to ssh
- *url* can be used to specify an exotic qemu url
- *tunnel* Defaults to False. Setting it to true will make kcli use tunnels for console and for ssh access. You want that if you only open ssh port to your client!
- *planview* Defaults to False. Setting it to true will make kcli use the value specified in *~/.kcli/plan* as default plan upon starting and stopping plan. Additionally, vms not belonging to the set plan wont show up when listing
- *keep_networks* Defaults to False. Setting it to true will make kcli keeps networks when deleting plan

# Available parameters for client/profile/plan files

- *cpumodel* Defaults to host-model
- *cpuflags* (optional). You can specify a list of strings with features to enable or use dict entries with *name* of the feature and *policy* either set to require,disable, optional or force. The value for vmx is ignored, as it's handled by the nested flag.
- *numcpus* Defaults to 2
- *cpuhotplug* Defaults to False
- *memory* Defaults to 512M
- *memoryhotplug* Defaults to False
- *flavor* For gcp, aws and openstack, You can specify an existing flavor so that cpu and memory is derived from it.
- *guestid* Defaults to guestrhel764
- *pool* Defaults to default
- *template* Should point to your base cloud image(optional). You can either specify short name or complete path. If you omit the full path and your image lives in several pools, the one from last (alphabetical) pool will be used.
- *disksize* Defaults to 10GB
- *diskinterface* Defaults to virtio. You can set it to ide if using legacy operating systems
- *diskthin* Defaults to True
- *disks* Array of disks to define. For each of them, you can specify pool, size, thin (as boolean), interface (either ide or virtio) and a wwn.If you omit parameters, default values will be used from config or profile file (You can actually let the entire entry blank or just indicate a size number directly)
- *iso* (optional)
- *nets* Array of networks to define. For each of them, you can specify just a string for the name, or a dict containing name, public and alias and ip, mask and gateway
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
- *scripts* array of paths of custom script to inject with cloudinit. It will be merged with cmds parameter. You can either specify full paths or relative to where you're running kcli. Only checked in profile or plan file
- *nested* Defaults to True
- *sharedkey* Defaults to False. Set it to true so that a private/public key gets shared between all the nodes of your plan. Additionally, root access will be allowed
- *privatekey* Defaults to False. Set it to true so that your private key is passed to the nodes of your plan. If you need this, you know why :)
- *files* (optional)- Array of files to inject to the vm. For each of them, you can specify path, owner ( root by default) , permissions (600 by default ) and either origin or content to gather content data directly or from specified origin. When specifying a directory as origin, all the files it contains will be parsed and added.
- *insecure* (optional) Handles all the ssh option details so you dont get any warnings about man in the middle
- *client* (optional) Allows you to create the vm on a specific client. This field is not used for other types like network, so expect to use this in relatively simple plans only
- *base* (optional) Allows you to point to a parent profile so that values are taken from parent when not found in the current profile. Scripts and commands are rather concatenated between default, father and children ( so you have a happy family...)
- *tags* (optional) Array of tags to apply to gcp instances (usefull when matched in a firewall rule). In the case of kubevirt, it s rather a dict of key=value used as node selector (allowing to force vms to be scheduled on a matching node)
- <a name="rhnregister">*rhnregister*</a> (optional). Auto registers vms whose template starts with rhel Defaults to false. Requires to either rhnuser and rhnpassword, or rhnactivationkey and rhnorg, and an optional rhnpool
- *rhnuser* (optional). Red Hat network user
- *rhnpassword* (optional). Red Hat network password
- *rhnactivationkey* (optional). Red Hat network activation key
- *rhnorg* (optional). Red Hat network organization
- *rhnpool* (optional). Red Hat network pool
- *rhnwait* (optional). Defaults to 0. Delay in seconds before attempting to subscribe machine, to be used in environment where networking takes more time to come up.
- *enableroot* (optional). Defaults to true. Allows ssh access as root user
- *storemetadata* (optional). Defaults to false. creates a /root/.metadata yaml file whith all the overrides applied. On gcp, those overrides are also stored as extra metadata
- *sharedfolders* (optional). Defaults to a blank array. List of paths to share between a kvm hypervisor and vm. You will also make sure that the path is accessible as qemu user (typically with id 107) and use an hypervisor and a guest with 9p support (centos/rhel lack it)
- *yamlinventory* (optional). Defaults to false. If set to true, ansible generated inventory for single vms or for plans containing ansible entries will be yaml based.
- *autostart* (optional). Defaults to false. Autostarts vm (only applies for libvirt)
- *kernel* (optional). Kernel location to pass to the vm. Needs to be local to the hypervisor.
- *initrd* (optional). Initrd location to pass to the vm. Needs to be local to the hypervisor.
- *cmdline* (optional). Cmdline to pass to the vm.
- *numamode* optional numamode to apply to the workers only.
- *cpupinning* optional cpupinning conf to apply to the workers only.
- *pcidevices* optional array of pcidevices to passthrough to the first worker only. Check [here](https://github.com/karmab/kcli-plans/blob/master/samples/pcipassthrough/pci.yml) for an example.

## Overriding parameters

You can override parameters in:

- commands
- scripts
- files
- plan files
- profiles

For that, you can pass in kcli vm or kcli plan the following parameters:

- -P x=1 -P y=2 and so on .
- --paramfile - In this case, you provide a yaml file ( and as such can provide more complex structures ).

The indicated objects are then rendered using jinja.

```
centos:
 template: CentOS-7-x86_64-GenericCloud.qcow2
 cmds:
  - echo x={{ x }} y={{ y }} >> /tmp/cocorico.txt
  - echo {{ password | default('unix1234') }} | passwd --stdin root
```

You can make the previous example cleaner by using the special key parameters in your plans and define there variables:

```
parameters:
 password: unix1234
 x: coucou
 y: toi
centos:
 template: CentOS-7-x86_64-GenericCloud.qcow2
 cmds:
  - echo x={{ x }} y={{ y }} >> /tmp/cocorico.txt
  - echo {{ password  }} | passwd --stdin root
```

Finally note that you can also use advanced jinja constructs like conditionals and so on. For instance:

```
parameters:
  net1: default
vm4:
  template: CentOS-7-x86_64-GenericCloud.qcow2
  nets:
    - {{ net1 }}
{% if net2 is defined %}
    - {{ net2 }}
{% endif %}
```

Also, you can reference a *baseplan* file in the *parameters* section, so that parameters are concatenated between the base plan file and the current one:

```
parameters:
   baseplan: upstream.yml
   xx_version: v0.7.0
```

# Auto Completion

You can enable autocompletion if running kcli from package or pip. It's enabled by default when running kclishell container alias

## Bash/Zsh

Add the following line in one of your shell files (.bashrc, .zshrc, ...)

```
eval "$(register-python-argcomplete kcli)"
```

## Fish

Add the following snippet in *.config/fish/config.fish*
```
function __fish_kcli_complete
    set -x _ARGCOMPLETE 1
    set -x _ARGCOMPLETE_IFS \n
    set -x _ARGCOMPLETE_SUPPRESS_SPACE 1
    set -x _ARGCOMPLETE_SHELL fish
    set -x COMP_LINE (commandline -p)
    set -x COMP_POINT (string length (commandline -cp))
    set -x COMP_TYPE
    if set -q _ARC_DEBUG
        kcli 8>&1 9>&2 1>/dev/null 2>&1
    else
        kcli 8>&1 9>&2 1>&9 2>&1
    end
end
complete -c kcli -f -a '(__fish_kcli_complete)'
```

# Api Usage

You can also use kvirt library directly, without the client or to embed it into your own application.

Here's a sample:

```
from kvirt.config import Kconfig
config = Kconfig()
k = config.k
```

You can then either use config for high level actions or the more low level *k* object.
