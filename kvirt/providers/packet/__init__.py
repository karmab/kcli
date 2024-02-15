#!/usr/bin/env python
# -*- coding: utf-8 -*-

from packet import Manager
from packet.baseapi import Error
from kvirt import common
from kvirt.common import error, pprint, warning
from kvirt.defaults import IMAGES, METADATA_FIELDS
import json
import os
from time import sleep
from urllib.request import urlopen, Request


class Kpacket(object):
    def __init__(self, auth_token, project=None, debug=False, facility=None, tunnelhost=None,
                 tunneluser='root', tunnelport=22, tunneldir='/var/www/html'):
        self.debug = debug
        self.conn = None
        self.tunnelhost = tunnelhost
        self.tunnelport = tunnelport
        self.tunneluser = tunneluser
        self.tunneldir = tunneldir
        self.facility = facility
        self.auth_token = auth_token
        conn = Manager(auth_token=auth_token)
        try:
            projects = [p.id for p in conn.list_projects() if p.name == project or p.id == project]
        except Error as e:
            error(e)
            return
        if projects:
            self.project = projects[0]
            self.conn = conn
        else:
            error(f"Invalid project {project}")
        return

    def close(self):
        return

    def exists(self, name):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            return True
        return False

    def net_exists(self, name):
        return True

    def disk_exists(self, pool, name):
        for v in self.conn.list_volumes(self.project):
            if v.description == name:
                return True
        return False

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt',
               cpumodel='host-model', cpuflags=[], cpupinning=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=['default'], iso=None, vnc=True,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=[], cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=[], storemetadata=False, sharedfolders=[], kernel=None, initrd=None,
               cmdline=None, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False,
               placement=[], autostart=False, rng=False, metadata={}, securitygroups=[], vmuser=None):
        reservation_id = overrides.get('hardware_reservation_id')
        if reservation_id is not None:
            reservations = self.conn.list_hardware_reservations(self.project)
            if not reservations:
                return {'result': 'failure', 'reason': "No reserved hardware found"}
            elif reservation_id != 'next-available':
                matching_ids = [r.id for r in reservations if r.id == reservation_id or r.short_id == reservation_id]
                if not matching_ids:
                    return {'result': 'failure', 'reason': f"Reserved hardware with id {reservation_id} not found"}
                else:
                    reservation_id = matching_ids[0]
        ipxe_script_url = None
        userdata = None
        networkid = None
        networkids = []
        vlan = False
        for index, network in enumerate(nets):
            if index > 1:
                warning(f"Ignoring net higher than {index}")
                break
            if isinstance(network, str):
                networkname = network
            elif isinstance(network, dict) and 'name' in network:
                networkname = network['name']
            if networkname != 'default':
                networks = [n for n in self.conn.list_vlans(self.project) if n.id == networkname or
                            (n.description is not None and n.description == networkname)]
                if not networks:
                    return {'result': 'failure', 'reason': f"Network {networkname} not found"}
                else:
                    vlan = True
                    networkid = networks[0].id
            else:
                networkid = None
            networkids.append(networkid)
        if image is not None and not common.needs_ignition(image):
            if '_' not in image and image in ['rhel8', 'rhel7', 'centos7', 'centos8']:
                image = image[:-1] + '_' + image[-1:]
                pprint(f"Using image {image}")
            found = False
            for img in self.conn.list_operating_systems():
                if img.slug == image:
                    found = True
            if not found:
                msg = f"image {image} doesn't exist"
                return {'result': 'failure', 'reason': msg}
        elif image is None:
            ipxe_script_url = overrides.get('ipxe_script_url')
            if ipxe_script_url is None:
                return {'result': 'failure', 'reason': 'You need to define ipxe_script_url as parameter'}
            image = 'custom_ipxe'
        else:
            ignition_url = overrides.get('ignition_url')
            if ignition_url is None:
                if self.tunnelhost is not None:
                    ignition_url = f"http://{self.tunnelhost}/{name}.ign"
                else:
                    return {'result': 'failure', 'reason': 'You need to define ignition_url as parameter'}
            url = IMAGES[image]
            if 'rhcos' in image:
                if 'commit_id' in overrides:
                    kernel, initrd, metal = common.get_commit_rhcos_metal(overrides['commit_id'])
                else:
                    kernel, initrd, metal = common.get_latest_rhcos_metal(url)
            elif 'fcos' in image:
                kernel, initrd, metal = common.get_latest_fcos_metal(url)
            interface = 'eth0' if 'fcos' in image else 'ens3f0'
            userdata = self._ipxe(kernel, initrd, metal, ignition_url, interface)
            version = common.ignition_version(image)
            ignitiondir = '/tmp'
            ipv6 = []
            ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, files=files, enableroot=enableroot, overrides=overrides,
                                           version=version, plan=plan, ipv6=ipv6, image=image, vmuser=vmuser)
            image = 'custom_ipxe'
            with open(f'{ignitiondir}/{name}.ign', 'w') as ignitionfile:
                ignitionfile.write(ignitiondata)
            if self.tunnelhost is not None:
                pprint(f"Copying ignition data to {self.tunnelhost}")
                scpcmd = "scp -qP %s /tmp/%s.ign %s@%s:%s/%s.ign" % (self.tunnelport, name, self.tunneluser,
                                                                     self.tunnelhost, self.tunneldir, name)
                os.system(scpcmd)
        if flavor is None:
            # if f[1] >= numcpus and f[2] >= memory:
            minmemory = 512000
            for f in self.conn.list_plans():
                if not f.specs:
                    continue
                flavorname = f.name
                # skip this flavor until we know where it can be launched
                if flavorname == 'c3.small.x86' or (vlan and flavorname in ['t1.small.x86', 'c1.small.x86']):
                    continue
                flavorcpus = int(f.specs['cpus'][0]['count'])
                flavormemory = int(f.specs['memory']['total'].replace('GB', '')) * 1024
                if flavorcpus >= 1 and flavormemory >= memory and flavormemory < minmemory:
                    flavor = flavorname
                    minmemory = flavormemory
                    validfacilities = f.available_in
            if flavor is None:
                return {'result': 'failure', 'reason': 'Couldnt find flavor matching requirements'}
            pprint(f"Using flavor {flavor}")
        else:
            flavors = [f for f in self.conn.list_plans() if f.slug == flavor]
            if not flavors:
                return {'result': 'failure', 'reason': f'Flavor {flavor} not found'}
            else:
                validfacilities = flavors[0].available_in
        features = ['tpm'] if tpm else []
        if cloudinit and userdata is None:
            userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                        domain=domain, files=files, enableroot=enableroot, overrides=overrides,
                                        fqdn=True, storemetadata=storemetadata, vmuser=vmuser)[0]
        validfacilities = [os.path.basename(e['href']) for e in validfacilities]
        validfacilities = [f.code for f in self.conn.list_facilities() if f.id in validfacilities]
        if not validfacilities:
            return {'result': 'failure', 'reason': f'no valid facility found for flavor {flavor}'}
        facility = overrides.get('facility')
        if facility is not None:
            matchingfacilities = [f for f in self.conn.list_facilities() if f.slug == facility]
            if not matchingfacilities:
                return {'result': 'failure', 'reason': f'Facility {facility} not found'}
            if facility not in validfacilities:
                return {'result': 'failure',
                        'reason': 'Facility %s not allowed. You should choose between %s' % (facility,
                                                                                             ','.join(validfacilities))}
        elif self.facility is not None:
            if self.facility not in validfacilities:
                return {'result': 'failure',
                        'reason': 'Facility %s not allowed. You should choose between %s' % (self.facility,
                                                                                             ','.join(validfacilities))}
            facility = self.facility
        else:
            facility = validfacilities[0]
        tags = [f'project_{self.project}']
        if userdata is not None and 'ignition' in userdata:
            tags.append(f"kernel_{os.path.basename(kernel)}")
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            tags.append(f"{entry}_{metadata[entry]}")
        data = {'project_id': self.project, 'hostname': name, 'plan': flavor, 'facility': facility,
                'operating_system': image, 'userdata': userdata, 'features': features, 'tags': tags}
        if ipxe_script_url is not None:
            data['ipxe_script_url'] = ipxe_script_url
        if reservation_id is not None:
            data['hardware_reservation_id'] = reservation_id
        try:
            device = self.conn.create_device(**data)
        except Exception as e:
            return {'result': 'failure', 'reason': e}
        for networkid in networkids:
            if networkid is None:
                continue
            elif 'cluster' in overrides and name.startswith(f"{overrides['cluster']}-"):
                warning("Not applying custom vlan to speed process for openshift...")
                warning("This will be applied manually later...")
                continue
            status = 'provisioning'
            while status != 'active':
                status = self.info(name).get('status')
                pprint(f"Waiting 5s for {name} to be active...")
                sleep(5)
            device_port_id = device["network_ports"][2]["id"]
            self.conn.disbond_ports(device_port_id, False)
            self.conn.assign_port(device_port_id, networkid)
            break
        return {'result': 'success'}

    def start(self, name):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            device.power_on()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': f"Node {name} not found"}

    def stop(self, name, soft=False):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            device.power_off()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': f"Node {name} not found"}

    def create_snapshot(self, name, base):
        print("not implemented")
        return {'result': 'success'}

    def delete_snapshot(self, name, base):
        print("not implemented")
        return {'result': 'success'}

    def list_snapshots(self, base):
        print("not implemented")
        return []

    def revert_snapshot(self, name, base):
        print("not implemented")
        return {'result': 'success'}

    def restart(self, name):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            device.reboot()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': f"Node {name} not found"}

    def info_host(self):
        data = {}
        projects = [proj for proj in self.conn.list_projects() if proj.name == self.project or proj.id == self.project]
        if not projects:
            error(f"Project {self.project} not found")
            return {}
        project = projects[0]
        data['project_name'] = project.name
        data['project_id'] = project.id
        if self.facility is not None:
            data['facility'] = self.facility
        data['nodes_running'] = len(self.conn.list_devices(self.project))
        return data

    def status(self, name):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            print(device.state)
            return device.state
        else:
            return None

    def list(self):
        vms = []
        for vm in self.conn.list_devices(self.project):
            try:
                vms.append(self.info(vm.hostname, vm=vm))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        self.serialconsole(name, web=web)
        return

    def serialconsole(self, name, web=False):
        user, ip = common._ssh_credentials(self, name)[:2]
        sshcommand = "ssh"
        identityfile = None
        if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        if identityfile is not None:
            sshcommand += f" -i {identityfile}"
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            return
        serverid = device.id
        facilitycode = [f.code for f in self.conn.list_facilities() if f.id == device['facility']['id']][0]
        sshcommand += f" {serverid}@sos.{facilitycode}.packet.net"
        if web:
            return sshcommand
        if self.debug:
            print(sshcommand)
        os.system(sshcommand)
        return

    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            error(f"Node {name} not found")
            return {}
        if debug:
            print(vars(device))
        name = device.hostname
        deviceid = device.id
        state = device.state
        nets = []
        ip = None
        for entry in device.ip_addresses:
            if entry['public'] and entry['address_family'] == 4:
                ip = entry['address']
                dev = 'bond0'
                mac = entry['address']
                network = entry['network']
                networktype = 'public' if entry['public'] else 'private'
                nets.append({'device': dev, 'mac': mac, 'net': network, 'type': networktype})
        if device.network_ports is not None:
            for entry in device.network_ports:
                if entry['type'] == 'NetworkBondPort':
                    continue
                dev = entry['name']
                bonded = entry['data']['bonded']
                networktype = 'bonded' if bonded else 'vlan'
                network = 'default'
                if not bonded:
                    virtual_networks = entry['virtual_networks']
                    virtual_network_ids = [os.path.basename(vn['href']) for vn in virtual_networks]
                    vlans = []
                    for vlan in self.conn.list_vlans(self.project):
                        if vlan.id in virtual_network_ids:
                            vlans.append(vlan.description if vlan.description is not None else vlan.vxlan)
                    network = ','.join(vlans)
                mac = entry['data']['mac']
                nets.append({'device': dev, 'mac': mac, 'net': network, 'type': networktype})
        kernel = None
        source = device.operating_system['slug']
        flavor = device.plan
        flavorname = device.plan['slug']
        disks = []
        for index0, entry in enumerate(flavor['specs']['drives']):
            for index1 in range(entry['count']):
                dev = f"disk{index0}_{index1}"
                disksize = entry['size'].replace('GB', '')
                if 'TB' in entry['size']:
                    disksize = int(float(disksize.replace('TB', '')) * 1000)
                else:
                    disksize = int(disksize)
                diskformat = entry['type']
                drivertype = entry['category']
                path = ''
                disks.append({'device': dev, 'size': disksize, 'format': diskformat, 'type': drivertype,
                              'path': path})
        for volume in device.volumes:
            volumeid = os.path.basename(volume['href'])
            volumeinfo = self.conn.get_volume(volumeid)
            dev = volumeinfo.name
            disksize = volumeinfo.size
            drivertype = 'volume'
            diskformat = ''
            path = volumeinfo.description if volumeinfo.description is not None else volumeinfo.name
            disks.append({'device': dev, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        numcpus = int(flavor['specs']['cpus'][0]['count'])
        memory = int(flavor['specs']['memory']['total'].replace('GB', '')) * 1024
        creationdate = device.created_at
        yamlinfo = {'name': name, 'instanceid': deviceid, 'status': state, 'ip': ip, 'nets': nets, 'disks': disks,
                    'flavor': flavorname, 'cpus': numcpus, 'memory': memory, 'creationdate': creationdate}
        if ip is not None:
            yamlinfo['ip'] = ip
        yamlinfo['user'] = common.get_user(kernel) if kernel is not None else 'root'
        if device.tags:
            for tag in device.tags:
                if '_' in tag and len(tag.split('_')) == 2:
                    key, value = tag.split('_')
                    yamlinfo[key] = value
                    if key == 'kernel':
                        kernel = value
        yamlinfo['image'] = kernel if kernel is not None and source == 'custom_ipxe' else source
        return yamlinfo

    def ip(self, name):
        print("not implemented")
        return None

    def volumes(self, iso=False):
        return [image.slug for image in self.conn.list_operating_systems()]

    def delete(self, name, snapshots=False):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            try:
                device.delete()
            except Exception as e:
                return {'result': 'failure', 'reason': str(e)}
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': f"Node {name} not found"}

    def dnsinfo(self, name):
        return None, None

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            return {'result': 'failure', 'reason': f"Node {name} not found"}
        for index, tag in enumerate(device.tags):
            if tag.startswith(f'{metatype}_'):
                device.tags[index] = f'{metatype}_{metavalue}'
                device.update()
                break

    def update_memory(self, name, memory):
        print("not implemented")
        return

    def update_cpus(self, name, numcpus):
        print("not implemented")
        return

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        print("not implemented")
        return

    def update_flavor(self, name, flavor):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            error(f"Node {name} not found")
            return
        flavors = [f for f in self.conn.list_plans() if f.slug == flavor]
        if not flavors:
            error(f"Flavor {flavor} not found")
            return
        device.plan = flavors[0]
        device.update()
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        if size < 100:
            error("Size must be greater than or equal to 100")
            return None
        if self.facility is None:
            error("a Facility needs to be set in order to create disk2")
            return None
        volume = self.conn.create_volume(project_id=self.project, description=name, plan="storage_1", size=size,
                                         facility=self.facility, snapshot_count=7, snapshot_frequency="1day")
        return volume.id

    def add_disk(self, name, size, pool=None, thin=True, image=None,
                 shareable=False, existing=None, interface='virtio', novm=False, overrides={}, diskname=None):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            return {'result': 'failure', 'reason': f"Node {name} not found"}
        volumeid = self.create_disk(name, size)
        if volumeid is None:
            return {'result': 'failure', 'reason': "Issue creating disk"}
        volume = self.conn.get_volume(volumeid)
        volume.attach(device.id)
        return {'result': 'success'}

    def delete_disk(self, name, diskname, pool=None, novm=False):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if not devices:
            return {'result': 'failure', 'reason': f"Node {name} not found"}
        volumes = [v for v in self.conn.list_volumes(self.project) if v.description == diskname or v.name == diskname]
        if volumes:
            volume = volumes[0]
            volume.detach()
            volume.delete()
        return {'result': 'success'}

    def list_disks(self):
        disks = {}
        for v in self.conn.list_volumes(self.project):
            path = v.description if v.description is not None else v.name
            disks[v.name] = {'pool': 'default', 'path': path}
        return disks

    def add_nic(self, name, network, model='virtio'):
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            error(f"Node {name} not found")
            return
        flavorname = device.plan['slug']
        if flavorname in ['t1.small.x86', 'c1.small.x86']:
            error(f"Layer2 is not supported with flavor {flavorname}")
            return
        networks = [n for n in self.conn.list_vlans(self.project) if n.id == network or
                    (n.description is not None and n.description == network)]
        if not networks:
            error(f"Network {network} not found")
            return
        else:
            networkid = networks[0].id
        status = 'provisioning'
        while status != 'active':
            status = self.info(name).get('status')
            pprint(f"Waiting 5s for {name} to be active...")
            sleep(5)
        device_eth1_port_id = device["network_ports"][2]["id"]
        self.conn.disbond_ports(device_eth1_port_id, False)
        self.conn.assign_port(device_eth1_port_id, networkid)
        return

    def delete_nic(self, name, interface):
        print("not implemented")
        return

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")
        return

    def delete_image(self, image, pool=None):
        print("not implemented")
        return {'result': 'success'}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
        return {'result': 'failure', 'reason': "not implemented"}

    def _create_network(self, name, facility, vlan=None, vxlan=None):
        data = {"project_id": self.project, "description": name, "facility": facility}
        if vlan is not None:
            data['vlan'] = vlan
        if vxlan is not None:
            data['vxlan'] = vxlan
        headers = {'X-Auth-Token': self.auth_token, 'Content-Type': 'application/json'}
        url = f"https://api.packet.net/projects/{self.project}/virtual-networks"
        data = json.dumps(data).encode('utf-8')
        request = Request(url, headers=headers, method='POST', data=data)
        return json.loads(urlopen(request).read())

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        if 'facility' in overrides:
            facility = overrides['facility']
        elif self.facility is not None:
            facility = self.facility
        else:
            return {'result': 'failure', 'reason': "Missing Facility"}
        vlan, vxlan = None, None
        if 'vlan' in overrides:
            vlan = overrides['vlan']
        if 'vxlan' in overrides:
            vxlan = overrides['vxlan']
        result = self._create_network(name, facility, vlan=vlan, vxlan=vxlan)
        if 'errors' in result:
            return {'result': 'failure', 'reason': ','.join(result['errors'])}
        else:
            return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        networks = [network for network in self.conn.list_vlans(self.project) if network.id == name]
        if networks:
            networks[0].delete()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': f"Network {name} not found"}

    def list_pools(self):
        return ['default']

    def list_networks(self):
        networks = {}
        for ip in self.conn.list_project_ips(self.project):
            mode = 'public' if ip.public else 'private'
            facility = ip.facility.code
            networks[ip.id] = {'cidr': f"{ip.network}/{ip.cidr}", 'dhcp': True, 'domain': facility,
                               'type': f'ipv{ip.address_family}', 'mode': mode}
        for vlan in self.conn.list_vlans(self.project):
            cidr = vlan.description if vlan.description is not None else 'N/A'
            networks[vlan.id] = {'cidr': cidr, 'dhcp': False, 'domain': vlan.facility_code, 'type': 'vlan',
                                 'mode': vlan.vxlan}
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        return networkinfo

    def list_subnets(self):
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        print("not implemented")
        return

    def network_ports(self, name):
        print("not implemented")
        return

    def vm_ports(self, name):
        return ['default']

    def get_pool_path(self, pool):
        return 'default'

    def list_flavors(self):
        results = []
        for flavor in self.conn.list_plans():
            if not flavor.specs:
                continue
            numcpus = int(flavor.specs['cpus'][0]['count'])
            memory = int(flavor.specs['memory']['total'].replace('GB', '')) * 1024
            results.append([str(flavor), numcpus, memory])
        return results

    def export(self, name, image=None):
        return

    def _ipxe(self, kernel, initrd, metal, ignition_url, interface):
        ipxeparameters = f"ip={interface}:dhcp "
        ipxeparameters += f"rd.neednet=1 initrd={initrd} console=ttyS1,115200n8 "
        ipxeparameters += "coreos.inst=yes coreos.inst.insecure=yes coreos.inst.install_dev=sda"
        return """#!ipxe
kernel %s %s coreos.inst.image_url=%s coreos.inst.ignition_url=%s
initrd %s
boot || reboot""" % (kernel, ipxeparameters, metal, ignition_url, initrd)

    def create_bucket(self, bucket, public=False):
        print("not implemented")
        return

    def delete_bucket(self, bucket):
        print("not implemented")
        return

    def delete_from_bucket(self, bucket, path):
        print("not implemented")
        return

    def download_from_bucket(self, bucket, path):
        print("not implemented")
        return

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        print("not implemented")
        return

    def list_buckets(self):
        print("not implemented")
        return []

    def list_bucketfiles(self, bucket):
        print("not implemented")
        return []

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        print("not implemented")
        return

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        print("not implemented")
        return []

    def create_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_security_group(self, name):
        print("not implemented")
        return {'result': 'success'}

    def update_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def info_subnet(self, name):
        print("not implemented")
        return {}

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        print("not implemented")
        return {'result': 'success'}

    def update_subnet(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_dns_zones(self):
        print("not implemented")
        return []
