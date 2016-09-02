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
            print "Missing ini file.Leaving..."
            os._exit(1)
        c.read(inifile)
        if 'default' not in c.sections() or 'client' not in c.options('default'):
            print "Missing default section in inifile.Leaving..."
            os._exit(1)
        client = c.get('default', 'client')
        if client not in c.sections():
            print "Missing section for client %s in inifile.Leaving..." % client
            os._exit(1)
        options = c.options(client)
        host = c.get(client, 'host') if 'host' in options else '127.0.0.1'
        port = c.get(client, 'port') if 'port' in options else None
        user = c.get(client, 'user') if 'user' in options else 'root'
        protocol = c.get(client, 'protocol') if 'protocol' in options else 'ssh'
        self.k = Kvirt(host=host, port=port, user=user, protocol=protocol)


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
    click.secho("Deleted vm %s..." % name, fg='red')


@cli.command()
@pass_config
def list(config):
    k = config.k
    print k.list()


@cli.command()
@click.option('-b', '--base', help='Base vm')
@click.argument('name')
@pass_config
def clone(config, base, name):
    click.secho("Deploying vm %s from template %s..." % (name, base), fg='green')
    k = config.k
    k.clone(base, name)


@cli.command()
@click.option('-m', '--memory', help='Memory to set')
@click.argument('name')
@pass_config
def update(config, memory, name):
    click.secho("Updated memory of vm %s to %d..." % (name, memory), fg='green')


@cli.command()
@click.argument('name')
@pass_config
def info(config, name):
    k = config.k
    k.info(name)

if __name__ == '__main__':
    cli()
