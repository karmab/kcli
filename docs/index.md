# About

This tool is meant to provide a unified user experience when interacting with the following virtualization providers:

- Libvirt
- Vsphere
- Kubevirt
- Aws
- Azure
- Gcp
- Hcloud
- Ibmcloud
- oVirt
- Openstack
- Proxmox

Beyond handling virtual machines, Kubernetes clusters can also be managed for the following types:

- Kubeadm
- Openshift
- OKD
- Hypershift
- Microshift
- K3S
- RKE2
- AKS
- EKS
- GKE

# Prerequisites

If you don't have Libvirt installed on the target hypervisor, you can use the following command:

```
sudo yum -y install libvirt libvirt-daemon-driver-qemu qemu-kvm tar
sudo usermod -aG qemu,libvirt $(id -un)
sudo newgrp libvirt
sudo systemctl enable --now libvirtd
```

# Installation

## Automated install

A generic script is provided for for installation:

```
curl https://raw.githubusercontent.com/karmab/kcli/main/install.sh | sudo bash
```

It does the following:

- make a guess on which method to use for deployment based on your OS
 - If OS is rhel or debian based, set repo source and install from package
 - Pull and image and set a proper alias if container method is selected
- set bash completion

Regarding of the method, you get latest version.


The following methods are supported for installation and are all updated automatically when new pushes to kcli are made.

- rpm package
- deb package
- container image
- pypi package


## RPM/Deb install

For rhel based OS (*fedora*/*rhel or centos*), you can run this:

```
sudo dnf -y copr enable karmab/kcli
sudo dnf -y install kcli
```

If using a debian based distribution, use this instead:

```
curl -1sLf https://dl.cloudsmith.io/public/karmab/kcli/cfg/setup/bash.deb.sh | sudo -E bash
sudo apt-get update
sudo apt-get -y install python3-kcli
```

The package based version doesn't bundle the dependencies for anything else than Libvirt, so you have to install the extra packages for each additional cloud platforms, which are listed in the *Provider specifics* section.

On Fedora, an additional metapackage named kcli-all (python3-kcli-all in the debian case) that contains dependencies for all the providers.

## Container install

In the commands below, feel free to use docker instead

Pull the latest image:

```
podman pull quay.io/karmab/kcli
```

To run it:

```
podman run --rm karmab/kcli
```

There are several flags you can use for tweaking:

- `--net host` for kcli ssh
- `-v /var/run/libvirt:/var/run/libvirt -v /var/lib/libvirt/images:/var/lib/libvirt/images` if running against a local client.
- `-v  ~/.kcli:/root/.kcli` to use your kcli configuration (and profiles) stored locally.
- `-v ~/.ssh:/root/.ssh` to share your ssh keys. Alternatively, you can store your public and private key in the ~/.kcli directory.
- `--security-opt label=disable` if running with selinux.
- `-v $PWD:/workdir` to access plans below your current directory.
- `-v $HOME:/root` to share your entire home directory, useful if you want to share secret files, `~/register.sh` for instance).
- `-e HTTP_PROXY=your_proxy -e HTTPS_PROXY=your_proxy`
- `-v ~/.kube:/root/.kube` to share your kubeconfig.
- `-v /etc:/etcdir` to share your /etc directory, which is needed for `reservehost`.

For accessing kweb, change the entrypoint and map port 9000 with `-p 9000:9000 --entrypoint=/usr/bin/kweb`.

Here are typical aliases ready for use:

```
alias kcli='podman run --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir quay.io/karmab/kcli'
alias kclishell='podman run --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir --entrypoint=/bin/bash quay.io/karmab/kcli'
alias kweb='podman run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir --entrypoint=/usr/bin/kweb quay.io/karmab/kcli'
```

- The container image contains dependencies for all the providers.
- The console/serial console functionality works better with the package version. In container mode, the graphical console/serial console only outputs the command to launch manually to get to the console.

## Dev installation

If only Libvirt provider is to be used:

```
pip3 install kcli
```

Or, for installing dependencies for all providers:

```
pip3 install -e git+https://github.com/karmab/kcli.git#egg=kcli[all]
```

# Configuration

## Libvirt additional configuration

If you plan to use local Libvirt, *no additional configuration* is needed.

On most distributions, default network and storage pool for Libvirt are already defined.

If needed, you can create this default storage pool with:

```
sudo kcli create pool -p /var/lib/libvirt/images default
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images
```

And default network:

```
kcli create network  -c 192.168.122.0/24 default
```


## Configuration file

Kcli configuration is done in ~/.kcli directory, that you need to manually create. It will contain:

- config.yml generic configuration where you declare clients.
- profiles.yml stores your profiles where you combine things like memory, numcpus and all supported parameters into named profiles to create vms from.
- Optionally a valid ssh key pair. You can store your default public and private keys in *.kcli* directory which will be the first place to look for them when connecting to a remote kvm hypervisor, virtual machine or when injecting your public key.

You can generate a default config file (with all parameters commented) pointing to your local host with:

```Shell
kcli create host kvm -H 127.0.0.1 local
```

Or indicate a different target host:

```Shell
kcli create host kvm -H 192.168.0.6 host1
```

Here's a sample `~/.kcli/config.yml` with two hypervisors:

```YAML
default:
 client: provider1
 pool: default
 numcpus: 2
 memory: 1024
 disks:
  - size: 10
 protocol: ssh
 nets:
  - default

provider1:
 host: 192.168.0.6
 pool: default

provider2:
 host: 192.168.0.4
 pool: whatever
```

Replace with your own client in default section and indicate the relevant parameters in the corresponding client section, depending on your client/host type.

Most of the parameters are actually optional, and can be overridden in the default, client or profile section (or in a plan file).
You can find a fully detailed config.yml sample [here](https://github.com/karmab/kcli/tree/main/samples/config.yml)


## Provider specifics

### Aws provider

```
aws:
 type: aws
 access_key_id: AKAAAAAAAAAAAAA
 access_key_secret: xxxxxxxxxxyyyyyyyy
 region: eu-west-3
 keypair: mykey
```

The following parameters are specific to aws:

- `access_key_id`
- `access_key_secret`
- `region`
- `zone` (Optional)
- `keypair`
- `session_token`

To use this provider with kcli rpm, you'll need to install

```
dnf -y install python3-boto3
```

see [AWS EKS workflow](https://github.com/karmab/kcli/blob/main/docs/EKS-kcli.md) for an example process

### Azure provider

```
azure:
 type: azure
 subscription_id: AKAAAAAAAAAAAAA
 app_id: AKAAAAAAAAAAAAA
 tenant_id: AKAAAAAAAAAAAAA
 secret: xxxxxxxxxxyyyyyyyy
 location: westus
```

The following parameters are specific to azure:

- `subscription_id`
- `app_id`
- `tenant_id`
- `secret`
- `location`
- `admin_user`. Defaults to superadmin
- `admin_password`. If specified, it need to be compliant with azure policy. When missing, a random one is generated (and printed) for each vm
- `mail`. Optional, used only to access serial console of vms.
- `storage_account`. Optional, used for bucket related operations.

The policy for password states that a valid password needs to satisfy at least 3 of the following requirements:

- contain an uppercase character.
- contain a lowercase character.
- contain a numeric digit.
- contain a special character.
- not contain control characters.

You can create a service principal using Azure UI and add Contributor (and Storage Blob Data Contributor) role from there, or using az command like this:

```
az ad sp create-for-rbac --role Contributor --name openshift-install --scope /subscriptions/${SUBSCRIPTION}
az ad sp create-for-rbac --role "Storage Blob Data Contributor" --name openshift-install --scope /subscriptions/${SUBSCRIPTION}
```

To use this provider, you'll need to install (from pip):

```
pip3 install azure-mgmt-compute azure-mgmt-network azure-mgmt-resource azure-mgmt-core azure-identity
```

### Gcp provider

```
gcp1:
 type: gcp
 credentials: ~/myproject.json
 project: myproject
 region: europe-west1
```

The following parameters are specific to Gcp:

- `credentials` (pointing to a json service account file). if not specified, the environment variable *GOOGLE_APPLICATION_CREDENTIALS* will be used
- `project`
- `region`
- `zone` (Optional)

also note that Gcp provider supports creation of dns records for an existing domain and that your home public key will be uploaded if needed

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

To use this provider, you'll need to install (from pip):

```
pip3 install google-api-python-client google-auth-httplib2 google-cloud-dns
```

If you want to deploy GKE clusters, you will also need `google-cloud-container` library

### Hetzner Cloud provider

```
myhetzner:
  type: hcloud
  apikey: xxxx
  location: eu-gb
```

The following parameters are specific to hetzner cloud:

- apikey.
- location

To use this provider with kcli rpm, you'll need to install the following packets (from pip):

```
pip3 install hcloud
```

### IBM Cloud provider

```
myibm:
  type: ibm
  iam_api_key: xxxx
  region: eu-gb
  zone: eu-gb-2
  vpc: pruebak
```

The following parameters are specific to ibm cloud:

- iam_api_key.
- region
- zone
- vpc. Default vpc
- cos_api_key. Optional Cloud object storage apikey
- cos_resource_instance_id. Optional Cloud object storage resource_instance_id (something like "crn:v1:bluemix:public:cloud-object-storage:global:a/yyy:xxxx::"). Alternatively you can provide the resource name
- cos_resource_instance_id. Optional Cis resource_instance_id used for DNS. Alternatively, you can provide the resource name

To use this provider with kcli rpm, you'll need to install the following packets (from pip):

```
pip3 install ibm_vpc ibm-cos-sdk ibm-platform-services ibm-cloud-networking-services cos-aspera
```

### KVM/Libvirt provider

```
twix:
 type: kvm
 host: 192.168.1.6
```

Without configuration, Libvirt provider tries to connect locally using qemu:///system.

Additionally, remote hypervisors can be configured by indicating either a host, a port and protocol or a custom qemu url.

When using the host, port and protocol combination, default protocol uses ssh and as such assumes you are able to connect without password to your remote instance.

If using tcp protocol instead, you will need to configure Libvirtd in your remote Libvirt hypervisor to accept insecure remote connections.

You will also likely want to indicate default Libvirt pool to use (although, as with any parameter, it can be done in the default section).

The following parameters are specific to Libvirt:

- `url` custom qemu uri.
- `session` Defaults to `False` If you want to use qemu:///session (locally or remotely). Not recommended as it complicates access to the vm and is said to have lower performance.
- `legacy` Defaults to `False`. Add extra socket information to libvirt uri as needed on some old hypervisors.

### Kubevirt provider

For Kubevirt, you will need to define one (or several) sections with the type Kubevirt in your *~/.kcli/config.yml*

```
kubevirt:
 type: kubevirt
 kubeconfig: _path_to_kubeconfig
```

You can use additional parameters for the Kubevirt section:

- `kubeconfig` kubeconfig file path
- `context` the k8s context to use.
- `pool` your default storageclass. can also be set as blank, if no storage class should try to bind pvcs.
- `namespace` target namespace.
- `tags` additional list of tags in a key=value format to put to all created vms in their *nodeSelector*. Can be further indicated at profile or plan level in which case values are combined. This provides an easy way to force vms to run on specific nodes, by matching labels.
- `access_mode` Way to access vms other ssh. Defaults to NodePort,in which case a svc with a nodeport pointing to the ssh port of the vm will be created. Otherpossible values are LoadBalancer to create a svc of type loadbalancer to point to the vm or External to connect using the sdn ip of the vm. If tunnel options are set, they take precedence
- `volume_mode` Volume Mode. Defaults to None
- `volume_access` Volume access mode. Defaults to None
- `disk_hotplug` Whether to allow to hotplug (and unplug) disks. Defaults to false. Note it also requires to enable The HotplugVolumes featureGate within Kubevirt
- `embed_userdata` Whether to embed userdata directly in the vm spec. Defaults to false
- `registry` Specific registry where to gather karmab/curl image used when pool/sc has a volume binding mode of WaitForFirstConsumer. Defaults to quay.io

You can use the following indications to gather context, create a suitable service account and retrieve its associated token:

To list the context at your disposal
```
kubectl config view -o jsonpath='{.contexts[*].name}'
```

To create a service account and give it privileges to handle vms on a given namespace,

```
SERVICEACCOUNT=kcli
NAMESPACE=default
kubectl create serviceaccount $SERVICEACCOUNT -n $NAMESPACE
kubectl create rolebinding $SERVICEACCOUNT --clusterrole=admin --user=system:serviceaccount:$NAMESPACE:$SERVICEACCOUNT
```

To gather a token (in /tmp/token):

```
SERVICEACCOUNT=kcli
NAMESPACE=default
SECRET=`kubectl get sa $SERVICEACCOUNT -n $NAMESPACE -o jsonpath={.secrets[0].name}`
kubectl get secret $SECRET -n $NAMESPACE -o jsonpath={.data.token} | base64 -d
```

You can then shape a kubeconfig providing data as in this sample

```
apiVersion: v1
clusters:
- cluster:
    insecure-skip-tls-verify: true
    server: https://${SERVER}:6443
  name: sa
contexts:
- context:
    cluster: sa
    namespace: ${NAMESPACE}
    user: sa
  name: sa
current-context: sa
kind: Config
preferences: {}
users:
- name: sa
  user:
    token: ${TOKEN}
```

On OpenShift, you can simply use

```
oc whoami -t
```

*kubectl* (or *oc*) is the only requirement

### Openstack provider

```
myopenstack:
 type: openstack
 user: testk
 password: testk
 project: testk
 domain: Default
 auth_url: http://openstack:5000/v3
 ca_file: ~/ca-trust.crt
```

The following parameters are specific to openstack:

- `envrc` (Optional) Path to an envrc file
- `auth_type` (Optional). Indicates the type of authentication to use. Will auto detect based on parameters when empty. Values: `token`, `password`, `v3applicationcredential`.
- `auth_url`
- `project`
- `domain` Defaults to *Default*
- `ca_file` (Optional). Certificate file
- `external_network` (Optional). Indicates which network use for floating ips (useful when you have several ones)
- `region_name` (Optional). Used in OVH Openstack
- `glance_disk` (Optional). Prevents creating a disk from glance image. Defaults to false
- `token` (Optional). Keystone Token (That can be retrieved with `openstack token issue -c id -f value`)

To use this provider with kcli rpm, you'll need to install the following rpms

```
grep -q 'Red Hat' /etc/redhat-release && subscription-manager repos --enable openstack-16-tools-for-rhel-8-x86_64-rpms
dnf -y install python3-keystoneclient python3-glanceclient python3-cinderclient python3-neutronclient python3-novaclient python3-swiftclient
```

### oVirt provider

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
```

The following parameters are specific to oVirt:

- `org` Organization
- `ca_file` Points to a local path with the cert of the oVirt engine host. It can be retrieved with
`curl "http://$HOST/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA" > ~/.kcli/ovirt.pem`
- `cluster`  Defaults to Default
- `datacenter` Defaults to Default
- `filtervms` Defaults to True. Only list vms created by kcli.
- `filteruser` Defaults to False. Only list vms created by own user
- `filtertag` Defaults to None. Only list vms created by kcli with the corresponding filter=filtertag in their description. Useful for environments when you share the same user

Note that pool in oVirt context refers to storage domain.

To use this provider with kcli rpm, you'll need to install

```
dnf -y install https://resources.ovirt.org/pub/yum-repo/ovirt-release44.rpm
dnf -y install python3-ovirt-engine-sdk4
```

#### Deploying oVirt dependencies with pip

You will need to get *ovirt-engine-sdk-python* . On fedora, for instance, you would run:

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

### Proxmox provider

```
myproxmox:
 type: proxmox
 host: pve.karmalabs.corp
 user: root@pam
 password: mypassword
 pool: local
```

The following parameters are specific to proxmox:

- `auth_token_name` and `auth_token_secret` (Optional). API Token used for authentification instead of password.
- `filtertag` (Optional). Only manage VMs created by kcli with the corresponding tag.
- `node` (Optional). Create VMs on specified PVE node in case of Proxmox cluster.
- `imagepool` (Optional). Storage pool for images and ISOs.
- `verify_ssl` (Optional). Enable/Disable SSL verification. Default to True.

Note that uploading images and cloud-init/ignition files requires ssh access to the Proxmox host. It's highly recommended to configure passwordless ssh authentification.

To use this provider with kcli rpm, you'll need to install the following rpms

```
pip3 install proxmoxer
```

### Vsphere provider

```
myvsphere:
 type: vsphere
 host: xxx-vcsa67.vcenter.e2e.karmalabs.corp
 user: administrator@karmalabs.corp
 password: mypassword
 datacenter: Madrid
 cluster: mycluster
 pool: mysuperdatastore
```

The following parameters are specific to Vsphere:

- `cluster`
- `datacenter` Defaults to Default
- `filtervms` Defaults to False. Only list vms created by kcli. Useful for environments when you are superadmin and have a ton of vms!!!
- `category` Defaults to kcli. Category where to create tags in order to apply them to vms. If tags are requested for a given vm, they will be created on the fly along with the category, if missing
- `basefolder` Optional base folder where to create all vms
- `isofolder` Optional folder where to keep ISOs
- `dvs` Whether to gather DVS networks. Enabled by default, but can be set to False to speed up operations if you don't have dvs networks
- `import_network` Defaults to 'VM Network'. Network to use as part of the template created when downloading image
- `timeout` Defaults to 3600. Custom connectionPooltimeout
- `force_pool` Defaults to False. Whether to check source pool of image and relocate when it doesn't match specified pool
- `restricted` Defaults to False. Prevents create folder operations
- `serial` Defaults to False. Enables serial console for each vm using an aleatory port on the corresponding host (This requires to add the firewall rule set named *VM serial port connected over network*)

Note that pool in Vsphere context refers to datastore.

To use this provider with kcli rpm, you'll need to install

```
dnf -y install python3-pyvmomi python3-cryptography
```

#### Using a standalone ESX

For an esx, a couple of adjustments are needed.
The cluster should point to the hostname of the esx and the keys datacenter, pools and user have fixed values.

```
myesx:
  type: vsphere
  host: 10.6.118.114
  user: root
  password: mypassword
  datacenter: ha-datacenter
  pool: datastore1
  cluster: superesx
```

#### Using hostgroups and vm-host rules

The prerequisite is to create the hostgroup by yourself so that you can associate your hosts to it.

Then, when creating a vm, one can provide the following extra parameters:

* vmgroup: if it doesn't exist, the group will be created and in any case, the vm will get added to it.

* hostgroup and hostrule: if both are provided and the hostrule doesnt exist, it will be created as affinity rule with the vmgroup and the hostgroup to it.

Note that when using this within a plan (or a cluster), it's enough to provide hostgroup and hostrule for the first vm of the plan so that the hostrule gets created ( though a kcli vmrule for instance), and vmgroup for all of them, so that the group gets created with the first vm, and then the remaining vm only get added.

Also note that vmgroups and hostrules dont get deleted along with vms (to ease recreation of the same assets).

#### Using vm anti affinity rules

Within a plan, you can set the keyword `antipeers` to a list of vms which should never land on the same ESX host.
When the last vm from this list gets created, the corresponding anti affinity rule will be created (and Vsphere will relocate the other vms accordingly)

### Web

This provider allows you to interact with a kweb instance using kcli commands

```
myweb:
 type: web
 host: 127.0.0.1
 port: 8000
```

The following parameters are specific to the web provider:

- `localkube`. Defaults to true. Use REST calls when handling kubes


## Storing credentials securely

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

## Auto Completion

You can enable autocompletion if running kcli from package or pip.

Add the following line in one of your shell files (.bashrc, .zshrc, ...)

```
eval "$(register-python-argcomplete kcli)"
```

With fish, add the following snippet in *.config/fish/config.fish*

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

# Usage

## Creating a vm

Cloud Images from common distros aim to be the primary source for your vms.

You can list available cloud images ready for downloading with

```Shell
kcli list available-images
```

*kcli download image* can be used to download a specific cloud image. for instance, centos9:

```Shell
kcli download image centos9stream
```

At this point, you can deploy vms directly from the image, using default settings for the vm:

```Shell
kcli create vm -i centos9stream vm1
```

This create a vm with 2 numcpus and 512Mb of ram, and also inject your public key using cloudinit.

The resulting vm can be accessed using *kcli ssh vm1*.

Kcli uses the default ssh_user associated to the [cloud image](http://docs.openstack.org/image-guide/obtain-images.html).

To guess it, kcli checks the image name. So for example, your centos image must contain the term "centos" in the file name,
otherwise "root" is used.

For out of band access to the vm, `kcli console` or `kcli console --serial` can be used

## Customizing a vm

Using parameters, you can tweak the vm creation. A full list of keywords can be used.

You can use the following to get a list of available keywords, and their default value

```Shell
kcli get keywords
```

When creating a vm, you can then combine any of those keywords

```Shell
kcli create vm -P keyword1=value1 -P keyword2=value2 -P keyword2=value3 (....)
```

Note that those parameters dont have to be only keyword. You can pass any key-value pair so that they are used when injecting files or commands.

### Cpus and Memory

Using such parameters, you can tweak the vm creation. For instance, the following customizes the number of cpus and memory of the vm.

```Shell
kcli create vm -i centos9stream -P memory=2048 -P numcpus=4 vm1
```

### Disks

You can also pass `disks`. For instance to create a vm with 2 disks

```Shell
kcli create vm -i centos9stream -P disks=[10,20] vm1
```

The disks keyword can either be a list of integers or we can pass a list of dictionaries to tweak even further. For instance, we can set the disk interface of one of the disk so that it uses SATA

```Shell
kcli create vm -i centos9stream -P disks=['{"size": 10, "interface": "sata"}'] vm1
```

You can combine both syntaxes, as shown in the next example where we create a 2-disks vm where the second one is SATA

```Shell
kcli create vm -i centos9stream -P disks=['20,{"size": 10, "interface": "sata"}'] vm1
```

### Nets

`nets` keyword allows you to create vms with several nics and using specific networks. For instance, we can create a vm with two nics connected to the default network

```Shell
kcli create vm -i centos9stream -P nets=[default,default] vm1
```

As with disks, we can tweak even further, for instance, to force the mac address of the vm

```Shell
kcli create vm -i centos9stream -P nets=['{"name": "default", "mac": "aa:aa:aa:bb:bb:90"}'] vm1
```

Or change the nic driver

```Shell
kcli create vm -i centos9stream -P nets=['{"name": "default", "type": "e1000"}'] vm1
```

Again, both syntaxes can be combined

It is also possible to leverage user mode networking with a couple of plugins, `slirp` and `passt`, and you can ssh into them
```Shell
kcli create vm -i centos9stream -P usermode=true -P usermode_backend=slirp vm-slirp
kcli create vm -i centos9stream -P usermode=true -P usermode_backend=passt vm-passt
```

### Injecting files

You can inject a list of `files` in your vms. For instance, to inject a file named myfile.txt, use

```Shell
kcli create vm -i centos9stream -P files=[myfile.txt] vm1
```

The corresponding file will be located in /root

Note that this file gets rendered first through jinja, by using any of the parameter provided in the command line.

For instance, if myfile.txt contains:

```
Welcome to the box {{ mybox }}
```

When we launch `kcli create vm -i centos9stream -P files=[myfile.txt] -P mybox=superbox`, the myfile.txt ends up with the following content:

```
Welcome to the box superbox
```

By using jinja constructs (whether variables, conditional or loops), we can customize completely the resulting vm

Of course, we might not want all files to end up in /root. By using a more accurate spec in our files section, we can indicate where to create the file

```Shell
kcli create vm -i centos9stream -P files=['{"path": "/etc/motd", "origin": "myfile.txt"}']
```

We can also set a specific mode for the file

```Shell
kcli create vm -i centos9stream -P files=['{"path": "/etc/motd", "origin": "myfile.txt", "mode": "644}']
```

### Injecting cmds and scripts

You can inject a list of `cmds` in your vms. For instance, to install a specific package use

```Shell
kcli create vm -i centos9stream -P cmds=['yum -y install nc'] vm1
```

Alternatively, you can use the keyword `scripts` to inject a list of script files from you current directory

```Shell
kcli create vm -i centos9stream -P scripts=[myscript.sh]  vm1
```

This has the benefit that the scripts get rendered via jinja in the same way as files do, by leveraging additional parameters provided in the command line

As always, both cmds and scripts can be specified, in which case cmds are run first.

### Creating empty vms

So far, our examples have used a cloud image via the `-i/--image` flag but it's not mandatory. For instance, we can create an empty vm with a complete spec

```Shell
kcli create vm -P uefi=true -P start=false -P memory=20480 -P numcpus=16 -P disks=[50,50] -P nets=[default] myvm
```

Note that when not using a cloud image, cloudinit/ignition wont be used.

## Using Profiles

Instead of providing parameters on the command line, you can use profiles.

Profiles are meant to help creating single vm with preconfigured settings (number of CPUS, memory, size of disk, network, which image to use, extra commands to run on start, whether reserving dns,....)

You use the file *~/.kcli/profiles.yml* to declare your profiles. Here's a snippet declaring a profile named `mycentos`:

```
mycentos:
 image: centos9stream
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

You can inherit settings from a base profile like this

```
profile2:
 base: profile1
```

## Cloudinit/Ignition support

Cloudinit is enabled by default and handles static networking configuration, hostname setting, injecting ssh keys and running specific commands and entire scripts, and copying entire files.

For vms based on coreos, ignition is used instead of cloudinit although the syntax is the same. If $name.ign or $plan.ign are found in the current directory, their content will be merged. The extension .cloudinit does the same for cloudinit.

To ease OpenShift deployment, when a node has a name in the \$cluster-role-\$num, where role can either be ctlplane, worker or bootstrap, additional paths are searched, namely:

* \$cluster-\$role.ign
* clusters/\$cluster/\$role.ign
* \$HOME/.kcli/clusters/\$cluster/\$role.ign

For ignition support on oVirt, you will need a version of ovirt >= 4.3.4


## Interacting with vms

Although the primary goal of kcli is to ease creation of vms, the tool is meant to make it easy to interact with the provider beyond that.

The following commands are typically used when dealing with vms

- List vms
  - `kcli list vm`
- List install images
  - `kcli list images `
- Delete vm
  - `kcli delete vm vm1`
- Get detailed info on a specific vm
  - `kcli info vm vm1`
- Start vm
  - `kcli start vm vm1`
- Stop vm
  - `kcli stop vm vm1`
- Get remote-viewer console
  - `kcli console vm vm1`
- Get serial console (over TCP). Requires the vms to have been created with kcli and netcat client installed on hypervisor
  - `kcli console vm -s vm1`
- Add 5GB disk to vm1, using pool named images
  - `kcli create vm-disk -s 5 -p images vm1`
- Delete disk named vm1_2.img from vm1
  - `kcli delete disk --vm vm1 vm1_2.img`
- Update memory in vm1 to 2GB memory
  - `kcli update vm -P memory=2048 vm1`
- Clone vm1 to new vm2
  - `kcli clone -b vm1 vm2`
- Connect with ssh to vm vm1
  - `kcli ssh vm1`
- Add a new nic from network default to vm1
  - `kcli create nic -n default vm1`
- Delete nic eth2 from vm
  - `kcli delete nic -i eth2 vm1`
- Create snapshot named snap1 for vm1:
  - `kcli create snapshot vm -n vm1 snap1`
- Export vm:
  - `kcli export vm vm1`

We can interact using the same constructs with other objects, such as network or (storage) pool

- Create a new network
  - `kcli create network -c 192.168.7.0/24 mynet`
- Create new pool
  - `kcli create pool -p /home/images images`

## Omitting vm's name

When you don't specify a vm, the last one created by kcli on the corresponding client is used (the list is stored in *~/.kcli/vm*)

So for instance, you can simply use the following command to access your last vm:

`kcli ssh`

## Using multiple providers

If you have multiple providers, you can generally use the flag *-C $CLIENT* to point to a specific one

You can also use the following to list the vms of all your hosts/clients:

`kcli -C all list vm`

## Using plans

a *plan* is a file in yaml with a list of profiles, vms, disks, and networks and vms to deploy.

The following types can be used within a plan:

- vm (this is the type used when none is specified)
- image
- network
- disk
- pool
- profile
- ansible
- container
- dns
- plan (so you can compose plans from several urls)
- kube
- workflow

### Create a plan

Here's a basic plan to get a feel of plan's logic

```
vm1:
 image: centos9stream
 numcpus: 8
 memory: 2048
 files:
 - path: /etc/motd
   content: Welcome to the cruel world

vm2:
 image: centos9stream
 numcpus: 8
 memory: 2048
 cmds:
 - yum -y install httpd
```

To run this plan, we save it as `myplan.yml` and we can then deploy it using `kcli create plan -f myplan.yml`

This will create two vms based on the centos9stream cloud image, with the specified hardware characteristics and injecting a specific file for vm1, or running a command to install httpd for vm2.

Additionally, your ssh public key gets automatically injected to the node, and the hostname of those vms get set, all through cloudinit.

Although this is a simple plan, note that:

- it's expected to behave exactly the same regardless of your target virtualization platform
- can be relaunched in an idempotent manner

### Use variables with a plan

Let's modify our plan to make it more dynamic

```
parameters:
 image: centos9stream
 numcpus: 8
 memory: 2048
 packages:
 - httpd
 motd: Welcome to the cruel world

vm1:
 image: {{ image }}
 numcpus: {{ numcpus }}
 memory: {{ memory }}
 files:
 - path: /etc/motd
   content: {{ motd }}

vm2:
 image: {{ image }}
 numcpus: {{ numcpus }}
 memory: {{ memory }}
 cmds:
{% for package in packages %}
 - yum -y install {{ package }}
{% endfor %}
```

This looks similar to the first example, but now we have a parameters section where we define default values for a set of variables that is then used within the plan, through jinja.

When creating the plan, any of those parameter can be overriden by using `-P key=value`, or providing a parameter file.

For instance, we would run `kcli create plan -f my_plan.yml -P numcpus=16 -P memory=4096 -P motd="Welcome to the cool world` to create the two same vms with different hardware values and with a custom motd in vm1

Note that any jinja construct can be used within a plan (or through the files or the scripts referenced by said plan)

### plan types

Here are some examples of each type (more examples can be found in the [samples repo ](https://github.com/karmab/kcli-plan-samples)):

#### cluster

```YAML
mycluster:
  type: cluster
  kubetype: openshift
  okd: true
  ctlplanes: 3
  workers: 3
```

Possible `kubetypes` are `openshift`, `generic`, `microshift`, `aks`, `eks`, `gke`, `hypershift`, `k3s` and `rke2`.


#### container

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

- *image* name of the image to pull.
- *cmd* command to run within the container.
- *ports* array of ports to map between host and container.
- *volumes* array of volumes to map between host and container. You can alternatively use the keyword *disks*. You can also use more complex information provided as a hash

Within a volumes section, you can use path, origin, destination and mode as keys. mode can either be rw o ro and when origin or destination are missing, path is used and the same path is used for origin and destination of the volume. You can also use this typical docker syntax:

```YAML
volumes:
 - /home/cocorico:/root/cocorico
```

Also, note that basic commands ( start, stop, console, plan, list) accept a *--container* flag.

#### disk

```YAML
share1.img:
 type: disk
 size: 5
 pool: vms
 vms:
  - centos1
  - centos2
```

Here the disk is shared between two vms (that typically would be defined within the same plan)

#### dns

```YAML
yyy:
 type: dns
 net: default
 ip: 192.168.1.35
```

#### image

```YAML
centos7:
 type: image
 url: http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
```

If you point to an url not ending in qcow2/qc2 (or img), your browser will be opened for you to proceed.
Also note that you can specify a command with the *cmd* key, so that virt-customize is used on the image once it's downloaded.


#### network

```YAML
mynet:
 type: network
 cidr: 192.168.95.0/24
```
You can also use the boolean keyword *dhcp* (mostly to disable it) and isolated . When not specified, dhcp and nat will be enabled


#### plan's plan

```YAML
ovirt:
  type: plan
  url: github.com/karmab/kcli-plans/ovirt/upstream.yml
  run: true
```

You can alternatively provide a file attribute instead of url pointing to a local plan file:


#### pool

```YAML
mypool:
  type: pool
  path: /home/mypool
```

#### profile

```YAML
myprofile:
  type: profile
  image: centos9stream
  memory: 3072
  numcpus: 1
  disks:
   - size: 15
   - size: 12
  nets:
   - default
  pool: default
```

#### vms
You can point at an existing profile in your plans, define all parameters for the vms, or combine both approaches. You can even add your own profile definitions in the plan file and reference them within the same plan:

```YAML
big:
  type: profile
  image: centos9stream
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

The [kcli-plan-samples repo](https://github.com/karmab/kcli-plan-samples) contains samples to get you started. You will also find under karmab user dedicated plan repos to deploy oVirt, Openstack, ...

When launching a plan, the plan name is optional. If none is provided, a random one will be used.

If no plan file is specified with the -f flag, the file `kcli_plan.yml` in the current directory will be used.

When deleting a plan, the network of the vms will also be deleted if no other vm are using them. You can prevent this by setting *keepnetworks* to `true` in your configuration.

#### workflow

Workflow allows you to launch scripts locally after they are rendered

```YAML
myworkflow:
  type: workflow
  scripts:
  - frout.sh
  - prout.py
  files:
  - frout.txt
```

This would execute the two scripts after rendering them into a temporary directory, along with the files if provided.
Note that you can omit the scripts section and instead indicate the script to run as name of the workflow. This requires it to be a sh/bash script and as such being suffixed by .sh

By default `files` items are rendered directly in the `/root` directory with the same directory structure as the original files, and `scripts` items are rendered in a temporary directory.  For example:

```YAML
myworkflow:
  type: workflow
  scripts:
  - arch/frout.sh
  files:
  - arch/frout.txt
  - arch/template/frout.j2
```

Will create files similar to this:

```
/tmp/tmpfiox_arx/frout.sh
/root/arch/frout.txt
/root/arch/template/frout.j2
```

There is an optional field called `destdir` that we can use to force the destination directory, so that:

```YAML
myworkflow:
  type: workflow
  destdir: outdir
  scripts:
  - arch/frout.sh
  files:
  - arch/frout.txt
  - arch/template/frout.j2
```

Will create the following file structure:

```
./outdir/frout.sh
./outdir/arch/frout.txt
./outdir/arch/template/frout.j2
```

Additionally elements from `files` can use a mapping instead of a string to specify the destination directories of the files:

```YAML
myworkflow:
  type: workflow
  destdir: outdir
  scripts:
  - arch/frout.sh
  files:
  - origin: arch/frout.txt
    path: ./outdir/frout.txt
  - origin: arch/template/frout.j2
    path: ./outdir/frout.j2
```

Will create the following file structure:

```
./outdir/frout.sh
./outdir/frout.txt
./outdir/frout.j2
```

When using a directory in a `files` section the structure will be recreated and all files within it will be rendered.

If we have this file structure:

```
./arch/frout.sh
./arch/frout.txt
./arch/frout.j2
./arch/subdir/anotherfile.sh
```

And we use this workflow:

```YAML
myworkflow:
  type: workflow
  destdir: outdir
  scripts:
  - arch/frout.sh
  files:
  - origin: arch
```

We'll end up with the following:

```
./outdir/frout.sh
./outdir/arch/frout.txt
./outdir/arch/frout.j2
./outdir/arch/subdir/anotherfile.sh
```

## Remote plans

You can use the following command to execute a plan from a remote url:

```YAML
kcli create plan --url https://raw.githubusercontent.com/karmab/kcli-plan-samples/main/simpleplan.yml
```
## Typical parameters

Disk and Network related parameters are detailed below as they are commonly used as part of profile or plans.

### Disk parameters

You can add disk this way in your profile or plan files:

```YAML
disks:
 - size: 20
   pool: default
 - size: 10
   thin: False
   interface: scsi
```

Within a disk section, you can use the word size, thin and format as keys.

- *thin* Value used when not specified in the disk entry. Defaults to true
- *interface* Value used when not specified in the disk entry. Defaults to virtio. Could also be scsi, sata or ide, if vm lacks virtio drivers

### Network parameters

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

You can also use  *noconf: true* to only add the nic with no configuration done in the vm.

the *ovs: true* allows you to create the nic as ovs port of the indicated bridge. Not that such bridges have to be created independently at the moment

You can also provide network configuration on the command line when creating a single vm with something like:

```
kcli create vm -i $img -P nets=['{"name":"default","ip":"192.168.122.250","netmask":"24","gateway":"192.168.122.1"}']
```

### ip, dns and host Reservations

If you set *reserveip*  to True, a reservation will be made if the corresponding network has dhcp and when the provided ip belongs to the network range. Note providing such ip is mandatory.

You can set *reservedns* to True to create a dns entry for the vm in the corresponding network ( only done for the first nic).

You can set *reservehost* to True to create an entry for the host in /etc/hosts ( only done for the first nic). It's done with sudo and the entry gets removed when you delete the vm. On macosx, you should use gnu-sed ( from brew ) instead of regular sed for proper deletion.

If you dont want to be asked for your sudo password each time, here are the commands that are escalated:

```Shell
 - echo .... # KVIRT >> /etc/hosts
 - sed -i '/.... # KVIRT/d' /etc/hosts
```
`

## Exposing a plan

You can expose a given plan in a web fashion with `kcli expose` so that others can make use of some infrastructure you own without having to deal with kcli themseleves.

The user will be presented with a simple UI (running on port 9000) with a listing of the current vms of the plan and buttons allowing to either get info on the plan, delete or reprovision it.

To expose your plan (with an optional list of parameters):

```
kcli expose plan -f your_plan.yml -P param1=value1 -P param2=value plan_name
```

The indicated parameters are the ones from the plan that you want to expose to the user upon provisioning, with a provided default value that they'll be able to overwrite.

When the user reprovisions, In addition to those parameters, he will be able to specify:

- a list of mail addresses to notify upon completion of the lab provisioning. Note it requires to properly set notifications in your kcli config.
- an optional owner which will be added as metadata to the vms, so that it's easy to know who provisioned a given plan

### Precreating a list of plans

If you’re running the same plan with different parameter files, you can simply create files in the directory where your plan lives, naming them parameters_XXX.yml|yaml, and/or in a subdirectory named `paramfiles`. The UI will then show you those as separated plans so that they can be provisioned individually applying the corresponding values from the parameter files (after merging them with the user provided data).

### Using several clients

When specifying different parameter files, you can include the `client` keyword to target a given client
The code will then select the proper client for create/delete/info operations.

### Using expose feature from a web server

You can use mod_wsgi with httpd or similar mechanisms to use the expose feature behind a web server so that you serve content from a specific port or add layer of security like htpasswd provided from outside the code.

For instance, you could create the following kcli.conf in apache

```
<VirtualHost *>
    WSGIScriptAlias / /var/www/kcli.wsgi
    <Directory /var/www/kcli>
        Order deny,allow
        Allow from all
    </Directory>
</VirtualHost>
```

the file kcli.wsgi would contain the following python code:

```
import logging
import os
import sys
from kvirt.config import Kconfig
from kvirt.expose import Kexposer
logging.basicConfig(stream=sys.stdout)

os.environ['HOME'] = '/usr/share/httpd'
inputfile = '/var/www/myplans/plan1.yml'
overrides = {'param1': 'jimi_hendrix', 'param2': False}
config = Kconfig()
kexposer = Kexposer(config, 'myplan', inputfile, overrides=overrides)
application = kexposer.app
application.secret_key = 'XXX'
```

### Calling expose endpoints through REST

the [swagger spec](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/karmab/kcli/main/kvirt/expose/swagger.yml) indicates the available endpoints.

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

Note that parameters provided as uppercase are made environment variables within the target vm by creating `/etc/profile.d/kcli.sh`

The indicated objects are then rendered using jinja.

```
centos:
 image: centos9stream
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
 image: centos9stre<m
 cmds:
  - echo x={{ x }} y={{ y }} >> /tmp/cocorico.txt
  - echo {{ password  }} | passwd --stdin root
```

Finally note that you can also use advanced jinja constructs like conditionals and so on. For instance:

```
parameters:
  net1: default
vm4:
  image: centos9stream
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

# Keyword Parameters

We provide a complete list of parameters

## Specific parameters for a provider

|Parameter      |Default Value|Comments|
|---------------|-------------|--------|
|*host*         |127.0.0.1||
|*port*         ||Defaults to 22 if ssh protocol is used|
|*user*         |root||
|*protocol*     |ssh||
|*url*          || can be used to specify an exotic qemu url|
|*tunnel*       |False|make kcli use tunnels for console and for ssh access|
|*keep_networks*|False|make kcli keeps networks when deleting plan|

## Available parameters for provider/profile/plan files

|Parameter                 |Default Value                                |Comments|
|--------------------------|---------------------------------------------|--------|
|*client*|None|Allows to target a different client/host for the corresponding entry|
|*virttype*|None|Only used for Libvirt where it evaluates to kvm if acceleration shows in capabilities, or qemu emulation otherwise. If a value is provided, it must be either kvm, qemu, xen or lxc|
|*cpumodel*|host-model||
|*cpuflags*|[]| You can specify a list of strings with features to enable or use dict entries with *name* of the feature and *policy* either set to require,disable, optional or force. The value for vmx is ignored, as it's handled by the nested flag|
|*numcpus*|2||
|*cpuhotplug*|False||
|*numamode*|None|numamode to apply to the workers only.|
|*cpupinning*|[]|cpupinning conf to apply|
|*memory*|512M||
|*memoryhotplug*|False||
|*flavor*|| Specific to gcp, aws and openstack|
|*guestid*|guestrhel764||
|*pool*|default||
|*image*|None|Should point to your base cloud image(optional). You can either specify short name or complete path. If you omit the full path and your image lives in several pools, the one from last (alphabetical) pool will be used\
|*disksize*|10GB||
|*diskinterface*|virtio|You can set it to ide, ssd or nvme instead|
|*diskthin*|True||
|*disks*|[]|Array of disks to define. For each of them, you can specify pool, size, thin (as boolean), interface (either ide or virtio) and a wwn.If you omit parameters, default values will be used from config or profile file (You can actually let the entire entry blank or just indicate a size number directly)|
|*iso*|None||
|*nets*|[]|Array of networks to define. For each of them, you can specify just a string for the name, or a dict containing name, public and alias and ip, mask and gateway, and bridge. Any visible network is valid, in particular bridges or specific interfaces can be used on Libvirt, beyond regular nat networks|
|*gateway*|None||
|*dns*|None|Dns server|
|*domain*|None|Dns search domain|
|*start*|true||
|*vnc*|false|if set to true, vnc is used for console instead of spice|
|*cloudinit*|true||
|*reserveip*|false|if set to true and an ip was provided, create a dhcp reservation in libvirt network|
|*reservedns*|false||
|*reservehost*|false||
|*keys*|[]|Array of ssh public keys to inject to the vm. Whether the actual content or the public key path|
|*cmds*|[]|Array of commands to run|
|*profile*|None|name of one of your profile|
|*scripts*|[]|array of paths of custom script to inject with cloudinit. It will be merged with cmds parameter. You can either specify full paths or relative to where you're running kcli. Only checked in profile or plan file|
|*nested*|True||
|*sharedkey*|False| Share a private/public key between all the nodes of your plan. Additionally, root access will be allowed|
|*privatekey*|False| Inject your private key to the nodes of your plan|
|*files*|[]|Array of files to inject to the vm. For each of them, you can specify path, owner ( root by default) , permissions (600 by default ) and either origin or content to gather content data directly or from specified origin. When specifying a directory as origin, all the files it contains will be parsed and added|
|*insecure*|True|Handles all the ssh option details so you don't get any warnings about man in the middle|
|*client*|None|Allows you to create the vm on a specific client. This field is not used for other types like network|
|*base*|None|Allows you to point to a parent profile so that values are taken from parent when not found in the current profile. Scripts and commands are rather concatenated between default, father and children|
|*tags*|[]|Array of tags to apply to gcp instances (usefull when matched in a firewall rule). In the case of Kubevirt, it s rather a dict of key=value used as node selector (allowing to force vms to be scheduled on a matching node)|
|*networkwait*|0|Delay in seconds before attempting to run further commands, to be used in environments where networking takes more time to come up|
|*rhnregister*|None|Auto registers vms whose image starts with rhel. Defaults to false. Requires to set either rhnuser and rhnpassword, or rhnactivationkey and rhnorg, and an optional rhnpool|
|*rhnunregister*|None|Auto unregisters vms whose image starts with rhel prior to deletion. Defaults to false. Requires to set either rhnuser and rhnpassword, or rhnactivationkey and rhnorg, and an optional rhnpool|
|*rhnserver*|https://subscription.rhsm.redhat.com|Red Hat Network server (for registering to a Satellite server)|
|*rhnuser*|None|Red Hat Network user|
|*rhnpassword*|None|Red Hat Network password|
|*rhnactivationkey*|None|Red Hat Network activation key|
|*rhnorg*|None|Red Hat Network organization|
|*rhnpool*|None|Red Hat Network pool|
|*enableroot*|true|Allows ssh access as root user|
|*rootpassword*|None|Root password to inject (when beeing to lazy to use a cmd to set it)|
|*storemetadata*|false|Creates a /root/.metadata yaml file whith all the overrides applied. On gcp, those overrides are also stored as extra metadata|
|*sharedfolders*|[]|List of paths to share between hypervisor and vm. You will also need to make sure that the path is accessible as qemu user (typically with id 107) and use an hypervisor and a guest with 9p support (centos/rhel lack it for instance)|
|*yamlinventory*|false|Ansible generated inventory for single vms or for plans containing ansible entries will be yaml based.|
|*autostart*|false|Autostarts vm (Libvirt specific)|
|*cmdline*|None|Cmdline to pass to the vm|
|*pcidevices*|[]|array of pcidevices to passthrough to the first worker only. Check [here](https://github.com/karmab/kcli-plan-samples/blob/main/pcipassthrough/pci.yml) for an example|
|*tpm*|false|Enables a TPM device in the vm, using emulator mode. Requires swtpm in the host|
|*rng*|false|Enables a RNG device in the vm|
|*notify*|false|Sends result of a command or a script run from the vm to one of the supported notify engines|
|*notifymethod*|[pushbullet]|Array of notify engines. Other options are slack and mail|
|*notifycmd*|None|Which command to run for notification. If none is provided and no notifyscript either, defaults to sending last 100 lines of the cloudinit file of the machine, or ignition for coreos based vms|
|*notifyscript*|None|Script to execute on the vm and whose output will be sent to notification engines|
|*pushbullettoken*|None|Token to use when notifying through pushbullet|
|*slacktoken*|None|Token to use when notifying through slack. Should be the token of an app generated in your workspace|
|*slackchannel*|None|Slack Channel where to send the notification|
|*mailserver*|None|Mail server where to send the notification (on port 25)|
|*mailfrom*|None|Mail address to send mail from|
|*mailto*|[]|List of mail addresses to send mail to|
|*vmrules*|[]|List of rules with an associated dict to apply for the corresponding entry, if a regex on the entry name is matched. The profile of the matching vm will be updated with the content of the rule|
|*wait*|False|Whether to wait for cloudinit/ignition to fully apply|
|*waitcommand*|None|a specific command to use to validate that vm is ready|
|*waittimeout*|0|Timeout when waiting for a vm to be ready. Default zero value means the wait wont timeout|

You can refer to the sample file [all_parameters.yml](https://github.com/karmab/kcli/blob/main/samples/all_parameters.yml) to see all those parameters in context

# Deploying Kubernetes/OpenShift clusters

You can deploy generic Kubernetes (based on Kubeadm), K3s, OpenShift/OKD, Hypershift, Microshift and GKE on any platform and on an arbitrary number of control plane nodes and workers.

The main benefit is to abstract deployment details to have an unified workflow

- create a parameter file
- launch the deployment oneliner
- enjoy

Other benefits are:

- easy tweaking of vms hardware
- tuning the version to deploy
- support for alternative CNIs
- configuration of static networking for the nodes
- installation of additional applications/operators
- handling of lifecycle after installation:
  - scaling
  - autoscaling
- support for deploying Baremetal workers in Openshift and Hypershift (optionally using Redfish)
- support for deploying Openshift SNOs (optionally using Redfish)

## How to deploy a cluster

For all the platforms, the workflow is the following:

- create a (yaml) parameter file to describe intented end result
- launch the specific subcommand. For instance, to deploy a generic Kubernetes cluster, one would use `kcli create cluster generic --pf my_parameters.yml  $cluster`. Parameter files can be repeated and combined with specific parameters on the command line, which always take precedence.
- Once the installation finishes, set the following environment variable in order to interact with the csluter  `export KUBECONFIG=$HOME/.kcli/clusters/$cluster/auth/kubeconfig`

see [AWS EKS workflow](https://github.com/karmab/kcli/blob/main/docs/EKS-kcli.md) for an example EKS process


## Getting information on available parameters

For each supported platform, you can use `kcli info cluster $clustertype`

For instance, `kcli info cluster generic` will provide you all the parameters available for customization for generic Kubernetes clusters.

## Deploying generic Kubernetes clusters

```
kcli create cluster generic -P ctlplanes=X -P workers=Y $cluster
```

## Deploying OpenShift clusters

*DISCLAIMER*: This is not supported in anyway by Red Hat (although the end result cluster would be).

for OpenShift, the official installer binary is leveraged with kcli creating the vms, and injecting some extra pods to provide api/ingress vip and self contained dns.

The benefits of deploying OpenShift with this workflow are:

- Auto download openshift-install specified version.
- Easy vms tuning.
- Single workflow regardless of the target platform.
- Self contained dns. (For cloud platforms, cloud public dns is leveraged instead)
- For Libvirt, no need to compile installer or tweak Libvirtd.
- Vms can be connected to a physical bridge.
- Multiple clusters can live on the same l2 network.
- Support for disconnected registry and ipv6 networks.
- Support for upstream OKD

### Requirements

- Valid pull secret
- Ssh public key.
- Write access to /etc/hosts file to allow editing of this file.
- An available ip in your vm's network to use as *api_ip*. Make sure it is excluded from your dhcp server. An optional *ingress_ip* can be specified, otherwise api_ip will be used.
- Direct access to the deployed vms. Use something like this otherwise `sshuttle -r your_hypervisor 192.168.122.0/24 -v`).
- Target platform needs:
  - Ignition support
  - On Openstack:
     - swift available on the install.
     - a flavor. You can create a dedicated one with `openstack flavor create --id 6 --ram 32768 --vcpus 16 --disk 30 m1.openshift`
     - a port on target network mapped to a floating ip. If not specified with api_ip and public_api_ip parameters, the second-to-last ip from the network will be used.
- For ipv6, you need to run the following: `sysctl -w net.ipv6.conf.all.accept_ra=2`

### Openshift cluster creation

Prepare a parameter file with valid variables:

A minimal one could be the following one

```
cluster: mycluster
domain: karmalabs.corp
version: stable
tag: '4.12'
ctlplanes: 3
workers: 2
memory: 16384
numcpus: 16
```

Here's the list of typical variables that can be used (you can list them with `kcli info cluster openshift`)

|Parameter              |Default Value                     |Comments|
|-----------------------|----------------------------------|--------|
|cluster                |testk                             ||
|domain                 |karmalabs.corp                    ||For cloud platforms, it should point to a domain name you have access to|
|*version*|stable|You can choose between stable, candidate, nightly, ci or stable. both ci and nightly require specific data in the pull secret|
|tag                    |4.12                               ||
|async                  |false                             |Exit once vms are created and let job in cluster delete bootstrap|
|notify                 |false                             |Whether to send notifications once cluster is deployed. Mean to be used in async mode|
|pull_secret            |openshift_pull.json               ||
|network                |default                           |Any existing network can be used|
|api_ip                 |None                              ||
|ingress_ip             |None                              ||
|ctlplanes              |1                                 |number of ctlplane|
|workers                |0                                 |number of workers|
|network_type           |OVNKubernetes                     ||
|pool                   |default                           ||
|flavor                 |None                              ||
|flavor_bootstrap       |None                              ||
|flavor_ctlplane        |None                              ||
|flavor_worker          |None                              ||
|numcpus                |4                                 ||
|bootstrap_numcpus      |None                              ||
|ctlplane_numcpus       |None                              ||
|worker_numcpus         |None                              ||
|memory                 |8192                              ||
|bootstrap_memory       |None                              ||
|ctlplane_memory        |None                              ||
|worker_memory          |None                              ||
|disk_size              |30                                |disk size in Gb for final nodes|
|extra_disks            |[]                                ||
|disconnected_url       |None                              ||
|disconnected_user      |None                              ||
|disconnected_password  |None                              ||
|imagecontentsources    |[]                                ||
|baremetal              |False                             |Whether to also deploy the metal3 operator, for provisioning physical workers|
|cloud_tag              |None                              ||
|cloud_scale            |False                             ||
|cloud\_api\_internal   |False                             ||
|apps                   |[]                                |Extra applications to deploy on the cluster|

We can then deploy it with

```
kcli create kube openshift --paramfile parameters.yml $cluster
```

### Storage support

By default, no storage provider is deployed but you can easily leverage LSO, LVMS or ODF. For instance, to use lvms, add the following to your parameter  file

```
extra_disks:
- 200
apps:
- lvms-operator
```

You can also deploy ODF by using the following snippet

```
extra_disks:
- 200
apps:
- local-storage-operator
- odf-operator
```

An other option is to use nfs provisioner, which gets installed indicating the following:

```
apps:
- nfs
```

Note that this will install and configure nfs on the host from where the workflow is launched

### Providing custom machine configs

If a `manifests` directory exists in the current directory, the *yaml assets found there are copied to the directory generated by the install, prior to deployment.

### SNO support

You can deploy a single node setting ctlplanes to 1 and workers to 0 in your parameter file.

Alternatively, bootstrap in place (bip) with rhcos live iso can be leveraged with the flag `sno`, which allows to provision a baremetal node by creating a custom iso stored in one specified Libvirt pool.
The following extra parameters are available with this workflow:

- sno_disk: You can indicate which disk to use for installing Rhcos operating system in your node. If none is specified, the disk will be autodiscovered
- extra_args: You can use this variable to specify as a string any extra args to add to the generated iso. A common use case for this is to set static networking for the node, for instanc with something like `ip=192.168.1.200::192.168.1.1:255.255.255.0:mysupersno.dev.local:enp1s0:none nameserver=192.168.1.1`
- api_ip: This is normally not needed but if DNS records already exist pointing to a given ip or when the ip of the node is unknown, a vip can be specified so that an extra keepalived static pod is injected.

In the baremetal context, the generated iso can be directly plugged to target nodes but the `baremetal_hosts` feature can also be used as described below, which required apache to be running on the hypervisor and to give write access to /var/www/html for the user launching the command, using something like:

```
sudo setfacl -m u:$(id -un):rwx /var/www/html
```

### Generating a worker iso

In OpenShift case, for baremetal workers you can use the following command to generate such an iso

```
kcli create openshift-iso --paramfile parameters.yml $cluster
```

### Baremetal hosts support

You can deploy baremetal workers in different way through this workflow.

The boolean baremetal_iso can be set to generate isos that you manually plug to the corresponding node (one iso per role).

You can also create isos only for a given role using the boolean baremetal_iso_bootstrap, baremetal_iso_ctlplane and baremetal_iso_worker

Alternatively, you can use the array baremetal_hosts to plug the worker iso to a list of baremetal hosts. The iso will be served from a deployment running in the control plane in that case.

For each entry you would specify:

- url or bmc_url. This is the redfish url to use, which is specific to the hardware. You can also just specify the ip and set the model if you dont know what the exact url is.
- user or bmc_user. bmc_user can also be set outside the array if you use the same user for all of your baremetal workers
- password or bmc_password. bmc_password can also be set outside the array if you use the same password for all of your baremetal workers

As an example, the following array will boot 3 workers (based on kvm vms with ksushy)

```
bmc_user: root
bmc_password: calvin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/bm3
```

### Disconnected support

To deploy with a disconnected registry, you can set the `disconnected_vm` boolean or specify a `disconnected_url`

In the first case, an helper vm will be deployed to host your disconnected registry and content will be synced for you

You can fine tweak this registry with several parameters:

- disconnected_disk_size
- disconnected_user
- disconnected_password
- disconnected_operators
- disconnected_vm_name
- ...

Note that this disconnected registry can also be deployed on its own using `kcli create openshift-registry` subcommand

Alternatively, you can specify the url of the registry where you have synced content by yourself. The `disconnected_url` typically is specified as `$host:$port`

You will also need to set disconnected_user and disconnected_password

You can specify disconnected_ca content, or let it undefined for the CA content to be fetched on the fly

Note that you will also need to sync the following images on the registry:

- quay.io/karmab/curl:multi
- quay.io/karmab/origin-coredns:multi
- quay.io/karmab/haproxy:multi
- quay.io/karmab/origin-keepalived-ipfailover:multi
- quay.io/karmab/mdns-publisher:multi
- quay.io/karmab/kubectl:multi
- quay.io/karmab/kcli:latest

The flag `disconnected_sync` allows you to sync content when reusing a given registry

### OKD

By setting `upstream` to true, you can deploy OKD (which will use a fake pull secret and fedora coreos as image)

## Interacting with clusters

All generated assets for a given cluster are stored in `$HOME/.kcli/clusters/$cluster`.

In particular, a kubeconfig file is available there for accessing your cluster.

## Scaling with more workers

The procedure is the same independently of the type of cluster used.

```
kcli scale kube <clustertype> -P workers=num_of_workers --paramfile parameters.yml $cluster
```

ctlplane nodes can also be scaled the same way

## Deleting clusters

The procedure is the same independently of the type of cluster used.

```
kcli delete kube $cluster
```

## Deploying Cloud Managed clusters

You can deploy AKS, EKS or GKE clusters using the same workflow.

First, make sure the corresponding provider is correctly defined then launch the workflow as usual

For instance, to deploy a GKE cluster, you would use

```
kcli create cluster gke mygke
```

Note that on those platforms, we rely more on default values provided by the Platform

see [AWS EKS workflow](https://github.com/karmab/kcli/blob/main/docs/EKS-kcli.md) for an example EKS process.

## Deploying applications on top of Kubernetes/OpenShift

You can use kcli to deploy applications on your Kubernetes/OpenShift (regardless of whether it was deployed with kcli)

Applications currently supported include:

- argocd
- kubevirt
- rook
- istio
- knative
- tekton

To list applications available on your cluster, run:

```
kcli list apps
```

For any of the supported applications, you can get information on the supported parameters with:

```
kcli info app $app_name
```

To deploy an app, use the following, with additional parameters passed in the command line or in a parameter file:

```
kcli create app $app_name
```

Applications can be deleted the same way:

```
kcli delete app $app_name
```

## Kubernetes Architecture

We provide details on the workflow used when deploying kubeadm or openshift clusters

### Kubeadm

The workflow leverages Kubeadm to create a cluster with the specified number of vms running either as ctlplanes or workers on any of the supported platforms.

Those vms can either be centos9stream, fedora or ubuntu based (as per the official Kubeadm doc).

The first node is used for bootstrapping the cluster, through commands that run by rendering cloudinit data.

Once it is done, the generated token is retrieved, which allows to add the other nodes.

for HA and Loadbalancing, Keepalived and Haproxy are leveraged, which involves declaring a vip. For Libvirt, when no vip is provided, an educated guess around the vip is done for virtual networks.

For cloud providers (aws, gcp and ibmcloud), loadbalancer along with dns is used to achieve the same result. That requires specifying an existing top level domain.

Available options in this workflow allow to:

- customizing the hardware of the involved vms
- using a different k8s version, cni or engine
- deploying nfs, nginx ingress or metallb.
- etc

### Openshift

We deploy:

- a bootstrap node removed at the end of the install.
- an arbitrary number of ctlplanes.
- an arbitrary number of workers.

When oc or openshift-install are missing, they are downloaded on the fly, using public mirrors or registry.ci.openshift.org if ci is specified (the provided pull secret needs an auth for this registry).

rhcos image associated to the specified version is downloaded and the corresponding line is added in the parameter file unless an image is specified as parameter.

Ignition files needed for the install are generated using `openshift-install create ignition-configs`

Also note that for bootstrap, ctlplanes and workers nodes, we merge the ignition data generated by the OpenShift installer with the ones generated by kcli, in particular we prepend dns server on those nodes to point to our keepalived vip, force hostnames and inject static pods.

Deployment of bootstrap and ctlplanes vms is then launched. Isos are optionally created for baremetal hosts

Keepalived and Coredns with mdns are deployed on the bootstrap and ctlplane nodes as static pods. They provide HA access and dns records as needed.

Initially, the api vip runs on the bootstrap node.

Ignition files are provided over 22624/http using api ip instead of fqdn. The ignition files for both ctlplane and worker are patched for it.

Haproxy is created as static pod on the ctlplane nodes to load balance traffic to the routers. When there are no workers, routers are instead scheduled on the ctlplane nodes and the haproxy static pod isn't created, so routers are simply accessed through the vip without load balancing.

Once bootstrap phase finished, the vips transition to one of the ctlplanes.

At this point, workers are created and the installation is monitored until completion. A flag allows to deploy in an async manner

On cloud platforms, We rely on dns and load balancing services and as such dont need static pods.

In the case of deploying a single ctlplane, the flag `sno_cloud_remove_lb` allows to get rid of the loadbalancer at the end of the install.

# kcli-controller

There is a controller leveraging kcli and using vm, plan and clusters crds to create vms the corresponding objects, regardless of the infrastructure.

## Prerequisites

- a running Kubernetes/OpenShift cluster and KUBECONFIG env variable pointing to it (or simply .kube/config)
- some infrastructure supported by kcli running somewhere and the corresponding credentials.
- storage to hold two pvcs (one from plan files data and the other for clusters data)

## Deploying

If you're running kcli locally, use the following to create the proper configmaps to share your credentials and ssh keys:

```
kcli sync kube
```

To do the same manually, run instead:

```
kubectl create configmap kcli-config --from-file=$HOME/.kcli
kubectl create configmap ssh-config --from-file=$HOME/.ssh
```

Then deploy the controller (along with its CRDS):

```
kubectl create -f https://raw.githubusercontent.com/karmab/kcli/main/extras/controller/deploy.yml
```

If you want to use a pvc named `kcli-clusters` for storing cluster data, add it:

```
kubectl -n kcli-infra patch deploy kcli-controller --type json -p='[{"op": "add", "path": "/spec/template/spec/containers/0/volumeMounts/-", "value": {"mountPath": "/root/.kcli/clusters", "name": "kcli-clusters"}}, {"op": "add", "path": "/spec/template/spec/volumes/-", "value": {"persistentVolumeClaim": {"claimName" : "kcli-clusters"}, "name": "kcli-clusters"}}]'
```

## How to use the controller

The directory [extras/controller/examples](https://github.com/karmab/kcli/tree/main/extras/controller/examples) contains different examples of vm, plan and cluster CRs.

Here are some sample ones for each type to get you started

with vms

```
apiVersion: kcli.karmalabs.local/v1
kind: Vm
metadata:
  name: cirros
spec:
  image: cirros
  memory: 512
  numcpus: 2
```

Note that when a vm is created, the controller waits before it gets an ip and populate it status with its complete information, which is then formatted when running `kubectl get vms`

with plans

```
apiVersion: kcli.karmalabs.local/v1
kind: Plan
metadata:
  name: simpleplan2
spec:
  plan: |
    vm11:
      memory: 512
      numcpus: 2
      nets:
       - default
      image: cirros
    vm22:
      memory: 1024
      numcpus: 4
      nets:
       - default
      disks:
       - 20
      pool: default
      image: cirros
      cmds:
       - echo this stuff works > /tmp/result.txt
```

To run plans which contain scripts or files, you ll need to copy those assets in the /workdir of the kcli pod

```
KCLIPOD=$(kubectl get pod -o name -n kcli | sed 's@pod/@@')
kubectl cp samplecrd/frout.txt $KCLIPOD:/workdir
```

with clusters

```
apiVersion: kcli.karmalabs.local/v1
kind: Cluster
metadata:
  name: hendrix
spec:
  ctlplanes: 1
  api_ip: 192.168.122.252
```

Once a cluster is deployed successfully, you can retrieve its kubeconfig from it status

```
kubectl get cluster $CLUSTER -o jsonpath='{.status.create_cluster.kubeconfig}' | base64 -d
```

### Autoscaling

You can enable autoscaling for a given cluster by setting `autoscale` to any value in its spec.

### Scaling up

When more than a given threshold of pods can't be scheduled, one more worker will be added to the cluster and the autoscaling will pause until it appears as a new ready node.

This threshold is configured as an env variable AUTOSCALE_MAXIMUM provided during the deployment of the controller, which defaults to 20

Setting the threshold to any value higher than 9999 effectively disables the feature.

### Scaling down

If the number of running pods for a given worker node goes below a minimum value, the cluster will be scaled down by one worker.

The minimum is configured as an env variable AUTOSCALE_MINIMUM provided during the deployment of the controller, which defaults to 2

Setting the minimum to any value below 1 effectively disables the feature.

# Configuration pools

Configuration pools allow to store a list of ips, names or baremetal_hosts and make them available to a vm or a cluster upon deployment.

This provides the following features:

- Provide static ip to vms from a self maintained list of ips
- Provide vip to clusters in the same manner
- Provide a list of baremetal_hosts to clusters.
- Provide names to vms or clusters from a specific list

Upon creation, the corresponding entry gets reserved to the vm or the cluster and released upon deletion.

## Creating a confpool

You can use `kcli create confpool` commands to create a configuration pool and then use list, update or delete calls.

Under the hood, all the pools are stored in `~/.kcli/confpools.yml` so this file can also be edited manually.

confpool typically contain ips, baremetal information or both.

Here's a sample content of this file

```
myvips:
  ips:
  - 192.168.122.250
  - 192.168.122.251
  - 192.168.122.252
  vm_reservations: {}
  bmc_user: root
  bmc_password: calvin
  baremetal_hosts:
  - http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
  - http://192.168.122.1:9000/redfish/v1/Systems/local/vm2
```

To create a confpool with 3 ips, use the following

```
kcli create confpool myconfpool -P ips=[192.168.122.250,192.168.122.251,192.168.122.252 -P netmask=24 -P gateway=192.168.122.1
```

For ips, note you can also provide a cidr such as 192.168.122.0/24

the pool can also store any value, some of which will be evaluated (in particular any of the network keywords such as netmask,gateway as shown in the example).

To create a confpool with 2 baremetal hosts, use the following

```
kcli create myconfpool -P baremetal_hosts=[http://192.168.122.1:9000/redfish/v1/Systems/vm1,http://192.168.122.1:9000/redfish/v1/Systems/local/vm2] -P bmc_user=admin -P bmc_password=admin0
```

Note that in this case, we also provide bmc credentials, all the hosts in your pool should share the same credentials.

To create a confpool with some DBZ names, use the following

```
kcli create dbzpool -P names=[gohan,goku,vegeta,picolo,raditz,tenchinhan]
```

## Using a confpool

For vms, the confpool is typically specified in a nets section to consume ips. For instance

```
kcli create vm -i centos9stream -P nets=['{"name": "default", "confpool": "myconfpool"}']
```

You can also create a vm with a name from the previously created dbz name confpool with the following call

```
kcli create vm -i centos9stream -P confpool=dbzpool
```

When creating the cluster, specify through a parameter which pool to use (`-P confpool=mypool`)

```
kcli create cluster generic -P confpool=mypool
```

If you need to use several pools when creating a vm/cluster, you can be more specific by using the following aliases:

- ippool
- namepool
- baremetalpool

For instance, you could do something like

```
kcli create vm -i centos9stream -P ippool=ippool -P namepool=dbzpool
```

# kweb

kweb provides a local web interface for interacting with your providers

Launch the following command and access your machine at port 8000:

```Shell
kweb
```

The command supports a flag `--readonly` to make the web read only.

You can check the [swagger spec](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/karmab/kcli/main/kvirt/web/swagger.yml) to call the different endpoints using your language of choice.

# ksushy

ksushy provides a REST interface to interact with vms using Redfish. This provides a functionality similar to sushy-emulator but extending it to more providers (typically Vsphere, Kubevirt and oVirt) and through more friendly urls.

## ksushy requirements

ksushy is bundled within kcli but ssl support requires installing manually cherrypy and pyopenssl package

## Deploy ksushy service

ksushy can be launched manually for testing purposes but the following command creates a systemd unit instead, listening on port 9000. The call parses the following environment variables:

- KSUSHY_LISTEN_PORT: use a specific port
- KSUSHY_DEBUG: enable debug
- KSUSHY_USER: username for authentication
- KSUSHY_PASSWORD: password for authentication
- KSUSHY_BOOTONCE: enable bootonce

```
kcli create sushy-service
```

## Interacting with vms through redfish

Once the service is deployed, one can query an existing vm running locally using the following

```
curl https://127.0.0.1/redfish/v1/Systems/local/mynode
```

For querying a vm running on a different provider, the url would change to specify the provider as defined in ~/.kcli/config.yml

```
curl https://127.0.0.1/redfish/v1/Systems/myotherprovider/mynode2
```

Typical redfish operations like start, stop, info, listing nics of a vm are supported for all providers.

For plugging an iso, only virtualization providers can be used.

## Restricting ksushy access

When deploying the service, an username and password can be specified for securing access through basic authentication


You can use kvirt library directly, without the client or to embed it into your own application.

Here's a sample:

```
from kvirt.config import Kconfig
config = Kconfig()
k = config.k
```

You can then either use config for high level actions or the more low level *k* object.

# Ansible support

klist.py is provided as a dynamic inventory for ansible.

The script uses sames conf as kcli (and as such defaults to local if no configuration file is found).

vms will be grouped by plan, or put in the kvirt group if they dont belong to any plan.

Try it with:

```Shell
klist.py --list
KLIST=$(which klist.py)
ansible all -i $KLIST -m ping
```

If you're using kcli as a container, you will have to create a script such as the following to properly call the inventory.

```
#!/bin/bash
podman run -it --security-opt label:disable -v ~/.kcli:/root/.kcli -v /var/run/libvirt:/var/run/libvirt --entrypoint=/usr/bin/klist.py karmab/kcli $@
```

Additionally, there are ansible kcli modules in [ansible-kcli-modules](https://github.com/karmab/ansible-kcli-modules) repository, with sample playbooks:

- kvirt_vm allows you to create/delete vm (based on an existing profile or image)
- kvirt_plan allows you to create/delete a plan
- kvirt_info allows you to retrieve a dict of values similar to `kcli info` output. You can select which fields to gather

Those modules rely on python3 so you will need to pass `-e 'ansible_python_interpreter=path_to_python3'` to your ansible-playbook invocations ( or set it in your inventory) if your default ansible installation is based on python2.

Both kvirt_vm and kvirt_plan support overriding parameters. For instance,

```
- name: Deploy fission with additional parameters
  karmab.kcli.kcli_vm:
    name: fission
    state: present
    image: centos9stream
    parameters:
      memory: 2048
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

# AI support

3 mcp servers are available to be used with chat apps such as ChatGpt, Claude Desktop and so on

- mcpcore.py provides core tools to start, stop,create, delete and list pool, networks, vms and clusters
- mcpcloud.py provides additional cloud tools to create, delete and list buckets, bucketfiles, dns entries, load balancers and securitygroups/firewalls
- mcpbm.py provides baremetal tools that allow to get info, start, stop, reset and update a Baremetal Host via redfish
