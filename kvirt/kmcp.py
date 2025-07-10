import argparse
import asyncio
from fastmcp import FastMCP, Context
from kvirt import common
from kvirt.common import get_git_version, compare_git_versions
from kvirt.config import Kbaseconfig, Kconfig
from kvirt.nameutils import get_random_name
from typing import Optional
from urllib.request import urlopen


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


core = FastMCP("kcli-core")
cloud = FastMCP("kcli-cloud")
baremetal = FastMCP("kcli-baremetal")


@core.prompt()
def prompt() -> str:
    """Indicates contexts of questions related to kcli"""
    return """You are a helpful assistant who knows everything about kcli, a powerful client and library written
    in Python and meant to interact with different virtualization providers, easily deploy and customize VMs or
    full kubernetes/OpenShift clusters. All information about kcli is available at
    https://github.com/karmab/kcli/blob/main/docs/index.md"""


@core.resource("resource://kcli-doc.md")
def get_doc() -> str:
    """Provides kcli documentation"""
    url = 'https://raw.githubusercontent.com/karmab/kcli/refs/heads/main/docs/index.md'
    return urlopen(url).read().decode('utf-8')


@core.tool()
def create_kube(context: Context,
                cluster: str, kubetype: str = 'generic', threaded: bool = False, force: bool = False,
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


@core.tool()
def create_network(context: Context,
                   name: str, cidr: str, domain: str = None, plan: str = 'kvirt', dual_cidr: str = None,
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


@core.tool()
def create_plan(context: Context,
                plan: str = None, ansible: bool = False, url: str = None, path: str = None, container: bool = False,
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


@core.tool()
def create_pool(context: Context,
                pool: str, pooltype: str = 'dir', path: str = None, thinpool: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> dict:
    """Create pool"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    if path is None:
        msg = "Missing path"
        return {'result': 'failure', 'reason': msg}
    return k.create_pool(name=pool, poolpath=path, pooltype=pooltype, thinpool=thinpool)


@core.tool()
def create_vm(context: Context,
              name: str, profile: str,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_vm(name, profile, overrides=overrides)


@core.tool()
def delete_kube(context: Context,
                cluster: str, allclusters: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None, overrides: dict = {}):
    """Delete cluster"""
    if client is not None:
        overrides['client'] = client
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    clusters = [c for c in config.list_kubes()] if allclusters else cluster
    for cluster in clusters:
        config.delete_kube(cluster, overrides=overrides)


@core.tool()
def delete_network(context: Context,
                   names: list = [], force: bool = False,
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


@core.tool()
def delete_plan(context: Context,
                plans: list = [], allplans: bool = False,
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


@core.tool()
def delete_pool(context: Context,
                pool: str, full: bool = False,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> dict:
    """Delete pool"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.delete_pool(name=pool, full=full)


@core.tool()
def delete_vm(context: Context,
              vm: str,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None) -> dict:
    """Delete vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.delete(vm)


@core.tool()
def info_vm(context: Context,
            name: str,
            client: str = None, debug: bool = False, region: str = None,
            zone: str = None, namespace: str = None) -> dict:
    """Get info of vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.info(name)


@core.tool()
def list_clients(context: Context,
                 client: str = None, debug: bool = False) -> list:
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


@core.tool()
def list_clusters(context: Context,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> list:
    """List clusters"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_kubes()


@core.tool()
def list_images(context: Context,
                client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> list:
    """List images"""
    return Kconfig(client=client).k.volumes()


@core.tool()
def list_networks(context: Context,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> dict:
    """List networks"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_networks()


@core.tool()
def list_pools(context: Context,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None) -> list:
    """List pools"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_pools()


@core.tool()
def list_vms(context: Context,
             client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> list:
    """List vms"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list()


@core.tool()
def scale_kube(context: Context,
               cluster: str, kubetype: str = 'generic', ctlplanes: Optional[int] = None, workers: Optional[int] = None,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Scale cluster"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if ctlplanes is not None:
        overrides['ctlplanes'] = ctlplanes
    if workers is not None:
        overrides['workers'] = workers
    return config.scale_kube(cluster, kubetype, overrides=overrides)


@core.tool()
def start_plan(context: Context,
               plans: list = [],
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None):
    """Start plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for plan in plans:
        result = config.start_plan(plan)
        if 'result' in result and result['result'] != 'success':
            return result
    return {'result': 'success'}


@core.tool()
def start_vm(context: Context,
             name: str,
             client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> dict:
    """Start vm"""
    return Kconfig(client).k.start(name)


@core.tool()
def stop_plan(context: Context,
              plans: list = [], soft: bool = False,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Stop plan"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for plan in plans:
        result = config.stop_plan(plan, soft=soft)
        if 'result' in result and result['result'] != 'success':
            return result
    return {'result': 'success'}


@core.tool()
def stop_vm(context: Context,
            name: str,
            client: str = None, debug: bool = False, region: str = None,
            zone: str = None, namespace: str = None) -> dict:
    """Stop vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.stop(name)


@cloud.tool()
def create_bucket(context: Context,
                  buckets: list = [], public: bool = False,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None):
    """Create bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for bucket in buckets:
        k.create_bucket(bucket, public=public)


@cloud.tool()
def create_bucketfile(context: Context,
                      bucket: str, path: str, temp: str = None, public: bool = False,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> str:
    """Create bucketfile in bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.upload_to_bucket(bucket, path, temp_url=temp, public=public)


@cloud.tool()
def create_dns(context: Context,
               names: list, net: str, domain: str, ip: str, alias: str,
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


@cloud.tool()
def create_lb(context: Context,
              name: str = None, checkpath: str = '/index.html', checkport: int = 80, ip: str = None,
              ports: list = [], domain: str = None, internal: bool = False, vms: list = [],
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Create load balancer"""
    if name is None:
        name = get_random_name().replace('_', '-')
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain,
                                      checkport=checkport, internal=internal, ip=ip)


@cloud.tool()
def create_securitygroup(context: Context,
                         securitygroup: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create security group"""
    securitygroup = securitygroup
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.create_security_group(securitygroup, overrides)


@cloud.tool()
def delete_bucket(context: Context,
                  buckets: list = [],
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None):
    """Delete bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for bucket in buckets:
        k.delete_bucket(bucket)


@cloud.tool()
def delete_bucketfile(context: Context,
                      bucket: str, path: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None):
    """Delete bucketfile from bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    k.delete_from_bucket(bucket, path)


@cloud.tool()
def delete_dns(context: Context,
               names: list, net: str, domain: str = None, allentries: bool = False,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None):
    """Delete dns entry"""
    domain = domain or net
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for name in names:
        k.delete_dns(name, domain, allentries=allentries)


@cloud.tool()
def delete_lb(context: Context,
              names: list = [], client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Delete load balancer"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for name in names:
        config.delete_loadbalancer(name)


@cloud.tool()
def delete_securitygroup(context: Context,
                         securitygroups: list = [],
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None):
    """Delete security group"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for securitygroup in securitygroups:
        k.delete_security_group(securitygroup)


@cloud.tool()
def download_bucketfile(context: Context,
                        bucket: str, path: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None):
    """Download bucketfile from bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    k.download_from_bucket(bucket, path)


@cloud.tool()
def list_bucketfiles(context: Context,
                     bucket: str,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> list:
    """List bucketfiles of bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_bucketfiles(bucket)


@cloud.tool()
def list_buckets(context: Context,
                 client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> list:
    """List buckets"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_buckets()


@cloud.tool()
def list_dns_entries(context: Context,
                     domain: str = None,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> list:
    """List dns entries"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if domain is None:
        return config.k.list_dns_zones()
    else:
        return config.k.list_dns_(domain)


@cloud.tool()
def list_lbs(context: Context,
             client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> list:
    """List load balancers"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.list_loadbalancers()


@cloud.tool()
def list_securitygroups(context: Context,
                        network: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None) -> list:
    """List security groups"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_security_groups(network=network)


@cloud.tool()
def update_securitygroup(context: Context,
                         securitygroup: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None, overrides: dict = {}):
    """Update security group"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    result = config.k.update_security_group(name=securitygroup, overrides=overrides)
    common.handle_response(result, securitygroup, element='SecurityGroup', action='updated')


@baremetal.tool()
def info_baremetal_host(context: Context,
                        url: str, user: str, password: str, full: bool = False,
                        debug: bool = False) -> dict:
    """Provide information on baremetal host"""
    return common.info_baremetal_host(url, user, password, debug=debug, full=full)


@baremetal.tool()
def reset_baremetal_host(context: Context,
                         url: str, user: str, password: str,
                         debug: bool = False) -> dict:
    """Reset baremetal host"""
    return common.reset_baremetal_host(url, user, password, debug=debug)


@baremetal.tool()
def start_baremetal_host(context: Context,
                         url: str, user: str, password: str,
                         debug: bool = False, overrides: dict = {}) -> dict:
    """Start baremetal host"""
    return common.start_baremetal_host(url, user, password, overrides, debug=debug)


@baremetal.tool()
def stop_baremetal_host(context: Context,
                        url: str, user: str, password: str,
                        debug: bool = False) -> dict:
    """Stop baremetal host"""
    return common.stop_baremetal_host(url, user, password, debug=debug)


@baremetal.tool()
def update_baremetal_host(context: Context,
                          url: str, user: str, password: str,
                          debug: bool = False, overrides: dict = {}) -> dict:
    """update baremetal host"""
    return common.update_baremetal_host(url, user, password, overrides, debug=debug)


def main():
    parser = argparse.ArgumentParser(description="kclimcp")
    parser.add_argument('-e', '--enable', action='append', help='enable additional tools. Can be used multiple times',
                        choices=["baremetal", "cloud"], default=[])
    parser.add_argument("--http", action='store_true')
    args = parser.parse_args()
    for tool in args.enable:
        if tool == 'cloud':
            asyncio.run(core.import_server(cloud))
        else:
            asyncio.run(core.import_server(baremetal))
    params = {'transport': 'http', 'host': '0.0.0.0', 'port': args.port} if args.http else {'transport': 'stdio'}
    core.run(**params)


if __name__ == "__main__":
    main()
