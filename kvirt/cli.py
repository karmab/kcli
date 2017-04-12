#!/usr/bin/env python

from config import Kconfig
from defaults import TEMPLATES
from prettytable import PrettyTable
from shutil import copyfile
import argparse
import common
import dockerutils
import fileinput
import os
import yaml
from kvirt.kvm import Kvirt

__version__ = '5.24'


def start(args):
    """Start vm/container"""
    name = args.name
    container = args.container
    global config
    k = config.k
    if container:
        common.pprint("Started container %s..." % name, color='green')
        dockerutils.start_container(k, name)
    else:
        common.pprint("Started vm %s..." % name, color='green')
        result = k.start(name)
        code = common.handle_response(result, name, element='', action='started')
        os._exit(code)


def stop(args):
    """Stop vm/container"""
    name = args.name
    container = args.container
    global config
    k = config.k
    if container:
        common.pprint("Stopped container %s..." % name, color='green')
        dockerutils.stop_container(k, name)
    else:
        common.pprint("Stopped vm %s..." % name, color='green')
        result = k.stop(name)
        code = common.handle_response(result, name, element='', action='stopped')
        os._exit(code)


def console(args):
    """Vnc/Spice/Serial/Container console"""
    name = args.name
    serial = args.serial
    global config
    k = config.k
    tunnel = config.tunnel
    if serial:
        k.serialconsole(name)
    else:
        k.console(name=name, tunnel=tunnel)


def delete(args):
    """Delete vm/container"""
    name = args.name
    container = args.container
    force = args.force
    yes = args.yes
    global config
    k = config.k
    if not yes:
        common.confirm("Are you sure?")
    if container:
        common.pprint("Deleted container %s..." % name, color='red')
        dockerutils.delete_container(k, name)
    else:
        code = k.delete(name, force=force)
        if code == 0:
            common.pprint("Deleted vm %s..." % name, color='red')
        os._exit(code)


def info(args):
    name = args.name
    global config
    k = config.k
    code = k.info(name)
    os._exit(code)


def host(args):
    """List and Handle host"""
    switch = args.switch
    report = args.report
    profiles = args.profiles
    templates = args.templates
    isos = args.isos
    disks = args.disks
    pool = args.pool
    template = args.template
    download = args.download
    global config
    k = config.k
    if switch:
        if switch not in config.clients:
            common.pprint("Client %s not found in config.Leaving...." % switch, color='green')
            os._exit(1)
        common.pprint("Switching to client %s..." % switch, color='green')
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if os.path.exists(inifile):
            for line in fileinput.input(inifile, inplace=True):
                if 'client' in line:
                    print(" client: %s" % switch)
                else:
                    print(line.rstrip())
        return
    if report:
        k.report()
    elif profiles:
        for profile in sorted(config.profiles):
            print(profile)
    elif templates:
        for template in sorted(k.volumes()):
            print(template)
    elif isos:
        for iso in sorted(k.volumes(iso=True)):
            print(iso)
    elif disks:
        common.pprint("Listing disks...", color='green')
        diskstable = PrettyTable(["Name", "Pool", "Path"])
        diskstable.align["Name"] = "l"
        k = config.get()
        disks = k.list_disks()
        for disk in sorted(disks):
            path = disks[disk]['path']
            pool = disks[disk]['pool']
            diskstable.add_row([disk, pool, path])
        print(diskstable)
    elif download:
        if pool is None:
            common.pprint("Missing pool.Leaving...", color='red')
            os._exit(1)
        if template is None:
            common.pprint("Missing template.Leaving...", color='red')
            os._exit(1)
        common.pprint("Grabbing template %s..." % template, color='green')
        template = TEMPLATES[template]
        shortname = os.path.basename(template)
        result = k.add_image(template, pool)
        code = common.handle_response(result, shortname, element='Template ', action='Added')
        os._exit(code)


def list(args):
    """List clients, profiles, templates, isos, pools or vms"""
    hosts = args.hosts
    clients = args.clients
    profiles = args.profiles
    templates = args.templates
    isos = args.isos
    disks = args.disks
    pools = args.pools
    networks = args.networks
    containers = args.containers
    plans = args.plans
    filters = args.filters
    short = args.short
    global config
    if config.client == 'all':
        clis = []
        for cli in sorted(config.clients):
            clientconfig = Kconfig(client=cli)
            clis.append(clientconfig)
    else:
        k = config.k
    if pools:
        pools = k.list_pools()
        if short:
            for pool in sorted(pools):
                poolstable = PrettyTable(["Pool"])
                poolstable.add_row([pool])
        else:
            for pool in sorted(pools):
                poolstable = PrettyTable(["Pool", "Path"])
                poolpath = k.get_pool_path(pool)
                poolstable.add_row([pool, poolpath])
        poolstable.align["Pool"] = "l"
        print(poolstable)
        return
    if hosts:
        clientstable = PrettyTable(["Host", "Current"])
        clientstable.align["Host"] = "l"
        for client in sorted(config.clients):
            if client == config.client:
                clientstable.add_row([client, 'X'])
            else:
                clientstable.add_row([client, ''])
        print(clientstable)
        return
    if networks:
        networks = k.list_networks()
        common.pprint("Listing Networks...", color='green')
        if short:
            networkstable = PrettyTable(["Network"])
            for network in sorted(networks):
                networkstable.add_row([network])
        else:
            networkstable = PrettyTable(["Network", "Type", "Cidr", "Dhcp", "Mode"])
            for network in sorted(networks):
                networktype = networks[network]['type']
                cidr = networks[network]['cidr']
                dhcp = networks[network]['dhcp']
                mode = networks[network]['mode']
                networkstable.add_row([network, networktype, cidr, dhcp, mode])
        networkstable.align["Network"] = "l"
        print(networkstable)
        return
    if clients:
        clientstable = PrettyTable(["Name", "Current"])
        clientstable.align["Name"] = "l"
        for client in sorted(config.clients):
            if client == config.client:
                clientstable.add_row([client, 'X'])
            else:
                clientstable.add_row([client, ''])
        print(clientstable)
    elif profiles:
        profiles = config.list_profiles()
        if short:
            profilestable = PrettyTable(["Profile"])
            for profile in sorted(profiles):
                profilename = profile[0]
                profilestable.add_row([profilename])
        else:
            profilestable = PrettyTable(["Profile", "Numcpus", "Memory", "Pool", "Disks", "Template", "Nets", "Cloudinit", "Nested", "Reservedns", "Reservehost"])
            for profile in sorted(profiles):
                    profilestable.add_row(profile)
        profilestable.align["Network"] = "l"
        print(profilestable)
        return
    elif templates:
        templatestable = PrettyTable(["Template"])
        templatestable.align["Template"] = "l"
        for template in sorted(k.volumes()):
                templatestable.add_row([template])
        print(templatestable)
    elif isos:
        isostable = PrettyTable(["Iso"])
        isostable.align["Iso"] = "l"
        for iso in sorted(k.volumes(iso=True)):
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
    elif plans:
        vms = {}
        plans = PrettyTable(["Name", "Vms"])
        for plan in config.list_plans():
            planname = plan[0]
            planvms = plan[1]
            plans.add_row([planname, planvms])
        print(plans)
    else:
        if config.client == 'all':
            vms = PrettyTable(["Name", "Hypervisor", "Status", "Ips", "Source", "Description/Plan", "Profile", "Report"])
            for cli in sorted(clis, key=lambda x: x.client):
                for vm in sorted(cli.k.list()):
                    vm.insert(1, cli.client)
                    if filters:
                        status = vm[2]
                        if status == filters:
                            vms.add_row(vm)
                    else:
                        vms.add_row(vm)
            print(vms)
            return
        else:
            vms = PrettyTable(["Name", "Status", "Ips", "Source", "Description/Plan", "Profile", "Report"])
            for vm in sorted(k.list()):
                if filters:
                    status = vm[1]
                    if status == filters:
                        vms.add_row(vm)
                else:
                    vms.add_row(vm)
            print(vms)
            return


def vm(args):
    """Create/Delete/Start/Stop/List vms"""
    name = args.name
    profile = args.profile
    ip1 = args.ip1
    ip2 = args.ip2
    ip3 = args.ip3
    ip4 = args.ip4
    ip5 = args.ip5
    ip6 = args.ip6
    ip7 = args.ip7
    ip8 = args.ip8
    global config
    if profile is None:
        common.pprint("Missing profile", color='red')
        os._exit(1)
    code = config.create_vm(name, profile, ip1=ip1, ip2=ip2, ip3=ip3, ip4=ip4, ip5=ip5, ip6=ip6, ip7=ip7, ip8=ip8)
    os._exit(code)


def clone(args):
    """Clone existing vm"""
    name = args.name
    base = args.base
    full = args.full
    start = args.start
    common.pprint("Cloning vm %s from vm %s..." % (name, base), color='green')
    global config
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
    template = args.template
    global config
    k = config.k
    if ip1 is not None:
        common.pprint("Updating ip of vm %s to %s..." % (name, ip1), color='green')
        k.update_metadata(name, 'ip', ip1)
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
    elif host:
        common.pprint("Creating Host entry for vm %s..." % (name), color='green')
        nets = k.vm_ports(name)
        if domain is None:
            domain = nets[0]
        k.reserve_host(name, nets, domain)
    elif dns:
        common.pprint("Creating Dns entry for vm %s..." % (name), color='green')
        nets = k.vm_ports(name)
        if domain is None:
            domain = nets[0]
        code = k.reserve_dns(name, nets, domain)
        os._exit(code)


def disk(args):
    """Add/Delete disk of vm"""
    name = args.name
    delete = args.delete
    size = args.size
    diskname = args.diskname
    template = args.template
    pool = args.pool
    global config
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
    common.pprint("Adding disk %s to %s..." % (diskname, name), color='green')
    k.add_disk(name=name, size=size, pool=pool, template=template)


def nic(args):
    """Add/Delete nic of vm"""
    name = args.name
    delete = args.delete
    interface = args.interface
    network = args.network
    global config
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
    global config
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
    start = args.start
    stop = args.stop
    delete = args.delete
    delay = args.delay
    global config
    config.plan(plan, ansible=ansible, get=get, path=path, autostart=autostart, container=container, noautostart=noautostart, inputfile=inputfile, start=start, stop=stop, delete=delete, delay=delay)


def ssh(args):
    """Ssh into vm"""
    name = args.name
    l = args.L
    r = args.R
    global config
    k = config.k
    tunnel = config.tunnel
    insecure = config.insecure
    k.ssh(name, local=l, remote=r, tunnel=tunnel, insecure=insecure)


def scp(args):
    """Scp into vm"""
    recursive = args.recursive
    source = args.source
    destination = args.destination
    global config
    k = config.k
    tunnel = config.tunnel
    if len(source.split(':')) == 2:
        name = source.split(':')[0]
        source = source.split(':')[1]
        k.scp(name, source=source, destination=destination, tunnel=tunnel, download=True, recursive=recursive)
    elif len(destination.split(':')) == 2:
        name = destination.split(':')[0]
        destination = destination.split(':')[1]
        k.scp(name, source=source, destination=destination, tunnel=tunnel, download=False, recursive=recursive)


def network(args):
    """Create/Delete/List Network"""
    name = args.name
    delete = args.delete
    isolated = args.isolated
    cidr = args.cidr
    nodhcp = args.nodhcp
    global config
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
        result = k.create_network(name=name, cidr=cidr, dhcp=dhcp, nat=nat)
        common.handle_response(result, name, element='Network ')


def bootstrap(args):
    """Handle hypervisor, reporting or bootstrapping by creating config file and optionally pools and network"""
    genfile = args.genfile
    auto = args.auto
    name = args.name
    host = args.host
    port = args.port
    user = args.user
    protocol = args.protocol
    url = args.url
    pool = args.pool
    poolpath = args.poolpath
    template = args.template
    common.pprint("Bootstrapping env", color='green')
    if genfile or auto:
        if host is None and url is None:
            url = 'qemu:///system'
            host = '127.0.0.1'
        if pool is None:
            pool = 'default'
        if poolpath is None:
            poolpath = '/var/lib/libvirt/images'
        if '/dev' in poolpath:
            pooltype = 'logical'
        else:
            pooltype = 'dir'
        if template:
            template = TEMPLATES['centos']
        else:
            template = None
        nets = {'default': {'cidr': '192.168.122.0/24'}}
        # disks = [{'size': 10}]
        if host == '127.0.0.1':
            ini = {'default': {'client': 'local'}, 'local': {'pool': pool, 'nets': ['default']}}
        else:
            if name is None:
                name = host
            ini = {'default': {'client': name}}
            ini[name] = {'host': host, 'pool': pool, 'nets': ['default']}
            if protocol is not None:
                ini[name]['protocol'] = protocol
            if user is not None:
                ini[name]['user'] = user
            if port is not None:
                ini[name]['port'] = port
            if url is not None:
                ini[name]['url'] = url
    else:
        ini = {'default': {}}
        default = ini['default']
        common.pprint("We will configure kcli together !", color='blue')
        if name is None:
            name = raw_input("Enter your default client name[local]: ") or 'local'
        if pool is None:
            pool = raw_input("Enter your default pool[default]: ") or 'default'
        default['pool'] = pool
        size = raw_input("Enter your client first disk size[10]: ") or '10'
        default['disks'] = [{'size': size}]
        net = raw_input("Enter your client first network[default]: ") or 'default'
        default['nets'] = [net]
        cloudinit = raw_input("Use cloudinit[True]: ") or 'True'
        default['cloudinit'] = cloudinit
        diskthin = raw_input("Use thin disks[True]: ") or 'True'
        default['diskthin'] = diskthin
        ini['default']['client'] = name
        ini[name] = {}
        client = ini[name]
        if host is None:
            host = raw_input("Enter your client hostname/ip[localhost]: ") or 'localhost'
        client['host'] = host
        if url is None:
            url = raw_input("Enter your client url: ") or None
            if url is not None:
                client['url'] = url
            else:
                if protocol is None:
                    protocol = raw_input("Enter your client protocol[ssh]: ") or 'ssh'
                client['protocol'] = protocol
                if port is None:
                    port = raw_input("Enter your client port: ") or None
                    if port is not None:
                        client['port'] = port
                user = raw_input("Enter your client user[root]: ") or 'root'
                client['user'] = user
        pool = raw_input("Enter your client pool[%s]: " % default['pool']) or default['pool']
        client['pool'] = pool
        poolcreate = raw_input("Create pool if not there[Y]: ") or 'Y'
        if poolcreate == 'Y':
            poolpath = raw_input("Enter yourpool path[/var/lib/libvirt/images]: ") or '/var/lib/libvirt/images'
        else:
            poolpath = None
        if poolpath is None:
            pooltype = None
        elif '/dev' in poolpath:
            pooltype = 'logical'
        else:
            pooltype = 'dir'
        client['pool'] = pool
        templatecreate = raw_input("Download centos7 image for you?[N]: ") or 'N'
        if templatecreate == 'Y':
            template = TEMPLATES['centos']
        else:
            template = None
        size = raw_input("Enter your client first disk size[%s]: " % default['disks'][0]['size']) or default['disks'][0]['size']
        client['disks'] = [{'size': size}]
        net = raw_input("Enter your client first network[%s]: " % default['nets'][0]) or default['nets'][0]
        client['nets'] = [net]
        nets = {}
        netcreate = raw_input("Create net if not there[Y]: ") or 'Y'
        if netcreate == 'Y':
            cidr = raw_input("Enter cidr [192.168.122.0/24]: ") or '192.168.122.0/24'
            nets[net] = {'cidr': cidr, 'dhcp': True}
        cloudinit = raw_input("Use cloudinit for this client[%s]: " % default['cloudinit']) or default['cloudinit']
        client['cloudinit'] = cloudinit
        diskthin = raw_input("Use thin disks for this client[%s]: " % default['diskthin']) or default['diskthin']
        client['diskthin'] = diskthin
    k = Kvirt(host=host, port=port, user=user, protocol=protocol, url=url)
    if k.conn is None:
        common.pprint("Couldnt connect to specify hypervisor %s. Leaving..." % host, color='red')
        os._exit(1)
    k.bootstrap(pool=pool, poolpath=poolpath, pooltype=pooltype, nets=nets, image=template)
    path = os.path.expanduser('~/kcli.yml')
    if os.path.exists(path):
        copyfile(path, "%s.bck" % path)
    with open(path, 'w') as conf_file:
        yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    common.pprint("Environment bootstrapped!", color='green')


def container(args):
    """Create/Delete/List containers"""
    name = args.name
    profile = args.profile
    start = args.start
    stop = args.stop
    console = args.console
    global config
    k = config.k
    if start:
        common.pprint("Started container %s..." % name, color='green')
        dockerutils.start_container(k, name)
        return
    if stop:
        common.pprint("Stopped container %s..." % name, color='green')
        dockerutils.stop_container(k, name)
        return
    if console:
        dockerutils.console_container(k, name)
        return
    if profile is None:
        common.pprint("Missing profile", color='red')
        os._exit(1)
    containerprofiles = {k: v for k, v in config.profiles.iteritems() if 'type' in v and v['type'] == 'container'}
    if profile not in containerprofiles:
        common.pprint("profile %s not found. Trying to use the profile as image and default values..." % profile, color='blue')
        dockerutils.create_container(k, name, profile)
        return
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
        dockerutils.create_container(k, name, image, nets=None, cmd=cmd, ports=ports, volumes=volumes, environment=environment)
        return


def snapshot(args):
    """Create/Delete/Revert snapshot"""
    snapshot = args.snapshot
    name = args.name
    revert = args.revert
    delete = args.delete
    listing = args.listing
    global config
    k = config.k
    if revert:
        common.pprint("Reverting snapshot of %s named %s..." % (name, snapshot), color='green')
    elif delete:
        common.pprint("Deleting snapshot of %s named %s..." % (name, snapshot), color='green')
    elif listing:
        common.pprint("Listing snapshots of %s..." % (name), color='green')
        k.snapshot(snapshot, name, listing=True)
        return 0
    elif snapshot is None:
        common.pprint("Missing snapshot name", color='red')
        return 1
    else:
        common.pprint("Creating snapshot of %s named %s..." % (name, snapshot), color='green')
    result = k.snapshot(snapshot, name, revert=revert, delete=delete)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def cli():
    global config
    parser = argparse.ArgumentParser(description='Libvirt/VirtualBox wrapper on steroids. Check out https://github.com/karmab/kcli!')
    parser.add_argument('-C', '--client')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--version', action='version', version=__version__)

    subparsers = parser.add_subparsers(metavar='')

    bootstrap_info = 'Handle hypervisor, reporting or bootstrapping...'
    bootstrap_parser = subparsers.add_parser('bootstrap', help=bootstrap_info, description=bootstrap_info)
    bootstrap_parser.add_argument('-f', '--genfile', action='store_true')
    bootstrap_parser.add_argument('-a', '--auto', action='store_true', help="Don't ask for anything")
    bootstrap_parser.add_argument('-n', '--name', help='Name to use', metavar='CLIENT')
    bootstrap_parser.add_argument('-H', '--host', help='Host to use', metavar='HOST')
    bootstrap_parser.add_argument('-p', '--port', help='Port to use', metavar='PORT')
    bootstrap_parser.add_argument('-u', '--user', help='User to use', default='root', metavar='USER')
    bootstrap_parser.add_argument('-P', '--protocol', help='Protocol to use', default='ssh', metavar='PROTOCOL')
    bootstrap_parser.add_argument('-U', '--url', help='URL to use', metavar='URL')
    bootstrap_parser.add_argument('--pool', help='Pool to use', metavar='POOL')
    bootstrap_parser.add_argument('--poolpath', help='Pool Path to use', metavar='POOLPATH')
    bootstrap_parser.add_argument('-t', '--template', action='store_true', help="Grab Centos Cloud Image")
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
    console_parser.add_argument('name', metavar='VMNAME')
    console_parser.set_defaults(func=console)

    container_info = 'Handle containers'
    container_parser = subparsers.add_parser('container', description=container_info, help=container_info)
    container_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    container_parser.add_argument('-s', '--start', help='Start Container', action='store_true')
    container_parser.add_argument('-w', '--stop', help='Stop Container', action='store_true')
    container_parser.add_argument('-c', '--console', help='Console of the Container', action='store_true')
    container_parser.add_argument('name', metavar='NAME')
    container_parser.set_defaults(func=container)

    delete_info = 'Delete vm/container'
    delete_parser = subparsers.add_parser('delete', description=delete_info, help=delete_info)
    delete_parser.add_argument('--yes', action='store_true', help='Dont ask for confirmation')
    delete_parser.add_argument('--container', action='store_true')
    delete_parser.add_argument('--force', action='store_true', help='Remove snapshots if needed')
    delete_parser.add_argument('name', metavar='VMNAME')
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

    host_info = 'List and Handle host'
    host_parser = subparsers.add_parser('host', description=host_info, help=host_info)
    host_parser.add_argument('-s', '--switch', help='Switch To indicated client', metavar='CLIENT')
    host_parser.add_argument('-r', '--report', help='Report Hypervisor Information', action='store_true')
    host_parser.add_argument('--profiles', help='List Profiles', action='store_true')
    host_parser.add_argument('-t', '--templates', help='List Templates', action='store_true')
    host_parser.add_argument('-i', '--isos', help='List Isos', action='store_true')
    host_parser.add_argument('-d', '--disks', help='List Disks', action='store_true')
    host_parser.add_argument('-p', '--pool', default='default', help='Pool to use when downloading', metavar='POOL')
    host_parser.add_argument('--template', choices=('arch', 'centos6', 'centos7', 'cirros', 'debian8', 'fedora24', 'fedora25', 'gentoo', 'opensuse', 'ubuntu1404', 'ubuntu1604'), help='Template/Image to download')
    host_parser.add_argument('--download', help='Download Template/Image', action='store_true')
    host_parser.set_defaults(func=host)

    info_info = 'Info vm'
    info_parser = subparsers.add_parser('info', description=info_info, help=info_info)
    info_parser.add_argument('name', help='VMNAME')
    info_parser.set_defaults(func=info)

    list_info = 'List clients, profiles, templates, isos,...'
    list_parser = subparsers.add_parser('list', description=list_info, help=list_info)
    list_parser.add_argument('-H', '--hosts', action='store_true')
    list_parser.add_argument('-c', '--clients', action='store_true')
    list_parser.add_argument('-p', '--profiles', action='store_true')
    list_parser.add_argument('-t', '--templates', action='store_true')
    list_parser.add_argument('-i', '--isos', action='store_true')
    list_parser.add_argument('-d', '--disks', action='store_true')
    list_parser.add_argument('-P', '--pools', action='store_true')
    list_parser.add_argument('-n', '--networks', action='store_true')
    list_parser.add_argument('--containers', action='store_true')
    list_parser.add_argument('--short', action='store_true')
    list_parser.add_argument('--plans', action='store_true')
    list_parser.add_argument('-f', '--filters', choices=('up', 'down'))
    list_parser.set_defaults(func=list)

    network_info = 'Create/Delete Network'
    network_parser = subparsers.add_parser('network', description=network_info, help=network_info)
    network_parser.add_argument('-d', '--delete', action='store_true')
    network_parser.add_argument('-i', '--isolated', action='store_true', help='Isolated Network')
    network_parser.add_argument('-c', '--cidr', help='Cidr of the net', metavar='CIDR')
    network_parser.add_argument('--nodhcp', action='store_true', help='Disable dhcp on the net')
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
    plan_parser.add_argument('-g', '--get', help='Download specific plan(s). Use --path for specific directory', metavar='URL')
    plan_parser.add_argument('-p', '--path', default='plans', help='Path where to download plans. Defaults to plan', metavar='PATH')
    plan_parser.add_argument('-a', '--autostart', action='store_true', help='Set all vms from plan to autostart')
    plan_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    plan_parser.add_argument('-n', '--noautostart', action='store_true', help='Prevent all vms from plan to autostart')
    plan_parser.add_argument('-f', '--inputfile', help='Input file')
    plan_parser.add_argument('-s', '--start', action='store_true', help='start all vms from plan')
    plan_parser.add_argument('-w', '--stop', action='store_true')
    plan_parser.add_argument('-d', '--delete', action='store_true')
    plan_parser.add_argument('-t', '--delay', default=0, help="Delay between each vm's creation", metavar='DELAY')
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

    scp_info = 'Scp into vm'
    scp_parser = subparsers.add_parser('scp', description=scp_info, help=scp_info)
    scp_parser.add_argument('-r', '--recursive', help='Recursive', action='store_true')
    scp_parser.add_argument('source', nargs=1)
    scp_parser.add_argument('destination', nargs=1)
    scp_parser.set_defaults(func=scp)

    snapshot_info = 'Create/Delete/Revert snapshot'
    snapshot_parser = subparsers.add_parser('snapshot', description=snapshot_info, help=snapshot_info)
    snapshot_parser.add_argument('-n', '--name', help='Use vm name for creation/revert/delete', required=True, metavar='VMNAME')
    snapshot_parser.add_argument('-r', '--revert', help='Revert to indicated snapshot', action='store_true')
    snapshot_parser.add_argument('-d', '--delete', help='Delete indicated snapshot', action='store_true')
    snapshot_parser.add_argument('-l', '--listing', help='List snapshots', action='store_true')
    snapshot_parser.add_argument('snapshot', nargs='?')
    snapshot_parser.set_defaults(func=snapshot)

    ssh_info = 'Ssh into vm'
    ssh_parser = subparsers.add_parser('ssh', description=ssh_info, help=ssh_info)
    ssh_parser.add_argument('-L', help='Local Forwarding', metavar='LOCAL')
    ssh_parser.add_argument('-R', help='Remote Forwarding', metavar='REMOTE')
    ssh_parser.add_argument('name', metavar='VMNAME')
    ssh_parser.set_defaults(func=ssh)

    start_info = 'Start vm/container'
    start_parser = subparsers.add_parser('start', description=start_info, help=start_info)
    start_parser.add_argument('-c', '--container', action='store_true')
    start_parser.add_argument('name')
    start_parser.set_defaults(func=start)

    stop_info = 'Stop vm/container'
    stop_parser = subparsers.add_parser('stop', description=stop_info, help=stop_info)
    stop_parser.add_argument('-c', '--container', action='store_true')
    stop_parser.add_argument('name', metavar='VMNAME')
    stop_parser.set_defaults(func=stop)

    update_info = 'Update ip, memory or numcpus'
    update_parser = subparsers.add_parser('update', description=update_info, help=update_info)
    update_parser.add_argument('-1', '--ip1', help='Ip to set', metavar='IP1')
    update_parser.add_argument('-m', '--memory', help='Memory to set', metavar='MEMORY')
    update_parser.add_argument('-c', '--numcpus', help='Number of cpus to set', metavar='NUMCPUS')
    update_parser.add_argument('-p', '--plan', help='Plan Name to set', metavar='PLAN')
    update_parser.add_argument('-a', '--autostart', action='store_true', help='Set VM to autostart')
    update_parser.add_argument('-n', '--noautostart', action='store_true', help='Prevent VM from autostart')
    update_parser.add_argument('--dns', action='store_true', help='Update Dns entry for the vm')
    update_parser.add_argument('--host', action='store_true', help='Update Host entry for the vm')
    update_parser.add_argument('-d', '--domain', help='Domain', metavar='DOMAIN')
    update_parser.add_argument('-t', '--template', help='Template to set', metavar='TEMPLATE')
    update_parser.add_argument('name', metavar='VMNAME')
    update_parser.set_defaults(func=update)

    vm_info = 'Create/Delete/Start/Stop vm'
    vm_parser = subparsers.add_parser('vm', description=vm_info, help=vm_info)
    vm_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    vm_parser.add_argument('-1', '--ip1', help='Optional Ip to assign to eth0. Netmask and gateway will be retrieved from profile', metavar='IP1')
    vm_parser.add_argument('-2', '--ip2', help='Optional Ip to assign to eth1. Netmask and gateway will be retrieved from profile', metavar='IP2')
    vm_parser.add_argument('-3', '--ip3', help='Optional Ip to assign to eth2. Netmask and gateway will be retrieved from profile', metavar='IP3')
    vm_parser.add_argument('-4', '--ip4', help='Optional Ip to assign to eth3. Netmask and gateway will be retrieved from profile', metavar='IP4')
    vm_parser.add_argument('-5', '--ip5', help='Optional Ip to assign to eth4. Netmask and gateway will be retrieved from profile', metavar='IP5')
    vm_parser.add_argument('-6', '--ip6', help='Optional Ip to assign to eth5. Netmask and gateway will be retrieved from profile', metavar='IP6')
    vm_parser.add_argument('-7', '--ip7', help='Optional Ip to assign to eth6. Netmask and gateway will be retrieved from profile', metavar='IP7')
    vm_parser.add_argument('-8', '--ip8', help='Optional Ip to assign to eth8. Netmask and gateway will be retrieved from profile', metavar='IP8')
    vm_parser.add_argument('name', metavar='VMNAME')
    vm_parser.set_defaults(func=vm)
    args = parser.parse_args()
    config = Kconfig(client=args.client, debug=args.debug)
    args.func(args)

if __name__ == '__main__':
    cli()
