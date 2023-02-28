|CI| |Pypi| |Copr| |Documentation Status|

About
=====

This tool is meant to ease interaction with virtualization providers:

-  libvirt
-  vsphere
-  kubevirt
-  aws
-  gcp
-  ibmcloud
-  packet
-  ovirt
-  openstack

You can:

-  manage vms:

   -  create
   -  delete
   -  list
   -  info
   -  ssh
   -  start
   -  stop
   -  console
   -  serialconsole,
   -  create/delete disk
   -  create/delete nic
   -  clone

-  deploy them using profiles
-  define more complex workflows using *plans* and products.

Kubernetes clusters can also be deployed, either:

-  kubernetes generic (kubeadm)
-  openshift/okd
-  k3s
-  kind
-  microshift

Installation
============

Libvirt Hypervisor Requisites
-----------------------------

If you don’t have libvirt installed on the target hypervisor, you can use the following command:

.. code:: bash

   sudo yum -y install libvirt libvirt-daemon-driver-qemu qemu-kvm 
   sudo usermod -aG qemu,libvirt $(id -un)
   sudo newgrp libvirt
   sudo systemctl enable --now libvirtd

(Optional) For interaction with your local docker daemon, you also need the following:

.. code:: bash

   sudo groupadd docker
   sudo usermod -aG docker $(id -un)
   sudo systemctl restart docker

Supported installation methods
------------------------------

The following methods are supported for installation and are all updated automatically when new pushes to kcli are made.

-  rpm package
-  deb package
-  container image
-  pypi package

Installing
----------

A generic script is provided for for installation:

.. code:: shell

   curl https://raw.githubusercontent.com/karmab/kcli/main/install.sh | sudo bash

It does the following:

-  make a guess on which method to use for deployment based on your OS
-  create the proper aliases if container method is selected
-  set bash completion

Package install method
----------------------

For rhel based OS (*fedora*/*rhel or centos*), you can run this:

.. code:: bash

   sudo dnf -y copr enable karmab/kcli ; sudo dnf -y install kcli

If using a debian based distribution, use this instead:

.. code:: bash

   curl -1sLf https://dl.cloudsmith.io/public/karmab/kcli/cfg/setup/bash.deb.sh | sudo -E bash
   sudo apt-get update
   sudo apt-get -y install python3-kcli

The package based version doesn’t bundle the dependencies for anything else than libvirt, so you have to install the extra packages for each additional cloud platforms, which are listed in the *Provider specifics* section.

Alternatively, the repo contains a meta package named kcli-all (python3-kcli-all in the debian case) that contains dependencies for all the providers.

*NOTE*: kcli-all is only available on fedora.

Container install method
------------------------

Note that:

-  The container image contains dependencies for all the providers.
-  The console/serial console functionality works better with the package version. In container mode, it only outputs the command to launch manually to get to the console.

In the commands below, feel free to use docker instead

Pull the latest image:

.. code:: shell

   podman pull quay.io/karmab/kcli

To run it

.. code:: shell

   podman run --rm karmab/kcli

There are several recommended flags:

-  ``--net host`` for kcli ssh
-  ``-v /var/run/libvirt:/var/run/libvirt -v /var/lib/libvirt/images:/var/lib/libvirt/images`` if running against a local client.
-  ``-v  ~/.kcli:/root/.kcli`` to use your kcli configuration (also profiles and repositories) stored locally.
-  ``-v ~/.ssh:/root/.ssh`` to share your ssh keys. Alternatively, you can store your public and private key in the ~/.kcli directory.
-  ``--security-opt label=disable`` if running with selinux.
-  ``-v $PWD:/workdir`` to access plans below your current directory.
-  ``-v $HOME:/root`` to share your entire home directory, useful if you want to share secret files, ``~/register.sh`` for instance).
-  ``-e HTTP_PROXY=your_proxy -e HTTPS_PROXY=your_proxy``
-  ``-v ~/.kube:/root/.kube`` to share your kubeconfig.

For web access, you can switch with ``-p 9000:9000 --entrypoint=/usr/bin/kweb`` and thus accessing to port 9000.

As a bonus, you can use the following aliases:

.. code:: shell

   alias kcli='podman run --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir quay.io/karmab/kcli'
   alias kclishell='podman run --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir --entrypoint=/bin/bash quay.io/karmab/kcli'
   alias kweb='podman run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir --entrypoint=/usr/bin/kweb quay.io/karmab/kcli'

Dev installation
----------------

Generic platform
~~~~~~~~~~~~~~~~

.. code:: shell

   pip3 install kcli

Or for a full install:

::

   pip3 install -e git+https://github.com/karmab/kcli.git#egg=kcli[all]

Configuration
=============

If you only want to use your local libvirt, *no specific configuration* is needed.

kcli configuration is done in ~/.kcli directory, that you need to manually create. It will contain:

-  config.yml generic configuration where you declare clients.
-  profiles.yml stores your profiles where you combine things like memory, numcpus and all supported parameters into named profiles to create vms from.
-  id_rsa/id_rsa.pub/id_dsa/id_dsa.pub/id_25519/id_25519.pub You can store your default public and private keys in *.kcli* directory which will be the first place to look for them when connecting to a remote kvm hypervisor, virtual machine or when injecting your public key.

You can generate a default config file (with all parameters commented) pointing to your local host with:

.. code:: shell

   kcli create host kvm -H 127.0.0.1 local

Or indicate a different target host

.. code:: shell

   kcli create host -H 192.168.0.6 host1

On most distributions, default network and storage pool for libvirt are already defined.

If needed, you can create this default storage pool with this:

.. code:: shell

   sudo kcli create pool -p /var/lib/libvirt/images default
   sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images

And default network:

.. code:: shell

   kcli create network  -c 192.168.122.0/24 default

For using several hypervisors, you can use the command *kcli create host* or simply edit your configuration file.

For instance, here’s a sample ``~/.kcli/config.yml`` with two hypervisors:

.. code:: yaml

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

Replace with your own client in default section and indicate the relevant parameters in the corresponding client section, depending on your client/host type.

Most of the parameters are actually optional, and can be overridden in the default, client or profile section (or in a plan file). You can find a fully detailed config.yml sample `here <https://github.com/karmab/kcli/tree/main/samples/config.yml>`__

Storing credentials securely
----------------------------

You can hide your secrets in *~/.kcli/config.yml* by replacing any value by *?secret*. You can then place the real value in *~/.kcli/secrets.yml* by using the same yaml hierarchy.

For instance, if you have the following in your config file:

::

   xxx:
    password: ?secret

You would then put the real password in your secrets file this way:

::

   xxx:
    password: mypassword

Provider specifics
==================

Libvirt
-------

::

   twix:
    type: kvm
    host: 192.168.1.6

Without configuration, libvirt provider tries to connect locally using qemu:///system.

Additionally, remote libvirt hypervisors can be configured by indicating either a host, a port and protocol or a custom qemu url.

When using the host, port and protocol combination, default protocol uses ssh and as such assumes you are able to connect without password to your remote libvirt instance.

If using tcp protocol instead, you will need to configure libvirtd in your remote libvirt hypervisor to accept insecure remote connections.

You will also likely want to indicate default libvirt pool to use (although as with all parameters, it can be done in the default section).

The following parameters are specific to libvirt:

-  url custom qemu uri.
-  session Defaults to False. If you want to use qemu:///session ( locally or remotely). Not recommended as it complicates access to the vm and is supposed to have lower performance.
-  remotednsmasq Defaults to False. Allow to create entries in a dedicated dnsmasq instance running on a remote hypervisor to provide DNS resolution for vms using bridged networks.

Gcp
---

::

   gcp1:
    type: gcp
    credentials: ~/myproject.json
    project: myproject
    zone: europe-west1-b

The following parameters are specific to gcp:

-  credentials (pointing to a json service account file). if not specified, the environment variable *GOOGLE_APPLICATION_CREDENTIALS* will be used
-  project
-  zone

also note that gcp provider supports creation of dns records for an existing domain and that your home public key will be uploaded if needed

To gather your service account file:

-  Select the “IAM” → “Service accounts” section within the Google Cloud Platform console.
-  Select “Create Service account”.
-  Select “Project” → “Editor” as service account Role.
-  Select “Furnish a new private key”.
-  Select “Save”.

To Create a dns zone:

-  Select the “Networking” → “Network Services” → “Cloud DNS”.
-  Select “Create Zone”.
-  Put the same name as your domain, but with ‘-’ instead.

If accessing behind a proxy, be sure to set *HTTPS_PROXY* environment variable to ``http://your_proxy:your_port``

To use this provider with kcli rpm, you’ll need to install (from pip):

::

   pip3 install google-api-python-client google-auth-httplib2 google-cloud-dns

Aws
---

::

   aws:
    type: aws
    access_key_id: AKAAAAAAAAAAAAA
    access_key_secret: xxxxxxxxxxyyyyyyyy
    region: eu-west-3
    keypair: mykey

The following parameters are specific to aws:

-  access_key_id
-  access_key_secret
-  region
-  keypair
-  session_token

To use this provider with kcli rpm, you’ll need to install

::

   dnf -y install python3-boto3

Kubevirt
--------

For kubevirt, you will need to define one ( or several !) sections with the type kubevirt in your *~/.kcli/config.yml*

Authentication is either handled by your local ~/.kubeconfig (kcli will try to connect to your current kubernetes/openshift context or with specific token:

::

   kubevirt:
    type: kubevirt

You can use additional parameters for the kubevirt section:

-  kubeconfig: kubeconfig file path
-  context: the k8s context to use.
-  pool: your default storageclass. can also be set as blank, if no storage class should try to bind pvcs.
-  host: k8s api node .Also used for tunneling ssh.
-  port: k8s api port.
-  ca_file: optional certificate path.
-  namespace: target namespace.
-  token: token, either from user or service account.
-  tags: additional list of tags in a key=value format to put to all created vms in their *nodeSelector*. Can be further indicated at profile or plan level in which case values are combined. This provides an easy way to force vms to run on specific nodes, by matching labels.
-  cdi: whether to use cdi. Defaults to true. A check on whether cdi is actually present will be performed.
-  registry: Registry where to pull containerdisk images. Defaults to none, in which case your configured registries will be used.
-  access_mode: Way to access vms other ssh. Defaults to NodePort,in which case a svc with a nodeport pointing to the ssh port of the vm will be created. Otherpossible values are LoadBalancer to create a svc of type loadbalancer to point to the vm or External to connect using the sdn ip of the vm. If tunnel options are set, they take precedence
-  volume_mode: Volume Mode. Defaults to Filesystem (Block can be specified instead).
-  volume_access: Volume access mode. Defaults to ReadWriteOnce.
-  disk_hotplug: Whether to allow to hotplug (and unplug) disks. Defaults to false. Note it also requires to enable The HotplugVolumes featureGate within Kubevirt
-  embed_userdata: Whether to embed userdata directly in the vm spec. Defaults to false
-  first_consumer: Whether the storage class has a volumeBindingMode set to WaitForFirstConsumer. Defaults to false. This allows to provision pvcs by creating a dummy job to force PVC binding

You can use the following indications to gather context, create a suitable service account and retrieve its associated token:

To list the context at your disposal

::

   kubectl config view -o jsonpath='{.contexts[*].name}'

To create a service account and give it privileges to handle vms,

::

   SERVICEACCOUNT=xxx
   kubectl create serviceaccount $SERVICEACCOUNT -n default
   kubectl create clusterrolebinding $SERVICEACCOUNT --clusterrole=cluster-admin --user=system:serviceaccount:default:$SERVICEACCOUNT

To gather a token (in /tmp/token):

::

   SERVICEACCOUNT=xxx
   SECRET=`kubectl get sa $SERVICEACCOUNT -o jsonpath={.secrets[0].name}`
   kubectl get secret $SECRET -o jsonpath={.data.token} | base64 -d

on openshift, you can simply use

::

   oc whoami -t

*kubectl* is currently a hard requirement for consoles

To use this provider with kcli rpm, you’ll need to install

::

   dnf -y install python3-kubernetes

Ovirt
-----

::

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

The following parameters are specific to ovirt:

-  org Organization
-  ca_file Points to a local path with the cert of the ovirt engine host. It can be retrieved with ``curl "http://$HOST/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA" > ~/.kcli/ovirt.pem``
-  cluster Defaults to Default
-  datacenter Defaults to Default
-  filtervms Defaults to True. Only list vms created by kcli.
-  filteruser Defaults to False. Only list vms created by own user
-  filtertag Defaults to None. Only list vms created by kcli with the corresponding filter=filtertag in their description. Useful for environments when you share the same user

Note that pool in Ovirt context refers to storage domain.

To use this provider with kcli rpm, you’ll need to install

::

   dnf -y install https://resources.ovirt.org/pub/yum-repo/ovirt-release44.rpm
   dnf -y install python3-ovirt-engine-sdk4

Deploying Ovirt dependencies with pip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You will need to get *ovirt-engine-sdk-python* . On fedora, for instance, you would run:

::

   dnf -y copr enable karmab/kcli
   yum -y install kcli gcc redhat-rpm-config python3-devel openssl-devel libxml2-devel libcurl-devel
   export PYCURL_SSL_LIBRARY=openssl
   pip3 install ovirt-engine-sdk-python

On rhel, set PYCURL_SSL_LIBRARY to nss instead

If you install manually from pip, you might need to install pycurl manually with the following line (and get openssl-dev headers)

::

   pip install --no-cache-dir --global-option=build_ext --global-option="-L/usr/local/opt/openssl/lib" --global-option="-I/usr/local/opt/openssl/include"  pycurl

Openstack
---------

::

   myopenstack:
    type: openstack
    user: testk
    password: testk
    project: testk
    domain: Default
    auth_url: http://openstack:5000/v3
    ca_file: ~/ca-trust.crt

The following parameters are specific to openstack:

-  auth_url
-  project
-  domain. Defaults to *Default*
-  ca_file (Optional)
-  external_network (Optional). Indicates which network use for floating ips (useful when you have several ones)
-  region_name (Optional). Used in OVH Openstack
-  glance_disk (Optional). Prevents creating a disk from glance image. Defaults to false
-  token (Optional). Keystone Token (That can be retrieved with ``openstack token issue -c id -f value``)

To use this provider with kcli rpm, you’ll need to install the following rpms

::

   grep -q 'Red Hat' /etc/redhat-release && subscription-manager repos --enable openstack-16-tools-for-rhel-8-x86_64-rpms
   dnf -y install python3-keystoneclient python3-glanceclient python3-cinderclient python3-neutronclient python3-novaclient python3-swiftclient

Vsphere
-------

::

   myvsphere:
    type: vsphere
    host: xxx-vcsa67.vcenter.e2e.karmalabs.corp
    user: administrator@karmalabs.corp
    password: mypassword
    datacenter: Madrid
    cluster: xxx
    filtervms: true
    pool: mysuperdatastore

The following parameters are specific to vsphere:

-  cluster
-  datacenter: Defaults to Default
-  filtervms Defaults to True. Only list vms created by kcli. Useful for environments when you are superadmin and have a ton of vms!!!
-  category: Defaults to kcli. Category where to create tags in order to apply them to vms. If tags are requested for a given vm, they will be created on the fly along with the category, if missing
-  basefolder: Optional base folder where to create all vms
-  isofolder: Optional folder where to keep ISOs
-  dvs: Whether to gather DVS networks. Enabled by default, but can be set to False to speed up operations if you don’t have dvs networks
-  import_network: Defaults to ‘VM Network’. Network to use as part of the template created when downloading image
-  timeout: Defaults to 1800. Custom connectionPooltimeout

Note that pool in Vsphere context refers to datastore.

To use this provider with kcli rpm, you’ll need to install

::

   dnf -y install python3-pyvmomi python3-cryptography python3-requests

Using hostgroups and vm-host rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The requisite is to create the hostgroup by yourself so that you can associate your hosts to it.

Then, when creating a vm, one can provide 3 extra parameters:

vmgroup: if it doesn’t exist, the group will be created and in any case, the vm will get added to it.

hostgroup and hostrule: if both are provided and the hostrule doesnt exist, it will be created as affinity rule with the vmgroup and the hostgroup to it.

Note that when using this within a plan (or a cluster), it’s enough to provide hostgroup and hostrule for the first vm of the plan so that the hostrule gets created ( though a kcli vmrule for instance), and vmgroup for all of them, so that the group gets created with the first vm, and then the remaining vm only get added.

Also note that vmgroups and hostrules dont get deleted along with vms (to ease recreation of the same assets)

Using vm anti affinity rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within a plan, you can set the keyword ``antipeers`` to a list of vms which should never land on the same esx host. When the last vm from this list gets created, the corresponding anti affinity rule will be created (and vsphere will relocate the other vms accordingly)

Packet
------

::

   myvpacket:
     type: packet
     auth_token: xxxx
     project: kcli
     facility: ams1
     tunnelhost: wilibonka.mooo.com

The following parameters are specific to packet:

-  auth_token.
-  project
-  facility. Can be omitted in which case you will have to specify on which facility to deploy vms.
-  tunnelhost. Optional. When creating vms using ignition, the generated ignition file will be copied to the tunnelhost so it can be served (typically via web)
-  tunneldir. Where to copy the ignition files when using a tunnelhost. Defaults to */var/www/html*

To use this provider with kcli rpm, you’ll need to install packet-python (from pip):

::

   pip3 install packet-python

IBM Cloud
---------

::

   myibm:
     type: ibm
     iam_api_key: xxxx
     region: eu-gb
     zone: eu-gb-2
     vpc: pruebak

The following parameters are specific to ibm cloud:

-  iam_api_key.
-  region
-  zone
-  vpc. Default vpc
-  cos_api_key. Optional Cloud object storage apikey
-  cos_resource_instance_id. Optional Cloud object storage resource_instance_id (something like “crn:v1:bluemix:public:cloud-object-storage:global:a/yyy:xxxx::”). Alternatively you can provide the resource name
-  cos_resource_instance_id. Optional Cis resource_instance_id used for DNS. Alternatively, you can provide the resource name

To use this provider with kcli rpm, you’ll need to install the following packets (from pip):

::

   pip3 install ibm_vpc ibm-cos-sdk ibm-platform-services ibm-cloud-networking-services
   # optionally
   pip install cos-aspera

Usage
=====

Basic workflow
--------------

Cloud Images from common distros aim to be the primary source for your vms *kcli download image* can be used to download a specific cloud image. for instance, centos7:

.. code:: shell

   kcli download image centos7

at this point, you can deploy vms directly from the template, using default settings for the vm:

.. code:: shell

   kcli create vm -i centos7 vm1

By default, your public key will be injected (using cloudinit) to the vm.

You can then access the vm using *kcli ssh*.

Kcli uses the default ssh_user according to the `cloud image <http://docs.openstack.org/image-guide/obtain-images.html>`__. To guess it, kcli checks the image name. So for example, your centos image must contain the term “centos” in the file name, otherwise “root” is used.

If you are not able to ssh into the vm, Note you can always ``kcli console`` or ``kcli console --serial`` to access the VM

Using parameters, you can tweak the vm creation. All keywords can be used. For instance:

.. code:: shell

   kcli create vm -i centos7 -P memory=2048 -P numcpus=2 vm1

You can also pass disks, networks, cmds (or any keyword, really):

.. code:: shell

   kcli create vm -i centos7 -P disks=[10,20] -P nets=[default,default] -P cmds=[yum -y install nc] vm1

You can use the following to get a list of available keywords, and their default value

.. code:: shell

   kcli get keyword

Profiles configuration
----------------------

Instead of passing parameters this way, you can use profiles.

Profiles are meant to help creating single vm with preconfigured settings (number of CPUS, memory, size of disk, network, whether to use a template, extra commands to run on start, whether reserving dns,….)

You use the file *~/.kcli/profiles.yml* to declare your profiles. Here’s a snippet declaring the profile ``centos``:

::

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

With this section, you can use the following to create a vm

.. code:: shell

   kcli create vm -p mycentos myvm

Note that when you download a given cloud image, a minimal associated profile is created for you.

Cloudinit/Ignition support
--------------------------

Cloudinit is enabled by default and handles static networking configuration, hostname setting, injecting ssh keys and running specific commands and entire scripts, and copying entire files.

For vms based on coreos, ignition is used instead of cloudinit although the syntax is the same. If $name.ign or $plan.ign are found in the current directory, their content will be merged. The extension .cloudinit does the same for cloudinit.

To ease openshift deployment, when a node has a name in the $cluster-role-$num, where role can either be ctlplane, worker or bootstrap, additional paths are searched, namely $cluster-$role.ign, clusters/$cluster/$role.ign and $HOME/.kcli/clusters/$cluster/$role.ign

For ignition support on ovirt, you will need a version of ovirt >= 4.3.4. Note that this requires to use an openstack based rhcos image.

Typical commands
----------------

-  List vms

   -  ``kcli list vm``

-  List cloud images

   -  ``kcli list images``

-  Create vm from a profile named base7

   -  ``kcli create vm -p base7 myvm``

-  Create vm from profile base7 on a specific client/host named twix

   -  ``kcli -C twix create vm -p base7 myvm``

-  Delete vm

   -  ``kcli delete vm vm1``

-  Do the same without having to confirm

   -  ``kcli delete vm vm1 --yes``

-  Get detailed info on a specific vm

   -  ``kcli info vm vm1``

-  Start vm

   -  ``kcli start vm vm1``

-  Stop vm

   -  ``kcli stop vm vm1``

-  Switch active client/host to bumblefoot

   -  ``kcli switch host bumblefoot``

-  Get remote-viewer console

   -  ``kcli console vm vm1``

-  Get serial console (over TCP). Requires the vms to have been created with kcli and netcat client installed on hypervisor

   -  ``kcli console vm -s vm1``

-  Deploy multiple vms using plan x defined in x.yml file

   -  ``kcli create plan -f x.yml x``

-  Delete all vm from plan x

   -  ``kcli delete plan x``

-  Add 5GB disk to vm1, using pool named images

   -  ``kcli create vm-disk -s 5 -p images vm1``

-  Delete disk named vm1_2.img from vm1

   -  ``kcli delete disk --vm vm1 vm1_2.img``

-  Update memory in vm1 to 2GB memory

   -  ``kcli update vm -P memory=2048 vm1``

-  Clone vm1 to new vm2

   -  ``kcli clone vm -b vm1 vm2``

-  Connect with ssh to vm vm1

   -  ``kcli ssh vm vm1``

-  Create a new network

   -  ``kcli create network -c 192.168.7.0/24 mynet``

-  Create new pool

   -  ``kcli create pool -t dir -p /hom/images images``

-  Add a new nic from network default to vm1

   -  ``kcli create nic -n default vm1``

-  Delete nic eth2 from vm

   -  ``kcli delete nic -i eth2 vm1``

-  Create snapshot named snap1 for vm1:

   -  ``kcli create snapshot vm -n vm1 snap1``

-  Get info on your kvm setup

   -  ``kcli info host``

-  Export vm:

   -  ``kcli export vm vm1``

-  Run workflow script named myworkflow.sh with some parameters:

   -  ``kcli create workflow myworkflow.sh -P xx=jimi``

Omitting vm’s name
------------------

When you don’t specify a vm, the last one created by kcli on the corresponding client is used (the list of the vms created is stored in *~/.kcli/vm*)

So for instance, you can simply use the following command to access your vm:

``kcli ssh``

How to use the web version
--------------------------

Launch the following command and access your machine at port 8000:

.. code:: shell

   kweb

The command supports a flag ``--readonly`` to make the web read only.

Calling web endpoints through REST
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

you can check the `swagger spec <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/karmab/kcli/main/kvirt/web/swagger.yml>`__ to call the different endpoints using your language of choice.

Multiple clients
----------------

If you have multiple hypervisors/clients, you can generally use the flag *-C $CLIENT* to point to a specific one.

You can also use the following to list the vms of all your hosts/clients:

``kcli -C all list vm``

plans
=====

You can also define *plan* which are files in yaml with a list of profiles, vms, disks, and networks and vms to deploy.

The following types can be used within a plan:

-  vm (this is the type used when none is specified)
-  image
-  network
-  disk
-  pool
-  profile
-  ansible
-  container
-  dns
-  plan (so you can compose plans from several urls)
-  kube
-  workflow

Create and run your first plan
------------------------------

Here’s a basic plan to get a feel of plan’s logic

::

   vm1:
    image: centos8stream
    numcpus: 8
    memory: 2048
    files:
    - path: /etc/motd
      content: Welcome to the cruel world

   vm2:
    image: centos8stream
    numcpus: 8
    memory: 2048
    cmds:
    - yum -y install httpd

To run this plan, we save it as ``myplan.yml`` and we can then deploy it using ``kcli create plan -f myplan.yml``

This will create two vms based on the centos8stream cloud image, with the specified hardware characteristics and injecting a specific file for vm1, or running a command to install httpd for vm2.

Additionally, your ssh public key gets automatically injected to the node, and the hostname of those vms get set, all through cloudinit.

Although this is a simple plan, note that:

-  it’s expected to behave exactly the same regardless of your target virtualization platform
-  can be relaunched in an idempotent manner

Make it more powerful with variables
------------------------------------

Let’s modify our plan to make it more dynamic

::

   parameters:
    image: centos8stream
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

This looks similar to the first example, but now we have a parameters section where we define default values for a set of variables that is then used within the plan, through jinja.

When creating the plan, any of those parameter can we overriden by using ``-P key=value``, or providing a parameter file.

For instance, we would run ``kcli create plan -f my_plan.yml -P numcpus=16 -P memory=4096 -P motd="Welcome to the cool world`` to create the two same vms with different hardware values and with a custom motd in vm1

Note that any jinja construct can be used within a plan (or through the files or the scripts referenced by said plan)

plan types
----------

Here are some examples of each type (more examples can be found in this `samples repo <https://github.com/karmab/kcli-plan-samples>`__):

network
~~~~~~~

.. code:: yaml

   mynet:
    type: network
    cidr: 192.168.95.0/24

You can also use the boolean keyword *dhcp* (mostly to disable it) and isolated . When not specified, dhcp and nat will be enabled

image
~~~~~

.. code:: yaml

   CentOS-7-x86_64-GenericCloud.qcow2:
    type: image
    url: http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2

If you point to an url not ending in qcow2/qc2 (or img), your browser will be opened for you to proceed. Also note that you can specify a command with the *cmd* key, so that virt-customize is used on the template once it’s downloaded.

disk
~~~~

.. code:: yaml

   share1.img:
    type: disk
    size: 5
    pool: vms
    vms:
     - centos1
     - centos2

Here the disk is shared between two vms (that typically would be defined within the same plan):

pool
~~~~

.. code:: yaml

   mypool:
     type: pool
     path: /home/mypool

profile
~~~~~~~

.. code:: yaml

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

ansible
~~~~~~~

.. code:: yaml

   myplay:
    type: ansible
    verbose: false
    playbook: prout.yml
    groups:
      nodes:
      - node1
      - node2
      ctlplanes:
      - ctlplane1
      - ctlplane2
      - ctlplane3

An inventory will be created for you in /tmp and that *group_vars* and *host_vars* directory are taken into account. You can optionally define your own groups, as in this example. The playbooks are launched in alphabetical order

container
~~~~~~~~~

.. code:: yaml

   centos:
    type: container
     image: centos
     cmd: /bin/bash
     ports:
      - 5500
     volumes:
      - /root/coco

Look at the container section for details on the parameters

plan’s plan ( Also known as inception style)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   ovirt:
     type: plan
     url: github.com/karmab/kcli-plans/ovirt/upstream.yml
     run: true

You can alternatively provide a file attribute instead of url pointing to a local plan file:

dns
~~~

.. code:: yaml

   yyy:
    type: dns
    net: default
    ip: 192.168.1.35

workflow
~~~~~~~~

Workflow allows you to launch scripts locally after they are rendered

.. code:: yaml

   myworkflow:
     type: workflow
     scripts:
     - frout.sh
     - prout.py
     files:
     - frout.txt

This would execute the two scripts after rendering them into a temporary directory, along with the files if provided. Note that you can omit the scripts section and instead indicate the script to run as name of the workflow. This requires it to be a sh/bash script and as such beeing suffixed by .sh

vms
~~~

You can point at an existing profile in your plans, define all parameters for the vms, or combine both approaches. You can even add your own profile definitions in the plan file and reference them within the same plan:

.. code:: yaml

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

Specific scripts and IPS arrays can be used directly in the plan file (or in profiles one).

The `kcli-plan-samples repo <https://github.com/karmab/kcli-plan-samples>`__ contains samples to get you started. You will also find under karmab user dedicated plan repos to deploy ovirt, openstack, …

When launching a plan, the plan name is optional. If none is provided, a random one will be used.

If no plan file is specified with the -f flag, the file ``kcli_plan.yml`` in the current directory will be used.

When deleting a plan, the network of the vms will also be deleted if no other vm are using them. You can prevent this by setting *keepnetworks* to ``true`` in your configuration.

Remote plans
------------

You can use the following command to execute a plan from a remote url:

.. code:: yaml

   kcli create plan --url https://raw.githubusercontent.com/karmab/kcli-plan-samples/main/simpleplan.yml

Disk parameters
---------------

You can add disk this way in your profile or plan files:

.. code:: yaml

   disks:
    - size: 20
      pool: default
    - size: 10
      thin: False
      interface: scsi

Within a disk section, you can use the word size, thin and format as keys.

-  *thin* Value used when not specified in the disk entry. Defaults to true
-  *interface* Value used when not specified in the disk entry. Defaults to virtio. Could also be scsi, sata or ide, if vm lacks virtio drivers

Network parameters
------------------

You can mix simple strings pointing to the name of your network and more complex information provided as hash. For instance:

.. code:: yaml

   nets:
    - default
    - name: private
      nic: eth1
      ip: 192.168.0.220
      mask: 255.255.255.0
      gateway: 192.168.0.1

Within a net section, you can use name, nic, IP, mac, mask, gateway and alias as keys. type defaults to virtio but you can specify anyone (e1000,….).

You can also use *noconf: true* to only add the nic with no configuration done in the vm.

the *ovs: true* allows you to create the nic as ovs port of the indicated bridge. Not that such bridges have to be created independently at the moment

You can provide network configuration on the command line when creating a single vm with *-P ip1=… -P netmask1=… -P gateway=…*

ip, dns and host Reservations
-----------------------------

If you set *reserveip* to True, a reservation will be made if the corresponding network has dhcp and when the provided IP belongs to the network range.

You can set *reservedns* to True to create a dns entry for the vm in the corresponding network ( only done for the first nic).

You can set *reservehost* to True to create an entry for the host in /etc/hosts ( only done for the first nic). It’s done with sudo and the entry gets removed when you delete the vm. On macosx, you should use gnu-sed ( from brew ) instead of regular sed for proper deletion.

If you dont want to be asked for your sudo password each time, here are the commands that are escalated:

.. code:: shell

    - echo .... # KVIRT >> /etc/hosts
    - sed -i '/.... # KVIRT/d' /etc/hosts

Podman/Docker support in plans
------------------------------

Podman/Docker support is mainly enabled as a commodity to launch some containers along vms in plan files. Of course, you will need podman or docker installed on the client. So the following can be used in a plan file to launch a container:

.. code:: yaml

   centos:
    type: container
     image: centos
     cmd: /bin/bash
     ports:
      - 5500
     volumes:
      - /root/coco

The following keywords can be used:

-  *image* name of the image to pull.
-  *cmd* command to run within the container.
-  *ports* array of ports to map between host and container.
-  *volumes* array of volumes to map between host and container. You can alternatively use the keyword *disks*. You can also use more complex information provided as a hash

Within a volumes section, you can use path, origin, destination and mode as keys. mode can either be rw o ro and when origin or destination are missing, path is used and the same path is used for origin and destination of the volume. You can also use this typical docker syntax:

.. code:: yaml

   volumes:
    - /home/cocorico:/root/cocorico

Additionally, basic commands ( start, stop, console, plan, list) accept a *–container* flag.

Exposing a plan
---------------

Basic functionality
~~~~~~~~~~~~~~~~~~~

You can expose a given plan in a web fashion with ``kcli expose`` so that others can make use of some infrastructure you own without having to deal with kcli themseleves.

The user will be presented with a simple UI (running on port 9000) with a listing of the current vms of the plan and buttons allowing to either get info on the plan, delete or reprovision it.

To expose your plan (with an optional list of parameters):

::

   kcli expose plan -f your_plan.yml -P param1=value1 -P param2=value plan_name

The indicated parameters are the ones from the plan that you want to expose to the user upon provisioning, with a provided default value that they’ll be able to overwrite.

When the user reprovisions, In addition to those parameters, he will be able to specify:

-  a list of mail addresses to notify upon completion of the lab provisioning. Note it requires to properly set notifications in your kcli config.
-  an optional owner which will be added as metadata to the vms, so that it’s easy to know who provisioned a given plan

Precreating a list of plans
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you’re running the same plan with different parameter files, you can simply create below the directory where your plan lives, naming them parameters_XXX.yml|yaml. The UI will then show you those as separated plans so that they can be provisioned individually applying the corresponding values from the parameter files (after merging them with the user provided data).

Using several clients
~~~~~~~~~~~~~~~~~~~~~

When specifying different parameter files, you can include the ``client`` keyword to target a given client The code will then select the proper client for create/delete/info operations.

Using expose feature from a web server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use mod_wsgi with httpd or similar mechanisms to use the expose feature behind a web server so that you serve content from a specific port or add layer of security like htpasswd provided from outside the code.

For instance, you could create the following kcli.conf in apache

::

   <VirtualHost *>
       WSGIScriptAlias / /var/www/kcli.wsgi
       <Directory /var/www/kcli>
           Order deny,allow
           Allow from all
       </Directory>
   #    <Location />
   #   AuthType Basic
   #   AuthName "Authentication Required"
   #   AuthUserFile "/var/www/kcli.htpasswd"
   #   Require valid-user
   #    </Location>
   </VirtualHost>

::

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

Note that further configuration will tipically be needed for apache user so that kcli can be used with it.

An alternative is to create different WSGI applications and tweak the *WSGIScriptAlias* to serve them from different paths.

Calling expose endpoints through REST
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

you can check the `swagger spec <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/karmab/kcli/main/kvirt/expose/swagger.yml>`__ to call the different endpoints using your language of choice.

Overriding parameters
=====================

You can override parameters in:

-  commands
-  scripts
-  files
-  plan files
-  profiles

For that, you can pass in kcli vm or kcli plan the following parameters:

-  -P x=1 -P y=2 and so on .
-  –paramfile - In this case, you provide a yaml file ( and as such can provide more complex structures ).

Note that parameters provided as uppercase are made environment variables within the target vm by creating ``/etc/profile.d/kcli.sh``

The indicated objects are then rendered using jinja.

::

   centos:
    template: CentOS-7-x86_64-GenericCloud.qcow2
    cmds:
     - echo x={{ x }} y={{ y }} >> /tmp/cocorico.txt
     - echo {{ password | default('unix1234') }} | passwd --stdin root

You can make the previous example cleaner by using the special key parameters in your plans and define there variables:

::

   parameters:
    password: unix1234
    x: coucou
    y: toi
   centos:
    template: CentOS-7-x86_64-GenericCloud.qcow2
    cmds:
     - echo x={{ x }} y={{ y }} >> /tmp/cocorico.txt
     - echo {{ password  }} | passwd --stdin root

Finally note that you can also use advanced jinja constructs like conditionals and so on. For instance:

::

   parameters:
     net1: default
   vm4:
     template: CentOS-7-x86_64-GenericCloud.qcow2
     nets:
       - {{ net1 }}
   {% if net2 is defined %}
       - {{ net2 }}
   {% endif %}

Also, you can reference a *baseplan* file in the *parameters* section, so that parameters are concatenated between the base plan file and the current one:

::

   parameters:
      baseplan: upstream.yml
      xx_version: v0.7.0

Keyword Parameters
==================

Specific parameters for a client
--------------------------------

=============== ============= ====================================================
Parameter       Default Value Comments
=============== ============= ====================================================
*host*          127.0.0.1     
*port*                        Defaults to 22 if ssh protocol is used
*user*          root          
*protocol*      ssh           
*url*                         can be used to specify an exotic qemu url
*tunnel*        False         make kcli use tunnels for console and for ssh access
*keep_networks* False         make kcli keeps networks when deleting plan
=============== ============= ====================================================

Available parameters for client/profile/plan files
--------------------------------------------------

================== ==================================== =====================================================================================================================================================================================================================================================================================================================
Parameter          Default Value                        Comments
================== ==================================== =====================================================================================================================================================================================================================================================================================================================
*client*           None                                 Allows to target a different client/host for the corresponding entry
*virttype*         None                                 Only used for libvirt where it evaluates to kvm if acceleration shows in capabilities, or qemu emulation otherwise. If a value is provided, it must be either kvm, qemu, xen or lxc
*cpumodel*         host-model                           
*cpuflags*         []                                   You can specify a list of strings with features to enable or use dict entries with *name* of the feature and *policy* either set to require,disable, optional or force. The value for vmx is ignored, as it’s handled by the nested flag
*numcpus*          2                                    
*cpuhotplug*       False                                
*numamode*         None                                 numamode to apply to the workers only.
*cpupinning*       []                                   cpupinning conf to apply
*memory*           512M                                 
*memoryhotplug*    False                                
*flavor*                                                Specific to gcp, aws, openstack and packet
*guestid*          guestrhel764                         
*pool*             default                              
*image*            None                                 Should point to your base cloud image(optional). You can either specify short name or complete path. If you omit the full path and your image lives in several pools, the one from last (alphabetical) pool will be used\\
*diskinterface*    virtio                               You can set it to ide, ssd or nvme instead
*diskthin*         True                                 
*disks*            []                                   Array of disks to define. For each of them, you can specify pool, size, thin (as boolean), interface (either ide or virtio) and a wwn.If you omit parameters, default values will be used from config or profile file (You can actually let the entire entry blank or just indicate a size number directly)
*iso*              None                                 
*nets*             []                                   Array of networks to define. For each of them, you can specify just a string for the name, or a dict containing name, public and alias and ip, mask and gateway, and bridge. Any visible network is valid, in particular bridge networks can be used on libvirt, beyond regular nat networks
*gateway*          None                                 
*dns*              None                                 Dns server
*domain*           None                                 Dns search domain
*start*            true                                 
*vnc*              false                                if set to true, vnc is used for console instead of spice
*cloudinit*        true                                 
*reserveip*        false                                
*reservedns*       false                                
*reservehost*      false                                
*keys*             []                                   Array of ssh public keys to inject to the vm. Whether the actual content or the public key path
*cmds*             []                                   Array of commands to run
*profile*          None                                 name of one of your profile
*scripts*          []                                   array of paths of custom script to inject with cloudinit. It will be merged with cmds parameter. You can either specify full paths or relative to where you’re running kcli. Only checked in profile or plan file
*nested*           True                                 
*sharedkey*        False                                Share a private/public key between all the nodes of your plan. Additionally, root access will be allowed
*privatekey*       False                                Inject your private key to the nodes of your plan
*files*            []                                   Array of files to inject to the vm. For each of them, you can specify path, owner ( root by default) , permissions (600 by default ) and either origin or content to gather content data directly or from specified origin. When specifying a directory as origin, all the files it contains will be parsed and added
*insecure*         True                                 Handles all the ssh option details so you don’t get any warnings about man in the middle
*client*           None                                 Allows you to create the vm on a specific client. This field is not used for other types like network
*base*             None                                 Allows you to point to a parent profile so that values are taken from parent when not found in the current profile. Scripts and commands are rather concatenated between default, father and children
*tags*             []                                   Array of tags to apply to gcp instances (usefull when matched in a firewall rule). In the case of kubevirt, it s rather a dict of key=value used as node selector (allowing to force vms to be scheduled on a matching node)
*networkwait*      0                                    Delay in seconds before attempting to run further commands, to be used in environments where networking takes more time to come up
*rhnregister*      None                                 Auto registers vms whose template starts with rhel Defaults to false. Requires to either rhnuser and rhnpassword, or rhnactivationkey and rhnorg, and an optional rhnpool
*rhnserver*        https://subscription.rhsm.redhat.com Red Hat Network server (for registering to a Satellite server)
*rhnuser*          None                                 Red Hat Network user
*rhnpassword*      None                                 Red Hat Network password
*rhnactivationkey* None                                 Red Hat Network activation key
*rhnorg*           None                                 Red Hat Network organization
*rhnpool*          None                                 Red Hat Network pool
*enableroot*       true                                 Allows ssh access as root user
*rootpassword*     None                                 Root password to inject (when beeing to lazy to use a cmd to set it)
*storemetadata*    false                                Creates a /root/.metadata yaml file whith all the overrides applied. On gcp, those overrides are also stored as extra metadata
*sharedfolders*    []                                   List of paths to share between hypervisor and vm. You will also need to make sure that the path is accessible as qemu user (typically with id 107) and use an hypervisor and a guest with 9p support (centos/rhel lack it for instance)
*yamlinventory*    false                                Ansible generated inventory for single vms or for plans containing ansible entries will be yaml based.
*autostart*        false                                Autostarts vm (libvirt specific)
*kernel*           None                                 Kernel location to pass to the vm. Needs to be local to the hypervisor
*initrd*           None                                 Initrd location to pass to the vm. Needs to be local to the hypervisor
*cmdline*          None                                 Cmdline to pass to the vm
*pcidevices*       []                                   array of pcidevices to passthrough to the first worker only. Check `here <https://github.com/karmab/kcli-plan-samples/blob/main/pcipassthrough/pci.yml>`__ for an example
*tpm*              false                                Enables a TPM device in the vm, using emulator mode. Requires swtpm in the host
*rng*              false                                Enables a RNG device in the vm
*notify*           false                                Sends result of a command or a script run from the vm to one of the supported notify engines
*notifymethod*     [pushbullet]                         Array of notify engines. Other options are slack and mail
*notifycmd*        None                                 Which command to run for notification. If none is provided and no notifyscript either, defaults to sending last 100 lines of the cloudinit file of the machine, or ignition for coreos based vms
*notifyscript*     None                                 Script to execute on the vm and whose output will be sent to notification engines
*pushbullettoken*  None                                 Token to use when notifying through pushbullet
*slacktoken*       None                                 Token to use when notifying through slack. Should be the token of an app generated in your workspace
*slackchannel*     None                                 Slack Channel where to send the notification
*mailserver*       None                                 Mail server where to send the notification (on port 25)
*mailfrom*         None                                 Mail address to send mail from
*mailto*           []                                   List of mail addresses to send mail to
*zerotier_net*     []                                   List of zerotier public networks where to join. Will trigger installation of zerotier on the node
*zerotier_kubelet* False                                Whether to configure kubelet to use the first zerotier address as node ip
*playbook*         False                                Generates a playbook for the vm of the plan instead of creating it. Useful to run parts of a plan on baremetal
*vmrules*          []                                   List of rules with an associated dict to apply for the corresponding entry, if a regex on the entry name is matched. The profile of the matching vm will be updated with the content of the rule
*wait*             False                                Whether to wait for cloudinit/ignition to fully apply
*waitcommand*      None                                 a specific command to use to validate that vm is ready
*waittimeout*      0                                    Timeout when waiting for a vm to be ready. Default zero value means the wait wont timeout
================== ==================================== =====================================================================================================================================================================================================================================================================================================================

Ansible support
===============

klist.py is provided as a dynamic inventory for ansible.

The script uses sames conf as kcli (and as such defaults to local if no configuration file is found).

vms will be grouped by plan, or put in the kvirt group if they dont belong to any plan.

Try it with:

.. code:: shell

   klist.py --list
   KLIST=$(which klist.py)
   ansible all -i $KLIST -m ping

If you’re using kcli as a container, you will have to create a script such as the following to properly call the inventory.

::

   #!/bin/bash
   podman run -it --security-opt label:disable -v ~/.kcli:/root/.kcli -v /var/run/libvirt:/var/run/libvirt --entrypoint=/usr/bin/klist.py karmab/kcli $@

Additionally, there are ansible kcli modules in `ansible-kcli-modules <https://github.com/karmab/ansible-kcli-modules>`__ repository, with sample playbooks:

-  kvirt_vm allows you to create/delete vm (based on an existing profile or a template)
-  kvirt_plan allows you to create/delete a plan
-  kvirt_product allows you to create/delete a product (provided you have a product repository configured)
-  kvirt_info allows you to retrieve a dict of values similar to ``kcli info`` output. You can select which fields to gather

Those modules rely on python3 so you will need to pass ``-e 'ansible_python_interpreter=path_to_python3'`` to your ansible-playbook invocations ( or set it in your inventory) if your default ansible installation is based on python2.

Both kvirt_vm, kvirt_plan and kvirt_product support overriding parameters:

::

   - name: Deploy fission with additional parameters
     kvirt_product:
       name: fission
       product: fission
       parameters:
        fission_type: all

Finally, you can use the key ansible within a profile:

.. code:: yaml

   ansible:
    - playbook: frout.yml
      verbose: true
      variables:
       - x: 8
       - z: 12

In a plan file, you can also define additional sections with the ansible type and point to your playbook, optionally enabling verbose and using the key hosts to specify a list of vms to run the given playbook instead.

You wont define variables in this case, as you can leverage host_vars and groups_vars directory for this purpose.

.. code:: yaml

   myplay:
    type: ansible
    verbose: false
    playbook: prout.yml

When leveraging ansible this way, an inventory file will be generated on the fly for you and let in */tmp/$PLAN.inv*.

You can set the variable yamlinventory to True at default, host or profile level if you want the generated file to be yaml based. In this case, it will be named */tmp/$PLAN.inv.yaml*.

Using products
==============

To easily share plans, you can make use of the products feature which leverages them:

Repos
-----

First, add a repo containing a KMETA file with yaml info about products you want to expose. For instance, mine

::

   kcli create repo -u https://github.com/karmab/kcli-plans karmab

You can also update later a given repo, to refresh its KMETA file ( or all the repos, if not specifying any)

::

   kcli update repo REPO_NAME

You can delete a given repo with

::

   kcli delete repo REPO_NAME

Product
-------

Once you have added some repos, you can list available products, and get their description

::

   kcli list products 

You can also get direct information on the product (memory and cpu used, number of vms deployed and all parameters that can be overriden)

::

   kcli info product YOUR_PRODUCT 

And deploy any product. Deletion is handled by deleting the corresponding plan.

::

   kcli create product YOUR_PRODUCT

Deploying kubernetes/openshift clusters
=======================================

You can deploy generic kubernetes (based on kubeadm), k3s, kind, openshift/okd, hypershift and microshift on any platform and on an arbitrary number of control plane nodes and workers. The cluster can be scaled afterwards if needed.

Getting information on available parameters
-------------------------------------------

For each supported platform, you can use ``kcli info cluster``

For instance, ``kcli info cluster generic`` will provide you all the parameters available for customization for generic kubernetes clusters.

Deploying generic kubernetes clusters
-------------------------------------

::

   kcli create cluster generic -P ctlplanes=X -P workers=Y $cluster

Deploying openshift clusters
----------------------------

*DISCLAIMER*: This is not supported in anyway by Red Hat (although the end result cluster would be).

for Openshift, the official installer is leveraged with kcli creating the vms, and injecting some extra pods to provide api/ingress vip and self contained dns.

The benefits of deploying Openshift with this workflow are:

-  Auto download openshift-install binary specified version.
-  Easy vms tuning.
-  Single workflow regardless of the target platform
-  Self contained dns. (For cloud platforms, cloud public dns is leveraged instead)
-  For libvirt, no need to compile installer or tweak libvirtd.
-  Vms can be connected to a physical bridge.
-  Multiple clusters can live on the same l2 network.
-  Support for disconnected registry and ipv6 networks

Requirements
~~~~~~~~~~~~

-  Valid pull secret (for downstream)
-  Ssh public key.
-  Write access to /etc/hosts file to allow editing of this file.
-  An available ip in your vm’s network to use as *api_ip*. Make sure it is excluded from your dhcp server. An optional *ingress_ip* can be specified, otherwise api_ip will be used.
-  Direct access to the deployed vms. Use something like this otherwise ``sshuttle -r your_hypervisor 192.168.122.0/24 -v``).
-  Target platform needs:

   -  Ignition support

      -  (for Ovirt/Rhv, this means >= 4.4).
      -  For Libvirt, support for fw_cfg in qemu (install qemu-kvm-ev on centos for instance).

   -  On Openstack:

      -  swift available on the install.
      -  a flavor. You can create a dedicated one with ``openstack flavor create --id 6 --ram 32768 --vcpus 16 --disk 30 m1.openshift``
      -  a port on target network mapped to a floating ip. If not specified with api_ip and public_api_ip parameters, the second-to-last ip from the network will be used.

-  For ipv6, you need to run the following sysctl ``net.ipv6.conf.all.accept_ra=2``

How to Use
~~~~~~~~~~

Create a parameters.yml
^^^^^^^^^^^^^^^^^^^^^^^

Prepare a parameter file with valid variables:

A minimal one could be the following one

::

   cluster: mycluster
   domain: karmalabs.corp
   version: stable
   tag: '4.8'
   ctlplanes: 3 
   workers: 2
   memory: 16384
   numcpus: 16

Here’s the list of all variables that can be used (you can list them with ``kcli info cluster openshift``)

======================= ================================== ========================================================================================================
Parameter               Default Value                      Comments
======================= ================================== ========================================================================================================
*version*               nightly                            You can choose between nightly, ci or stable. ci requires specific data in your secret
tag                     4.5                                
async                   false                              Exit once vms are created and let job in cluster delete bootstrap
notify                  false                              Whether to send notifications once cluster is deployed. Mean to be used in async mode
pull_secret             openshift_pull.json                
image                   rhcos45                            rhcos image to use (should be qemu for libvirt/kubevirt and openstack one for ovirt/openstack)
helper_image            CentOS-7-x86_64-GenericCloud.qcow2 which image to use when deploying temporary helper vms
network                 default                            Any existing network can be used
api_ip                  None                               
ingress_ip              None                               
ctlplanes               1                                  number of ctlplane
workers                 0                                  number of workers
fips                    False                              
cluster                 testk                              
domain                  karmalabs.corp                     
network_type            OpenShiftSDN                       
minimal                 False                              
pool                    default                            
flavor                  None                               
flavor_bootstrap        None                               
flavor_ctlplane         None                               
flavor_worker           None                               
numcpus                 4                                  
bootstrap_numcpus       None                               
ctlplane_numcpus        None                               
worker_numcpus          None                               
memory                  8192                               
bootstrap_memory        None                               
ctlplane_memory         None                               
worker_memory           None                               
disk_size               30                                 disk size in Gb for final nodes
keys                    []                                 
apps                    []                                 
extra_disks             []                                 
extra_ctlplane_disks    []                                 
extra_worker_disks      []                                 
extra_networks          []                                 
extra_ctlplane_networks []                                 
extra_worker_networks   []                                 
bootstrap_mac           None                               
disconnected_url        None                               
disconnected_user       None                               
disconnected_password   None                               
imagecontentsources     []                                 
ca                      None                               optional string of certificates to trust
ipv6                    False                              
baremetal               False                              Whether to also deploy the metal3 operator, for provisioning physical workers
baremetal_machine_cidr  None                               
provisioning_net        provisioning                       
provisioning_nic        ens4                               
cloud_tag               None                               
cloud_scale             False                              
cloud_api_internal      False                              
apps                    []                                 Extra applications to deploy on the cluster, available ones are visible with ``kcli list app openshift``
======================= ================================== ========================================================================================================

Deploying
^^^^^^^^^

::

   kcli create kube openshift --paramfile parameters.yml $cluster

-  You will be asked for your sudo password in order to create a /etc/hosts entry for the api vip.

-  Once that finishes, set the following environment variable in order to use oc commands ``export KUBECONFIG=$HOME/.kcli/clusters/$cluster/auth/kubeconfig``

Providing custom machine configs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a ``manifests`` directory exists in the current directory, the \*yaml assets found there are copied to the directory generated by the install, prior to deployment.

Architecture
~~~~~~~~~~~~

On kubeadm
^^^^^^^^^^

the generic cluster workflow leverages Kubeadm to create a cluster with the specified number of vms running either as ctlplanes or workers on any of the supported platforms.

Those vms can either be centos8 or ubuntu based (as per the official Kubeadm doc).

The first node is used for bootstrapping the cluster, through commands that are run by rendering cloudinit data.

Once it is finished, the generated token is retrieved, which allows to add additional controle plane nodes or workers (and later on scale if needed).

for HA and Loadbalancing, Keepalived and Haproxy are leveraged, which involves declaring a vip. With Libvirt and when no vip is provided, an educated guess around the vip is done when using a virtual network.

For the cloud providers (aws, gcp and ibmcloud), loadbalancer along with dns is used instead to achieve the same result. That does require specifying an existing top level domain.

There are a lot of available options in this workflow, whether it’s:

-  customizing the hardware of the involved vms
-  using a different k8s version, cni or engine
-  deploying nfs, nginx ingress or metallb.
-  etc

All the parameters can be seen with ``kcli info cluster generic``

On libvirt/ovirt/vsphere/kubevirt/openstack
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We deploy :

-  a bootstrap node removed at the end of the install.
-  an arbitrary number of ctlplanes.
-  an arbitrary number of workers.

When oc or openshift-install are missing, they are downloaded on the fly, using public mirrors or registry.ci.openshift.org if ci is specified (the provided pull secret needs an auth for this registry).

rhcos image associated to the specified version is downloaded and the corresponding line is added in the parameter file unless an image is specified as parameter.

Ignition files needed for the install are generated using ``openshift-install create ignition-configs``

Also note that for bootstrap, ctlplanes and workers nodes, we merge the ignition data generated by the openshift installer with the ones generated by kcli, in particular we prepend dns server on those nodes to point to our keepalived vip, force hostnames and inject static pods.

Deployment of bootstrap and ctlplanes vms is then launched. Isos are optionally created for baremetal hosts

Keepalived and Coredns with mdns are deployed on the bootstrap and ctlplane nodes as static pods. They provide HA access and dns records as needed.

Initially, the api vip runs on the bootstrap node.

Ignition files are provided over 22624/http using api ip instead of fqdn. The ignition files for both ctlplane and worker are patched for it.

Haproxy is created as static pod on the ctlplane nodes to load balance traffic to the routers. When there are no workers, routers are instead scheduled on the ctlplane nodes and the haproxy static pod isn’t created, so routers are simply accessed through the vip without load balancing in this case.

Once bootstrap steps finished, the vips transitions to one of the ctlplanes.

At this point, workers are created and the installation is monitored until completion. A flag allows to deploy in an async manner

It’s possible to scale ctlplanes or workers after the initial installation, using ``kcli scale cluster openshift`` (Instead of scaling machines as done in IPI workflows)

On aws/gcp/ibmcloud
^^^^^^^^^^^^^^^^^^^

On those platforms, We rely on dns and load balancing services and as such dont need static pods.

In the case of deploying a single ctlplane, a flag allows to get rid of the loadbalancer at the end of the install.

SNO (single node openshift ) support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can deploy a single node setting ctlplanes to 1 and workers to 0 in your parameter file. On Cloud platforms, you can use an extra parameter, ``sno_cloud_remove_lb``, to remove loadbalancer and point dns directly to the public ip of your node, making the resulting cluster only rely on the corresponding instance.

Alternatively, you can leverage bootstrap in place (bip) and rhcos live iso with the flag ``sno``, which allows you to provision a baremetal sno by creating a custom iso stored in your specified libvirt pool. The following extra parameters are available with this workflow:

-  sno_disk: You can indicate which disk to use for installing Rhcos operating system in your node. If none is specified, the disk will be autodiscovered
-  sno_dns: Defaults to true. A static pod leveraging coredns and pointing the relevant dns records to the ip of the node is injected after ctlplane ignition is generated, removing the need for external dns. Use this if you can’t provide the DNS requirements for the single node
-  extra_args: You can use this variable to specify as a string any extra args to add to the generated iso. A common use case for this is to set static networking for the node, for instanc with something like ``ip=192.168.1.200::192.168.1.1:255.255.255.0:mysupersno.dev.local:enp1s0:none nameserver=192.168.1.1``
-  api_ip: This is normally not needed but if you already have some DNS records in place pointing to a given api vip or you don’t know your baremetal ip, you can specify the vip so that an extra keepalived static pod is injected.

In the baremetal context, you are normally responsible for attaching the generated iso to your target node but you can also use the ``baremetal_hosts`` feature described below, you will need to have apache running on the hypervisor and give write access to /var/www/html for the user launching the command, using something like the following

::

   sudo setfacl -m u:$(id -un):rwx /var/www/html

Adding more workers
~~~~~~~~~~~~~~~~~~~

The procedure is the same independently of the type of cluster used.

::

   kcli scale kube <generic|openshift|okd|k3s> -P workers=num_of_workers --paramfile parameters.yml $cluster

Generating a worker iso
~~~~~~~~~~~~~~~~~~~~~~~

In openshift case, for baremetal workers you can use the following command to generate such an iso

::

   kcli create openshift-iso --paramfile parameters.yml $cluster

Interacting with your clusters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All generated assets for a given cluster are stored in ``$HOME/.kcli/clusters/$cluster``.

In particular, the kubeconfig file to use to interact with the cluster is stored at ``$HOME/.kcli/clusters/$cluster/auth/kubeconfig``

Cleaning up
~~~~~~~~~~~

The procedure is the same independently of the type of cluster used.

::

   kcli delete kube $cluster

Baremetal hosts support
~~~~~~~~~~~~~~~~~~~~~~~

You can deploy baremetal workers in different way through this workflow.

The boolean baremetal_iso can be set to generate isos that you manually plug to the corresponding node (one iso per role).

You can also create isos only for a given role using the boolean baremetal_iso_bootstrap, baremetal_iso_ctlplane and baremetal_iso_worker

Alternatively, you can use the array baremetal_hosts to plug the worker iso to a list of baremetal hosts. The iso will be served from a deployment running in the control plane in that case.

For each entry you would specify:

-  url or bmc_url. This is the redfish url to use, which is specific to the hardware. You can also just specify the ip and set the model if you dont know what the exact url is.
-  user or bmc_user. bmc_user can also be set outside the array if you use the same user for all of your baremetal workers
-  password or bmc_password. bmc_password can also be set outside the array if you use the same password for all of your baremetal workers
-  Optionally model or bmc_model (either dell,hp, supermicro) to have the bmc_url evaluated for you (Only specify its ip in this case)

As an example, the following array will boot 3 workers (based on kvm vms with sushy tool)

::


   bmc_user: root
   bmc_password: calvin
   baremetal_hosts:
   - bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
   - bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2
   - bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/bm3

Disconnected support
~~~~~~~~~~~~~~~~~~~~

To deploy with a disconnected registry, you can set the ``disconnected_deploy`` boolean or specify a ``disconnected_url``

disconnected_deploy
^^^^^^^^^^^^^^^^^^^

In the first case, an helper vm will be deployed to host your disconnected registry and content will be synced for you

You can fine tweak this registry with several parameters:

-  disconnected_disk_size
-  disconnected_user
-  disconnected_password
-  disconnected_operators
-  …

Note that this disconnected registry can also be deployed on its own using ``kcli create openshift-registry`` subcommand

disconnected_url
^^^^^^^^^^^^^^^^

In this case, you can specify the url of the registry where you have synced content by yourself. The ``disconnected_url`` typically is specified as ``$host:$port``

You will also need to set disconnected_user and disconnected_password

You can specify disconnected_ca content, or let it undefined for the CA content to be fetched on the fly

The default prefix where the ocp content is expected to be synced is ocp4, but you can use the parameter ``disconnected_prefix``\ to specify a different one

Note that you will also need to sync the following images on the registry:

-  quay.io/karmab/curl:latest
-  quay.io/karmab/origin-coredns:latest
-  quay.io/karmab/haproxy:latest
-  quay.io/karmab/origin-keepalived-ipfailover:latest
-  quay.io/karmab/mdns-publisher:latest
-  quay.io/karmab/kubectl:latest
-  quay.io/karmab/kcli:latest

Deploying applications on top of kubernetes/openshift
=====================================================

You can use kcli to deploy applications on your kubernetes/openshift (regardless of whether it was deployed with kcli)

Applications such as the following one are currently supported:

-  argocd
-  kubevirt
-  rook
-  istio
-  knative
-  tekton

To list applications available on generic kubernetes, run:

::

   kcli list app generic

To list applications available on generic openshift, run:

::

   kcli list app openshift

For any of the supported applications, you can get information on the supported parameters with:

::

   kcli info app generic|openshift $app_name

To deploy an app, use the following, with additional parameters passed in the command line or in a parameter file:

::

   kcli create app generic|openshift $app_name

Applications can be deleted the same way:

::

   kcli delete app generic|openshift $app_name

Running on kubernetes/openshift
===============================

You can run the container on those platforms and either use the web interface or log in the pod to run ``kcli`` commandline

On openshift, you’ll need to run first those extra commands:

::

   oc new-project kcli
   oc adm policy add-scc-to-user anyuid system:serviceaccount:kcli:default
   oc expose svc kcli

Then:

::

   kubectl create configmap kcli-config --from-file=~/.kcli
   kubectl create configmap ssh-config --from-file=~/.ssh
   kubectl create -f https://raw.githubusercontent.com/karmab/kcli/main/extras/k8sdeploy.yml

kcli-controller
===============

There is a controller leveraging kcli and using vm, plan and clusters crds to create vms the corresponding objects, regardless of the infrastructure.

Requisites
----------

-  a running kubernetes/openshift cluster and KUBECONFIG env variable pointing to it (or simply .kube/config)
-  some infrastructure supported by kcli running somewhere and the corresponding credentials.
-  storage to hold two pvcs (one from plan files data and the other for clusters data)

.. _deploying-1:

Deploying
---------

If you’re running kcli locally, use the following to create the proper configmaps to share your credentials and ssh keys:

::

   kcli sync kube

To do the same manually, run instead:

::

   kubectl create configmap kcli-config --from-file=$HOME/.kcli
   kubectl create configmap ssh-config --from-file=$HOME/.ssh

Then deploy the controller (along with its CRDS):

::

   kubectl create -f https://raw.githubusercontent.com/karmab/kcli/main/extras/controller/deploy.yml

If you want to use a pvc named ``kcli-clusters`` for storing cluster data, add it:

::

   kubectl -n kcli-infra patch deploy kcli-controller --type json -p='[{"op": "add", "path": "/spec/template/spec/containers/0/volumeMounts/-", "value": {"mountPath": "/root/.kcli/clusters", "name": "kcli-clusters"}}, {"op": "add", "path": "/spec/template/spec/volumes/-", "value": {"persistentVolumeClaim": {"claimName" : "kcli-clusters"}, "name": "kcli-clusters"}}]'

.. _how-to-use-1:

How to use
----------

The directory `extras/controller/examples <https://github.com/karmab/kcli/tree/main/extras/controller/examples>`__ contains different examples of vm, plan and cluster CRs.

Here are some sample ones for each type to get you started

.. _vms-1:

vms
~~~

::

   apiVersion: kcli.karmalabs.local/v1
   kind: Vm
   metadata:
     name: cirros
   spec:
     image: cirros
     memory: 512
     numcpus: 2

Note that when a vm is created, the controller waits before it gets an ip and populate it status with its complete information, which is then formatted when running ``kubectl get vms``

.. _plans-1:

plans
~~~~~

::

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

To run plans which contain scripts or files, you ll need to copy those assets in the /workdir of the kcli pod

::

   KCLIPOD=$(kubectl get pod -o name -n kcli | sed 's@pod/@@')
   kubectl cp samplecrd/frout.txt $KCLIPOD:/workdir

clusters
~~~~~~~~

::

   apiVersion: kcli.karmalabs.local/v1
   kind: Cluster
   metadata:
     name: hendrix
   spec:
     ctlplanes: 1
     api_ip: 192.168.122.252

Once a cluster is deployed successfully, you can retrieve its kubeconfig from it status

::

   kubectl get cluster $CLUSTER -o jsonpath='{.status.create_cluster.kubeconfig}' | base64 -d

autoscaling
^^^^^^^^^^^

You can enable autoscaling for a given cluster by setting ``autoscale`` to any value in its spec.

Scaling up
''''''''''

When more than a given threshold of pods can’t be scheduled, one more worker will be added to the cluster and the autoscaling will pause until it appears as a new ready node.

This threshold is configured as an env variable AUTOSCALE_MAXIMUM provided during the deployment of the controller, which defaults to 20

Setting the threshold to any value higher than 9999 effectively disables the feature.

Scaling down
''''''''''''

If the number of running pods for a given worker node goes below a minimum value, the cluster will be scaled down by one worker.

The minimum is configured as an env variable AUTOSCALE_MINIMUM provided during the deployment of the controller, which defaults to 2

Setting the minimum to any value below 1 effectively disables the feature.

Configuration pools
===================

Configuration pools allow to store a list of ips, names or baremetal_hosts and make them available to a vm or a cluster upon deployment.

This provides the following features:

-  Provide static ip to vms from a self maintained list of ips
-  Provide vip to clusters in the same manner
-  Provide a list of baremetal_hosts to clusters.
-  Provide names to vms or clusters from a specific list

Upon creation, the corresponding entry gets reserved to the vm or the cluster and released upon deletion.

Handling confpools
------------------

You can use ``kcli create confpool`` commands to create a configuration pool and then use list, update or delete calls.

Under the hood, all the pools are stored in ``~/.kcli/confpools.yml`` so this file can also be edited manually.

confpool typically contain ips, baremetal information or both.

Here’s a sample content of this file

::

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

confpool with ips information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a confpool with 3 ips, use the following

::

   kcli create confpool myconfpool -P ips=[192.168.122.250,192.168.122.251,192.168.122.252 -P netmask=24 -P gateway=192.168.122.1

For ips, note you can also provide a cidr such as 192.168.122.0/24

the pool can also store any value, some of which will be evaluated (in particular any of the network keywords such as netmask,gateway as shown in the example)

confpool with baremetal_hosts information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a confpool with 2 baremetal hosts, use the following

::

   kcli create myconfpool -P baremetal_hosts=[http://192.168.122.1:9000/redfish/v1/Systems/vm1,http://192.168.122.1:9000/redfish/v1/Systems/local/vm2] -P bmc_user=admin -P bmc_password=admin0

Note that in this case, we also provide bmc credentials, all the hosts in your pool should share the same credentials.

confpool with names information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a confpool with some DBZ names, use the following

::

   kcli create dbzpool -P names=[gohan,goku,vegeta,picolo,raditz,tenchinhan]

Using the confpool
------------------

In vms
~~~~~~

For vms, the confpool is typically specified in a nets section to consume ips. For instance

::

   kcli create vm -i centos8stream -P nets=['{"name": "default", "confpool": "myconfpool"}']

You can also create a vm with a name from the previously created dbz name confpool with the following call

::

   kcli create vm -i centos8stream -P confpool=dbzpool

In clusters
~~~~~~~~~~~

When creating the cluster, specify through a parameter which pool to use (``-P confpool=mypool``)

::

   kcli create cluster generic -P confpool=mypool

Using several confpools at once
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to use several pools when creating a vm/cluster, you can be more specific by using the following aliases:

-  ippool
-  namepool
-  baremetalpool

For instance, you could do something like

::

   kcli create vm -i centos8stream -P ippool=ippool -P namepool=dbzpool

   # Using Jenkins

   ## Requisites

   - Jenkins running somewhere, either:
      - standalone
      - on K8s/Openshift
   - Docker running if using this backend
   - Podman installed if using this backend

   ## Credentials

   First, create the following credentials in Jenkins as secret files:

   - kcli-config with the content of your ~/.kcli/config.yml
   - kcli-id-rsa with your ssh private key
   - kcli-id-rsa-pub with your ssh public key

   You can use arbitrary names for those credentials, but you will then have to either edit Jenkinsfile later or specify credentials when running your build.

   ## Kcli configuration

   Default backend is *podman* . If you want to use Docker or Kubernetes instead, add the corresponding snippet in *~/.kcli/config.yml*.

   For instance, for Kubernetes:

jenkinsmode: kubernetes

::


   ## Create Jenkins file

   Now you can create a Jenkinsfile from your specific, or from default *kcli_plan.yml*

kcli create pipeline

::


   You can see an example of the generated Jenkinsfile for both targets from the sample plan provided in this directory.

   Parameters from the plan get converted in Jenkins parameters, along with extra parameters:
   - for needed credentials (kcli config file, public and private ssh key)
   - a `wait` boolean to indicated whether to wait for plan completion upon run.
   - a `kcli_client` parameter that can be used to override the target client where to launch plan at run time.

   Your Jenkinsfile is ready for use!

   ## Openshift

   You can create credentials as secrets and tag them so they get synced to Jenkins:

oc create secret generic kcli-config-yml –from-file=filename=config.yml oc annotate secret/kcli-config-yml jenkins.openshift.io/secret.name=kcli-config-yml oc label secret/kcli-config-yml credential.sync.jenkins.openshift.io=true

oc create secret generic kcli-id-rsa –from-file=filename=~/.ssh/id_rsa oc annotate secret/kcli-id-rsa jenkins.openshift.io/secret.name=kcli-id-rsa oc label secret/kcli-id-rsa credential.sync.jenkins.openshift.io=true

oc create secret generic kcli-id-rsa-pub –from-file=filename=$HOME/.ssh/id_rsa.pub oc annotate secret/kcli-id-rsa-pub jenkins.openshift.io/secret.name=kcli-id-rsa-pub oc label secret/kcli-id-rsa-pub credential.sync.jenkins.openshift.io=true

::


   You will also need to allow *anyuid* scc for kcli pod, which can be done with the following command (adjust to your project):

PROJECT=kcli oc adm policy add-scc-to-user anyuid system:serviceaccount:$PROJECT:default

::


   # Auto Completion

   You can enable autocompletion if running kcli from package or pip. It's enabled by default when running kclishell container alias

   ## Bash/Zsh

   Add the following line in one of your shell files (.bashrc, .zshrc, ...)

eval “$(register-python-argcomplete kcli)”

::


   ## Fish

   Add the following snippet in *.config/fish/config.fish*

function \__fish_kcli_complete set -x \_ARGCOMPLETE 1 set -x \_ARGCOMPLETE_IFS :raw-latex:`\n` set -x \_ARGCOMPLETE_SUPPRESS_SPACE 1 set -x \_ARGCOMPLETE_SHELL fish set -x COMP_LINE (commandline -p) set -x COMP_POINT (string length (commandline -cp)) set -x COMP_TYPE if set -q \_ARC_DEBUG kcli 8>&1 9>&2 1>/dev/null 2>&1 else kcli 8>&1 9>&2 1>&9 2>&1 end end complete -c kcli -f -a
’(__fish_kcli_complete)’

::


   # Api Usage

   ## Locally

   You can also use kvirt library directly, without the client or to embed it into your own application.

   Here's a sample:

from kvirt.config import Kconfig config = Kconfig() k = config.k \``\`

You can then either use config for high level actions or the more low level *k* object.

.. |CI| image:: https://github.com/karmab/kcli/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/karmab/kcli/actions/workflows/ci.yml
.. |Pypi| image:: http://img.shields.io/pypi/v/kcli.svg
   :target: https://pypi.python.org/pypi/kcli/
.. |Copr| image:: https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli/status_image/last_build.png
   :target: https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli
.. |Documentation Status| image:: https://readthedocs.org/projects/kcli/badge/?version=latest
   :target: https://kcli.readthedocs.io/en/latest/?badge=latest
