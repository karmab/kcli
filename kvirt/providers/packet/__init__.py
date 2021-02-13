#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Packet provider class
"""

from packet import Manager
from packet.baseapi import Error
from kvirt import common
from kvirt.common import error, pprint, warning
from kvirt.defaults import IMAGES, METADATA_FIELDS
import json
import requests
import os
from time import sleep


class Kpacket(object):
    """

    """
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
            error("Invalid project %s" % project)
        return

# should cleanly close your connection, if needed
    def close(self):
        """

        :return:
        """
        print("not implemented")
        return

    def exists(self, name):
        """

        :param name:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            return True
        return False

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        return True

    def disk_exists(self, pool, name):
        """

        :param pool:
        :param name:
        """
        for v in self.conn.list_volumes(self.project):
            if v.description == name:
                return True
        return False

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt',
               cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=None, cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=[], storemetadata=False, sharedfolders=[], kernel=None, initrd=None,
               cmdline=None, cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False,
               placement=[], autostart=False, rng=False, metadata={}, securitygroups=[]):
        """

        :param name:
        :param virttype:
        :param profile:
        :param flavor:
        :param plan:
        :param cpumodel:
        :param cpuflags:
        :param cpupinning:
        :param numcpus:
        :param memory:
        :param guestid:
        :param pool:
        :param image:
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
        :param cpuhotplug:
        :param memoryhotplug:
        :param numamode:
        :param numa:
        :param pcidevices:
        :param tpm:
        :return:
        """
        reservation_id = overrides.get('hardware_reservation_id')
        if reservation_id is not None:
            reservations = self.conn.list_hardware_reservations(self.project)
            if not reservations:
                return {'result': 'failure', 'reason': "No reserved hardware found"}
            elif reservation_id != 'next-available':
                matching_ids = [r.id for r in reservations if r.id == reservation_id or r.short_id == reservation_id]
                if not matching_ids:
                    return {'result': 'failure', 'reason': "Reserved hardware with id %s not found" % reservation_id}
                else:
                    reservation_id = matching_ids[0]
        ipxe_script_url = None
        userdata = None
        networkid = None
        networkids = []
        vlan = False
        for index, network in enumerate(nets):
            if index > 1:
                warning("Ignoring net higher than %s" % index)
                break
            if isinstance(network, str):
                networkname = network
            elif isinstance(network, dict) and 'name' in network:
                networkname = network['name']
            if networkname != 'default':
                networks = [n for n in self.conn.list_vlans(self.project) if n.id == networkname or
                            (n.description is not None and n.description == networkname)]
                if not networks:
                    return {'result': 'failure', 'reason': "Network %s not found" % networkname}
                else:
                    vlan = True
                    networkid = networks[0].id
            else:
                    networkid = None
            networkids.append(networkid)
        if image is not None and not common.needs_ignition(image):
            if '_' not in image and image in ['rhel8', 'rhel7', 'centos7', 'centos8']:
                image = image[:-1] + '_' + image[-1:]
                pprint("Using image %s" % image)
            found = False
            for img in self.conn.list_operating_systems():
                if img.slug == image:
                    found = True
            if not found:
                msg = "image %s doesn't exist" % image
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
                    ignition_url = "http://%s/%s.ign" % (self.tunnelhost, name)
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
                                           domain=domain, reserveip=reserveip, files=files,
                                           enableroot=enableroot, overrides=overrides, version=version, plan=plan,
                                           ipv6=ipv6, image=image)
            image = 'custom_ipxe'
            with open('%s/%s.ign' % (ignitiondir, name), 'w') as ignitionfile:
                ignitionfile.write(ignitiondata)
            if self.tunnelhost is not None:
                pprint("Copying ignition data to %s" % self.tunnelhost)
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
            pprint("Using flavor %s" % flavor)
        else:
            flavors = [f for f in self.conn.list_plans() if f.slug == flavor]
            if not flavors:
                return {'result': 'failure', 'reason': 'Flavors %s not found' % flavor}
            else:
                validfacilities = flavors[0].available_in
        features = ['tpm'] if tpm else []
        if cloudinit and userdata is None:
            userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                        domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                        overrides=overrides, fqdn=True, storemetadata=storemetadata)[0]
        validfacilities = [os.path.basename(e['href']) for e in validfacilities]
        validfacilities = [f.code for f in self.conn.list_facilities() if f.id in validfacilities]
        if not validfacilities:
                return {'result': 'failure', 'reason': 'no valid facility found for flavor %s' % flavor}
        facility = overrides.get('facility')
        if facility is not None:
            matchingfacilities = [f for f in self.conn.list_facilities() if f.slug == facility]
            if not matchingfacilities:
                return {'result': 'failure', 'reason': 'Facility %s not found' % facility}
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
        tags = ['project_%s' % self.project]
        if userdata is not None and 'ignition' in userdata:
            tags.append("kernel_%s" % os.path.basename(kernel))
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            tags.append("%s_%s" % (entry, metadata[entry]))
        # ip_addresses = [{"address_family": 4, "public": True}, {"address_family": 6, "public": False}]
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
            elif 'cluster' in overrides and name.startswith("%s-" % overrides['cluster']):
                warning("Not applying custom vlan to speed process for openshift...")
                warning("This will be applied manually later...")
                continue
            status = 'provisioning'
            while status != 'active':
                status = self.info(name).get('status')
                pprint("Waiting 5s for %s to be active..." % name)
                sleep(5)
            device_port_id = device["network_ports"][2]["id"]
            self.conn.disbond_ports(device_port_id, False)
            self.conn.assign_port(device_port_id, networkid)
            break
        return {'result': 'success'}

    def start(self, name):
        """

        :param name:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            device.power_on()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def stop(self, name):
        """

        :param name:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            device.power_off()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        """

        :param name:
        :param base:
        :param revert:
        :param delete:
        :param listing:
        :return:
        """
        print("not implemented")
        return

    def restart(self, name):
        """

        :param name:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            device.reboot()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def report(self):
        """

        :return:
        """
        projects = [proj for proj in self.conn.list_projects() if proj.name == self.project or proj.id == self.project]
        if not projects:
            error("Project %s not found" % self.project)
            return
        project = projects[0]
        print("Project name: %s" % project.name)
        print("Project id: %s" % project.id)
        if self.facility is not None:
            print("Facility: %s" % self.facility)
        print("Vms Running: %s" % len(self.conn.list_devices(self.project)))
        return

    def status(self, name):
        """

        :param name:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            print(device.state)
            return device.state
        else:
            return None

# should return a sorted list of name, state, ip, source, plan, profile, report
    def list(self):
        """

        :return:
        """
        vms = []
        for vm in self.conn.list_devices(self.project):
            vms.append(self.info(vm.hostname, vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        """

        :param name:
        :param tunnel:
        :return:
        """
        self.serialconsole(name, web=web)
        return

    def serialconsole(self, name, web=False):
        """

        :param name:
        :return:
        """
        user, ip = common._ssh_credentials(self, name)[:2]
        sshcommand = "ssh"
        identityfile = None
        if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        if identityfile is not None:
            sshcommand += " -i %s" % identityfile
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            return
        serverid = device.id
        facilitycode = [f.code for f in self.conn.list_facilities() if f.id == device['facility']['id']][0]
        sshcommand = "%s %s@sos.%s.packet.net" % (sshcommand, serverid, facilitycode)
        if web:
            return sshcommand
        if self.debug:
            print(sshcommand)
        os.system(sshcommand)
        return

    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        """

        :param name:
        :param output:
        :param fields:
        :param values:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            error("VM %s not found" % name)
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
                dev = "disk%s_%s" % (index0, index1)
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
        # for entry in device.network_ports:
        #    print(entry)
        return yamlinfo

# should return ip string
    def ip(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return None

# should return a list of available images, or isos ( if iso is set to True
    def volumes(self, iso=False):
        """

        :param iso:
        :return:
        """
        return [image.slug for image in self.conn.list_operating_systems()]

    def delete(self, name, snapshots=False):
        """

        :param name:
        :param snapshots:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
            try:
                device.delete()
            except Exception as e:
                return {'result': 'failure', 'reason': str(e)}
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

# should return dnsclient, domain for the given vm
    def dnsinfo(self, name):
        """

        :param name:
        :return:
        """
        return None, None

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

    def update_metadata(self, name, metatype, metavalue, append=False):
        """

        :param name:
        :param metatype:
        :param metavalue:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for index, tag in enumerate(device.tags):
            if tag.startswith('%s_' % metatype):
                device.tags[index] = '%s_%s' % (metatype, metavalue)
                device.update()
                break

    def update_memory(self, name, memory):
        """

        :param name:
        :param memory:
        :return:
        """
        print("not implemented")
        return

    def update_cpus(self, name, numcpus):
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

    def update_flavor(self, name, flavor):
        """

        :param name:
        :param flavor:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            error("VM %s not found" % name)
            return
        flavors = [f for f in self.conn.list_plans() if f.slug == flavor]
        if not flavors:
            error("Flavor %s not found" % flavor)
            return
        device.plan = flavors[0]
        device.update()
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param image:
        :return:
        """
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
                 shareable=False, existing=None, interface='virtio', novm=False):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param image:
        :param shareable:
        :param existing:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        volumeid = self.create_disk(name, size)
        if volumeid is None:
            return {'result': 'failure', 'reason': "Issue creating disk"}
        volume = self.conn.get_volume(volumeid)
        volume.attach(device.id)
        return {'result': 'success'}

    def delete_disk(self, name, diskname, pool=None, novm=False):
        """

        :param name:
        :param diskname:
        :param pool:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if not devices:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        volumes = [v for v in self.conn.list_volumes(self.project) if v.description == diskname or v.name == diskname]
        if volumes:
            volume = volumes[0]
            volume.detach()
            volume.delete()
        return {'result': 'success'}

# should return a dict of {'pool': poolname, 'path': name}
    def list_disks(self):
        """

        :return:
        """
        disks = {}
        for v in self.conn.list_volumes(self.project):
            path = v.description if v.description is not None else v.name
            disks[v.name] = {'pool': 'default', 'path': path}
        return disks

    def add_nic(self, name, network):
        """

        :param name:
        :param network:
        :return:
        """
        devices = [d for d in self.conn.list_devices(self.project) if d.hostname == name]
        if devices:
            device = devices[0]
        else:
            error("VM %s not found" % name)
            return
        flavorname = device.plan['slug']
        if flavorname in ['t1.small.x86', 'c1.small.x86']:
            error("Layer2 is not supported with flavor %s" % flavorname)
            return
        networks = [n for n in self.conn.list_vlans(self.project) if n.id == network or
                    (n.description is not None and n.description == network)]
        if not networks:
            error("Network %s not found" % network)
            return
        else:
            networkid = networks[0].id
        status = 'provisioning'
        while status != 'active':
            status = self.info(name).get('status')
            pprint("Waiting 5s for %s to be active..." % name)
            sleep(5)
        device_eth1_port_id = device["network_ports"][2]["id"]
        self.conn.disbond_ports(device_eth1_port_id, False)
        self.conn.assign_port(device_eth1_port_id, networkid)
        return

    def delete_nic(self, name, interface):
        """

        :param name:
        :param interface:
        :return:
        """
        print("not implemented")
        return

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

    def delete_image(self, image, pool=None):
        """

        :param image:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def add_image(self, url, pool, short=None, cmd=None, name=None):
        """

        :param image:
        :param pool:
        :param short:
        :param cmd:
        :param name:
        :param size:
        :return:
        """
        return {'result': 'failure', 'reason': "not implemented"}

    def _create_network(self, name, facility, vlan=None, vxlan=None):
        data = {"project_id": self.project, "description": name, "facility": facility}
        if vlan is not None:
            data['vlan'] = vlan
        if vxlan is not None:
            data['vxlan'] = vxlan
        headers = {'X-Auth-Token': self.auth_token, 'Content-Type': 'application/json'}
        url = "https://api.packet.net/projects/%s/virtual-networks" % self.project
        r = requests.post(url, headers=headers, data=json.dumps(data))
        return r.json()

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
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
        # networks = self.list_networks()
        # if name in networks:
        #    pprint("Network %s already exists" % name)
        #    return {'result': 'exist'}
        if 'facility' in overrides:
            facility = overrides['facility']
        elif self.facility is not None:
            facility = self.facility
        else:
            return {'result': 'failure', 'reason': "Missing Facility"}
        # data = {'project_id': self.project, 'facility': facility, 'description': name}
        # if 'vlan' in overrides:
        #    data['vlan'] = overrides['vlan']
        # if 'vxlan' in overrides:
        #    data['vxlan'] = overrides['vxlan']
        # vlan = self.conn.create_vlan(**data)
        # return {'result': 'success'}
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

    def delete_network(self, name=None, cidr=None):
        """

        :param name:
        :param cidr:
        :return:
        """
        networks = [network for network in self.conn.list_vlans(self.project) if network.id == name]
        if networks:
            networks[0].delete()
            return {'result': 'success'}
        else:
            return {'result': 'failure', 'reason': "Network %s not found" % name}

# should return a dict of pool strings
    def list_pools(self):
        """

        :return:
        """
        return ['default']

    def list_networks(self):
        """

        :return:
        """
        networks = {}
        for ip in self.conn.list_project_ips(self.project):
            mode = 'public' if ip.public else 'private'
            facility = ip.facility.code
            networks[ip.id] = {'cidr': "%s/%s" % (ip.network, ip.cidr),
                               'dhcp': True, 'domain': facility, 'type': 'ipv%s' % ip.address_family, 'mode': mode}
        for vlan in self.conn.list_vlans(self.project):
            cidr = vlan.description if vlan.description is not None else 'N/A'
            networks[vlan.id] = {'cidr': cidr, 'dhcp': False, 'domain': vlan.facility_code, 'type': 'vlan',
                                 'mode': vlan.vxlan}
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
        print("not implemented")
        return

    def vm_ports(self, name):
        """

        :param name:
        :return:
        """
        return ['default']

    def get_pool_path(self, pool):
        """

        :param pool:
        :return:
        """
        return 'default'

    def flavors(self):
        """

        :return:
        """
        results = []
        for flavor in self.conn.list_plans():
            if not flavor.specs:
                continue
            numcpus = int(flavor.specs['cpus'][0]['count'])
            memory = int(flavor.specs['memory']['total'].replace('GB', '')) * 1024
            results.append([str(flavor), numcpus, memory])
        return results

# export the primary disk of the corresponding instance so it's available as a image
    def export(self, name, image=None):
        """

        :param image:
        :return:
        """
        return

    def _ipxe(self, kernel, initrd, metal, ignition_url, interface):
        ipxeparameters = "ip=%s:dhcp " % interface
        ipxeparameters += "rd.neednet=1 initrd=%s console=ttyS1,115200n8 " % initrd
        ipxeparameters += "coreos.inst=yes coreos.inst.insecure=yes coreos.inst.install_dev=sda"
        return """#!ipxe
kernel %s %s coreos.inst.image_url=%s coreos.inst.ignition_url=%s
initrd %s
boot || reboot""" % (kernel, ipxeparameters, metal, ignition_url, initrd)
