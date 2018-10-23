#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvirt config class
"""

from jinja2 import Environment, FileSystemLoader
from kvirt.defaults import TEMPLATES, TEMPLATESCOMMANDS
from kvirt import ansibleutils
from kvirt import nameutils
from kvirt import common
from kvirt.baseconfig import Kbaseconfig
from distutils.spawn import find_executable
import glob
import os
import re
import shutil
import sys
from time import sleep
import webbrowser
import yaml

__version__ = '13.6'


class Kconfig(Kbaseconfig):
    """

    """
    def __init__(self, client=None, debug=False, quiet=False, region=None, zone=None):
        Kbaseconfig.__init__(self, client=client, debug=debug, quiet=quiet)
        self.overrides = {}
        if not self.enabled:
            k = None
        else:
            if self.type == 'fake':
                from kvirt.fake import Kfake
                k = Kfake()
            elif self.type == 'vbox':
                from kvirt.vbox import Kbox
                k = Kbox()
            elif self.type == 'kubevirt':
                context = self.options.get('context')
                cdi = self.options.get('cdi', False)
                multus = self.options.get('multus', True)
                from kvirt.kubevirt import Kubevirt
                k = Kubevirt(context=context, cdi=cdi, multus=multus, host=self.host, port=self.port,
                             user=self.user, debug=debug)
                self.host = k.host
            elif self.type == 'gcp':
                credentials = self.options.get('credentials')
                if credentials is not None:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser(credentials)
                elif 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
                    common.pprint("set GOOGLE_APPLICATION_CREDENTIALS variable.Leaving...", color='red')
                    os._exit(1)
                project = self.options.get('project')
                if project is None:
                    common.pprint("Missing project in the configuration. Leaving", color='red')
                    os._exit(1)
                zone = self.options.get('zone', 'europe-west1-b') if zone is None else zone
                region = self.options.get('region') if region is None else region
                region = zone[:-2] if region is None else region
                from kvirt.gcp import Kgcp
                k = Kgcp(region=region, zone=zone, project=project, debug=debug)
            elif self.type == 'aws':
                region = self.options.get('region') if region is None else region
                if region is None:
                    common.pprint("Missing region in the configuration. Leaving", color='red')
                    os._exit(1)
                access_key_id = self.options.get('access_key_id')
                if access_key_id is None:
                    common.pprint("Missing access_key_id in the configuration. Leaving", color='red')
                    os._exit(1)
                access_key_secret = self.options.get('access_key_secret')
                if access_key_secret is None:
                    common.pprint("Missing access_key_secret in the configuration. Leaving", color='red')
                    os._exit(1)
                from kvirt.aws import Kaws
                k = Kaws(access_key_id=access_key_id, access_key_secret=access_key_secret, region=region,
                         debug=debug)
            elif self.type == 'ovirt':
                datacenter = self.options.get('datacenter', 'Default')
                cluster = self.options.get('cluster', 'Default')
                user = self.options.get('user', 'admin@internal')
                password = self.options.get('password')
                if password is None:
                    common.pprint("Missing password in the configuration. Leaving", color='red')
                    os._exit(1)
                org = self.options.get('org')
                if org is None:
                    common.pprint("Missing org in the configuration. Leaving", color='red')
                    os._exit(1)
                ca_file = self.options.get('ca_file')
                if ca_file is None:
                    common.pprint("Missing ca_file in the configuration. Leaving", color='red')
                    os._exit(1)
                ca_file = os.path.expanduser(ca_file)
                if not os.path.exists(ca_file):
                    common.pprint("Ca file path doesn't exist. Leaving", color='red')
                    os._exit(1)
                imagerepository = self.options.get('imagerepository', 'ovirt-image-repository')
                filtervms = self.options.get('filtervms', True)
                filteruser = self.options.get('filtervms')
                from kvirt.ovirt import KOvirt
                k = KOvirt(host=self.host, port=self.port, user=user, password=password,
                           debug=debug, datacenter=datacenter, cluster=cluster, ca_file=ca_file, org=org,
                           imagerepository=imagerepository, filtervms=filtervms, filteruser=filteruser)
                self.overrides.update({'host': self.host, 'user': user, 'password': password})
            elif self.type == 'openstack':
                version = self.options.get('version', '2')
                domain = next((e for e in [self.options.get('domain'),
                                           os.environ.get("OS_USER_DOMAIN_NAME")] if e is not None), 'Default')
                auth_url = next((e for e in [self.options.get('auth_url'),
                                             os.environ.get("OS_AUTH_URL")] if e is not None),
                                None)
                if auth_url is None:
                    common.pprint("Missing auth_url in the configuration. Leaving", color='red')
                    os._exit(1)
                user = next((e for e in [self.options.get('user'),
                                         os.environ.get("OS_USERNAME")] if e is not None), 'admin')
                project = next((e for e in [self.options.get('project'),
                                            os.environ.get("OS_PROJECT_NAME")] if e is not None), 'admin')
                password = next((e for e in [self.options.get('password'),
                                             os.environ.get("OS_PASSWORD")] if e is not None), None)
                if password is None:
                    common.pprint("Missing password in the configuration. Leaving", color='red')
                    os._exit(1)
                if auth_url.endswith('v2.0'):
                    domain = None
                from kvirt.openstack import Kopenstack
                k = Kopenstack(host=self.host, port=self.port, user=user, password=password, version=version,
                               debug=debug, project=project, domain=domain, auth_url=auth_url)
            else:
                if self.host is None:
                    common.pprint("Problem parsing your configuration file", color='red')
                    os._exit(1)
                from kvirt.kvm import Kvirt
                k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url,
                          debug=debug, insecure=self.insecure)
            if k.conn is None:
                common.pprint("Couldn't connect to client %s. Leaving..." % self.client, color='red')
                os._exit(1)
            for extraclient in self._extraclients:
                if extraclient not in self.ini:
                    common.pprint("Missing section for client %s in config file. Leaving..." % extraclient, color='red')
                    os._exit(1)
                c = Kconfig(client=extraclient)
                e = c.k
                self.extraclients[extraclient] = e
                if e.conn is None:
                    common.pprint("Couldn't connect to specify hypervisor %s. Leaving..." % extraclient, color='red')
                    os._exit(1)
        self.k = k
        self.overrides.update({'type': self.type})

    def create_vm(self, name, profile, overrides={}, customprofile={}, k=None,
                  plan='kvirt', basedir='.'):
        """

        :param k:
        :param plan:
        :param name:
        :param profile:
        :param overrides:
        :param customprofile:
        :return:
        """
        overrides.update(self.overrides)
        overrides.update({'plan': plan})
        k = self.k if k is None else k
        tunnel = self.tunnel
        if profile is None:
            common.pprint("Missing profile", color='red')
            os._exit(1)
        vmprofiles = {k: v for k, v in self.profiles.items() if 'type' not in v or v['type'] == 'vm'}
        if customprofile:
            vmprofiles[profile] = customprofile
        else:
            common.pprint("Deploying vm %s from profile %s..." % (name, profile), color='green')
        if profile not in vmprofiles:
            common.pprint("profile %s not found. Trying to use the profile as template and default values..." % profile,
                          color='blue')
            vmprofiles[profile] = {'template': profile}
        profilename = profile
        profile = vmprofiles[profile]
        profile.update(overrides)
        if 'base' in profile:
            father = vmprofiles[profile['base']]
            default_numcpus = father.get('numcpus', self.numcpus)
            default_memory = father.get('memory', self.memory)
            default_pool = father.get('pool', self.pool)
            default_disks = father.get('disks', self.disks)
            default_nets = father.get('nets', self.nets)
            default_template = father.get('template', self.template)
            default_cloudinit = father.get('cloudinit', self.cloudinit)
            default_nested = father.get('nested', self.nested)
            default_reservedns = father.get('reservedns', self.reservedns)
            default_reservehost = father.get('reservehost', self.reservehost)
            default_cpumodel = father.get('cpumodel', self.cpumodel)
            default_cpuflags = father.get('cpuflags', self.cpuflags)
            default_disksize = father.get('disksize', self.disksize)
            default_diskinterface = father.get('diskinterface', self.diskinterface)
            default_diskthin = father.get('diskthin', self.diskthin)
            default_guestid = father.get('guestid', self.guestid)
            default_iso = father.get('iso', self.iso)
            default_vnc = father.get('vnc', self.vnc)
            default_reserveip = father.get('reserveip', self.reserveip)
            default_start = father.get('start', self.start)
            default_report = father.get('report', self.report)
            default_reportall = father.get('reportall', self.reportall)
            default_keys = father.get('keys', self.keys)
            default_netmasks = father.get('netmasks', self.netmasks)
            default_gateway = father.get('gateway', self.gateway)
            default_dns = father.get('dns', self.dns)
            default_domain = father.get('domain', self.domain)
            default_files = father.get('files', self.files)
            default_enableroot = father.get('enableroot', self.enableroot)
            default_privatekey = father.get('privatekey', self.privatekey)
            default_rhnregister = father.get('rhnregister', self.rhnregister)
            default_rhnuser = father.get('rhnuser', self.rhnuser)
            default_rhnpassword = father.get('rhnpassword', self.rhnpassword)
            default_rhnak = father.get('rhnactivationkey', self.rhnak)
            default_rhnorg = father.get('rhnorg', self.rhnorg)
            default_rhnpool = father.get('rhnpool', self.rhnpool)
            default_tags = father.get('tags', self.tags)
            default_flavor = father.get('flavor', self.flavor)
            default_cmds = common.remove_duplicates(self.cmds + father.get('cmds', []))
            default_scripts = common.remove_duplicates(self.scripts + father.get('scripts', []))
            default_dnshost = father.get('dnshost', self.dnshost)
        else:
            default_numcpus = self.numcpus
            default_memory = self.memory
            default_pool = self.pool
            default_disks = self.disks
            default_nets = self.nets
            default_template = self.template
            default_cloudinit = self.cloudinit
            default_nested = self.nested
            default_reservedns = self.reservedns
            default_reservehost = self.reservehost
            default_cpumodel = self.cpumodel
            default_cpuflags = self.cpuflags
            default_disksize = self.disksize
            default_diskinterface = self.diskinterface
            default_diskthin = self.diskthin
            default_guestid = self.guestid
            default_iso = self.iso
            default_vnc = self.vnc
            default_reserveip = self.reserveip
            default_start = self.start
            default_report = self.report
            default_reportall = self.reportall
            default_keys = self.keys
            default_netmasks = self.netmasks
            default_gateway = self.gateway
            default_dns = self.dns
            default_domain = self.domain
            default_files = self.files
            default_enableroot = self.enableroot
            default_tags = self.tags
            default_flavor = self.flavor
            default_privatekey = self.privatekey
            default_rhnregister = self.rhnregister
            default_rhnuser = self.rhnuser
            default_rhnpassword = self.rhnpassword
            default_rhnak = self.rhnak
            default_rhnorg = self.rhnorg
            default_rhnpool = self.rhnpool
            default_cmds = self.cmds
            default_scripts = self.scripts
            default_dnshost = self.dnshost
        plan = profile.get('plan', plan)
        template = profile.get('template', default_template)
        nets = profile.get('nets', default_nets)
        cpumodel = profile.get('cpumodel', default_cpumodel)
        cpuflags = profile.get('cpuflags', default_cpuflags)
        numcpus = profile.get('numcpus', default_numcpus)
        memory = profile.get('memory', default_memory)
        pool = profile.get('pool', default_pool)
        disks = profile.get('disks', default_disks)
        disksize = profile.get('disksize', default_disksize)
        diskinterface = profile.get('diskinterface', default_diskinterface)
        diskthin = profile.get('diskthin', default_diskthin)
        guestid = profile.get('guestid', default_guestid)
        iso = profile.get('iso', default_iso)
        vnc = profile.get('vnc', default_vnc)
        cloudinit = profile.get('cloudinit', default_cloudinit)
        if cloudinit and self.type in ['kvm', 'vbox'] and\
                find_executable('mkisofs') is None and find_executable('genisoimage') is None:
            common.pprint("mkisofs/genisoimage not found. One of them is needed for cloudinit.Leaving...", 'red')
            os._exit(1)
        reserveip = profile.get('reserveip', default_reserveip)
        reservedns = profile.get('reservedns', default_reservedns)
        reservehost = profile.get('reservehost', default_reservehost)
        nested = profile.get('nested', default_nested)
        start = profile.get('start', default_start)
        report = profile.get('report', default_report)
        reportall = profile.get('reportall', default_reportall)
        keys = profile.get('keys', default_keys)
        cmds = common.remove_duplicates(default_cmds + profile.get('cmds', []))
        netmasks = profile.get('netmasks', default_netmasks)
        gateway = profile.get('gateway', default_gateway)
        dns = profile.get('dns', default_dns)
        domain = profile.get('domain', default_domain)
        scripts = common.remove_duplicates(default_scripts + profile.get('scripts', []))
        files = profile.get('files', default_files)
        if files:
            for index, fil in enumerate(files):
                if not isinstance(fil, dict):
                    common.pprint("Incorrect file entry.Leaving...", color='red')
                    os._exit(1)
                else:
                    path = fil.get('path')
                    origin = fil.get('origin')
                    content = fil.get('content')
                    if path is None:
                            common.pprint("Missing path in files of %s.Leaving..." % name, color='red')
                            os._exit(1)
                    if origin is not None:
                        origin = os.path.expanduser(origin)
                        if basedir != '.':
                            origin = "%s/%s" % (basedir, origin)
                            files[index]['origin'] = origin
                        if not os.path.exists(origin):
                            common.pprint("File %s not found in %s.Leaving..." % (origin, name),
                                          color='red')
                            os._exit(1)
                    elif content is None:
                            common.pprint("Content of file %s not found in %s.Ignoring..." % (path, name),
                                          color='red')
                            os._exit(1)
        enableroot = profile.get('enableroot', default_enableroot)
        tags = None
        if default_tags is not None:
            if isinstance(default_tags, dict):
                tags = default_tags.copy()
                tags.update(profile.get('tags', {}))
            elif isinstance(default_tags, list):
                customtags = profile.get('tags')
                tags = default_tags + customtags if customtags else default_tags
        elif profile.get('tags') is not None:
            tags = profile.get('tags')
        privatekey = profile.get('privatekey', default_privatekey)
        rhnregister = profile.get('rhnregister', default_rhnregister)
        rhnuser = profile.get('rhnuser', default_rhnuser)
        rhnpassword = profile.get('rhnpassword', default_rhnpassword)
        rhnak = profile.get('rhnactivationkey', default_rhnak)
        rhnorg = profile.get('rhnorg', default_rhnorg)
        rhnpool = profile.get('rhnpool', default_rhnpool)
        flavor = profile.get('flavor', default_flavor)
        dnshost = profile.get('dnshost', default_dnshost)
        scriptcmds = []
        skip_rhnregister_script = False
        if rhnregister:
            if rhnuser is not None and rhnpassword is not None:
                skip_rhnregister_script = True
                overrides['rhnuser'] = rhnuser
                overrides['rhnpassword'] = rhnpassword
            elif rhnak is not None and rhnorg is not None:
                skip_rhnregister_script = True
                overrides['rhnak'] = rhnak
                overrides['rhnorg'] = rhnorg
            else:
                common.pprint("Rhn registration required but missing credentials.Leaving...", color='red')
                os._exit(1)
        if scripts:
            for script in scripts:
                script = os.path.expanduser(script)
                if basedir != '.':
                    script = '%s/%s' % (basedir, script)
                if script.endswith('register.sh') and skip_rhnregister_script:
                    continue
                elif not os.path.exists(script):
                    common.pprint("Script %s not found.Ignoring..." % script, color='red')
                    os._exit(1)
                else:
                    scriptbasedir = os.path.dirname(script) if os.path.dirname(script) != '' else '.'
                    env = Environment(block_start_string='[%', block_end_string='%]',
                                      variable_start_string='[[', variable_end_string=']]',
                                      loader=FileSystemLoader(scriptbasedir))
                    templ = env.get_template(os.path.basename(script))
                    scriptentries = templ.render(overrides)
                    scriptlines = [line.strip() for line in scriptentries.split('\n') if line.strip() != '']
                    if scriptlines:
                        scriptcmds.extend(scriptlines)
        if skip_rhnregister_script and cloudinit and template is not None and template.lower().startswith('rhel'):
            # rhncommands = ['sleep 30']
            rhncommands = []
            if rhnak is not None and rhnorg is not None:
                rhncommands.append('subscription-manager register --force --activationkey=%s --org=%s'
                                   % (rhnak, rhnorg))
                rhncommands.append('subscription-manager repos --enable=rhel-7-server-rpms')
            elif rhnuser is not None and rhnpassword is not None:
                rhncommands.append('subscription-manager register --force --username=%s --password=%s'
                                   % (rhnuser, rhnpassword))
                if rhnpool is not None:
                    rhncommands.append('subscription-manager attach --pool=%s' % rhnpool)
                else:
                    rhncommands.append('subscription-manager attach --auto')
        else:
            rhncommands = []
        cmds = rhncommands + cmds + scriptcmds
        if reportall:
            reportcmd = 'curl -s -X POST -d "name=%s&status=Running&report=`cat /var/log/cloud-init.log`" %s/report '
            '>/dev/null' % (name, self.reporturl)
            finishcmd = 'curl -s -X POST -d "name=%s&status=OK&report=`cat /var/log/cloud-init.log`" %s/report '
            '>/dev/null' % (name, self.reporturl)
            if not cmds:
                cmds = [finishcmd]
            else:
                results = []
                for cmd in cmds[:-1]:
                    results.append(cmd)
                    results.append(reportcmd)
                results.append(cmds[-1])
                results.append(finishcmd)
                cmds = results
        elif report:
            reportcmd = ['curl -s -X POST -d "name=%s&status=OK&report=`cat /var/log/cloud-init.log`" %s/report '
                         '/dev/null' % (name, self.reporturl)]
            cmds = cmds + reportcmd
        ips = [overrides[key] for key in overrides if key.startswith('ip')]
        netmasks = [overrides[key] for key in overrides if key.startswith('netmask')]
        if privatekey:
            privatekeyfile = None
            if os.path.exists("%s/.ssh/id_rsa" % os.environ['HOME']):
                privatekeyfile = "%s/.ssh/id_rsa" % os.environ['HOME']
            elif os.path.exists("%s/.ssh/id_rsa" % os.environ['HOME']):
                privatekeyfile = "%s/.ssh/id_dsa" % os.environ['HOME']
            if privatekeyfile is not None:
                privatekey = open(privatekeyfile).read().strip()
                if files:
                    files.append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                else:
                    files = [{'path': '/root/.ssh/id_rsa', 'content': privatekey}]
        result = k.create(name=name, plan=plan, profile=profilename, flavor=flavor, cpumodel=cpumodel,
                          cpuflags=cpuflags, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool,
                          template=template, disks=disks, disksize=disksize, diskthin=diskthin,
                          diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit),
                          reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost),
                          start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns,
                          domain=domain, nested=bool(nested), tunnel=tunnel, files=files, enableroot=enableroot,
                          overrides=overrides, tags=tags, dnshost=None)
        if result['result'] != 'success':
            return result
        if dnshost is not None and domain is not None:
            if dnshost in self.clients:
                z = Kconfig(client=dnshost).k
                ip = None
                if ip is None:
                    counter = 0
                    while counter != 300:
                        ip = k.ip(name)
                        if ip is None:
                            sleep(5)
                            print("Waiting 5 seconds to grab ip and create DNS record...")
                            counter += 10
                        else:
                            break
                if ip is None:
                    common.print("Couldn't assign DNS", color='red')
                else:
                    z.reserve_dns(name=name, nets=[domain], domain=domain, ip=ip, force=True)
            else:
                common.pprint("Host %s not found. Skipping" % dnshost, color='blue')
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
                with open("/tmp/%s.inv" % name, "w") as f:
                    inventory = ansibleutils.inventory(k, name)
                    if inventory is not None:
                        if variables is not None:
                            for variable in variables:
                                if not isinstance(variable, dict) or len(list(variable)) != 1:
                                    continue
                                else:
                                    key, value = list(variable)[0], variable[list(variable)[0]]
                                    inventory = "%s %s=%s" % (inventory, key, value)
                    if self.tunnel:
                        inventory = "%s ansible_ssh_common_args='-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\""
                        "'\n" % (inventory, self.port, self.user, self.host)
                    f.write("%s\n" % inventory)
                ansiblecommand = "ansible-playbook"
                if verbose:
                    ansiblecommand = "%s -vvv" % ansiblecommand
                ansibleconfig = os.path.expanduser('~/.ansible.cfg')
                with open(ansibleconfig, "w") as f:
                    f.write("[ssh_connection]\nretries=10\n")
                print("Running: %s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
                os.system("%s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
        if os.access(os.path.expanduser('~/.kcli'), os.W_OK):
            common.set_lastvm(name, self.client)
        return {'result': 'success', 'vm': name}

    def list_plans(self):
        """

        :return:
        """
        k = self.k
        vms = {}
        plans = []
        for vm in sorted(k.list(), key=lambda x: x[4]):
                vmname = vm[0]
                plan = vm[4]
                if plan in vms:
                    vms[plan].append(vmname)
                else:
                    vms[plan] = [vmname]
        for plan in sorted(vms):
            planvms = ','.join(vms[plan])
            plans.append([plan, planvms])
        return plans

    def list_profiles(self):
        """

        :return:
        """
        default_disksize = '10'
        default = self.default
        results = []
        for profile in [p for p in self.profiles if 'base' not in self.profiles[p]] + [p for p in self.profiles
                                                                                       if 'base' in self.profiles[p]]:
                info = self.profiles[profile]
                if 'base' in info:
                    father = self.profiles[info['base']]
                    default_numcpus = father.get('numcpus', default['numcpus'])
                    default_memory = father.get('memory', default['memory'])
                    default_pool = father.get('pool', default['pool'])
                    default_disks = father.get('disks', default['disks'])
                    default_nets = father.get('nets', default['nets'])
                    default_template = father.get('template', '')
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
                    default_template = ''
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
                disks = info.get('disks', default_disks)
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
                template = info.get('template', default_template)
                cloudinit = info.get('cloudinit', default_cloudinit)
                nested = info.get('nested', default_nested)
                reservedns = info.get('reservedns', default_reservedns)
                reservehost = info.get('reservehost', default_reservehost)
                flavor = info.get('flavor', default_flavor)
                if flavor is None:
                    flavor = "%scpus %sMb ram" % (numcpus, memory)
                results.append([profile, flavor, pool, diskinfo, template, netinfo, cloudinit, nested,
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
                    image = next((e for e in [info.get('image'), info.get('template')] if e is not None), '')
                    nets = info.get('nets', '')
                    ports = info.get('ports', '')
                    volumes = next((e for e in [info.get('volumes'), info.get('disks')] if e is not None), '')
                    # environment = profile.get('environment', '')
                    cmd = info.get('cmd', '')
                    results.append([profile, image, nets, ports, volumes, cmd])
        return results

    def create_product(self, name, repo=None, group=None, plan=None, latest=False, overrides={}):
        """Create product"""
        if repo is not None and group is not None:
            products = [product for product in self.list_products()
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
                    common.pprint("Product not found. Leaving...", color='red')
                    os._exit(1)
        elif len(products) > 1:
                    common.pprint("Product found in several repos or groups. Specify one...", color='red')
                    for product in products:
                        group = product['group']
                        repo = product['repo']
                        print("repo:%s\tgroup:%s" % (repo, group))
                    os._exit(1)
        else:
            product = products[0]
            plan = nameutils.get_random_name() if plan is None else plan
            url = product['url']
            inputfile = product['file']
            repo = product['repo']
            repodir = "%s/.kcli/repo_%s" % (os.environ.get('HOME'), repo)
            group = product['group']
            template = product.get('template')
            parameters = product.get('parameters')
            if template is not None:
                print("Note that this product uses template: %s" % template)
            if parameters is not None:
                for parameter in parameters:
                    applied_parameter = overrides[parameter] if parameter in overrides else parameters[parameter]
                    print("Using parameter %s: %s" % (parameter, applied_parameter))
            extraparameters = list(set(overrides) - set(parameters)) if parameters is not None else overrides
            for parameter in extraparameters:
                print("Using parameter %s: %s" % (parameter, overrides[parameter]))
            common.pprint("Gathering all from group %s" % group, color='green')
            if os.path.exists(group):
                common.pprint("Using current directory %s. Make sure it contains kcli content" % group, color='green')
                productdir = group
                self.plan(plan, path=productdir, inputfile=inputfile, overrides=overrides)
            elif os.path.exists("%s/%s" % (repodir, group)) and not latest:
                common.pprint("Using cached directory %s/%s" % (repodir, group), color='green')
                productdir = "%s/%s" % (repodir, group)
                self.plan(plan, path=productdir, inputfile=inputfile, overrides=overrides)
            elif os.path.exists("%s/%s" % (repodir, group)) and latest:
                productdir = "%s/%s" % (repodir, group)
                shutil.rmtree(productdir)
                self.plan(plan, get=url, path=productdir, inputfile=inputfile, overrides=overrides)
            else:
                productdir = "%s/%s" % (repodir, group)
                self.plan(plan, get=url, path=productdir, inputfile=inputfile, overrides=overrides)
            # os.chdir(productdir)
            # common.pprint("Running: kcli plan -f %s %s" % (inputfile, plan), color='green')
            # self.plan(plan, inputfile=inputfile, overrides=overrides)
            # os.chdir('..')
            common.pprint("Product can be deleted with: kcli plan -d %s" % plan, color='green')
        return {'result': 'success', 'plan': plan}

    def plan(self, plan, ansible=False, get=None, path=None, autostart=False, container=False, noautostart=False,
             inputfile=None, start=False, stop=False, delete=False, delay=0, force=True, overrides={}, info=False):
        """Create/Delete/Stop/Start vms from plan file"""
        k = self.k
        no_overrides = not overrides
        newvms = []
        existingvms = []
        vmprofiles = {key: value for key, value in self.profiles.items()
                      if 'type' not in value or value['type'] == 'vm'}
        containerprofiles = {key: value for key, value in self.profiles.items()
                             if 'type' in value and value['type'] == 'container'}
        if plan is None:
            plan = nameutils.get_random_name()
        # if path is None:
        #    path = plan
        if delete:
            deletedvms = []
            dnsclients = []
            networks = []
            if plan == '':
                common.pprint("That would delete every vm...Not doing that", color='red')
                os._exit(1)
            if not force:
                common.confirm('Are you sure about deleting plan %s' % plan)
            found = False
            if not self.extraclients:
                deleteclients = {self.client: k}
            else:
                deleteclients = self.extraclients
                deleteclients.update({self.client: k})
            for hypervisor in deleteclients:
                c = deleteclients[hypervisor]
                for vm in sorted(c.list()):
                    name = vm[0]
                    description = vm[4]
                    if description == plan:
                        vmnetworks = c.vm_ports(name)
                        for network in vmnetworks:
                            if network != 'default' and network not in networks:
                                networks.append(network)
                        dnshost, domain = c.dnsinfo(name)
                        c.delete(name)
                        if dnshost is not None and domain is not None and dnshost in self.clients:
                            if dnshost in dnsclients:
                                z = dnsclients[dnshost]
                            elif dnshost in self.clients:
                                z = Kconfig(client=dnshost).k
                                dnsclients[dnshost] = z
                            z.delete_dns(dnshost, domain)
                        common.set_lastvm(name, self.client, delete=True)
                        common.pprint("VM %s deleted on %s!" % (name, hypervisor), color='green')
                        deletedvms.append(name)
                        found = True
            if container:
                from kvirt import dockerutils
                for cont in sorted(dockerutils.list_containers(k)):
                    name = cont[0]
                    container_plan = cont[3]
                    if container_plan == plan:
                        dockerutils.delete_container(k, name)
                        common.pprint("Container %s deleted!" % name, color='green')
                        found = True
            # for network in k.list_networks():
            #    if 'plan' in network and network['plan'] == plan:
            if not self.keep_networks and networks:
                found = True
                for network in networks:
                    networkresult = k.delete_network(network)
                    if networkresult['result'] == 'success':
                        common.pprint("Unused network %s deleted!" % network, color='green')
            for keyfile in glob.glob("%s.key*" % plan):
                common.pprint("file %s from %s deleted!" % (keyfile, plan), color='green')
                os.remove(keyfile)
            if found:
                common.pprint("Plan %s deleted!" % plan, color='green')
            else:
                common.pprint("Nothing to do for plan %s" % plan, color='red')
                os._exit(1)
            return {'result': 'success', 'deletedvm': deletedvms}
        if autostart:
            common.pprint("Set vms from plan %s to autostart" % plan, color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.update_start(name, start=True)
                    common.pprint("%s set to autostart!" % name, color='green')
            return {'result': 'success'}
        if noautostart:
            common.pprint("Preventing vms from plan %s to autostart" % plan, color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.update_start(name, start=False)
                    common.pprint("%s prevented to autostart!" % name, color='green')
            return {'result': 'success'}
        if start:
            common.pprint("Starting vms from plan %s" % plan, color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.start(name)
                    common.pprint("VM %s started!" % name, color='green')
            if container:
                from kvirt import dockerutils
                for cont in sorted(dockerutils.list_containers(k)):
                    name = cont[0]
                    containerplan = cont[3]
                    if containerplan == plan:
                        dockerutils.start_container(k, name)
                        common.pprint("Container %s started!" % name, color='green')
            common.pprint("Plan %s started!" % plan, color='green')
            return {'result': 'success'}
        if stop:
            common.pprint("Stopping vms from plan %s" % plan, color='green')
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    k.stop(name)
                    common.pprint("%s stopped!" % name, color='green')
            if container:
                from kvirt import dockerutils
                for cont in sorted(dockerutils.list_containers(k)):
                    name = cont[0]
                    containerplan = cont[3]
                    if containerplan == plan:
                        dockerutils.stop_container(k, name)
                        common.pprint("Container %s stopped!" % name, color='green')
            common.pprint("Plan %s stopped!" % plan, color='green')
            return {'result': 'success'}
        if get is not None:
            # path = '.' if path is None else path
            path = plan if path is None else path
            common.pprint("Retrieving specified plan from %s to %s" % (get, path), color='green')
            if not os.path.exists(path):
                os.mkdir(path)
                common.fetch(get, path)
            # os.chdir(path)
        if inputfile is None:
            inputfile = 'kcli_plan.yml'
            common.pprint("using default input file kcli_plan.yml", color='green')
        if path is not None:
            os.chdir(path)
        inputfile = os.path.expanduser(inputfile)
        if not os.path.exists(inputfile):
            common.pprint("No input file found nor default kcli_plan.yml.Leaving....", color='red')
            os._exit(1)
        if info:
            self.info_plan(inputfile)
            return {'result': 'success'}
        # basedir = os.path.dirname(inputfile)
        basedir = os.path.dirname(inputfile) if os.path.dirname(inputfile) != '' else '.'
        env = Environment(block_start_string='[%', block_end_string='%]', variable_start_string='[[',
                          variable_end_string=']]', loader=FileSystemLoader(basedir))
        templ = env.get_template(os.path.basename(inputfile))
        parameters = common.get_parameters(inputfile)
        basefile = None
        if parameters is not None:
            parameters = yaml.load(parameters)['parameters']
            for parameter in parameters:
                if parameter == 'baseplan':
                    basefile = parameters['baseplan']
                    baseparameters = common.get_parameters(basefile)
                    if baseparameters is not None:
                        baseparameters = yaml.load(baseparameters)['parameters']
                        for baseparameter in baseparameters:
                            if baseparameter not in overrides:
                                overrides[baseparameter] = baseparameters[baseparameter]
                elif parameter not in overrides:
                    overrides[parameter] = parameters[parameter]
        with open(inputfile, 'r') as entries:
            overrides.update(self.overrides)
            entries = templ.render(overrides)
            entries = yaml.load(entries)
            parameters = entries.get('parameters')
            if parameters is not None:
                del entries['parameters']
            vmentries = [entry for entry in entries if 'type' not in entries[entry] or entries[entry]['type'] == 'vm']
            diskentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'disk']
            networkentries = [entry for entry in entries
                              if 'type' in entries[entry] and entries[entry]['type'] == 'network']
            containerentries = [entry for entry in entries
                                if 'type' in entries[entry] and entries[entry]['type'] == 'container']
            ansibleentries = [entry for entry in entries
                              if 'type' in entries[entry] and entries[entry]['type'] == 'ansible']
            profileentries = [entry for entry in entries
                              if 'type' in entries[entry] and entries[entry]['type'] == 'profile']
            templateentries = [entry for entry in entries
                               if 'type' in entries[entry] and entries[entry]['type'] == 'template']
            poolentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'pool']
            planentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'plan']
            dnsentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'dns']
            for p in profileentries:
                vmprofiles[p] = entries[p]
            if planentries:
                common.pprint("Deploying Plans...", color='green')
                for planentry in planentries:
                    details = entries[planentry]
                    url = details.get('url')
                    path = details.get('path', planentry)
                    inputfile = details.get('file', 'kcli_plan.yml')
                    run = details.get('run', False)
                    if url is None:
                        common.pprint("Missing Url for plan %s. Not creating it..." % planentry, color='blue')
                        continue
                    else:
                        common.pprint("Grabbing Plan %s!" % planentry, color='green')
                        if not os.path.exists(planentry):
                            os.mkdir(planentry)
                            common.fetch(url, path)
                        if run:
                            os.chdir(path)
                            if no_overrides and parameters:
                                common.pprint("Using parameters from master plan in child ones", color='blue')
                                for override in overrides:
                                    print("Using parameter %s: %s" % (override, overrides[override]))
                            common.pprint("Running kcli plan -f %s %s" % (inputfile, plan), color='green')
                            self.plan(plan, ansible=False, get=None, path=path, autostart=False, container=False,
                                      noautostart=False, inputfile=inputfile, start=False, stop=False, delete=False,
                                      delay=delay, overrides=overrides)
                            os.chdir('..')
                return {'result': 'success'}
            if networkentries:
                common.pprint("Deploying Networks...", color='green')
                for net in networkentries:
                    netprofile = entries[net]
                    if k.net_exists(net):
                        common.pprint("Network %s skipped!" % net, color='blue')
                        continue
                    cidr = netprofile.get('cidr')
                    nat = bool(netprofile.get('nat', True))
                    if cidr is None:
                        common.pprint("Missing Cidr for network %s. Not creating it..." % net, color='blue')
                        continue
                    dhcp = netprofile.get('dhcp', True)
                    domain = netprofile.get('domain')
                    pxe = netprofile.get('pxe')
                    vlan = netprofile.get('vlan')
                    result = k.create_network(name=net, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, plan=plan,
                                              pxe=pxe, vlan=vlan)
                    common.handle_response(result, net, element='Network ')
            if poolentries:
                common.pprint("Deploying Pool...", color='green')
                pools = k.list_pools()
                for pool in poolentries:
                    if pool in pools:
                        common.pprint("Pool %s skipped!" % pool, color='blue')
                        continue
                    else:
                        poolprofile = entries[pool]
                        poolpath = poolprofile.get('path')
                        if poolpath is None:
                            common.pprint("Pool %s skipped as path is missing!" % pool, color='blue')
                            continue
                        k.create_pool(pool, poolpath)
            if templateentries:
                common.pprint("Deploying Templates...", color='green')
                templates = [os.path.basename(t) for t in k.volumes()]
                for template in templateentries:
                    if template in templates:
                        common.pprint("Template %s skipped!" % template, color='blue')
                        continue
                    else:
                        templateprofile = entries[template]
                        pool = templateprofile.get('pool', self.pool)
                        url = templateprofile.get('url')
                        cmd = templateprofile.get('cmd')
                        if url is None:
                            common.pprint("Template %s skipped as url is missing!" % template, color='blue')
                            continue
                        if not url.endswith('qcow2') and not url.endswith('img') and not url.endswith('qc2')\
                                and not url.endswith('qcow2.xz'):
                            common.pprint("Opening url %s for you to grab complete url for %s" % (url, template),
                                          color='blue')
                            webbrowser.open(url, new=2, autoraise=True)
                            url = input("Copy Url:\n")
                            if url.strip() == '':
                                common.pprint("Template %s skipped as url is empty!" % template, color='blue')
                                continue
                        result = k.add_image(url, pool, cmd=cmd)
                        common.handle_response(result, template, element='Template ', action='Added')
            if dnsentries:
                common.pprint("Deploying Dns Entry...", color='green')
                dnsclients = {}
                for dnsentry in dnsentries:
                    dnsprofile = entries[dnsentry]
                    dnsdomain = dnsprofile.get('domain')
                    dnsnet = dnsprofile.get('net')
                    dnsdomain = dnsprofile.get('domain', dnsnet)
                    dnsip = dnsprofile.get('ip')
                    dnsalias = dnsprofile.get('alias', [])
                    host = dnsprofile.get('host')
                    if host is None:
                        z = k
                    elif host in dnsclients:
                        z = dnsclients[host]
                    elif host in self.clients:
                        # z = Kconfig(client=host, debug=args.debug, region=args.region, zone=args.zone)
                        z = Kconfig(client=host).k
                        dnsclients[host] = z
                    else:
                        common.pprint("Host %s not found. Skipping" % host, color='blue')
                        return
                    if dnsip is None:
                        common.pprint("Missing ip. Skipping!", color='blue')
                        return
                    if dnsnet is None:
                        common.pprint("Missing net. Skipping!", color='blue')
                        return
                    z.reserve_dns(name=dnsentry, nets=[dnsnet], domain=dnsdomain, ip=dnsip, alias=dnsalias, force=True)
            if vmentries:
                common.pprint("Deploying Vms...", color='green')
                vmcounter = 0
                hosts = []
                for name in vmentries:
                    if len(vmentries) == 1 and 'name' in overrides:
                        newname = overrides['name']
                        profile = entries[name]
                        name = newname
                    else:
                        profile = entries[name]
                    host = profile.get('host')
                    if host is None:
                        z = k
                    elif host in hosts:
                        z = hosts[host]
                    elif host in self.clients:
                        # z = Kconfig(client=host, debug=args.debug, region=args.region, zone=args.zone)
                        z = Kconfig(client=host).k
                        hosts[host] = z
                    else:
                        common.pprint("Host %s not found. Using default one" % host, color='blue')
                        z = k
                    if z.exists(name):
                        common.pprint("VM %s skipped!" % name, color='blue')
                        existingvms.append(name)
                        continue
                    if 'profile' in profile and profile['profile'] in vmprofiles:
                        customprofile = vmprofiles[profile['profile']]
                        profilename = profile['profile']
                    else:
                        customprofile = {}
                        profilename = 'kvirt'
                    if customprofile:
                        profile.update(customprofile)
                    # cmds = default_cmds + customprofile.get('cmds', []) + profile.get('cmds', [])
                    # ips = profile.get('ips')
                    sharedkey = next((e for e in [profile.get('sharedkey'), customprofile.get('sharedkey'),
                                                  self.sharedkey] if e is not None))
                    if sharedkey:
                        vmcounter += 1
                        if not os.path.exists("%s.key" % plan) or not os.path.exists("%s.key.pub" % plan):
                            os.system("ssh-keygen -qt rsa -N '' -f %s.key" % plan)
                        publickey = open("%s.key.pub" % plan).read().strip()
                        privatekey = open("%s.key" % plan).read().strip()
                        if 'keys' not in profile:
                            profile['keys'] = [publickey]
                        else:
                            profile['keys'].append(publickey)
                        if 'files' in profile:
                            profile['files'].append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                            profile['files'].append({'path': '/root/.ssh/id_rsa.pub', 'content': publickey})
                        else:
                            profile['files'] = [{'path': '/root/.ssh/id_rsa', 'content': privatekey},
                                                {'path': '/root/.ssh/id_rsa.pub', 'content': publickey}]
                        if vmcounter >= len(vmentries):
                            os.remove("%s.key.pub" % plan)
                            os.remove("%s.key" % plan)
                    result = self.create_vm(name, profilename, overrides=overrides, customprofile=profile, k=z,
                                            plan=plan, basedir=basedir)
                    common.handle_response(result, name)
                    if result['result'] == 'success':
                        newvms.append(name)
                        common.set_lastvm(name, self.client)
                    _ansible = next((e for e in [profile.get('ansible'), customprofile.get('ansible')]
                                     if e is not None), None)
                    if _ansible is not None:
                        for element in _ansible:
                            if 'playbook' not in element:
                                continue
                            playbook = element['playbook']
                            if 'variables' in element:
                                variables = element['variables']
                            else:
                                variables = None
                            if 'verbose' in element:
                                verbose = element['verbose']
                            else:
                                verbose = False
                            ansibleutils.play(z, name, playbook=playbook, variables=variables, verbose=verbose)
                    if delay > 0:
                        sleep(delay)
            if diskentries:
                common.pprint("Deploying Disks...", color='green')
            for disk in diskentries:
                profile = entries[disk]
                pool = profile.get('pool')
                vms = profile.get('vms')
                template = profile.get('template')
                size = int(profile.get('size', 10))
                if pool is None:
                    common.pprint("Missing Key Pool for disk section %s. Not creating it..." % disk, color='red')
                    continue
                if vms is None:
                    common.pprint("Missing or Incorrect Key Vms for disk section %s. Not creating it..." % disk,
                                  color='red')
                    continue
                if k.disk_exists(pool, disk):
                    common.pprint("Disk %s skipped!" % disk, color='blue')
                    continue
                if len(vms) > 1:
                    shareable = True
                else:
                    shareable = False
                newdisk = k.create_disk(disk, size=size, pool=pool, template=template, thin=False)
                common.pprint("Disk %s deployed!" % disk, color='green')
                for vm in vms:
                    k.add_disk(name=vm, size=size, pool=pool, template=template, shareable=shareable, existing=newdisk,
                               thin=False)
            if containerentries:
                common.pprint("Deploying Containers...", color='green')
                label = "plan=%s" % plan
                for container in containerentries:
                    if dockerutils.exists_container(k, container):
                        common.pprint("Container %s skipped!" % container, color='blue')
                        continue
                    profile = entries[container]
                    if 'profile' in profile and profile['profile'] in containerprofiles:
                        customprofile = containerprofiles[profile['profile']]
                    else:
                        customprofile = {}
                    image = next((e for e in [profile.get('image'), profile.get('template'), customprofile.get('image'),
                                              customprofile.get('template')] if e is not None), None)
                    nets = next((e for e in [profile.get('nets'), customprofile.get('nets')] if e is not None), None)
                    ports = next((e for e in [profile.get('ports'), customprofile.get('ports')] if e is not None), None)
                    volumes = next((e for e in [profile.get('volumes'), profile.get('disks'),
                                                customprofile.get('volumes'), customprofile.get('disks')]
                                    if e is not None), None)
                    environment = next((e for e in [profile.get('environment'), customprofile.get('environment')]
                                        if e is not None), None)
                    cmd = next((e for e in [profile.get('cmd'), customprofile.get('cmd')] if e is not None), None)
                    common.pprint("Container %s deployed!" % container, color='green')
                    dockerutils.create_container(k, name=container, image=image, nets=nets, cmd=cmd, ports=ports,
                                                 volumes=volumes, environment=environment, label=label)
            if ansibleentries:
                if not newvms:
                    common.pprint("Ansible skipped as no new vm within playbook provisioned", color='blue')
                    return
                for entry in sorted(ansibleentries):
                    _ansible = entries[entry]
                    if 'playbook' not in _ansible:
                        common.pprint("Missing Playbook for ansible.Ignoring...", color='red')
                        os._exit(1)
                    playbook = _ansible['playbook']
                    if 'verbose' in _ansible:
                        verbose = _ansible['verbose']
                    else:
                        verbose = False
                    if 'groups' in _ansible:
                        groups = _ansible['groups']
                    else:
                        groups = {}
                    vms = []
                    if 'vms' in _ansible:
                        vms = _ansible['vms']
                        for vm in vms:
                            if vm not in newvms:
                                vms.remove(vm)
                    else:
                        vms = newvms
                    if not vms:
                        common.pprint("Ansible skipped as no new vm within playbook provisioned", color='blue')
                        return
                    ansibleutils.make_inventory(k, plan, newvms, tunnel=self.tunnel, groups=groups)
                    ansiblecommand = "ansible-playbook"
                    if verbose:
                        ansiblecommand = "%s -vvv" % ansiblecommand
                    ansibleconfig = os.path.expanduser('~/.ansible.cfg')
                    with open(ansibleconfig, "w") as f:
                        f.write("[ssh_connection]\nretries=10\n")
                    print("Running: %s -i /tmp/%s.inv %s" % (ansiblecommand, plan, playbook))
                    os.system("%s -i /tmp/%s.inv %s" % (ansiblecommand, plan, playbook))
        if ansible:
            common.pprint("Deploying Ansible Inventory...", color='green')
            if os.path.exists("/tmp/%s.inv" % plan):
                common.pprint("Inventory in /tmp/%s.inv skipped!" % plan, color='blue')
            else:
                common.pprint("Creating ansible inventory for plan %s in /tmp/%s.inv" % (plan, plan), color='green')
                vms = []
                for vm in sorted(k.list()):
                    name = vm[0]
                    description = vm[4]
                    if description == plan:
                        vms.append(name)
                ansibleutils.make_inventory(k, plan, vms, tunnel=self.tunnel)
                return
        returndata = {'result': 'success', 'plan': plan}
        if newvms:
            returndata['newvms'] = newvms
        if existingvms:
            returndata['existingvms'] = existingvms
        allvms = newvms + existingvms
        returndata['vms'] = allvms if allvms else []
        return returndata

    def handle_host(self, pool=None, templates=[], switch=None, download=False,
                    url=None, cmd=None, sync=False):
        """

        :param pool:
        :param templates:
        :param switch:
        :param download:
        :param url:
        :param cmd:
        :param sync:
        :return:
        """
        if download:
            k = self.k
            if pool is None:
                pool = self.pool
                common.pprint("Using pool %s" % pool, color='red')
            if url is None and not templates:
                common.pprint("Missing template or url.Leaving...", color='red')
                return {'result': 'failure', 'reason': "Missing template"}
            for template in templates:
                if url is None:
                    url = TEMPLATES[template]
                    shortname = os.path.basename(url)
                    template = os.path.basename(template)
                    if not url.endswith('qcow2') and not url.endswith('img') and not url.endswith('qc2')\
                            and not url.endswith('qcow2.xz'):
                        if 'web' in sys.argv[0]:
                            return {'result': 'failure', 'reason': "Missing url"}
                        common.pprint("Opening url %s for you to grab complete url for %s" % (url, template), 'blue')
                        webbrowser.open(url, new=2, autoraise=True)
                        url = input("Copy Url:\n")
                        if url.strip() == '':
                            common.pprint("Missing proper url.Leaving...", color='red')
                            return {'result': 'failure', 'reason': "Missing template"}
                        search = re.search(r".*/(.*)\?.*", url)
                        if search is not None:
                            shortname = search.group(1)
                else:
                    shortname = os.path.basename(url)
                if cmd is None and template != '' and template in TEMPLATESCOMMANDS:
                    cmd = TEMPLATESCOMMANDS[template]
                common.pprint("Grabbing template %s..." % shortname, color='green')
                result = k.add_image(url, pool, cmd=cmd, name=shortname)
                common.handle_response(result, shortname, element='Template ', action='Added')
            return {'result': 'success'}
        elif switch:
            if switch not in self.clients:
                common.pprint("Client %s not found in config.Leaving...." % switch, color='red')
                return {'result': 'failure', 'reason': "Client %s not found in config" % switch}
            enabled = self.ini[switch].get('enabled', True)
            if not enabled:
                common.pprint("Client %s is disabled.Leaving...." % switch, color='red')
                return {'result': 'failure', 'reason': "Client %s is disabled" % switch}
            common.pprint("Switching to client %s..." % switch, color='green')
            inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
            if os.path.exists(inifile):
                newini = ''
                for line in open(inifile).readlines():
                    if 'client' in line:
                        newini += " client: %s\n" % switch
                    else:
                        newini += line
                open(inifile, 'w').write(newini)
            return {'result': 'success'}
        elif sync:
            k = self.k
            if not self.extraclients:
                common.pprint("Nothing to do. Leaving...", color='blue')
                return {'result': 'success'}
            for cli in self.extraclients:
                dest = self.extraclients[cli]
                common.pprint("syncing client templates from %s to %s" % (self.client, cli), color='green')
                common.pprint("Note rhel templates are currently not synced", color='green')
            for vol in k.volumes():
                template = os.path.basename(vol)
                if template in [os.path.basename(v) for v in dest.volumes()]:
                    common.pprint("Ignoring %s as it's already there" % template, color='blue')
                    continue
                url = None
                for n in list(TEMPLATES.values()):
                    if n is None:
                        continue
                    elif n.split('/')[-1] == template:
                        url = n
                if url is None:
                        return {'result': 'failure', 'reason': "template not in default list"}
                if not url.endswith('qcow2') and not url.endswith('img') and not url.endswith('qc2'):
                    if 'web' in sys.argv[0]:
                        return {'result': 'failure', 'reason': "Missing url"}
                    common.pprint("Opening url %s for you to grab complete url for %s" % (url, vol), color='blue')
                    webbrowser.open(url, new=2, autoraise=True)
                    url = input("Copy Url:\n")
                    if url.strip() == '':
                        common.pprint("Missing proper url.Leaving...", color='red')
                        return {'result': 'failure', 'reason': "Missing template"}
                cmd = None
                if vol in TEMPLATESCOMMANDS:
                    cmd = TEMPLATESCOMMANDS[template]
                common.pprint("Grabbing template %s..." % template, color='green')
                dest.add_image(url, pool, cmd=cmd)
        return {'result': 'success'}
