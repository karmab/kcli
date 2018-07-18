|Build Status| |Pypi| |Copr| |image3|

About
=====

This tool is meant to interact with a local/remote libvirt daemon and to
easily deploy from templates (optionally using cloudinit). It will also
report IPS for any vm connected to a dhcp-enabled libvirt network and
generally for every vm deployed from this client. There is also support
for - gcp - aws - kubevirt - ovirt

Installation
============

Requisites
----------

If you dont have kvm installed on the target host, you can also use the
following command to get you going ( not needed for ubuntu as it’s done
when installing kcli package)

.. code:: bash

    yum -y install libvirt libvirt-daemon-driver-qemu qemu-kvm 
    sudo usermod -aG qemu,libvirt YOUR_USER

For interaction with local docker, you might also need the following

.. code:: bash

    sudo groupadd docker
    sudo usermod -aG docker YOUR_USER
    sudo systemctl restart docker

For ubuntu, you will also need the following hack:

.. code:: bash

    export PYTHONPATH=/usr/lib/python2.7/site-packages

If not running as root, you’ll also have to add your user to those
groups

.. code:: bash

    sudo usermod -aG qemu,libvirt YOUR_USER

for *macosx*, you’ll want to check the docker installation section ( if
planning to go against a remote kvm host)

Recomended install method
-------------------------

If using *fedora*, you can use this:

.. code:: bash

    dnf -y copr enable karmab/kcli ; dnf -y install kcli

If using a debian based distribution, you can use this( example is for
ubuntu zesty):

.. code:: bash

    echo deb [trusted=yes] https://packagecloud.io/karmab/kcli/ubuntu/ zesty main > /etc/apt/sources.list.d/kcli.list ; apt-get update ; apt-get -y install kcli-all

Using docker
------------

Pull the latest image:

.. code:: shell

    docker pull karmab/kcli

To run it

.. code:: shell

    docker run --rm karmab/kcli

the are several flags you’ll want to pass depending on your use case

-  ``-v /var/run/libvirt:/var/run/libvirt`` if running against a local
   hypervisor
-  ``~/.kcli:/root/.kcli`` to use your kcli configuration (also profiles
   and repositories) stored locally
-  ``-v ~/.ssh:/root/.ssh`` to share your ssh keys
-  ``-v $SSH_AUTH_SOCK:/ssh-agent --env SSH_AUTH_SOCK=/ssh-agent``
   alternative way to share your ssh keys, to avoid selinux denials

As a bonus, you can alias kcli and run kcli as if it is installed
locally instead a Docker container:

.. code:: shell

    alias kcli='docker run -it --rm -v ~/.kcli:/root/.kcli -v /var/run/libvirt:/var/run/libvirt -v $SSH_AUTH_SOCK:/ssh-agent --env SSH_AUTH_SOCK=/ssh-agent karmab/kcli'

Note that the container cant be used for virtualbox ( i tried hard but
there’s no way that will work…)

For web access, you can switch with ``--entrypoint=/usr/bin/kweb``

Dev installation from pip
-------------------------

Centos installation
~~~~~~~~~~~~~~~~~~~

Use the provided `script <extras/centos.sh>`__ which will install a
dedicated python3 env

Generic plafrom
~~~~~~~~~~~~~~~

1. Install requirements. you will also need to grab *genisoimage* (or
   *mkisofs* on OSX) for cloudinit isos to get generated Console access
   is based on remote-viewer For instance if using a RHEL based
   distribution:

.. code:: bash

    yum -y install gcc libvirt-devel python-devel genisoimage qemu-kvm nmap-ncat python-pip libguestfs-tools

On Fedora, you’ will need an additional package

.. code:: shell

    yum -y install redhat-rpm-config

If using a Debian based distribution:

.. code:: shell

    apt-get -y install python-pip pkg-config libvirt-dev genisoimage qemu-kvm netcat libvirt-bin python-dev libyaml-dev

2. Install kcli from pypi

.. code:: shell

    pip install kcli

Configuration
=============

If you are starting from a completely clean kvm host, you might have to
create default pool . You can do it with kcli actually

.. code:: bash

    sudo kcli pool -p /var/lib/libvirt/images default
    sudo chmod g+rw /var/lib/libvirt/images

If you only want to use your local libvirt or virtualbox daemon, *no
configuration* is needed. On most distributions, default network and
storage pool already exist.

You can add an additional storage pool with:

.. code:: shell

    kcli pool  -p /var/lib/libvirt/images default

You can also create a default network

.. code:: shell

    kcli network  -c 192.168.122.0/24 default

If you want to generate a settings file ( for tweaking or to add remote
hosts), you can use the following command:

.. code:: shell

    kcli bootstrap

And for advanced bootstrapping, you can specify a target name, host, a
pool with a path, and have centos cloud image downloaded

.. code:: shell

    kcli bootstrap -n twix -H 192.168.0.6 --pool vms --poolpath /home/vms

You can also edit directly ~/.kcli/config.yml. For instance,

.. code:: yaml

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

Replace with your own client in default section and indicate host and
protocol in the corresponding client section.

Note that most of the parameters are actually optional, and can be
overridden in the default, host or profile section (or in a plan file)

Provider specifics
==================

Gcp
---

::

    gcp1:
     type: gcp
     user: jhendrix
     credentials: ~/myproject.json
     enabled: true
     project: myproject
     zone: europe-west1-b

The following parameters are specific to gcp:

-  user
-  credentials (pointing to a json service account file). if not
   specified, the environment variable *GOOGLE_APPLICATION_CREDENTIALS*
   will be used
-  project
-  zone

also note that gcp provider supports creation of dns records for an
existing domain and that your home public key will be uploaded if needed

To gather your service account file:

-  Select the “IAM” → “Service accounts” section within the Google Cloud
   Platform console.
-  Select “Create Service account”.
-  Select “Project” → “Editor” as service account Role.
-  Select “Furnish a new private key”.
-  Select “Save”

to Create a dns zone

-  Select the “Networking” → “Network Services” → “Cloud DNS”
-  Select “Create Zone”
-  Put the same name as your domain, but with ‘-’ instead

Aws
---

::

    aws:
     type: aws
     access_key_id: AKAAAAAAAAAAAAA
     access_key_secret: xxxxxxxxxxyyyyyyyy
     enabled: true
     region: eu-west-3
     keypair: mykey

The following parameters are specific to aws:

-  access_key_id
-  access_key_secret
-  region
-  keypair

Kubevirt
--------

for kubevirt, you will need to define one ( or several !) sections with
the type kubevirt in your *~/.kcli/config.yml*

authentication is handled by your local ~/.kubeconfig, which means that
by default, kcli will try to connect to your current
kubernetes/openshift context. For instance,

::

    kubevirt:
     type: kubevirt
     enabled: true
     pool: glusterfs-storage
     tags:
       region: master

You can use additional parameters for the kubevirt section:

-  context: the context to use . You can use the following command to
   list the context at your disposal

::

    kubectl config view -o jsonpath='{.contexts[*].name}'

-  pool: your default storageclass. can also be set as blank, if no
   storage class should try to bind pvcs
-  host: the node to use for tunneling to reach ssh (and consoles). If
   running on openshift, this is evaluated from your current context
-  usecloning: whether pvcs for templates will be cloned by the
   underlying storageclass. Defaults to false, so pvcs are manually
   copied under the hood launching a specific copy pod.
-  tags: additional tags to put to all created vms in their
   *nodeSelector*. Can be further indicated at profile or plan level in
   which case values are combined. This provides an easy way to force
   vms to run on specific nodes, by matching labels.

*virtctl* is a hard requirement for consoles. If present on your local
machine, this will be used. otherwise, it s expected that the host node
has it installed.

Also, note that the kubevirt plugin uses *offlinevirtualmachines*
instead of virtualmachines.

Ovirt
-----

::

    ovirt:
     type: ovirt
     host: ovirt.default
     user: admin@internal
     password: prout
     pool: vms
     tunnel: false
     org: Karmalabs
     ca_file: ~/ovirt.pem
     imagerepository: ovirt-image-repository

The following parameters are specific to ovirt:

-  org Organization
-  ca_file Points to a local path with the cert of the ovirt engine
   host. It can be retrieved with
   ``wget http://$HOST/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA``
-  imagerepository. A Glance image provider repository. Defaults to
   ``ovirt-image-repository``. You can get default one created for you
   with kcli download

Fake
----

you can also use a fake provider to get a feel of how kcli works (or to
generate the scripts for a platform yet not supported like Openstack)

::

    fake:
     type: fake
     enabled: true

Usage
=====

Templates aim to typically be the source for your vms, using the
existing cloud images from the different distributions. *kcli download*
can be used to download a specific cloud image. for instance, centos7:

.. code:: shell

    kcli download centos7

at this point, you can actually deploy vms directly from the template,
using default settings for the vm:

.. code:: shell

    kcli vm -p CentOS-7-x86_64-GenericCloud.qcow2 vm1

by default, your public key will be injected (using cloudinit) to the
vm!

you can then access the vm using *kcli ssh*

Note also that kcli uses the default ssh_user according to the different
`cloud
images <http://docs.openstack.org/image-guide/obtain-images.html>`__. To
guess it, kcli checks the template name. So for example, your centos
image must contain the term “centos” in the file name, otherwise the
default user “root” will be used.

Cloudinit stuff
---------------

If cloudinit is enabled (it is by default), a custom iso is generated on
the fly for your vm (using mkisofs) and uploaded to your kvm instance
(using the libvirt API, not using ssh commands).

The iso handles static networking configuration, hostname setting,
injecting ssh keys and running specific commands and entire scripts, and
copying entire files

Also note that if you use cloudinit but dont specify ssh keys to inject,
the default *~/.ssh/id_rsa.pub* will be used, if present.

Profiles configuration
----------------------

Profiles are meant to help creating single vm with preconfigured
settings (number of CPUS, memory, size of disk, network,whether to use a
template,…)

You use the file *~/.kcli/profiles.yml* to declare your profiles.

Once created, you can use the following for instance to create a vm
named myvm from profile centos7

.. code:: shell

    kcli vm -p centos7 myvm

The `samples
directory <https://github.com/karmab/kcli/tree/master/samples>`__
contains more examples to get you started

Typical commands
----------------

-  Get info on your kvm setup
-  ``kcli report``
-  Switch active client to bumblefoot

   -  ``kcli host --switch bumblefoot``

-  List vms, along with their private IP (and plan if applicable)
-  ``kcli list``
-  List templates (Note that it will find them out based on their qcow2
   extension…)
-  ``kcli list -t``
-  Create vm from profile base7
-  ``kcli vm -p base7 myvm``
-  Delete vm
-  ``kcli delete vm1``
-  Get detailed info on a specific vm
-  ``kcli infovm1``
-  Start vm
-  ``kcli start vm1``
-  Stop vm
-  ``kcli stop vm1``
-  Get remote-viewer console
-  ``kcli console vm1``
-  Get serial console (over TCP!!!). Note that it will only work with
   vms created with kcli and will require netcat client to be installed
   on host
-  ``kcli console -s vm1``
-  Deploy multiple vms using plan x defined in x.yml file
-  ``kcli plan -f x.yml x``
-  Delete all vm from plan x

   -  ``kcli plan -d x``

-  Add 5GB disk to vm1, using pool named vms

   -  ``kcli disk -s 5 -p vms vm1``

-  Delete disk named vm1_2.img from vm1

   -  ``kcli disk -d -n vm1_2.img  vm1``

-  Update to 2GB memory vm1

   -  ``kcli update -m 2048 vm1``

-  Update internal IP (useful for ansible inventory over existing
   bridged vms)

   -  ``kcli update -1 192.168.0.40 vm1``

-  Clone vm1 to new vm2

   -  ``kcli clone -b vm1 vm2``

-  Connect by ssh to the vm (retrieving ip and adjusting user based on
   the template)

   -  ``kcli ssh vm1``

-  Add a new network

   -  ``kcli network -c 192.168.7.0/24 --dhcp mynet``

-  Add a new nic from network default
-  ``kcli nic -n default myvm``
-  Delete nic eth2 from vm
-  ``kcli nic -di eth2 myvm``
-  Create snapshot snap of vm:
-  ``kcli snapshot -n vm1 snap1``

How to use the web version
--------------------------

Launch the following command and access your machine at port 9000:

.. code:: shell

    kweb

Multiple hypervisors
--------------------

If you have multiple hypervisors, you can generally use the flag *-C
$CLIENT* to temporarily point to a specific one.

You can also use the following to list all you vms :

``kcli -C all list``

Using plans
-----------

You can also define plan files in yaml with a list of profiles, vms,
disks, and networks and vms to deploy (look at the sample) and deploy it
with kcli plan. The following type can be used within a plan:

-  network
-  template
-  disk
-  pool
-  profile
-  ansible
-  container
-  dns
-  plan ( so you can compose plans from several url)
-  vm ( this is the type used when none is specified )

Here are some examples of each type ( additional ones can be found in
the `samples
directory <https://github.com/karmab/kcli/tree/master/samples>`__:

network
~~~~~~~

.. code:: yaml

    mynet:
     type: network
     cidr: 192.168.95.0/24

You can also use the boolean keyword dhcp (mostly to disable it) and
isolated . Note that when not specified, dhcp and nat will be enabled

template
~~~~~~~~

.. code:: yaml

    CentOS-7-x86_64-GenericCloud.qcow2:
     type: template
     url: http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2

It will only be downloaded only if not present

Note that if you point to an url not ending in qcow2/qc2 ( or img), your
browser will be opened for you to proceed. Also note that you can
specify a command with the cmd: key, so that virt-customize is used on
the template once it s downloaded

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

Note the disk is shared between two vms (that typically would be defined
within the same plan):

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
       masters:
       - master1
       - master2
       - master3

Note that an inventory will be created for you in /tmp and that
*group_vars* and *host_vars* directory are taken into account. You can
optionally define your own groups, as in this example The playbooks are
launched in alphabetical order

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

Look at the docker section for details on the parameters

plan’s plan ( Also known as inception style)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

    ovirt:
      type: plan
      url: github.com/karmab/kcli/plans/ovirt
      file: upstream.yml
      run: true

dns
~~~

.. code:: yaml

    yyy:
     type: dns
     net: default
     ip: 192.168.1.35

vms
~~~

You can point at an existing profile in your plans, define all
parameters for the vms, or combine both approaches. You can even add
your own profile definitions in the plan file and reference them within
the same plan:

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

Specific scripts and IPS arrays can be used directly in the plan file
(or in profiles one).

The samples directory contains examples to get you started.

Note that the description of the vm will automatically be set to the
plan name, and this value will be used when deleting the entire plan as
a way to locate matching vms.

When launching a plan, the plan name is optional. If not is provided, a
random generated keyword will be used.

If a file with the plan isn’t specified with -f , the file kcli_plan.yml
in the current directory will be used, if available.

Also note that when deleting a plan, the network of the vms will also be
deleted if no other vm are using them. You can prevent this by using the
keep (-k) flag.

For an advanced use of plans along with scripts, you can check the
`plans <plans/README.md>`__ page to deploy all upstream projects
associated with Red Hat Cloud Infrastructure products (or downstream
versions too).

Sharing plans
-------------

You can use the following to retrieve plans from a github repo:

.. code:: yaml

    kcli plan --get github.com/karmab/kcli/plans -p karmab_plans

The url can also be in:

-  an arbitary url ( github api is not used in this case)
-  raw github format to retrieve a single file
-  a github link

Disk parameters
---------------

You can add disk this way in your profile or plan files

.. code:: yaml

    disks:
     - size: 20
       pool: vms
     - size: 10
       thin: False
       format: ide

Within a disk section, you can use the word size, thin and format as
keys

-  *thin* Value used when not specified in the disk entry. Defaults to
   true
-  *interface* Value used when not specified in the disk entry. Defaults
   to virtio. Could also be ide, if vm lacks virtio drivers

Network parameters
------------------

You can mix simple strings pointing to the name of your network and more
complex information provided as hash. For instance:

.. code:: yaml

    nets:
     - default
     - name: private
       nic: eth1
       ip: 192.168.0.220
       mask: 255.255.255.0
       gateway: 192.168.0.1

Within a net section, you can use name, nic, IP, mac, mask, gateway and
alias as keys.

You can also use *noconf: true* to only add the nic with no
configuration done in the vm

Note that up to 4 IPS can also be provided on command line when creating
a single vm (with the flag -1, -2, -3,-4,…)

ip, dns and host Reservations
-----------------------------

If you set *reserveip* to True, a reservation will be made if the
corresponding network has dhcp and when the provided IP belongs to the
network range.

You can also set *reservedns* to True to create a DNS entry for the host
in the corresponding network ( only done for the first nic)

You can also set *reservehost* to True to create a HOST entry for the
host in /etc/hosts ( only done for the first nic). It’s done with sudo
and the entry gets removed when you delete the host. Note you should use
gnu-sed ( from brew ) instead of regular sed on macosx for proper
deletion.

If you dont want to be asked for your sudo password each time, here are
the commands that are escalated:

.. code:: shell

     - echo .... # KVIRT >> /etc/hosts
     - sed -i '/.... # KVIRT/d' /etc/hosts

Docker support
--------------

Docker support is mainly enabled as a commodity to launch some
containers along vms in plan files. Of course, you will need docker
installed on the hypervisor. So the following can be used in a plan file
to launch a container:

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

-  *image* name of the image to pull ( You can alternatively use the
   keyword *template*
-  *cmd* command to run within the container
-  *ports* array of ports to map between host and container
-  *volumes* array of volumes to map between host and container. You can
   alternatively use the keyword *disks*. You can also use more complex
   information provided as a hash

Within a volumes section, you can use path, origin, destination and mode
as keys. mode can either be rw o ro and when origin or destination are
missing, path is used and the same path is used for origin and
destination of the volume. You can also use this typical docker syntax:

.. code:: yaml

    volumes:
     - /home/cocorico:/root/cocorico

Additionally, basic commands ( start, stop, console, plan, list) accept
a *–container* flag.

Also note that while python sdk is used when connecting locally,
commands are rather proxied other ssh when using a remote host ( reasons
beeing to prevent mismatch of version between local and remote docker
and because enabling remote access for docker is considered insecure and
needs some uncommon additional steps )

Finally, note that if using the docker version of kcli against your
local host , you’ll need to pass a docker socket:

``docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/.ssh:/root/.ssh -v /var/run/docker.sock:/var/run/docker.sock karmab/kcli``

Ansible support
---------------

You can check klist.py in the extra directory and use it as a dynamic
inventory for ansible.

The script uses sames conf as kcli (and as such defaults to local
hypervisor if no configuration file is found).

vm will be grouped by plan, or put in the kvirt group if they dont
belong to any plan.

Interesting thing is that the script will try to guess the type of vm
based on its template, if present, and populate ansible_user accordingly

Try it with:

.. code:: shell

    python extra/klist.py --list
    ansible all -i extra/klist.py -m ping

Additionally, there is an ansible kcli/kvirt module under extras, with a
sample playbook

You can also use the key ansible within a profile

.. code:: yaml

    ansible:
     - playbook: frout.yml
       verbose: true
       variables:
        - x: 8
        - z: 12

In a plan file, you can also define additional sections with the ansible
type and point to your playbook, optionally enabling verbose and using
the key hosts to specify a list of vms to run the given playbook
instead. You wont define variables in this case, as you can leverage
host_vars and groups_vars directory for this purpose

.. code:: yaml

    myplay:
     type: ansible
     verbose: false
     playbook: prout.yml

Note that when leveraging ansible this way, an inventory file will be
generated on the fly for you and let in */tmp/$PLAN.inv*

Using products
--------------

If plans seem too complex, you can make use of the products feature
which leverages them

Repos
~~~~~

You first add a repo containing a KMETA file with yaml info about
products you want to expose. For instance, mine

::

    kcli repo -u github.com/karmab/kcli/plans karmab

You can also update later a given repo, to refresh its KMETA file ( or
all the repos, if not specifying any)

::

    kcli repo --update REPO_NAME

You can delete a given repo with

::

    kcli repo -d REPO_NAME

Product
~~~~~~~

Once you have added some repos, you can list available products, and get
their description

::

    kcli list --products 

You can also get direct information on the product (memory and cpu used,
number of vms deployed and all parameters that can be overriden)

::

    kcli product --info YOUR_PRODUCT 

And deploy any product . Note deletion is currently handled by deleting
the corresponding plan

::

    kcli product YOUR_PRODUCT

Testing
-------

Basic testing can be run with pytest. If using a remote hypervisor, you
ll want to set the *KVIRT_HOST* and *KVIRT_USER* environment variables
so that it points to your host with the corresponding user.

about virtualbox support
------------------------

While the tool should pretty much work the same on this hypervisor,
there are some issues:

-  it’s impossible to connect using ip, so port forwarding is used
   instead
-  with NATnetworks ( not NAT!), guest addons are needed to gather ip of
   the vm so they are automatically installed for you. It implies an
   automatic reboot at the end of provisioning….
-  when you specify an unknown network, NAT is used instead. The reason
   behind is to be able to seamlessly use simple existing plans which
   make use of the default network ( as found on libvirt)

Specific parameters for a hypervisor
------------------------------------

-  *host* Defaults to 127.0.0.1
-  *port*
-  *user* Defaults to root
-  *protocol* Defaults to ssh
-  *url* can be used to specify an exotic qemu url
-  *tunnel* Defaults to False. Setting it to true will make kcli use
   tunnels for console and for ssh access. You want that if you only
   open ssh port to your hypervisor!
-  *planview* Defaults to False. Setting it to true will make kcli use
   the value specified in *~/.kcli/plan* as default plan upon starting
   and stopping plan. Additionally, vms not belonging to the set plan
   wont show up when listing

Available parameters for hypervisor/profile/plan files
------------------------------------------------------

-  *cpumodel* Defaults to Westmere
-  *cpuflags* (optional). You can specify a list of strings with
   features to enable or use dict entries with *name* of the feature and
   *enable* either set to True or False. Note that the value for vmx is
   ignored, as it s handled by the nested flag
-  *numcpus* Defaults to 2
-  *memory* Defaults to 512M
-  *guestid* Defaults to guestrhel764
-  *pool* Defaults to default
-  *template* Should point to your base cloud image(optional). You can
   either specify short name or complete path. Note that if you omit the
   full path and your image lives in several pools, the one from last
   (alphabetical) pool will be used.
-  *disksize* Defaults to 10GB
-  *diskinterface* Defaults to virtio. You can set it to ide if using
   legacy operating systems
-  *diskthin* Defaults to True
-  *disks* Array of disks to define. For each of them, you can specify
   pool, size, thin (as boolean), interface (either ide or virtio) and a
   wwn.If you omit parameters, default values will be used from config
   or profile file (You can actually let the entire entry blank or just
   indicate a size number directly)
-  *iso* (optional)
-  *nets* (optional)
-  *gateway* (optional)
-  *dns* (optional) Dns servers
-  *domain* (optional) Dns search domain
-  *start* Defaults to true
-  *vnc* Defaults to false (use spice instead)
-  *cloudinit* Defaults to true
-  *reserveip* Defaults to false
-  *reservedns* Defaults to false
-  *reservehost* Defaults to false
-  *keys* (optional). Array of ssh public keys to inject to th vm
-  *cmds* (optional). Array of commands to run
-  *profile* name of one of your profile. Only checked in plan file
-  *scripts* array of paths of custom script to inject with cloudinit.
   Note that it will override cmds part. You can either specify full
   paths or relative to where you’re running kcli. Only checked in
   profile or plan file
-  *nested* Defaults to True
-  *sharedkey* Defaults to False. Set it to true so that a
   private/public key gets shared between all the nodes of your plan.
   Additionally, root access will be allowed
-  *files* (optional)- Array of files to inject to the vm. For ecach of
   the them , you can specify path, owner ( root by default) ,
   permissions (600 by default ) and either origin or content to gather
   content data directly or from specified origin
-  *insecure* (optional) Handles all the ssh option details so you dont
   get any warnings about man in the middle
-  *host* (optional) Allows you to create the vm on a specific host,
   provided you used kcli -C host1,host2,… and specify the wanted
   hypervisor ( or use kcli -C all ). Note that this field is not used
   for other types like network, so expect to use this in relatively
   simple plans only
-  *base* (optional) Allows you to point to a parent profile so that
   values are taken from parent when not found in the current profile.
   Note that scripts and commands are rather concatenated between
   default, father and children ( so you have a happy family…)
-  *tags* (optional) Array of tags to apply to gcp instances (usefull
   when matched in a firewall rule). In the case of kubevirt, it s
   rather a dict of key=value used as node selector (allowing to force
   vms to be scheduled on a matching host)
-  rhnregister (optional). Auto registers vms whose template starts with
   rhel Defaults to false. Requires to either rhnuser and rhnpassword,
   or rhnactivationkey and rhnorg
-  rhnuser (optional). Red Hat network user
-  rhnpassword (optional). Red Hat network password
-  rhnactivationkey (optional). Red Hat network activation key
-  rhnorg (optional). Red Hat network organization
-  rhnuser (optional). Red Hat network user

Overriding parameters
---------------------

Note that you can override parameters in - commands - scripts - files -
plan files - profiles

For that , you can pass in kcli vm or kcli plan the following
parameters: - -P x=1 -P y=2 and so on - –paramfile - In this case, you
provide a yaml file ( and as such can provide more complex structures )

The indicated objects are then rendered using jinja. For instance in a
profile Note we use the delimiters ‘[[’ and ’]]’ instead of the commonly
used ‘{{’ and ‘}}’ so that this rendering doesnt get in the way when
providing j2 files for instance

::

    centos:
     template: CentOS-7-x86_64-GenericCloud.qcow2
     cmds:
      - echo x=[[ x ]] y=[[ y ]] >> /tmp/cocorico.txt
      - echo [[ password | default('unix1234') ]] | passwd --stdin root

You can make the previous example cleaner by using the special key
parameters in your plans and define there variables

::

    parameters:
     password: unix1234
     x: coucou
     y: toi
    centos:
     template: CentOS-7-x86_64-GenericCloud.qcow2
     cmds:
      - echo x=[[ x ]] y=[[ y ]] >> /tmp/cocorico.txt
      - echo [[ password  ]] | passwd --stdin root

Finally note that you can also use advanced jinja constructs like
conditionals and so on. For instance:

::

    parameters:
      net1: default
    vm4:
      template: CentOS-7-x86_64-GenericCloud.qcow2
      nets:
        - [[ net1 ]]
    {% if net2 is defined %}
        - [[ net2 ]]
    {% endif %}

Also, you can reference a *baseplan* file in the *parameters* section,
so that parameters are concatenated between the base plan file and the
current one

::

    parameters:
       baseplan: upstream.yml
       xx_version: v0.7.0

.. |Build Status| image:: https://travis-ci.org/karmab/kcli.svg?branch=master
   :target: https://travis-ci.org/karmab/kcli
.. |Pypi| image:: http://img.shields.io/pypi/v/kcli.svg
   :target: https://pypi.python.org/pypi/kcli/
.. |Copr| image:: https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli/status_image/last_build.png
   :target: https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli
.. |image3| image:: https://images.microbadger.com/badges/image/karmab/kcli.svg
   :target: https://microbadger.com/images/karmab/kcli
