from kvirt import common
from kvirt.config import Kbaseconfig, Kconfig
from kvirt.common import get_git_version, compare_git_versions
from kvirt.nameutils import get_random_name
from mcp.server.fastmcp import FastMCP
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


mcp = FastMCP("kcli-core")


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
def create_vm(name: str, profile: str,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_vm(name, profile, overrides=overrides)


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
def delete_vm(vm: str,
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None) -> dict:
    """Delete vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.delete(vm)


@mcp.tool()
def info_vm(name: str,
            client: str = None, debug: bool = False, region: str = None,
            zone: str = None, namespace: str = None) -> dict:
    """Get info of vm"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.info(name)


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
def list_clusters(client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> list:
    """List clusters"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_kubes()


@mcp.tool()
def list_images(client: str = None, debug: bool = False, region: str = None,
                zone: str = None, namespace: str = None) -> list:
    """List images"""
    return Kconfig(client=client).k.volumes()


@mcp.tool()
def list_networks(client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None) -> dict:
    """List networks"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_networks()


@mcp.tool()
def list_pools(client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None) -> list:
    """List pools"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list_pools()


@mcp.tool()
def list_vms(client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> list:
    """List vms"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.k.list()


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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
