from kvirt import common
import json
from kvirt.config import Kbaseconfig, Kconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt.common import get_git_version
from kvirt.nameutils import get_random_name
from kvirt.defaults import IMAGES, VERSION, PLANTYPES
from mcp.server.fastmcp import FastMCP
import os
from shutil import which
from urllib.request import urlopen

mcp = FastMCP("kclimcp")


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
def get_changelog(diff: str = None) -> str:
    """Returns kcli changelog between diff and main"""
    return common.get_changelog(diff)


@mcp.tool()
def reset_baremetal_host(overrides: dict) -> dict:
    """Reset baremetal hosts"""
    debug = overrides.get('debug', False)
    baseconfig = Kbaseconfig(debug=debug, offline=True)
    url = overrides.get('bmc_url') or overrides.get('url')
    user = overrides.get('bmc_user') or overrides.get('user') or overrides.get('bmc_username')\
        or overrides.get('username') or baseconfig.bmc_user
    password = overrides.get('bmc_password') or overrides.get('password') or baseconfig.bmc_password
    if url is None:
        return {'result': 'failure', 'reason': "Missing url"}
    if user is None:
        return {'result': 'failure', 'reason': "Missing user"}
    if password is None:
        return {'result': 'failure', 'reason': "Missing password"}
    return common.reset_baremetal_host(url, user, password, debug=debug)


@mcp.tool()
def start_baremetal_host(overrides: dict) -> dict:
    """Start baremetal hosts"""
    debug = overrides.get('debug', False)
    baseconfig = Kbaseconfig(debug=debug, offline=True)
    url = overrides.get('bmc_url') or overrides.get('url')
    user = overrides.get('bmc_user') or overrides.get('user') or overrides.get('bmc_username')\
        or overrides.get('username') or baseconfig.bmc_user
    password = overrides.get('bmc_password') or overrides.get('password') or baseconfig.bmc_password
    if url is None:
        return {'result': 'failure', 'reason': "Missing url"}
    if user is None:
        return {'result': 'failure', 'reason': "Missing user"}
    if password is None:
        return {'result': 'failure', 'reason': "Missing password"}
    return common.start_baremetal_host(url, user, password, overrides, debug=debug)


@mcp.tool()
def stop_baremetal_host(overrides: dict) -> dict:
    """Stop baremetal hosts"""
    debug = overrides.get('debug', False)
    baseconfig = Kbaseconfig(debug=debug, offline=True)
    url = overrides.get('bmc_url') or overrides.get('url')
    user = overrides.get('bmc_user') or overrides.get('user') or overrides.get('bmc_username')\
        or overrides.get('username') or baseconfig.bmc_user
    password = overrides.get('bmc_password') or overrides.get('password') or baseconfig.bmc_password
    if url is None:
        return {'result': 'failure', 'reason': "Missing url"}
    if user is None:
        return {'result': 'failure', 'reason': "Missing user"}
    if password is None:
        return {'result': 'failure', 'reason': "Missing password"}
    return common.stop_baremetal_host(url, user, password, debug=debug)


@mcp.tool()
def update_baremetal_host(overrides: dict) -> dict:
    """Update baremetal hosts"""
    debug = overrides.get('debug', False)
    baseconfig = Kbaseconfig(debug=debug, offline=True)
    url = overrides.get('bmc_url') or overrides.get('url')
    user = overrides.get('bmc_user') or overrides.get('user') or overrides.get('bmc_username')\
        or overrides.get('username') or baseconfig.bmc_user
    password = overrides.get('bmc_password') or overrides.get('password') or baseconfig.bmc_password
    if url is None:
        return {'result': 'failure', 'reason': "Missing url"}
    if user is None:
        return {'result': 'failure', 'reason': "Missing user"}
    if password is None:
        return {'result': 'failure', 'reason': "Missing password"}
    return common.reset_baremetal_host(url, user, password, overrides, debug=debug)


@mcp.tool()
def start_vm(name: str, client: str = None) -> dict:
    """Start kcli vm"""
    return Kconfig(client).k.start(name)


@mcp.tool()
def start_container(name: str, client: str = None) -> dict:
    """Start kcli container"""
    config = Kconfig(client)
    cont = Kcontainerconfig(config, client=client).cont
    return cont.start_container(name)


@mcp.tool()
def stop_vm(name: str, client: str = None) -> dict:
    """Stop kcli vm"""
    return Kconfig(client).k.stop(name)


@mcp.tool()
def stop_container(name: str, client: str = None) -> dict:
    """Stop kcli container"""
    config = Kconfig(client)
    cont = Kcontainerconfig(config, client=client).cont
    return cont.stop_container(name)


@mcp.tool()
def restart_vm(name: str, client: str = None) -> dict:
    """Restart kcli vm"""
    return Kconfig(client).k.restart(name)


@mcp.tool()
def restart_container(name: str, client: str = None) -> dict:
    """Restart kcli container"""
    config = Kconfig(client)
    cont = Kcontainerconfig(config, client=client).cont
    cont.stop_container(name)
    return cont.start_container(name)


@mcp.tool()
def delete_container(name: str, client: str = None) -> dict:
    """Delete kcli container"""
    config = Kconfig(client)
    cont = Kcontainerconfig(config, client=client).cont
    return cont.delete_container(name)


@mcp.tool()
def download_image(image: str, client: str = None, overrides: dict = {}) -> dict:
    """Download image"""
    name = overrides.get('name')
    cmds = overrides.get('cmds')
    url = overrides.get('url')
    if image is None:
        if url is not None:
            image = os.path.basename(url)
        else:
            return {'result': 'failure', 'reason': "An image or url needs to be specified"}
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
    rhcos_installer = overrides.get('installer', False)
    kvm_openstack = not overrides.get('qemu', False)
    config = Kconfig(client)
    pool = overrides.get('pool') or config.pool
    return config.download_image(pool=pool, image=image, cmds=cmds, url=url, size=size, arch=arch,
                                 kvm_openstack=kvm_openstack, rhcos_installer=rhcos_installer, name=name)


@mcp.tool()
def download_iso(image: str, client: str = None, overrides: dict = {}) -> dict:
    url = overrides.get('url')
    if url is None:
        return {'result': 'failure', 'reason': "An url needs to be specified"}
    iso = os.path.basename(url)
    config = Kconfig(client=client)
    pool = overrides.get('pool') or config.pool
    return config.download_image(pool=pool, image=iso, url=url)


@mcp.tool()
def delete_image(image: str, client: str = None, overrides: dict = {}) -> dict:
    """Delete image"""
    config = Kconfig(client=client)
    pool = overrides.get('pool') or config.pool
    return config.k.delete_image(image, pool=pool)


@mcp.tool()
def download_kubeconfig(kube: str, client: str = None, overrides: dict = {}) -> str:
    """Download kubeconfig"""
    config = Kconfig(client=client)
    if config.type != 'web':
        return "Downloading kubeconfig is only available for web provider"
    return config.k.download_kubeconfig(kube).decode("UTF-8") or f"Cluster {kube} was not found"


@mcp.tool()
def create_clusterprofile(clusterprofile: str, client: str = None, overrides: dict = {}) -> dict:
    """Create Cluster Profile"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.create_clusterprofile(clusterprofile, overrides=overrides)


@mcp.tool()
def delete_clusterprofile(clusterprofile: str, client: str = None) -> dict:
    """Delete Cluster Profile"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.delete_clusterprofile(clusterprofile)


@mcp.tool()
def update_clusterprofile(clusterprofile: str, client: str = None, overrides: dict = {}) -> dict:
    """Update Cluster Profile"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.update_clusterprofile(clusterprofile, overrides=overrides)


@mcp.tool()
def create_confpool(confpool: str, client: str = None, overrides: dict = {}) -> dict:
    """Create Configuration Pool"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.create_confpool(confpool, overrides=overrides)


@mcp.tool()
def delete_confpool(confpool: str, client: str = None) -> dict:
    """Delete Configuration Pool"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.delete_confpool(confpool)


@mcp.tool()
def update_confpool(confpool: str, client: str = None, overrides: dict = {}) -> dict:
    """Update Configuration Pool"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.update_confpool(confpool, overrides=overrides)


@mcp.tool()
def create_profile(profile: str, client: str = None, overrides: dict = {}) -> dict:
    """Create Profile"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.create_profile(profile, overrides=overrides)


@mcp.tool()
def delete_profile(profile: str, client: str = None) -> dict:
    """Delete Profile"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.delete_profile(profile)


@mcp.tool()
def update_profile(profile: str, client: str = None, overrides: dict = {}) -> dict:
    """Update Profile"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.update_profile(profile, overrides=overrides)


@mcp.tool()
def info_vm(name: str, client: str = None) -> dict:
    """Get info of a kcli vm"""
    return Kconfig(client).k.info(name)


@mcp.tool()
def enable_host(host: str, client: str = None) -> dict:
    """Enable Host"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.enable_host(host)


@mcp.tool()
def disable_host(host: str, client: str = None) -> dict:
    """Disable Host"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.disable_host(host)


@mcp.tool()
def delete_host(host: str, client: str = None) -> dict:
    """Delete Host"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.delete_host(host)


@mcp.tool()
def sync_config(network: str, client: str = None) -> dict:
    """Sync Config to Kubernetes/Openshift cluster"""
    baseconfig = Kbaseconfig(client=client)
    return baseconfig.import_in_kube(network=network)


@mcp.tool()
def list_vms(client: str = None) -> list:
    """List kcli vms for specific client or for default one when unspecified"""
    return Kconfig(client).k.list()


@mcp.tool()
def list_clusterprofiles(client: str = None) -> list:
    """List Cluster Profiles"""
    return Kbaseconfig(client).list_clusterprofiles()


@mcp.tool()
def list_confpools(client: str = None) -> list:
    """List Configuration Pools"""
    return Kbaseconfig(client).list_confpools()


@mcp.tool()
def list_containers(client: str = None) -> list:
    """List Containers"""
    return Kconfig(client).list_containers()


@mcp.tool()
def list_containerprofiles(client: str = None) -> list:
    """List Container Profiles"""
    return Kbaseconfig(client).list_containerprofiles()


@mcp.tool()
def list_containerimages(client: str = None) -> list:
    """List Container Images"""
    config = Kconfig(client=client)
    if config.type not in ['kvm', 'proxmox']:
        return ["Operation not supported on this kind of client.Leaving..."]
    cont = Kcontainerconfig(config, client=client).cont
    return cont.list_images()


@mcp.tool()
def list_clients() -> list:
    """List kcli clients/providers"""
    clientstable = ["Client", "Type", "Enabled", "Current"]
    baseconfig = Kbaseconfig()
    for client in sorted(baseconfig.clients):
        enabled = baseconfig.ini[client].get('enabled', True)
        _type = baseconfig.ini[client].get('type', 'kvm')
        if client == baseconfig.client:
            clientstable.append([client, _type, enabled, 'X'])
        else:
            clientstable.append([client, _type, enabled, ''])
    return clientstable


@mcp.tool()
def list_lbs(client: str = None) -> list:
    """List Load Balancers"""
    return Kconfig(client).list_loadbalancers()


@mcp.tool()
def info_clusterprofile(clusterprofile: str, client: str = None) -> dict:
    """Provide information on Cluster Profile"""
    baseconfig = Kbaseconfig(client=client)
    if clusterprofile not in baseconfig.clusterprofiles:
        return {'result': 'failure', 'reason': f"Clusterprofile {clusterprofile} not found"}
    else:
        return baseconfig.clusterprofiles[clusterprofile]


@mcp.tool()
def info_confpool(confpool: str, client: str = None) -> dict:
    """Provide information on Configuration Pool"""
    baseconfig = Kbaseconfig(client=client)
    if confpool not in baseconfig.confpools:
        return {'result': 'failure', 'reason': f"Confpool {confpool} not found"}
    else:
        return baseconfig.confpools[confpool]


@mcp.tool()
def info_profile(profile: str, client: str = None) -> dict:
    """Provide information on Profile"""
    baseconfig = Kbaseconfig(client=client)
    if profile not in baseconfig.list_profiles():
        return {'result': 'failure', 'reason': f"Profile {profile} not found"}
    else:
        return baseconfig.profiles[profile]


@mcp.tool()
def list_profiles(client: str = None) -> dict:
    """List Profiles"""
    return Kbaseconfig(client=client).list_profiles()


@mcp.tool()
def list_dns_entries(domain: str = None, client: str = None) -> list:
    """List Dns Entries"""
    if domain is None:
        return Kconfig(client=client).k.list_dns_zones()
    else:
        return Kconfig(client=client).k.list_dns_(domain)


@mcp.tool()
def list_flavors(client: str = None) -> list:
    """List Flavors"""
    return Kconfig(client=client).k.list_flavors()


@mcp.tool()
def list_available_images(client: str = None) -> list:
    """List Available images"""
    return IMAGES


@mcp.tool()
def list_images(client: str = None) -> list:
    """List Images"""
    return Kconfig(client=client).k.volumes()


@mcp.tool()
def list_isos(client: str = None) -> list:
    """List Isos"""
    return Kconfig(client=client).k.volumes(iso=True)


@mcp.tool()
def list_networks(client: str = None) -> dict:
    """List Networks"""
    return Kconfig(client=client).k.list_networks()


@mcp.tool()
def list_plans(client: str = None) -> list:
    """List Plans"""
    return Kconfig(client=client).k.list_plans()


@mcp.tool()
def list_plantypes(client: str = None) -> list:
    """List Plan Types"""
    return sorted(PLANTYPES)


@mcp.tool()
def list_subnets(client: str = None) -> list:
    """List Subnets"""
    return Kconfig(client=client).k.list_subnets()


@mcp.tool()
def create_app(app: str, client: str = None, overrides: dict = {}) -> dict:
    """Create Application"""
    kubectl = which('kubectl') or which('oc')
    if kubectl is None:
        return {'result': 'failure', 'reason': "You need kubectl/oc to install apps"}
    if 'KUBECONFIG' in os.environ and not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
    baseconfig = Kbaseconfig(client=client, offline=True)
    overrides[f'{app}_version'] = overrides[f'{app}_version'] if f'{app}_version' in overrides else 'latest'
    return baseconfig.create_app(app, overrides)


@mcp.tool()
def delete_app(app: str, client: str = None, overrides: dict = {}) -> dict:
    """Delete Application"""
    kubectl = which('kubectl') or which('oc')
    if kubectl is None:
        return {'result': 'failure', 'reason': "You need kubectl/oc to install apps"}
    if 'KUBECONFIG' in os.environ and not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
    baseconfig = Kbaseconfig(client=client, offline=True)
    return baseconfig.delete_app(app, overrides)


@mcp.tool()
def list_apps(client: str = None, installed: bool = False, overrides: dict = {}) -> list:
    """List Applications"""
    kubectl = which('kubectl') or which('oc')
    if kubectl is None:
        return {'result': 'failure', 'reason': "You need kubectl/oc to install apps"}
    if 'KUBECONFIG' in os.environ and not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
    baseconfig = Kbaseconfig(client=client, offline=True)
    return baseconfig.list_apps(quiet=True, installed=installed, overrides=overrides)


@mcp.tool()
def list_clusters(client: str = None) -> list:
    """List Clusters"""
    return Kconfig(client=client).k.list_kubes()


@mcp.tool()
def list_pools(client: str = None) -> list:
    """List Pools"""
    return Kconfig(client=client).k.list_pools()


@mcp.tool()
def list_vmdisks(client: str = None) -> list:
    """List Disks"""
    return Kconfig(client=client).k.list_disks()


@mcp.tool()
def create_kubeadm_registry(plan: str = None, overrides: dict = {}, client: str = None) -> dict:
    """Create Kubeadm/Generic registry"""
    if plan is None:
        plan = get_random_name()
    if 'cluster' not in overrides:
        overrides['cluster'] = plan
    return Kconfig(client=client).create_kubeadm_registry(plan, overrides=overrides)


@mcp.tool()
def create_openshift_iso(cluster: str = None, overrides: dict = {}, client: str = None) -> dict:
    """Create OpenShift iso"""
    ignitionfile = overrides.get('ignitionfile', False)
    direct = overrides.get('direct', False)
    offline = client == 'fake' or common.need_fake()
    return Kconfig(client=client, offline=offline).create_openshift_iso(cluster, overrides=overrides, ignitionfile=ignitionfile, direct=direct)


@mcp.tool()
def create_openshift_registry(plan: str = None, overrides: dict = {}, client: str = None) -> dict:
    """Create OpenShift registry"""
    if plan is None:
        plan = get_random_name()
    if 'cluster' not in overrides:
        overrides['cluster'] = plan
    return Kconfig(client=client).create_openshift_registry(plan, overrides=overrides)


@mcp.tool()
def create_vm(name: str, profile: str, overrides: dict, client: str = None) -> dict:
    """Create a kcli vm"""
    return Kconfig(client).create_vm(name, profile, overrides=overrides)


@mcp.tool()
def clone_vm(name: str, base: str, full: bool = False, start: bool = False, client: str = None) -> dict:
    """Clone a kcli vm"""
    return Kconfig(client).k.clone(base, name, full=full, start=start)


@mcp.tool()
def update_vm(name: str, overrides: dict, client: str = None) -> dict:
    """Update a kcli vm"""
    return Kconfig(client).update_vm(name, overrides)


@mcp.tool()
def create_vmdisk(name: str, pool: str = 'default', size: int = 10, image: str = None, interface: str = 'virtio',
                  shareable: bool = False, force: bool = False, novm: bool = False,
                  overrides: dict = {}, client: str = None) -> dict:
    """Add a disk to a kcli vm"""
    existing = overrides.get('diskname')
    thin = overrides.get('thin', not shareable)
    if interface not in ['virtio', 'ide', 'scsi']:
        return {'result': 'failure', 'reason': "Incorrect disk interface. Choose between virtio, scsi or ide..."}
    k = Kconfig(client).k
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
def delete_vmdisk(diskname: str, vm: str = None, pool: str = 'default', client: str = None) -> dict:
    novm = vm is None
    config = Kconfig(client=client)
    k = config.k
    return k.delete_disk(name=vm, diskname=diskname, pool=pool, novm=novm)


@mcp.tool()
def delete_vm(vm: str, client: str = None) -> dict:
    """Delete a kcli vm"""
    return Kconfig(client).k.delete(vm)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
