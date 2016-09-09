#!/usr/bin/python

import click
from defaults import NET1, POOL, NUMCPUS, MEMORY, DISKSIZE1, DISKINTERFACE1, DISKTHIN1, DISKSIZE2, DISKINTERFACE2, DISKTHIN2, GUESTID, VNC, CLOUDINIT, START
from prettytable import PrettyTable
from kvirt import Kvirt
import os
import yaml

VERSION = '0.99.3'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class Config():
    def load(self):
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            ini = {'default': {'client': 'local'}, 'local': {}}
            click.secho("Using local hypervisor as no kcli.yml was found...", fg='green')
        else:
            with open(inifile, 'r') as entries:
                ini = yaml.load(entries)
            if 'default' not in ini or 'client' not in ini['default']:
                click.secho("Missing default section in config file. Leaving...", fg='red')
                os._exit(1)
        client = ini['default']['client']
        if client not in ini:
            click.secho("Missing section for client %s in config file. Leaving..." % client, fg='red')
            os._exit(1)
        defaults = {}
        default = ini['default']
        defaults['net1'] = default.get('net1', NET1)
        defaults['pool'] = default.get('pool', POOL)
        defaults['numcpus'] = int(default.get('numcpus', NUMCPUS))
        defaults['memory'] = int(default.get('memory', MEMORY))
        defaults['disksize1'] = int(default.get('disksize1', DISKSIZE1))
        defaults['diskinterface1'] = default.get('diskinterface1', DISKINTERFACE1)
        defaults['diskthin1'] = bool(default.get('diskthin1', DISKTHIN1))
        defaults['disksize2'] = int(default.get('disksize1', DISKSIZE2))
        defaults['diskinterface2'] = default.get('diskinterface2', DISKINTERFACE2)
        defaults['diskthin2'] = bool(default.get('diskthin2', DISKTHIN2))
        defaults['guestid'] = default.get('guestid', GUESTID)
        defaults['vnc'] = bool(default.get('vnc', VNC))
        defaults['cloudinit'] = bool(default.get('cloudinit', CLOUDINIT))
        defaults['start'] = bool(default.get('start', START))
        self.default = defaults
        options = ini[client]
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
@click.version_option(version=VERSION)
@pass_config
# @click.option('-c', '--client',help='client', envvar='CLIENT')
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
@click.argument('name')
@pass_config
def console(config, name):
    k = config.k
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
@click.option('-p', '--profiles', is_flag=True)
@click.option('-t', '--templates', is_flag=True)
@click.option('-i', '--isos', is_flag=True)
@pass_config
def list(config, profiles, templates, isos):
    k = config.k
    if profiles:
        for profile in sorted(config.profiles):
            print profile
    elif templates:
        for template in sorted(k.volumes()):
            print template
    elif isos:
        for iso in sorted(k.volumes(iso=True)):
            print iso
    else:
        vms = PrettyTable(["Name", "Status", "Ips", "Source", "Description"])
        for vm in sorted(k.list()):
            vms.add_row(vm)
        print vms


@cli.command()
@click.option('-p', '--profile', help='Profile to use')
@click.option('-1', '--ip1', help='Optional Ip to assign to eth0. Netmask and gateway will be retrieved from profile')
@click.option('-2', '--ip2', help='Optional Ip to assign to eth1. Netmask and gateway will be retrieved from profile')
@click.option('-3', '--ip3', help='Optional Ip to assign to eth2. Netmask and gateway will be retrieved from profile')
@click.option('-4', '--ip4', help='Optional Ip to assign to eth3. Netmask and gateway will be retrieved from profile')
@click.argument('name')
@pass_config
def create(config, profile, ip1, ip2, ip3, ip4, name):
    click.secho("Deploying vm %s from profile %s..." % (name, profile), fg='green')
    k = config.k
    default = config.default
    profiles = config.profiles
    if profile not in profiles:
        click.secho("Invalid profile %s. Leaving..." % profile, fg='red')
        os._exit(1)
    profile = profiles[profile]
    template = profile.get('template')
    description = ''
    net1 = profile.get('net1', default['net1'])
    numcpus = profile.get('numcpus', default['numcpus'])
    memory = profile.get('memory', default['memory'])
    pool = profile.get('pool', default['pool'])
    diskthin1 = bool(profile.get('diskthin1', default['diskthin1']))
    disksize1 = profile.get('disksize1', default['disksize1'])
    diskinterface1 = profile.get('diskinterface', default['diskinterface1'])
    disksize2 = profile.get('disksize2', 0)
    diskthin2 = profile.get('diskthin2')
    diskinterface2 = profile.get('diskinterface', default['diskinterface2'])
    guestid = profile.get('guestid', default['guestid'])
    net2 = profile.get('net2')
    net3 = profile.get('net3')
    net4 = profile.get('net4')
    iso = profile.get('iso')
    vnc = profile.get('vnc', default['vnc'])
    cloudinit = profile.get('cloudinit', default['cloudinit'])
    start = profile.get('start', default['start'])
    keys = profile.get('keys', None)
    cmds = profile.get('cmds', None)
    netmask1 = profile.get('netmask1')
    gateway1 = profile.get('gateway1')
    netmask2 = profile.get('netmask2')
    netmask3 = profile.get('netmask3')
    netmask4 = profile.get('netmask4')
    k.create(name=name, description=description, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disksize1=disksize1, diskthin1=diskthin1, diskinterface1=diskinterface1, disksize2=disksize2, diskthin2=diskthin2, diskinterface2=diskinterface2, net1=net1, net2=net2, net3=net3, net4=net4, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), start=bool(start), keys=keys, cmds=cmds, ip1=ip1, netmask1=netmask1, gateway1=gateway1, ip2=ip2, netmask2=netmask2, ip3=ip3, netmask3=netmask3, ip4=ip4, netmask4=netmask4)


@cli.command()
@click.option('-b', '--base', help='Base template')
@click.argument('name')
@pass_config
def clone(config, base, full, name):
    click.secho("Cloning vm %s from vm %s..." % (name, base), fg='green')
    k = config.k
    k.clone(base, name, full)


# @cli.command()
# @click.option('-m', '--memory', help='Memory to set')
# @click.argument('name')
# @pass_config
# def update(config, memory, name):
#     click.secho("Updated memory of vm %s to %d..." % (name, memory), fg='green')


@cli.command()
@pass_config
def report(config):
    click.secho("Reporting setup...", fg='green')
    k = config.k
    k.report()


@cli.command()
@click.option('-f', '--inputfile', help='Input file')
@click.option('-d', '--delete', is_flag=True)
@click.argument('plan')
@pass_config
def plan(config, inputfile, delete, plan):
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
    if inputfile is None:
        if os.path.exists('kcli_plan.yml'):
            click.secho("using default input file kcli_plan.yml", fg='green')
            inputfile = 'kcli_plan.yml'
        else:
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
            else:
                customprofile = {}
            pool = next((e for e in [profile.get('pool'), customprofile.get('pool'), default['pool']] if e is not None))
            template = next((e for e in [profile.get('template'), customprofile.get('template')] if e is not None), None)
            numcpus = next((e for e in [profile.get('numcpus'), customprofile.get('numcpus'), default['numcpus']] if e is not None))
            memory = next((e for e in [profile.get('memory'), customprofile.get('memory'), default['memory']] if e is not None))
            disksize1 = next((e for e in [profile.get('disksize1'), customprofile.get('disksize1'), default['disksize1']] if e is not None))
            diskinterface1 = next((e for e in [profile.get('diskinterface1'), customprofile.get('diskinterface1'), default['diskinterface1']] if e is not None))
            diskthin1 = next((e for e in [profile.get('diskthin1'), customprofile.get('diskthin1'), default['diskthin1']] if e is not None))
            disksize2 = next((e for e in [profile.get('disksize2'), customprofile.get('disksize2'), default['disksize2']] if e is not None))
            diskinterface2 = next((e for e in [profile.get('diskinterface2'), customprofile.get('diskinterface2'), default['diskinterface2']] if e is not None))
            diskthin2 = next((e for e in [profile.get('diskthin2'), customprofile.get('diskthin2')] if e is not None), None)
            guestid = next((e for e in [profile.get('guestid'), customprofile.get('guestid'), default['guestid']] if e is not None))
            vnc = next((e for e in [profile.get('vnc'), customprofile.get('vnc'), default['vnc']] if e is not None))
            cloudinit = next((e for e in [profile.get('cloudinit'), customprofile.get('cloudinit'), default['cloudinit']] if e is not None))
            start = next((e for e in [profile.get('start'), customprofile.get('start'), default['start']] if e is not None))
            net1 = next((e for e in [profile.get('net1'), customprofile.get('net1'), default['net1']] if e is not None))
            net2 = next((e for e in [profile.get('net2'), customprofile.get('net2')] if e is not None), None)
            net3 = next((e for e in [profile.get('net3'), customprofile.get('net3')] if e is not None), None)
            net4 = next((e for e in [profile.get('net4'), customprofile.get('net4')] if e is not None), None)
            iso = next((e for e in [profile.get('iso'), customprofile.get('iso')] if e is not None), None)
            keys = next((e for e in [profile.get('keys'), customprofile.get('keys')] if e is not None), None)
            cmds = next((e for e in [profile.get('cmds'), customprofile.get('cmds')] if e is not None), None)
            script = next((e for e in [profile.get('script'), customprofile.get('scripts')] if e is not None), None)
            netmask1 = next((e for e in [profile.get('netmask1'), customprofile.get('netmask1')] if e is not None), None)
            gateway1 = next((e for e in [profile.get('gateway1'), customprofile.get('gateway1')] if e is not None), None)
            netmask2 = next((e for e in [profile.get('netmask2'), customprofile.get('netmask2')] if e is not None), None)
            netmask3 = next((e for e in [profile.get('netmask3'), customprofile.get('netmask3')] if e is not None), None)
            netmask4 = next((e for e in [profile.get('netmask4'), customprofile.get('netmask4')] if e is not None), None)
            ip1 = profile.get('ip1')
            ip2 = profile.get('ip2')
            ip3 = profile.get('ip3')
            ip4 = profile.get('ip4')
            if script is not None and os.path.exists(script):
                scriptlines = [line.strip() for line in open(script).readlines() if line != '\n']
                if not scriptlines:
                    break
                cmds = scriptlines
            description = plan
            k.create(name=name, description=description, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disksize1=disksize1, diskthin1=diskthin1, diskinterface1=diskinterface1, disksize2=disksize2, diskthin2=diskthin2, diskinterface2=diskinterface2, net1=net1, net2=net2, net3=net3, net4=net4, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), start=bool(start), keys=keys, cmds=cmds, ip1=ip1, netmask1=netmask1, gateway1=gateway1, ip2=ip2, netmask2=netmask2, ip3=ip3, netmask3=netmask3, ip4=ip4, netmask4=netmask4)
            click.secho("%s deployed!" % name, fg='green')


@cli.command()
@click.argument('name')
@pass_config
def info(config, name):
    k = config.k
    k.info(name)

if __name__ == '__main__':
    cli()
