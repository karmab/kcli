#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvirt config class
"""

from getpass import getuser
from kvirt.defaults import (NETS, POOL, CPUMODEL, NUMCPUS, MEMORY, DISKS,
                            DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID,
                            VNC, CLOUDINIT, RESERVEIP, RESERVEDNS, RESERVEHOST,
                            START, AUTOSTART, NESTED, TUNNEL, TUNNELHOST, TUNNELPORT, TUNNELUSER, TUNNELDIR,
                            INSECURE, KEYS, CMDS, DNS, DOMAIN, SCRIPTS, FILES, ISO,
                            NETMASKS, GATEWAY, SHAREDKEY, IMAGE, ENABLEROOT,
                            PRIVATEKEY, TAGS, RHNREGISTER, RHNUNREGISTER, RHNSERVER, RHNUSER, RHNPASSWORD, RHNAK,
                            RHNORG, RHNPOOL, NETWORKWAIT, FLAVOR, KEEP_NETWORKS, DNSCLIENT, STORE_METADATA, NOTIFY,
                            PUSHBULLETTOKEN, NOTIFYSCRIPT, SLACKTOKEN, NOTIFYCMD, NOTIFYMETHODS, SLACKCHANNEL,
                            SHAREDFOLDERS, KERNEL, INITRD, CMDLINE, PLACEMENT, YAMLINVENTORY, CPUHOTPLUG, MEMORYHOTPLUG,
                            CPUFLAGS, CPUPINNING, NUMAMODE, NUMA, PCIDEVICES, VIRTTYPE, MAILSERVER, MAILFROM, MAILTO,
                            TPM, JENKINSMODE, RNG, ZEROTIER_NETS, ZEROTIER_KUBELET, VMPORT, VMUSER, VMRULES,
                            VMRULES_STRICT, CACHE, SECURITYGROUPS, LOCAL_OPENSHIFT_APPS, OPENSHIFT_TAG, ROOTPASSWORD,
                            WAIT, WAITCOMMAND, WAITTIMEOUT, TEMPKEY, BMC_USER, BMC_PASSWORD, BMC_MODEL)
from ipaddress import ip_address
from random import choice
from kvirt import common
from kvirt.common import error, pprint, warning, container_mode, ssh, scp
from kvirt.jinjafilters import jinjafilters
from kvirt import kind
from kvirt import microshift
from kvirt import k3s
from kvirt import kubeadm
from kvirt import hypershift
from kvirt import openshift
import os
from shutil import copytree, rmtree, which, copy2
import yaml
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined as strictundefined
from jinja2.runtime import Undefined as defaultundefined
from jinja2.exceptions import TemplateSyntaxError, TemplateError, TemplateNotFound
import re
import sys
from subprocess import call
from tempfile import TemporaryDirectory
from time import sleep


def other_client(profile, clients):
    for cli in clients:
        if profile.startswith(f"{cli}_"):
            return True
    return False


class Kbaseconfig:
    """

    """
    def __init__(self, client=None, containerclient=None, debug=False, quiet=False, offline=False):
        self.debug = debug
        homedir = os.environ.get('HOME')
        cmdir = f"{homedir}/.kcli_cm"
        kclidir = f"{homedir}/.kcli"
        if os.path.isdir(cmdir) and not os.path.isdir(kclidir):
            copytree(cmdir, kclidir)
        inifile = None
        if 'KCLI_CONFIG' in os.environ:
            inifile = os.path.expanduser(os.environ['KCLI_CONFIG'])
            if not os.path.exists(inifile):
                error(f"Config file {inifile} not found. Leaving...")
                sys.exit(1)
        elif os.path.exists(f"{kclidir}/config.yml"):
            inifile = f"{kclidir}/config.yml"
        elif os.path.exists(f"{kclidir}/config.yaml"):
            inifile = f"{kclidir}/config.yaml"
        secretsfile = None
        if os.path.exists(f"{kclidir}/secrets.yml"):
            secretsfile = f"{kclidir}/secrets.yml"
        elif os.path.exists(f"{kclidir}/secrets.yaml"):
            secretsfile = f"{kclidir}/secrets.yaml"
        if secretsfile is None:
            secrets = {}
        else:
            with open(secretsfile, 'r') as entries:
                try:
                    secrets = yaml.safe_load(entries)
                except yaml.scanner.ScannerError as err:
                    error(f"Couldn't parse yaml in {secretsfile}. Got {err}")
                    sys.exit(1)
        if inifile is None:
            defaultclient = 'local'
            _type = 'kvm'
            if offline:
                defaultclient = 'fake'
                _type = 'fake'
            elif not os.path.exists('/var/run/libvirt/libvirt-sock'):
                if os.path.exists('/i_am_a_container') and os.environ.get('KUBERNETES_SERVICE_HOST') is not None:
                    _type = 'kubevirt'
                else:
                    error("No configuration found nor local hypervisor. Is libvirt running?")
                    sys.exit(1)
            self.ini = {'default': {'client': defaultclient}, defaultclient:
                        {'pool': 'default', 'type': _type}}
        else:
            with open(inifile, 'r') as entries:
                try:
                    self.ini = yaml.safe_load(entries)
                except yaml.scanner.ScannerError as err:
                    error(f"Couldn't parse yaml in {inifile}. Got {err}")
                    sys.exit(1)
                except:
                    self.host = None
                    return
            if self.ini is None:
                error(f"Couldn't parse empty {inifile}")
                sys.exit(1)
            for key1 in self.ini:
                for key2 in self.ini[key1]:
                    if isinstance(self.ini[key1][key2], str) and self.ini[key1][key2] == '?secret':
                        if key1 in secrets and key2 in secrets[key1]:
                            self.ini[key1][key2] = secrets[key1][key2]
                        else:
                            error(f"Missing secret for {key1}/{key2}")
                            sys.exit(1)
            if 'default' not in self.ini:
                if len(self.ini) == 1:
                    client = list(self.ini.keys())[0]
                    self.ini['default'] = {"client": client}
                else:
                    error("Missing default section in config file. Leaving...")
                    self.host = None
                    return
            if 'client' not in self.ini['default']:
                self.ini['default']['client'] = 'local'
                self.ini['local'] = {}
        self.clients = [e for e in self.ini if e != 'default']
        defaults = {}
        default = self.ini['default']
        defaults['nets'] = default.get('nets', NETS)
        defaults['pool'] = default.get('pool', POOL)
        defaults['image'] = default.get('image', IMAGE)
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
        defaults['autostart'] = bool(default.get('autostart', AUTOSTART))
        defaults['tunnel'] = bool(default.get('tunnel', TUNNEL))
        defaults['tunnelhost'] = default.get('tunnelhost', TUNNELHOST)
        defaults['tunnelport'] = default.get('tunnelport', TUNNELPORT)
        defaults['tunneluser'] = default.get('tunneluser', TUNNELUSER)
        defaults['tunneldir'] = default.get('tunneldir', TUNNELDIR)
        defaults['insecure'] = bool(default.get('insecure', INSECURE))
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
        defaults['privatekey'] = default.get('privatekey', PRIVATEKEY)
        defaults['networkwait'] = default.get('networkwait', NETWORKWAIT)
        defaults['rhnregister'] = default.get('rhnregister', RHNREGISTER)
        defaults['rhnunregister'] = default.get('rhnunregister', RHNUNREGISTER)
        defaults['rhnserver'] = default.get('rhnserver', RHNSERVER)
        defaults['rhnuser'] = default.get('rhnuser', RHNUSER)
        defaults['rhnpassword'] = default.get('rhnpassword', RHNPASSWORD)
        defaults['rhnactivationkey'] = default.get('rhnactivationkey', RHNAK)
        defaults['rhnorg'] = default.get('rhnorg', RHNORG)
        defaults['rhnpool'] = default.get('rhnpool', RHNPOOL)
        defaults['tags'] = default.get('tags', TAGS)
        defaults['flavor'] = default.get('flavor', FLAVOR)
        defaults['keep_networks'] = default.get('keep_networks', KEEP_NETWORKS)
        defaults['dnsclient'] = default.get('dnsclient', DNSCLIENT)
        defaults['storemetadata'] = default.get('storemetadata', STORE_METADATA)
        defaults['notify'] = default.get('notify', NOTIFY)
        defaults['slacktoken'] = default.get('slacktoken', SLACKTOKEN)
        defaults['pushbullettoken'] = default.get('pushbullettoken', PUSHBULLETTOKEN)
        defaults['notifycmd'] = default.get('notifycmd', NOTIFYCMD)
        defaults['notifyscript'] = default.get('notifyscript', NOTIFYSCRIPT)
        defaults['notifymethods'] = default.get('notifymethods', NOTIFYMETHODS)
        defaults['slackchannel'] = default.get('slackchannel', SLACKCHANNEL)
        defaults['mailserver'] = default.get('mailserver', MAILSERVER)
        defaults['mailfrom'] = default.get('mailfrom', MAILFROM)
        defaults['mailto'] = default.get('mailto', MAILTO)
        defaults['sharedfolders'] = default.get('sharedfolders', SHAREDFOLDERS)
        defaults['kernel'] = default.get('kernel', KERNEL)
        defaults['initrd'] = default.get('initrd', INITRD)
        defaults['cmdline'] = default.get('cmdline', CMDLINE)
        defaults['placement'] = default.get('placement', PLACEMENT)
        defaults['yamlinventory'] = default.get('yamlinventory', YAMLINVENTORY)
        defaults['cpuhotplug'] = bool(default.get('cpuhotplug', CPUHOTPLUG))
        defaults['memoryhotplug'] = bool(default.get('memoryhotplug', MEMORYHOTPLUG))
        defaults['virttype'] = default.get('virttype', VIRTTYPE)
        defaults['tpm'] = default.get('tpm', TPM)
        defaults['rng'] = default.get('rng', RNG)
        defaults['zerotier_nets'] = default.get('zerotier_nets', ZEROTIER_NETS)
        defaults['zerotier_kubelet'] = default.get('zerotier_kubelet', ZEROTIER_KUBELET)
        defaults['jenkinsmode'] = default.get('jenkinsmode', JENKINSMODE)
        defaults['vmuser'] = default.get('vmuser', VMUSER)
        defaults['vmport'] = default.get('vmport', VMPORT)
        defaults['vmrules'] = default.get('vmrules', VMRULES)
        defaults['vmrules_strict'] = default.get('vmrules_strict', VMRULES_STRICT)
        defaults['cache'] = default.get('cache', CACHE)
        defaults['securitygroups'] = default.get('securitygroups', SECURITYGROUPS)
        defaults['rootpassword'] = default.get('rootpassword', ROOTPASSWORD)
        defaults['wait'] = default.get('wait', WAIT)
        defaults['waitcommand'] = default.get('waitcommand', WAITCOMMAND)
        defaults['waittimeout'] = default.get('waittimeout', WAITTIMEOUT)
        defaults['tempkey'] = default.get('tempkey', TEMPKEY)
        defaults['bmc_user'] = default.get('bmc_user', BMC_USER)
        defaults['bmc_password'] = default.get('bmc_password', BMC_PASSWORD)
        defaults['bmc_model'] = default.get('bmc_model', BMC_MODEL)
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
                self.profiles = yaml.safe_load(entries)
                if self.profiles is None:
                    self.profiles = {}
                wrongprofiles = [key for key in self.profiles if 'type' in self.profiles[key] and
                                 self.profiles[key]['type'] not in ['vm', 'container']]
                if wrongprofiles:
                    error("Incorrect type in profiles %s in .kcli/profiles.yml" % ','.join(wrongprofiles))
                    sys.exit(1)
        flavorsfile = default.get('flavors', "%s/.kcli/flavors.yml" % os.environ.get('HOME'))
        flavorsfile = os.path.expanduser(flavorsfile)
        if not os.path.exists(flavorsfile):
            self.flavors = {}
        else:
            with open(flavorsfile, 'r') as entries:
                try:
                    self.flavors = yaml.safe_load(entries)
                except yaml.scanner.ScannerError as err:
                    error("Couldn't parse yaml in .kcli/flavors.yml. Leaving...")
                    error(err)
                    sys.exit(1)
        self.extraclients = {}
        self._extraclients = []
        if client == 'all':
            clis = [cli for cli in self.clients if
                    self.ini[cli].get('enabled', True)]
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
            if '@' in self.client:
                u, h = self.client.split('@')
            else:
                u, h = 'root', self.client
            try:
                ip_address(h)
                warning(f"Missing section for client {self.client} in config file. Trying to connect to {h}")
            except ValueError:
                error(f"Missing Section for client {client}.Leaving...")
                sys.exit(1)
            self.ini[self.client] = {'host': h, 'user': u}
        self.options = self.ini[self.client]
        if self.options.get('type', 'kvm') == 'group':
            enabled = self.options.get('enabled', True)
            if not enabled:
                error(f"Disabled group {client}.Leaving...")
                sys.exit(1)
            self.group = self.client
            algorithm = self.options.get('algorithm', 'random')
            members = self.options.get('members', [])
            if not members:
                error(f"Empty group {client}.Leaving...")
                sys.exit(1)
            elif len(members) == 1:
                self.client = members[0]
                self.algorithm = algorithm
            else:
                if algorithm == 'random':
                    self.client = choice(members)
                    if self.client not in self.ini:
                        error(f"Missing section for client {self.client} in config file. Leaving...")
                        sys.exit(1)
                elif algorithm in ['free', 'balance']:
                    self.client = members[0]
                    self._extraclients = members[1:] if len(members) > 1 else []
                else:
                    error(f"Invalid algorithm {algorithm}.Choose between random, balance and free...")
                    sys.exit(1)
                self.algorithm = algorithm
            self.options = self.ini[self.client]
        options = self.options
        self.enabled = options.get('enabled', True)
        if not self.enabled:
            error(f"Disabled client {self.client}.Leaving...")
            sys.exit(1)
        self.host = options.get('host', '127.0.0.1')
        if self.host.startswith('http'):
            error("Host field shouldn't be an uri. Leaving")
            sys.exit(1)
        if ':' in self.host and '[' not in self.host:
            self.host = f'[{self.host}]'
        self.port = options.get('port', 22)
        self.user = options.get('user', 'root')
        self.protocol = options.get('protocol', 'ssh')
        self.type = options.get('type', 'kvm')
        self.url = options.get('url', None)
        self.pool = options.get('pool', self.default['pool'])
        self.image = options.get('image', self.default['image'])
        self.tunnel = bool(options.get('tunnel', self.default['tunnel']))
        self.tunnelhost = options.get('tunnelhost', self.default['tunnelhost'])
        self.tunnelport = options.get('tunnelport', self.default['tunnelport'])
        self.tunneluser = options.get('tunneluser', self.default['tunneluser'])
        if self.tunnelhost is None and self.type == 'kvm' and self.host != '127.0.0.1':
            self.tunnelhost = self.host.replace('[', '').replace(']', '')
            self.tunnelport = self.port
            self.tunneluser = self.user
        self.tunneldir = options.get('tunneldir', self.default['tunneldir'])
        self.insecure = bool(options.get('insecure', self.default['insecure']))
        self.nets = options.get('nets', self.default['nets'])
        self.cpumodel = options.get('cpumodel', self.default['cpumodel'])
        self.cpuflags = options.get('cpuflags', CPUFLAGS)
        self.cpupinning = options.get('cpupinning', CPUPINNING)
        self.numamode = options.get('numamode', NUMAMODE)
        self.numa = options.get('numa', NUMA)
        self.pcidevices = options.get('pcidevices', PCIDEVICES)
        self.tpm = options.get('tpm', self.default['tpm'])
        self.rng = options.get('rng', self.default['rng'])
        self.zerotier_nets = options.get('zerotier_nets', self.default['zerotier_nets'])
        self.zerotier_kubelet = options.get('zerotier_kubelet', self.default['zerotier_kubelet'])
        self.jenkinsmode = options.get('jenkinsmode', self.default['jenkinsmode'])
        self.numcpus = options.get('numcpus', self.default['numcpus'])
        self.memory = options.get('memory', self.default['memory'])
        self.disks = options.get('disks', self.default['disks'])
        self.disksize = options.get('disksize', self.default['disksize'])
        self.diskinterface = options.get('diskinterface',
                                         self.default['diskinterface'])
        self.diskthin = options.get('diskthin', self.default['diskthin'])
        self.guestid = options.get('guestid', self.default['guestid'])
        self.vnc = options.get('vnc', self.default['vnc'])
        self.cloudinit = options.get('cloudinit', self.default['cloudinit'])
        self.reserveip = options.get('reserveip', self.default['reserveip'])
        self.reservedns = options.get('reservedns', self.default['reservedns'])
        self.reservehost = options.get('reservehost',
                                       self.default['reservehost'])
        self.nested = options.get('nested', self.default['nested'])
        self.start = options.get('start', self.default['start'])
        self.autostart = options.get('autostart', self.default['autostart'])
        self.iso = options.get('iso', self.default['iso'])
        self.keys = options.get('keys', self.default['keys'])
        self.cmds = options.get('cmds', self.default['cmds'])
        self.netmasks = options.get('netmasks', self.default['netmasks'])
        self.gateway = options.get('gateway', self.default['gateway'])
        self.sharedkey = options.get('sharedkey', self.default['sharedkey'])
        self.enableroot = options.get('enableroot', self.default['enableroot'])
        self.dns = options.get('dns', self.default['dns'])
        self.domain = options.get('domain', self.default['domain'])
        self.scripts = options.get('scripts', self.default['scripts'])
        self.files = options.get('files', self.default['files'])
        self.networkwait = options.get('networkwait', self.default['networkwait'])
        self.privatekey = options.get('privatekey', self.default['privatekey'])
        self.rhnregister = options.get('rhnregister', self.default['rhnregister'])
        self.rhnunregister = options.get('rhnunregister', self.default['rhnunregister'])
        self.rhnserver = options.get('rhnserver', self.default['rhnserver'])
        self.rhnuser = options.get('rhnuser', self.default['rhnuser'])
        self.rhnpassword = options.get('rhnpassword', self.default['rhnpassword'])
        self.rhnak = options.get('rhnactivationkey', self.default['rhnactivationkey'])
        self.rhnorg = options.get('rhnorg', self.default['rhnorg'])
        self.rhnpool = options.get('rhnpool', self.default['rhnpool'])
        self.tags = options.get('tags', self.default['tags'])
        self.flavor = options.get('flavor', self.default['flavor'])
        self.dnsclient = options.get('dnsclient', self.default['dnsclient'])
        self.storemetadata = options.get('storemetadata', self.default['storemetadata'])
        self.notify = options.get('notify', self.default['notify'])
        self.slacktoken = options.get('slacktoken', self.default['slacktoken'])
        self.pushbullettoken = options.get('self.pushbullettoken', self.default['pushbullettoken'])
        self.notifycmd = options.get('notifycmd', self.default['notifycmd'])
        self.notifyscript = options.get('notifyscript', self.default['notifyscript'])
        self.notifymethods = options.get('notifymethods', self.default['notifymethods'])
        self.slackchannel = options.get('slackchannel', self.default['slackchannel'])
        self.keep_networks = options.get('keep_networks', self.default['keep_networks'])
        self.sharedfolders = options.get('sharedfolders', self.default['sharedfolders'])
        self.mailserver = options.get('mailserver', self.default['mailserver'])
        self.mailfrom = options.get('mailfrom', self.default['mailfrom'])
        self.mailto = options.get('mailto', self.default['mailto'])
        self.kernel = options.get('kernel', self.default['kernel'])
        self.initrd = options.get('initrd', self.default['initrd'])
        self.cmdline = options.get('cmdline', self.default['cmdline'])
        self.placement = options.get('placement', self.default['placement'])
        self.yamlinventory = options.get('yamlinventory', self.default['yamlinventory'])
        self.cpuhotplug = options.get('cpuhotplug', self.default['cpuhotplug'])
        self.memoryhotplug = options.get('memoryhotplug', self.default['memoryhotplug'])
        self.virttype = options.get('virttype', self.default['virttype'])
        self.containerclient = containerclient
        self.vmuser = options.get('vmuser', self.default['vmuser'])
        self.vmport = options.get('vmport', self.default['vmport'])
        self.vmrules = options.get('vmrules', self.default['vmrules'])
        self.vmrules_strict = options.get('vmrules_strict', self.default['vmrules_strict'])
        self.cache = options.get('cache', self.default['cache'])
        self.securitygroups = options.get('securitygroups', self.default['securitygroups'])
        self.rootpassword = options.get('rootpassword', self.default['rootpassword'])
        self.wait = options.get('wait', self.default['wait'])
        self.waitcommand = options.get('waitcommand', self.default['waitcommand'])
        self.waittimeout = options.get('waittimeout', self.default['waittimeout'])
        self.tempkey = options.get('tempkey', self.default['tempkey'])
        self.bmc_user = options.get('bmc_user', self.default['bmc_user'])
        self.bmc_password = options.get('bmc_password', self.default['bmc_password'])
        self.bmc_model = options.get('bmc_model', self.default['bmc_model'])
        self.overrides = {}

    def switch_host(self, client):
        """

        :param client:
        :return:
        """
        if client not in self.clients:
            error(f"Client {client} not found in config.Leaving....")
            return {'result': 'failure', 'reason': f"Client {client} not found in config"}
        enabled = self.ini[client].get('enabled', True)
        if not enabled:
            error(f"Client {client} is disabled.Leaving....")
            return {'result': 'failure', 'reason': f"Client {client} is disabled"}
        pprint(f"Switching to client {client}...")
        self.ini['default']['client'] = client
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        with open(inifile, 'w') as conf_file:
            try:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                               sort_keys=False)
            except:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
        return {'result': 'success'}

    def enable_host(self, client):
        """

        :param client:
        :return:
        """
        if client not in self.clients:
            error(f"Client {client} not found in config.Leaving....")
            return {'result': 'failure', 'reason': f"Client {client} not found in config"}
        pprint(f"Enabling client {client}...")
        self.ini[client]['enabled'] = True
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        with open(inifile, 'w') as conf_file:
            try:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                               sort_keys=False)
            except:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
        return {'result': 'success'}

    def disable_host(self, client):
        """

        :param client:
        :return:
        """
        if client not in self.clients:
            error(f"Client {client} not found in config.Leaving....")
            return {'result': 'failure', 'reason': f"Client {client} not found in config"}
        elif self.ini['default']['client'] == client:
            error(f"Client {client} currently default.Leaving....")
            return {'result': 'failure', 'reason': f"Client {client} currently default"}
        pprint(f"Disabling client {client}...")
        self.ini[client]['enabled'] = False
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        with open(inifile, 'w') as conf_file:
            try:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                               sort_keys=False)
            except:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
        return {'result': 'success'}

    def set_defaults(self):
        """

        """
        default = {}
        for key in sorted(self.default):
            if self.default[key] is None or (isinstance(self.default[key], list) and not self.default[key]):
                continue
            else:
                default[key] = self.default[key]
        sort_keys = False
        if len(self.clients) == 1:
            default['client'] = [*self.clients][0]
            sort_keys = True
        self.ini['default'] = default
        path = os.path.expanduser('~/.kcli/config.yml')
        with open(path, 'w') as conf_file:
            try:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                               sort_keys=sort_keys)
            except:
                yaml.safe_dump(self.ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)

    def list_keywords(self):
        """

        """
        results = {}
        for keyword in self.default:
            results[keyword] = vars(self)[keyword] if keyword in vars(self) else self.default[keyword]
        return results

    def list_repos(self):
        """

        :return:
        """
        repos = {}
        plansdir = "%s/.kcli/plans" % os.environ.get('HOME')
        if not os.path.exists(plansdir):
            return {}
        else:
            repodirs = [d for d in os.listdir(plansdir) if os.path.isdir(f"{plansdir}/{d}")]
            for d in repodirs:
                repos[d] = None
                if os.path.exists(f"{plansdir}/{d}/.git/config") and which('git') is not None:
                    gitcmd = f"git config -f {plansdir}/{d}/.git/config  --get remote.origin.url"
                    giturl = os.popen(gitcmd).read().strip()
                    repos[d] = giturl
        return repos

    def list_products(self, group=None, repo=None):
        """

        :param group:
        :param repo:
        :return:
        """
        plansdir = "%s/.kcli/plans" % os.environ.get('HOME')
        if not os.path.exists(plansdir):
            return []
        else:
            products = []
            repodirs = [d for d in os.listdir(plansdir) if os.path.isdir(f"{plansdir}/{d}")]
            for rep in repodirs:
                repometa = f"{plansdir}/{rep}/KMETA"
                if not os.path.exists(repometa):
                    continue
                else:
                    realdir = os.path.dirname(os.readlink(repometa)) if os.path.islink(repometa) else None
                    with open(repometa, 'r') as entries:
                        try:
                            repoproducts = yaml.safe_load(entries)
                            for repoproduct in repoproducts:
                                repoproduct['repo'] = rep
                                if 'file' not in repoproduct:
                                    repoproduct['file'] = 'kcli_plan.yml'
                                if '/' in repoproduct['file']:
                                    repoproduct['group'] = repoproduct['file'].split('/')[0]
                                else:
                                    repoproduct['group'] = ''
                                if realdir is not None:
                                    repoproduct['realdir'] = realdir
                                products.append(repoproduct)
                        except yaml.scanner.ScannerError:
                            error("Couldn't properly parse .kcli/repo. Leaving...")
                            continue
            if repo is not None:
                products = [product for product in products if 'repo'
                            in product and product['repo'] == repo]
            if group is not None:
                products = [product for product in products if 'group'
                            in product and product['group'] == group]
            return products

    def create_repo(self, name, url):
        """

        :param name:
        :param url:
        :return:
        """
        reponame = name if name is not None else os.path.basename(url)
        repodir = "%s/.kcli/plans/%s" % (os.environ.get('HOME'), reponame)
        if not os.path.exists(repodir):
            os.makedirs(repodir, exist_ok=True)
        if not url.startswith('http') and not url.startswith('git'):
            os.symlink(url, repodir)
        elif which('git') is None:
            error('repo operations require git')
            sys.exit(1)
        else:
            os.system(f"git clone {url} {repodir}")
        if not os.path.exists(f"{repodir}/KMETA"):
            for root, dirs, files in os.walk(repodir):
                for name in files:
                    if name == 'KMETA':
                        dst = f"{repodir}/KMETA"
                        src = "%s/KMETA" % root.replace("%s/" % repodir, '')
                        os.symlink(src, dst)
                        break
        sys.exit(1)

    def update_repo(self, name, url=None):
        """

        :param name:
        :param url:
        :return:
        """
        repodir = "%s/.kcli/plans/%s" % (os.environ.get('HOME'), name)
        if not os.path.exists(repodir):
            return {'result': 'failure', 'reason': f'repo {name} not found'}
        elif which('git') is None:
            return {'result': 'failure', 'reason': 'repo operations require git'}
        else:
            os.chdir(repodir)
            if os.path.exists('.git'):
                os.system("git pull --rebase")
        return {'result': 'success'}

    def delete_repo(self, name):
        """

        :param name:
        :return:
        """
        repodir = "%s/.kcli/plans/%s" % (os.environ.get('HOME'), name)
        if os.path.exists(repodir) and os.path.isdir(repodir):
            rmtree(repodir)
            return {'result': 'success'}

    def info_plan(self, inputfile, quiet=False, web=False, onfly=None, doc=False):
        """

        :param inputfile:
        :param quiet:
        :return:
        """
        inputfile = os.path.expanduser(inputfile) if inputfile is not None else 'kcli_plan.yml'
        basedir = os.path.dirname(inputfile)
        if basedir == "":
            basedir = '.'
        plan = os.path.basename(inputfile).replace('.yml', '').replace('.yaml', '')
        if not quiet:
            pprint(f"Providing information on parameters of plan {inputfile}...")
        if not os.path.exists(inputfile):
            error("No input file found nor default kcli_plan.yml. Leaving....")
            sys.exit(1)
        parameters = {}
        if os.path.exists(f"{basedir}/{plan}_default.yml"):
            parameterfile = f"{basedir}/{plan}_default.yml"
            if not quiet:
                pprint(f"Parsing {plan}_default.yml for default parameters")
            parameters.update(common.get_parameters(parameterfile))
        if os.path.exists(f"{basedir}/kcli_default.yml"):
            parameterfile = f"{basedir}/kcli_default.yml"
            if not quiet:
                pprint("Parsing kcli_default.yml for default parameters")
            parameters.update(common.get_parameters(parameterfile))
        inputfile_default = "%s_default%s" % os.path.splitext(inputfile)
        if os.path.exists(f"{basedir}/{inputfile_default}"):
            parameterfile = f"{basedir}/{inputfile_default}"
            parameters.update(common.get_parameters(parameterfile))
        parameters.update(common.get_parameters(inputfile, planfile=True))
        if parameters:
            description = parameters.get('description')
            if description is not None:
                print("description: %s" % description.strip())
                del parameters['description']
            info = parameters.get('info')
            if info is not None:
                pprint(info.strip())
                del parameters['info']
            if web:
                return parameters
            if doc:
                maxkey = max([len(x) for x in parameters])
                maxvalue = max([len(str(parameters[x])) for x in parameters if parameters[x] is not None])
                print("|Parameter%s|Default Value%s|" % (" " * (maxkey - len("Parameter")),
                                                         " " * (maxvalue - len("Default Value"))))
                print("|%s|%s|" % ("-" * maxkey, "-" * maxvalue))
            for parameter in sorted(parameters):
                if doc:
                    print("|%s%s|%s%s|" % (parameter, " " * (maxkey - len(parameter)),
                                           parameters[parameter], " " * (maxvalue - len(str(parameters[parameter])))))
                else:
                    print("%s: %s" % (parameter, parameters[parameter]))
                if parameter == 'baseplan':
                    if onfly is not None:
                        common.fetch("%s/%s" % (onfly, parameters[parameter]), '.')
                    baseplan = parameters[parameter]
                    basedir = os.path.dirname(inputfile) if os.path.basename(inputfile) != inputfile else '.'
                    baseplan = f"{basedir}/{baseplan}"
                    self.info_plan(baseplan, quiet=True)
                    print()
        else:
            warning("No parameters found. Leaving...")
        # return {'result': 'success'}

    def info_openshift_disconnected(self):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        inputfile = f'{plandir}/disconnected.yml'
        return self.info_plan(inputfile)

    def info_product(self, name, repo=None, group=None, web=False):
        """Info product"""
        if repo is not None and group is not None:
            products = [product for product in self.list_products
                        if product['name'] == name and product['repo'] == repo and product['group'] == group]
        elif repo is not None:
            products = [product for product in self.list_products()
                        if product['name'] == name and product['repo'] == repo]
        if group is not None:
            products = [product for product in self.list_products()
                        if product['name'] == name and product['group'] == group]
        else:
            products = [product for product in self.list_products() if product['name'] == name]
        if len(products) == 0:
            error("Product not found. Leaving...")
            sys.exit(1)
        elif len(products) > 1:
            error("Product found in several places. Specify repo or group")
            sys.exit(1)
        else:
            product = products[0]
            repo = product['repo']
            repodir = "%s/.kcli/plans/%s" % (os.environ.get('HOME'), repo)
            group = product['group']
            description = product.get('description')
            _file = product['file']
            if not web:
                if group is not None:
                    print(f"group: {group}")
                if description is not None:
                    print(f"description: {description}")
            inputfile = "%s/%s" % (product['realdir'], _file) if 'realdir' in product else _file
            print(f"{repodir}/{inputfile}")
            parameters = self.info_plan(f"{repodir}/{inputfile}", quiet=True, web=web)
            if web:
                if parameters is None:
                    parameters = {}
                return {'product': product, 'parameters': parameters}

    def process_inputfile(self, plan, inputfile, overrides={}, onfly=None, full=False, ignore=False,
                          download_mode=False, extra_funcs=[]):
        default_dir = '/workdir' if container_mode() else '.'
        basedir = os.path.dirname(inputfile) if os.path.dirname(inputfile) != '' else default_dir
        basefile = None
        undefined = strictundefined if not ignore else defaultundefined
        env = Environment(loader=FileSystemLoader(basedir), undefined=undefined, extensions=['jinja2.ext.do'],
                          trim_blocks=True, lstrip_blocks=True)
        for func in extra_funcs:
            env.globals[func.__name__] = func
        for jinjafilter in jinjafilters.jinjafilters:
            env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        try:
            templ = env.get_template(os.path.basename(inputfile))
        except TemplateNotFound:
            error(f"Input file {os.path.basename(inputfile)} not found")
            sys.exit(1)
        except TemplateSyntaxError as e:
            error(f"Error rendering line {e.lineno} of input file {e.filename}. Got: {e.message}")
            sys.exit(1)
        except TemplateError as e:
            error(f"Error rendering input file {inputfile}. Got: {e.message}")
            sys.exit(1)
        except UnicodeDecodeError as e:
            error(f"Error rendering input file {inputfile}. Got: {e}")
            sys.exit(1)
        parameters = {}
        if os.path.exists(f"{basedir}/{plan}_default.yml"):
            parameterfile = f"{basedir}/{plan}_default.yml"
            parameters.update(common.get_parameters(parameterfile))
        if os.path.exists(f"{basedir}/kcli_default.yml"):
            parameterfile = f"{basedir}/kcli_default.yml"
            parameters.update(common.get_parameters(parameterfile))
        inputfile_default = os.path.basename("%s_default%s" % os.path.splitext(inputfile))
        if os.path.exists(f"{basedir}/{inputfile_default}"):
            parameterfile = f"{basedir}/{inputfile_default}"
            parameters.update(common.get_parameters(parameterfile))
        parameters.update(common.get_parameters(inputfile, planfile=True))
        if parameters:
            if 'baseplan' in parameters:
                basefile = parameters['baseplan']
                basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
                baseinputfile = f"{basedir}/{basefile}"
                if container_mode() and not os.path.isabs(basefile) and '/workdir' not in basedir:
                    baseinputfile = f"/workdir/{basedir}/{basefile}"
                if onfly is not None:
                    common.fetch(f"{onfly}/{basefile}", '.')
                baseparameters = self.process_inputfile(plan, baseinputfile, overrides=overrides, onfly=onfly,
                                                        full=True)[1]
                if baseparameters:
                    parameters.update({key: baseparameters[key] for key in baseparameters if key not in parameters})
                baseparameters = common.get_parameters(baseinputfile, planfile=True)
                if baseparameters:
                    baseparameters = yaml.safe_load(baseparameters)['parameters']
                    for baseparameter in baseparameters:
                        if baseparameter not in overrides and baseparameter not in parameters:
                            overrides[baseparameter] = baseparameters[baseparameter]
            for parameter in parameters:
                if parameter in overrides:
                    continue
                currentparameter = parameters[parameter]
                if isinstance(currentparameter, bool) and download_mode:
                    currentparameter = True
                overrides[parameter] = currentparameter
        with open(inputfile, 'r') as entries:
            overrides.update(self.overrides)
            overrides.update({'plan': plan})
            try:
                entries = templ.render(overrides)
            except TemplateError as e:
                error(f"Error rendering inputfile {inputfile}. Got: {e.message}")
                sys.exit(1)
            if not full:
                entrieslist = entries.split('\n')
                if entrieslist[0].startswith('parameters:'):
                    for index, line in enumerate(entrieslist[1:]):
                        if re.match(r'\S', line):
                            entries = '\n'.join(entrieslist[index + 1:])
                            break
                return entries
            try:
                entries = yaml.safe_load(entries)
            except Exception as e:
                error(f"Couldn't load file. Hit {e}")
                sys.exit(1)
        wrong_overrides = [y for y in overrides if '-' in y]
        if wrong_overrides:
            for wrong_override in wrong_overrides:
                error(f"Incorrect parameter {wrong_override}. Hyphens are not allowed")
            sys.exit(1)
        return entries, overrides, basefile, basedir

    def list_profiles(self):
        """

        :return:
        """
        default_disksize = '10'
        default = self.default
        results = []
        other_clients = [cli for cli in self.clients if cli != self.client]
        for profile in [p for p in self.profiles if 'base' not in self.profiles[p]] + [p for p in self.profiles
                                                                                       if 'base' in self.profiles[p]]:
            if other_client(profile, other_clients):
                continue
            info = self.profiles[profile]
            if 'base' in info:
                father = self.profiles[info['base']]
                default_numcpus = father.get('numcpus', default['numcpus'])
                default_memory = father.get('memory', default['memory'])
                default_pool = father.get('pool', default['pool'])
                default_disks = father.get('disks', default['disks'])
                default_nets = father.get('nets', default['nets'])
                default_image = father.get('image', '')
                default_cloudinit = father.get('cloudinit', default['cloudinit'])
                default_nested = father.get('nested', default['nested'])
                default_reservedns = father.get('reservedns', default['reservedns'])
                default_reservehost = father.get('reservehost', default['reservehost'])
                default_flavor = father.get('flavor', default['flavor'])
            else:
                default_numcpus = default['numcpus']
                default_memory = default['memory']
                default_pool = default['pool']
                default_disks = default['disks']
                default_nets = default['nets']
                default_image = ''
                default_cloudinit = default['cloudinit']
                default_nested = default['nested']
                default_reservedns = default['reservedns']
                default_reservehost = default['reservehost']
                default_flavor = default['flavor']
            profiletype = info.get('type', '')
            if profiletype == 'container':
                continue
            numcpus = info.get('numcpus', default_numcpus)
            memory = info.get('memory', default_memory)
            pool = info.get('pool', default_pool)
            diskinfo = []
            disks = info.get('disks')
            if disks is None:
                if 'disksize' in info:
                    disks = [info['disksize']]
                else:
                    disks = default_disks
            for disk in disks:
                if disk is None:
                    size = default_disksize
                elif isinstance(disk, int):
                    size = str(disk)
                elif isinstance(disk, dict):
                    size = str(disk.get('size', default_disksize))
                diskinfo.append(size)
            diskinfo = ','.join(diskinfo)
            netinfo = []
            nets = info.get('nets', default_nets)
            for net in nets:
                if isinstance(net, str):
                    netname = net
                elif isinstance(net, dict) and 'name' in net:
                    netname = net['name']
                netinfo.append(netname)
            netinfo = ','.join(netinfo)
            template = info.get('template', default_image)
            image = info.get('image', template)
            cloudinit = info.get('cloudinit', default_cloudinit)
            nested = info.get('nested', default_nested)
            reservedns = info.get('reservedns', default_reservedns)
            reservehost = info.get('reservehost', default_reservehost)
            flavor = info.get('flavor', default_flavor)
            if flavor is None:
                flavor = f"{numcpus}cpus {memory}Mb ram"
            if profile.startswith(f'{self.client}_'):
                profile = profile.replace(f'{self.client}_', '')
            results.append([profile, flavor, pool, diskinfo, image, netinfo, cloudinit, nested,
                            reservedns, reservehost])
        return sorted(results, key=lambda x: x[0])

    def list_flavors(self):
        """

        :return:
        """
        results = []
        for flavor in self.flavors:
            info = self.flavors[flavor]
            numcpus = info.get('numcpus')
            memory = info.get('memory')
            disk = info.get('disk', '')
            if numcpus is not None and memory is not None:
                results.append([flavor, numcpus, memory, disk])
        return sorted(results, key=lambda x: x[0])

    def list_containerprofiles(self):
        """

        :return:
        """
        results = []
        for profile in sorted(self.profiles):
            info = self.profiles[profile]
            if 'type' not in info or info['type'] != 'container':
                continue
            else:
                image = next((e for e in [info.get('image'), info.get('image')] if e is not None), '')
                nets = info.get('nets', '')
                ports = info.get('ports', '')
                volumes = next((e for e in [info.get('volumes'), info.get('disks')] if e is not None), '')
                # environment = profile.get('environment', '')
                cmd = info.get('cmd', '')
                results.append([profile, image, nets, ports, volumes, cmd])
        return results

    def delete_profile(self, profile, quiet=False):
        found = False
        for prof in [profile, f'{self.client}_{profile}']:
            if prof in self.profiles:
                del self.profiles[prof]
                found = True
        if found:
            path = os.path.expanduser('~/.kcli/profiles.yml')
            if not self.profiles:
                os.remove(path)
            else:
                with open(path, 'w') as profile_file:
                    try:
                        yaml.safe_dump(self.profiles, profile_file, default_flow_style=False, encoding='utf-8',
                                       allow_unicode=True, sort_keys=False)
                    except:
                        yaml.safe_dump(self.profiles, profile_file, default_flow_style=False, encoding='utf-8',
                                       allow_unicode=True)
            return {'result': 'success'}
        else:
            if not quiet:
                error(f"Profile {profile} not found")
            return {'result': 'failure', 'reason': f'Profile {profile} not found'}

    def create_profile(self, profile, overrides={}, quiet=False):
        if profile in self.profiles:
            if not quiet:
                pprint(f"Profile {profile} already there")
            return {'result': 'success'}
        if not overrides:
            return {'result': 'failure', 'reason': "You need to specify at least one parameter"}
        if 'type' in overrides and 'type' not in ['vm', 'container']:
            return {'result': 'failure', 'reason': f"Invalid type {overrides['type']} for profile {profile}"}
        path = os.path.expanduser('~/.kcli/profiles.yml')
        rootdir = os.path.expanduser('~/.kcli')
        self.profiles[profile] = overrides
        if not os.path.exists(rootdir):
            os.makedirs(rootdir)
        if not os.access(rootdir, os.W_OK):
            msg = f"Can't write in {rootdir}"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        if os.path.exists(path) and not os.access(path, os.W_OK):
            msg = f"Can't write in {path}"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        with open(path, 'w') as profile_file:
            try:
                yaml.safe_dump(self.profiles, profile_file, default_flow_style=False, encoding='utf-8',
                               allow_unicode=True, sort_keys=False)
            except:
                yaml.safe_dump(self.profiles, profile_file, default_flow_style=False, encoding='utf-8',
                               allow_unicode=True)
        return {'result': 'success'}

    def update_profile(self, profile, overrides={}, quiet=False):
        mathching_profiles = [p for p in self.profiles if p == profile or p == f'{self.client}_{profile}']
        if not mathching_profiles:
            if quiet:
                error(f"Profile {profile} not found")
            return {'result': 'failure', 'reason': f'Profile {profile} not found'}
        else:
            profile = mathching_profiles[0]
        if not overrides:
            return {'result': 'failure', 'reason': "You need to specify at least one parameter"}
        path = os.path.expanduser('~/.kcli/profiles.yml')
        self.profiles[profile].update(overrides)
        with open(path, 'w') as profile_file:
            try:
                yaml.safe_dump(self.profiles, profile_file, default_flow_style=False, encoding='utf-8',
                               allow_unicode=True, sort_keys=False)
            except:
                yaml.safe_dump(self.profiles, profile_file, default_flow_style=False, encoding='utf-8',
                               allow_unicode=True)
        return {'result': 'success'}

    def create_jenkins_pipeline(self, plan, inputfile, overrides={}, kube=False):
        _type = 'plan'
        if kube:
            _type = 'generic'
            plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
            if 'type' in overrides:
                _type = overrides['type']
                del overrides['type']
                if _type == 'openshift':
                    plandir = os.path.dirname(openshift.create.__code__.co_filename)
                elif _type != 'generic':
                    error(f"Incorrect kubernetes type {_type}. Choose between generic or openshift")
                    sys.exit(1)
                inputfile = f"{plandir}/masters.yml"
        if 'jenkinsmode' in overrides:
            jenkinsmode = overrides['jenkinsmode']
            del overrides['jenkinsmode']
        else:
            jenkinsmode = self.jenkinsmode
        if jenkinsmode not in ['docker', 'podman', 'kubernetes']:
            error(f"Incorrect jenkins mode {self.jenkinsmode}. Choose between docker, podman or kubernetes")
            sys.exit(1)
        inputfile = os.path.expanduser(inputfile) if inputfile is not None else 'kcli_plan.yml'
        basedir = os.path.dirname(inputfile)
        if basedir == "":
            basedir = '.'
        if plan is None:
            plan = os.path.basename(inputfile).replace('.yml', '').replace('.yaml', '')
        if not os.path.exists(inputfile):
            error("No input file found nor default kcli_plan.yml. Leaving....")
            sys.exit(1)
        parameters = {}
        if os.path.exists(f"{basedir}/{plan}_default.yml"):
            parameterfile = f"{basedir}/{plan}_default.yml"
            parameters.update(common.get_parameters(parameterfile))
        if os.path.exists(f"{basedir}/kcli_default.yml"):
            parameterfile = f"{basedir}/kcli_default.yml"
            parameters.update(common.get_parameters(parameterfile))
        inputfile_default = "%s_default%s" % os.path.splitext(inputfile)
        if os.path.exists(f"{basedir}/{inputfile_default}"):
            parameterfile = f"{basedir}/{inputfile_default}"
            parameters.update(common.get_parameters(parameterfile))
        parameters.update(common.get_parameters(inputfile, planfile=True))
        parameters.update(overrides)
        jenkinsdir = os.path.dirname(common.__file__)
        env = Environment(loader=FileSystemLoader(jenkinsdir), extensions=['jinja2.ext.do'], trim_blocks=True,
                          lstrip_blocks=True)
        for jinjafilter in jinjafilters.jinjafilters:
            env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        try:
            templ = env.get_template(os.path.basename("Jenkinsfile.j2"))
        except TemplateSyntaxError as e:
            error(f"Error rendering line {e.lineno} of file {e.filename}. Got: {e.message}")
            sys.exit(1)
        except TemplateError as e:
            error(f"Error rendering file {inputfile}. Got: {e.message}")
            sys.exit(1)
        parameterline = " ".join(["-P %s=${params.%s}" % (parameter, parameter) for parameter in parameters])
        jenkinsfile = templ.render(parameters=parameters, parameterline=parameterline, jenkinsmode=jenkinsmode,
                                   _type=_type)
        return jenkinsfile

    def create_github_pipeline(self, plan, inputfile, paramfile=None, overrides={}, kube=False, script=False):
        if not kube:
            inputfile = os.path.expanduser(inputfile) if inputfile is not None else 'kcli_plan.yml'
            basedir = os.path.dirname(inputfile)
            if basedir == "":
                basedir = '.'
            if not os.path.exists(inputfile):
                error("No input file found nor default kcli_plan.yml. Leaving....")
                sys.exit(1)
            if plan is None:
                plan = os.path.basename(inputfile).replace('.yml', '').replace('.yaml', '')
        else:
            inputfile = None
            if plan is None:
                plan = 'testk'
        if 'plan' in overrides:
            del overrides['plan']
        runner = 'ubuntu-latest'
        if 'runner' in overrides:
            runner = overrides['runner']
            del overrides['runner']
        client = 'local'
        if 'client' in overrides:
            client = overrides['client']
            del overrides['client']
        kubetype = 'generic'
        if kube:
            if 'kubetype' in overrides:
                kubetype = overrides['kubetype']
                del overrides['kubetype']
        runscript = 'true'
        if script:
            if 'runscript' in overrides:
                runscript = str(overrides['runscript']).lower()
                del overrides['runscript']
        workflowdir = os.path.dirname(common.__file__)
        env = Environment(loader=FileSystemLoader(workflowdir), extensions=['jinja2.ext.do'], trim_blocks=True,
                          lstrip_blocks=True)
        for jinjafilter in jinjafilters.jinjafilters:
            env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        try:
            workflowfile = "workflow_script.yml.j2" if script else "workflow.yml.j2"
            templ = env.get_template(os.path.basename(workflowfile))
        except TemplateSyntaxError as e:
            error(f"Error rendering line {e.lineno} of file {e.filename}. Got: {e.message}")
            sys.exit(1)
        except TemplateError as e:
            error(f"Error rendering file {inputfile}. Got: {e.message}")
            sys.exit(1)
        paramline = []
        for parameter in overrides:
            newparam = "%s" % parameter.upper()
            paramline.append(f"-P {parameter}=${newparam}")
        parameterline = " ".join(paramline)
        paramfileline = "--paramfile $PARAMFILE" if paramfile is not None else ""
        gitbase = os.popen('git rev-parse --show-prefix 2>/dev/null').read().strip()
        workflowfile = templ.render(plan=plan, inputfile=inputfile, parameters=overrides, parameterline=parameterline,
                                    paramfileline=paramfileline, paramfile=paramfile, gitbase=gitbase, runner=runner,
                                    client=client, kube=kube, kubetype=kubetype, runscript=runscript)
        return workflowfile

    def create_tekton_pipeline(self, plan, inputfile, paramfile=None, overrides={}, kube=False):
        if not kube:
            inputfile = os.path.expanduser(inputfile) if inputfile is not None else 'kcli_plan.yml'
            basedir = os.path.dirname(inputfile)
            if basedir == "":
                basedir = '.'
            if not os.path.exists(inputfile):
                error("No input file found nor default kcli_plan.yml. Leaving....")
                sys.exit(1)
            if plan is None:
                plan = os.path.basename(inputfile).replace('.yml', '').replace('.yaml', '')
        else:
            inputfile = None
            if plan is None:
                plan = 'testk'
        if 'plan' in overrides:
            del overrides['plan']
        client = 'local'
        if 'client' in overrides:
            client = overrides['client']
            del overrides['client']
        kubetype = 'generic'
        if kube:
            if 'kubetype' in overrides:
                kubetype = overrides['kubetype']
                del overrides['kubetype']
        workflowdir = os.path.dirname(common.__file__)
        env = Environment(loader=FileSystemLoader(workflowdir), extensions=['jinja2.ext.do'], trim_blocks=True,
                          lstrip_blocks=True)
        for jinjafilter in jinjafilters.jinjafilters:
            env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        try:
            workflowfile = "pipeline_kube.yml.j2" if kube else "pipeline.yml.j2"
            templ = env.get_template(os.path.basename(workflowfile))
        except TemplateSyntaxError as e:
            error(f"Error rendering line {e.lineno} of file {e.filename}. Got: {e.message}")
            sys.exit(1)
        except TemplateError as e:
            error(f"Error rendering file {inputfile}. Got: {e.message}")
            sys.exit(1)
        paramline = []
        for parameter in overrides:
            paramline.append('-P %s="$%s"' % (parameter, parameter.upper()))
        parameterline = " ".join(paramline)
        giturl, gitbase = None, None
        paramfileline = None
        if kube:
            paramfiledata = ''
            if paramfile is not None:
                paramfiledata = open(paramfile).read()
                paramfileline = 'echo -ne """%s""" > kcli_parameters.yml' % paramfiledata
                paramfileline = paramfileline.replace('\n', '\n      ')
            if "pull_secret" not in paramfiledata and "pull_secret" not in overrides:
                parameterline += " -P pull_secret=/home/tekton/.kcli/openshift_pull.json"
        else:
            paramfileline = "--paramfile $PARAMFILE" if paramfile is not None else ""
            giturl = os.popen('git config --get remote.origin.url').read().strip()
            gitbase = os.popen('git rev-parse --show-prefix 2>/dev/null').read().strip()
        workflowfile = templ.render(plan=plan, inputfile=inputfile, parameters=overrides, parameterline=parameterline,
                                    paramfileline=paramfileline, paramfile=paramfile, gitbase=gitbase, giturl=giturl,
                                    client=client, kube=kube, kubetype=kubetype)
        return workflowfile

    def info_kube_generic(self, quiet, web=False):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        inputfile = f'{plandir}/masters.yml'
        return self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_kind(self, quiet, web=False):
        plandir = os.path.dirname(kind.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan.yml'
        return self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_microshift(self, quiet, web=False):
        plandir = os.path.dirname(microshift.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan.yml'
        return self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_k3s(self, quiet, web=False):
        plandir = os.path.dirname(k3s.create.__code__.co_filename)
        inputfile = f'{plandir}/masters.yml'
        return self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_hypershift(self, quiet, web=False):
        plandir = os.path.dirname(hypershift.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan.yml'
        return self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_openshift(self, quiet, web=False):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        inputfile = f'{plandir}/masters.yml'
        return self.info_plan(inputfile, quiet=quiet, web=web)

    def list_apps_generic(self, quiet=True):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        appdir = plandir + '/apps'
        return sorted([x for x in os.listdir(appdir) if os.path.isdir(f"{appdir}/{x}") and x != '__pycache__'])

    def list_apps_openshift(self, quiet=True, installed=False):
        if installed:
            header = 'subscription.operators.coreos.com/'
            results = []
            manifestscmd = "oc get subscriptions.operators.coreos.com -A -o name"
            manifestsdata = os.popen(manifestscmd).read().split('\n')
        else:
            header = 'packagemanifest.packages.operators.coreos.com/'
            results = ['autolabeller', 'users', 'metal3']
            manifestscmd = "oc get packagemanifest -n openshift-marketplace -o name"
            manifestsdata = os.popen(manifestscmd).read().split('\n')
        results.extend([entry.replace(header, '') for entry in manifestsdata])
        return sorted(results)

    def create_app_generic(self, app, overrides={}, outputdir=None):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        appdir = f"{plandir}/apps/{app}"
        common.kube_create_app(self, appdir, overrides=overrides, outputdir=outputdir)

    def delete_app_generic(self, app, overrides={}):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        appdir = f"{plandir}/apps/{app}"
        common.kube_delete_app(self, appdir, overrides=overrides)

    def info_app_generic(self, app):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        appdir = f"{plandir}/apps/{app}"
        default_parameter_file = f"{appdir}/kcli_default.yml"
        if not os.path.exists(appdir):
            warning(f"App {app} not supported")
        elif not os.path.exists(default_parameter_file):
            print(f"{app}_version: latest")
        else:
            with open(default_parameter_file, 'r') as f:
                print(f.read().strip())

    def create_app_openshift(self, app, overrides={}, outputdir=None):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        if app in LOCAL_OPENSHIFT_APPS:
            appdir = f"{plandir}/apps/{app}"
            common.kube_create_app(self, appdir, overrides=overrides, outputdir=outputdir)
        else:
            appdir = f"{plandir}/apps"
            common.openshift_create_app(self, appdir, overrides=overrides, outputdir=outputdir)

    def delete_app_openshift(self, app, overrides={}):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        if app in LOCAL_OPENSHIFT_APPS:
            appdir = f"{plandir}/apps/{app}"
            common.kube_delete_app(self, appdir, overrides=overrides)
        else:
            appdir = f"{plandir}/apps"
            common.openshift_delete_app(self, appdir, overrides=overrides)

    def info_app_openshift(self, app):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        if app not in LOCAL_OPENSHIFT_APPS:
            name, source, defaultchannel, csv, description, target_namespace, channels, crd = common.olm_app(app)
            if name is None:
                warning(f"Couldn't find any app matching {app}")
            else:
                pprint(f"Providing information for app {name}")
                print(f"source: {source}")
                print(f"channels: {channels}")
                print(f"channel: {defaultchannel}")
                print(f"target namespace: {target_namespace}")
                print(f"csv: {csv}")
                print(f"description:\n{description}")
                app = name
        appdir = f"{plandir}/apps/{app}"
        default_parameter_file = f"{appdir}/kcli_default.yml"
        if os.path.exists(default_parameter_file):
            with open(default_parameter_file, 'r') as f:
                print(f.read().strip())

    def download_openshift_installer(self, overrides={}):
        pull_secret = overrides.get('pull_secret', 'openshift_pull.json')
        version = overrides.get('version', 'stable')
        tag = overrides.get('tag', OPENSHIFT_TAG)
        upstream = overrides.get('upstream', False)
        baremetal = overrides.get('baremetal', False)
        macosx = True if os.path.exists('/Users') else False
        if version == 'ci':
            run = openshift.get_ci_installer(pull_secret, tag=tag, macosx=macosx, upstream=upstream, debug=self.debug,
                                             baremetal=baremetal)
        elif version == 'nightly':
            run = openshift.get_downstream_installer(nightly=True, tag=tag, macosx=macosx, debug=self.debug,
                                                     baremetal=baremetal, pull_secret=pull_secret)
        elif upstream:
            run = openshift.get_upstream_installer(tag=tag, macosx=macosx, debug=self.debug)
        else:
            run = openshift.get_downstream_installer(tag=tag, macosx=macosx, debug=self.debug, baremetal=baremetal,
                                                     pull_secret=pull_secret)
        if run != 0:
            error("Couldn't download openshift-install")
        return run

    def create_vm_playbook(self, name, profile, overrides={}, store=False, env=None):
        jinjadir = os.path.dirname(jinjafilters.__file__)
        if not os.path.exists('filter_plugins'):
            pprint("Creating symlink to kcli jinja filters")
            os.symlink(jinjadir, 'filter_plugins')
        if env is None:
            playbookdir = os.path.dirname(common.__file__)
            env = Environment(loader=FileSystemLoader(playbookdir), extensions=['jinja2.ext.do'],
                              trim_blocks=True, lstrip_blocks=True)
            for jinjafilter in jinjafilters.jinjafilters:
                env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        dirs = []
        if 'scripts' not in profile:
            profile['scripts'] = []
        profile['cmds'] = '\n'.join(profile['cmds']) if 'cmds' in profile else None
        if 'files' in profile:
            files = []
            for _file in profile['files']:
                if isinstance(_file, str):
                    entry = {'path': f'/root/{_file}', 'origin': _file, 'mode': 700}
                else:
                    entry = _file
                if os.path.isdir(entry['origin']):
                    dirs.append(entry['origin'])
                    continue
                if entry['path'].count('/') > 2 and os.path.dirname(entry['path']) not in dirs:
                    dirs.append(os.path.dirname(entry['path']))
                files.append(entry)
            profile['files'] = files
        else:
            profile['files'] = []
        try:
            templ = env.get_template(os.path.basename("playbook.j2"))
        except TemplateSyntaxError as e:
            error(f"Error rendering line {e.lineno} of file {e.filename}. Got: {e.message}")
            sys.exit(1)
        except TemplateError as e:
            error(f"Error rendering playbook. Got: {e.message}")
            sys.exit(1)
        hostname = overrides.get('hostname', name)
        profile['hostname'] = hostname
        if 'info' in overrides:
            del overrides['info']
        profile['overrides'] = overrides
        profile['dirs'] = dirs
        playbookfile = templ.render(**profile)
        playbookfile = '\n'.join([line for line in playbookfile.split('\n') if line.strip() != ""])
        if store:
            pprint(f"Generating playbook_{hostname}.yml")
            with open(f"playbook_{hostname}.yml", 'w') as f:
                f.write(playbookfile)
        else:
            print(playbookfile)

    def create_playbook(self, inputfile, overrides={}, store=False):
        playbookdir = os.path.dirname(common.__file__)
        env = Environment(loader=FileSystemLoader(playbookdir), extensions=['jinja2.ext.do'],
                          trim_blocks=True, lstrip_blocks=True)
        for jinjafilter in jinjafilters.jinjafilters:
            env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        inputfile = os.path.expanduser(inputfile) if inputfile is not None else 'kcli_plan.yml'
        basedir = os.path.dirname(inputfile)
        if basedir == "":
            basedir = '.'
        pprint(f"Using plan {inputfile}...")
        pprint("Make sure to export ANSIBLE_JINJA2_EXTENSIONS=jinja2.ext.do")
        jinjadir = os.path.dirname(jinjafilters.__file__)
        if not os.path.exists('filter_plugins'):
            pprint("Creating symlink to kcli jinja filters")
            os.symlink(jinjadir, 'filter_plugins')
        if not os.path.exists(inputfile):
            error("No input file found nor default kcli_plan.yml. Leaving....")
            sys.exit(1)
        plan = 'xxx'
        entries, overrides, basefile, basedir = self.process_inputfile(plan, inputfile, overrides=overrides, full=True)
        config_data = {}
        config_data['config_host'] = self.ini[self.client].get('host', '127.0.0.1')
        config_data['config_type'] = config_data.get('config_type', 'kvm')
        default_user = getuser() if config_data['config_type'] == 'kvm'\
            and config_data['config_host'] in ['localhost', '127.0.0.1'] else 'root'
        config_data['config_user'] = config_data.get('config_user', default_user)
        overrides.update(config_data)
        renderfile = self.process_inputfile(plan, inputfile, overrides=overrides, onfly=False, ignore=True)
        try:
            data = yaml.safe_load(renderfile)
        except:
            error("Couldnt' parse plan. Leaving....")
            sys.exit(1)
        for key in data:
            if 'type' in data[key] and data[key]['type'] != 'kvm':
                continue
            elif 'scripts' not in data[key] and 'files' not in data[key] and 'cmds' not in data[key]:
                continue
            else:
                self.create_vm_playbook(key, data[key], overrides=overrides, store=store, env=env)

    def create_plan_template(self, directory, overrides, skipfiles=False, skipscripts=False):
        pprint(f"Creating plan template in {directory}...")
        if container_mode():
            directory = f"/workdir/{directory}"
        if not os.path.exists(directory):
            os.makedirs(directory)
            os.makedirs(f"{directory}/scripts")
            os.makedirs(f"{directory}/files")
        else:
            warning(f"Directory {directory} already exists")
        ori_data = {'cluster': 'testk', 'image': 'centos8stream', 'vms_number': 3, 'memory': 8192, 'numcpus': 4,
                    'nets': ['default', {'name': 'default', 'type': 'e1000'}],
                    'disks': [10, {'size': 20, 'interface': 'scsi'}], 'bestguitarist': 'jimihendrix',
                    'bestmovie': 'interstellar'}
        data = ori_data.copy()
        data.update(overrides)
        with open(f"{directory}/README.md", "w") as f:
            f.write("This is a sample plan for you to understand how to create yours. It showcases:\n\n")
            f.write("- how the plan looks like\n- can optionally use jinja\n- defines default parameters")
            f.write("\n- can overrides those parameters at run time")
            f.write("\n- can include hardware spec, inject files in different ways or scripts\n")
        with open(f"{directory}/kcli_default.yml", "w") as f:
            f.write("# Default parameter values for your plan\n# This is a YAML-formatted file\n")
            yaml.safe_dump(data, f, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                           sort_keys=True)
        with open(f"{directory}/kcli_parameters.yml.sample", "w") as f:
            f.write("# Optional runtime parameter values for your plan\n# This is a YAML-formatted file\n")
            yaml.safe_dump(data, f, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                           sort_keys=True)
        filessection = """ files:
 - path: /etc/motd
   content: Welcome to cluster {{ cluster }}
 - path: /etc/myfile01
   origin: files/myfile01\n""" if not skipfiles else ''
        scriptssection = """ scripts:
 - scripts/script01.sh
{% if num == 0 %}
 - scripts/script02.sh
{% endif %}\n""" if not skipscripts else ''
        plankeys = "\n".join([" %s: {{ %s }}" % (key, key) for key in sorted(overrides) if key not in ori_data])
        plantemplatedata = """{% for num in range(0, vms_number) %}

{{ cluster }}-{{ num }}:
 image: {{ image }}
 memory: {{ memory }}
 numcpus: {{ numcpus }}
 disks: {{ disks }}
 nets: {{ nets }}"""
        plantemplatedata += f"\n{filessection}{scriptssection}{plankeys}"
        plantemplatedata += "{% endfor %}"
        with open(f"{directory}/kcli_plan.yml", "w") as f:
            f.write(plantemplatedata)
        if not skipscripts:
            script01data = '#!/bin/bash\necho best guitarist is {{ bestguitarist }}\n'
            with open(f"{directory}/scripts/script01.sh", "w") as f:
                f.write(script01data)
            script02data = '#!/bin/bash\necho i am vm {{ name }} >/tmp/plan.txt'
            with open(f"{directory}/scripts/script02.sh", "w") as f:
                f.write(script02data)
        if not skipfiles:
            myfile01data = 'a good movie to see is {{ bestmovie }}'
            with open(f"{directory}/files/myfile01", "w") as f:
                f.write(myfile01data)

    def create_workflow(self, workflow, overrides={}, outputdir=None, run=True):
        target = overrides.get('target')
        if target is not None:
            if isinstance(target, str):
                tunnel, tunnelhost, tunnelport, tunneluser, vmport = False, None, 22, 'root', None
                if '@' in target:
                    target = target.split('@')
                    if len(target) == 2:
                        user, hostname = target
                        ip = hostname
                    else:
                        msg = f"Invalid target {target}"
                        error(msg)
                        return {'result': 'failure', 'reason': msg}
                else:
                    user, hostname, ip = 'root', target, target
            elif isinstance(target, dict):
                hostname = target.get('hostname')
                user = target.get('user')
                ip = target.get('ip')
                vmport = target.get('vmport')
                tunnel = self.tunnel
                tunnelhost = self.tunnelhost
                tunnelport = self.tunnelport
                tunneluser = self.tunneluser
        requirefile = overrides.get('requirefile')
        if requirefile is not None:
            requirefile = os.path.expanduser(requirefile)
            while not os.path.exists(requirefile):
                pprint(f"Waiting 5s for file {requirefile} to be present")
                sleep(5)
        files = overrides.get('files', [])
        scripts = overrides.get('scripts', [])
        cmds = overrides.get('cmds', [])
        if not scripts and not cmds:
            if workflow.endswith('.sh'):
                scripts = [workflow]
            else:
                msg = "No scripts provided"
                error(msg)
                return {'result': 'failure', 'reason': msg}
        finalscripts = []
        with TemporaryDirectory() as tmpdir:
            destdir = outputdir or tmpdir
            directoryfiles = []
            directories = []
            for index, entry in enumerate(scripts + files):
                if isinstance(entry, dict):
                    origin = os.path.expanduser(entry.get('origin') or entry.get('path'))
                    content = entry.get('content')
                else:
                    origin = os.path.expanduser(entry)
                    content = None
                if origin in directories:
                    continue
                elif not os.path.exists(origin):
                    msg = f"Origin file {origin} not found"
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
                elif os.path.isdir(origin):
                    origindir = entry if not isinstance(entry, dict) else entry.get('origin') or entry.get('path')
                    if not os.path.exists(f"{destdir}/{origindir}"):
                        os.makedirs(f"{destdir}/{origindir}")
                        directories.append(origin)
                        for _fic in os.listdir(origindir):
                            directoryfiles.append(f'{origindir}/{_fic}')
                    continue
                path = os.path.basename(origin)
                rendered = content or self.process_inputfile(workflow, origin, overrides=overrides)
                destfile = f"{destdir}/{path}"
                with open(destfile, 'w') as f:
                    f.write(rendered)
                if index < len(scripts):
                    finalscripts.append(path)
            for entry in directoryfiles:
                path = os.path.basename(entry)
                rendered = self.process_inputfile(workflow, entry, overrides=overrides)
                destfile = f"{destdir}/{path}"
                with open(destfile, 'w') as f:
                    f.write(rendered)
            if cmds:
                cmdscontent = '\n'.join(cmds)
                destfile = f"{destdir}/cmds.sh"
                with open(destfile, 'w') as f:
                    f.write(cmdscontent)
                finalscripts.append('cmds.sh')
            if not run:
                pprint("Not running as dry mode was requested")
                return {'result': 'success'}
            if target is not None:
                remotedir = f"/tmp/{os.path.basename(tmpdir)}"
                scpcmd = scp(hostname, ip=ip, user=user, source=tmpdir, destination=remotedir, download=False,
                             insecure=True, tunnel=tunnel, tunnelhost=tunnelhost, tunnelport=tunnelport,
                             tunneluser=tunneluser, vmport=vmport)
                os.system(scpcmd)
                cmd = [f"cd {remotedir}"]
                for script in finalscripts:
                    cmd.append(f'bash {script}' if script.endswith('.sh') else f'./{script}')
                cmd.append(f"rm -rf {remotedir}")
                cmd = ';'.join(cmd)
                pprint(f"Running script {script} on {hostname}")
                sshcommand = ssh(hostname, ip=ip, user=user, cmd=cmd, tunnel=tunnel, tunnelhost=tunnelhost,
                                 tunnelport=tunnelport, tunneluser=tunneluser, vmport=vmport)
                os.system(sshcommand)
            else:
                os.chdir(destdir)
                for script in finalscripts:
                    os.chmod(script, 0o700)
                    pprint(f"Running script {script} locally")
                    command = f'bash {script}' if script.endswith('.sh') else f'./{script}'
                    result = call(command, shell=True)
                    if result != 0:
                        msg = f"Failure in script {script}"
                        error(msg)
                        return {'result': 'failure', 'reason': msg}
        return {'result': 'success'}

    def info_keyword(self, keyword):
        default = self.default
        keywords = self.list_keywords()
        if keyword not in keywords:
            error(f"Keyword {keyword} not found")
            return 1
        else:
            print("Default value: %s" % default[keyword])
            print("Current value: %s" % keywords[keyword])
            kvirt_dir = os.path.dirname(self.__init__.__code__.co_filename)
            with open(f'{kvirt_dir}/keywords.yaml') as f:
                keywords_info = yaml.safe_load(f)
                if keyword in keywords_info and keywords_info[keyword] is not None:
                    pprint("Detailed information:")
                    pprint(keywords_info[keyword].strip())
        return 0

    def import_in_kube(self, network='default', dest=None, secure=False):
        kubectl = 'oc' if which('oc') is not None else 'kubectl'
        kubectl += ' -n kcli-infra'
        plandir = os.path.dirname(common.get_kubectl.__code__.co_filename)
        oriconf = os.path.expanduser('~/.kcli')
        orissh = os.path.expanduser('~/.ssh')
        self.ini[self.client]
        with TemporaryDirectory() as tmpdir:
            if self.type == 'kvm' and self.ini[self.client].get('host', 'localhost') in ['localhost', '127.0.0.1']:
                oriconf = f"{tmpdir}/.kcli"
                orissh = f"{tmpdir}/.ssh"
                os.mkdir(oriconf)
                os.mkdir(orissh)
                kvm_overrides = {'network': network, 'user': getuser(), 'client': self.client}
                kcliconf = self.process_inputfile('xxx', f"{plandir}/local_kcli_conf.j2", overrides=kvm_overrides)
                with open(f"{oriconf}/config.yml", 'w') as _f:
                    _f.write(kcliconf)
                if secure:
                    sshcmd = f"ssh-keygen -t rsa -N '' -f {orissh}/id_rsa > /dev/null"
                    call(sshcmd, shell=True)
                    authorized_keys_file = os.path.expanduser('~/.ssh/authorized_keys')
                    file_mode = 'a' if os.path.exists(authorized_keys_file) else 'w'
                    with open(authorized_keys_file, file_mode) as f:
                        publickey = open(f"{orissh}/id_rsa.pub").read().strip()
                        f.write(f"\n{publickey}")
                else:
                    publickeyfile = common.get_ssh_pub_key()
                    if publickeyfile is not None:
                        identityfile = publickeyfile.replace('.pub', '')
                        copy2(publickeyfile, orissh)
                        copy2(identityfile, orissh)
                    else:
                        warning("No public key was found")
            elif self.type == 'kubevirt':
                oriconf = f"{tmpdir}/.kcli"
                os.mkdir(oriconf)
                kubeconfig_overrides = {'kubeconfig': False, 'client': self.client}
                destkubeconfig = self.options.get('kubeconfig', os.environ.get('KUBECONFIG'))
                if destkubeconfig is not None:
                    destkubeconfig = os.path.expanduser(destkubeconfig)
                    copy2(destkubeconfig, f"{oriconf}/kubeconfig")
                    kubeconfig_overrides['kubeconfig'] = True
                kcliconf = self.process_inputfile('xxx', f"{plandir}/kubevirt_kcli_conf.j2",
                                                  overrides=kubeconfig_overrides)
                with open(f"{oriconf}/config.yml", 'w') as _f:
                    _f.write(kcliconf)
            if dest is not None:
                desx = f"{dest}/99-kcli-conf-cm.yaml"
                cmcmd = f'KUBECONFIG={plandir}/fake_kubeconfig.json '
                cmcmd += f"{kubectl} create cm kcli-conf --from-file={oriconf} --dry-run=client -o yaml > {desx}"
                call(cmcmd, shell=True)
                desx = f"{dest}/99-kcli-ssh-cm.yaml"
                cmcmd = f'KUBECONFIG={plandir}/fake_kubeconfig.json  '
                cmcmd += f"{kubectl} create cm kcli-ssh --from-file={orissh} --dry-run=client -o yaml > {desx}"
                call(cmcmd, shell=True)
            else:
                cmcmd = f"{kubectl} create ns kcli-infra --dry-run=client -o yaml | {kubectl} apply -f -"
                call(cmcmd, shell=True)
                cmcmd = f"{kubectl} get cm kcli-conf >/dev/null 2>&1 && {kubectl} delete cm kcli-conf ; "
                cmcmd += f"{kubectl} create cm kcli-conf --from-file={oriconf}"
                call(cmcmd, shell=True)
                cmcmd = f"{kubectl} get cm kcli-ssh >/dev/null 2>&1 && {kubectl} delete cm kcli-ssh ; "
                cmcmd += f"{kubectl} create cm kcli-ssh --from-file={orissh}"
                call(cmcmd, shell=True)
        return {'result': 'success'}
