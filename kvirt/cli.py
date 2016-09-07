#!/usr/bin/python

import click
from prettytable import PrettyTable
from kvirt import Kvirt
import os
import yaml

VERSION = '0.1.1'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class Config():
    def load(self):
        inifile = "%s/kvirt.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            print "Missing kvirt.yml file.Leaving..."
            os._exit(1)
        with open(inifile, 'r') as entries:
            ini = yaml.load(entries)
        if 'default' not in ini or 'client' not in ini['default']:
            print "Missing default section in config file.Leaving..."
            os._exit(1)
        client = ini['default']['client']
        if client not in ini:
            print "Missing section for client %s in config file.Leaving..." % client
            os._exit(1)
        defaults = {}
        default = ini['default']
        defaults['net1'] = default.get('net1', 'default')
        defaults['pool'] = default.get('pool', 'default')
        defaults['numcpus'] = int(default.get('numcpus', 2))
        defaults['memory'] = int(default.get('memory', 512))
        defaults['disksize1'] = int(default.get('disksize1', '10'))
        defaults['diskinterface1'] = default.get('diskinterface1', 'virtio')
        defaults['diskinterface2'] = default.get('diskinterface2', 'virtio')
        defaults['diskthin1'] = bool(default.get('diskthin1', True))
        defaults['diskthin2'] = bool(default.get('diskthin2', True))
        defaults['guestid'] = default.get('guestid', 'guestrhel764')
        defaults['vnc'] = bool(default.get('vnc', False))
        defaults['cloudinit'] = bool(default.get('cloudinit', True))
        defaults['start'] = bool(default.get('start', True))
        self.default = defaults
        options = ini[client]
        host = options.get('host', '127.0.0.1')
        port = options.get('port', None)
        user = options.get('user', 'root')
        protocol = options.get('protocol', 'ssh')
        self.k = Kvirt(host=host, port=port, user=user, protocol=protocol)
        profilefile = "%s/kvirt_profiles.yml" % os.environ.get('HOME')
        if not os.path.exists(profilefile):
            print "Missing kvirt_profiles.yml file.Leaving..."
            os._exit(1)
        with open(profilefile, 'r') as entries:
            self.profiles = yaml.load(entries)

pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=VERSION)
@pass_config
# @click.option('-c', '--client',help='client', envvar='CLIENT')
def cli(config):
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
        for profile in config.profiles:
            print profile
    elif templates:
        for template in k.volumes():
            print template
    elif isos:
        for iso in k.volumes(iso=True):
            print iso
    else:
        vms = PrettyTable(["Name", "Status", "Ips", "Description"])
        for vm in k.list():
            vms.add_row(vm)
        print vms


@cli.command()
@click.option('-p', '--profile', help='Profile to use')
@click.argument('name')
@pass_config
def create(config, profile, name):
    click.secho("Deploying vm %s from profile %s..." % (name, profile), fg='green')
    k = config.k
    default = config.default
    profiles = config.profiles
    if profile not in profiles:
        click.secho("Invalid profile %s.Leaving..." % profile, fg='red')
        os._exit(1)
    profile = profiles[profile]
    template = profile.get('template')
    description = ''
    net1 = profile.get('net1', default['net1'])
    if template is None or net1 is None:
        click.secho("Missing info from profile %s.Leaving..." % profile, fg='red')
        os._exit(1)
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
    k.create(name=name, description=description, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disksize1=disksize1, diskthin1=diskthin1, diskinterface1=diskinterface1, disksize2=disksize2, diskthin2=diskthin2, diskinterface2=diskinterface2, net1=net1, net2=net2, net3=net3, net4=net4, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), start=bool(start), keys=keys, cmds=cmds)


@cli.command()
@click.option('-b', '--base', help='Base template')
@click.argument('name')
@pass_config
def clone(config, base, full, name):
    click.secho("Cloning vm %s from vm %s..." % (name, base), fg='green')
    k = config.k
    k.clone(base, name, full)


@cli.command()
@click.option('-m', '--memory', help='Memory to set')
@click.argument('name')
@pass_config
def update(config, memory, name):
    click.secho("Updated memory of vm %s to %d..." % (name, memory), fg='green')


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
        click.confirm('Are you sure about deleting this plan', abort=True)
        for vm in k.list():
            name = vm[0]
            description = vm[3]
            if description == plan:
                k.delete(name)
                click.secho("%s deleted!" % name, fg='green')
        click.secho("Plan %s deleted!" % plan, fg='green')
        return
    if inputfile is None:
        if os.path.exists('kvirt_plan.yml'):
            click.secho("using default input file kvirt_plan.yml", fg='green')
            inputfile = 'kvirt_plan.yml'
        else:
            click.secho("No input file found nor default kvirt_plan.yml.Leaving....", fg='red')
            os._exit(1)
    click.secho("Deploying vms from plan %s" % (plan), fg='green')
    default = config.default
    with open(inputfile, 'r') as entries:
        vms = yaml.load(entries)
        for name in vms:
            profile = vms[name]
            pool = profile.get('pool', default['pool'])
            template = profile.get('template')
            numcpus = profile.get('numcpus', default['numcpus'])
            memory = profile.get('memory', default['memory'])
            disksize1 = profile.get('disksize1', default['disksize1'])
            diskinterface1 = profile.get('diskinterface', default['diskinterface1'])
            diskthin1 = profile.get('diskthin1', default['diskthin1'])
            disksize2 = profile.get('disksize2', 0)
            diskinterface2 = profile.get('diskinterface', default['diskinterface2'])
            diskthin2 = profile.get('diskthin2')
            guestid = profile.get('guestid', default['guestid'])
            vnc = profile.get('vnc', default['vnc'])
            cloudinit = profile.get('cloudinit', default['cloudinit'])
            start = profile.get('start', default['start'])
            net1 = profile.get('net1', default['net1'])
            net2 = profile.get('net2')
            net3 = profile.get('net3')
            net4 = profile.get('net4')
            iso = profile.get('iso')
            keys = profile.get('keys')
            cmds = profile.get('cmds')
            description = plan
            k.create(name=name, description=description, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disksize1=disksize1, diskthin1=diskthin1, diskinterface1=diskinterface1, disksize2=disksize2, diskthin2=diskthin2, diskinterface2=diskinterface2, net1=net1, net2=net2, net3=net3, net4=net4, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), start=bool(start), keys=keys, cmds=cmds)
            click.secho("%s deployed!" % name, fg='green')


@cli.command()
@click.argument('name')
@pass_config
def info(config, name):
    k = config.k
    k.info(name)

if __name__ == '__main__':
    cli()
