#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gcp Provider Class
"""

from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined as undefined
from jinja2.exceptions import TemplateSyntaxError, TemplateError
from kvirt import common
from kvirt.common import pprint, error, warning
from kvirt.defaults import UBUNTUS, METADATA_FIELDS
from dateutil import parser as dateparser
from getpass import getuser
import googleapiclient.discovery
from google.cloud import dns
from netaddr import IPNetwork
import os
from time import sleep
import webbrowser
import yaml

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip']


class Kgcp(object):
    """

    """
    def __init__(self, debug=False, project="kubevirt-button", zone="europe-west1-b",
                 region='europe-west1'):
        self.conn = googleapiclient.discovery.build('compute', 'v1')
        self.project = project
        self.zone = zone
        self.region = region
        self.debug = debug
        return

    def _wait_for_operation(self, operation):
        selflink = operation['selfLink']
        operation = operation['name']
        conn = self.conn
        project = self.project
        done = False
        timeout = 0
        while not done:
            if timeout > 60:
                return
            if 'zone' in selflink:
                check = conn.zoneOperations().get(project=project, zone=self.zone, operation=operation).execute()
            elif 'region' in selflink:
                check = conn.regionOperations().get(project=project, region=self.region, operation=operation).execute()
            else:
                check = conn.globalOperations().get(project=project, operation=operation).execute()
            if check['status'] == 'DONE':
                done = True
            else:
                sleep(1)
                timeout += 1
        if 'httpErrorMessage' in check:
            httperror = check['httpErrorMessage']
            code = check['error']['errors'][0]["code"]
            message = check['error']['errors'][0]["message"]
            error("Got %s Code %s Error %s" % (httperror, code, message))
        return

    def close(self):
        return

    def exists(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.instances().get(zone=zone, project=project, instance=name).execute()
            return True
        except:
            return False

    def net_exists(self, name):
        conn = self.conn
        project = self.project
        try:
            conn.networks().get(project=project, network=name).execute()
        except:
            return False
        return True

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[],
               cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None,
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, alias=[], overrides={}, tags=[], storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False,
               metadata={}, securitygroups=[]):
        conn = self.conn
        project = self.project
        zone = self.zone
        region = self.region
        if flavor is None:
            if numcpus != 1 and numcpus % 2 != 0:
                return {'result': 'failure', 'reason': "Number of cpus is not even"}
            if memory != 512 and memory % 1024 != 0:
                return {'result': 'failure', 'reason': "Memory is not multiple of 1024"}
            if numcpus > 1 and memory < 2048:
                pprint("Rounding memory to 2048Mb as more than one cpu is used")
                memory = 2048
            machine_type = 'custom-%s-%s' % (numcpus, memory)
            if memory < 921.6:
                pprint("Rounding memory to 1024Mb")
                machine_type = 'f1-micro'
        else:
            machine_type = flavor
        machine_type = "zones/%s/machineTypes/%s" % (zone, machine_type)
        body = {'name': name, 'machineType': machine_type, 'networkInterfaces': []}
        foundnets = []
        for index, net in enumerate(nets):
            if isinstance(net, str):
                netname = net
                netpublic = True
                ip = None
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                ip = net.get('ip')
                alias = net.get('alias')
                netpublic = net.get('public', True)
            if ips and len(ips) > index and ips[index] is not None:
                ip = ips[index]
            if netname in foundnets:
                continue
            else:
                foundnets.append(netname)
            newnet = {'network': 'global/networks/%s' % netname}
            if netpublic and index == 0:
                newnet['accessConfigs'] = [{'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}]
            if netname != 'default':
                newnet['subnetwork'] = 'projects/%s/regions/%s/subnetworks/%s' % (project, region, netname)
            if ip is not None:
                newnet['networkIP'] = ip
            body['networkInterfaces'].append(newnet)
        body['disks'] = []
        for index, disk in enumerate(disks):
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
            newdisk = {'boot': False, 'autoDelete': True}
            if index == 0 and image is not None:
                image = self.__evaluate_image(image)
                imageproject = self.__get_image_project(image)
                if imageproject is not None:
                    image_response = conn.images().getFromFamily(project=imageproject, family=image).execute()
                else:
                    try:
                        image_response = conn.images().get(project=self.project, image=image).execute()
                    except:
                        return {'result': 'failure', 'reason': 'Issue with image %s' % image}
                src = image_response['selfLink']
                newdisk['initializeParams'] = {'sourceImage': src, 'diskSizeGb': disksize}
                newdisk['boot'] = True
            else:
                diskname = "%s-disk%s" % (name, index)
                diskpath = '/compute/v1/projects/%s/zones/%s/disks/%s' % (project, zone, diskname)
                info = {'sizeGb': disksize, 'sourceDisk': 'zones/%s/diskTypes/pd-standard' % zone, 'name': diskname}
                conn.disks().insert(zone=zone, project=project, body=info).execute()
                timeout = 0
                while True:
                    if timeout > 60:
                        return {'result': 'failure', 'reason': 'timeout waiting for disk %s to be ready' % diskname}
                    newstatus = conn.disks().get(zone=zone, project=project, disk=diskname).execute()
                    if newstatus['status'] == 'READY':
                        break
                    else:
                        timeout += 5
                        sleep(5)
                        pprint("Waiting for disk %s to be ready" % diskname)
                newdisk['source'] = diskpath
            body['disks'].append(newdisk)
        body['serviceAccounts'] = [{'email': 'default',
                                    'scopes': ['https://www.googleapis.com/auth/devstorage.read_write',
                                               'https://www.googleapis.com/auth/logging.write']}]
        body['metadata'] = {'items': []}
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            body['metadata']['items'].append({'key': entry, 'value': metadata[entry]})
        startup_script = ''
        sshdircreated = False
        if storemetadata and overrides:
            storedata = {'path': '/root/.metadata', 'content': yaml.dump(overrides, default_flow_style=False, indent=2)}
            if files:
                files.append(storedata)
            else:
                files = [storedata]
        for fil in files:
            if not isinstance(fil, dict):
                continue
            origin = fil.get('origin')
            path = fil.get('path')
            content = fil.get('content')
            render = fil.get('render', True)
            mode = fil.get('mode', '0600')
            permissions = fil.get('permissions', mode)
            if path is None:
                continue
            if path.startswith('/root/.ssh/') and not sshdircreated:
                startup_script += 'mkdir -p /root/.ssh\nchmod 700 /root/.ssh\n'
                sshdircreated = True
            if origin is not None:
                origin = os.path.expanduser(origin)
                if not os.path.exists(origin):
                    print("Skipping file %s as not found" % origin)
                    continue
                binary = True if '.' in origin and origin.split('.')[-1].lower() in binary_types else False
                if binary:
                    with open(origin, "rb") as f:
                        content = f.read().encode("base64")
                elif overrides and render:
                    basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                    env = Environment(loader=FileSystemLoader(basedir), undefined=undefined,
                                      extensions=['jinja2.ext.do'], trim_blocks=True, lstrip_blocks=True)
                    try:
                        templ = env.get_template(os.path.basename(origin))
                        newfile = templ.render(overrides)
                    except TemplateSyntaxError as e:
                        error("Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message))
                        os._exit(1)
                    except TemplateError as e:
                        error("Error rendering file %s. Got: %s" % (origin, e.message))
                        os._exit(1)
                    startup_script += "cat <<'EOF' >%s\n%s\nEOF\nchmod %s %s\n" % (path, newfile, permissions, path)
                else:
                    newfile = open(origin, 'r').read()
                    startup_script += "cat <<'EOF' >%s\n%s\nEOF\nchmod %s %s\n" % (path, newfile, permissions, path)
            elif content is not None:
                startup_script += "cat <<'EOF' >%s\n%s\nEOF\nchmod %s %s\n" % (path, content, permissions, path)
        if enableroot and image is not None:
            enablerootcmds = ['sed -i "s/.*PermitRootLogin.*/PermitRootLogin yes/" /etc/ssh/sshd_config',
                              'systemctl restart sshd']
            if not cmds:
                cmds = enablerootcmds
            else:
                cmds.extend(enablerootcmds)
        if cmds:
            for cmd in cmds:
                if cmd.startswith('#'):
                    continue
                else:
                    try:
                        newcmd = Environment(undefined=undefined).from_string(cmd).render(overrides)
                    except TemplateError as e:
                        error("Error rendering cmd %s. Got: %s" % (cmd, e.message))
                        os._exit(1)
                startup_script += '%s\n' % newcmd
        if startup_script != '':
            beginningcmd = 'test -f /root/.kcli_startup && exit 0\n'
            endcmd = 'touch /root/.kcli_startup\n'
            newval = {'key': 'startup-script', 'value': beginningcmd + startup_script + endcmd}
            body['metadata']['items'].append(newval)
        if not os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub"))\
                and not os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub"))\
                and not os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub"))\
                and not os.path.exists(os.path.expanduser("~/.kcli/id_dsa.pub")):
            print("neither id_rsa.pub or id_dsa public keys found in your .ssh or .kcli directory, you might have "
                  "trouble accessing the vm")
            homekey = None
        elif os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub")):
            homekey = open(os.path.expanduser("~/.ssh/id_rsa.pub")).read()
        elif os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub")):
            homekey = open(os.path.expanduser("~/.ssh/id_dsa.pub")).read()
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub")):
            homekey = open(os.path.expanduser("~/.kcli/id_rsa.pub")).read()
        else:
            homekey = open(os.path.expanduser("~/.kcli/id_dsa.pub")).read()
        if homekey is not None:
            keys = [homekey] + keys if keys is not None else [homekey]
        if keys is not None:
            user = common.get_user(image)
            if user == 'root':
                user = getuser()
            finalkeys = ["%s: %s" % (user, x) for x in keys]
            if enableroot:
                finalkeys.extend(["root: %s" % x for x in keys])
            keys = '\n'.join(finalkeys)
            newval = {'key': 'ssh-keys', 'value': keys}
            body['metadata']['items'].append(newval)
        if tags:
            body['tags'] = {'items': tags}
        if image is not None and common.needs_ignition(image):
            version = common.ignition_version(image)
            userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                       domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                       overrides=overrides, version=version, plan=plan, image=image)
            newval = {'key': 'user-data', 'value': userdata}
            body['metadata']['items'].append(newval)
        newval = {'key': 'serial-port-enable', 'value': 1}
        body['metadata']['items'].append(newval)
        if self.debug:
            print(body)
        if storemetadata and overrides:
            existingkeys = [entry['key'] for entry in body['metadata']['items']]
            for key in overrides:
                if key not in existingkeys:
                    newval = {'key': key, 'value': overrides[key]}
                    body['metadata']['items'].append(newval)
        try:
            conn.instances().insert(project=project, zone=zone, body=body).execute()
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        action = conn.instances().start(zone=zone, project=project, instance=name).execute()
        if action is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        else:
            return {'result': 'success'}

    def stop(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        action = conn.instances().stop(zone=zone, project=project, instance=name).execute()
        if action is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        else:
            return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        body = {'name': name, 'forceCreate': True}
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=base).execute()
            body['sourceDisk'] = vm['disks'][0]['source']
        except:
            try:
                disk = conn.images().get(project=project, image=base).execute()
                body['sourceImage'] = disk['selfLink']
            except:
                return {'result': 'failure', 'reason': "VM/disk %s not found" % name}
        if revert:
            body['licenses'] = ["projects/vm-options/global/licenses/enable-vmx"]
        conn.images().insert(project=project, body=body).execute()
        return {'result': 'success'}

    def restart(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.instances().reset(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        return {'result': 'success'}

    def report(self):
        resource = googleapiclient.discovery.build('cloudresourcemanager', 'v1')
        project = self.project
        zone = self.zone
        print("Project: %s" % project)
        projectinfo = resource.projects().get(projectId=project).execute()
        print("ProjectNumber: %s" % projectinfo['projectNumber'])
        print("Creation Time: %s" % projectinfo['createTime'])
        print("Zone: %s" % zone)
        return

    def status(self, name):
        status = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            status = vm['status']
        except:
            error("Vm %s not found" % name)
        return status

    def list(self):
        conn = self.conn
        project = self.project
        zone = self.zone
        vms = []
        results = conn.instances().list(project=project, zone=zone).execute()
        if 'items' not in results:
            return []
        for vm in results['items']:
            vms.append(self.info(vm['name'], vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        project = self.project
        zone = self.zone
        resource = googleapiclient.discovery.build('cloudresourcemanager', 'v1')
        projectinfo = resource.projects().get(projectId=project).execute()
        projectnumber = projectinfo['projectNumber']
        url = "%s/zones/%s/instances/%s?authuser=1&hl=en_US&projectNumber=%s" % (project, zone, name, projectnumber)
        url = "https://ssh.cloud.google.com/projects/%s" % url
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = "Open the following url:\n%s" % url if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint("Opening url: %s" % url)
            webbrowser.open(url, new=2, autoraise=True)
        return

    def serialconsole(self, name, web=False):
        project = self.project
        zone = self.zone
        user, ip = common._ssh_credentials(self, name)[:2]
        sshcommand = "ssh"
        identityfile = None
        if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        if identityfile is not None:
            sshcommand += " -i %s" % identityfile
        sshcommand = "%s -p 9600 %s.%s.%s.%s@ssh-serialport.googleapis.com" % (sshcommand, project, zone, name, user)
        if web:
            return sshcommand
        if self.debug:
            print(sshcommand)
        os.system(sshcommand)
        return

    def dnsinfo(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return None, None
        dnsclient, domain = None, None
        if 'items' in vm['metadata']:
            for data in vm['metadata']['items']:
                if data['key'] == 'dnsclient':
                    dnsclient = data['value']
                if data['key'] == 'domain':
                    domain = data['value']
        return dnsclient, domain

    def info(self, name, vm=None, debug=False):
        yamlinfo = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        if vm is None:
            try:
                vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            except:
                error("VM %s not found" % name)
                return {}
        yamlinfo['name'] = vm['name']
        yamlinfo['status'] = vm['status']
        machinetype = os.path.basename(vm['machineType'])
        yamlinfo['flavor'] = machinetype
        if 'custom' in machinetype:
            yamlinfo['cpus'], yamlinfo['memory'] = machinetype.split('-')[1:]
        yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        if 'accessConfigs' in vm['networkInterfaces'][0] and 'natIP'in vm['networkInterfaces'][0]['accessConfigs'][0]:
            yamlinfo['ip'] = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        source = os.path.basename(vm['disks'][0]['source'])
        source = conn.disks().get(zone=zone, project=self.project, disk=source).execute()
        if self.project in source['sourceImage']:
            yamlinfo['image'] = os.path.basename(source['sourceImage'])
        elif 'licenses' in vm['disks'][0]:
            yamlinfo['image'] = os.path.basename(vm['disks'][0]['licenses'][-1])
        if 'image' in yamlinfo:
            yamlinfo['user'] = common.get_user(yamlinfo['image'])
        yamlinfo['creationdate'] = dateparser.parse(vm['creationTimestamp']).strftime("%d-%m-%Y %H:%M")
        nets = []
        for interface in vm['networkInterfaces']:
            network = os.path.basename(interface['network'])
            device = interface['name']
            private_ip = interface['networkIP'] if 'networkIP' in interface else 'N/A'
            yamlinfo['private_ip'] = private_ip
            network_type = ''
            nets.append({'device': device, 'mac': private_ip, 'net': network, 'type': network_type})
        if nets:
            yamlinfo['nets'] = nets
        disks = []
        for index, disk in enumerate(vm['disks']):
            devname = disk['deviceName']
            diskname = os.path.basename(disk['source'])
            diskformat = disk['interface']
            drivertype = disk['type']
            path = os.path.basename(disk['source'])
            diskinfo = conn.disks().get(zone=zone, project=project, disk=diskname).execute()
            disksize = diskinfo['sizeGb']
            disks.append({'device': devname, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        if disks:
            yamlinfo['disks'] = disks
        if 'items' in vm['metadata']:
            for data in vm['metadata']['items']:
                yamlinfo[data['key']] = data['value']
        if 'tags' in vm and 'items' in vm['tags']:
            yamlinfo['tags'] = ','.join(vm['tags']['items'])
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def ip(self, name):
        ip = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            error("Vm %s not found" % name)
            return None
        if 'natIP' not in vm['networkInterfaces'][0]['accessConfigs'][0]:
            return None
        else:
            ip = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        return ip

    def internalip(self, name):
        ip = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            error("Vm %s not found" % name)
            return None
        if 'networkIP' not in vm['networkInterfaces'][0]:
            return None
        else:
            ip = vm['networkInterfaces'][0]['networkIP']
        return ip

    def volumes(self, iso=False):
        projects = ['centos-cloud', 'coreos-cloud', 'cos-cloud', 'debian-cloud', 'rhel-cloud', 'suse-cloud',
                    'ubuntu-os-cloud', self.project]
        conn = self.conn
        images = []
        for project in projects:
            results = conn.images().list(project=project).execute()
            if 'items' in results:
                for image in results['items']:
                    if project == self.project:
                        images.append(image['name'])
                    elif 'family' not in image:
                        continue
                    elif image['family'] not in images:
                        images.append(image['family'])
        return sorted(images)

    def delete(self, name, snapshots=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        domain = None
        if 'items' in vm['metadata']:
            for data in vm['metadata']['items']:
                if data['key'] == 'domain':
                    domain = data['value']
        if domain is not None:
            self.delete_dns(name, domain)
        conn.instances().delete(zone=zone, project=project, instance=name).execute()
        # try:
        #     firewall_name = "ssh-%s" % name
        #     operation = conn.firewalls().delete(project=project, firewall=firewall_name).execute()
        #     self._wait_for_operation(operation)
        # except Exception as e:
        #     pass
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error("VM %s not found" % name)
            return 1
        metadata = vm['metadata']['items'] if 'items' in vm['metadata'] else []
        found = False
        for entry in metadata:
            if entry['key'] == metatype:
                if append:
                    entry['value'] += ",%s" % metavalue
                else:
                    entry['value'] = metavalue
                found = True
                break
        if not found:
            metadata.append({"key": metatype, "value": metavalue})
        metadata_body = {"fingerprint": vm['metadata']['fingerprint'], "items": metadata}
        conn.instances().setMetadata(project=project, zone=zone, instance=name, body=metadata_body).execute()
        return 0

    def update_flavor(self, name, flavor):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error("Can't update flavor of VM %s while up" % name)
            return {'result': 'failure', 'reason': "VM %s up" % name}
        machinetype = os.path.basename(vm['machineType'])
        if machinetype == flavor:
            return {'result': 'success'}
        else:
            url = "https://www.googleapis.com/compute/v1/projects/%s/zones/%s/machineTypes/%s" % (project, zone, flavor)
            body = {"machineType": url}
            conn.instances().setMachineType(project=project, zone=zone, instance=name, body=body).execute()
        return {'result': 'success'}

    def update_memory(self, name, memory):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error("Can't update memory of VM %s while up" % name)
            return {'result': 'failure', 'reason': "VM %s up" % name}
        machinetype = os.path.basename(vm['machineType'])
        if 'custom' in machinetype:
            currentcpus, currentmemory = machinetype.split('-')[1:]
            if memory == currentmemory:
                return {'result': 'success'}
            url = "https://www.googleapis.com/compute/v1/projects/%s/zones/%s/machineTypes" % (project, zone)
            newmachinetype = "%s/custom-%s-%s" % (url, currentcpus, memory)
            body = {"machineType": newmachinetype}
            conn.instances().setMachineType(project=project, zone=zone, instance=name, body=body).execute()
        else:
            warning("No custom machine type found. Not updating memory of %s" % name)
        return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error("Can't update cpus of VM %s while up" % name)
            return {'result': 'failure', 'reason': "VM %s up" % name}
        machinetype = os.path.basename(vm['machineType'])
        if 'custom' in machinetype:
            currentcpus, currentmemory = machinetype.split('-')[1:]
            if numcpus == currentcpus:
                return {'result': 'success'}
            url = "https://www.googleapis.com/compute/v1/projects/%s/zones/%s/machineTypes" % (project, zone)
            newmachinetype = "%s/custom-%s-%s" % (url, numcpus, currentmemory)
            body = {"machineType": newmachinetype}
            conn.instances().setMachineType(project=project, zone=zone, instance=name, body=body).execute()
        else:
            warning("No custom machine type found. Not updating memory of %s" % name)
        return {'result': 'success'}

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        print("not implemented")
        return

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        numdisks = len(vm['disks']) + 1
        diskname = "%s-disk%s" % (name, numdisks)
        body = {'sizeGb': size, 'sourceDisk': 'zones/%s/diskTypes/pd-standard' % zone, 'name': diskname}
        conn.disks().insert(zone=zone, project=project, body=body).execute()
        timeout = 0
        while True:
            if timeout > 60:
                return {'result': 'failure', 'reason': 'timeout waiting for new disk to be ready'}
            newdisk = conn.disks().get(zone=zone, project=project, disk=diskname).execute()
            if newdisk['status'] == 'READY':
                break
            else:
                timeout += 5
                sleep(5)
                pprint("Waiting for disk to be ready")
        body = {'source': '/compute/v1/projects/%s/zones/%s/disks/%s' % (project, zone, diskname), 'autoDelete': True}
        conn.instances().attachDisk(zone=zone, project=project, instance=name, body=body).execute()
        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.disks().delete(zone=zone, project=project, disk=diskname).execute()
        except:
            return {'result': 'failure', 'reason': "Disk %s not found" % diskname}
        return

    def list_disks(self):
        disks = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        alldisks = conn.disks().list(zone=zone, project=project).execute()
        if 'items' in alldisks:
            for disk in alldisks['items']:
                if self.debug:
                    print(disk)
                diskname = disk['name']
                pool = os.path.basename(disk['type'])
                disks[diskname] = {'pool': pool, 'path': zone}
        return disks

    def add_nic(self, name, network):
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        print("not implemented")
        return

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")
        return

    def delete_image(self, image, pool=None):
        pprint("Deleting image %s" % image)
        conn = self.conn
        project = self.project
        try:
            operation = conn.images().delete(project=project, image=image).execute()
            self._wait_for_operation(operation)
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': 'Image %s not found' % image}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None):
        conn = self.conn
        project = self.project
        shortimage = os.path.basename(url).split('?')[0].replace('.tar.gz', '').replace('.', '-').replace('-', '.')
        if 'rhcos' in url:
            shortimage = "rhcos-%s" % shortimage
        pprint("Adding image %s" % shortimage)
        image_body = {'name': shortimage, 'licenses': ["projects/vm-options/global/licenses/enable-vmx"]}
        if url.endswith('tar.gz'):
            image_body['rawDisk'] = {'source': url}
        operation = conn.images().insert(project=project, body=image_body).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        conn = self.conn
        project = self.project
        region = self.region
        body = {'name': name, 'autoCreateSubnetworks': True if cidr is None else False}
        operation = conn.networks().insert(project=project, body=body).execute()
        networkpath = operation["targetLink"]
        self._wait_for_operation(operation)
        # sleep(20)
        if cidr is not None:
            try:
                IPNetwork(cidr)
            except:
                return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
            regionpath = "https://www.googleapis.com/compute/v1/projects/%s/regions/%s" % (project, region)
            subnet_body = {'name': name, "ipCidrRange": cidr, 'network': networkpath, "region": regionpath}
            operation = conn.subnetworks().insert(region=region, project=project, body=subnet_body).execute()
            self._wait_for_operation(operation)
        allowed = {"IPProtocol": "tcp", "ports": ["22"]}
        firewall_body = {'name': 'allow-ssh-%s' % name, 'network': 'global/networks/%s' % name,
                         'sourceRanges': ['0.0.0.0/0'], 'allowed': [allowed]}
        conn.firewalls().insert(project=project, body=firewall_body).execute()
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        conn = self.conn
        project = self.project
        region = self.region
        try:
            network = conn.networks().get(project=project, network=name).execute()
        except:
            return {'result': 'failure', 'reason': "Network %s not found" % name}
        if not network['autoCreateSubnetworks'] and 'subnetworks' in network:
            for subnet in network['subnetworks']:
                subnetwork = os.path.basename(subnet)
                operation = conn.subnetworks().delete(region=region, project=project, subnetwork=subnetwork).execute()
                self._wait_for_operation(operation)
        try:
            operation = conn.firewalls().delete(project=project, firewall='allow-ssh-%s' % name).execute()
            self._wait_for_operation(operation)
        except:
            pass
        operation = conn.networks().delete(project=project, network=name).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

# should return a dict of pool strings
    def list_pools(self):
        print("not implemented")
        return

    def list_networks(self):
        conn = self.conn
        project = self.project
        region = self.region
        nets = conn.networks().list(project=project).execute()
        if 'items' not in nets:
            return {}
        subnets = conn.subnetworks().list(region=region, project=project).execute()['items']
        networks = {}
        for net in nets['items']:
            if self.debug:
                print(net)
            networkname = net['name']
            cidr = net['IPv4Range'] if 'IPv4Range' in net else ''
            if 'subnetworks' in net:
                for subnet in net['subnetworks']:
                    subnetname = os.path.basename(subnet)
                    for sub in subnets:
                        if sub['name'] == subnetname:
                            cidr = sub['ipCidrRange']
                            break
            dhcp = True
            domainname = ''
            mode = ''
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
        return networks

    def list_subnets(self):
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        print("not implemented")
        return

    def network_ports(self, name):
        return []

    def vm_ports(self, name):
        return ['default']

    def get_pool_path(self, pool):
        print("not implemented")
        return

    def __get_image_project(self, image):
        if image.startswith('sles'):
            return 'suse-cloud'
        if image.startswith('ubuntu'):
            return 'ubuntu-os-cloud'
        elif any([image.startswith(s) for s in ['centos', 'coreos', 'cos', 'debian', 'rhel']]):
            project = image.split('-')[0]
            return "%s-cloud" % project
        else:
            return None

    def __evaluate_image(self, image):
        # image = image.lower()
        if 'CentOS-7' in image:
            return 'centos-7'
        elif 'debian-8' in image:
            return 'debian-8'
        elif 'debian-9' in image:
            return 'debian-9'
        elif 'rhel-guest-image-7' in image.lower() or 'rhel-server-7' in image.lower():
            return 'rhel-7'
        elif 'rhel-guest-image-8' in image.lower() or 'rhel-server-8' in image.lower():
            return 'rhel-8'
        elif [x for x in UBUNTUS if x in image.lower()]:
            return 'ubuntu-1804-lts'
        else:
            return image

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        if domain is None:
            domain = nets[0]
        internalip = None
        project = self.project
        zone = self.zone
        region = self.region
        client = dns.Client(project)
        cluster = None
        fqdn = "%s.%s" % (name, domain)
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace("%s." % name, '').replace("%s." % cluster, '')
        domain_name = domain.replace('.', '-')
        pprint("Assuming Domain name is %s..." % domain_name)
        dnszones = [z for z in client.list_zones() if z.name == domain_name]
        if not dnszones:
            error("Domain %s not found" % domain_name)
            return {'result': 'failure', 'reason': "Domain not found"}
        else:
            dnszone = dnszones[0]
        dnsentry = name if cluster is None else "%s.%s" % (name, cluster)
        entry = "%s.%s." % (dnsentry, domain)
        if cluster is not None and ('master' in name or 'worker' in name):
            counter = 0
            while counter != 100:
                internalip = self.internalip(name)
                if internalip is None:
                    sleep(5)
                    pprint("Waiting 5 seconds to grab internal ip and create DNS record for %s..." % name)
                    counter += 10
                else:
                    break
        if ip is None:
            net = nets[0]
            if isinstance(net, dict):
                ip = net.get('ip')
            if ip is None:
                counter = 0
                while counter != 100:
                    ip = self.ip(name)
                    if ip is None:
                        sleep(5)
                        pprint("Waiting 5 seconds to grab ip and create DNS record for %s..." % name)
                        counter += 10
                    else:
                        address_body = {"name": name, "address": ip}
                        self.conn.addresses().insert(project=project, region=region, body=address_body).execute()
                        network_interface = "nic0"
                        access_config_body = {"natIP": ip}
                        self.conn.instances().updateAccessConfig(project=project, zone=zone, instance=name,
                                                                 networkInterface=network_interface,
                                                                 body=access_config_body).execute()
                        break
        if ip is None:
            error("Couldn't assign DNS for %s" % name)
            return
        changes = dnszone.changes()
        dnsip = ip if internalip is None else internalip
        record_set = dnszone.resource_record_set(entry, 'A', 300, [dnsip])
        changes.add_record_set(record_set)
        if alias:
            for a in alias:
                if a == '*':
                    if cluster is not None and ('master' in name or 'worker' in name):
                        new = '*.apps.%s.%s.' % (cluster, domain)
                    else:
                        new = '*.%s.%s.' % (name, domain)
                    alias_record_set = dnszone.resource_record_set(new, 'A', 300, [ip])
                else:
                    new = '%s.%s.' % (a, domain) if '.' not in a else '%s.' % a
                    alias_record_set = dnszone.resource_record_set(new, 'CNAME', 300, [entry])
                changes.add_record_set(alias_record_set)
        if cluster is not None and 'master' in name and internalip is not None:
            etcd1 = "_etcd-server-ssl._tcp.%s.%s." % (cluster, domain)
            etcd2 = "etcd-%s.%s.%s." % (name[-1], cluster, domain)
            srventries = ["0 10 2380 %s" % (etcd2)]
            srvexist = False
            for entry in dnszone.list_resource_record_sets():
                if entry.name == etcd1:
                    srvexist = True
                    oldentry = entry
                    srventries = oldentry.rrdatas + srventries
            record_set = dnszone.resource_record_set(etcd2, 'A', 300, [internalip])
            changes.add_record_set(record_set)
            if srvexist:
                old_record_set = dnszone.resource_record_set(oldentry.name, oldentry.record_type, oldentry.ttl,
                                                             oldentry.rrdatas)
                changes.delete_record_set(old_record_set)
            record_set = dnszone.resource_record_set(etcd1, 'SRV', 300, srventries)
            changes.add_record_set(record_set)
        changes.create()
        return {'result': 'success'}

    def delete_dns(self, name, domain):
        project = self.project
        region = self.region
        client = dns.Client(project)
        cluster = None
        fqdn = "%s.%s" % (name, domain)
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace("%s." % name, '').replace("%s." % cluster, '')
        domain_name = domain.replace('.', '-')
        dnszones = [z for z in client.list_zones() if z.name == domain_name]
        if not dnszones:
            return
        else:
            dnszone = dnszones[0]
        dnsentry = name if cluster is None else "%s.%s" % (name, cluster)
        entry = "%s.%s." % (dnsentry, domain)
        changes = dnszone.changes()
        records = []
        # records = [record for record in dnszone.list_resource_record_sets() if entry in record.name
        #           or name in record.rrdata
        #           ('master-0' in name and record.name.endswith("%s.%s." % (cluster, domain)))]
        for record in dnszone.list_resource_record_sets():
            if entry in record.name or ('master-0' in name and record.name.endswith("%s.%s." % (cluster, domain))):
                records.append(record)
            else:
                for rrdata in record.rrdatas:
                    if name in rrdata:
                        records.append(record)
        if records:
            for record in records:
                record_set = dnszone.resource_record_set(record.name, record.record_type, record.ttl, record.rrdatas)
                changes.delete_record_set(record_set)
            changes.create()
        try:
            self.conn.addresses().delete(project=project, region=region, address=name).execute()
        except:
            pass
        return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        project = self.project
        client = dns.Client(project)
        domain_name = domain.replace('.', '-')
        dnszones = [z for z in client.list_zones() if z.name == domain_name]
        if dnszones:
            dnszone = dnszones[0]
            for record in dnszone.list_resource_record_sets():
                if record.record_type in ['SOA', 'NS']:
                    continue
                results.append([record.name, record.record_type, record.ttl, ','.join(record.rrdatas)])
        return results

    def flavors(self):
        conn = self.conn
        project = self.project
        zone = self.zone
        flavors = []
        results = conn.machineTypes().list(project=project, zone=zone).execute()
        if 'items' not in results:
            return []
        for flavor in results['items']:
            name = flavor['name']
            numcpus = flavor['guestCpus']
            memory = flavor['memoryMb']
            flavors.append([name, numcpus, memory])
        return flavors

    def export(self, name, image=None):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            status = vm['status']
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if status.lower() == 'running':
            return {'result': 'failure', 'reason': "VM %s up" % name}
        newname = image if image is not None else name
        description = "image based on %s" % name
        body = {'name': newname, 'forceCreate': True, 'description': description,
                'sourceDisk': vm['disks'][0]['source'], 'licenses': ["projects/vm-options/global/licenses/enable-vmx"]}
        conn.images().insert(project=project, body=body).execute()
        return {'result': 'success'}

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False):
        sane_name = name.replace('.', '-')
        ports = [int(port) for port in ports]
        conn = self.conn
        project = self.project
        zone = self.zone
        region = self.region
        instances = []
        vmpath = "https://www.googleapis.com/compute/v1/projects/%s/zones/%s/instances" % (project, zone)
        if vms:
            for vm in vms:
                update = self.update_metadata(vm, 'loadbalancer', name, append=True)
                if update == 0:
                    instances.append({"instance": "%s/%s" % (vmpath, vm)})
        if internal:
            health_check_body = {"checkIntervalSec": "10", "timeoutSec": "10", "unhealthyThreshold": 3,
                                 "healthyThreshold": 3, "name": sane_name, "type": "TCP"}
            health_check_body["tcpHealthCheck"] = {"port": checkport}
            pprint("Creating healthcheck %s" % name)
            operation = conn.healthChecks().insert(project=project, body=health_check_body).execute()
            healthurl = operation['targetLink']
            self._wait_for_operation(operation)
        else:
            health_check_body = {"checkIntervalSec": "10", "timeoutSec": "10", "unhealthyThreshold": 3,
                                 "healthyThreshold": 3, "name": sane_name, "port": checkport, "requestPath": checkpath}
            pprint("Creating http healthcheck %s" % name)
            operation = conn.httpHealthChecks().insert(project=project, body=health_check_body).execute()
            healthurl = operation['targetLink']
            self._wait_for_operation(operation)
        sane_name = name.replace('.', '-')
        if internal:
            instances_group_body = {"name": sane_name, "healthChecks": [healthurl]}
            pprint("Creating instances group %s" % sane_name)
            operation = conn.instanceGroups().insert(project=project, zone=zone, body=instances_group_body).execute()
            instances_group_url = operation['targetLink']
            self._wait_for_operation(operation)
            if instances:
                instances_body = {"instances": instances}
                operation = conn.instanceGroups().addInstances(project=project, zone=zone, instanceGroup=sane_name,
                                                               body=instances_body).execute()
                self._wait_for_operation(operation)
            backend_body = {"name": sane_name, "loadBalancingScheme": "INTERNAL",
                            "backends": [{"group": instances_group_url}],
                            "protocol": "TCP", "healthChecks": [healthurl]}
            pprint("Creating backend service %s" % sane_name)
            operation = conn.regionBackendServices().insert(project=project, region=region, body=backend_body).execute()
            backendurl = operation['targetLink']
            self._wait_for_operation(operation)
        else:
            target_pool_body = {"name": sane_name, "healthChecks": [healthurl]}
            pprint("Creating target pool %s" % sane_name)
            operation = conn.targetPools().insert(project=project, region=region, body=target_pool_body).execute()
            targeturl = operation['targetLink']
            self._wait_for_operation(operation)
            if instances:
                instances_body = {"instances": instances}
                operation = conn.targetPools().addInstance(project=project, region=region, targetPool=sane_name,
                                                           body=instances_body).execute()
                self._wait_for_operation(operation)
        address_body = {"name": sane_name}
        if domain is not None:
            address_body["description"] = domain
        if internal:
            address_body["addressType"] = 'INTERNAL'
        pprint("Creating address %s" % sane_name)
        operation = conn.addresses().insert(project=project, region=region, body=address_body).execute()
        ipurl = operation['targetLink']
        self._wait_for_operation(operation)
        ip = conn.addresses().get(project=project, region=region, address=sane_name).execute()['address']
        pprint("Using load balancer ip %s" % ip)
        self._wait_for_operation(operation)
        if internal:
            forwarding_name = sane_name
            forwarding_rule_body = {"IPAddress": ipurl, "name": forwarding_name}
            forwarding_rule_body["loadBalancingScheme"] = "INTERNAL"
            forwarding_rule_body["backendService"] = backendurl
            forwarding_rule_body["IPProtocol"] = "TCP"
            forwarding_rule_body["ports"] = ports
            pprint("Creating forwarding rule %s" % forwarding_name)
            operation = conn.forwardingRules().insert(project=project, region=region,
                                                      body=forwarding_rule_body).execute()
            self._wait_for_operation(operation)
        else:
            for port in ports:
                forwarding_name = "%s-%s" % (sane_name, port)
                forwarding_rule_body = {"IPAddress": ipurl, "name": forwarding_name}
                forwarding_rule_body["target"] = targeturl
                forwarding_rule_body["portRange"] = [port]
                pprint("Creating forwarding rule %s" % forwarding_name)
                operation = conn.forwardingRules().insert(project=project, region=region,
                                                          body=forwarding_rule_body).execute()
                self._wait_for_operation(operation)
        if not internal:
            firewall_body = {"name": sane_name, "direction": "INGRESS",
                             "allowed": [{"IPProtocol": "tcp", "ports": ports}]}
            pprint("Creating firewall rule %s" % sane_name)
            operation = conn.firewalls().insert(project=project, body=firewall_body).execute()
            self._wait_for_operation(operation)
        if domain is not None:
            self.reserve_dns(name, ip=ip, domain=domain, alias=alias)
        return {'result': 'success'}

    def delete_loadbalancer(self, name):
        name = name.replace('.', '-')
        conn = self.conn
        project = self.project
        zone = self.zone
        region = self.region
        firewall_rules = conn.firewalls().list(project=project).execute()
        if 'items' in firewall_rules:
            for firewall_rule in firewall_rules['items']:
                firewall_rule_name = firewall_rule['name']
                if firewall_rule_name == name:
                    pprint("Deleting firewall rule %s" % name)
                    operation = conn.firewalls().delete(project=project, firewall=name).execute()
                    self._wait_for_operation(operation)
        forwarding_rules = conn.forwardingRules().list(project=project, region=region).execute()
        if 'items' in forwarding_rules:
            for forwarding_rule in forwarding_rules['items']:
                forwarding_rule_name = forwarding_rule['name']
                if forwarding_rule_name == name or forwarding_rule_name.startswith('%s-' % name):
                    pprint("Deleting forwarding rule %s" % forwarding_rule_name)
                    operation = conn.forwardingRules().delete(project=project, region=region,
                                                              forwardingRule=forwarding_rule_name).execute()
                    self._wait_for_operation(operation)
        # addresses = conn.addresses().list(project=project, region=region).execute()
        # if 'items' in addresses:
        #     for address in addresses['items']:
        #         address_name = address['name']
        #         if address_name == name:
        #             pprint("Deleting address %s" % name)
        #             if '.' in address["description"]:
        #                 domain = address["description"]
        #                 self.delete_dns(name, domain=domain)
        #             operation = conn.addresses().delete(project=project, region=region, address=name).execute()
        #             self._wait_for_operation(operation)
        try:
            address = conn.addresses().get(project=project, region=region, address=name).execute()
            if '.' in address["description"]:
                domain = address["description"]
                self.delete_dns(name, domain=domain)
            pprint("Deleting address %s" % name)
            operation = conn.addresses().delete(project=project, region=region, address=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        targetpools = conn.targetPools().list(project=project, region=region).execute()
        if 'items' in targetpools:
            for targetpool in targetpools['items']:
                targetpool_name = targetpool['name']
                if targetpool_name == name:
                    if 'healthChecks' in targetpool:
                        healtchecks = [{'healthCheck': healthcheck} for healthcheck in targetpool['healthChecks']]
                        healtchecks_body = {"healthChecks": healtchecks}
                        if healtchecks:
                            operation = conn.targetPools().removeHealthCheck(project=project, region=region,
                                                                             targetPool=name,
                                                                             body=healtchecks_body).execute()
                            self._wait_for_operation(operation)
                            for healthcheck in targetpool['healthChecks']:
                                healthcheck_short = os.path.basename(healthcheck)
                                pprint("Deleting http healthcheck %s" % healthcheck_short)
                                operation = conn.httpHealthChecks().delete(project=project,
                                                                           httpHealthCheck=healthcheck_short).execute()
                                self._wait_for_operation(operation)
                    pprint("Deleting target pool %s" % name)
                    operation = conn.targetPools().delete(project=project, region=region, targetPool=name).execute()
                    self._wait_for_operation(operation)
        backendservices = conn.regionBackendServices().list(project=project, region=region).execute()
        healthchecks = []
        if 'items' in backendservices:
            for backendservice in backendservices['items']:
                backendservice_name = backendservice['name']
                if backendservice_name == name:
                    if 'healthChecks' in backendservice:
                        healtchecks = [{'healthCheck': healthcheck} for healthcheck in backendservice['healthChecks']]
                        healtchecks_body = {"healthChecks": healtchecks}
                        healthchecks = backendservice['healthChecks']
                    pprint("Waiting to make sure forwarding rule is gone")
                    sleep(10)
                    pprint("Deleting backend service %s" % name)
                    operation = conn.regionBackendServices().delete(project=project, region=region,
                                                                    backendService=name).execute()
                    self._wait_for_operation(operation)
                    for healthcheck in healthchecks:
                        healthcheck_short = os.path.basename(healthcheck)
                        pprint("Deleting healthcheck %s" % healthcheck_short)
                        operation = conn.healthChecks().delete(project=project, healthCheck=healthcheck_short).execute()
                        self._wait_for_operation(operation)
        instancegroups = conn.instanceGroups().list(project=project, zone=zone).execute()
        if 'items' in instancegroups:
            for instancegroup in instancegroups['items']:
                instancegroup_name = instancegroup['name']
                if instancegroup_name == name:
                    pprint("Deleting instance group %s" % name)
                    operation = conn.instanceGroups().delete(project=project, zone=zone, instanceGroup=name).execute()
                    self._wait_for_operation(operation)
        return {'result': 'success'}

    def list_loadbalancers(self):
        conn = self.conn
        project = self.project
        region = self.region
        results = []
        results1 = conn.globalForwardingRules().list(project=project).execute()
        results2 = conn.forwardingRules().list(project=project, region=region).execute()
        if 'items' in results1:
            for lb in results1['items']:
                name = lb['name']
                ip = lb['IPAddress']
                protocol = lb['IPProtocol']
                port = lb['port']
                target = os.path.basename(lb['target'])
                results.append([name, ip, protocol, port, target])
        if 'items' in results2:
            for lb in results2['items']:
                name = lb['name']
                ip = lb['IPAddress']
                protocol = lb['IPProtocol']
                port = lb['portRange'] if 'portRange' in lb else ','.join(lb['ports'])
                target = lb['target'] if 'target' in lb else lb['backendService']
                target = os.path.basename(target)
                results.append([name, ip, protocol, port, target])
        return results
