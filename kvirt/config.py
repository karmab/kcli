#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Kvirt config class
"""

from defaults import NETS, POOL, CPUMODEL, NUMCPUS, MEMORY, DISKS, DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID, VNC, CLOUDINIT, RESERVEIP, RESERVEDNS, RESERVEHOST, START, NESTED, TUNNEL
import ansibleutils
from kvirt import common
from kvm import Kvirt
from vbox import Kbox
import os
import yaml

__version__ = '5.24'


class Kconfig:
    def __init__(self, client=None, debug=False):
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            if os.path.exists('/Users'):
                _type = 'vbox'
            else:
                _type = 'kvm'
            ini = {'default': {'client': 'local'}, 'local': {'pool': 'default', 'type': _type}}
            common.pprint("Using local hypervisor as no kcli.yml was found...", color='green')
        else:
            with open(inifile, 'r') as entries:
                try:
                    ini = yaml.load(entries)
                except:
                    self.host = None
                    return
            if 'default' not in ini or 'client' not in ini['default']:
                common.pprint("Missing default section in config file. Leaving...", color='red')
                self.host = None
                return
        self.clients = [e for e in ini if e != 'default']
        defaults = {}
        default = ini['default']
        defaults['nets'] = default.get('nets', NETS)
        defaults['pool'] = default.get('pool', POOL)
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
        defaults['tunnel'] = default.get('tunnel', TUNNEL)
        self.default = defaults
        self.ini = ini
        profilefile = default.get('profiles', "%s/kcli_profiles.yml" % os.environ.get('HOME'))
        profilefile = os.path.expanduser(profilefile)
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                self.profiles = yaml.load(entries)
        if client is None:
            self.client = self.ini['default']['client']
        else:
            self.client = client
        if self.client not in self.ini:
            common.pprint("Missing section for client %s in config file. Leaving..." % self.client, color='red')
            os._exit(1)
        options = self.ini[self.client]
        self.host = options.get('host', '127.0.0.1')
        self.port = options.get('port', 22)
        self.user = options.get('user', 'root')
        self.protocol = options.get('protocol', 'ssh')
        self.url = options.get('url', None)
        self.tunnel = bool(options.get('tunnel', self.default['tunnel']))
        self.type = options.get('type', 'kvm')
        if self.type == 'vbox':
            k = Kbox()
        else:
            if self.host is None:
                common.pprint("Problem parsing your configuration file", color='red')
                os._exit(1)
            k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url, debug=debug)
        if k.conn is None:
            common.pprint("Couldnt connect to specify hypervisor %s. Leaving..." % self.host, color='red')
            os._exit(1)
        self.k = k

    def create_vm(self, name, profile, ip1=None, ip2=None, ip3=None, ip4=None, ip5=None, ip6=None, ip7=None, ip8=None):
        k = self.k
        tunnel = self.tunnel
        if profile is None:
            common.pprint("Missing profile", color='red')
            os._exit(1)
        default = self.default
        vmprofiles = {k: v for k, v in self.profiles.iteritems() if 'type' not in v or v['type'] == 'vm'}
        common.pprint("Deploying vm %s from profile %s..." % (name, profile), color='green')
        if profile not in vmprofiles:
            common.pprint("profile %s not found. Trying to use the profile as template and default values..." % profile, color='blue')
            result = k.create(name=name, memory=1024, template=profile)
            code = common.handle_response(result, name)
            os._exit(code)
            return
        profilename = profile
        profile = vmprofiles[profile]
        template = profile.get('template')
        plan = 'kvirt'
        nets = profile.get('nets', default['nets'])
        cpumodel = profile.get('cpumodel', default['cpumodel'])
        cpuflags = profile.get('cpuflags', [])
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
        reservedns = profile.get('reservedns', default['reservedns'])
        reservehost = profile.get('reservehost', default['reservehost'])
        nested = profile.get('nested', default['nested'])
        start = profile.get('start', default['start'])
        keys = profile.get('keys', None)
        cmds = profile.get('cmds', None)
        netmasks = profile.get('netmasks')
        gateway = profile.get('gateway')
        dns = profile.get('dns')
        domain = profile.get('domain')
        scripts = profile.get('scripts')
        files = profile.get('files', [])
        if scripts is not None:
            scriptcmds = []
            for script in scripts:
                script = os.path.expanduser(script)
                if not os.path.exists(script):
                    common.pprint("Script %s not found.Ignoring..." % script, color='red')
                    os._exit(1)
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
        result = k.create(name=name, plan=plan, profile=profilename, cpumodel=cpumodel, cpuflags=cpuflags, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain, nested=bool(nested), tunnel=tunnel, files=files)
        common.handle_response(result, name)
        if result['result'] != 'success':
            return
        ansible = profile.get('ansible')
        if ansible is not None:
            for element in ansible:
                if 'playbook' not in element:
                    continue
                playbook = element['playbook']
                if 'variables' in element:
                    variables = element['variables']
                if 'verbose' in element:
                    verbose = element['verbose']
                else:
                    verbose = False
                # k.play(name, playbook=playbook, variables=variables, verbose=verbose)
                with open("/tmp/%s.inv" % name, "w") as f:
                    inventory = ansibleutils.inventory(k, name)
                    if inventory is not None:
                        if variables is not None:
                            for variable in variables:
                                if not isinstance(variable, dict) or len(variable.keys()) != 1:
                                    continue
                                else:
                                    key, value = variable.keys()[0], variable[variable.keys()[0]]
                                    inventory = "%s %s=%s" % (inventory, key, value)
                    if self.tunnel:
                        inventory = "%s ansible_ssh_common_args='-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"'\n" % (inventory, self.port, self.user, self.host)
                    f.write("%s\n" % inventory)
                ansiblecommand = "ansible-playbook"
                if verbose:
                    ansiblecommand = "%s -vvv" % ansiblecommand
                ansibleconfig = os.path.expanduser('~/.ansible.cfg')
                with open(ansibleconfig, "w") as f:
                    f.write("[ssh_connection]\nretries=10\n")
                print("Running: %s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
                os.system("%s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))

    def list_profiles(self):
        default_disksize = '10'
        default = self.default
        results = []
        for profile in sorted(self.profiles):
                info = self.profiles[profile]
                numcpus = info.get('numcpus', default['pool'])
                memory = info.get('memory', default['memory'])
                pool = info.get('pool', default['pool'])
                diskinfo = []
                disks = info.get('disks', default['disks'])
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
                nets = info.get('nets', default['nets'])
                for net in nets:
                    if isinstance(net, str):
                        netname = net
                    elif isinstance(net, dict) and 'name' in net:
                        netname = net['name']
                    netinfo.append(netname)
                netinfo = ','.join(netinfo)
                template = info.get('template', '')
                cloudinit = info.get('cloudinit', default['cloudinit'])
                nested = info.get('nested', default['nested'])
                reservedns = info.get('reservedns', default['reservedns'])
                reservehost = info.get('reservehost', default['reservehost'])
                results.append([profile, numcpus, memory, pool, diskinfo, template, netinfo, cloudinit, nested, reservedns, reservehost])
        return results
