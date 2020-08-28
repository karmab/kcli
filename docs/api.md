---
description: |
    API documentation for modules: kvirt, kvirt.ansibleutils, kvirt.baseconfig, kvirt.cli, kvirt.common, kvirt.config, kvirt.container, kvirt.containerconfig, kvirt.defaults, kvirt.examples, kvirt.expose, kvirt.internalplans, kvirt.jinjafilters, kvirt.k3s, kvirt.kbmc, kvirt.klist, kvirt.krpc, kvirt.krpc.cli, kvirt.krpc.commoncli, kvirt.krpc.kcli_pb2, kvirt.krpc.kcli_pb2_grpc, kvirt.krpc.server, kvirt.kubeadm, kvirt.kubecommon, kvirt.kubernetes, kvirt.nameutils, kvirt.openshift, kvirt.openshift.calico, kvirt.providers, kvirt.providers.aws, kvirt.providers.gcp, kvirt.providers.kubevirt, kvirt.providers.kvm, kvirt.providers.openstack, kvirt.providers.ovirt, kvirt.providers.ovirt.helpers, kvirt.providers.packet, kvirt.providers.sampleprovider, kvirt.providers.vsphere, kvirt.providers.vsphere.helpers, kvirt.version, kvirt.web, kvirt.web.main.

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
* [kvirt.baseconfig](#kvirt.baseconfig)
* [kvirt.cli](#kvirt.cli)
* [kvirt.common](#kvirt.common)
* [kvirt.config](#kvirt.config)
* [kvirt.container](#kvirt.container)
* [kvirt.containerconfig](#kvirt.containerconfig)
* [kvirt.defaults](#kvirt.defaults)
* [kvirt.examples](#kvirt.examples)
* [kvirt.expose](#kvirt.expose)
* [kvirt.internalplans](#kvirt.internalplans)
* [kvirt.jinjafilters](#kvirt.jinjafilters)
* [kvirt.k3s](#kvirt.k3s)
* [kvirt.kbmc](#kvirt.kbmc)
* [kvirt.klist](#kvirt.klist)
* [kvirt.krpc](#kvirt.krpc)
* [kvirt.kubeadm](#kvirt.kubeadm)
* [kvirt.kubecommon](#kvirt.kubecommon)
* [kvirt.kubernetes](#kvirt.kubernetes)
* [kvirt.nameutils](#kvirt.nameutils)
* [kvirt.openshift](#kvirt.openshift)
* [kvirt.providers](#kvirt.providers)
* [kvirt.version](#kvirt.version)
* [kvirt.web](#kvirt.web)






    
# Module `kvirt.ansibleutils` {#kvirt.ansibleutils}

interact with a local/remote libvirt daemon




    
## Functions


    
### Function `make_plan_inventory` {#kvirt.ansibleutils.make_plan_inventory}




>     def make_plan_inventory(
>         vms_to_host,
>         plan,
>         vms,
>         groups={},
>         user=None,
>         yamlinventory=False,
>         insecure=True
>     )


:param vms_per_host:
:param plan:
:param vms:
:param groups:
:param user:
:param yamlinventory:

    
### Function `play` {#kvirt.ansibleutils.play}




>     def play(
>         k,
>         name,
>         playbook,
>         variables=[],
>         verbose=False,
>         user=None,
>         tunnel=False,
>         tunnelhost=None,
>         tunnelport=None,
>         tunneluser=None,
>         yamlinventory=False,
>         insecure=True
>     )


:param k:
:param name:
:param playbook:
:param variables:
:param verbose:
:param tunnelhost:
:param tunnelport:
:param tunneluser:

    
### Function `vm_inventory` {#kvirt.ansibleutils.vm_inventory}




>     def vm_inventory(
>         k,
>         name,
>         user=None,
>         yamlinventory=False,
>         insecure=True
>     )


:param self:
:param name:
:return:




    
# Module `kvirt.baseconfig` {#kvirt.baseconfig}

Kvirt config class





    
## Classes


    
### Class `Kbaseconfig` {#kvirt.baseconfig.Kbaseconfig}




>     class Kbaseconfig(
>         client=None,
>         containerclient=None,
>         debug=False,
>         quiet=False
>     )






    
#### Descendants

* [kvirt.config.Kconfig](#kvirt.config.Kconfig)





    
#### Methods


    
##### Method `create_app_generic` {#kvirt.baseconfig.Kbaseconfig.create_app_generic}




>     def create_app_generic(
>         self,
>         app,
>         overrides={}
>     )




    
##### Method `create_app_openshift` {#kvirt.baseconfig.Kbaseconfig.create_app_openshift}




>     def create_app_openshift(
>         self,
>         app,
>         overrides={}
>     )




    
##### Method `create_pipeline` {#kvirt.baseconfig.Kbaseconfig.create_pipeline}




>     def create_pipeline(
>         self,
>         inputfile,
>         overrides={},
>         kube=False
>     )




    
##### Method `create_profile` {#kvirt.baseconfig.Kbaseconfig.create_profile}




>     def create_profile(
>         self,
>         profile,
>         overrides={},
>         quiet=False
>     )




    
##### Method `create_repo` {#kvirt.baseconfig.Kbaseconfig.create_repo}




>     def create_repo(
>         self,
>         name,
>         url
>     )


:param name:
:param url:
:return:

    
##### Method `delete_app_generic` {#kvirt.baseconfig.Kbaseconfig.delete_app_generic}




>     def delete_app_generic(
>         self,
>         app,
>         overrides={}
>     )




    
##### Method `delete_app_openshift` {#kvirt.baseconfig.Kbaseconfig.delete_app_openshift}




>     def delete_app_openshift(
>         self,
>         app,
>         overrides={}
>     )




    
##### Method `delete_profile` {#kvirt.baseconfig.Kbaseconfig.delete_profile}




>     def delete_profile(
>         self,
>         profile,
>         quiet=False
>     )




    
##### Method `delete_repo` {#kvirt.baseconfig.Kbaseconfig.delete_repo}




>     def delete_repo(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `disable_host` {#kvirt.baseconfig.Kbaseconfig.disable_host}




>     def disable_host(
>         self,
>         client
>     )


:param client:
:return:

    
##### Method `enable_host` {#kvirt.baseconfig.Kbaseconfig.enable_host}




>     def enable_host(
>         self,
>         client
>     )


:param client:
:return:

    
##### Method `info_app_generic` {#kvirt.baseconfig.Kbaseconfig.info_app_generic}




>     def info_app_generic(
>         self,
>         app
>     )




    
##### Method `info_app_openshift` {#kvirt.baseconfig.Kbaseconfig.info_app_openshift}




>     def info_app_openshift(
>         self,
>         app
>     )




    
##### Method `info_kube_generic` {#kvirt.baseconfig.Kbaseconfig.info_kube_generic}




>     def info_kube_generic(
>         self,
>         quiet,
>         web=False
>     )




    
##### Method `info_kube_k3s` {#kvirt.baseconfig.Kbaseconfig.info_kube_k3s}




>     def info_kube_k3s(
>         self,
>         quiet,
>         web=False
>     )




    
##### Method `info_kube_openshift` {#kvirt.baseconfig.Kbaseconfig.info_kube_openshift}




>     def info_kube_openshift(
>         self,
>         quiet,
>         web=False
>     )




    
##### Method `info_plan` {#kvirt.baseconfig.Kbaseconfig.info_plan}




>     def info_plan(
>         self,
>         inputfile,
>         quiet=False,
>         web=False,
>         onfly=None,
>         doc=False
>     )


:param inputfile:
:param quiet:
:return:

    
##### Method `info_product` {#kvirt.baseconfig.Kbaseconfig.info_product}




>     def info_product(
>         self,
>         name,
>         repo=None,
>         group=None,
>         web=False
>     )


Info product

    
##### Method `list_apps_generic` {#kvirt.baseconfig.Kbaseconfig.list_apps_generic}




>     def list_apps_generic(
>         self,
>         quiet=True
>     )




    
##### Method `list_apps_openshift` {#kvirt.baseconfig.Kbaseconfig.list_apps_openshift}




>     def list_apps_openshift(
>         self,
>         quiet=True
>     )




    
##### Method `list_containerprofiles` {#kvirt.baseconfig.Kbaseconfig.list_containerprofiles}




>     def list_containerprofiles(
>         self
>     )


:return:

    
##### Method `list_flavors` {#kvirt.baseconfig.Kbaseconfig.list_flavors}




>     def list_flavors(
>         self
>     )


:return:

    
##### Method `list_keywords` {#kvirt.baseconfig.Kbaseconfig.list_keywords}




>     def list_keywords(
>         self
>     )




    
##### Method `list_products` {#kvirt.baseconfig.Kbaseconfig.list_products}




>     def list_products(
>         self,
>         group=None,
>         repo=None
>     )


:param group:
:param repo:
:return:

    
##### Method `list_profiles` {#kvirt.baseconfig.Kbaseconfig.list_profiles}




>     def list_profiles(
>         self
>     )


:return:

    
##### Method `list_repos` {#kvirt.baseconfig.Kbaseconfig.list_repos}




>     def list_repos(
>         self
>     )


:return:

    
##### Method `process_inputfile` {#kvirt.baseconfig.Kbaseconfig.process_inputfile}




>     def process_inputfile(
>         self,
>         plan,
>         inputfile,
>         overrides={},
>         onfly=None,
>         full=False,
>         ignore=False,
>         download_mode=False
>     )




    
##### Method `set_defaults` {#kvirt.baseconfig.Kbaseconfig.set_defaults}




>     def set_defaults(
>         self
>     )




    
##### Method `switch_host` {#kvirt.baseconfig.Kbaseconfig.switch_host}




>     def switch_host(
>         self,
>         client
>     )


:param client:
:return:

    
##### Method `update_profile` {#kvirt.baseconfig.Kbaseconfig.update_profile}




>     def update_profile(
>         self,
>         profile,
>         overrides={},
>         quiet=False
>     )




    
##### Method `update_repo` {#kvirt.baseconfig.Kbaseconfig.update_repo}




>     def update_repo(
>         self,
>         name,
>         url=None
>     )


:param name:
:param url:
:return:



    
# Module `kvirt.cli` {#kvirt.cli}






    
## Functions


    
### Function `alias` {#kvirt.cli.alias}




>     def alias(
>         text
>     )




    
### Function `autostart_plan` {#kvirt.cli.autostart_plan}




>     def autostart_plan(
>         args
>     )


Autostart plan

    
### Function `cache_vms` {#kvirt.cli.cache_vms}




>     def cache_vms(
>         baseconfig,
>         region,
>         zone,
>         namespace
>     )




    
### Function `choose_parameter_file` {#kvirt.cli.choose_parameter_file}




>     def choose_parameter_file(
>         paramfile
>     )




    
### Function `cli` {#kvirt.cli.cli}




>     def cli()




    
### Function `clone_vm` {#kvirt.cli.clone_vm}




>     def clone_vm(
>         args
>     )


Clone existing vm

    
### Function `console_container` {#kvirt.cli.console_container}




>     def console_container(
>         args
>     )


Container console

    
### Function `console_vm` {#kvirt.cli.console_vm}




>     def console_vm(
>         args
>     )


Vnc/Spice/Serial Vm console

    
### Function `create_app_generic` {#kvirt.cli.create_app_generic}




>     def create_app_generic(
>         args
>     )




    
### Function `create_app_openshift` {#kvirt.cli.create_app_openshift}




>     def create_app_openshift(
>         args
>     )




    
### Function `create_container` {#kvirt.cli.create_container}




>     def create_container(
>         args
>     )


Create container

    
### Function `create_dns` {#kvirt.cli.create_dns}




>     def create_dns(
>         args
>     )


Create dns entries

    
### Function `create_generic_kube` {#kvirt.cli.create_generic_kube}




>     def create_generic_kube(
>         args
>     )


Create Generic kube

    
### Function `create_host_aws` {#kvirt.cli.create_host_aws}




>     def create_host_aws(
>         args
>     )


Create Aws Host

    
### Function `create_host_gcp` {#kvirt.cli.create_host_gcp}




>     def create_host_gcp(
>         args
>     )


Create Gcp Host

    
### Function `create_host_kubevirt` {#kvirt.cli.create_host_kubevirt}




>     def create_host_kubevirt(
>         args
>     )


Create Kubevirt Host

    
### Function `create_host_kvm` {#kvirt.cli.create_host_kvm}




>     def create_host_kvm(
>         args
>     )


Generate Kvm Host

    
### Function `create_host_openstack` {#kvirt.cli.create_host_openstack}




>     def create_host_openstack(
>         args
>     )


Create Openstack Host

    
### Function `create_host_ovirt` {#kvirt.cli.create_host_ovirt}




>     def create_host_ovirt(
>         args
>     )


Create Ovirt Host

    
### Function `create_host_vsphere` {#kvirt.cli.create_host_vsphere}




>     def create_host_vsphere(
>         args
>     )


Create Vsphere Host

    
### Function `create_k3s_kube` {#kvirt.cli.create_k3s_kube}




>     def create_k3s_kube(
>         args
>     )


Create K3s kube

    
### Function `create_lb` {#kvirt.cli.create_lb}




>     def create_lb(
>         args
>     )


Create loadbalancer

    
### Function `create_network` {#kvirt.cli.create_network}




>     def create_network(
>         args
>     )


Create Network

    
### Function `create_openshift_kube` {#kvirt.cli.create_openshift_kube}




>     def create_openshift_kube(
>         args
>     )


Create Generic kube

    
### Function `create_pipeline` {#kvirt.cli.create_pipeline}




>     def create_pipeline(
>         args
>     )


Create Pipeline

    
### Function `create_plan` {#kvirt.cli.create_plan}




>     def create_plan(
>         args
>     )


Create plan

    
### Function `create_pool` {#kvirt.cli.create_pool}




>     def create_pool(
>         args
>     )


Create/Delete pool

    
### Function `create_product` {#kvirt.cli.create_product}




>     def create_product(
>         args
>     )


Create product

    
### Function `create_profile` {#kvirt.cli.create_profile}




>     def create_profile(
>         args
>     )


Create profile

    
### Function `create_repo` {#kvirt.cli.create_repo}




>     def create_repo(
>         args
>     )


Create repo

    
### Function `create_vm` {#kvirt.cli.create_vm}




>     def create_vm(
>         args
>     )


Create vms

    
### Function `create_vmdisk` {#kvirt.cli.create_vmdisk}




>     def create_vmdisk(
>         args
>     )


Add disk to vm

    
### Function `create_vmnic` {#kvirt.cli.create_vmnic}




>     def create_vmnic(
>         args
>     )


Add nic to vm

    
### Function `delete_app_generic` {#kvirt.cli.delete_app_generic}




>     def delete_app_generic(
>         args
>     )




    
### Function `delete_app_openshift` {#kvirt.cli.delete_app_openshift}




>     def delete_app_openshift(
>         args
>     )




    
### Function `delete_cache` {#kvirt.cli.delete_cache}




>     def delete_cache(
>         args
>     )




    
### Function `delete_container` {#kvirt.cli.delete_container}




>     def delete_container(
>         args
>     )


Delete container

    
### Function `delete_dns` {#kvirt.cli.delete_dns}




>     def delete_dns(
>         args
>     )


Delete dns entries

    
### Function `delete_host` {#kvirt.cli.delete_host}




>     def delete_host(
>         args
>     )


Delete host

    
### Function `delete_image` {#kvirt.cli.delete_image}




>     def delete_image(
>         args
>     )




    
### Function `delete_kube` {#kvirt.cli.delete_kube}




>     def delete_kube(
>         args
>     )


Delete kube

    
### Function `delete_lb` {#kvirt.cli.delete_lb}




>     def delete_lb(
>         args
>     )


Delete loadbalancer

    
### Function `delete_network` {#kvirt.cli.delete_network}




>     def delete_network(
>         args
>     )


Delete Network

    
### Function `delete_plan` {#kvirt.cli.delete_plan}




>     def delete_plan(
>         args
>     )


Delete plan

    
### Function `delete_pool` {#kvirt.cli.delete_pool}




>     def delete_pool(
>         args
>     )


Delete pool

    
### Function `delete_profile` {#kvirt.cli.delete_profile}




>     def delete_profile(
>         args
>     )


Delete profile

    
### Function `delete_repo` {#kvirt.cli.delete_repo}




>     def delete_repo(
>         args
>     )


Delete repo

    
### Function `delete_vm` {#kvirt.cli.delete_vm}




>     def delete_vm(
>         args
>     )


Delete vm

    
### Function `delete_vmdisk` {#kvirt.cli.delete_vmdisk}




>     def delete_vmdisk(
>         args
>     )


Delete disk of vm

    
### Function `delete_vmnic` {#kvirt.cli.delete_vmnic}




>     def delete_vmnic(
>         args
>     )


Delete nic of vm

    
### Function `disable_host` {#kvirt.cli.disable_host}




>     def disable_host(
>         args
>     )


Disable host

    
### Function `download_image` {#kvirt.cli.download_image}




>     def download_image(
>         args
>     )


Download Image

    
### Function `download_kubectl` {#kvirt.cli.download_kubectl}




>     def download_kubectl(
>         args
>     )


Download Kubectl

    
### Function `download_oc` {#kvirt.cli.download_oc}




>     def download_oc(
>         args
>     )


Download Oc

    
### Function `download_okd_installer` {#kvirt.cli.download_okd_installer}




>     def download_okd_installer(
>         args
>     )


Download Okd Installer

    
### Function `download_openshift_installer` {#kvirt.cli.download_openshift_installer}




>     def download_openshift_installer(
>         args
>     )


Download Openshift Installer

    
### Function `download_plan` {#kvirt.cli.download_plan}




>     def download_plan(
>         args
>     )


Download plan

    
### Function `enable_host` {#kvirt.cli.enable_host}




>     def enable_host(
>         args
>     )


Enable host

    
### Function `export_vm` {#kvirt.cli.export_vm}




>     def export_vm(
>         args
>     )


Export a vm

    
### Function `expose_plan` {#kvirt.cli.expose_plan}




>     def expose_plan(
>         args
>     )




    
### Function `get_subparser` {#kvirt.cli.get_subparser}




>     def get_subparser(
>         parser,
>         subcommand
>     )




    
### Function `get_subparser_print_help` {#kvirt.cli.get_subparser_print_help}




>     def get_subparser_print_help(
>         parser,
>         subcommand
>     )




    
### Function `get_version` {#kvirt.cli.get_version}




>     def get_version(
>         args
>     )




    
### Function `info_generic_app` {#kvirt.cli.info_generic_app}




>     def info_generic_app(
>         args
>     )




    
### Function `info_generic_kube` {#kvirt.cli.info_generic_kube}




>     def info_generic_kube(
>         args
>     )


Info Generic kube

    
### Function `info_k3s_kube` {#kvirt.cli.info_k3s_kube}




>     def info_k3s_kube(
>         args
>     )


Info K3s kube

    
### Function `info_openshift_app` {#kvirt.cli.info_openshift_app}




>     def info_openshift_app(
>         args
>     )




    
### Function `info_openshift_kube` {#kvirt.cli.info_openshift_kube}




>     def info_openshift_kube(
>         args
>     )


Info Openshift kube

    
### Function `info_plan` {#kvirt.cli.info_plan}




>     def info_plan(
>         args
>     )


Info plan

    
### Function `info_product` {#kvirt.cli.info_product}




>     def info_product(
>         args
>     )


Info product

    
### Function `info_profile` {#kvirt.cli.info_profile}




>     def info_profile(
>         args
>     )


List profiles

    
### Function `info_vm` {#kvirt.cli.info_vm}




>     def info_vm(
>         args
>     )


Get info on vm

    
### Function `list_apps_generic` {#kvirt.cli.list_apps_generic}




>     def list_apps_generic(
>         args
>     )


List generic kube apps

    
### Function `list_apps_openshift` {#kvirt.cli.list_apps_openshift}




>     def list_apps_openshift(
>         args
>     )


List openshift kube apps

    
### Function `list_container` {#kvirt.cli.list_container}




>     def list_container(
>         args
>     )


List containers

    
### Function `list_containerimage` {#kvirt.cli.list_containerimage}




>     def list_containerimage(
>         args
>     )


List container images

    
### Function `list_dns` {#kvirt.cli.list_dns}




>     def list_dns(
>         args
>     )


List flavors

    
### Function `list_flavor` {#kvirt.cli.list_flavor}




>     def list_flavor(
>         args
>     )


List flavors

    
### Function `list_host` {#kvirt.cli.list_host}




>     def list_host(
>         args
>     )


List hosts

    
### Function `list_image` {#kvirt.cli.list_image}




>     def list_image(
>         args
>     )


List images

    
### Function `list_iso` {#kvirt.cli.list_iso}




>     def list_iso(
>         args
>     )


List isos

    
### Function `list_keyword` {#kvirt.cli.list_keyword}




>     def list_keyword(
>         args
>     )


List keywords

    
### Function `list_kube` {#kvirt.cli.list_kube}




>     def list_kube(
>         args
>     )


List kube

    
### Function `list_lb` {#kvirt.cli.list_lb}




>     def list_lb(
>         args
>     )


List lbs

    
### Function `list_network` {#kvirt.cli.list_network}




>     def list_network(
>         args
>     )


List networks

    
### Function `list_plan` {#kvirt.cli.list_plan}




>     def list_plan(
>         args
>     )


List plans

    
### Function `list_pool` {#kvirt.cli.list_pool}




>     def list_pool(
>         args
>     )


List pools

    
### Function `list_product` {#kvirt.cli.list_product}




>     def list_product(
>         args
>     )


List products

    
### Function `list_profile` {#kvirt.cli.list_profile}




>     def list_profile(
>         args
>     )


List profiles

    
### Function `list_repo` {#kvirt.cli.list_repo}




>     def list_repo(
>         args
>     )


List repos

    
### Function `list_vm` {#kvirt.cli.list_vm}




>     def list_vm(
>         args
>     )


List vms

    
### Function `list_vmdisk` {#kvirt.cli.list_vmdisk}




>     def list_vmdisk(
>         args
>     )


List vm disks

    
### Function `noautostart_plan` {#kvirt.cli.noautostart_plan}




>     def noautostart_plan(
>         args
>     )


Noautostart plan

    
### Function `profilelist_container` {#kvirt.cli.profilelist_container}




>     def profilelist_container(
>         args
>     )


List container profiles

    
### Function `render_file` {#kvirt.cli.render_file}




>     def render_file(
>         args
>     )


Render file

    
### Function `report_host` {#kvirt.cli.report_host}




>     def report_host(
>         args
>     )


Report info about host

    
### Function `restart_container` {#kvirt.cli.restart_container}




>     def restart_container(
>         args
>     )


Restart containers

    
### Function `restart_plan` {#kvirt.cli.restart_plan}




>     def restart_plan(
>         args
>     )


Restart plan

    
### Function `restart_vm` {#kvirt.cli.restart_vm}




>     def restart_vm(
>         args
>     )


Restart vms

    
### Function `revert_plan` {#kvirt.cli.revert_plan}




>     def revert_plan(
>         args
>     )


Revert snapshot of plan

    
### Function `scale_generic_kube` {#kvirt.cli.scale_generic_kube}




>     def scale_generic_kube(
>         args
>     )


Scale generic kube

    
### Function `scale_k3s_kube` {#kvirt.cli.scale_k3s_kube}




>     def scale_k3s_kube(
>         args
>     )


Scale k3s kube

    
### Function `scale_openshift_kube` {#kvirt.cli.scale_openshift_kube}




>     def scale_openshift_kube(
>         args
>     )


Scale openshift kube

    
### Function `scp_vm` {#kvirt.cli.scp_vm}




>     def scp_vm(
>         args
>     )


Scp into vm

    
### Function `snapshot_plan` {#kvirt.cli.snapshot_plan}




>     def snapshot_plan(
>         args
>     )


Snapshot plan

    
### Function `snapshotcreate_vm` {#kvirt.cli.snapshotcreate_vm}




>     def snapshotcreate_vm(
>         args
>     )


Create snapshot

    
### Function `snapshotdelete_vm` {#kvirt.cli.snapshotdelete_vm}




>     def snapshotdelete_vm(
>         args
>     )


Delete snapshot

    
### Function `snapshotlist_vm` {#kvirt.cli.snapshotlist_vm}




>     def snapshotlist_vm(
>         args
>     )


List snapshots of vm

    
### Function `snapshotrevert_vm` {#kvirt.cli.snapshotrevert_vm}




>     def snapshotrevert_vm(
>         args
>     )


Revert snapshot of vm

    
### Function `ssh_vm` {#kvirt.cli.ssh_vm}




>     def ssh_vm(
>         args
>     )


Ssh into vm

    
### Function `start_container` {#kvirt.cli.start_container}




>     def start_container(
>         args
>     )


Start containers

    
### Function `start_plan` {#kvirt.cli.start_plan}




>     def start_plan(
>         args
>     )


Start plan

    
### Function `start_vm` {#kvirt.cli.start_vm}




>     def start_vm(
>         args
>     )


Start vms

    
### Function `stop_container` {#kvirt.cli.stop_container}




>     def stop_container(
>         args
>     )


Stop containers

    
### Function `stop_plan` {#kvirt.cli.stop_plan}




>     def stop_plan(
>         args
>     )


Stop plan

    
### Function `stop_vm` {#kvirt.cli.stop_vm}




>     def stop_vm(
>         args
>     )


Stop vms

    
### Function `switch_host` {#kvirt.cli.switch_host}




>     def switch_host(
>         args
>     )


Handle host

    
### Function `sync_host` {#kvirt.cli.sync_host}




>     def sync_host(
>         args
>     )


Handle host

    
### Function `update_plan` {#kvirt.cli.update_plan}




>     def update_plan(
>         args
>     )


Update plan

    
### Function `update_profile` {#kvirt.cli.update_profile}




>     def update_profile(
>         args
>     )


Update profile

    
### Function `update_repo` {#kvirt.cli.update_repo}




>     def update_repo(
>         args
>     )


Update repo

    
### Function `update_vm` {#kvirt.cli.update_vm}




>     def update_vm(
>         args
>     )


Update ip, memory or numcpus

    
### Function `valid_cluster` {#kvirt.cli.valid_cluster}




>     def valid_cluster(
>         name
>     )




    
### Function `valid_fqdn` {#kvirt.cli.valid_fqdn}




>     def valid_fqdn(
>         name
>     )







    
# Module `kvirt.common` {#kvirt.common}






    
## Functions


    
### Function `cloudinit` {#kvirt.common.cloudinit}




>     def cloudinit(
>         name,
>         keys=[],
>         cmds=[],
>         nets=[],
>         gateway=None,
>         dns=None,
>         domain=None,
>         reserveip=False,
>         files=[],
>         enableroot=True,
>         overrides={},
>         iso=True,
>         fqdn=False,
>         storemetadata=True,
>         image=None,
>         ipv6=[]
>     )


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




>     def confirm(
>         message
>     )


:param message:
:return:

    
### Function `create_host` {#kvirt.common.create_host}




>     def create_host(
>         data
>     )


:param data:

    
### Function `delete_host` {#kvirt.common.delete_host}




>     def delete_host(
>         name
>     )


:param name:

    
### Function `fetch` {#kvirt.common.fetch}




>     def fetch(
>         url,
>         path
>     )




    
### Function `find_ignition_files` {#kvirt.common.find_ignition_files}




>     def find_ignition_files(
>         role,
>         cluster
>     )




    
### Function `gen_mac` {#kvirt.common.gen_mac}




>     def gen_mac()




    
### Function `get_binary` {#kvirt.common.get_binary}




>     def get_binary(
>         name,
>         linuxurl,
>         macosurl,
>         compressed=False
>     )




    
### Function `get_cloudinitfile` {#kvirt.common.get_cloudinitfile}




>     def get_cloudinitfile(
>         image
>     )


:param image:
:return:

    
### Function `get_commit_rhcos` {#kvirt.common.get_commit_rhcos}




>     def get_commit_rhcos(
>         commitid
>     )




    
### Function `get_commit_rhcos_metal` {#kvirt.common.get_commit_rhcos_metal}




>     def get_commit_rhcos_metal(
>         commitid
>     )




    
### Function `get_free_nodeport` {#kvirt.common.get_free_nodeport}




>     def get_free_nodeport()


:return:

    
### Function `get_free_port` {#kvirt.common.get_free_port}




>     def get_free_port()


:return:

    
### Function `get_kubectl` {#kvirt.common.get_kubectl}




>     def get_kubectl()




    
### Function `get_lastvm` {#kvirt.common.get_lastvm}




>     def get_lastvm(
>         client
>     )


:param client:
:return:

    
### Function `get_latest_fcos` {#kvirt.common.get_latest_fcos}




>     def get_latest_fcos(
>         url
>     )




    
### Function `get_latest_fcos_metal` {#kvirt.common.get_latest_fcos_metal}




>     def get_latest_fcos_metal(
>         url
>     )




    
### Function `get_latest_rhcos` {#kvirt.common.get_latest_rhcos}




>     def get_latest_rhcos(
>         url
>     )




    
### Function `get_latest_rhcos_metal` {#kvirt.common.get_latest_rhcos_metal}




>     def get_latest_rhcos_metal(
>         url
>     )




    
### Function `get_oc` {#kvirt.common.get_oc}




>     def get_oc(
>         macosx=False
>     )




    
### Function `get_overrides` {#kvirt.common.get_overrides}




>     def get_overrides(
>         paramfile=None,
>         param=[]
>     )


:param paramfile:
:param param:
:return:

    
### Function `get_parameters` {#kvirt.common.get_parameters}




>     def get_parameters(
>         inputfile,
>         raw=False
>     )


:param inputfile:
:param raw:
:return:

    
### Function `get_user` {#kvirt.common.get_user}




>     def get_user(
>         image
>     )


:param image:
:return:

    
### Function `get_values` {#kvirt.common.get_values}




>     def get_values(
>         data,
>         element,
>         field
>     )




    
### Function `handle_response` {#kvirt.common.handle_response}




>     def handle_response(
>         result,
>         name,
>         quiet=False,
>         element='',
>         action='deployed',
>         client=None
>     )


:param result:
:param name:
:param quiet:
:param element:
:param action:
:param client:
:return:

    
### Function `ignition` {#kvirt.common.ignition}




>     def ignition(
>         name,
>         keys=[],
>         cmds=[],
>         nets=[],
>         gateway=None,
>         dns=None,
>         domain=None,
>         reserveip=False,
>         files=[],
>         enableroot=True,
>         overrides={},
>         iso=True,
>         fqdn=False,
>         version='3.0.0',
>         plan=None,
>         compact=False,
>         removetls=False,
>         ipv6=[],
>         image=None
>     )


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




>     def ignition_version(
>         image
>     )




    
### Function `info` {#kvirt.common.info}




>     def info(
>         text
>     )




    
### Function `insecure_fetch` {#kvirt.common.insecure_fetch}




>     def insecure_fetch(
>         url,
>         headers=[]
>     )




    
### Function `is_7` {#kvirt.common.is_7}




>     def is_7(
>         image
>     )




    
### Function `is_debian` {#kvirt.common.is_debian}




>     def is_debian(
>         image
>     )




    
### Function `kube_create_app` {#kvirt.common.kube_create_app}




>     def kube_create_app(
>         config,
>         appdir,
>         overrides={}
>     )




    
### Function `kube_delete_app` {#kvirt.common.kube_delete_app}




>     def kube_delete_app(
>         config,
>         appdir,
>         overrides={}
>     )




    
### Function `mergeignition` {#kvirt.common.mergeignition}




>     def mergeignition(
>         name,
>         ignitionextrapath,
>         data
>     )




    
### Function `need_guest_agent` {#kvirt.common.need_guest_agent}




>     def need_guest_agent(
>         image
>     )




    
### Function `needs_ignition` {#kvirt.common.needs_ignition}




>     def needs_ignition(
>         image
>     )




    
### Function `pprint` {#kvirt.common.pprint}




>     def pprint(
>         text,
>         color='green'
>     )


:param text:
:param color:

    
### Function `pretty_print` {#kvirt.common.pretty_print}




>     def pretty_print(
>         o,
>         value=False
>     )


:param o:

    
### Function `print_info` {#kvirt.common.print_info}




>     def print_info(
>         yamlinfo,
>         output='plain',
>         fields=[],
>         values=False,
>         pretty=True
>     )


:param yamlinfo:
:param output:
:param fields:
:param values:

    
### Function `process_cmds` {#kvirt.common.process_cmds}




>     def process_cmds(
>         cmds,
>         overrides
>     )


:param cmds:
:param overrides:
:return:

    
### Function `process_files` {#kvirt.common.process_files}




>     def process_files(
>         files=[],
>         overrides={}
>     )


:param files:
:param overrides:
:return:

    
### Function `process_ignition_cmds` {#kvirt.common.process_ignition_cmds}




>     def process_ignition_cmds(
>         cmds,
>         overrides
>     )


:param cmds:
:param overrides:
:return:

    
### Function `process_ignition_files` {#kvirt.common.process_ignition_files}




>     def process_ignition_files(
>         files=[],
>         overrides={}
>     )


:param files:
:param overrides:
:return:

    
### Function `pwd_path` {#kvirt.common.pwd_path}




>     def pwd_path(
>         x
>     )




    
### Function `real_path` {#kvirt.common.real_path}




>     def real_path(
>         x
>     )




    
### Function `remove_duplicates` {#kvirt.common.remove_duplicates}




>     def remove_duplicates(
>         oldlist
>     )


:param oldlist:
:return:

    
### Function `scp` {#kvirt.common.scp}




>     def scp(
>         name,
>         ip='',
>         user=None,
>         source=None,
>         destination=None,
>         recursive=None,
>         tunnel=False,
>         tunnelhost=None,
>         tunnelport=22,
>         tunneluser='root',
>         debug=False,
>         download=False,
>         vmport=None,
>         insecure=False
>     )


:param name:
:param ip:
:param user:
:param source:
:param destination:
:param recursive:
:param tunnel:
:param tunnelhost:
:param tunnelport:
:param tunneluser:
:param debug:
:param download:
:param vmport:
:return:

    
### Function `set_lastvm` {#kvirt.common.set_lastvm}




>     def set_lastvm(
>         name,
>         client,
>         delete=False
>     )


:param name:
:param client:
:param delete:
:return:

    
### Function `ssh` {#kvirt.common.ssh}




>     def ssh(
>         name,
>         ip='',
>         user=None,
>         local=None,
>         remote=None,
>         tunnel=False,
>         tunnelhost=None,
>         tunnelport=22,
>         tunneluser='root',
>         insecure=False,
>         cmd=None,
>         X=False,
>         Y=False,
>         debug=False,
>         D=None,
>         vmport=None
>     )


:param name:
:param ip:
:param host:
:param port:
:param user:
:param local:
:param remote:
:param tunnel:
:param tunnelhost:
:param tunnelport:
:param tunneluser:
:param insecure:
:param cmd:
:param X:
:param Y:
:param debug:
:param D:
:param vmport:
:return:

    
### Function `url_exists` {#kvirt.common.url_exists}




>     def url_exists(
>         url
>     )




    
### Function `valid_tag` {#kvirt.common.valid_tag}




>     def valid_tag(
>         tag
>     )







    
# Module `kvirt.config` {#kvirt.config}

Kvirt config class





    
## Classes


    
### Class `Kconfig` {#kvirt.config.Kconfig}




>     class Kconfig(
>         client=None,
>         debug=False,
>         quiet=False,
>         region=None,
>         zone=None,
>         namespace=None
>     )





    
#### Ancestors (in MRO)

* [kvirt.baseconfig.Kbaseconfig](#kvirt.baseconfig.Kbaseconfig)






    
#### Methods


    
##### Method `create_kube_generic` {#kvirt.config.Kconfig.create_kube_generic}




>     def create_kube_generic(
>         self,
>         cluster,
>         overrides={}
>     )




    
##### Method `create_kube_k3s` {#kvirt.config.Kconfig.create_kube_k3s}




>     def create_kube_k3s(
>         self,
>         cluster,
>         overrides={}
>     )




    
##### Method `create_kube_openshift` {#kvirt.config.Kconfig.create_kube_openshift}




>     def create_kube_openshift(
>         self,
>         cluster,
>         overrides={}
>     )




    
##### Method `create_product` {#kvirt.config.Kconfig.create_product}




>     def create_product(
>         self,
>         name,
>         repo=None,
>         group=None,
>         plan=None,
>         latest=False,
>         overrides={}
>     )


Create product

    
##### Method `create_vm` {#kvirt.config.Kconfig.create_vm}




>     def create_vm(
>         self,
>         name,
>         profile,
>         overrides={},
>         customprofile={},
>         k=None,
>         plan='kvirt',
>         basedir='.',
>         client=None,
>         onfly=None,
>         wait=False
>     )


:param k:
:param plan:
:param name:
:param profile:
:param overrides:
:param customprofile:
:return:

    
##### Method `delete_kube` {#kvirt.config.Kconfig.delete_kube}




>     def delete_kube(
>         self,
>         cluster,
>         overrides={}
>     )




    
##### Method `download_openshift_installer` {#kvirt.config.Kconfig.download_openshift_installer}




>     def download_openshift_installer(
>         self,
>         overrides={}
>     )




    
##### Method `expose_plan` {#kvirt.config.Kconfig.expose_plan}




>     def expose_plan(
>         self,
>         plan,
>         inputfile=None,
>         overrides={},
>         port=9000
>     )




    
##### Method `handle_host` {#kvirt.config.Kconfig.handle_host}




>     def handle_host(
>         self,
>         pool=None,
>         image=None,
>         switch=None,
>         download=False,
>         url=None,
>         cmd=None,
>         sync=False,
>         update_profile=False,
>         commit=None
>     )


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




>     def handle_loadbalancer(
>         self,
>         name,
>         nets=['default'],
>         ports=[],
>         checkpath='/',
>         vms=[],
>         delete=False,
>         domain=None,
>         plan=None,
>         checkport=80,
>         alias=[],
>         internal=False
>     )




    
##### Method `list_kubes` {#kvirt.config.Kconfig.list_kubes}




>     def list_kubes(
>         self
>     )


:return:

    
##### Method `list_loadbalancers` {#kvirt.config.Kconfig.list_loadbalancers}




>     def list_loadbalancers(
>         self
>     )




    
##### Method `list_plans` {#kvirt.config.Kconfig.list_plans}




>     def list_plans(
>         self
>     )


:return:

    
##### Method `plan` {#kvirt.config.Kconfig.plan}




>     def plan(
>         self,
>         plan,
>         ansible=False,
>         url=None,
>         path=None,
>         autostart=False,
>         container=False,
>         noautostart=False,
>         inputfile=None,
>         inputstring=None,
>         start=False,
>         stop=False,
>         delete=False,
>         force=True,
>         overrides={},
>         info=False,
>         snapshot=False,
>         revert=False,
>         update=False,
>         embedded=False,
>         restart=False,
>         download=False,
>         wait=False,
>         quiet=False,
>         doc=False
>     )


Manage plan file

    
##### Method `scale_kube_generic` {#kvirt.config.Kconfig.scale_kube_generic}




>     def scale_kube_generic(
>         self,
>         cluster,
>         overrides={}
>     )




    
##### Method `scale_kube_k3s` {#kvirt.config.Kconfig.scale_kube_k3s}




>     def scale_kube_k3s(
>         self,
>         cluster,
>         overrides={}
>     )




    
##### Method `scale_kube_openshift` {#kvirt.config.Kconfig.scale_kube_openshift}




>     def scale_kube_openshift(
>         self,
>         cluster,
>         overrides={}
>     )




    
##### Method `wait` {#kvirt.config.Kconfig.wait}




>     def wait(
>         self,
>         name,
>         image=None
>     )






    
# Module `kvirt.container` {#kvirt.container}

container utilites





    
## Classes


    
### Class `Kcontainer` {#kvirt.container.Kcontainer}




>     class Kcontainer(
>         host='127.0.0.1',
>         user='root',
>         port=22,
>         engine='podman',
>         debug=False,
>         insecure=False
>     )










    
#### Methods


    
##### Method `console_container` {#kvirt.container.Kcontainer.console_container}




>     def console_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:

    
##### Method `create_container` {#kvirt.container.Kcontainer.create_container}




>     def create_container(
>         self,
>         name,
>         image,
>         nets=None,
>         cmds=[],
>         ports=[],
>         volumes=[],
>         environment=[],
>         label=None,
>         overrides={}
>     )


:param self:
:param name:
:param image:
:param nets:
:param cmds:
:param ports:
:param volumes:
:param environment:
:param label:
:param overrides:
:return:

    
##### Method `delete_container` {#kvirt.container.Kcontainer.delete_container}




>     def delete_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:

    
##### Method `exists_container` {#kvirt.container.Kcontainer.exists_container}




>     def exists_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:

    
##### Method `list_containers` {#kvirt.container.Kcontainer.list_containers}




>     def list_containers(
>         self
>     )


:param self:
:return:

    
##### Method `list_images` {#kvirt.container.Kcontainer.list_images}




>     def list_images(
>         self
>     )


:param self:
:return:

    
##### Method `start_container` {#kvirt.container.Kcontainer.start_container}




>     def start_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:

    
##### Method `stop_container` {#kvirt.container.Kcontainer.stop_container}




>     def stop_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:



    
# Module `kvirt.containerconfig` {#kvirt.containerconfig}

Kvirt containerconfig class





    
## Classes


    
### Class `Kcontainerconfig` {#kvirt.containerconfig.Kcontainerconfig}




>     class Kcontainerconfig(
>         config,
>         client=None,
>         namespace=None
>     )












    
# Module `kvirt.defaults` {#kvirt.defaults}









    
# Module `kvirt.examples` {#kvirt.examples}









    
# Module `kvirt.expose` {#kvirt.expose}







    
## Classes


    
### Class `Kexposer` {#kvirt.expose.Kexposer}




>     class Kexposer(
>         config,
>         inputfile,
>         overrides={},
>         plan=None,
>         port=9000
>     )










    
#### Methods


    
##### Method `run` {#kvirt.expose.Kexposer.run}




>     def run(
>         self
>     )






    
# Module `kvirt.internalplans` {#kvirt.internalplans}









    
# Module `kvirt.jinjafilters` {#kvirt.jinjafilters}






    
## Functions


    
### Function `base64` {#kvirt.jinjafilters.base64}




>     def base64(
>         value
>     )




    
### Function `basename` {#kvirt.jinjafilters.basename}




>     def basename(
>         path
>     )




    
### Function `certificate` {#kvirt.jinjafilters.certificate}




>     def certificate(
>         value
>     )




    
### Function `defaultnodes` {#kvirt.jinjafilters.defaultnodes}




>     def defaultnodes(
>         replicas,
>         cluster,
>         domain,
>         masters,
>         workers
>     )




    
### Function `dirname` {#kvirt.jinjafilters.dirname}




>     def dirname(
>         path
>     )




    
### Function `githubversion` {#kvirt.jinjafilters.githubversion}




>     def githubversion(
>         repo,
>         version=None
>     )




    
### Function `none` {#kvirt.jinjafilters.none}




>     def none(
>         value
>     )




    
### Function `ocpnodes` {#kvirt.jinjafilters.ocpnodes}




>     def ocpnodes(
>         cluster,
>         platform,
>         masters,
>         workers
>     )







    
# Module `kvirt.k3s` {#kvirt.k3s}






    
## Functions


    
### Function `create` {#kvirt.k3s.create}




>     def create(
>         config,
>         plandir,
>         cluster,
>         overrides
>     )




    
### Function `scale` {#kvirt.k3s.scale}




>     def scale(
>         config,
>         plandir,
>         cluster,
>         overrides
>     )







    
# Module `kvirt.kbmc` {#kvirt.kbmc}






    
## Functions


    
### Function `main` {#kvirt.kbmc.main}




>     def main()





    
## Classes


    
### Class `KBmc` {#kvirt.kbmc.KBmc}




>     class KBmc(
>         authdata,
>         port,
>         name,
>         client
>     )


Create a new ipmi bmc instance.

:param authdata: A dict or object with .get() to provide password
                lookup by username.  This does not support the full
                complexity of what IPMI can support, only a
                reasonable subset.
:param port: The default port number to bind to.  Defaults to the
             standard 623
:param address: The IP address to bind to. Defaults to '::' (all
                zeroes)


    
#### Ancestors (in MRO)

* [pyghmi.ipmi.bmc.Bmc](#pyghmi.ipmi.bmc.Bmc)
* [pyghmi.ipmi.private.serversession.IpmiServer](#pyghmi.ipmi.private.serversession.IpmiServer)






    
#### Methods


    
##### Method `cold_reset` {#kvirt.kbmc.KBmc.cold_reset}




>     def cold_reset(
>         self
>     )




    
##### Method `get_boot_device` {#kvirt.kbmc.KBmc.get_boot_device}




>     def get_boot_device(
>         self
>     )




    
##### Method `get_power_state` {#kvirt.kbmc.KBmc.get_power_state}




>     def get_power_state(
>         self
>     )




    
##### Method `iohandler` {#kvirt.kbmc.KBmc.iohandler}




>     def iohandler(
>         self,
>         data
>     )




    
##### Method `is_active` {#kvirt.kbmc.KBmc.is_active}




>     def is_active(
>         self
>     )




    
##### Method `power_off` {#kvirt.kbmc.KBmc.power_off}




>     def power_off(
>         self
>     )




    
##### Method `power_on` {#kvirt.kbmc.KBmc.power_on}




>     def power_on(
>         self
>     )




    
##### Method `power_reset` {#kvirt.kbmc.KBmc.power_reset}




>     def power_reset(
>         self
>     )




    
##### Method `power_shutdown` {#kvirt.kbmc.KBmc.power_shutdown}




>     def power_shutdown(
>         self
>     )




    
##### Method `set_boot_device` {#kvirt.kbmc.KBmc.set_boot_device}




>     def set_boot_device(
>         self,
>         bootdevice
>     )






    
# Module `kvirt.klist` {#kvirt.klist}






    
## Functions


    
### Function `empty` {#kvirt.klist.empty}




>     def empty()


:return:

    
### Function `main` {#kvirt.klist.main}




>     def main()





    
## Classes


    
### Class `KcliInventory` {#kvirt.klist.KcliInventory}




>     class KcliInventory










    
#### Methods


    
##### Method `get` {#kvirt.klist.KcliInventory.get}




>     def get(
>         self,
>         name
>     )


:return:

    
##### Method `read_cli_args` {#kvirt.klist.KcliInventory.read_cli_args}




>     def read_cli_args(
>         self
>     )






    
# Module `kvirt.krpc` {#kvirt.krpc}




    
## Sub-modules

* [kvirt.krpc.cli](#kvirt.krpc.cli)
* [kvirt.krpc.commoncli](#kvirt.krpc.commoncli)
* [kvirt.krpc.kcli_pb2](#kvirt.krpc.kcli_pb2)
* [kvirt.krpc.kcli_pb2_grpc](#kvirt.krpc.kcli_pb2_grpc)
* [kvirt.krpc.server](#kvirt.krpc.server)






    
# Module `kvirt.krpc.cli` {#kvirt.krpc.cli}






    
## Functions


    
### Function `alias` {#kvirt.krpc.cli.alias}




>     def alias(
>         text
>     )




    
### Function `autostart_plan` {#kvirt.krpc.cli.autostart_plan}




>     def autostart_plan(
>         args
>     )


Autostart plan

    
### Function `cli` {#kvirt.krpc.cli.cli}




>     def cli()




    
### Function `clone_vm` {#kvirt.krpc.cli.clone_vm}




>     def clone_vm(
>         args
>     )


Clone existing vm

    
### Function `console_container` {#kvirt.krpc.cli.console_container}




>     def console_container(
>         args
>     )


Container console

    
### Function `console_vm` {#kvirt.krpc.cli.console_vm}




>     def console_vm(
>         args
>     )


Vnc/Spice/Serial Vm console

    
### Function `create_container` {#kvirt.krpc.cli.create_container}




>     def create_container(
>         args
>     )


Create container

    
### Function `create_dns` {#kvirt.krpc.cli.create_dns}




>     def create_dns(
>         args
>     )


Create dns entries

    
### Function `create_generic_kube` {#kvirt.krpc.cli.create_generic_kube}




>     def create_generic_kube(
>         args
>     )


Create Generic kube

    
### Function `create_host_aws` {#kvirt.krpc.cli.create_host_aws}




>     def create_host_aws(
>         args
>     )


Create Aws Host

    
### Function `create_host_gcp` {#kvirt.krpc.cli.create_host_gcp}




>     def create_host_gcp(
>         args
>     )


Create Gcp Host

    
### Function `create_host_kubevirt` {#kvirt.krpc.cli.create_host_kubevirt}




>     def create_host_kubevirt(
>         args
>     )


Create Kubevirt Host

    
### Function `create_host_kvm` {#kvirt.krpc.cli.create_host_kvm}




>     def create_host_kvm(
>         args
>     )


Generate Kvm Host

    
### Function `create_host_openstack` {#kvirt.krpc.cli.create_host_openstack}




>     def create_host_openstack(
>         args
>     )


Create Openstack Host

    
### Function `create_host_ovirt` {#kvirt.krpc.cli.create_host_ovirt}




>     def create_host_ovirt(
>         args
>     )


Create Ovirt Host

    
### Function `create_host_vsphere` {#kvirt.krpc.cli.create_host_vsphere}




>     def create_host_vsphere(
>         args
>     )


Create Vsphere Host

    
### Function `create_lb` {#kvirt.krpc.cli.create_lb}




>     def create_lb(
>         args
>     )


Create loadbalancer

    
### Function `create_network` {#kvirt.krpc.cli.create_network}




>     def create_network(
>         args
>     )


Create Network

    
### Function `create_openshift_kube` {#kvirt.krpc.cli.create_openshift_kube}




>     def create_openshift_kube(
>         args
>     )


Create Generic kube

    
### Function `create_pipeline` {#kvirt.krpc.cli.create_pipeline}




>     def create_pipeline(
>         args
>     )


Create Pipeline

    
### Function `create_plan` {#kvirt.krpc.cli.create_plan}




>     def create_plan(
>         args
>     )


Create plan

    
### Function `create_pool` {#kvirt.krpc.cli.create_pool}




>     def create_pool(
>         args
>     )


Create/Delete pool

    
### Function `create_product` {#kvirt.krpc.cli.create_product}




>     def create_product(
>         args
>     )


Create product

    
### Function `create_profile` {#kvirt.krpc.cli.create_profile}




>     def create_profile(
>         args
>     )


Create profile

    
### Function `create_repo` {#kvirt.krpc.cli.create_repo}




>     def create_repo(
>         args
>     )


Create repo

    
### Function `create_vm` {#kvirt.krpc.cli.create_vm}




>     def create_vm(
>         args
>     )


Create vms

    
### Function `create_vmdisk` {#kvirt.krpc.cli.create_vmdisk}




>     def create_vmdisk(
>         args
>     )


Add disk to vm

    
### Function `create_vmnic` {#kvirt.krpc.cli.create_vmnic}




>     def create_vmnic(
>         args
>     )


Add nic to vm

    
### Function `delete_container` {#kvirt.krpc.cli.delete_container}




>     def delete_container(
>         args
>     )


Delete container

    
### Function `delete_dns` {#kvirt.krpc.cli.delete_dns}




>     def delete_dns(
>         args
>     )


Delete dns entries

    
### Function `delete_host` {#kvirt.krpc.cli.delete_host}




>     def delete_host(
>         args
>     )


Delete host

    
### Function `delete_image` {#kvirt.krpc.cli.delete_image}




>     def delete_image(
>         args
>     )




    
### Function `delete_kube` {#kvirt.krpc.cli.delete_kube}




>     def delete_kube(
>         args
>     )


Delete kube

    
### Function `delete_lb` {#kvirt.krpc.cli.delete_lb}




>     def delete_lb(
>         args
>     )


Delete loadbalancer

    
### Function `delete_network` {#kvirt.krpc.cli.delete_network}




>     def delete_network(
>         args
>     )


Delete Network

    
### Function `delete_plan` {#kvirt.krpc.cli.delete_plan}




>     def delete_plan(
>         args
>     )


Delete plan

    
### Function `delete_pool` {#kvirt.krpc.cli.delete_pool}




>     def delete_pool(
>         args
>     )


Delete pool

    
### Function `delete_profile` {#kvirt.krpc.cli.delete_profile}




>     def delete_profile(
>         args
>     )


Delete profile

    
### Function `delete_repo` {#kvirt.krpc.cli.delete_repo}




>     def delete_repo(
>         args
>     )


Delete repo

    
### Function `delete_vm` {#kvirt.krpc.cli.delete_vm}




>     def delete_vm(
>         args
>     )


Delete vm

    
### Function `delete_vmdisk` {#kvirt.krpc.cli.delete_vmdisk}




>     def delete_vmdisk(
>         args
>     )


Delete disk of vm

    
### Function `delete_vmnic` {#kvirt.krpc.cli.delete_vmnic}




>     def delete_vmnic(
>         args
>     )


Delete nic of vm

    
### Function `disable_host` {#kvirt.krpc.cli.disable_host}




>     def disable_host(
>         args
>     )


Disable host

    
### Function `download_image` {#kvirt.krpc.cli.download_image}




>     def download_image(
>         args
>     )


Download Image

    
### Function `download_kubectl` {#kvirt.krpc.cli.download_kubectl}




>     def download_kubectl(
>         args
>     )


Download Kubectl

    
### Function `download_oc` {#kvirt.krpc.cli.download_oc}




>     def download_oc(
>         args
>     )


Download Oc

    
### Function `download_openshift_installer` {#kvirt.krpc.cli.download_openshift_installer}




>     def download_openshift_installer(
>         args
>     )


Download Openshift Installer

    
### Function `download_plan` {#kvirt.krpc.cli.download_plan}




>     def download_plan(
>         args
>     )


Download plan

    
### Function `enable_host` {#kvirt.krpc.cli.enable_host}




>     def enable_host(
>         args
>     )


Enable host

    
### Function `export_vm` {#kvirt.krpc.cli.export_vm}




>     def export_vm(
>         args
>     )


Export a vm

    
### Function `finalswitch` {#kvirt.krpc.cli.finalswitch}




>     def finalswitch(
>         baseconfig,
>         client
>     )




    
### Function `get_subparser` {#kvirt.krpc.cli.get_subparser}




>     def get_subparser(
>         parser,
>         subcommand
>     )




    
### Function `get_subparser_print_help` {#kvirt.krpc.cli.get_subparser_print_help}




>     def get_subparser_print_help(
>         parser,
>         subcommand
>     )




    
### Function `get_version` {#kvirt.krpc.cli.get_version}




>     def get_version(
>         args
>     )




    
### Function `info_generic_kube` {#kvirt.krpc.cli.info_generic_kube}




>     def info_generic_kube(
>         args
>     )


Info Generic kube

    
### Function `info_openshift_kube` {#kvirt.krpc.cli.info_openshift_kube}




>     def info_openshift_kube(
>         args
>     )


Info Openshift kube

    
### Function `info_plan` {#kvirt.krpc.cli.info_plan}




>     def info_plan(
>         args
>     )


Info plan

    
### Function `info_product` {#kvirt.krpc.cli.info_product}




>     def info_product(
>         args
>     )


Info product

    
### Function `info_vm` {#kvirt.krpc.cli.info_vm}




>     def info_vm(
>         args
>     )


Get info on vm

    
### Function `list_container` {#kvirt.krpc.cli.list_container}




>     def list_container(
>         args
>     )


List containers

    
### Function `list_containerimage` {#kvirt.krpc.cli.list_containerimage}




>     def list_containerimage(
>         args
>     )


List container images

    
### Function `list_dns` {#kvirt.krpc.cli.list_dns}




>     def list_dns(
>         args
>     )


List flavors

    
### Function `list_flavor` {#kvirt.krpc.cli.list_flavor}




>     def list_flavor(
>         args
>     )


List flavors

    
### Function `list_host` {#kvirt.krpc.cli.list_host}




>     def list_host(
>         args
>     )


List hosts

    
### Function `list_image` {#kvirt.krpc.cli.list_image}




>     def list_image(
>         args
>     )


List images

    
### Function `list_iso` {#kvirt.krpc.cli.list_iso}




>     def list_iso(
>         args
>     )


List isos

    
### Function `list_keyword` {#kvirt.krpc.cli.list_keyword}




>     def list_keyword(
>         args
>     )


List keywords

    
### Function `list_kube` {#kvirt.krpc.cli.list_kube}




>     def list_kube(
>         args
>     )


List kube

    
### Function `list_lb` {#kvirt.krpc.cli.list_lb}




>     def list_lb(
>         args
>     )


List lbs

    
### Function `list_network` {#kvirt.krpc.cli.list_network}




>     def list_network(
>         args
>     )


List networks

    
### Function `list_plan` {#kvirt.krpc.cli.list_plan}




>     def list_plan(
>         args
>     )


List plans

    
### Function `list_pool` {#kvirt.krpc.cli.list_pool}




>     def list_pool(
>         args
>     )


List pools

    
### Function `list_product` {#kvirt.krpc.cli.list_product}




>     def list_product(
>         args
>     )


List products

    
### Function `list_profile` {#kvirt.krpc.cli.list_profile}




>     def list_profile(
>         args
>     )


List profiles

    
### Function `list_repo` {#kvirt.krpc.cli.list_repo}




>     def list_repo(
>         args
>     )


List repos

    
### Function `list_vm` {#kvirt.krpc.cli.list_vm}




>     def list_vm(
>         args
>     )


List vms

    
### Function `list_vmdisk` {#kvirt.krpc.cli.list_vmdisk}




>     def list_vmdisk(
>         args
>     )


List vm disks

    
### Function `noautostart_plan` {#kvirt.krpc.cli.noautostart_plan}




>     def noautostart_plan(
>         args
>     )


Noautostart plan

    
### Function `profilelist_container` {#kvirt.krpc.cli.profilelist_container}




>     def profilelist_container(
>         args
>     )


List container profiles

    
### Function `render_file` {#kvirt.krpc.cli.render_file}




>     def render_file(
>         args
>     )


Render file

    
### Function `report_host` {#kvirt.krpc.cli.report_host}




>     def report_host(
>         args
>     )


Report info about host

    
### Function `restart_container` {#kvirt.krpc.cli.restart_container}




>     def restart_container(
>         args
>     )


Restart containers

    
### Function `restart_plan` {#kvirt.krpc.cli.restart_plan}




>     def restart_plan(
>         args
>     )


Restart plan

    
### Function `restart_vm` {#kvirt.krpc.cli.restart_vm}




>     def restart_vm(
>         args
>     )


Restart vms

    
### Function `revert_plan` {#kvirt.krpc.cli.revert_plan}




>     def revert_plan(
>         args
>     )


Revert snapshot of plan

    
### Function `scale_generic_kube` {#kvirt.krpc.cli.scale_generic_kube}




>     def scale_generic_kube(
>         args
>     )


Scale kube

    
### Function `scale_openshift_kube` {#kvirt.krpc.cli.scale_openshift_kube}




>     def scale_openshift_kube(
>         args
>     )


Scale openshift kube

    
### Function `scp_vm` {#kvirt.krpc.cli.scp_vm}




>     def scp_vm(
>         args
>     )


Scp into vm

    
### Function `snapshot_plan` {#kvirt.krpc.cli.snapshot_plan}




>     def snapshot_plan(
>         args
>     )


Snapshot plan

    
### Function `snapshotcreate_vm` {#kvirt.krpc.cli.snapshotcreate_vm}




>     def snapshotcreate_vm(
>         args
>     )


Create snapshot

    
### Function `snapshotdelete_vm` {#kvirt.krpc.cli.snapshotdelete_vm}




>     def snapshotdelete_vm(
>         args
>     )


Delete snapshot

    
### Function `snapshotlist_vm` {#kvirt.krpc.cli.snapshotlist_vm}




>     def snapshotlist_vm(
>         args
>     )


List snapshots of vm

    
### Function `snapshotrevert_vm` {#kvirt.krpc.cli.snapshotrevert_vm}




>     def snapshotrevert_vm(
>         args
>     )


Revert snapshot of vm

    
### Function `ssh_vm` {#kvirt.krpc.cli.ssh_vm}




>     def ssh_vm(
>         args
>     )


Ssh into vm

    
### Function `start_container` {#kvirt.krpc.cli.start_container}




>     def start_container(
>         args
>     )


Start containers

    
### Function `start_plan` {#kvirt.krpc.cli.start_plan}




>     def start_plan(
>         args
>     )


Start plan

    
### Function `start_vm` {#kvirt.krpc.cli.start_vm}




>     def start_vm(
>         args
>     )


Start vms

    
### Function `stop_container` {#kvirt.krpc.cli.stop_container}




>     def stop_container(
>         args
>     )


Stop containers

    
### Function `stop_plan` {#kvirt.krpc.cli.stop_plan}




>     def stop_plan(
>         args
>     )


Stop plan

    
### Function `stop_vm` {#kvirt.krpc.cli.stop_vm}




>     def stop_vm(
>         args
>     )


Stop vms

    
### Function `switch_host` {#kvirt.krpc.cli.switch_host}




>     def switch_host(
>         args
>     )


Handle host

    
### Function `sync_host` {#kvirt.krpc.cli.sync_host}




>     def sync_host(
>         args
>     )


Handle host

    
### Function `update_plan` {#kvirt.krpc.cli.update_plan}




>     def update_plan(
>         args
>     )


Update plan

    
### Function `update_profile` {#kvirt.krpc.cli.update_profile}




>     def update_profile(
>         args
>     )


Update profile

    
### Function `update_repo` {#kvirt.krpc.cli.update_repo}




>     def update_repo(
>         args
>     )


Update repo

    
### Function `update_vm` {#kvirt.krpc.cli.update_vm}




>     def update_vm(
>         args
>     )


Update ip, memory or numcpus

    
### Function `valid_cluster` {#kvirt.krpc.cli.valid_cluster}




>     def valid_cluster(
>         name
>     )




    
### Function `valid_fqdn` {#kvirt.krpc.cli.valid_fqdn}




>     def valid_fqdn(
>         name
>     )





    
## Classes


    
### Class `Kconfig` {#kvirt.krpc.cli.Kconfig}




>     class Kconfig(
>         client=None,
>         debug=None,
>         region=None,
>         zone=None,
>         namespace=None
>     )










    
### Class `empty` {#kvirt.krpc.cli.empty}




>     class empty(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.cli.empty.DESCRIPTOR}











    
# Module `kvirt.krpc.commoncli` {#kvirt.krpc.commoncli}






    
## Functions


    
### Function `confirm` {#kvirt.krpc.commoncli.confirm}




>     def confirm(
>         message
>     )


:param message:
:return:

    
### Function `fetch` {#kvirt.krpc.commoncli.fetch}




>     def fetch(
>         url,
>         path
>     )




    
### Function `get_free_nodeport` {#kvirt.krpc.commoncli.get_free_nodeport}




>     def get_free_nodeport()


:return:

    
### Function `get_free_port` {#kvirt.krpc.commoncli.get_free_port}




>     def get_free_port()


:return:

    
### Function `get_kubectl` {#kvirt.krpc.commoncli.get_kubectl}




>     def get_kubectl()




    
### Function `get_oc` {#kvirt.krpc.commoncli.get_oc}




>     def get_oc(
>         macosx=False
>     )




    
### Function `get_overrides` {#kvirt.krpc.commoncli.get_overrides}




>     def get_overrides(
>         paramfile=None,
>         param=[]
>     )


:param paramfile:
:param param:
:return:

    
### Function `get_parameters` {#kvirt.krpc.commoncli.get_parameters}




>     def get_parameters(
>         inputfile,
>         raw=False
>     )


:param inputfile:
:param raw:
:return:

    
### Function `handle_response` {#kvirt.krpc.commoncli.handle_response}




>     def handle_response(
>         result,
>         name,
>         quiet=False,
>         element='',
>         action='deployed',
>         client=None
>     )


:param result:
:param name:
:param quiet:
:param element:
:param action:
:param client:
:return:

    
### Function `pprint` {#kvirt.krpc.commoncli.pprint}




>     def pprint(
>         text,
>         color='green'
>     )


:param text:
:param color:

    
### Function `print_info` {#kvirt.krpc.commoncli.print_info}




>     def print_info(
>         yamlinfo,
>         output='plain',
>         fields=[],
>         values=False,
>         pretty=True
>     )


:param yamlinfo:
:param output:
:param fields:
:param values:

    
### Function `url_exists` {#kvirt.krpc.commoncli.url_exists}




>     def url_exists(
>         url
>     )







    
# Module `kvirt.krpc.kcli_pb2` {#kvirt.krpc.kcli_pb2}







    
## Classes


    
### Class `client` {#kvirt.krpc.kcli_pb2.client}




>     class client(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.client.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `access_key_id` {#kvirt.krpc.kcli_pb2.client.access_key_id}




Field client.access_key_id

    
##### Variable `access_key_secret` {#kvirt.krpc.kcli_pb2.client.access_key_secret}




Field client.access_key_secret

    
##### Variable `auth_url` {#kvirt.krpc.kcli_pb2.client.auth_url}




Field client.auth_url

    
##### Variable `ca_file` {#kvirt.krpc.kcli_pb2.client.ca_file}




Field client.ca_file

    
##### Variable `cdi` {#kvirt.krpc.kcli_pb2.client.cdi}




Field client.cdi

    
##### Variable `client` {#kvirt.krpc.kcli_pb2.client.client}




Field client.client

    
##### Variable `cluster` {#kvirt.krpc.kcli_pb2.client.cluster}




Field client.cluster

    
##### Variable `credentials` {#kvirt.krpc.kcli_pb2.client.credentials}




Field client.credentials

    
##### Variable `current` {#kvirt.krpc.kcli_pb2.client.current}




Field client.current

    
##### Variable `datacenter` {#kvirt.krpc.kcli_pb2.client.datacenter}




Field client.datacenter

    
##### Variable `domain` {#kvirt.krpc.kcli_pb2.client.domain}




Field client.domain

    
##### Variable `enabled` {#kvirt.krpc.kcli_pb2.client.enabled}




Field client.enabled

    
##### Variable `host` {#kvirt.krpc.kcli_pb2.client.host}




Field client.host

    
##### Variable `keypair` {#kvirt.krpc.kcli_pb2.client.keypair}




Field client.keypair

    
##### Variable `multus` {#kvirt.krpc.kcli_pb2.client.multus}




Field client.multus

    
##### Variable `name` {#kvirt.krpc.kcli_pb2.client.name}




Field client.name

    
##### Variable `org` {#kvirt.krpc.kcli_pb2.client.org}




Field client.org

    
##### Variable `password` {#kvirt.krpc.kcli_pb2.client.password}




Field client.password

    
##### Variable `pool` {#kvirt.krpc.kcli_pb2.client.pool}




Field client.pool

    
##### Variable `port` {#kvirt.krpc.kcli_pb2.client.port}




Field client.port

    
##### Variable `project` {#kvirt.krpc.kcli_pb2.client.project}




Field client.project

    
##### Variable `protocol` {#kvirt.krpc.kcli_pb2.client.protocol}




Field client.protocol

    
##### Variable `region` {#kvirt.krpc.kcli_pb2.client.region}




Field client.region

    
##### Variable `token` {#kvirt.krpc.kcli_pb2.client.token}




Field client.token

    
##### Variable `type` {#kvirt.krpc.kcli_pb2.client.type}




Field client.type

    
##### Variable `url` {#kvirt.krpc.kcli_pb2.client.url}




Field client.url

    
##### Variable `user` {#kvirt.krpc.kcli_pb2.client.user}




Field client.user

    
##### Variable `zone` {#kvirt.krpc.kcli_pb2.client.zone}




Field client.zone



    
### Class `clientslist` {#kvirt.krpc.kcli_pb2.clientslist}




>     class clientslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.clientslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `clients` {#kvirt.krpc.kcli_pb2.clientslist.clients}




Field clientslist.clients



    
### Class `cmd` {#kvirt.krpc.kcli_pb2.cmd}




>     class cmd(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.cmd.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `cmd` {#kvirt.krpc.kcli_pb2.cmd.cmd}




Field cmd.cmd



    
### Class `config` {#kvirt.krpc.kcli_pb2.config}




>     class config(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.config.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `client` {#kvirt.krpc.kcli_pb2.config.client}




Field config.client

    
##### Variable `extraclients` {#kvirt.krpc.kcli_pb2.config.extraclients}




Field config.extraclients



    
### Class `container` {#kvirt.krpc.kcli_pb2.container}




>     class container(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.container.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `command` {#kvirt.krpc.kcli_pb2.container.command}




Field container.command

    
##### Variable `container` {#kvirt.krpc.kcli_pb2.container.container}




Field container.container

    
##### Variable `deploy` {#kvirt.krpc.kcli_pb2.container.deploy}




Field container.deploy

    
##### Variable `image` {#kvirt.krpc.kcli_pb2.container.image}




Field container.image

    
##### Variable `plan` {#kvirt.krpc.kcli_pb2.container.plan}




Field container.plan

    
##### Variable `ports` {#kvirt.krpc.kcli_pb2.container.ports}




Field container.ports

    
##### Variable `status` {#kvirt.krpc.kcli_pb2.container.status}




Field container.status



    
### Class `containerslist` {#kvirt.krpc.kcli_pb2.containerslist}




>     class containerslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.containerslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `containers` {#kvirt.krpc.kcli_pb2.containerslist.containers}




Field containerslist.containers



    
### Class `disk` {#kvirt.krpc.kcli_pb2.disk}




>     class disk(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.disk.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `disk` {#kvirt.krpc.kcli_pb2.disk.disk}




Field disk.disk

    
##### Variable `path` {#kvirt.krpc.kcli_pb2.disk.path}




Field disk.path

    
##### Variable `pool` {#kvirt.krpc.kcli_pb2.disk.pool}




Field disk.pool



    
### Class `diskinfo` {#kvirt.krpc.kcli_pb2.diskinfo}




>     class diskinfo(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.diskinfo.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `device` {#kvirt.krpc.kcli_pb2.diskinfo.device}




Field diskinfo.device

    
##### Variable `format` {#kvirt.krpc.kcli_pb2.diskinfo.format}




Field diskinfo.format

    
##### Variable `path` {#kvirt.krpc.kcli_pb2.diskinfo.path}




Field diskinfo.path

    
##### Variable `size` {#kvirt.krpc.kcli_pb2.diskinfo.size}




Field diskinfo.size

    
##### Variable `type` {#kvirt.krpc.kcli_pb2.diskinfo.type}




Field diskinfo.type



    
### Class `diskslist` {#kvirt.krpc.kcli_pb2.diskslist}




>     class diskslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.diskslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `disks` {#kvirt.krpc.kcli_pb2.diskslist.disks}




Field diskslist.disks



    
### Class `empty` {#kvirt.krpc.kcli_pb2.empty}




>     class empty(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.empty.DESCRIPTOR}









    
### Class `flavor` {#kvirt.krpc.kcli_pb2.flavor}




>     class flavor(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.flavor.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `flavor` {#kvirt.krpc.kcli_pb2.flavor.flavor}




Field flavor.flavor

    
##### Variable `memory` {#kvirt.krpc.kcli_pb2.flavor.memory}




Field flavor.memory

    
##### Variable `numcpus` {#kvirt.krpc.kcli_pb2.flavor.numcpus}




Field flavor.numcpus



    
### Class `flavorslist` {#kvirt.krpc.kcli_pb2.flavorslist}




>     class flavorslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.flavorslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `flavors` {#kvirt.krpc.kcli_pb2.flavorslist.flavors}




Field flavorslist.flavors



    
### Class `image` {#kvirt.krpc.kcli_pb2.image}




>     class image(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.image.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `image` {#kvirt.krpc.kcli_pb2.image.image}




Field image.image



    
### Class `imageslist` {#kvirt.krpc.kcli_pb2.imageslist}




>     class imageslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.imageslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `images` {#kvirt.krpc.kcli_pb2.imageslist.images}




Field imageslist.images



    
### Class `isoslist` {#kvirt.krpc.kcli_pb2.isoslist}




>     class isoslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.isoslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `isos` {#kvirt.krpc.kcli_pb2.isoslist.isos}




Field isoslist.isos



    
### Class `keyword` {#kvirt.krpc.kcli_pb2.keyword}




>     class keyword(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.keyword.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `keyword` {#kvirt.krpc.kcli_pb2.keyword.keyword}




Field keyword.keyword

    
##### Variable `value` {#kvirt.krpc.kcli_pb2.keyword.value}




Field keyword.value



    
### Class `keywordslist` {#kvirt.krpc.kcli_pb2.keywordslist}




>     class keywordslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.keywordslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `keywords` {#kvirt.krpc.kcli_pb2.keywordslist.keywords}




Field keywordslist.keywords



    
### Class `kube` {#kvirt.krpc.kcli_pb2.kube}




>     class kube(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.kube.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `kube` {#kvirt.krpc.kcli_pb2.kube.kube}




Field kube.kube

    
##### Variable `type` {#kvirt.krpc.kcli_pb2.kube.type}




Field kube.type

    
##### Variable `vms` {#kvirt.krpc.kcli_pb2.kube.vms}




Field kube.vms



    
### Class `kubeslist` {#kvirt.krpc.kcli_pb2.kubeslist}




>     class kubeslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.kubeslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `kubes` {#kvirt.krpc.kcli_pb2.kubeslist.kubes}




Field kubeslist.kubes



    
### Class `lb` {#kvirt.krpc.kcli_pb2.lb}




>     class lb(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.lb.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `ip` {#kvirt.krpc.kcli_pb2.lb.ip}




Field lb.ip

    
##### Variable `lb` {#kvirt.krpc.kcli_pb2.lb.lb}




Field lb.lb

    
##### Variable `ports` {#kvirt.krpc.kcli_pb2.lb.ports}




Field lb.ports

    
##### Variable `protocol` {#kvirt.krpc.kcli_pb2.lb.protocol}




Field lb.protocol

    
##### Variable `target` {#kvirt.krpc.kcli_pb2.lb.target}




Field lb.target



    
### Class `lbslist` {#kvirt.krpc.kcli_pb2.lbslist}




>     class lbslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.lbslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `lbs` {#kvirt.krpc.kcli_pb2.lbslist.lbs}




Field lbslist.lbs



    
### Class `netinfo` {#kvirt.krpc.kcli_pb2.netinfo}




>     class netinfo(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.netinfo.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `device` {#kvirt.krpc.kcli_pb2.netinfo.device}




Field netinfo.device

    
##### Variable `mac` {#kvirt.krpc.kcli_pb2.netinfo.mac}




Field netinfo.mac

    
##### Variable `net` {#kvirt.krpc.kcli_pb2.netinfo.net}




Field netinfo.net

    
##### Variable `type` {#kvirt.krpc.kcli_pb2.netinfo.type}




Field netinfo.type



    
### Class `network` {#kvirt.krpc.kcli_pb2.network}




>     class network(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.network.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `cidr` {#kvirt.krpc.kcli_pb2.network.cidr}




Field network.cidr

    
##### Variable `dhcp` {#kvirt.krpc.kcli_pb2.network.dhcp}




Field network.dhcp

    
##### Variable `domain` {#kvirt.krpc.kcli_pb2.network.domain}




Field network.domain

    
##### Variable `ip` {#kvirt.krpc.kcli_pb2.network.ip}




Field network.ip

    
##### Variable `mode` {#kvirt.krpc.kcli_pb2.network.mode}




Field network.mode

    
##### Variable `nat` {#kvirt.krpc.kcli_pb2.network.nat}




Field network.nat

    
##### Variable `network` {#kvirt.krpc.kcli_pb2.network.network}




Field network.network

    
##### Variable `overrides` {#kvirt.krpc.kcli_pb2.network.overrides}




Field network.overrides

    
##### Variable `plan` {#kvirt.krpc.kcli_pb2.network.plan}




Field network.plan

    
##### Variable `type` {#kvirt.krpc.kcli_pb2.network.type}




Field network.type



    
### Class `networkslist` {#kvirt.krpc.kcli_pb2.networkslist}




>     class networkslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.networkslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `networks` {#kvirt.krpc.kcli_pb2.networkslist.networks}




Field networkslist.networks



    
### Class `plan` {#kvirt.krpc.kcli_pb2.plan}




>     class plan(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.plan.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `plan` {#kvirt.krpc.kcli_pb2.plan.plan}




Field plan.plan

    
##### Variable `vms` {#kvirt.krpc.kcli_pb2.plan.vms}




Field plan.vms



    
### Class `planslist` {#kvirt.krpc.kcli_pb2.planslist}




>     class planslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.planslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `plans` {#kvirt.krpc.kcli_pb2.planslist.plans}




Field planslist.plans



    
### Class `pool` {#kvirt.krpc.kcli_pb2.pool}




>     class pool(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.pool.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `full` {#kvirt.krpc.kcli_pb2.pool.full}




Field pool.full

    
##### Variable `path` {#kvirt.krpc.kcli_pb2.pool.path}




Field pool.path

    
##### Variable `pool` {#kvirt.krpc.kcli_pb2.pool.pool}




Field pool.pool

    
##### Variable `thinpool` {#kvirt.krpc.kcli_pb2.pool.thinpool}




Field pool.thinpool

    
##### Variable `type` {#kvirt.krpc.kcli_pb2.pool.type}




Field pool.type



    
### Class `poolslist` {#kvirt.krpc.kcli_pb2.poolslist}




>     class poolslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.poolslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `pools` {#kvirt.krpc.kcli_pb2.poolslist.pools}




Field poolslist.pools



    
### Class `product` {#kvirt.krpc.kcli_pb2.product}




>     class product(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.product.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `description` {#kvirt.krpc.kcli_pb2.product.description}




Field product.description

    
##### Variable `group` {#kvirt.krpc.kcli_pb2.product.group}




Field product.group

    
##### Variable `memory` {#kvirt.krpc.kcli_pb2.product.memory}




Field product.memory

    
##### Variable `numvms` {#kvirt.krpc.kcli_pb2.product.numvms}




Field product.numvms

    
##### Variable `product` {#kvirt.krpc.kcli_pb2.product.product}




Field product.product

    
##### Variable `repo` {#kvirt.krpc.kcli_pb2.product.repo}




Field product.repo



    
### Class `productslist` {#kvirt.krpc.kcli_pb2.productslist}




>     class productslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.productslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `products` {#kvirt.krpc.kcli_pb2.productslist.products}




Field productslist.products



    
### Class `profile` {#kvirt.krpc.kcli_pb2.profile}




>     class profile(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.profile.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `cloudinit` {#kvirt.krpc.kcli_pb2.profile.cloudinit}




Field profile.cloudinit

    
##### Variable `disks` {#kvirt.krpc.kcli_pb2.profile.disks}




Field profile.disks

    
##### Variable `flavor` {#kvirt.krpc.kcli_pb2.profile.flavor}




Field profile.flavor

    
##### Variable `image` {#kvirt.krpc.kcli_pb2.profile.image}




Field profile.image

    
##### Variable `name` {#kvirt.krpc.kcli_pb2.profile.name}




Field profile.name

    
##### Variable `nested` {#kvirt.krpc.kcli_pb2.profile.nested}




Field profile.nested

    
##### Variable `nets` {#kvirt.krpc.kcli_pb2.profile.nets}




Field profile.nets

    
##### Variable `pool` {#kvirt.krpc.kcli_pb2.profile.pool}




Field profile.pool

    
##### Variable `reservedns` {#kvirt.krpc.kcli_pb2.profile.reservedns}




Field profile.reservedns

    
##### Variable `reservehost` {#kvirt.krpc.kcli_pb2.profile.reservehost}




Field profile.reservehost



    
### Class `profileslist` {#kvirt.krpc.kcli_pb2.profileslist}




>     class profileslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.profileslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `profiles` {#kvirt.krpc.kcli_pb2.profileslist.profiles}




Field profileslist.profiles



    
### Class `repo` {#kvirt.krpc.kcli_pb2.repo}




>     class repo(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.repo.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `repo` {#kvirt.krpc.kcli_pb2.repo.repo}




Field repo.repo

    
##### Variable `url` {#kvirt.krpc.kcli_pb2.repo.url}




Field repo.url



    
### Class `reposlist` {#kvirt.krpc.kcli_pb2.reposlist}




>     class reposlist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.reposlist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `repos` {#kvirt.krpc.kcli_pb2.reposlist.repos}




Field reposlist.repos



    
### Class `result` {#kvirt.krpc.kcli_pb2.result}




>     class result(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.result.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `deletedvm` {#kvirt.krpc.kcli_pb2.result.deletedvm}




Field result.deletedvm

    
##### Variable `reason` {#kvirt.krpc.kcli_pb2.result.reason}




Field result.reason

    
##### Variable `result` {#kvirt.krpc.kcli_pb2.result.result}




Field result.result

    
##### Variable `vm` {#kvirt.krpc.kcli_pb2.result.vm}




Field result.vm



    
### Class `scpdetails` {#kvirt.krpc.kcli_pb2.scpdetails}




>     class scpdetails(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.scpdetails.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `destination` {#kvirt.krpc.kcli_pb2.scpdetails.destination}




Field scpdetails.destination

    
##### Variable `download` {#kvirt.krpc.kcli_pb2.scpdetails.download}




Field scpdetails.download

    
##### Variable `name` {#kvirt.krpc.kcli_pb2.scpdetails.name}




Field scpdetails.name

    
##### Variable `recursive` {#kvirt.krpc.kcli_pb2.scpdetails.recursive}




Field scpdetails.recursive

    
##### Variable `source` {#kvirt.krpc.kcli_pb2.scpdetails.source}




Field scpdetails.source

    
##### Variable `user` {#kvirt.krpc.kcli_pb2.scpdetails.user}




Field scpdetails.user



    
### Class `snapshot` {#kvirt.krpc.kcli_pb2.snapshot}




>     class snapshot(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.snapshot.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `current` {#kvirt.krpc.kcli_pb2.snapshot.current}




Field snapshot.current

    
##### Variable `snapshot` {#kvirt.krpc.kcli_pb2.snapshot.snapshot}




Field snapshot.snapshot



    
### Class `sshcmd` {#kvirt.krpc.kcli_pb2.sshcmd}




>     class sshcmd(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.sshcmd.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `sshcmd` {#kvirt.krpc.kcli_pb2.sshcmd.sshcmd}




Field sshcmd.sshcmd



    
### Class `subnet` {#kvirt.krpc.kcli_pb2.subnet}




>     class subnet(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.subnet.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `az` {#kvirt.krpc.kcli_pb2.subnet.az}




Field subnet.az

    
##### Variable `cidr` {#kvirt.krpc.kcli_pb2.subnet.cidr}




Field subnet.cidr

    
##### Variable `network` {#kvirt.krpc.kcli_pb2.subnet.network}




Field subnet.network

    
##### Variable `subnet` {#kvirt.krpc.kcli_pb2.subnet.subnet}




Field subnet.subnet



    
### Class `subnetslist` {#kvirt.krpc.kcli_pb2.subnetslist}




>     class subnetslist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.subnetslist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `subnets` {#kvirt.krpc.kcli_pb2.subnetslist.subnets}




Field subnetslist.subnets



    
### Class `version` {#kvirt.krpc.kcli_pb2.version}




>     class version(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.version.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `git_version` {#kvirt.krpc.kcli_pb2.version.git_version}




Field version.git_version

    
##### Variable `version` {#kvirt.krpc.kcli_pb2.version.version}




Field version.version



    
### Class `vm` {#kvirt.krpc.kcli_pb2.vm}




>     class vm(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.vm.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `D` {#kvirt.krpc.kcli_pb2.vm.D}




Field vm.D

    
##### Variable `X` {#kvirt.krpc.kcli_pb2.vm.X}




Field vm.X

    
##### Variable `Y` {#kvirt.krpc.kcli_pb2.vm.Y}




Field vm.Y

    
##### Variable `cmd` {#kvirt.krpc.kcli_pb2.vm.cmd}




Field vm.cmd

    
##### Variable `debug` {#kvirt.krpc.kcli_pb2.vm.debug}




Field vm.debug

    
##### Variable `l` {#kvirt.krpc.kcli_pb2.vm.l}




Field vm.l

    
##### Variable `name` {#kvirt.krpc.kcli_pb2.vm.name}




Field vm.name

    
##### Variable `r` {#kvirt.krpc.kcli_pb2.vm.r}




Field vm.r

    
##### Variable `snapshots` {#kvirt.krpc.kcli_pb2.vm.snapshots}




Field vm.snapshots

    
##### Variable `user` {#kvirt.krpc.kcli_pb2.vm.user}




Field vm.user



    
### Class `vmfile` {#kvirt.krpc.kcli_pb2.vmfile}




>     class vmfile(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.vmfile.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `content` {#kvirt.krpc.kcli_pb2.vmfile.content}




Field vmfile.content

    
##### Variable `origin` {#kvirt.krpc.kcli_pb2.vmfile.origin}




Field vmfile.origin



    
### Class `vminfo` {#kvirt.krpc.kcli_pb2.vminfo}




>     class vminfo(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.vminfo.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `autostart` {#kvirt.krpc.kcli_pb2.vminfo.autostart}




Field vminfo.autostart

    
##### Variable `az` {#kvirt.krpc.kcli_pb2.vminfo.az}




Field vminfo.az

    
##### Variable `cpus` {#kvirt.krpc.kcli_pb2.vminfo.cpus}




Field vminfo.cpus

    
##### Variable `creationdate` {#kvirt.krpc.kcli_pb2.vminfo.creationdate}




Field vminfo.creationdate

    
##### Variable `debug` {#kvirt.krpc.kcli_pb2.vminfo.debug}




Field vminfo.debug

    
##### Variable `disks` {#kvirt.krpc.kcli_pb2.vminfo.disks}




Field vminfo.disks

    
##### Variable `error` {#kvirt.krpc.kcli_pb2.vminfo.error}




Field vminfo.error

    
##### Variable `flavor` {#kvirt.krpc.kcli_pb2.vminfo.flavor}




Field vminfo.flavor

    
##### Variable `host` {#kvirt.krpc.kcli_pb2.vminfo.host}




Field vminfo.host

    
##### Variable `image` {#kvirt.krpc.kcli_pb2.vminfo.image}




Field vminfo.image

    
##### Variable `instanceid` {#kvirt.krpc.kcli_pb2.vminfo.instanceid}




Field vminfo.instanceid

    
##### Variable `ip` {#kvirt.krpc.kcli_pb2.vminfo.ip}




Field vminfo.ip

    
##### Variable `kube` {#kvirt.krpc.kcli_pb2.vminfo.kube}




Field vminfo.kube

    
##### Variable `kubetype` {#kvirt.krpc.kcli_pb2.vminfo.kubetype}




Field vminfo.kubetype

    
##### Variable `loadbalancer` {#kvirt.krpc.kcli_pb2.vminfo.loadbalancer}




Field vminfo.loadbalancer

    
##### Variable `memory` {#kvirt.krpc.kcli_pb2.vminfo.memory}




Field vminfo.memory

    
##### Variable `name` {#kvirt.krpc.kcli_pb2.vminfo.name}




Field vminfo.name

    
##### Variable `namespace` {#kvirt.krpc.kcli_pb2.vminfo.namespace}




Field vminfo.namespace

    
##### Variable `nets` {#kvirt.krpc.kcli_pb2.vminfo.nets}




Field vminfo.nets

    
##### Variable `nodeport` {#kvirt.krpc.kcli_pb2.vminfo.nodeport}




Field vminfo.nodeport

    
##### Variable `owner` {#kvirt.krpc.kcli_pb2.vminfo.owner}




Field vminfo.owner

    
##### Variable `plan` {#kvirt.krpc.kcli_pb2.vminfo.plan}




Field vminfo.plan

    
##### Variable `privateip` {#kvirt.krpc.kcli_pb2.vminfo.privateip}




Field vminfo.privateip

    
##### Variable `profile` {#kvirt.krpc.kcli_pb2.vminfo.profile}




Field vminfo.profile

    
##### Variable `snapshots` {#kvirt.krpc.kcli_pb2.vminfo.snapshots}




Field vminfo.snapshots

    
##### Variable `status` {#kvirt.krpc.kcli_pb2.vminfo.status}




Field vminfo.status

    
##### Variable `tags` {#kvirt.krpc.kcli_pb2.vminfo.tags}




Field vminfo.tags

    
##### Variable `user` {#kvirt.krpc.kcli_pb2.vminfo.user}




Field vminfo.user



    
### Class `vmlist` {#kvirt.krpc.kcli_pb2.vmlist}




>     class vmlist(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.vmlist.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `vms` {#kvirt.krpc.kcli_pb2.vmlist.vms}




Field vmlist.vms



    
### Class `vmprofile` {#kvirt.krpc.kcli_pb2.vmprofile}




>     class vmprofile(
>         *args,
>         **kwargs
>     )


A ProtocolMessage


    
#### Ancestors (in MRO)

* [google.protobuf.pyext._message.CMessage](#google.protobuf.pyext._message.CMessage)
* [google.protobuf.message.Message](#google.protobuf.message.Message)



    
#### Class variables


    
##### Variable `DESCRIPTOR` {#kvirt.krpc.kcli_pb2.vmprofile.DESCRIPTOR}







    
#### Instance variables


    
##### Variable `customprofile` {#kvirt.krpc.kcli_pb2.vmprofile.customprofile}




Field vmprofile.customprofile

    
##### Variable `ignitionfile` {#kvirt.krpc.kcli_pb2.vmprofile.ignitionfile}




Field vmprofile.ignitionfile

    
##### Variable `image` {#kvirt.krpc.kcli_pb2.vmprofile.image}




Field vmprofile.image

    
##### Variable `name` {#kvirt.krpc.kcli_pb2.vmprofile.name}




Field vmprofile.name

    
##### Variable `overrides` {#kvirt.krpc.kcli_pb2.vmprofile.overrides}




Field vmprofile.overrides

    
##### Variable `profile` {#kvirt.krpc.kcli_pb2.vmprofile.profile}




Field vmprofile.profile

    
##### Variable `vmfiles` {#kvirt.krpc.kcli_pb2.vmprofile.vmfiles}




Field vmprofile.vmfiles

    
##### Variable `wait` {#kvirt.krpc.kcli_pb2.vmprofile.wait}




Field vmprofile.wait





    
# Module `kvirt.krpc.kcli_pb2_grpc` {#kvirt.krpc.kcli_pb2_grpc}






    
## Functions


    
### Function `add_KcliServicer_to_server` {#kvirt.krpc.kcli_pb2_grpc.add_KcliServicer_to_server}




>     def add_KcliServicer_to_server(
>         servicer,
>         server
>     )




    
### Function `add_KconfigServicer_to_server` {#kvirt.krpc.kcli_pb2_grpc.add_KconfigServicer_to_server}




>     def add_KconfigServicer_to_server(
>         servicer,
>         server
>     )





    
## Classes


    
### Class `Kcli` {#kvirt.krpc.kcli_pb2_grpc.Kcli}




>     class Kcli


Missing associated documentation comment in .proto file






    
#### Static methods


    
##### `Method console` {#kvirt.krpc.kcli_pb2_grpc.Kcli.console}




>     def console(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method create_network` {#kvirt.krpc.kcli_pb2_grpc.Kcli.create_network}




>     def create_network(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method create_pool` {#kvirt.krpc.kcli_pb2_grpc.Kcli.create_pool}




>     def create_pool(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete` {#kvirt.krpc.kcli_pb2_grpc.Kcli.delete}




>     def delete(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_image` {#kvirt.krpc.kcli_pb2_grpc.Kcli.delete_image}




>     def delete_image(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_network` {#kvirt.krpc.kcli_pb2_grpc.Kcli.delete_network}




>     def delete_network(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_pool` {#kvirt.krpc.kcli_pb2_grpc.Kcli.delete_pool}




>     def delete_pool(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method get_lastvm` {#kvirt.krpc.kcli_pb2_grpc.Kcli.get_lastvm}




>     def get_lastvm(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method info` {#kvirt.krpc.kcli_pb2_grpc.Kcli.info}




>     def info(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list}




>     def list(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_disks` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list_disks}




>     def list_disks(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_flavors` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list_flavors}




>     def list_flavors(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_images` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list_images}




>     def list_images(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_isos` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list_isos}




>     def list_isos(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_networks` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list_networks}




>     def list_networks(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_pools` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list_pools}




>     def list_pools(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_subnets` {#kvirt.krpc.kcli_pb2_grpc.Kcli.list_subnets}




>     def list_subnets(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method restart` {#kvirt.krpc.kcli_pb2_grpc.Kcli.restart}




>     def restart(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method scp` {#kvirt.krpc.kcli_pb2_grpc.Kcli.scp}




>     def scp(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method serial_console` {#kvirt.krpc.kcli_pb2_grpc.Kcli.serial_console}




>     def serial_console(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method ssh` {#kvirt.krpc.kcli_pb2_grpc.Kcli.ssh}




>     def ssh(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method start` {#kvirt.krpc.kcli_pb2_grpc.Kcli.start}




>     def start(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method stop` {#kvirt.krpc.kcli_pb2_grpc.Kcli.stop}




>     def stop(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )





    
### Class `KcliServicer` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer}




>     class KcliServicer


Missing associated documentation comment in .proto file



    
#### Descendants

* [kvirt.krpc.server.KcliServicer](#kvirt.krpc.server.KcliServicer)





    
#### Methods


    
##### Method `console` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.console}




>     def console(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `create_network` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.create_network}




>     def create_network(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `create_pool` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.create_pool}




>     def create_pool(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.delete}




>     def delete(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_image` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.delete_image}




>     def delete_image(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_network` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.delete_network}




>     def delete_network(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_pool` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.delete_pool}




>     def delete_pool(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `get_lastvm` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.get_lastvm}




>     def get_lastvm(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `info` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.info}




>     def info(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list}




>     def list(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_disks` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list_disks}




>     def list_disks(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_flavors` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list_flavors}




>     def list_flavors(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_images` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list_images}




>     def list_images(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_isos` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list_isos}




>     def list_isos(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_networks` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list_networks}




>     def list_networks(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_pools` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list_pools}




>     def list_pools(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_subnets` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.list_subnets}




>     def list_subnets(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `restart` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.restart}




>     def restart(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `scp` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.scp}




>     def scp(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `serial_console` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.serial_console}




>     def serial_console(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `ssh` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.ssh}




>     def ssh(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `start` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.start}




>     def start(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `stop` {#kvirt.krpc.kcli_pb2_grpc.KcliServicer.stop}




>     def stop(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
### Class `KcliStub` {#kvirt.krpc.kcli_pb2_grpc.KcliStub}




>     class KcliStub(
>         channel
>     )


Missing associated documentation comment in .proto file

Constructor.


Args
-----=
**```channel```**
:   A grpc.Channel.









    
### Class `Kconfig` {#kvirt.krpc.kcli_pb2_grpc.Kconfig}




>     class Kconfig


Missing associated documentation comment in .proto file






    
#### Static methods


    
##### `Method autostart_plan` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.autostart_plan}




>     def autostart_plan(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method create_host` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.create_host}




>     def create_host(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method create_vm` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.create_vm}




>     def create_vm(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_container` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.delete_container}




>     def delete_container(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_host` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.delete_host}




>     def delete_host(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_kube` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.delete_kube}




>     def delete_kube(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_lb` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.delete_lb}




>     def delete_lb(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_plan` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.delete_plan}




>     def delete_plan(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_profile` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.delete_profile}




>     def delete_profile(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method delete_repo` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.delete_repo}




>     def delete_repo(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method get_config` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.get_config}




>     def get_config(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method get_version` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.get_version}




>     def get_version(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_container_images` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_container_images}




>     def list_container_images(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_containers` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_containers}




>     def list_containers(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_hosts` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_hosts}




>     def list_hosts(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_keywords` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_keywords}




>     def list_keywords(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_kubes` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_kubes}




>     def list_kubes(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_lbs` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_lbs}




>     def list_lbs(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_plans` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_plans}




>     def list_plans(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_products` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_products}




>     def list_products(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_profiles` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_profiles}




>     def list_profiles(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method list_repos` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.list_repos}




>     def list_repos(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method noautostart_plan` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.noautostart_plan}




>     def noautostart_plan(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method restart_container` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.restart_container}




>     def restart_container(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method start_container` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.start_container}




>     def start_container(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method start_plan` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.start_plan}




>     def start_plan(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method stop_container` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.stop_container}




>     def stop_container(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method stop_plan` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.stop_plan}




>     def stop_plan(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )




    
##### `Method switch_host` {#kvirt.krpc.kcli_pb2_grpc.Kconfig.switch_host}




>     def switch_host(
>         request,
>         target,
>         options=(),
>         channel_credentials=None,
>         call_credentials=None,
>         compression=None,
>         wait_for_ready=None,
>         timeout=None,
>         metadata=None
>     )





    
### Class `KconfigServicer` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer}




>     class KconfigServicer


Missing associated documentation comment in .proto file



    
#### Descendants

* [kvirt.krpc.server.KconfigServicer](#kvirt.krpc.server.KconfigServicer)





    
#### Methods


    
##### Method `autostart_plan` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.autostart_plan}




>     def autostart_plan(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `create_host` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.create_host}




>     def create_host(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `create_vm` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.create_vm}




>     def create_vm(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_container` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.delete_container}




>     def delete_container(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_host` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.delete_host}




>     def delete_host(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_kube` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.delete_kube}




>     def delete_kube(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_lb` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.delete_lb}




>     def delete_lb(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_plan` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.delete_plan}




>     def delete_plan(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_profile` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.delete_profile}




>     def delete_profile(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `delete_repo` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.delete_repo}




>     def delete_repo(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `get_config` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.get_config}




>     def get_config(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `get_version` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.get_version}




>     def get_version(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_container_images` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_container_images}




>     def list_container_images(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_containers` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_containers}




>     def list_containers(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_hosts` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_hosts}




>     def list_hosts(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_keywords` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_keywords}




>     def list_keywords(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_kubes` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_kubes}




>     def list_kubes(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_lbs` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_lbs}




>     def list_lbs(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_plans` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_plans}




>     def list_plans(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_products` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_products}




>     def list_products(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_profiles` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_profiles}




>     def list_profiles(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `list_repos` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.list_repos}




>     def list_repos(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `noautostart_plan` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.noautostart_plan}




>     def noautostart_plan(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `restart_container` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.restart_container}




>     def restart_container(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `start_container` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.start_container}




>     def start_container(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `start_plan` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.start_plan}




>     def start_plan(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `stop_container` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.stop_container}




>     def stop_container(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `stop_plan` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.stop_plan}




>     def stop_plan(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
##### Method `switch_host` {#kvirt.krpc.kcli_pb2_grpc.KconfigServicer.switch_host}




>     def switch_host(
>         self,
>         request,
>         context
>     )


Missing associated documentation comment in .proto file

    
### Class `KconfigStub` {#kvirt.krpc.kcli_pb2_grpc.KconfigStub}




>     class KconfigStub(
>         channel
>     )


Missing associated documentation comment in .proto file

Constructor.


Args
-----=
**```channel```**
:   A grpc.Channel.











    
# Module `kvirt.krpc.server` {#kvirt.krpc.server}






    
## Functions


    
### Function `main` {#kvirt.krpc.server.main}




>     def main()





    
## Classes


    
### Class `KcliServicer` {#kvirt.krpc.server.KcliServicer}




>     class KcliServicer


Missing associated documentation comment in .proto file


    
#### Ancestors (in MRO)

* [kvirt.krpc.kcli_pb2_grpc.KcliServicer](#kvirt.krpc.kcli_pb2_grpc.KcliServicer)






    
### Class `KconfigServicer` {#kvirt.krpc.server.KconfigServicer}




>     class KconfigServicer


Missing associated documentation comment in .proto file


    
#### Ancestors (in MRO)

* [kvirt.krpc.kcli_pb2_grpc.KconfigServicer](#kvirt.krpc.kcli_pb2_grpc.KconfigServicer)








    
# Module `kvirt.kubeadm` {#kvirt.kubeadm}






    
## Functions


    
### Function `create` {#kvirt.kubeadm.create}




>     def create(
>         config,
>         plandir,
>         cluster,
>         overrides
>     )




    
### Function `scale` {#kvirt.kubeadm.scale}




>     def scale(
>         config,
>         plandir,
>         cluster,
>         overrides
>     )







    
# Module `kvirt.kubecommon` {#kvirt.kubecommon}

Kubecommon Base Class





    
## Classes


    
### Class `Kubecommon` {#kvirt.kubecommon.Kubecommon}




>     class Kubecommon(
>         token=None,
>         ca_file=None,
>         context=None,
>         host='127.0.0.1',
>         port=443,
>         user='root',
>         debug=False,
>         namespace=None,
>         readwritemany=False
>     )






    
#### Descendants

* [kvirt.providers.kubevirt.Kubevirt](#kvirt.providers.kubevirt.Kubevirt)







    
# Module `kvirt.kubernetes` {#kvirt.kubernetes}

kubernetes utilites





    
## Classes


    
### Class `Kubernetes` {#kvirt.kubernetes.Kubernetes}




>     class Kubernetes(
>         host='127.0.0.1',
>         user='root',
>         port=443,
>         token=None,
>         ca_file=None,
>         context=None,
>         namespace='default',
>         readwritemany=False,
>         debug=False,
>         insecure=False
>     )










    
#### Methods


    
##### Method `console_container` {#kvirt.kubernetes.Kubernetes.console_container}




>     def console_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:

    
##### Method `create_container` {#kvirt.kubernetes.Kubernetes.create_container}




>     def create_container(
>         self,
>         name,
>         image,
>         nets=None,
>         cmd=[],
>         ports=[],
>         volumes=[],
>         environment=[],
>         label=None,
>         overrides={}
>     )


:param self:
:param name:
:param image:
:param nets:
:param cmds:
:param ports:
:param volumes:
:param environment:
:param label:
:param overrides:
:return:

    
##### Method `delete_container` {#kvirt.kubernetes.Kubernetes.delete_container}




>     def delete_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:

    
##### Method `exists_container` {#kvirt.kubernetes.Kubernetes.exists_container}




>     def exists_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:

    
##### Method `list_containers` {#kvirt.kubernetes.Kubernetes.list_containers}




>     def list_containers(
>         self
>     )


:param self:
:return:

    
##### Method `list_images` {#kvirt.kubernetes.Kubernetes.list_images}




>     def list_images(
>         self
>     )


:param self:
:return:

    
##### Method `start_container` {#kvirt.kubernetes.Kubernetes.start_container}




>     def start_container(
>         self,
>         name
>     )


:param self:
:param name:

:return:

    
##### Method `stop_container` {#kvirt.kubernetes.Kubernetes.stop_container}




>     def stop_container(
>         self,
>         name
>     )


:param self:
:param name:
:return:



    
# Module `kvirt.nameutils` {#kvirt.nameutils}

provide random names




    
## Functions


    
### Function `get_random_name` {#kvirt.nameutils.get_random_name}




>     def get_random_name(
>         sep='-'
>     )


:param sep:
:return:

    
### Function `random_ip` {#kvirt.nameutils.random_ip}




>     def random_ip()


:return:




    
# Module `kvirt.openshift` {#kvirt.openshift}




    
## Sub-modules

* [kvirt.openshift.calico](#kvirt.openshift.calico)



    
## Functions


    
### Function `create` {#kvirt.openshift.create}




>     def create(
>         config,
>         plandir,
>         cluster,
>         overrides
>     )




    
### Function `gather_dhcp` {#kvirt.openshift.gather_dhcp}




>     def gather_dhcp(
>         data,
>         platform
>     )




    
### Function `get_ci_installer` {#kvirt.openshift.get_ci_installer}




>     def get_ci_installer(
>         pull_secret,
>         tag=None,
>         macosx=False,
>         upstream=False
>     )




    
### Function `get_downstream_installer` {#kvirt.openshift.get_downstream_installer}




>     def get_downstream_installer(
>         nightly=False,
>         macosx=False,
>         tag=None
>     )




    
### Function `get_installer_version` {#kvirt.openshift.get_installer_version}




>     def get_installer_version()




    
### Function `get_minimal_rhcos` {#kvirt.openshift.get_minimal_rhcos}




>     def get_minimal_rhcos()




    
### Function `get_rhcos_openstack_url` {#kvirt.openshift.get_rhcos_openstack_url}




>     def get_rhcos_openstack_url()




    
### Function `get_upstream_installer` {#kvirt.openshift.get_upstream_installer}




>     def get_upstream_installer(
>         macosx=False,
>         tag=None
>     )




    
### Function `scale` {#kvirt.openshift.scale}




>     def scale(
>         config,
>         plandir,
>         cluster,
>         overrides
>     )







    
# Module `kvirt.openshift.calico` {#kvirt.openshift.calico}









    
# Module `kvirt.providers` {#kvirt.providers}




    
## Sub-modules

* [kvirt.providers.aws](#kvirt.providers.aws)
* [kvirt.providers.gcp](#kvirt.providers.gcp)
* [kvirt.providers.kubevirt](#kvirt.providers.kubevirt)
* [kvirt.providers.kvm](#kvirt.providers.kvm)
* [kvirt.providers.openstack](#kvirt.providers.openstack)
* [kvirt.providers.ovirt](#kvirt.providers.ovirt)
* [kvirt.providers.packet](#kvirt.providers.packet)
* [kvirt.providers.sampleprovider](#kvirt.providers.sampleprovider)
* [kvirt.providers.vsphere](#kvirt.providers.vsphere)






    
# Module `kvirt.providers.aws` {#kvirt.providers.aws}

Aws Provider Class





    
## Classes


    
### Class `Kaws` {#kvirt.providers.aws.Kaws}




>     class Kaws(
>         access_key_id=None,
>         access_key_secret=None,
>         debug=False,
>         region='eu-west-3',
>         keypair=None
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.aws.Kaws.add_disk}




>     def add_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )




    
##### Method `add_image` {#kvirt.providers.aws.Kaws.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )




    
##### Method `add_nic` {#kvirt.providers.aws.Kaws.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )




    
##### Method `clone` {#kvirt.providers.aws.Kaws.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )




    
##### Method `close` {#kvirt.providers.aws.Kaws.close}




>     def close(
>         self
>     )




    
##### Method `console` {#kvirt.providers.aws.Kaws.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )




    
##### Method `create` {#kvirt.providers.aws.Kaws.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='Westmere',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         alias=[],
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         placement=[],
>         autostart=False,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )




    
##### Method `create_disk` {#kvirt.providers.aws.Kaws.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )




    
##### Method `create_loadbalancer` {#kvirt.providers.aws.Kaws.create_loadbalancer}




>     def create_loadbalancer(
>         self,
>         name,
>         ports=[],
>         checkpath='/index.html',
>         vms=[],
>         domain=None,
>         checkport=80,
>         alias=[],
>         internal=False
>     )




    
##### Method `create_network` {#kvirt.providers.aws.Kaws.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )




    
##### Method `create_pool` {#kvirt.providers.aws.Kaws.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )




    
##### Method `delete` {#kvirt.providers.aws.Kaws.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )




    
##### Method `delete_disk` {#kvirt.providers.aws.Kaws.delete_disk}




>     def delete_disk(
>         self,
>         name=None,
>         diskname=None,
>         pool=None
>     )




    
##### Method `delete_dns` {#kvirt.providers.aws.Kaws.delete_dns}




>     def delete_dns(
>         self,
>         name,
>         domain,
>         instanceid=None
>     )




    
##### Method `delete_image` {#kvirt.providers.aws.Kaws.delete_image}




>     def delete_image(
>         self,
>         image
>     )




    
##### Method `delete_loadbalancer` {#kvirt.providers.aws.Kaws.delete_loadbalancer}




>     def delete_loadbalancer(
>         self,
>         name
>     )




    
##### Method `delete_network` {#kvirt.providers.aws.Kaws.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )




    
##### Method `delete_nic` {#kvirt.providers.aws.Kaws.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )




    
##### Method `delete_pool` {#kvirt.providers.aws.Kaws.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )




    
##### Method `disk_exists` {#kvirt.providers.aws.Kaws.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )




    
##### Method `dnsinfo` {#kvirt.providers.aws.Kaws.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )




    
##### Method `exists` {#kvirt.providers.aws.Kaws.exists}




>     def exists(
>         self,
>         name
>     )




    
##### Method `export` {#kvirt.providers.aws.Kaws.export}




>     def export(
>         self,
>         name,
>         image=None
>     )




    
##### Method `flavors` {#kvirt.providers.aws.Kaws.flavors}




>     def flavors(
>         self
>     )




    
##### Method `get_id` {#kvirt.providers.aws.Kaws.get_id}




>     def get_id(
>         self,
>         name
>     )




    
##### Method `get_pool_path` {#kvirt.providers.aws.Kaws.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )




    
##### Method `get_security_group_id` {#kvirt.providers.aws.Kaws.get_security_group_id}




>     def get_security_group_id(
>         self,
>         name,
>         vpcid
>     )




    
##### Method `get_security_groups` {#kvirt.providers.aws.Kaws.get_security_groups}




>     def get_security_groups(
>         self,
>         name
>     )




    
##### Method `info` {#kvirt.providers.aws.Kaws.info}




>     def info(
>         self,
>         name,
>         vm=None,
>         debug=False
>     )




    
##### Method `internalip` {#kvirt.providers.aws.Kaws.internalip}




>     def internalip(
>         self,
>         name
>     )




    
##### Method `ip` {#kvirt.providers.aws.Kaws.ip}




>     def ip(
>         self,
>         name
>     )




    
##### Method `list` {#kvirt.providers.aws.Kaws.list}




>     def list(
>         self
>     )




    
##### Method `list_disks` {#kvirt.providers.aws.Kaws.list_disks}




>     def list_disks(
>         self
>     )




    
##### Method `list_dns` {#kvirt.providers.aws.Kaws.list_dns}




>     def list_dns(
>         self,
>         domain
>     )




    
##### Method `list_loadbalancers` {#kvirt.providers.aws.Kaws.list_loadbalancers}




>     def list_loadbalancers(
>         self
>     )




    
##### Method `list_networks` {#kvirt.providers.aws.Kaws.list_networks}




>     def list_networks(
>         self
>     )




    
##### Method `list_pools` {#kvirt.providers.aws.Kaws.list_pools}




>     def list_pools(
>         self
>     )




    
##### Method `list_subnets` {#kvirt.providers.aws.Kaws.list_subnets}




>     def list_subnets(
>         self
>     )




    
##### Method `net_exists` {#kvirt.providers.aws.Kaws.net_exists}




>     def net_exists(
>         self,
>         name
>     )




    
##### Method `network_ports` {#kvirt.providers.aws.Kaws.network_ports}




>     def network_ports(
>         self,
>         name
>     )




    
##### Method `report` {#kvirt.providers.aws.Kaws.report}




>     def report(
>         self
>     )




    
##### Method `reserve_dns` {#kvirt.providers.aws.Kaws.reserve_dns}




>     def reserve_dns(
>         self,
>         name,
>         nets=[],
>         domain=None,
>         ip=None,
>         alias=[],
>         force=False,
>         primary=False,
>         instanceid=None
>     )




    
##### Method `restart` {#kvirt.providers.aws.Kaws.restart}




>     def restart(
>         self,
>         name
>     )




    
##### Method `serialconsole` {#kvirt.providers.aws.Kaws.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )




    
##### Method `snapshot` {#kvirt.providers.aws.Kaws.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )




    
##### Method `start` {#kvirt.providers.aws.Kaws.start}




>     def start(
>         self,
>         name
>     )




    
##### Method `status` {#kvirt.providers.aws.Kaws.status}




>     def status(
>         self,
>         name
>     )




    
##### Method `stop` {#kvirt.providers.aws.Kaws.stop}




>     def stop(
>         self,
>         name
>     )




    
##### Method `update_cpus` {#kvirt.providers.aws.Kaws.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )




    
##### Method `update_flavor` {#kvirt.providers.aws.Kaws.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )




    
##### Method `update_information` {#kvirt.providers.aws.Kaws.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )




    
##### Method `update_iso` {#kvirt.providers.aws.Kaws.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )




    
##### Method `update_memory` {#kvirt.providers.aws.Kaws.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )




    
##### Method `update_metadata` {#kvirt.providers.aws.Kaws.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )




    
##### Method `update_start` {#kvirt.providers.aws.Kaws.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )




    
##### Method `vm_ports` {#kvirt.providers.aws.Kaws.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )




    
##### Method `volumes` {#kvirt.providers.aws.Kaws.volumes}




>     def volumes(
>         self,
>         iso=False
>     )






    
# Module `kvirt.providers.gcp` {#kvirt.providers.gcp}

Gcp Provider Class





    
## Classes


    
### Class `Kgcp` {#kvirt.providers.gcp.Kgcp}




>     class Kgcp(
>         debug=False,
>         project='kubevirt-button',
>         zone='europe-west1-b',
>         region='europe-west1'
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.gcp.Kgcp.add_disk}




>     def add_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )




    
##### Method `add_image` {#kvirt.providers.gcp.Kgcp.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )




    
##### Method `add_nic` {#kvirt.providers.gcp.Kgcp.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )




    
##### Method `clone` {#kvirt.providers.gcp.Kgcp.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )




    
##### Method `close` {#kvirt.providers.gcp.Kgcp.close}




>     def close(
>         self
>     )




    
##### Method `console` {#kvirt.providers.gcp.Kgcp.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )




    
##### Method `create` {#kvirt.providers.gcp.Kgcp.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='Westmere',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         alias=[],
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         placement=[],
>         autostart=False,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )




    
##### Method `create_disk` {#kvirt.providers.gcp.Kgcp.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )




    
##### Method `create_loadbalancer` {#kvirt.providers.gcp.Kgcp.create_loadbalancer}




>     def create_loadbalancer(
>         self,
>         name,
>         ports=[],
>         checkpath='/index.html',
>         vms=[],
>         domain=None,
>         checkport=80,
>         alias=[],
>         internal=False
>     )




    
##### Method `create_network` {#kvirt.providers.gcp.Kgcp.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )




    
##### Method `create_pool` {#kvirt.providers.gcp.Kgcp.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )




    
##### Method `delete` {#kvirt.providers.gcp.Kgcp.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )




    
##### Method `delete_disk` {#kvirt.providers.gcp.Kgcp.delete_disk}




>     def delete_disk(
>         self,
>         name=None,
>         diskname=None,
>         pool=None
>     )




    
##### Method `delete_dns` {#kvirt.providers.gcp.Kgcp.delete_dns}




>     def delete_dns(
>         self,
>         name,
>         domain
>     )




    
##### Method `delete_image` {#kvirt.providers.gcp.Kgcp.delete_image}




>     def delete_image(
>         self,
>         image
>     )




    
##### Method `delete_loadbalancer` {#kvirt.providers.gcp.Kgcp.delete_loadbalancer}




>     def delete_loadbalancer(
>         self,
>         name
>     )




    
##### Method `delete_network` {#kvirt.providers.gcp.Kgcp.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )




    
##### Method `delete_nic` {#kvirt.providers.gcp.Kgcp.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )




    
##### Method `delete_pool` {#kvirt.providers.gcp.Kgcp.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )




    
##### Method `disk_exists` {#kvirt.providers.gcp.Kgcp.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )




    
##### Method `dnsinfo` {#kvirt.providers.gcp.Kgcp.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )




    
##### Method `exists` {#kvirt.providers.gcp.Kgcp.exists}




>     def exists(
>         self,
>         name
>     )




    
##### Method `export` {#kvirt.providers.gcp.Kgcp.export}




>     def export(
>         self,
>         name,
>         image=None
>     )




    
##### Method `flavors` {#kvirt.providers.gcp.Kgcp.flavors}




>     def flavors(
>         self
>     )




    
##### Method `get_pool_path` {#kvirt.providers.gcp.Kgcp.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )




    
##### Method `info` {#kvirt.providers.gcp.Kgcp.info}




>     def info(
>         self,
>         name,
>         vm=None,
>         debug=False
>     )




    
##### Method `internalip` {#kvirt.providers.gcp.Kgcp.internalip}




>     def internalip(
>         self,
>         name
>     )




    
##### Method `ip` {#kvirt.providers.gcp.Kgcp.ip}




>     def ip(
>         self,
>         name
>     )




    
##### Method `list` {#kvirt.providers.gcp.Kgcp.list}




>     def list(
>         self
>     )




    
##### Method `list_disks` {#kvirt.providers.gcp.Kgcp.list_disks}




>     def list_disks(
>         self
>     )




    
##### Method `list_dns` {#kvirt.providers.gcp.Kgcp.list_dns}




>     def list_dns(
>         self,
>         domain
>     )




    
##### Method `list_loadbalancers` {#kvirt.providers.gcp.Kgcp.list_loadbalancers}




>     def list_loadbalancers(
>         self
>     )




    
##### Method `list_networks` {#kvirt.providers.gcp.Kgcp.list_networks}




>     def list_networks(
>         self
>     )




    
##### Method `list_pools` {#kvirt.providers.gcp.Kgcp.list_pools}




>     def list_pools(
>         self
>     )




    
##### Method `list_subnets` {#kvirt.providers.gcp.Kgcp.list_subnets}




>     def list_subnets(
>         self
>     )




    
##### Method `net_exists` {#kvirt.providers.gcp.Kgcp.net_exists}




>     def net_exists(
>         self,
>         name
>     )




    
##### Method `network_ports` {#kvirt.providers.gcp.Kgcp.network_ports}




>     def network_ports(
>         self,
>         name
>     )




    
##### Method `report` {#kvirt.providers.gcp.Kgcp.report}




>     def report(
>         self
>     )




    
##### Method `reserve_dns` {#kvirt.providers.gcp.Kgcp.reserve_dns}




>     def reserve_dns(
>         self,
>         name,
>         nets=[],
>         domain=None,
>         ip=None,
>         alias=[],
>         force=False,
>         primary=False
>     )




    
##### Method `restart` {#kvirt.providers.gcp.Kgcp.restart}




>     def restart(
>         self,
>         name
>     )




    
##### Method `serialconsole` {#kvirt.providers.gcp.Kgcp.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )




    
##### Method `snapshot` {#kvirt.providers.gcp.Kgcp.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )




    
##### Method `start` {#kvirt.providers.gcp.Kgcp.start}




>     def start(
>         self,
>         name
>     )




    
##### Method `status` {#kvirt.providers.gcp.Kgcp.status}




>     def status(
>         self,
>         name
>     )




    
##### Method `stop` {#kvirt.providers.gcp.Kgcp.stop}




>     def stop(
>         self,
>         name
>     )




    
##### Method `update_cpus` {#kvirt.providers.gcp.Kgcp.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )




    
##### Method `update_flavor` {#kvirt.providers.gcp.Kgcp.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )




    
##### Method `update_information` {#kvirt.providers.gcp.Kgcp.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )




    
##### Method `update_iso` {#kvirt.providers.gcp.Kgcp.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )




    
##### Method `update_memory` {#kvirt.providers.gcp.Kgcp.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )




    
##### Method `update_metadata` {#kvirt.providers.gcp.Kgcp.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )




    
##### Method `update_start` {#kvirt.providers.gcp.Kgcp.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )




    
##### Method `vm_ports` {#kvirt.providers.gcp.Kgcp.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )




    
##### Method `volumes` {#kvirt.providers.gcp.Kgcp.volumes}




>     def volumes(
>         self,
>         iso=False
>     )






    
# Module `kvirt.providers.kubevirt` {#kvirt.providers.kubevirt}

Kubevirt Provider Class





    
## Classes


    
### Class `Kubevirt` {#kvirt.providers.kubevirt.Kubevirt}




>     class Kubevirt(
>         token=None,
>         ca_file=None,
>         context=None,
>         multus=True,
>         host='127.0.0.1',
>         port=443,
>         user='root',
>         debug=False,
>         tags=None,
>         namespace=None,
>         cdi=False,
>         datavolumes=True,
>         readwritemany=False
>     )





    
#### Ancestors (in MRO)

* [kvirt.kubecommon.Kubecommon](#kvirt.kubecommon.Kubecommon)






    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.kubevirt.Kubevirt.add_disk}




>     def add_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )




    
##### Method `add_image` {#kvirt.providers.kubevirt.Kubevirt.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )




    
##### Method `add_nic` {#kvirt.providers.kubevirt.Kubevirt.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )




    
##### Method `check_pool` {#kvirt.providers.kubevirt.Kubevirt.check_pool}




>     def check_pool(
>         self,
>         pool
>     )




    
##### Method `clone` {#kvirt.providers.kubevirt.Kubevirt.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )




    
##### Method `close` {#kvirt.providers.kubevirt.Kubevirt.close}




>     def close(
>         self
>     )




    
##### Method `console` {#kvirt.providers.kubevirt.Kubevirt.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )




    
##### Method `copy_image` {#kvirt.providers.kubevirt.Kubevirt.copy_image}




>     def copy_image(
>         self,
>         pool,
>         ori,
>         dest,
>         size=1
>     )




    
##### Method `create` {#kvirt.providers.kubevirt.Kubevirt.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='host-model',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool=None,
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         alias=[],
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         placement=[],
>         autostart=False,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )




    
##### Method `create_disk` {#kvirt.providers.kubevirt.Kubevirt.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )




    
##### Method `create_network` {#kvirt.providers.kubevirt.Kubevirt.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )




    
##### Method `create_pool` {#kvirt.providers.kubevirt.Kubevirt.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )




    
##### Method `delete` {#kvirt.providers.kubevirt.Kubevirt.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )




    
##### Method `delete_disk` {#kvirt.providers.kubevirt.Kubevirt.delete_disk}




>     def delete_disk(
>         self,
>         name=None,
>         diskname=None,
>         pool=None
>     )




    
##### Method `delete_image` {#kvirt.providers.kubevirt.Kubevirt.delete_image}




>     def delete_image(
>         self,
>         image
>     )




    
##### Method `delete_network` {#kvirt.providers.kubevirt.Kubevirt.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )




    
##### Method `delete_nic` {#kvirt.providers.kubevirt.Kubevirt.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )




    
##### Method `delete_pool` {#kvirt.providers.kubevirt.Kubevirt.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )




    
##### Method `disk_exists` {#kvirt.providers.kubevirt.Kubevirt.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )




    
##### Method `dnsinfo` {#kvirt.providers.kubevirt.Kubevirt.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )




    
##### Method `exists` {#kvirt.providers.kubevirt.Kubevirt.exists}




>     def exists(
>         self,
>         name
>     )




    
##### Method `flavors` {#kvirt.providers.kubevirt.Kubevirt.flavors}




>     def flavors(
>         self
>     )




    
##### Method `get_image_name` {#kvirt.providers.kubevirt.Kubevirt.get_image_name}




>     def get_image_name(
>         self,
>         name
>     )




    
##### Method `get_pool_path` {#kvirt.providers.kubevirt.Kubevirt.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )




    
##### Method `import_completed` {#kvirt.providers.kubevirt.Kubevirt.import_completed}




>     def import_completed(
>         self,
>         volname,
>         namespace
>     )




    
##### Method `info` {#kvirt.providers.kubevirt.Kubevirt.info}




>     def info(
>         self,
>         name,
>         vm=None,
>         debug=False
>     )




    
##### Method `ip` {#kvirt.providers.kubevirt.Kubevirt.ip}




>     def ip(
>         self,
>         name
>     )




    
##### Method `list` {#kvirt.providers.kubevirt.Kubevirt.list}




>     def list(
>         self
>     )




    
##### Method `list_disks` {#kvirt.providers.kubevirt.Kubevirt.list_disks}




>     def list_disks(
>         self
>     )




    
##### Method `list_dns` {#kvirt.providers.kubevirt.Kubevirt.list_dns}




>     def list_dns(
>         self,
>         domain
>     )




    
##### Method `list_networks` {#kvirt.providers.kubevirt.Kubevirt.list_networks}




>     def list_networks(
>         self
>     )




    
##### Method `list_pools` {#kvirt.providers.kubevirt.Kubevirt.list_pools}




>     def list_pools(
>         self
>     )




    
##### Method `list_subnets` {#kvirt.providers.kubevirt.Kubevirt.list_subnets}




>     def list_subnets(
>         self
>     )




    
##### Method `net_exists` {#kvirt.providers.kubevirt.Kubevirt.net_exists}




>     def net_exists(
>         self,
>         name
>     )




    
##### Method `network_ports` {#kvirt.providers.kubevirt.Kubevirt.network_ports}




>     def network_ports(
>         self,
>         name
>     )




    
##### Method `pod_completed` {#kvirt.providers.kubevirt.Kubevirt.pod_completed}




>     def pod_completed(
>         self,
>         podname,
>         namespace
>     )




    
##### Method `prepare_pvc` {#kvirt.providers.kubevirt.Kubevirt.prepare_pvc}




>     def prepare_pvc(
>         self,
>         name,
>         size=1
>     )




    
##### Method `pvc_bound` {#kvirt.providers.kubevirt.Kubevirt.pvc_bound}




>     def pvc_bound(
>         self,
>         volname,
>         namespace
>     )




    
##### Method `report` {#kvirt.providers.kubevirt.Kubevirt.report}




>     def report(
>         self
>     )




    
##### Method `restart` {#kvirt.providers.kubevirt.Kubevirt.restart}




>     def restart(
>         self,
>         name
>     )




    
##### Method `serialconsole` {#kvirt.providers.kubevirt.Kubevirt.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )


:param name:
:return:

    
##### Method `snapshot` {#kvirt.providers.kubevirt.Kubevirt.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )




    
##### Method `start` {#kvirt.providers.kubevirt.Kubevirt.start}




>     def start(
>         self,
>         name
>     )




    
##### Method `status` {#kvirt.providers.kubevirt.Kubevirt.status}




>     def status(
>         self,
>         name
>     )




    
##### Method `stop` {#kvirt.providers.kubevirt.Kubevirt.stop}




>     def stop(
>         self,
>         name
>     )




    
##### Method `update_cpus` {#kvirt.providers.kubevirt.Kubevirt.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )




    
##### Method `update_flavor` {#kvirt.providers.kubevirt.Kubevirt.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )




    
##### Method `update_information` {#kvirt.providers.kubevirt.Kubevirt.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )




    
##### Method `update_iso` {#kvirt.providers.kubevirt.Kubevirt.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )




    
##### Method `update_memory` {#kvirt.providers.kubevirt.Kubevirt.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )




    
##### Method `update_metadata` {#kvirt.providers.kubevirt.Kubevirt.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )




    
##### Method `update_start` {#kvirt.providers.kubevirt.Kubevirt.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )




    
##### Method `vm_ports` {#kvirt.providers.kubevirt.Kubevirt.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )




    
##### Method `volumes` {#kvirt.providers.kubevirt.Kubevirt.volumes}




>     def volumes(
>         self,
>         iso=False
>     )






    
# Module `kvirt.providers.kvm` {#kvirt.providers.kvm}

Kvm Provider class




    
## Functions


    
### Function `libvirt_callback` {#kvirt.providers.kvm.libvirt_callback}




>     def libvirt_callback(
>         ignore,
>         err
>     )


:param ignore:
:param err:
:return:


    
## Classes


    
### Class `Kvirt` {#kvirt.providers.kvm.Kvirt}




>     class Kvirt(
>         host='127.0.0.1',
>         port=None,
>         user='root',
>         protocol='ssh',
>         url=None,
>         debug=False,
>         insecure=False,
>         session=False
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.kvm.Kvirt.add_disk}




>     def add_disk(
>         self,
>         name,
>         size=1,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )




    
##### Method `add_image` {#kvirt.providers.kvm.Kvirt.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         cmd=None,
>         name=None,
>         size=1
>     )




    
##### Method `add_image_to_deadpool` {#kvirt.providers.kvm.Kvirt.add_image_to_deadpool}




>     def add_image_to_deadpool(
>         self,
>         poolname,
>         pooltype,
>         poolpath,
>         shortimage,
>         thinpool=None
>     )




    
##### Method `add_nic` {#kvirt.providers.kvm.Kvirt.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )




    
##### Method `clone` {#kvirt.providers.kvm.Kvirt.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )


:param old:
:param new:
:param full:
:param start:

    
##### Method `close` {#kvirt.providers.kvm.Kvirt.close}




>     def close(
>         self
>     )




    
##### Method `console` {#kvirt.providers.kvm.Kvirt.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )




    
##### Method `create` {#kvirt.providers.kvm.Kvirt.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='kvirt',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='host-model',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         placement=[],
>         autostart=False,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )




    
##### Method `create_disk` {#kvirt.providers.kvm.Kvirt.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )




    
##### Method `create_network` {#kvirt.providers.kvm.Kvirt.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )




    
##### Method `create_pool` {#kvirt.providers.kvm.Kvirt.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )




    
##### Method `delete` {#kvirt.providers.kvm.Kvirt.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )




    
##### Method `delete_disk` {#kvirt.providers.kvm.Kvirt.delete_disk}




>     def delete_disk(
>         self,
>         name=None,
>         diskname=None,
>         pool=None
>     )




    
##### Method `delete_disk_by_name` {#kvirt.providers.kvm.Kvirt.delete_disk_by_name}




>     def delete_disk_by_name(
>         self,
>         name,
>         pool
>     )




    
##### Method `delete_dns` {#kvirt.providers.kvm.Kvirt.delete_dns}




>     def delete_dns(
>         self,
>         name,
>         domain
>     )




    
##### Method `delete_image` {#kvirt.providers.kvm.Kvirt.delete_image}




>     def delete_image(
>         self,
>         image
>     )




    
##### Method `delete_network` {#kvirt.providers.kvm.Kvirt.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )




    
##### Method `delete_nic` {#kvirt.providers.kvm.Kvirt.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )




    
##### Method `delete_pool` {#kvirt.providers.kvm.Kvirt.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )




    
##### Method `disk_exists` {#kvirt.providers.kvm.Kvirt.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )




    
##### Method `dnsinfo` {#kvirt.providers.kvm.Kvirt.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )




    
##### Method `exists` {#kvirt.providers.kvm.Kvirt.exists}




>     def exists(
>         self,
>         name
>     )




    
##### Method `export` {#kvirt.providers.kvm.Kvirt.export}




>     def export(
>         self,
>         name,
>         image=None
>     )




    
##### Method `flavors` {#kvirt.providers.kvm.Kvirt.flavors}




>     def flavors(
>         self
>     )




    
##### Method `get_pool_path` {#kvirt.providers.kvm.Kvirt.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )




    
##### Method `handler` {#kvirt.providers.kvm.Kvirt.handler}




>     def handler(
>         self,
>         stream,
>         data,
>         file_
>     )




    
##### Method `info` {#kvirt.providers.kvm.Kvirt.info}




>     def info(
>         self,
>         name,
>         vm=None,
>         debug=False
>     )




    
##### Method `ip` {#kvirt.providers.kvm.Kvirt.ip}




>     def ip(
>         self,
>         name
>     )




    
##### Method `list` {#kvirt.providers.kvm.Kvirt.list}




>     def list(
>         self
>     )




    
##### Method `list_disks` {#kvirt.providers.kvm.Kvirt.list_disks}




>     def list_disks(
>         self
>     )




    
##### Method `list_dns` {#kvirt.providers.kvm.Kvirt.list_dns}




>     def list_dns(
>         self,
>         domain
>     )




    
##### Method `list_networks` {#kvirt.providers.kvm.Kvirt.list_networks}




>     def list_networks(
>         self
>     )




    
##### Method `list_pools` {#kvirt.providers.kvm.Kvirt.list_pools}




>     def list_pools(
>         self
>     )




    
##### Method `list_subnets` {#kvirt.providers.kvm.Kvirt.list_subnets}




>     def list_subnets(
>         self
>     )




    
##### Method `net_exists` {#kvirt.providers.kvm.Kvirt.net_exists}




>     def net_exists(
>         self,
>         name
>     )




    
##### Method `network_ports` {#kvirt.providers.kvm.Kvirt.network_ports}




>     def network_ports(
>         self,
>         name
>     )




    
##### Method `no_memory` {#kvirt.providers.kvm.Kvirt.no_memory}




>     def no_memory(
>         self,
>         memory
>     )




    
##### Method `remove_cloudinit` {#kvirt.providers.kvm.Kvirt.remove_cloudinit}




>     def remove_cloudinit(
>         self,
>         name
>     )




    
##### Method `report` {#kvirt.providers.kvm.Kvirt.report}




>     def report(
>         self
>     )




    
##### Method `reserve_dns` {#kvirt.providers.kvm.Kvirt.reserve_dns}




>     def reserve_dns(
>         self,
>         name,
>         nets=[],
>         domain=None,
>         ip=None,
>         alias=[],
>         force=False,
>         primary=False
>     )




    
##### Method `reserve_host` {#kvirt.providers.kvm.Kvirt.reserve_host}




>     def reserve_host(
>         self,
>         name,
>         nets,
>         domain
>     )




    
##### Method `restart` {#kvirt.providers.kvm.Kvirt.restart}




>     def restart(
>         self,
>         name
>     )




    
##### Method `serialconsole` {#kvirt.providers.kvm.Kvirt.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )




    
##### Method `snapshot` {#kvirt.providers.kvm.Kvirt.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )




    
##### Method `start` {#kvirt.providers.kvm.Kvirt.start}




>     def start(
>         self,
>         name
>     )




    
##### Method `status` {#kvirt.providers.kvm.Kvirt.status}




>     def status(
>         self,
>         name
>     )




    
##### Method `stop` {#kvirt.providers.kvm.Kvirt.stop}




>     def stop(
>         self,
>         name
>     )




    
##### Method `thinimages` {#kvirt.providers.kvm.Kvirt.thinimages}




>     def thinimages(
>         self,
>         path,
>         thinpool
>     )




    
##### Method `update_cpus` {#kvirt.providers.kvm.Kvirt.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )




    
##### Method `update_flavor` {#kvirt.providers.kvm.Kvirt.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )




    
##### Method `update_information` {#kvirt.providers.kvm.Kvirt.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )




    
##### Method `update_iso` {#kvirt.providers.kvm.Kvirt.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )




    
##### Method `update_memory` {#kvirt.providers.kvm.Kvirt.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )




    
##### Method `update_metadata` {#kvirt.providers.kvm.Kvirt.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )




    
##### Method `update_start` {#kvirt.providers.kvm.Kvirt.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )




    
##### Method `vm_ports` {#kvirt.providers.kvm.Kvirt.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )




    
##### Method `volumes` {#kvirt.providers.kvm.Kvirt.volumes}




>     def volumes(
>         self,
>         iso=False
>     )






    
# Module `kvirt.providers.openstack` {#kvirt.providers.openstack}

Openstack Provider Class





    
## Classes


    
### Class `Kopenstack` {#kvirt.providers.openstack.Kopenstack}




>     class Kopenstack(
>         host='127.0.0.1',
>         version='2',
>         port=None,
>         user='root',
>         password=None,
>         debug=False,
>         project=None,
>         domain='Default',
>         auth_url=None,
>         ca_file=None
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.openstack.Kopenstack.add_disk}




>     def add_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )




    
##### Method `add_image` {#kvirt.providers.openstack.Kopenstack.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )




    
##### Method `add_nic` {#kvirt.providers.openstack.Kopenstack.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )




    
##### Method `clone` {#kvirt.providers.openstack.Kopenstack.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )




    
##### Method `close` {#kvirt.providers.openstack.Kopenstack.close}




>     def close(
>         self
>     )




    
##### Method `console` {#kvirt.providers.openstack.Kopenstack.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )




    
##### Method `create` {#kvirt.providers.openstack.Kopenstack.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='',
>         plan='kvirt',
>         flavor=None,
>         cpumodel='Westmere',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         alias=[],
>         overrides={},
>         tags={},
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         placement=[],
>         autostart=False,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )




    
##### Method `create_disk` {#kvirt.providers.openstack.Kopenstack.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )




    
##### Method `create_network` {#kvirt.providers.openstack.Kopenstack.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )




    
##### Method `create_pool` {#kvirt.providers.openstack.Kopenstack.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )




    
##### Method `delete` {#kvirt.providers.openstack.Kopenstack.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )




    
##### Method `delete_disk` {#kvirt.providers.openstack.Kopenstack.delete_disk}




>     def delete_disk(
>         self,
>         name=None,
>         diskname=None,
>         pool=None
>     )




    
##### Method `delete_image` {#kvirt.providers.openstack.Kopenstack.delete_image}




>     def delete_image(
>         self,
>         image
>     )




    
##### Method `delete_network` {#kvirt.providers.openstack.Kopenstack.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )




    
##### Method `delete_nic` {#kvirt.providers.openstack.Kopenstack.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )




    
##### Method `delete_pool` {#kvirt.providers.openstack.Kopenstack.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )




    
##### Method `disk_exists` {#kvirt.providers.openstack.Kopenstack.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )




    
##### Method `dnsinfo` {#kvirt.providers.openstack.Kopenstack.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )




    
##### Method `exists` {#kvirt.providers.openstack.Kopenstack.exists}




>     def exists(
>         self,
>         name
>     )




    
##### Method `export` {#kvirt.providers.openstack.Kopenstack.export}




>     def export(
>         self,
>         name,
>         image=None
>     )




    
##### Method `flavors` {#kvirt.providers.openstack.Kopenstack.flavors}




>     def flavors(
>         self
>     )




    
##### Method `get_pool_path` {#kvirt.providers.openstack.Kopenstack.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )




    
##### Method `info` {#kvirt.providers.openstack.Kopenstack.info}




>     def info(
>         self,
>         name,
>         vm=None,
>         debug=False
>     )




    
##### Method `ip` {#kvirt.providers.openstack.Kopenstack.ip}




>     def ip(
>         self,
>         name
>     )




    
##### Method `list` {#kvirt.providers.openstack.Kopenstack.list}




>     def list(
>         self
>     )




    
##### Method `list_disks` {#kvirt.providers.openstack.Kopenstack.list_disks}




>     def list_disks(
>         self
>     )




    
##### Method `list_dns` {#kvirt.providers.openstack.Kopenstack.list_dns}




>     def list_dns(
>         self,
>         domain
>     )




    
##### Method `list_networks` {#kvirt.providers.openstack.Kopenstack.list_networks}




>     def list_networks(
>         self
>     )




    
##### Method `list_pools` {#kvirt.providers.openstack.Kopenstack.list_pools}




>     def list_pools(
>         self
>     )




    
##### Method `list_subnets` {#kvirt.providers.openstack.Kopenstack.list_subnets}




>     def list_subnets(
>         self
>     )




    
##### Method `net_exists` {#kvirt.providers.openstack.Kopenstack.net_exists}




>     def net_exists(
>         self,
>         name
>     )




    
##### Method `network_ports` {#kvirt.providers.openstack.Kopenstack.network_ports}




>     def network_ports(
>         self,
>         name
>     )




    
##### Method `report` {#kvirt.providers.openstack.Kopenstack.report}




>     def report(
>         self
>     )




    
##### Method `restart` {#kvirt.providers.openstack.Kopenstack.restart}




>     def restart(
>         self,
>         name
>     )




    
##### Method `serialconsole` {#kvirt.providers.openstack.Kopenstack.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )




    
##### Method `snapshot` {#kvirt.providers.openstack.Kopenstack.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )




    
##### Method `start` {#kvirt.providers.openstack.Kopenstack.start}




>     def start(
>         self,
>         name
>     )




    
##### Method `status` {#kvirt.providers.openstack.Kopenstack.status}




>     def status(
>         self,
>         name
>     )




    
##### Method `stop` {#kvirt.providers.openstack.Kopenstack.stop}




>     def stop(
>         self,
>         name
>     )




    
##### Method `update_cpus` {#kvirt.providers.openstack.Kopenstack.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )




    
##### Method `update_flavor` {#kvirt.providers.openstack.Kopenstack.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )




    
##### Method `update_information` {#kvirt.providers.openstack.Kopenstack.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )




    
##### Method `update_iso` {#kvirt.providers.openstack.Kopenstack.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )




    
##### Method `update_memory` {#kvirt.providers.openstack.Kopenstack.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )




    
##### Method `update_metadata` {#kvirt.providers.openstack.Kopenstack.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )




    
##### Method `update_start` {#kvirt.providers.openstack.Kopenstack.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )




    
##### Method `vm_ports` {#kvirt.providers.openstack.Kopenstack.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )




    
##### Method `volumes` {#kvirt.providers.openstack.Kopenstack.volumes}




>     def volumes(
>         self,
>         iso=False
>     )






    
# Module `kvirt.providers.ovirt` {#kvirt.providers.ovirt}

Ovirt Provider Class


    
## Sub-modules

* [kvirt.providers.ovirt.helpers](#kvirt.providers.ovirt.helpers)




    
## Classes


    
### Class `KOvirt` {#kvirt.providers.ovirt.KOvirt}




>     class KOvirt(
>         host='127.0.0.1',
>         port=22,
>         user='admin@internal',
>         password=None,
>         insecure=True,
>         ca_file=None,
>         org=None,
>         debug=False,
>         cluster='Default',
>         datacenter='Default',
>         ssh_user='root',
>         imagerepository='ovirt-image-repository',
>         filtervms=False,
>         filteruser=False,
>         filtertag=None
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.ovirt.KOvirt.add_disk}




>     def add_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )




    
##### Method `add_image` {#kvirt.providers.ovirt.KOvirt.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )




    
##### Method `add_nic` {#kvirt.providers.ovirt.KOvirt.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )




    
##### Method `clone` {#kvirt.providers.ovirt.KOvirt.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )




    
##### Method `close` {#kvirt.providers.ovirt.KOvirt.close}




>     def close(
>         self
>     )




    
##### Method `console` {#kvirt.providers.ovirt.KOvirt.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )




    
##### Method `create` {#kvirt.providers.ovirt.KOvirt.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='Westmere',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         alias=[],
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         placement=[],
>         autostart=False,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )




    
##### Method `create_disk` {#kvirt.providers.ovirt.KOvirt.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )




    
##### Method `create_network` {#kvirt.providers.ovirt.KOvirt.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )




    
##### Method `create_pool` {#kvirt.providers.ovirt.KOvirt.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )




    
##### Method `delete` {#kvirt.providers.ovirt.KOvirt.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )




    
##### Method `delete_disk` {#kvirt.providers.ovirt.KOvirt.delete_disk}




>     def delete_disk(
>         self,
>         name=None,
>         diskname=None,
>         pool=None
>     )




    
##### Method `delete_image` {#kvirt.providers.ovirt.KOvirt.delete_image}




>     def delete_image(
>         self,
>         image
>     )




    
##### Method `delete_network` {#kvirt.providers.ovirt.KOvirt.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )




    
##### Method `delete_nic` {#kvirt.providers.ovirt.KOvirt.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )




    
##### Method `delete_pool` {#kvirt.providers.ovirt.KOvirt.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )




    
##### Method `disk_exists` {#kvirt.providers.ovirt.KOvirt.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )




    
##### Method `dnsinfo` {#kvirt.providers.ovirt.KOvirt.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )




    
##### Method `exists` {#kvirt.providers.ovirt.KOvirt.exists}




>     def exists(
>         self,
>         name
>     )




    
##### Method `export` {#kvirt.providers.ovirt.KOvirt.export}




>     def export(
>         self,
>         name,
>         image=None
>     )




    
##### Method `flavors` {#kvirt.providers.ovirt.KOvirt.flavors}




>     def flavors(
>         self
>     )




    
##### Method `get_hostname` {#kvirt.providers.ovirt.KOvirt.get_hostname}




>     def get_hostname(
>         self,
>         address
>     )




    
##### Method `get_pool_path` {#kvirt.providers.ovirt.KOvirt.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )




    
##### Method `info` {#kvirt.providers.ovirt.KOvirt.info}




>     def info(
>         self,
>         name,
>         vm=None,
>         debug=False
>     )




    
##### Method `ip` {#kvirt.providers.ovirt.KOvirt.ip}




>     def ip(
>         self,
>         name
>     )




    
##### Method `list` {#kvirt.providers.ovirt.KOvirt.list}




>     def list(
>         self
>     )




    
##### Method `list_disks` {#kvirt.providers.ovirt.KOvirt.list_disks}




>     def list_disks(
>         self
>     )




    
##### Method `list_dns` {#kvirt.providers.ovirt.KOvirt.list_dns}




>     def list_dns(
>         self,
>         domain
>     )




    
##### Method `list_networks` {#kvirt.providers.ovirt.KOvirt.list_networks}




>     def list_networks(
>         self
>     )




    
##### Method `list_pools` {#kvirt.providers.ovirt.KOvirt.list_pools}




>     def list_pools(
>         self
>     )




    
##### Method `list_subnets` {#kvirt.providers.ovirt.KOvirt.list_subnets}




>     def list_subnets(
>         self
>     )




    
##### Method `net_exists` {#kvirt.providers.ovirt.KOvirt.net_exists}




>     def net_exists(
>         self,
>         name
>     )




    
##### Method `network_ports` {#kvirt.providers.ovirt.KOvirt.network_ports}




>     def network_ports(
>         self,
>         name
>     )




    
##### Method `report` {#kvirt.providers.ovirt.KOvirt.report}




>     def report(
>         self
>     )




    
##### Method `restart` {#kvirt.providers.ovirt.KOvirt.restart}




>     def restart(
>         self,
>         name
>     )




    
##### Method `serialconsole` {#kvirt.providers.ovirt.KOvirt.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )


:param name:
:return:

    
##### Method `snapshot` {#kvirt.providers.ovirt.KOvirt.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )




    
##### Method `start` {#kvirt.providers.ovirt.KOvirt.start}




>     def start(
>         self,
>         name
>     )




    
##### Method `status` {#kvirt.providers.ovirt.KOvirt.status}




>     def status(
>         self,
>         name
>     )




    
##### Method `stop` {#kvirt.providers.ovirt.KOvirt.stop}




>     def stop(
>         self,
>         name
>     )




    
##### Method `update_cpus` {#kvirt.providers.ovirt.KOvirt.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )




    
##### Method `update_flavor` {#kvirt.providers.ovirt.KOvirt.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )




    
##### Method `update_image_size` {#kvirt.providers.ovirt.KOvirt.update_image_size}




>     def update_image_size(
>         self,
>         vmid,
>         size
>     )




    
##### Method `update_information` {#kvirt.providers.ovirt.KOvirt.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )




    
##### Method `update_iso` {#kvirt.providers.ovirt.KOvirt.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )




    
##### Method `update_memory` {#kvirt.providers.ovirt.KOvirt.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )




    
##### Method `update_metadata` {#kvirt.providers.ovirt.KOvirt.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )




    
##### Method `update_start` {#kvirt.providers.ovirt.KOvirt.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )




    
##### Method `vm_ports` {#kvirt.providers.ovirt.KOvirt.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )




    
##### Method `volumes` {#kvirt.providers.ovirt.KOvirt.volumes}




>     def volumes(
>         self,
>         iso=False
>     )






    
# Module `kvirt.providers.ovirt.helpers` {#kvirt.providers.ovirt.helpers}






    
## Functions


    
### Function `get_home_ssh_key` {#kvirt.providers.ovirt.helpers.get_home_ssh_key}




>     def get_home_ssh_key()


:return:




    
# Module `kvirt.providers.packet` {#kvirt.providers.packet}

Packet provider class





    
## Classes


    
### Class `Kpacket` {#kvirt.providers.packet.Kpacket}




>     class Kpacket(
>         auth_token,
>         project=None,
>         debug=False,
>         facility=None,
>         tunnelhost=None,
>         tunneluser='root',
>         tunnelport=22,
>         tunneldir='/var/www/html'
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.packet.Kpacket.add_disk}




>     def add_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:

    
##### Method `add_image` {#kvirt.providers.packet.Kpacket.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:

    
##### Method `add_nic` {#kvirt.providers.packet.Kpacket.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )


:param name:
:param network:
:return:

    
##### Method `clone` {#kvirt.providers.packet.Kpacket.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )


:param old:
:param new:
:param full:
:param start:
:return:

    
##### Method `close` {#kvirt.providers.packet.Kpacket.close}




>     def close(
>         self
>     )


:return:

    
##### Method `console` {#kvirt.providers.packet.Kpacket.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )


:param name:
:param tunnel:
:return:

    
##### Method `create` {#kvirt.providers.packet.Kpacket.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='Westmere',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         alias=[],
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         placement=[],
>         autostart=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )


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
:param tpm:
:return:

    
##### Method `create_disk` {#kvirt.providers.packet.Kpacket.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:

    
##### Method `create_network` {#kvirt.providers.packet.Kpacket.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param pxe:
:param vlan:
:return:

    
##### Method `create_pool` {#kvirt.providers.packet.Kpacket.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:

    
##### Method `delete` {#kvirt.providers.packet.Kpacket.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )


:param name:
:param snapshots:
:return:

    
##### Method `delete_disk` {#kvirt.providers.packet.Kpacket.delete_disk}




>     def delete_disk(
>         self,
>         name,
>         diskname,
>         pool=None
>     )


:param name:
:param diskname:
:param pool:
:return:

    
##### Method `delete_image` {#kvirt.providers.packet.Kpacket.delete_image}




>     def delete_image(
>         self,
>         image
>     )


:param image:
:return:

    
##### Method `delete_network` {#kvirt.providers.packet.Kpacket.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )


:param name:
:param cidr:
:return:

    
##### Method `delete_nic` {#kvirt.providers.packet.Kpacket.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )


:param name:
:param interface:
:return:

    
##### Method `delete_pool` {#kvirt.providers.packet.Kpacket.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )


:param name:
:param full:
:return:

    
##### Method `disk_exists` {#kvirt.providers.packet.Kpacket.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )


:param pool:
:param name:

    
##### Method `dnsinfo` {#kvirt.providers.packet.Kpacket.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `exists` {#kvirt.providers.packet.Kpacket.exists}




>     def exists(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `export` {#kvirt.providers.packet.Kpacket.export}




>     def export(
>         self,
>         name,
>         image=None
>     )


:param image:
:return:

    
##### Method `flavors` {#kvirt.providers.packet.Kpacket.flavors}




>     def flavors(
>         self
>     )


:return:

    
##### Method `get_pool_path` {#kvirt.providers.packet.Kpacket.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )


:param pool:
:return:

    
##### Method `info` {#kvirt.providers.packet.Kpacket.info}




>     def info(
>         self,
>         name,
>         output='plain',
>         fields=[],
>         values=False,
>         vm=None,
>         debug=False
>     )


:param name:
:param output:
:param fields:
:param values:
:return:

    
##### Method `ip` {#kvirt.providers.packet.Kpacket.ip}




>     def ip(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `list` {#kvirt.providers.packet.Kpacket.list}




>     def list(
>         self
>     )


:return:

    
##### Method `list_disks` {#kvirt.providers.packet.Kpacket.list_disks}




>     def list_disks(
>         self
>     )


:return:

    
##### Method `list_networks` {#kvirt.providers.packet.Kpacket.list_networks}




>     def list_networks(
>         self
>     )


:return:

    
##### Method `list_pools` {#kvirt.providers.packet.Kpacket.list_pools}




>     def list_pools(
>         self
>     )


:return:

    
##### Method `list_subnets` {#kvirt.providers.packet.Kpacket.list_subnets}




>     def list_subnets(
>         self
>     )


:return:

    
##### Method `net_exists` {#kvirt.providers.packet.Kpacket.net_exists}




>     def net_exists(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `network_ports` {#kvirt.providers.packet.Kpacket.network_ports}




>     def network_ports(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `report` {#kvirt.providers.packet.Kpacket.report}




>     def report(
>         self
>     )


:return:

    
##### Method `restart` {#kvirt.providers.packet.Kpacket.restart}




>     def restart(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `serialconsole` {#kvirt.providers.packet.Kpacket.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )


:param name:
:return:

    
##### Method `snapshot` {#kvirt.providers.packet.Kpacket.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:

    
##### Method `start` {#kvirt.providers.packet.Kpacket.start}




>     def start(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `status` {#kvirt.providers.packet.Kpacket.status}




>     def status(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `stop` {#kvirt.providers.packet.Kpacket.stop}




>     def stop(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `update_cpus` {#kvirt.providers.packet.Kpacket.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )


:param name:
:param numcpus:
:return:

    
##### Method `update_flavor` {#kvirt.providers.packet.Kpacket.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )


:param name:
:param flavor:
:return:

    
##### Method `update_information` {#kvirt.providers.packet.Kpacket.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )


:param name:
:param information:
:return:

    
##### Method `update_iso` {#kvirt.providers.packet.Kpacket.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )


:param name:
:param iso:
:return:

    
##### Method `update_memory` {#kvirt.providers.packet.Kpacket.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )


:param name:
:param memory:
:return:

    
##### Method `update_metadata` {#kvirt.providers.packet.Kpacket.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )


:param name:
:param metatype:
:param metavalue:
:return:

    
##### Method `update_start` {#kvirt.providers.packet.Kpacket.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )


:param name:
:param start:
:return:

    
##### Method `vm_ports` {#kvirt.providers.packet.Kpacket.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `volumes` {#kvirt.providers.packet.Kpacket.volumes}




>     def volumes(
>         self,
>         iso=False
>     )


:param iso:
:return:



    
# Module `kvirt.providers.sampleprovider` {#kvirt.providers.sampleprovider}

Base Kvirt serving as interface for the virtualisation providers





    
## Classes


    
### Class `Kbase` {#kvirt.providers.sampleprovider.Kbase}




>     class Kbase(
>         host='127.0.0.1',
>         port=None,
>         user='root',
>         debug=False
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.sampleprovider.Kbase.add_disk}




>     def add_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )


:param name:
:param size:
:param pool:
:param thin:
:param image:
:param shareable:
:param existing:
:return:

    
##### Method `add_image` {#kvirt.providers.sampleprovider.Kbase.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )


:param image:
:param pool:
:param short:
:param cmd:
:param name:
:param size:
:return:

    
##### Method `add_nic` {#kvirt.providers.sampleprovider.Kbase.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )


:param name:
:param network:
:return:

    
##### Method `clone` {#kvirt.providers.sampleprovider.Kbase.clone}




>     def clone(
>         self,
>         old,
>         new,
>         full=False,
>         start=False
>     )


:param old:
:param new:
:param full:
:param start:
:return:

    
##### Method `close` {#kvirt.providers.sampleprovider.Kbase.close}




>     def close(
>         self
>     )


:return:

    
##### Method `console` {#kvirt.providers.sampleprovider.Kbase.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )


:param name:
:param tunnel:
:return:

    
##### Method `create` {#kvirt.providers.sampleprovider.Kbase.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='Westmere',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='guestrhel764',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         alias=[],
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         placement=[],
>         autostart=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )


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
:param tpm:
:return:

    
##### Method `create_disk` {#kvirt.providers.sampleprovider.Kbase.create_disk}




>     def create_disk(
>         self,
>         name,
>         size,
>         pool=None,
>         thin=True,
>         image=None
>     )


:param name:
:param size:
:param pool:
:param thin:
:param image:
:return:

    
##### Method `create_network` {#kvirt.providers.sampleprovider.Kbase.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )


:param name:
:param cidr:
:param dhcp:
:param nat:
:param domain:
:param plan:
:param pxe:
:param vlan:
:return:

    
##### Method `create_pool` {#kvirt.providers.sampleprovider.Kbase.create_pool}




>     def create_pool(
>         self,
>         name,
>         poolpath,
>         pooltype='dir',
>         user='qemu',
>         thinpool=None
>     )


:param name:
:param poolpath:
:param pooltype:
:param user:
:param thinpool:
:return:

    
##### Method `delete` {#kvirt.providers.sampleprovider.Kbase.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )


:param name:
:param snapshots:
:return:

    
##### Method `delete_disk` {#kvirt.providers.sampleprovider.Kbase.delete_disk}




>     def delete_disk(
>         self,
>         name,
>         diskname,
>         pool=None
>     )


:param name:
:param diskname:
:param pool:
:return:

    
##### Method `delete_image` {#kvirt.providers.sampleprovider.Kbase.delete_image}




>     def delete_image(
>         self,
>         image
>     )


:param image:
:return:

    
##### Method `delete_network` {#kvirt.providers.sampleprovider.Kbase.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )


:param name:
:param cidr:
:return:

    
##### Method `delete_nic` {#kvirt.providers.sampleprovider.Kbase.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )


:param name:
:param interface:
:return:

    
##### Method `delete_pool` {#kvirt.providers.sampleprovider.Kbase.delete_pool}




>     def delete_pool(
>         self,
>         name,
>         full=False
>     )


:param name:
:param full:
:return:

    
##### Method `disk_exists` {#kvirt.providers.sampleprovider.Kbase.disk_exists}




>     def disk_exists(
>         self,
>         pool,
>         name
>     )


:param pool:
:param name:

    
##### Method `dnsinfo` {#kvirt.providers.sampleprovider.Kbase.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `exists` {#kvirt.providers.sampleprovider.Kbase.exists}




>     def exists(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `export` {#kvirt.providers.sampleprovider.Kbase.export}




>     def export(
>         self,
>         name,
>         image=None
>     )


:param image:
:return:

    
##### Method `flavors` {#kvirt.providers.sampleprovider.Kbase.flavors}




>     def flavors(
>         self
>     )


:return:

    
##### Method `get_pool_path` {#kvirt.providers.sampleprovider.Kbase.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )


:param pool:
:return:

    
##### Method `info` {#kvirt.providers.sampleprovider.Kbase.info}




>     def info(
>         self,
>         name,
>         output='plain',
>         fields=[],
>         values=False,
>         vm=None,
>         debug=False
>     )


:param name:
:param output:
:param fields:
:param values:
:return:

    
##### Method `ip` {#kvirt.providers.sampleprovider.Kbase.ip}




>     def ip(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `list` {#kvirt.providers.sampleprovider.Kbase.list}




>     def list(
>         self
>     )


:return:

    
##### Method `list_disks` {#kvirt.providers.sampleprovider.Kbase.list_disks}




>     def list_disks(
>         self
>     )


:return:

    
##### Method `list_networks` {#kvirt.providers.sampleprovider.Kbase.list_networks}




>     def list_networks(
>         self
>     )


:return:

    
##### Method `list_pools` {#kvirt.providers.sampleprovider.Kbase.list_pools}




>     def list_pools(
>         self
>     )


:return:

    
##### Method `list_subnets` {#kvirt.providers.sampleprovider.Kbase.list_subnets}




>     def list_subnets(
>         self
>     )


:return:

    
##### Method `net_exists` {#kvirt.providers.sampleprovider.Kbase.net_exists}




>     def net_exists(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `network_ports` {#kvirt.providers.sampleprovider.Kbase.network_ports}




>     def network_ports(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `report` {#kvirt.providers.sampleprovider.Kbase.report}




>     def report(
>         self
>     )


:return:

    
##### Method `restart` {#kvirt.providers.sampleprovider.Kbase.restart}




>     def restart(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `scp` {#kvirt.providers.sampleprovider.Kbase.scp}




>     def scp(
>         self,
>         name,
>         user=None,
>         source=None,
>         destination=None,
>         tunnel=False,
>         tunnelhost=None,
>         tunnelport=22,
>         tunneluser='root',
>         download=False,
>         recursive=False,
>         insecure=False
>     )


:param name:
:param user:
:param source:
:param destination:
:param tunnel:
:param download:
:param recursive:
:param insecure:
:return:

    
##### Method `serialconsole` {#kvirt.providers.sampleprovider.Kbase.serialconsole}




>     def serialconsole(
>         self,
>         name,
>         web=False
>     )


:param name:
:return:

    
##### Method `snapshot` {#kvirt.providers.sampleprovider.Kbase.snapshot}




>     def snapshot(
>         self,
>         name,
>         base,
>         revert=False,
>         delete=False,
>         listing=False
>     )


:param name:
:param base:
:param revert:
:param delete:
:param listing:
:return:

    
##### Method `start` {#kvirt.providers.sampleprovider.Kbase.start}




>     def start(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `status` {#kvirt.providers.sampleprovider.Kbase.status}




>     def status(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `stop` {#kvirt.providers.sampleprovider.Kbase.stop}




>     def stop(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `update_cpus` {#kvirt.providers.sampleprovider.Kbase.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )


:param name:
:param numcpus:
:return:

    
##### Method `update_flavor` {#kvirt.providers.sampleprovider.Kbase.update_flavor}




>     def update_flavor(
>         self,
>         name,
>         flavor
>     )


:param name:
:param flavor:
:return:

    
##### Method `update_information` {#kvirt.providers.sampleprovider.Kbase.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )


:param name:
:param information:
:return:

    
##### Method `update_iso` {#kvirt.providers.sampleprovider.Kbase.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )


:param name:
:param iso:
:return:

    
##### Method `update_memory` {#kvirt.providers.sampleprovider.Kbase.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )


:param name:
:param memory:
:return:

    
##### Method `update_metadata` {#kvirt.providers.sampleprovider.Kbase.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )


:param name:
:param metatype:
:param metavalue:
:return:

    
##### Method `update_start` {#kvirt.providers.sampleprovider.Kbase.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )


:param name:
:param start:
:return:

    
##### Method `vm_ports` {#kvirt.providers.sampleprovider.Kbase.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )


:param name:
:return:

    
##### Method `volumes` {#kvirt.providers.sampleprovider.Kbase.volumes}




>     def volumes(
>         self,
>         iso=False
>     )


:param iso:
:return:



    
# Module `kvirt.providers.vsphere` {#kvirt.providers.vsphere}




    
## Sub-modules

* [kvirt.providers.vsphere.helpers](#kvirt.providers.vsphere.helpers)



    
## Functions


    
### Function `changecd` {#kvirt.providers.vsphere.changecd}




>     def changecd(
>         si,
>         vm,
>         iso
>     )




    
### Function `collectproperties` {#kvirt.providers.vsphere.collectproperties}




>     def collectproperties(
>         si,
>         view,
>         objtype,
>         pathset=None,
>         includemors=False
>     )




    
### Function `convert` {#kvirt.providers.vsphere.convert}




>     def convert(
>         octets,
>         GB=True
>     )




    
### Function `create_filter_spec` {#kvirt.providers.vsphere.create_filter_spec}




>     def create_filter_spec(
>         pc,
>         vms
>     )




    
### Function `createcdspec` {#kvirt.providers.vsphere.createcdspec}




>     def createcdspec()




    
### Function `createclonespec` {#kvirt.providers.vsphere.createclonespec}




>     def createclonespec(
>         pool
>     )




    
### Function `creatediskspec` {#kvirt.providers.vsphere.creatediskspec}




>     def creatediskspec(
>         number,
>         disksize,
>         ds,
>         diskmode,
>         thin=False
>     )




    
### Function `createfolder` {#kvirt.providers.vsphere.createfolder}




>     def createfolder(
>         si,
>         parentfolder,
>         folder
>     )




    
### Function `createisospec` {#kvirt.providers.vsphere.createisospec}




>     def createisospec(
>         iso=None
>     )




    
### Function `createnicspec` {#kvirt.providers.vsphere.createnicspec}




>     def createnicspec(
>         nicname,
>         netname
>     )




    
### Function `createscsispec` {#kvirt.providers.vsphere.createscsispec}




>     def createscsispec()




    
### Function `deletedirectory` {#kvirt.providers.vsphere.deletedirectory}




>     def deletedirectory(
>         si,
>         dc,
>         path
>     )




    
### Function `deletefolder` {#kvirt.providers.vsphere.deletefolder}




>     def deletefolder(
>         si,
>         parentfolder,
>         folder
>     )




    
### Function `dssize` {#kvirt.providers.vsphere.dssize}




>     def dssize(
>         ds
>     )




    
### Function `filter_results` {#kvirt.providers.vsphere.filter_results}




>     def filter_results(
>         results
>     )




    
### Function `find` {#kvirt.providers.vsphere.find}




>     def find(
>         si,
>         folder,
>         vimtype,
>         name
>     )




    
### Function `findvm` {#kvirt.providers.vsphere.findvm}




>     def findvm(
>         si,
>         folder,
>         name
>     )




    
### Function `makecuspec` {#kvirt.providers.vsphere.makecuspec}




>     def makecuspec(
>         name,
>         nets=[],
>         gateway=None,
>         dns=None,
>         domain=None
>     )




    
### Function `waitForMe` {#kvirt.providers.vsphere.waitForMe}




>     def waitForMe(
>         t
>     )





    
## Classes


    
### Class `Ksphere` {#kvirt.providers.vsphere.Ksphere}




>     class Ksphere(
>         host,
>         user,
>         password,
>         datacenter,
>         cluster,
>         debug=False,
>         filtervms=False,
>         filteruser=False,
>         filtertag=None
>     )










    
#### Methods


    
##### Method `add_disk` {#kvirt.providers.vsphere.Ksphere.add_disk}




>     def add_disk(
>         self,
>         name,
>         size=1,
>         pool=None,
>         thin=True,
>         image=None,
>         shareable=False,
>         existing=None,
>         interface='virtio'
>     )




    
##### Method `add_image` {#kvirt.providers.vsphere.Ksphere.add_image}




>     def add_image(
>         self,
>         image,
>         pool,
>         short=None,
>         cmd=None,
>         name=None,
>         size=1
>     )




    
##### Method `add_nic` {#kvirt.providers.vsphere.Ksphere.add_nic}




>     def add_nic(
>         self,
>         name,
>         network
>     )




    
##### Method `beststorage` {#kvirt.providers.vsphere.Ksphere.beststorage}




>     def beststorage(
>         self
>     )




    
##### Method `close` {#kvirt.providers.vsphere.Ksphere.close}




>     def close(
>         self
>     )




    
##### Method `console` {#kvirt.providers.vsphere.Ksphere.console}




>     def console(
>         self,
>         name,
>         tunnel=False,
>         web=False
>     )




    
##### Method `create` {#kvirt.providers.vsphere.Ksphere.create}




>     def create(
>         self,
>         name,
>         virttype=None,
>         profile='kvirt',
>         flavor=None,
>         plan='kvirt',
>         cpumodel='host-model',
>         cpuflags=[],
>         cpupinning=[],
>         numcpus=2,
>         memory=512,
>         guestid='centos7_64Guest',
>         pool='default',
>         image=None,
>         disks=[{'size': 10}],
>         disksize=10,
>         diskthin=True,
>         diskinterface='virtio',
>         nets=['default'],
>         iso=None,
>         vnc=False,
>         cloudinit=True,
>         reserveip=False,
>         reservedns=False,
>         reservehost=False,
>         start=True,
>         keys=None,
>         cmds=[],
>         ips=None,
>         netmasks=None,
>         gateway=None,
>         nested=True,
>         dns=None,
>         domain=None,
>         tunnel=False,
>         files=[],
>         enableroot=True,
>         overrides={},
>         tags=[],
>         dnsclient=None,
>         storemetadata=False,
>         sharedfolders=[],
>         kernel=None,
>         initrd=None,
>         cmdline=None,
>         placement=[],
>         autostart=False,
>         cpuhotplug=False,
>         memoryhotplug=False,
>         numamode=None,
>         numa=[],
>         pcidevices=[],
>         tpm=False,
>         rng=False,
>         kube=None,
>         kubetype=None
>     )




    
##### Method `create_network` {#kvirt.providers.vsphere.Ksphere.create_network}




>     def create_network(
>         self,
>         name,
>         cidr=None,
>         dhcp=True,
>         nat=True,
>         domain=None,
>         plan='kvirt',
>         overrides={}
>     )




    
##### Method `delete` {#kvirt.providers.vsphere.Ksphere.delete}




>     def delete(
>         self,
>         name,
>         snapshots=False
>     )




    
##### Method `delete_disk` {#kvirt.providers.vsphere.Ksphere.delete_disk}




>     def delete_disk(
>         self,
>         name=None,
>         diskname=None,
>         pool=None
>     )




    
##### Method `delete_image` {#kvirt.providers.vsphere.Ksphere.delete_image}




>     def delete_image(
>         self,
>         image
>     )




    
##### Method `delete_network` {#kvirt.providers.vsphere.Ksphere.delete_network}




>     def delete_network(
>         self,
>         name=None,
>         cidr=None
>     )




    
##### Method `delete_nic` {#kvirt.providers.vsphere.Ksphere.delete_nic}




>     def delete_nic(
>         self,
>         name,
>         interface
>     )




    
##### Method `dnsinfo` {#kvirt.providers.vsphere.Ksphere.dnsinfo}




>     def dnsinfo(
>         self,
>         name
>     )




    
##### Method `exists` {#kvirt.providers.vsphere.Ksphere.exists}




>     def exists(
>         self,
>         name
>     )




    
##### Method `export` {#kvirt.providers.vsphere.Ksphere.export}




>     def export(
>         self,
>         name,
>         image=None
>     )




    
##### Method `get_pool_path` {#kvirt.providers.vsphere.Ksphere.get_pool_path}




>     def get_pool_path(
>         self,
>         pool
>     )




    
##### Method `info` {#kvirt.providers.vsphere.Ksphere.info}




>     def info(
>         self,
>         name,
>         output='plain',
>         fields=[],
>         values=False,
>         vm=None,
>         debug=False
>     )




    
##### Method `list` {#kvirt.providers.vsphere.Ksphere.list}




>     def list(
>         self
>     )




    
##### Method `list_dns` {#kvirt.providers.vsphere.Ksphere.list_dns}




>     def list_dns(
>         self,
>         domain
>     )




    
##### Method `list_networks` {#kvirt.providers.vsphere.Ksphere.list_networks}




>     def list_networks(
>         self
>     )




    
##### Method `list_pools` {#kvirt.providers.vsphere.Ksphere.list_pools}




>     def list_pools(
>         self
>     )




    
##### Method `net_exists` {#kvirt.providers.vsphere.Ksphere.net_exists}




>     def net_exists(
>         self,
>         name
>     )




    
##### Method `report` {#kvirt.providers.vsphere.Ksphere.report}




>     def report(
>         self
>     )




    
##### Method `start` {#kvirt.providers.vsphere.Ksphere.start}




>     def start(
>         self,
>         name
>     )




    
##### Method `status` {#kvirt.providers.vsphere.Ksphere.status}




>     def status(
>         self,
>         name
>     )




    
##### Method `stop` {#kvirt.providers.vsphere.Ksphere.stop}




>     def stop(
>         self,
>         name
>     )




    
##### Method `update_cpus` {#kvirt.providers.vsphere.Ksphere.update_cpus}




>     def update_cpus(
>         self,
>         name,
>         numcpus
>     )




    
##### Method `update_information` {#kvirt.providers.vsphere.Ksphere.update_information}




>     def update_information(
>         self,
>         name,
>         information
>     )




    
##### Method `update_iso` {#kvirt.providers.vsphere.Ksphere.update_iso}




>     def update_iso(
>         self,
>         name,
>         iso
>     )




    
##### Method `update_memory` {#kvirt.providers.vsphere.Ksphere.update_memory}




>     def update_memory(
>         self,
>         name,
>         memory
>     )




    
##### Method `update_metadata` {#kvirt.providers.vsphere.Ksphere.update_metadata}




>     def update_metadata(
>         self,
>         name,
>         metatype,
>         metavalue,
>         append=False
>     )




    
##### Method `update_start` {#kvirt.providers.vsphere.Ksphere.update_start}




>     def update_start(
>         self,
>         name,
>         start=True
>     )




    
##### Method `vm_ports` {#kvirt.providers.vsphere.Ksphere.vm_ports}




>     def vm_ports(
>         self,
>         name
>     )




    
##### Method `volumes` {#kvirt.providers.vsphere.Ksphere.volumes}




>     def volumes(
>         self,
>         iso=False
>     )






    
# Module `kvirt.providers.vsphere.helpers` {#kvirt.providers.vsphere.helpers}









    
# Module `kvirt.version` {#kvirt.version}









    
# Module `kvirt.web` {#kvirt.web}




    
## Sub-modules

* [kvirt.web.main](#kvirt.web.main)






    
# Module `kvirt.web.main` {#kvirt.web.main}






    
## Functions


    
### Function `containeraction` {#kvirt.web.main.containeraction}




>     def containeraction()


start/stop/delete container

    
### Function `containercreate` {#kvirt.web.main.containercreate}




>     def containercreate()


create container

    
### Function `containerprofiles` {#kvirt.web.main.containerprofiles}




>     def containerprofiles()


retrieves all containerprofiles

    
### Function `containerprofilestable` {#kvirt.web.main.containerprofilestable}




>     def containerprofilestable()


retrieves container profiles in table

    
### Function `containers` {#kvirt.web.main.containers}




>     def containers()


retrieves all containers

    
### Function `containerstable` {#kvirt.web.main.containerstable}




>     def containerstable()


retrieves all containers in table

    
### Function `diskaction` {#kvirt.web.main.diskaction}




>     def diskaction()


add/delete disk to vm

    
### Function `hostaction` {#kvirt.web.main.hostaction}




>     def hostaction()


enable/disable/default host

    
### Function `hosts` {#kvirt.web.main.hosts}




>     def hosts()


retrieves all hosts

    
### Function `hoststable` {#kvirt.web.main.hoststable}




>     def hoststable()


retrieves all clients in table

    
### Function `imageaction` {#kvirt.web.main.imageaction}




>     def imageaction()


create/delete image

    
### Function `imagecreate` {#kvirt.web.main.imagecreate}




>     def imagecreate()


create image

    
### Function `images` {#kvirt.web.main.images}




>     def images()


:return:

    
### Function `imagestable` {#kvirt.web.main.imagestable}




>     def imagestable()


retrieves images in table

    
### Function `isos` {#kvirt.web.main.isos}




>     def isos()


:return:

    
### Function `isostable` {#kvirt.web.main.isostable}




>     def isostable()


retrieves isos in table

    
### Function `kubeaction` {#kvirt.web.main.kubeaction}




>     def kubeaction()


create kube

    
### Function `kubegenericcreate` {#kvirt.web.main.kubegenericcreate}




>     def kubegenericcreate()


create generic kube

    
### Function `kubeopenshiftcreate` {#kvirt.web.main.kubeopenshiftcreate}




>     def kubeopenshiftcreate()


create openshift kube

    
### Function `kubes` {#kvirt.web.main.kubes}




>     def kubes()


:return:

    
### Function `kubestable` {#kvirt.web.main.kubestable}




>     def kubestable()


retrieves all kubes in table

    
### Function `networkaction` {#kvirt.web.main.networkaction}




>     def networkaction()


create/delete network

    
### Function `networkcreate` {#kvirt.web.main.networkcreate}




>     def networkcreate()


network form

    
### Function `networks` {#kvirt.web.main.networks}




>     def networks()


retrieves all networks

    
### Function `networkstable` {#kvirt.web.main.networkstable}




>     def networkstable()


retrieves all networks in table

    
### Function `nicaction` {#kvirt.web.main.nicaction}




>     def nicaction()


add/delete nic to vm

    
### Function `planaction` {#kvirt.web.main.planaction}




>     def planaction()


start/stop/delete plan

    
### Function `plancreate` {#kvirt.web.main.plancreate}




>     def plancreate()


create plan

    
### Function `plans` {#kvirt.web.main.plans}




>     def plans()


:return:

    
### Function `planstable` {#kvirt.web.main.planstable}




>     def planstable()


retrieves all plans in table

    
### Function `poolaction` {#kvirt.web.main.poolaction}




>     def poolaction()


create/delete pool

    
### Function `poolcreate` {#kvirt.web.main.poolcreate}




>     def poolcreate()


pool form

    
### Function `pools` {#kvirt.web.main.pools}




>     def pools()


retrieves all pools

    
### Function `poolstable` {#kvirt.web.main.poolstable}




>     def poolstable()


retrieves all pools in table

    
### Function `productaction` {#kvirt.web.main.productaction}




>     def productaction()


create product

    
### Function `productcreate` {#kvirt.web.main.productcreate}




>     def productcreate(
>         prod
>     )


product form

    
### Function `products` {#kvirt.web.main.products}




>     def products()


:return:

    
### Function `productstable` {#kvirt.web.main.productstable}




>     def productstable()


retrieves all products in table

    
### Function `repoaction` {#kvirt.web.main.repoaction}




>     def repoaction()


create/delete repo

    
### Function `repocreate` {#kvirt.web.main.repocreate}




>     def repocreate()


repo form

    
### Function `repos` {#kvirt.web.main.repos}




>     def repos()


:return:

    
### Function `repostable` {#kvirt.web.main.repostable}




>     def repostable()


retrieves all repos in table

    
### Function `run` {#kvirt.web.main.run}




>     def run()




    
### Function `snapshotaction` {#kvirt.web.main.snapshotaction}




>     def snapshotaction()


create/delete/revert snapshot

    
### Function `vmaction` {#kvirt.web.main.vmaction}




>     def vmaction()


start/stop/delete/create vm

    
### Function `vmconsole` {#kvirt.web.main.vmconsole}




>     def vmconsole(
>         name
>     )


Get url for console

    
### Function `vmcreate` {#kvirt.web.main.vmcreate}




>     def vmcreate()


create vm

    
### Function `vmprofiles` {#kvirt.web.main.vmprofiles}




>     def vmprofiles()


:return:

    
### Function `vmprofilestable` {#kvirt.web.main.vmprofilestable}




>     def vmprofilestable()


retrieves vm profiles in table

    
### Function `vms` {#kvirt.web.main.vms}




>     def vms()


:return:

    
### Function `vmstable` {#kvirt.web.main.vmstable}




>     def vmstable()


retrieves all vms in table



-----
Generated by *pdoc* 0.9.1 (<https://pdoc3.github.io>).
