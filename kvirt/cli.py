#!/usr/bin/env python

import click
import fileinput
from defaults import NETS, POOL, NUMCPUS, MEMORY, DISKS, DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID, VNC, CLOUDINIT, START, EMULATOR
from prettytable import PrettyTable
from kvirt import Kvirt, __version__
import os
import yaml

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class Config():
    def load(self):
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            ini = {'default': {'client': 'local'}, 'local': {'pool': 'default'}}
            click.secho("Using local hypervisor as no kcli.yml was found...", fg='green')
        else:
            with open(inifile, 'r') as entries:
                ini = yaml.load(entries)
            if 'default' not in ini or 'client' not in ini['default']:
                click.secho("Missing default section in config file. Leaving...", fg='red')
                os._exit(1)
        self.clients = [e for e in ini if e != 'default']
        self.client = ini['default']['client']
        if self.client not in ini:
            click.secho("Missing section for client %s in config file. Leaving..." % self.client, fg='red')
            os._exit(1)
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
        defaults['start'] = bool(default.get('start', START))
        defaults['emulator'] = default.get('emulator', EMULATOR)
        self.default = defaults
        options = ini[self.client]
        host = options.get('host', '127.0.0.1')
        port = options.get('port', None)
        user = options.get('user', 'root')
        protocol = options.get('protocol', 'ssh')
        self.k = Kvirt(host=host, port=port, user=user, protocol=protocol)
        if self.k.conn is None:
            click.secho("Couldnt connect to specify hypervisor %s. Leaving..." % host, fg='red')
            os._exit(1)
        profilefile = "%s/kcli_profiles.yml" % os.environ.get('HOME')
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                self.profiles = yaml.load(entries)

pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@pass_config
def cli(config):
    """ Libvirt wrapper on steroids. Check out https://github.com/karmab/kcli!"""
    config.load()


@cli.command()
@click.argument('name')
@pass_config
def start(config, name):
    k = config.k
    click.secho("Started vm %s..." % name, fg='green')
    k.start(name)


@cli.command()
@click.argument('name')
@pass_config
def stop(config, name):
    k = config.k
    click.secho("Stopped vm %s..." % name, fg='green')
    k.stop(name)


@cli.command()
@click.option('-s', '--serial', is_flag=True)
@click.argument('name')
@pass_config
def console(config, serial, name):
    k = config.k
    if serial:
        k.serialconsole(name)
    else:
        k.console(name)


@cli.command()
@click.confirmation_option(help='Are you sure?')
@click.argument('name')
@pass_config
def delete(config, name):
    k = config.k
    click.secho("Deleted vm %s..." % name, fg='red')
    k.delete(name)


@cli.command()
@click.argument('client')
@pass_config
def switch(config, client):
    # k = config.k
    if client not in config.clients:
        click.secho("Client %s not found in config.Leaving...." % client, fg='green')
        os._exit(1)
    click.secho("Switching to client %s..." % client, fg='green')
    inifile = "%s/kcli.yml" % os.environ.get('HOME')
    if os.path.exists(inifile):
        for line in fileinput.input(inifile, inplace=True):
            if 'client' in line:
                print " client: %s" % client
            else:
                print line.rstrip()


@cli.command()
@click.option('-c', '--clients', is_flag=True)
@click.option('-p', '--profiles', is_flag=True)
@click.option('-t', '--templates', is_flag=True)
@click.option('-i', '--isos', is_flag=True)
@pass_config
def list(config, clients, profiles, templates, isos):
    k = config.k
    if clients:
        clientstable = PrettyTable(["Name", "Current"])
        clientstable.align["Name"] = "l"
        for client in sorted(config.clients):
            if client == config.client:
                clientstable.add_row([client, 'X'])
            else:
                clientstable.add_row([client, ''])
        print clientstable
    elif profiles:
        for profile in sorted(config.profiles):
            print profile
    elif templates:
        for template in sorted(k.volumes()):
            print template
    elif isos:
        for iso in sorted(k.volumes(iso=True)):
            print iso
    else:
        vms = PrettyTable(["Name", "Status", "Ips", "Source", "Description/Plan", "Profile"])
        for vm in sorted(k.list()):
            vms.add_row(vm)
        print vms


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
    click.secho("Deploying vm %s from profile %s..." % (name, profile), fg='green')
    k = config.k
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
    start = profile.get('start', default['start'])
    keys = profile.get('keys', None)
    cmds = profile.get('cmds', None)
    netmasks = profile.get('netmasks')
    gateway = profile.get('gateway')
    dns = profile.get('dns')
    domain = profile.get('domain')
    scripts = profile.get('scripts')
    emulator = profile.get('emulator', default['emulator'])
    k.emulator = emulator
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
            cmds = scriptcmds
    ips = [ip1, ip2, ip3, ip4, ip5, ip6, ip7, ip8]
    result = k.create(name=name, description=description, title=title, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain)
    if result == 0:
        click.secho("%s deployed!" % name, fg='green')
    else:
        click.secho("%s not deployed! :(" % name, fg='green')


@cli.command()
@click.option('-b', '--base', help='Base template')
@click.option('-f', '--full', is_flag=True)
@click.argument('name')
@pass_config
def clone(config, base, full, name):
    click.secho("Cloning vm %s from vm %s..." % (name, base), fg='green')
    k = config.k
    k.clone(base, name, full)


@cli.command()
@click.option('-1', '--ip', help='Ip to set')
@click.option('-m', '--memory', help='Memory to set')
@click.option('-c', '--numcpus', help='Number of cpus to set')
@click.argument('name')
@pass_config
def update(config, ip, memory, numcpus, name):
    k = config.k
    if ip is not None:
        click.secho("Updating ip of vm %s to %s..." % (name, ip), fg='green')
        k.update_ip(name, ip)
    elif memory is not None:
        click.secho("Updating memory of vm %s to %s..." % (name, memory), fg='green')
        k.update_memory(name, memory)
    elif numcpus is not None:
        click.secho("Updating numcpus of vm %s to %s..." % (name, numcpus), fg='green')
        k.update_cpu(name, numcpus)


@cli.command()
@click.option('-s', '--size', help='Size of the disk to add, in GB')
@click.option('-p', '--pool', help='Pool')
@click.argument('name')
@pass_config
def add(config, size, pool, name):
    if size is None:
        click.secho("Missing size. Leaving...", fg='red')
        os._exit(1)
    k = config.k
    click.secho("Adding disk %s..." % (name), fg='green')
    k.add_disk(name=name, size=size, pool=pool)


@cli.command()
@pass_config
def report(config):
    click.secho("Reporting setup for client %s..." % config.client, fg='green')
    k = config.k
    k.report()


@cli.command()
@click.option('-f', '--inputfile', help='Input file')
@click.option('-s', '--start', is_flag=True)
@click.option('-w', '--stop', is_flag=True)
@click.option('-d', '--delete', is_flag=True)
@click.argument('plan', required=False)
@pass_config
def plan(config, inputfile, start, stop, delete, plan):
    if plan is None:
        plan = 'kvirt'
    k = config.k
    if delete:
        if plan == '':
            click.secho("That would delete every vm...Not doing that", fg='red')
            return
        click.confirm('Are you sure about deleting this plan', abort=True)
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.delete(name)
                click.secho("%s deleted!" % name, fg='green')
        click.secho("Plan %s deleted!" % plan, fg='green')
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
    click.secho("Deploying vms from plan %s" % (plan), fg='green')
    default = config.default
    with open(inputfile, 'r') as entries:
        vms = yaml.load(entries)
        for name in vms:
            profile = vms[name]
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
            start = next((e for e in [profile.get('start'), customprofile.get('start'), default['start']] if e is not None))
            nets = next((e for e in [profile.get('nets'), customprofile.get('nets'), default['nets']] if e is not None))
            iso = next((e for e in [profile.get('iso'), customprofile.get('iso')] if e is not None), None)
            keys = next((e for e in [profile.get('keys'), customprofile.get('keys')] if e is not None), None)
            cmds = next((e for e in [profile.get('cmds'), customprofile.get('cmds')] if e is not None), None)
            netmasks = next((e for e in [profile.get('netmasks'), customprofile.get('netmasks')] if e is not None), None)
            gateway = next((e for e in [profile.get('gateway'), customprofile.get('gateway')] if e is not None), None)
            dns = next((e for e in [profile.get('dns'), customprofile.get('dns')] if e is not None), None)
            domain = next((e for e in [profile.get('domain'), customprofile.get('domain')] if e is not None), None)
            emulator = next((e for e in [profile.get('emulator'), customprofile.get('emulator'), default['emulator']] if e is not None))
            k.emulator = emulator
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
                    cmds = scriptcmds
            result = k.create(name=name, description=description, title=title, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain)
            if result == 0:
                click.secho("%s deployed!" % name, fg='green')
            else:
                click.secho("%s not deployed! :(" % name, fg='green')


@cli.command()
@click.argument('name')
@pass_config
def info(config, name):
    k = config.k
    k.info(name)


@cli.command()
@click.argument('name')
@pass_config
def ssh(config, name):
    k = config.k
    k.ssh(name)

if __name__ == '__main__':
    cli()
