# coding=utf-8
Changelog
=========

2018-07-04
----------

-  gcp and aws support
-  defaults to host-model. Edu knows
-  parameters information for remote plans
-  pep8 E501 up to 120 characters
-  fix switching host damn space issue
-  lighter docker image based on alpine
-  defaults to 3.10 in upstream openshift plans

.. _section-1:

2018-03-27
----------

-  fix paths for rhel downloads
-  defaults to kubevirt when libvirt socket not found
-  dynamic forwarding for kcli ssh

.. _section-2:

2018-03-20
----------

|asciicast|

-  kubevirt support (using offlinevirtualmachines and creating pvcs on
   the fly)
-  readthedocs page
-  improvements in openshift plans for 3.9
-  updated kubevirt plans
-  updated virtualbox instructions
-  dynamic ovirt plans
-  gluster upstream plans
-  use a baseconfig for operations not needing to actually test
   connection to hypervisors
-  allow to use kcli switch when current hypervisor is down
-  support multiple clients at once of different type, for instance kcli
   -C host1,host2 list
-  fix download when url is None ( for @valadas )
-  Add download links for RHEL atomic host

.. _section-3:

2018-02-12
----------

|asciicast|

-  cache product repositories
-  ansible kcli modules
-  dynamic nodes plan for openshift
-  support for vips
-  refactored openshift plans using parameters
-  dynamic number of nodes in kubernetes basic plan
-  fixes k8s basic plan
-  sync non rhel templates between hypervisors
-  updated ubuntu instructions
-  fix identation for injected files when overriding is enabled
-  tweaked kubevirt plan as per latest 0.2.0 release
-  openfaas plan
-  better information when trying to use a non existing template
-  remove kcli host –switch so we just use kcli switch
-  display help when no arguments are passed
-  remove pub and priv keys when using sharedkey as they are only useful
   on the vms

.. _section-4:

2017-12-22
----------

|asciicast|

-  restablished vbox support and fix minor issues
-  transparent support of binary files in plans
-  update most openshift plans so that docker disk size is configurable
-  tripleo plans refactoring ( thanks @manuvaldi )
-  basic search feature for products
-  allow additional comments as metadata for products
-  parameter to set version of fission plan to core or full
-  update ovirt plan to 4.2
-  basic helper renderer for scripts and plans (kcli_renderer.py)

.. _section-5:

2017-12-18
----------

|asciicast|

-  rendering of parameters using jinja2 and –set ( or –paramfile ) in
   profile, plan and product. This is used also in scripts and commands.
   To make it easy to use, an additional *parameters* keyword can be
   added in the plan to define parameters ( and to easily set default
   values )
-  Auto rendering of the name parameter so one can easily change the
   name when using a single vm in a plan/product
-  Rewriting of most of the provided plans to make use of the rendering
   functionality
-  Transfer parameters from a father plan to its chidren when using a
   “plan of plans”
-  use *base* keyword in profiles to indicate a base profile ( and
   defaults to its values when not found). Note that commands and
   scripts are rather concatenated
-  possibility to indicate a list of hypervisors in most commands (kcli
   -C host1,host2)
-  select a random hypervisor when using ``kcli -C host1,host2,... vm``
-  bitbar extra to list vms from your menu bar
-  allow filtering of products per group
-  information on product, in particular available dynamic parameters
-  indicate memory used by a product
-  enable (optional) injection of the private key of the user too with
   the privatekey keyword)
-  filtering of values to return in kcli info
-  allow use of the mode keyword in the files section ( old keyword
   permission can still be used )
-  allow X11 forwarding in kcli ssh
-  additional openshift plans with multiple vms
-  old openshift releases plans
-  istio plan improvements
-  report yaml exception when config file cant be parsed
-  ansible logs in openshift multimaster plan
-  minishift per version
-  boot from iso when cloudinit is enabled and iso present
-  ovirt42 plan
-  remove wget from ovirt plans in favor of files section
-  katello preliminary plan
-  workaround for ansible service broker issues plan
-  silent download
-  properly expand scripts when not running plan from current directory
-  better dynamic support in web
-  fedora 27 cloud image
-  delete generated pub and private keyfiles along with plan

Note: as of this version, most of the karmab repository have been
rewritten to use rendering

This means that if you don’t use a version of kcli >10.X but still
points at this same repository, you won’get proper results ( as the
dynamic variables will betreated as static).

Either update (recommended) or use the following alternative repository

::

    kcli repo -u github.com/karmab/kcli/plans_legacy karmab_legacy

.. _section-6:

2017-10-23
----------

-  better dynamic support in web
-  properly expand scripts when not running plan from current directory

.. _section-7:

2017-10-23
----------

-  fix stupid issues with lastvm when file doesnt exist

.. _section-8:

2017-10-21
----------

-  products and repo support to leverage plans and make them easier to
   use
-  added clean parameter to kcli product to remove downloaded plan
-  helm and fission plan
-  allow minimal syntax in config.yml to specify default values but
   implicitly using the local hypervisor
-  support for repo and products in the web version
-  allow to specify a plan name when deploying a product
-  full KMETA list from my github repo
-  merged copr and packagecloud plans ( only useful for me, as this is
   what i use to build rpm and deb)

.. _section-9:

2017-10-20
----------

-  added clean parameter to kcli product to remove downloaded plan

.. _section-10:

2017-10-20
----------

-  improved repo handling
-  full KMETA list from my github repo
-  merged copr and packagecloud plans ( only usefull for me, as this is
   what i use to build rpm and deb)

.. _section-11:

2017-10-20
----------

-  products and repo support to leverage plans and make them easier to
   use
-  helm plan
-  fission plan
-  allow minimal syntax in config.yml to specify default values but
   implicitly using the local hypervisor *Starting from version9, each
   release gets its dedicated changelog page*

.. _section-12:

8.12 (2017-10-06)
-----------------

-  allow to have both cloudinit and an additional iso
-  remove soukron from random names
-  fix bad ordering of commands when using vm -p
-  ansible service broker plan

.. _section-13:

8.11 (2017-10-03)
-----------------

-  improved workflow for plan of plans, as per @dittolive good feedback

.. _section-14:

8.9 (2017-09-29)
----------------

-  fix deletion issue with .kcli/vm IMPORTANT: Starting from now, each
   version will have their own page, accessible from this same directory
   or linked to the release

.. _section-15:

8.8 (2017-09-28)
----------------

-  allow most commands to make use of last created vm, when no one is
   provided
-  track all created vms in reverse order in .kcli/vm

.. _section-16:

8.7 (2017-09-20)
----------------

-  kcli ssh without specifying vm s name
-  Use -p as input file in kcli vm -p when it ends with .yml
-  create single vm from plan file (using it as a profile)
-  running vms and used memory in kcli report
-  additional random names like federer and soukron
-  istio sample plans
-  F5 sample plan
-  pike support
-  minishift plan

.. _section-17:

8.3 (2017-08-21)
----------------

-  concatenate scripts and commands at all level (host or default)
-  dont handle duplicate scripts and commands
-  report info of vms as yaml
-  dns entries
-  use netmask keyword instead of mask
-  fix bootstrap bug

.. _section-18:

8.2 (2017-07-14)
----------------

-  stupid print when running kcli ssh and proper cast

.. _section-19:

8.0 (2017-07-14)
----------------

-  topology feature allowing to indicate with a file how many of a given
   vm type are to be deployed in a plan. Also allows to scale plan
   directly from command line
-  start/stop/delete several vms at once
-  add optional –domain parameter for networks to use custom dns domains
-  dns alias
-  debian9 template
-  minimal jenkins plan
-  temporarily (?) remove virtualbox indications as requirements are
   broken
-  allow to remove cloudinit iso
-  allow noconf for nics
-  rename cloudinit generated isos to .ISO so they dont appear when
   listing isos
-  updated openshift upstream plan to 3.6
-  indicate pxe server for network

.. _section-20:

7.20 (2017-05-26)
-----------------

-  move config and profile to ~/.kcli
-  fix listing of snapshots when vm not found
-  fixes in openshift advanced plan

.. _section-21:

7.19 (2017-05-24)
-----------------

-  minor cleaning
-  fix inventory when running locally
-  use –snapshots instead of –force when deleting vm with snapshots
-  atomic image download

.. _section-22:

7.18 (2017-05-16)
-----------------

-  debian package
-  enableroot through config
-  visible default options when bootstrapping
-  exit when : is not specified in kcli scp
-  fix on kcli scp
-  pass commands with kcli ssh
-  quiet exit for kcli ssh when proxied
-  allow random names when deploying vm

.. _section-23:

7.17 (2017-05-14)
-----------------

-  allow using user@ in kcli ssh and scp

.. _section-24:

7.16 (2017-05-14)
-----------------

-  dedicated advanced openstack plan with live migration and rally
-  simplify bootstrap command so it only creates the config file
-  move kcli host –download –template to good old kcli download
-  move kcli host –report to good old kcli report
-  properly enable nested for amd procesors

.. _section-25:

7.15 (2017-05-13)
-----------------

-  fix in advanced plan of openstack
-  correctly inject public keys along with private when using sharedkeys
   ( and injecting files)
-  remove all .pyc files in order to generate deb package using

.. _section-26:

7.14 (2017-05-12)
-----------------

-  fix docker api bugs when creating container
-  homogeneous container commands ( ie only use kcli container for
   creating container and nothing else)
-  sample app in kubernetes plan
-  kcli list –images to check container images

.. _section-27:

7.13 (2017-05-11)
-----------------

-  copr repo indication
-  fix hidden url in plancreate and web
-  lighter rpm
-  kubernetes simple plan

.. _section-28:

7.12 (2017-05-10)
-----------------

-  rpm spec and binary for fedora25
-  fix identation in write_files
-  fix satellite downstream plan
-  fixing the used port when running vms locally and pointing to a
   remote host

.. _section-29:

7.7 (2017-05-05)
----------------

-  cli and web support for downloading rhel and cloudforms images (
   asking the concrete cdn url)
-  cli and web support for running a given command after downloading an
   image
-  tripleo typo fixes

.. _section-30:

7.5 (2017-04-23)
----------------

-  automatically enable root access with the same public keys
-  reorganization of the advanced plans to ease their utilization from
   the UI
-  advanced packstack with plan with multiple compute nodes
-  take screenshot of vm

.. _section-31:

7.4 (2017-04-20)
----------------

-  ovirt hosted plans
-  use default/hypervisor values when deploying from unknown template
-  yakkety and zesty support
-  fix to report fixed_ip only when it s really fixed
-  allow all parameters to be overriden at client/hypervisor level
-  fix inline editing of kcli.yml in docker
-  allow to execute a command on a template after it’s downloaded

.. _section-32:

6.1 (2017-04-18)
----------------

-  fix kcli host –switch/enable/update ( and in the UI) within container

.. _section-33:

6.0 (2017-04-17)
----------------

-  web version to use with kweb
-  cloudinit reports in the UI at the end and during provisioning
-  custom reportdir for the UI reports
-  plan of plans ( so a single file can reference several plans located
   at different urls)
-  kcli snapshot with create/delete/revert/list
-  enable/disable hypervisors
-  unified configuration class
-  common base class for all providers to serve as a base to additional
   providers
-  manageiq/cloudforms plans working
-  common ansible dynamic inventory
-  enhance list profiles
-  insecure option for quiet ssh connections
-  report paths with list –pools to please @rsevilla87
-  short option for listing profiles or networks
-  switch from click to argparse
-  IMPORTANT: as part of the refactorization, metadata about the vms are
   stored differently. So you re advised to run kcli list prior to
   upgrade so you can use this information afterwards to run *kcli
   update –template* or *kcli update –plan*

.. _section-34:

5.24 (2017-04-04)
-----------------

-  Cleaner options
-  Removed -l from every section in favor of kcli list
-  *–force* option to delete vm when it has existing snapshots

.. _section-35:

5.21 (2017-03-31)
-----------------

-  Create pools in the plans
-  Download templates in the plans
-  Optional libvirt+Virtualbox Dockerfile ( with limited support)
-  Fix commands array for virtualbox cloudinit

.. _section-36:

5.20 (2017-03-27)
-----------------

-  Virtualbox support
-  /etc/hosts support
-  Update DNS/HOSTS for existing vms
-  Cpumodel and cpuflags
-  Support for files in plan
-  Sharedkeys between vms of a plan
-  Define profiles within plans
-  Iso full support
-  Ansible improvements
-  Code refactoring/cleaning for virtualbox
-  Bootstrapping fixes
-  Fix for serial console in local

.. _section-37:

5.0 (2017-02-07)
----------------

-  Support for kcli plan –get so plans and directory plans can be shared
-  Proxy commands for ssh access and tunnels for consoles
-  Added reservedns to autocreate DNS entries in libvirt
-  Fix for iso deletion
-  Fix pep8 issues
-  Fix container volumes when connecting remotely.

.. _section-38:

4.2 (2017-01-20)
----------------

-  Refactored most stuff to ease commands
-  Move kcli create to kcli vm in particular
-  Created a kcli container command and applied some container fix when
   running locally with the API
-  Put plan as label for containers

.. _section-39:

3.00 (2016-12-30)
-----------------

-  Docker support
-  Deployment of kcli as a container
-  Dont put ip information in cloudinit iso when reserveip is set to
   True ( let libvirt handle all the ip stuff then)
-  Helpers for tripleo plans
-  Use eth1 instead for undercloud plans
-  Allow to specify mac addresses on the plan files
-  Fix bugs with multiple macs

.. _section-40:

2.11 (2016-10-20)
-----------------

-  Shared disks support in plan files
-  Only download centos upon bootstrapping and provide download option
   for additional OS
-  Full shared disks support
-  Evaluate pooltype when bootstrapping in interactive mode
-  Better report for networks
-  Report volumes in pool with name from default templates as such (
   that it, as templates…)
-  Stupid handle_response fix for start/stop
-  Stupid profile fix

.. _section-41:

2.0 (2016-10-16)
----------------

-  Ability to create networks within plan file, and treating them first
   in those cases
-  New keyword reserveip at profile level to force dhcp reservation,
   regardless of whether cloudinit is enabled

.. _section-42:

1.0.52 (2016-10-16)
-------------------

-  Locate correct image when full path is specified
-  Skip existing vms when deploying a plan
-  Allow dhcp reservation to be made when cloudinit is disabled and an
   ip is still provided
-  Add/delete nics
-  Use netcat instead of telnet as it exits cleanly on itself
-  Use last found ip
-  Make sure hotplug add/delete disk is permanent
-  Report last ip in kcli list
-  Report error when trying to create a vm with a file template on a lvm
   pool, or a lvm template on a dir pool
-  Allow specifying by path disks to add
-  Switch kcli add to kcli disk and add delete disk option there
-  Set minimal size for iso on lvm pool
-  Refactored the ip code to use dhcp leases instead of buggy
   InterfaceAddress
-  Detect whether to use genisoimage or mkisofs
-  Stupid array disk bug

.. _section-43:

1.0.29 (2016-10-08)
-------------------

-  Add/delete network
-  Fix for update_memory
-  Fix add disk code
-  Thanks *efenex* for your suggestion/contribution

1.0.25 release (2016-09-29)
---------------------------

-  Uci/rhci support, providing plans for Red Hat upstream and dowsntream
   infrastructure projects
-  Serial consoles over tcp
-  lvm based pool support
-  Bootstrap command
-  Refactored the nets array so it accepts hashes
-  Refactored script1, script2,…. to array based scripts. Good idea
   *eminguez*
-  Exit if pool isn’t found
-  Optional plan name
-  Python3 compatibility
-  *Fran* fix

.. _section-44:

1.0.8 (2016-09-20)
------------------

-  Static dns and search domain support
-  Kcli ssh
-  Better parsing for ubuntu based templates
-  Fix memory update calculation

1.0 release (2016-09-12)
------------------------

-  Disk3 and disk4 feature
-  Store profile in libvirt
-  Update ip for existing vms
-  Locate pool for iso and backend volume instead of relying on disk
   pool
-  Allow to separate pools by purpose
-  Define volumes just before creating vm
-  Store profile in smbios asset

.. _section-45:

0.99.6 (2016-09-11)
-------------------

-  Initial public release
-  Basic info and console
-  Cloning
-  Report ips
-  Deploy with cloudinit and with params from profile
-  Plans
-  Ansible Inventory
-  Support for scripts in the profile

.. |asciicast| image:: https://asciinema.org/a/169350.png
   :target: https://asciinema.org/a/169350?autoplay=1
.. |asciicast| image:: https://asciinema.org/a/153438.png
   :target: https://asciinema.org/a/153438?autoplay=1
