#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# coding=utf-8

from distutils.spawn import find_executable
from kvirt.config import Kconfig
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt.version import __version__
from kvirt.defaults import IMAGES
from prettytable import PrettyTable
import argcomplete
import argparse
from kvirt import common
from kvirt import nameutils
import os
import random
import sys
import yaml


def alias(text):
    return "Alias for %s" % text


def subparser_print_help(parser, subcommand):
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)]
    for subparsers_action in subparsers_actions:
        for choice, subparser in subparsers_action.choices.items():
            if choice == subcommand:
                subparser.print_help()
                return


def start_vm(args):
    """Start vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    codes = []
    for name in names:
        common.pprint("Starting vm %s..." % name)
        result = k.start(name)
        code = common.handle_response(result, name, element='', action='started')
        codes.append(code)
    os._exit(1 if 1 in codes else 0)


def start_container(args):
    """Start containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    for name in names:
        common.pprint("Starting container %s..." % name)
        cont.start_container(name)


def stop_vm(args):
    """Stop vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    if config.extraclients:
        ks = config.extraclients
        ks.update({config.client: config.k})
    else:
        ks = {config.client: config.k}
    codes = []
    for cli in ks:
        k = ks[cli]
        for name in names:
            common.pprint("Stopping vm %s in %s..." % (name, cli))
            result = k.stop(name)
            code = common.handle_response(result, name, element='', action='stopped')
            codes.append(code)
    os._exit(1 if 1 in codes else 0)


def stop_container(args):
    """Stop containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    if config.extraclients:
        ks = config.extraclients
        ks.update({config.client: config.k})
    else:
        ks = {config.client: config.k}
    for cli in ks:
        cont = Kcontainerconfig(config, client=args.containerclient).cont
        for name in names:
            common.pprint("Stopping container %s in %s..." % (name, cli))
            cont.stop_container(name)


def restart_vm(args):
    """Restart vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    codes = []
    for name in names:
        common.pprint("Restarting vm %s..." % name)
        result = k.restart(name)
        code = common.handle_response(result, name, element='', action='restarted')
        codes.append(code)
    os._exit(1 if 1 in codes else 0)


def restart_container(args):
    """Restart containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    for name in names:
        common.pprint("Restarting container %s..." % name)
        cont.stop_container(name)
        cont.start_container(name)


def console_vm(args):
    """Vnc/Spice/Serial Vm console"""
    serial = args.serial
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    name = common.get_lastvm(config.client) if not args.name else args.name
    k = config.k
    tunnel = config.tunnel
    if serial:
        k.serialconsole(name)
    else:
        k.console(name=name, tunnel=tunnel)


def console_container(args):
    """Container console"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    name = common.get_lastvm(config.client) if not args.name else args.name
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    cont.console_container(name)
    return


def delete_vm(args):
    """Delete vm"""
    snapshots = args.snapshots
    yes = args.yes
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        names = args.names
        if not names:
            common.pprint("Can't delete vms on multiple hosts without specifying their names", color='red')
            os._exit(1)
    else:
        allclients = {config.client: config.k}
        names = [common.get_lastvm(config.client)] if not args.names else args.names
    for cli in sorted(allclients):
        k = allclients[cli]
        common.pprint("Deleting on %s" % cli)
        if not yes:
            common.confirm("Are you sure?")
        codes = []
        for name in names:
            dnsclient, domain = k.dnsinfo(name)
            result = k.delete(name, snapshots=snapshots)
            if result['result'] == 'success':
                common.pprint("%s deleted" % name)
                codes.append(0)
                common.set_lastvm(name, cli, delete=True)
            else:
                reason = result['reason']
                common.pprint("Could not delete %s because %s" % (name, reason), color='red')
                codes.append(1)
            if dnsclient is not None and domain is not None:
                z = Kconfig(client=dnsclient).k
                z.delete_dns(name, domain)
    os._exit(1 if 1 in codes else 0)


def delete_container(args):
    """Delete container"""
    yes = args.yes
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        names = args.names
        if not names:
            common.pprint("Can't delete vms on multiple hosts without specifying their names", color='red')
            os._exit(1)
    else:
        allclients = {config.client: config.k}
        names = [common.get_lastvm(config.client)] if not args.names else args.names
    for cli in sorted(allclients):
        common.pprint("Deleting on %s" % cli)
        if not yes:
            common.confirm("Are you sure?")
        codes = [0]
        cont = Kcontainerconfig(config, client=args.containerclient).cont
        for name in names:
            common.pprint("Deleting container %s" % name)
            cont.delete_container(name)
    os._exit(1 if 1 in codes else 0)


def download_image(args):
    """Download Image"""
    pool = args.pool
    image = args.image
    cmd = args.cmd
    url = args.url
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(pool=pool, image=image, download=True, cmd=cmd, url=url, profile=True)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def delete_image(args):
    images = args.images
    yes = args.yes
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
    else:
        allclients = {config.client: config.k}
    for cli in sorted(allclients):
        k = allclients[cli]
        common.pprint("Deleting on %s" % cli)
        if not yes:
            common.confirm("Are you sure?")
        codes = []
        for image in images:
            if image in config.profiles and len(config.profiles[image]) == 1 and 'image' in config.profiles[image]:
                profileimage = config.profiles[image]['image']
                config.delete_profile(image, quiet=True)
                result = k.delete_image(profileimage)
            else:
                result = k.delete_image(image)
            if result['result'] == 'success':
                common.pprint("%s deleted" % image)
                codes.append(0)
            else:
                reason = result['reason']
                common.pprint("Could not delete image %s because %s" % (image, reason), color='red')
                codes.append(1)
    os._exit(1 if 1 in codes else 0)


def create_profile(args):
    """Create profile"""
    profile = args.profile
    overrides = common.get_overrides(param=args.param)
    baseconfig = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
    result = baseconfig.create_profile(profile, overrides=overrides)
    code = common.handle_response(result, profile, element='Profile', action='created', client=baseconfig.client)
    return code


def delete_profile(args):
    """Delete profile"""
    yes = args.yes
    profile = args.profile
    baseconfig = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
    common.pprint("Deleting on %s" % baseconfig.client)
    if not yes:
        common.confirm("Are you sure?")
    result = baseconfig.delete_profile(profile)
    code = common.handle_response(result, profile, element='Profile', action='deleted', client=baseconfig.client)
    return code
    # os._exit(0) if result['result'] == 'success' else os._exit(1)


def info_vm(args):
    """Get info on vm"""
    output = args.output
    fields = args.fields.split(',') if args.fields is not None else []
    values = args.values
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    for name in names:
        data = k.info(name)
        if data:
            print(common.print_info(data, output=output, fields=fields, values=values, pretty=True))


def enable_host(args):
    """Enable host"""
    host = args.host
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.enable_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def disable_host(args):
    """Disable host"""
    host = args.host
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.disable_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def sync_host(args):
    """Handle host"""
    hosts = args.hosts
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(sync=hosts)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def list_vm(args):
    """List vms"""
    filters = args.filters
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    customcolumns = {'kubevirt': 'Namespace', 'aws': 'InstanceId', 'openstack': 'Project'}
    customcolumn = customcolumns[config.type] if config.type in customcolumns else 'Report'
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        vms = PrettyTable(["Name", "Host", "Status", "Ips", "Source", "Plan", "Profile", customcolumn])
        for cli in sorted(allclients):
            for vm in allclients[cli].list():
                name = vm.get('name')
                status = vm.get('status')
                ip = vm.get('ip', '')
                source = vm.get('image', '')
                plan = vm.get('plan', '')
                profile = vm.get('profile', '')
                report = vm.get('report', '')
                vminfo = [name, cli, status, ip, source, plan, profile, report]
                if filters:
                    if status == filters:
                        vms.add_row(vminfo)
                else:
                    vms.add_row(vminfo)
        print(vms)
    else:
        vms = PrettyTable(["Name", "Status", "Ips", "Source", "Plan", "Profile", customcolumn])
        for vm in k.list():
            name = vm.get('name')
            status = vm.get('status')
            ip = vm.get('ip', '')
            source = vm.get('image', '')
            plan = vm.get('plan', '')
            profile = vm.get('profile', '')
            report = vm.get('report', '')
            vminfo = [name, status, ip, source, plan, profile, report]
            if config.planview and vm[4] != config.currentplan:
                continue
            if filters:
                if status == filters:
                    vms.add_row(vminfo)
            else:
                vms.add_row(vminfo)
        print(vms)
    return


def list_container(args):
    """List containers"""
    filters = args.filters
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    common.pprint("Listing containers...")
    containers = PrettyTable(["Name", "Status", "Image", "Plan", "Command", "Ports", "Deploy"])
    for container in cont.list_containers():
        if filters:
            status = container[1]
            if status == filters:
                containers.add_row(container)
        else:
            containers.add_row(container)
    print(containers)
    return


def profilelist_container(args):
    """List container profiles"""
    short = args.short
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    profiles = baseconfig.list_containerprofiles()
    if short:
        profilestable = PrettyTable(["Profile"])
        for profile in sorted(profiles):
            profilename = profile[0]
            profilestable.add_row([profilename])
    else:
        profilestable = PrettyTable(["Profile", "Image", "Nets", "Ports", "Volumes", "Cmd"])
        for profile in sorted(profiles):
            profilestable.add_row(profile)
    profilestable.align["Profile"] = "l"
    print(profilestable)
    return


def imagelist_container(args):
    """List container images"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.type != 'kvm':
        common.pprint("Operation not supported on this kind of client.Leaving...", color='red')
        os._exit(1)
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    common.pprint("Listing images...")
    images = PrettyTable(["Name"])
    for image in cont.list_images():
        images.add_row([image])
    print(images)
    return


def list_host(args):
    """List hosts"""
    clientstable = PrettyTable(["Client", "Type", "Enabled", "Current"])
    clientstable.align["Client"] = "l"
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    for client in sorted(baseconfig.clients):
        enabled = baseconfig.ini[client].get('enabled', True)
        _type = baseconfig.ini[client].get('type', 'kvm')
        if client == baseconfig.client:
            clientstable.add_row([client, _type, enabled, 'X'])
        else:
            clientstable.add_row([client, _type, enabled, ''])
    print(clientstable)
    return


def list_lb(args):
    """List lbs"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    loadbalancers = config.list_loadbalancer()
    if short:
        loadbalancerstable = PrettyTable(["Loadbalancer"])
        for lb in sorted(loadbalancers):
            loadbalancerstable.add_row([lb])
    else:
        loadbalancerstable = PrettyTable(["LoadBalancer", "IPAddress", "IPProtocol", "Ports", "Target"])
        for lb in sorted(loadbalancers):
            loadbalancerstable.add_row(lb)
    loadbalancerstable.align["Loadbalancer"] = "l"
    print(loadbalancerstable)
    return


def list_profile(args):
    """List profiles"""
    short = args.short
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    profiles = baseconfig.list_profiles()
    if short:
        profilestable = PrettyTable(["Profile"])
        for profile in sorted(profiles):
            profilename = profile[0]
            profilestable.add_row([profilename])
    else:
        profilestable = PrettyTable(["Profile", "Flavor",
                                     "Pool", "Disks", "Image",
                                     "Nets", "Cloudinit", "Nested",
                                     "Reservedns", "Reservehost"])
        for profile in sorted(profiles):
            profilestable.add_row(profile)
    profilestable.align["Profile"] = "l"
    print(profilestable)
    return


def list_flavor(args):
    """List flavors"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    flavors = k.flavors()
    if short:
        flavorstable = PrettyTable(["Flavor"])
        for flavor in sorted(flavors):
            flavorname = flavor[0]
            flavorstable.add_row([flavorname])
    else:
        flavorstable = PrettyTable(["Flavor", "Numcpus", "Memory"])
        for flavor in sorted(flavors):
            flavorstable.add_row(flavor)
    flavorstable.align["Flavor"] = "l"
    print(flavorstable)
    return


def list_image(args):
    """List images"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    imagestable = PrettyTable(["Images"])
    imagestable.align["Images"] = "l"
    for image in k.volumes():
        imagestable.add_row([image])
    print(imagestable)
    return


def list_iso(args):
    """List isos"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    isostable = PrettyTable(["Iso"])
    isostable.align["Iso"] = "l"
    for iso in k.volumes(iso=True):
        isostable.add_row([iso])
    print(isostable)
    return


def list_network(args):
    """List networks"""
    short = args.short
    subnets = args.subnets
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    if not subnets:
        networks = k.list_networks()
        common.pprint("Listing Networks...")
        if short:
            networkstable = PrettyTable(["Network"])
            for network in sorted(networks):
                networkstable.add_row([network])
        else:
            networkstable = PrettyTable(["Network", "Type", "Cidr", "Dhcp", "Domain", "Mode"])
            for network in sorted(networks):
                networktype = networks[network]['type']
                cidr = networks[network]['cidr']
                dhcp = networks[network]['dhcp']
                mode = networks[network]['mode']
                if 'domain' in networks[network]:
                    domain = networks[network]['domain']
                else:
                    domain = 'N/A'
                networkstable.add_row([network, networktype, cidr, dhcp, domain, mode])
        networkstable.align["Network"] = "l"
        print(networkstable)
        return
    else:
        subnets = k.list_subnets()
        common.pprint("Listing Subnets...")
        if short:
            subnetstable = PrettyTable(["Subnets"])
            for subnet in sorted(subnets):
                subnetstable.add_row([subnet])
        else:
            subnetstable = PrettyTable(["Subnet", "Az", "Cidr", "Network"])
            for subnet in sorted(subnets):
                cidr = subnets[subnet]['cidr']
                az = subnets[subnet]['az']
                if 'network' in subnets[subnet]:
                    network = subnets[subnet]['network']
                else:
                    network = 'N/A'
                subnetstable.add_row([subnet, az, cidr, network])
        subnetstable.align["Network"] = "l"
        print(subnetstable)
        return


def list_plan(args):
    """List plans"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        plans = PrettyTable(["Name", "Host", "Vms"])
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        for cli in sorted(allclients):
            currentconfig = Kconfig(client=cli, debug=args.debug, region=args.region, zone=args.zone,
                                    namespace=args.namespace)
            for plan in currentconfig.list_plans():
                planname = plan[0]
                planvms = plan[1]
                plans.add_row([planname, cli, planvms])
    else:
        plans = PrettyTable(["Name", "Vms"])
        for plan in config.list_plans():
            planname = plan[0]
            planvms = plan[1]
            plans.add_row([planname, planvms])
    print(plans)
    return


def list_pool(args):
    """List pools"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pools = k.list_pools()
    if short:
        poolstable = PrettyTable(["Pool"])
        for pool in sorted(pools):
            poolstable.add_row([pool])
    else:
        poolstable = PrettyTable(["Pool", "Path"])
        for pool in sorted(pools):
            poolpath = k.get_pool_path(pool)
            poolstable.add_row([pool, poolpath])
    poolstable.align["Pool"] = "l"
    print(poolstable)
    return


def list_product(args):
    """List products"""
    group = args.group
    repo = args.repo
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    products = PrettyTable(["Repo", "Group", "Product", "Description", "Numvms", "Memory"])
    products.align["Repo"] = "l"
    productsinfo = baseconfig.list_products(group=group, repo=repo)
    for product in sorted(productsinfo, key=lambda x: (x['repo'], x['group'], x['name'])):
        name = product['name']
        repo = product['repo']
        description = product.get('description', 'N/A')
        numvms = product.get('numvms', 'N/A')
        memory = product.get('memory', 'N/A')
        group = product.get('group', 'N/A')
        products.add_row([repo, group, name, description, numvms, memory])
    print(products)
    return


def list_repo(args):
    """List repos"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    repos = PrettyTable(["Repo", "Url"])
    repos.align["Repo"] = "l"
    reposinfo = baseconfig.list_repos()
    for repo in sorted(reposinfo):
        url = reposinfo[repo]
        repos.add_row([repo, url])
    print(repos)
    return


def disklist_vm(args):
    """List vm disks"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Listing disks...")
    diskstable = PrettyTable(["Name", "Pool", "Path"])
    diskstable.align["Name"] = "l"
    disks = k.list_disks()
    for disk in sorted(disks):
        path = disks[disk]['path']
        pool = disks[disk]['pool']
        diskstable.add_row([disk, pool, path])
    print(diskstable)
    return


def create_vm(args):
    """Create vms"""
    name = args.name
    image = args.image
    profile = args.profile
    profilefile = args.profilefile
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if 'name' in overrides:
        name = overrides['name']
    if name is None:
        name = nameutils.get_random_name()
        if config.type in ['gcp', 'kubevirt']:
            name = name.replace('_', '-')
        if config.type != 'aws':
            common.pprint("Using %s as name of the vm" % name)
    if image is not None:
        if image in config.profiles:
            common.pprint("Using %s as profile" % image)
        profile = image
    elif profile.endswith('.yml'):
        profilefile = profile
        profile = None
        if not os.path.exists(profilefile):
            common.pprint("Missing profile file", color='red')
            os._exit(1)
        else:
            with open(profilefile, 'r') as entries:
                config.profiles = yaml.safe_load(entries)
    result = config.create_vm(name, profile, overrides=overrides)
    code = common.handle_response(result, name, element='', action='created', client=config.client)
    return code


def clone_vm(args):
    """Clone existing vm"""
    name = args.name
    base = args.base
    full = args.full
    start = args.start
    common.pprint("Cloning vm %s from vm %s..." % (name, base))
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    k.clone(base, name, full=full, start=start)


def update_vm(args):
    """Update ip, memory or numcpus"""
    ip1 = args.ip1
    flavor = args.flavor
    numcpus = args.numcpus
    memory = args.memory
    plan = args.plan
    autostart = args.autostart
    noautostart = args.noautostart
    dns = args.dns
    host = args.host
    domain = args.domain
    cloudinit = args.cloudinit
    image = args.image
    net = args.network
    information = args.information
    iso = args.iso
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    for name in names:
        if dns:
            common.pprint("Creating Dns entry for %s..." % name)
            if net is not None:
                nets = [net]
            else:
                nets = k.vm_ports(name)
            if nets and domain is None:
                domain = nets[0]
            if not nets:
                return
            else:
                k.reserve_dns(name=name, nets=nets, domain=domain, ip=ip1)
        elif ip1 is not None:
            common.pprint("Updating ip of vm %s to %s..." % (name, ip1))
            k.update_metadata(name, 'ip', ip1)
        elif cloudinit:
            common.pprint("Removing cloudinit information of vm %s" % name)
            k.remove_cloudinit(name)
            return
        elif plan is not None:
            common.pprint("Updating plan of vm %s to %s..." % (name, plan))
            k.update_metadata(name, 'plan', plan)
        elif image is not None:
            common.pprint("Updating image of vm %s to %s..." % (name, image))
            k.update_metadata(name, 'image', image)
        elif memory is not None:
            common.pprint("Updating memory of vm %s to %s..." % (name, memory))
            k.update_memory(name, memory)
        elif numcpus is not None:
            common.pprint("Updating numcpus of vm %s to %s..." % (name, numcpus))
            k.update_cpus(name, numcpus)
        elif autostart:
            common.pprint("Setting autostart for vm %s..." % name)
            k.update_start(name, start=True)
        elif noautostart:
            common.pprint("Removing autostart for vm %s..." % name)
            k.update_start(name, start=False)
        elif information:
            common.pprint("Setting information for vm %s..." % name)
            k.update_descrmation(name, information)
        elif iso is not None:
            common.pprint("Switching iso for vm %s to %s..." % (name, iso))
            k.update_iso(name, iso)
        elif flavor is not None:
            common.pprint("Updating flavor of vm %s to %s..." % (name, flavor))
            k.update_flavor(name, flavor)
        elif host:
            common.pprint("Creating Host entry for vm %s..." % name)
            nets = k.vm_ports(name)
            if not nets:
                return
            if domain is None:
                domain = nets[0]
            k.reserve_host(name, nets, domain)


def create_vmdisk(args):
    """Add disk to vm"""
    name = args.name
    size = args.size
    image = args.image
    pool = args.pool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if size is None:
        common.pprint("Missing size. Leaving...", color='red')
        os._exit(1)
    if pool is None:
        common.pprint("Missing pool. Leaving...", color='red')
        os._exit(1)
    if name is None:
        common.pprint("Missing name. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding disk to %s..." % name)
    k.add_disk(name=name, size=size, pool=pool, image=image)


def diskdelete_vm(args):
    """Delete disk of vm"""
    name = args.name
    diskname = args.diskname
    pool = args.pool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if diskname is None:
        common.pprint("Missing diskname. Leaving...", color='red')
        os._exit(1)
    common.pprint("Deleting disk %s" % diskname)
    k.delete_disk(name=name, diskname=diskname, pool=pool)
    return


def create_dns(args):
    """Create dns entries"""
    name = args.name
    net = args.net
    domain = net
    ip = args.ip
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Creating Dns entry for %s..." % name)
    k.reserve_dns(name=name, nets=[net], domain=domain, ip=ip)


def delete_dns(args):
    """Delete dns entries"""
    name = args.name
    net = args.net
    domain = net
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting Dns entry for %s..." % name)
    k.delete_dns(name, domain)


def export_vm(args):
    """Export a vm"""
    image = args.image
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    codes = []
    for name in names:
        result = k.export(name=name, image=image)
        if result['result'] == 'success':
            common.pprint("Exporting vm %s" % name)
            codes.append(0)
        else:
            reason = result['reason']
            common.pprint("Could not delete vm %s because %s" % (name, reason), color='red')
            codes.append(1)
    os._exit(1 if 1 in codes else 0)


def create_lb(args):
    """Create loadbalancer"""
    checkpath = args.checkpath
    checkport = args.checkport
    ports = args.ports
    domain = args.domain
    internal = args.internal
    vms = args.vms.split(',') if args.vms is not None else []
    ports = args.ports.split(',') if args.ports is not None else []
    name = nameutils.get_random_name().replace('_', '-') if args.name is None else args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.handle_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain, checkport=checkport,
                               internal=internal)
    return 0


def delete_lb(args):
    """Delete loadbalancer"""
    checkpath = args.checkpath
    checkport = args.checkport
    yes = args.yes
    ports = args.ports
    domain = args.domain
    internal = args.internal
    vms = args.vms.split(',') if args.vms is not None else []
    ports = args.ports.split(',') if args.ports is not None else []
    name = nameutils.get_random_name().replace('_', '-') if args.name is None else args.name
    if not yes:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.handle_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, delete=True, domain=domain,
                               checkport=checkport, internal=internal)
    return 0


def add_nic(args):
    """Add nic to vm"""
    name = args.name
    network = args.network
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if network is None:
        common.pprint("Missing network. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding Nic to %s..." % name)
    k.add_nic(name=name, network=network)


def delete_nic(args):
    """Delete nic of vm"""
    name = args.name
    interface = args.interface
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting nic from %s..." % name)
    k.delete_nic(name, interface)
    return


def create_pool(args):
    """Create/Delete pool"""
    pool = args.pool
    pooltype = args.pooltype
    path = args.path
    thinpool = args.thinpool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if path is None:
        common.pprint("Missing path. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding pool %s..." % pool)
    k.create_pool(name=pool, poolpath=path, pooltype=pooltype, thinpool=thinpool)


def delete_pool(args):
    """Delete pool"""
    pool = args.pool
    full = args.full
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting pool %s..." % pool)
    k.delete_pool(name=pool, full=full)
    return


def create_plan(args):
    """Create plan"""
    plan = args.plan
    ansible = args.ansible
    url = args.url
    path = args.path
    container = args.container
    inputfile = args.inputfile
    delay = args.delay
    volumepath = args.volumepath
    paramfile = args.paramfile
    if os.path.exists("/i_am_a_container"):
        inputfile = "%s/%s" % (volumepath, inputfile) if inputfile is not None else "%s/kcli_plan.yml" % volumepath
        if paramfile is not None:
            paramfile = "%s/%s" % (volumepath, paramfile)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if plan is None:
        plan = nameutils.get_random_name()
        common.pprint("Using %s as name of the plan" % plan)
    config.plan(plan, ansible=ansible, url=url, path=path,
                container=container, inputfile=inputfile,
                delay=delay, overrides=overrides)
    return 0


def update_plan(args):
    """Update plan"""
    autostart = args.autostart
    plan = args.plan
    url = args.url
    path = args.path
    container = args.container
    inputfile = args.inputfile
    volumepath = args.volumepath
    paramfile = args.paramfile
    if os.path.exists("/i_am_a_container"):
        inputfile = "%s/%s" % (volumepath, inputfile) if inputfile is not None else "%s/kcli_plan.yml" % volumepath
        if paramfile is not None:
            paramfile = "%s/%s" % (volumepath, paramfile)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if autostart:
        config.plan(plan, autostart=autostart)
        return 0
    config.plan(plan, url=url, path=path, container=container, inputfile=inputfile, overrides=overrides, update=True)
    return 0


def delete_plan(args):
    """Delete plan"""
    plan = args.plan
    yes = args.yes
    if not yes:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, delete=True)
    return 0


def start_plan(args):
    """Start plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, start=True)
    return 0


def stop_plan(args):
    """Stop plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, stop=True)
    return 0


def autostart_plan(args):
    """Autostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, autostart=True)
    return 0


def noautostart_plan(args):
    """Noautostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, autostart=False)
    return 0


def restart_plan(args):
    """Restart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, delete=True)
    return 0


def desc_plan(args):
    """Info plan """
    plan = args.plan
    url = args.url
    path = args.path
    inputfile = args.inputfile
    volumepath = args.volumepath
    if os.path.exists("/i_am_a_container"):
        inputfile = "%s/%s" % (volumepath, inputfile) if inputfile is not None else "%s/kcli_plan.yml" % volumepath
    if url is None:
        inputfile = plan if inputfile is None and plan is not None else inputfile
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        baseconfig.info_plan(inputfile)
    else:
        config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
        config.plan(plan, url=url, path=path, inputfile=inputfile, info=True)
    return 0


def render_plan(args):
    """Render plan file"""
    plan = None
    inputfile = args.inputfile
    volumepath = args.volumepath
    paramfile = args.paramfile
    if os.path.exists("/i_am_a_container"):
        inputfile = "%s/%s" % (volumepath, inputfile) if inputfile is not None else "%s/kcli_plan.yml" % volumepath
        if paramfile is not None:
            paramfile = "%s/%s" % (volumepath, paramfile)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    renderfile = baseconfig.process_inputfile(plan, inputfile, overrides=overrides, onfly=False)
    print(renderfile)
    return 0


def snapshot_plan(args):
    """Snapshot plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, snapshot=True)
    return 0


def revert_plan(args):
    """Revert snapshot of plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, revert=True)
    return 0


def create_repo(args):
    """Create repo"""
    repo = args.repo
    url = args.url
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if repo is None:
        common.pprint("Missing repo. Leaving...", color='red')
        os._exit(1)
    if url is None:
        common.pprint("Missing url. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding repo %s..." % repo)
    baseconfig.create_repo(repo, url)
    return 0


def delete_repo(args):
    """Delete repo"""
    repo = args.repo
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if repo is None:
        common.pprint("Missing repo. Leaving...", color='red')
        os._exit(1)
    common.pprint("Deleting repo %s..." % repo)
    baseconfig.delete_repo(repo)
    return


def update_repo(args):
    """Update repo"""
    repo = args.repo
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if repo is None:
        common.pprint("Updating all repos...", color='blue')
        repos = baseconfig.list_repos()
        for repo in repos:
            common.pprint("Updating repo %s..." % repo)
            baseconfig.update_repo(repo)
    else:
        common.pprint("Updating repo %s..." % repo)
        baseconfig.update_repo(repo)
    return


def create_product(args):
    """Create product"""
    repo = args.repo
    product = args.product
    latest = args.latest
    group = args.group
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    plan = overrides['plan'] if 'plan' in overrides else None
    info = args.info
    search = args.search
    if info:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        common.pprint("Providing information on product %s..." % product)
        baseconfig.info_product(product, repo, group)
    elif search:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        products = PrettyTable(["Repo", "Group", "Product", "Description", "Numvms", "Memory"])
        products.align["Repo"] = "l"
        productsinfo = baseconfig.list_products(repo=repo)
        for prod in sorted(productsinfo, key=lambda x: (x['repo'], x['group'], x['name'])):
            name = prod['name']
            repo = prod['repo']
            prodgroup = prod['group']
            description = prod.get('description', 'N/A')
            if product.lower() not in name.lower() and product.lower() not in description.lower():
                continue
            if group is not None and prodgroup != group:
                continue
            numvms = prod.get('numvms', 'N/A')
            memory = prod.get('memory', 'N/A')
            group = prod.get('group', 'N/A')
            products.add_row([repo, group, name, description, numvms, memory])
        print(products)
    else:
        config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
        common.pprint("Creating product %s..." % product)
        config.create_product(product, repo=repo, group=group, plan=plan, latest=latest, overrides=overrides)
    return 0


def ssh_vm(args):
    """Ssh into vm"""
    l = args.L
    r = args.R
    D = args.D
    X = args.X
    Y = args.Y
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    name = [common.get_lastvm(config.client)] if not args.name else args.name
    k = config.k
    tunnel = config.tunnel
    insecure = config.insecure
    if len(name) > 1:
        cmd = ' '.join(name[1:])
    else:
        cmd = None
    name = name[0]
    if '@' in name and len(name.split('@')) == 2:
        user = name.split('@')[0]
        name = name.split('@')[1]
    else:
        user = None
    if os.path.exists("/i_am_a_container") and not os.path.exists("/root/.kcli/config.yml")\
            and not os.path.exists("/root/.ssh/config"):
        insecure = True
    sshcommand = k.ssh(name, user=user, local=l, remote=r, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, Y=Y, D=D)
    if sshcommand is not None:
        if find_executable('ssh') is not None:
            os.system(sshcommand)
        else:
            print(sshcommand)
    else:
        common.pprint("Couldnt ssh to %s" % name, color='red')


def scp_vm(args):
    """Scp into vm"""
    recursive = args.recursive
    volumepath = args.volumepath
    source = args.source[0]
    source = source if not os.path.exists("/i_am_a_container") else "%s/%s" % (volumepath, source)
    destination = args.destination[0]
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    tunnel = config.tunnel
    if len(source.split(':')) == 2:
        name, source = source.split(':')
        download = True
    elif len(destination.split(':')) == 2:
        name, destination = destination.split(':')
        download = False
    else:
        common.pprint("Couldn't run scp", color='red')
        return
    if '@' in name and len(name.split('@')) == 2:
        user, name = name.split('@')
    else:
        user = None
    scpcommand = k.scp(name, user=user, source=source, destination=destination,
                       tunnel=tunnel, download=download, recursive=recursive)
    if scpcommand is not None:
        if find_executable('scp') is not None:
            os.system(scpcommand)
        else:
            print(scpcommand)
    else:
        common.pprint("Couldn't run scp", color='red')


def create_network(args):
    """Create Network"""
    name = args.name
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    isolated = args.isolated
    cidr = args.cidr
    nodhcp = args.nodhcp
    domain = args.domain
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if name is None:
        common.pprint("Missing Network", color='red')
        os._exit(1)
    if isolated:
        nat = False
    else:
        nat = True
    dhcp = not nodhcp
    result = k.create_network(name=name, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, overrides=overrides)
    common.handle_response(result, name, element='Network')


def delete_network(args):
    """Delete Network"""
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if name is None:
        common.pprint("Missing Network", color='red')
        os._exit(1)
    result = k.delete_network(name=name)
    common.handle_response(result, name, element='Network', action='deleted')


def create_host(args):
    """Generate basic config file"""
    host = args.host
    default = args.default
    port = args.port
    user = args.user
    protocol = args.protocol
    url = args.url
    pool = args.pool
    poolpath = args.poolpath
    common.bootstrap(args.client, host, port, user, protocol, url, pool, poolpath)
    if default:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        baseconfig.set_defaults()


def create_container(args):
    """Create container"""
    name = args.name
    profile = args.profile
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    if name is None:
        name = nameutils.get_random_name()
        if config.type == 'kubevirt':
            name = name.replace('_', '-')
    if profile is None:
        common.pprint("Missing profile", color='red')
        os._exit(1)
    containerprofiles = {k: v for k, v in config.profiles.items() if 'type' in v and v['type'] == 'container'}
    if profile not in containerprofiles:
        common.pprint("profile %s not found. Trying to use the profile as image"
                      "and default values..." % profile, color='blue')
        cont.create_container(name, profile, overrides=overrides)
    else:
        common.pprint("Deploying container %s from profile %s..." % (name, profile))
        profile = containerprofiles[profile]
        image = next((e for e in [profile.get('image'), profile.get('image')] if e is not None), None)
        if image is None:
            common.pprint("Missing image in profile %s. Leaving..." % profile, color='red')
            os._exit(1)
        cmd = profile.get('cmd', None)
        ports = profile.get('ports', None)
        environment = profile.get('environment', None)
        volumes = next((e for e in [profile.get('volumes'), profile.get('disks')] if e is not None), None)
        cont.create_container(name, image, nets=None, cmd=cmd, ports=ports, volumes=volumes, environment=environment)
    common.pprint("container %s created" % name)
    return


def snapshotcreate_vm(args):
    """Create snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Creating snapshot of %s named %s..." % (name, snapshot))
    result = k.snapshot(snapshot, name)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def snapshotdelete_vm(args):
    """Delete snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting snapshot of %s named %s..." % (name, snapshot))
    result = k.snapshot(snapshot, name, delete=True)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def snapshotrevert_vm(args):
    """Revert snapshot of vm"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Reverting snapshot of %s named %s..." % (name, snapshot))
    result = k.snapshot(snapshot, name, revert=True)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def snapshotlist_vm(args):
    """List snapshots of vm"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Listing snapshots of %s..." % name)
    snapshots = k.snapshot(snapshot, name, listing=True)
    if isinstance(snapshots, dict):
        common.pprint("Vm %s not found" % name, color='red')
        return
    else:
        for snapshot in snapshots:
            print(snapshot)
    return


def report_host(args):
    """Report info about host"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    k.report()


def switch_host(args):
    """Handle host"""
    host = args.host
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.switch_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def list_keyword(args):
    """List keywords"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    keywords = baseconfig.list_keywords()
    print(keywords)


def cli():
    """

    """
    parser = argparse.ArgumentParser(description='Libvirt/Ovirt/Vsphere/Gcp/Aws/Openstack/Kubevirt Wrapper')
    parser.add_argument('-C', '--client')
    parser.add_argument('--containerclient', help='Containerclient to use')
    parser.add_argument('--dnsclient', help='Dnsclient to use')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-n', '--namespace', help='Namespace to use. specific to kubevirt')
    parser.add_argument('-r', '--region', help='Region to use. specific to aws/gcp')
    parser.add_argument('-z', '--zone', help='Zone to use. specific to gcp')
    parser.add_argument('-v', '--version', action='version', version="%s" % __version__)

    subparsers = parser.add_subparsers(metavar='')

    # subcommands
    clone_desc = 'Clone Vm'
    clone_parser = subparsers.add_parser('clone', description=clone_desc, help=clone_desc)
    clone_subparsers = clone_parser.add_subparsers(metavar='', dest='subcommand_clone')

    console_desc = 'Console Vm/Container'
    console_parser = subparsers.add_parser('console', description=console_desc, help=console_desc)
    console_subparsers = console_parser.add_subparsers(metavar='', dest='subcommand_console')

    create_desc = 'Create Object'
    create_parser = subparsers.add_parser('create', description=create_desc, help=create_desc)
    create_subparsers = create_parser.add_subparsers(metavar='', dest='subcommand_create')

    delete_desc = 'Delete Object'
    delete_parser = subparsers.add_parser('delete', description=delete_desc, help=delete_desc)
    delete_subparsers = delete_parser.add_subparsers(metavar='', dest='subcommand_delete')

    disable_desc = 'Disable Host'
    disable_parser = subparsers.add_parser('disable', description=disable_desc, help=disable_desc)
    disable_subparsers = disable_parser.add_subparsers(metavar='', dest='subcommand_disable')

    download_desc = 'Download Image'
    download_parser = subparsers.add_parser('download', description=download_desc, help=download_desc)
    download_subparsers = download_parser.add_subparsers(metavar='', dest='subcommand_download')

    enable_desc = 'Enable Host'
    enable_parser = subparsers.add_parser('enable', description=enable_desc, help=enable_desc)
    enable_subparsers = enable_parser.add_subparsers(metavar='', dest='subcommand_enable')

    export_desc = 'Export Vm'
    export_parser = subparsers.add_parser('export', description=export_desc, help=export_desc)
    export_subparsers = export_parser.add_subparsers(metavar='', dest='subcommand_export')

    info_desc = 'Info Host/Plan/Vm'
    info_parser = subparsers.add_parser('info', description=info_desc, help=info_desc)
    info_subparsers = info_parser.add_subparsers(metavar='', dest='subcommand_info')

    list_desc = 'List Object'
    list_parser = subparsers.add_parser('list', description=list_desc, help=list_desc, aliases=['get'])
    list_subparsers = list_parser.add_subparsers(metavar='', dest='subcommand_list')

    render_desc = 'Render Plan/file'
    render_parser = subparsers.add_parser('render', description=render_desc, help=render_desc)
    render_subparsers = render_parser.add_subparsers(metavar='', dest='subcommand_render')

    restart_desc = 'Restart Vm/Plan/Container'
    restart_parser = subparsers.add_parser('restart', description=restart_desc, help=restart_desc)
    restart_subparsers = restart_parser.add_subparsers(metavar='', dest='subcommand_restart')

    revert_desc = 'Revert Snapshot/Plan Snapshot'
    revert_parser = subparsers.add_parser('revert', description=revert_desc, help=revert_desc)
    revert_subparsers = revert_parser.add_subparsers(metavar='', dest='subcommand_revert')

    scp_desc = 'Scp Into Vm'
    scp_parser = subparsers.add_parser('scp', description=scp_desc, help=scp_desc)
    scp_subparsers = scp_parser.add_subparsers(metavar='', dest='subcommand_scp')

    snapshot_desc = 'Snapshot Plan'
    snapshot_parser = subparsers.add_parser('snapshot', description=snapshot_desc, help=snapshot_desc)
    snapshot_subparsers = snapshot_parser.add_subparsers(metavar='', dest='subcommand_snapshot')

    ssh_desc = 'Ssh Into Vm'
    ssh_parser = subparsers.add_parser('ssh', description=ssh_desc, help=ssh_desc)
    ssh_subparsers = ssh_parser.add_subparsers(metavar='', dest='subcommand_ssh')

    start_desc = 'Start Vm/Plan/Container'
    start_parser = subparsers.add_parser('start', description=start_desc, help=start_desc)
    start_subparsers = start_parser.add_subparsers(metavar='', dest='subcommand_start')

    stop_desc = 'Stop Vm/Plan/Container'
    stop_parser = subparsers.add_parser('stop', description=stop_desc, help=stop_desc)
    stop_subparsers = stop_parser.add_subparsers(metavar='', dest='subcommand_stop')

    switch_desc = 'Switch Host'
    switch_parser = subparsers.add_parser('switch', description=switch_desc, help=switch_desc)
    switch_subparsers = switch_parser.add_subparsers(metavar='', dest='subcommand_switch')

    sync_desc = 'Sync Host'
    sync_parser = subparsers.add_parser('sync', description=sync_desc, help=sync_desc)
    sync_subparsers = sync_parser.add_subparsers(metavar='', dest='subcommand_sync')

    update_desc = 'Update Vm/Plan/Repo'
    update_parser = subparsers.add_parser('update', description=update_desc, help=update_desc)
    update_subparsers = update_parser.add_subparsers(metavar='', dest='subcommand_update')

    # sub subcommands
    containerconsole_desc = 'Console Container'
    containerconsole_parser = console_subparsers.add_parser('container', description=containerconsole_desc,
                                                            help=containerconsole_desc)
    containerconsole_parser.add_argument('name', metavar='CONTAINERNAME', nargs='?')
    containerconsole_parser.set_defaults(func=console_container)

    containercreate_desc = 'Create Container'
    containercreate_parser = create_subparsers.add_parser('container', description=containercreate_desc,
                                                          help=containercreate_desc)
    containercreate_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    containercreate_parser.add_argument('-P', '--param', action='append',
                                        help='specify parameter or keyword for rendering (multiple can be specified)',
                                        metavar='PARAM')
    containercreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    containercreate_parser.add_argument('name', metavar='NAME', nargs='?')
    containercreate_parser.set_defaults(func=create_container)

    containerdelete_desc = 'Delete Container'
    containerdelete_parser = delete_subparsers.add_parser('container', description=containerdelete_desc,
                                                          help=containerdelete_desc)
    containerdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    containerdelete_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    containerdelete_parser.set_defaults(func=delete_container)

    containerimagelist_desc = 'List Container Images'
    containerimagelist_parser = list_subparsers.add_parser('container-image', description=containerimagelist_desc,
                                                           help=containerimagelist_desc)
    containerimagelist_parser.set_defaults(func=imagelist_container)

    containerlist_desc = 'List Containers'
    containerlist_parser = list_subparsers.add_parser('container', description=containerlist_desc,
                                                      help=containerlist_desc)
    containerlist_parser.add_argument('--filters', choices=('up', 'down'))
    containerlist_parser.set_defaults(func=list_container)

    containerprofilelist_desc = 'List Container Profiles'
    containerprofilelist_parser = list_subparsers.add_parser('list', description=containerprofilelist_desc,
                                                             help=containerprofilelist_desc)
    containerprofilelist_parser.add_argument('--short', action='store_true')
    containerprofilelist_parser.set_defaults(func=profilelist_container)

    containerrestart_desc = 'Restart Containers'
    containerrestart_parser = restart_subparsers.add_parser('container', description=containerrestart_desc,
                                                            help=containerrestart_desc)
    containerrestart_parser.add_argument('names', metavar='CONTAINERNAMES', nargs='*')
    containerrestart_parser.set_defaults(func=restart_container)

    containerstart_desc = 'Start Containers'
    containerstart_parser = start_subparsers.add_parser('container', description=containerstart_desc,
                                                        help=containerstart_desc)
    containerstart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    containerstart_parser.set_defaults(func=start_container)

    containerstop_desc = 'Stop Containers'
    containerstop_parser = stop_subparsers.add_parser('container', description=containerstop_desc,
                                                      help=containerstop_desc)
    containerstop_parser.add_argument('names', metavar='CONTAINERNAMES', nargs='*')
    containerstop_parser.set_defaults(func=stop_container)

    dnscreate_desc = 'Create Dns Entries'
    dnscreate_parser = create_subparsers.add_parser('dns', description=dnscreate_desc, help=dnscreate_desc)
    dnscreate_parser.add_argument('-n', '--net', help='Domain where to create entry', metavar='NET')
    dnscreate_parser.add_argument('-i', '--ip', help='Ip', metavar='IP')
    dnscreate_parser.add_argument('name', metavar='NAME', nargs='?')
    dnscreate_parser.set_defaults(func=create_dns)

    dnsdelete_desc = 'Delete Dns Entries'
    dnsdelete_parser = delete_subparsers.add_parser('dns', description=dnsdelete_desc, help=dnsdelete_desc)
    dnsdelete_parser.add_argument('-n', '--net', help='Domain where to create entry', metavar='NET')
    dnsdelete_parser.add_argument('name', metavar='NAME', nargs='?')
    dnsdelete_parser.set_defaults(func=delete_dns)

    hostcreate_desc = 'Create Host'
    hostcreate_parser = create_subparsers.add_parser('host', help=hostcreate_desc, description=hostcreate_desc)
    hostcreate_parser.add_argument('-d', '--default', help="add default values in config file", action='store_true')
    hostcreate_parser.add_argument('-H', '--host', help='Host to use', metavar='HOST')
    hostcreate_parser.add_argument('-p', '--port', help='Port to use', metavar='PORT')
    hostcreate_parser.add_argument('-u', '--user', help='User to use', default='root', metavar='USER')
    hostcreate_parser.add_argument('-P', '--protocol', help='Protocol to use', default='ssh', metavar='PROTOCOL')
    hostcreate_parser.add_argument('-U', '--url', help='URL to use', metavar='URL')
    hostcreate_parser.add_argument('--pool', help='Pool to use', metavar='POOL')
    hostcreate_parser.add_argument('--poolpath', help='Pool Path to use', metavar='POOLPATH')
    hostcreate_parser.add_argument('client', metavar='CLIENT', nargs='?')
    hostcreate_parser.set_defaults(func=create_host)

    hostdisable_desc = 'Disable Host'
    hostdisable_parser = disable_subparsers.add_parser('host', description=hostdisable_desc, help=hostdisable_desc)
    hostdisable_parser.add_argument('host', metavar='HOST', nargs='?')
    hostdisable_parser.set_defaults(func=disable_host)

    hostenable_desc = 'Enable Host'
    hostenable_parser = enable_subparsers.add_parser('host', description=hostenable_desc, help=hostenable_desc)
    hostenable_parser.add_argument('host', metavar='HOST', nargs='?')
    hostenable_parser.set_defaults(func=enable_host)

    hostlist_desc = 'List Hosts'
    hostlist_parser = list_subparsers.add_parser('host', description=hostlist_desc, help=hostlist_desc)
    hostlist_parser.set_defaults(func=list_host)

    hostreport_desc = 'Report Info About Host'
    hostreport_parser = argparse.ArgumentParser(add_help=False)
    hostreport_parser.set_defaults(func=report_host)
    info_subparsers.add_parser('host', parents=[hostreport_parser], description=hostreport_desc, help=hostreport_desc)

    hostswitch_desc = 'Switch Host'
    hostswitch_parser = argparse.ArgumentParser(add_help=False)
    hostswitch_parser.add_argument('host', help='HOST')
    hostswitch_parser.set_defaults(func=switch_host)
    switch_subparsers.add_parser('host', parents=[hostswitch_parser], description=hostswitch_desc, help=hostswitch_desc)

    hostsync_desc = 'Sync Host'
    hostsync_parser = sync_subparsers.add_parser('host', description=hostsync_desc, help=hostsync_desc)
    hostsync_parser.add_argument('hosts', help='HOSTS', nargs='*')
    hostsync_parser.set_defaults(func=sync_host)

    lbcreate_desc = 'Create Load Balancer'
    lbcreate_parser = create_subparsers.add_parser('lb', description=lbcreate_desc, help=lbcreate_desc)
    lbcreate_parser.add_argument('--checkpath', default='/index.html', help="Path to check. Defaults to /index.html")
    lbcreate_parser.add_argument('--checkport', default=80, help="Port to check. Defaults to 80")
    lbcreate_parser.add_argument('--domain', help='Domain to create a dns entry associated to the load balancer')
    lbcreate_parser.add_argument('-i', '--internal', action='store_true')
    lbcreate_parser.add_argument('-p', '--ports', default='443', help='Load Balancer Ports. Defaults to 443')
    lbcreate_parser.add_argument('-v', '--vms', help='Vms to add to the pool')
    lbcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    lbcreate_parser.set_defaults(func=create_lb)

    lbdelete_desc = 'Delete Load Balancer'
    lbdelete_parser = delete_subparsers.add_parser('lb', description=lbdelete_desc, help=lbdelete_desc)
    lbdelete_parser.add_argument('--checkpath', default='/index.html', help="Path to check. Defaults to /index.html")
    lbdelete_parser.add_argument('--checkport', default=80, help="Port to check. Defaults to 80")
    lbdelete_parser.add_argument('-d', '--delete', action='store_true')
    lbdelete_parser.add_argument('--domain', help='Domain to create a dns entry associated to the load balancer')
    lbdelete_parser.add_argument('-i', '--internal', action='store_true')
    lbdelete_parser.add_argument('-p', '--ports', default='443', help='Load Balancer Ports. Defaults to 443')
    lbdelete_parser.add_argument('-v', '--vms', help='Vms to add to the pool')
    lbdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    lbdelete_parser.add_argument('name', metavar='NAME', nargs='?')
    lbdelete_parser.set_defaults(func=delete_lb)

    lblist_desc = 'List Load Balancers'
    lblist_parser = list_subparsers.add_parser('lb', description=lblist_desc, help=lblist_desc)
    lblist_parser.add_argument('--short', action='store_true')
    lblist_parser.set_defaults(func=list_lb)

    profilecreate_desc = 'Create Profile'
    profilecreate_parser = argparse.ArgumentParser(add_help=False)
    profilecreate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (can specify multiple)',
                                      metavar='PARAM')
    profilecreate_parser.add_argument('profile', metavar='PROFILE')
    profilecreate_parser.set_defaults(func=create_profile)
    create_subparsers.add_parser('profile', parents=[profilecreate_parser], description=profilecreate_desc,
                                 help=profilecreate_desc)

    profilelist_desc = 'List Profiles'
    profilelist_parser = list_subparsers.add_parser('profile', description=profilelist_desc, help=profilelist_desc)
    profilelist_parser.add_argument('--short', action='store_true')
    profilelist_parser.set_defaults(func=list_profile)

    profiledelete_desc = 'Delete Profile'
    profiledelete_help = "Image to delete"
    profiledelete_parser = argparse.ArgumentParser(add_help=False)
    profiledelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    profiledelete_parser.add_argument('profile', help=profiledelete_help, metavar='PROFILE')
    profiledelete_parser.set_defaults(func=delete_profile)
    delete_subparsers.add_parser('profile', parents=[profiledelete_parser], description=profiledelete_desc,
                                 help=profiledelete_desc)

    flavorlist_desc = 'List Flavors'
    flavorlist_parser = list_subparsers.add_parser('flavor', description=flavorlist_desc, help=flavorlist_desc)
    flavorlist_parser.add_argument('--short', action='store_true')
    flavorlist_parser.set_defaults(func=list_flavor)

    isolist_desc = 'List Isos'
    isolist_parser = list_subparsers.add_parser('iso', description=isolist_desc, help=isolist_desc)
    isolist_parser.set_defaults(func=list_iso)

    keywordlist_desc = 'List Keyword'
    keywordlist_parser = list_subparsers.add_parser('keyword', description=keywordlist_desc, help=keywordlist_desc)
    keywordlist_parser.set_defaults(func=list_keyword)

    networklist_desc = 'List Networks'
    networklist_parser = list_subparsers.add_parser('network', description=networklist_desc, help=networklist_desc)
    networklist_parser.add_argument('--short', action='store_true')
    networklist_parser.add_argument('-s', '--subnets', action='store_true')
    networklist_parser.set_defaults(func=list_network)

    networkcreate_desc = 'Create Network'
    networkcreate_parser = create_subparsers.add_parser('network', description=networkcreate_desc,
                                                        help=networkcreate_desc)
    networkcreate_parser.add_argument('-i', '--isolated', action='store_true', help='Isolated Network')
    networkcreate_parser.add_argument('-c', '--cidr', help='Cidr of the net', metavar='CIDR')
    networkcreate_parser.add_argument('--nodhcp', action='store_true', help='Disable dhcp on the net')
    networkcreate_parser.add_argument('--domain', help='DNS domain. Defaults to network name')
    networkcreate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (can specify multiple)',
                                      metavar='PARAM')
    networkcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    networkcreate_parser.add_argument('name', metavar='NETWORK')
    networkcreate_parser.set_defaults(func=create_network)

    networkdelete_desc = 'Delete Network'
    networkdelete_parser = delete_subparsers.add_parser('network', description=networkdelete_desc,
                                                        help=networkdelete_desc)
    networkdelete_parser.add_argument('name', metavar='NETWORK')
    networkdelete_parser.set_defaults(func=delete_network)

    plancreate_desc = 'Create Plan'
    plancreate_parser = create_subparsers.add_parser('plan', description=plancreate_desc, help=plancreate_desc)
    plancreate_parser.add_argument('-A', '--ansible', help='Generate ansible inventory', action='store_true')
    plancreate_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    plancreate_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan',
                                   metavar='PATH')
    plancreate_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    plancreate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    plancreate_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                                   default='/workdir', metavar='VOLUMEPATH')
    plancreate_parser.add_argument('--delay', default=0, help="Delay between each vm's creation", metavar='DELAY')
    plancreate_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    plancreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    plancreate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plancreate_parser.set_defaults(func=create_plan)

    plandelete_desc = 'Delete Plan'
    plandelete_parser = delete_subparsers.add_parser('plan', description=plandelete_desc, help=plandelete_desc)
    plandelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    plandelete_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plandelete_parser.set_defaults(func=delete_plan)

    planinfo_desc = 'Info Plan'
    planinfo_parser = info_subparsers.add_parser('plan', description=plandelete_desc, help=planinfo_desc)
    planinfo_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planinfo_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan', metavar='PATH')
    planinfo_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    planinfo_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                                 default='/workdir', metavar='VOLUMEPATH')
    planinfo_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planinfo_parser.set_defaults(func=desc_plan)

    planlist_desc = 'List Plans'
    planlist_parser = list_subparsers.add_parser('plan', description=planlist_desc, help=planlist_desc)
    planlist_parser.set_defaults(func=list_plan)

    planrender_desc = 'Render Plans/Files'
    planrender_parser = render_subparsers.add_parser('plan', description=planrender_desc,
                                                     help=planrender_desc)
    planrender_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planrender_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    planrender_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    planrender_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                                   default='/workdir', metavar='VOLUMEPATH')
    planrender_parser.set_defaults(func=render_plan)

    planrestart_desc = 'Restart Plan'
    planrestart_parser = restart_subparsers.add_parser('plan', description=planrestart_desc, help=planrestart_desc)
    planrestart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planrestart_parser.set_defaults(func=restart_plan)

    planrevert_desc = 'Revert Snapshot Of Plan'
    planrevert_parser = revert_subparsers.add_parser('plan', description=planrevert_desc, help=planrevert_desc)
    planrevert_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planrevert_parser.set_defaults(func=revert_plan)

    plansnapshot_desc = 'Snapshot Plan'
    plansnapshot_parser = snapshot_subparsers.add_parser('plan', description=plansnapshot_desc, help=plansnapshot_desc)
    plansnapshot_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plansnapshot_parser.set_defaults(func=snapshot_plan)

    planstart_desc = 'Start Plan'
    planstart_parser = start_subparsers.add_parser('plan', description=planstart_desc, help=planstart_desc)
    planstart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planstart_parser.set_defaults(func=start_plan)

    planstop_desc = 'Stop Plan'
    planstop_parser = stop_subparsers.add_parser('plan', description=planstop_desc, help=planstop_desc)
    planstop_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planstop_parser.set_defaults(func=stop_plan)

    planupdate_desc = 'Update Plan'
    planupdate_parser = update_subparsers.add_parser('plan', description=planupdate_desc, help=planupdate_desc)
    planupdate_parser.add_argument('--autostart', action='store_true', help='Set autostart for vms of the plan')
    planupdate_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    planupdate_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan',
                                   metavar='PATH')
    planupdate_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    planupdate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planupdate_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    planupdate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    planupdate_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                                   default='/workdir', metavar='VOLUMEPATH')
    planupdate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planupdate_parser.set_defaults(func=update_plan)

    poolcreate_desc = 'Create Pool'
    poolcreate_parser = create_subparsers.add_parser('pool', description=poolcreate_desc, help=poolcreate_desc)
    poolcreate_parser.add_argument('-f', '--full', action='store_true')
    poolcreate_parser.add_argument('-t', '--pooltype', help='Type of the pool', choices=('dir', 'lvm', 'zfs'),
                                   default='dir')
    poolcreate_parser.add_argument('-p', '--path', help='Path of the pool', metavar='PATH')
    poolcreate_parser.add_argument('--thinpool', help='Existing thin pool to use with lvm', metavar='THINPOOL')
    poolcreate_parser.add_argument('pool')
    poolcreate_parser.set_defaults(func=create_pool)

    pooldelete_desc = 'Delete Pool'
    pooldelete_parser = delete_subparsers.add_parser('pool', description=pooldelete_desc, help=pooldelete_desc)
    pooldelete_parser.add_argument('-d', '--delete', action='store_true')
    pooldelete_parser.add_argument('-f', '--full', action='store_true')
    pooldelete_parser.add_argument('-p', '--path', help='Path of the pool', metavar='PATH')
    pooldelete_parser.add_argument('--thinpool', help='Existing thin pool to use with lvm', metavar='THINPOOL')
    pooldelete_parser.add_argument('pool')
    pooldelete_parser.set_defaults(func=delete_pool)

    poollist_desc = 'List Pools'
    poollist_parser = list_subparsers.add_parser('pool', description=poollist_desc, help=poollist_desc)
    poollist_parser.add_argument('--short', action='store_true')
    poollist_parser.set_defaults(func=list_pool)

    product_desc = 'Create Product'
    product_parser = create_subparsers.add_parser('product', description=product_desc, help=product_desc)
    product_parser.add_argument('-g', '--group', help='Group to use as a name during deployment', metavar='GROUP')
    product_parser.add_argument('-i', '--info', action='store_true', help='Provide information on the given product')
    product_parser.add_argument('-l', '--latest', action='store_true', help='Grab latest version of the plans')
    product_parser.add_argument('-P', '--param', action='append',
                                help='Define parameter for rendering within '
                                'scripts. Can be repeated several times',
                                metavar='PARAM')
    product_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    product_parser.add_argument('-r', '--repo', help='Repo to use, '
                                'if deploying a product present in several '
                                'repos', metavar='REPO')
    product_parser.add_argument('-s', '--search', action='store_true',
                                help='Display matching products')
    product_parser.add_argument('product', metavar='PRODUCT')
    product_parser.set_defaults(func=create_product)

    productlist_desc = 'List Products'
    productlist_parser = list_subparsers.add_parser('product', description=productlist_desc, help=productlist_desc)
    productlist_parser.add_argument('-g', '--group', help='Only Display products of the indicated group',
                                    metavar='GROUP')
    productlist_parser.add_argument('-r', '--repo', help='Only Display products of the indicated repository',
                                    metavar='REPO')
    productlist_parser.set_defaults(func=list_product)

    repocreate_desc = 'Create Repo'
    repocreate_parser = create_subparsers.add_parser('repo', description=repocreate_desc, help=repocreate_desc)
    repocreate_parser.add_argument('-u', '--url', help='URL of the repo', metavar='URL')
    repocreate_parser.add_argument('repo')
    repocreate_parser.set_defaults(func=create_repo)

    repodelete_desc = 'Delete Repo'
    repodelete_parser = delete_subparsers.add_parser('repo', description=repodelete_desc, help=repodelete_desc)
    repodelete_parser.add_argument('repo')
    repodelete_parser.set_defaults(func=delete_repo)

    repolist_desc = 'List Repos'
    repolist_parser = list_subparsers.add_parser('repo', description=repolist_desc, help=repolist_desc)
    repolist_parser.set_defaults(func=list_repo)

    repoupdate_desc = 'Update Repo'
    repoupdate_parser = update_subparsers.add_parser('repo', description=repoupdate_desc, help=repoupdate_desc)
    repoupdate_parser.add_argument('repo')
    repoupdate_parser.set_defaults(func=update_repo)

    imagedelete_desc = 'Delete Image'
    imagedelete_help = "Image to delete"
    imagedelete_parser = argparse.ArgumentParser(add_help=False)
    imagedelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    imagedelete_parser.add_argument('images', help=imagedelete_help, metavar='IMAGES', nargs='*')
    imagedelete_parser.set_defaults(func=delete_image)
    delete_subparsers.add_parser('image', parents=[imagedelete_parser], description=imagedelete_desc,
                                 help=imagedelete_desc)

    imagedownload_desc = 'Download Image'
    imagedownload_help = "Image to download. Choose between \n%s" % '\n'.join(IMAGES.keys())
    imagedownload_parser = argparse.ArgumentParser(add_help=False)
    imagedownload_parser.add_argument('-c', '--cmd', help='Extra command to launch after downloading', metavar='CMD')
    imagedownload_parser.add_argument('-p', '--pool', help='Pool to use. Defaults to default', metavar='POOL')
    imagedownload_parser.add_argument('-u', '--url', help='Url to use', metavar='URL')
    imagedownload_parser.add_argument('image', choices=sorted(IMAGES.keys()), help=imagedownload_help, metavar='IMAGE')
    imagedownload_parser.set_defaults(func=download_image)
    download_subparsers.add_parser('image', parents=[imagedownload_parser], description=imagedownload_desc,
                                   help=imagedownload_desc)

    imagelist_desc = 'List Images'
    imagelist_parser = list_subparsers.add_parser('image', description=imagelist_desc, help=imagelist_desc,
                                                  aliases=['template'])
    imagelist_parser.set_defaults(func=list_image)

    vmclone_desc = 'Clone Vm'
    vmclone_parser = clone_subparsers.add_parser('vm', description=vmclone_desc, help=vmclone_desc)
    vmclone_parser.add_argument('-b', '--base', help='Base VM', metavar='BASE')
    vmclone_parser.add_argument('-f', '--full', action='store_true', help='Full Clone')
    vmclone_parser.add_argument('-s', '--start', action='store_true', help='Start cloned VM')
    vmclone_parser.add_argument('name', metavar='VMNAME')
    vmclone_parser.set_defaults(func=clone_vm)

    vmconsole_desc = 'Vm Console (vnc/spice/serial)'
    vmconsole_parser = argparse.ArgumentParser(add_help=False)
    vmconsole_parser.add_argument('-s', '--serial', action='store_true')
    vmconsole_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmconsole_parser.set_defaults(func=console_vm)
    console_subparsers.add_parser('vm', parents=[vmconsole_parser], description=vmconsole_desc, help=vmconsole_desc)

    vmcreate_desc = 'Create Vm'
    vmcreate_parser = argparse.ArgumentParser(add_help=False)
    vmcreate_parser_group = vmcreate_parser.add_mutually_exclusive_group(required=True)
    vmcreate_parser_group.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    vmcreate_parser_group.add_argument('-i', '--image', help='Image to use', metavar='IMAGE')
    vmcreate_parser.add_argument('--profilefile', help='File to load profiles from', metavar='PROFILEFILE')
    vmcreate_parser.add_argument('-P', '--param', action='append',
                                 help='specify parameter or keyword for rendering (multiple can be specified)',
                                 metavar='PARAM')
    vmcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    vmcreate_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmcreate_parser.set_defaults(func=create_vm)
    create_subparsers.add_parser('vm', parents=[vmcreate_parser], description=vmcreate_desc, help=vmcreate_desc)

    vmdelete_desc = 'Delete Vm'
    vmdelete_parser = argparse.ArgumentParser(add_help=False)
    vmdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    vmdelete_parser.add_argument('--snapshots', action='store_true', help='Remove snapshots if needed')
    vmdelete_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmdelete_parser.set_defaults(func=delete_vm)
    delete_subparsers.add_parser('vm', parents=[vmdelete_parser], description=vmdelete_desc, help=vmdelete_desc)

    vmdiskadd_desc = 'Add Disk To Vm'
    vmdiskadd_parser = argparse.ArgumentParser(add_help=False)
    vmdiskadd_parser.add_argument('-s', '--size', type=int, help='Size of the disk to add, in GB', metavar='SIZE')
    vmdiskadd_parser.add_argument('-i', '--image', help='Name or Path of a Image, when adding',
                                  metavar='TEMPLATE')
    vmdiskadd_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskadd_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmdiskadd_parser.set_defaults(func=create_vmdisk)
    create_subparsers.add_parser('vm-disk', parents=[vmdiskadd_parser], description=vmdiskadd_desc, help=vmdiskadd_desc)

    vmdiskdelete_desc = 'Delete Vm Disk'
    vmdiskdelete_parser = argparse.ArgumentParser(add_help=False)
    vmdiskdelete_parser.add_argument('-n', '--diskname', help='Name or Path of the disk, when deleting',
                                     metavar='DISKNAME')
    vmdiskdelete_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskdelete_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmdiskdelete_parser.set_defaults(func=diskdelete_vm)
    delete_subparsers.add_parser('vm-disk', parents=[vmdiskdelete_parser], description=vmdiskdelete_desc,
                                 help=vmdiskdelete_desc)

    vmdisklist_desc = 'List Vms Disks'
    vmdisklist_parser = argparse.ArgumentParser(add_help=False)
    vmdisklist_parser.set_defaults(func=disklist_vm)
    list_subparsers.add_parser('vm-disk', parents=[vmdisklist_parser], description=vmdisklist_desc,
                               help=vmdisklist_desc)

    vmexport_desc = 'Export Vms'
    vmexport_parser = export_subparsers.add_parser('vm', description=vmexport_desc, help=vmexport_desc)
    vmexport_parser.add_argument('-t', '--image', help='Name for the generated image. Uses the vm name otherwise',
                                 metavar='IMAGE')
    vmexport_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmexport_parser.set_defaults(func=export_vm)

    vminfo_desc = 'Info Of Vms'
    vminfo_parser = argparse.ArgumentParser(add_help=False)
    vminfo_parser.add_argument('-f', '--fields', help='Display Corresponding list of fields,'
                               'separated by a comma', metavar='FIELDS')
    vminfo_parser.add_argument('-o', '--output', choices=['plain', 'yaml'], help='Format of the output')
    vminfo_parser.add_argument('-v', '--values', action='store_true', help='Only report values')
    vminfo_parser.add_argument('names', help='VMNAMES', nargs='*')
    vminfo_parser.set_defaults(func=info_vm)
    info_subparsers.add_parser('vm', parents=[vminfo_parser], description=vminfo_desc, help=vminfo_desc)

    vmlist_desc = 'List Vms'
    vmlist_parser = argparse.ArgumentParser(add_help=False)
    vmlist_parser.add_argument('--filters', choices=('up', 'down'))
    vmlist_parser.set_defaults(func=list_vm)
    list_subparsers.add_parser('vm', parents=[vmlist_parser], description=vmlist_desc, help=vmlist_desc)

    nicadd_desc = 'Add Nic To Vm'
    nicadd_parser = argparse.ArgumentParser(add_help=False)
    nicadd_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    nicadd_parser.add_argument('name', metavar='VMNAME')
    nicadd_parser.set_defaults(func=add_nic)
    create_subparsers.add_parser('vm-nic', parents=[nicadd_parser], description=nicadd_desc, help=nicadd_desc)

    nicdelete_desc = 'Delete Nic From vm'
    nicdelete_parser = argparse.ArgumentParser(add_help=False)
    nicdelete_parser.add_argument('-i', '--interface', help='Name of the interface, when deleting', metavar='INTERFACE')
    nicdelete_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    nicdelete_parser.add_argument('name', metavar='VMNAME')
    nicdelete_parser.set_defaults(func=delete_nic)
    delete_subparsers.add_parser('vm-nic', parents=[nicadd_parser], description=nicdelete_desc, help=nicdelete_desc)

    vmrestart_desc = 'Restart Vms'
    vmrestart_parser = restart_subparsers.add_parser('vm', description=vmrestart_desc, help=vmrestart_desc)
    vmrestart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmrestart_parser.set_defaults(func=restart_vm)

    vmscp_desc = 'Scp Into Vm'
    vmscp_parser = argparse.ArgumentParser(add_help=False)
    vmscp_parser.add_argument('-r', '--recursive', help='Recursive', action='store_true')
    vmscp_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                              default='/workdir', metavar='VOLUMEPATH')
    vmscp_parser.add_argument('source', nargs=1)
    vmscp_parser.add_argument('destination', nargs=1)
    vmscp_parser.set_defaults(func=scp_vm)
    scp_subparsers.add_parser('vm', parents=[vmscp_parser], description=vmscp_desc, help=vmscp_desc)

    vmsnapshotcreate_desc = 'Create Snapshot Of Vm'
    vmsnapshotcreate_parser = create_subparsers.add_parser('vm-snapshot', description=vmsnapshotcreate_desc,
                                                           help=vmsnapshotcreate_desc)
    vmsnapshotcreate_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotcreate_parser.add_argument('snapshot')
    vmsnapshotcreate_parser.set_defaults(func=snapshotcreate_vm)

    vmsnapshotdelete_desc = 'Delete Snapshot Of Vm'
    vmsnapshotdelete_parser = delete_subparsers.add_parser('vm-snapshot', description=vmsnapshotdelete_desc,
                                                           help=vmsnapshotdelete_desc)
    vmsnapshotdelete_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotdelete_parser.add_argument('snapshot')
    vmsnapshotdelete_parser.set_defaults(func=snapshotdelete_vm)

    vmsnapshotlist_desc = 'List Snapshots Of Vm'
    vmsnapshotlist_parser = list_subparsers.add_parser('vm-snapshot', description=vmsnapshotlist_desc,
                                                       help=vmsnapshotlist_desc)
    vmsnapshotlist_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotlist_parser.set_defaults(func=snapshotlist_vm)

    vmsnapshotrevert_desc = 'Revert Snapshot Of Vm'
    vmsnapshotrevert_parser = revert_subparsers.add_parser('vm-snapshot', description=vmsnapshotrevert_desc,
                                                           help=vmsnapshotrevert_desc)
    vmsnapshotrevert_parser.add_argument('-n', '--name', help='Use vm name for creation/revert/delete',
                                         required=True, metavar='VMNAME')
    vmsnapshotrevert_parser.add_argument('snapshot')
    vmsnapshotrevert_parser.set_defaults(func=snapshotrevert_vm)

    vmssh_desc = 'Ssh Into Vm'
    vmssh_parser = argparse.ArgumentParser(add_help=False)
    vmssh_parser.add_argument('-D', help='Dynamic Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-L', help='Local Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-R', help='Remote Forwarding', metavar='REMOTE')
    vmssh_parser.add_argument('-X', action='store_true', help='Enable X11 Forwarding')
    vmssh_parser.add_argument('-Y', action='store_true', help='Enable X11 Forwarding(Insecure)')
    vmssh_parser.add_argument('name', metavar='VMNAME', nargs='*')
    vmssh_parser.set_defaults(func=ssh_vm)
    ssh_subparsers.add_parser('vm', parents=[vmssh_parser], description=vmssh_desc, help=vmssh_desc)

    vmstart_desc = 'Start Vms'
    vmstart_parser = argparse.ArgumentParser(add_help=False)
    vmstart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstart_parser.set_defaults(func=start_vm)
    start_subparsers.add_parser('vm', parents=[vmstart_parser], description=vmstart_desc, help=vmstart_desc)

    vmstop_desc = 'Stop Vms'
    vmstop_parser = argparse.ArgumentParser(add_help=False)
    vmstop_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstop_parser.set_defaults(func=stop_vm)
    stop_subparsers.add_parser('vm', parents=[vmstop_parser], description=vmstop_desc, help=vmstop_desc)

    vmupdate_desc = 'Update Vm\'s Ip, Memory Or Numcpus'
    vmupdate_parser = update_subparsers.add_parser('vm', description=vmupdate_desc, help=vmupdate_desc)
    vmupdate_parser.add_argument('-1', '--ip1', help='Ip to set', metavar='IP1')
    vmupdate_parser.add_argument('--information', '--info', help='Information to set', metavar='INFORMATION')
    vmupdate_parser.add_argument('--network', '--net', help='Network to update', metavar='NETWORK')
    vmupdate_parser.add_argument('-f', '--flavor', help='Flavor to set', metavar='Flavor')
    vmupdate_parser.add_argument('-m', '--memory', help='Memory to set', metavar='MEMORY')
    vmupdate_parser.add_argument('-c', '--numcpus', type=int, help='Number of cpus to set', metavar='NUMCPUS')
    vmupdate_parser.add_argument('-p', '--plan', help='Plan Name to set', metavar='PLAN')
    vmupdate_parser.add_argument('-a', '--autostart', action='store_true', help='Set VM to autostart')
    vmupdate_parser.add_argument('-n', '--noautostart', action='store_true', help='Prevent VM from autostart')
    vmupdate_parser.add_argument('--dns', action='store_true', help='Update Dns entry for the vm')
    vmupdate_parser.add_argument('--host', action='store_true', help='Update Host entry for the vm')
    vmupdate_parser.add_argument('-d', '--domain', help='Domain', metavar='DOMAIN')
    vmupdate_parser.add_argument('-i', '--image', help='Image to set', metavar='IMAGE')
    vmupdate_parser.add_argument('--iso', help='Iso to set', metavar='ISO')
    vmupdate_parser.add_argument('--cloudinit', action='store_true', help='Remove Cloudinit Information from vm')
    vmupdate_parser.add_argument('names', help='VMNAMES', nargs='*')
    vmupdate_parser.set_defaults(func=update_vm)

    argcomplete.autocomplete(parser)
    if len(sys.argv) == 1 or (len(sys.argv) == 3 and sys.argv[1] == '-C'):
        parser.print_help()
        os._exit(0)
    args = parser.parse_args()
    if not hasattr(args, 'func'):
        for attr in dir(args):
            if attr.startswith('subcommand'):
                subcommand = attr.replace('subcommand_', '')
                subparser_print_help(parser, subcommand)
                os._exit(0)
        os._exit(0)
    elif args.func.__name__ == 'vmcreate' and args.client is not None and ',' in args.client:
        args.client = random.choice(args.client.split(','))
        common.pprint("Selecting %s for creation" % args.client)
    args.func(args)


if __name__ == '__main__':
    cli()
