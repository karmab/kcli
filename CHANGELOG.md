2019-11-24T23:17:48Z


- fix stupid typo in kcli info
- rhcos44
- dont duplicate download code


2019-11-23T21:15:21Z


- transform kcli renderer in a generic file renderer
- include commit version in kcli -v (container version only)
- kvm: fixes for reserveip
- kvm: preliminary mac support by indicating macosx: true in one of the disks (the ESP one)
- kvm: support for latest fcos
- kvm: handles deletion of disk of a vm  without an extension
- vsphere: make kcli download use OVA (and govc)
- gcp: fix enabling nested when adding an image
- gcp: kcli download rhcos
- gcp: fix list lb with internal lbs
- aws: fix image list
-  merge ignition data for keys not present in user provided ignition
- replace _ with - for random vm/plan names
- allow skipping profile when downloading an image (since it can easily mess profiles when using more than one client)
- uses simpler logic to gather ip for kcli ssh
- skip missing files when downloading a plan ( to handle the parameterized ones which refer to local paths)
- ubuntu1910 download
- fix vms listing in web interface
- allow specifying aliases when creating a dns entry `kcli create dns -n mydomain.com -i xxx -a '*' api.jhendrix`
- build docker image from travis to speed up releases


2019-11-04T11:20:52Z


- make memory and cpu hotplug optional (through dedicated flags)


2019-11-04T07:20:01Z


- install.sh script to ease installation
- vsphere: improved way to gather primary ip
- kvm: fix for tunneled consoles
- kvm: fix cpus update code
- kvm: memory hotplug
- fedora31 image
- rhel7 image instead of minor versions
- kcli download rhcos41, rhcos42, rhcos43
- user provided name when using kcli download image


2019-10-14T13:22:07Z


- major rewrite of the client syntax to make it more intuitive and homogeneous using a verb object pattern and by adding examples within the client (thanks @e-minguez for the feedback).
- autocompletion in cli
- provided *install.sh* to allow deploying in an easy way (creating the proper alias for container install method)
- includes keywords within the kcli help.
- creates a default profile when downloading a image to allow to create a vm using the same helper name (`kcli download image centos7 ; kcli create vm -p centos7` )
- create/delete hosts from all kind (libvirt, aws, gcp, openstack, ovirt, vsphere,...) from command line
- create/delete profiles from command line.
- kcli download plan
- switch to alpine 3.10 for container
- kvm allows to use existing disks when deploying vms.
- kvm: store ignition files in /var/tmp to make sure they dont get deleted on reboot.
- web: provide html5 console
- kubevirt: remove need for virtctl when getting console
- dont default to fake or kubevirt when no local hypervisor is found.
- pinkman in the random names!



2019-09-23T20:57:18Z


stupid typo fix after 15.1 release


2019-09-23T14:23:13Z


- vsphere support!
- kvm: force bridge name
- kvm: allow to indicate scsi as disk interface
- kcli render to easily render through jinja files (and preview rendered plans)


2019-09-06T17:36:20Z


- ovirt: resize template disk
- ovirt: use info in a smarter way with kcli list
- default to ssh for non existing clients
- kvm: autostart parameter
- kvm: preliminary delete_dns
- kvm: only reports snapshots when present
- kvm: deploy with existing disks
- kvm: deploy from iso not in a pool
- gcp: fix network load balancer
- gcp: multiple ports in single lb
- gcp: handle checkpath in lb
- gcp: support for internal loadbalancer
- aws: fix list lbs
- fake: render plan
- kvm: fix for ignitiondir with selinux in container
-  debian10 support, ubuntu1904 and fix old ubuntu download links
- kubevirt minor improvements
- handle fedora coreos new link
- preliminary alternative use of podman
- foreman initial support (wip)



2019-06-23T19:52:27Z


- fix issue with info
-  handle parameter file when using container
- simplify setup.py
- allow to force using kubevirt without config.yml
- fake: use same naming for random vms


2019-06-19T08:38:18Z


-  fake: generate ignition files
- fake: generate a proper launch script for each host
- fake:  indicate template to use
- openstack: properly inject ignition
- openstack: allow ssh as root
- openstack: report error messages in status
- openstack,aws,gcp: report privateip
- gcp: detect rhel8
- allow overriding parameters in network subfunction
- use plan as parameter in kcli product
- either download specific rhcosoopta or latest


2019-06-14T15:44:55Z


- gcp,aws: dns adjustments for openshift4
- gcp,aws,osp,kubevirt: handle ignition version
- aws: improved filtering of images
- aws: evaluate template when not an ami id
- aws: improvements on security groups from tags
- kubevirt: use common method for gathering user
- kubevirt: report properly L2 network ips
- kubevirt: report macs
- kubevirt: use static ips for ssh if there
- kubevirt: dont override already provisioned pvcs



2019-06-06T14:26:12Z


- revert to previous version for forcing ignition dns (through prepending resolv.conf)
- generate inventory with both grouped and ungouped hosts (thanks Johan Belin!)
- kvm: fix adding tunnel info during inventory generation (Johan too)
- exit when trying to list container images somewhere else than on libvirt


2019-06-04T13:56:04Z


- properly retrieve fcos and rhcos images
- append correct extension .gz when downloading rhcos
- ovirt: better parsing of glance repository
- ovirt: handle macs override for nic0 and report ip
- ovirt: prioritize ip from description
- ovirt: remove tls ignition data
- ovirt: add some info during kcli download
- ovirt: defaults to using cloudinit for ignition (no hook needed)
- use master,worker,boostrap ignition files when found and matching hostname pattern
- restrict ignition role search in current and one below dir
- merge ignition found files with kcli generated ones
- kvm: dedicated ignition file per vm
- kvm: prioritize ip from metadata
-  ignition static networking support
- yaml ansible inventory with yamlinventory variable
- handle dnsserver in ignition (by forcing it in resolv.conf and preventing network manager to ever touch it)
-  remove bold stuff from pretty prints
- Fixed bug avoiding disk additions to current plans (sperez++)
- handle client field from plan when using ansible
- only store plan group for ansible yaml inv
- delete ansible generated inventories when deleting plan
- start/stop vms from plan when vms spread in different hypervisors





2019-05-16T19:09:32Z


- ovirt: ignition support along with ignition vdsm hook
- kvm: fix for mixed reserveip/reservedns
- restart plan with single command
- New Redhat Logo, for mikel
- download rhel80
- kvm: default to 127.0.0.1 for display when run locally
- updated fedora coreos url
- use ignition 3.0.0 version only for fedora coreos


2019-04-08T08:47:49Z


- switch to yaml.safe_load instead of yaml.load to prevent warnings (and exploits)


2019-04-03T15:46:41Z


- enable fedora 30 and rawhide builds


2019-03-25T09:15:20Z


- kvm: emulate dns entries with dnsmasq when using a bridged nic
- kvm: allow to delete disk by device name
- kvm: basic support for emulating location from virt-install
- kvm: support for custom kernel, initrd, cmdline
- kvm: add support for sharedfolders (despite missing 9p on centos7 hosts)
- kvm: handle missing networks in kcli info
- ovirt: additional check when listing disks
- ovirt: preliminary placement support
- ovirt: properly handle update_memory for running vms
- ovirt: ignore cni0
- ovirt: fix scp upload
- ovirt: print warning when using memory from template
- ovirt: properly evaluate nic profile_id in download template workflow
- ovirt: properly stop powering_up vms
- ovirt: fix issue with download
- kubevirt: ignition support
- kubevirt: properly delete pvc based disks
- kubevirt: enable ssh access from outside using tunnel or nodeport
- aws: dont print vm name twice upon creation
- aws: make sure we cant create vm with same name twice
- specify user when using ansible, configure ansible user within plan
- initial set of tests for libvirt and fake
- auto gunzip images
- Reference raw github file, not html rendered one (robipolli++)
- Update defaults.py to fix centos7atomic template (javilinux++)
- updated debian instructions
- always report the consolecommand in container
-  default to tunnel True when bootstrapping a remote kvm host
- web: properly report status



2019-01-19T18:51:21Z


check 14.3


2019-01-19T18:07:49Z



- remediation of memory and autostart for plan
- remediation of disks and nets for plan
- remediation of cpus of plan
- containers:  kubernetes provider
- containers: allow to specify a different containerclient for a given client
- containers: allow to overrides containerclient on command line
- containers: supports replicas overrides
- kvm: allows deploying a vm without template when cloudinit is set to True
- kvm: report error when trying to live reduce number of cpus
- kvm: support for qemu:///session
- kvm: browse through pools when deleting a template
- kvm: fix console when no tunnel
- kubevirt: allow to live migrate by default
- kubevirt: use namespace from context if not specified
- kubevirt: conditionally enable readwritemany
- kubevirt: defaults to listing vm in current context namespace
- gcp: update cpu/memory
- gcp: fix scp as root
- gcp: fix no rendering option in files section
- gcp: support permanent ips when reserving dns
- aws: add_disk
- awd: delete_disk
- aws: update cpu/memory
- aws: minimal report
- ovirt: update cpu/memory
- ovirt: delete_disk
- ovirt: delete_nic
- ovirt: report pool
- openstack: update cpu/memory
- openstack, gcp, aws: update flavor
- fake: generate a plan dir with all the assets
- fake: automatically add fake provider in the config
- make sure reboot is the last executed command if present
- launch notifycmd prior to rebooting
- use default parameter from current plan when its defined there and in baseplan
- use value from vm when not using a parameter
- snapshot of plan
- support for basevm in plan
- properly evaluate basedir when using baseplan/basevm
- rename host to client and dnshost to dnsclient when used in plans
- handle baseplan when using plan with url
- provide information for remote plans and delete intermediary directory
- fix paramfiles rendering and overriding parameters on command line
- make name available when rendering files and scripts
- fix custom dnsclient deletion
- complete sample config file
- throw a rendering error for undefined variables
- move plan samples to kcli-plans repo
- include default values when bootstrapping
- handle in a simpler way plan info


2018-12-19T16:08:20Z


- all: notify support with push bullet tokens
- secrets handling in dedicated file ~/.kcli/secrets.yml
- complete product logic refactoring to ease use
- support for file attribute in plan to use with plan of plans
- improvements of plan using a url, downloading artifacts on the fly and properly cleaning after deployment
- make sure that values at vm level have priority other profile
- ovirt: download of image
- ovirt:  allows to filter vms created by kcli, by user or with a specific filter tag
- ovirt,openstack: handle download urls with bash special chars
- ovirt: dont leak password as metadata
- ovirt: add a default nic when creating a template
- ovirt: properly gather vnic profiles by filtering by dc
- ovirt: make sure to create only nics not in template and add_nic
- kvm:  defaults to force dns update at deploy time
- kvm: capture memory errors upon start
- kvm: force reservedns when alias found
- fix klist.py after refactoring the list function
- kubevirt: switch to containerDisks
- kubevirt: additional container disk images for ubuntu, debian, gentoo and arch
- kubevirt: use namespace from context
- gcp: only store metadata keys not already defined
- web: cleaner refresh on creation
- web: allow passing parameters when creating a vm
- web: escape when hitting cancel on vm creation

Also note that plans were moved to a dedicated github repo ( and out of the rpm)


2018-11-29T14:09:01Z


- switch to default jinja delimiters {{ and }} for rendering
- capture incorrect jinja templating errors
- all: delete_image support
- all: conditionally store metadata as a file /root/.metadata in the vm with yaml info of the overrides
- gcp: fix ssh credentials when using self made image
- openstack: better report networks
- openstack: aggregate subnets in list networks
- openstack: improve ssh access
- better message for missing rhn data
- several updates in origin, istio, kubedev, and openshift multi plans

Note that the change of delimiters will force an update for plans using the old [[ and ]] delimiters.
The following oneliner can be applied to update recursively all plans and their associated files:

`find . -type f -exec sed -i -e 's/\[\[/{{/g' -e 's/\]\]/}}/g' -e 's/\[%/{%/g' -e 's/%\]/%}/g'  {} +`






2018-11-23T13:27:10Z


- kvm: fix info with snapshots
- kvm: fix kcli list --plans with multiple host
- kubevirt: detect cdinamespace more precisely
- gcp: get correct user for vms missing template
- update openstack plan



2018-11-21T17:52:01Z


- kvm: only list physical networks associated to bridges
- kvm: fix scp (for download)
- kvm: fix static ip reporting
-  kvm: handle listing and deletion of plans when there are vms with no plan info
- kubevirt: support for token auth
- kubevirt: reservedns
- kubevirt: autodetect if cdi is there
- kubevirt: fix cdi import template
- kubevirt: report
- kubevirt: node port for ssh
- kubevirt: custom networks even at index 0
- use insecure for tunnel ssh
- subscribe rhel8 to correct channel
- plans: updated kubevirt and origin plans
- plans: switch to k8s for kubevirt with multus
- updated ubuntu disk images
- fix kcli -C all list
- properly handle lastvm within plans
- fix host section in kcli plan
- list_containers fix


2018-11-21T17:08:30Z


[release notes](http://kcli.readthedocs.io/en/latest/#changelog)


2018-11-08T11:54:49Z


- all: load balancing  feature (command line and plan)
- web: hoover over vm name to get its info
- kvm: also check the ip from reserveip entry
- kvm: fix ignitiondata wrong copy command
- kvm: don't launch reservedns with bridged nics
- ovirt: force hostname to fqdn if domain is present
- ovirt: fix filtering and dnshost
- remove ansible modules from extras as they have their own repos
- fedora29 and rhel7.6 download links



2018-10-23T19:52:47Z


- kvm: switch to domifaddr and drop detect_bridge_ips


2018-10-23T15:08:57Z


- only check client when makes sense, so config is loaded only once
- support for dnshost allowing to create vms on a host, but have their dns records created on another
- extend optional use of private key from .kcli dir to all ssh commands in kvm provider
- kvm: force insecure mode in qemu uri if used from a container
- kvm: fix ssh_credentials for static ips
- fix utf8 issue when using kcli update
- ovirt: filteruser
- ovirt: set memory at creation time and with update
- ovirt: properly report plan and profile and add plan to overrides
- ovirt: fix plan deletion
- ovirt: dont force dns
- ovirt: inject additional keys
- ovirt: spice and vnc console
-  ovirt: handle thick disks
-  ovirt: attach/detach iso
- ovirt: boot from iso
- ovirt: install guest agent in the beginning
- ovirt: subscribe rhel vm before installing guest agent
- ovirt: force guest agent to ignore docker0 and tun0 ips
- ovirt: also create when setting noconf
- aws: allow overriding user for kcli ssh
- handle ovirt lack of dns in openshift multi plan
- make sure kcli info can be used with stdout
- refactor info so it can be used as basis for kvirt_info ansible module
- extra container image for running ansible with kcli modules
- only report network deletion when it really happens
- fix kcli scp from container
- defaults to insecure when run from container and no ssh or kcli conf has been supplied
- use clients instead of hosts for listing


2018-10-11T16:12:24Z


- kvm: detect ips from bridges with helper scapy script (detect_bridge_ips feature)
- kvm: improves kcli ssh speed by getting only ip from guest
- gcp: fix multiple keys injection
- expose rhn variables as parameters and use them in openshift multi plan



2018-10-10T18:16:51Z


 - fix relative paths for files and scripts in plan


2018-10-10T15:33:52Z


- use override parameters for profile in kcli vm!
- use pub and priv keys if found in the .kcli dir
- remove duplicate code between plan and create_vm and reimplement overriding ips
- Codeformatting. iranzo++
- conditionally render files (render keyword)
-  info on running on kubernetes/openshift
- support rhnpool

- kvm: fix stupid dns regression
- kvm: use existing ignition files
- aws,gcp,openstack: ignition support
- ovirt: list_networks
- ovirt: dont regenerate ssh keys
- ovirt: ssh/scp allow forcing user
- ovirt: capture exception when vm fails to create
- ovirt: restart
- ovirt: report isos
- openstack: dont use domain when auth_url ends in v2.0
- openstack:  report vms with blank images
- gcp: capture exception when deploying from a wrong template

- switch to alpine3.8 to avoid stack sizes with ovirt provider
- better handling of kcli download with a custom url
- handle prefix in list_networks
- sample playbooks to use with ansible modules
- switch to alpine3.8 to avoid stack sizes with ovirt provider
- document how to use podman
- handle vlan when creating network in plan
- implement net_exists for remaining providers
- remove old legacy plans and use rhnregister instead of register.sh
- latest okd plan
- document privatekey keyword
- remove topology and scale as rendering plans provide the same functionality




