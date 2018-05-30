#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Interacts with google compute engine
"""

from jinja2 import Environment, FileSystemLoader
from kvirt import common
from dateutil import parser as dateparser
import googleapiclient.discovery
import os
import time

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip']


# your base class __init__ needs to define the conn attribute and set it to None when backend cannot be reached
# it should also set debug from the debug variable passed in kcli client
class Kgcloud(object):
    def __init__(self, host='127.0.0.1', port=None, user='root', debug=False,
                 project="kubevirt-button", zone="europe-west1-b", region='europe-west1'):
        if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
            common.pprint("set GOOGLE_APPLICATION_CREDENTIALS variable.Leaving...", color='red')
            self.conn = None
        else:
            self.conn = googleapiclient.discovery.build('compute', 'v1')
        self.project = project
        self.zone = zone
        self.region = region
        self.user = user
        self.host = host
        self.port = port
        self.debug = debug
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
        print("not implemented")
        return

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype='kvm', profile='', plan='kvirt', cpumodel='Westmere', cpuflags=[], numcpus=2,
               memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10,
               diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True,
               reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[],
               ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[],
               enableroot=True, alias=[], overrides={}, tags={}):
        conn = self.conn
        project = self.project
        zone = self.zone
        region = self.region
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
        machine_type = "zones/%s/machineTypes/%s" % (zone, machine_type)
        body = {'name': name, 'machineType': machine_type}
        body['disks'] = []
        for index, disk in enumerate(disks):
            newdisk = {'boot': False, 'autoDelete': True}
            if index == 0 and template is not None:
                template = self.__evaluate_template(template)
                templateproject = self.__get_template_project(template)
                if templateproject is not None:
                    image_response = conn.images().getFromFamily(project=templateproject, family=template).execute()
                else:
                    image_response = conn.images().get(project=self.project, image=template).execute()
                src = image_response['selfLink']
                newdisk['initializeParams'] = {'sourceImage': src}
                newdisk['boot'] = True
            else:
                if isinstance(disk, int):
                    disksize = disk
                elif isinstance(disk, dict):
                    disksize = disk.get('size', '10')
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
                        time.sleep(5)
                        common.pprint("Waiting for disk %s to be ready" % diskname, color='green')
                newdisk['source'] = diskpath
            body['disks'].append(newdisk)
        body['networkInterfaces'] = []
        foundnets = []
        for net in nets:
            if isinstance(net, str):
                netname = net
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
            if netname in foundnets:
                continue
            else:
                foundnets.append(netname)
            newnet = {'network': 'global/networks/%s' % netname}
            if netname == 'default':
                newnet['accessConfigs'] = [{'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}]
            else:
                newnet['subnetwork'] = 'projects/%s/regions/%s/subnetworks/%s' % (project, region, netname)
            body['networkInterfaces'].append(newnet)
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
                    startup_script += "echo '%s' > %s\n" % (newfile, path)
                else:
                    newfile = open(origin, 'r').read()
                    startup_script += "echo '%s' > %s\n" % (newfile, path)
            elif content is None:
                continue
        if cmds:
            for cmd in cmds:
                if cmd.startswith('#'):
                    continue
                else:
                    newcmd = Environment(block_start_string='[%', block_end_string='%]',
                                         variable_start_string='[[',
                                         variable_end_string=']]').from_string(cmd).render(overrides)
                startup_script += '%s\n' % newcmd
            newval = {'key': 'startup-script', 'value': startup_script}
            body['metadata']['items'].append(newval)
        if not os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME'])\
                and not os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
            print("neither id_rsa.pub or id_dsa public keys found in your .ssh directory, you might have trouble "
                  "accessing the vm")
        elif os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
            homekey = open("%s/.ssh/id_rsa.pub" % os.environ['HOME']).read()
        else:
            homekey = open("%s/.ssh/id_dsa.pub" % os.environ['HOME']).read()
        keys = [homekey] + keys if keys is not None else [homekey]
        keys = map(lambda x: "%s: %s" % (self.user, x), keys)
        keys = ''.join(keys)
        newval = {'key': 'ssh-keys', 'value': keys}
        body['metadata']['items'].append(newval)
        newval = {'key': 'plan', 'value': plan}
        body['metadata']['items'].append(newval)
        newval = {'key': 'profile', 'value': profile}
        body['metadata']['items'].append(newval)
        if self.debug:
            print(body)
        conn.instances().insert(project=project, zone=zone, body=body).execute()
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
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=base).execute()
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        source = vm['disks'][0]['source']
        body = {'name': name, 'sourceDisk': source, 'forceCreate': True}
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
        print("not implemented")
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
            common.pprint("Vm %s not found" % name, color='red')
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
            name = vm['name']
            state = vm['status']
            ip = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP'] if 'natIP'\
                in vm['networkInterfaces'][0]['accessConfigs'][0] else ''
            source = os.path.basename(vm['disks'][0]['licenses'][0])
            plan = ''
            profile = ''
            report = 'N/A'
            if 'items' in vm['metadata']:
                for data in vm['metadata']['items']:
                    if data['key'] == 'plan':
                        plan = data['value']
                    if data['key'] == 'profile':
                        profile = data['value']
            vms.append([name, state, ip, source, plan, profile, report])
        return vms

    def console(self, name, tunnel=False):
        print("not implemented")
        return

    def serialconsole(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        console = conn.instances().getSerialPortOutput(zone=zone, project=project, instance=name).execute()
        if console is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        print(console['contents'])
        return

    def info(self, name, output='plain', fields=None, values=False):
        yamlinfo = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.debug:
            print(vm)
        yamlinfo['name'] = vm['name']
        yamlinfo['status'] = vm['status']
        machinetype = os.path.basename(vm['machineType'])
        if 'custom' in machinetype:
            yamlinfo['cpus'], yamlinfo['memory'] = machinetype.split('-')[1:]
        yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        if 'natIP'in vm['networkInterfaces'][0]['accessConfigs'][0]:
            yamlinfo['ip'] = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        yamlinfo['template'] = os.path.basename(vm['disks'][0]['licenses'][0])
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
        common.print_info(yamlinfo, output=output, fields=fields, values=values)
        return {'result': 'success'}

    def ip(self, name):
        ip = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            common.pprint("Vm %s not found" % name, color='red')
        else:
            ip = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        return ip

# should return a list of available templates, or isos ( if iso is set to True
    def volumes(self, iso=False):
        projects = ['centos-cloud', 'coreos-cloud', 'cos-cloud', 'debian-cloud',
                    'rhel-cloud', 'suse-cloud', 'ubuntu-os-cloud']
        projects.append(self.project)
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
            conn.instances().delete(zone=zone, project=project, instance=name).execute()
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue):
        print("not implemented")
        return

    def update_memory(self, name, memory):
        print("not implemented")
        return

    def update_cpu(self, name, numcpus):
        print("not implemented")
        return

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        print("not implemented")
        return

    def update_iso(self, name, iso):
        print("not implemented")
        return

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        # if int(size) < 500:
        #    common.pprint("Note that default size will be 500Gb", color='blue')
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
                time.sleep(5)
                common.pprint("Waiting for disk to be ready", color='green')
        body = {'source': '/compute/v1/projects/%s/zones/%s/disks/%s' % (project, zone, diskname), 'autoDelete': True}
        conn.instances().attachDisk(zone=zone, project=project, instance=name, body=body).execute()
        return {'result': 'success'}

    def delete_disk(self, name, diskname):
        print("not implemented")
        return

# should return a dict of {'pool': poolname, 'path': name}
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

    def _ssh_credentials(self, name):
        user = self.user
        ip = self.ip(name)
        return (user, ip)

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, D=None):
        u, ip = self._ssh_credentials(name)
        sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=u,
                                local=local, remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X,
                                debug=self.debug)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        u, ip = self._ssh_credentials(name)
        scpcommand = common.scp(name, ip='', host=self.host, port=self.port, hostuser=self.user, user=user,
                                source=source, destination=destination, recursive=recursive, tunnel=tunnel,
                                debug=self.debug, download=False)
        return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None):
        conn = self.conn
        project = self.project
        region = self.region
        body = {'name': name}
        body['autoCreateSubnetworks'] = True if cidr is not None else False
        conn.networks().insert(project=project, body=body).execute()
        timeout = 0
        while True:
            if timeout > 60:
                return {'result': 'failure', 'reason': 'timeout waiting for network to be ready'}
            try:
                if cidr is not None:
                    subnetbody = {'name': name, "ipCidrRange": cidr,
                                  "network": "projects/%s/global/networks/%s" % (project, name),
                                  'region': "projects/%s/regions/%s" % (project, region)}
                    conn.subnetworks().insert(region=region, project=project, body=subnetbody).execute()
                allowed = {"IPProtocol": "tcp", "ports": ["22"]}
                firewallbody = {'name': 'allow-ssh-%s' % name, 'network': 'global/networks/%s' % name,
                                'sourceRanges': ['0.0.0.0/0'], 'allowed': [allowed]}
                conn.firewalls().insert(project=project, body=firewallbody).execute()
                break
            except Exception as e:
                print(e)
                timeout += 5
                time.sleep(5)
                common.pprint("Waiting for network to be ready", color='green')
        return {'result': 'success'}

    def delete_network(self, name=None):
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
                conn.subnetworks().delete(region=region, project=project, subnetwork=subnetwork).execute()
        conn.networks().delete(project=project, network=name).execute()
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

    def delete_pool(self, name, full=False):
        print("not implemented")
        return

    def network_ports(self, name):
        return []

    def vm_ports(self, name):
        return []

# returns the path of the pool, if it makes sense. used by kcli list --pools
    def get_pool_path(self, pool):
        print("not implemented")
        return

    def __get_template_project(self, template):
        if template.startswith('sles'):
            return 'suse-cloud'
        if template.startswith('ubuntu'):
            return 'ubuntu-os-cloud'
        elif template in ['centos', 'coreos', 'cos', 'debian', 'rhel']:
            project = template.split('-')[0]
            return "%s-cloud" % project
        else:
            return None

    def __evaluate_template(self, template):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        template = template.lower()
        if 'centos-7' in template:
            return 'centos-7'
        elif 'debian' in template:
            return 'debian-8'
        elif 'rhel-guest-image-7' in template or 'rhel-server-7' in template:
            return 'rhel-7'
        elif [x for x in ubuntus if x in template]:
            return 'ubuntu-1804-lts'
        else:
            return template
