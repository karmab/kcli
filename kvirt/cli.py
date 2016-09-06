#!/usr/bin/python

import click
from kvirt import Kvirt
import ConfigParser
import os

VERSION = '0.1.1'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class Config():
    def load(self):
        c = ConfigParser.ConfigParser()
        inifile = "%s/kvirt.ini" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            print "Missing kvirt.ini file.Leaving..."
            os._exit(1)
        c.read(inifile)
        if 'default' not in c.sections() or 'client' not in c.options('default'):
            print "Missing default section in inifile.Leaving..."
            os._exit(1)
        client = c.get('default', 'client')
        if client not in c.sections():
            print "Missing section for client %s in inifile.Leaving..." % client
            os._exit(1)
        defaults = {}
        default = dict(c.items('default'))
        defaults['pool'] = int(default['pool']) if 'pool' in default.keys() else 'default'
        defaults['numcpus'] = int(default['numcpus']) if 'numcpus' in default.keys() else 2
        defaults['memory'] = int(default['memory']) if 'memory' in default.keys() else 512
        defaults['disksize1'] = default['disksize1'] if 'disksize1' in default.keys() else '10'
        defaults['diskinterface'] = default['diskinterface'] if 'diskinterface' in default.keys() else 'virtio'
        defaults['diskthin1'] = bool(default['diskthin1']) if 'diskthin1' in default.keys() else True
        defaults['guestid'] = default['guestid'] if 'guestid' in default.keys() else 'guestrhel764'
        defaults['vnc'] = bool(default['vnc']) if 'vnc' in default.keys() else False
        defaults['cloudinit'] = bool(default['cloudinit']) if 'cloudinit' in default.keys() else True
        defaults['start'] = bool(default['start']) if 'start' in default.keys() else True
        self.default = defaults
        options = c.options(client)
        host = c.get(client, 'host') if 'host' in options else '127.0.0.1'
        port = c.get(client, 'port') if 'port' in options else None
        user = c.get(client, 'user') if 'user' in options else 'root'
        protocol = c.get(client, 'protocol') if 'protocol' in options else 'ssh'
        self.k = Kvirt(host=host, port=port, user=user, protocol=protocol)
        profilefile = "%s/kvirt_profiles.ini" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            print "Missing kvirt_profiles.ini file.Leaving..."
            os._exit(1)
        c = ConfigParser.ConfigParser()
        c.read(profilefile)
        profiles = {}
        for prof in c.sections():
            for option in c.options(prof):
                profiles.setdefault(prof, {option: c.get(prof, option)})[option] = c.get(prof, option)
        self.profiles = profiles

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
        print k.list()


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
    net1 = profile.get('net1')
    net2 = profile.get('net2')
    net3 = profile.get('net3')
    net4 = profile.get('net4')
    pool = profile.get('pool', default['pool'])
    iso = profile.get('iso')
    if template is None or net1 is None:
        click.secho("Missing info from profile %s.Leaving..." % profile, fg='red')
        os._exit(1)
    numcpus = int(profile.get('numcpus', default['numcpus']))
    memory = int(profile.get('memory', default['memory']))
    disksize1 = int(profile.get('disksize1', default['disksize1']))
    diskinterface = profile.get('diskinterface', default['diskinterface'])
    diskthin1 = bool(profile.get('diskthin1', default['diskthin1']))
    # disksize2 = profile.get('disksize2')
    disksize2 = None
    diskthin2 = profile.get('diskthin2')
    guestid = profile.get('guestid', default['guestid'])
    vnc = bool(profile.get('vnc', default['vnc']))
    cloudinit = bool(profile.get('cloudinit', default['cloudinit']))
    start = bool(profile.get('start', default['start']))
    keys = profile.get('keys', None)
    cmds = profile.get('cmds', None)
    k.create(name=name, numcpus=numcpus, diskthin1=diskthin1, disksize1=disksize1, diskinterface=diskinterface, backing=template, memory=memory, pool=pool, guestid=guestid, net1=net1, net2=net2, net3=net3, net4=net4, iso=iso, diskthin2=diskthin2, disksize2=disksize2, vnc=vnc, cloudinit=cloudinit, start=start, keys=keys, cmds=cmds)


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
    click.secho("Information about setup...", fg='green')
    k = config.k
    k.report()


@cli.command()
@click.argument('name')
@pass_config
def info(config, name):
    k = config.k
    k.info(name)

if __name__ == '__main__':
    cli()
