#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gcp Provider Class
"""

from jinja2 import Environment, FileSystemLoader
from kvirt import common
from dateutil import parser as dateparser
from getpass import getuser
import googleapiclient.discovery
from google.cloud import dns
from netaddr import IPNetwork
import os
from time import sleep

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
            common.pprint("Got %s Code %s Error %s" % (httperror, code, message), color='red')
        return

    def close(self):
        """

        :return:
        """
        return

    def exists(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.instances().get(zone=zone, project=project, instance=name).execute()
            return True
        except:
            return False

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        project = self.project
        try:
            conn.networks().get(project=project, network=name).execute()
        except:
            return False
        return True

    def disk_exists(self, pool, name):
        """

        :param pool:
        :param name:
        """
        print("not implemented")

    def create(self, name, virttype='kvm', profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[],
               numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}],
               disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[],
               ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[],
               enableroot=True, alias=[], overrides={}, tags={}, dnshost=None):
        """

        :param name:
        :param virttype:
        :param profile:
        :param flavor:
        :param plan:
        :param cpumodel:
        :param cpuflags:
        :param numcpus:
        :param memory:
        :param guestid:
        :param pool:
        :param template:
        :param disks:
        :param disksize:
        :param diskthin:
        :param diskinterface:
        :param nets:
        :param iso:
        :param vnc:
        :param cloudinit:
        :param reserveip:
        :param reservedns:
        :param reservehost:
        :param start:
        :param keys:
        :param cmds:
        :param ips:
        :param netmasks:
        :param gateway:
        :param nested:
        :param dns:
        :param domain:
        :param tunnel:
        :param files:
        :param enableroot:
        :param alias:
        :param overrides:
        :param tags:
        :return:
        """
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
                common.pprint("Rounding memory to 2048Mb as more than one cpu is used", color='blue')
                memory = 2048
            machine_type = 'custom-%s-%s' % (numcpus, memory)
            if memory < 921.6:
                common.pprint("Rounding memory to 1024Mb", color='blue')
                machine_type = 'f1-micro'
        else:
            machine_type = flavor
        machine_type = "zones/%s/machineTypes/%s" % (zone, machine_type)
        body = {'name': name, 'machineType': machine_type, 'networkInterfaces': []}
        foundnets = []
        for index, net in enumerate(nets):
            ip = None
            if isinstance(net, str):
                netname = net
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                if 'ip' in net:
                    ip = net['ip']
                if 'alias' in net:
                    alias = net['alias']
            if ips and len(ips) > index and ips[index] is not None:
                ip = ips[index]
            if netname in foundnets:
                continue
            else:
                foundnets.append(netname)
            newnet = {'network': 'global/networks/%s' % netname}
            if netname == 'default':
                newnet['accessConfigs'] = [{'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}]
            else:
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
            if index == 0 and template is not None:
                template = self.__evaluate_template(template)
                templateproject = self.__get_template_project(template)
                if templateproject is not None:
                    image_response = conn.images().getFromFamily(project=templateproject, family=template).execute()
                else:
                    try:
                        image_response = conn.images().get(project=self.project, image=template).execute()
                    except:
                        return {'result': 'failure', 'reason': 'Issue with template %s' % template}
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
                        common.pprint("Waiting for disk %s to be ready" % diskname, color='green')
                newdisk['source'] = diskpath
            body['disks'].append(newdisk)
        body['serviceAccounts'] = [{'email': 'default',
                                    'scopes': ['https://www.googleapis.com/auth/devstorage.read_write',
                                               'https://www.googleapis.com/auth/logging.write']}]
        body['metadata'] = {'items': []}
        startup_script = ''
        for fil in files:
            if not isinstance(fil, dict):
                continue
            origin = fil.get('origin')
            path = fil.get('path')
            content = fil.get('content')
            if origin is not None:
                origin = os.path.expanduser(origin)
                if not os.path.exists(origin):
                    print("Skipping file %s as not found" % origin)
                    continue
                binary = True if '.' in origin and origin.split('.')[-1].lower() in binary_types else False
                if binary:
                    with open(origin, "rb") as f:
                        content = f.read().encode("base64")
                elif overrides:
                    basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                    env = Environment(block_start_string='[%', block_end_string='%]',
                                      variable_start_string='[[', variable_end_string=']]',
                                      loader=FileSystemLoader(basedir))
                    templ = env.get_template(os.path.basename(origin))
                    newfile = templ.render(overrides)
                    startup_script += "cat <<'EOF' >%s\n%s\nEOF\n" % (path, newfile)
                else:
                    newfile = open(origin, 'r').read()
                    startup_script += "cat <<'EOF' >%s\n%s\nEOF\n" % (path, newfile)
            elif content is None:
                continue
        if enableroot and template is not None:
            user = common.get_user(template)
            enablerootcmds = ['sed -i "s/.*PermitRootLogin.*/PermitRootLogin yes/" /etc/ssh/sshd_config',
                              'systemctl restart sshd']
            if not cmds:
                cmds.extend(enablerootcmds)
            else:
                cmds = enablerootcmds
        if cmds:
            for cmd in cmds:
                if cmd.startswith('#'):
                    continue
                else:
                    newcmd = Environment(block_start_string='[%', block_end_string='%]',
                                         variable_start_string='[[',
                                         variable_end_string=']]').from_string(cmd).render(overrides)
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
            user = common.get_user(template)
            if user == 'root':
                user = getuser()
            finalkeys = ["%s: %s" % (user, x) for x in keys]
            if enableroot:
                finalkeys.extend(["root: %s" % x for x in keys])
            keys = '\n'.join(finalkeys)
            newval = {'key': 'ssh-keys', 'value': keys}
            body['metadata']['items'].append(newval)
        newval = {'key': 'plan', 'value': plan}
        body['metadata']['items'].append(newval)
        newval = {'key': 'profile', 'value': profile}
        body['metadata']['items'].append(newval)
        if tags:
            body['tags'] = {'items': tags}
        if reservedns:
            newval = {'key': 'domain', 'value': domain}
            body['metadata']['items'].append(newval)
        if template is not None and (template.startswith('coreos') or template.startswith('rhcos')):
            etcd = None
            userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                       domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                       overrides=overrides, etcd=etcd)
            newval = {'key': 'user-data', 'value': userdata}
            body['metadata']['items'].append(newval)
        newval = {'key': 'serial-port-enable', 'value': 1}
        body['metadata']['items'].append(newval)
        if dnshost is not None:
            newval = {'key': 'dnshost', 'value': dnshost}
            body['metadata']['items'].append(newval)
        if self.debug:
            print(body)
        conn.instances().insert(project=project, zone=zone, body=body).execute()
        if reservedns:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias)
        return {'result': 'success'}

    def start(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        project = self.project
        zone = self.zone
        action = conn.instances().start(zone=zone, project=project, instance=name).execute()
        if action is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        else:
            return {'result': 'success'}

    def stop(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        project = self.project
        zone = self.zone
        action = conn.instances().stop(zone=zone, project=project, instance=name).execute()
        if action is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        else:
            return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        """

        :param name:
        :param base:
        :param revert:
        :param delete:
        :param listing:
        :return:
        """
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
        """

        :param name:
        :return:
        """
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.instances().reset(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        return {'result': 'success'}

    def report(self):
        """

        :return:
        """
        # conn = self.conn
        project = self.project
        zone = self.zone
        # resource = googleapiclient.discovery.build('cloudresourcemanager', 'v1')
        # print(dir(resource.projects()))
        print("Project: %s" % project)
        print("Zone: %s" % zone)
        return

    def status(self, name):
        """

        :param name:
        :return:
        """
        status = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            status = vm['status']
        except:
            common.pprint("Vm %s not found" % name, color='red')
        return status

    def list(self):
        """

        :return:
        """
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

    def console(self, name, tunnel=False):
        """

        :param name:
        :param tunnel:
        :return:
        """
        print("not implemented")
        return

    def serialconsole(self, name):
        """

        :param name:
        :return:
        """
        project = self.project
        zone = self.zone
        user, ip = self._ssh_credentials(name)
        sshcommand = "ssh"
        identityfile = None
        if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        if identityfile is not None:
            sshcommand += " -i %s" % identityfile
        sshcommand = "%s -p 9600 %s.%s.%s.%s@ssh-serialport.googleapis.com" % (sshcommand, project, zone, name, user)
        if self.debug:
            print(sshcommand)
        os.system(sshcommand)
        return

    def dnsinfo(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            common.pprint("VM %s not found" % name, color='red')
            return None, None
        dnshost, domain = None, None
        if 'items' in vm['metadata']:
            for data in vm['metadata']['items']:
                if data['key'] == 'dnshost':
                    dnshost = data['value']
                if data['key'] == 'domain':
                    domain = data['value']
        return dnshost, domain

    def info(self, name, vm=None):
        """

        :param name:
        :param vm:
        :return:
        """
        yamlinfo = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        if vm is None:
            try:
                vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            except:
                common.pprint("VM %s not found" % name, color='red')
                return {}
        if self.debug:
            print(vm)
        yamlinfo['name'] = vm['name']
        yamlinfo['status'] = vm['status']
        machinetype = os.path.basename(vm['machineType'])
        yamlinfo['flavor'] = machinetype
        if 'custom' in machinetype:
            yamlinfo['cpus'], yamlinfo['memory'] = machinetype.split('-')[1:]
        yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        if 'natIP'in vm['networkInterfaces'][0]['accessConfigs'][0]:
            yamlinfo['ip'] = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        source = os.path.basename(vm['disks'][0]['source'])
        source = conn.disks().get(zone=zone, project=self.project, disk=source).execute()
        if self.project in source['sourceImage']:
            yamlinfo['template'] = os.path.basename(source['sourceImage'])
        elif 'licenses' in vm['disks'][0]:
            yamlinfo['template'] = os.path.basename(vm['disks'][0]['licenses'][-1])
        yamlinfo['creationdate'] = dateparser.parse(vm['creationTimestamp']).strftime("%d-%m-%Y %H:%M")
        nets = []
        for interface in vm['networkInterfaces']:
            network = os.path.basename(interface['network'])
            device = interface['name']
            mac = interface['networkIP']
            network_type = ''
            nets.append({'device': device, 'mac': mac, 'net': network, 'type': network_type})
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
                if data['key'] == 'plan':
                    yamlinfo['plan'] = data['value']
                if data['key'] == 'profile':
                    yamlinfo['profile'] = data['value']
                if data['key'] == 'loadbalancer':
                    yamlinfo['loadbalancer'] = data['value']
        if 'tags' in vm and 'items' in vm['tags']:
            yamlinfo['tags'] = ','.join(vm['tags']['items'])
        return yamlinfo

    def ip(self, name):
        """

        :param name:
        :return:
        """
        ip = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            common.pprint("Vm %s not found" % name, color='red')
            return None
        if 'natIP' not in vm['networkInterfaces'][0]['accessConfigs'][0]:
            return None
        else:
            ip = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        return ip

# should return a list of available templates, or isos ( if iso is set to True
    def volumes(self, iso=False):
        """

        :param iso:
        :return:
        """
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
        """

        :param name:
        :param snapshots:
        :return:
        """
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
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        """

        :param old:
        :param new:
        :param full:
        :param start:
        :return:
        """
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue):
        """

        :param name:
        :param metatype:
        :param metavalue:
        :return:
        """
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception as e:
            common.pprint("VM %s not found" % name)
            return 1
        metadata = vm['metadata']['items'] if 'items' in vm['metadata'] else []
        found = False
        for entry in metadata:
            if entry['key'] == metatype:
                entry['value'] = metavalue
                found = True
                break
        if not found:
            metadata.append({"key": metatype, "value": metavalue})
        metadata_body = {"fingerprint": vm['metadata']['fingerprint'], "items": metadata}
        conn.instances().setMetadata(project=project, zone=zone, instance=name, body=metadata_body).execute()
        return 0

    def update_memory(self, name, memory):
        """

        :param name:
        :param memory:
        :return:
        """
        print("not implemented")
        return

    def update_cpu(self, name, numcpus):
        """

        :param name:
        :param numcpus:
        :return:
        """
        print("not implemented")
        return

    def update_start(self, name, start=True):
        """

        :param name:
        :param start:
        :return:
        """
        print("not implemented")
        return

    def update_information(self, name, information):
        """

        :param name:
        :param information:
        :return:
        """
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        """

        :param name:
        :param iso:
        :return:
        """
        print("not implemented")
        return

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param template:
        :return:
        """
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param template:
        :param shareable:
        :param existing:
        :return:
        """
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
                common.pprint("Waiting for disk to be ready", color='green')
        body = {'source': '/compute/v1/projects/%s/zones/%s/disks/%s' % (project, zone, diskname), 'autoDelete': True}
        conn.instances().attachDisk(zone=zone, project=project, instance=name, body=body).execute()
        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None):
        """

        :param name:
        :param diskname:
        :param pool:
        :return:
        """
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.disks().delete(zone=zone, project=project, disk=diskname).execute()
        except Exception as e:
            print(e)
            return {'result': 'failure', 'reason': "Disk %s not found" % name}
        return

    def list_disks(self):
        """

        :return:
        """
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
        """

        :param name:
        :param network:
        :return:
        """
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        """

        :param name:
        :param interface:
        :return:
        """
        print("not implemented")
        return

    def _ssh_credentials(self, name):
        user, ip = None, None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            common.pprint("Vm %s not found" % name, color='red')
            os._exit(1)
        if 'natIP' in vm['networkInterfaces'][0]['accessConfigs'][0]:
            ip = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        template = os.path.basename(vm['disks'][0]['licenses'][-1])
        user = common.get_user(template)
        if user == 'root':
            user = getuser()
        return user, ip

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False,
            D=None):
        """

        :param name:
        :param user:
        :param local:
        :param remote:
        :param tunnel:
        :param insecure:
        :param cmd:
        :param X:
        :param Y:
        :param D:
        :return:
        """
        u, ip = self._ssh_credentials(name)
        if ip is None:
            return None
        if user is None:
            user = u
        sshcommand = common.ssh(name, ip=ip, host=None, hostuser=None, user=user,
                                local=local, remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, Y=Y, D=D,
                                debug=self.debug)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        """

        :param name:
        :param user:
        :param source:
        :param destination:
        :param tunnel:
        :param download:
        :param recursive:
        :return:
        """
        u, ip = self._ssh_credentials(name)
        scpcommand = common.scp(name, ip=ip, host=None, hostuser=None, user=u,
                                source=source, destination=destination, recursive=recursive, tunnel=tunnel,
                                debug=self.debug, download=False)
        return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        """

        :param name:
        :param poolpath:
        :param pooltype:
        :param user:
        :param thinpool:
        :return:
        """
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        """

        :param image:
        :param pool:
        :param short:
        :param cmd:
        :param name:
        :param size:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None, vlan=None):
        """

        :param name:
        :param cidr:
        :param dhcp:
        :param nat:
        :param domain:
        :param plan:
        :param pxe:
        :param vlan:
        :return:
        """
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
        """

        :param name:
        :param cidr:
        :return:
        """
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
        """

        :return:
        """
        print("not implemented")
        return

    def list_networks(self):
        """

        :return:
        """
        conn = self.conn
        project = self.project
        region = self.region
        nets = conn.networks().list(project=project).execute()
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
        """

        :return:
        """
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        """

        :param name:
        :param full:
        :return:
        """
        print("not implemented")
        return

    def network_ports(self, name):
        """

        :param name:
        :return:
        """
        return []

    def vm_ports(self, name):
        """

        :param name:
        :return:
        """
        return ['default']

# returns the path of the pool, if it makes sense. used by kcli list --pools
    def get_pool_path(self, pool):
        """

        :param pool:
        :return:
        """
        print("not implemented")
        return

    def __get_template_project(self, template):
        if template.startswith('sles'):
            return 'suse-cloud'
        if template.startswith('ubuntu'):
            return 'ubuntu-os-cloud'
        elif any([template.startswith(s) for s in ['centos', 'coreos', 'cos', 'debian', 'rhel']]):
            project = template.split('-')[0]
            return "%s-cloud" % project
        else:
            return None

    def __evaluate_template(self, template):
        # template = template.lower()
        if 'CentOS-7' in template:
            return 'centos-7'
        elif 'debian-8' in template:
            return 'debian-8'
        elif 'debian-9' in template:
            return 'debian-9'
        elif 'rhel-guest-image-7' in template.lower() or 'rhel-server-7' in template.lower():
            return 'rhel-7'
        elif [x for x in common.ubuntus if x in template.lower()]:
            return 'ubuntu-1804-lts'
        else:
            return template

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False):
        """

        :param name:
        :param nets:
        :param domain:
        :param ip:
        :param alias:
        :param force:
        :return:
        """
        project = self.project
        zone = self.zone
        client = dns.Client(project)
        domain_name = domain.replace('.', '-')
        common.pprint("Assuming Domain name is %s..." % domain_name, color='green')
        zones = [z for z in client.list_zones() if z.name == domain_name]
        if not zones:
            common.pprint("Domain %s not found" % domain_name, color='red')
            return {'result': 'failure', 'reason': "Domain not found"}
        else:
            zone = zones[0]
        # zone = client.zone(domain_name)
        # if not zone.exists():
        #     common.pprint("Domain %s not found" % domain_name, color='red')
        #    return {'result': 'failure', 'reason': "Domain not found"}
        entry = "%s.%s." % (name, domain)
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
                        print("Waiting 5 seconds to grab ip and create DNS record...")
                        counter += 10
                    else:
                        break
        if ip is None:
            print("Couldn't assign DNS")
            return
        changes = zone.changes()
        record_set = zone.resource_record_set(entry, 'A', 300, [ip])
        changes.add_record_set(record_set)
        if alias:
            for a in alias:
                if a == '*':
                    new = '*.%s.%s.' % (name, domain)
                    record_set = zone.resource_record_set(new, 'A', 300, [ip])
                else:
                    new = '%s.%s.' % (a, domain) if '.' not in a else '%s.' % a
                    record_set = zone.resource_record_set(new, 'CNAME', 300, [entry])
                changes.add_record_set(record_set)
        changes.create()
        return {'result': 'success'}

    def delete_dns(self, name, domain):
        """

        :param name:
        :param domain:
        :return:
        """
        project = self.project
        zone = self.zone
        client = dns.Client(project)
        domain_name = domain.replace('.', '-')
        zones = [z for z in client.list_zones() if z.name == domain_name]
        if not zones:
            return
        else:
            zone = zones[0]
        # zone = client.zone(domain_name)
        #
        # if not zone.exists():
        #    return
        entry = "%s.%s." % (name, domain)
        changes = zone.changes()
        records = [record for record in zone.list_resource_record_sets() if entry in record.name]
        if records:
            for record in records:
                record_set = zone.resource_record_set(record.name, record.record_type, record.ttl, record.rrdatas)
                changes.delete_record_set(record_set)
            changes.create()
        return {'result': 'success'}

    def flavors(self):
        """

        :return:
        """
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

    def export(self, name, template=None):
        """

        :param name:
        :param template:
        :return:
        """
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
        newname = template if template is not None else name
        description = "template based on %s" % name
        body = {'name': newname, 'forceCreate': True, 'description': description,
                'sourceDisk': vm['disks'][0]['source'], 'licenses': ["projects/vm-options/global/licenses/enable-vmx"]}
        conn.images().insert(project=project, body=body).execute()
        return {'result': 'success'}

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None):
        port = int(ports[0])
        if len(ports) > 1:
            common.pprint("Only deploying for first port %s of the list" % port, color='blue')
        protocols = {80: 'HTTP', 8080: 'HTTP', 443: 'HTTPS'}
        protocol = protocols[port] if port in protocols else 'TCP'
        conn = self.conn
        project = self.project
        zone = self.zone
        region = self.region
        instances = []
        vmpath = "https://www.googleapis.com/compute/v1/projects/%s/zones/%s/instances" % (project, zone)
        if vms:
            for vm in vms:
                update = self.update_metadata(vm, 'loadbalancer', name)
                if update == 0:
                    instances.append({"instance": "%s/%s" % (vmpath, vm)})
        health_check_body = {"checkIntervalSec": "10", "timeoutSec": "10", "unhealthyThreshold": 3,
                             "healthyThreshold": 3, "type": protocol, "name": name}
        newcheck = {"port": port}
        if protocol == 'TCP':
            health_check_body["tcpHealthCheck"] = newcheck
            operation = conn.healthChecks().insert(project=project, body=health_check_body).execute()
            healthurl = operation['targetLink']
            self._wait_for_operation(operation)
            instance_group_body = {"name": name, "namedPorts": [{"name": "%s-%d" % (name, port), "port": port}]}
            operation = conn.instanceGroups().insert(project=project, zone=zone, body=instance_group_body).execute()
            instancegroupurl = operation['targetLink']
            self._wait_for_operation(operation)
            if instances:
                instances_body = {"instances": instances}
                operation = conn.instanceGroups().addInstances(project=project, zone=zone, instanceGroup=name,
                                                               body=instances_body).execute()
                self._wait_for_operation(operation)
            backend_body = {"healthChecks": [healthurl], "sessionAffinity": 'CLIENT_IP', "protocol": protocol,
                            "port-name": "%s-%d" % (name, port), "name": name,
                            "backends": [{"group": instancegroupurl}]}
            for port in ports:
                backend_body
            operation = conn.backendServices().insert(project=project, body=backend_body).execute()
            backendurl = operation['targetLink']
            self._wait_for_operation(operation)
            target_tcp_proxy_body = {"service": backendurl, "proxyHeader": "NONE", "name": name}
            operation = conn.targetTcpProxies().insert(project=project, body=target_tcp_proxy_body).execute()
            targeturl = operation['targetLink']
            self._wait_for_operation(operation)
        else:
            newcheck["requestPath"] = checkpath
            health_check_body["httpHealthCheck"] = newcheck
            operation = conn.httpHealthChecks().insert(project=project, body=health_check_body).execute()
            healthurl = operation['targetLink']
            self._wait_for_operation(operation)
            target_pool_body = {"name": name, "healthChecks": [healthurl]}
            operation = conn.targetPools().insert(project=project, region=region, body=target_pool_body).execute()
            targeturl = operation['targetLink']
            self._wait_for_operation(operation)
            if instances:
                instances_body = {"instances": instances}
                operation = conn.targetPools().addInstance(project=project, region=region, targetPool=name,
                                                           body=instances_body).execute()
                self._wait_for_operation(operation)
        if protocol == 'TCP':
            address_body = {"name": name, "ipVersion": "IPV4"}
            if domain is not None:
                address_body["description"] = domain
            operation = conn.globalAddresses().insert(project=project, body=address_body).execute()
            ipurl = operation['targetLink']
            self._wait_for_operation(operation)
            ip = conn.globalAddresses().get(project=project, address=name).execute()['address']
            common.pprint("Using load balancer ip %s" % ip, color='green')
            self._wait_for_operation(operation)
            forwarding_rule_body = {"IPAddress": ipurl, "target": targeturl, "portRange": port, "name": name}
            operation = conn.globalForwardingRules().insert(project=project, body=forwarding_rule_body).execute()
        else:
            address_body = {"name": name}
            if domain is not None:
                address_body["description"] = domain
            operation = conn.addresses().insert(project=project, region=region, body=address_body).execute()
            ipurl = operation['targetLink']
            self._wait_for_operation(operation)
            ip = conn.addresses().get(project=project, region=region, address=name).execute()['address']
            common.pprint("Using load balancer ip %s" % ip, color='green')
            self._wait_for_operation(operation)
            forwarding_rule_body = {"IPAddress": ipurl, "target": targeturl, "portRange": port, "name": name}
            operation = conn.forwardingRules().insert(project=project, region=region,
                                                      body=forwarding_rule_body).execute()
        self._wait_for_operation(operation)
        firewall_body = {"name": name, "direction": "INGRESS", "allowed": [{"IPProtocol": "tcp", "ports": [port]}]}
        operation = conn.firewalls().insert(project=project, body=firewall_body).execute()
        self._wait_for_operation(operation)
        if domain is not None:
            self.reserve_dns(name, ip=ip, domain=domain)
        return {'result': 'success'}

    def delete_loadbalancer(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        region = self.region
        try:
            operation = conn.firewalls().delete(project=project, firewall=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.globalForwardingRules().delete(project=project, forwardingRule=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.forwardingRules().delete(project=project, region=region, forwardingRule=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            address = conn.globalAddresses().get(project=project, address=name).execute()
            if '.' in address["description"]:
                domain = address["description"]
                self.delete_dns(name, domain=domain)
            operation = conn.globalAddresses().delete(project=project, address=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            address = conn.addresses().get(project=project, region=region, address=name).execute()
            if '.' in address["description"]:
                domain = address["description"]
                self.delete_dns(name, domain=domain)
            operation = conn.addresses().delete(project=project, region=region, address=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.targetTcpProxies().delete(project=project, targetTcpProxy=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.backendServices().delete(project=project, backendService=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.instanceGroups().delete(project=project, zone=zone, instanceGroup=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.targetPools().delete(project=project, region=region, targetPool=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.healthChecks().delete(project=project, healthCheck=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        try:
            operation = conn.httpHealthChecks().delete(project=project, httpHealthCheck=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
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
                port = lb['portRange']
                target = os.path.basename(lb['target'])
                results.append([name, ip, protocol, port, target])
        return results
