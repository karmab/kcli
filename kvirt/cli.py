#!/usr/bin/env python

import click
import fileinput
from .defaults import NETS, POOL, NUMCPUS, MEMORY, DISKS, DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID, VNC, CLOUDINIT, RESERVEIP, START, TEMPLATES
from prettytable import PrettyTable
from kvirt import Kvirt, __version__
import os
from time import sleep
import yaml
from shutil import copyfile

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def handle_response(result, name, element='', action='deployed'):
    if result['result'] == 'success':
        click.secho("%s%s %s!" % (element, name, action), fg='green')
    else:
        reason = result['reason']
        click.secho("%s%s not %s because %s" % (element, name, action, reason), fg='red')


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


class Config():
    def load(self):
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            ini = {'default': {'client': 'local'}, 'local': {'pool': 'default'}}
            click.secho("Using local hypervisor as no kcli.yml was found...", fg='green')
        else:
            with open(inifile, 'r') as entries:
                try:
                    ini = yaml.load(entries)
                except:
                    self.host = None
                    return
            if 'default' not in ini or 'client' not in ini['default']:
                click.secho("Missing default section in config file. Leaving...", fg='red')
                self.host = None
                return
        self.clients = [e for e in ini if e != 'default']
        self.client = ini['default']['client']
        if self.client not in ini:
            click.secho("Missing section for client %s in config file. Leaving..." % self.client, fg='red')
            self.host = None
            return
        defaults = {}
        default = ini['default']
        defaults['nets'] = default.get('nets', NETS)
        defaults['pool'] = default.get('pool', POOL)
        defaults['numcpus'] = int(default.get('numcpus', NUMCPUS))
        defaults['memory'] = int(default.get('memory', MEMORY))
        defaults['disks'] = default.get('disks', DISKS)
        defaults['disksize'] = default.get('disksize', DISKSIZE)
        defaults['diskinterface'] = default.get('diskinterface', DISKINTERFACE)
        defaults['diskthin'] = default.get('diskthin', DISKTHIN)
        defaults['guestid'] = default.get('guestid', GUESTID)
        defaults['vnc'] = bool(default.get('vnc', VNC))
        defaults['cloudinit'] = bool(default.get('cloudinit', CLOUDINIT))
        defaults['reserveip'] = bool(default.get('reserveip', RESERVEIP))
        defaults['start'] = bool(default.get('start', START))
        self.default = defaults
        options = ini[self.client]
        self.host = options.get('host', '127.0.0.1')
        self.port = options.get('port', None)
        self.user = options.get('user', 'root')
        self.protocol = options.get('protocol', 'ssh')
        self.url = options.get('url', None)
        profilefile = "%s/kcli_profiles.yml" % os.environ.get('HOME')
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                self.profiles = yaml.load(entries)

    def get(self):
        if self.host is None:
            click.secho("Problem parsing your configuration file", fg='red')
            os._exit(1)
        k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url)
        if k.conn is None:
            click.secho("Couldnt connect to specify hypervisor %s. Leaving..." % self.host, fg='red')
            os._exit(1)
        return k

pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@pass_config
def cli(config):
    """Libvirt wrapper on steroids. Check out https://github.com/karmab/kcli!"""
    config.load()


@cli.command()
@click.argument('name')
@pass_config
def start(config, name):
    """Start vm"""
    k = config.get()
    click.secho("Started vm %s..." % name, fg='green')
    result = k.start(name)
    handle_response(result, name, element='', action='started')


@cli.command()
@click.argument('name')
@pass_config
def stop(config, name):
    """Stop vm"""
    k = config.get()
    click.secho("Stopped vm %s..." % name, fg='green')
    result = k.stop(name)
    handle_response(result, name, element='', action='stopped')


@cli.command()
@click.option('-s', '--serial', is_flag=True)
@click.argument('name')
@pass_config
def console(config, serial, name):
    """Vnc/Spice/Serial console"""
    k = config.get()
    if serial:
        k.serialconsole(name)
    else:
        k.console(name)


@cli.command()
@click.confirmation_option(help='Are you sure?')
@click.argument('name')
@pass_config
def delete(config, name):
    """Delete vm"""
    k = config.get()
    click.secho("Deleted vm %s..." % name, fg='red')
    k.delete(name)


@cli.command()
@click.argument('client')
@pass_config
def switch(config, client):
    """Switch from a client to another"""
    if client not in config.clients:
        click.secho("Client %s not found in config.Leaving...." % client, fg='green')
        os._exit(1)
    click.secho("Switching to client %s..." % client, fg='green')
    inifile = "%s/kcli.yml" % os.environ.get('HOME')
    if os.path.exists(inifile):
        for line in fileinput.input(inifile, inplace=True):
            if 'client' in line:
                print(" client: %s" % client)
            else:
                print(line.rstrip())


@cli.command()
@click.option('-c', '--clients', is_flag=True)
@click.option('-p', '--profiles', is_flag=True)
@click.option('-t', '--templates', is_flag=True)
@click.option('-i', '--isos', is_flag=True)
@click.option('-d', '--disks', is_flag=True)
@click.option('-P', '--pools', is_flag=True)
@click.option('-n', '--networks', is_flag=True)
@click.option('-f', '--filters', type=click.Choice(['up', 'down']))
@pass_config
def list(config, clients, profiles, templates, isos, disks, pools, networks, filters):
    """List clients, profiles, templates, isos, pools or vms"""
    k = config.get()
    if pools:
        pools = k.list_pools()
        for pool in sorted(pools):
            print(pool)
        return
    if networks:
        networks = k.list_networks()
        click.secho("Listing Networks...", fg='green')
        networkstable = PrettyTable(["Name", "Type", "Cidr", "Dhcp", "Mode"])
        networkstable.align["Name"] = "l"
        for network in sorted(networks):
            networktype = networks[network]['type']
            cidr = networks[network]['cidr']
            dhcp = networks[network]['dhcp']
            mode = networks[network]['mode']
            networkstable.add_row([network, networktype, cidr, dhcp, mode])
        print networkstable
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
        for profile in sorted(config.profiles):
            print(profile)
    elif templates:
        for template in sorted(k.volumes()):
            print(template)
    elif isos:
        for iso in sorted(k.volumes(iso=True)):
            print(iso)
    elif disks:
        click.secho("Listing disks...", fg='green')
        diskstable = PrettyTable(["Name", "Pool", "Path"])
        diskstable.align["Name"] = "l"
        k = config.get()
        disks = k.list_disks()
        for disk in sorted(disks):
            path = disks[disk]['path']
            pool = disks[disk]['pool']
            diskstable.add_row([disk, pool, path])
        print diskstable
    else:
        vms = PrettyTable(["Name", "Status", "Ips", "Source", "Description/Plan", "Profile"])
        for vm in sorted(k.list()):
            if filters:
                status = vm[1]
                if status == filters:
                    vms.add_row(vm)
            else:
                vms.add_row(vm)
        print(vms)


@cli.command()
@click.option('-p', '--profile', help='Profile to use')
@click.option('-1', '--ip1', help='Optional Ip to assign to eth0. Netmask and gateway will be retrieved from profile')
@click.option('-2', '--ip2', help='Optional Ip to assign to eth1. Netmask and gateway will be retrieved from profile')
@click.option('-3', '--ip3', help='Optional Ip to assign to eth2. Netmask and gateway will be retrieved from profile')
@click.option('-4', '--ip4', help='Optional Ip to assign to eth3. Netmask and gateway will be retrieved from profile')
@click.option('-5', '--ip5', help='Optional Ip to assign to eth4. Netmask and gateway will be retrieved from profile')
@click.option('-6', '--ip6', help='Optional Ip to assign to eth5. Netmask and gateway will be retrieved from profile')
@click.option('-7', '--ip7', help='Optional Ip to assign to eth6. Netmask and gateway will be retrieved from profile')
@click.option('-8', '--ip8', help='Optional Ip to assign to eth8. Netmask and gateway will be retrieved from profile')
@click.argument('name')
@pass_config
def create(config, profile, ip1, ip2, ip3, ip4, ip5, ip6, ip7, ip8, name):
    """Create vm from given profile"""
    click.secho("Deploying vm %s from profile %s..." % (name, profile), fg='green')
    k = config.get()
    default = config.default
    profiles = config.profiles
    if profile not in profiles:
        click.secho("Invalid profile %s. Leaving..." % profile, fg='red')
        os._exit(1)
    title = profile
    profile = profiles[profile]
    template = profile.get('template')
    description = 'kvirt'
    nets = profile.get('nets', default['nets'])
    numcpus = profile.get('numcpus', default['numcpus'])
    memory = profile.get('memory', default['memory'])
    pool = profile.get('pool', default['pool'])
    disks = profile.get('disks', default['disks'])
    disksize = profile.get('disksize', default['disksize'])
    diskinterface = profile.get('diskinterface', default['diskinterface'])
    diskthin = profile.get('diskthin', default['diskthin'])
    guestid = profile.get('guestid', default['guestid'])
    iso = profile.get('iso')
    vnc = profile.get('vnc', default['vnc'])
    cloudinit = profile.get('cloudinit', default['cloudinit'])
    reserveip = profile.get('reserveip', default['reserveip'])
    start = profile.get('start', default['start'])
    keys = profile.get('keys', None)
    cmds = profile.get('cmds', None)
    netmasks = profile.get('netmasks')
    gateway = profile.get('gateway')
    dns = profile.get('dns')
    domain = profile.get('domain')
    scripts = profile.get('scripts')
    if scripts is not None:
        scriptcmds = []
        for script in scripts:
            script = os.path.expanduser(script)
            if not os.path.exists(script):
                click.secho("Script %s not found.Ignoring..." % script, fg='red')
            else:
                scriptlines = [line.strip() for line in open(script).readlines() if line != '\n']
                if scriptlines:
                    scriptcmds.extend(scriptlines)
        if scriptcmds:
            if cmds is None:
                cmds = scriptcmds
            else:
                cmds = cmds + scriptcmds
    ips = [ip1, ip2, ip3, ip4, ip5, ip6, ip7, ip8]
    result = k.create(name=name, description=description, title=title, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), reserveip=bool(reserveip), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain)
    handle_response(result, name)


@cli.command()
@click.option('-b', '--base', help='Base VM')
@click.option('-f', '--full', is_flag=True)
@click.option('-s', '--start', is_flag=True, help='Start cloned VM')
@click.argument('name')
@pass_config
def clone(config, base, full, start, name):
    """Clone existing vm"""
    click.secho("Cloning vm %s from vm %s..." % (name, base), fg='green')
    k = config.get()
    k.clone(base, name, full=full, start=start)


@cli.command()
@click.option('-1', '--ip', help='Ip to set')
@click.option('-m', '--memory', help='Memory to set')
@click.option('-c', '--numcpus', help='Number of cpus to set')
@click.option('-a', '--autostart', is_flag=True, help='Set VM to autostart')
@click.option('-n', '--noautostart', is_flag=True, help='Prevent VM from autostart')
@click.argument('name')
@pass_config
def update(config, ip, memory, numcpus, autostart, noautostart, name):
    """Update ip, memory or numcpus"""
    k = config.get()
    if ip is not None:
        click.secho("Updating ip of vm %s to %s..." % (name, ip), fg='green')
        k.update_ip(name, ip)
    elif memory is not None:
        click.secho("Updating memory of vm %s to %s..." % (name, memory), fg='green')
        k.update_memory(name, memory)
    elif numcpus is not None:
        click.secho("Updating numcpus of vm %s to %s..." % (name, numcpus), fg='green')
        k.update_cpu(name, numcpus)
    elif autostart:
        click.secho("Setting autostart for vm %s..." % (name), fg='green')
        k.update_start(name, start=True)
    elif noautostart:
        click.secho("Removing autostart for vm %s..." % (name), fg='green')
        k.update_start(name, start=False)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-s', '--size', help='Size of the disk to add, in GB')
@click.option('-n', '--diskname', help='Name or Path of the disk, when deleting')
@click.option('-t', '--template', help='Name or Path of a Template, when adding')
@click.option('-p', '--pool', help='Pool')
@click.argument('name')
@pass_config
def disk(config, delete, size, diskname, template, pool, name):
    """Add/Delete disk of vm"""
    if delete:
        if diskname is None:
            click.secho("Missing diskname. Leaving...", fg='red')
            os._exit(1)
        click.secho("Deleting disk %s from %s..." % (diskname, name), fg='green')
        k = config.get()
        k.delete_disk(name, diskname)
        return
    if size is None:
        click.secho("Missing size. Leaving...", fg='red')
        os._exit(1)
    if pool is None:
        click.secho("Missing pool. Leaving...", fg='red')
        os._exit(1)
    k = config.get()
    click.secho("Adding disk %s..." % (name), fg='green')
    k.add_disk(name=name, size=size, pool=pool, template=template)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-i', '--interface', help='Name of the interface, when deleting')
@click.option('-n', '--network', help='Network')
@click.argument('name')
@pass_config
def nic(config, delete, interface, network, name):
    """Add/Delete nic of vm"""
    if delete:
        click.secho("Deleting nic from %s..." % (name), fg='green')
        k = config.get()
        k.delete_nic(name, interface)
        return
    if network is None:
        click.secho("Missing network. Leaving...", fg='red')
        os._exit(1)
    k = config.get()
    click.secho("Adding Nic %s..." % (name), fg='green')
    k.add_nic(name=name, network=network)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-f', '--full', is_flag=True)
@click.option('-t', '--pooltype', help='Type of the pool', type=click.Choice(['dir', 'logical']), default='dir')
@click.option('-p', '--path', help='Path of the pool')
@click.argument('pool')
@pass_config
def pool(config, delete, full, pooltype, path, pool):
    """Create/Delete pool"""
    k = config.get()
    if delete:
        click.secho("Deleting pool %s..." % (pool), fg='green')
        k.delete_pool(name=pool, full=full)
        return
    if path is None:
        click.secho("Missing path. Leaving...", fg='red')
        return
    click.secho("Adding pool %s..." % (pool), fg='green')
    k.create_pool(name=pool, poolpath=path, pooltype=pooltype)


@cli.command()
@pass_config
def report(config):
    """Report hypervisor setup"""
    click.secho("Reporting setup for client %s..." % config.client, fg='green')
    k = config.get()
    k.report()


@cli.command()
@click.option('-a', '--autostart', is_flag=True, help='Set all vms from plan to autostart')
@click.option('-n', '--noautostart', is_flag=True, help='Prevent all vms from plan to autostart')
@click.option('-f', '--inputfile', help='Input file')
@click.option('-s', '--start', is_flag=True, help='start all vms from plan')
@click.option('-w', '--stop', is_flag=True)
@click.option('-d', '--delete', is_flag=True)
@click.option('-t', '--delay', default=0, help="Delay between each vm's creation")
@click.argument('plan', required=False)
@pass_config
def plan(config, autostart, noautostart, inputfile, start, stop, delete, time, plan):
    """Create/Delete/Stop/Start vms from plan file"""
    if plan is None:
        plan = 'kvirt'
    k = config.get()
    if delete:
        if plan == '':
            click.secho("That would delete every vm...Not doing that", fg='red')
            return
        click.confirm('Are you sure about deleting plan %s' % plan, abort=True)
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.delete(name)
                click.secho("%s deleted!" % name, fg='green')
        click.secho("Plan %s deleted!" % plan, fg='green')
        return
    if autostart:
        click.secho("Set vms from plan %s to autostart" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.update_start(name, start=True)
                click.secho("%s set to autostart!" % name, fg='green')
        return
    if noautostart:
        click.secho("Preventing vms from plan %s to autostart" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.update_start(name, start=False)
                click.secho("%s prevented to autostart!" % name, fg='green')
        return
    if start:
        click.secho("Starting vms from plan %s" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.start(name)
                click.secho("%s started!" % name, fg='green')
        click.secho("Plan %s started!" % plan, fg='green')
        return
    if stop:
        click.secho("Stopping vms from plan %s" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.stop(name)
                click.secho("%s stopped!" % name, fg='green')
        click.secho("Plan %s stopped!" % plan, fg='green')
        return
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
        click.secho("using default input file kcli_plan.yml", fg='green')
    inputfile = os.path.expanduser(inputfile)
    if not os.path.exists(inputfile):
        click.secho("No input file found nor default kcli_plan.yml.Leaving....", fg='red')
        os._exit(1)
    default = config.default
    with open(inputfile, 'r') as entries:
        entries = yaml.load(entries)
        vmentries = [entry for entry in entries if 'type' not in entries[entry] or entries[entry]['type'] == 'vm']
        diskentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'disk']
        networkentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'network']
        if networkentries:
            click.secho("Deploying Networks...", fg='green')
        for net in networkentries:
            profile = entries[net]
            if k.net_exists(net):
                click.secho("%s skipped!" % net, fg='blue')
                continue
            cidr = profile.get('cidr')
            nat = bool(profile.get('nat', True))
            if cidr is None:
                print "Missing Cidr for network %s. Not creating it..." % net
                continue
            dhcp = profile.get('dhcp', True)
            result = k.create_network(name=net, cidr=cidr, dhcp=dhcp, nat=nat)
            handle_response(result, net, element='Network ')
        if vmentries:
            click.secho("Deploying Vms...", fg='green')
            for name in vmentries:
                profile = entries[name]
                if k.exists(name):
                    click.secho("%s skipped!" % name, fg='blue')
                    continue
                if 'profile' in profile.keys():
                    profiles = config.profiles
                    customprofile = profiles[profile['profile']]
                    title = profile['profile']
                else:
                    customprofile = {}
                    title = plan
                description = plan
                pool = next((e for e in [profile.get('pool'), customprofile.get('pool'), default['pool']] if e is not None))
                template = next((e for e in [profile.get('template'), customprofile.get('template')] if e is not None), None)
                numcpus = next((e for e in [profile.get('numcpus'), customprofile.get('numcpus'), default['numcpus']] if e is not None))
                memory = next((e for e in [profile.get('memory'), customprofile.get('memory'), default['memory']] if e is not None))
                disks = next((e for e in [profile.get('disks'), customprofile.get('disks'), default['disks']] if e is not None))
                disksize = next((e for e in [profile.get('disksize'), customprofile.get('disksize'), default['disksize']] if e is not None))
                diskinterface = next((e for e in [profile.get('diskinterface'), customprofile.get('diskinterface'), default['diskinterface']] if e is not None))
                diskthin = next((e for e in [profile.get('diskthin'), customprofile.get('diskthin'), default['diskthin']] if e is not None))
                guestid = next((e for e in [profile.get('guestid'), customprofile.get('guestid'), default['guestid']] if e is not None))
                vnc = next((e for e in [profile.get('vnc'), customprofile.get('vnc'), default['vnc']] if e is not None))
                cloudinit = next((e for e in [profile.get('cloudinit'), customprofile.get('cloudinit'), default['cloudinit']] if e is not None))
                reserveip = next((e for e in [profile.get('reserveip'), customprofile.get('reserveip'), default['reserveip']] if e is not None))
                start = next((e for e in [profile.get('start'), customprofile.get('start'), default['start']] if e is not None))
                nets = next((e for e in [profile.get('nets'), customprofile.get('nets'), default['nets']] if e is not None))
                iso = next((e for e in [profile.get('iso'), customprofile.get('iso')] if e is not None), None)
                keys = next((e for e in [profile.get('keys'), customprofile.get('keys')] if e is not None), None)
                cmds = next((e for e in [profile.get('cmds'), customprofile.get('cmds')] if e is not None), None)
                netmasks = next((e for e in [profile.get('netmasks'), customprofile.get('netmasks')] if e is not None), None)
                gateway = next((e for e in [profile.get('gateway'), customprofile.get('gateway')] if e is not None), None)
                dns = next((e for e in [profile.get('dns'), customprofile.get('dns')] if e is not None), None)
                domain = next((e for e in [profile.get('domain'), customprofile.get('domain')] if e is not None), None)
                ips = profile.get('ips')
                scripts = next((e for e in [profile.get('scripts'), customprofile.get('scripts')] if e is not None), None)
                if scripts is not None:
                    scriptcmds = []
                    for script in scripts:
                        script = os.path.expanduser(script)
                        if not os.path.exists(script):
                            click.secho("Script %s not found.Ignoring..." % script, fg='red')
                        else:
                            scriptlines = [line.strip() for line in open(script).readlines() if line != '\n']
                            if scriptlines:
                                scriptcmds.extend(scriptlines)
                    if scriptcmds:
                        if cmds is None:
                            cmds = scriptcmds
                        else:
                            cmds = cmds + scriptcmds
                result = k.create(name=name, description=description, title=title, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), reserveip=bool(reserveip), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain)
                handle_response(result, name)
                if time > 0:
                    sleep(time)
        if diskentries:
            click.secho("Deploying Disks...", fg='green')
        for disk in diskentries:
            profile = entries[disk]
            pool = profile.get('pool')
            vms = profile.get('vms')
            template = profile.get('template')
            size = int(profile.get('size', 10))
            if pool is None:
                print "Missing Key Pool for disk section %s. Not creating it..." % disk
                continue
            if vms is None:
                print "Missing or Incorrect Key Vms for disk section %s. Not creating it..." % disk
                continue
            if k.disk_exists(pool, disk):
                click.secho("Disk %s skipped!" % disk, fg='blue')
                continue
            if len(vms) > 1:
                shareable = True
            else:
                shareable = False
            newdisk = k.create_disk(disk, size=size, pool=pool, template=template, thin=False)
            click.secho("Disk %s deployed!" % disk, fg='green')
            for vm in vms:
                k.add_disk(name=vm, size=size, pool=pool, template=template, shareable=shareable, existing=newdisk, thin=False)


@cli.command()
@click.argument('name')
@pass_config
def info(config, name):
    """Info about vm"""
    k = config.get()
    k.info(name)


@cli.command()
@click.argument('name')
@pass_config
def ssh(config, name):
    """Ssh into vm"""
    k = config.get()
    k.ssh(name)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-i', '--isolated', is_flag=True, help='Isolated Network')
@click.option('-c', '--cidr', help='Cidr of the net')
@click.option('--dhcp', is_flag=True, help='Enable dhcp on the net')
@click.argument('name')
@pass_config
def network(config, delete, isolated, cidr, dhcp, name):
    """Create Network"""
    k = config.get()
    if delete:
        result = k.delete_network(name=name)
        handle_response(result, name, element='Network ', action='deleted')
    else:
        if isolated:
            nat = False
        else:
            nat = True
        result = k.create_network(name=name, cidr=cidr, dhcp=dhcp, nat=nat)
        handle_response(result, name, element='Network ')


@cli.command()
@click.option('-f', '--genfile', is_flag=True)
@click.option('-a', '--auto', is_flag=True, help="Don't ask for anything")
@click.option('-n', '--name', help='Name to use')
@click.option('-H', '--host', help='Host to use')
@click.option('-p', '--port', help='Port to use')
@click.option('-u', '--user', help='User to use', default='root')
@click.option('-P', '--protocol', help='Protocol to use', default='ssh')
@click.option('-U', '--url', help='URL to use')
@click.option('--pool', help='Pool to use')
@click.option('--poolpath', help='Pool Path to use')
@click.option('-t', '--template', is_flag=True, help="Grab Centos Cloud Image")
def bootstrap(genfile, auto, name, host, port, user, protocol, url, pool, poolpath, template):
    """Bootstrap hypervisor, creating config file and optionally pools and network"""
    click.secho("Bootstrapping env", fg='green')
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
        nets = {'default': {'cidr': '192.168.122.0/24'}, 'cinet': {'cidr': '192.168.5.0/24'}}
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
        click.secho("We will configure kcli together !", fg='blue')
        if name is None:
            name = raw_input("Enter your default client name[local]: ") or 'local'
            client = name
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
        ini['default']['client'] = client
        ini[client] = {}
        client = ini[client]
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
        cinetcreate = raw_input("Create cinet network for uci demos if not there[N]") or 'N'
        if cinetcreate == 'Y':
            nets['cinet'] = {'cidr': '192.168.5.0/24', 'dhcp': True}
        cloudinit = raw_input("Use cloudinit for this client[%s]: " % default['cloudinit']) or default['cloudinit']
        client['cloudinit'] = cloudinit
        diskthin = raw_input("Use thin disks for this client[%s]: " % default['diskthin']) or default['diskthin']
        client['diskthin'] = diskthin
    k = Kvirt(host=host, port=port, user=user, protocol=protocol, url=url)
    if k.conn is None:
        click.secho("Couldnt connect to specify hypervisor %s. Leaving..." % host, fg='red')
        os._exit(1)
    k.bootstrap(pool=pool, poolpath=poolpath, pooltype=pooltype, nets=nets, template=template)
    # TODO:
    # DOWNLOAD CIRROS ( AND CENTOS7? ) IMAGES TO POOL ?
    path = os.path.expanduser('~/kcli.yml')
    if os.path.exists(path):
        copyfile(path, "%s.bck" % path)
    with open(path, 'w') as conf_file:
        yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    click.secho("Environment bootstrapped!", fg='green')


@cli.command()
@click.option('-p', '--pool', help='Pool to use')
@click.option('-t', '--template', type=click.Choice(['centos', 'fedora', 'debian', 'ubuntu', 'cirros']), help='Template/Image to grab from internet')
@pass_config
def download(config, pool, template):
    """Download cloud template and upload it to specified pool"""
    if pool is None:
        click.secho("Missing pool.Leaving...", fg='red')
        return
    if template is None:
        click.secho("Missing template.Leaving...", fg='red')
        return
    k = config.get()
    click.secho("Handling template %s..." % template, fg='green')
    template = TEMPLATES[template]
    shortname = os.path.basename(template)
    result = k.add_image(template, pool)
    handle_response(result, shortname, element='Template ', action='Added')


if __name__ == '__main__':
    cli()
