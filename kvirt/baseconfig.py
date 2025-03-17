# -*- coding: utf-8 -*-

from getpass import getuser
from ipaddress import ip_address, ip_network
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined as strictundefined
from jinja2.runtime import Undefined as defaultundefined
from jinja2.exceptions import TemplateSyntaxError, TemplateError, TemplateNotFound
from kvirt import common
from kvirt.common import error, pprint, warning, container_mode, ssh, scp, NoAliasDumper, olm_app
from kvirt.common import PlanLoader, get_kubetype, detect_openshift_version, valid_ip
from kvirt import defaults as kdefaults
from kvirt.cluster import hypershift
from kvirt.cluster import k3s
from kvirt.cluster import kubeadm
from kvirt.cluster import microshift
from kvirt.cluster import openshift
from kvirt.cluster import rke2
from kvirt.jinjafilters import jinjafilters
import os
from random import choice
import re
import stat
from subprocess import call
import sys
from shutil import copytree, which, copy2
from tempfile import TemporaryDirectory
from time import sleep
import yaml


def libvirt_macosx():
    return which('brew') is not None and 'libvirt started' in os.popen('brew services list').read()


class Kbaseconfig:
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
            if not offline and not os.path.exists('/var/run/libvirt/libvirt-sock')\
               and not os.path.exists('/var/run/libvirt/libvirt-admin-sock')\
               and not os.path.exists('/var/run/libvirt/virtqemud-sock'):
                if os.path.exists('/i_am_a_container') and os.environ.get('KUBERNETES_SERVICE_HOST') is not None:
                    _type = 'kubevirt'
                elif not libvirt_macosx():
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
        defaults['nets'] = default.get('nets', kdefaults.NETS)
        defaults['pool'] = default.get('pool', kdefaults.POOL)
        defaults['image'] = default.get('image', kdefaults.IMAGE)
        defaults['numcpus'] = int(default.get('numcpus', kdefaults.NUMCPUS))
        defaults['cpumodel'] = default.get('cpumodel', kdefaults.CPUMODEL)
        defaults['cpuflags'] = default.get('cpuflags', kdefaults.CPUFLAGS)
        defaults['cpupinning'] = default.get('cpupinning', kdefaults.CPUPINNING)
        defaults['numa'] = default.get('numa', kdefaults.NUMA)
        defaults['numamode'] = default.get('numamode', kdefaults.NUMAMODE)
        defaults['pcidevices'] = default.get('pcidevides', kdefaults.PCIDEVICES)
        defaults['memory'] = int(default.get('memory', kdefaults.MEMORY))
        defaults['disks'] = default.get('disks', kdefaults.DISKS)
        defaults['disksize'] = default.get('disksize', kdefaults.DISKSIZE)
        defaults['diskinterface'] = default.get('diskinterface', kdefaults.DISKINTERFACE)
        defaults['diskthin'] = default.get('diskthin', kdefaults.DISKTHIN)
        defaults['guestid'] = default.get('guestid', kdefaults.GUESTID)
        defaults['vnc'] = bool(default.get('vnc', kdefaults.VNC))
        defaults['cloudinit'] = bool(default.get('cloudinit', kdefaults.CLOUDINIT))
        defaults['guestagent'] = bool(default.get('guestagent', kdefaults.GUESTAGENT))
        defaults['reserveip'] = bool(default.get('reserveip', kdefaults.RESERVEIP))
        defaults['reservedns'] = bool(default.get('reservedns', kdefaults.RESERVEDNS))
        defaults['reservehost'] = bool(default.get('reservehost', kdefaults.RESERVEHOST))
        defaults['nested'] = bool(default.get('nested', kdefaults.NESTED))
        defaults['start'] = bool(default.get('start', kdefaults.START))
        defaults['autostart'] = bool(default.get('autostart', kdefaults.AUTOSTART))
        defaults['tunnel'] = bool(default.get('tunnel', kdefaults.TUNNEL))
        defaults['tunnelhost'] = default.get('tunnelhost', kdefaults.TUNNELHOST)
        defaults['tunnelport'] = default.get('tunnelport', kdefaults.TUNNELPORT)
        defaults['tunneluser'] = default.get('tunneluser', kdefaults.TUNNELUSER)
        defaults['tunneldir'] = default.get('tunneldir', kdefaults.TUNNELDIR)
        defaults['insecure'] = bool(default.get('insecure', kdefaults.INSECURE))
        defaults['keys'] = default.get('keys', kdefaults.KEYS)
        defaults['cmds'] = default.get('cmds', kdefaults.CMDS)
        defaults['dns'] = default.get('dns', kdefaults.DNS)
        defaults['domain'] = default.get('file', kdefaults.DOMAIN)
        defaults['scripts'] = default.get('script', kdefaults.SCRIPTS)
        defaults['files'] = default.get('files', kdefaults.FILES)
        defaults['iso'] = default.get('iso', kdefaults.ISO)
        defaults['netmasks'] = default.get('netmasks', kdefaults.NETMASKS)
        defaults['gateway'] = default.get('gateway', kdefaults.GATEWAY)
        defaults['sharedkey'] = default.get('sharedkey', kdefaults.SHAREDKEY)
        defaults['enableroot'] = default.get('enableroot', kdefaults.ENABLEROOT)
        defaults['privatekey'] = default.get('privatekey', kdefaults.PRIVATEKEY)
        defaults['networkwait'] = default.get('networkwait', kdefaults.NETWORKWAIT)
        defaults['rhnregister'] = default.get('rhnregister', kdefaults.RHNREGISTER)
        defaults['rhnunregister'] = default.get('rhnunregister', kdefaults.RHNUNREGISTER)
        defaults['rhnserver'] = default.get('rhnserver', kdefaults.RHNSERVER)
        defaults['rhnuser'] = default.get('rhnuser', kdefaults.RHNUSER)
        defaults['rhnpassword'] = default.get('rhnpassword', kdefaults.RHNPASSWORD)
        defaults['rhnactivationkey'] = default.get('rhnactivationkey', kdefaults.RHNAK)
        defaults['rhnorg'] = default.get('rhnorg', kdefaults.RHNORG)
        defaults['rhnpool'] = default.get('rhnpool', kdefaults.RHNPOOL)
        defaults['tags'] = default.get('tags', kdefaults.TAGS)
        defaults['flavor'] = default.get('flavor', kdefaults.FLAVOR)
        defaults['keep_networks'] = default.get('keep_networks', kdefaults.KEEP_NETWORKS)
        defaults['dnsclient'] = default.get('dnsclient', kdefaults.DNSCLIENT)
        defaults['storemetadata'] = default.get('storemetadata', kdefaults.STORE_METADATA)
        defaults['notify'] = default.get('notify', kdefaults.NOTIFY)
        defaults['slacktoken'] = default.get('slacktoken', kdefaults.SLACKTOKEN)
        defaults['pushbullettoken'] = default.get('pushbullettoken', kdefaults.PUSHBULLETTOKEN)
        defaults['notifycmd'] = default.get('notifycmd', kdefaults.NOTIFYCMD)
        defaults['notifyscript'] = default.get('notifyscript', kdefaults.NOTIFYSCRIPT)
        defaults['notifymethods'] = default.get('notifymethods', kdefaults.NOTIFYMETHODS)
        defaults['slackchannel'] = default.get('slackchannel', kdefaults.SLACKCHANNEL)
        defaults['mailserver'] = default.get('mailserver', kdefaults.MAILSERVER)
        defaults['mailfrom'] = default.get('mailfrom', kdefaults.MAILFROM)
        defaults['mailto'] = default.get('mailto', kdefaults.MAILTO)
        defaults['sharedfolders'] = default.get('sharedfolders', kdefaults.SHAREDFOLDERS)
        defaults['cmdline'] = default.get('cmdline', kdefaults.CMDLINE)
        defaults['placement'] = default.get('placement', kdefaults.PLACEMENT)
        defaults['cpuhotplug'] = bool(default.get('cpuhotplug', kdefaults.CPUHOTPLUG))
        defaults['memoryhotplug'] = bool(default.get('memoryhotplug', kdefaults.MEMORYHOTPLUG))
        defaults['virttype'] = default.get('virttype', kdefaults.VIRTTYPE)
        defaults['tpm'] = default.get('tpm', kdefaults.TPM)
        defaults['rng'] = default.get('rng', kdefaults.RNG)
        defaults['vmuser'] = default.get('vmuser', kdefaults.VMUSER)
        defaults['vmport'] = default.get('vmport', kdefaults.VMPORT)
        defaults['vmrules'] = default.get('vmrules', kdefaults.VMRULES)
        defaults['vmrules_strict'] = default.get('vmrules_strict', kdefaults.VMRULES_STRICT)
        defaults['securitygroups'] = default.get('securitygroups', kdefaults.SECURITYGROUPS)
        defaults['rootpassword'] = default.get('rootpassword', kdefaults.ROOTPASSWORD)
        defaults['wait'] = default.get('wait', kdefaults.WAIT)
        defaults['waitcommand'] = default.get('waitcommand', kdefaults.WAITCOMMAND)
        defaults['waittimeout'] = default.get('waittimeout', kdefaults.WAITTIMEOUT)
        defaults['tempkey'] = default.get('tempkey', kdefaults.TEMPKEY)
        defaults['bmc_user'] = default.get('bmc_user', kdefaults.BMC_USER)
        defaults['bmc_password'] = default.get('bmc_password', kdefaults.BMC_PASSWORD)
        defaults['bmc_model'] = default.get('bmc_model', kdefaults.BMC_MODEL)
        for key in default:
            if key not in defaults:
                defaults[key] = default[key]
        currentplanfile = f"{os.environ.get('HOME')}/.kcli/plan"
        if os.path.exists(currentplanfile):
            self.currentplan = open(currentplanfile).read().strip()
        else:
            self.currentplan = 'kvirt'
        self.default = defaults
        profilefile = default.get('profiles', f"{os.environ.get('HOME')}/.kcli/profiles.yml")
        profilefile = os.path.expanduser(profilefile)
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                try:
                    self.profiles = yaml.safe_load(entries)
                except yaml.scanner.ScannerError as err:
                    error("Couldn't parse yaml in .kcli/profiles.yml. Leaving...")
                    error(err)
                    sys.exit(1)
                if self.profiles is None:
                    self.profiles = {}
                wrongprofiles = [key for key in self.profiles if 'type' in self.profiles[key] and
                                 self.profiles[key]['type'] not in ['vm', 'container']]
                if wrongprofiles:
                    error(f"Incorrect type in profiles {','.join(wrongprofiles)} in .kcli/profiles.yml")
                    sys.exit(1)
        flavorsfile = default.get('flavors', f"{os.environ.get('HOME')}/.kcli/flavors.yml")
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
        confpoolfile = default.get('confpools', f"{os.environ.get('HOME')}/.kcli/confpools.yml")
        confpoolfile = os.path.expanduser(confpoolfile)
        if not os.path.exists(confpoolfile):
            self.confpools = {}
        else:
            with open(confpoolfile, 'r') as entries:
                try:
                    self.confpools = yaml.safe_load(entries)
                except yaml.scanner.ScannerError as e:
                    error(f"Couldn't parse yaml in .kcli/confpools.yml. Hit {e}...")
                    sys.exit(1)
                if self.confpools is None:
                    self.confpools = {}
        self.clusterprofiles = {}
        clusterprofilesdir = f"{os.path.dirname(sys.modules[Kbaseconfig.__module__].__file__)}/cluster/profiles"
        for clusterprofile in os.listdir(clusterprofilesdir):
            entry = clusterprofile.replace('.yml', '')
            self.clusterprofiles[entry] = yaml.safe_load(open(f"{clusterprofilesdir}/{clusterprofile}"))
        clusterprofilesfile = default.get('clusterprofiles', f"{os.environ.get('HOME')}/.kcli/clusterprofiles.yml")
        clusterprofilesfile = os.path.expanduser(clusterprofilesfile)
        if os.path.exists(clusterprofilesfile):
            with open(clusterprofilesfile, 'r') as entries:
                try:
                    self.clusterprofiles.update(yaml.safe_load(entries))
                except yaml.scanner.ScannerError as e:
                    error(f"Couldn't parse yaml in .kcli/clusterprofiles.yml. Hit {e}")
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
        self.options = defaults
        self.options.update(self.ini[self.client])
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
        self.pool = options.get('pool')
        self.image = options.get('image')
        self.tunnel = bool(options.get('tunnel'))
        self.tunnelhost = options.get('tunnelhost')
        self.tunnelport = options.get('tunnelport')
        self.tunneluser = options.get('tunneluser')
        if self.tunnelhost is None and self.type == 'kvm' and self.host != '127.0.0.1':
            self.tunnelhost = self.host.replace('[', '').replace(']', '')
            self.tunnelport = self.port
            self.tunneluser = self.user
        self.tunneldir = options.get('tunneldir')
        self.insecure = bool(options.get('insecure'))
        self.nets = options.get('nets')
        self.cpumodel = options.get('cpumodel')
        self.cpuflags = options.get('cpuflags')
        self.cpupinning = options.get('cpupinning')
        self.numamode = options.get('numamode')
        self.numa = options.get('numa')
        self.pcidevices = options.get('pcidevices')
        self.tpm = options.get('tpm')
        self.rng = options.get('rng')
        self.numcpus = options.get('numcpus')
        self.memory = options.get('memory')
        self.disks = options.get('disks')
        self.disksize = options.get('disksize')
        self.diskinterface = options.get('diskinterface')
        self.diskthin = options.get('diskthin')
        self.guestid = options.get('guestid')
        self.vnc = options.get('vnc')
        self.cloudinit = options.get('cloudinit')
        self.guestagent = options.get('guestagent')
        self.reserveip = options.get('reserveip')
        self.reservedns = options.get('reservedns')
        self.reservehost = options.get('reservehost')
        self.nested = options.get('nested')
        self.start = options.get('start')
        self.autostart = options.get('autostart')
        self.iso = options.get('iso')
        self.keys = options.get('keys')
        self.cmds = options.get('cmds')
        self.netmasks = options.get('netmasks')
        self.gateway = options.get('gateway')
        self.sharedkey = options.get('sharedkey')
        self.enableroot = options.get('enableroot')
        self.dns = options.get('dns')
        self.domain = options.get('domain')
        self.scripts = options.get('scripts')
        self.files = options.get('files')
        self.networkwait = options.get('networkwait')
        self.privatekey = options.get('privatekey')
        self.rhnregister = options.get('rhnregister')
        self.rhnunregister = options.get('rhnunregister')
        self.rhnserver = options.get('rhnserver')
        self.rhnuser = options.get('rhnuser')
        self.rhnpassword = options.get('rhnpassword')
        self.rhnactivationkey = options.get('rhnactivationkey')
        self.rhnorg = options.get('rhnorg')
        self.rhnpool = options.get('rhnpool')
        self.tags = options.get('tags')
        self.flavor = options.get('flavor')
        self.dnsclient = options.get('dnsclient')
        self.storemetadata = options.get('storemetadata')
        self.notify = options.get('notify')
        self.slacktoken = options.get('slacktoken')
        self.pushbullettoken = options.get('self.pushbullettoken')
        self.notifycmd = options.get('notifycmd')
        self.notifyscript = options.get('notifyscript')
        self.notifymethods = options.get('notifymethods')
        self.slackchannel = options.get('slackchannel')
        self.keep_networks = options.get('keep_networks')
        self.sharedfolders = options.get('sharedfolders')
        self.mailserver = options.get('mailserver')
        self.mailfrom = options.get('mailfrom')
        self.mailto = options.get('mailto')
        self.cmdline = options.get('cmdline')
        self.placement = options.get('placement')
        self.cpuhotplug = options.get('cpuhotplug')
        self.memoryhotplug = options.get('memoryhotplug')
        self.virttype = options.get('virttype')
        self.containerclient = containerclient
        self.vmuser = options.get('vmuser')
        self.vmport = options.get('vmport')
        self.vmrules = options.get('vmrules')
        self.vmrules_strict = options.get('vmrules_strict')
        self.securitygroups = options.get('securitygroups')
        self.rootpassword = options.get('rootpassword')
        self.wait = options.get('wait')
        self.waitcommand = options.get('waitcommand')
        self.waittimeout = options.get('waittimeout')
        self.tempkey = options.get('tempkey')
        self.bmc_user = options.get('bmc_user')
        self.bmc_password = options.get('bmc_password')
        self.bmc_model = options.get('bmc_model')
        self.overrides = {}

    def switch_host(self, client):
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
        results = {}
        for keyword in self.default:
            results[keyword] = vars(self)[keyword] if keyword in vars(self) else self.default[keyword]
        kvirt_dir = os.path.dirname(self.__init__.__code__.co_filename)
        extra_keywords_file = f'{kvirt_dir}/extra_keywords/{self.type}.yaml'
        extra_keywords = yaml.safe_load(open(extra_keywords_file)) if os.path.exists(extra_keywords_file) else []
        for keyword in extra_keywords:
            results[keyword] = None
        return results

    def info_plan(self, inputfile, quiet=False, web=False, onfly=None, doc=False):
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
        inputfile_split = os.path.splitext(os.path.basename(inputfile))
        inputfile_default = f"{inputfile_split[0]}_default{inputfile_split[1]}"
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

    def info_kubeadm_registry(self):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        inputfile = f'{plandir}/disconnected.yml'
        return self.info_plan(inputfile)

    def info_openshift_registry(self):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        inputfile = f'{plandir}/disconnected.yml'
        return self.info_plan(inputfile)

    def process_inputfile(self, plan, inputfile, overrides={}, onfly=None, full=False, ignore=False,
                          download_mode=False, extra_funcs=[], split=False):
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
                    parameter_value = parameters[parameter]
                    parameter_type = type(parameter_value)
                    override_value = overrides[parameter]
                    override_type = type(override_value)
                    if parameter_type == str and override_type == type(None):
                        continue
                    if parameter_value is not None and override_type != parameter_type:
                        msg = f"Parameter {parameter} doesn't have type {parameter_type}, it has type {override_type}"
                        msg += f" and value {override_value}"
                        if parameter_type == str and override_type in [int, float]:
                            try:
                                float(override_value)
                            except:
                                error(msg)
                                sys.exit(1)
                        else:
                            error(msg)
                            sys.exit(1)
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
                if split:
                    entries = yaml.load(entries, Loader=PlanLoader)
                else:
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
        cli = self.client
        all_profiles = self.profiles
        valid_profiles = {p: all_profiles[p] for p in all_profiles if all_profiles[p].get('type', 'vm') == 'vm'}
        for profile in valid_profiles:
            entry = self.default.copy()
            base_profiles = []
            base_profile = valid_profiles[profile].get('base')
            while base_profile is not None:
                base_profiles.append(base_profile)
                base_profile = valid_profiles[base_profile].get('base')
            for base_profile in reversed(base_profiles):
                entry.update(valid_profiles[base_profile])
            entry.update(valid_profiles[profile])
            valid_profiles[profile] = entry
        valid_profiles = {p: valid_profiles[p] for p in valid_profiles if all_profiles[p].get('client', cli) == cli}
        return valid_profiles

    def list_clusterprofiles(self):
        return self.clusterprofiles

    def list_confpools(self):
        return self.confpools

    def list_flavors(self):
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

    def _delete_yaml_object(self, name, selfconf, conf_type, quiet=False):
        found = False
        for obj in [name, f'{self.client}_{name}']:
            if obj in selfconf:
                del selfconf[obj]
                found = True
        if found:
            path = os.path.expanduser(f'~/.kcli/{conf_type}s.yml')
            if not selfconf:
                os.remove(path)
            else:
                with open(path, 'w') as dest_file:
                    try:
                        yaml.safe_dump(selfconf, dest_file, default_flow_style=False, encoding='utf-8',
                                       allow_unicode=True, sort_keys=False)
                    except:
                        yaml.safe_dump(selfconf, dest_file, default_flow_style=False, encoding='utf-8',
                                       allow_unicode=True)
            return {'result': 'success'}
        else:
            if not quiet:
                error(f"{conf_type.upper()} {name} not found")
            return {'result': 'failure', 'reason': f'{conf_type.upper()} {name} not found'}

    def _create_yaml_file(self, name, selfconf, conf_type, overrides={}, quiet=False):
        if name in conf_type:
            if not quiet:
                pprint(f"{conf_type.upper()} {name} already there")
            return {'result': 'success'}
        if not overrides:
            return {'result': 'failure', 'reason': "You need to specify at least one parameter"}
        if 'type' in overrides and 'type' not in ['vm', 'container']:
            return {'result': 'failure', 'reason': f"Invalid type {overrides['type']} for {conf_type} {name}"}
        path = os.path.expanduser(f'~/.kcli/{conf_type}s.yml')
        rootdir = os.path.expanduser('~/.kcli')
        selfconf[name] = overrides
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
        with open(path, 'w') as dest_file:
            try:
                yaml.safe_dump(selfconf, dest_file, default_flow_style=False, encoding='utf-8',
                               allow_unicode=True, sort_keys=False)
            except:
                yaml.safe_dump(selfconf, dest_file, default_flow_style=False, encoding='utf-8',
                               allow_unicode=True)
        return {'result': 'success'}

    def _update_yaml_file(self, name, selfconf, conf_type, overrides={}, quiet=False, ignore_aliases=False):
        matching_objects = [o for o in selfconf if o == name or o == f'{self.client}_{name}']
        if not matching_objects:
            if quiet:
                error(f"{conf_type.upper()} {name} not found")
            return {'result': 'failure', 'reason': f'{conf_type.upper()} {name} not found'}
        else:
            name = matching_objects[0]
        if not overrides:
            return {'result': 'failure', 'reason': "You need to specify at least one parameter"}
        path = os.path.expanduser(f'~/.kcli/{conf_type}s.yml')
        selfconf[name].update(overrides)
        with open(path, 'w') as dest_file:
            if ignore_aliases:
                yaml.dump(selfconf, dest_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                          Dumper=NoAliasDumper)
            else:
                yaml.safe_dump(selfconf, dest_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
        return {'result': 'success'}

    def create_profile(self, profile, overrides={}, quiet=False):
        return self._create_yaml_file(profile, self.profiles, 'profile', overrides=overrides, quiet=quiet)

    def delete_profile(self, profile, quiet=False):
        return self._delete_yaml_object(profile, self.profiles, 'profile', quiet=quiet)

    def update_profile(self, profile, overrides={}, quiet=False):
        return self._update_yaml_file(profile, self.profiles, 'profile', overrides=overrides, quiet=quiet)

    def create_clusterprofile(self, clusterprofile, overrides={}, quiet=False):
        clusterprofiles = self.clusterprofiles
        clusterprofilesdir = f"{os.path.dirname(sys.modules[Kbaseconfig.__module__].__file__)}/cluster/profiles"
        for entry in os.listdir(clusterprofilesdir):
            entry = entry.replace('.yml', '')
            del clusterprofiles[entry]
        return self._create_yaml_file(clusterprofile, self.clusterprofiles, 'clusterprofile', overrides=overrides,
                                      quiet=quiet)

    def delete_clusterprofile(self, clusterprofile, quiet=False):
        return self._delete_yaml_object(clusterprofile, self.clusterprofiles, 'clusterprofile', quiet=quiet)

    def update_clusterprofile(self, clusterprofile, overrides={}, quiet=False):
        return self._update_yaml_file(clusterprofile, self.clusterprofiles, 'clusterprofile', overrides=overrides,
                                      quiet=quiet, ignore_aliases=True)

    def create_confpool(self, confpool, overrides={}, quiet=False):
        return self._create_yaml_file(confpool, self.confpools, 'confpool', overrides=overrides, quiet=quiet)

    def delete_confpool(self, confpool, quiet=False):
        return self._delete_yaml_object(confpool, self.confpools, 'confpool', quiet=quiet)

    def update_confpool(self, confpool, overrides={}, quiet=False):
        return self._update_yaml_file(confpool, self.confpools, 'confpool', overrides=overrides, quiet=quiet,
                                      ignore_aliases=True)

    def info_kube_generic(self, quiet, web=False):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        inputfile = f'{plandir}/ctlplanes.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_hypershift(self, quiet, web=False):
        plandir = os.path.dirname(hypershift.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_k3s(self, quiet, web=False):
        plandir = os.path.dirname(k3s.create.__code__.co_filename)
        inputfile = f'{plandir}/ctlplanes.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_microshift(self, quiet, web=False):
        plandir = os.path.dirname(microshift.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_openshift(self, quiet, web=False):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        inputfile = f'{plandir}/ctlplanes.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)

    def info_kube_rke2(self, quiet, web=False):
        plandir = os.path.dirname(rke2.create.__code__.co_filename)
        inputfile = f'{plandir}/ctlplanes.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)

    def info_openshift_sno(self, quiet, web=False):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        inputfile = f'{plandir}/sno.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)

    def create_app(self, app, overrides={}, outputdir=None):
        kubetype = get_kubetype(overrides)
        if kubetype == 'openshift':
            return self.create_app_openshift(app, overrides, outputdir)
        elif kubetype == 'eks':
            return self.create_app_eks(app, overrides, outputdir)
        else:
            return self.create_app_generic(app, overrides, outputdir)

    def create_app_generic(self, app, overrides={}, outputdir=None):
        appdir = f"{os.path.dirname(kubeadm.create.__code__.co_filename)}/apps"
        return common.create_app_generic(self, app, appdir, overrides=overrides, outputdir=outputdir)

    def create_app_eks(self, app, overrides={}, outputdir=None):
        from kvirt.cluster import eks
        return eks.create_app(self, app, overrides)

    def create_app_openshift(self, app, overrides={}, outputdir=None):
        appdir = f"{os.path.dirname(openshift.create.__code__.co_filename)}/apps"
        if app in kdefaults.LOCAL_OPENSHIFT_APPS:
            app_data = overrides.copy()
            app_data['name'] = app
            if app == 'users' and overrides.get('hypershift', False):
                app_data['hypershift'] = True
            return common.create_app_generic(self, app, appdir, overrides=overrides, outputdir=outputdir)
        else:
            name, catalog, channel, csv, description, namespace, channels, crds = common.olm_app(app, overrides)
            if name is None:
                error(f"Couldn't find any app matching {app}. Skipping...")
                return 1
            if 'channel' in overrides:
                overrides_channel = overrides['channel']
                if overrides_channel not in channels:
                    error(f"Target channel {channel} not found in {channels}. Skipping...")
                    return 1
                else:
                    channel = overrides_channel
            if 'namespace' in overrides:
                namespace = overrides['namespace']
            app_data = {'catalog': catalog, 'channel': channel, 'namespace': namespace, 'csv': csv}
            app_data.update(overrides)
            return common.create_app_openshift(self, app, appdir, app_data, outputdir)

    def delete_app(self, app, overrides={}):
        kubetype = get_kubetype(overrides)
        if kubetype == 'openshift':
            return self.delete_app_openshift(app, overrides)
        elif kubetype == 'eks':
            return self.delete_app_eks(app, overrides)
        else:
            return self.delete_app_generic(app, overrides)

    def delete_app_generic(self, app, overrides={}):
        appdir = f"{os.path.dirname(kubeadm.create.__code__.co_filename)}/apps"
        return common.delete_app_delete_generic(self, app, appdir, overrides=overrides)

    def delete_app_eks(self, app, overrides={}):
        from kvirt.cluster import eks
        return eks.delete_app(self, app, overrides)

    def delete_app_openshift(self, app, overrides={}):
        appdir = f"{os.path.dirname(openshift.create.__code__.co_filename)}/apps"
        if app in kdefaults.LOCAL_OPENSHIFT_APPS:
            app_data = overrides.copy()
            if app == 'users' and overrides.get('hypershift', False):
                app_data['hypershift'] = True
            return common.delete_app_generic(self, app, appdir, app_data)
        else:
            name, catalog, channel, csv, description, namespace, channels, crds = common.olm_app(app, overrides)
            if name is None:
                error(f"Couldn't find any app matching {app}. Skipping...")
                return 1
            app_data = {'catalog': catalog, 'channel': channel, 'namespace': namespace, 'crds': crds}
            app_data.update(overrides)
            return common.delete_app_openshift(self, app, appdir, app_data)

    def info_app(self, app, overrides={}):
        kubetype = get_kubetype(overrides)
        if kubetype == 'openshift':
            return self.info_app_openshift(app, overrides)
        elif kubetype == 'eks':
            return self.info_app_eks(app)
        else:
            return self.info_app_generic(app)

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

    def info_app_eks(self, app):
        from kvirt.cluster import eks
        return eks.info_app(self, app)

    def info_app_openshift(self, app, overrides={}):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        if app not in kdefaults.LOCAL_OPENSHIFT_APPS:
            name, catalog, defaultchannel, csv, description, target_namespace, channels, crds = olm_app(app, overrides)
            if name is None:
                warning(f"Couldn't find any app matching {app}")
            else:
                pprint(f"Providing information for app {name}")
                print(f"catalog: {catalog}")
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

    def list_apps(self, quiet=True, installed=False, overrides={}):
        kubetype = get_kubetype(overrides)
        if kubetype == 'openshift':
            return self.list_apps_openshift(quiet=quiet, installed=installed)
        elif kubetype == 'eks':
            return self.list_apps_eks(quiet=quiet, installed=installed)
        else:
            return self.list_apps_generic(quiet=quiet)

    def list_apps_generic(self, quiet=True):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        appdir = plandir + '/apps'
        return sorted([x for x in os.listdir(appdir) if os.path.isdir(f"{appdir}/{x}") and x != '__pycache__'])

    def list_apps_eks(self, quiet=True, installed=False):
        from kvirt.cluster import eks
        return eks.list_apps(self, quiet=quiet, installed=installed)

    def list_apps_openshift(self, quiet=True, installed=False):
        if installed:
            header = 'subscription.operators.coreos.com/'
            results = []
            manifestscmd = "oc get subscriptions.operators.coreos.com -A -o name"
            manifestsdata = os.popen(manifestscmd).read().split('\n')
        else:
            header = 'packagemanifest.packages.operators.coreos.com/'
            results = ['autolabeller', 'users', 'metal3', 'nfs']
            manifestscmd = "oc get packagemanifest -n openshift-marketplace -o name"
            manifestsdata = os.popen(manifestscmd).read().split('\n')
        results.extend([entry.replace(header, '') for entry in manifestsdata if entry != ''])
        return sorted(results)

    def download_openshift_installer(self, overrides={}):
        OPENSHIFT_TAG = kdefaults.OPENSHIFT_TAG
        pull_secret = overrides.get('pull_secret') or 'openshift_pull.json'
        okd = overrides.get('okd') or False
        baremetal = overrides.get('baremetal') or False
        tag = overrides.get('tag') or OPENSHIFT_TAG
        version = overrides.get('version') or detect_openshift_version(tag, OPENSHIFT_TAG)
        macosx = os.path.exists('/Users')
        if okd:
            run = openshift.get_okd_installer(tag, version=version, debug=self.debug)
        elif version in ['ci', 'nightly']:
            nightly = version == 'nightly'
            run = openshift.get_ci_installer(pull_secret, tag=tag, macosx=macosx, debug=self.debug, nightly=nightly,
                                             baremetal=baremetal)
        elif version in ['candidate', 'stable', 'latest']:
            run = openshift.get_downstream_installer(version=version, tag=tag, macosx=macosx, debug=self.debug,
                                                     pull_secret=pull_secret, baremetal=baremetal)
        else:
            error(f"Invalid version {version}")
            return 1
        if run != 0:
            error("Couldn't download openshift-install")
        return run

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
        ori_data = {'cluster': 'mykube', 'image': 'centos8stream', 'vms_number': 3, 'memory': 8192, 'numcpus': 4,
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
            try:
                yaml.safe_dump(data, f, default_flow_style=False, encoding='utf-8', allow_unicode=True, sort_keys=True)
            except:
                yaml.safe_dump(data, f, default_flow_style=False, encoding='utf-8', allow_unicode=True)
        with open(f"{directory}/kcli_parameters.yml.sample", "w") as f:
            f.write("# Optional runtime parameter values for your plan\n# This is a YAML-formatted file\n")
            try:
                yaml.safe_dump(data, f, default_flow_style=False, encoding='utf-8', allow_unicode=True, sort_keys=True)
            except:
                yaml.safe_dump(data, f, default_flow_style=False, encoding='utf-8', allow_unicode=True)
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

    def create_workflow(self, workflow, overrides={}, outputdir=None, run=True, basedir=None):
        cwd = os.getcwd()
        target = overrides.get('target')
        if target is not None:
            tunnel, tunnelhost, tunnelport, tunneluser, vmport = False, None, 22, 'root', None
            if isinstance(target, str):
                user = None
                if '@' in target:
                    target_details = target.split('@')
                    if len(target_details) != 2:
                        msg = f"Invalid target {target}"
                        error(msg)
                        return {'result': 'failure', 'reason': msg}
                    user, target = target_details
                if '.' not in target and not valid_ip(target):
                    credentials = common._ssh_credentials(self.k, target)
                    user = user or credentials[0]
                    ip = credentials[1]
                    hostname = ip
                else:
                    hostname, ip = target, target
                    user = user or 'root'
            elif isinstance(target, dict):
                user = target.get('user', 'root')
                hostname = target.get('hostname', 'localhost')
                ip = target.get('ip', 'localhost')
                vmport = target.get('vmport')
                tunnel = target.get('tunnel', False)
                tunnelhost = target.get('tunnelhost', None)
                tunnelport = target.get('tunnelport', 22)
                tunneluser = target.get('tunneluser', 'root')
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
        tmpdir = None
        if 'destdir' in overrides:
            outputdir = overrides['destdir']
        elif outputdir is None:
            tmpdir = TemporaryDirectory()
            outputdir = tmpdir.name
        outputdir = os.path.realpath(outputdir)
        directoryfiles = []
        treatedfiles = []
        directories = []
        for entry in files:
            if not isinstance(entry, dict):
                entry = {'origin': entry}
            origin = os.path.expanduser(entry['origin'])
            if not os.path.isabs(origin) and basedir is not None:
                origin = f'{basedir}/{origin}'
            if 'path' in entry:
                destdir = os.path.dirname(entry['path'])
            else:
                destdir = f"{destdir}/{os.path.dirname(entry['origin'])}"
            if not os.path.exists(destdir):
                pprint(f"Creating directory {destdir}")
                os.makedirs(destdir)
            content = entry.get('content')
            render = entry.get('render', True)
            if isinstance(render, str):
                render = render.lower() == 'true'
            if origin in directories:
                continue
            elif not os.path.exists(origin):
                msg = f"Origin file {origin} not found"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            elif os.path.isdir(origin):
                origin = entry.get('origin')
                if not os.path.exists(f"{destdir}/{os.path.basename(origin)}"):
                    pprint(f"Creating directory {destdir}/{os.path.basename(origin)}")
                    os.makedirs(f"{destdir}/{os.path.basename(origin)}")
                    directories.append(origin)
                for _fic in os.listdir(origin):
                    directoryfiles.append(f'{origin}/{_fic}')
                continue
            filename = os.path.basename(origin)
            if not render:
                content = open(origin, 'r').read()
            rendered = content or self.process_inputfile(workflow, origin, overrides=overrides)
            destfile = f"{destdir}/{filename}"
            if 'path' in entry:
                destfile = entry['path']
            if not os.path.exists(os.path.dirname(destfile)):
                pprint(f"Creating directory {os.path.dirname(destfile)}")
                os.makedirs(os.path.dirname(destfile))
            with open(destfile, 'w') as f:
                pprint(f"Copying rendered file {filename} to {destfile}")
                f.write(rendered)
                os.chmod(destfile, stat.S_IMODE(os.stat(origin).st_mode))
            treatedfiles.append(origin)
        for entry in directoryfiles:
            if entry in treatedfiles:
                continue
            entrydir = os.path.dirname(entry)
            entryname = os.path.basename(entry)
            rendered = self.process_inputfile(workflow, entry, overrides=overrides)
            destfile = f"{destdir}/{entrydir}/{entryname}"
            with open(destfile, 'w') as f:
                f.write(rendered)
                os.chmod(destfile, stat.S_IMODE(os.stat(entry).st_mode))
        finalscripts = []
        for entry in scripts:
            origin = os.path.expanduser(entry)
            if not os.path.isabs(origin) and basedir is not None:
                origin = f'{basedir}/{origin}'
            if not os.path.exists(origin):
                msg = f"Origin file {origin} not found"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            elif os.path.isdir(origin):
                origin = entry.get('origin')
                if not os.path.exists(f"{outputdir}/{origin}"):
                    os.makedirs(f"{outputdir}/{origin}")
                    directories.append(origin)
                for _fic in os.listdir(origin):
                    directoryfiles.append(f'{origin}/{_fic}')
                continue
            scriptname = os.path.basename(origin)
            rendered = self.process_inputfile(workflow, origin, overrides=overrides)
            destfile = f"{outputdir}/{scriptname}"
            if 'path' in destfile:
                destfile = entry.get('path')
            if not os.path.exists(os.path.dirname(destfile)):
                pprint(f"Creating directory {os.path.dirname(destfile)}")
                os.makedirs(os.path.dirname(destfile))
            with open(destfile, 'w') as f:
                f.write(rendered)
            finalscripts.append(scriptname)
        if cmds:
            cmdscontent = '\n'.join(cmds)
            destfile = f"{outputdir}/cmds.sh"
            with open(destfile, 'w') as f:
                f.write(cmdscontent)
            finalscripts.append('cmds.sh')
        if not run:
            pprint("Not running as dry mode was requested")
            return {'result': 'success'}
        if target is not None:
            remotedir = f"/tmp/{os.path.basename(outputdir)}"
            scpcmd = scp(hostname, ip=ip, user=user, source=outputdir, destination=remotedir, download=False,
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
                             tunnelport=tunnelport, tunneluser=tunneluser, vmport=vmport, insecure=True)
            os.system(sshcommand)
        else:
            os.chdir(outputdir)
            for script in finalscripts:
                os.chmod(script, 0o700)
                pprint(f"Running script {script} locally")
                command = f'bash {script}' if script.endswith('.sh') else f'./{script}'
                result = call(command, shell=True)
                if result != 0:
                    msg = f"Failure in script {script}"
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
        if tmpdir is not None:
            tmpdir.cleanup()
        os.chdir(cwd)
        return {'result': 'success'}

    def info_keyword(self, keyword):
        default = self.default
        keywords = self.list_keywords()
        if keyword not in keywords:
            error(f"Keyword {keyword} not found")
            return 1
        else:
            print(f"Default value: {default.get(keyword)}")
            print(f"Current value: {keywords[keyword]}")
            kvirt_dir = os.path.dirname(self.__init__.__code__.co_filename)
            keywords_info = yaml.safe_load(open(f'{kvirt_dir}/keywords.yaml'))
            extra_keywords_file = f'{kvirt_dir}/extra_keywords/{self.type}.yaml'
            if os.path.exists(extra_keywords_file):
                keywords_info.update(yaml.safe_load(open(extra_keywords_file)))
            if keyword in keywords_info and keywords_info[keyword] is not None:
                pprint("Detailed information:")
                print(keywords_info[keyword].strip())
        return 0

    def info_plantype(self, plantype):
        vmtype = list(self.list_keywords().keys())
        plantypes = {'ansible': ['playbook', 'verbose', 'groups', 'user', 'variables', 'vms'],
                     'bucket': ['files'],
                     'cluster': ['kubetype'],
                     'container': ['image', 'nets', 'ports', 'volumes', 'environment', 'cmds'],
                     'disk': ['pool', 'vms', 'image', 'size'],
                     'dns': ['domain', 'net', 'ip', 'alias'],
                     'image': ['pool', 'size', 'url', 'cmd'],
                     'kube': ['kubetype'],
                     'loadbalancer': ['checkpath', 'checkport', 'alias', 'domain', 'dnsclient', 'vms', 'internal',
                                      'subnetid'],
                     'network': ['cidr', 'nat', 'dhcp', 'domain', 'dual_cidr'],
                     'plan': ['url', 'file'],
                     'pool': ['path'],
                     'profile': vmtype,
                     'securitygroup': ['ports'],
                     'vm': vmtype,
                     'workflow': []}
        if plantype not in plantypes:
            error(f"Plan type {plantype} not found")
            return 1
        else:
            for key in sorted(plantypes[plantype]):
                print(key)

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

    def deploy_ksushy_service(self, port=9000, ssl=False, ipv6=False, user=None, password=None, bootonce=False,
                              plan=None):
        if ssl:
            warning("ssl support requires installing manually pyopenssl and cherrypy")
        root = os.getuid() == 0
        if root:
            service_file = "/etc/systemd/system/ksushy.service"
        else:
            service_file = f"{os.environ.get('HOME')}/.config/systemd/user/ksushy.service"
        if not os.path.exists(os.path.dirname(service_file)):
            os.makedirs(os.path.dirname(service_file))
        update = os.path.exists(service_file)
        home = os.environ.get('HOME', '/root')
        iso_remover = bootonce
        executable = which('ksushy')
        port = f"Environment=KSUSHY_PORT={port}\n" if port != 9000 else ''
        ssl = "Environment=KSUSHY_SSL=true\n" if ssl else ''
        ipv6 = "Environment=KSUSHY_IPV6=true\n" if ipv6 else ''
        user = f"Environment=KSUSHY_USER={user}\n" if user is not None else ''
        password = f"Environment=KSUSHY_PASSWORD={password}\n" if password is not None else ''
        bootonce = "Environment=KSUSHY_BOOTONCE=true\n" if bootonce else ''
        sushydata = kdefaults.KSUSHYSERVICE.format(home=home, port=port, ipv6=ipv6, ssl=ssl, user=user,
                                                   password=password, bootonce=bootonce, executable=executable)
        with open(service_file, "w") as f:
            f.write(sushydata)
        user_space = "--user" if not root else ""
        cmd = f"systemctl {user_space} restart ksushy" if update else f"systemctl {user_space} enable --now ksushy"
        call(cmd, shell=True)
        if iso_remover:
            executable = which('ksushy-isoremover')
            plan = f"Environment=KSUSHY_PLAN={plan}\n" if plan is not None else ''
            isoremoverdata = kdefaults.ISOSERVICE.format(home=home, executable=executable, plan=plan)
            if root:
                service_file = "/etc/systemd/system/ksushy-isoremover.service"
            else:
                service_file = f"{os.environ.get('HOME')}/.config/systemd/user/ksushy-isoremover.service"
            with open(service_file, "w") as f:
                f.write(isoremoverdata)
            cmd = f"systemctl {user_space} restart" if update else f"systemctl {user_space} enable --now"
            cmd += " ksushy-isoremover"
            call(cmd, shell=True)

    def deploy_web_service(self, port=8000, ssl=False, ipv6=False):
        update = os.path.exists("/usr/lib/systemd/system/kweb.service")
        home = os.environ.get('HOME', '/root')
        port = f"Environment=KWEB_PORT={port}\n" if port != 8000 else ''
        ipv6 = "Environment=KWEB_IPV6=true\n" if ipv6 else ''
        webdata = kdefaults.WEBSERVICE.format(home=home, port=port, ipv6=ipv6, ssl=ssl)
        with open("/usr/lib/systemd/system/kweb.service", "w") as f:
            f.write(webdata)
        cmd = "systemctl restart kweb" if update else "systemctl enable --now kweb"
        call(cmd, shell=True)

    def get_vip_from_confpool(self, confpool, cluster, overrides):
        if confpool not in self.confpools:
            error("Confpool {confpool} not found")
            sys.exit(1)
        else:
            currentconfpool = self.confpools[confpool]
            ip_reservations = currentconfpool.get('ip_reservations', {})
            reserved_ips = list(ip_reservations.values())
            if "ips" in currentconfpool and self.type in [
                "kvm",
                "kubevirt",
                "ovirt",
                "openstack",
                "vsphere",
                "proxmox",
            ]:
                ips = currentconfpool['ips']
                if '/' in ips:
                    ips = [str(i) for i in ip_network(ips)[1:.1]]
                free_ips = [ip for ip in ips if ip not in reserved_ips]
                if free_ips:
                    free_ip = free_ips[0]
                    ip_reservations[cluster] = free_ip
                    pprint(f"Using {free_ip} from confpool {confpool} as api_ip")
                    overrides['api_ip'] = free_ip
                    self.update_confpool(confpool, {'ip_reservations': ip_reservations})
                else:
                    error(f"No available ip in confpool {confpool}")
                    sys.exit(1)

    def get_baremetal_hosts_from_confpool(self, confpool, cluster, overrides):
        if confpool not in self.confpools:
            error("Confpool {confpool} not found")
            sys.exit(1)
        else:
            currentconfpool = self.confpools[confpool]
            cluster_baremetal_reservations = currentconfpool.get('cluster_baremetal_reservations', {})
            reserved_hosts = list(cluster_baremetal_reservations.values())
            if 'baremetal_hosts' in currentconfpool:
                baremetal_hosts = currentconfpool['baremetal_hosts']
                baremetal_hosts_number = overrides.get('baremetal_hosts_number')
                if baremetal_hosts_number is None:
                    warning("Setting baremetal_hosts_number to 2")
                    baremetal_hosts_number = 2
                all_free_hosts = [host for host in baremetal_hosts if host not in reserved_hosts]
                if len(all_free_hosts) >= baremetal_hosts_number:
                    free_hosts = all_free_hosts[:baremetal_hosts_number]
                    cluster_baremetal_reservations[cluster] = free_hosts
                    pprint(f"Using {baremetal_hosts_number} baremetal hosts from {confpool}")
                    overrides['baremetal_hosts'] = free_hosts
                    if 'bmc_user' in currentconfpool:
                        overrides['bmc_user'] = currentconfpool['bmc_user']
                    if 'bmc_password' in currentconfpool:
                        overrides['bmc_password'] = currentconfpool['bmc_password']
                    self.update_confpool(confpool, {'cluster_baremetal_reservations': cluster_baremetal_reservations})
                else:
                    error(f"Not sufficient available baremetal hosts in confpool {confpool}")
                    sys.exit(1)

    def get_name_from_confpool(self, confpool):
        if confpool not in self.confpools:
            error("Confpool {confpool} not found")
            sys.exit(1)
        else:
            currentconfpool = self.confpools[confpool]
            name_reservations = currentconfpool.get('name_reservations', [])
            if 'names' in currentconfpool:
                names = currentconfpool['names']
                free_names = [n for n in names if n not in name_reservations]
                if free_names:
                    free_name = free_names[0]
                    name_reservations.append(free_name)
                    pprint(f"Using {free_name} from confpool {confpool} as name")
                else:
                    error(f"No available name in confpool {confpool}")
                    sys.exit(1)
                self.update_confpool(confpool, {'name_reservations': name_reservations})
                return free_name

    def info_specific_kube(self, cluster, openshift=False):
        clusterdir = os.path.expanduser(f'~/.kcli/clusters/{cluster}')
        if os.path.exists(f'{clusterdir}/worker.ign'):
            openshift = True
        kubeconfig = f'{clusterdir}/auth/kubeconfig'
        if not os.path.exists(kubeconfig):
            if 'KUBECONFIG' in os.environ:
                kubeconfig = os.environ['KUBECONFIG']
                warning(f"{kubeconfig} not found...Using KUBECONFIG instead")
            else:
                warning("KUBECONFIG not set...Using .kube/config instead")
                kubeconfig = os.path.expanduser('~/.kube/config')
        nodes = []
        if openshift:
            nodes_command = f'KUBECONFIG={kubeconfig} oc get nodes --no-headers=true -o wide'
            try:
                version = os.popen(f'KUBECONFIG={kubeconfig} oc get clusterversion --no-headers').read().strip()
            except:
                version = 'N/A'
        else:
            nodes_command = f'KUBECONFIG={kubeconfig} kubectl get nodes --no-headers=true -o wide'
            server_command = f'KUBECONFIG={kubeconfig} kubectl version -o yaml'
            try:
                version = yaml.safe_load(os.popen(server_command).read())['serverVersion']['gitVersion']
            except:
                version = 'N/A'
        try:
            for entry in os.popen(nodes_command).readlines():
                node = [column.strip() for column in entry.split()[0:6]]
                nodes.append(node)
        except:
            pass
        results = {'nodes': nodes, 'version': version}
        return results

    def update_openshift_registry(self, cluster, overrides={}):
        os.environ["PATH"] = f'{os.getcwd()}:{os.environ["PATH"]}'
        data = {}
        clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}") if cluster is not None else '.'
        if os.path.exists(clusterdir) and os.path.exists(f'{clusterdir}/kcli_parameters.yml'):
            with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
                installparam = yaml.safe_load(install)
                data.update(installparam)
        data.update(overrides)
        pull_secret = os.path.expanduser(data.get('pull_secret', 'openshift_pull.json'))
        if not os.path.exists(pull_secret):
            error(f"pull_secret {pull_secret} not found")
            sys.exit(1)
        data['pull_secret'] = pull_secret
        if data.get('disconnected_url') is None:
            error("It is mandatory to set disconnected_url")
            sys.exit(1)
        if 'version' not in data:
            data['version'] = 'stable'
        if 'tag' not in data:
            data['tag'] = kdefaults.OPENSHIFT_TAG
        if which('openshift-install') is None:
            self.download_openshift_installer(data)
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        openshift.update_registry(self, plandir, cluster, data)


def interactive_kube(_type):
    overrides = {}
    # version = input("Input version: {default_version"
    return overrides
