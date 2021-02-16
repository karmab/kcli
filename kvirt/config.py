#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvirt config class
"""

import base64
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined as undefined
from jinja2.exceptions import TemplateSyntaxError, TemplateError
from kvirt.defaults import IMAGES, IMAGESCOMMANDS
from kvirt import ansibleutils
from kvirt.jinjafilters import jinjafilters
from kvirt import nameutils
from kvirt import common
from kvirt.common import error, pprint, success, warning, generate_rhcos_iso
from kvirt import k3s
from kvirt import kubeadm
from kvirt.expose import Kexposer
from kvirt import openshift
from kvirt.internalplans import haproxy as haproxyplan
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from distutils.spawn import find_executable
from getpass import getuser
import glob
import os
import re
import socket
from shutil import rmtree
import sys
from time import sleep
import webbrowser
import yaml

zerotier_service = """[Unit]
Description=Zero Tier service
After=network-online.target
Wants=network-online.target
Before=kubelet.service
[Service]
Type=forking
KillMode=none
Restart=on-failure
RemainAfterExit=yes
ExecStartPre=modprobe tun
ExecStartPre=podman pull quay.io/karmab/zerotier-cli
ExecStartPre=podman create --name=zerotier -it --cap-add=NET_ADMIN --device=/dev/net/tun --cap-add=SYS_ADMIN \
--net=host --entrypoint=/bin/sh karmab/zerotier-cli -c "zerotier-one -d ; sleep 10 ; \
{zerotier_join} ; \
sleep infinity"
ExecStart=podman start zerotier
ExecStop=podman stop -t 10 zerotier
ExecStopPost=podman rm zerotier
{zerotier_kubelet_script}
[Install]
WantedBy=multi-user.target"""


zerotier_kubelet_data = """ExecStartPost=/bin/bash -c 'sleep 20 ;\
IP=$(ip -4 -o addr show ztppiqixar | cut -f7 -d" " | cut -d "/" -f 1 | head -1) ;\
if [ "$(grep $IP /etc/systemd/system/kubelet.service)" == "" ] ; then \
sed -i "/node-ip/d" /etc/systemd/system/kubelet.service ;\
sed -i "/.*node-labels*/a --node-ip=$IP --address=$IP \\" /etc/systemd/system/kubelet.service ;\
systemctl daemon-reload ;\
fi'"""


class Kconfig(Kbaseconfig):
    """

    """
    def __init__(self, client=None, debug=False, quiet=False, region=None, zone=None, namespace=None):
        Kbaseconfig.__init__(self, client=client, debug=debug, quiet=quiet)
        if not self.enabled:
            k = None
        else:
            if self.type == 'kubevirt':
                if namespace is None:
                    namespace = self.options.get('namespace')
                context = self.options.get('context')
                cdi = self.options.get('cdi', True)
                datavolumes = self.options.get('datavolumes', True)
                readwritemany = self.options.get('readwritemany', False)
                ca_file = self.options.get('ca_file')
                if ca_file is not None:
                    ca_file = os.path.expanduser(ca_file)
                    if not os.path.exists(ca_file):
                        error("Ca file %s doesn't exist. Leaving" % ca_file)
                        os._exit(1)
                token = self.options.get('token')
                token_file = self.options.get('token_file')
                if token_file is not None:
                    token_file = os.path.expanduser(token_file)
                    if not os.path.exists(token_file):
                        error("Token file path doesn't exist. Leaving")
                        os._exit(1)
                    else:
                        token = open(token_file).read()
                registry = self.options.get('registry')
                access_mode = self.options.get('access_mode', 'NodePort')
                if access_mode not in ['External', 'LoadBalancer', 'NodePort']:
                    msg = "Incorrect access_mode %s. Should be External, NodePort or LoadBalancer" % access_mode
                    error(msg)
                    os._exit(1)
                from kvirt.providers.kubevirt import Kubevirt
                k = Kubevirt(context=context, token=token, ca_file=ca_file, host=self.host,
                             port=self.port, user=self.user, debug=debug, namespace=namespace, cdi=cdi,
                             datavolumes=datavolumes, readwritemany=readwritemany, registry=registry,
                             access_mode=access_mode)
                self.host = k.host
            elif self.type == 'gcp':
                credentials = self.options.get('credentials')
                if credentials is not None:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser(credentials)
                elif 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
                    error("set GOOGLE_APPLICATION_CREDENTIALS variable.Leaving...")
                    os._exit(1)
                project = self.options.get('project')
                if project is None:
                    error("Missing project in the configuration. Leaving")
                    os._exit(1)
                zone = self.options.get('zone', 'europe-west1-b') if zone is None else zone
                region = self.options.get('region') if region is None else region
                region = zone[:-2] if region is None else region
                from kvirt.providers.gcp import Kgcp
                k = Kgcp(region=region, zone=zone, project=project, debug=debug)
                self.overrides.update({'project': project})
            elif self.type == 'aws':
                region = self.options.get('region') if region is None else region
                if region is None:
                    error("Missing region in the configuration. Leaving")
                    os._exit(1)
                access_key_id = self.options.get('access_key_id')
                if access_key_id is None:
                    error("Missing access_key_id in the configuration. Leaving")
                    os._exit(1)
                access_key_secret = self.options.get('access_key_secret')
                if access_key_secret is None:
                    error("Missing access_key_secret in the configuration. Leaving")
                    os._exit(1)
                keypair = self.options.get('keypair')
                from kvirt.providers.aws import Kaws
                k = Kaws(access_key_id=access_key_id, access_key_secret=access_key_secret, region=region,
                         debug=debug, keypair=keypair)
            elif self.type == 'ovirt':
                datacenter = self.options.get('datacenter', 'Default')
                cluster = self.options.get('cluster', 'Default')
                user = self.options.get('user', 'admin@internal')
                password = self.options.get('password')
                if password is None:
                    error("Missing password in the configuration. Leaving")
                    os._exit(1)
                org = self.options.get('org')
                if org is None:
                    error("Missing org in the configuration. Leaving")
                    os._exit(1)
                ca_file = self.options.get('ca_file')
                if ca_file is None:
                    error("Missing ca_file in the configuration. Leaving")
                    os._exit(1)
                ca_file = os.path.expanduser(ca_file)
                if not os.path.exists(ca_file):
                    error("Ca file path doesn't exist. Leaving")
                    os._exit(1)
                imagerepository = self.options.get('imagerepository', 'ovirt-image-repository')
                filtervms = self.options.get('filtervms', False)
                filteruser = self.options.get('filteruser', False)
                filtertag = self.options.get('filtertag')
                from kvirt.providers.ovirt import KOvirt
                k = KOvirt(host=self.host, port=self.port, user=user, password=password,
                           debug=debug, datacenter=datacenter, cluster=cluster, ca_file=ca_file, org=org,
                           imagerepository=imagerepository, filtervms=filtervms, filteruser=filteruser,
                           filtertag=filtertag)
                self.overrides.update({'host': self.host, 'user': user, 'password': password})
            elif self.type == 'openstack':
                version = self.options.get('version', '2')
                domain = next((e for e in [self.options.get('domain'),
                                           os.environ.get("OS_USER_DOMAIN_NAME")] if e is not None), 'Default')
                auth_url = next((e for e in [self.options.get('auth_url'),
                                             os.environ.get("OS_AUTH_URL")] if e is not None),
                                None)
                if auth_url is None:
                    error("Missing auth_url in the configuration. Leaving")
                    os._exit(1)
                user = next((e for e in [self.options.get('user'),
                                         os.environ.get("OS_USERNAME")] if e is not None), 'admin')
                project = next((e for e in [self.options.get('project'),
                                            os.environ.get("OS_PROJECT_NAME")] if e is not None), 'admin')
                password = next((e for e in [self.options.get('password'),
                                             os.environ.get("OS_PASSWORD")] if e is not None), None)
                ca_file = next((e for e in [self.options.get('ca_file'),
                                            os.environ.get("OS_CACERT")] if e is not None), None)
                external_network = self.options.get('external_network')
                if password is None:
                    error("Missing password in the configuration. Leaving")
                    os._exit(1)
                if auth_url.endswith('v2.0'):
                    domain = None
                if ca_file is not None and not os.path.exists(os.path.expanduser(ca_file)):
                    error("Indicated ca_file %s not found. Leaving" % ca_file)
                    os._exit(1)
                from kvirt.providers.openstack import Kopenstack
                k = Kopenstack(host=self.host, port=self.port, user=user, password=password, version=version,
                               debug=debug, project=project, domain=domain, auth_url=auth_url, ca_file=ca_file,
                               external_network=external_network)
            elif self.type == 'vsphere':
                user = self.options.get('user')
                if user is None:
                    error("Missing user in the configuration. Leaving")
                    os._exit(1)
                password = self.options.get('password')
                if password is None:
                    error("Missing password in the configuration. Leaving")
                    os._exit(1)
                cluster = self.options.get('cluster')
                if cluster is None:
                    error("Missing cluster in the configuration. Leaving")
                datacenter = self.options.get('datacenter')
                if datacenter is None:
                    error("Missing datacenter in the configuration. Leaving")
                filtervms = self.options.get('filtervms', False)
                filteruser = self.options.get('filteruser', False)
                filtertag = self.options.get('filtertag')
                from kvirt.providers.vsphere import Ksphere
                k = Ksphere(self.host, user, password, datacenter, cluster, debug=debug, filtervms=filtervms,
                            filteruser=filteruser, filtertag=filtertag)
            elif self.type == 'packet':
                auth_token = self.options.get('auth_token')
                if auth_token is None:
                    error("Missing auth_token in the configuration. Leaving")
                    os._exit(1)
                project = self.options.get('project')
                if project is None:
                    error("Missing project in the configuration. Leaving")
                    os._exit(1)
                facility = self.options.get('facility')
                from kvirt.providers.packet import Kpacket
                k = Kpacket(auth_token, project, facility=facility, debug=debug,
                            tunnelhost=self.tunnelhost, tunneluser=self.tunneluser, tunnelport=self.tunnelport,
                            tunneldir=self.tunneldir)
            else:
                if self.host is None:
                    error("Problem parsing your configuration file")
                    os._exit(1)
                session = self.options.get('session', False)
                from kvirt.providers.kvm import Kvirt
                k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url,
                          debug=debug, insecure=self.insecure, session=session)
            if k.conn is None:
                error("Couldn't connect to client %s. Leaving..." % self.client)
                os._exit(1)
            for extraclient in self._extraclients:
                if extraclient not in self.ini:
                    warning("Missing section for client %s in config file. Trying to connect..." % extraclient)
                    self.ini[extraclient] = {'host': extraclient}
                c = Kconfig(client=extraclient)
                e = c.k
                self.extraclients[extraclient] = e
                if e.conn is None:
                    error("Couldn't connect to specify hypervisor %s. Leaving..." % extraclient)
                    os._exit(1)
        self.k = k
        default_data = {'config_%s' % k: self.default[k] for k in self.default}
        config_data = {'config_%s' % k: self.ini[self.client][k] for k in self.ini[self.client]}
        config_data['config_type'] = config_data.get('config_type', 'kvm')
        default_user = getuser() if config_data['config_type'] == 'kvm'\
            and self.host in ['localhost', '127.0.0.1'] else 'root'
        config_data['config_user'] = config_data.get('config_user', default_user)
        self.overrides.update(default_data)
        self.overrides.update(config_data)

    def create_vm(self, name, profile, overrides={}, customprofile={}, k=None,
                  plan='kvirt', basedir='.', client=None, onfly=None, wait=False, onlyassets=False):
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
        wrong_overrides = [y for y in overrides if '-' in y]
        if wrong_overrides:
            for wrong_override in wrong_overrides:
                error("Incorrect parameter %s. Hyphens are not allowed" % wrong_override)
            os._exit(1)
        overrides['name'] = name
        kube = overrides.get('kube')
        kubetype = overrides.get('kubetype')
        k = self.k if k is None else k
        tunnel = self.tunnel
        if profile is None:
            return {'result': 'failure', 'reason': "Missing profile"}
        vmprofiles = {k: v for k, v in self.profiles.items() if 'type' not in v or v['type'] == 'vm'}
        if not onlyassets:
            if customprofile:
                vmprofiles[profile] = customprofile
                customprofileimage = customprofile.get('image')
                if customprofileimage is not None:
                    clientprofile = "%s_%s" % (self.client, customprofileimage)
                    if clientprofile in vmprofiles and 'image' in vmprofiles[clientprofile]:
                        vmprofiles[profile]['image'] = vmprofiles[clientprofile]['image']
                    elif customprofileimage in IMAGES and self.type != 'packet' and\
                            IMAGES[customprofileimage] not in [os.path.basename(v) for v in self.k.volumes()]:
                        pprint("Image %s not found. Downloading" % customprofileimage)
                        self.handle_host(pool=self.pool, image=customprofileimage, download=True, update_profile=True)
                        vmprofiles[profile]['image'] = os.path.basename(IMAGES[customprofileimage])
            else:
                pprint("Deploying vm %s from profile %s..." % (name, profile))
            if profile not in vmprofiles:
                clientprofile = "%s_%s" % (self.client, profile)
                if clientprofile in vmprofiles:
                    if 'image' in vmprofiles[clientprofile]:
                        vmprofiles[profile] = {'image': vmprofiles[clientprofile]['image']}
                    if 'iso' in vmprofiles[clientprofile]:
                        vmprofiles[profile] = {'iso': vmprofiles[clientprofile]['iso']}
                elif profile in IMAGES and IMAGES[profile] not in [os.path.basename(v) for v in self.k.volumes()]\
                        and self.type not in ['aws', 'gcp', 'packet']:
                    pprint("Image %s not found. Downloading" % profile)
                    self.handle_host(pool=self.pool, image=profile, download=True, update_profile=True)
                    good_image = os.path.basename(IMAGES[profile])
                    if not good_image.endswith('.qcow2') and not good_image.endswith('.img'):
                        good_image = [x[4] for x in self.list_profiles() if x[0] == clientprofile][0]
                    vmprofiles[profile] = {'image': good_image}
                else:
                    pprint("Profile %s not found. Using the image as profile..." % profile)
                    vmprofiles[profile] = {'image': profile}
        elif customprofile:
            vmprofiles[profile] = customprofile
        else:
            vmprofiles[profile] = {'image': profile}
        profilename = profile
        profile = vmprofiles[profile]
        if not customprofile:
            profile.update(overrides)
        if 'base' in profile:
            father = vmprofiles[profile['base']]
            default_numcpus = father.get('numcpus', self.numcpus)
            default_memory = father.get('memory', self.memory)
            default_pool = father.get('pool', self.pool)
            default_disks = father.get('disks', self.disks)
            default_nets = father.get('nets', self.nets)
            default_image = father.get('image', self.image)
            default_cloudinit = father.get('cloudinit', self.cloudinit)
            default_nested = father.get('nested', self.nested)
            default_reservedns = father.get('reservedns', self.reservedns)
            default_reservehost = father.get('reservehost', self.reservehost)
            default_cpumodel = father.get('cpumodel', self.cpumodel)
            default_cpuflags = father.get('cpuflags', self.cpuflags)
            default_cpupinning = father.get('cpupinning', self.cpupinning)
            default_disksize = father.get('disksize', self.disksize)
            default_diskinterface = father.get('diskinterface', self.diskinterface)
            default_diskthin = father.get('diskthin', self.diskthin)
            default_guestid = father.get('guestid', self.guestid)
            default_iso = father.get('iso', self.iso)
            default_vnc = father.get('vnc', self.vnc)
            default_reserveip = father.get('reserveip', self.reserveip)
            default_start = father.get('start', self.start)
            default_autostart = father.get('autostart', self.autostart)
            default_keys = father.get('keys', self.keys)
            default_netmasks = father.get('netmasks', self.netmasks)
            default_gateway = father.get('gateway', self.gateway)
            default_dns = father.get('dns', self.dns)
            default_domain = father.get('domain', self.domain)
            default_files = father.get('files', self.files)
            default_enableroot = father.get('enableroot', self.enableroot)
            default_privatekey = father.get('privatekey', self.privatekey)
            default_networkwait = father.get('networkwait', self.networkwait)
            default_rhnregister = father.get('rhnregister', self.rhnregister)
            default_rhnserver = father.get('rhnserver', self.rhnserver)
            default_rhnuser = father.get('rhnuser', self.rhnuser)
            default_rhnpassword = father.get('rhnpassword', self.rhnpassword)
            default_rhnak = father.get('rhnactivationkey', self.rhnak)
            default_rhnorg = father.get('rhnorg', self.rhnorg)
            default_rhnpool = father.get('rhnpool', self.rhnpool)
            default_tags = father.get('tags', self.tags)
            default_flavor = father.get('flavor', self.flavor)
            default_cmds = common.remove_duplicates(self.cmds + father.get('cmds', []))
            default_scripts = common.remove_duplicates(self.scripts + father.get('scripts', []))
            default_dnsclient = father.get('dnsclient', self.dnsclient)
            default_storemetadata = father.get('storemetadata', self.storemetadata)
            default_notify = father.get('notify', self.notify)
            default_pushbullettoken = father.get('pushbullettoken', self.pushbullettoken)
            default_mailserver = father.get('mailserver', self.mailserver)
            default_mailfrom = father.get('mailfrom', self.mailfrom)
            default_mailto = father.get('mailto', self.mailto)
            default_notifycmd = father.get('notifycmd', self.notifycmd)
            default_notifyscript = father.get('notifyscript', self.notifyscript)
            default_notifymethods = father.get('notifymethods', self.notifymethods)
            default_slackchannel = father.get('slackchannel', self.slackchannel)
            default_pushbullettoken = father.get('pushbullettoken', self.pushbullettoken)
            default_slacktoken = father.get('slacktoken', self.slacktoken)
            default_sharedfolders = father.get('sharedfolders', self.sharedfolders)
            default_kernel = father.get('kernel', self.kernel)
            default_initrd = father.get('initrd', self.initrd)
            default_cmdline = father.get('cmdline', self.cmdline)
            default_placement = father.get('placement', self.placement)
            default_yamlinventory = father.get('yamlinventory', self.yamlinventory)
            default_cpuhotplug = father.get('cpuhotplug', self.cpuhotplug)
            default_memoryhotplug = father.get('memoryhotplug', self.memoryhotplug)
            default_numa = father.get('numa', self.numa)
            default_numamode = father.get('numamode', self.numamode)
            default_pcidevices = father.get('pcidevices', self.pcidevices)
            default_tpm = father.get('tpm', self.tpm)
            default_rng = father.get('rng', self.rng)
            default_zerotier_nets = father.get('zerotier_nets', self.zerotier_nets)
            default_zerotier_kubelet = father.get('zerotier_kubelet', self.zerotier_kubelet)
            default_virttype = father.get('virttype', self.virttype)
            default_securitygroups = father.get('securitygroups', self.securitygroups)
        else:
            default_numcpus = self.numcpus
            default_memory = self.memory
            default_pool = self.pool
            default_disks = self.disks
            default_nets = self.nets
            default_image = self.image
            default_cloudinit = self.cloudinit
            default_nested = self.nested
            default_reservedns = self.reservedns
            default_reservehost = self.reservehost
            default_cpumodel = self.cpumodel
            default_cpuflags = self.cpuflags
            default_cpupinning = self.cpupinning
            default_numamode = self.numamode
            default_numa = self.numa
            default_pcidevices = self.pcidevices
            default_tpm = self.tpm
            default_rng = self.rng
            default_zerotier_nets = self.zerotier_nets
            default_zerotier_kubelet = self.zerotier_kubelet
            default_disksize = self.disksize
            default_diskinterface = self.diskinterface
            default_diskthin = self.diskthin
            default_guestid = self.guestid
            default_iso = self.iso
            default_vnc = self.vnc
            default_reserveip = self.reserveip
            default_start = self.start
            default_autostart = self.autostart
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
            default_networkwait = self.networkwait
            default_rhnregister = self.rhnregister
            default_rhnserver = self.rhnserver
            default_rhnuser = self.rhnuser
            default_rhnpassword = self.rhnpassword
            default_rhnak = self.rhnak
            default_rhnorg = self.rhnorg
            default_rhnpool = self.rhnpool
            default_cmds = self.cmds
            default_scripts = self.scripts
            default_dnsclient = self.dnsclient
            default_storemetadata = self.storemetadata
            default_notify = self.notify
            default_pushbullettoken = self.pushbullettoken
            default_slacktoken = self.slacktoken
            default_mailserver = self.mailserver
            default_mailfrom = self.mailfrom
            default_mailto = self.mailto
            default_notifycmd = self.notifycmd
            default_notifyscript = self.notifyscript
            default_notifymethods = self.notifymethods
            default_slackchannel = self.slackchannel
            default_sharedfolders = self.sharedfolders
            default_kernel = self.kernel
            default_initrd = self.initrd
            default_cmdline = self.cmdline
            default_placement = self.placement
            default_yamlinventory = self.yamlinventory
            default_cpuhotplug = self.cpuhotplug
            default_memoryhotplug = self.memoryhotplug
            default_virttype = self.virttype
            default_securitygroups = self.securitygroups
        plan = profile.get('plan', plan)
        template = profile.get('template', default_image)
        image = profile.get('image', template)
        nets = profile.get('nets', default_nets)
        cpumodel = profile.get('cpumodel', default_cpumodel)
        cpuflags = profile.get('cpuflags', default_cpuflags)
        cpupinning = profile.get('cpupinning', default_cpupinning)
        numamode = profile.get('numamode', default_numamode)
        numa = profile.get('numa', default_numa)
        pcidevices = profile.get('pcidevices', default_pcidevices)
        tpm = profile.get('tpm', default_tpm)
        rng = profile.get('rng', default_rng)
        zerotier_nets = profile.get('zerotier_nets', default_zerotier_nets)
        zerotier_kubelet = profile.get('zerotier_kubelet', default_zerotier_kubelet)
        securitygroups = profile.get('securitygroups', default_securitygroups)
        numcpus = profile.get('numcpus', default_numcpus)
        memory = profile.get('memory', default_memory)
        pool = profile.get('pool', default_pool)
        disks = profile.get('disks', default_disks)
        disksize = profile.get('disksize', default_disksize)
        diskinterface = profile.get('diskinterface', default_diskinterface)
        diskthin = profile.get('diskthin', default_diskthin)
        if disks and isinstance(disks, dict) and 'default' in disks[0]:
            disks = [{'size': disksize, 'interface': diskinterface, 'thin': diskthin}]
        guestid = profile.get('guestid', default_guestid)
        iso = profile.get('iso', default_iso)
        vnc = profile.get('vnc', default_vnc)
        cloudinit = profile.get('cloudinit', default_cloudinit)
        if cloudinit and self.type == 'kvm' and\
                find_executable('mkisofs') is None and find_executable('genisoimage') is None:
            return {'result': 'failure', 'reason': "Missing mkisofs/genisoimage needed for cloudinit"}
        reserveip = profile.get('reserveip', default_reserveip)
        reservedns = profile.get('reservedns', default_reservedns)
        reservehost = profile.get('reservehost', default_reservehost)
        nested = profile.get('nested', default_nested)
        start = profile.get('start', default_start)
        autostart = profile.get('autostart', default_autostart)
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
                if isinstance(fil, str):
                    path = "/root/%s" % fil
                    if basedir != '.':
                        origin = "%s/%s" % (basedir, path)
                    origin = fil
                    content = None
                    files[index] = {'path': path, 'origin': origin}
                elif isinstance(fil, dict):
                    path = fil.get('path')
                    if not path.startswith('/'):
                        error("Incorrect path %s.Leaving..." % path)
                        os._exit(1)
                    origin = fil.get('origin')
                    content = fil.get('content')
                else:
                    return {'result': 'failure', 'reason': "Incorrect file entry"}
                if origin is not None:
                    if onfly is not None and '~' not in origin:
                        destdir = basedir
                        if '/' in origin:
                            destdir = os.path.dirname(origin)
                            os.makedirs(destdir, exist_ok=True)
                        common.fetch("%s/%s" % (onfly, origin), destdir)
                    origin = os.path.expanduser(origin)
                    if basedir != '.' and not origin.startswith('./') and not origin.startswith('/workdir/'):
                        origin = "%s/%s" % (basedir, origin)
                        files[index]['origin'] = origin
                    if not os.path.exists(origin):
                        return {'result': 'failure', 'reason': "File %s not found in %s" % (origin, name)}
                elif content is None:
                    return {'result': 'failure', 'reason': "Content of file %s not found in %s" % (path, name)}
                if path is None:
                    pprint("Using current directory for path in files of %s" % name)
                    path = os.path.basename(origin)
        enableroot = profile.get('enableroot', default_enableroot)
        tags = profile.get('tags', [])
        if default_tags:
            tags = default_tags + tags if tags else default_tags
        privatekey = profile.get('privatekey', default_privatekey)
        networkwait = profile.get('networkwait', default_networkwait)
        rhnregister = profile.get('rhnregister', default_rhnregister)
        rhnserver = profile.get('rhnserver', default_rhnserver)
        rhnuser = profile.get('rhnuser', default_rhnuser)
        rhnpassword = profile.get('rhnpassword', default_rhnpassword)
        rhnak = profile.get('rhnactivationkey', default_rhnak)
        rhnorg = profile.get('rhnorg', default_rhnorg)
        rhnpool = profile.get('rhnpool', default_rhnpool)
        flavor = profile.get('flavor', default_flavor)
        dnsclient = profile.get('dnsclient', default_dnsclient)
        storemetadata = profile.get('storemetadata', default_storemetadata)
        notify = profile.get('notify', default_notify)
        pushbullettoken = profile.get('pushbullettoken', default_pushbullettoken)
        slacktoken = profile.get('slacktoken', default_slacktoken)
        notifycmd = profile.get('notifycmd', default_notifycmd)
        notifyscript = profile.get('notifyscript', default_notifyscript)
        notifymethods = profile.get('notifymethods', default_notifymethods)
        slackchannel = profile.get('slackchannel', default_slackchannel)
        mailserver = profile.get('mailserver', default_mailserver)
        mailfrom = profile.get('mailfrom', default_mailfrom)
        mailto = profile.get('mailto', default_mailto)
        sharedfolders = profile.get('sharedfolders', default_sharedfolders)
        kernel = profile.get('kernel', default_kernel)
        initrd = profile.get('initrd', default_initrd)
        cmdline = profile.get('cmdline', default_cmdline)
        placement = profile.get('placement', default_placement)
        yamlinventory = profile.get('yamlinventory', default_yamlinventory)
        cpuhotplug = profile.get('cpuhotplug', default_cpuhotplug)
        memoryhotplug = profile.get('memoryhotplug', default_memoryhotplug)
        virttype = profile.get('virttype', default_virttype)
        overrides.update(profile)
        scriptcmds = []
        skip_rhnregister_script = False
        if rhnregister and image is not None and 'rhel' in image.lower():
            if rhnuser is not None and rhnpassword is not None:
                skip_rhnregister_script = True
                overrides['rhnuser'] = rhnuser
                overrides['rhnpassword'] = rhnpassword
            elif rhnak is not None and rhnorg is not None:
                skip_rhnregister_script = True
                overrides['rhnak'] = rhnak
                overrides['rhnorg'] = rhnorg
            else:
                msg = "Rhn registration required but missing credentials. Define rhnuser/rhnpassword or rhnak/rhnorg"
                return {'result': 'failure', 'reason': msg}
        if scripts:
            for script in scripts:
                if onfly is not None and '~' not in script:
                    destdir = basedir
                    if '/' in script:
                        destdir = os.path.dirname(script)
                        os.makedirs(destdir, exist_ok=True)
                    common.fetch("%s/%s" % (onfly, script), destdir)
                script = os.path.expanduser(script)
                if basedir != '.':
                    script = '%s/%s' % (basedir, script)
                if script.endswith('register.sh') and skip_rhnregister_script:
                    continue
                elif not os.path.exists(script):
                    return {'result': 'failure', 'reason': "Script %s not found" % script}
                else:
                    scriptbasedir = os.path.dirname(script) if os.path.dirname(script) != '' else '.'
                    env = Environment(loader=FileSystemLoader(scriptbasedir), undefined=undefined,
                                      extensions=['jinja2.ext.do'], trim_blocks=True, lstrip_blocks=True)
                    for jinjafilter in jinjafilters.jinjafilters:
                        env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
                    try:
                        templ = env.get_template(os.path.basename(script))
                        scriptentries = templ.render(overrides)
                    except TemplateSyntaxError as e:
                        msg = "Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message)
                        return {'result': 'failure', 'reason': msg}
                    except TemplateError as e:
                        msg = "Error rendering script %s. Got: %s" % (script, e.message)
                        return {'result': 'failure', 'reason': msg}
                    scriptlines = [line.strip() for line in scriptentries.split('\n') if line.strip() != '']
                    if scriptlines:
                        scriptcmds.extend(scriptlines)
        if skip_rhnregister_script and cloudinit and image is not None and image.lower().startswith('rhel'):
            rhncommands = []
            if rhnak is not None and rhnorg is not None:
                rhncommands.append('subscription-manager register --serverurl=%s --force --activationkey=%s --org=%s'
                                   % (rhnserver, rhnak, rhnorg))
                if image.startswith('rhel-8'):
                    rhncommands.append('subscription-manager repos --enable=rhel-8-for-x86_64-baseos-rpms')
                else:
                    rhncommands.append('subscription-manager repos --enable=rhel-7-server-rpms')
            elif rhnuser is not None and rhnpassword is not None:
                rhncommands.append('subscription-manager register --serverurl=%s --force --username=%s --password=%s'
                                   % (rhnserver, rhnuser, rhnpassword))
                if rhnpool is not None:
                    rhncommands.append('subscription-manager attach --pool=%s' % rhnpool)
                else:
                    rhncommands.append('subscription-manager attach --auto')
        else:
            rhncommands = []
        sharedfoldercmds = []
        if sharedfolders and self.type == 'kvm':
            for sharedfolder in sharedfolders:
                basefolder = os.path.basename(sharedfolder)
                cmd1 = "mkdir -p /mnt/%s" % sharedfolder
                cmd2 = "echo %s /mnt/%s 9p trans=virtio,version=9p2000.L,rw 0 0 >> /etc/fstab" % (basefolder,
                                                                                                  sharedfolder)
                sharedfoldercmds.append(cmd1)
                sharedfoldercmds.append(cmd2)
        if sharedfoldercmds:
            sharedfoldercmds.append("mount -a")
        zerotiercmds = []
        if zerotier_nets:
            if image is not None and common.needs_ignition(image):
                zerotier_join = ';'.join([' zerotier-cli join %s ' % entry for entry in zerotier_nets])
                zerotier_kubelet_script = zerotier_kubelet_data if zerotier_kubelet else ''
                zerotiercontent = zerotier_service.format(zerotier_join=zerotier_join,
                                                          zerotier_kubelet_script=zerotier_kubelet_script)
                files.append({'path': '/root/zerotier.service', 'content': zerotiercontent})
            else:
                zerotiercmds.append("curl -s https://install.zerotier.com | bash")
                for entry in zerotier_nets:
                    zerotiercmds.append("zerotier-cli join %s" % entry)
        networkwaitcommand = ['sleep %s' % networkwait] if networkwait > 0 else []
        cmds = networkwaitcommand + rhncommands + sharedfoldercmds + zerotiercmds + cmds + scriptcmds
        if notify:
            if notifycmd is None and notifyscript is None:
                if 'cos' in image:
                    notifycmd = 'journalctl --identifier=ignition --all --no-pager'
                else:
                    cloudinitfile = common.get_cloudinitfile(image)
                    notifycmd = "tail -100 %s" % cloudinitfile
            if notifyscript is not None:
                notifyscript = os.path.expanduser(notifyscript)
                if basedir != '.':
                    notifyscript = '%s/%s' % (basedir, notifyscript)
                if not os.path.exists(notifyscript):
                    notifycmd = None
                    notifyscript = None
                    warning("Notification required for %s but missing notifyscript" % name)
                else:
                    files.append({'path': '/root/.notify.sh', 'origin': notifyscript})
                    notifycmd = "bash /root/.notify.sh"
            for notifymethod in notifymethods:
                if notifymethod == 'pushbullet':
                    if pushbullettoken is None:
                        warning("Notification required for %s but missing pushbullettoken" % name)
                    elif notifyscript is None and notifycmd is None:
                        continue
                    else:
                        title = "Vm %s on %s report" % (name, self.client)
                        token = pushbullettoken
                        pbcmd = 'curl -su "%s:" -d type="note" -d body="`%s 2>&1`" -d title="%s" ' % (token,
                                                                                                      notifycmd,
                                                                                                      title)
                        pbcmd += 'https://api.pushbullet.com/v2/pushes'
                        if not cmds:
                            cmds = [pbcmd]
                        else:
                            cmds.append(pbcmd)
                elif notifymethod == 'slack':
                    if slackchannel is None:
                        warning("Notification required for %s but missing slack channel" % name)
                    elif slacktoken is None:
                        warning("Notification required for %s but missing slacktoken" % name)
                    else:
                        title = "Vm %s on %s report" % (name, self.client)
                        slackcmd = "info=`%s 2>&1 | sed 's/\\x2/ /g'`;" % notifycmd
                        slackcmd += """curl -X POST -H 'Authorization: Bearer %s'
 -H 'Content-type: application/json; charset=utf-8'
 --data '{"channel":"%s","text":"%s","attachments": [{"text":"'"$info"'","fallback":"nothing",
"color":"#3AA3E3","attachment_type":"default"}]}' https://slack.com/api/chat.postMessage""" % (slacktoken,
                                                                                               slackchannel, title)
                        slackcmd = slackcmd.replace('\n', '')
                        if not cmds:
                            cmds = [slackcmd]
                        else:
                            cmds.append(slackcmd)
                elif notifymethod == 'mail':
                    if mailserver is None:
                        warning("Notification required for %s but missing mailserver" % name)
                    elif mailfrom is None:
                        warning("Notification required for %s but missing mailfrom" % name)
                    elif not mailto:
                        warning("Notification required for %s but missing mailto" % name)
                    else:
                        title = "Vm %s on %s report" % (name, self.client)
                        now = datetime.now()
                        now = now. strftime("%a,%d %b %Y %H:%M:%S")
                        rcpt = '\n'.join(["RCPT TO:<%s>" % to for to in mailto])
                        tos = ','.join(["<%s>" % to for to in mailto])
                        mailcontent = """HELO %s
MAIL FROM:<%s>
%s
DATA
From: %s <%s>
To: %s
Date: %s
Subject: %s

$INFO

.
""" % (mailserver, mailfrom, rcpt, mailfrom, mailfrom, tos, now, title)
                        files.append({'path': '/tmp/.mail.txt', 'content': mailcontent})
                        mailcmd = ['pkg=yum ; which apt-get /dev/null 2>&1 && pkg=apt-get ; $pkg -y install nc']
                        mailcmd.append('export INFO=`%s 2>&1` ; envsubst < /tmp/.mail.txt > /tmp/mail.txt' % notifycmd)
                        mailcmd.append("nc %s 25 < /tmp/mail.txt" % mailserver)
                        if not cmds:
                            cmds = mailcmd
                        else:
                            cmds.extend(mailcmd)
                else:
                    error("Invalid method %s" % notifymethod)
        ips = [overrides[key] for key in overrides if key.startswith('ip')]
        netmasks = [overrides[key] for key in overrides if key.startswith('netmask')]
        if privatekey and self.type == 'kvm':
            privatekeyfile, publickeyfile = None, None
            for path in ["~/.kcli/id_rsa", "~/.kcli/id_dsa", "~/.ssh/id_rsa", "~/.ssh/id_dsa"]:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path) and os.path.exists(expanded_path + ".pub"):
                    privatekeyfile = expanded_path
                    publickeyfile = expanded_path + ".pub"
                    break
            if privatekeyfile is not None and publickeyfile is not None:
                privatekey = open(privatekeyfile).read().strip()
                publickey = open(publickeyfile).read().strip()
                warning("Injecting private key for %s" % name)
                if files:
                    files.append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                    files.append({'path': '/root/.ssh/id_rsa.pub', 'content': publickey})
                else:
                    files = [{'path': '/root/.ssh/id_rsa', 'content': privatekey},
                             {'path': '/root/.ssh/id_rsa.pub', 'content': publickey}]
                if self.host in ['127.0.0.1', 'localhost']:
                    authorized_keys_file = os.path.expanduser('~/.ssh/authorized_keys')
                    found = False
                    if os.path.exists(authorized_keys_file):
                        for line in open(authorized_keys_file).readlines():
                            if publickey in line:
                                found = True
                                break
                        if not found:
                            warning("Adding public key to authorized_keys_file for %s" % name)
                            with open(authorized_keys_file, 'a') as f:
                                f.write(publickey)
        if cmds and 'reboot' in cmds:
            while 'reboot' in cmds:
                cmds.remove('reboot')
            cmds.append('reboot')
        if image is not None and ('rhel-8' in image or 'rhcos' in image) and disks and not onlyassets:
            firstdisk = disks[0]
            if isinstance(firstdisk, str) and firstdisk.isdigit():
                firstdisk = int(firstdisk)
            if isinstance(firstdisk, int):
                firstdisksize = firstdisk
                if firstdisksize < 20:
                    pprint("Rounding up first disk to 20Gb")
                    disks[0] = 20
            elif isinstance(firstdisk, dict) and 'size' in firstdisk:
                firstdisksize = firstdisk['size']
                if firstdisksize < 20:
                    pprint("Rounding up first disk to 20Gb")
                    disks[0]['size'] = 20
            else:
                msg = "Incorrect first disk spec"
                return {'result': 'failure', 'reason': msg}
        metadata = {'plan': plan, 'profile': profilename}
        if reservedns and domain is not None:
            metadata['domain'] = domain
        if image is not None:
            metadata['image'] = image
        if dnsclient is not None:
            metadata['dnsclient'] = dnsclient
        if 'owner' in overrides:
            metadata['owner'] = overrides['owner']
        if kube is not None and kubetype is not None:
            metadata['kubetype'] = kubetype
            metadata['kube'] = kube
        if onlyassets:
            if image is not None and common.needs_ignition(image):
                version = common.ignition_version(image)
                nokeys = overrides.get('nokeys', False)
                noname = overrides.get('noname', False)
                data = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                       domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                       overrides=overrides, version=version, plan=plan, image=image, nokeys=nokeys,
                                       noname=noname)
            else:
                data = common.cloudinit(name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                        domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                        overrides=overrides, image=image, storemetadata=False)[0]
            return {'result': 'success', 'data': data}
        result = k.create(name=name, virttype=virttype, plan=plan, profile=profilename, flavor=flavor,
                          cpumodel=cpumodel, cpuflags=cpuflags, cpupinning=cpupinning, numamode=numamode, numa=numa,
                          numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool,
                          image=image, disks=disks, disksize=disksize, diskthin=diskthin,
                          diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit),
                          reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost),
                          start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns,
                          domain=domain, nested=bool(nested), tunnel=tunnel, files=files, enableroot=enableroot,
                          overrides=overrides, tags=tags, storemetadata=storemetadata,
                          sharedfolders=sharedfolders, kernel=kernel, initrd=initrd, cmdline=cmdline,
                          placement=placement, autostart=autostart, cpuhotplug=cpuhotplug, memoryhotplug=memoryhotplug,
                          pcidevices=pcidevices, tpm=tpm, rng=rng, metadata=metadata, securitygroups=securitygroups)
        if result['result'] != 'success':
            return result
        if dnsclient is not None and domain is not None:
            if dnsclient in self.clients:
                z = Kconfig(client=dnsclient).k
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
                    error("Couldn't assign DNS")
                else:
                    z.reserve_dns(name=name, nets=[domain], domain=domain, ip=ip, force=True)
            else:
                warning("Client %s not found. Skipping" % dnsclient)
        ansibleprofile = profile.get('ansible')
        if ansibleprofile is not None:
            if find_executable('ansible-playbook') is None:
                warning("ansible-playbook executable not found. Skipping ansible play")
            else:
                for element in ansibleprofile:
                    if 'playbook' not in element:
                        continue
                    playbook = element['playbook']
                    variables = element.get('variables', {})
                    verbose = element.get('verbose', False)
                    user = element.get('user')
                    ansibleutils.play(k, name, playbook=playbook, variables=variables, verbose=verbose, user=user,
                                      tunnel=self.tunnel, tunnelhost=self.host, tunnelport=self.port,
                                      tunneluser=self.user, yamlinventory=yamlinventory, insecure=self.insecure)
        if os.access(os.path.expanduser('~/.kcli'), os.W_OK):
            client = client if client is not None else self.client
            common.set_lastvm(name, client)
        if wait:
            if not cloudinit or not start or image is None:
                pprint("Skipping wait on %s" % name)
            else:
                self.wait(name, image=image)
                finishfiles = profile.get('finishfiles', [])
                if finishfiles:
                    self.handle_finishfiles(name, finishfiles)
        return {'result': 'success', 'vm': name}

    def list_plans(self):
        """

        :return:
        """
        k = self.k
        results = []
        plans = {}
        for vm in k.list():
            vmname = vm['name']
            plan = vm.get('plan')
            if plan is None or plan == 'kvirt' or plan == '':
                continue
            elif plan not in plans:
                plans[plan] = [vmname]
            else:
                plans[plan].append(vmname)
        for plan in plans:
            results.append([plan, ','.join(plans[plan])])
        return results

    def list_kubes(self):
        """

        :return:
        """
        k = self.k
        kubes = {}
        for vm in k.list():
            if 'kube' in vm and 'kubetype' in vm:
                vmname = vm['name']
                kube = vm['kube']
                kubetype = vm['kubetype']
                kubeplan = vm['plan']
                if kube not in kubes:
                    kubes[kube] = {'type': kubetype, 'plan': kubeplan, 'vms': [vmname]}
                else:
                    kubes[kube]['vms'].append(vmname)
        for kube in kubes:
            kubes[kube]['vms'] = ','.join(kubes[kube]['vms'])
        return kubes

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
            error("Product not found. Leaving...")
            os._exit(1)
        elif len(products) > 1:
            error("Product found in several repos or groups. Specify one...")
            for product in products:
                group = product['group']
                repo = product['repo']
                print("repo:%s\tgroup:%s" % (repo, group))
            os._exit(1)
        else:
            product = products[0]
            plan = nameutils.get_random_name() if plan is None else plan
            repo = product['repo']
            if 'realdir' in product:
                repodir = "%s/.kcli/plans/%s/%s" % (os.environ.get('HOME'), repo, product['realdir'])
            else:
                repodir = "%s/.kcli/plans/%s" % (os.environ.get('HOME'), repo)
            if '/' in product['file']:
                inputfile = os.path.basename(product['file'])
                repodir += "/%s" % os.path.dirname(product['file'])
            else:
                inputfile = product['file']
            image = product.get('image')
            parameters = product.get('parameters')
            if image is not None:
                print("Note that this product uses image: %s" % image)
            if parameters is not None:
                for parameter in parameters:
                    applied_parameter = overrides[parameter] if parameter in overrides else parameters[parameter]
                    print("Using parameter %s: %s" % (parameter, applied_parameter))
            extraparameters = list(set(overrides) - set(parameters)) if parameters is not None else overrides
            for parameter in extraparameters:
                print("Using parameter %s: %s" % (parameter, overrides[parameter]))
            if not latest:
                pprint("Using directory %s" % repodir)
                self.plan(plan, path=repodir, inputfile=inputfile, overrides=overrides)
            else:
                self.update_repo(repo)
                self.plan(plan, path=repodir, inputfile=inputfile, overrides=overrides)
            pprint("Product can be deleted with: kcli delete plan --yes %s" % plan)
        return {'result': 'success', 'plan': plan}

    def plan(self, plan, ansible=False, url=None, path=None, autostart=False, container=False, noautostart=False,
             inputfile=None, inputstring=None, start=False, stop=False, delete=False, force=True, overrides={},
             info=False, snapshot=False, snapshotname=None, revert=False, update=False, embedded=False, restart=False,
             download=False, quiet=False, doc=False, onlyassets=False):
        """Manage plan file"""
        k = self.k
        no_overrides = not overrides
        newvms = []
        newassets = []
        failedvms = []
        existingvms = []
        asyncwaitvms = []
        onfly = None
        toclean = False
        getback = False
        vmprofiles = {key: value for key, value in self.profiles.items()
                      if 'type' not in value or value['type'] == 'vm'}
        containerprofiles = {key: value for key, value in self.profiles.items()
                             if 'type' in value and value['type'] == 'container'}
        if plan is None:
            plan = nameutils.get_random_name()
        if delete:
            deletedvms = []
            deletedlbs = []
            dnsclients = []
            networks = []
            if plan == '':
                error("That would delete every vm...Not doing that")
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
                for vm in sorted(c.list(), key=lambda x: x['name']):
                    name = vm['name']
                    description = vm.get('plan')
                    if description == plan:
                        if 'loadbalancer' in vm:
                            lbs = vm['loadbalancer'].split(',')
                            for lb in lbs:
                                if lb not in deletedlbs:
                                    deletedlbs.append(lb)
                        vmnetworks = c.vm_ports(name)
                        for network in vmnetworks:
                            if network != 'default' and network not in networks:
                                networks.append(network)
                        dnsclient, domain = c.dnsinfo(name)
                        c.delete(name, snapshots=True)
                        if dnsclient is not None and domain is not None and dnsclient in self.clients:
                            if dnsclient in dnsclients:
                                z = dnsclients[dnsclient]
                            elif dnsclient in self.clients:
                                z = Kconfig(client=dnsclient).k
                                dnsclients[dnsclient] = z
                            z.delete_dns(dnsclient, domain)
                        common.set_lastvm(name, self.client, delete=True)
                        success("%s deleted on %s!" % (name, hypervisor))
                        deletedvms.append(name)
                        found = True
            if container:
                cont = Kcontainerconfig(self, client=self.containerclient).cont
                for conta in sorted(cont.list_containers(k)):
                    name = conta[0]
                    container_plan = conta[3]
                    if container_plan == plan:
                        cont.delete_container(name)
                        success("Container %s deleted!" % name)
                        found = True
            if not self.keep_networks:
                if self.type == 'kvm':
                    networks = k.list_networks()
                    for network in k.list_networks():
                        if 'plan' in networks[network] and networks[network]['plan'] == plan:
                            networkresult = k.delete_network(network)
                            if networkresult['result'] == 'success':
                                success("network %s deleted!" % network)
                                found = True
                elif networks:
                    found = True
                    for network in networks:
                        networkresult = k.delete_network(network)
                        if networkresult['result'] == 'success':
                            success("Unused network %s deleted!" % network)
            for keyfile in glob.glob("%s.key*" % plan):
                success("file %s from %s deleted!" % (keyfile, plan))
                os.remove(keyfile)
            for ansiblefile in glob.glob("/tmp/%s*inv*" % plan):
                success("file %s from %s deleted!" % (ansiblefile, plan))
                os.remove(ansiblefile)
            if deletedlbs and self.type in ['aws', 'gcp']:
                for lb in deletedlbs:
                    self.k.delete_loadbalancer(lb)
            if found:
                success("Plan %s deleted!" % plan)
            else:
                pprint("Nothing to do for plan %s" % plan)
                return {'result': 'success'}
            return {'result': 'success', 'deletedvm': deletedvms}
        if autostart:
            pprint("Set vms from plan %s to autostart" % plan)
            for vm in sorted(k.list(), key=lambda x: x['name']):
                name = vm['name']
                description = vm['plan']
                if description == plan:
                    k.update_start(name, start=True)
                    success("%s set to autostart!" % name)
            return {'result': 'success'}
        if noautostart:
            pprint("Preventing vms from plan %s to autostart" % plan)
            for vm in sorted(k.list(), key=lambda x: x['name']):
                name = vm['name']
                description = vm['plan']
                if description == plan:
                    k.update_start(name, start=False)
                    success("%s prevented to autostart!" % name)
            return {'result': 'success'}
        if stop or restart:
            stopfound = True
            pprint("Stopping vms from plan %s" % plan)
            if not self.extraclients:
                stopclients = {self.client: k}
            else:
                stopclients = self.extraclients
                stopclients.update({self.client: k})
            for hypervisor in stopclients:
                c = stopclients[hypervisor]
                for vm in sorted(c.list(), key=lambda x: x['name']):
                    name = vm['name']
                    description = vm.get('plan')
                    if description == plan:
                        stopfound = True
                        c.stop(name)
                        success("%s stopped on %s!" % (name, hypervisor))
            if container:
                cont = Kcontainerconfig(self, client=self.containerclient).cont
                for conta in sorted(cont.list_containers()):
                    name = conta[0]
                    containerplan = conta[3]
                    if containerplan == plan:
                        stopfound = True
                        cont.stop_container(name)
                        success("Container %s stopped!" % name)
            if stopfound:
                success("Plan %s stopped!" % plan)
            else:
                warning("No matching objects found")
            if not restart:
                return {'result': 'success'}
        if start or restart:
            startfound = False
            pprint("Starting vms from plan %s" % plan)
            if not self.extraclients:
                startclients = {self.client: k}
            else:
                startclients = self.extraclients
                startclients.update({self.client: k})
            for hypervisor in startclients:
                c = startclients[hypervisor]
                for vm in sorted(c.list(), key=lambda x: x['name']):
                    name = vm['name']
                    description = vm.get('plan')
                    if description == plan:
                        startfound = True
                        c.start(name)
                        success("%s started on %s!" % (name, hypervisor))
            if container:
                cont = Kcontainerconfig(self, client=self.containerclient).cont
                for conta in sorted(cont.list_containers(k)):
                    name = conta[0]
                    containerplan = conta[3]
                    if containerplan == plan:
                        startfound = True
                        cont.start_container(name)
                        success("Container %s started!" % name)
            if startfound:
                success("Plan %s started!" % plan)
            else:
                warning("No matching objects found")
            return {'result': 'success'}
        if snapshot:
            snapshotfound = False
            if revert:
                error("Can't revert and snapshot plan at the same time")
                os._exit(1)
            pprint("Snapshotting vms from plan %s" % plan)
            if snapshotname is None:
                warning("Using %s as snapshot name as None was provider" % plan)
                snapshotname = plan
            for vm in sorted(k.list(), key=lambda x: x['name']):
                name = vm['name']
                description = vm['plan']
                if description == plan:
                    snapshotfound = True
                    k.snapshot(snapshotname, name)
                    success("%s snapshotted!" % name)
            if snapshotfound:
                success("Plan %s snapshotted!" % plan)
            else:
                warning("No matching vms found")
            return {'result': 'success'}
        if revert:
            revertfound = False
            pprint("Reverting snapshots of vms from plan %s" % plan)
            if snapshotname is None:
                warning("Using %s as snapshot name as None was provider" % plan)
                snapshotname = plan
            for vm in sorted(k.list(), key=lambda x: x['name']):
                name = vm['name']
                description = vm['plan']
                if description == plan:
                    revertfound = True
                    k.snapshot(snapshotname, name, revert=True)
                    success("snapshot of %s reverted!" % name)
            if revertfound:
                success("Plan %s reverted with snapshot %s!" % (plan, snapshotname))
            else:
                warning("No matching vms found")
            return {'result': 'success'}
        if url is not None:
            if url.startswith('/'):
                url = "file://%s" % url
            if not url.endswith('.yml'):
                url = "%s/kcli_plan.yml" % url
                pprint("Trying to retrieve %s" % url)
            inputfile = os.path.basename(url)
            onfly = os.path.dirname(url)
            path = plan if path is None else path
            if not quiet:
                pprint("Retrieving specified plan from %s to %s" % (url, path))
            if os.path.exists("/i_am_a_container"):
                path = "/workdir/%s" % path
            if not os.path.exists(path):
                toclean = True if info else False
                os.mkdir(path)
                common.fetch(url, path)
            elif download:
                msg = "target directory %s already there" % (path)
                error(msg)
                return {'result': 'failure', 'reason': msg}
            else:
                pprint("Using existing directory %s" % path)
            if download:
                inputfile = "%s/%s" % (path, inputfile)
                entries, overrides, basefile, basedir = self.process_inputfile(plan, inputfile, overrides=overrides,
                                                                               onfly=onfly, full=True,
                                                                               download_mode=True)
                os.chdir(path)
                for entry in entries:
                    if 'type' in entries[entry] and entries[entry]['type'] != 'vm':
                        continue
                    vmentry = entries[entry]
                    vmfiles = vmentry.get('files', [])
                    scriptfiles = vmentry.get('scripts', [])
                    for fil in vmfiles:
                        if isinstance(fil, str):
                            origin = fil
                        elif isinstance(fil, dict):
                            origin = fil.get('origin')
                        else:
                            return {'result': 'failure', 'reason': "Incorrect file entry"}
                        if '~' not in origin:
                            destdir = "."
                            if '/' in origin:
                                destdir = os.path.dirname(origin)
                                os.makedirs(destdir, exist_ok=True)
                            pprint("Retrieving file %s/%s" % (onfly, origin))
                            try:
                                common.fetch("%s/%s" % (onfly, origin), destdir)
                            except:
                                if common.url_exists("%s/%s/README.md" % (onfly, origin)):
                                    os.makedirs("%s/%s" % (destdir, os.path.basename(onfly)), exist_ok=True)
                                else:
                                    pprint("file %s/%s skipped" % (onfly, origin))
                    for script in scriptfiles:
                        if '~' not in script:
                            destdir = "."
                            if '/' in script:
                                destdir = os.path.dirname(script)
                                os.makedirs(destdir, exist_ok=True)
                            pprint("Retrieving script %s/%s" % (onfly, script))
                            common.fetch("%s/%s" % (onfly, script), destdir)
                os.chdir('..')
                return {'result': 'success'}
        if inputstring is not None:
            inputfile = "temp_plan_%s.yml" % plan
            with open(inputfile, "w") as f:
                f.write(inputstring)
        if inputfile is None:
            inputfile = 'kcli_plan.yml'
            pprint("using default input file kcli_plan.yml")
        if path is not None:
            os.chdir(path)
            getback = True
        inputfile = os.path.expanduser(inputfile)
        if not os.path.exists(inputfile):
            error("Input file %s not found.Leaving...." % inputfile)
            os._exit(1)
        if info:
            self.info_plan(inputfile, onfly=onfly, quiet=quiet, doc=doc)
            if toclean:
                os.chdir('..')
                rmtree(path)
            return {'result': 'success'}
        baseentries = {}
        entries, overrides, basefile, basedir = self.process_inputfile(plan, inputfile, overrides=overrides,
                                                                       onfly=onfly, full=True)
        if basefile is not None:
            baseinfo = self.process_inputfile(plan, basefile, overrides=overrides, full=True)
            baseentries, baseoverrides = baseinfo[0], baseinfo[1]
            if baseoverrides:
                overrides.update({key: baseoverrides[key] for key in baseoverrides if key not in overrides})
        parameters = entries.get('parameters')
        if parameters is not None:
            del entries['parameters']
        dict_types = [entry for entry in entries if isinstance(entries[entry], dict)]
        if not dict_types:
            error("%s doesn't look like a valid plan.Leaving...." % inputfile)
            os._exit(1)
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
        imageentries = [entry for entry in entries if 'type' in
                        entries[entry] and (entries[entry]['type'] == 'image' or entries[entry]['type'] == 'template')]
        poolentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'pool']
        planentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'plan']
        dnsentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'dns']
        kubeentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'kube']
        lbs = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'loadbalancer']
        for p in profileentries:
            vmprofiles[p] = entries[p]
        if planentries:
            pprint("Deploying Plans...")
            for planentry in planentries:
                details = entries[planentry]
                planurl = details.get('url')
                planfile = details.get('file')
                if planurl is None and planfile is None:
                    warning("Missing Url/File for plan %s. Not creating it..." % planentry)
                    continue
                elif planurl is not None:
                    path = planentry
                    if not planurl.endswith('yml'):
                        planurl = "%s/kcli_plan.yml" % planurl
                elif '/' in planfile:
                    path = os.path.dirname(planfile)
                    inputfile = os.path.basename(planfile)
                else:
                    path = '.'
                    inputfile = planentry
                if no_overrides and parameters:
                    pprint("Using parameters from master plan in child ones")
                    for override in overrides:
                        print("Using parameter %s: %s" % (override, overrides[override]))
                self.plan(plan, ansible=False, url=planurl, path=path, autostart=False, container=False,
                          noautostart=False, inputfile=inputfile, start=False, stop=False, delete=False,
                          overrides=overrides, embedded=embedded, download=download)
            return {'result': 'success'}
        if networkentries and not onlyassets:
            pprint("Deploying Networks...")
            for net in networkentries:
                netprofile = entries[net]
                if k.net_exists(net):
                    pprint("Network %s skipped!" % net)
                    continue
                cidr = netprofile.get('cidr')
                nat = bool(netprofile.get('nat', True))
                if cidr is None:
                    warning("Missing Cidr for network %s. Not creating it..." % net)
                    continue
                dhcp = netprofile.get('dhcp', True)
                domain = netprofile.get('domain')
                result = k.create_network(name=net, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, plan=plan,
                                          overrides=netprofile)
                common.handle_response(result, net, element='Network ')
        if poolentries and not onlyassets:
            pprint("Deploying Pools...")
            pools = k.list_pools()
            for pool in poolentries:
                if pool in pools:
                    pprint("Pool %s skipped!" % pool)
                    continue
                else:
                    poolprofile = entries[pool]
                    poolpath = poolprofile.get('path')
                    if poolpath is None:
                        warning("Pool %s skipped as path is missing!" % pool)
                        continue
                    k.create_pool(pool, poolpath)
        if imageentries and not onlyassets:
            pprint("Deploying Images...")
            images = [os.path.basename(t) for t in k.volumes()]
            for image in imageentries:
                clientprofile = "%s_%s" % (self.client, image)
                if image in images or image in self.profiles or clientprofile in self.profiles:
                    pprint("Image %s skipped!" % image)
                    continue
                else:
                    imageprofile = entries[image]
                    pool = imageprofile.get('pool', self.pool)
                    imageurl = imageprofile.get('url')
                    if isinstance(imageurl, str) and imageurl == "None":
                        imageurl = None
                    cmd = imageprofile.get('cmd')
                    self.handle_host(pool=pool, image=image, download=True, cmd=cmd, url=imageurl, update_profile=True)
        if dnsentries and not onlyassets:
            pprint("Deploying Dns Entries...")
            dnsclients = {}
            for dnsentry in dnsentries:
                dnsprofile = entries[dnsentry]
                dnsdomain = dnsprofile.get('domain')
                dnsnet = dnsprofile.get('net')
                dnsdomain = dnsprofile.get('domain', dnsnet)
                dnsip = dnsprofile.get('ip')
                dnsalias = dnsprofile.get('alias', [])
                dnsclient = dnsprofile.get('client')
                if dnsclient is None:
                    z = k
                elif dnsclient in dnsclients:
                    z = dnsclients[dnsclient]
                elif dnsclient in self.clients:
                    z = Kconfig(client=dnsclient).k
                    dnsclients[dnsclient] = z
                else:
                    warning("Client %s not found. Skipping" % dnsclient)
                    return
                if dnsip is None:
                    warning("Missing ip. Skipping!")
                    return
                if dnsnet is None:
                    warning("Missing net. Skipping!")
                    return
                z.reserve_dns(name=dnsentry, nets=[dnsnet], domain=dnsdomain, ip=dnsip, alias=dnsalias, force=True,
                              primary=True)
        if kubeentries and not onlyassets:
            pprint("Deploying Kube Entries...")
            dnsclients = {}
            for cluster in kubeentries:
                pprint("Deploying Cluster %s..." % cluster)
                kubeprofile = entries[cluster]
                kubeclient = kubeprofile.get('client')
                if kubeclient is None:
                    currentconfig = self
                elif kubeclient in self.clients:
                    currentconfig = Kconfig(client=kubeclient)
                else:
                    error("Client %s not found. skipped" % kubeclient)
                    continue
                kubetype = kubeprofile.get('kubetype', 'generic')
                overrides = kubeprofile
                overrides['cluster'] = cluster
                existing_masters = [v for v in currentconfig.k.list() if '%s-master' % cluster in v['name']]
                if existing_masters:
                    pprint("Cluster %s found. skipped!" % cluster)
                    continue
                if kubetype == 'openshift':
                    currentconfig.create_kube_openshift(plan, overrides=overrides)
                elif kubetype == 'k3s':
                    currentconfig.create_kube_k3s(plan, overrides=overrides)
                elif kubetype == 'generic':
                    currentconfig.create_kube_generic(plan, overrides=overrides)
                else:
                    warning("Incorrect kubetype %s specified. skipped!" % kubetype)
                    continue
        if vmentries:
            if not onlyassets:
                pprint("Deploying Vms...")
            vmcounter = 0
            hosts = {}
            vms_to_host = {}
            for name in vmentries:
                currentplandir = basedir
                if len(vmentries) == 1 and 'name' in overrides:
                    newname = overrides['name']
                    profile = entries[name]
                    name = newname
                else:
                    profile = entries[name]
                if 'name' in profile:
                    name = profile['name']
                if 'basevm' in profile or 'baseplan' in profile:
                    baseprofile = {}
                    appendkeys = ['disks', 'nets', 'files', 'scripts', 'cmds']
                    if 'baseplan' in profile:
                        basevm = profile['basevm'] if 'basevm' in profile else name
                        baseinfo = self.process_inputfile(plan, profile['baseplan'], overrides=overrides, full=True)
                        baseprofile = baseinfo[0][basevm]
                        currentplandir = baseinfo[3]
                    elif 'basevm' in profile and profile['basevm'] in baseentries:
                        baseprofile = baseentries[profile['basevm']]
                    else:
                        warning("Incorrect base entry for %s. skipping..." % name)
                        continue
                    for key in baseprofile:
                        if key not in profile:
                            profile[key] = baseprofile[key]
                        elif key in baseprofile and key in profile and key in appendkeys:
                            profile[key] = baseprofile[key] + profile[key]
                for entry in overrides.get('vmrules', self.vmrules):
                    if len(entry) != 1:
                        error("Wrong vm rule %s" % entry)
                        os._exit(1)
                    rule = list(entry.keys())[0]
                    if re.match(rule, name) and isinstance(entry[rule], dict):
                        profile.update(entry[rule])
                        break
                vmclient = profile.get('client')
                if vmclient is None:
                    z = k
                    vmclient = self.client
                    if vmclient not in hosts:
                        hosts[vmclient] = self
                elif vmclient in hosts:
                    z = hosts[vmclient].k
                elif vmclient in self.clients:
                    newclient = Kconfig(client=vmclient)
                    z = newclient.k
                    hosts[vmclient] = newclient
                else:
                    pprint("Client %s not found. Using default one" % vmclient)
                    z = k
                    vmclient = self.client
                    if vmclient not in hosts:
                        hosts[vmclient] = self
                vms_to_host[name] = hosts[vmclient]
                if 'profile' in profile and profile['profile'] in vmprofiles:
                    customprofile = vmprofiles[profile['profile']]
                    profilename = profile['profile']
                else:
                    customprofile = {}
                    profilename = 'kvirt'
                if customprofile:
                    customprofile.update(profile)
                    profile = customprofile
                if 'playbook' in profile and profile['playbook']:
                    if 'scripts' not in profile and 'files' not in profile and 'cmds' not in profile:
                        pprint("Skipping empty playbook for %s" % name)
                    else:
                        if 'image' in profile and 'rhel' in profile['image']\
                                and 'rhnregister' in profile and profile['rhnregister']:
                            warning("Make sure to subscribe %s to Red Hat network" % name)
                        if 'privatekey' in profile and profile['privatekey']:
                            warning("Copy your private key to %s" % name)
                        for net in profile.get('nets', []):
                            if 'ip' in net and 'mask' in net and 'gateway' in net:
                                ip, mask, gateway = net['ip'], net['mask'], net['gateway']
                                warning("Add manually this network %s/%s with gateway %s" % (ip, mask, gateway))
                            if 'vips' in net:
                                vips = ','.join(net['vips'])
                                warning("Add manually vips %s" % vips)
                        pprint("Make sure to export ANSIBLE_JINJA2_EXTENSIONS=jinja2.ext.do")
                        self.create_vm_playbook(name, profile, overrides=overrides, store=True)
                        continue
                if z.exists(name) and not onlyassets:
                    if not update:
                        pprint("%s skipped on %s!" % (name, vmclient))
                    else:
                        updated = False
                        currentvm = z.info(name)
                        currentstart = currentvm['autostart']
                        currentmemory = currentvm['memory']
                        currentimage = currentvm.get('template')
                        currentimage = currentvm.get('image', currentimage)
                        currentcpus = int(currentvm['cpus'])
                        currentnets = currentvm['nets']
                        currentdisks = currentvm['disks']
                        currentflavor = currentvm.get('flavor')
                        if 'image' in currentvm:
                            if 'image' in profile and currentimage != profile['image']:
                                pprint("Existing %s has a different image. skipped!" % name)
                                continue
                        elif 'image' in profile:
                            pprint("Existing %s has a different image. skipped!" % name)
                            continue
                        if 'autostart' in profile and currentstart != profile['autostart']:
                            updated = True
                            pprint("Updating autostart of %s to %s" % (name, profile['autostart']))
                            z.update_start(name, profile['autostart'])
                        if 'flavor' in profile and currentflavor != profile['flavor']:
                            updated = True
                            pprint("Updating flavor of %s to %s" % (name, profile['flavor']))
                            z.update_flavor(name, profile['flavor'])
                        else:
                            if 'memory' in profile and currentmemory != profile['memory']:
                                updated = True
                                pprint("Updating memory of %s to %s" % (name, profile['memory']))
                                z.update_memory(name, profile['memory'])
                            if 'numcpus' in profile and currentcpus != profile['numcpus']:
                                updated = True
                                pprint("Updating cpus of %s to %s" % (name, profile['numcpus']))
                                z.update_cpus(name, profile['numcpus'])
                        if 'disks' in profile:
                            if len(currentdisks) < len(profile['disks']):
                                updated = True
                                pprint("Adding Disks to %s" % name)
                                for disk in profile['disks'][len(currentdisks):]:
                                    if isinstance(disk, int):
                                        size = disk
                                        pool = self.pool
                                    elif isinstance(disk, str) and disk.isdigit():
                                        size = int(disk)
                                        pool = self.pool
                                    elif isinstance(disk, dict):
                                        size = disk.get('size', self.disksize)
                                        pool = disk.get('pool', self.pool)
                                    else:
                                        continue
                                    z.add_disk(name=name, size=size, pool=pool)
                            if len(currentdisks) > len(profile['disks']):
                                updated = True
                                pprint("Removing Disks of %s" % name)
                                for disk in currentdisks[len(currentdisks) - len(profile['disks']):]:
                                    diskname = os.path.basename(disk['path'])
                                    diskpool = os.path.dirname(disk['path'])
                                    z.delete_disk(name=name, diskname=diskname, pool=diskpool)
                        if 'nets' in profile:
                            if len(currentnets) < len(profile['nets']):
                                updated = True
                                pprint("Adding Nics to %s" % name)
                                for net in profile['nets'][len(currentnets):]:
                                    if isinstance(net, str):
                                        network = net
                                    elif isinstance(net, dict):
                                        network = net.get('name', self.network)
                                    else:
                                        continue
                                    z.add_nic(name, network)
                            if len(currentnets) > len(profile['nets']):
                                updated = True
                                pprint("Removing Nics of %s" % name)
                                for net in range(len(currentnets) - len(profile['nets']), len(currentnets)):
                                    interface = "eth%s" % net
                                    z.delete_nic(name, interface)
                        if not updated:
                            pprint("%s skipped on %s!" % (name, vmclient))
                    existingvms.append(name)
                    continue
                # cmds = default_cmds + customprofile.get('cmds', []) + profile.get('cmds', [])
                # ips = profile.get('ips')
                sharedkey = profile.get('sharedkey', self.sharedkey)
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
                currentoverrides = overrides.copy()
                if 'image' in profile:
                    for entry in self.list_profiles():
                        currentimage = profile['image']
                        entryprofile = entry[0]
                        clientprofile = "%s_%s" % (self.client, currentimage)
                        if entryprofile == currentimage or entryprofile == clientprofile:
                            profile['image'] = entry[4]
                            currentoverrides['image'] = profile['image']
                            break
                    imageprofile = profile['image']
                    if imageprofile in IMAGES and self.type != 'packet' and\
                            IMAGES[imageprofile] not in [os.path.basename(v) for v in self.k.volumes()]:
                        pprint("Image %s not found. Downloading" % imageprofile)
                        self.handle_host(pool=self.pool, image=imageprofile, download=True, update_profile=True)
                        profile['image'] = os.path.basename(IMAGES[imageprofile])
                        currentoverrides['image'] = profile['image']
                result = self.create_vm(name, profilename, overrides=currentoverrides, customprofile=profile, k=z,
                                        plan=plan, basedir=currentplandir, client=vmclient, onfly=onfly,
                                        onlyassets=onlyassets)
                if not onlyassets:
                    common.handle_response(result, name, client=vmclient)
                if result['result'] == 'success':
                    newvms.append(name)
                    start = profile.get('start', True)
                    cloudinit = profile.get('cloudinit', True)
                    wait = profile.get('wait', False)
                    asyncwait = profile.get('asyncwait', False)
                    finishfiles = profile.get('finishfiles', [])
                    if onlyassets:
                        newassets.append(result['data'])
                    elif not wait and not asyncwait:
                        continue
                    elif not start or not cloudinit or profile.get('image') is None:
                        pprint("Skipping wait on %s" % name)
                    elif asyncwait:
                        asyncwaitvm = {'name': name, 'finishfiles': finishfiles}
                        asyncwaitvms.append(asyncwaitvm)
                    else:
                        self.wait(name)
                        if finishfiles:
                            self.handle_finishfiles(name, finishfiles)
                else:
                    failedvms.append(name)
        if diskentries and not onlyassets:
            pprint("Deploying Disks...")
        for disk in diskentries:
            profile = entries[disk]
            pool = profile.get('pool')
            vms = profile.get('vms')
            template = profile.get('template')
            image = profile.get('image', template)
            size = int(profile.get('size', 10))
            if pool is None:
                error("Missing Key Pool for disk section %s. Not creating it..." % disk)
                continue
            if vms is None:
                error("Missing or Incorrect Key Vms for disk section %s. Not creating it..." % disk)
                continue
            shareable = True if len(vms) > 1 else False
            if k.disk_exists(pool, disk):
                pprint("Creation for Disk %s skipped!" % disk)
                poolpath = k.get_pool_path(pool)
                newdisk = "%s/%s" % (poolpath, disk)
                for vm in vms:
                    pprint("Adding disk %s to %s" % (disk, vm))
                    k.add_disk(name=vm, size=size, pool=pool, image=image, shareable=shareable, existing=newdisk,
                               thin=False)
            else:
                newdisk = k.create_disk(disk, size=size, pool=pool, image=image, thin=False)
                if newdisk is None:
                    error("Disk %s not deployed. It won't be added to any vm" % disk)
                else:
                    common.pprint("Disk %s deployed!" % disk)
                    for vm in vms:
                        pprint("Adding disk %s to %s" % (disk, vm))
                        k.add_disk(name=vm, size=size, pool=pool, image=image, shareable=shareable,
                                   existing=newdisk, thin=False)
        if containerentries and not onlyassets:
            cont = Kcontainerconfig(self, client=self.containerclient).cont
            pprint("Deploying Containers...")
            label = "plan=%s" % plan
            for container in containerentries:
                if cont.exists_container(container):
                    pprint("Container %s skipped!" % container)
                    continue
                profile = entries[container]
                if 'profile' in profile and profile['profile'] in containerprofiles:
                    customprofile = containerprofiles[profile['profile']]
                else:
                    customprofile = {}
                containerimage = next((e for e in [profile.get('image'), profile.get('image'),
                                                   customprofile.get('image'),
                                                   customprofile.get('image')] if e is not None), None)
                nets = next((e for e in [profile.get('nets'), customprofile.get('nets')] if e is not None), None)
                ports = next((e for e in [profile.get('ports'), customprofile.get('ports')] if e is not None), None)
                volumes = next((e for e in [profile.get('volumes'), profile.get('disks'),
                                            customprofile.get('volumes'), customprofile.get('disks')]
                                if e is not None), None)
                environment = next((e for e in [profile.get('environment'), customprofile.get('environment')]
                                    if e is not None), None)
                cmds = next((e for e in [profile.get('cmds'), customprofile.get('cmds')] if e is not None), [])
                success("Container %s deployed!" % container)
                cont.create_container(name=container, image=containerimage, nets=nets, cmds=cmds, ports=ports,
                                      volumes=volumes, environment=environment, label=label)
        if ansibleentries and not onlyassets:
            if not newvms:
                warning("Ansible skipped as no new vm within playbook provisioned")
                return
            for entry in sorted(ansibleentries):
                _ansible = entries[entry]
                if 'playbook' not in _ansible:
                    error("Missing Playbook for ansible.Ignoring...")
                    os._exit(1)
                playbook = _ansible['playbook']
                verbose = _ansible['verbose'] if 'verbose' in _ansible else False
                groups = _ansible.get('groups', {})
                user = _ansible.get('user')
                variables = _ansible.get('variables', {})
                vms = []
                if 'vms' in _ansible:
                    vms = _ansible['vms']
                    for vm in vms:
                        if vm not in newvms:
                            vms.remove(vm)
                else:
                    vms = newvms
                if not vms:
                    warning("Ansible skipped as no new vm within playbook provisioned")
                    return
                ansiblecommand = "ansible-playbook"
                if verbose:
                    ansiblecommand += " -vvv"
                inventoryfile = "/tmp/%s.inv.yaml" % plan if self.yamlinventory else "/tmp/%s.inv" % plan
                ansibleutils.make_plan_inventory(vms_to_host, plan, newvms, groups=groups, user=user,
                                                 yamlinventory=self.yamlinventory, insecure=self.insecure)
                if not os.path.exists('~/.ansible.cfg'):
                    ansibleconfig = os.path.expanduser('~/.ansible.cfg')
                    with open(ansibleconfig, "w") as f:
                        f.write("[ssh_connection]\nretries=10\n")
                if variables:
                    varsfile = "/tmp/%s.vars.yml" % plan
                    with open(varsfile, 'w') as f:
                        yaml.dump(variables, f, default_flow_style=False)
                    ansiblecommand += " --extra-vars @%s" % (varsfile)
                ansiblecommand += " -i  %s %s" % (inventoryfile, playbook)
                pprint("Running: %s" % ansiblecommand)
                os.system(ansiblecommand)
        if ansible and not onlyassets:
            pprint("Deploying Ansible Inventory...")
            inventoryfile = "/tmp/%s.inv.yaml" % plan if self.yamlinventory else "/tmp/%s.inv" % plan
            if os.path.exists(inventoryfile):
                pprint("Inventory in %s skipped!" % inventoryfile)
            else:
                pprint("Creating ansible inventory for plan %s in %s" % (plan, inventoryfile))
                vms = []
                for vm in sorted(k.list(), key=lambda x: x['name']):
                    name = vm['name']
                    description = vm['plan']
                    if description == plan:
                        vms.append(name)
                ansibleutils.make_plan_inventory(vms_to_host, plan, vms, yamlinventory=self.yamlinventory,
                                                 insecure=self.insecure)
                return
        if lbs and not onlyassets:
            pprint("Deploying Loadbalancers...")
            for index, lbentry in enumerate(lbs):
                details = entries[lbentry]
                ports = details.get('ports', [])
                if not ports:
                    error("Missing Ports for loadbalancer. Not creating it...")
                    return
                checkpath = details.get('checkpath', '/')
                checkport = details.get('checkport', 80)
                alias = details.get('alias', [])
                domain = details.get('domain')
                lbvms = details.get('vms', [])
                lbnets = details.get('nets', ['default'])
                internal = details.get('internal')
                self.handle_loadbalancer(lbentry, nets=lbnets, ports=ports, checkpath=checkpath, vms=lbvms,
                                         domain=domain, plan=plan, checkport=checkport, alias=alias,
                                         internal=internal)
        returndata = {'result': 'success', 'plan': plan}
        returndata['newvms'] = newvms if newvms else []
        returndata['existingvms'] = existingvms if existingvms else []
        returndata['failedvms'] = failedvms if failedvms else []
        returndata['assets'] = newassets if newassets else []
        if failedvms:
            returndata['result'] = 'failure'
            returndata['reason'] = 'The following vm failed: %s' % ','.join(failedvms)
        if getback or toclean:
            os.chdir('..')
        if toclean:
            rmtree(path)
        if inputstring is not None and os.path.exists("temp_plan_%s.yml" % plan):
            os.remove("temp_plan_%s.yml" % plan)
        for entry in asyncwaitvms:
            name, finishfiles = entry['name'], entry['finishfiles']
            self.wait(name)
            if finishfiles:
                self.handle_finishfiles(self, name, finishfiles)
        return returndata

    def handle_host(self, pool=None, image=None, switch=None, download=False,
                    url=None, cmd=None, sync=False, update_profile=False, commit=None):
        """

        :param pool:
        :param images:
        :param switch:
        :param download:
        :param url:
        :param cmd:
        :param sync:
        :param profile:
        :return:
        """
        if download:
            imagename = image
            k = self.k
            if pool is None:
                pool = self.pool
                pprint("Using pool %s" % pool)
            if image is not None:
                if url is None:
                    if image not in IMAGES:
                        error("Image %s has no associated url" % image)
                        return {'result': 'failure', 'reason': "Incorrect image"}
                    url = IMAGES[image]
                    if 'rhcos' in image:
                        if commit is not None:
                            url = common.get_commit_rhcos(commit, _type=self.type)
                        else:
                            url = common.get_latest_rhcos(url, _type=self.type)
                    if 'fcos' in image:
                        url = common.get_latest_fcos(url, _type=self.type)
                    image = os.path.basename(image)
                    if image.startswith('rhel'):
                        if 'web' in sys.argv[0]:
                            return {'result': 'failure', 'reason': "Missing url"}
                        pprint("Opening url %s for you to grab complete url for %s kvm guest image" % (url, image))
                        webbrowser.open(url, new=2, autoraise=True)
                        url = input("Copy Url:\n")
                        if url.strip() == '':
                            error("Missing proper url.Leaving...")
                            return {'result': 'failure', 'reason': "Missing image"}
                if cmd is None and image != '' and image in IMAGESCOMMANDS:
                    cmd = IMAGESCOMMANDS[image]
                pprint("Using url %s..." % url)
                pprint("Grabbing image %s..." % image)
                shortname = os.path.basename(url).split('?')[0]
                try:
                    result = k.add_image(url, pool, cmd=cmd, name=image)
                except Exception as e:
                    error("Got %s" % e)
                    error("Please run kcli delete image --yes %s" % shortname)
                    return {'result': 'failure', 'reason': "User interruption"}
                common.handle_response(result, image, element='Image', action='Added')
                if update_profile and result['result'] == 'success':
                    if shortname.endswith('.bz2') or shortname.endswith('.gz') or shortname.endswith('.xz'):
                        shortname = os.path.splitext(shortname)[0]
                    if self.type == 'vsphere':
                        shortname = image
                    clientprofile = "%s_%s" % (self.client, imagename)
                    profileinfo = {'iso': shortname} if shortname.endswith('.iso') else {'image': shortname}
                    if clientprofile not in self.profiles:
                        pprint("Adding a profile named %s with default values" % clientprofile)
                        self.create_profile(clientprofile, profileinfo, quiet=True)
                    else:
                        pprint("Updating profile %s" % clientprofile)
                        self.update_profile(clientprofile, profileinfo, quiet=True)
            return {'result': 'success'}
        elif switch:
            if switch not in self.clients:
                error("Client %s not found in config.Leaving...." % switch)
                return {'result': 'failure', 'reason': "Client %s not found in config" % switch}
            enabled = self.ini[switch].get('enabled', True)
            if not enabled:
                error("Client %s is disabled.Leaving...." % switch)
                return {'result': 'failure', 'reason': "Client %s is disabled" % switch}
            pprint("Switching to client %s..." % switch)
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
                warning("Nothing to do. Leaving...")
                return {'result': 'success'}
            for cli in self.extraclients:
                dest = self.extraclients[cli]
                pprint("syncing client images from %s to %s" % (self.client, cli))
                warning("Note rhel images are currently not synced")
            for vol in k.volumes():
                image = os.path.basename(vol)
                if image in [os.path.basename(v) for v in dest.volumes()]:
                    warning("Ignoring %s as it's already there" % image)
                    continue
                url = None
                for n in list(IMAGES.values()):
                    if n is None:
                        continue
                    elif n.split('/')[-1] == image:
                        url = n
                if url is None:
                    return {'result': 'failure', 'reason': "image not in default list"}
                if image.startswith('rhel'):
                    if 'web' in sys.argv[0]:
                        return {'result': 'failure', 'reason': "Missing url"}
                    pprint("Opening url %s for you to grab complete url for %s kvm guest image" % (url, vol))
                    webbrowser.open(url, new=2, autoraise=True)
                    url = input("Copy Url:\n")
                    if url.strip() == '':
                        error("Missing proper url.Leaving...")
                        return {'result': 'failure', 'reason': "Missing image"}
                cmd = None
                if vol in IMAGESCOMMANDS:
                    cmd = IMAGESCOMMANDS[image]
                pprint("Grabbing image %s..." % image)
                dest.add_image(url, pool, cmd=cmd)
        return {'result': 'success'}

    def handle_loadbalancer(self, name, nets=['default'], ports=[], checkpath='/', vms=[], delete=False, domain=None,
                            plan=None, checkport=80, alias=[], internal=False):
        name = nameutils.get_random_name().replace('_', '-') if name is None else name
        k = self.k
        if self.type in ['aws', 'gcp']:
            if delete:
                pprint("Deleting loadbalancer %s" % name)
                k.delete_loadbalancer(name)
                return
            else:
                pprint("Deploying loadbalancer %s" % name)
                k.create_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain,
                                      checkport=checkport, alias=alias, internal=internal)
        elif delete:
            if self.type == 'kvm':
                k.delete(name)
            return
        else:
            pprint("Deploying loadbalancer %s" % name)
            vminfo = []
            for vm in vms:
                counter = 0
                while counter != 100:
                    ip = k.ip(vm)
                    if ip is None:
                        sleep(5)
                        print("Waiting 5 seconds to grab ip for vm %s..." % vm)
                        counter += 5
                    else:
                        break
                vminfo.append({'name': vm, 'ip': ip})
            overrides = {'name': name, 'vms': vminfo, 'nets': nets, 'ports': ports, 'checkpath': checkpath}
            self.plan(plan, inputstring=haproxyplan, overrides=overrides)

    def list_loadbalancers(self):
        k = self.k
        if self.type not in ['aws', 'gcp']:
            results = []
            for vm in k.list():
                if vm['profile'].startswith('loadbalancer') and len(vm['profile'].split('-')) == 2:
                    ports = vm['profile'].split('-')[1]
                    results.append([vm['name'], vm['ip'], 'tcp', ports, ''])
            return results
        else:
            return k.list_loadbalancers()

    def wait(self, name, image=None, quiet=False):
        k = self.k
        if image is None:
            image = k.info(name)['image']
        pprint("Waiting for vm %s to finish customisation" % name)
        if 'cos' in image:
            cmd = 'journalctl --identifier=ignition --all --no-pager'
        else:
            cloudinitfile = common.get_cloudinitfile(image)
            cmd = "sudo tail -n 50 %s" % cloudinitfile
        user, ip, vmport = None, None, None
        hostip = None
        while ip is None:
            info = k.info(name)
            if self.type == 'packet' and info.get('status') != 'active':
                warning("Waiting for node to be active")
                ip = None
            else:
                user, ip = info.get('user'), info.get('ip')
                if self.type == 'kubevirt':
                    if k.access_mode == 'NodePort':
                        vmport = info.get('nodeport')
                        if hostip is None:
                            hostip = k.node_host(name=info.get('host'))
                        ip = hostip
                    elif k.access_mode == 'LoadBalancer':
                        ip = info.get('loadbalancerip')
                if user is not None and ip is not None:
                    if self.type == 'openstack' and info.get('privateip') == ip and self.k.external_network is not None\
                            and info.get('nets')[0]['net'] != self.k.external_network:
                        warning("Waiting for floating ip instead of a private ip...")
                        ip = None
                    else:
                        testcmd = common.ssh(name, user=user, ip=ip, tunnel=self.tunnel, tunnelhost=self.tunnelhost,
                                             tunnelport=self.tunnelport, tunneluser=self.tunneluser,
                                             insecure=self.insecure, cmd='id -un', vmport=vmport)
                        if os.popen(testcmd).read().strip() != user:
                            warning("Gathered ip not functional yet...")
                            ip = None
            pprint("Waiting for vm to be accessible...")
            sleep(5)
        sleep(5)
        oldoutput = ''
        while True:
            sshcmd = common.ssh(name, user=user, ip=ip, tunnel=self.tunnel, tunnelhost=self.tunnelhost, vmport=vmport,
                                tunnelport=self.tunnelport, tunneluser=self.tunneluser, insecure=self.insecure, cmd=cmd)
            output = os.popen(sshcmd).read()
            if 'kcli boot finished' in output:
                break
            output = output.replace(oldoutput, '')
            if not quiet:
                print(output)
            oldoutput = output
            sleep(2)
        return True

    def create_kube_generic(self, cluster, overrides={}):
        if os.path.exists('/i_am_a_container'):
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        kubeadm.create(self, plandir, cluster, overrides)

    def create_kube_k3s(self, cluster, overrides={}):
        if os.path.exists('/i_am_a_container'):
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(k3s.create.__code__.co_filename)
        k3s.create(self, plandir, cluster, overrides)

    def create_kube_openshift(self, cluster, overrides={}):
        if os.path.exists('/i_am_a_container'):
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        openshift.create(self, plandir, cluster, overrides)

    def delete_kube(self, cluster, overrides={}):
        k = self.k
        cluster = overrides.get('cluster', cluster)
        if cluster is None:
            cluster = 'testk'
        clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
        if os.path.exists(clusterdir):
            pprint("Deleting directory %s" % clusterdir)
            rmtree(clusterdir)
        for vm in sorted(k.list(), key=lambda x: x['name']):
            name = vm['name']
            currentcluster = vm.get('kube')
            if currentcluster is not None and currentcluster == cluster:
                k.delete(name, snapshots=True)
                common.set_lastvm(name, self.client, delete=True)
                success("%s deleted on %s!" % (name, self.client))
        if self.type == 'kubevirt' and self.k.access_mode == 'LoadBalancer':
            try:
                k.delete_service("%s-api-svc" % cluster, k.namespace)
            except:
                pass

    def scale_kube_generic(self, cluster, overrides={}):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        kubeadm.scale(self, plandir, cluster, overrides)

    def scale_kube_k3s(self, cluster, overrides={}):
        plandir = os.path.dirname(k3s.create.__code__.co_filename)
        k3s.scale(self, plandir, cluster, overrides)

    def scale_kube_openshift(self, cluster, overrides={}):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        openshift.scale(self, plandir, cluster, overrides)

    def expose_plan(self, plan, inputfile=None, overrides={}, port=9000, extraconfigs={}, installermode=False):
        inputfile = os.path.expanduser(inputfile)
        if not os.path.exists(inputfile):
            error("No input file found nor default kcli_plan.yml.Leaving....")
            os._exit(1)
        pprint("Handling expose of plan with name %s and inputfile %s" % (plan, inputfile))
        kexposer = Kexposer(self, plan, inputfile, overrides=overrides, port=port, extraconfigs=extraconfigs,
                            installermode=installermode)
        kexposer.run()

    def create_openshift_iso(self, cluster, overrides={}):
        liveiso_version = overrides.get('version', 'latest')
        if liveiso_version not in ['latest', 'pre-release']:
            error("Incorrect live iso version. Choose between latest and pre-release")
            os._exit(1)
        liveiso = "https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/"
        liveiso += "%s/latest/rhcos-live.x86_64.iso" % liveiso_version
        api_ip = overrides.get('api_ip')
        domain = overrides.get('domain')
        role = overrides.get('role', 'worker')
        iso = overrides.get('iso', True)
        if '.' in cluster:
            domain = '.'.join(cluster.split('.')[1:])
            pprint("Using domain %s" % domain)
            cluster = cluster.replace(".%s" % domain, '')
        hosts_content = None
        if api_ip is None:
            try:
                api_ip = socket.gethostbyname('api.%s.%s' % (cluster, domain))
            except:
                pass
        if api_ip is None:
            warning("Couldn't figure out api_ip. Relying on dns")
            api_ip = "api.%s.%s" % (cluster, domain)
        else:
            hosts_content = "127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n"
            hosts_content += "::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n"
            hosts_content += "%s api-int.%s.%s api.%s.%s" % (api_ip, cluster, domain, cluster, domain)
        ignitionfile = "%s.ign" % role
        config = Kconfig()
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        if os.path.exists(ignitionfile):
            warning("Using existing %s" % ignitionfile)
        with open("iso.ign", 'w') as f:
            pprint("Writing file iso.ign for %s in %s.%s" % (role, cluster, domain))
            isodir = os.path.dirname(common.__file__)
            env = Environment(loader=FileSystemLoader(isodir), extensions=['jinja2.ext.do'], trim_blocks=True,
                              lstrip_blocks=True)
            templ = env.get_template(os.path.basename("ignition.j2"))
            if hosts_content is not None:
                hosts_content = base64.b64encode(hosts_content.encode()).decode("UTF-8")
            finaldata = templ.render(api_ip=api_ip, role=role, hosts_content=hosts_content)
            _files = [{"path": "/root/config.ign", "content": finaldata}]
            if os.path.exists('iso.sh'):
                pprint("Using local iso.sh script")
                isoscript = 'iso.sh'
            else:
                isoscript = '%s/iso.sh' % plandir
            iso_overrides = {'scripts': [isoscript], 'files': _files}
            iso_overrides.update(overrides)
            result = config.create_vm('autoinstaller', 'rhcos46', overrides=iso_overrides, onlyassets=True)
            if 'reason' in result:
                error(result['reason'])
            else:
                f.write(result['data'])
        if iso:
            if config.type != 'kvm':
                warning("Iso only get generated for kvm type")
            else:
                generate_rhcos_iso(self.k, cluster, overrides.get('pool', 'default'))

    def handle_finishfiles(self, name, finishfiles):
        current_ip = common._ssh_credentials(self.k, name)[1]
        for finishfile in finishfiles:
            if isinstance(finishfile, str):
                destination = '.'
                source = finishfile if '/' in finishfile else '/root/%s' % finishfile
            elif isinstance(finishfile, dict) and 'origin' in finishfile and 'path' in finishfile:
                source, destination = finishfile.get('origin'), finishfile.get('path', '.')
            else:
                warning("Incorrect finishfile entry %s. Skipping" % finishfile)
                continue
            scpcmd = common.scp(name, ip=current_ip, user='root', source=source, destination=destination,
                                tunnel=self.tunnel, tunnelhost=self.tunnelhost, tunnelport=self.tunnelport,
                                tunneluser=self.tunneluser, download=True, insecure=True)
            os.system(scpcmd)
