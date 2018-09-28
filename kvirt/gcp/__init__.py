#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gcp Provider Class
"""

from jinja2 import Environment, FileSystemLoader
from kvirt import common
from dateutil import parser as dateparser
import googleapiclient.discovery
from google.cloud import dns
from netaddr import IPNetwork
import os
import time

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip']


class Kgcp(object):
    def __init__(self, host='127.0.0.1', port=None, user='root', debug=False,
                 project="kubevirt-button", zone="europe-west1-b", region='europe-west1'):
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

    def create(self, name, virttype='kvm', profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[],
               numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}],
               disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[],
               ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[],
               enableroot=True, alias=[], overrides={}, tags={}):
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
        body = {'name': name, 'machineType': machine_type}
        body['networkInterfaces'] = []
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
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
            newdisk = {'boot': False, 'autoDelete': True}
            if index == 0 and template is not None:
                template = self.__evaluate_template(template)
                templateproject = self.__get_template_project(template)
                if templateproject is not None:
                    image_response = conn.images().getFromFamily(project=templateproject, family=template).execute()
                else:
                    image_response = conn.images().get(project=self.project, image=template).execute()
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
                        time.sleep(5)
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
                    print(("Skipping file %s as not found" % origin))
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
        if not os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME'])\
                and not os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
            print("neither id_rsa.pub or id_dsa public keys found in your .ssh directory, you might have trouble "
                  "accessing the vm")
            homekey = None
        elif os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
            homekey = open("%s/.ssh/id_rsa.pub" % os.environ['HOME']).read()
        else:
            homekey = open("%s/.ssh/id_dsa.pub" % os.environ['HOME']).read()
        if homekey is not None:
            keys = [homekey] + keys if keys is not None else [homekey]
        if keys is not None:
            keys = ["%s: %s" % (self.user, x) for x in keys]
            keys = ''.join(keys)
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
        if self.debug:
            print(body)
        conn.instances().insert(project=project, zone=zone, body=body).execute()
        if reservedns:
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
        # conn = self.conn
        # project = self.project
        # zone = self.zone
        resource = googleapiclient.discovery.build('cloudresourcemanager', 'v1')
        print(dir(resource.projects()))
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
        # zones = [zone['name'] for zone in self.conn.zones().list(project=project).execute()['items']]
        vms = []
        results = conn.instances().list(project=project, zone=zone).execute()
        if 'items' not in results:
            return []
        for vm in results['items']:
            name = vm['name']
            state = vm['status']
            ip = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP'] if 'natIP'\
                in vm['networkInterfaces'][0]['accessConfigs'][0] else ''
            source = os.path.basename(vm['disks'][0]['source'])
            source = conn.disks().get(zone=zone, project=self.project, disk=source).execute()
            if self.project in source['sourceImage']:
                source = os.path.basename(source['sourceImage'])
            elif 'licenses' in vm['disks'][0]:
                source = os.path.basename(vm['disks'][0]['licenses'][-1])
            else:
                source = ''
            plan = ''
            profile = ''
            # report = 'N/A'
            report = zone
            if 'items' in vm['metadata']:
                for data in vm['metadata']['items']:
                    if data['key'] == 'plan':
                        plan = data['value']
                    if data['key'] == 'profile':
                        profile = data['value']
            vms.append([name, state, ip, source, plan, profile, report])
        return sorted(vms)

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
        print((console['contents']))
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
        if 'tags' in vm and 'items' in vm['tags']:
            yamlinfo['tags'] = ','.join(vm['tags']['items'])
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
            return None
        if 'natIP' not in vm['networkInterfaces'][0]['accessConfigs'][0]:
            return None
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
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.disks().delete(zone=zone, project=project, disk=diskname).execute()
        except Exception as e:
            print(e)
            return {'result': 'failure', 'reason': "Disk %s not found" % name}
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

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False,
            D=None):
        u, ip = self._ssh_credentials(name)
        if ip is None:
            return None
        sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=u,
                                local=local, remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, Y=Y,
                                debug=self.debug)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        u, ip = self._ssh_credentials(name)
        scpcommand = common.scp(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=u,
                                source=source, destination=destination, recursive=recursive, tunnel=tunnel,
                                debug=self.debug, download=False)
        return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None, vlan=None):
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
                    try:
                        IPNetwork(cidr)
                    except:
                        return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
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

# returns the path of the pool, if it makes sense. used by kcli list --pools
    def get_pool_path(self, pool):
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
        template = template.lower()
        if 'centos-7' in template:
            return 'centos-7'
        elif 'debian' in template:
            return 'debian-8'
        elif 'rhel-guest-image-7' in template or 'rhel-server-7' in template:
            return 'rhel-7'
        elif [x for x in common.ubuntus if x in template]:
            return 'ubuntu-1804-lts'
        else:
            return template

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False):
        net = nets[0]
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
            if isinstance(net, dict):
                ip = net.get('ip')
            if ip is None:
                counter = 0
                while counter != 100:
                    ip = self.ip(name)
                    if ip is None:
                        time.sleep(5)
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
