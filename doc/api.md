---
description: |
    API documentation for modules: kvirt, kvirt.ansibleutils, kvirt.aws, kvirt.baseconfig, kvirt.cli, kvirt.common, kvirt.config, kvirt.container, kvirt.containerconfig, kvirt.defaults, kvirt.examples, kvirt.gcp, kvirt.internalplans, kvirt.jinjafilters, kvirt.kubeadm, kvirt.kubecommon, kvirt.kubernetes, kvirt.kubevirt, kvirt.kvm, kvirt.nameutils, kvirt.openshift, kvirt.openstack, kvirt.ovirt, kvirt.ovirt.helpers, kvirt.sampleprovider, kvirt.version, kvirt.vsphere, kvirt.vsphere.helpers, kvirt.web.

lang: en

classoption: oneside
geometry: margin=1in
papersize: a4

linkcolor: blue
links-as-notes: true
...


    
# Module `kvirt` {#kvirt}





    
## Sub-modules

* [kvirt.ansibleutils](#kvirt.ansibleutils)
* [kvirt.aws](#kvirt.aws)
* [kvirt.baseconfig](#kvirt.baseconfig)
* [kvirt.cli](#kvirt.cli)
* [kvirt.common](#kvirt.common)
* [kvirt.config](#kvirt.config)
* [kvirt.container](#kvirt.container)
* [kvirt.containerconfig](#kvirt.containerconfig)
* [kvirt.defaults](#kvirt.defaults)
* [kvirt.examples](#kvirt.examples)
* [kvirt.gcp](#kvirt.gcp)
* [kvirt.internalplans](#kvirt.internalplans)
* [kvirt.jinjafilters](#kvirt.jinjafilters)
* [kvirt.kubeadm](#kvirt.kubeadm)
* [kvirt.kubecommon](#kvirt.kubecommon)
* [kvirt.kubernetes](#kvirt.kubernetes)
* [kvirt.kubevirt](#kvirt.kubevirt)
* [kvirt.kvm](#kvirt.kvm)
* [kvirt.nameutils](#kvirt.nameutils)
* [kvirt.openshift](#kvirt.openshift)
* [kvirt.openstack](#kvirt.openstack)
* [kvirt.ovirt](#kvirt.ovirt)
* [kvirt.sampleprovider](#kvirt.sampleprovider)
* [kvirt.version](#kvirt.version)
* [kvirt.vsphere](#kvirt.vsphere)
* [kvirt.web](#kvirt.web)






    
# Module `kvirt.ansibleutils` {#kvirt.ansibleutils}

interact with a local/remote libvirt daemon





    
## Functions


    
### Function `make_plan_inventory` {#kvirt.ansibleutils.make_plan_inventory}



    
> `def make_plan_inventory(vms_to_host, plan, vms, groups={}, user=None, yamlinventory=False)`


:param vms_per_host:
:param plan:
:param vms:
:param groups:
:param user:
:param yamlinventory:


    
### Function `play` {#kvirt.ansibleutils.play}



    
> `def play(k, name, playbook, variables=[], verbose=False, user=None, tunnel=False, tunnelhost=None, tunnelport=None, tunneluser=None, yamlinventory=False)`


:param k:
:param name:
:param playbook:
:param variables:
:param verbose:
:param tunnelhost:
:param tunnelport:
:param tunneluser:


    
### Function `vm_inventory` {#kvirt.ansibleutils.vm_inventory}



    
> `def vm_inventory(k, name, user=None, yamlinventory=False)`


:param self:
:param name:
:return:





    
# Module `kvirt.aws` {#kvirt.aws}

Aws Provider Class






    
## Classes


    
### Class `Kaws` {#kvirt.aws.Kaws}



> `class Kaws(access_key_id=None, access_key_secret=None, debug=False, region='eu-west-3', keypair=None)`











    
#### Methods


    
##### Method `add_disk` {#kvirt.aws.Kaws.add_disk}



    
> `def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:


    
##### Method `add_image` {#kvirt.aws.Kaws.add_image}



    
> `def add_image(self, image, pool, short=None, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_nic` {#kvirt.aws.Kaws.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `clone` {#kvirt.aws.Kaws.clone}



    
> `def clone(self, old, new, full=False, start=False)`


:param old:
:param new:
:param full:
:param start:
:return:


    
##### Method `close` {#kvirt.aws.Kaws.close}



    
> `def close(self)`


:return:


    
##### Method `console` {#kvirt.aws.Kaws.console}



    
> `def console(self, name, tunnel=False, web=False)`


:param name:
:param tunnel:
:return:


    
##### Method `create` {#kvirt.aws.Kaws.create}



    
> `def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags=[], dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param flavor:
:param plan:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param numcpus:
:param memory:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param alias:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_disk` {#kvirt.aws.Kaws.create_disk}



    
> `def create_disk(self, name, size, pool=None, thin=True, image=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:


    
##### Method `create_loadbalancer` {#kvirt.aws.Kaws.create_loadbalancer}



    
> `def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[], internal=False)`





    
##### Method `create_network` {#kvirt.aws.Kaws.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param overrides:
:return:


    
##### Method `create_pool` {#kvirt.aws.Kaws.create_pool}



    
> `def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None)`


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:


    
##### Method `delete` {#kvirt.aws.Kaws.delete}



    
> `def delete(self, name, snapshots=False)`


:param name:
:param snapshots:
:return:


    
##### Method `delete_disk` {#kvirt.aws.Kaws.delete_disk}



    
> `def delete_disk(self, name=None, diskname=None, pool=None)`


:param name:
:param diskname:
:param pool:
:return:


    
##### Method `delete_dns` {#kvirt.aws.Kaws.delete_dns}



    
> `def delete_dns(self, name, domain, instanceid=None)`


:param name:
:param domain:
:param instanceid:
:return:


    
##### Method `delete_image` {#kvirt.aws.Kaws.delete_image}



    
> `def delete_image(self, image)`





    
##### Method `delete_loadbalancer` {#kvirt.aws.Kaws.delete_loadbalancer}



    
> `def delete_loadbalancer(self, name)`





    
##### Method `delete_network` {#kvirt.aws.Kaws.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:param cidr:
:return:


    
##### Method `delete_nic` {#kvirt.aws.Kaws.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface:
:return:


    
##### Method `delete_pool` {#kvirt.aws.Kaws.delete_pool}



    
> `def delete_pool(self, name, full=False)`


:param name:
:param full:
:return:


    
##### Method `disk_exists` {#kvirt.aws.Kaws.disk_exists}



    
> `def disk_exists(self, pool, name)`


:param pool:
:param name:


    
##### Method `dnsinfo` {#kvirt.aws.Kaws.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:param output:
:param fields:
:param values:
:return:


    
##### Method `exists` {#kvirt.aws.Kaws.exists}



    
> `def exists(self, name)`


:param name:
:return:


    
##### Method `export` {#kvirt.aws.Kaws.export}



    
> `def export(self, name, image=None)`


:param name:
:param image:
:return:


    
##### Method `flavors` {#kvirt.aws.Kaws.flavors}



    
> `def flavors(self)`


:return:


    
##### Method `get_id` {#kvirt.aws.Kaws.get_id}



    
> `def get_id(self, name)`


:param name:
:return:


    
##### Method `get_pool_path` {#kvirt.aws.Kaws.get_pool_path}



    
> `def get_pool_path(self, pool)`


:param pool:
:return:


    
##### Method `get_security_group_id` {#kvirt.aws.Kaws.get_security_group_id}



    
> `def get_security_group_id(self, name, vpcid)`


:return:


    
##### Method `get_security_groups` {#kvirt.aws.Kaws.get_security_groups}



    
> `def get_security_groups(self, name)`


:param name:
:return:


    
##### Method `info` {#kvirt.aws.Kaws.info}



    
> `def info(self, name, vm=None, debug=False)`


:param name:
:param vm:
:return:


    
##### Method `internalip` {#kvirt.aws.Kaws.internalip}



    
> `def internalip(self, name)`


:param name:
:return:


    
##### Method `ip` {#kvirt.aws.Kaws.ip}



    
> `def ip(self, name)`


:param name:
:return:


    
##### Method `list` {#kvirt.aws.Kaws.list}



    
> `def list(self)`


:return:


    
##### Method `list_disks` {#kvirt.aws.Kaws.list_disks}



    
> `def list_disks(self)`


:return:


    
##### Method `list_dns` {#kvirt.aws.Kaws.list_dns}



    
> `def list_dns(self, domain)`


:param domain:
:return:


    
##### Method `list_loadbalancers` {#kvirt.aws.Kaws.list_loadbalancers}



    
> `def list_loadbalancers(self)`





    
##### Method `list_networks` {#kvirt.aws.Kaws.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.aws.Kaws.list_pools}



    
> `def list_pools(self)`


:return:


    
##### Method `list_subnets` {#kvirt.aws.Kaws.list_subnets}



    
> `def list_subnets(self)`


:return:


    
##### Method `net_exists` {#kvirt.aws.Kaws.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `network_ports` {#kvirt.aws.Kaws.network_ports}



    
> `def network_ports(self, name)`


:param name:
:return:


    
##### Method `report` {#kvirt.aws.Kaws.report}



    
> `def report(self)`


:return:


    
##### Method `reserve_dns` {#kvirt.aws.Kaws.reserve_dns}



    
> `def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None)`


:param name:
:param nets:
:param domain:
:param ip:
:param alias:
:param force:
:param instanceid:
:return:


    
##### Method `restart` {#kvirt.aws.Kaws.restart}



    
> `def restart(self, name)`


:param name:
:return:


    
##### Method `scp` {#kvirt.aws.Kaws.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `serialconsole` {#kvirt.aws.Kaws.serialconsole}



    
> `def serialconsole(self, name)`


:param name:
:return:


    
##### Method `snapshot` {#kvirt.aws.Kaws.snapshot}



    
> `def snapshot(self, name, base, revert=False, delete=False, listing=False)`


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:


    
##### Method `ssh` {#kvirt.aws.Kaws.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.aws.Kaws.start}



    
> `def start(self, name)`


:param name:
:return:


    
##### Method `status` {#kvirt.aws.Kaws.status}



    
> `def status(self, name)`


:param name:
:return:


    
##### Method `stop` {#kvirt.aws.Kaws.stop}



    
> `def stop(self, name)`


:param name:
:return:


    
##### Method `update_cpus` {#kvirt.aws.Kaws.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_flavor` {#kvirt.aws.Kaws.update_flavor}



    
> `def update_flavor(self, name, flavor)`


:param name:
:param flavor:
:return:


    
##### Method `update_information` {#kvirt.aws.Kaws.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.aws.Kaws.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.aws.Kaws.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.aws.Kaws.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`


:param name:
:param metatype:
:param metavalue:
:return:


    
##### Method `update_start` {#kvirt.aws.Kaws.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.aws.Kaws.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
:return:


    
##### Method `volumes` {#kvirt.aws.Kaws.volumes}



    
> `def volumes(self, iso=False)`


:param iso:
:return:




    
# Module `kvirt.baseconfig` {#kvirt.baseconfig}

Kvirt config class






    
## Classes


    
### Class `Kbaseconfig` {#kvirt.baseconfig.Kbaseconfig}



> `class Kbaseconfig(client=None, containerclient=None, debug=False, quiet=False)`







    
#### Descendants

* [kvirt.config.Kconfig](#kvirt.config.Kconfig)





    
#### Methods


    
##### Method `create_profile` {#kvirt.baseconfig.Kbaseconfig.create_profile}



    
> `def create_profile(self, profile, overrides={}, quiet=False)`





    
##### Method `create_repo` {#kvirt.baseconfig.Kbaseconfig.create_repo}



    
> `def create_repo(self, name, url)`


:param name:
:param url:
:return:


    
##### Method `delete_profile` {#kvirt.baseconfig.Kbaseconfig.delete_profile}



    
> `def delete_profile(self, profile, quiet=False)`





    
##### Method `delete_repo` {#kvirt.baseconfig.Kbaseconfig.delete_repo}



    
> `def delete_repo(self, name)`


:param name:
:return:


    
##### Method `disable_host` {#kvirt.baseconfig.Kbaseconfig.disable_host}



    
> `def disable_host(self, client)`


:param client:
:return:


    
##### Method `enable_host` {#kvirt.baseconfig.Kbaseconfig.enable_host}



    
> `def enable_host(self, client)`


:param client:
:return:


    
##### Method `info_plan` {#kvirt.baseconfig.Kbaseconfig.info_plan}



    
> `def info_plan(self, inputfile, quiet=False, web=False, onfly=None)`


:param inputfile:
:param quiet:
:return:


    
##### Method `info_product` {#kvirt.baseconfig.Kbaseconfig.info_product}



    
> `def info_product(self, name, repo=None, group=None, web=False)`


Info product


    
##### Method `list_containerprofiles` {#kvirt.baseconfig.Kbaseconfig.list_containerprofiles}



    
> `def list_containerprofiles(self)`


:return:


    
##### Method `list_flavors` {#kvirt.baseconfig.Kbaseconfig.list_flavors}



    
> `def list_flavors(self)`


:return:


    
##### Method `list_keywords` {#kvirt.baseconfig.Kbaseconfig.list_keywords}



    
> `def list_keywords(self)`





    
##### Method `list_products` {#kvirt.baseconfig.Kbaseconfig.list_products}



    
> `def list_products(self, group=None, repo=None)`


:param group:
:param repo:
:return:


    
##### Method `list_profiles` {#kvirt.baseconfig.Kbaseconfig.list_profiles}



    
> `def list_profiles(self)`


:return:


    
##### Method `list_repos` {#kvirt.baseconfig.Kbaseconfig.list_repos}



    
> `def list_repos(self)`


:return:


    
##### Method `process_inputfile` {#kvirt.baseconfig.Kbaseconfig.process_inputfile}



    
> `def process_inputfile(self, plan, inputfile, overrides={}, onfly=None, full=False, ignore=False, download_mode=False)`





    
##### Method `set_defaults` {#kvirt.baseconfig.Kbaseconfig.set_defaults}



    
> `def set_defaults(self)`





    
##### Method `switch_host` {#kvirt.baseconfig.Kbaseconfig.switch_host}



    
> `def switch_host(self, client)`


:param client:
:return:


    
##### Method `update_profile` {#kvirt.baseconfig.Kbaseconfig.update_profile}



    
> `def update_profile(self, profile, overrides={}, quiet=False)`





    
##### Method `update_repo` {#kvirt.baseconfig.Kbaseconfig.update_repo}



    
> `def update_repo(self, name, url=None)`


:param name:
:param url:
:return:




    
# Module `kvirt.cli` {#kvirt.cli}







    
## Functions


    
### Function `alias` {#kvirt.cli.alias}



    
> `def alias(text)`





    
### Function `autostart_plan` {#kvirt.cli.autostart_plan}



    
> `def autostart_plan(args)`


Autostart plan


    
### Function `cli` {#kvirt.cli.cli}



    
> `def cli()`





    
### Function `clone_vm` {#kvirt.cli.clone_vm}



    
> `def clone_vm(args)`


Clone existing vm


    
### Function `console_container` {#kvirt.cli.console_container}



    
> `def console_container(args)`


Container console


    
### Function `console_vm` {#kvirt.cli.console_vm}



    
> `def console_vm(args)`


Vnc/Spice/Serial Vm console


    
### Function `create_container` {#kvirt.cli.create_container}



    
> `def create_container(args)`


Create container


    
### Function `create_dns` {#kvirt.cli.create_dns}



    
> `def create_dns(args)`


Create dns entries


    
### Function `create_host_aws` {#kvirt.cli.create_host_aws}



    
> `def create_host_aws(args)`


Create Aws Host


    
### Function `create_host_gcp` {#kvirt.cli.create_host_gcp}



    
> `def create_host_gcp(args)`


Create Gcp Host


    
### Function `create_host_kubevirt` {#kvirt.cli.create_host_kubevirt}



    
> `def create_host_kubevirt(args)`


Create Kubevirt Host


    
### Function `create_host_kvm` {#kvirt.cli.create_host_kvm}



    
> `def create_host_kvm(args)`


Generate Kvm Host


    
### Function `create_host_openstack` {#kvirt.cli.create_host_openstack}



    
> `def create_host_openstack(args)`


Create Openstack Host


    
### Function `create_host_ovirt` {#kvirt.cli.create_host_ovirt}



    
> `def create_host_ovirt(args)`


Create Ovirt Host


    
### Function `create_host_vsphere` {#kvirt.cli.create_host_vsphere}



    
> `def create_host_vsphere(args)`


Create Vsphere Host


    
### Function `create_kube` {#kvirt.cli.create_kube}



    
> `def create_kube(args)`


Create kube


    
### Function `create_lb` {#kvirt.cli.create_lb}



    
> `def create_lb(args)`


Create loadbalancer


    
### Function `create_network` {#kvirt.cli.create_network}



    
> `def create_network(args)`


Create Network


    
### Function `create_plan` {#kvirt.cli.create_plan}



    
> `def create_plan(args)`


Create plan


    
### Function `create_pool` {#kvirt.cli.create_pool}



    
> `def create_pool(args)`


Create/Delete pool


    
### Function `create_product` {#kvirt.cli.create_product}



    
> `def create_product(args)`


Create product


    
### Function `create_profile` {#kvirt.cli.create_profile}



    
> `def create_profile(args)`


Create profile


    
### Function `create_repo` {#kvirt.cli.create_repo}



    
> `def create_repo(args)`


Create repo


    
### Function `create_vm` {#kvirt.cli.create_vm}



    
> `def create_vm(args)`


Create vms


    
### Function `create_vmdisk` {#kvirt.cli.create_vmdisk}



    
> `def create_vmdisk(args)`


Add disk to vm


    
### Function `create_vmnic` {#kvirt.cli.create_vmnic}



    
> `def create_vmnic(args)`


Add nic to vm


    
### Function `delete_container` {#kvirt.cli.delete_container}



    
> `def delete_container(args)`


Delete container


    
### Function `delete_dns` {#kvirt.cli.delete_dns}



    
> `def delete_dns(args)`


Delete dns entries


    
### Function `delete_host` {#kvirt.cli.delete_host}



    
> `def delete_host(args)`


Delete host


    
### Function `delete_image` {#kvirt.cli.delete_image}



    
> `def delete_image(args)`





    
### Function `delete_kube` {#kvirt.cli.delete_kube}



    
> `def delete_kube(args)`


Delete kube


    
### Function `delete_lb` {#kvirt.cli.delete_lb}



    
> `def delete_lb(args)`


Delete loadbalancer


    
### Function `delete_network` {#kvirt.cli.delete_network}



    
> `def delete_network(args)`


Delete Network


    
### Function `delete_plan` {#kvirt.cli.delete_plan}



    
> `def delete_plan(args)`


Delete plan


    
### Function `delete_pool` {#kvirt.cli.delete_pool}



    
> `def delete_pool(args)`


Delete pool


    
### Function `delete_profile` {#kvirt.cli.delete_profile}



    
> `def delete_profile(args)`


Delete profile


    
### Function `delete_repo` {#kvirt.cli.delete_repo}



    
> `def delete_repo(args)`


Delete repo


    
### Function `delete_vm` {#kvirt.cli.delete_vm}



    
> `def delete_vm(args)`


Delete vm


    
### Function `delete_vmdisk` {#kvirt.cli.delete_vmdisk}



    
> `def delete_vmdisk(args)`


Delete disk of vm


    
### Function `delete_vmnic` {#kvirt.cli.delete_vmnic}



    
> `def delete_vmnic(args)`


Delete nic of vm


    
### Function `disable_host` {#kvirt.cli.disable_host}



    
> `def disable_host(args)`


Disable host


    
### Function `download_image` {#kvirt.cli.download_image}



    
> `def download_image(args)`


Download Image


    
### Function `download_kubectl` {#kvirt.cli.download_kubectl}



    
> `def download_kubectl(args)`


Download Kubectl


    
### Function `download_oc` {#kvirt.cli.download_oc}



    
> `def download_oc(args)`


Download Oc


    
### Function `download_openshift_installer` {#kvirt.cli.download_openshift_installer}



    
> `def download_openshift_installer(args)`


Download Openshift Installer


    
### Function `download_plan` {#kvirt.cli.download_plan}



    
> `def download_plan(args)`


Download plan


    
### Function `enable_host` {#kvirt.cli.enable_host}



    
> `def enable_host(args)`


Enable host


    
### Function `export_vm` {#kvirt.cli.export_vm}



    
> `def export_vm(args)`


Export a vm


    
### Function `get_subparser` {#kvirt.cli.get_subparser}



    
> `def get_subparser(parser, subcommand)`





    
### Function `get_subparser_print_help` {#kvirt.cli.get_subparser_print_help}



    
> `def get_subparser_print_help(parser, subcommand)`





    
### Function `info_kube` {#kvirt.cli.info_kube}



    
> `def info_kube(args)`


Info kube


    
### Function `info_plan` {#kvirt.cli.info_plan}



    
> `def info_plan(args)`


Info plan


    
### Function `info_product` {#kvirt.cli.info_product}



    
> `def info_product(args)`


Info product


    
### Function `info_vm` {#kvirt.cli.info_vm}



    
> `def info_vm(args)`


Get info on vm


    
### Function `list_container` {#kvirt.cli.list_container}



    
> `def list_container(args)`


List containers


    
### Function `list_containerimage` {#kvirt.cli.list_containerimage}



    
> `def list_containerimage(args)`


List container images


    
### Function `list_dns` {#kvirt.cli.list_dns}



    
> `def list_dns(args)`


List flavors


    
### Function `list_flavor` {#kvirt.cli.list_flavor}



    
> `def list_flavor(args)`


List flavors


    
### Function `list_host` {#kvirt.cli.list_host}



    
> `def list_host(args)`


List hosts


    
### Function `list_image` {#kvirt.cli.list_image}



    
> `def list_image(args)`


List images


    
### Function `list_iso` {#kvirt.cli.list_iso}



    
> `def list_iso(args)`


List isos


    
### Function `list_keyword` {#kvirt.cli.list_keyword}



    
> `def list_keyword(args)`


List keywords


    
### Function `list_lb` {#kvirt.cli.list_lb}



    
> `def list_lb(args)`


List lbs


    
### Function `list_network` {#kvirt.cli.list_network}



    
> `def list_network(args)`


List networks


    
### Function `list_plan` {#kvirt.cli.list_plan}



    
> `def list_plan(args)`


List plans


    
### Function `list_pool` {#kvirt.cli.list_pool}



    
> `def list_pool(args)`


List pools


    
### Function `list_product` {#kvirt.cli.list_product}



    
> `def list_product(args)`


List products


    
### Function `list_profile` {#kvirt.cli.list_profile}



    
> `def list_profile(args)`


List profiles


    
### Function `list_repo` {#kvirt.cli.list_repo}



    
> `def list_repo(args)`


List repos


    
### Function `list_vm` {#kvirt.cli.list_vm}



    
> `def list_vm(args)`


List vms


    
### Function `list_vmdisk` {#kvirt.cli.list_vmdisk}



    
> `def list_vmdisk(args)`


List vm disks


    
### Function `noautostart_plan` {#kvirt.cli.noautostart_plan}



    
> `def noautostart_plan(args)`


Noautostart plan


    
### Function `profilelist_container` {#kvirt.cli.profilelist_container}



    
> `def profilelist_container(args)`


List container profiles


    
### Function `render_file` {#kvirt.cli.render_file}



    
> `def render_file(args)`


Render file


    
### Function `report_host` {#kvirt.cli.report_host}



    
> `def report_host(args)`


Report info about host


    
### Function `restart_container` {#kvirt.cli.restart_container}



    
> `def restart_container(args)`


Restart containers


    
### Function `restart_plan` {#kvirt.cli.restart_plan}



    
> `def restart_plan(args)`


Restart plan


    
### Function `restart_vm` {#kvirt.cli.restart_vm}



    
> `def restart_vm(args)`


Restart vms


    
### Function `revert_plan` {#kvirt.cli.revert_plan}



    
> `def revert_plan(args)`


Revert snapshot of plan


    
### Function `scale_kube` {#kvirt.cli.scale_kube}



    
> `def scale_kube(args)`


Scale kube


    
### Function `scp_vm` {#kvirt.cli.scp_vm}



    
> `def scp_vm(args)`


Scp into vm


    
### Function `snapshot_plan` {#kvirt.cli.snapshot_plan}



    
> `def snapshot_plan(args)`


Snapshot plan


    
### Function `snapshotcreate_vm` {#kvirt.cli.snapshotcreate_vm}



    
> `def snapshotcreate_vm(args)`


Create snapshot


    
### Function `snapshotdelete_vm` {#kvirt.cli.snapshotdelete_vm}



    
> `def snapshotdelete_vm(args)`


Delete snapshot


    
### Function `snapshotlist_vm` {#kvirt.cli.snapshotlist_vm}



    
> `def snapshotlist_vm(args)`


List snapshots of vm


    
### Function `snapshotrevert_vm` {#kvirt.cli.snapshotrevert_vm}



    
> `def snapshotrevert_vm(args)`


Revert snapshot of vm


    
### Function `ssh_vm` {#kvirt.cli.ssh_vm}



    
> `def ssh_vm(args)`


Ssh into vm


    
### Function `start_container` {#kvirt.cli.start_container}



    
> `def start_container(args)`


Start containers


    
### Function `start_plan` {#kvirt.cli.start_plan}



    
> `def start_plan(args)`


Start plan


    
### Function `start_vm` {#kvirt.cli.start_vm}



    
> `def start_vm(args)`


Start vms


    
### Function `stop_container` {#kvirt.cli.stop_container}



    
> `def stop_container(args)`


Stop containers


    
### Function `stop_plan` {#kvirt.cli.stop_plan}



    
> `def stop_plan(args)`


Stop plan


    
### Function `stop_vm` {#kvirt.cli.stop_vm}



    
> `def stop_vm(args)`


Stop vms


    
### Function `switch_host` {#kvirt.cli.switch_host}



    
> `def switch_host(args)`


Handle host


    
### Function `sync_host` {#kvirt.cli.sync_host}



    
> `def sync_host(args)`


Handle host


    
### Function `update_plan` {#kvirt.cli.update_plan}



    
> `def update_plan(args)`


Update plan


    
### Function `update_profile` {#kvirt.cli.update_profile}



    
> `def update_profile(args)`


Update profile


    
### Function `update_repo` {#kvirt.cli.update_repo}



    
> `def update_repo(args)`


Update repo


    
### Function `update_vm` {#kvirt.cli.update_vm}



    
> `def update_vm(args)`


Update ip, memory or numcpus


    
### Function `valid_fqdn` {#kvirt.cli.valid_fqdn}



    
> `def valid_fqdn(name)`








    
# Module `kvirt.common` {#kvirt.common}







    
## Functions


    
### Function `cloudinit` {#kvirt.common.cloudinit}



    
> `def cloudinit(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[], enableroot=True, overrides={}, iso=True, fqdn=False, storemetadata=True, image=None, ipv6=[])`


:param name:
:param keys:
:param cmds:
:param nets:
:param gateway:
:param dns:
:param domain:
:param reserveip:
:param files:
:param enableroot:
:param overrides:
:param iso:
:param fqdn:


    
### Function `confirm` {#kvirt.common.confirm}



    
> `def confirm(message)`


:param message:
:return:


    
### Function `create_host` {#kvirt.common.create_host}



    
> `def create_host(data)`


:param data:


    
### Function `delete_host` {#kvirt.common.delete_host}



    
> `def delete_host(name)`


:param name:


    
### Function `fetch` {#kvirt.common.fetch}



    
> `def fetch(url, path)`





    
### Function `find_ignition_files` {#kvirt.common.find_ignition_files}



    
> `def find_ignition_files(role, plan)`





    
### Function `gen_mac` {#kvirt.common.gen_mac}



    
> `def gen_mac()`





    
### Function `get_binary` {#kvirt.common.get_binary}



    
> `def get_binary(name, linuxurl, macosurl, compressed=False)`





    
### Function `get_cloudinitfile` {#kvirt.common.get_cloudinitfile}



    
> `def get_cloudinitfile(image)`


:param image:
:return:


    
### Function `get_free_nodeport` {#kvirt.common.get_free_nodeport}



    
> `def get_free_nodeport()`


:return:


    
### Function `get_free_port` {#kvirt.common.get_free_port}



    
> `def get_free_port()`


:return:


    
### Function `get_kubectl` {#kvirt.common.get_kubectl}



    
> `def get_kubectl()`





    
### Function `get_lastvm` {#kvirt.common.get_lastvm}



    
> `def get_lastvm(client)`


:param client:
:return:


    
### Function `get_latest_fcos` {#kvirt.common.get_latest_fcos}



    
> `def get_latest_fcos(url)`





    
### Function `get_latest_rhcos` {#kvirt.common.get_latest_rhcos}



    
> `def get_latest_rhcos(url)`





    
### Function `get_oc` {#kvirt.common.get_oc}



    
> `def get_oc(macosx=False)`





    
### Function `get_overrides` {#kvirt.common.get_overrides}



    
> `def get_overrides(paramfile=None, param=[])`


:param paramfile:
:param param:
:return:


    
### Function `get_parameters` {#kvirt.common.get_parameters}



    
> `def get_parameters(inputfile, raw=False)`


:param inputfile:
:param raw:
:return:


    
### Function `get_user` {#kvirt.common.get_user}



    
> `def get_user(image)`


:param image:
:return:


    
### Function `get_values` {#kvirt.common.get_values}



    
> `def get_values(data, element, field)`





    
### Function `handle_response` {#kvirt.common.handle_response}



    
> `def handle_response(result, name, quiet=False, element='', action='deployed', client=None)`


:param result:
:param name:
:param quiet:
:param element:
:param action:
:param client:
:return:


    
### Function `ignition` {#kvirt.common.ignition}



    
> `def ignition(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[], enableroot=True, overrides={}, iso=True, fqdn=False, version='3.0.0', plan=None, compact=False, removetls=False, ipv6=[])`


:param name:
:param keys:
:param cmds:
:param nets:
:param gateway:
:param dns:
:param domain:
:param reserveip:
:param files:
:param enableroot:
:param overrides:
:param iso:
:param fqdn:
:return:


    
### Function `ignition_version` {#kvirt.common.ignition_version}



    
> `def ignition_version(image)`





    
### Function `insecure_fetch` {#kvirt.common.insecure_fetch}



    
> `def insecure_fetch(url)`





    
### Function `is_debian` {#kvirt.common.is_debian}



    
> `def is_debian(image)`





    
### Function `mergeignition` {#kvirt.common.mergeignition}



    
> `def mergeignition(name, ignitionextrapath, data)`





    
### Function `need_guest_agent` {#kvirt.common.need_guest_agent}



    
> `def need_guest_agent(image)`





    
### Function `needs_ignition` {#kvirt.common.needs_ignition}



    
> `def needs_ignition(image)`





    
### Function `pprint` {#kvirt.common.pprint}



    
> `def pprint(text, color='green')`


:param text:
:param color:


    
### Function `pretty_print` {#kvirt.common.pretty_print}



    
> `def pretty_print(o, value=False)`


:param o:


    
### Function `print_info` {#kvirt.common.print_info}



    
> `def print_info(yamlinfo, output='plain', fields=[], values=False, pretty=True)`


:param yamlinfo:
:param output:
:param fields:
:param values:


    
### Function `process_cmds` {#kvirt.common.process_cmds}



    
> `def process_cmds(cmds, overrides)`


:param cmds:
:param overrides:
:return:


    
### Function `process_files` {#kvirt.common.process_files}



    
> `def process_files(files=[], overrides={})`


:param files:
:param overrides:
:return:


    
### Function `process_ignition_cmds` {#kvirt.common.process_ignition_cmds}



    
> `def process_ignition_cmds(cmds, overrides)`


:param cmds:
:param overrides:
:return:


    
### Function `process_ignition_files` {#kvirt.common.process_ignition_files}



    
> `def process_ignition_files(files=[], overrides={})`


:param files:
:param overrides:
:return:


    
### Function `pwd_path` {#kvirt.common.pwd_path}



    
> `def pwd_path(x)`





    
### Function `real_path` {#kvirt.common.real_path}



    
> `def real_path(x)`





    
### Function `remove_duplicates` {#kvirt.common.remove_duplicates}



    
> `def remove_duplicates(oldlist)`


:param oldlist:
:return:


    
### Function `scp` {#kvirt.common.scp}



    
> `def scp(name, ip='', host=None, port=22, hostuser=None, user=None, source=None, destination=None, recursive=None, tunnel=False, debug=False, download=False, vmport=None, insecure=False)`


:param name:
:param ip:
:param host:
:param port:
:param hostuser:
:param user:
:param source:
:param destination:
:param recursive:
:param tunnel:
:param debug:
:param download:
:param vmport:
:return:


    
### Function `set_lastvm` {#kvirt.common.set_lastvm}



    
> `def set_lastvm(name, client, delete=False)`


:param name:
:param client:
:param delete:
:return:


    
### Function `ssh` {#kvirt.common.ssh}



    
> `def ssh(name, ip='', host=None, port=22, hostuser=None, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, debug=False, D=None, vmport=None)`


:param name:
:param ip:
:param host:
:param port:
:param hostuser:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param debug:
:param D:
:param vmport:
:return:


    
### Function `url_exists` {#kvirt.common.url_exists}



    
> `def url_exists(url)`





    
### Function `valid_tag` {#kvirt.common.valid_tag}



    
> `def valid_tag(tag)`








    
# Module `kvirt.config` {#kvirt.config}

Kvirt config class






    
## Classes


    
### Class `Kconfig` {#kvirt.config.Kconfig}



> `class Kconfig(client=None, debug=False, quiet=False, region=None, zone=None, namespace=None)`






    
#### Ancestors (in MRO)

* [kvirt.baseconfig.Kbaseconfig](#kvirt.baseconfig.Kbaseconfig)






    
#### Methods


    
##### Method `create_kube_generic` {#kvirt.config.Kconfig.create_kube_generic}



    
> `def create_kube_generic(self, cluster, overrides={})`





    
##### Method `create_kube_openshift` {#kvirt.config.Kconfig.create_kube_openshift}



    
> `def create_kube_openshift(self, cluster, overrides={})`





    
##### Method `create_product` {#kvirt.config.Kconfig.create_product}



    
> `def create_product(self, name, repo=None, group=None, plan=None, latest=False, overrides={})`


Create product


    
##### Method `create_vm` {#kvirt.config.Kconfig.create_vm}



    
> `def create_vm(self, name, profile, overrides={}, customprofile={}, k=None, plan='kvirt', basedir='.', client=None, onfly=None, wait=False, planmode=False)`


:param k:
:param plan:
:param name:
:param profile:
:param overrides:
:param customprofile:
:return:


    
##### Method `delete_kube` {#kvirt.config.Kconfig.delete_kube}



    
> `def delete_kube(self, cluster, overrides={})`





    
##### Method `download_openshift_installer` {#kvirt.config.Kconfig.download_openshift_installer}



    
> `def download_openshift_installer(self, overrides={})`





    
##### Method `handle_host` {#kvirt.config.Kconfig.handle_host}



    
> `def handle_host(self, pool=None, image=None, switch=None, download=False, url=None, cmd=None, sync=False, update_profile=False)`


:param pool:
:param images:
:param switch:
:param download:
:param url:
:param cmd:
:param sync:
:param profile:
:return:


    
##### Method `handle_loadbalancer` {#kvirt.config.Kconfig.handle_loadbalancer}



    
> `def handle_loadbalancer(self, name, nets=['default'], ports=[], checkpath='/', vms=[], delete=False, domain=None, plan=None, checkport=80, alias=[], internal=False)`





    
##### Method `info_kube_generic` {#kvirt.config.Kconfig.info_kube_generic}



    
> `def info_kube_generic(self, quiet)`





    
##### Method `info_kube_openshift` {#kvirt.config.Kconfig.info_kube_openshift}



    
> `def info_kube_openshift(self, quiet)`





    
##### Method `list_loadbalancer` {#kvirt.config.Kconfig.list_loadbalancer}



    
> `def list_loadbalancer(self)`





    
##### Method `list_plans` {#kvirt.config.Kconfig.list_plans}



    
> `def list_plans(self)`


:return:


    
##### Method `plan` {#kvirt.config.Kconfig.plan}



    
> `def plan(self, plan, ansible=False, url=None, path=None, autostart=False, container=False, noautostart=False, inputfile=None, inputstring=None, start=False, stop=False, delete=False, force=True, overrides={}, info=False, snapshot=False, revert=False, update=False, embedded=False, restart=False, download=False, wait=False, quiet=False)`


Manage plan file


    
##### Method `scale_kube_generic` {#kvirt.config.Kconfig.scale_kube_generic}



    
> `def scale_kube_generic(self, cluster, overrides={})`





    
##### Method `scale_kube_openshift` {#kvirt.config.Kconfig.scale_kube_openshift}



    
> `def scale_kube_openshift(self, cluster, overrides={})`





    
##### Method `wait` {#kvirt.config.Kconfig.wait}



    
> `def wait(self, name, image=None)`







    
# Module `kvirt.container` {#kvirt.container}

container utilites






    
## Classes


    
### Class `Kcontainer` {#kvirt.container.Kcontainer}



> `class Kcontainer(host='127.0.0.1', user='root', port=22)`











    
#### Methods


    
##### Method `console_container` {#kvirt.container.Kcontainer.console_container}



    
> `def console_container(self, name)`


:param self:
:param name:
:return:


    
##### Method `create_container` {#kvirt.container.Kcontainer.create_container}



    
> `def create_container(self, name, image, nets=None, cmd=None, ports=[], volumes=[], environment=[], label=None, overrides={})`


:param self:
:param name:
:param image:
:param nets:
:param cmd:
:param ports:
:param volumes:
:param environment:
:param label:
:param overrides:
:return:


    
##### Method `delete_container` {#kvirt.container.Kcontainer.delete_container}



    
> `def delete_container(self, name)`


:param self:
:param name:
:return:


    
##### Method `exists_container` {#kvirt.container.Kcontainer.exists_container}



    
> `def exists_container(self, name)`


:param self:
:param name:
:return:


    
##### Method `list_containers` {#kvirt.container.Kcontainer.list_containers}



    
> `def list_containers(self)`


:param self:
:return:


    
##### Method `list_images` {#kvirt.container.Kcontainer.list_images}



    
> `def list_images(self)`


:param self:
:return:


    
##### Method `start_container` {#kvirt.container.Kcontainer.start_container}



    
> `def start_container(self, name)`


:param self:
:param name:
:return:


    
##### Method `stop_container` {#kvirt.container.Kcontainer.stop_container}



    
> `def stop_container(self, name)`


:param self:
:param name:
:return:




    
# Module `kvirt.containerconfig` {#kvirt.containerconfig}

Kvirt containerconfig class






    
## Classes


    
### Class `Kcontainerconfig` {#kvirt.containerconfig.Kcontainerconfig}



> `class Kcontainerconfig(config, client=None, namespace=None)`













    
# Module `kvirt.defaults` {#kvirt.defaults}










    
# Module `kvirt.examples` {#kvirt.examples}










    
# Module `kvirt.gcp` {#kvirt.gcp}

Gcp Provider Class






    
## Classes


    
### Class `Kgcp` {#kvirt.gcp.Kgcp}



> `class Kgcp(debug=False, project='kubevirt-button', zone='europe-west1-b', region='europe-west1')`











    
#### Methods


    
##### Method `add_disk` {#kvirt.gcp.Kgcp.add_disk}



    
> `def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:


    
##### Method `add_image` {#kvirt.gcp.Kgcp.add_image}



    
> `def add_image(self, image, pool, short=None, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_nic` {#kvirt.gcp.Kgcp.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `clone` {#kvirt.gcp.Kgcp.clone}



    
> `def clone(self, old, new, full=False, start=False)`


:param old:
:param new:
:param full:
:param start:
:return:


    
##### Method `close` {#kvirt.gcp.Kgcp.close}



    
> `def close(self)`


:return:


    
##### Method `console` {#kvirt.gcp.Kgcp.console}



    
> `def console(self, name, tunnel=False, web=False)`


:param name:
:param tunnel:
:return:


    
##### Method `create` {#kvirt.gcp.Kgcp.create}



    
> `def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags=[], dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param flavor:
:param plan:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param numcpus:
:param memory:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param alias:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_disk` {#kvirt.gcp.Kgcp.create_disk}



    
> `def create_disk(self, name, size, pool=None, thin=True, image=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:


    
##### Method `create_loadbalancer` {#kvirt.gcp.Kgcp.create_loadbalancer}



    
> `def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[], internal=False)`





    
##### Method `create_network` {#kvirt.gcp.Kgcp.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param overrides:
:return:


    
##### Method `create_pool` {#kvirt.gcp.Kgcp.create_pool}



    
> `def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None)`


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:


    
##### Method `delete` {#kvirt.gcp.Kgcp.delete}



    
> `def delete(self, name, snapshots=False)`


:param name:
:param snapshots:
:return:


    
##### Method `delete_disk` {#kvirt.gcp.Kgcp.delete_disk}



    
> `def delete_disk(self, name=None, diskname=None, pool=None)`


:param name:
:param diskname:
:param pool:
:return:


    
##### Method `delete_dns` {#kvirt.gcp.Kgcp.delete_dns}



    
> `def delete_dns(self, name, domain)`


:param name:
:param domain:
:return:


    
##### Method `delete_image` {#kvirt.gcp.Kgcp.delete_image}



    
> `def delete_image(self, image)`





    
##### Method `delete_loadbalancer` {#kvirt.gcp.Kgcp.delete_loadbalancer}



    
> `def delete_loadbalancer(self, name)`





    
##### Method `delete_network` {#kvirt.gcp.Kgcp.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:param cidr:
:return:


    
##### Method `delete_nic` {#kvirt.gcp.Kgcp.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface:
:return:


    
##### Method `delete_pool` {#kvirt.gcp.Kgcp.delete_pool}



    
> `def delete_pool(self, name, full=False)`


:param name:
:param full:
:return:


    
##### Method `disk_exists` {#kvirt.gcp.Kgcp.disk_exists}



    
> `def disk_exists(self, pool, name)`


:param pool:
:param name:


    
##### Method `dnsinfo` {#kvirt.gcp.Kgcp.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:return:


    
##### Method `exists` {#kvirt.gcp.Kgcp.exists}



    
> `def exists(self, name)`


:param name:
:return:


    
##### Method `export` {#kvirt.gcp.Kgcp.export}



    
> `def export(self, name, image=None)`


:param name:
:param image:
:return:


    
##### Method `flavors` {#kvirt.gcp.Kgcp.flavors}



    
> `def flavors(self)`


:return:


    
##### Method `get_pool_path` {#kvirt.gcp.Kgcp.get_pool_path}



    
> `def get_pool_path(self, pool)`


:param pool:
:return:


    
##### Method `info` {#kvirt.gcp.Kgcp.info}



    
> `def info(self, name, vm=None, debug=False)`


:param name:
:param vm:
:return:


    
##### Method `internalip` {#kvirt.gcp.Kgcp.internalip}



    
> `def internalip(self, name)`


:param name:
:return:


    
##### Method `ip` {#kvirt.gcp.Kgcp.ip}



    
> `def ip(self, name)`


:param name:
:return:


    
##### Method `list` {#kvirt.gcp.Kgcp.list}



    
> `def list(self)`


:return:


    
##### Method `list_disks` {#kvirt.gcp.Kgcp.list_disks}



    
> `def list_disks(self)`


:return:


    
##### Method `list_dns` {#kvirt.gcp.Kgcp.list_dns}



    
> `def list_dns(self, domain)`


:param domain:
:return:


    
##### Method `list_loadbalancers` {#kvirt.gcp.Kgcp.list_loadbalancers}



    
> `def list_loadbalancers(self)`





    
##### Method `list_networks` {#kvirt.gcp.Kgcp.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.gcp.Kgcp.list_pools}



    
> `def list_pools(self)`


:return:


    
##### Method `list_subnets` {#kvirt.gcp.Kgcp.list_subnets}



    
> `def list_subnets(self)`


:return:


    
##### Method `net_exists` {#kvirt.gcp.Kgcp.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `network_ports` {#kvirt.gcp.Kgcp.network_ports}



    
> `def network_ports(self, name)`


:param name:
:return:


    
##### Method `report` {#kvirt.gcp.Kgcp.report}



    
> `def report(self)`


:return:


    
##### Method `reserve_dns` {#kvirt.gcp.Kgcp.reserve_dns}



    
> `def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False)`


:param name:
:param nets:
:param domain:
:param ip:
:param alias:
:param force:
:return:


    
##### Method `restart` {#kvirt.gcp.Kgcp.restart}



    
> `def restart(self, name)`


:param name:
:return:


    
##### Method `scp` {#kvirt.gcp.Kgcp.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `serialconsole` {#kvirt.gcp.Kgcp.serialconsole}



    
> `def serialconsole(self, name)`


:param name:
:return:


    
##### Method `snapshot` {#kvirt.gcp.Kgcp.snapshot}



    
> `def snapshot(self, name, base, revert=False, delete=False, listing=False)`


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:


    
##### Method `ssh` {#kvirt.gcp.Kgcp.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.gcp.Kgcp.start}



    
> `def start(self, name)`


:param name:
:return:


    
##### Method `status` {#kvirt.gcp.Kgcp.status}



    
> `def status(self, name)`


:param name:
:return:


    
##### Method `stop` {#kvirt.gcp.Kgcp.stop}



    
> `def stop(self, name)`


:param name:
:return:


    
##### Method `update_cpus` {#kvirt.gcp.Kgcp.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_flavor` {#kvirt.gcp.Kgcp.update_flavor}



    
> `def update_flavor(self, name, flavor)`


:param name:
:param memory:
:return:


    
##### Method `update_information` {#kvirt.gcp.Kgcp.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.gcp.Kgcp.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.gcp.Kgcp.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.gcp.Kgcp.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`


:param name:
:param metatype:
:param metavalue:
:return:


    
##### Method `update_start` {#kvirt.gcp.Kgcp.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.gcp.Kgcp.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
:return:


    
##### Method `volumes` {#kvirt.gcp.Kgcp.volumes}



    
> `def volumes(self, iso=False)`


:param iso:
:return:




    
# Module `kvirt.internalplans` {#kvirt.internalplans}










    
# Module `kvirt.jinjafilters` {#kvirt.jinjafilters}







    
## Functions


    
### Function `basename` {#kvirt.jinjafilters.basename}



    
> `def basename(path)`





    
### Function `dirname` {#kvirt.jinjafilters.dirname}



    
> `def dirname(path)`





    
### Function `ocpnodes` {#kvirt.jinjafilters.ocpnodes}



    
> `def ocpnodes(cluster, platform, masters, workers)`








    
# Module `kvirt.kubeadm` {#kvirt.kubeadm}







    
## Functions


    
### Function `create` {#kvirt.kubeadm.create}



    
> `def create(config, plandir, cluster, overrides)`





    
### Function `scale` {#kvirt.kubeadm.scale}



    
> `def scale(config, plandir, cluster, overrides)`








    
# Module `kvirt.kubecommon` {#kvirt.kubecommon}

Kubecommon Base Class






    
## Classes


    
### Class `Kubecommon` {#kvirt.kubecommon.Kubecommon}



> `class Kubecommon(token=None, ca_file=None, context=None, host='127.0.0.1', port=443, user='root', debug=False, namespace=None, readwritemany=False)`







    
#### Descendants

* [kvirt.kubevirt.Kubevirt](#kvirt.kubevirt.Kubevirt)







    
# Module `kvirt.kubernetes` {#kvirt.kubernetes}

kubernetes utilites






    
## Classes


    
### Class `Kubernetes` {#kvirt.kubernetes.Kubernetes}



> `class Kubernetes(host='127.0.0.1', user='root', port=443, token=None, ca_file=None, context=None, namespace='default', readwritemany=False)`











    
#### Methods


    
##### Method `console_container` {#kvirt.kubernetes.Kubernetes.console_container}



    
> `def console_container(self, name)`


:param self:
:param name:
:return:


    
##### Method `create_container` {#kvirt.kubernetes.Kubernetes.create_container}



    
> `def create_container(self, name, image, nets=None, cmd=None, ports=[], volumes=[], environment=[], label=None, overrides={})`


:param self:
:param name:
:param image:
:param nets:
:param cmd:
:param ports:
:param volumes:
:param environment:
:param label:
:param overrides:
:return:


    
##### Method `delete_container` {#kvirt.kubernetes.Kubernetes.delete_container}



    
> `def delete_container(self, name)`


:param self:
:param name:
:return:


    
##### Method `exists_container` {#kvirt.kubernetes.Kubernetes.exists_container}



    
> `def exists_container(self, name)`


:param self:
:param name:
:return:


    
##### Method `list_containers` {#kvirt.kubernetes.Kubernetes.list_containers}



    
> `def list_containers(self)`


:param self:
:return:


    
##### Method `list_images` {#kvirt.kubernetes.Kubernetes.list_images}



    
> `def list_images(self)`


:param self:
:return:


    
##### Method `start_container` {#kvirt.kubernetes.Kubernetes.start_container}



    
> `def start_container(self, name)`


:param self:
:param name:

:return:


    
##### Method `stop_container` {#kvirt.kubernetes.Kubernetes.stop_container}



    
> `def stop_container(self, name)`


:param self:
:param name:
:return:




    
# Module `kvirt.kubevirt` {#kvirt.kubevirt}

Kubevirt Provider Class






    
## Classes


    
### Class `Kubevirt` {#kvirt.kubevirt.Kubevirt}



> `class Kubevirt(token=None, ca_file=None, context=None, multus=True, host='127.0.0.1', port=443, user='root', debug=False, tags=None, namespace=None, cdi=True, datavolumes=True, readwritemany=False)`






    
#### Ancestors (in MRO)

* [kvirt.kubecommon.Kubecommon](#kvirt.kubecommon.Kubecommon)






    
#### Methods


    
##### Method `add_disk` {#kvirt.kubevirt.Kubevirt.add_disk}



    
> `def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:


    
##### Method `add_image` {#kvirt.kubevirt.Kubevirt.add_image}



    
> `def add_image(self, image, pool, short=None, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_nic` {#kvirt.kubevirt.Kubevirt.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `check_pool` {#kvirt.kubevirt.Kubevirt.check_pool}



    
> `def check_pool(self, pool)`


:param pool:
:return:


    
##### Method `clone` {#kvirt.kubevirt.Kubevirt.clone}



    
> `def clone(self, old, new, full=False, start=False)`


:param old:
:param new:
:param full:
:param start:
:return:


    
##### Method `close` {#kvirt.kubevirt.Kubevirt.close}



    
> `def close(self)`


:return:


    
##### Method `console` {#kvirt.kubevirt.Kubevirt.console}



    
> `def console(self, name, tunnel=False, web=False)`


:param name:
:param tunnel:
:return:


    
##### Method `copy_image` {#kvirt.kubevirt.Kubevirt.copy_image}



    
> `def copy_image(self, pool, ori, dest, size=1)`


:param pool:
:param ori:
:param dest:
:param size:
:return:


    
##### Method `create` {#kvirt.kubevirt.Kubevirt.create}



    
> `def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool=None, image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags=[], dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param flavor:
:param plan:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param numcpus:
:param memory:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param alias:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_disk` {#kvirt.kubevirt.Kubevirt.create_disk}



    
> `def create_disk(self, name, size, pool=None, thin=True, image=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:


    
##### Method `create_network` {#kvirt.kubevirt.Kubevirt.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param overrides:
:return:


    
##### Method `create_pool` {#kvirt.kubevirt.Kubevirt.create_pool}



    
> `def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None)`


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:


    
##### Method `delete` {#kvirt.kubevirt.Kubevirt.delete}



    
> `def delete(self, name, snapshots=False)`


:param name:
:param snapshots:
:return:


    
##### Method `delete_disk` {#kvirt.kubevirt.Kubevirt.delete_disk}



    
> `def delete_disk(self, name=None, diskname=None, pool=None)`


:param name:
:param diskname:
:param pool:
:return:


    
##### Method `delete_image` {#kvirt.kubevirt.Kubevirt.delete_image}



    
> `def delete_image(self, image)`





    
##### Method `delete_network` {#kvirt.kubevirt.Kubevirt.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:param cidr:
:return:


    
##### Method `delete_nic` {#kvirt.kubevirt.Kubevirt.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface:
:return:


    
##### Method `delete_pool` {#kvirt.kubevirt.Kubevirt.delete_pool}



    
> `def delete_pool(self, name, full=False)`


:param name:
:param full:
:return:


    
##### Method `disk_exists` {#kvirt.kubevirt.Kubevirt.disk_exists}



    
> `def disk_exists(self, pool, name)`


:param pool:
:param name:
:return:


    
##### Method `dnsinfo` {#kvirt.kubevirt.Kubevirt.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:return:


    
##### Method `exists` {#kvirt.kubevirt.Kubevirt.exists}



    
> `def exists(self, name)`


:param name:
:return:


    
##### Method `flavors` {#kvirt.kubevirt.Kubevirt.flavors}



    
> `def flavors(self)`


:return:


    
##### Method `get_image_name` {#kvirt.kubevirt.Kubevirt.get_image_name}



    
> `def get_image_name(self, name)`


:param name:
:return:


    
##### Method `get_pool_path` {#kvirt.kubevirt.Kubevirt.get_pool_path}



    
> `def get_pool_path(self, pool)`


:param pool:
:return:


    
##### Method `import_completed` {#kvirt.kubevirt.Kubevirt.import_completed}



    
> `def import_completed(self, volname, namespace)`


:param volname:
:param namespace:
:return:


    
##### Method `info` {#kvirt.kubevirt.Kubevirt.info}



    
> `def info(self, name, vm=None, debug=False)`


:param name:
:param vm:
:return:


    
##### Method `ip` {#kvirt.kubevirt.Kubevirt.ip}



    
> `def ip(self, name)`


:param name:
:return:


    
##### Method `list` {#kvirt.kubevirt.Kubevirt.list}



    
> `def list(self)`


:return:


    
##### Method `list_disks` {#kvirt.kubevirt.Kubevirt.list_disks}



    
> `def list_disks(self)`


:return:


    
##### Method `list_dns` {#kvirt.kubevirt.Kubevirt.list_dns}



    
> `def list_dns(self, domain)`


:param domain:
:return:


    
##### Method `list_networks` {#kvirt.kubevirt.Kubevirt.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.kubevirt.Kubevirt.list_pools}



    
> `def list_pools(self)`


:return:


    
##### Method `list_subnets` {#kvirt.kubevirt.Kubevirt.list_subnets}



    
> `def list_subnets(self)`


:return:


    
##### Method `net_exists` {#kvirt.kubevirt.Kubevirt.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `network_ports` {#kvirt.kubevirt.Kubevirt.network_ports}



    
> `def network_ports(self, name)`


:param name:
:return:


    
##### Method `pod_completed` {#kvirt.kubevirt.Kubevirt.pod_completed}



    
> `def pod_completed(self, podname, namespace)`


:param podname:
:param namespace:
:return:


    
##### Method `prepare_pvc` {#kvirt.kubevirt.Kubevirt.prepare_pvc}



    
> `def prepare_pvc(self, name, size=1)`


:param name:
:param size:
:return:


    
##### Method `pvc_bound` {#kvirt.kubevirt.Kubevirt.pvc_bound}



    
> `def pvc_bound(self, volname, namespace)`


:param volname:
:param namespace:
:return:


    
##### Method `report` {#kvirt.kubevirt.Kubevirt.report}



    
> `def report(self)`


:return:


    
##### Method `restart` {#kvirt.kubevirt.Kubevirt.restart}



    
> `def restart(self, name)`


:param name:
:return:


    
##### Method `scp` {#kvirt.kubevirt.Kubevirt.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `serialconsole` {#kvirt.kubevirt.Kubevirt.serialconsole}



    
> `def serialconsole(self, name)`


:param name:
:return:


    
##### Method `snapshot` {#kvirt.kubevirt.Kubevirt.snapshot}



    
> `def snapshot(self, name, base, revert=False, delete=False, listing=False)`


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:


    
##### Method `ssh` {#kvirt.kubevirt.Kubevirt.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.kubevirt.Kubevirt.start}



    
> `def start(self, name)`


:param name:
:return:


    
##### Method `status` {#kvirt.kubevirt.Kubevirt.status}



    
> `def status(self, name)`


:param name:
:return:


    
##### Method `stop` {#kvirt.kubevirt.Kubevirt.stop}



    
> `def stop(self, name)`


:param name:
:return:


    
##### Method `update_cpus` {#kvirt.kubevirt.Kubevirt.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_flavor` {#kvirt.kubevirt.Kubevirt.update_flavor}



    
> `def update_flavor(self, name, flavor)`


:param name:
:param flavor:
:return:


    
##### Method `update_information` {#kvirt.kubevirt.Kubevirt.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.kubevirt.Kubevirt.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.kubevirt.Kubevirt.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.kubevirt.Kubevirt.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`


:param name:
:param metatype:
:param metavalue:
:return:


    
##### Method `update_start` {#kvirt.kubevirt.Kubevirt.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.kubevirt.Kubevirt.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
:return:


    
##### Method `volumes` {#kvirt.kubevirt.Kubevirt.volumes}



    
> `def volumes(self, iso=False)`


:param iso:
:return:




    
# Module `kvirt.kvm` {#kvirt.kvm}

Kvm Provider class





    
## Functions


    
### Function `libvirt_callback` {#kvirt.kvm.libvirt_callback}



    
> `def libvirt_callback(ignore, err)`


:param ignore:
:param err:
:return:



    
## Classes


    
### Class `Kvirt` {#kvirt.kvm.Kvirt}



> `class Kvirt(host='127.0.0.1', port=None, user='root', protocol='ssh', url=None, debug=False, insecure=False, session=False)`











    
#### Methods


    
##### Method `add_disk` {#kvirt.kvm.Kvirt.add_disk}



    
> `def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:


    
##### Method `add_image` {#kvirt.kvm.Kvirt.add_image}



    
> `def add_image(self, image, pool, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_image_to_deadpool` {#kvirt.kvm.Kvirt.add_image_to_deadpool}



    
> `def add_image_to_deadpool(self, poolname, pooltype, poolpath, shortimage, thinpool=None)`


:param poolname:
:param pooltype:
:param poolpath:
:param shortimage:
:param thinpool:
:return:


    
##### Method `add_nic` {#kvirt.kvm.Kvirt.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `clone` {#kvirt.kvm.Kvirt.clone}



    
> `def clone(self, old, new, full=False, start=False)`


:param old:
:param new:
:param full:
:param start:


    
##### Method `close` {#kvirt.kvm.Kvirt.close}



    
> `def close(self)`





    
##### Method `console` {#kvirt.kvm.Kvirt.console}



    
> `def console(self, name, tunnel=False, web=False)`


:param name:
:param tunnel:
:return:


    
##### Method `create` {#kvirt.kvm.Kvirt.create}



    
> `def create(self, name, virttype=None, profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, overrides={}, tags=[], dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param flavor:
:param plan:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param cpuhotplug:
:param numcpus:
:param memory:
:param memoryhotplug:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_disk` {#kvirt.kvm.Kvirt.create_disk}



    
> `def create_disk(self, name, size, pool=None, thin=True, image=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:


    
##### Method `create_network` {#kvirt.kvm.Kvirt.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param overrides:
:return:


    
##### Method `create_pool` {#kvirt.kvm.Kvirt.create_pool}



    
> `def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None)`


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:


    
##### Method `delete` {#kvirt.kvm.Kvirt.delete}



    
> `def delete(self, name, snapshots=False)`


:param name:
:param snapshots:
:return:


    
##### Method `delete_disk` {#kvirt.kvm.Kvirt.delete_disk}



    
> `def delete_disk(self, name=None, diskname=None, pool=None)`


:param name:
:param diskname:
:param pool:
:return:


    
##### Method `delete_disk_by_name` {#kvirt.kvm.Kvirt.delete_disk_by_name}



    
> `def delete_disk_by_name(self, name, pool)`


:param name:
:param pool:
:return:


    
##### Method `delete_dns` {#kvirt.kvm.Kvirt.delete_dns}



    
> `def delete_dns(self, name, domain)`


:param name:
:param domain:
:return:


    
##### Method `delete_image` {#kvirt.kvm.Kvirt.delete_image}



    
> `def delete_image(self, image)`





    
##### Method `delete_network` {#kvirt.kvm.Kvirt.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:param cidr:
:return:


    
##### Method `delete_nic` {#kvirt.kvm.Kvirt.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface:
:return:


    
##### Method `delete_pool` {#kvirt.kvm.Kvirt.delete_pool}



    
> `def delete_pool(self, name, full=False)`


:param name:
:param full:
:return:


    
##### Method `disk_exists` {#kvirt.kvm.Kvirt.disk_exists}



    
> `def disk_exists(self, pool, name)`


:param pool:
:param name:
:return:


    
##### Method `dnsinfo` {#kvirt.kvm.Kvirt.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:param snapshots:
:return:


    
##### Method `exists` {#kvirt.kvm.Kvirt.exists}



    
> `def exists(self, name)`


:param name:
:return:


    
##### Method `export` {#kvirt.kvm.Kvirt.export}



    
> `def export(self, name, image=None)`


:param name:
:param image:
:return:


    
##### Method `flavors` {#kvirt.kvm.Kvirt.flavors}



    
> `def flavors(self)`


:return:


    
##### Method `get_pool_path` {#kvirt.kvm.Kvirt.get_pool_path}



    
> `def get_pool_path(self, pool)`


:param pool:
:return:


    
##### Method `handler` {#kvirt.kvm.Kvirt.handler}



    
> `def handler(self, stream, data, file_)`


:param stream:
:param data:
:param file_:
:return:


    
##### Method `info` {#kvirt.kvm.Kvirt.info}



    
> `def info(self, name, vm=None, debug=False)`


:param name:
:param name:
:return:


    
##### Method `ip` {#kvirt.kvm.Kvirt.ip}



    
> `def ip(self, name)`


:param name:
:return:


    
##### Method `list` {#kvirt.kvm.Kvirt.list}



    
> `def list(self)`


:return:


    
##### Method `list_disks` {#kvirt.kvm.Kvirt.list_disks}



    
> `def list_disks(self)`


:return:


    
##### Method `list_dns` {#kvirt.kvm.Kvirt.list_dns}



    
> `def list_dns(self, domain)`


:param domain:
:return:


    
##### Method `list_networks` {#kvirt.kvm.Kvirt.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.kvm.Kvirt.list_pools}



    
> `def list_pools(self)`


:return:


    
##### Method `list_subnets` {#kvirt.kvm.Kvirt.list_subnets}



    
> `def list_subnets(self)`


:return:


    
##### Method `net_exists` {#kvirt.kvm.Kvirt.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `network_ports` {#kvirt.kvm.Kvirt.network_ports}



    
> `def network_ports(self, name)`


:param name:
:return:


    
##### Method `no_memory` {#kvirt.kvm.Kvirt.no_memory}



    
> `def no_memory(self, memory)`





    
##### Method `remove_cloudinit` {#kvirt.kvm.Kvirt.remove_cloudinit}



    
> `def remove_cloudinit(self, name)`


:param name:
:return:


    
##### Method `report` {#kvirt.kvm.Kvirt.report}



    
> `def report(self)`





    
##### Method `reserve_dns` {#kvirt.kvm.Kvirt.reserve_dns}



    
> `def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False)`


:param name:
:param nets:
:param domain:
:param ip:
:param alias:
:param force:
:return:


    
##### Method `reserve_host` {#kvirt.kvm.Kvirt.reserve_host}



    
> `def reserve_host(self, name, nets, domain)`


:param name:
:param nets:
:param domain:
:return:


    
##### Method `restart` {#kvirt.kvm.Kvirt.restart}



    
> `def restart(self, name)`


:param name:
:return:


    
##### Method `scp` {#kvirt.kvm.Kvirt.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param insecure:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `serialconsole` {#kvirt.kvm.Kvirt.serialconsole}



    
> `def serialconsole(self, name)`


:param name:
:return:


    
##### Method `snapshot` {#kvirt.kvm.Kvirt.snapshot}



    
> `def snapshot(self, name, base, revert=False, delete=False, listing=False)`


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:


    
##### Method `ssh` {#kvirt.kvm.Kvirt.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.kvm.Kvirt.start}



    
> `def start(self, name)`


:param name:
:return:


    
##### Method `status` {#kvirt.kvm.Kvirt.status}



    
> `def status(self, name)`


:param name:
:return:


    
##### Method `stop` {#kvirt.kvm.Kvirt.stop}



    
> `def stop(self, name)`


:param name:
:return:


    
##### Method `thinimages` {#kvirt.kvm.Kvirt.thinimages}



    
> `def thinimages(self, path, thinpool)`


:param path:
:param thinpool:
:return:


    
##### Method `update_cpus` {#kvirt.kvm.Kvirt.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_flavor` {#kvirt.kvm.Kvirt.update_flavor}



    
> `def update_flavor(self, name, flavor)`


:param name:
:param flavor:
:return:


    
##### Method `update_information` {#kvirt.kvm.Kvirt.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.kvm.Kvirt.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.kvm.Kvirt.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.kvm.Kvirt.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`


:param name:
:param metatype:
:param metavalue:
:return:


    
##### Method `update_start` {#kvirt.kvm.Kvirt.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.kvm.Kvirt.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
:return:


    
##### Method `volumes` {#kvirt.kvm.Kvirt.volumes}



    
> `def volumes(self, iso=False)`


:param iso:
:return:




    
# Module `kvirt.nameutils` {#kvirt.nameutils}

provide random names





    
## Functions


    
### Function `get_random_name` {#kvirt.nameutils.get_random_name}



    
> `def get_random_name(sep='-')`


:param sep:
:return:


    
### Function `random_ip` {#kvirt.nameutils.random_ip}



    
> `def random_ip()`


:return:





    
# Module `kvirt.openshift` {#kvirt.openshift}







    
## Functions


    
### Function `create` {#kvirt.openshift.create}



    
> `def create(config, plandir, cluster, overrides)`





    
### Function `gather_dhcp` {#kvirt.openshift.gather_dhcp}



    
> `def gather_dhcp(data, platform)`





    
### Function `get_ci_installer` {#kvirt.openshift.get_ci_installer}



    
> `def get_ci_installer(pull_secret, tag=None, macosx=False, upstream=False)`





    
### Function `get_downstream_installer` {#kvirt.openshift.get_downstream_installer}



    
> `def get_downstream_installer(nightly=False, macosx=False, tag=None)`





    
### Function `get_rhcos_openstack_url` {#kvirt.openshift.get_rhcos_openstack_url}



    
> `def get_rhcos_openstack_url()`





    
### Function `get_upstream_installer` {#kvirt.openshift.get_upstream_installer}



    
> `def get_upstream_installer(macosx=False)`





    
### Function `scale` {#kvirt.openshift.scale}



    
> `def scale(config, plandir, cluster, overrides)`








    
# Module `kvirt.openstack` {#kvirt.openstack}

Openstack Provider Class






    
## Classes


    
### Class `Kopenstack` {#kvirt.openstack.Kopenstack}



> `class Kopenstack(host='127.0.0.1', version='2', port=None, user='root', password=None, debug=False, project=None, domain='Default', auth_url=None)`











    
#### Methods


    
##### Method `add_disk` {#kvirt.openstack.Kopenstack.add_disk}



    
> `def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:


    
##### Method `add_image` {#kvirt.openstack.Kopenstack.add_image}



    
> `def add_image(self, image, pool, short=None, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_nic` {#kvirt.openstack.Kopenstack.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `clone` {#kvirt.openstack.Kopenstack.clone}



    
> `def clone(self, old, new, full=False, start=False)`


:param old:
:param new:
:param full:
:param start:
:return:


    
##### Method `close` {#kvirt.openstack.Kopenstack.close}



    
> `def close(self)`


:return:


    
##### Method `console` {#kvirt.openstack.Kopenstack.console}



    
> `def console(self, name, tunnel=False, web=False)`


:param name:
:param tunnel:
:return:


    
##### Method `create` {#kvirt.openstack.Kopenstack.create}



    
> `def create(self, name, virttype=None, profile='', plan='kvirt', flavor=None, cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags={}, dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param plan:
:param flavor:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param numcpus:
:param memory:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param alias:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_disk` {#kvirt.openstack.Kopenstack.create_disk}



    
> `def create_disk(self, name, size, pool=None, thin=True, image=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:


    
##### Method `create_network` {#kvirt.openstack.Kopenstack.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param overrides:
:return:


    
##### Method `create_pool` {#kvirt.openstack.Kopenstack.create_pool}



    
> `def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None)`


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:


    
##### Method `delete` {#kvirt.openstack.Kopenstack.delete}



    
> `def delete(self, name, snapshots=False)`


:param name:
:param snapshots:
:return:


    
##### Method `delete_disk` {#kvirt.openstack.Kopenstack.delete_disk}



    
> `def delete_disk(self, name=None, diskname=None, pool=None)`


:param name:
:param diskname:
:param pool:
:return:


    
##### Method `delete_image` {#kvirt.openstack.Kopenstack.delete_image}



    
> `def delete_image(self, image)`





    
##### Method `delete_network` {#kvirt.openstack.Kopenstack.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:param cidr:
:return:


    
##### Method `delete_nic` {#kvirt.openstack.Kopenstack.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface:
:return:


    
##### Method `delete_pool` {#kvirt.openstack.Kopenstack.delete_pool}



    
> `def delete_pool(self, name, full=False)`


:param name:
:param full:
:return:


    
##### Method `disk_exists` {#kvirt.openstack.Kopenstack.disk_exists}



    
> `def disk_exists(self, pool, name)`


:param pool:
:param name:


    
##### Method `dnsinfo` {#kvirt.openstack.Kopenstack.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:return:


    
##### Method `exists` {#kvirt.openstack.Kopenstack.exists}



    
> `def exists(self, name)`


:param name:
:return:


    
##### Method `export` {#kvirt.openstack.Kopenstack.export}



    
> `def export(self, name, image=None)`


:param name:
:param image:
:return:


    
##### Method `flavors` {#kvirt.openstack.Kopenstack.flavors}



    
> `def flavors(self)`


:return:


    
##### Method `get_pool_path` {#kvirt.openstack.Kopenstack.get_pool_path}



    
> `def get_pool_path(self, pool)`


:param pool:
:return:


    
##### Method `info` {#kvirt.openstack.Kopenstack.info}



    
> `def info(self, name, vm=None, debug=False)`


:param name:
:param vm:
:return:


    
##### Method `ip` {#kvirt.openstack.Kopenstack.ip}



    
> `def ip(self, name)`


:param name:
:return:


    
##### Method `list` {#kvirt.openstack.Kopenstack.list}



    
> `def list(self)`


:return:


    
##### Method `list_disks` {#kvirt.openstack.Kopenstack.list_disks}



    
> `def list_disks(self)`


:return:


    
##### Method `list_dns` {#kvirt.openstack.Kopenstack.list_dns}



    
> `def list_dns(self, domain)`


:param domain:
:return:


    
##### Method `list_networks` {#kvirt.openstack.Kopenstack.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.openstack.Kopenstack.list_pools}



    
> `def list_pools(self)`


:return:


    
##### Method `list_subnets` {#kvirt.openstack.Kopenstack.list_subnets}



    
> `def list_subnets(self)`


:return:


    
##### Method `net_exists` {#kvirt.openstack.Kopenstack.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `network_ports` {#kvirt.openstack.Kopenstack.network_ports}



    
> `def network_ports(self, name)`


:param name:
:return:


    
##### Method `report` {#kvirt.openstack.Kopenstack.report}



    
> `def report(self)`


:return:


    
##### Method `restart` {#kvirt.openstack.Kopenstack.restart}



    
> `def restart(self, name)`


:param name:
:return:


    
##### Method `scp` {#kvirt.openstack.Kopenstack.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `serialconsole` {#kvirt.openstack.Kopenstack.serialconsole}



    
> `def serialconsole(self, name)`


:param name:
:return:


    
##### Method `snapshot` {#kvirt.openstack.Kopenstack.snapshot}



    
> `def snapshot(self, name, base, revert=False, delete=False, listing=False)`


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:


    
##### Method `ssh` {#kvirt.openstack.Kopenstack.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.openstack.Kopenstack.start}



    
> `def start(self, name)`


:param name:
:return:


    
##### Method `status` {#kvirt.openstack.Kopenstack.status}



    
> `def status(self, name)`


:param name:
:return:


    
##### Method `stop` {#kvirt.openstack.Kopenstack.stop}



    
> `def stop(self, name)`


:param name:
:return:


    
##### Method `update_cpus` {#kvirt.openstack.Kopenstack.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_flavor` {#kvirt.openstack.Kopenstack.update_flavor}



    
> `def update_flavor(self, name, flavor)`


:param name:
:param flavor:
:return:


    
##### Method `update_information` {#kvirt.openstack.Kopenstack.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.openstack.Kopenstack.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.openstack.Kopenstack.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.openstack.Kopenstack.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`


:param name:
:param metatype:
:param metavalue:
:return:


    
##### Method `update_start` {#kvirt.openstack.Kopenstack.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.openstack.Kopenstack.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
:return:


    
##### Method `volumes` {#kvirt.openstack.Kopenstack.volumes}



    
> `def volumes(self, iso=False)`


:param iso:
:return:




    
# Module `kvirt.ovirt` {#kvirt.ovirt}

Ovirt Provider Class



    
## Sub-modules

* [kvirt.ovirt.helpers](#kvirt.ovirt.helpers)




    
## Classes


    
### Class `KOvirt` {#kvirt.ovirt.KOvirt}



> `class KOvirt(host='127.0.0.1', port=22, user='admin@internal', password=None, insecure=True, ca_file=None, org=None, debug=False, cluster='Default', datacenter='Default', ssh_user='root', imagerepository='ovirt-image-repository', filtervms=False, filteruser=False, filtertag=None)`











    
#### Methods


    
##### Method `add_disk` {#kvirt.ovirt.KOvirt.add_disk}



    
> `def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:


    
##### Method `add_image` {#kvirt.ovirt.KOvirt.add_image}



    
> `def add_image(self, image, pool, short=None, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_nic` {#kvirt.ovirt.KOvirt.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `clone` {#kvirt.ovirt.KOvirt.clone}



    
> `def clone(self, old, new, full=False, start=False)`


:param old:
:param new:
:param full:
:param start:
:return:


    
##### Method `close` {#kvirt.ovirt.KOvirt.close}



    
> `def close(self)`


:return:


    
##### Method `console` {#kvirt.ovirt.KOvirt.console}



    
> `def console(self, name, tunnel=False, web=False)`


:param name:
:param tunnel:
:return:


    
##### Method `create` {#kvirt.ovirt.KOvirt.create}



    
> `def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags=[], dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param flavor:
:param plan:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param numcpus:
:param memory:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param alias:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_disk` {#kvirt.ovirt.KOvirt.create_disk}



    
> `def create_disk(self, name, size, pool=None, thin=True, image=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:


    
##### Method `create_network` {#kvirt.ovirt.KOvirt.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param overrides:
:return:


    
##### Method `create_pool` {#kvirt.ovirt.KOvirt.create_pool}



    
> `def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None)`


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:


    
##### Method `delete` {#kvirt.ovirt.KOvirt.delete}



    
> `def delete(self, name, snapshots=False)`


:param name:
:param snapshots:
:return:


    
##### Method `delete_disk` {#kvirt.ovirt.KOvirt.delete_disk}



    
> `def delete_disk(self, name=None, diskname=None, pool=None)`


:param name:
:param diskname:
:param pool:
:return:


    
##### Method `delete_image` {#kvirt.ovirt.KOvirt.delete_image}



    
> `def delete_image(self, image)`





    
##### Method `delete_network` {#kvirt.ovirt.KOvirt.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:param cidr:
:return:


    
##### Method `delete_nic` {#kvirt.ovirt.KOvirt.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface:
:return:


    
##### Method `delete_pool` {#kvirt.ovirt.KOvirt.delete_pool}



    
> `def delete_pool(self, name, full=False)`


:param name:
:param full:
:return:


    
##### Method `disk_exists` {#kvirt.ovirt.KOvirt.disk_exists}



    
> `def disk_exists(self, pool, name)`


:param pool:
:param name:


    
##### Method `dnsinfo` {#kvirt.ovirt.KOvirt.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:return:


    
##### Method `exists` {#kvirt.ovirt.KOvirt.exists}



    
> `def exists(self, name)`


:param name:
:return:


    
##### Method `export` {#kvirt.ovirt.KOvirt.export}



    
> `def export(self, name, image=None)`


:param name:
:param image:
:return:


    
##### Method `flavors` {#kvirt.ovirt.KOvirt.flavors}



    
> `def flavors(self)`


:return:


    
##### Method `get_hostname` {#kvirt.ovirt.KOvirt.get_hostname}



    
> `def get_hostname(self, address)`





    
##### Method `get_pool_path` {#kvirt.ovirt.KOvirt.get_pool_path}



    
> `def get_pool_path(self, pool)`


:param pool:
:return:


    
##### Method `info` {#kvirt.ovirt.KOvirt.info}



    
> `def info(self, name, vm=None, debug=False)`


:param name:
:param vm:
:return:


    
##### Method `ip` {#kvirt.ovirt.KOvirt.ip}



    
> `def ip(self, name)`


:param name:
:return:


    
##### Method `list` {#kvirt.ovirt.KOvirt.list}



    
> `def list(self)`


:return:


    
##### Method `list_disks` {#kvirt.ovirt.KOvirt.list_disks}



    
> `def list_disks(self)`


:return:


    
##### Method `list_dns` {#kvirt.ovirt.KOvirt.list_dns}



    
> `def list_dns(self, domain)`


:param domain:
:return:


    
##### Method `list_networks` {#kvirt.ovirt.KOvirt.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.ovirt.KOvirt.list_pools}



    
> `def list_pools(self)`


:return:


    
##### Method `list_subnets` {#kvirt.ovirt.KOvirt.list_subnets}



    
> `def list_subnets(self)`


:return:


    
##### Method `net_exists` {#kvirt.ovirt.KOvirt.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `network_ports` {#kvirt.ovirt.KOvirt.network_ports}



    
> `def network_ports(self, name)`


:param name:
:return:


    
##### Method `report` {#kvirt.ovirt.KOvirt.report}



    
> `def report(self)`





    
##### Method `restart` {#kvirt.ovirt.KOvirt.restart}



    
> `def restart(self, name)`


:param name:
:return:


    
##### Method `scp` {#kvirt.ovirt.KOvirt.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `serialconsole` {#kvirt.ovirt.KOvirt.serialconsole}



    
> `def serialconsole(self, name)`


:param name:
:return:


    
##### Method `snapshot` {#kvirt.ovirt.KOvirt.snapshot}



    
> `def snapshot(self, name, base, revert=False, delete=False, listing=False)`


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:


    
##### Method `ssh` {#kvirt.ovirt.KOvirt.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.ovirt.KOvirt.start}



    
> `def start(self, name)`


:param name:
:return:


    
##### Method `status` {#kvirt.ovirt.KOvirt.status}



    
> `def status(self, name)`


:param name:
:return:


    
##### Method `stop` {#kvirt.ovirt.KOvirt.stop}



    
> `def stop(self, name)`


:param name:
:return:


    
##### Method `update_cpus` {#kvirt.ovirt.KOvirt.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_flavor` {#kvirt.ovirt.KOvirt.update_flavor}



    
> `def update_flavor(self, name, flavor)`


:param name:
:param flavor:
:return:


    
##### Method `update_image_size` {#kvirt.ovirt.KOvirt.update_image_size}



    
> `def update_image_size(self, vmid, size)`





    
##### Method `update_information` {#kvirt.ovirt.KOvirt.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.ovirt.KOvirt.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.ovirt.KOvirt.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.ovirt.KOvirt.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`


:param name:
:param metatype:
:param metavalue:
:return:


    
##### Method `update_start` {#kvirt.ovirt.KOvirt.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.ovirt.KOvirt.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
:return:


    
##### Method `volumes` {#kvirt.ovirt.KOvirt.volumes}



    
> `def volumes(self, iso=False)`


:param iso:
:return:




    
# Module `kvirt.ovirt.helpers` {#kvirt.ovirt.helpers}







    
## Functions


    
### Function `get_home_ssh_key` {#kvirt.ovirt.helpers.get_home_ssh_key}



    
> `def get_home_ssh_key()`


:return:





    
# Module `kvirt.sampleprovider` {#kvirt.sampleprovider}

Base Kvirt serving as interface for the virtualisation providers






    
## Classes


    
### Class `Kbase` {#kvirt.sampleprovider.Kbase}



> `class Kbase(host='127.0.0.1', port=None, user='root', debug=False)`











    
#### Methods


    
##### Method `add_disk` {#kvirt.sampleprovider.Kbase.add_disk}



    
> `def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:


    
##### Method `add_image` {#kvirt.sampleprovider.Kbase.add_image}



    
> `def add_image(self, image, pool, short=None, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_nic` {#kvirt.sampleprovider.Kbase.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `clone` {#kvirt.sampleprovider.Kbase.clone}



    
> `def clone(self, old, new, full=False, start=False)`


:param old:
:param new:
:param full:
:param start:
:return:


    
##### Method `close` {#kvirt.sampleprovider.Kbase.close}



    
> `def close(self)`


:return:


    
##### Method `console` {#kvirt.sampleprovider.Kbase.console}



    
> `def console(self, name, tunnel=False, web=False)`


:param name:
:param tunnel:
:return:


    
##### Method `create` {#kvirt.sampleprovider.Kbase.create}



    
> `def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags=[], dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param flavor:
:param plan:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param numcpus:
:param memory:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param alias:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_disk` {#kvirt.sampleprovider.Kbase.create_disk}



    
> `def create_disk(self, name, size, pool=None, thin=True, image=None)`


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:


    
##### Method `create_network` {#kvirt.sampleprovider.Kbase.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param pxe:
:param vlan:
:return:


    
##### Method `create_pool` {#kvirt.sampleprovider.Kbase.create_pool}



    
> `def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None)`


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:


    
##### Method `delete` {#kvirt.sampleprovider.Kbase.delete}



    
> `def delete(self, name, snapshots=False)`


:param name:
:param snapshots:
:return:


    
##### Method `delete_disk` {#kvirt.sampleprovider.Kbase.delete_disk}



    
> `def delete_disk(self, name, diskname, pool=None)`


:param name:
:param diskname:
:param pool:
:return:


    
##### Method `delete_image` {#kvirt.sampleprovider.Kbase.delete_image}



    
> `def delete_image(self, image)`


:param image:
:return:


    
##### Method `delete_network` {#kvirt.sampleprovider.Kbase.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:param cidr:
:return:


    
##### Method `delete_nic` {#kvirt.sampleprovider.Kbase.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface:
:return:


    
##### Method `delete_pool` {#kvirt.sampleprovider.Kbase.delete_pool}



    
> `def delete_pool(self, name, full=False)`


:param name:
:param full:
:return:


    
##### Method `disk_exists` {#kvirt.sampleprovider.Kbase.disk_exists}



    
> `def disk_exists(self, pool, name)`


:param pool:
:param name:


    
##### Method `dnsinfo` {#kvirt.sampleprovider.Kbase.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:return:


    
##### Method `exists` {#kvirt.sampleprovider.Kbase.exists}



    
> `def exists(self, name)`


:param name:
:return:


    
##### Method `export` {#kvirt.sampleprovider.Kbase.export}



    
> `def export(name, image=None)`


:param image:
:return:


    
##### Method `flavors` {#kvirt.sampleprovider.Kbase.flavors}



    
> `def flavors(self)`


:return:


    
##### Method `get_pool_path` {#kvirt.sampleprovider.Kbase.get_pool_path}



    
> `def get_pool_path(self, pool)`


:param pool:
:return:


    
##### Method `info` {#kvirt.sampleprovider.Kbase.info}



    
> `def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False)`


:param name:
:param output:
:param fields:
:param values:
:return:


    
##### Method `ip` {#kvirt.sampleprovider.Kbase.ip}



    
> `def ip(self, name)`


:param name:
:return:


    
##### Method `list` {#kvirt.sampleprovider.Kbase.list}



    
> `def list(self)`


:return:


    
##### Method `list_disks` {#kvirt.sampleprovider.Kbase.list_disks}



    
> `def list_disks(self)`


:return:


    
##### Method `list_networks` {#kvirt.sampleprovider.Kbase.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.sampleprovider.Kbase.list_pools}



    
> `def list_pools(self)`


:return:


    
##### Method `list_subnets` {#kvirt.sampleprovider.Kbase.list_subnets}



    
> `def list_subnets(self)`


:return:


    
##### Method `net_exists` {#kvirt.sampleprovider.Kbase.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `network_ports` {#kvirt.sampleprovider.Kbase.network_ports}



    
> `def network_ports(self, name)`


:param name:
:return:


    
##### Method `report` {#kvirt.sampleprovider.Kbase.report}



    
> `def report(self)`


:return:


    
##### Method `restart` {#kvirt.sampleprovider.Kbase.restart}



    
> `def restart(self, name)`


:param name:
:return:


    
##### Method `scp` {#kvirt.sampleprovider.Kbase.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `serialconsole` {#kvirt.sampleprovider.Kbase.serialconsole}



    
> `def serialconsole(self, name)`


:param name:
:return:


    
##### Method `snapshot` {#kvirt.sampleprovider.Kbase.snapshot}



    
> `def snapshot(self, name, base, revert=False, delete=False, listing=False)`


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:


    
##### Method `ssh` {#kvirt.sampleprovider.Kbase.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.sampleprovider.Kbase.start}



    
> `def start(self, name)`


:param name:
:return:


    
##### Method `status` {#kvirt.sampleprovider.Kbase.status}



    
> `def status(self, name)`


:param name:
:return:


    
##### Method `stop` {#kvirt.sampleprovider.Kbase.stop}



    
> `def stop(self, name)`


:param name:
:return:


    
##### Method `update_cpus` {#kvirt.sampleprovider.Kbase.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_flavor` {#kvirt.sampleprovider.Kbase.update_flavor}



    
> `def update_flavor(self, name, flavor)`


:param name:
:param flavor:
:return:


    
##### Method `update_information` {#kvirt.sampleprovider.Kbase.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.sampleprovider.Kbase.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.sampleprovider.Kbase.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.sampleprovider.Kbase.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`


:param name:
:param metatype:
:param metavalue:
:return:


    
##### Method `update_start` {#kvirt.sampleprovider.Kbase.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.sampleprovider.Kbase.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
:return:


    
##### Method `volumes` {#kvirt.sampleprovider.Kbase.volumes}



    
> `def volumes(self, iso=False)`


:param iso:
:return:




    
# Module `kvirt.version` {#kvirt.version}










    
# Module `kvirt.vsphere` {#kvirt.vsphere}





    
## Sub-modules

* [kvirt.vsphere.helpers](#kvirt.vsphere.helpers)



    
## Functions


    
### Function `changecd` {#kvirt.vsphere.changecd}



    
> `def changecd(si, vm, iso)`





    
### Function `collectproperties` {#kvirt.vsphere.collectproperties}



    
> `def collectproperties(si, view, objtype, pathset=None, includemors=False)`





    
### Function `convert` {#kvirt.vsphere.convert}



    
> `def convert(octets, GB=True)`





    
### Function `create_filter_spec` {#kvirt.vsphere.create_filter_spec}



    
> `def create_filter_spec(pc, vms)`





    
### Function `createcdspec` {#kvirt.vsphere.createcdspec}



    
> `def createcdspec()`





    
### Function `createclonespec` {#kvirt.vsphere.createclonespec}



    
> `def createclonespec(pool)`





    
### Function `creatediskspec` {#kvirt.vsphere.creatediskspec}



    
> `def creatediskspec(number, disksize, ds, diskmode, thin=False)`





    
### Function `createfolder` {#kvirt.vsphere.createfolder}



    
> `def createfolder(si, parentfolder, folder)`





    
### Function `createisospec` {#kvirt.vsphere.createisospec}



    
> `def createisospec(iso=None)`





    
### Function `createnicspec` {#kvirt.vsphere.createnicspec}



    
> `def createnicspec(nicname, netname)`





    
### Function `createscsispec` {#kvirt.vsphere.createscsispec}



    
> `def createscsispec()`





    
### Function `deletedirectory` {#kvirt.vsphere.deletedirectory}



    
> `def deletedirectory(si, dc, path)`





    
### Function `deletefolder` {#kvirt.vsphere.deletefolder}



    
> `def deletefolder(si, parentfolder, folder)`





    
### Function `dssize` {#kvirt.vsphere.dssize}



    
> `def dssize(ds)`





    
### Function `filter_results` {#kvirt.vsphere.filter_results}



    
> `def filter_results(results)`





    
### Function `find` {#kvirt.vsphere.find}



    
> `def find(si, folder, vimtype, name)`





    
### Function `findvm` {#kvirt.vsphere.findvm}



    
> `def findvm(si, folder, name)`





    
### Function `makecuspec` {#kvirt.vsphere.makecuspec}



    
> `def makecuspec(name, nets=[], gateway=None, dns=None, domain=None)`





    
### Function `waitForMe` {#kvirt.vsphere.waitForMe}



    
> `def waitForMe(t)`






    
## Classes


    
### Class `Ksphere` {#kvirt.vsphere.Ksphere}



> `class Ksphere(host, user, password, datacenter, cluster, debug=False, filtervms=False, filteruser=False, filtertag=None)`











    
#### Methods


    
##### Method `add_disk` {#kvirt.vsphere.Ksphere.add_disk}



    
> `def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None)`





    
##### Method `add_image` {#kvirt.vsphere.Ksphere.add_image}



    
> `def add_image(self, image, pool, short=None, cmd=None, name=None, size=1)`


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:


    
##### Method `add_nic` {#kvirt.vsphere.Ksphere.add_nic}



    
> `def add_nic(self, name, network)`


:param name:
:param network:
:return:


    
##### Method `beststorage` {#kvirt.vsphere.Ksphere.beststorage}



    
> `def beststorage(self)`





    
##### Method `close` {#kvirt.vsphere.Ksphere.close}



    
> `def close(self)`





    
##### Method `console` {#kvirt.vsphere.Ksphere.console}



    
> `def console(self, name, tunnel=False, web=False)`





    
##### Method `create` {#kvirt.vsphere.Ksphere.create}



    
> `def create(self, name, virttype=None, profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model', cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='centos7_64Guest', pool='default', image=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, overrides={}, tags=[], dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[])`


:param name:
:param virttype:
:param profile:
:param flavor:
:param plan:
:param cpumodel:
:param cpuflags:
:param cpupinning:
:param cpuhotplug:
:param numcpus:
:param memory:
:param memoryhotplug:
:param guestid:
:param pool:
:param image:
:param disks:
:param disksize:
:param diskthin:
:param diskinterface:
:param nets:
:param iso:
:param vnc:
:param cloudinit:
:param reserveip:
:param reservedns:
:param reservehost:
:param start:
:param keys:
:param cmds:
:param ips:
:param netmasks:
:param gateway:
:param nested:
:param dns:
:param domain:
:param tunnel:
:param files:
:param enableroot:
:param overrides:
:param tags:
:param cpuhotplug:
:param memoryhotplug:
:param numamode:
:param numa:
:param pcidevices:
:return:


    
##### Method `create_network` {#kvirt.vsphere.Ksphere.create_network}



    
> `def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={})`


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param pxe:
:param vlan:
:return:


    
##### Method `delete` {#kvirt.vsphere.Ksphere.delete}



    
> `def delete(self, name, snapshots=False)`





    
##### Method `delete_disk` {#kvirt.vsphere.Ksphere.delete_disk}



    
> `def delete_disk(self, name=None, diskname=None, pool=None)`





    
##### Method `delete_image` {#kvirt.vsphere.Ksphere.delete_image}



    
> `def delete_image(self, image)`





    
##### Method `delete_network` {#kvirt.vsphere.Ksphere.delete_network}



    
> `def delete_network(self, name=None, cidr=None)`


:param name:
:return:


    
##### Method `delete_nic` {#kvirt.vsphere.Ksphere.delete_nic}



    
> `def delete_nic(self, name, interface)`


:param name:
:param interface
:return:


    
##### Method `dnsinfo` {#kvirt.vsphere.Ksphere.dnsinfo}



    
> `def dnsinfo(self, name)`


:param name:
:return:


    
##### Method `exists` {#kvirt.vsphere.Ksphere.exists}



    
> `def exists(self, name)`





    
##### Method `export` {#kvirt.vsphere.Ksphere.export}



    
> `def export(self, name, image=None)`


:param name:
:param image:
:return:


    
##### Method `get_pool_path` {#kvirt.vsphere.Ksphere.get_pool_path}



    
> `def get_pool_path(self, pool)`





    
##### Method `info` {#kvirt.vsphere.Ksphere.info}



    
> `def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False)`





    
##### Method `list` {#kvirt.vsphere.Ksphere.list}



    
> `def list(self)`





    
##### Method `list_dns` {#kvirt.vsphere.Ksphere.list_dns}



    
> `def list_dns(self, domain)`


:param domain:
:return:


    
##### Method `list_networks` {#kvirt.vsphere.Ksphere.list_networks}



    
> `def list_networks(self)`


:return:


    
##### Method `list_pools` {#kvirt.vsphere.Ksphere.list_pools}



    
> `def list_pools(self)`





    
##### Method `net_exists` {#kvirt.vsphere.Ksphere.net_exists}



    
> `def net_exists(self, name)`


:param name:
:return:


    
##### Method `report` {#kvirt.vsphere.Ksphere.report}



    
> `def report(self)`





    
##### Method `scp` {#kvirt.vsphere.Ksphere.scp}



    
> `def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False, insecure=False)`


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:


    
##### Method `ssh` {#kvirt.vsphere.Ksphere.ssh}



    
> `def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False, D=None)`


:param name:
:param user:
:param local:
:param remote:
:param tunnel:
:param insecure:
:param cmd:
:param X:
:param Y:
:param D:
:return:


    
##### Method `start` {#kvirt.vsphere.Ksphere.start}



    
> `def start(self, name)`





    
##### Method `status` {#kvirt.vsphere.Ksphere.status}



    
> `def status(self, name)`





    
##### Method `stop` {#kvirt.vsphere.Ksphere.stop}



    
> `def stop(self, name)`





    
##### Method `update_cpus` {#kvirt.vsphere.Ksphere.update_cpus}



    
> `def update_cpus(self, name, numcpus)`


:param name:
:param numcpus:
:return:


    
##### Method `update_information` {#kvirt.vsphere.Ksphere.update_information}



    
> `def update_information(self, name, information)`


:param name:
:param information:
:return:


    
##### Method `update_iso` {#kvirt.vsphere.Ksphere.update_iso}



    
> `def update_iso(self, name, iso)`


:param name:
:param iso:
:return:


    
##### Method `update_memory` {#kvirt.vsphere.Ksphere.update_memory}



    
> `def update_memory(self, name, memory)`


:param name:
:param memory:
:return:


    
##### Method `update_metadata` {#kvirt.vsphere.Ksphere.update_metadata}



    
> `def update_metadata(self, name, metatype, metavalue, append=False)`





    
##### Method `update_start` {#kvirt.vsphere.Ksphere.update_start}



    
> `def update_start(self, name, start=True)`


:param name:
:param start:
:return:


    
##### Method `vm_ports` {#kvirt.vsphere.Ksphere.vm_ports}



    
> `def vm_ports(self, name)`


:param name:
return:


    
##### Method `volumes` {#kvirt.vsphere.Ksphere.volumes}



    
> `def volumes(self, iso=False)`







    
# Module `kvirt.vsphere.helpers` {#kvirt.vsphere.helpers}










    
# Module `kvirt.web` {#kvirt.web}







    
## Functions


    
### Function `containeraction` {#kvirt.web.containeraction}



    
> `def containeraction()`


start/stop/delete container


    
### Function `containercreate` {#kvirt.web.containercreate}



    
> `def containercreate()`


create container


    
### Function `containerprofiles` {#kvirt.web.containerprofiles}



    
> `def containerprofiles()`


retrieves all containerprofiles


    
### Function `containerprofilestable` {#kvirt.web.containerprofilestable}



    
> `def containerprofilestable()`


retrieves container profiles in table


    
### Function `containers` {#kvirt.web.containers}



    
> `def containers()`


retrieves all containers


    
### Function `containerstable` {#kvirt.web.containerstable}



    
> `def containerstable()`


retrieves all containers in table


    
### Function `diskaction` {#kvirt.web.diskaction}



    
> `def diskaction()`


add/delete disk to vm


    
### Function `hostaction` {#kvirt.web.hostaction}



    
> `def hostaction()`


enable/disable/default host


    
### Function `hosts` {#kvirt.web.hosts}



    
> `def hosts()`


retrieves all hosts


    
### Function `hoststable` {#kvirt.web.hoststable}



    
> `def hoststable()`


retrieves all clients in table


    
### Function `imageaction` {#kvirt.web.imageaction}



    
> `def imageaction()`


create/delete image


    
### Function `imagecreate` {#kvirt.web.imagecreate}



    
> `def imagecreate()`


create image


    
### Function `images` {#kvirt.web.images}



    
> `def images()`


:return:


    
### Function `imagestable` {#kvirt.web.imagestable}



    
> `def imagestable()`


retrieves images in table


    
### Function `isos` {#kvirt.web.isos}



    
> `def isos()`


:return:


    
### Function `isostable` {#kvirt.web.isostable}



    
> `def isostable()`


retrieves isos in table


    
### Function `networkaction` {#kvirt.web.networkaction}



    
> `def networkaction()`


create/delete network


    
### Function `networkcreate` {#kvirt.web.networkcreate}



    
> `def networkcreate()`


network form


    
### Function `networks` {#kvirt.web.networks}



    
> `def networks()`


retrieves all networks


    
### Function `networkstable` {#kvirt.web.networkstable}



    
> `def networkstable()`


retrieves all networks in table


    
### Function `nicaction` {#kvirt.web.nicaction}



    
> `def nicaction()`


add/delete nic to vm


    
### Function `planaction` {#kvirt.web.planaction}



    
> `def planaction()`


start/stop/delete plan


    
### Function `plancreate` {#kvirt.web.plancreate}



    
> `def plancreate()`


create plan


    
### Function `plans` {#kvirt.web.plans}



    
> `def plans()`


:return:


    
### Function `planstable` {#kvirt.web.planstable}



    
> `def planstable()`


retrieves all plans in table


    
### Function `poolaction` {#kvirt.web.poolaction}



    
> `def poolaction()`


create/delete pool


    
### Function `poolcreate` {#kvirt.web.poolcreate}



    
> `def poolcreate()`


pool form


    
### Function `pools` {#kvirt.web.pools}



    
> `def pools()`


retrieves all pools


    
### Function `poolstable` {#kvirt.web.poolstable}



    
> `def poolstable()`


retrieves all pools in table


    
### Function `productaction` {#kvirt.web.productaction}



    
> `def productaction()`


create product


    
### Function `productcreate` {#kvirt.web.productcreate}



    
> `def productcreate(prod)`


product form


    
### Function `products` {#kvirt.web.products}



    
> `def products()`


:return:


    
### Function `productstable` {#kvirt.web.productstable}



    
> `def productstable()`


retrieves all products in table


    
### Function `repoaction` {#kvirt.web.repoaction}



    
> `def repoaction()`


create/delete repo


    
### Function `repocreate` {#kvirt.web.repocreate}



    
> `def repocreate()`


repo form


    
### Function `report` {#kvirt.web.report}



    
> `def report()`


updatestatus


    
### Function `repos` {#kvirt.web.repos}



    
> `def repos()`


:return:


    
### Function `repostable` {#kvirt.web.repostable}



    
> `def repostable()`


retrieves all repos in table


    
### Function `run` {#kvirt.web.run}



    
> `def run()`





    
### Function `snapshotaction` {#kvirt.web.snapshotaction}



    
> `def snapshotaction()`


create/delete/revert snapshot


    
### Function `vmaction` {#kvirt.web.vmaction}



    
> `def vmaction()`


start/stop/delete/create vm


    
### Function `vmconsole` {#kvirt.web.vmconsole}



    
> `def vmconsole(name)`


Get url for console


    
### Function `vmcreate` {#kvirt.web.vmcreate}



    
> `def vmcreate()`


create vm


    
### Function `vmprofiles` {#kvirt.web.vmprofiles}



    
> `def vmprofiles()`


:return:


    
### Function `vmprofilestable` {#kvirt.web.vmprofilestable}



    
> `def vmprofilestable()`


retrieves vm profiles in table


    
### Function `vms` {#kvirt.web.vms}



    
> `def vms()`


:return:


    
### Function `vmstable` {#kvirt.web.vmstable}



    
> `def vmstable()`


retrieves all vms in table




-----
Generated by *pdoc* 0.7.5 (<https://pdoc3.github.io>).
