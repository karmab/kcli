from getpass import getuser
from glob import glob
from kvirt import common
import json
from kvirt.config import Kbaseconfig, Kconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt.common import get_git_version, compare_git_versions, filter_info_plan, convert_yaml_to_cmd
from kvirt.common import _ssh_credentials
from kvirt.nameutils import get_random_name
from kvirt.defaults import IMAGES, VERSION, PLANTYPES, OPENSHIFT_TAG
from mcp.server.fastmcp import FastMCP
import os
import sys
from shutil import which, copy2
from typing import Optional
from urllib.request import urlopen
import yaml


def _parse_vms_list(_list, overrides={}):
    if isinstance(_list, str):
        print(_list)
        return
    field = overrides.get('field')
    if field is not None:
        vmstable = ["Name", field.capitalize()]
    else:
        vmstable = ["Name", "Status", "Ips", "Source", "Plan", "Profile"]
    for vm in _list:
        if field is not None:
            name = next(iter(vm))
            vminfo = [name, vm[name]]
            vmstable.append(vminfo)
            continue
        name = vm.get('name')
        status = vm.get('status')
        ip = vm.get('ip', '')
        source = vm.get('image', '')
        plan = vm.get('plan', '')
        profile = vm.get('profile', '')
        vminfo = [name, status, ip, source, plan, profile]
        vmstable.append(vminfo)
    return vmstable


mcp = FastMCP("kcli")


@mcp.prompt()
def prompt() -> str:
    """Indicates contexts of questions related to kcli"""
    return """You are a helpful assistant who knows everything about kcli, a powerful client and library written
    in Python and meant to interact with different virtualization providers, easily deploy and customize VMs or
    full kubernetes/OpenShift clusters. All information about kcli is available at
    https://github.com/karmab/kcli/blob/main/docs/index.md"""


@mcp.resource("resource://kcli-doc.md")
def get_doc() -> str:
    """Provides kcli documentation"""
    url = 'https://raw.githubusercontent.com/karmab/kcli/refs/heads/main/docs/index.md'
    return urlopen(url).read().decode('utf-8')


@mcp.tool()
def about_kcli() -> str:
    """What is kcli"""
    return """This tool is meant to interact with existing virtualization providers (libvirt, KubeVirt, oVirt,
    OpenStack, VMware vSphere, Packet, AWS, Azure, GCP, IBM cloud and Hcloud)
    and to easily deploy and customize VMs from cloud images.
    You can also interact with those VMs (list, info, ssh, start, stop, delete, console, serialconsole,
    add/delete disk, add/delete nic, ...).
    Furthermore, you can deploy VMs using predefined profiles,
    several at once using plan files or entire products for which plans were already created for you.
    Refer to the [documentation](https://kcli.readthedocs.io) for more information
    """


@mcp.tool()
def clone_vm(name: str, base: str, full: bool = False, start: bool = False,
             client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> dict:
    """Clone vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.clone(base, name, full=full, start=start)


@mcp.tool()
def create_app(app: str, client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Create application"""
    kubectl = which('kubectl') or which('oc')
    if kubectl is None:
        return {'result': 'failure', 'reason': "You need kubectl/oc to install apps"}
    if 'KUBECONFIG' in os.environ and not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    overrides[f'{app}_version'] = overrides[f'{app}_version'] if f'{app}_version' in overrides else 'latest'
    return baseconfig.create_app(app, overrides)


@mcp.tool()
def create_bucket(buckets: list = [], public: bool = False,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None):
    """Create bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for bucket in buckets:
        k.create_bucket(bucket, public=public)


@mcp.tool()
def create_bucketfile(bucket: str, path: str, temp: str = None, public: bool = False,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> str:
    """Create bucketfile in bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.upload_to_bucket(bucket, path, temp_url=temp, public=public)


@mcp.tool()
def create_clusterprofile(clusterprofile: str,
                          client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Create cluster profile"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.create_clusterprofile(clusterprofile, overrides=overrides)


@mcp.tool()
def create_confpool(confpool: str,
                    client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Create configuration pool"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.create_confpool(confpool, overrides=overrides)


@mcp.tool()
def create_container(name: str = None, image: str = None, profile: str = None,
                     containerclient: str = None,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create container"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    cont = Kcontainerconfig(config, client=containerclient).cont
    containerprofiles = {k: v for k, v in config.profiles.items() if 'type' in v and v['type'] == 'container'}
    if name is None:
        name = get_random_name()
        if config.type == 'kubevirt':
            name = name.replace('_', '-')
    if image is not None:
        profile = image
        if image not in containerprofiles:
            containerprofiles[image] = {'image': image}
    profile = containerprofiles[profile]
    image = next((e for e in [profile.get('image'), profile.get('image')] if e is not None), None)
    if image is None:
        msg = f"Missing image in profile {profile}"
        return {'result': 'failure', 'reason': msg}
        sys.exit(1)
    if config.type == 'proxmox':
        overrides['lxc'] = True
        return config.create_vm(name, image, overrides=overrides)
    cmd = profile.get('cmd')
    ports = profile.get('ports')
    environment = profile.get('environment')
    volumes = next((e for e in [profile.get('volumes'), profile.get('disks')] if e is not None), None)
    profile.update(overrides)
    params = {'name': name, 'image': image, 'ports': ports, 'volumes': volumes, 'environment': environment,
              'overrides': overrides}
    if cmd is not None:
        params['cmds'] = [cmd]
    return cont.create_container(**params)


@mcp.tool()
def create_dns(names: list, net: str, domain: str, ip: str, alias: str,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None):
    """Create dns entry"""
    if alias is None:
        alias = []
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    name = names[0]
    if len(names) > 1:
        alias.extend(names[1:])
    k.reserve_dns(name=name, nets=[net], domain=domain, ip=ip, alias=alias, primary=True)


@mcp.tool()
def create_host_aws(name: str, access_key_id: str, access_key_secret: str, region: str, keypair, str,
                    client: str = None, debug: bool = False):
    """Create aws host"""
    data = {}
    data['name'] = name
    data['_type'] = 'aws'
    data['access_key_id'] = access_key_id
    data['access_key_secret'] = access_key_secret
    data['region'] = region
    data['keypair'] = keypair
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_azure(name: str, subscription_id: str, app_id: str, tenant_id: str, admin_password: str, secret: str,
                      mail: str, storageaccount: str,
                      client: str = None, debug: bool = False):
    """Create azure host"""
    data = {}
    data['name'] = name
    data['_type'] = 'azure'
    data['subscription_id'] = subscription_id
    data['app_id'] = app_id
    data['tenant_id'] = tenant_id
    data['secret'] = secret
    data['admin_password'] = admin_password
    data['mail'] = mail
    data['storageaccount'] = storageaccount
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_gcp(name: str, credentials: str, project: str, zone: str,
                    client: str = None, debug: bool = False):
    """Create gcp host"""
    data = {}
    data['name'] = name
    data['credentials'] = credentials
    data['project'] = project
    data['zone'] = zone
    data['_type'] = 'gcp'
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_ibm(name: str, iam_api_key: str, region: str, vpc: str, zone: str,
                    access_key_id: str, access_key_secret: str,
                    client: str = None, debug: bool = False):
    """Create ibm host"""
    data = {}
    data['name'] = name
    data['_type'] = 'ibm'
    data['iam_api_key'] = iam_api_key
    data['region'] = region
    data['vpc'] = vpc
    data['zone'] = zone
    data['access_key_id'] = access_key_id
    data['secret_access_key'] = access_key_secret
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_kubevirt(name: str, pool: str, token: str = None, ca: str = None, multus: bool = False,
                         cdi: bool = True, host: str = None, port: str = None,
                         client: str = None, debug: bool = False):
    """Create kubevirt host"""
    data = {}
    data['name'] = name
    data['_type'] = 'kubevirt'
    if pool is not None:
        data['pool'] = pool
    if token is not None:
        data['token'] = token
    if ca is not None:
        data['ca_file'] = ca
    data['multus'] = multus
    data['cdi'] = cdi
    if host is not None:
        data['host'] = host
    if port is not None:
        data['port'] = port
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_kvm(name: str, url: str, host: str = 'localhost', pool: str = 'default', user: str = 'root',
                    protocol: str = 'ssh', port: str = None,
                    client: str = None, debug: bool = False, region: str = None,
                    zone: str = None, namespace: str = None):
    """Create kvm host"""
    data = {}
    data['_type'] = 'kvm'
    data['host'] = host
    data['port'] = port
    data['user'] = user
    data['protocol'] = protocol
    data['url'] = url
    data['pool'] = pool
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_openstack(name: str, user: str, password: str, project: str, domain: str, auth_url: str,
                          client: str = None, debug: bool = False):
    """Create openstack host"""
    data = {}
    data['name'] = name
    data['_type'] = 'openstack'
    data['user'] = user
    data['password'] = password
    data['project'] = project
    data['domain'] = domain
    data['auth_url'] = auth_url
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_ovirt(name: str, pool: str, host: str, org: str, password: str, user: str = 'admin@internal',
                      datacenter: str = 'Default', cluster: str = 'Default', ca: str = None,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None):
    """Create ovirt host"""
    data = {}
    data['name'] = name
    data['_type'] = 'ovirt'
    data['host'] = host
    data['datacenter'] = datacenter
    data['ca_file'] = ca
    data['cluster'] = cluster
    data['org'] = org
    data['user'] = user
    data['password'] = password
    if pool is not None:
        data['pool'] = pool
    data['client'] = client
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_proxmox(name: str, host: str, user: str, password: str, insecure: bool = True, pool: str = None,
                        node: str = None,
                        client: str = None, debug: bool = False):
    """Create proxmox host"""
    data = {}
    data['name'] = name
    data['_type'] = 'proxmox'
    data['host'] = host
    data['user'] = user
    data['password'] = password
    if insecure:
        data['verify_ssl'] = False
    if pool is not None:
        data['pool'] = pool
    if node is not None:
        data['node'] = node
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_host_vsphere(name: str, host: str, user: str, password: str, datacenter: str, cluster: str, pool: str,
                        client: str = None, debug: bool = False):
    """Create vsphere host"""
    data = {}
    data['name'] = name
    data['_type'] = 'vsphere'
    data['host'] = host
    data['user'] = user
    data['password'] = password
    data['datacenter'] = datacenter
    data['cluster'] = cluster
    if pool is not None:
        data['pool'] = pool
    common.create_host(data)
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


@mcp.tool()
def create_ksushy_service(port: int = 9000, ipv6: bool = False, ssl: bool = False,
                          user: str = None, password: str = None, plan: str = None, bootonce: bool = False,
                          client: str = None, debug: bool = False):
    """Create ksushy service"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    baseconfig.deploy_ksushy_service(port=port, ipv6=ipv6, ssl=ssl, user=user,
                                     password=password, bootonce=bootonce, plan=plan)


@mcp.tool()
def create_kube(cluster: str, kubetype: str = 'generic', threaded: bool = False, force: bool = False,
                disks: list = [], nets: list = [], sno_vm: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create cluster"""
    if disks:
        overrides['disk_size'] = disks[0]['size'] if isinstance(disks[0], dict) else disks[0]
        if len(disks) > 1:
            overrides['extra_disks'] = disks[1:]
    if nets:
        overrides['network'] = nets[0]['name'] if isinstance(nets[0], dict) else nets[0]
        if len(nets) > 1:
            overrides['extra_networks'] = nets[1:]
    if threaded:
        overrides['threaded'] = threaded
    master_parameters = [key for key in overrides if 'master' in key]
    if master_parameters:
        master_parameters = ','.join(master_parameters)
        msg = f"parameters that contain master word need to be replaced with ctlplane. Found {master_parameters}"
        return {'result': 'failure', 'reason': msg}
    sno = kubetype == 'openshift-sno' or (kubetype == 'openshift' and 'sno' in overrides and overrides['sno'])
    offline = sno and not sno_vm and (client == 'fake' or common.need_fake())
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace, offline=offline)
    if force:
        overrides['kubetype'] = kubetype
        config.delete_kube(cluster, overrides=overrides)
    confpool = overrides.get('namepool') or overrides.get('confpool')
    if cluster is None and confpool is not None:
        cluster = config.get_name_from_confpool(confpool)
    clusterprofile = overrides.get('clusterprofile')
    if clusterprofile is not None:
        if clusterprofile not in config.clusterprofiles:
            msg = f"Clusterprofile {clusterprofile} not found"
            return {'result': 'failure', 'reason': msg}
        else:
            initial_apps = overrides.get('apps', [])
            clusterprofile = config.clusterprofiles[clusterprofile]
            clusterprofiles_apps = clusterprofile.get('apps', [])
            clusterprofile.update(overrides)
            overrides = clusterprofile
            overrides['apps'] = list(dict.fromkeys(clusterprofiles_apps + initial_apps))
    return config.create_kube(cluster, kubetype, overrides=overrides)


@mcp.tool()
def create_kubeadm_registry(plan: str = None,
                            client: str = None, debug: bool = False, region: str = None,
                            zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create generic registry"""
    if plan is None:
        plan = get_random_name()
    if 'cluster' not in overrides:
        overrides['cluster'] = plan
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_kubeadm_registry(plan, overrides=overrides)


@mcp.tool()
def create_lb(name: str = None, checkpath: str = '/index.html', checkport: int = 80, ip: str = None,
              ports: list = [], domain: str = None, internal: bool = False, vms: list = [],
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Create load balancer"""
    if name is None:
        name = get_random_name().replace('_', '-')
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain,
                                      checkport=checkport, internal=internal, ip=ip)


@mcp.tool()
def create_network(name: str, cidr: str, domain: str = None, plan: str = 'kvirt', dual_cidr: str = None,
                   dual_name: str = None, dhcp: bool = True, nodhcp: bool = False, isolated: bool = False,
                   client: str = None, debug: bool = False, region: str = None,
                   zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create network"""
    nodhcp = not dhcp if dhcp is not None else nodhcp
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    nat = not isolated
    dhcp = not nodhcp
    if dual_cidr is not None:
        overrides['dual_cidr'] = dual_cidr
    if dual_name is not None:
        overrides['dual_name'] = dual_name
    return k.create_network(name=name, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, overrides=overrides, plan=plan)


@mcp.tool()
def create_openshift_iso(cluster: str = None, ignitionfile: bool = False, direct: bool = False,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create openshift iso"""
    offline = client == 'fake' or common.need_fake()
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace, offline=offline)
    return config.create_openshift_iso(cluster, overrides=overrides, ignitionfile=ignitionfile, direct=direct)


@mcp.tool()
def create_openshift_registry(plan: str = None,
                              client: str = None, debug: bool = False, region: str = None,
                              zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create openshift registry"""
    if plan is None:
        plan = get_random_name()
    if 'cluster' not in overrides:
        overrides['cluster'] = plan
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_openshift_registry(plan, overrides=overrides)


@mcp.tool()
def create_plan(plan: str = None, ansible: bool = False, url: str = None, path: str = None, container: bool = False,
                threaded: bool = False, inputfile: str = 'kcli_plan.yml', force: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create plan"""
    # if container_mode():
    #    inputfile = f"/workdir/{inputfile}"
    if 'minimum_version' in overrides:
        minimum_version = overrides['minimum_version']
        current_version = get_git_version()[0]
        if current_version != 'N/A':
            if not compare_git_versions(minimum_version, current_version):
                msg = f"Current kcli version {current_version} lower than plan minimum version {minimum_version}"
                return {'result': 'failure', 'reason': msg}
    offline = overrides.get('offline', False)
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace, offline=offline)
    _type = config.ini[config.client].get('type', 'kvm')
    overrides.update({'type': _type})
    if plan is None:
        plan = get_random_name()
    if force:
        if plan is None:
            msg = "Force requires specifying a plan name"
            return {'result': 'failure', 'reason': msg}
        else:
            config.delete_plan(plan, unregister=config.rhnunregister)
    return config.plan(plan, ansible=ansible, url=url, path=path, container=container, inputfile=inputfile,
                       overrides=overrides, threaded=threaded)


@mcp.tool()
def create_pool(pool: str, pooltype: str = 'dir', path: str = None, thinpool: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> dict:
    """Create pool"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    if path is None:
        msg = "Missing path"
        return {'result': 'failure', 'reason': msg}
    return k.create_pool(name=pool, poolpath=path, pooltype=pooltype, thinpool=thinpool)


@mcp.tool()
def create_profile(profile: str,
                   client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Create profile"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.create_profile(profile, overrides=overrides)


@mcp.tool()
def create_securitygroup(securitygroup: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create security group"""
    securitygroup = securitygroup
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.create_security_group(securitygroup, overrides)


@mcp.tool()
def create_snapshot_plan(plan: str, snapshot: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None) -> dict:
    """Create snapshot plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.snapshot_plan(plan, snapshotname=snapshot)


@mcp.tool()
def create_subnet(name: str, cidr: str, isolated: bool = False, network: str = None, domain: str = None,
                  dhcp: bool = True, nodhcp: bool = False, dual_cidr: str = None, dual_name: str = None,
                  client: str = None, debug: bool = False, region: str = None, plan: str = 'kvirt',
                  zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create subnet"""
    if network is None and '-' in name:
        network = name.replace(f'-{name.split("-")[-1]}', '')
    if network is not None:
        overrides['network'] = network
    if cidr is None:
        msg = "Missing Cidr"
        return {'result': 'failure', 'reason': msg}
    dhcp = overrides.get('dhcp')
    nodhcp = not dhcp if dhcp is not None else nodhcp
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    nat = not isolated
    dhcp = not nodhcp
    if dual_cidr is not None:
        overrides['dual_cidr'] = dual_cidr
    if dual_name is not None:
        overrides['dual_name'] = dual_name
    return k.create_subnet(name, cidr, dhcp=dhcp, nat=nat, domain=domain, overrides=overrides, plan=plan)


@mcp.tool()
def create_vm(name: str, profile: str,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_vm(name, profile, overrides=overrides)


@mcp.tool()
def create_vmdata(name: str = None, profile: str = None,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None, overrides: dict = {}) -> str:
    """Create vmdata"""
    if name is None:
        get_random_name()
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_vm(name, profile, overrides=overrides, onlyassets=True)


@mcp.tool()
def create_vmdisk(name: str, diskname: str = None,
                  pool: str = 'default', size: int = 10, image: str = None, interface: str = 'virtio',
                  shareable: bool = False, force: bool = False, novm: bool = False,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Add disk to vm"""
    existing = diskname
    thin = overrides.get('thin', not shareable)
    if interface not in ['virtio', 'ide', 'scsi']:
        return {'result': 'failure', 'reason': "Incorrect disk interface. Choose between virtio, scsi or ide..."}
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    if force:
        diskname = f"{name}_0.img"
        info = k.info(name)
        disks = info['disks']
        size = disks[0]['size'] if disks else 30
        interface = disks[0]['format'] if disks else 'virtio'
        k.delete_disk(name=name, diskname=diskname, pool=pool)
        k.add_disk(name=name, size=size, pool=pool, interface=interface, diskname=diskname, thin=thin)
    return k.add_disk(name=name, size=size, pool=pool, image=image, interface=interface, novm=novm,
                      overrides=overrides, thin=thin, existing=existing, shareable=shareable)


@mcp.tool()
def create_vmnic(name: str, network: str, model: str = None,
                 client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> dict:
    """Add nic to vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    if network is None:
        msg = "Missing network"
        return {'result': 'failure', 'reason': msg}
    return k.add_nic(name=name, network=network, model=model)


@mcp.tool()
def create_vmsnapshot(snapshot: str, name: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> dict:
    """Create snapshot of vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.create_snapshot(snapshot, name)


@mcp.tool()
def create_web_service(port: int = 8000, ipv6: bool = False, ssl: bool = False,
                       client: str = None, debug: bool = False):
    """Create web service"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    baseconfig.deploy_web_service(port=port, ipv6=ipv6, ssl=ssl)


@mcp.tool()
def create_workflow(workflow: str, outputdir: str = None, render: bool = True,
                    client: str = None, debug: bool = False, region: str = None,
                    zone: str = None, namespace: str = None, overrides: dict = {}):
    """Create workflow"""
    if outputdir is not None:
        # if container_mode() and not outputdir.startswith('/'):
        #    outputdir = f"/workdir/{outputdir}"
        if os.path.exists(outputdir) and os.path.isfile(outputdir):
            msg = f"Invalid outputdir {outputdir}"
            return {'result': 'failure', 'reason': msg}
        elif not os.path.exists(outputdir):
            os.mkdir(outputdir)
    workflow = workflow
    if workflow is None:
        workflow = get_random_name()
    config = None
    if 'target' in overrides:
        user = None
        vmport = None
        target = overrides['target']
        if '@' in target:
            user, hostname = target.split('@')
        else:
            hostname = target
        if '.' not in hostname and ':' not in hostname:
            config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
            vmuser, vmip, vmport = _ssh_credentials(config.k, hostname)
            if vmip is not None:
                overrides['target'] = {'user': user or vmuser, 'port': vmport, 'ip': vmip, 'hostname': hostname}
    if config is None:
        config = Kbaseconfig(client=client, debug=debug)
    return config.create_workflow(workflow, overrides, outputdir=outputdir, run=not render)


@mcp.tool()
def delete_app(app: str, client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Delete application"""
    kubectl = which('kubectl') or which('oc')
    if kubectl is None:
        return {'result': 'failure', 'reason': "You need kubectl/oc to install apps"}
    if 'KUBECONFIG' in os.environ and not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.delete_app(app, overrides)


@mcp.tool()
def delete_bucket(buckets: list = [],
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None):
    """Delete bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for bucket in buckets:
        k.delete_bucket(bucket)


@mcp.tool()
def delete_bucketfile(bucket: str, path: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None):
    """Delete bucketfile from bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    k.delete_from_bucket(bucket, path)


@mcp.tool()
def delete_clusterprofile(clusterprofile: str,
                          client: str = None, debug: bool = False) -> dict:
    """Delete cluster profile"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.delete_clusterprofile(clusterprofile)


@mcp.tool()
def delete_confpool(confpool: str,
                    client: str = None, debug: bool = False) -> dict:
    """Delete configuration pool"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.delete_confpool(confpool)


@mcp.tool()
def delete_container(name: str,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> dict:
    """Delete container"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    cont = Kcontainerconfig(config, client=client).cont
    return cont.delete_container(name)


@mcp.tool()
def delete_dns(names: list, net: str, domain: str = None, allentries: bool = False,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None):
    """Delete dns entry"""
    domain = domain or net
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for name in names:
        k.delete_dns(name, domain, allentries=allentries)


@mcp.tool()
def delete_host(name: str,
                client: str = None, debug: bool = False) -> dict:
    """Delete host"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    return baseconfig.delete_host(name)


@mcp.tool()
def delete_image(image: str, pool: str = None,
                 client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> dict:
    """Delete image"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.delete_image(image, pool=pool)


@mcp.tool()
def delete_kube(cluster: str, allclusters: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None, overrides: dict = {}):
    """Delete cluster"""
    if client is not None:
        overrides['client'] = client
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    clusters = [c for c in config.list_kubes()] if allclusters else cluster
    for cluster in clusters:
        config.delete_kube(cluster, overrides=overrides)


@mcp.tool()
def delete_lb(names: list = [], client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Delete load balancer"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for name in names:
        config.delete_loadbalancer(name)


@mcp.tool()
def delete_network(names: list = [], force: bool = False,
                   client: str = None, debug: bool = False, region: str = None,
                   zone: str = None, namespace: str = None) -> dict:
    """Delete network"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for name in names:
        result = k.delete_network(name=name, force=force)
        if result['result'] != 'success':
            return result
    return {'result': 'success'}


@mcp.tool()
def delete_plan(plans: list = [], allplans: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> dict:
    """Delete plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    plans = [p[0] for p in config.list_plans()] if allplans else plans
    for plan in plans:
        result = config.delete_plan(plan, unregister=config.rhnunregister)
        if 'result' in result and result['result'] != 'success':
            return result
    return {'result': 'success'}


@mcp.tool()
def delete_pool(pool: str, full: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> dict:
    """Delete pool"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.delete_pool(name=pool, full=full)


@mcp.tool()
def delete_profile(profile: str,
                   client: str = None, debug: bool = False) -> dict:
    """Delete profile"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.delete_profile(profile)


@mcp.tool()
def delete_securitygroup(securitygroups: list = [],
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None):
    """Delete security group"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for securitygroup in securitygroups:
        k.delete_security_group(securitygroup)


@mcp.tool()
def delete_snapshot_plan(plan: str, snapshot: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None):
    """Delete snapshot plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for vm in sorted(k.list(), key=lambda x: x['name']):
        name = vm['name']
        if vm['plan'] == plan:
            k.delete_snapshot(snapshot, name)


@mcp.tool()
def delete_subnet(names: list = [], force: bool = False,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Delete subnet"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for name in names:
        result = k.delete_subnet(name=name, force=force)
        if result['result'] != 'success':
            return result
    return {'result': 'success'}


@mcp.tool()
def delete_vm(vm: str,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None) -> dict:
    """Delete vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.delete(vm)


@mcp.tool()
def delete_vmdisk(diskname: str, vm: str = None, pool: str = 'default',
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> dict:
    """Delete disk from vm"""
    novm = vm is None
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.delete_disk(name=vm, diskname=diskname, pool=pool, novm=novm)


@mcp.tool()
def delete_vmnic(name: str, interface: str = None,
                 client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> dict:
    """Delete nic from vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.delete_nic(name, interface)


@mcp.tool()
def delete_vmsnapshot(snapshot: str, name: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> dict:
    """Delete snapshot of vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.delete_snapshot(snapshot, name)


@mcp.tool()
def disable_host(name: str,
                 client: str = None, debug: bool = False) -> dict:
    """Disable host"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    return baseconfig.disable_host(name)


@mcp.tool()
def download_bucketfile(bucket: str, path: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None):
    """Download bucketfile from bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    k.download_from_bucket(bucket, path)


@mcp.tool()
def download_helm(version: str = 'latest',
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None):
    """Download helm"""
    common.get_helm(version=version, debug=debug)


@mcp.tool()
def download_hypershift(version: str = 'latest',
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None):
    """Download hypershift"""
    common.get_hypershift(version=version, debug=debug)


@mcp.tool()
def download_image(image: str, name: str = None, cmds: list = [], qemu: bool = False,
                   installer: bool = False,
                   client: str = None, debug: bool = False, region: str = None,
                   zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Download image"""
    arch = overrides.get('arch', 'x86_64')
    valid_archs = ['x86_64', 'aarch64', 'ppc64le', 's390x']
    if arch not in valid_archs:
        return {'result': 'failure', 'reason': "Arch needs to belong to {','.join(valid_archs)}"}
    size = overrides.get('size')
    if size is not None:
        if size.isdigit():
            size = int(size)
        else:
            return {'result': 'failure', 'reason': "Size needs to be an integer"}
    kvm_openstack = not qemu
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    pool = overrides.get('pool') or config.pool
    return config.download_image(pool=pool, image=image, cmds=cmds, size=size, arch=arch,
                                 kvm_openstack=kvm_openstack, rhcos_installer=installer, name=name)


@mcp.tool()
def download_iso(url: str, pool: str = None,
                 client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> dict:
    "Download iso"
    iso = os.path.basename(url)
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    pool = pool or config.pool
    return config.download_image(pool=pool, image=iso, url=url)


@mcp.tool()
def download_kubeconfig(cluster: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None) -> str:
    """Download kubeconfig"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if config.type != 'web':
        return "Downloading kubeconfig is only available for web provider"
    return config.k.download_kubeconfig(cluster).decode("UTF-8") or f"Cluster {cluster} was not found"


@mcp.tool()
def download_kubectl(version: str = 'latest',
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None):
    """Download kubectl"""
    common.get_kubectl(version=version, debug=debug)


@mcp.tool()
def download_oc_mirror(version: str = 'stable', tag: str = None,
                       client: str = None, debug: bool = False, region: str = None,
                       zone: str = None, namespace: str = None):
    """Download oc-mirror"""
    common.get_oc_mirror(version=version, tag=tag or OPENSHIFT_TAG, debug=debug)


@mcp.tool()
def download_oc(version: str = 'stable', tag: str = None,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None):
    """Download oc"""
    common.get_oc(version=version, tag=tag or OPENSHIFT_TAG, debug=debug)


@mcp.tool()
def download_openshift_installer(client: str = None, debug: bool = False, overrides: dict = {}) -> int:
    """Download openshift-installer"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.download_openshift_installer(overrides)


@mcp.tool()
def download_plan(plan: str = None, url: str = None,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> dict:
    """Download plan"""
    if plan is None:
        plan = get_random_name()
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.plan(plan, url=url, download=True)


@mcp.tool()
def enable_host(name: str,
                client: str = None, debug: bool = False) -> dict:
    """Enable host"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    return baseconfig.enable_host(name)


@mcp.tool()
def export_vm(names: list = [], image: str = None,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None) -> dict:
    """Export vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if not names:
        names = [common.get_lastvm(config.client)]
    k = config.k
    for name in names:
        result = k.export(name=name, image=image)
        if result['result'] != 'success':
            return result
    return {'result': 'success'}


@mcp.tool()
def get_changelog(diff: str = None) -> str:
    """Returns kcli changelog between diff and main"""
    return common.get_changelog(diff)


@mcp.tool()
def get_version() -> str:
    """Returns kcli version"""
    full_version = f"version: {VERSION}"
    git_version, git_date = get_git_version()
    full_version += f" commit: {git_version} {git_date}"
    update = 'N/A'
    if git_version != 'N/A':
        try:
            response = json.loads(urlopen("https://api.github.com/repos/karmab/kcli/commits/main", timeout=5).read())
            upstream_version = response['sha'][:7]
            update = upstream_version != git_version
        except:
            pass
    full_version += f" Available Updates: {update}"
    return full_version


@mcp.tool()
def info_app(app: str, client: str = None, debug: bool = False) -> str:
    """Provide information on app"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.info_app(app)


@mcp.tool()
def info_baremetal_host(url: str, user: str, password: str, full: bool = False,
                        debug: bool = False) -> dict:
    """Provide information on baremetal host"""
    return common.info_baremetal_host(url, user, password, debug=debug, full=full)


@mcp.tool()
def info_clusterprofile(clusterprofile: str,
                        client: str = None, debug: bool = False) -> dict:
    """Provide information on cluster profile"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    if clusterprofile not in baseconfig.clusterprofiles:
        return {'result': 'failure', 'reason': f"Clusterprofile {clusterprofile} not found"}
    else:
        return baseconfig.clusterprofiles[clusterprofile]


@mcp.tool()
def info_confpool(confpool: str,
                  client: str = None, debug: bool = False) -> dict:
    """Provide information on configuration pool"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    if confpool not in baseconfig.confpools:
        return {'result': 'failure', 'reason': f"Confpool {confpool} not found"}
    else:
        return baseconfig.confpools[confpool]


@mcp.tool()
def info_host(client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None) -> str:
    """Provide information on host"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    common.pretty_print(k.info_host(), width=100)


@mcp.tool()
def info_keyword(keyword: str,
                 client: str = None, debug: bool = False) -> str:
    """Provide information on keyword"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.info_keyword(keyword)


@mcp.tool()
def info_kube(cluster: str = None, kubetype: str = 'generic',
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None) -> str:
    """Provide information on cluster"""
    if kubetype not in ['generic', 'kubeadm', 'openshift', 'openshift-sno', 'aks', 'gke', 'eks',
                        'microshift', 'hypershift', 'rke2', 'k3s']:
        return "Invalid kubetype"
    openshift = kubetype == 'openshift'
    if kubetype in ['aks', 'eks', 'gke']:
        baseconfig = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    else:
        baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    if cluster is not None:
        if kubetype == 'aks':
            status = baseconfig.info_specific_aks(cluster)
        elif kubetype == 'eks':
            status = baseconfig.info_specific_eks(cluster)
        elif kubetype == 'gke':
            status = baseconfig.info_specific_gke(cluster)
        else:
            status = baseconfig.info_specific_kube(cluster, openshift)
        if status is None or not status:
            return ''
        else:
            kubetable = ["Name", "Status", "Role", "Age", "Version", "Ip"]
            kubetable.title = f"{status['version'].strip()}"
            for node in status['nodes']:
                kubetable.append(node)
            return kubetable
    else:
        if kubetype == 'openshift':
            return baseconfig.info_kube_openshift(quiet=True)
        elif kubetype == 'openshift-sno':
            return baseconfig.info_openshift_sno(quiet=True)
        elif kubetype == 'hypershift':
            return baseconfig.info_kube_hypershift(quiet=True)
        elif kubetype == 'microshift':
            return baseconfig.info_kube_microshift(quiet=True)
        elif kubetype == 'k3s':
            return baseconfig.info_kube_k3s(quiet=True)
        elif kubetype == 'rke2':
            return baseconfig.info_kube_rke2(quiet=True)
        elif kubetype == 'gke':
            return baseconfig.info_kube_gke(quiet=True)
        elif kubetype == 'aks':
            return baseconfig.info_kube_aks(quiet=True)
        elif kubetype == 'eks':
            return baseconfig.info_kube_eks(quiet=True)
        else:
            return baseconfig.info_kube_generic(quiet=True)


@mcp.tool()
def info_kubeadm_registry(client: str = None, debug: bool = False) -> str:
    """Provide information on generic registry"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.info_kubeadm_registry()


@mcp.tool()
def info_network(network: str,
                 client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> str:
    """Provide information on network"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    networkinfo = config.k.info_network(network)
    if networkinfo:
        return common.pretty_print(networkinfo)
    else:
        return f"No information found for network {network}"


@mcp.tool()
def info_openshift_registry(client: str = None, debug: bool = False) -> str:
    """Provide information on openshift registry"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.info_openshift_registry()


@mcp.tool()
def info_plan(plan: str = None, url: str = None, path: str = None, inputfile: str = 'kcli_plan.yml',
              quiet: bool = False,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None, overrides: dict = {}) -> str:
    """Provide information on plan"""
    # if container_mode():
    #    inputfile = f"/workdir/{inputfile}"
    if plan is not None:
        config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
        _list = config.info_specific_plan(plan, quiet=quiet)
        if overrides:
            _list = filter_info_plan(_list, overrides)
        return _parse_vms_list(_list, overrides)
    elif url is None:
        baseconfig = Kbaseconfig(client=client, debug=debug)
        return baseconfig.info_plan(inputfile, quiet=quiet)
    else:
        config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
        return config.plan('info', url=url, path=path, inputfile=inputfile, info=True, quiet=quiet)


@mcp.tool()
def info_plantype(plantype: str,
                  client: str = None, debug: bool = False) -> str:
    """Provide information on plantype"""
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.info_plantype(plantype)


@mcp.tool()
def info_profile(profile: str,
                 client: str = None, debug: bool = False) -> dict:
    """Provide information on profile"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    if profile not in baseconfig.list_profiles():
        return {'result': 'failure', 'reason': f"Profile {profile} not found"}
    else:
        return baseconfig.profiles[profile]


@mcp.tool()
def info_subnet(subnet: str,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None):
    """Provide information on subnet"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    networkinfo = config.k.info_subnet(subnet)
    if networkinfo:
        return common.pretty_print(networkinfo)
    else:
        return f"No information found for subnet {subnet}"


@mcp.tool()
def info_vm(name: str,
            client: str = None, debug: bool = False, region: str = None,
            zone: str = None, namespace: str = None) -> dict:
    """Get info of vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.info(name)


@mcp.tool()
def install_provider(provider: str, pip: bool = False,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None):
    """Install provider"""
    common.install_provider(provider, pip=pip)


@mcp.tool()
def list_apps(client: str = None, debug: bool = False, installed: bool = False, overrides: dict = {}) -> list:
    """List applications"""
    kubectl = which('kubectl') or which('oc')
    if kubectl is None:
        return {'result': 'failure', 'reason': "You need kubectl/oc to install apps"}
    if 'KUBECONFIG' in os.environ and not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=True)
    return baseconfig.list_apps(quiet=True, installed=installed, overrides=overrides)


@mcp.tool()
def list_available_images(client: str = None, debug: bool = False, region: str = None,
                          zone: str = None, namespace: str = None) -> list:
    """List available images"""
    return IMAGES


@mcp.tool()
def list_bucketfiles(bucket: str,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> list:
    """List bucketfiles of bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_bucketfiles(bucket)


@mcp.tool()
def list_buckets(client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> list:
    """List buckets"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_buckets()


@mcp.tool()
def list_clients(client: str = None, debug: bool = False) -> list:
    """List clients"""
    clientstable = ["Client", "Type", "Enabled", "Current"]
    baseconfig = Kbaseconfig(client=client, debug=debug)
    for client in sorted(baseconfig.clients):
        enabled = baseconfig.ini[client].get('enabled', True)
        _type = baseconfig.ini[client].get('type', 'kvm')
        if client == baseconfig.client:
            clientstable.append([client, _type, enabled, 'X'])
        else:
            clientstable.append([client, _type, enabled, ''])
    return clientstable


@mcp.tool()
def list_clusterprofiles(client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None) -> list:
    """List cluster profiles"""
    return Kbaseconfig(client).list_clusterprofiles()


@mcp.tool()
def list_clusters(client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> list:
    """List clusters"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_kubes()


@mcp.tool()
def list_confpools(client: str = None, debug: bool = False, region: str = None,
                   zone: str = None, namespace: str = None) -> list:
    """List configuration pools"""
    return Kbaseconfig(client).list_confpools()


@mcp.tool()
def list_containerimages(client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None) -> list:
    """List container images"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if config.type not in ['kvm', 'proxmox']:
        return ["Operation not supported on this kind of client"]
    cont = Kcontainerconfig(config, client=client).cont
    return cont.list_images()


@mcp.tool()
def list_containerprofiles(client: str = None, debug: bool = False, region: str = None,
                           zone: str = None, namespace: str = None) -> list:
    """List container profiles"""
    return Kbaseconfig(client).list_containerprofiles()


@mcp.tool()
def list_containers(client: str = None, debug: bool = False, region: str = None,
                    zone: str = None, namespace: str = None) -> list:
    """List containers"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.list_containers()


@mcp.tool()
def list_dns_entries(domain: str = None,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> list:
    """List dns entries"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if domain is None:
        return config.k.list_dns_zones()
    else:
        return config.k.list_dns_(domain)


@mcp.tool()
def list_flavors(client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> list:
    """List flavors"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_flavors()


@mcp.tool()
def list_images(client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> list:
    """List images"""
    return Kconfig(client=client).k.volumes()


@mcp.tool()
def list_isos(client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None) -> list:
    """List isos"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.volumes(iso=True)


@mcp.tool()
def list_keywords(client: str = None, debug: bool = False):
    """List keywords"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    default = baseconfig.default
    keywordstable = ["Keyword", "Default Value", "Current Value"]
    keywords = baseconfig.list_keywords()
    for keyword in sorted(keywords):
        value = keywords[keyword]
        default_value = default.get(keyword)
        keywordstable.append([keyword, default_value, value])
    return keywordstable


@mcp.tool()
def list_lbs(client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> list:
    """List load balancers"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.list_loadbalancers()


@mcp.tool()
def list_networks(client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> dict:
    """List networks"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_networks()


@mcp.tool()
def list_plans(client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None) -> list:
    """List plans"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_plans()


@mcp.tool()
def list_plansnapshots(plan: str,
                       client: str = None, debug: bool = False, region: str = None,
                       zone: str = None, namespace: str = None) -> list:
    """List plan snapshots"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    _list = config.info_specific_plan(plan, quiet=True)
    if not _list:
        return [f"Plan {plan} not found"]
    return k.list_snapshots(_list[0]['name'])


@mcp.tool()
def list_plantypes(client: str = None, debug: bool = False, region: str = None,
                   zone: str = None, namespace: str = None) -> list:
    """List plan types"""
    return sorted(PLANTYPES)


@mcp.tool()
def list_pools(client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None) -> list:
    """List pools"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_pools()


@mcp.tool()
def list_profiles(client: str = None, debug: bool = False) -> dict:
    """List profiles"""
    return Kbaseconfig(client=client, debug=debug).list_profiles()


@mcp.tool()
def list_securitygroups(network: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None) -> list:
    """List security groups"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_security_groups(network=network)


@mcp.tool()
def list_subnets(client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> list:
    """List subnets"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_subnets()


@mcp.tool()
def list_vmdisks(client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> list:
    """List vm disks"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_disks()


@mcp.tool()
def list_vms(client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> list:
    """List vms"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list()


@mcp.tool()
def list_vmsnapshots(name: str,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> list:
    """List snapshots of vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    snapshots = k.list_snapshots(name)
    if isinstance(snapshots, dict):
        return [f"Vm {name} not found"]
    else:
        return snapshots


@mcp.tool()
def render_file(inputfile: str = 'kcli_plan.yml', ignore: bool = False, offline: bool = False, cmd: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None, initial_overrides: dict = {}) -> str:
    """Render inputfile"""
    plan = None
    overrides = {}
    allparamfiles = [paramfile for paramfile in glob("*_default.y*ml")]
    for paramfile in allparamfiles:
        overrides.update(common.get_overrides(paramfile=paramfile))
    overrides.update(initial_overrides)
    # if container_mode():
    #    inputfile = f"/workdir/{inputfile}"
    baseconfig = Kbaseconfig(client=client, debug=debug, offline=offline)
    default_data = {f'config_{k}': baseconfig.default[k] for k in baseconfig.default}
    client_data = {f'config_{k}': baseconfig.ini[baseconfig.client][k] for k in baseconfig.ini[baseconfig.client]}
    client_data['config_type'] = client_data.get('config_type', 'kvm')
    client_data['config_host'] = client_data.get('config_host', '127.0.0.1')
    default_user = getuser() if client_data['config_type'] == 'kvm'\
        and client_data['config_host'] in ['localhost', '127.0.0.1'] else 'root'
    client_data['config_user'] = client_data.get('config_user', default_user)
    client_data['config_client'] = baseconfig.client
    config_data = default_data.copy()
    config_data.update(client_data)
    overrides.update(config_data)
    if not os.path.exists(inputfile):
        return (f"Error: Input file {inputfile} not found")
    renderfile = baseconfig.process_inputfile(plan, inputfile, overrides=overrides, ignore=ignore)
    if cmd:
        return convert_yaml_to_cmd(yaml.safe_load(renderfile))
    else:
        return renderfile


@mcp.tool()
def reset_baremetal_host(url: str, user: str, password: str,
                         debug: bool = False) -> dict:
    """Reset baremetal host"""
    return common.reset_baremetal_host(url, user, password, debug=debug)


@mcp.tool()
def restart_container(name: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> dict:
    """Restart container"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    cont = Kcontainerconfig(config, client=client).cont
    cont.stop_container(name)
    return cont.start_container(name)


@mcp.tool()
def restart_plan(plans: list = [], soft: bool = False,
                 client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None):
    """Restart plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for plan in plans:
        result1 = config.stop_plan(plan, soft=soft)
        result2 = config.start_plan(plan)
        if 'result' in result1 and result1['result'] == 'success'\
           and 'result' in result2 and result2['result'] == 'success':
            continue
        elif result1['result'] != 'success':
            return result1
        else:
            return result2
    return {'result': 'success'}


@mcp.tool()
def restart_vm(name: str,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None) -> dict:
    """Restart vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.restart(name)


@mcp.tool()
def revert_plansnapshot(plan: str, snapshot: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None) -> dict:
    """Revert snapshot plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.revert_plan(plan, snapshotname=snapshot)


@mcp.tool()
def revert_vmsnapshot(snapshot: str, name: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> dict:
    """Revert snapshot of vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.revert_snapshot(snapshot, name)


@mcp.tool()
def scale_kube(cluster: str, kubetype: str = 'generic', ctlplanes: Optional[int] = None, workers: Optional[int] = None,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Scale cluster"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if ctlplanes is not None:
        overrides['ctlplanes'] = ctlplanes
    if workers is not None:
        overrides['workers'] = workers
    return config.scale_kube(cluster, kubetype, overrides=overrides)


@mcp.tool()
def scp_vm(source: str, destination: str,
           identityfile: str = None, recursive: bool = False, user: str = None, vmport: str = None,
           client: str = None, debug: bool = False, region: str = None,
           zone: str = None, namespace: str = None):
    """Scp from source to destination"""
    # source = f"/workdir/{source}" if container_mode() else source
    # destination = args.destination[0]
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    tunnel = baseconfig.tunnel
    tunnelhost = baseconfig.tunnelhost
    tunnelport = baseconfig.tunnelport
    tunneluser = baseconfig.tunneluser
    if tunnel and tunnelhost is None:
        return "Tunnel requested but no tunnelhost defined"
    insecure = baseconfig.insecure
    if len(source.split(':')) == 2:
        name, source = source.split(':')
        download = True
    elif len(destination.split(':')) == 2:
        name, destination = destination.split(':')
        download = False
    else:
        return "Couldn't run scp"
    if '@' in name and len(name.split('@')) == 2:
        user, name = name.split('@')
    scpcommand = None
    if scpcommand is None:
        config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
        k = config.k
        u, ip, vmport = common._ssh_credentials(k, name)
        if ip is None:
            return
        if user is None:
            user = config.vmuser if config.vmuser is not None else u
        if vmport is None and config.vmport is not None:
            vmport = config.vmport
        if config.type in ['kvm', 'packet'] and '.' not in ip and ':' not in ip:
            vmport = ip
            ip = '127.0.0.1'
        scpcommand = common.scp(name, ip=ip, user=user, source=source, destination=destination, recursive=recursive,
                                tunnel=tunnel, tunnelhost=tunnelhost, tunnelport=tunnelport, tunneluser=tunneluser,
                                debug=config.debug, download=download, vmport=vmport, insecure=insecure,
                                identityfile=identityfile)
    if scpcommand is not None:
        return scpcommand
    else:
        return "Couldn't run scp"


@mcp.tool()
def ssh_vm(name: str = None, local: bool = False, remote: bool = False, D: bool = False, X: bool = False,
           Y: bool = False, pty: bool = False, identityfile: str = None, user: str = None, vmport: str = None,
           client: str = None, debug: bool = False, region: str = None,
           zone: str = None, namespace: str = None, overrides: dict = {}) -> str:
    """Print ssh command to vm"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    if name is None:
        name = [common.get_lastvm(baseconfig.client)]
    tunnel = baseconfig.tunnel
    tunnelhost = baseconfig.tunnelhost
    tunnelport = baseconfig.tunnelport
    tunneluser = baseconfig.tunneluser
    if tunnel and tunnelhost is None and baseconfig.type != 'kubevirt':
        return "Tunnel requested but no tunnelhost defined"
    insecure = baseconfig.insecure
    if len(name) > 1:
        cmd = ' '.join(name[1:])
    else:
        cmd = None
    name = name[0]
    if '@' in name and len(name.split('@')) == 2:
        user = name.split('@')[0]
        name = name.split('@')[1]
    if os.path.exists("/i_am_a_container") and not os.path.exists("/root/.kcli/config.yml")\
            and not os.path.exists("/root/.ssh/config"):
        insecure = True
    sshcommand = None
    if sshcommand is None:
        config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
        k = config.k
        u, ip, vmport = common._ssh_credentials(k, name)
        if tunnel and tunnelhost is None and config.type == 'kubevirt':
            info = k.info(name, debug=False)
            tunnelhost = k.node_host(name=info.get('host'))
            if tunnelhost is None:
                return f"No valid node ip found for {name}"
        if ip is None:
            return
        if user is None:
            user = config.vmuser if config.vmuser is not None else u
        if vmport is None and config.vmport is not None:
            vmport = config.vmport
        if config.type in ['kvm', 'packet'] and '.' not in ip and ':' not in ip:
            vmport = ip
            ip = config.host
        sshcommand = common.ssh(name, ip=ip, user=user, local=local, remote=remote, tunnel=tunnel,
                                tunnelhost=tunnelhost, tunnelport=tunnelport, tunneluser=tunneluser,
                                insecure=insecure, cmd=cmd, X=X, Y=Y, D=D, debug=debug, vmport=vmport,
                                identityfile=identityfile, pty=pty)
    if sshcommand is not None:
        return sshcommand
    else:
        return f"Couldnt ssh to {name}"


@mcp.tool()
def start_baremetal_host(url: str, user: str, password: str,
                         debug: bool = False, overrides: dict = {}) -> dict:
    """Start baremetal host"""
    return common.start_baremetal_host(url, user, password, overrides, debug=debug)


@mcp.tool()
def start_container(name: str,
                    client: str = None, debug: bool = False, region: str = None,
                    zone: str = None, namespace: str = None) -> dict:
    """Start container"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    cont = Kcontainerconfig(config, client=client).cont
    return cont.start_container(name)


@mcp.tool()
def start_plan(plans: list = [],
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None):
    """Start plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for plan in plans:
        result = config.start_plan(plan)
        if 'result' in result and result['result'] != 'success':
            return result
    return {'result': 'success'}


@mcp.tool()
def start_vm(name: str,
             client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> dict:
    """Start vm"""
    return Kconfig(client).k.start(name)


@mcp.tool()
def stop_baremetal_host(url: str, user: str, password: str,
                        debug: bool = False) -> dict:
    """Stop baremetal host"""
    return common.stop_baremetal_host(url, user, password, debug=debug)


@mcp.tool()
def stop_container(name: str,
                   client: str = None, debug: bool = False, region: str = None,
                   zone: str = None, namespace: str = None) -> dict:
    """Stop container"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    cont = Kcontainerconfig(config, client=client).cont
    return cont.stop_container(name)


@mcp.tool()
def stop_plan(plans: list = [], soft: bool = False,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Stop plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for plan in plans:
        result = config.stop_plan(plan, soft=soft)
        if 'result' in result and result['result'] != 'success':
            return result
    return {'result': 'success'}


@mcp.tool()
def stop_vm(name: str,
            client: str = None, debug: bool = False, region: str = None,
            zone: str = None, namespace: str = None) -> dict:
    """Stop vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.stop(name)


@mcp.tool()
def switch_host(host: str,
                client: str = None, debug: bool = False):
    """Switch host"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    return baseconfig.switch_host(host)


@mcp.tool()
def switch_kubeconfig(name: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> str:
    """Switch kubeconfig"""
    homedir = os.path.expanduser("~")
    clusterdir = os.path.expanduser(f"{homedir}/.kcli/clusters/{name}")
    kubeconfig = f'{clusterdir}/auth/kubeconfig'
    if not os.path.exists(kubeconfig):
        return f"{kubeconfig} not found"
    if not os.path.exists(f"{homedir}/.kube"):
        os.mkdir(f"{homedir}/.kube")
    if os.path.exists(f"{homedir}/.kube/config") and not os.path.exists(f"{homedir}/.kube/config.old"):
        copy2(f"{homedir}/.kube/config", f"{homedir}/.kube/config.old")
        if not os.path.exists(f"{homedir}/.kcli/clusters/old/auth"):
            os.makedirs(f"{homedir}/.kcli/clusters/old/auth")
            copy2(f"{homedir}/.kube/config", f"{homedir}/.kcli/clusters/old/auth/kubeconfig")
    copy2(kubeconfig, f"{homedir}/.kube/config")
    if name == 'old':
        os.remove(clusterdir)
        if os.path.exists(f"{homedir}/.kube/config.old"):
            os.remove(f"{homedir}/.kube/config.old")
    if 'KUBECONFIG' in os.environ:
        return "run the following command for this to apply\nunset KUBECONFIG"


@mcp.tool()
def sync_config(network: str,
                client: str = None, debug: bool = False) -> dict:
    """Sync config to cluster"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    return baseconfig.import_in_kube(network=network)


@mcp.tool()
def update_baremetal_host(url: str, user: str, password: str,
                          debug: bool = False, overrides: dict = {}) -> dict:
    """update baremetal host"""
    return common.update_baremetal_host(url, user, password, overrides, debug=debug)


@mcp.tool()
def update_clusterprofile(clusterprofile: str,
                          client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Update cluster profile"""
    baseconfig = Kbaseconfig(client=client, debug=debug)
    return baseconfig.update_clusterprofile(clusterprofile, overrides=overrides)


@mcp.tool()
def update_confpool(confpool: str,
                    client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Update configuration pool"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.update_confpool(confpool, overrides=overrides)


@mcp.tool()
def update_kube(cluster: str, kubetype: str = 'generic',
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Update cluster"""
    data = {'kube': cluster, 'kubetype': kubetype}
    plan = None
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if not os.path.exists(clusterdir):
        msg = f"Cluster directory {clusterdir} not found..."
        return {'result': 'failure', 'reason': msg}
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    if plan is None:
        plan = cluster
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.update_kube(plan, kubetype, overrides=data)


@mcp.tool()
def update_network(name: str, domain: str = None, plan: str = None,
                   nat: bool = True, nodhcp: bool = False,
                   client: str = None, debug: bool = False, region: str = None,
                   zone: str = None, namespace: str = None, overrides: dict = {}):
    """Update network"""
    dhcp = not nodhcp
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.update_network(name=name, dhcp=dhcp, nat=nat, domain=domain, overrides=overrides, plan=plan)


@mcp.tool()
def update_openshift_registry(plan: str,
                              client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Update openshift registry"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.update_openshift_registry(plan, overrides=overrides)


@mcp.tool()
def update_plan(plan: str = None, url: str = None, path: str = None, container: bool = False,
                threaded: bool = False, inputfile: str = 'kcli_plan.yml', force: bool = False,
                autostart: bool = False, noautostart: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Update plan"""
    # if container_mode():
    #   inputfile = f"/workdir/{inputfile}"
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if autostart or noautostart:
        if config.type != 'kvm':
            msg = "Changing autostart of vms only apply to kvm"
            return {'result': 'failure', 'reason': msg}
        elif autostart:
            config.autostart_plan(plan)
        elif noautostart:
            config.noautostart_plan(plan)
        return
    return config.plan(plan, url=url, path=path, container=container, inputfile=inputfile, overrides=overrides,
                       update=True)


@mcp.tool()
def update_profile(profile: str,
                   client: str = None, debug: bool = False, overrides: dict = {}) -> dict:
    """Update profile"""
    baseconfig = Kbaseconfig(client=client, debug=debug, quiet=True)
    return baseconfig.update_profile(profile, overrides=overrides)


@mcp.tool()
def update_securitygroup(securitygroup: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None, overrides: dict = {}):
    """Update security group"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    result = config.k.update_security_group(name=securitygroup, overrides=overrides)
    common.handle_response(result, securitygroup, element='SecurityGroup', action='updated')


@mcp.tool()
def update_subnet(name: str,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Update subnet"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.update_subnet(name=name, overrides=overrides)


@mcp.tool()
def update_vm(name: str,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Update vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.update_vm(name, overrides)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
