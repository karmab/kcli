#!/usr/bin/env python

from kvirt.config import Kconfig
from kvirt.baseconfig import Kbaseconfig
from kvirt.config import __version__
from kvirt.defaults import TEMPLATES
from prettytable import PrettyTable
import argparse
from kvirt import common
from kvirt import nameutils
from kvirt import dockerutils
import json
import os
import random
import sys
import urllib2
import yaml


def start(args):
    """Start vm/container"""
    names = args.names
    container = args.container
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if not names:
        if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
            names = [open(lastvm).readlines()[0].strip()]
            common.pprint("Using %s as vm" % names[0], color='green')
        else:
            common.pprint("Missing Vm's name", color='red')
            return
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if container:
        for name in names:
            common.pprint("Starting container %s..." % name, color='green')
            dockerutils.start_container(k, name)
    else:
        codes = []
        for name in names:
            common.pprint("Starting vm %s..." % name, color='green')
            result = k.start(name)
            code = common.handle_response(result, name, element='', action='started')
            codes.append(code)
        os._exit(1 if 1 in codes else 0)


def stop(args):
    """Stop vm/container"""
    names = args.names
    container = args.container
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if not names:
        if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
            names = [open(lastvm).readlines()[0].strip()]
            common.pprint("Using %s as vm" % names[0], color='green')
        else:
            common.pprint("Missing Vm's name", color='red')
            return
    config = Kconfig(client=args.client, debug=args.debug)
    if config.extraclients:
        ks = config.extraclients
        ks.update({config.client: config.k})
    else:
        ks = {config.client: config.k}
    codes = []
    for cli in ks:
        k = ks[cli]
        if container:
            for name in names:
                common.pprint("Stopping container %s in %s..." % (name, cli), color='green')
                dockerutils.stop_container(k, name)
        else:
            for name in names:
                common.pprint("Stopping vm %s in %s..." % (name, cli), color='green')
                result = k.stop(name)
                code = common.handle_response(result, name, element='', action='stopped')
                codes.append(code)
    os._exit(1 if 1 in codes else 0)


def restart(args):
    """Restart vm/container"""
    names = args.names
    container = args.container
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if not names:
        if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
            names = [open(lastvm).readlines()[0].strip()]
            common.pprint("Using %s as vm" % names[0], color='green')
        else:
            common.pprint("Missing Vm's name", color='red')
            return
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if container:
        for name in names:
            common.pprint("Restarting container %s..." % name, color='green')
            dockerutils.stop_container(k, name)
            dockerutils.start_container(k, name)
    else:
        codes = []
        for name in names:
            common.pprint("Restarting vm %s..." % name, color='green')
            result = k.restart(name)
            code = common.handle_response(result, name, element='', action='restarted')
            codes.append(code)
        os._exit(1 if 1 in codes else 0)


def console(args):
    """Vnc/Spice/Serial/Container console"""
    name = args.name
    serial = args.serial
    container = args.container
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if not name:
        if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
            name = open(lastvm).readlines()[0].strip()
            common.pprint("Using %s as vm" % name, color='green')
        else:
            common.pprint("Missing Vm's name", color='red')
            return
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    tunnel = config.tunnel
    if container:
        dockerutils.console_container(k, name)
        return
    elif serial:
        k.serialconsole(name)
    else:
        k.console(name=name, tunnel=tunnel)


def delete(args):
    """Delete vm/container"""
    names = args.names
    container = args.container
    snapshots = args.snapshots
    yes = args.yes
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if not names:
        if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
            names = [open(lastvm).readlines()[0].strip()]
            common.pprint("Using %s as vm" % names[0], color='green')
        else:
            common.pprint("Missing Vm's name", color='red')
            return
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if not yes:
        common.confirm("Are you sure?")
    if container:
        for name in names:
            common.pprint("Deleting container %s" % name, color='red')
            dockerutils.delete_container(k, name)
    else:
        codes = []
        for name in names:
            result = k.delete(name, snapshots=snapshots)
            if result['result'] == 'success':
                common.pprint("vm %s deleted on %s" % (name, config.client), color='green')
                codes.append(0)
                common.lastvm(name, delete=True)
            else:
                reason = result['reason']
                common.pprint("Could not delete vm %s because %s" % (name, reason), color='red')
                codes.append(1)
        os._exit(1 if 1 in codes else 0)


def download(args):
    """Download Template"""
    pool = args.pool
    templates = args.templates
    cmd = args.cmd
    url = args.url
    config = Kconfig(client=args.client, debug=args.debug)
    result = config.handle_host(pool=pool, templates=templates, download=True, cmd=cmd, url=url)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def info(args):
    """Get info on vm"""
    names = args.names
    output = args.output
    fields = args.fields
    values = args.values
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if not names:
        if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
            names = [open(lastvm).readlines()[0].strip()]
            common.pprint("Using %s as vm" % names[0], color='green')
        else:
            common.pprint("Missing Vm's name", color='red')
            return
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    codes = []
    for name in names:
        result = k.info(name, output=output, fields=fields, values=values)
        code = common.handle_response(result, name, quiet=True)
        codes.append(code)
    os._exit(1 if 1 in codes else 0)


def host(args):
    """Handle host"""
    enable = args.enable
    disable = args.disable
    sync = args.sync
    if enable:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        result = baseconfig.enable_host(enable)
    elif disable:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        result = baseconfig.switch_host(disable)
    else:
        config = Kconfig(client=args.client, debug=args.debug)
        result = config.handle_host(enable=enable, disable=disable, sync=sync)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def list(args):
    """List hosts, profiles, templates, isos, pools or vms"""
    hosts = args.hosts
    profiles = args.profiles
    templates = args.templates
    isos = args.isos
    disks = args.disks
    pools = args.pools
    repos = args.repos
    products = args.products
    networks = args.networks
    containers = args.containers
    images = args.images
    plans = args.plans
    filters = args.filters
    short = args.short
    group = args.group
    repo = args.repo
    if hosts:
        clientstable = PrettyTable(["Host", "Type", "Enabled", "Current"])
        clientstable.align["Host"] = "l"
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
    if repos:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        repos = PrettyTable(["Repo", "Url"])
        repos.align["Repo"] = "l"
        reposinfo = baseconfig.list_repos()
        for repo in sorted(reposinfo):
            url = reposinfo[repo]
            repos.add_row([repo, url])
        print(repos)
        return
    elif products:
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
    config = Kconfig(client=args.client, debug=args.debug)
    if config.client != 'all':
        k = config.k
    if pools:
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
    if networks:
        networks = k.list_networks()
        common.pprint("Listing Networks...", color='green')
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
                # if 'plan' in networks[network]:
                #    plan = networks[network]['plan']
                # else:
                #     plan = 'N/A'
                # networkstable.add_row([network, networktype, cidr, dhcp, domain, mode, plan])
                networkstable.add_row([network, networktype, cidr, dhcp, domain, mode])
        networkstable.align["Network"] = "l"
        print(networkstable)
        return
    elif profiles:
        if containers:
            profiles = config.list_containerprofiles()
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
        else:
            profiles = config.list_profiles()
            if short:
                profilestable = PrettyTable(["Profile"])
                for profile in sorted(profiles):
                    profilename = profile[0]
                    profilestable.add_row([profilename])
            else:
                profilestable = PrettyTable(["Profile", "Numcpus", "Memory",
                                             "Pool", "Disks", "Template",
                                             "Nets", "Cloudinit", "Nested",
                                             "Reservedns", "Reservehost"])
                for profile in sorted(profiles):
                        profilestable.add_row(profile)
            profilestable.align["Profile"] = "l"
            print(profilestable)
        return
    elif templates:
        templatestable = PrettyTable(["Template"])
        templatestable.align["Template"] = "l"
        for template in k.volumes():
                templatestable.add_row([template])
        print(templatestable)
    elif isos:
        isostable = PrettyTable(["Iso"])
        isostable.align["Iso"] = "l"
        for iso in k.volumes(iso=True):
                isostable.add_row([iso])
        print(isostable)
    elif disks:
        common.pprint("Listing disks...", color='green')
        diskstable = PrettyTable(["Name", "Pool", "Path"])
        diskstable.align["Name"] = "l"
        disks = k.list_disks()
        for disk in sorted(disks):
            path = disks[disk]['path']
            pool = disks[disk]['pool']
            diskstable.add_row([disk, pool, path])
        print(diskstable)
    elif containers:
        common.pprint("Listing containers...", color='green')
        containers = PrettyTable(["Name", "Status", "Image", "Plan", "Command", "Ports"])
        for container in dockerutils.list_containers(k):
            if filters:
                status = container[1]
                if status == filters:
                    containers.add_row(container)
            else:
                containers.add_row(container)
        print(containers)
    elif images:
        common.pprint("Listing images...", color='green')
        images = PrettyTable(["Name"])
        for image in dockerutils.list_images(k):
            images.add_row([image])
        print(images)
    elif plans:
        vms = {}
        plans = PrettyTable(["Name", "Vms"])
        for plan in config.list_plans():
            planname = plan[0]
            planvms = plan[1]
            plans.add_row([planname, planvms])
        print(plans)
    else:
        customcolumn = 'Namespace' if config.type == 'kubevirt' else 'Report'
        if config.extraclients:
            allclients = config.extraclients.copy()
            allclients.update({config.client: config.k})
            vms = PrettyTable(["Name", "Host", "Status", "Ips", "Source", "Plan", "Profile", customcolumn])
            for cli in sorted(allclients):
                for vm in allclients[cli].list():
                    vm.insert(1, cli)
                    if filters:
                        status = vm[2]
                        if status == filters:
                            vms.add_row(vm)
                    else:
                        vms.add_row(vm)
            print(vms)
        else:
            vms = PrettyTable(["Name", "Status", "Ips", "Source", "Plan", "Profile", customcolumn])
            for vm in k.list():
                if config.planview and vm[4] != config.currentplan:
                    continue
                if filters:
                    status = vm[1]
                    if status == filters:
                        vms.add_row(vm)
                else:
                    vms.add_row(vm)
            print(vms)
            return


def vm(args):
    """Create vms"""
    name = args.name
    profile = args.profile
    profilefile = args.profilefile
    ip1 = args.ip1
    ip2 = args.ip2
    ip3 = args.ip3
    ip4 = args.ip4
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug)
    if name is None:
        name = nameutils.get_random_name()
        if config.type == 'kubevirt':
            name = name.replace('_', '-')
        common.pprint("Using %s as name of the vm" % name, color='green')
    if profile is not None and profile.endswith('.yml'):
        profilefile = profile
        profile = None
    if profilefile is not None:
        if not os.path.exists(profilefile):
            common.pprint("Missing profile file", color='red')
            os._exit(1)
        else:
            with open(profilefile, 'r') as entries:
                config.profiles = yaml.load(entries)
    if profile is None:
        if len(config.profiles) == 1:
            profile = config.profiles.keys()[0]
        else:
            common.pprint("Missing profile", color='red')
            os._exit(1)
    result = config.create_vm(name, profile, ip1=ip1, ip2=ip2, ip3=ip3, ip4=ip4, overrides=overrides)
    code = common.handle_response(result, name, element='', action='created', client=config.client)
    return code


def clone(args):
    """Clone existing vm"""
    name = args.name
    base = args.base
    full = args.full
    start = args.start
    common.pprint("Cloning vm %s from vm %s..." % (name, base), color='green')
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    k.clone(base, name, full=full, start=start)


def update(args):
    """Update ip, memory or numcpus"""
    name = args.name
    ip1 = args.ip1
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
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if dns:
        common.pprint("Creating Dns entry for %s..." % (name), color='green')
        if net is not None:
            nets = [net]
        else:
            nets = k.vm_ports(name)
        if nets and domain is None:
            domain = nets[0]
        if not nets:
            return
        else:
            common.pprint("Updating ip of vm %s to %s..." % (name, ip1), color='green')
            k.reserve_dns(name=name, nets=nets, domain=domain, ip=ip1)
    elif ip1 is not None:
        common.pprint("Updating ip of vm %s to %s..." % (name, ip1), color='green')
        k.update_metadata(name, 'ip', ip1)
    elif cloudinit:
        common.pprint("Removing cloudinit information of vm %s" % (name), color='green')
        k.remove_cloudinit(name)
        return
    elif plan is not None:
        common.pprint("Updating plan of vm %s to %s..." % (name, plan), color='green')
        k.update_metadata(name, 'plan', plan)
    elif template is not None:
        common.pprint("Updating template of vm %s to %s..." % (name, template), color='green')
        k.update_metadata(name, 'template', template)
    elif memory is not None:
        common.pprint("Updating memory of vm %s to %s..." % (name, memory), color='green')
        k.update_memory(name, memory)
    elif numcpus is not None:
        common.pprint("Updating numcpus of vm %s to %s..." % (name, numcpus), color='green')
        k.update_cpu(name, numcpus)
    elif autostart:
        common.pprint("Setting autostart for vm %s..." % (name), color='green')
        k.update_start(name, start=True)
    elif noautostart:
        common.pprint("Removing autostart for vm %s..." % (name), color='green')
        k.update_start(name, start=False)
    elif information:
        common.pprint("Setting information for vm %s..." % (name), color='green')
        k.update_information(name, information)
    elif iso:
        common.pprint("Switching iso for vm %s to %s..." % (name, iso), color='green')
        common.pprint("Note it will only be effective upon next start", color='green')
        k.update_iso(name, iso)
    elif host:
        common.pprint("Creating Host entry for vm %s..." % (name), color='green')
        nets = k.vm_ports(name)
        if not nets:
            return
        if domain is None:
            domain = nets[0]
        k.reserve_host(name, nets, domain)


def disk(args):
    """Add/Delete disk of vm"""
    name = args.name
    delete = args.delete
    size = args.size
    diskname = args.diskname
    template = args.template
    pool = args.pool
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if delete:
        if diskname is None:
            common.pprint("Missing diskname. Leaving...", color='red')
            os._exit(1)
        common.pprint("Deleting disk %s from %s..." % (diskname, name), color='green')
        k.delete_disk(name, diskname)
        return
    if size is None:
        common.pprint("Missing size. Leaving...", color='red')
        os._exit(1)
    if pool is None:
        common.pprint("Missing pool. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding disk to %s..." % (name), color='green')
    k.add_disk(name=name, size=size, pool=pool, template=template)


def nic(args):
    """Add/Delete nic of vm"""
    name = args.name
    delete = args.delete
    interface = args.interface
    network = args.network
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if delete:
        common.pprint("Deleting nic from %s..." % (name), color='green')
        k.delete_nic(name, interface)
        return
    if network is None:
        common.pprint("Missing network. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding Nic %s..." % (name), color='green')
    k.add_nic(name=name, network=network)


def pool(args):
    """Create/Delete pool"""
    pool = args.pool
    delete = args.delete
    full = args.delete
    pooltype = args.pooltype
    path = args.path
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if delete:
        common.pprint("Deleting pool %s..." % (pool), color='green')
        k.delete_pool(name=pool, full=full)
        return
    if path is None:
        common.pprint("Missing path. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding pool %s..." % (pool), color='green')
    k.create_pool(name=pool, poolpath=path, pooltype=pooltype)


def plan(args):
    """Create/Delete/Stop/Start vms from plan file"""
    plan = args.plan
    ansible = args.ansible
    get = args.get
    path = args.path
    autostart = args.autostart
    noautostart = args.noautostart
    container = args.container
    inputfile = args.inputfile
    topologyfile = args.topologyfile
    start = args.start
    stop = args.stop
    delete = args.delete
    delay = args.delay
    use = args.use
    yes = args.yes
    scale = args.scale
    info = args.info
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    if info and get is None:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        baseconfig.info_plan(inputfile)
        os._exit(0)
    config = Kconfig(client=args.client, debug=args.debug)
    if use is not None:
        rootdir = os.path.expanduser('~/.kcli')
        if not os.path.exists(rootdir):
            os.makedirs(rootdir)
        with open('%s/plan' % rootdir, 'w') as p:
            p.write('%s\n' % use)
        return
    if plan is None:
        if config.planview:
            plan = config.currentplan
        else:
            plan = nameutils.get_random_name()
            common.pprint("Using %s as name of the plan" % plan, color='green')
    if delete and not yes:
        common.confirm("Are you sure?")
    config.plan(plan, ansible=ansible, get=get, path=path, autostart=autostart,
                container=container, noautostart=noautostart, inputfile=inputfile,
                start=start, stop=stop, delete=delete, delay=delay,
                topologyfile=topologyfile, scale=scale,
                overrides=overrides, info=info)
    return 0


def repo(args):
    """Create/Delete repo"""
    repo = args.repo
    delete = args.delete
    url = args.url
    update = args.update
    download = args.download
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if update:
        if repo is None:
            common.pprint("Updating all repos...", color='blue')
            repos = baseconfig.list_repos()
            for repo in repos:
                common.pprint("Updating repo %s..." % (repo), color='green')
                baseconfig.update_repo(repo)
        else:
            common.pprint("Updating repo %s..." % (repo), color='green')
            baseconfig.update_repo(repo)
        return
    if repo is None:
        common.pprint("Missing repo. Leaving...", color='red')
        os._exit(1)
    if delete:
        common.pprint("Deleting repo %s..." % (repo), color='green')
        baseconfig.delete_repo(repo)
        return
    if update:
        common.pprint("Deleting repo %s..." % (repo), color='green')
        baseconfig.delete_repo(repo)
        return
    if download:
        common.pprint("Downloading repo %s..." % (repo), color='green')
        baseconfig.download_repo(repo)
        return
    if url is None:
        common.pprint("Missing url. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding repo %s..." % (repo), color='green')
    baseconfig.create_repo(repo, url)
    return 0


def product(args):
    """Create product"""
    repo = args.repo
    product = args.product
    latest = args.latest
    plan = args.plan
    group = args.group
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    info = args.info
    search = args.search
    if info:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        common.pprint("Providing information on product %s..." % (product), color='green')
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
        config = Kconfig(client=args.client, debug=args.debug)
        common.pprint("Creating product %s..." % (product), color='green')
        config.create_product(product, repo=repo, group=group, plan=plan, latest=latest, overrides=overrides)
    return 0


def ssh(args):
    """Ssh into vm"""
    name = args.name
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if not name:
        if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
            name = [open(lastvm).readlines()[0].strip()]
            common.pprint("Using %s as vm" % name[0], color='green')
        else:
            common.pprint("Missing Vm's name", color='red')
            return
    l = args.L
    r = args.R
    D = args.D
    X = args.X
    config = Kconfig(client=args.client, debug=args.debug)
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
    sshcommand = k.ssh(name, user=user, local=l, remote=r, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, D=D)
    if sshcommand is not None:
        os.system(sshcommand)
    else:
        common.pprint("Couldnt ssh to %s" % name, color='red')


def scp(args):
    """Scp into vm"""
    recursive = args.recursive
    source = args.source[0]
    destination = args.destination[0]
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    tunnel = config.tunnel
    if len(source.split(':')) == 2:
        name = source.split(':')[0]
        source = source.split(':')[1]
        download = True
    elif len(destination.split(':')) == 2:
        name = destination.split(':')[0]
        destination = destination.split(':')[1]
        download = False
    else:
        common.pprint("Couldn't run scp", color='red')
        return
    if '@' in name and len(name.split('@')) == 2:
        user = name.split('@')[0]
        name = name.split('@')[1]
    else:
        user = None
    scpcommand = k.scp(name, user=user, source=source, destination=destination,
                       tunnel=tunnel, download=download, recursive=recursive)
    if scpcommand is not None:
        os.system(scpcommand)
    else:
        common.pprint("Couldn't run scp", color='red')


def network(args):
    """Create/Delete/List Network"""
    name = args.name
    delete = args.delete
    isolated = args.isolated
    cidr = args.cidr
    nodhcp = args.nodhcp
    domain = args.domain
    pxe = args.pxe
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if name is None:
        common.pprint("Missing Network", color='red')
        os._exit(1)
    if delete:
        result = k.delete_network(name=name)
        common.handle_response(result, name, element='Network ', action='deleted')
    else:
        if isolated:
            nat = False
        else:
            nat = True
        dhcp = not nodhcp
        result = k.create_network(name=name, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, pxe=pxe)
        common.handle_response(result, name, element='Network ')


def bootstrap(args):
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


def container(args):
    """Create container"""
    name = args.name
    profile = args.profile
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if name is None:
        name = nameutils.get_random_name()
        if config.type == 'kubevirt':
            name = name.replace('_', '-')
    if profile is None:
        common.pprint("Missing profile", color='red')
        os._exit(1)
    containerprofiles = {k: v for k, v in config.profiles.iteritems() if 'type' in v and v['type'] == 'container'}
    if profile not in containerprofiles:
        common.pprint("profile %s not found. Trying to use the profile as image"
                      "and default values..." % profile, color='blue')
        dockerutils.create_container(k, name, profile)
    else:
        common.pprint("Deploying vm %s from profile %s..." % (name, profile), color='green')
        profile = containerprofiles[profile]
        image = next((e for e in [profile.get('image'), profile.get('template')] if e is not None), None)
        if image is None:
            common.pprint("Missing image in profile %s. Leaving..." % profile, color='red')
            os._exit(1)
        cmd = profile.get('cmd', None)
        ports = profile.get('ports', None)
        environment = profile.get('environment', None)
        volumes = next((e for e in [profile.get('volumes'), profile.get('disks')] if e is not None), None)
        dockerutils.create_container(k, name, image, nets=None, cmd=cmd,
                                     ports=ports, volumes=volumes,
                                     environment=environment)
    common.pprint("container %s created" % (name), color='green')
    return


def snapshot(args):
    """Create/Delete/Revert snapshot"""
    snapshot = args.snapshot
    name = args.name
    revert = args.revert
    delete = args.delete
    listing = args.listing
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    if revert:
        common.pprint("Reverting snapshot of %s named %s..." % (name, snapshot), color='green')
    elif delete:
        common.pprint("Deleting snapshot of %s named %s..." % (name, snapshot), color='green')
    elif listing:
        common.pprint("Listing snapshots of %s..." % (name), color='green')
        snapshots = k.snapshot(snapshot, name, listing=True)
        if isinstance(snapshots, dict):
            common.pprint("Vm %s not found" % (name), color='red')
            return
        else:
            for snapshot in snapshots:
                print(snapshot)
        return
    elif snapshot is None:
        common.pprint("Missing snapshot name", color='red')
        return {'result': 'success'}
    else:
        common.pprint("Creating snapshot of %s named %s..." % (name, snapshot), color='green')
    result = k.snapshot(snapshot, name, revert=revert, delete=delete)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def report(args):
    """Report info about host"""
    config = Kconfig(client=args.client, debug=args.debug)
    k = config.k
    k.report()


def switch(args):
    """Handle host"""
    host = args.host
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.switch_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def version(args):
    """Show product version"""
    common.pprint("Current version: %s" % __version__)
    try:
        f = urllib2.urlopen('https://pypi.python.org/pypi/kcli/json', timeout=3)
        common.pprint("Latest PyPI published version: %s" % json.load(f)['info']['version'])
    except Exception as e:
        pass


def cli():
    parser = argparse.ArgumentParser(description='Libvirt/VirtualBox/Kubevirt'
                                     'wrapper on steroids. Check out '
                                     'https://github.com/karmab/kcli!')
    parser.add_argument('-C', '--client')
    parser.add_argument('-d', '--debug', action='store_true')

    subparsers = parser.add_subparsers(metavar='')

    bootstrap_info = 'Generate basic config file'
    bootstrap_parser = subparsers.add_parser('bootstrap', help=bootstrap_info, description=bootstrap_info)
    bootstrap_parser.add_argument('-n', '--name', help='Name to use', metavar='CLIENT')
    bootstrap_parser.add_argument('-H', '--host', help='Host to use', metavar='HOST')
    bootstrap_parser.add_argument('-p', '--port', help='Port to use', metavar='PORT')
    bootstrap_parser.add_argument('-u', '--user', help='User to use', default='root', metavar='USER')
    bootstrap_parser.add_argument('-P', '--protocol', help='Protocol to use', default='ssh', metavar='PROTOCOL')
    bootstrap_parser.add_argument('-U', '--url', help='URL to use', metavar='URL')
    bootstrap_parser.add_argument('--pool', help='Pool to use', metavar='POOL')
    bootstrap_parser.add_argument('--poolpath', help='Pool Path to use', metavar='POOLPATH')
    bootstrap_parser.set_defaults(func=bootstrap)

    clone_info = 'Clone existing vm'
    clone_parser = subparsers.add_parser('clone', description=clone_info, help=clone_info)
    clone_parser.add_argument('-b', '--base', help='Base VM', metavar='BASE')
    clone_parser.add_argument('-f', '--full', action='store_true', help='Full Clone')
    clone_parser.add_argument('-s', '--start', action='store_true', help='Start cloned VM')
    clone_parser.add_argument('name', metavar='VMNAME')
    clone_parser.set_defaults(func=clone)

    console_info = 'Vnc/Spice/Serial/Container console'
    console_parser = subparsers.add_parser('console', description=console_info, help=console_info)
    console_parser.add_argument('-s', '--serial', action='store_true')
    console_parser.add_argument('--container', action='store_true')
    console_parser.add_argument('name', metavar='VMNAME', nargs='?')
    console_parser.set_defaults(func=console)

    container_info = 'Create container'
    container_parser = subparsers.add_parser('container', description=container_info, help=container_info)
    container_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    container_parser.add_argument('name', metavar='NAME', nargs='?')
    container_parser.set_defaults(func=container)

    delete_info = 'Delete vm/container'
    delete_parser = subparsers.add_parser('delete', description=delete_info, help=delete_info)
    delete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    delete_parser.add_argument('--container', action='store_true')
    delete_parser.add_argument('--snapshots', action='store_true', help='Remove snapshots if needed')
    delete_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    delete_parser.set_defaults(func=delete)

    disk_info = 'Add/Delete disk of vm'
    disk_parser = subparsers.add_parser('disk', description=disk_info, help=disk_info)
    disk_parser.add_argument('-d', '--delete', action='store_true')
    disk_parser.add_argument('-s', '--size', help='Size of the disk to add, in GB', metavar='SIZE')
    disk_parser.add_argument('-n', '--diskname', help='Name or Path of the disk, when deleting', metavar='DISKNAME')
    disk_parser.add_argument('-t', '--template', help='Name or Path of a Template, when adding', metavar='TEMPLATE')
    disk_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    disk_parser.add_argument('name')
    disk_parser.set_defaults(func=disk)

    download_info = 'Download template'
    download_parser = subparsers.add_parser('download', description=download_info, help=download_info)
    download_parser.add_argument('-c', '--cmd', help='Extra command to launch after downloading', metavar='CMD')
    download_parser.add_argument('-p', '--pool', default='default',
                                 help='Pool to use. Defaults to default',
                                 metavar='POOL')
    download_parser.add_argument('-u', '--url', help='Url to use', metavar='URL')
    download_parser.add_argument('templates', choices=sorted(TEMPLATES.keys()),
                                 default='', help='Template/Image to download',
                                 nargs='*')
    download_parser.set_defaults(func=download)

    host_info = 'List and Handle host'
    host_parser = subparsers.add_parser('host', description=host_info, help=host_info)
    host_parser.add_argument('-d', '--disable', help='Disable indicated client', metavar='CLIENT')
    host_parser.add_argument('-e', '--enable', help='Enable indicated client', metavar='CLIENT')
    host_parser.add_argument('-s', '--sync', action='store_true',
                             help='sync templates between first host and other'
                             'ones of the specified list')
    host_parser.set_defaults(func=host)

    info_info = 'Info vms'
    info_parser = subparsers.add_parser('info', description=info_info, help=info_info)
    info_parser.add_argument('-f', '--fields',
                             help='Display Corresponding list of fields,'
                             'separated by a comma', metavar='FIELDS')
    info_parser.add_argument('-o', '--output', choices=['plain', 'yaml'], help='Format of the output')
    info_parser.add_argument('-v', '--values', action='store_true', help='Only report values')
    info_parser.add_argument('names', help='VMNAMES', nargs='*')
    info_parser.set_defaults(func=info)

    list_info = 'List hosts, profiles, templates, isos,...'
    list_parser = subparsers.add_parser('list', description=list_info, help=list_info)
    list_parser.add_argument('-H', '--hosts', action='store_true')
    list_parser.add_argument('-p', '--profiles', action='store_true')
    list_parser.add_argument('-t', '--templates', action='store_true')
    list_parser.add_argument('-i', '--isos', action='store_true')
    list_parser.add_argument('-d', '--disks', action='store_true')
    list_parser.add_argument('-P', '--pools', action='store_true')
    list_parser.add_argument('-n', '--networks', action='store_true')
    list_parser.add_argument('--containers', action='store_true')
    list_parser.add_argument('--images', action='store_true')
    list_parser.add_argument('--short', action='store_true')
    list_parser.add_argument('--plans', action='store_true')
    list_parser.add_argument('--repos', action='store_true')
    list_parser.add_argument('--products', action='store_true')
    list_parser.add_argument('-g', '--group', help='Only Display products of the indicated group', metavar='GROUP')
    list_parser.add_argument('-r', '--repo', help='Only Display products of the indicated repository', metavar='REPO')
    list_parser.add_argument('-f', '--filters', choices=('up', 'down'))
    list_parser.set_defaults(func=list)

    network_info = 'Create/Delete Network'
    network_parser = subparsers.add_parser('network', description=network_info, help=network_info)
    network_parser.add_argument('-d', '--delete', action='store_true')
    network_parser.add_argument('-i', '--isolated', action='store_true', help='Isolated Network')
    network_parser.add_argument('-c', '--cidr', help='Cidr of the net', metavar='CIDR')
    network_parser.add_argument('--nodhcp', action='store_true', help='Disable dhcp on the net')
    network_parser.add_argument('--domain', help='DNS domain. Defaults to network name')
    network_parser.add_argument('-p', '--pxe', help='Ip of a Pxe Server', metavar='PXE')
    network_parser.add_argument('name', metavar='NETWORK')
    network_parser.set_defaults(func=network)

    nic_info = 'Add/Delete nic of vm'
    nic_parser = subparsers.add_parser('nic', description=nic_info, help=nic_info)
    nic_parser.add_argument('-d', '--delete', action='store_true')
    nic_parser.add_argument('-i', '--interface', help='Name of the interface, when deleting', metavar='INTERFACE')
    nic_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    nic_parser.add_argument('name', metavar='VMNAME')
    nic_parser.set_defaults(func=nic)

    plan_info = 'Create/Delete/Stop/Start vms from plan file'
    plan_parser = subparsers.add_parser('plan', description=plan_info, help=plan_info)
    plan_parser.add_argument('-A', '--ansible', help='Generate ansible inventory', action='store_true')
    plan_parser.add_argument('-d', '--delete', action='store_true')
    plan_parser.add_argument('-g', '--get', help='Download specific plan(s).'
                             ' Use --path for specific directory', metavar='URL')
    plan_parser.add_argument('-i', '--info', action='store_true', help='Provide information on the given plan')
    plan_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan', metavar='PATH')
    plan_parser.add_argument('-a', '--autostart', action='store_true', help='Set all vms from plan to autostart')
    plan_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    plan_parser.add_argument('-n', '--noautostart', action='store_true', help='Prevent all vms from plan to autostart')
    plan_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    plan_parser.add_argument('-s', '--start', action='store_true', help='start all vms from plan')
    plan_parser.add_argument('-w', '--stop', action='store_true')
    plan_parser.add_argument('--scale', help='Scale plan using provided parameters')
    plan_parser.add_argument('-t', '--topologyfile', help='Topology file')
    plan_parser.add_argument('-u', '--use', nargs='?', const='kvirt',
                             help='Plan to set as current. Defaults to kvirt',
                             metavar='USE')
    plan_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    plan_parser.add_argument('--delay', default=0, help="Delay between each vm's creation", metavar='DELAY')
    plan_parser.add_argument('-P', '--param', action='append',
                             help='Define parameter for rendering within'
                             ' scripts. Can be repeated', metavar='PARAM')
    plan_parser.add_argument('--paramfile', help='Param file', metavar='PARAMFILE')
    plan_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plan_parser.set_defaults(func=plan)

    pool_info = 'Create/Delete pool'
    pool_parser = subparsers.add_parser('pool', description=pool_info, help=pool_info)
    pool_parser.add_argument('-d', '--delete', action='store_true')
    pool_parser.add_argument('-f', '--full', action='store_true')
    pool_parser.add_argument('-t', '--pooltype', help='Type of the pool', choices=('dir', 'logical'), default='dir')
    pool_parser.add_argument('-p', '--path', help='Path of the pool', metavar='PATH')
    pool_parser.add_argument('pool')
    pool_parser.set_defaults(func=pool)

    product_info = 'Deploy Product'
    product_parser = subparsers.add_parser('product', description=product_info, help=product_info)
    product_parser.add_argument('-g', '--group', help='Group to use as a name during deployment', metavar='GROUP')
    product_parser.add_argument('-i', '--info', action='store_true', help='Provide information on the given product')
    product_parser.add_argument('-l', '--latest', action='store_true', help='Grab latest version of the plans')
    product_parser.add_argument('-p', '--plan', help='Plan to use as a name '
                                'during deployment', metavar='PLAN')
    product_parser.add_argument('-P', '--param', action='append',
                                help='Define parameter for rendering within '
                                'scripts. Can be repeated several times',
                                metavar='PARAM')
    product_parser.add_argument('--paramfile', help='Input file', metavar='PARAMFILE')
    product_parser.add_argument('-r', '--repo', help='Repo to use, '
                                'if deploying a product present in several '
                                'repos', metavar='REPO')
    product_parser.add_argument('-s', '--search', action='store_true',
                                help='Display matching products')
    product_parser.add_argument('product', metavar='PRODUCT')
    product_parser.set_defaults(func=product)

    repo_info = 'Create/Delete repos'
    repo_parser = subparsers.add_parser('repo', description=repo_info, help=repo_info)
    repo_parser.add_argument('-d', '--delete', action='store_true')
    repo_parser.add_argument('-u', '--url', help='URL of the repo', metavar='URL')
    repo_parser.add_argument('-U', '--update', action='store_true', help='Update metadata of the repo')
    repo_parser.add_argument('-D', '--download', action='store_true', help='Download all content of the repo')
    repo_parser.add_argument('repo')
    repo_parser.set_defaults(func=repo)

    report_info = 'Report Info about Host'
    report_parser = subparsers.add_parser('report', description=report_info, help=report_info)
    report_parser.set_defaults(func=report)

    scp_info = 'Scp into vm'
    scp_parser = subparsers.add_parser('scp', description=scp_info, help=scp_info)
    scp_parser.add_argument('-r', '--recursive', help='Recursive', action='store_true')
    scp_parser.add_argument('source', nargs=1)
    scp_parser.add_argument('destination', nargs=1)
    scp_parser.set_defaults(func=scp)

    snapshot_info = 'Create/Delete/Revert snapshot'
    snapshot_parser = subparsers.add_parser('snapshot', description=snapshot_info, help=snapshot_info)
    snapshot_parser.add_argument('-n', '--name', help='Use vm name for creation'
                                 '/revert/delete', required=True,
                                 metavar='VMNAME')
    snapshot_parser.add_argument('-r', '--revert', help='Revert to indicated snapshot', action='store_true')
    snapshot_parser.add_argument('-d', '--delete', help='Delete indicated snapshot', action='store_true')
    snapshot_parser.add_argument('-l', '--listing', help='List snapshots', action='store_true')
    snapshot_parser.add_argument('snapshot', nargs='?')
    snapshot_parser.set_defaults(func=snapshot)

    ssh_info = 'Ssh into vm'
    ssh_parser = subparsers.add_parser('ssh', description=ssh_info, help=ssh_info)
    ssh_parser.add_argument('-D', help='Dynamic Forwarding', metavar='LOCAL')
    ssh_parser.add_argument('-L', help='Local Forwarding', metavar='LOCAL')
    ssh_parser.add_argument('-R', help='Remote Forwarding', metavar='REMOTE')
    ssh_parser.add_argument('-X', action='store_true', help='Enable X11 Forwarding')
    ssh_parser.add_argument('name', metavar='VMNAME', nargs='*')
    ssh_parser.set_defaults(func=ssh)

    start_info = 'Start vms/containers'
    start_parser = subparsers.add_parser('start', description=start_info, help=start_info)
    start_parser.add_argument('-c', '--container', action='store_true')
    start_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    start_parser.set_defaults(func=start)

    stop_info = 'Stop vms/containers'
    stop_parser = subparsers.add_parser('stop', description=stop_info, help=stop_info)
    stop_parser.add_argument('-c', '--container', action='store_true')
    stop_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    stop_parser.set_defaults(func=stop)

    restart_info = 'Restart vms/containers'
    restart_parser = subparsers.add_parser('restart', description=restart_info, help=stop_info)
    restart_parser.add_argument('-c', '--container', action='store_true')
    restart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    restart_parser.set_defaults(func=restart)

    switch_info = 'Switch host'
    switch_parser = subparsers.add_parser('switch', description=switch_info, help=switch_info)
    switch_parser.add_argument('host', help='HOST')
    switch_parser.set_defaults(func=switch)

    update_info = 'Update ip, memory or numcpus'
    update_parser = subparsers.add_parser('update', description=update_info, help=update_info)
    update_parser.add_argument('-1', '--ip1', help='Ip to set', metavar='IP1')
    update_parser.add_argument('-i', '--information', '--info', help='Information to set', metavar='INFORMATION')
    update_parser.add_argument('--network', '--net', help='Network to update', metavar='NETWORK')
    update_parser.add_argument('-m', '--memory', help='Memory to set', metavar='MEMORY')
    update_parser.add_argument('-c', '--numcpus', type=int, help='Number of cpus to set', metavar='NUMCPUS')
    update_parser.add_argument('-p', '--plan', help='Plan Name to set', metavar='PLAN')
    update_parser.add_argument('-a', '--autostart', action='store_true', help='Set VM to autostart')
    update_parser.add_argument('-n', '--noautostart', action='store_true', help='Prevent VM from autostart')
    update_parser.add_argument('--dns', action='store_true', help='Update Dns entry for the vm')
    update_parser.add_argument('--host', action='store_true', help='Update Host entry for the vm')
    update_parser.add_argument('-d', '--domain', help='Domain', metavar='DOMAIN')
    update_parser.add_argument('-t', '--template', help='Template to set', metavar='TEMPLATE')
    update_parser.add_argument('--iso', help='Iso to set', metavar='ISO')
    update_parser.add_argument('--cloudinit', action='store_true', help='Remove Cloudinit Information from vm')
    update_parser.add_argument('name', metavar='VMNAME')
    update_parser.set_defaults(func=update)

    version_info = 'Show program\'s version number and exit'
    version_parser = subparsers.add_parser('version', description=version_info, help=version_info)
    version_parser.set_defaults(func=version)

    vm_info = 'Create vm'
    vm_parser = subparsers.add_parser('vm', description=vm_info, help=vm_info)
    vm_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    vm_parser.add_argument('--profilefile', help='File to load profiles from', metavar='PROFILEFILE')
    vm_parser.add_argument('-1', '--ip1', help='Optional Ip to assign to eth0. '
                           'Netmask and gateway will be retrieved from profile',
                           metavar='IP1')
    vm_parser.add_argument('-2', '--ip2', help='Optional Ip to assign to eth1. '
                           'Netmask and gateway will be retrieved from profile',
                           metavar='IP2')
    vm_parser.add_argument('-3', '--ip3', help='Optional Ip to assign to eth2. '
                           'Netmask and gateway will be retrieved from profile',
                           metavar='IP3')
    vm_parser.add_argument('-4', '--ip4', help='Optional Ip to assign to eth3. '
                           'Netmask and gateway will be retrieved from profile',
                           metavar='IP4')
    vm_parser.add_argument('-P', '--param', action='append',
                           help='Define parameter for rendering within scripts.'
                           'Can be repeated', metavar='PARAM')
    vm_parser.add_argument('--paramfile', help='Get parameters for rendering'
                           'within scripts from a file.Takes precedence over'
                           'individual parameters', metavar='PARAMFILE')
    vm_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vm_parser.set_defaults(func=vm)
    if len(sys.argv) == 1:
        parser.print_help()
        os._exit(0)
    args = parser.parse_args()
    if args.func.func_name == 'vm' and args.client is not None and ',' in args.client:
            args.client = random.choice(args.client.split(','))
            common.pprint("Selecting %s for creation" % args.client, color='green')
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if args.client != 'all' and not baseconfig.enabled:
        common.pprint("Disabled hypervisor.Leaving...", color='red')
        os._exit(1)
    args.func(args)


if __name__ == '__main__':
    cli()
