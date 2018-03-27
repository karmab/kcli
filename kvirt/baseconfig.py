#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvirt config class
"""

from kvirt.defaults import NETS, POOL, CPUMODEL, NUMCPUS, MEMORY, DISKS, DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID, VNC, CLOUDINIT, RESERVEIP, RESERVEDNS, RESERVEHOST, START, NESTED, TUNNEL, REPORTURL, REPORTDIR, REPORT, REPORTALL, INSECURE, KEYS, CMDS, DNS, DOMAIN, SCRIPTS, FILES, ISO, NETMASKS, GATEWAY, SHAREDKEY, TEMPLATE, ENABLEROOT, PLANVIEW, PRIVATEKEY, TAGS
from kvirt import common
import os
from shutil import copyfile
import sys
import yaml


class Kbaseconfig:
    def __init__(self, client=None, debug=False, quiet=False):
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            if os.path.exists('/Users'):
                _type = 'vbox'
            elif not os.path.exists('/var/run/libvirt/libvirt-sock'):
                _type = 'kubevirt'
            else:
                _type = 'kvm'
            self.ini = {'default': {'client': 'local'}, 'local': {'pool': 'default', 'type': _type}}
        else:
            with open(inifile, 'r') as entries:
                try:
                    self.ini = yaml.load(entries)
                except yaml.scanner.ScannerError as err:
                    common.pprint("Couldn't parse yaml in .kcli/config.yml. Leaving...", color='red')
                    common.pprint(err, color='red')
                    os._exit(1)
                except:
                    self.host = None
                    return
            if 'default' not in self.ini:
                common.pprint("Missing default section in config file. Leaving...", color='red')
                self.host = None
                return
            if 'client' not in self.ini['default']:
                common.pprint("Using local hypervisor as no client was specified...", color='green')
                self.ini['default']['client'] = 'local'
                self.ini['local'] = {}
        self.clients = [e for e in self.ini if e != 'default']
        defaults = {}
        default = self.ini['default']
        defaults['nets'] = default.get('nets', NETS)
        defaults['pool'] = default.get('pool', POOL)
        defaults['template'] = default.get('template', TEMPLATE)
        defaults['cpumodel'] = default.get('cpumodel', CPUMODEL)
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
        defaults['reservedns'] = bool(default.get('reservedns', RESERVEDNS))
        defaults['reservehost'] = bool(default.get('reservehost', RESERVEHOST))
        defaults['nested'] = bool(default.get('nested', NESTED))
        defaults['start'] = bool(default.get('start', START))
        defaults['tunnel'] = bool(default.get('tunnel', TUNNEL))
        defaults['insecure'] = bool(default.get('insecure', INSECURE))
        defaults['reporturl'] = default.get('reporturl', REPORTURL)
        defaults['reportdir'] = default.get('reportdir', REPORTDIR)
        defaults['report'] = bool(default.get('report', REPORT))
        defaults['reportall'] = bool(default.get('reportall', REPORTALL))
        defaults['keys'] = default.get('keys', KEYS)
        defaults['cmds'] = default.get('cmds', CMDS)
        defaults['dns'] = default.get('dns', DNS)
        defaults['domain'] = default.get('file', DOMAIN)
        defaults['scripts'] = default.get('script', SCRIPTS)
        defaults['files'] = default.get('files', FILES)
        defaults['iso'] = default.get('iso', ISO)
        defaults['netmasks'] = default.get('netmasks', NETMASKS)
        defaults['gateway'] = default.get('gateway', GATEWAY)
        defaults['sharedkey'] = default.get('sharedkey', SHAREDKEY)
        defaults['enableroot'] = default.get('enableroot', ENABLEROOT)
        defaults['planview'] = default.get('planview', PLANVIEW)
        defaults['privatekey'] = default.get('privatekey', PRIVATEKEY)
        defaults['tags'] = default.get('tags', TAGS)
        currentplanfile = "%s/.kcli/plan" % os.environ.get('HOME')
        if os.path.exists(currentplanfile):
            self.currentplan = open(currentplanfile).read().strip()
        else:
            self.currentplan = 'kvirt'
        self.default = defaults
        profilefile = default.get('profiles', "%s/.kcli/profiles.yml" % os.environ.get('HOME'))
        profilefile = os.path.expanduser(profilefile)
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                self.profiles = yaml.load(entries)
        self.extraclients = {}
        self._extraclients = []
        if client == 'all':
            clis = [cli for cli in self.clients if self.ini[cli].get('enabled', True)]
            self.client = clis[0]
            self._extraclients = clis[1:]
        elif client is None:
            self.client = self.ini['default']['client']
        elif ',' in client:
            self.client = client.split(',')[0]
            self._extraclients = client.split(',')[1:]
        else:
            self.client = client
        if self.client not in self.ini:
            common.pprint("Missing section for client %s in config file. Leaving..." % self.client, color='red')
            os._exit(1)
        self.options = self.ini[self.client]
        options = self.options
        self.host = options.get('host', '127.0.0.1')
        self.port = options.get('port', 22)
        self.user = options.get('user', 'root')
        self.protocol = options.get('protocol', 'ssh')
        self.type = options.get('type', 'kvm')
        self.url = options.get('url', None)
        self.pool = options.get('pool', self.default['pool'])
        self.template = options.get('template', self.default['template'])
        self.tunnel = bool(options.get('tunnel', self.default['tunnel']))
        self.insecure = bool(options.get('insecure', self.default['insecure']))
        self.report = options.get('report', self.default['report'])
        self.reporturl = options.get('reporturl', self.default['reportdir'])
        self.reportdir = options.get('reportdir', self.default['reportdir'])
        self.reportall = options.get('reportall', self.default['reportall'])
        self.enabled = options.get('enabled', True)
        self.nets = options.get('nets', self.default['nets'])
        self.cpumodel = options.get('cpumodel', self.default['cpumodel'])
        self.cpuflags = options.get('cpuflags', [])
        self.numcpus = options.get('numcpus', self.default['numcpus'])
        self.memory = options.get('memory', self.default['memory'])
        self.disks = options.get('disks', self.default['disks'])
        self.disksize = options.get('disksize', self.default['disksize'])
        self.diskinterface = options.get('diskinterface', self.default['diskinterface'])
        self.diskthin = options.get('diskthin', self.default['diskthin'])
        self.guestid = options.get('guestid', self.default['guestid'])
        self.vnc = options.get('vnc', self.default['vnc'])
        self.cloudinit = options.get('cloudinit', self.default['cloudinit'])
        self.reserveip = options.get('reserveip', self.default['reserveip'])
        self.reservedns = options.get('reservedns', self.default['reservedns'])
        self.reservehost = options.get('reservehost', self.default['reservehost'])
        self.nested = options.get('nested', self.default['nested'])
        self.start = options.get('start', self.default['start'])
        self.iso = options.get('iso', self.default['iso'])
        self.keys = options.get('keys', self.default['keys'])
        self.cmds = options.get('cmds', self.default['cmds'])
        self.netmasks = options.get('netmasks', self.default['netmasks'])
        self.gateway = options.get('gateway', self.default['gateway'])
        self.sharedkey = options.get('sharedkey', self.default['sharedkey'])
        self.enableroot = options.get('enableroot', self.default['enableroot'])
        self.planview = options.get('planview', self.default['planview'])
        self.dns = options.get('dns', self.default['dns'])
        self.domain = options.get('domain', self.default['domain'])
        self.scripts = options.get('scripts', self.default['scripts'])
        self.files = options.get('files', self.default['files'])
        self.privatekey = options.get('privatekey', self.default['privatekey'])
        self.tags = options.get('tags', self.default['tags'])

    def switch_host(self, client):
        if client not in self.clients:
            common.pprint("Client %s not found in config.Leaving...." % client, color='red')
            return {'result': 'failure', 'reason': "Client %s not found in config" % client}
        enabled = self.ini[client].get('enabled', True)
        if not enabled:
            common.pprint("Client %s is disabled.Leaving...." % client, color='red')
            return {'result': 'failure', 'reason': "Client %s is disabled" % client}
        common.pprint("Switching to client %s..." % client, color='green')
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        if os.path.exists(inifile):
            newini = ''
            for line in open(inifile).readlines():
                if 'client' in line:
                    newini += " client: %s\n" % client
                else:
                    newini += line
            open(inifile, 'w').write(newini)
        return {'result': 'success'}

    def enable_host(self, client):
        if client not in self.clients:
            common.pprint("Client %s not found in config.Leaving...." % client, color='green')
            return {'result': 'failure', 'reason': "Client %s not found in config" % client}
        common.pprint("Enabling client %s..." % client, color='green')
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        if os.path.exists(inifile):
            newini = ''
            clientreached = False
            for line in open(inifile).readlines():
                if line.startswith("%s:" % client):
                    clientreached = True
                    newini += line
                    continue
                if clientreached and 'enabled' not in self.ini[client]:
                    newini += " enabled: true\n"
                    clientreached = False
                    newini += line
                    continue
                elif clientreached and line.startswith(' enabled:'):
                    newini += " enabled: true\n"
                    clientreached = False
                else:
                    newini += line
            open(inifile, 'w').write(newini)
        return {'result': 'success'}

    def disable_host(self, client):
        if client not in self.clients:
            common.pprint("Client %s not found in config.Leaving...." % client, color='red')
            return {'result': 'failure', 'reason': "Client %s not found in config" % client}
        elif self.ini['default']['client'] == client:
            common.pprint("Client %s currently default.Leaving...." % client, color='red')
            return {'result': 'failure', 'reason': "Client %s currently default" % client}
        common.pprint("Disabling client %s..." % client, color='green')
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        if os.path.exists(inifile):
            newini = ''
            clientreached = False
            for line in open(inifile).readlines():
                if line.startswith("%s:" % client):
                    clientreached = True
                    newini += line
                    continue
                if clientreached and 'enabled' not in self.ini[client]:
                    newini += " enabled: false\n"
                    clientreached = False
                    newini += line
                    continue
                elif clientreached and line.startswith(' enabled:'):
                    newini += " enabled: false\n"
                    clientreached = False
                else:
                    newini += line
            open(inifile, 'w').write(newini)
        return {'result': 'success'}

    def bootstrap(self, name, host, port, user, protocol, url, pool, poolpath):
        common.pprint("Bootstrapping env", color='green')
        if host is None and url is None:
            url = 'qemu:///system'
            host = '127.0.0.1'
        if pool is None:
            pool = 'default'
        if poolpath is None:
            poolpath = '/var/lib/libvirt/images'
        if host == '127.0.0.1':
            ini = {'default': {'client': 'local', 'cloudinit': True, 'tunnel': False, 'reservehost': False, 'insecure': True, 'enableroot': True, 'reserveip': False, 'reservedns': False, 'reservehost': False, 'nested': True, 'start': True}, 'local': {'pool': pool, 'nets': ['default']}}
            if not sys.platform.startswith('linux'):
                ini['local']['type'] = 'vbox'
        else:
            if name is None:
                name = host
            ini = {'default': {'client': name, 'cloudinit': True, 'tunnel': True, 'reservehost': False, 'insecure': True, 'enableroot': True, 'reserveip': False, 'reservedns': False, 'reservehost': False, 'nested': True, 'start': True}}
            ini[name] = {'host': host, 'pool': pool, 'nets': ['default']}
            if protocol is not None:
                ini[name]['protocol'] = protocol
            if user is not None:
                ini[name]['user'] = user
            if port is not None:
                ini[name]['port'] = port
            if url is not None:
                ini[name]['url'] = url
        path = os.path.expanduser('~/.kcli/config.yml')
        rootdir = os.path.expanduser('~/.kcli')
        if os.path.exists(path):
            copyfile(path, "%s.bck" % path)
        if not os.path.exists(rootdir):
            os.makedirs(rootdir)
        with open(path, 'w') as conf_file:
            yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
        common.pprint("Environment bootstrapped!", color='green')
