#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# coding=utf-8

from distutils.spawn import find_executable
from kvirt.config import Kconfig
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt.version import __version__
from kvirt.defaults import TEMPLATES
from prettytable import PrettyTable
import argcomplete
import argparse
from kvirt import common
from kvirt import nameutils
import os
import random
import sys
import yaml


def subparser_print_help(parser, subcommand):
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)]
    for subparsers_action in subparsers_actions:
        for choice, subparser in subparsers_action.choices.items():
            if choice == subcommand:
                subparser.print_help()
                return


def vm_start(args):
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


def container_start(args):
    """Start containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    for name in names:
        common.pprint("Starting container %s..." % name)
        cont.start_container(name)


def vm_stop(args):
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


def container_stop(args):
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


def vm_restart(args):
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


def container_restart(args):
    """Restart containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    for name in names:
        common.pprint("Restarting container %s..." % name)
        cont.stop_container(name)
        cont.start_container(name)


def vm_console(args):
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


def container_console(args):
    """Container console"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    name = common.get_lastvm(config.client) if not args.name else args.name
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    cont.console_container(name)
    return


def vm_delete(args):
    """Delete vm"""
    template = args.template
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
        elif template:
            # k = config.k
            codes = []
            for name in names:
                # shortname = os.path.basename(url)
                # template = os.path.basename(template)
                result = k.delete_image(name)
                if result['result'] == 'success':
                    common.pprint("%s deleted" % name)
                    codes.append(0)
                else:
                    reason = result['reason']
                    common.pprint("Could not delete %s because %s" % (name, reason), color='red')
                    codes.append(1)
        else:
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


def container_delete(args):
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


def template_download(args):
    """Download Template"""
    pool = args.pool
    templates = args.templates
    cmd = args.cmd
    url = args.url
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(pool=pool, templates=templates, download=True, cmd=cmd, url=url)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def vm_info(args):
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


def host_enable(args):
    """Enable host"""
    host = args.host
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.enable_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def host_disable(args):
    """Disable host"""
    host = args.host
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.disable_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def host_sync(args):
    """Handle host"""
    hosts = args.hosts
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(sync=hosts)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def vm_list(args):
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
                source = vm.get('template', '')
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
            source = vm.get('template', '')
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


def container_list(args):
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


def container_profilelist(args):
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


def container_imagelist(args):
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


def host_list(args):
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


def lb_list(args):
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


def profile_list(args):
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
                                     "Pool", "Disks", "Template",
                                     "Nets", "Cloudinit", "Nested",
                                     "Reservedns", "Reservehost"])
        for profile in sorted(profiles):
            profilestable.add_row(profile)
    profilestable.align["Profile"] = "l"
    print(profilestable)
    return


def flavor_list(args):
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


def template_list(args):
    """List templates"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    templatestable = PrettyTable(["Template"])
    templatestable.align["Template"] = "l"
    for template in k.volumes():
        templatestable.add_row([template])
    print(templatestable)
    return


def iso_list(args):
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


def network_list(args):
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


def plan_list(args):
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


def pool_list(args):
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


def product_list(args):
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


def repo_list(args):
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


def vm_disklist(args):
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


def vm_create(args):
    """Create vms"""
    name = args.name
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
    if profile.endswith('.yml'):
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


def vm_clone(args):
    """Clone existing vm"""
    name = args.name
    base = args.base
    full = args.full
    start = args.start
    common.pprint("Cloning vm %s from vm %s..." % (name, base))
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    k.clone(base, name, full=full, start=start)


def vm_update(args):
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
    template = args.template
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
        elif template is not None:
            common.pprint("Updating template of vm %s to %s..." % (name, template))
            k.update_metadata(name, 'template', template)
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
            k.update_information(name, information)
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


def vm_diskadd(args):
    """Add disk to vm"""
    name = args.name
    size = args.size
    template = args.template
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
    k.add_disk(name=name, size=size, pool=pool, template=template)


def vm_diskdelete(args):
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


def dns_create(args):
    """Create dns entries"""
    name = args.name
    net = args.net
    domain = net
    ip = args.ip
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Creating Dns entry for %s..." % name)
    k.reserve_dns(name=name, nets=[net], domain=domain, ip=ip)


def dns_delete(args):
    """Delete dns entries"""
    name = args.name
    net = args.net
    domain = net
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting Dns entry for %s..." % name)
    k.delete_dns(name, domain)


def vm_export(args):
    """Export a vm"""
    template = args.template
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    codes = []
    for name in names:
        result = k.export(name=name, template=template)
        if result['result'] == 'success':
            common.pprint("Exporting vm %s" % name)
            codes.append(0)
        else:
            reason = result['reason']
            common.pprint("Could not delete vm %s because %s" % (name, reason), color='red')
            codes.append(1)
    os._exit(1 if 1 in codes else 0)


def lb_create(args):
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


def lb_delete(args):
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


def nic_add(args):
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


def nic_delete(args):
    """Delete nic of vm"""
    name = args.name
    interface = args.interface
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting nic from %s..." % name)
    k.delete_nic(name, interface)
    return


def pool_create(args):
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


def pool_delete(args):
    """Delete pool"""
    pool = args.pool
    full = args.full
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting pool %s..." % pool)
    k.delete_pool(name=pool, full=full)
    return


def plan_create(args):
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


def plan_update(args):
    """Update plan"""
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
    if plan is None:
        plan = nameutils.get_random_name()
        common.pprint("Using %s as name of the plan" % plan)
    config.plan(plan, url=url, path=path, container=container, inputfile=inputfile, overrides=overrides, update=True)
    return 0


def plan_delete(args):
    """Delete plan"""
    plan = args.plan
    yes = args.yes
    if not yes:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, delete=True)
    return 0


def plan_start(args):
    """Start plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, start=True)
    return 0


def plan_stop(args):
    """Stop plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, stop=True)
    return 0


def plan_autostart(args):
    """Autostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, autostart=True)
    return 0


def plan_noautostart(args):
    """Noautostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, autostart=False)
    return 0


def plan_restart(args):
    """Restart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, delete=True)
    return 0


def plan_info(args):
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


def plan_render(args):
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


def plan_snapshot(args):
    """Snapshot plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, snapshot=True)
    return 0


def plan_revert(args):
    """Revert snapshot of plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, revert=True)
    return 0


def repo_create(args):
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


def repo_delete(args):
    """Delete repo"""
    repo = args.repo
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if repo is None:
        common.pprint("Missing repo. Leaving...", color='red')
        os._exit(1)
    common.pprint("Deleting repo %s..." % repo)
    baseconfig.delete_repo(repo)
    return


def repo_update(args):
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


def product_create(args):
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


def vm_ssh(args):
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


def vm_scp(args):
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


def network_create(args):
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
    common.handle_response(result, name, element='Network ')


def network_delete(args):
    """Delete Network"""
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if name is None:
        common.pprint("Missing Network", color='red')
        os._exit(1)
    result = k.delete_network(name=name)
    common.handle_response(result, name, element='Network ', action='deleted')


def host_bootstrap(args):
    """Generate basic config file"""
    name = args.name
    host = args.host
    port = args.port
    user = args.user
    protocol = args.protocol
    url = args.url
    pool = args.pool
    poolpath = args.poolpath
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    baseconfig.bootstrap(name, host, port, user, protocol, url, pool, poolpath)


def container_create(args):
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
        image = next((e for e in [profile.get('image'), profile.get('template')] if e is not None), None)
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


def vm_snapshotcreate(args):
    """Create snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Creating snapshot of %s named %s..." % (name, snapshot))
    result = k.snapshot(snapshot, name)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def vm_snapshotdelete(args):
    """Delete snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting snapshot of %s named %s..." % (name, snapshot))
    result = k.snapshot(snapshot, name, delete=True)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def vm_snapshotrevert(args):
    """Revert snapshot of vm"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Reverting snapshot of %s named %s..." % (name, snapshot))
    result = k.snapshot(snapshot, name, revert=True)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def vm_snapshotlist(args):
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


def host_report(args):
    """Report info about host"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    k.report()


def host_switch(args):
    """Handle host"""
    host = args.host
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.switch_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def cli():
    """

    """
    parser = argparse.ArgumentParser(description='Libvirt/Ovirt/Vsphere/Gcp/Aws/Openstack/Kubevirt Wrapper On Steroids')
    parser.add_argument('-C', '--client')
    parser.add_argument('--containerclient', help='Containerclient to use')
    parser.add_argument('--dnsclient', help='Dnsclient to use')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-n', '--namespace', help='Namespace to use. specific to kubevirt')
    parser.add_argument('-r', '--region', help='Region to use. specific to aws/gcp')
    parser.add_argument('-z', '--zone', help='Zone to use. specific to gcp')
    parser.add_argument('-v', '--version', action='version', version="%s" % __version__)

    subparsers = parser.add_subparsers(metavar='')

    container_info = 'Container'
    container_parser = subparsers.add_parser('container', description=container_info, help=container_info)
    container_subparsers = container_parser.add_subparsers(metavar='', dest='subcommand_container')

    containerconsole_info = 'Container Console'
    containerconsole_parser = container_subparsers.add_parser('console', description=containerconsole_info,
                                                              help=containerconsole_info)
    containerconsole_parser.add_argument('name', metavar='CONTAINERNAME', nargs='?')
    containerconsole_parser.set_defaults(func=container_console)

    containercreate_info = 'Create Container'
    containercreate_parser = container_subparsers.add_parser('create', description=containercreate_info,
                                                             help=containercreate_info)
    containercreate_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    containercreate_parser.add_argument('-P', '--param', action='append',
                                        help='specify parameter or keyword for rendering (can specify multiple)',
                                        metavar='PARAM')
    containercreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    containercreate_parser.add_argument('name', metavar='NAME', nargs='?')
    containercreate_parser.set_defaults(func=container_create)

    containerdelete_info = 'Delete Container'
    containerdelete_parser = container_subparsers.add_parser('delete', description=containerdelete_info,
                                                             help=containerdelete_info)
    containerdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    containerdelete_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    containerdelete_parser.set_defaults(func=container_delete)

    containerimagelist_info = 'List Container Images'
    containerimagelist_parser = container_subparsers.add_parser('image-list', description=containerimagelist_info,
                                                                help=containerimagelist_info)
    containerimagelist_parser.set_defaults(func=container_imagelist)

    containerlist_info = 'List Containers'
    containerlist_parser = container_subparsers.add_parser('list', description=containerlist_info,
                                                           help=containerlist_info)
    containerlist_parser.add_argument('--filters', choices=('up', 'down'))
    containerlist_parser.set_defaults(func=container_list)

    containerprofilelist_info = 'List Container Profiles'
    containerprofilelist_parser = container_subparsers.add_parser('profile-list', description=containerprofilelist_info,
                                                                  help=containerprofilelist_info)
    containerprofilelist_parser.add_argument('--short', action='store_true')
    containerprofilelist_parser.set_defaults(func=container_profilelist)

    containerrestart_info = 'Restart Containers'
    containerrestart_parser = container_subparsers.add_parser('restart', description=containerrestart_info,
                                                              help=containerrestart_info)
    containerrestart_parser.add_argument('names', metavar='CONTAINERNAMES', nargs='*')
    containerrestart_parser.set_defaults(func=container_restart)

    containerstart_info = 'Start Containers'
    containerstart_parser = container_subparsers.add_parser('start', description=containerstart_info,
                                                            help=containerstart_info)
    containerstart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    containerstart_parser.set_defaults(func=container_start)

    containerstop_info = 'Stop Containers'
    containerstop_parser = container_subparsers.add_parser('stop', description=containerstop_info,
                                                           help=containerstop_info)
    containerstop_parser.add_argument('names', metavar='CONTAINERNAMES', nargs='*')
    containerstop_parser.set_defaults(func=container_stop)

    dns_info = 'Dns'
    dns_parser = subparsers.add_parser('dns', description=dns_info, help=dns_info)
    dns_subparsers = dns_parser.add_subparsers(metavar='', dest='subcommand_dns')

    dnscreate_info = 'Create Dns Entries'
    dnscreate_parser = dns_subparsers.add_parser('create', description=dnscreate_info, help=dnscreate_info)
    dnscreate_parser.add_argument('-n', '--net', help='Domain where to create entry', metavar='NET')
    dnscreate_parser.add_argument('-i', '--ip', help='Ip', metavar='IP')
    dnscreate_parser.add_argument('name', metavar='NAME', nargs='?')
    dnscreate_parser.set_defaults(func=dns_create)

    dnsdelete_info = 'Delete Dns entries'
    dnsdelete_parser = dns_subparsers.add_parser('delete', description=dnsdelete_info, help=dnsdelete_info)
    dnsdelete_parser.add_argument('-n', '--net', help='Domain where to create entry', metavar='NET')
    dnsdelete_parser.add_argument('name', metavar='NAME', nargs='?')
    dnsdelete_parser.set_defaults(func=dns_delete)

    host_info = 'Host'
    host_parser = subparsers.add_parser('host', description=host_info, help=host_info)
    host_subparsers = host_parser.add_subparsers(metavar='', dest='subcommand_host')

    hostbootstrap_info = 'Generate Config file'
    hostbootstrap_parser = host_subparsers.add_parser('bootstrap', help=hostbootstrap_info,
                                                      description=hostbootstrap_info)
    hostbootstrap_parser.add_argument('-n', '--name', help='Name to use', metavar='CLIENT')
    hostbootstrap_parser.add_argument('-H', '--host', help='Host to use', metavar='HOST')
    hostbootstrap_parser.add_argument('-p', '--port', help='Port to use', metavar='PORT')
    hostbootstrap_parser.add_argument('-u', '--user', help='User to use', default='root', metavar='USER')
    hostbootstrap_parser.add_argument('-P', '--protocol', help='Protocol to use', default='ssh', metavar='PROTOCOL')
    hostbootstrap_parser.add_argument('-U', '--url', help='URL to use', metavar='URL')
    hostbootstrap_parser.add_argument('--pool', help='Pool to use', metavar='POOL')
    hostbootstrap_parser.add_argument('--poolpath', help='Pool Path to use', metavar='POOLPATH')
    hostbootstrap_parser.set_defaults(func=host_bootstrap)

    hostdisable_info = 'Disable Host'
    hostdisable_parser = host_subparsers.add_parser('disable', description=hostdisable_info, help=hostdisable_info)
    hostdisable_parser.add_argument('host', metavar='HOST', nargs='?')
    hostdisable_parser.set_defaults(func=host_disable)

    hostenable_info = 'Enable Host'
    hostenable_parser = host_subparsers.add_parser('enable', description=hostenable_info, help=hostenable_info)
    hostenable_parser.add_argument('host', metavar='HOST', nargs='?')
    hostenable_parser.set_defaults(func=host_enable)

    hostlist_info = 'List Hosts'
    hostlist_parser = host_subparsers.add_parser('list', description=hostlist_info, help=hostlist_info)
    hostlist_parser.set_defaults(func=host_list)

    hostreport_info = 'Report Info About Host'
    hostreport_parser = host_subparsers.add_parser('report', description=hostreport_info, help=hostreport_info)
    hostreport_parser.set_defaults(func=host_report)

    hostswitch_info = 'Switch Host'
    hostswitch_parser = host_subparsers.add_parser('switch', description=hostswitch_info, help=hostswitch_info)
    hostswitch_parser.add_argument('host', help='HOST')
    hostswitch_parser.set_defaults(func=host_switch)

    hostsync_info = 'Sync Host'
    hostsync_parser = host_subparsers.add_parser('sync', description=hostsync_info, help=hostsync_info)
    hostsync_parser.add_argument('hosts', help='HOSTS', nargs='*')
    hostsync_parser.set_defaults(func=host_sync)

    lb_info = 'Lb'
    lb_parser = subparsers.add_parser('lb', description=lb_info, help=lb_info)
    lb_subparsers = lb_parser.add_subparsers(metavar='', dest='subcommand_lb')

    lbcreate_info = 'Create Loadbalancer'
    lbcreate_parser = lb_subparsers.add_parser('create', description=lbcreate_info, help=lbcreate_info)
    lbcreate_parser.add_argument('--checkpath', default='/index.html', help="Path to check. Defaults to /index.html")
    lbcreate_parser.add_argument('--checkport', default=80, help="Port to check. Defaults to 80")
    lbcreate_parser.add_argument('--domain', help='Domain to create a dns entry associated to the load balancer')
    lbcreate_parser.add_argument('-i', '--internal', action='store_true')
    lbcreate_parser.add_argument('-p', '--ports', default='443', help='Load Balancer Ports. Defaults to 443')
    lbcreate_parser.add_argument('-v', '--vms', help='Vms to add to the pool')
    lbcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    lbcreate_parser.set_defaults(func=lb_create)

    lbdelete_info = 'Delete Loadbalancer'
    lbdelete_parser = lb_subparsers.add_parser('delete', description=lbdelete_info, help=lbdelete_info)
    lbdelete_parser.add_argument('--checkpath', default='/index.html', help="Path to check. Defaults to /index.html")
    lbdelete_parser.add_argument('--checkport', default=80, help="Port to check. Defaults to 80")
    lbdelete_parser.add_argument('-d', '--delete', action='store_true')
    lbdelete_parser.add_argument('--domain', help='Domain to create a dns entry associated to the load balancer')
    lbdelete_parser.add_argument('-i', '--internal', action='store_true')
    lbdelete_parser.add_argument('-p', '--ports', default='443', help='Load Balancer Ports. Defaults to 443')
    lbdelete_parser.add_argument('-v', '--vms', help='Vms to add to the pool')
    lbdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    lbdelete_parser.add_argument('name', metavar='NAME', nargs='?')
    lbdelete_parser.set_defaults(func=lb_delete)

    lblist_info = 'List Loadbalancers'
    lblist_parser = lb_subparsers.add_parser('list', description=lblist_info, help=lblist_info)
    lblist_parser.add_argument('--short', action='store_true')
    lblist_parser.set_defaults(func=lb_list)

    profile_info = 'Profile'
    profile_parser = subparsers.add_parser('profile', description=profile_info, help=profile_info)
    profile_subparsers = profile_parser.add_subparsers(metavar='', dest='profile_container')

    profilelist_info = 'List Profiles'
    profilelist_parser = profile_subparsers.add_parser('list', description=profilelist_info, help=profilelist_info)
    profilelist_parser.add_argument('--short', action='store_true')
    profilelist_parser.set_defaults(func=profile_list)

    flavor_info = 'Flavor'
    flavor_parser = subparsers.add_parser('flavor', description=flavor_info, help=flavor_info)
    flavor_subparsers = flavor_parser.add_subparsers(metavar='', dest='subcommand_flavor')

    flavorlist_info = 'List Flavors'
    flavorlist_parser = flavor_subparsers.add_parser('list', description=flavorlist_info, help=flavorlist_info)
    flavorlist_parser.add_argument('--short', action='store_true')
    flavorlist_parser.set_defaults(func=flavor_list)

    iso_info = 'Iso'
    iso_parser = subparsers.add_parser('iso', description=iso_info, help=iso_info)
    iso_subparsers = iso_parser.add_subparsers(metavar='', dest='subcommand_iso')

    isolist_info = 'List Isos'
    isolist_parser = iso_subparsers.add_parser('list', description=isolist_info, help=isolist_info)
    isolist_parser.set_defaults(func=iso_list)

    network_info = 'Network'
    network_parser = subparsers.add_parser('network', description=network_info, help=network_info)
    network_subparsers = network_parser.add_subparsers(metavar='', dest='subcommand_network')

    networklist_info = 'List Networks'
    networklist_parser = network_subparsers.add_parser('list', description=networklist_info, help=networklist_info)
    networklist_parser.add_argument('--short', action='store_true')
    networklist_parser.add_argument('-s', '--subnets', action='store_true')
    networklist_parser.set_defaults(func=network_list)

    networkcreate_info = 'Create Network'
    networkcreate_parser = network_subparsers.add_parser('create', description=networkcreate_info,
                                                         help=networkcreate_info)
    networkcreate_parser.add_argument('-i', '--isolated', action='store_true', help='Isolated Network')
    networkcreate_parser.add_argument('-c', '--cidr', help='Cidr of the net', metavar='CIDR')
    networkcreate_parser.add_argument('--nodhcp', action='store_true', help='Disable dhcp on the net')
    networkcreate_parser.add_argument('--domain', help='DNS domain. Defaults to network name')
    networkcreate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (can specify multiple)',
                                      metavar='PARAM')
    networkcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    networkcreate_parser.add_argument('name', metavar='NETWORK')
    networkcreate_parser.set_defaults(func=network_create)

    networkdelete_info = 'Delete Network'
    networkdelete_parser = network_subparsers.add_parser('delete', description=networkdelete_info,
                                                         help=networkdelete_info)
    networkdelete_parser.add_argument('name', metavar='NETWORK')
    networkdelete_parser.set_defaults(func=network_delete)

    plan_info = 'Plan'
    plan_parser = subparsers.add_parser('plan', description=plan_info, help=plan_info)
    plan_subparsers = plan_parser.add_subparsers(metavar='', dest='subcommand_plan')

    planautostart_info = 'Autostart Plan'
    planautostart_parser = plan_subparsers.add_parser('autostart', description=planautostart_info,
                                                      help=planautostart_info)
    planautostart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planautostart_parser.set_defaults(func=plan_autostart)

    plancreate_info = 'Create Plan'
    plancreate_parser = plan_subparsers.add_parser('create', description=plancreate_info, help=plancreate_info)
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
    plancreate_parser.set_defaults(func=plan_create)

    plandelete_info = 'Delete Plan'
    plandelete_parser = plan_subparsers.add_parser('delete', description=plandelete_info, help=plandelete_info)
    plandelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    plandelete_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plandelete_parser.set_defaults(func=plan_delete)

    planinfo_info = 'Info Plan'
    planinfo_parser = plan_subparsers.add_parser('info', description=plandelete_info, help=planinfo_info)
    planinfo_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planinfo_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan', metavar='PATH')
    planinfo_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    planinfo_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                                 default='/workdir', metavar='VOLUMEPATH')
    planinfo_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planinfo_parser.set_defaults(func=plan_info)

    planlist_info = 'List Plans'
    planlist_parser = plan_subparsers.add_parser('list', description=planlist_info, help=planlist_info)
    planlist_parser.set_defaults(func=plan_list)

    plannoautostart_info = 'Noautostart Plan'
    plannoautostart_parser = plan_subparsers.add_parser('noautostart', description=plannoautostart_info,
                                                        help=planautostart_info)
    plannoautostart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plannoautostart_parser.set_defaults(func=plan_noautostart)

    planrender_info = 'Render Plans/Files'
    planrender_parser = plan_subparsers.add_parser('render', description=planrender_info,
                                                   help=planrender_info)
    planrender_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planrender_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    planrender_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    planrender_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                                   default='/workdir', metavar='VOLUMEPATH')
    planrender_parser.set_defaults(func=plan_render)

    planrestart_info = 'Restart Plan'
    planrestart_parser = plan_subparsers.add_parser('restart', description=planrestart_info, help=planrestart_info)
    planrestart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planrestart_parser.set_defaults(func=plan_restart)

    planrevert_info = 'Revert Snapshot Of Plan'
    planrevert_parser = plan_subparsers.add_parser('revert', description=planrevert_info, help=planrevert_info)
    planrevert_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planrevert_parser.set_defaults(func=plan_revert)

    plansnapshot_info = 'Snapshot Plan'
    plansnapshot_parser = plan_subparsers.add_parser('snapshot', description=plansnapshot_info, help=plansnapshot_info)
    plansnapshot_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plansnapshot_parser.set_defaults(func=plan_snapshot)

    planstart_info = 'Start Plan'
    planstart_parser = plan_subparsers.add_parser('start', description=planstart_info, help=planstart_info)
    planstart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planstart_parser.set_defaults(func=plan_start)

    planstop_info = 'Stop Plan'
    planstop_parser = plan_subparsers.add_parser('stop', description=planstop_info, help=planstop_info)
    planstop_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planstop_parser.set_defaults(func=plan_stop)

    planupdate_info = 'Update Plan'
    planupdate_parser = plan_subparsers.add_parser('update', description=planupdate_info, help=planupdate_info)
    planupdate_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    planupdate_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan',
                                   metavar='PATH')
    planupdate_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    planupdate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planupdate_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                                   default='/workdir', metavar='VOLUMEPATH')
    planupdate_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    planupdate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    planupdate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planupdate_parser.set_defaults(func=plan_update)

    pool_info = 'Pool'
    pool_parser = subparsers.add_parser('pool', description=pool_info, help=pool_info)
    pool_subparsers = pool_parser.add_subparsers(metavar='', dest='subcommand_pool')

    poolcreate_info = 'Create Pool'
    poolcreate_parser = pool_subparsers.add_parser('create', description=poolcreate_info, help=poolcreate_info)
    poolcreate_parser.add_argument('-f', '--full', action='store_true')
    poolcreate_parser.add_argument('-t', '--pooltype', help='Type of the pool', choices=('dir', 'lvm', 'zfs'),
                                   default='dir')
    poolcreate_parser.add_argument('-p', '--path', help='Path of the pool', metavar='PATH')
    poolcreate_parser.add_argument('--thinpool', help='Existing thin pool to use with lvm', metavar='THINPOOL')
    poolcreate_parser.add_argument('pool')
    poolcreate_parser.set_defaults(func=pool_create)

    pooldelete_info = 'Delete Pool'
    pooldelete_parser = pool_subparsers.add_parser('delete', description=pooldelete_info, help=pooldelete_info)
    pooldelete_parser.add_argument('-d', '--delete', action='store_true')
    pooldelete_parser.add_argument('-f', '--full', action='store_true')
    pooldelete_parser.add_argument('-p', '--path', help='Path of the pool', metavar='PATH')
    pooldelete_parser.add_argument('--thinpool', help='Existing thin pool to use with lvm', metavar='THINPOOL')
    pooldelete_parser.add_argument('pool')
    pooldelete_parser.set_defaults(func=pool_delete)

    poollist_info = 'List Pools'
    poollist_parser = pool_subparsers.add_parser('list', description=poollist_info, help=poollist_info)
    poollist_parser.add_argument('--short', action='store_true')
    poollist_parser.set_defaults(func=pool_list)

    product_info = 'Product'
    product_parser = subparsers.add_parser('product', description=product_info, help=product_info)
    product_subparsers = product_parser.add_subparsers(metavar='', dest='subcommand_product')

    product_info = 'Create Product'
    product_parser = product_subparsers.add_parser('create', description=product_info, help=product_info)
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
    product_parser.set_defaults(func=product_create)

    productlist_info = 'List Products'
    productlist_parser = product_subparsers.add_parser('list', description=productlist_info, help=productlist_info)
    productlist_parser.add_argument('-g', '--group', help='Only Display products of the indicated group',
                                    metavar='GROUP')
    productlist_parser.add_argument('-r', '--repo', help='Only Display products of the indicated repository',
                                    metavar='REPO')
    productlist_parser.set_defaults(func=product_list)

    repo_info = 'Repo'
    repo_parser = subparsers.add_parser('repo', description=repo_info, help=repo_info)
    repo_subparsers = repo_parser.add_subparsers(metavar='', dest='subcommand_repo')

    repocreate_info = 'Create Repo'
    repocreate_parser = repo_subparsers.add_parser('create', description=repocreate_info, help=repocreate_info)
    repocreate_parser.add_argument('-u', '--url', help='URL of the repo', metavar='URL')
    repocreate_parser.add_argument('repo')
    repocreate_parser.set_defaults(func=repo_create)

    repodelete_info = 'Delete Repo'
    repodelete_parser = repo_subparsers.add_parser('delete', description=repodelete_info, help=repodelete_info)
    repodelete_parser.add_argument('repo')
    repodelete_parser.set_defaults(func=repo_delete)

    repolist_info = 'List Repos'
    repolist_parser = repo_subparsers.add_parser('list', description=repolist_info, help=repolist_info)
    repolist_parser.set_defaults(func=repo_list)

    repoupdate_info = 'Update Repo'
    repoupdate_parser = repo_subparsers.add_parser('update', description=repoupdate_info, help=repoupdate_info)
    repoupdate_parser.add_argument('repo')
    repoupdate_parser.set_defaults(func=repo_update)

    template_info = 'Template'
    template_parser = subparsers.add_parser('template', description=template_info, help=template_info)
    template_subparsers = template_parser.add_subparsers(metavar='', dest='subcommand_template')

    templatedownload_info = 'Download Template'
    templatedownload_help = "Template to download. Choose between \n%s" % '\n'.join(TEMPLATES.keys())
    templatedownload_parser = template_subparsers.add_parser('download', description=templatedownload_info,
                                                             help=templatedownload_info)
    templatedownload_parser.add_argument('-c', '--cmd', help='Extra command to launch after downloading', metavar='CMD')
    templatedownload_parser.add_argument('-p', '--pool', help='Pool to use. Defaults to default', metavar='POOL')
    templatedownload_parser.add_argument('-u', '--url', help='Url to use', metavar='URL')
    templatedownload_parser.add_argument('templates', choices=sorted(TEMPLATES.keys()), default='',
                                         help=templatedownload_help, nargs='*', metavar='')
    templatedownload_parser.set_defaults(func=template_download)

    templatelist_info = 'List Templates'
    templatelist_parser = template_subparsers.add_parser('list', description=templatelist_info, help=templatelist_info)
    templatelist_parser.set_defaults(func=template_list)

    vm_info = 'Vm'
    vm_parser = subparsers.add_parser('vm', description=vm_info, help=vm_info)
    vm_subparsers = vm_parser.add_subparsers(metavar='', dest='subcommand_vm')

    vmclone_info = 'Clone Vm'
    vmclone_parser = vm_subparsers.add_parser('clone', description=vmclone_info, help=vmclone_info)
    vmclone_parser.add_argument('-b', '--base', help='Base VM', metavar='BASE')
    vmclone_parser.add_argument('-f', '--full', action='store_true', help='Full Clone')
    vmclone_parser.add_argument('-s', '--start', action='store_true', help='Start cloned VM')
    vmclone_parser.add_argument('name', metavar='VMNAME')
    vmclone_parser.set_defaults(func=vm_clone)

    vmconsole_info = 'Vm Console (vnc/spice/serial)'
    vmconsole_parser = vm_subparsers.add_parser('console', description=vmconsole_info, help=vmconsole_info)
    vmconsole_parser.add_argument('-s', '--serial', action='store_true')
    vmconsole_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmconsole_parser.set_defaults(func=vm_console)

    vmcreate_info = 'Create Vm'
    vmcreate_parser = vm_subparsers.add_parser('create', description=vmcreate_info, help=vmcreate_info)
    vmcreate_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE', required=True)
    vmcreate_parser.add_argument('--profilefile', help='File to load profiles from', metavar='PROFILEFILE')
    vmcreate_parser.add_argument('-P', '--param', action='append',
                                 help='specify parameter or keyword for rendering (can specify multiple)',
                                 metavar='PARAM')
    vmcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    vmcreate_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmcreate_parser.set_defaults(func=vm_create)

    vmdelete_info = 'Delete Vm'
    vmdelete_parser = vm_subparsers.add_parser('delete', description=vmdelete_info, help=vmdelete_info)
    vmdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    vmdelete_parser.add_argument('-t', '--template', action='store_true', help='delete template')
    vmdelete_parser.add_argument('--snapshots', action='store_true', help='Remove snapshots if needed')
    vmdelete_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmdelete_parser.set_defaults(func=vm_delete)

    vmdiskadd_info = 'Add Disk To Vm'
    vmdiskadd_parser = vm_subparsers.add_parser('disk-add', description=vmdiskadd_info, help=vmdiskadd_info)
    vmdiskadd_parser.add_argument('-s', '--size', type=int, help='Size of the disk to add, in GB', metavar='SIZE')
    vmdiskadd_parser.add_argument('-t', '--template', help='Name or Path of a Template, when adding',
                                  metavar='TEMPLATE')
    vmdiskadd_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskadd_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmdiskadd_parser.set_defaults(func=vm_diskadd)

    vmdiskdelete_info = 'Delete Vm Disk'
    vmdiskdelete_parser = vm_subparsers.add_parser('disk-delete', description=vmdiskdelete_info, help=vmdiskdelete_info)
    vmdiskdelete_parser.add_argument('-n', '--diskname', help='Name or Path of the disk, when deleting',
                                     metavar='DISKNAME')
    vmdiskdelete_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskdelete_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmdiskdelete_parser.set_defaults(func=vm_diskdelete)

    vmdisklist_info = 'List Vms Disks'
    vmdisklist_parser = vm_subparsers.add_parser('disk-list', description=vmdisklist_info, help=vmdisklist_info)
    vmdisklist_parser.set_defaults(func=vm_disklist)

    vmexport_info = 'Export Vms'
    vmexport_parser = vm_subparsers.add_parser('export', description=vmexport_info, help=vmexport_info)
    vmexport_parser.add_argument('-t', '--template', help='Name for the generated template. Uses the vm name otherwise',
                                 metavar='TEMPLATE')
    vmexport_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmexport_parser.set_defaults(func=vm_export)

    vminfo_info = 'Info Of Vms'
    vminfo_parser = vm_subparsers.add_parser('info', description=vminfo_info, help=vminfo_info)
    vminfo_parser.add_argument('-f', '--fields', help='Display Corresponding list of fields,'
                               'separated by a comma', metavar='FIELDS')
    vminfo_parser.add_argument('-o', '--output', choices=['plain', 'yaml'], help='Format of the output')
    vminfo_parser.add_argument('-v', '--values', action='store_true', help='Only report values')
    vminfo_parser.add_argument('names', help='VMNAMES', nargs='*')
    vminfo_parser.set_defaults(func=vm_info)

    vmlist_info = 'List Vms'
    vmlist_parser = vm_subparsers.add_parser('list', description=vmlist_info, help=vmlist_info)
    vmlist_parser.add_argument('--filters', choices=('up', 'down'))
    vmlist_parser.set_defaults(func=vm_list)

    nicadd_info = 'Add Nic To Vm'
    nicadd_parser = vm_subparsers.add_parser('nic-add', description=nicadd_info, help=nicadd_info)
    nicadd_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    nicadd_parser.add_argument('name', metavar='VMNAME')
    nicadd_parser.set_defaults(func=nic_add)

    nicdelete_info = 'Delete Nic From vm'
    nicdelete_parser = vm_subparsers.add_parser('nic-delete', description=nicdelete_info, help=nicdelete_info)
    nicdelete_parser.add_argument('-i', '--interface', help='Name of the interface, when deleting', metavar='INTERFACE')
    nicdelete_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    nicdelete_parser.add_argument('name', metavar='VMNAME')
    nicdelete_parser.set_defaults(func=nic_delete)

    vmrestart_info = 'Restart Vms'
    vmrestart_parser = vm_subparsers.add_parser('restart', description=vmrestart_info, help=vmrestart_info)
    vmrestart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmrestart_parser.set_defaults(func=vm_restart)

    vmscp_info = 'Scp Into Vm'
    vmscp_parser = vm_subparsers.add_parser('scp', description=vmscp_info, help=vmscp_info)
    vmscp_parser.add_argument('-r', '--recursive', help='Recursive', action='store_true')
    vmscp_parser.add_argument('-v', '--volumepath', help='Volume Path (only used with kcli container)',
                              default='/workdir', metavar='VOLUMEPATH')
    vmscp_parser.add_argument('source', nargs=1)
    vmscp_parser.add_argument('destination', nargs=1)
    vmscp_parser.set_defaults(func=vm_scp)

    vmsnapshotcreate_info = 'Create Snapshot Of Vm'
    vmsnapshotcreate_parser = vm_subparsers.add_parser('snapshot-create', description=vmsnapshotcreate_info,
                                                       help=vmsnapshotcreate_info)
    vmsnapshotcreate_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotcreate_parser.add_argument('snapshot')
    vmsnapshotcreate_parser.set_defaults(func=vm_snapshotcreate)

    vmsnapshotdelete_info = 'Delete Snapshot Of Vm'
    vmsnapshotdelete_parser = vm_subparsers.add_parser('snapshot-delete', description=vmsnapshotdelete_info,
                                                       help=vmsnapshotdelete_info)
    vmsnapshotdelete_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotdelete_parser.add_argument('snapshot')
    vmsnapshotdelete_parser.set_defaults(func=vm_snapshotdelete)

    vmsnapshotlist_info = 'List Snapshots Of Vm'
    vmsnapshotlist_parser = vm_subparsers.add_parser('snapshot-list', description=vmsnapshotlist_info,
                                                     help=vmsnapshotlist_info)
    vmsnapshotlist_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotlist_parser.set_defaults(func=vm_snapshotlist)

    vmsnapshotrevert_info = 'Revert Snapshot Of Vm'
    vmsnapshotrevert_parser = vm_subparsers.add_parser('snapshot-revert', description=vmsnapshotrevert_info,
                                                       help=vmsnapshotrevert_info)
    vmsnapshotrevert_parser.add_argument('-n', '--name', help='Use vm name for creation/revert/delete',
                                         required=True, metavar='VMNAME')
    vmsnapshotrevert_parser.add_argument('snapshot')
    vmsnapshotrevert_parser.set_defaults(func=vm_snapshotrevert)

    vmssh_info = 'Ssh Into Vm'
    vmssh_parser = vm_subparsers.add_parser('ssh', description=vmssh_info, help=vmssh_info)
    vmssh_parser.add_argument('-D', help='Dynamic Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-L', help='Local Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-R', help='Remote Forwarding', metavar='REMOTE')
    vmssh_parser.add_argument('-X', action='store_true', help='Enable X11 Forwarding')
    vmssh_parser.add_argument('-Y', action='store_true', help='Enable X11 Forwarding(Insecure)')
    vmssh_parser.add_argument('name', metavar='VMNAME', nargs='*')
    vmssh_parser.set_defaults(func=vm_ssh)

    vmstart_info = 'Start Vms'
    vmstart_parser = vm_subparsers.add_parser('start', description=vmstart_info, help=vmstart_info)
    vmstart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstart_parser.set_defaults(func=vm_start)

    vmstop_info = 'Stop Vms'
    vmstop_parser = vm_subparsers.add_parser('stop', description=vmstop_info, help=vmstop_info)
    vmstop_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstop_parser.set_defaults(func=vm_stop)

    vmupdate_info = 'Update Vm\'s Ip, Memory Or Numcpus'
    vmupdate_parser = vm_subparsers.add_parser('update', description=vmupdate_info, help=vmupdate_info)
    vmupdate_parser.add_argument('-1', '--ip1', help='Ip to set', metavar='IP1')
    vmupdate_parser.add_argument('-i', '--information', '--info', help='Information to set', metavar='INFORMATION')
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
    vmupdate_parser.add_argument('-t', '--template', help='Template to set', metavar='TEMPLATE')
    vmupdate_parser.add_argument('--iso', help='Iso to set', metavar='ISO')
    vmupdate_parser.add_argument('--cloudinit', action='store_true', help='Remove Cloudinit Information from vm')
    vmupdate_parser.add_argument('names', help='VMNAMES', nargs='*')
    vmupdate_parser.set_defaults(func=vm_update)

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
