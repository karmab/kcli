# -*- coding: utf-8 -*-

import base64
from datetime import datetime
from fnmatch import fnmatch
from ipaddress import ip_network
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined as undefined
from jinja2.exceptions import TemplateSyntaxError, TemplateError, TemplateNotFound
from kvirt.defaults import IMAGES, IMAGESCOMMANDS, OPENSHIFT_TAG
from kvirt.jinjafilters import jinjafilters
from kvirt import nameutils
from kvirt import common
from kvirt.common import error, pprint, success, warning, generate_rhcos_iso, pwd_path, container_mode, get_user
from kvirt.common import ssh, scp, _ssh_credentials, valid_ip, process_files, get_rhcos_url_from_file, get_free_port
from kvirt.cluster import microshift
from kvirt.cluster import k3s
from kvirt.cluster import kubeadm
from kvirt.cluster import hypershift
from kvirt.cluster import openshift
from kvirt.cluster import rke2
from kvirt.expose import Kexposer
from kvirt.internalplans import haproxy as haproxyplan
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt import defaults as kdefaults
from kvirt.miniconsole import Kminiconsole
from getpass import getuser
import glob
import os
import re
import socket
from shutil import rmtree, which
import sys
from subprocess import call, run, PIPE, STDOUT
from tempfile import TemporaryDirectory
import threading
from time import sleep
import webbrowser
import yaml

cloudplatforms = ['aws', 'azure', 'gcp', 'packet', 'ibmcloud', 'hcloud']


def dependency_error(provider, exception=None):
    msg = f"Couldnt import {provider}. Use kcli install provider {provider}"
    if exception is not None:
        msg += f"\nHit {exception}"
    error(msg)
    sys.exit(1)


class Kconfig(Kbaseconfig):
    def __init__(self, client=None, debug=False, quiet=False, region=None, zone=None, namespace=None, offline=False):
        Kbaseconfig.__init__(self, client=client, debug=debug, quiet=quiet, offline=offline)
        options = self.options
        if not self.enabled:
            k = None
        else:
            if self.type == 'kubevirt':
                kubeconfig_file = options.get('kubeconfig')
                if kubeconfig_file is None:
                    error("Missing kubeconfig in the configuration. Leaving")
                    sys.exit(1)
                elif not os.path.exists(os.path.expanduser(kubeconfig_file)):
                    error("Kubeconfig file path doesn't exist. Leaving")
                    sys.exit(1)
                namespace = namespace or options.get('namespace')
                context = options.get('context')
                readwritemany = options.get('readwritemany', kdefaults.KUBEVIRT['readwritemany'])
                disk_hotplug = options.get('disk_hotplug', kdefaults.KUBEVIRT['disk_hotplug'])
                access_mode = options.get('access_mode', kdefaults.KUBEVIRT['access_mode'])
                if access_mode not in ['External', 'LoadBalancer', 'NodePort']:
                    msg = f"Incorrect access_mode {access_mode}. Should be External, NodePort or LoadBalancer"
                    error(msg)
                    sys.exit(1)
                volume_mode = options.get('volume_mode', kdefaults.KUBEVIRT['volume_mode'])
                if volume_mode not in ['Filesystem', 'Block']:
                    msg = f"Incorrect volume_mode {volume_mode}. Should be Filesystem or Block"
                    error(msg)
                    sys.exit(1)
                volume_access = options.get('volume_access', kdefaults.KUBEVIRT['volume_access'])
                if volume_access not in ['ReadWriteMany', 'ReadWriteOnce']:
                    msg = f"Incorrect volume_access {volume_access}. Should be ReadWriteOnce or ReadWriteOnce"
                    error(msg)
                    sys.exit(1)
                harvester = options.get('harvester', kdefaults.KUBEVIRT['harvester'])
                embed_userdata = options.get('embed_userdata', kdefaults.KUBEVIRT['embed_userdata'])
                registry = options.get('registry', kdefaults.KUBEVIRT['registry'])
                try:
                    from kvirt.providers.kubevirt import Kubevirt
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('kubevirt', exception)
                k = Kubevirt(kubeconfig_file, context=context, debug=debug, namespace=namespace,
                             disk_hotplug=disk_hotplug, readwritemany=readwritemany, access_mode=access_mode,
                             volume_mode=volume_mode, volume_access=volume_access, harvester=harvester,
                             embed_userdata=embed_userdata, registry=registry)
            elif self.type == 'gcp':
                credentials = options.get('credentials')
                if credentials is not None:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser(credentials)
                elif 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
                    error("set GOOGLE_APPLICATION_CREDENTIALS variable.Leaving...")
                    sys.exit(1)
                project = options.get('project')
                if project is None:
                    error("Missing project in the configuration. Leaving")
                    sys.exit(1)
                if region is None:
                    region = options.get('region', kdefaults.GCP['region'])
                if zone is None:
                    zone = options.get('zone')
                try:
                    from kvirt.providers.gcp import Kgcp
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('gcp', exception)
                k = Kgcp(project, region=region, zone=zone, debug=debug)
                self.overrides.update({'project': project})
            elif self.type == 'hcloud':
                apikey = options.get('apikey')
                if apikey is None:
                    error("Missing apikey in the hcloud configuration. Leaving")
                    sys.exit(1)
                location = options.get('location')
                if location is None:
                    error("Missing location in the hcloud configuration. Leaving")
                    sys.exit(1)
                try:
                    from kvirt.providers.hcloud import Khcloud
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('hcloud', exception)
                k = Khcloud(api_key=apikey, location=location)
            elif self.type == 'azure':
                try:
                    from kvirt.providers.azure import Kazure
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('azure', exception)
                admin_user = options.get('admin_user', kdefaults.AZURE['admin_user'])
                admin_password = options.get('admin_password')
                location = options.get('location', kdefaults.AZURE['location'])
                resource_group = options.get('resource_group', kdefaults.AZURE['resource_group'])
                mail = options.get('mail')
                storage_account = options.get('storage_account')
                subscription_id = options.get('subscription_id')
                if subscription_id is None:
                    error("Missing subscription_id in the configuration. Leaving")
                    sys.exit(1)
                tenant_id = options.get('tenant_id')
                if tenant_id is None:
                    error("Missing tenant_id in the configuration. Leaving")
                    sys.exit(1)
                app_id = options.get('app_id')
                if app_id is None:
                    error("Missing app_id in the configuration. Leaving")
                    sys.exit(1)
                secret = options.get('secret')
                if secret is None:
                    error("Missing secret in the configuration. Leaving")
                    sys.exit(1)
                k = Kazure(subscription_id=subscription_id, tenant_id=tenant_id, app_id=app_id, location=location,
                           secret=secret, resource_group=resource_group, admin_user=admin_user,
                           admin_password=admin_password, mail=mail, storage_account=storage_account, debug=debug)
            elif self.type == 'aws':
                if region is None:
                    region = options.get('region', kdefaults.AWS['region'])
                if zone is None:
                    zone = options.get('zone')
                access_key_id = options.get('access_key_id')
                if access_key_id is None:
                    error("Missing access_key_id in the configuration. Leaving")
                    sys.exit(1)
                access_key_secret = options.get('access_key_secret')
                if access_key_secret is None:
                    error("Missing access_key_secret in the configuration. Leaving")
                    sys.exit(1)
                keypair = options.get('keypair')
                session_token = options.get('session_token')
                try:
                    from kvirt.providers.aws import Kaws
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('aws', exception)
                k = Kaws(access_key_id=access_key_id, access_key_secret=access_key_secret, region=region,
                         debug=debug, keypair=keypair, session_token=session_token, zone=zone)
            elif self.type == 'ibm':
                iam_api_key = options.get('iam_api_key')
                cos_api_key = options.get('cos_api_key')
                cos_resource_instance_id = options.get('cos_resource_instance_id')
                cis_resource_instance_id = options.get('cis_resource_instance_id')
                region = options.get('region')
                if region is None:
                    region = options.get('region', kdefaults.IBM['region'])
                if zone is None:
                    zone = options.get('zone')
                vpc = options.get('vpc')
                if iam_api_key is None:
                    error("Missing iam_api_key in the configuration. Leaving")
                    sys.exit(1)
                from kvirt.providers.ibm import Kibm
                k = Kibm(iam_api_key=iam_api_key, region=region, zone=zone, vpc=vpc, debug=debug,
                         cos_api_key=cos_api_key, cos_resource_instance_id=cos_resource_instance_id,
                         cis_resource_instance_id=cis_resource_instance_id)
            elif self.type == 'ovirt':
                datacenter = options.get('datacenter', kdefaults.OVIRT['datacenter'])
                cluster = options.get('cluster', kdefaults.OVIRT['cluster'])
                user = options.get('user', kdefaults.OVIRT['user'])
                password = options.get('password')
                if password is None:
                    error("Missing password in the configuration. Leaving")
                    sys.exit(1)
                org = options.get('org')
                if org is None:
                    error("Missing org in the configuration. Leaving")
                    sys.exit(1)
                ca_file = options.get('ca_file')
                if ca_file is None:
                    error("Missing ca_file in the configuration. Leaving")
                    sys.exit(1)
                ca_file = os.path.expanduser(ca_file)
                if not os.path.exists(ca_file):
                    error("Ca file path doesn't exist. Leaving")
                    sys.exit(1)
                filtervms = options.get('filtervms', kdefaults.OVIRT['filtervms'])
                filteruser = options.get('filteruser', kdefaults.OVIRT['filteruser'])
                filtertag = options.get('filtertag')
                try:
                    from kvirt.providers.ovirt import KOvirt
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('ovirt', exception)
                k = KOvirt(host=self.host, port=self.port, user=user, password=password,
                           debug=debug, datacenter=datacenter, cluster=cluster, ca_file=ca_file, org=org,
                           filtervms=filtervms, filteruser=filteruser, filtertag=filtertag)
            elif self.type == 'openstack':
                envrc = options.get('envrc')
                if envrc is not None:
                    envrc = os.path.expanduser(envrc)
                    if not os.path.exists(envrc):
                        error(f"Envrc {envrc} not found. Leaving")
                        sys.exit(1)
                    else:
                        for line in open(envrc).readlines():
                            if line.startswith('export '):
                                new_key, new_variable = line.split('=')
                                new_key = new_key.replace('export ', '')
                                new_variable = new_variable.strip().replace('"', '').replace("'", '')
                                os.environ[new_key] = new_variable
                version = options.get('version') or kdefaults.OPENSTACK['version']
                domain = options.get('domain') or os.environ.get("OS_USER_DOMAIN_NAME") or kdefaults.OPENSTACK['domain']
                auth_url = options.get('auth_url') or os.environ.get("OS_AUTH_URL")
                if auth_url is None:
                    error("Missing auth_url in the configuration. Leaving")
                    sys.exit(1)
                user = options.get('user') or os.environ.get("OS_USERNAME") or kdefaults.OPENSTACK['user']
                project = options.get('project') or os.environ.get("OS_PROJECT_NAME") or kdefaults.OPENSTACK['project']
                password = options.get('password') or os.environ.get("OS_PASSWORD")
                ca_file = options.get('ca_file') or os.environ.get("OS_CACERT")
                region_name = options.get('region_name') or os.environ.get("OS_REGION_NAME")
                external_network = options.get('external_network')
                if auth_url.endswith('v2.0'):
                    domain = None
                if ca_file is not None and not os.path.exists(os.path.expanduser(ca_file)):
                    error(f"Indicated ca_file {ca_file} not found. Leaving")
                    sys.exit(1)
                glance_disk = options.get('glance_disk', False)
                auth_token = options.get('token') or os.environ.get("OS_TOKEN") or 'password'
                default_auth_type = 'token' if auth_token is not None else 'password'
                auth_type = options.get('auth_type') or os.environ.get("OS_AUTH_TYPE") or default_auth_type
                if auth_type == 'password' and password is None:
                    error("Missing password in the configuration. Leaving")
                    sys.exit(1)
                if auth_type == 'token':
                    user, password, domain = None, None, None
                if auth_type == 'v3applicationcredential':
                    options_credential_id = options.get('application_credential_id')
                    env_application_credential_id = os.environ.get("OS_APPLICATION_CREDENTIAL_ID")
                    application_credential_id = options_credential_id or env_application_credential_id
                    options_credential_secret = options.get('application_credential_secret')
                    env_application_credential_secret = os.environ.get("OS_APPLICATION_CREDENTIAL_SECRET")
                    application_credential_secret = options_credential_secret or env_application_credential_secret
                try:
                    from kvirt.providers.openstack import Kopenstack
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('openstack', exception)
                k = Kopenstack(host=self.host, port=self.port, user=user, password=password, version=version,
                               debug=debug, project=project, domain=domain, auth_url=auth_url, ca_file=ca_file,
                               external_network=external_network, region_name=region_name, glance_disk=glance_disk,
                               auth_type=auth_type, auth_token=auth_token,
                               application_credential_id=application_credential_id,
                               application_credential_secret=application_credential_secret)
            elif self.type == 'vsphere':
                user = options.get('user')
                if user is None:
                    error("Missing user in the configuration. Leaving")
                    sys.exit(1)
                password = options.get('password')
                if password is None:
                    error("Missing password in the configuration. Leaving")
                    sys.exit(1)
                cluster = options.get('cluster')
                if cluster is None:
                    error("Missing cluster in the configuration. Leaving")
                datacenter = options.get('datacenter')
                if datacenter is None:
                    error("Missing datacenter in the configuration. Leaving")
                isofolder = options.get('isofolder')
                if isofolder is not None:
                    if '/' not in isofolder:
                        isopool = self.pool
                    elif '[' not in isofolder:
                        isofolder = isofolder.split('/')
                        isopool = isofolder[0]
                        isofolder = isofolder[1:]
                    isofolder = f'[{isopool}]/{isofolder}'
                filtervms = options.get('filtervms', kdefaults.VSPHERE['filtervms'])
                filtervms = options.get('filteruser', kdefaults.VSPHERE['filteruser'])
                filteruser = options.get('filteruser', kdefaults.VSPHERE['filteruser'])
                filtertag = options.get('filtertag')
                category = options.get('category', kdefaults.VSPHERE['category'])
                basefolder = options.get('basefolder')
                dvs = options.get('dvs', kdefaults.VSPHERE['dvs'])
                import_network = options.get('import_network', kdefaults.VSPHERE['import_network'])
                timeout = options.get('timeout', kdefaults.VSPHERE['timeout'])
                force_pool = options.get('force_pool', kdefaults.VSPHERE['force_pool'])
                restricted = options.get('restricted', kdefaults.VSPHERE['restricted'])
                serial = options.get('serial', kdefaults.VSPHERE['serial'])
                try:
                    from kvirt.providers.vsphere import Ksphere
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('vsphere', exception)
                k = Ksphere(self.host, user, password, datacenter, cluster, isofolder=isofolder, debug=debug,
                            filtervms=filtervms, filteruser=filteruser, filtertag=filtertag, category=category,
                            basefolder=basefolder, dvs=dvs, import_network=import_network, timeout=timeout,
                            force_pool=force_pool, restricted=restricted, serial=serial)
            elif self.type == 'packet':
                auth_token = options.get('auth_token')
                if auth_token is None:
                    error("Missing auth_token in the configuration. Leaving")
                    sys.exit(1)
                project = options.get('project')
                if project is None:
                    error("Missing project in the configuration. Leaving")
                    sys.exit(1)
                facility = options.get('facility')
                try:
                    from kvirt.providers.packet import Kpacket
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('packet', exception)
                k = Kpacket(auth_token, project, facility=facility, debug=debug,
                            tunnelhost=self.tunnelhost, tunneluser=self.tunneluser, tunnelport=self.tunnelport,
                            tunneldir=self.tunneldir)
            elif self.type == 'proxmox':
                user = options.get('user')
                if user is None:
                    error("Missing user in the configuration. Leaving")
                    sys.exit(1)
                auth_token_name = options.get('auth_token_name')
                password = options.get('password')
                if not auth_token_name and not password:
                    error("Missing auth_token_name or password in the configuration. Leaving")
                    sys.exit(1)
                auth_token_secret = options.get('auth_token_secret')
                if auth_token_name and auth_token_secret is None:
                    error("Missing auth_token_secret in the configuration. Leaving")
                    sys.exit(1)
                filtertag = options.get('filtertag')
                imagepool = options.get('imagepool')
                node = options.get('node')
                verify_ssl = options.get('verify_ssl')
                try:
                    from kvirt.providers.proxmox import Kproxmox
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('proxmox', exception)
                k = Kproxmox(
                    host=self.host,
                    port=None,
                    user=user,
                    password=password,
                    token_name=auth_token_name,
                    token_secret=auth_token_secret,
                    filtertag=filtertag,
                    node=node,
                    verify_ssl=verify_ssl,
                    imagepool=imagepool,
                    debug=False)
            elif self.type == 'web':
                port = options.get('port', 8000)
                localkube = options.get('localkube', True)
                from kvirt.providers.web import Kwebclient
                k = Kwebclient(self.host, port, localkube=localkube, debug=debug)
                self.type = 'web'
            elif offline:
                from kvirt.providers.fake import Kfake
                k = Kfake()
                self.type = 'fake'
            else:
                if self.host is None:
                    error("Problem parsing your configuration file")
                    sys.exit(1)
                session = options.get('session', False)
                legacy = options.get('legacy', False)
                try:
                    from kvirt.providers.kvm import Kvirt
                except Exception as e:
                    exception = e if debug else None
                    dependency_error('libvirt', exception)
                k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url,
                          debug=debug, insecure=self.insecure, session=session, legacy=legacy)
            if k.conn is None:
                error(f"Couldn't connect to client {self.client}. Leaving...")
                sys.exit(1)
            for extraclient in self._extraclients:
                if extraclient not in self.ini:
                    warning(f"Missing section for client {extraclient} in config file. Trying to connect...")
                    self.ini[extraclient] = {'host': extraclient}
                c = Kconfig(client=extraclient)
                e = c.k
                self.extraclients[extraclient] = e
                if e.conn is None:
                    error(f"Couldn't connect to specify hypervisor {extraclient}. Leaving...")
                    sys.exit(1)
            if hasattr(self, 'algorithm'):
                if self.algorithm == 'free':
                    upstatus = ['active', 'up', 'running']
                    allclis = {self.client: k}
                    allclis.update(self.extraclients)
                    mincli, minvms = None, None
                    for cli in allclis:
                        clivms = len([vm for vm in allclis[cli].list() if vm['status'].lower() in upstatus])
                        if minvms is None or clivms < minvms:
                            mincli = cli
                            minvms = clivms
                    if mincli != self.client:
                        self.extraclients[self.client] = k
                        k = self.extraclients[mincli]
                        del self.extraclients[mincli]
                        self.client = mincli
                if self.algorithm == 'balance':
                    members = [self.client] + list(self.extraclients.keys())
                    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
                    if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
                        for line in open(lastvm).readlines():
                            line = line.split(' ')
                            if len(line) != 2:
                                continue
                            cli = line[0].strip()
                            if cli in members and members.index(cli) < len(members):
                                cliindex = members.index(cli)
                                newcli = members[(cliindex + 1) % len(members)]
                                if newcli != self.client:
                                    self.extraclients[self.client] = k
                                    k = self.extraclients[newcli]
                                    del self.extraclients[newcli]
                                    self.client = newcli
                                break

                pprint(f"Selecting client {self.client} from group {self.group}")
        self.k = k
        default_data = {'config_%s' % k: self.default[k] for k in self.default}
        config_data = {'config_%s' % k: self.ini[self.client][k] for k in self.ini[self.client]}
        config_data['config_type'] = config_data.get('config_type', 'kvm')
        config_data['config_host'] = config_data.get('config_host', '127.0.0.1')
        default_user = getuser() if config_data['config_type'] == 'kvm'\
            and self.host in ['localhost', '127.0.0.1'] else 'root'
        config_data['config_user'] = config_data.get('config_user', default_user)
        config_data['config_client'] = self.client
        self.overrides.update(default_data)
        self.overrides.update(config_data)

    def create_vm(self, name, profile=None, overrides={}, customprofile={}, k=None,
                  plan='kvirt', basedir='.', client=None, onfly=None, onlyassets=False):
        overrides.update(self.overrides)
        wrong_overrides = [y for y in overrides if '-' in y]
        if wrong_overrides:
            for wrong_override in wrong_overrides:
                error(f"Incorrect parameter {wrong_overrides}. Hyphens are not allowed")
            return {'result': 'failure', 'reason': 'Incorrect parameters found'}
        overrides['name'] = name
        kube = overrides.get('kube')
        kubetype = overrides.get('kubetype')
        k = self.k if k is None else k
        tunnel = self.tunnel
        esx = self.type == 'vsphere' and self.k.esx
        profile = profile or overrides.get('image') or 'kvirt'
        full_volumes = self.k.volumes()
        volumes = [os.path.basename(v) for v in full_volumes]
        vmprofiles = {k: v for k, v in self.profiles.items() if 'type' not in v or v['type'] == 'vm'}
        if customprofile:
            vmprofiles[profile] = customprofile
        elif profile in vmprofiles:
            pprint(f"Deploying vm {name} from profile {profile}...")
        elif self.type in cloudplatforms:
            vmprofiles[profile] = {'image': profile}
        elif (os.path.basename(profile) == profile and profile in volumes) or profile in full_volumes:
            if not onlyassets:
                pprint(f"Deploying vm {name} from image {profile}...")
            new_profile = os.path.basename(profile)
            vmprofiles[new_profile] = {'image': profile}
            profile = new_profile
        elif profile in IMAGES or profile == 'rhcos4000' or esx:
            vmprofiles[profile] = {'image': profile}
        elif profile.startswith('http'):
            new_profile = os.path.basename(profile)
            vmprofiles[new_profile] = {'image': profile}
            profile = new_profile
        elif profile.startswith('rhcos-4') and profile.endswith('qcow2') and self.type not in cloudplatforms:
            vmprofiles[profile] = {'image': profile}
        elif profile == 'kvirt':
            vmprofiles[profile] = {}
        elif self.type == 'kubevirt' and '/' in profile:
            vmprofiles[profile] = {'image': profile}
        else:
            return {'result': 'failure', 'reason': f'Image {profile} not found'}
        profilename = profile
        profile = vmprofiles[profile]
        pimage = profile.get('image', 'XXX')
        pimage_missing = pimage in IMAGES and pimage not in volumes
        esx_image = esx and ('image_url' in overrides or os.path.exists(pimage))
        download_needed = pimage is not None and pimage.startswith('http')
        if not onlyassets and self.type not in cloudplatforms and (pimage_missing or esx_image or download_needed):
            pprint(f"Image {pimage} not found. Downloading")
            pimage_data = {'pool': overrides.get('pool') or self.pool, 'image': pimage}
            pimage_size = profile.get('kubevirt_disk_size') or profile.get('size')
            if pimage_size is not None:
                pimage_data['size'] = pimage_size
            if profilename.startswith('rhcos-4') and profilename.endswith('qcow2'):
                pimage_data['image'] = profilename.split('.')[0].replace('rhcos-4', 'rhcos4')
                pimage_data['url'] = get_rhcos_url_from_file(profilename, _type=self.type)
            if esx:
                pimage_data['name'] = name
                pimage_data['url'] = pimage if download_needed or os.path.exists(pimage) else overrides.get('image_url')
            if download_needed:
                pimage_data['name'] = profilename
                pimage_data['url'] = pimage
                vmprofiles[profilename]['image'] = profilename
            self.download_image(**pimage_data)
        if not customprofile:
            profile.update(overrides)
        father = vmprofiles[profile['base']] if 'base' in profile else {}
        default_numcpus = father.get('numcpus', self.numcpus)
        default_memory = father.get('memory', self.memory)
        default_pool = father.get('pool', self.pool)
        default_disks = father.get('disks', self.disks)
        default_nets = father.get('nets', self.nets)
        default_image = father.get('image', self.image)
        default_cloudinit = father.get('cloudinit', self.cloudinit)
        default_guestagent = father.get('guestagent', self.guestagent)
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
        default_rhnactivationkey = father.get('rhnactivationkey', self.rhnactivationkey)
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
        default_cmdline = father.get('cmdline', self.cmdline)
        default_placement = father.get('placement', self.placement)
        default_cpuhotplug = father.get('cpuhotplug', self.cpuhotplug)
        default_memoryhotplug = father.get('memoryhotplug', self.memoryhotplug)
        default_numa = father.get('numa', self.numa)
        default_numamode = father.get('numamode', self.numamode)
        default_pcidevices = father.get('pcidevices', self.pcidevices)
        default_tpm = father.get('tpm', self.tpm)
        default_rng = father.get('rng', self.rng)
        default_virttype = father.get('virttype', self.virttype)
        default_securitygroups = father.get('securitygroups', self.securitygroups)
        default_rootpassword = father.get('rootpassword', self.rootpassword)
        default_tempkey = father.get('tempkey', self.tempkey)
        default_vmuser = father.get('vmuser', self.vmuser)
        default_wait = father.get('wait', self.wait)
        default_waitcommand = father.get('waitcommand', self.waitcommand)
        default_waittimeout = father.get('waittimeout', self.waittimeout)
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
        securitygroups = profile.get('securitygroups', default_securitygroups)
        numcpus = profile.get('numcpus', default_numcpus)
        memory = profile.get('memory', default_memory)
        if isinstance(memory, str) and (memory.lower().endswith('gb') or memory.lower().endswith('g')):
            try:
                memory = int(memory.lower('gb', '').replace('g', '')) * 1024
            except Exception as e:
                error(f"Couldnt convert memory. Hit {e}")
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
                which('mkisofs') is None and which('genisoimage') and which('xorrisofs') is None:
            return {'result': 'failure', 'reason': "Missing mkisofs/genisoimage/xorrisofs needed for cloudinit"}
        guestagent = profile.get('guestagent', default_guestagent)
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
        domain = profile.get('domain', overrides.get('domain', default_domain))
        dnsclient = profile.get('dnsclient', overrides.get('dnsclient', default_dnsclient))
        scripts = common.remove_duplicates(default_scripts + profile.get('scripts', []))
        files = profile.get('files', default_files)
        extra_files = profile.get('extra_files') or overrides.get('extra_files') or []
        files.extend(extra_files)
        result = self.parse_files(name, files, basedir, onfly)
        if result is not None:
            return result
        profile_env_parameters = [key for key in profile if key.isupper()]
        overrides_env_parameters = [key for key in overrides if key.isupper()]
        env_parameters = sorted(list(set(profile_env_parameters + overrides_env_parameters)))
        if env_parameters:
            env_data = ''
            for key in env_parameters:
                value = profile.get(key) or overrides.get(key)
                env_data += f"export {key}={value}\nexport {key.lower()}={value}\n"
            files.append({'path': '/etc/profile.d/kcli.sh', 'content': env_data, 'mode': 644})
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
        rhnactivationkey = profile.get('rhnactivationkey', default_rhnactivationkey)
        rhnorg = profile.get('rhnorg', default_rhnorg)
        rhnpool = profile.get('rhnpool', default_rhnpool)
        flavor = profile.get('flavor', default_flavor)
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
        cmdline = profile.get('cmdline', default_cmdline)
        placement = profile.get('placement', default_placement)
        cpuhotplug = profile.get('cpuhotplug', default_cpuhotplug)
        memoryhotplug = profile.get('memoryhotplug', default_memoryhotplug)
        rootpassword = profile.get('rootpassword', default_rootpassword)
        vmuser = profile.get('vmuser', default_vmuser)
        tempkey = profile.get('tempkey', default_tempkey)
        wait = profile.get('wait', default_wait)
        waitcommand = profile.get('waitcommand', default_waitcommand)
        if waitcommand is not None:
            wait = True
        waittimeout = profile.get('waittimeout', default_waittimeout)
        virttype = profile.get('virttype', default_virttype)
        overrides.update(profile)
        scriptcmds = []
        if image is not None and 'rhel' in image.lower():
            if rhnregister:
                if rhnuser is not None and rhnpassword is not None:
                    overrides['rhnuser'] = rhnuser
                    overrides['rhnpassword'] = rhnpassword
                elif rhnactivationkey is not None and rhnorg is not None:
                    overrides['rhnactivationkey'] = rhnactivationkey
                    overrides['rhnorg'] = rhnorg
                else:
                    msg = "Rhn registration required but missing credentials. "
                    msg += "Define rhnuser/rhnpassword or rhnactivationkey/rhnorg"
                    warning(msg)
                    rhnregister = False
            else:
                warning(f"{name} will require manual subscription to Red Hat Network")
        if image is not None and cloudinit and iso is not None:
            warning(f"Ignoring iso {iso} as image {image} is set")
            iso = None
        if scripts:
            scripts_overrides = overrides.copy()
            for script in scripts:
                if onfly is not None and '~' not in script:
                    destdir = basedir
                    if '/' in script:
                        destdir = os.path.dirname(script)
                        os.makedirs(destdir, exist_ok=True)
                    common.fetch(f"{onfly}/{script}", destdir)
                script = os.path.expanduser(script)
                if os.path.exists(script):
                    if not os.path.isabs(script):
                        script = os.path.abspath(script)
                elif basedir != '.':
                    script = f'{basedir}/{script}'
                if not os.path.exists(script):
                    error(f"Script file {script} not found")
                    sys.exit(1)
                else:
                    scriptbasedir = os.path.dirname(script) if os.path.dirname(script) != '' else '.'
                    env = Environment(loader=FileSystemLoader(scriptbasedir), undefined=undefined,
                                      extensions=['jinja2.ext.do'], trim_blocks=True, lstrip_blocks=True)
                    for jinjafilter in jinjafilters.jinjafilters:
                        env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
                    try:
                        templ = env.get_template(os.path.basename(script))
                        scriptentries = templ.render(scripts_overrides)
                    except TemplateNotFound:
                        error(f"Script file {os.path.basename(script)} not found")
                        sys.exit(1)
                    except TemplateSyntaxError as e:
                        msg = f"Error rendering line {e.lineno} of script file {e.filename}. Got: {e.message}"
                        return {'result': 'failure', 'reason': msg}
                    except TemplateError as e:
                        msg = f"Error rendering script file {script}. Got: {e.message}"
                        return {'result': 'failure', 'reason': msg}
                    scriptlines = [line.strip() for line in scriptentries.split('\n') if line.strip() != '']
                    if scriptlines:
                        scriptlines.insert(0, f"echo Running script {os.path.basename(script)}")
                        scriptcmds.extend(scriptlines)
        if cloudinit and image is not None and 'rhel' in image.lower():
            rhncommands = []
            if rhnserver != "https://subscription.rhsm.redhat.com" and not valid_ip(rhnserver):
                fqdn = os.path.basename(rhnserver)
                rhncommands.append(f'rpm -Uvh http://{fqdn}/pub/katello-ca-consumer-latest.noarch.rpm')
            if rhnactivationkey is not None and rhnorg is not None:
                rhncommands.append('subscription-manager register --serverurl=%s --force --activationkey=%s --org=%s'
                                   % (rhnserver, rhnactivationkey, rhnorg))
                if image.startswith('rhel-8') or image == 'rhel8':
                    rhncommands.append('subscription-manager repos --enable=rhel-8-for-x86_64-baseos-rpms')
                elif image.startswith('rhel-server-7') or image == 'rhel7':
                    rhncommands.append('subscription-manager repos --enable=rhel-7-server-rpms')
            elif rhnuser is not None and rhnpassword is not None:
                rhncommands.append('subscription-manager register --serverurl=%s --force --username=%s --password=%s'
                                   % (rhnserver, rhnuser, rhnpassword))
                if rhnpool is not None:
                    rhncommands.append(f'subscription-manager attach --pool={rhnpool}')
                else:
                    rhncommands.append('subscription-manager attach --auto')
        else:
            rhncommands = []
        sharedfoldercmds = []
        if sharedfolders and self.type == 'kvm':
            for sharedfolder in sharedfolders:
                basefolder = os.path.basename(sharedfolder)
                cmd1 = f"mkdir -p /mnt/{sharedfolder}"
                cmd2 = f"echo {basefolder} /mnt/{sharedfolder} 9p trans=virtio,version=9p2000.L,rw 0 0 >> /etc/fstab"
                sharedfoldercmds.append(cmd1)
                sharedfoldercmds.append(cmd2)
        if sharedfoldercmds:
            sharedfoldercmds.append("mount -a")
        networkwaitcommand = [f'sleep {networkwait}'] if networkwait > 0 else []
        rootcommand = [f'echo root:{rootpassword} | chpasswd'] if rootpassword is not None else []
        cmds = rootcommand + networkwaitcommand + rhncommands + sharedfoldercmds + cmds + scriptcmds
        if notify and image is not None:
            if notifycmd is None and notifyscript is None:
                if 'cos' in image:
                    notifycmd = 'journalctl --identifier=ignition --all --no-pager'
                else:
                    cloudinitfile = common.get_cloudinitfile(image)
                    notifycmd = "tail -100 %s" % cloudinitfile
            if notifyscript is not None:
                notifyscript = os.path.expanduser(notifyscript)
                if basedir != '.':
                    notifyscript = f'{basedir}/{notifyscript}'
                if not os.path.exists(notifyscript):
                    notifycmd = None
                    notifyscript = None
                    warning(f"Notification required for {name} but missing notifyscript")
                else:
                    files.append({'path': '/root/.notify.sh', 'origin': notifyscript})
                    notifycmd = "bash /root/.notify.sh"
            notifycmds, mailcontent = self.handle_notifications(name, notifymethods=notifymethods,
                                                                pushbullettoken=pushbullettoken,
                                                                notifyscript=notifyscript, notifycmd=notifycmd,
                                                                slackchannel=slackchannel, slacktoken=slacktoken,
                                                                mailserver=mailserver, mailfrom=mailfrom, mailto=mailto)
            if mailcontent is not None:
                files.append({'path': '/var/tmp/mail.txt', 'content': mailcontent})
            if notifycmds:
                if not cmds:
                    cmds = notifycmds
                else:
                    cmds.extend(notifycmds)
        ips = [overrides[key] for key in overrides if re.match('ip[0-9]+', key)]
        netmasks = [overrides[key] for key in overrides if re.match('netmask[0-9]+', key)]
        if privatekey:
            privatekeyfile = None
            publickeyfile = common.get_ssh_pub_key()
            if publickeyfile is not None:
                privatekeyfile = publickeyfile.replace('.pub', '')
            if privatekeyfile is not None and publickeyfile is not None:
                privatekey = open(privatekeyfile).read().strip()
                publickey = open(publickeyfile).read().strip()
                warning(f"Injecting private key in {name}")
                files.append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                files.append({'path': '/root/.ssh/id_rsa.pub', 'content': publickey})
                files.append({'path': f'/home/{get_user(image)}/.ssh/id_rsa', 'content': privatekey})
                if self.host in ['127.0.0.1', 'localhost']:
                    authorized_keys_file = os.path.expanduser('~/.ssh/authorized_keys')
                    found = False
                    if os.path.exists(authorized_keys_file):
                        for line in open(authorized_keys_file).readlines():
                            if publickey in line:
                                found = True
                                break
                        if not found:
                            warning(f"Adding public key to {authorized_keys_file} for {name}")
                            with open(authorized_keys_file, 'a') as f:
                                f.write(f"\n{publickey}")
                    else:
                        warning(f"Creating {authorized_keys_file}")
                        with open(authorized_keys_file, 'w') as f:
                            f.write(publickey)
                            os.chmod(authorized_keys_file, 0o600)
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
            if 'rhcos' in image and memory < 1024:
                pprint("Adjusting memory to 1024Mb")
                memory = 1024
        metadata = {'plan': plan, 'profile': profilename}
        if domain is not None and reservedns:
            metadata['domain'] = domain
            if dnsclient is not None:
                metadata['dnsclient'] = dnsclient
                reservedns = False
        if image is not None:
            metadata['image'] = image
        elif [n for n in nets if isinstance(n, dict) and 'nic' in n]:
            warning("Your nets definition contains nic key which won't be used")
        if 'owner' in profile or 'owner' in overrides:
            metadata['owner'] = profile.get('owner') or overrides.get('owner')
        if 'redfish_iso' in profile or 'redfish_iso' in overrides:
            metadata['redfish_iso'] = profile.get('redfish_iso') or overrides.get('redfish_iso')
        if 'vmuser' in profile or 'vmuser' in overrides:
            metadata['user'] = profile.get('vmuser') or overrides.get('vmuser')
        elif 'user' in profile or 'user' in overrides:
            metadata['user'] = profile.get('user') or overrides.get('user')
        if kube is not None and kubetype is not None:
            metadata['kubetype'] = kubetype
            metadata['kube'] = kube
            cluster_networks = overrides.get('cluster_networks', [])
            cluster_network = cluster_networks[0] if cluster_networks else overrides.get('cluster_network_ipv4')
            if cluster_network is not None:
                metadata['cluster_network'] = cluster_network
        if tempkey:
            if overrides.get('tempkeydir') is None:
                tempkeydir = TemporaryDirectory()
                overrides['tempkeydir'] = tempkeydir
        # confpool handling for network
        for index, net in enumerate(nets):
            confpool = None
            if isinstance(net, dict):
                confpool = net.get('ippool') or net.get('confpool')
            if index == 0 and confpool is None:
                confpool = overrides.get('ippool') or overrides.get('confpool')
                if isinstance(net, str):
                    nets[index] = {'name': net}
            if confpool is None:
                continue
            if confpool not in self.confpools:
                warning(f"{confpool} is not a valid confpool")
                continue
            currentconfpool = self.confpools[confpool]
            netmask = net.get('netmask') or net.get('prefix') or currentconfpool.get('netmask')\
                or currentconfpool.get('prefix')
            gateway = net.get('gateway') or currentconfpool.get('gateway')
            if netmask is None:
                warning(f"Ignoring confpool {confpool} as netmask isnt specified")
                continue
            elif gateway is None:
                warning(f"Ignoring confpool {confpool} as gateway isnt specified")
                continue
            ip_reservations = currentconfpool.get('ip_reservations', {})
            reserved_ips = list(ip_reservations.values())
            if 'ips' in currentconfpool:
                ips = currentconfpool['ips']
                if '/' in ips:
                    ips = [str(i) for i in ip_network(ips)[1:.1]]
                free_ips = [ip for ip in ips if ip not in reserved_ips]
                if free_ips:
                    free_ip = free_ips[0]
                    ip_reservations[name] = free_ip
                    pprint(f"Using ip {free_ip} from confpool {confpool} in net {index}")
                    new_conf = currentconfpool.copy()
                    new_conf['ip'] = free_ip
                    nets[index].update(currentconfpool)
                    if not onlyassets:
                        self.update_confpool(confpool, {'ip_reservations': ip_reservations})
                else:
                    warning(f"No available ip in confpool {confpool}")
                    continue
        if onlyassets:
            image = image or profilename
            result = {'result': 'success'}
            if common.needs_ignition(image):
                version = common.ignition_version(image)
                compact = True if overrides.get('compact') else False
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, files=files, enableroot=enableroot, overrides=overrides,
                                           version=version, plan=plan, image=image, compact=compact,
                                           vmuser=vmuser)
            else:
                userdata, metadata, netdata = common.cloudinit(name, keys=keys, cmds=cmds, nets=nets, gateway=gateway,
                                                               dns=dns, domain=domain, files=files,
                                                               enableroot=enableroot, overrides=overrides,
                                                               image=image, storemetadata=storemetadata, vmuser=vmuser)
                if netdata is not None:
                    result['netdata'] = netdata
            result['userdata'] = userdata
            return result
        result = k.create(name=name, virttype=virttype, plan=plan, profile=profilename, flavor=flavor,
                          cpumodel=cpumodel, cpuflags=cpuflags, cpupinning=cpupinning, numamode=numamode, numa=numa,
                          numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool,
                          image=image, disks=disks, disksize=disksize, diskthin=diskthin,
                          diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit),
                          reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost),
                          start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns,
                          domain=domain, nested=bool(nested), tunnel=tunnel, files=files, enableroot=enableroot,
                          overrides=overrides, tags=tags, storemetadata=storemetadata,
                          sharedfolders=sharedfolders, cmdline=cmdline, placement=placement, autostart=autostart,
                          cpuhotplug=cpuhotplug, memoryhotplug=memoryhotplug, pcidevices=pcidevices, tpm=tpm, rng=rng,
                          metadata=metadata, securitygroups=securitygroups, vmuser=vmuser, guestagent=guestagent)
        if result['result'] != 'success':
            return result
        if reservedns and dnsclient is not None and domain is not None:
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
                warning(f"Client {dnsclient} not found. Skipping")
        homedir = os.path.expanduser('~')
        if os.access(homedir, os.W_OK):
            if not os.path.exists(f'{homedir}/.kcli'):
                os.mkdir(f'{homedir}/.kcli')
            if os.access(f'{homedir}/.kcli', os.W_OK):
                common.set_lastvm(name, client or self.client)
        ansibleprofile = profile.get('ansible')
        if ansibleprofile is not None:
            if which('ansible-playbook') is None:
                warning("ansible-playbook executable not found. Skipping ansible play")
            else:
                for element in ansibleprofile:
                    playbook = element.get('playbook')
                    if playbook is None:
                        continue
                    if not os.path.exists(playbook):
                        warning(f"{playbook} not found. Skipping ansible play")
                        continue
                    ansiblecommand = "ansible-playbook"
                    verbose = element.get('verbose', False)
                    if verbose:
                        ansiblecommand += " -vvv"
                    variables = element.get('variables', {})
                    if variables:
                        varsfile = f"@{name}_vars.yaml"
                        with open(varsfile, 'w') as f:
                            yaml.safe_dump(variables, f)
                        ansiblecommand += f' -e "@{varsfile}"'
                    ansiblecommand += f" -T 20 -i {which('klist.py')} -l {name} {playbook}"
                    pprint(f"Running: {ansiblecommand}")
                    os.system(ansiblecommand)
        unplugcd = overrides.get('unplugcd', False)
        if wait or unplugcd:
            if not cloudinit or not start or image is None:
                pprint(f"Skipping wait on {name}")
            else:
                identityfile = f'{plan}.key' if os.path.exists(f'{plan}.key') else None
                tempkey_clean = False
                if overrides.get('tempkeydir') is not None:
                    identityfile = f"{overrides['tempkeydir'].name}/id_rsa"
                    tempkey_clean = True
                self.wait_finish(name, image=image, waitcommand=waitcommand, waittimeout=waittimeout,
                                 identityfile=identityfile, vmclient=client)
                finishfiles = profile.get('finishfiles', [])
                if finishfiles:
                    self.handle_finishfiles(name, finishfiles, identityfile=identityfile, vmclient=client)
                if tempkey_clean:
                    self.clean_tempkey(name, identityfile=identityfile)
            if unplugcd:
                self.k.update_iso(name, None)
        if overrides.get('tempkeydir') is not None and not overrides.get('tempkeydirkeep', False):
            overrides.get('tempkeydir').cleanup()
        return {'result': 'success', 'vm': name}

    def update_vm(self, name, overrides):
        k = self.k
        ip = overrides.get('ip')
        flavor = overrides.get('flavor')
        numcpus = overrides.get('numcpus')
        memory = overrides.get('memory')
        autostart = overrides.get('autostart')
        dns = overrides.get('dns')
        host = overrides.get('host')
        domain = overrides.get('domain')
        cloudinit = overrides.get('cloudinit')
        image = overrides.get('image')
        nets = overrides.get('nets')
        disks = overrides.get('disks')
        information = overrides.get('information')
        cpuflags = overrides.get('cpuflags', [])
        disable = overrides.get('disable', False)
        overrides.pop('disable', None)
        extra_metadata = {k: overrides[k] for k in overrides if k not in self.list_keywords()}
        template = overrides.get('template')
        if template is not None:
            del extra_metadata['template']
        if dns:
            pprint(f"Creating Dns entry for {name}...")
            networks = k.vm_ports(name)
            if networks and domain is None:
                domain = networks[0]
            if not nets:
                return
            else:
                k.reserve_dns(name=name, nets=networks, domain=domain, ip=ip)
        if ip is not None:
            pprint(f"Updating ip of vm {name} to {ip}...")
            k.update_metadata(name, 'ip', ip)
        if cloudinit:
            pprint(f"Removing cloudinit information of vm {name}")
            k.remove_cloudinit(name)
        if image is not None:
            pprint(f"Updating image of vm {name} to {image}...")
            k.update_metadata(name, 'image', image)
        if memory is not None:
            pprint(f"Updating memory of vm {name} to {memory}...")
            k.update_memory(name, memory)
        if numcpus is not None:
            pprint(f"Updating numcpus of vm {name} to {numcpus}...")
            k.update_cpus(name, numcpus)
        if autostart is not None:
            pprint(f"Setting autostart to {autostart} for vm {name}...")
            k.update_start(name, start=autostart)
        if information:
            pprint(f"Setting information for vm {name}...")
            k.update_information(name, information)
        if 'iso' in overrides:
            iso = overrides['iso']
            pprint(f"Switching iso for vm {name} to {iso}...")
            if iso == 'None' or iso == '':
                iso = None
            k.update_iso(name, iso)
        if flavor is not None:
            pprint(f"Updating flavor of vm {name} to {flavor}...")
            k.update_flavor(name, flavor)
        if host:
            pprint(f"Creating Host entry for vm {name}...")
            networks = k.vm_ports(name)
            if networks:
                if domain is None:
                    domain = networks[0]
                k.reserve_host(name, networks, domain)
        currentvm = k.info(name)
        currentnets = currentvm.get('nets', [])
        currentdisks = currentvm.get('disks', [])
        if disks:
            pprint(f"Updating disks of vm {name}")
            for index, currentdisk in enumerate(currentdisks):
                if index < len(disks):
                    disk = disks[index]
                    currentdisksize = currentdisk['size']
                    disksize = disk.get('size', 10) if isinstance(disk, dict) else int(disk)
                    if disksize > currentdisksize:
                        if currentvm.get('status') != 'down':
                            warning(f"Cant resize Disk {index} in {name} while VM is up")
                            break
                        pprint(f"Resizing Disk {index} in {name}")
                        diskpath = currentdisk['path']
                        k.resize_disk(diskpath, disksize)
            if len(currentdisks) < len(disks):
                pprint(f"Adding Disks to {name}")
                for disk in disks[len(currentdisks):]:
                    diskname = None
                    size = self.disksize
                    pool = self.pool
                    interface = overrides.get('diskinterface') or 'virtio'
                    if isinstance(disk, int):
                        size = disk
                    elif isinstance(disk, str):
                        if disk.isdigit():
                            size = int(disk)
                        else:
                            diskname = disk
                    elif isinstance(disk, dict):
                        if 'name' in disk:
                            diskname = disk['name']
                        if 'size' in disk:
                            size = disk['size']
                        if 'pool' in disk:
                            pool = disk['pool']
                        if 'interface' in disk:
                            interface = disk['interface']
                    else:
                        continue
                    k.add_disk(name=name, size=size, pool=pool, interface=interface, existing=diskname)
            if len(currentdisks) > len(disks):
                pprint(f"Removing Disks of {name}")
                for disk in currentdisks[len(currentdisks) - len(disks) - 1:]:
                    diskname = os.path.basename(disk['path'])
                    diskpool = os.path.dirname(disk['path'])
                    k.delete_disk(name=name, diskname=diskname, pool=diskpool)
        if nets:
            pprint(f"Updating nets of vm {name}")
            if len(currentnets) < len(nets):
                pprint(f"Adding Nics to {name}")
                for net in nets[len(currentnets):]:
                    model = 'virtio'
                    if isinstance(net, str):
                        network = net
                    elif isinstance(net, dict) and 'name' in net:
                        network = net['name']
                        model = net.get('model', 'virtio')
                    else:
                        error(f"Skipping wrong nic spec for {name}")
                        continue
                    k.add_nic(name, network, model=model)
            if len(currentnets) > len(nets):
                pprint(f"Removing Nics of {name}")
                for net in range(len(currentnets), len(nets), -1):
                    interface = "eth%s" % (net - 1)
                    k.delete_nic(name, interface)
            for index, currentnet in enumerate(currentnets):
                if index > len(nets):
                    break
                netname = currentnet['net']
                targetnetname = nets[index]['name'] if isinstance(nets[index], dict) else nets[index]
                if targetnetname != netname:
                    pprint(f"Updating nic {index} to network {targetnetname}")
                    k.update_nic(name, index, targetnetname)
        if extra_metadata:
            for key in extra_metadata:
                if key in ['ena', 'EnaSupport', 'sriov', 'SriovNetSupport', 'gpus', 'accelerators', 'router',
                           'can_ip_forward', 'SourceDestCheck']:
                    continue
                value = extra_metadata[key]
                pprint(f"Updating {key} of vm {name} to {value}...")
                k.update_metadata(name, key, value)
        if overrides.get('files', []) and not overrides.get('skip_files_remediation', False):
            newfiles = overrides['files']
            pprint(f"Remediating files of {name}")
            self.remediate_files(name, newfiles, overrides)
        if self.type == 'kvm':
            pool = overrides.get('pool')
            if pool is not None:
                k.update_pool(name, pool)
            if cpuflags:
                pprint(f"Updating cpuflags of vm {name}")
                k.update_cpuflags(name, cpuflags, disable)
        elif self.type == 'vsphere' and template is not None and isinstance(template, bool):
            target = 'template' if template else 'vm'
            pprint(f"Updating vm {name} to {target}...")
            if template:
                k.convert_to_template(name)
            else:
                k.convert_to_vm(name)
        elif self.type == 'aws':
            ena = overrides.get('ena') or overrides.get('EnaSupport')
            if ena is not None:
                k.update_attribute(name, 'EnaSupport', ena)
            sriov = overrides.get('sriov') or overrides.get('SriovNetSupport')
            if sriov is not None:
                if isinstance(sriov, bool) and not sriov:
                    warning("SriovNetSupport can't be disabled")
                else:
                    sriov = 'simple'
                    k.update_attribute(name, 'SriovNetSupport', sriov)
            if 'router' in overrides or 'SourceDestCheck' in overrides:
                mode = not overrides.get('SourceDestCheck') or overrides.get('router')
                pprint(f"Setting router mode in vm {name} to {mode}...")
                k.set_router_mode(name, mode)
        elif self.type == 'gcp':
            accelerators = overrides.get('accelerators') or overrides.get('gpus') or []
            if accelerators:
                pprint(f"Updating gpus of vm {name}")
                k.update_gpus(name, accelerators)
            if overrides.get('reserveip', False):
                pprint(f"Updating reserveip of vm {name}")
                k.update_reserveip(name)
            if 'router' in overrides or 'can_ip_forward' in overrides:
                mode = overrides.get('can_ip_forward') or overrides.get('router')
                pprint(f"Setting router mode in vm {name} to {mode}...")
                k.set_router_mode(name, mode)
        return {'result': 'success'}

    def list_plans(self):
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
        k = self.k
        if self.type == 'web' and self.k.localkube:
            return k.list_kubes()
        kubes = {}
        for vm in k.list():
            if 'kube' in vm and 'kubetype' in vm:
                vmname = vm['name']
                kube = vm['kube']
                _type = vm['kubetype']
                plan = vm['plan']
                if kube not in kubes:
                    kubes[kube] = {'type': _type, 'plan': plan, 'vms': [vmname]}
                else:
                    kubes[kube]['vms'].append(vmname)
        for kube in kubes:
            kubes[kube]['vms'] = ','.join(kubes[kube]['vms'])
        clustersdir = os.path.expanduser('~/.kcli/clusters')
        if os.path.exists(clustersdir):
            for kube in next(os.walk(clustersdir))[1]:
                if kube in kubes:
                    continue
                clusterdir = f'{clustersdir}/{kube}'
                _type, plan = 'generic', kube
                if os.path.exists(f'{clusterdir}/kcli_parameters.yml'):
                    with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
                        installparam = yaml.safe_load(install)
                        _type = installparam.get('kubetype', _type)
                        plan = installparam.get('plan', plan)
                kubes[kube] = {'type': _type, 'plan': plan, 'vms': []}
        if self.type == 'gcp':
            try:
                from kvirt.cluster import gke
                kubes.update(gke.list(self))
            except:
                pass
        elif self.type == 'aws':
            try:
                from kvirt.cluster import eks
                kubes.update(eks.list(self))
            except:
                pass
        elif self.type == 'azure':
            try:
                from kvirt.cluster import aks
                kubes.update(aks.list(self))
            except:
                pass
        return kubes

    def start_plan(self, plan, container=False):
        k = self.k
        startfound = False
        pprint(f"Starting vms from plan {plan}")
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
                    success(f"{name} started on {hypervisor}!")
        if container:
            cont = Kcontainerconfig(self, client=self.containerclient).cont
            for conta in sorted(cont.list_containers(k)):
                name = conta[0]
                containerplan = conta[3]
                if containerplan == plan:
                    startfound = True
                    cont.start_container(name)
                    success(f"Container {name} started!")
        if startfound:
            success(f"Plan {plan} started!")
        else:
            warning("No matching objects found")
        return {'result': 'success'}

    def stop_plan(self, plan, soft=False, container=False):
        k = self.k
        stopfound = False
        pprint(f"Stopping vms from plan {plan}")
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
                    c.stop(name, soft=soft)
                    success(f"{name} stopped on {hypervisor}!")
        if container:
            cont = Kcontainerconfig(self, client=self.containerclient).cont
            for conta in sorted(cont.list_containers()):
                name = conta[0]
                containerplan = conta[3]
                if containerplan == plan:
                    stopfound = True
                    cont.stop_container(name)
                    success(f"Container {name} stopped!")
        if stopfound:
            success(f"Plan {plan} stopped!")
        else:
            warning("No matching objects found")
        return {'result': 'success'}

    def autostart_plan(self, plan):
        k = self.k
        pprint(f"Set vms from plan {plan} to autostart")
        for vm in sorted(k.list(), key=lambda x: x['name']):
            name = vm['name']
            description = vm['plan']
            if description == plan:
                k.update_start(name, start=True)
                success(f"{name} set to autostart!")
        return {'result': 'success'}

    def noautostart_plan(self, plan):
        k = self.k
        pprint(f"Preventing vms from plan {plan} to autostart")
        for vm in sorted(k.list(), key=lambda x: x['name']):
            name = vm['name']
            description = vm['plan']
            if description == plan:
                k.update_start(name, start=False)
                success(f"{name} prevented to autostart!")
        return {'result': 'success'}

    def delete_plan(self, plan, container=False, unregister=False):
        k = self.k
        deletedvms = []
        deletedlbs = []
        dnsclients = []
        networks = []
        if plan == '':
            error("That would delete every vm...Not doing that")
            sys.exit(1)
        found = False
        deleteclients = {self.client: k}
        vmclients = []
        vmclients_file = os.path.expanduser(f'~/.kcli/vmclients_{plan}')
        if os.path.exists(vmclients_file):
            vmclients = yaml.safe_load(open(vmclients_file))
            os.remove(vmclients_file)
        if self.extraclients:
            deleteclients.update(self.extraclients)
        elif vmclients:
            deleteclients.update({cli: Kconfig(client=cli).k for cli in vmclients if cli != self.client})
        deleted_clusters = []
        for hypervisor in deleteclients:
            c = deleteclients[hypervisor]
            for vm in sorted(c.list(), key=lambda x: x['name']):
                name = vm['name']
                description = vm.get('plan')
                if description == plan:
                    if vm.get('kubetype', 'generic') in ['aks', 'eks', 'gke']:
                        continue
                    cluster = vm.get('kube')
                    if cluster is not None and cluster != '':
                        if cluster not in deleted_clusters:
                            pprint(f"Deleting cluster {cluster}")
                            self.delete_kube(cluster)
                            deleted_clusters.append(cluster)
                            found = True
                        continue
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
                    if unregister:
                        image = k.info(name).get('image')
                        if 'rhel' in image:
                            pprint(f"Removing rhel subscription for {name}")
                            ip, vmport = _ssh_credentials(k, name)[1:]
                            cmd = "subscription-manager unregister"
                            sshcmd = ssh(name, ip=ip, user='root', tunnel=self.tunnel,
                                         tunnelhost=self.tunnelhost, tunnelport=self.tunnelport,
                                         tunneluser=self.tunneluser, insecure=True, cmd=cmd, vmport=vmport)
                            os.system(sshcmd)
                    c.delete(name, snapshots=True)
                    if dnsclient is not None and domain is not None and dnsclient in self.clients:
                        if dnsclient in dnsclients:
                            z = dnsclients[dnsclient]
                        elif dnsclient in self.clients:
                            z = Kconfig(client=dnsclient).k
                            dnsclients[dnsclient] = z
                        z.delete_dns(dnsclient, domain)
                    common.delete_lastvm(name, self.client)
                    success(f"{name} deleted on {hypervisor}!")
                    deletedvms.append(name)
                    found = True
        if container:
            cont = Kcontainerconfig(self, client=self.containerclient).cont
            for conta in sorted(cont.list_containers(k)):
                name = conta[0]
                container_plan = conta[3]
                if container_plan == plan:
                    cont.delete_container(name)
                    success(f"Container {name} deleted!")
                    found = True
        if not self.keep_networks:
            if self.type == 'kvm':
                networks = k.list_networks()
                for network in k.list_networks():
                    if 'plan' in networks[network] and networks[network]['plan'] == plan:
                        networkresult = k.delete_network(network)
                        if networkresult['result'] == 'success':
                            success(f"network {network} deleted!")
                            found = True
            elif networks:
                found = True
                for network in networks:
                    networkresult = k.delete_network(network)
                    if networkresult['result'] == 'success':
                        success(f"Unused network {network} deleted!")
        for keyfile in glob.glob("%s.key*" % plan):
            success(f"file {keyfile} from {plan} deleted!")
            os.remove(keyfile)
        if deletedlbs and self.type in ['aws', 'azure', 'gcp']:
            for lb in deletedlbs:
                self.delete_loadbalancer(lb)
        if found:
            success(f"Plan {plan} deleted!")
            return {'result': 'success', 'deletedvm': deletedvms}
        else:
            error(f"No objects found during deletion of plan {plan}")
            return {'result': 'failure'}

    def snapshot_plan(self, plan, snapshotname=None):
        k = self.k
        snapshotfound = False
        pprint(f"Snapshotting vms from plan {plan}")
        if snapshotname is None:
            warning(f"Using {plan} as snapshot name as None was provided")
            snapshotname = plan
        for vm in sorted(k.list(), key=lambda x: x['name']):
            name = vm['name']
            description = vm['plan']
            if description == plan:
                snapshotfound = True
                k.create_snapshot(snapshotname, name)
                success(f"{name} snapshotted!")
        if snapshotfound:
            success(f"Plan {plan} snapshotted!")
        else:
            warning("No matching vms found")
        return {'result': 'success'}

    def revert_plan(self, plan, snapshotname=None):
        k = self.k
        revertfound = False
        pprint(f"Reverting snapshots of vms from plan {plan}")
        if snapshotname is None:
            warning(f"Using {plan} as snapshot name as None was provided")
            snapshotname = plan
        for vm in sorted(k.list(), key=lambda x: x['name']):
            name = vm['name']
            description = vm['plan']
            if description == plan:
                revertfound = True
                k.revert_snapshot(snapshotname, name)
                success(f"snapshot of {name} reverted!")
        if revertfound:
            success(f"Plan {plan} reverted with snapshot {snapshotname}!")
        else:
            warning("No matching vms found")
        return {'result': 'success'}

    def select_client(self, vmclient, hosts):
        if vmclient is None:
            z = self.k
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
            error(f"Client {vmclient} not found. Skipping")
            return
        return vmclient, z

    def plan(self, plan, ansible=False, url=None, path=None, container=False, inputfile=None, inputstring=None,
             overrides={}, info=False, update=False, embedded=False, download=False, quiet=False, doc=False,
             onlyassets=False, excludevms=[], basemode=False, threaded=False):
        pre = overrides.get('pre', True)
        k = self.k
        no_overrides = not overrides
        threads = []
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
        if url is not None:
            if url.startswith('/'):
                url = f"file://{url}"
            if not url.endswith('.yml'):
                url = f"{url}/kcli_plan.yml"
                pprint(f"Trying to retrieve {url}")
            inputfile = os.path.basename(url)
            onfly = os.path.dirname(url)
            path = plan if path is None else path
            if not quiet:
                pprint(f"Retrieving specified plan from {url} to {path}")
            if container_mode():
                path = f"/workdir/{path}"
            if not os.path.exists(path):
                toclean = True
                common.fetch(url, path)
                for default_parameter_file in ['/kcli_default.yml', f'/{plan}_default.yml',
                                               "/%s_default%s" % os.path.splitext(os.path.basename(url))]:
                    try:
                        common.fetch(os.path.dirname(url) + default_parameter_file, path)
                    except:
                        pass
            elif download:
                msg = f"target directory {path} already there"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            else:
                pprint(f"Using existing directory {path}")
            if download:
                inputfile = f"{path}/{inputfile}"
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
                            pprint(f"Retrieving file {onfly}/{origin}")
                            try:
                                common.fetch(f"{onfly}/{origin}", destdir)
                            except:
                                if common.url_exists(f"{onfly}/{origin}/README.md"):
                                    os.makedirs(origin, exist_ok=True)
                                else:
                                    pprint(f"file {onfly}/{origin} skipped")
                    for script in scriptfiles:
                        if '~' not in script:
                            destdir = "."
                            if '/' in script:
                                destdir = os.path.dirname(script)
                                os.makedirs(destdir, exist_ok=True)
                            pprint(f"Retrieving script {onfly}/{script}")
                            common.fetch(f"{onfly}/{script}", destdir)
                os.chdir('..')
                return {'result': 'success'}
        if inputstring is not None:
            inputfile = f"temp_plan_{plan}.yml"
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
            error(f"Input file {inputfile} not found.Leaving....")
            sys.exit(1)
        elif os.path.isdir(inputfile):
            inputfile = f"{inputfile}/kcli_plan.yml"
        if info:
            self.info_plan(inputfile, onfly=onfly, quiet=quiet, doc=doc)
            if toclean:
                os.chdir('..')
                rmtree(path)
            return {'result': 'success'}
        baseentries = {}
        entries, overrides, basefile, basedir = self.process_inputfile(plan, inputfile, overrides=overrides,
                                                                       onfly=onfly, full=True, split=True)
        if basefile is not None:
            baseinfo = self.process_inputfile(plan, f"{basedir}/{basefile}", overrides=overrides, full=True)
            baseentries, baseoverrides = baseinfo[0], baseinfo[1]
            if baseoverrides:
                overrides.update({key: baseoverrides[key] for key in baseoverrides if key not in overrides})
        if entries is None:
            entries = {}
        if self.debug:
            print(yaml.dump(entries))
        parameters = entries.get('parameters', {})
        if parameters:
            del entries['parameters']
        valid_plan = [entry for entry in entries if isinstance(entries[entry], list) and
                      all(isinstance(item, dict) for item in entries[entry])]
        if not valid_plan:
            if basemode:
                warning(f"{inputfile} doesn't look like a valid plan.Skipping....")
                return {"result": "success"}
            else:
                msg = f"{inputfile} doesn't look like a valid plan file. Maybe you provided a parameter file ?"
                return {'result': 'failure', 'reason': msg}
        inputdir = os.path.dirname(inputfile) if os.path.dirname(inputfile) != '' and os.path.isabs(inputfile) else '.'
        pre_base = os.path.splitext(os.path.basename(inputfile))[0]
        pre_script = f'{inputdir}/kcli_pre.sh' if pre_base == 'kcli_plan' else f"{inputdir}/{pre_base}_pre.sh"
        if os.path.exists(pre_script):
            pre_script_short = os.path.basename(pre_script)
            if pre:
                pprint(f"Running {pre_script_short}")
                with TemporaryDirectory() as tmpdir:
                    pre_script = self.process_inputfile('xxx', pre_script, overrides=overrides)
                    with open(f"{tmpdir}/pre.sh", 'w') as f:
                        f.write(pre_script)
                    pre_run = run(f'bash {tmpdir}/pre.sh', shell=True, stdout=PIPE, stderr=STDOUT,
                                  universal_newlines=True)
                    print(pre_run.stdout)
                    if pre_run.returncode != 0:
                        msg = f"Issue when running {pre_script_short}:\n{pre_run.stdout}"
                        return {'result': 'failure', 'reason': msg}
            else:
                warning(f"Skipping {pre_script_short} as requested")
        keywords = self.list_keywords()
        for key in sorted(overrides):
            if key in keywords:
                key_value = getattr(self, key, 'not_default')
                if key_value == 'not_default':
                    continue
                key_type = type(key_value)
                override_key_type = type(overrides[key])
                if key_value is not None and overrides[key] is not None and key_type != override_key_type:
                    error(f"The provided parameter {key} has a wrong type {override_key_type}, it should be {key_type}")
                    sys.exit(1)
                elif overrides[key] is not None:
                    setattr(self, key, overrides[key])
        baseplans = []
        vmentries = entries.get('vm', [])
        diskentries = entries.get('disk', [])
        networkentries = entries.get('network', [])
        containerentries = entries.get('container', [])
        ansibleentries = entries.get('ansible', [])
        profileentries = entries.get('profile', [])
        imageentries = entries.get('image', []) + entries.get('template', [])
        poolentries = entries.get('pool', [])
        planentries = entries.get('plan', [])
        dnsentries = entries.get('dns', [])
        kubeentries = entries.get('kube', []) + entries.get('cluster', [])
        lbs = entries.get('loadbalancer', [])
        sgs = entries.get('securitygroup', [])
        bucketentries = entries.get('bucket', [])
        workflowentries = entries.get('workflow', [])
        if overrides.get('workflow_installer', False):
            for index, entry in enumerate(vmentries):
                if 'installer' in next(iter(entry)):
                    workflowentries.append(vmentries[index])
                    del vmentries[index]
                    break
        for entry in profileentries:
            p = next(iter(entry))
            vmprofiles[p] = entry[p]
        hosts = {}
        if networkentries and not onlyassets:
            pprint("Deploying Networks...")
            for entry in networkentries:
                net = next(iter(entry))
                netprofile = entry[net]
                vmclient, z = self.select_client(netprofile.get('vmclient'), hosts)
                if z is None:
                    continue
                if z.net_exists(net):
                    pprint(f"Network {net} skipped!")
                    continue
                cidr = netprofile.get('cidr')
                nat = bool(netprofile.get('nat', True))
                if cidr is None:
                    warning(f"Missing Cidr for network {net}. Not creating it...")
                    continue
                dhcp = netprofile.get('dhcp', True)
                domain = netprofile.get('domain')
                result = z.create_network(name=net, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, plan=plan,
                                          overrides=netprofile)
                common.handle_response(result, net, element='Network')
        if poolentries and not onlyassets:
            pprint("Deploying Pools...")
            pools = k.list_pools()
            for entry in poolentries:
                pool = next(iter(entry))
                if pool in pools:
                    pprint(f"Pool {pool} skipped!")
                    continue
                else:
                    poolprofile = entry[pool]
                    poolpath = poolprofile.get('path')
                    if poolpath is None:
                        warning(f"Pool {pool} skipped as path is missing!")
                        continue
                    k.create_pool(pool, poolpath)
        if imageentries and not onlyassets:
            pprint("Deploying Images...")
            images = [os.path.basename(t) for t in k.volumes()]
            for entry in imageentries:
                image = next(iter(entry))
                imageprofile = entry[image]
                pool = imageprofile.get('pool', self.pool)
                imagesize = imageprofile.get('size')
                imageurl = imageprofile.get('url')
                if image in images:
                    pprint(f"Image {image} skipped!")
                    continue
                else:
                    if isinstance(imageurl, str) and imageurl == "None":
                        imageurl = None
                    cmds = imageprofile.get('cmds', [])
                    self.download_image(pool=pool, image=image, cmds=cmds, url=imageurl, size=imagesize)
        if bucketentries and not onlyassets and self.type in ['aws', 'azure', 'gcp', 'openstack']:
            pprint("Deploying Bucket Entries...")
            for entry in bucketentries:
                bucketentry = next(iter(entry))
                bucketprofile = entry[bucketentry]
                _files = bucketprofile.get('files', [])
                self.k.create_bucket(bucketentry)
                for _fil in _files:
                    self.k.upload_to_bucket(bucketentry, _fil)
        tempkey = overrides.get('tempkey', False) or self.tempkey
        if tempkey:
            tempkeydir = TemporaryDirectory()
            overrides['tempkeydir'] = tempkeydir
            overrides['tempkeydirkeep'] = True
        if planentries:
            pprint("Deploying Plans...")
            for entry in planentries:
                planentry = next(iter(entry))
                details = entry[planentry]
                planurl = details.get('url')
                planfile = details.get('file')
                if planurl is None and planfile is None:
                    warning(f"Missing Url/File for plan {planentry}. Not creating it...")
                    continue
                elif planurl is not None:
                    path = planentry
                    if not planurl.endswith('yml'):
                        planurl = f"{planurl}/kcli_plan.yml"
                elif '/' in planfile:
                    path = os.path.dirname(planfile)
                    inputfile = os.path.basename(planfile)
                else:
                    path = '.'
                    inputfile = planentry
                if no_overrides and parameters:
                    pprint("Using parameters from father plan in child ones")
                    for override in overrides:
                        print("Using parameter %s: %s" % (override, overrides[override]))
                self.plan(plan, ansible=False, url=planurl, path=path, container=False, inputfile=inputfile,
                          overrides=overrides, embedded=embedded, download=download)
        if kubeentries and not onlyassets:
            pprint("Deploying Cluster entries...")
            dnsclients = {}
            kubethreaded = len(kubeentries) > 1
            if kubethreaded:
                warning("Launching each cluster in a thread as there is more than one...")
            for entry in kubeentries:
                cluster = next(iter(entry))
                pprint(f"Deploying Cluster {cluster}...")
                kubeprofile = entry[cluster]
                kubeclient = kubeprofile.get('client')
                if kubeclient is None:
                    currentconfig = self
                elif kubeclient in self.clients:
                    currentconfig = Kconfig(client=kubeclient)
                else:
                    error(f"Client {kubeclient} not found. skipped")
                    continue
                kubetype = kubeprofile.get('kubetype') or kubeprofile.get('clustertype', 'generic')
                kube_overrides = overrides.copy()
                kube_overrides.update(kubeprofile)
                kube_overrides['cluster'] = cluster
                existing_ctlplanes = [v for v in currentconfig.k.list() if f'{cluster}-ctlplane' in v['name']]
                if existing_ctlplanes:
                    pprint(f"Cluster {cluster} found. skipped!")
                    continue
                kubetypes = ['generic', 'openshift', 'hypershift', 'microshift', 'k3s', 'gke', 'aks', 'eks', 'rke2']
                if kubetype not in kubetypes:
                    warning(f"Incorrect kubetype {kubetype} specified. skipped!")
                    continue
                if kubethreaded:
                    kube_overrides['use_existing_openshift'] = True
                    new_args = (plan, kubetype, kube_overrides)
                    t = threading.Thread(target=self.threaded_create_kube, args=new_args)
                    threads.append(t)
                    t.start()
                else:
                    result = currentconfig.create_kube(plan, kubetype, overrides=kube_overrides)
                    if 'result' in result and result['result'] != 'success':
                        error(result['reason'])
        if vmentries:
            if not onlyassets:
                pprint("Deploying Vms...")
            vmcounter = 0
            vms_to_host = {}
            vmnames = [next(iter(entry)) for entry in vmentries]
            if basefile is not None:
                basedir = os.path.dirname(inputfile) if os.path.isabs(inputfile) else '.'
                baseinputfile = f"{basedir}/{basefile}"
                if container_mode() and not os.path.isabs(basefile) and '/workdir' not in basedir:
                    baseinputfile = f"/workdir/{basedir}/{basefile}"
                result = self.plan(plan, inputfile=baseinputfile, overrides=overrides, excludevms=vmnames,
                                   basemode=True, onlyassets=onlyassets)
                if result['result'] != 'success':
                    return result
                baseplans.append(basefile)
            vmrules_strict = overrides.get('vmrules_strict', self.vmrules_strict)
            for entry in vmentries:
                name = next(iter(entry))
                if name in excludevms:
                    continue
                currentplandir = basedir
                if len(vmentries) == 1 and 'name' in overrides:
                    newname = overrides['name']
                    profile = entry[name]
                    name = newname
                else:
                    profile = entry[name]
                if 'name' in profile:
                    name = profile['name']
                if 'basevm' in profile or 'baseplan' in profile:
                    baseprofile = {}
                    appendkeys = ['disks', 'nets', 'files', 'scripts', 'cmds']
                    if 'baseplan' in profile:
                        baseplan = profile['baseplan']
                        basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
                        baseinputfile = f"{basedir}/{baseplan}"
                        if container_mode() and not os.path.isabs(baseplan) and '/workdir' not in basedir:
                            baseinputfile = f"/workdir/{basedir}/{baseplan}"
                        basevm = profile['basevm'] if 'basevm' in profile else name
                        if baseplan not in baseplans:
                            self.plan(plan, inputfile=baseinputfile, overrides=overrides, excludevms=vmnames,
                                      basemode=True, onlyassets=onlyassets)
                            baseplans.append(baseplan)
                        baseinfo = self.process_inputfile(plan, baseinputfile, overrides=overrides, full=True)
                        baseprofile = baseinfo[0][basevm] if basevm in baseinfo[0] else {}
                        currentplandir = baseinfo[3] if os.path.isabs(baseinfo[3]) else '.'
                    elif 'basevm' in profile and profile['basevm'] in baseentries:
                        baseprofile = baseentries[profile['basevm']]
                    else:
                        warning(f"Incorrect base entry for {name}. Skipping...")
                        continue
                    for key in baseprofile:
                        if key not in profile:
                            profile[key] = baseprofile[key]
                        elif key in baseprofile and key in profile and key in appendkeys:
                            profile[key] = baseprofile[key] + profile[key]
                rulefound = False
                for entry in overrides.get('vmrules', self.vmrules):
                    if len(entry) != 1:
                        error(f"Wrong vm rule {entry}")
                        sys.exit(1)
                    rule = next(iter(entry))
                    if (re.match(rule, name) or fnmatch(name, rule)) and isinstance(entry[rule], dict):
                        rulefound = True
                        listkeys = ['cmds', 'files', 'scripts']
                        for rule in entry:
                            current = entry[rule]
                            for key in current:
                                if key in listkeys and isinstance(current[key], list) and key in profile:
                                    current[key] = profile[key] + current[key]
                            profile.update(entry[rule])
                            if 'name' in entry[rule]:
                                old_name = name
                                warning(f"Renaming {name} to {entry[rule]['name']}")
                                name = entry[rule]['name']
                                if 'ctlplane' or 'worker' in old_name:
                                    profile['role'] = 'ctlplane' if 'ctlplane' in old_name else 'worker'
                if vmrules_strict and not rulefound:
                    warning(f"No vmrules found for {name}. Skipping...")
                    continue
                vmclient, z = self.select_client(profile.get('client'), hosts)
                if z is None:
                    continue
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
                if z.exists(name) and not onlyassets:
                    if not update:
                        pprint(f"{name} skipped on {vmclient}!")
                    else:
                        updated = False
                        currentvm = z.info(name)
                        currentstart = currentvm.get('autostart', False)
                        currentmemory = currentvm['memory']
                        currentimage = currentvm.get('template')
                        currentimage = currentvm.get('image', currentimage)
                        currentcpus = int(currentvm['numcpus'])
                        currentnets = currentvm['nets']
                        currentdisks = currentvm['disks']
                        currentflavor = currentvm.get('flavor')
                        if 'autostart' in profile and currentstart != profile['autostart']:
                            updated = True
                            pprint(f"Updating autostart of {name} to {profile['autostart']}")
                            z.update_start(name, profile['autostart'])
                        if 'flavor' in profile and str(currentflavor) != str(profile['flavor']):
                            updated = True
                            pprint(f"Updating flavor of {name} to {profile['flavor']}")
                            z.update_flavor(name, profile['flavor'])
                        else:
                            if 'memory' in profile and currentmemory != profile['memory']:
                                updated = True
                                pprint(f"Updating memory of {name} to {profile['memory']}")
                                z.update_memory(name, profile['memory'])
                            if 'numcpus' in profile and currentcpus != profile['numcpus']:
                                updated = True
                                pprint(f"Updating cpus of {name} to {profile['numcpus']}")
                                z.update_cpus(name, profile['numcpus'])
                        if 'disks' in profile:
                            if len(currentdisks) < len(profile['disks']):
                                updated = True
                                pprint(f"Adding Disks to {name}")
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
                                pprint(f"Removing Disks of {name}")
                                for disk in currentdisks[len(currentdisks) - len(profile['disks']):]:
                                    diskname = os.path.basename(disk['path'])
                                    diskpool = os.path.dirname(disk['path'])
                                    z.delete_disk(name=name, diskname=diskname, pool=diskpool)
                        if 'nets' in profile:
                            if len(currentnets) < len(profile['nets']):
                                updated = True
                                pprint(f"Adding Nics to {name}")
                                for net in profile['nets'][len(currentnets):]:
                                    if isinstance(net, str):
                                        network = net
                                    elif isinstance(net, dict) and 'name' in net:
                                        network = net['name']
                                    else:
                                        error(f"Skpping wrong nic spec for {name}")
                                        continue
                                    z.add_nic(name, network)
                            if len(currentnets) > len(profile['nets']):
                                updated = True
                                pprint(f"Removing Nics of {name}")
                                for net in range(len(currentnets), len(profile['nets']), -1):
                                    interface = f"eth{net - 1}"
                                    z.delete_nic(name, interface)
                        if profile.get('files', []) and not overrides.get('skip_files_remediation', False)\
                           and self.remediate_files(name, profile.get('files', []), overrides, inputdir=inputdir):
                            updated = True
                        if not updated:
                            pprint(f"{name} skipped on {vmclient}!")
                    existingvms.append(name)
                    continue
                sharedkey = profile.get('sharedkey', self.sharedkey)
                if sharedkey:
                    vmcounter += 1
                    if not os.path.exists(f"{plan}.key") or not os.path.exists(f"{plan}.key.pub"):
                        os.system(f"ssh-keygen -qt rsa -N '' -f {plan}.key")
                    publickey = open(f"{plan}.key.pub").read().strip()
                    privatekey = open(f"{plan}.key").read().strip()
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
                        os.remove(f"{plan}.key.pub")
                currentoverrides = overrides.copy()
                if 'image' in profile:
                    for entry in self.list_profiles():
                        currentimage = profile['image']
                        entryprofile = entry[0]
                        if entryprofile == currentimage:
                            profile['image'] = entry[4]
                            currentoverrides['image'] = profile['image']
                            break
                if threaded:
                    new_args = (name, profilename, currentoverrides, profile, z, plan, currentplandir, vmclient,
                                onfly, onlyassets, newvms, failedvms, asyncwaitvms, newassets)
                    t = threading.Thread(target=self.threaded_create_vm, args=new_args)
                    threads.append(t)
                    t.start()
                else:
                    result = self.create_vm(name, profilename, overrides=currentoverrides, customprofile=profile, k=z,
                                            plan=plan, basedir=currentplandir, client=vmclient, onfly=onfly,
                                            onlyassets=onlyassets)
                    if not onlyassets:
                        common.handle_response(result, name, client=vmclient)
                    self.handle_vm_result(name, profile, result=result, newvms=newvms, failedvms=failedvms,
                                          asyncwaitvms=asyncwaitvms, onlyassets=onlyassets, newassets=newassets,
                                          vmclient=vmclient)
        if vmentries and threaded:
            while True:
                for index, t in enumerate(threads):
                    if not t.is_alive():
                        del threads[index]
                if not threads:
                    break
                else:
                    sleep(1)
        vmclients = list(hosts.keys())
        if len(vmclients) > 1:
            yaml.safe_dump(vmclients, open(os.path.expanduser(f'~/.kcli/vmclients_{plan}'), 'w'))
        if diskentries and not onlyassets:
            pprint("Deploying Disks...")
        for entry in diskentries:
            disk = next(iter(entry))
            profile = entry[disk]
            pool = profile.get('pool')
            vms = profile.get('vms')
            template = profile.get('template')
            image = profile.get('image', template)
            size = int(profile.get('size', 10))
            thin = profile.get('thin', True)
            if pool is None:
                error(f"Missing Key Pool for disk section {disk}. Not creating it...")
                continue
            if vms is None:
                error(f"Missing or Incorrect Key Vms for disk section {disk}. Not creating it...")
                continue
            shareable = True if len(vms) > 1 else False
            if k.disk_exists(pool, disk):
                pprint(f"Creation for Disk {disk} skipped!")
                poolpath = k.get_pool_path(pool)
                newdisk = f"{poolpath}/{disk}"
                for vm in vms:
                    pprint(f"Adding disk {disk} to {vm}")
                    k.add_disk(name=vm, size=size, pool=pool, image=image, shareable=shareable, existing=newdisk,
                               thin=thin)
            else:
                newdisk = k.create_disk(disk, size=size, pool=pool, image=image, thin=thin)
                if newdisk is None:
                    error(f"Disk {disk} not deployed. It won't be added to any vm")
                else:
                    common.pprint(f"Disk {disk} deployed!")
                    for vm in vms:
                        pprint(f"Adding disk {disk} to {vm}")
                        k.add_disk(name=vm, size=size, pool=pool, image=image, shareable=shareable,
                                   existing=newdisk, thin=thin)
        if containerentries and not onlyassets:
            cont = Kcontainerconfig(self, client=self.containerclient).cont
            pprint("Deploying Containers...")
            label = f"plan={plan}"
            for entry in containerentries:
                container = next(iter(entry))
                if cont.exists_container(container):
                    pprint(f"Container {container} skipped!")
                    continue
                profile = entry[container]
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
                success(f"Container {container} deployed!")
                cont.create_container(name=container, image=containerimage, nets=nets, cmds=cmds, ports=ports,
                                      volumes=volumes, environment=environment, label=label)
        if dnsentries and not onlyassets:
            pprint("Deploying Dns Entries...")
            dnsclients = {}
            for entry in dnsentries:
                dnsentry = next(iter(entry))
                dnsprofile = entry[dnsentry]
                dnsdomain = dnsprofile.get('domain')
                dnsnet = dnsprofile.get('net', 'default')
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
                    warning(f"Client {dnsclient} not found. Skipping")
                    return
                if dnsip is None:
                    warning("Missing ip. Skipping!")
                    return
                if dnsnet is None:
                    warning("Missing net. Skipping!")
                    return
                z.reserve_dns(name=dnsentry, nets=[dnsnet], domain=dnsdomain, ip=dnsip, alias=dnsalias, force=True,
                              primary=True)
        if ansibleentries and not onlyassets:
            if not newvms:
                warning("Ansible skipped as no new vm within playbook provisioned")
                return {'result': 'success'}
            for entry in sorted(ansibleentries):
                ansible_name = next(iter(entry))
                _ansible = entry[ansible_name]
                if 'playbook' not in _ansible:
                    error("Missing Playbook for ansible.Ignoring...")
                    sys.exit(1)
                playbook = _ansible['playbook']
                verbose = _ansible['verbose'] if 'verbose' in _ansible else False
                variables = _ansible.get('variables', {})
                targetvms = [vm for vm in _ansible['vms'] if vm in newvms] if 'vms' in _ansible else newvms
                if not targetvms:
                    warning("Ansible skipped as no new vm within playbook provisioned")
                    return
                ansiblecommand = "ansible-playbook"
                if verbose:
                    ansiblecommand += " -vvv"
                if variables:
                    varsfile = f"{plan}_vars.yml"
                    with open(varsfile, 'w') as f:
                        yaml.safe_dump(variables, f)
                    ansiblecommand += f" -e @{varsfile}"
                ansiblecommand += f" -i {which('klist.py')} {playbook} -l {','.join(targetvms)}"
                pprint(f"Running: {ansiblecommand}")
                os.system(ansiblecommand)
        if lbs and not onlyassets:
            dnsclients = {}
            pprint("Deploying Loadbalancers...")
            for index, entry in enumerate(lbs):
                lbentry = next(iter(entry))
                details = entry[lbentry]
                ports = details.get('ports', [])
                if not ports:
                    error("Missing Ports for loadbalancer. Not creating it...")
                    return
                checkpath = details.get('checkpath', '/')
                checkport = details.get('checkport', 80)
                alias = details.get('alias', [])
                domain = details.get('domain')
                dnsclient = details.get('dnsclient', overrides.get('dnsclient'))
                lbvms = details.get('vms', [])
                lbnets = details.get('nets', ['default'])
                internal = details.get('internal')
                ip = details.get('ip')
                self.create_loadbalancer(lbentry, nets=lbnets, ports=ports, checkpath=checkpath, vms=lbvms,
                                         domain=domain, plan=plan, checkport=checkport, alias=alias,
                                         internal=internal, dnsclient=dnsclient, ip=ip)
        if sgs and not onlyassets:
            pprint("Deploying SecurityGroups...")
            for entry in sgs:
                sg = next(iter(entry))
                details = entry[sg]
                name
                ports = details.get('ports', [])
                if not ports:
                    error("Missing Ports for sgs. Not creating it...")
                    return
                self.create_security_group(sg, {'ports': ports})
        if workflowentries and not onlyassets:
            pprint("Deploying Workflow Entries...")
            for entry in workflowentries:
                workflow = next(iter(entry))
                pprint(f"Deploying workflow {workflow}")
                workflow_overrides = overrides.copy()
                workflow_overrides.update(entry[workflow])
                baseplan = workflow_overrides.get('baseplan')
                if baseplan is not None and baseplan not in baseplans:
                    pprint(f"Deploying baseplan {baseplan}")
                    basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
                    baseinputfile = f"{basedir}/{baseplan}"
                    if container_mode() and not os.path.isabs(baseplan) and '/workdir' not in basedir:
                        baseinputfile = f"/workdir/{basedir}/{baseplan}"
                    self.plan(plan, inputfile=baseinputfile, overrides=overrides)
                    baseplans.append(baseplan)
                self.create_workflow(workflow, overrides=workflow_overrides)
        returndata = {'result': 'success', 'plan': plan}
        returndata['newvms'] = newvms if newvms else []
        returndata['existingvms'] = existingvms if existingvms else []
        returndata['failedvms'] = failedvms if failedvms else []
        returndata['assets'] = newassets if newassets else []
        if failedvms:
            returndata['result'] = 'failure'
            failednames = ','.join([v['name'] for v in failedvms])
            returndata['reason'] = f'The following vms failed: {failednames}'
        if getback or toclean:
            os.chdir('..')
        if toclean:
            rmtree(path)
        if inputstring is not None and os.path.exists(f"temp_plan_{plan}.yml"):
            os.remove(f"temp_plan_{plan}.yml")
        for entry in asyncwaitvms:
            name, finishfiles = entry['name'], entry['finishfiles']
            waitcommand, waittimeout = entry['waitcommand'], entry['waittimeout']
            vmclient = entry['vmclient']
            self.wait_finish(name, waitcommand=waitcommand, waittimeout=waittimeout, vmclient=vmclient)
            if finishfiles:
                self.handle_finishfiles(name, finishfiles, vmclient=vmclient)
        if overrides.get('tempkeydir') is not None:
            overrides.get('tempkeydir').cleanup()
        return returndata

    def download_image(self, pool=None, image=None, url=None, cmds=[], size=None, arch='x86_64',
                       kvm_openstack=True, rhcos_commit=None, rhcos_installer=False, name=None):
        k = self.k
        if pool is None:
            pool = self.pool
            pprint(f"Using pool {pool}")
        if image is not None:
            if url is None:
                if arch == 'aarch64':
                    IMAGES.update({i: IMAGES[i].replace('x86_64', arch).replace('amd64', 'arm64')
                                   for i in IMAGES})
                elif arch != 'x86_64':
                    IMAGES.update({i: IMAGES[i].replace('x86_64', arch).replace('amd64', arch)
                                   for i in IMAGES})
                if image not in IMAGES:
                    error(f"Image {image} has no associated url")
                    return {'result': 'failure', 'reason': "Incorrect image"}
                url = IMAGES[image]
                image_type = self.type
                if kvm_openstack and self.type == 'kvm':
                    image_type = 'openstack'
                if self.type == "proxmox":
                    image_type = 'kvm'
                if not kvm_openstack and self.type == 'kvm':
                    image += "-qemu"
                if 'rhcos' in image and not image.endswith('qcow2.gz'):
                    if rhcos_commit is not None:
                        url = common.get_commit_rhcos(rhcos_commit, _type=image_type)
                    elif rhcos_installer:
                        os.environ['PATH'] += f':{os.getcwd()}'
                        url = common.get_installer_rhcos(_type=image_type, arch=arch)
                    else:
                        if arch != 'x86_64':
                            url += f'-{arch}'
                        url = common.get_latest_rhcos(url, _type=image_type, arch=arch)
                if 'fcos' in image:
                    url = common.get_latest_fcos(url, _type=image_type)
                if image == 'fedoralatest':
                    url = common.get_latest_fedora(arch)
                image = os.path.basename(image)
                if image.startswith('rhel'):
                    if 'web' in sys.argv[0]:
                        return {'result': 'failure', 'reason': "Missing url"}
                    pprint(f"Opening url {url} for you to grab complete url for {image} kvm guest image")
                    webbrowser.open(url, new=2, autoraise=True)
                    url = input("Copy Url:\n")
                    if url.strip() == '':
                        error("Missing proper url.Leaving...")
                        return {'result': 'failure', 'reason': "Missing image"}
            if not cmds and image != '' and image in IMAGESCOMMANDS:
                cmds = [IMAGESCOMMANDS[image]]
            pprint(f"Grabbing image {image} from url {url}")
            need_iso = 'api/assisted-images/images' in url
            shortname = os.path.basename(url).split('?')[0]
            if need_iso and name is None:
                image = f'boot-{shortname}.iso'
            try:
                convert = '.raw.' in url
                result = k.add_image(url, pool, cmds=cmds, name=name or image, size=size, convert=convert)
            except Exception as e:
                image_type = 'iso' if url.endswith('.iso') else 'image'
                error(f"Hit issue when adding {image_type}. Got {e}")
                error(f"Please run kcli delete {image_type} --yes {name or image}")
                return {'result': 'failure', 'reason': "User interruption"}
            found = 'found' in result
            if found:
                return {'result': 'success'}
            common.handle_response(result, name or image, element='Image', action='Added')
            if result['result'] != 'success':
                return {'result': 'failure', 'reason': result['reason']}
        return {'result': 'success'}

    def switch_host(self, switch):
        if switch not in self.clients:
            error(f"Client {switch} not found in config.Leaving....")
            return {'result': 'failure', 'reason': f"Client {switch} not found in config"}
        enabled = self.ini[switch].get('enabled', True)
        if not enabled:
            error(f"Client {switch} is disabled.Leaving....")
            return {'result': 'failure', 'reason': f"Client {switch} is disabled"}
        pprint(f"Switching to client {switch}...")
        inifile = "%s/.kcli/config.yml" % os.environ.get('HOME')
        if os.path.exists(inifile):
            newini = ''
            for line in open(inifile).readlines():
                if 'client' in line:
                    newini += f" client: {switch}\n"
                else:
                    newini += line
            open(inifile, 'w').write(newini)
        return {'result': 'success'}

    def delete_loadbalancer(self, name, domain=None):
        k = self.k
        pprint(f"Deleting loadbalancer {name}")
        if self.type in ['aws', 'azure', 'gcp', 'ibm', 'hcloud']:
            dnsclient = k.delete_loadbalancer(name)
            if domain is not None and dnsclient is not None and isinstance(dnsclient, str):
                if dnsclient in self.clients:
                    z = Kconfig(client=dnsclient).k
                else:
                    warning(f"Client {dnsclient} not found. Skipping")
                z.delete_dns(name.replace('_', '-'), domain)
        elif self.type == 'kvm':
            k.delete(name)

    def create_loadbalancer(self, name, nets=['default'], ports=[], checkpath='/', vms=[], domain=None,
                            plan=None, checkport=80, alias=[], internal=False, dnsclient=None, ip=None):
        name = nameutils.get_random_name().replace('_', '-') if name is None else name
        pprint(f"Deploying loadbalancer {name}")
        k = self.k
        if self.type in ['aws', 'azure', 'gcp', 'ibm', 'hcloud']:
            lb_ip = k.create_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain,
                                          checkport=checkport, alias=alias, internal=internal,
                                          dnsclient=dnsclient, ip=ip)
            if dnsclient is not None:
                if dnsclient in self.clients:
                    z = Kconfig(client=dnsclient).k
                else:
                    warning(f"Client {dnsclient} not found. Skipping")
                z.reserve_dns(name.replace('_', '-'), ip=lb_ip, domain=domain, alias=alias)
        else:
            vminfo = []
            for vm in vms:
                if valid_ip(vm):
                    vmname = vm.replace(':', '-').replace('.', '-')
                    vminfo.append({'name': vmname, 'ip': vm})
                    continue
                counter = 0
                while counter != 100:
                    ip = k.ip(vm)
                    if ip is None:
                        sleep(5)
                        print(f"Waiting 5 seconds to grab ip for vm {vm}...")
                        counter += 5
                    else:
                        break
                vminfo.append({'name': vm, 'ip': ip})
            overrides = {
                "name": name,
                "vms": vminfo,
                "nets": nets,
                "ports": ports,
                "checkpath": checkpath,
                "domain": domain,
            }
            self.plan(plan, inputstring=haproxyplan, overrides=overrides)

    def list_loadbalancers(self):
        k = self.k
        if self.type not in ['aws', 'azure', 'gcp', 'ibm', 'hcloud']:
            results = []
            for vm in k.list():
                if vm['profile'].startswith('loadbalancer') and len(vm['profile'].split('-')) == 2:
                    ports = vm['profile'].split('-')[1]
                    results.append([vm['name'], vm['ip'], 'tcp', ports, ''])
            return results
        else:
            return k.list_loadbalancers()

    def wait_finish(self, name, image=None, quiet=False, waitcommand=None, waittimeout=0, identityfile=None,
                    vmclient=None):
        config = Kconfig(client=vmclient) if vmclient is not None else self
        k = config.k
        if image is None:
            image = k.info(name)['image']
        pprint(f"Waiting for vm {name} to finish customisation")
        if waitcommand is not None and '2>' not in waitcommand:
            waitcommand += " 2>/dev/null"
        if common.needs_ignition(image):
            cmd = waitcommand or 'sudo journalctl --all --no-pager'
        else:
            cmd = waitcommand or f"sudo tail -n 50 {common.get_cloudinitfile(image)}"
        user, ip, vmport = None, None, None
        hostip = None
        timeout = 0
        while ip is None:
            info = k.info(name)
            if config.type == 'packet' and info.get('status') != 'active':
                warning("Waiting for node to be active")
                ip = None
            else:
                user, ip = config.vmuser or info.get('user'), info.get('ip')
                if config.type == 'kubevirt':
                    if k.access_mode == 'NodePort':
                        vmport = info.get('nodeport')
                        if hostip is None:
                            hostip = k.node_host(name=info.get('host'))
                        ip = hostip
                    elif k.access_mode == 'LoadBalancer':
                        ip = info.get('loadbalancerip')
                if user is not None and ip is not None:
                    if config.type == 'openstack' and info.get('privateip') == ip and k.external_network is not None\
                            and info.get('nets')[0]['net'] != k.external_network:
                        warning("Waiting for floating ip instead of a private ip...")
                        ip = None
                    else:
                        testcmd = common.ssh(name, user=user, ip=ip, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                                             tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                                             insecure=config.insecure, cmd='id -un', vmport=vmport,
                                             identityfile=identityfile, password=False)
                        if os.popen(testcmd).read().strip() != user:
                            warning("Gathered ip not functional yet...")
                            ip = None
            pprint("Waiting for vm to be accessible...")
            sleep(5)
            timeout += 5
            if waittimeout > 0 and timeout > waittimeout:
                error("Timeout waiting for vm to be accessible...")
                break
        sleep(5)
        oldoutput = ''
        timeout = 0
        while True:
            sshcmd = common.ssh(name, user=user, ip=ip, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                                vmport=vmport, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                                insecure=config.insecure, cmd=cmd, identityfile=identityfile, password=False)
            output = os.popen(sshcmd).read()
            if waitcommand is not None:
                if output != '':
                    print(output)
                    break
                else:
                    pprint("Waiting for waitcommand to succeed...")
            else:
                if 'kcli boot finished' in output or 'Ignition finished successfully' in output or\
                   'Finished Combustion' in output:
                    break
                output = output.replace(oldoutput, '')
                if not quiet:
                    print(output)
                oldoutput = output
            sleep(2)
            timeout += 2
            if waittimeout > 0 and timeout > waittimeout:
                error("Timeout waiting for waitcommand to execute...")
                break
        return True

    def clean_tempkey(self, name, identityfile=None):
        cmd = "sed -i '/temp-kcli-key/d' /home/*/.ssh/authorized_keys /root/.ssh/authorized_keys"
        k = self.k
        info = k.info(name)
        vmport = None
        ip = info.get('ip')
        if self.type == 'kubevirt':
            if k.access_mode == 'NodePort':
                vmport = info.get('nodeport')
                ip = k.node_host(name=info.get('host'))
            elif k.access_mode == 'LoadBalancer':
                ip = info.get('loadbalancerip')
        sshcmd = common.ssh(name, user='root', ip=ip, tunnel=self.tunnel, tunnelhost=self.tunnelhost, vmport=vmport,
                            tunnelport=self.tunnelport, tunneluser=self.tunneluser, insecure=self.insecure, cmd=cmd,
                            identityfile=identityfile, password=False)
        os.popen(sshcmd).read()

    def threaded_create_kube(self, cluster, kubetype, kube_overrides):
        cluster = kube_overrides.get('cluster') or cluster or f"my{kubetype}"
        ippool = kube_overrides.get('ippool') or kube_overrides.get('confpool')
        baremetalpool = kube_overrides.get('ippool') or kube_overrides.get('confpool')
        if ippool is not None:
            self.get_vip_from_confpool(ippool, cluster, kube_overrides)
        if baremetalpool is not None:
            self.get_baremetal_hosts_from_confpool(baremetalpool, cluster, kube_overrides)
        self.create_kube(cluster, kubetype, kube_overrides)

    def create_kube(self, cluster, kubetype, overrides={}):
        cluster = overrides.get('cluster') or cluster or f"my{kubetype}"
        if self.type == 'web' and self.k.localkube:
            return self.k.create_kube(cluster, kubetype, overrides)
        ippool = overrides.get('ippool') or overrides.get('confpool')
        baremetalpool = overrides.get('ippool') or overrides.get('confpool')
        if ippool is not None:
            self.get_vip_from_confpool(ippool, cluster, overrides)
        if baremetalpool is not None:
            self.get_baremetal_hosts_from_confpool(baremetalpool, cluster, overrides)
        if kubetype == 'openshift':
            result = self.create_kube_openshift(cluster, overrides)
        elif kubetype == 'openshift-sno':
            overrides['sno'] = True
            result = self.create_kube_openshift(cluster, overrides)
        elif kubetype == 'hypershift':
            result = self.create_kube_hypershift(cluster, overrides)
        elif kubetype == 'microshift':
            result = self.create_kube_microshift(cluster, overrides)
        elif kubetype == 'k3s':
            result = self.create_kube_k3s(cluster, overrides)
        elif kubetype == 'rke2':
            result = self.create_kube_rke2(cluster, overrides)
        elif kubetype == 'gke':
            result = self.create_kube_gke(cluster, overrides)
        elif kubetype == 'eks':
            result = self.create_kube_eks(cluster, overrides)
        elif kubetype == 'aks':
            result = self.create_kube_aks(cluster, overrides)
        else:
            result = self.create_kube_generic(cluster, overrides)
        return result

    def create_kube_aks(self, cluster, overrides={}):
        from kvirt.cluster import aks
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        return aks.create(self, cluster, overrides)

    def create_kube_eks(self, cluster, overrides={}):
        from kvirt.cluster import eks
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        return eks.create(self, cluster, overrides)

    def create_kube_generic(self, cluster, overrides={}):
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        return kubeadm.create(self, plandir, cluster, overrides)

    def create_kube_gke(self, cluster, overrides={}):
        from kvirt.cluster import gke
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        return gke.create(self, cluster, overrides)

    def create_kube_microshift(self, cluster, overrides={}):
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(microshift.create.__code__.co_filename)
        return microshift.create(self, plandir, cluster, overrides)

    def create_kube_k3s(self, cluster, overrides={}):
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(k3s.create.__code__.co_filename)
        return k3s.create(self, plandir, cluster, overrides)

    def create_kube_hypershift(self, cluster, overrides={}):
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(hypershift.create.__code__.co_filename)
        # dnsclient = overrides.get('dnsclient')
        # dnsconfig = Kconfig(client=dnsclient) if dnsclient is not None else None
        return hypershift.create(self, plandir, cluster, overrides)

    def create_kube_openshift(self, cluster, overrides={}):
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        dnsclient = overrides.get('dnsclient')
        dnsconfig = Kconfig(client=dnsclient) if dnsclient is not None else None
        return openshift.create(self, plandir, cluster, overrides, dnsconfig=dnsconfig)

    def create_kube_rke2(self, cluster, overrides={}):
        if container_mode():
            os.environ['PATH'] += ':/workdir'
        else:
            os.environ['PATH'] += ':%s' % os.getcwd()
        plandir = os.path.dirname(rke2.create.__code__.co_filename)
        return rke2.create(self, plandir, cluster, overrides)

    def delete_kube(self, cluster, overrides={}):
        k = self.k
        hypershift = overrides.get('kubetype', 'xxx') == 'hypershift'
        assisted = False
        aks = overrides.get('kubetype', 'xxx') == 'aks'
        eks = overrides.get('kubetype', 'xxx') == 'eks'
        gke = overrides.get('kubetype', 'xxx') == 'gke'
        domain = overrides.get('domain', 'karmalabs.corp')
        kubetype = overrides.get('kubetype', 'generic')
        dnsclient = None
        if self.type == 'web' and k.localkube:
            return k.delete_kube(cluster, kubetype, overrides=overrides)
        cluster = overrides.get('cluster', cluster)
        if cluster is None or cluster == '':
            default_clusters = {'generic': 'mykube', 'hypershift': 'myhypershift', 'openshift': 'myopenshift',
                                'k3s': 'myk3s', 'microshift': 'mymicroshift', 'rke2': 'myrke2', 'gke': 'mygke',
                                'eks': 'myeks', 'aks': 'myaks'}
            cluster = default_clusters[kubetype]
        clusterdata = {}
        clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
        if os.path.exists(clusterdir):
            parametersfile = f"{clusterdir}/kcli_parameters.yml"
            if os.path.exists(parametersfile):
                with open(parametersfile) as f:
                    clusterdata = yaml.safe_load(f)
                    kubetype = clusterdata.get('kubetype', 'generic')
                    if kubetype == 'hypershift':
                        hypershift = True
                        assisted = clusterdata.get('assisted', False)
                    domain = clusterdata.get('domain', domain)
                    dnsclient = clusterdata.get('dnsclient')
                    gke = kubetype == 'gke'
                    eks = kubetype == 'eks'
                    aks = kubetype == 'aks'
                    if 'client' in clusterdata and clusterdata['client'] != self.client:
                        self.__init__(client=clusterdata['client'])
                        k = self.k
        deleteclients = {self.client: k}
        vmclients = []
        vmclients_file = os.path.expanduser(f'~/.kcli/vmclients_{cluster}')
        if os.path.exists(vmclients_file):
            vmclients = yaml.safe_load(open(vmclients_file))
            os.remove(vmclients_file)
        if self.extraclients:
            deleteclients.update(self.extraclients)
        elif vmclients:
            deleteclients.update({cli: Kconfig(client=cli).k for cli in vmclients if cli != self.client})
        if hypershift:
            kubeconfigmgmt = f"{clusterdir}/kubeconfig.mgmt"
            if os.path.exists(f'{clusterdir}/bmcs.yml'):
                call(f'KUBECONFIG={kubeconfigmgmt} oc delete -f {clusterdir}/bmcs.yml', shell=True)
            call(f'KUBECONFIG={kubeconfigmgmt} oc delete -f {clusterdir}/autoapprovercron.yml', shell=True)
            call(f'KUBECONFIG={kubeconfigmgmt} oc delete -f {clusterdir}/nodepools.yaml', shell=True)
            call(f'KUBECONFIG={kubeconfigmgmt} oc delete -f {clusterdir}/hostedcluster.yaml', shell=True)
            if not assisted and ('baremetal_iso' in clusterdata or 'baremetal_hosts' in clusterdata):
                call(f'KUBECONFIG={kubeconfigmgmt} oc -n default delete all -l app=httpd-kcli', shell=True)
                call(f'KUBECONFIG={kubeconfigmgmt} oc -n default delete pvc httpd-kcli-pvc', shell=True)
            ingress_ip = clusterdata.get('ingress_ip')
            if self.type == 'kubevirt' and clusterdata.get('platform') is None and ingress_ip is None:
                call(f'KUBECONFIG={kubeconfigmgmt} oc -n {k.namespace} delete route {cluster}-ingress', shell=True)
        for hypervisor in deleteclients:
            c = deleteclients[hypervisor]
            for vm in sorted(c.list(), key=lambda x: x['name']):
                name = vm['name']
                dnsclient = vm.get('dnsclient') or dnsclient
                currentcluster = vm.get('kube')
                kubetype = vm.get('kubetype', 'generic')
                if currentcluster is not None and currentcluster == cluster:
                    if kubetype == 'gke':
                        gke = True
                        break
                    elif kubetype == 'eks':
                        eks = True
                        break
                    elif kubetype == 'aks':
                        aks = True
                        break
                    c.delete(name, snapshots=True)
                    common.delete_lastvm(name, self.client)
                    success(f"{name} deleted on {hypervisor}!")
        if self.type == 'kubevirt':
            if f"{cluster}-api" in k.list_services(k.namespace):
                k.delete_service(f"{cluster}-api", k.namespace)
            if f"{cluster}-ingress" in k.list_services(k.namespace):
                k.delete_service(f"{cluster}-ingress", k.namespace)
            try:
                call(f'oc delete -n {k.namespace} route {cluster}-ingress', shell=True)
            except:
                pass
        if self.type in ['aws', 'azure', 'gcp', 'ibm', 'hcloud'] and not gke and not eks and not aks:
            existing_lbs = [l[0] for l in self.list_loadbalancers() if l[0].endswith(cluster) and
                            (l[0].startswith('api') or l[0].startswith('apps'))]
            for lb in existing_lbs:
                self.delete_loadbalancer(lb, domain=domain)
            bucket = f"{cluster}-{domain}"
            if bucket in self.k.list_buckets():
                pprint(f"Deleting bucket {bucket}")
                k.delete_bucket(bucket)
            if self.type == 'aws' and cluster in k.list_instance_profiles():
                iam_role = clusterdata.get('role', cluster)
                try:
                    k.delete_instance_profile(cluster, iam_role)
                except:
                    pass
                try:
                    k.delete_role(iam_role)
                except:
                    pass
            if self.type == 'gcp' and kubetype == 'openshift' and os.path.exists(f'{clusterdir}/metadata.json'):
                cluster_id = yaml.safe_load(open(f'{clusterdir}/metadata.json'))['infraID']
                k.delete_service_accounts(cluster_id)
            if self.type in ['aws', 'gcp']:
                try:
                    self.k.delete_security_group(cluster)
                except:
                    pass
            if self.type == 'azure':
                try:
                    self.k.delete_identity(f'kcli-{cluster}')
                except:
                    pass
        elif dnsclient is not None:
            z = Kconfig(client=dnsclient).k
            z.delete_dns(f"api.{cluster}", domain)
            z.delete_dns(f"apps.{cluster}", domain)
        if gke:
            gcpclient = None
            if 'client' in clusterdata:
                gcpclient = clusterdata['client']
            elif self.type == 'gcp':
                gcpclient = self.client
            else:
                msg = "Deleting gke cluster requires to instantiate gcp provider"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            from kvirt.cluster import gke
            currentconfig = Kconfig(client=gcpclient).k if gcpclient != self.client else self
            zonal = clusterdata.get('zonal', True)
            gke.delete(currentconfig, cluster, zonal)
        elif eks:
            eksclient = None
            if 'client' in clusterdata:
                eksclient = clusterdata['client']
            elif self.type == 'aws':
                eksclient = self.client
            else:
                msg = "Deleting eks cluster requires to instantiate aws provider"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            from kvirt.cluster import eks
            currentconfig = Kconfig(client=eksclient).k if eksclient != self.client else self
            eks.delete(currentconfig, cluster)
        elif aks:
            aksclient = None
            if 'client' in clusterdata:
                aksclient = clusterdata['client']
            elif self.type == 'azure':
                aksclient = self.client
            else:
                msg = "Deleting aks cluster requires to instantiate azure provider"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            from kvirt.cluster import aks
            currentconfig = Kconfig(client=aksclient).k if aksclient != self.client else self
            aks.delete(currentconfig, cluster)
        for confpool in self.confpools:
            ip_reservations = self.confpools[confpool].get('ip_reservations', {})
            if cluster in ip_reservations:
                del ip_reservations[cluster]
                self.update_confpool(confpool, {'ip_reservations': ip_reservations})
            name_reservations = self.confpools[confpool].get('name_reservations', [])
            if cluster in name_reservations:
                name_reservations.remove(cluster)
                self.update_confpool(confpool, {'name_reservations': name_reservations})
            cluster_baremetal_reservations = self.confpools[confpool].get('cluster_baremetal_reservations', {})
            if cluster in cluster_baremetal_reservations:
                del cluster_baremetal_reservations[cluster]
                self.update_confpool(confpool, {'cluster_baremetal_reservations': cluster_baremetal_reservations})
        if os.path.exists(clusterdir):
            pprint(f"Deleting directory {clusterdir}")
            rmtree(clusterdir)
        return {'result': 'success'}

    def scale_kube(self, cluster, kubetype, overrides={}):
        if kubetype == 'generic':
            result = self.scale_kube_generic(cluster, overrides=overrides)
        elif kubetype == 'k3s':
            result = self.scale_kube_k3s(cluster, overrides=overrides)
        elif kubetype == 'openshift':
            result = self.scale_kube_openshift(cluster, overrides=overrides)
        elif kubetype == 'hypershift':
            result = self.scale_kube_hypershift(cluster, overrides=overrides)
        elif kubetype == 'rke2':
            result = self.scale_kube_rke2(cluster, overrides=overrides)
        elif kubetype == 'gke':
            result = self.scale_kube_gke(cluster, overrides=overrides)
        elif kubetype == 'eks':
            result = self.scale_kube_eks(cluster, overrides=overrides)
        elif kubetype == 'aks':
            result = self.scale_kube_aks(cluster, overrides=overrides)
        return result

    def scale_kube_aks(self, cluster, overrides={}):
        from kvirt.cluster import aks
        return aks.scale(self, cluster, overrides)

    def scale_kube_eks(self, cluster, overrides={}):
        from kvirt.cluster import eks
        return eks.scale(self, cluster, overrides)

    def scale_kube_generic(self, cluster, overrides={}):
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        return kubeadm.scale(self, plandir, cluster, overrides)

    def scale_kube_gke(self, cluster, overrides={}):
        from kvirt.cluster import gke
        return gke.scale(self, cluster, overrides)

    def scale_kube_hypershift(self, cluster, overrides={}):
        plandir = os.path.dirname(hypershift.create.__code__.co_filename)
        return hypershift.scale(self, plandir, cluster, overrides)

    def scale_kube_k3s(self, cluster, overrides={}):
        plandir = os.path.dirname(k3s.create.__code__.co_filename)
        return k3s.scale(self, plandir, cluster, overrides)

    def scale_kube_openshift(self, cluster, overrides={}):
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        return openshift.scale(self, plandir, cluster, overrides)

    def scale_kube_rke2(self, cluster, overrides={}):
        plandir = os.path.dirname(rke2.create.__code__.co_filename)
        return rke2.scale(self, plandir, cluster, overrides)

    def update_kube(self, cluster, _type, overrides={}, plan=None):
        overrides['skip_files_remediation'] = True
        overrides['scale'] = True
        clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
        planvms = []
        if plan is None:
            plan = cluster
        if _type == 'aks':
            self.scale_kube_aks(cluster, overrides=overrides)
            return
        if _type == 'eks':
            self.scale_kube_eks(cluster, overrides=overrides)
            return
        if _type == 'gke':
            self.scale_kube_gke(cluster, overrides=overrides)
            return
        if _type == 'generic':
            roles = ['ctlplanes', 'workers']
            plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        elif _type == 'k3s':
            plandir = os.path.dirname(k3s.create.__code__.co_filename)
            roles = ['bootstrap', 'workers'] if overrides.get('ctlplanes', 1) == 1 else ['bootstrap', 'ctlplanes',
                                                                                         'workers']
        elif _type == 'rke2':
            roles = ['ctlplanes', 'workers']
            plandir = os.path.dirname(rke2.create.__code__.co_filename)
        elif _type == 'hypershift':
            roles = ['workers']
            plandir = os.path.dirname(hypershift.create.__code__.co_filename)
        else:
            plandir = os.path.dirname(openshift.create.__code__.co_filename)
            roles = ['ctlplanes', 'workers']
            if self.type in ['aws', 'azure', 'gcp']:
                roles = [f'cloud_{role}' for role in roles]
        if overrides.get('workers', 0) == 0:
            del roles[-1]
        if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
            data = {'cluster': cluster, 'kube': cluster, 'kubetype': _type}
            with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
                installparam = yaml.safe_load(install)
                data.update(installparam)
                plan = installparam.get('plan', plan)
            data.update(overrides)
            with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
                yaml.safe_dump(data, paramfile)
        os.chdir(os.path.expanduser("~/.kcli"))
        for role in roles:
            pprint(f"Updating vms with {role} role")
            plandata = self.plan(plan, inputfile=f'{plandir}/{role}.yml', overrides=overrides, update=True)
            planvms.extend(plandata['newvms'] + plandata['existingvms'])
        existing_ctlplanes = len([v for v in planvms if v.startswith(f'{cluster}-ctlplane-')])
        existing_workers = len([v for v in planvms if v.startswith(f'{cluster}-worker-')])
        if data['ctlplanes'] != existing_ctlplanes or data['workers'] != existing_workers:
            os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
            binary = 'oc' if which('oc') is not None else 'kubectl'
            nodescmd = f'{binary} get node -o name'
            nodes = [n.strip().replace('node/', '') for n in os.popen(nodescmd).readlines()]
            for vm in self.k.list():
                vmname = vm['name']
                vmplan = vm.get('plan', 'kvirt')
                if vmplan == plan and vmname not in planvms:
                    pprint(f"Deleting vm {vmname}")
                    for node in nodes:
                        if node.split('.')[0] == vmname:
                            pprint(f"Deleting node {node} from your cluster")
                            call(f'{binary} delete node {node}', shell=True)
                            break
                    self.k.delete(vmname)

    def expose_plan(self, plan, inputfile=None, overrides={}, port=9000, pfmode=False, cluster=False, extras=False):
        inputfile = os.path.expanduser(inputfile)
        if not os.path.exists(inputfile):
            error("No input file found nor default kcli_plan.yml.Leaving....")
            sys.exit(1)
        pprint(f"Handling expose of plan with name {plan} and inputfile {inputfile}")
        kexposer = Kexposer(self, plan, inputfile, overrides=overrides, port=port, pfmode=pfmode, cluster=cluster,
                            extras=extras)
        kexposer.run()

    def create_openshift_iso(self, cluster, overrides={}, ignitionfile=None, installer=False, direct=False):
        metal_url = None
        iso_version = str(overrides.get('version', 'latest'))
        if not installer:
            if iso_version not in ['latest', 'pre-release'] and not iso_version.startswith('4.'):
                warning("Forcing live iso version to latest")
                iso_version = 'latest'
            elif iso_version.startswith('4.'):
                minor_version = iso_version.split('.')[1]
                if minor_version.isdigit() and int(minor_version) < 6:
                    metal_url = f"https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/{iso_version}/latest"
                    metal_url += "/rhcos-metal.x86_64.raw.gz"
                    warning("Embedding metal url in iso for target version and installing with a more recent iso")
                iso_version = 'latest'
        api_ip = overrides.get('api_ip')
        ignition_version = overrides.get('ignition_version',
                                         common.ignition_version("rhcos-%s" % iso_version.replace('.', '')))
        role = overrides.get('role', 'worker')
        iso = overrides.get('iso', True)
        domain = overrides.get('domain')
        if '.' in cluster:
            domain = '.'.join(cluster.split('.')[1:])
            pprint(f"Using domain {domain}")
            cluster = cluster.replace(f".{domain}", '')
        if cluster.startswith('api.'):
            cluster = cluster.replace("api.", '')
            pprint(f"Using cluster {cluster}")
        hosts_content = None
        finaldata = None
        if ignitionfile is not None:
            if not os.path.exists(ignitionfile):
                error(f"{ignitionfile} not found")
                sys.exit(1)
            finaldata = open(ignitionfile).read()
        else:
            ignitionfile = f"{role}.ign"
            if os.path.exists(ignitionfile):
                warning(f"Using existing {ignitionfile}")
                finaldata = open(ignitionfile).read()
            else:
                if api_ip is None:
                    try:
                        api_ip = socket.gethostbyname(f'api.{cluster}.{domain}')
                    except:
                        pass
                if api_ip is None:
                    if domain is None:
                        error("Couldn't figure out api_ip nor rely on dns since domain is not set")
                        sys.exit(1)
                    warning("Couldn't figure out api_ip. Relying on dns")
                    api_ip = f"api.{cluster}.{domain}"
                else:
                    hosts_content = "127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n"
                    hosts_content += "::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n"
                    hosts_content += f"{api_ip} api-int.{cluster}.{domain} api.{cluster}.{domain}"
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        with open("iso.ign", 'w') as f:
            full_name = f'{cluster}.{domain}' if domain is not None else cluster
            pprint(f"Writing file iso.ign for {role} in {full_name}")
            isodir = os.path.dirname(common.__file__)
            if finaldata is None:
                env = Environment(loader=FileSystemLoader(isodir), extensions=['jinja2.ext.do'], trim_blocks=True,
                                  lstrip_blocks=True)
                templ = env.get_template(os.path.basename("ignition.j2"))
                if hosts_content is not None:
                    hosts_content = base64.b64encode(hosts_content.encode()).decode("UTF-8")
                full_ip = api_ip
                if ':' in api_ip:
                    full_ip = f"[{api_ip}]"
                config_role = 'master' if role == 'ctlplane' else role
                ignition_url = f"http://{full_ip}:22624/config/{config_role}"
                finaldata = templ.render(ignition_url=ignition_url, hosts_content=hosts_content,
                                         ignition_version=ignition_version)
            if direct:
                f.write(finaldata)
            else:
                _files = [{"path": "/root/config.ign", "content": finaldata}]
                if os.path.exists('iso.sh'):
                    pprint("Using local iso.sh script")
                    isoscript = 'iso.sh'
                else:
                    isoscript = f'{plandir}/iso.sh'
                clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
                if os.path.exists(f'{clusterdir}/macs.txt') or os.path.exists('macs.txt'):
                    macsdir = f'{clusterdir}' if os.path.exists(clusterdir) else '.'
                    _files.append({"path": "/root/macs.txt", "origin": f'{macsdir}/macs.txt'})
                iso_overrides = {'scripts': [isoscript], 'files': _files, 'metal_url': metal_url, 'noname': True,
                                 'image': 'rhcos4000'}
                if metal_url is not None:
                    iso_overrides['need_network'] = True
                iso_overrides.update(overrides)
                if 'name' in overrides:
                    iso_name = overrides['name']
                    iso_overrides['noname'] = False
                else:
                    iso_name = 'autoinstaller'
                result = self.create_vm(iso_name, overrides=iso_overrides, onlyassets=True)
                if 'reason' in result:
                    error(result['reason'])
                else:
                    f.write(result['userdata'])
        if iso:
            if self.type not in ['kvm', 'fake', 'kubevirt', 'vsphere', 'openstack']:
                warning(f"Iso generation not supported on {self.type}")
            else:
                iso_pool = overrides.get('pool') or self.pool
                generate_rhcos_iso(self.k, f"{cluster}-{role}", iso_pool, version=iso_version, installer=installer)

    def create_openshift_disconnected(self, plan, overrides={}):
        data = overrides
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        cluster = data.get('cluster', 'myopenshift')
        upstream = data.get('upstream', False)
        version = data.get('version', 'stable')
        tag = data.get('tag', OPENSHIFT_TAG)
        pprint(f"Using version {version} and tag {tag}")
        disconnected_vm = f"{cluster}-disconnected"
        disconnected_reuse = data.get('disconnected_reuse', False)
        disconnected_sync = data.get('disconnected_sync', True)
        pprint(f"Deploying disconnected vm {disconnected_vm}")
        if disconnected_sync:
            pull_secret = pwd_path(data.get('pull_secret')) if not upstream else f"{plandir}/fake_pull.json"
            if not upstream:
                pull_secret = pwd_path(data.get('pull_secret', 'openshift_pull.json'))
            else:
                pull_secret = f"{plandir}/fake_pull.json"
            if not os.path.exists(pull_secret):
                error(f"Missing pull secret file {pull_secret}")
                sys.exit(1)
            data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
        disconnected_plan = f"{plan}-reuse" if disconnected_reuse else plan
        if version == 'ci' and 'disconnected_origin' not in overrides:
            reg = 'registry.build01.ci.openshift.org' if str(tag).startswith('ci-') else 'registry.ci.openshift.org'
            warning(f"Forcing disconnected_origin to {reg}")
            data['disconnected_origin'] = reg
        result = self.plan(disconnected_plan, inputfile=f'{plandir}/disconnected.yml', overrides=data)
        if result['result'] != 'success':
            sys.exit(1)
        name = data.get('disconnected_reuse_name') or cluster
        ip, vmport = _ssh_credentials(self.k, f'{name}-disconnected')[1:]
        if disconnected_sync:
            pprint("Use the following OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE")
            cmd = "cat /root/version.txt"
        else:
            pprint("Use the following disconnected_url")
            cmd = "cat /root/url.txt"
        sshcmd = ssh(name, ip=ip, user='root', tunnel=self.tunnel, tunnelhost=self.tunnelhost,
                     tunnelport=self.tunnelport, tunneluser=self.tunneluser, insecure=True, cmd=cmd, vmport=vmport)
        os.system(sshcmd)

    def handle_finishfiles(self, name, finishfiles, identityfile=None, vmclient=None):
        config = Kconfig(client=vmclient) if vmclient is not None else self
        k = config.k
        current_ip = common._ssh_credentials(k, name)[1]
        for finishfile in finishfiles:
            if isinstance(finishfile, str):
                destination = '.'
                source = finishfile if '/' in finishfile else f'/root/{finishfile}'
            elif isinstance(finishfile, dict) and 'origin' in finishfile and 'path' in finishfile:
                source, destination = finishfile.get('origin'), os.path.expanduser(finishfile.get('path', '.'))
            else:
                warning(f"Incorrect finishfile entry {finishfile}. Skipping")
                continue
            scpcmd = common.scp(name, ip=current_ip, user='root', source=source, destination=destination,
                                tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                                tunneluser=self.tunneluser, download=True, insecure=True, identityfile=identityfile)
            os.system(scpcmd)

    def handle_notifications(self, name, notifymethods=[], pushbullettoken=None, notifyscript=None, notifycmd=None,
                             slackchannel=None, slacktoken=None, mailserver=None, mailfrom=None, mailto=None,
                             cluster=False):
        _type = 'Cluster' if cluster else 'Vm'
        title = f"{_type} {name} on {self.client} report"
        cmds, mailcontent = [], None
        for notifymethod in sorted(notifymethods, reverse=True):
            if notifymethod == 'pushbullet':
                if pushbullettoken is None:
                    warning(f"Notification required for {name} but missing pushbullettoken")
                elif notifyscript is None and notifycmd is None:
                    continue
                else:
                    token = pushbullettoken
                    pbcmd = 'curl -su "%s:" -d type="note" -d body="`%s 2>&1`" -d title="%s" ' % (token,
                                                                                                  notifycmd,
                                                                                                  title)
                    pbcmd += 'https://api.pushbullet.com/v2/pushes'
                    cmds.append(pbcmd)
            elif notifymethod == 'slack':
                if slackchannel is None:
                    warning(f"Notification required for {name} but missing slack channel")
                elif slacktoken is None:
                    warning(f"Notification required for {name} but missing slacktoken")
                else:
                    slackcmd = f"info=`{notifycmd} 2>&1 | sed 's/\\x2/ /g'`;"
                    slackcmd += """curl -X POST -H 'Authorization: Bearer %s'
 -H 'Content-type: application/json; charset=utf-8'
 --data '{"channel":"%s","text":"%s","attachments": [{"text":"'"$info"'","fallback":"nothing",
"color":"#3AA3E3","attachment_type":"default"}]}' https://slack.com/api/chat.postMessage""" % (slacktoken,
                                                                                               slackchannel, title)
                    slackcmd = slackcmd.replace('\n', '')
                    cmds.append(slackcmd)
            elif notifymethod == 'mail':
                if mailserver is None:
                    warning(f"Notification required for {name} but missing mailserver")
                elif mailfrom is None:
                    warning(f"Notification required for {name} but missing mailfrom")
                elif not mailto:
                    warning(f"Notification required for {name} but missing mailto")
                else:
                    now = datetime.now()
                    now = now. strftime("%a,%d %b %Y %H:%M:%S")
                    tos = ','.join([f"<{to}>" for to in mailto])
                    mailcontent = f"From: {mailfrom} <{mailfrom}>\nTo: {tos}\nDate: {now}\nSubject: {title}"
                    mailcmd = []
                    if not cluster:
                        mailcmd.append('test -f /etc/debian_version && apt-get -y install curl')
                        mailcmd.append('echo "" >> /var/tmp/mail.txt')
                    mailcmd.append(f'{notifycmd} 2>&1 >> /var/tmp/mail.txt')
                    curlcmd = f"curl --silent --url smtp://{mailserver}:25 --mail-from {mailfrom}"
                    for address in mailto:
                        curlcmd += f" --mail-rcpt {address} "
                    if cluster:
                        mailcontent = ""
                        kubeconfig = f'/etc/kubernetes/kubeconfig.{name}'
                        curlcmd += f' -H "Subject: {title}" -H "From: {mailfrom} <{mailfrom}>"'
                        for address in mailto:
                            curlcmd += f' -H "To: {address} <{address}>"'
                        curlcmd += ' -F "=(;type=multipart/mixed" -F "=$(cat /var/tmp/mail.txt);type=text/plain"'
                        curlcmd += f' -F "file=@{kubeconfig};type=text/plain;encoder=base64" -F "=)"'
                    else:
                        curlcmd += " --upload-file /var/tmp/mail.txt"
                    mailcmd.append(curlcmd)
                    cmds.extend(mailcmd)
            else:
                error(f"Invalid method {notifymethod}")
        return cmds, mailcontent

    def handle_vm_result(self, name, profile, result, newvms, failedvms, asyncwaitvms, onlyassets=False, newassets=[],
                         vmclient=None):
        if 'result' in result and result['result'] == 'success':
            newvms.append(name)
        else:
            failedvms.append({'name': name, 'reason': result['reason']})
        start = profile.get('start', True)
        cloudinit = profile.get('cloudinit', True)
        asyncwait = profile.get('asyncwait', False)
        finishfiles = profile.get('finishfiles', [])
        if onlyassets:
            if 'userdata' in result:
                newassets.append(result['userdata'])
            else:
                error(result['reason'])
        if not asyncwait:
            return
        elif not start or not cloudinit or profile.get('image') is None:
            pprint(f"Skipping wait on {name}")
        else:
            waitcommand = profile.get('waitcommand')
            waittimeout = profile.get('waittimeout', 0)
            asyncwaitvm = {'name': name, 'finishfiles': finishfiles, 'waitcommand': waitcommand,
                           'waittimeout': waittimeout, 'vmclient': vmclient}
            asyncwaitvms.append(asyncwaitvm)

    def threaded_create_vm(self, name, profilename, currentoverrides, profile, z, plan, currentplandir, vmclient,
                           onfly, onlyassets, newvms, failedvms, asyncwaitvms, newassets):
        result = self.create_vm(name, profilename, overrides=currentoverrides, customprofile=profile, k=z,
                                plan=plan, basedir=currentplandir, client=vmclient, onfly=onfly,
                                onlyassets=onlyassets)
        if not onlyassets:
            common.handle_response(result, name, client=vmclient)
        self.handle_vm_result(name, profile, result=result, newvms=newvms, failedvms=failedvms,
                              asyncwaitvms=asyncwaitvms, onlyassets=onlyassets, newassets=newassets, vmclient=vmclient)

    def parse_files(self, name, files, basedir='.', onfly=None):
        if not files:
            return
        for index, fil in enumerate(files):
            if isinstance(fil, str):
                path = f"/root/{fil}"
                if basedir != '.':
                    origin = f"{basedir}/{path}"
                origin = fil
                content = None
                files[index] = {'path': path, 'origin': origin}
            elif isinstance(fil, dict):
                origin = fil.get('origin')
                content = fil.get('content')
                path = fil.get('path')
                if path is None:
                    if origin is not None:
                        files[index]['path'] = f"/root/{origin}"
                    else:
                        error(f"Incorrect entry {fil}.Leaving...")
                        sys.exit(1)
                elif not path.startswith('/'):
                    error(f"Incorrect path {path}.Leaving...")
                    sys.exit(1)
            else:
                return {'result': 'failure', 'reason': "Incorrect file entry"}
            if origin is not None:
                if onfly is not None and '~' not in origin:
                    destdir = basedir
                    if '/' in origin:
                        destdir = os.path.dirname(origin)
                        os.makedirs(destdir, exist_ok=True)
                    common.fetch(f"{onfly}/{origin}", destdir)
                origin = os.path.expanduser(origin)
                if not os.path.isabs(origin):
                    if isinstance(fil, dict) and fil.get('currentdir', False):
                        origin = f"{os.getcwd()}/{origin}"
                        files[index]['origin'] = origin
                    elif basedir != '.' and not origin.startswith('./') and not origin.startswith('/workdir/'):
                        origin = f"{basedir}/{origin}"
                        files[index]['origin'] = origin
                if not os.path.exists(origin):
                    return {'result': 'failure', 'reason': f"Origin file {origin} not found for {name}"}
            elif content is None:
                return {'result': 'failure', 'reason': f"Content of file {path} not found for {name}"}

    def prepend_input_dir(self, newfiles, inputdir):
        results = []
        for fic in newfiles:
            if isinstance(fic, str) and not os.path.isabs(fic):
                new_fic = f"{inputdir}/{fic}"
            elif isinstance(fic, dict) and 'origin' in fic and not os.path.isabs(os.path.expanduser(fic['origin'])):
                new_fic = fic.copy()
                new_fic['origin'] = f"{inputdir}/{fic['origin']}"
            else:
                new_fic = fic
            results.append(new_fic)
        return results

    def remediate_files(self, name, newfiles, overrides={}, inputdir='.'):
        updated_files = []
        ip, vmport = _ssh_credentials(self.k, name)[1:]
        if inputdir != '.':
            newfiles = self.prepend_input_dir(newfiles, inputdir)
        self.parse_files(name, newfiles)
        overrides_files = overrides.copy()
        overrides_files['name'] = name
        data = process_files(files=newfiles, overrides=overrides_files, remediate=True)
        datadirs = {}
        with TemporaryDirectory() as tmpdir:
            for index, entry in enumerate(data):
                destination = entry['path']
                pathdir = os.path.dirname(destination)
                if pathdir not in datadirs:
                    pathdircmd = f'ls -a {pathdir} 2>&1'
                    pathdircmd = ssh(name, ip=ip, user='root', tunnel=self.tunnel, tunnelhost=self.tunnelhost,
                                     tunnelport=self.tunnelport, tunneluser=self.tunneluser, insecure=True,
                                     cmd=pathdircmd, vmport=vmport)
                    pathdirfiles = os.popen(pathdircmd).readlines()
                    if len(pathdirfiles) == 1 and 'No such file or directory' in pathdirfiles[0]:
                        createdircmd = f'mkdir -p {pathdir}'
                        createdircmd = ssh(name, ip=ip, user='root', tunnel=self.tunnel, tunnelhost=self.tunnelhost,
                                           tunnelport=self.tunnelport, tunneluser=self.tunneluser, insecure=True,
                                           cmd=createdircmd, vmport=vmport)
                        os.popen(createdircmd)
                        pathdirfiles = []
                    else:
                        pathdirfiles = [x.strip() for x in pathdirfiles]
                    datadirs[pathdir] = pathdirfiles
                if os.path.basename(destination) not in datadirs[pathdir]:
                    pprint(f"Updating {destination} in {name}")
                    source = f"{tmpdir}/fic{index}"
                    with open(source, 'w') as f:
                        f.write(entry['content'])
                    scpcmd = scp(name, ip=ip, user='root', source=source, destination=destination, tunnel=self.tunnel,
                                 tunnelhost=self.tunnelhost, tunnelport=self.tunnelport, tunneluser=self.tunneluser,
                                 download=False, insecure=True, vmport=vmport)
                    os.system(scpcmd)
                    updated_files.append(destination)
        return updated_files

    def info_specific_plan(self, plan, quiet=False):
        if not quiet:
            pprint(f"Providing information about plan {plan}")
        k = self.k
        results = []
        for vm in k.list():
            if vm.get('plan', '') == plan:
                results.append(vm)
        return results

    def autoscale_cluster(self, kube, kubetype, workers, threshold, idle):
        if threshold > 9999:
            pprint(f"Skipping autoscaling up checks for cluster {kube} as per threshold {threshold}")
            return {'result': 'success', 'workers': workers}
        if idle < 1:
            pprint(f"Skipping autoscaling down checks for cluster {kube} as per idle {idle}")
            return {'result': 'success', 'workers': workers}
        pprint(f"Checking non scheduled pods count on cluster {kube}")
        selector = "!node-role.kubernetes.io/control-plane,node-role.kubernetes.io/worker"
        currentcmd = f"kubectl get node --selector='{selector}'"
        currentcmd += " | grep ' Ready'"
        workers = len(os.popen(currentcmd).readlines())
        pendingcmd = "kubectl get pods -A --field-selector=status.phase=Pending -o yaml"
        pending_pods = yaml.safe_load(os.popen(pendingcmd).read())['items']
        if len(pending_pods) > threshold:
            pprint(f"Triggering scaling up for cluster {kube} as there are {len(pending_pods)} pending pods")
            workers += 1
            pprint("Scaling up cluster {kube} to {workers} workers")
            result = self.scale_kube(kube, kubetype, overrides={'workers': workers})
            result['workers'] = workers
            return result
        nodes = {}
        currentcmd = "kubectl get pod -A -o yaml"
        allpods = yaml.safe_load(os.popen(currentcmd).read())['items']
        for pod in allpods:
            nodename = pod['spec']['nodeName']
            status = pod['status']['phase']
            if status != 'Running':
                continue
            if nodename not in nodes:
                nodes[nodename] = 1
            else:
                nodes[nodename] += 1
        todelete = 0
        for node in nodes:
            if nodes[node] < idle:
                pprint(f"node {node} to be removed since it only has the following pods: {nodes[node]}")
                todelete += 1
        if todelete > 0:
            pprint(f"Triggering scaling down for cluster {kube} as there are {todelete} idle nodes")
            workers = workers - todelete
            pprint(f"Scaling down cluster {kube} to {workers} workers")
            result = self.scale_kube(kube, kubetype, overrides={'workers': workers})
            result['workers'] = workers
            return result
        return {'result': 'success', 'workers': workers}

    def loop_autoscale_cluster(self, kube, kubetype, workers, threshold, idle):
        pprint(f"Starting with {workers} workers")
        if which('kubectl') is None:
            common.get_kubectl()
            os.environ['PATH'] += ':.'
        while True:
            selector = "!node-role.kubernetes.io/control-plane,node-role.kubernetes.io/worker"
            currentcmd = f"kubectl get node --selector='{selector}'"
            currentcmd += " | grep ' Ready'"
            currentnodes = os.popen(currentcmd).readlines()
            if len(currentnodes) != workers:
                pprint(f"Ongoing scaling operation on cluster {kube}")
            else:
                result = self.autoscale_cluster(kube, kubetype, workers, threshold, idle)
                if result['result'] != 'success':
                    return result
                else:
                    workers = result['workers']
                    pprint(f"Current workers number desired: {workers}")
            sleep(60)

    def threaded_web_console(self, port, name):
        console = Kminiconsole(config=self, port=port, name=name)
        console.run()

    def webconsole(self, name):
        port = get_free_port()
        t = threading.Thread(target=self.threaded_web_console, args=(port, name,))
        t.start()
        webbrowser.open(f"http://127.0.0.1:{port}", new=2, autoraise=True)

    def info_specific_aks(self, cluster):
        from kvirt.cluster.aks import info as aks_info
        return aks_info(self, cluster, self.debug)

    def info_specific_eks(self, cluster):
        from kvirt.cluster.eks import info as eks_info
        return eks_info(self, cluster, self.debug)

    def info_kube_aks(self, quiet, web=False):
        from kvirt.cluster import aks
        plandir = os.path.dirname(aks.create.__code__.co_filename)
        inputfile = f'{plandir}/fake.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)
        aks.info_service(self)

    def info_kube_eks(self, quiet, web=False):
        from kvirt.cluster import eks
        plandir = os.path.dirname(eks.create.__code__.co_filename)
        inputfile = f'{plandir}/fake.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)
        eks.info_service(self)

    def info_specific_gke(self, cluster):
        from kvirt.cluter.gke import info as gke_info
        return gke_info(self, cluster, self.debug)

    def info_kube_gke(self, quiet, web=False):
        from kvirt.cluster import gke
        plandir = os.path.dirname(gke.create.__code__.co_filename)
        inputfile = f'{plandir}/fake.yml'
        self.info_plan(inputfile, quiet=quiet, web=web)
        gke.info_service(self)
