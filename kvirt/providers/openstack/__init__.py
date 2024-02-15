#!/usr/bin/env python
# -*- coding: utf-8 -*-

from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import METADATA_FIELDS
from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client as glanceclient
from cinderclient import client as cinderclient
from novaclient import client as novaclient
from neutronclient.v2_0.client import Client as neutronclient
import swiftclient.client as swiftclient
import os
from shutil import which
from time import sleep
import webbrowser
from ipaddress import ip_address, ip_network


class Kopenstack(object):
    """

    """
    def __init__(self, host='127.0.0.1', version='3', port=None, user='root', password=None, debug=False, project=None,
                 domain='Default', auth_url=None, ca_file=None, external_network=None, region_name=None,
                 glance_disk=False, auth_type='password', auth_token=None):
        self.debug = debug
        self.host = host
        loader = loading.get_plugin_loader(auth_type)
        if auth_type == 'password':
            auth = loader.load_from_options(auth_url=auth_url, username=user, password=password, project_name=project,
                                            user_domain_name=domain, project_domain_name=domain)
        else:
            auth = loader.load_from_options(auth_url=auth_url, token=auth_token, project_id=project)
        if ca_file is not None:
            sess = session.Session(auth=auth, verify=os.path.expanduser(ca_file))
        else:
            sess = session.Session(auth=auth)
        self.nova = novaclient.Client(version, session=sess, region_name=region_name)
        self.glance = glanceclient(version, session=sess, region_name=region_name)
        self.cinder = cinderclient.Client('3', session=sess, region_name=region_name)
        self.neutron = neutronclient(session=sess, region_name=region_name)
        os_options = {'user_domain_name': domain, 'project_domain_name': domain, 'project_name': project}
        self.swift = swiftclient.Connection(authurl=auth_url, user=user, key=password, os_options=os_options,
                                            auth_version='3')
        self.conn = self.nova
        self.project = project
        self.external_network = external_network
        self.region_name = region_name
        self.glance_disk = glance_disk

# should cleanly close your connection, if needed
    def close(self):
        print("not implemented")

    def exists(self, name):
        return

    def net_exists(self, name):
        neutron = self.neutron
        networks = {net['name']: net['id'] for net in neutron.list_networks()['networks']}
        return name in networks

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', plan='kvirt', flavor=None,
               cpumodel='host-model', cpuflags=[], cpupinning=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=['default'], iso=None, vnc=True,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=[], cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=[], storemetadata=False, sharedfolders=[], kernel=None, initrd=None,
               cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None,
               numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[], vmuser=None):
        default_diskinterface = diskinterface
        glance = self.glance
        nova = self.nova
        neutron = self.neutron
        try:
            nova.servers.find(name=name)
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        except:
            pass
        allflavors = [f for f in nova.flavors.list()]
        allflavornames = [flavor.name for flavor in allflavors]
        if flavor is None:
            flavors = [flavor for flavor in allflavors if flavor.ram >= memory and flavor.vcpus >= numcpus]
            if flavors:
                flavor = flavors[0]
                pprint(f"Using flavor {flavor.name}")
            else:
                return {'result': 'failure', 'reason': "Couldn't find a valid flavor matching your specs"}
        elif flavor not in allflavornames:
            return {'result': 'failure', 'reason': f"Flavor {flavor} not found"}
        else:
            flavor = nova.flavors.find(name=flavor)
        nics = []
        need_floating = True
        for net in nets:
            if isinstance(net, str):
                netname = net
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
            try:
                net = nova.neutron.find_network(name=netname)
                if net.to_dict()['router:external']:
                    need_floating = False
            except Exception as e:
                error(e)
                return {'result': 'failure', 'reason': f"Network {netname} not found"}
            nics.append({'net-id': net.id})
        target = iso or image
        if iso is not None and not self.glance_disk and len(disks) in [0, 1]:
            if len(disks) == 0:
                return {'result': 'failure', 'reason': "Booting from iso requires to specify at least one extra disk"}
            else:
                warning("Adding additional disk for booting from iso")
                disks.append(10)
        if target is not None:
            glanceimages = [img for img in glance.images.list() if img.name == target]
            if glanceimages:
                glanceimage = glanceimages[0]
            else:
                msg = f"you don't have image {target}"
                return {'result': 'failure', 'reason': msg}
        else:
            warning("a bootable disk is needed")
            glanceimage = None
        os_index = len(disks) - 1 if disks and iso is not None else 0
        block_device_mapping_v2 = []
        for index, disk in enumerate(disks):
            if index == os_index and self.glance_disk:
                continue
            diskname = f"{name}-disk{index}"
            letter = chr(index + ord('a'))
            diskinterface = default_diskinterface
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
                diskinterface = disk.get('interface', default_diskinterface)
            imageref = None
            if index == os_index and glanceimage is not None:
                imageref = glanceimage.id
                glanceimage = None
            newvol = self.cinder.volumes.create(name=diskname, size=disksize, imageRef=imageref)
            if index in [0, os_index]:
                self.cinder.volumes.set_bootable(newvol.id, True)
            while True:
                newvolstatus = self.cinder.volumes.get(newvol.id).status
                if newvolstatus == 'available':
                    break
                elif newvolstatus == 'error':
                    msg = f"Hit error when waiting for Disk {diskname} to be available"
                    return {'result': 'failure', 'reason': msg}
                else:
                    pprint(f"Waiting 10s for Disk {diskname} to be available")
                    sleep(10)
            block_device_mapping = {'device_name': f'vd{letter}', 'device_type': 'disk', 'disk_bus': diskinterface,
                                    'source_type': 'blank', "destination_type": "volume",
                                    'volume_size': disksize, "delete_on_termination": True, 'volume_id': newvol.id}
            if index == 0:
                block_device_mapping['boot_index'] = 0
            if iso is not None and index == os_index:
                block_device_mapping['device_type'] = 'cdrom'
                del block_device_mapping['disk_bus']
                block_device_mapping['boot_index'] = 1
            block_device_mapping_v2.append(block_device_mapping)
        key_name = 'kvirt'
        keypairs = [k.name for k in nova.keypairs.list()]
        if key_name not in keypairs:
            publickeyfile = get_ssh_pub_key()
            if publickeyfile is None:
                warning("neither id_rsa, id_dsa nor id_ed25519 public keys found in your .ssh directory, you "
                        "might have trouble accessing the vm")
            else:
                publickeyfile = open(publickeyfile).read()
                nova.keypairs.create(key_name, publickeyfile)
        elif keypairs:
            key_name = keypairs[0]
            if key_name != 'kvirt':
                pprint(f'Using keypair {key_name}')
        else:
            error("Couldn't locate or create keypair for use. Leaving...")
            return {'result': 'failure', 'reason': "No usable keypair found"}
        userdata = None
        if cloudinit:
            if image is not None and common.needs_ignition(image):
                version = common.ignition_version(image)
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, files=files, enableroot=enableroot, overrides=overrides,
                                           version=version, plan=plan, image=image, vmuser=vmuser)
            else:
                userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                            domain=domain, files=files, enableroot=enableroot, overrides=overrides,
                                            storemetadata=storemetadata, vmuser=vmuser)[0]
        meta = {x: metadata[x] for x in metadata if x in METADATA_FIELDS}
        instance = nova.servers.create(name=name, image=glanceimage, flavor=flavor, key_name=key_name, nics=nics,
                                       meta=meta, userdata=userdata, block_device_mapping_v2=block_device_mapping_v2,
                                       security_groups=securitygroups)
        tenant_id = instance.tenant_id
        if need_floating:
            floating_ips = [f['id'] for f in neutron.list_floatingips()['floatingips']
                            if f['port_id'] is None]
            if not floating_ips:
                network_id = None
                if self.external_network is not None:
                    networks = [n for n in neutron.list_networks()['networks'] if n['router:external']
                                if n['name'] == self.external_network]
                else:
                    networks = [n for n in neutron.list_networks()['networks'] if n['router:external']]
                if networks:
                    network_id = networks[0]['id']
                if network_id is not None and tenant_id is not None:
                    args = dict(floating_network_id=network_id, tenant_id=tenant_id)
                    floating_ip = neutron.create_floatingip(body={'floatingip': args})
                    floatingip_id = floating_ip['floatingip']['id']
                    floatingip_ip = floating_ip['floatingip']['floating_ip_address']
                    pprint(f'Assigning new floating ip {floatingip_ip} for this vm')
            else:
                floatingip_id = floating_ips[0]
            fixed_ip = None
            timeout = 0
            while fixed_ip is None:
                pprint("Waiting 5 seconds for vm to get an ip")
                sleep(5)
                timeout += 5
                if timeout >= 240:
                    error("Time out waiting for vm to get an ip")
                    break
                vm = nova.servers.get(instance.id)
                if vm.status.lower() == 'error':
                    msg = "Vm reports error status"
                    return {'result': 'failure', 'reason': msg}
                for key in list(vm.addresses):
                    entry1 = vm.addresses[key]
                    for entry2 in entry1:
                        if entry2['OS-EXT-IPS:type'] == 'fixed':
                            fixed_ip = entry2['addr']
                            break
            if fixed_ip is not None:
                fixedports = [i['id'] for i in neutron.list_ports()['ports']
                              if i['fixed_ips'] and i['fixed_ips'][0]['ip_address'] == fixed_ip]
                port_id = fixedports[0]
                neutron.update_floatingip(floatingip_id, {'floatingip': {'port_id': port_id}})
                if 'api_ip' in overrides:
                    api_ip = overrides['api_ip']
                    neutron.update_port(port_id, {'port': {'allowed_address_pairs': [{'ip_address': api_ip}]}})
            if not securitygroups:
                default_securitygroups = [s for s in neutron.list_security_groups()['security_groups']
                                          if s['name'] == 'default' and s['tenant_id'] == tenant_id]
                if default_securitygroups:
                    securitygroup = default_securitygroups[0]
                    securitygroupid = securitygroup['id']
                    sshrule = {'security_group_rule': {'direction': 'ingress', 'security_group_id': securitygroupid,
                                                       'port_range_min': '22', 'port_range_max': '22',
                                                       'protocol': 'tcp', 'remote_group_id': None,
                                                       'remote_ip_prefix': '0.0.0.0/0'}}
                    icmprule = {'security_group_rule': {'direction': 'ingress', 'security_group_id': securitygroupid,
                                                        'protocol': 'icmp', 'remote_group_id': None,
                                                        'remote_ip_prefix': '0.0.0.0/0'}}
                    try:
                        neutron.create_security_group_rule(sshrule)
                        neutron.create_security_group_rule(icmprule)
                    except:
                        pass
        if not start:
            vm.stop()
        return {'result': 'success'}

    def start(self, name):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        vm.start()
        return {'result': 'success'}

    def stop(self, name, soft=False):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        vm.stop()
        return {'result': 'success'}

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
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        vm.reboot()
        return {'result': 'success'}

    def info_host(self):
        print("not implemented")
        return {}

    def status(self, name):
        print("not implemented")
        return

    def list(self):
        vms = []
        nova = self.nova
        vmslist = nova.servers.list()
        for vm in vmslist:
            try:
                vms.append(self.info(vm.name, vm=vm))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        url = vm.get_vnc_console('novnc')['console']['url']
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = f"Open the following url:\n{url}" if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint(f"Opening url: {url}")
            webbrowser.open(url, new=2, autoraise=True)
        return

    def serialconsole(self, name, web=False):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        cmd = vm.get_console_output()
        if web:
            return cmd
        print(cmd)

    def dnsinfo(self, name):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            return None, None
        dnsclient, domain = None, None
        metadata = vm.metadata
        if metadata is not None:
            if 'dnsclient' in metadata:
                dnsclient = metadata['dnsclient']
            if 'domain' in metadata:
                domain = metadata['domain']
        return dnsclient, domain

    def info(self, name, vm=None, debug=False):
        nova = self.nova
        cinder = self.cinder
        if vm is None:
            try:
                vm = nova.servers.find(name=name)
            except:
                error(f"VM {name} not found")
                return {}
        yamlinfo = {'name': vm.name, 'status': vm.status, 'project': self.project, 'id': vm.id}
        if vm.status.lower() == 'error':
            try:
                yamlinfo['error'] = vm.fault['message']
            except:
                pass

        source = ''
        if 'id' in vm.image:
            source = vm.image['id']
            try:
                source = self.glance.images.get(vm.image['id']).name
            except:
                pass
        yamlinfo['iso' if source.endswith('.iso') else 'image'] = source
        yamlinfo['creationdate'] = vm.created
        yamlinfo['user'] = common.get_user(source)
        flavor = nova.flavors.get(vm.flavor['id'])
        yamlinfo['flavor'] = flavor.name
        yamlinfo['memory'] = flavor.ram
        yamlinfo['cpus'] = flavor.vcpus
        yamlinfo['nets'] = []
        index = 0
        for key in list(vm.addresses):
            entry1 = vm.addresses[key]
            for entry2 in entry1:
                mac = entry2['OS-EXT-IPS-MAC:mac_addr']
                if entry2['OS-EXT-IPS:type'] == 'floating':
                    yamlinfo['ip'] = entry2['addr']
                else:
                    net = {'device': f'eth{index}', 'mac': mac, 'net': key, 'type': entry2['addr']}
                    if index == 0:
                        yamlinfo['privateip'] = entry2['addr']
                    yamlinfo['nets'].append(net)
                    index += 1
        if 'ip' not in yamlinfo and 'privateip' in yamlinfo:
            yamlinfo['ip'] = yamlinfo['privateip']
        disks = []
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            diskid = disk['id']
            try:
                volume = cinder.volumes.get(diskid)
            except cinderclient.exceptions.NotFound:
                disks.append({'device': 'N/A', 'size': 'N/A', 'format': 'N/A', 'type': 'N/A', 'path': diskid})
                continue
            disksize = volume.size
            devname = volume.name
            _type = volume.volume_type
            _format = volume.availability_zone
            volinfo = volume.to_dict()
            if 'volume_image_metadata' in volinfo and 'image_name' in volinfo['volume_image_metadata']:
                source = volinfo['volume_image_metadata']['image_name']
                yamlinfo['iso' if source.endswith('.iso') else 'image'] = source
            disks.append({'device': devname, 'size': disksize, 'format': _format, 'type': _type, 'path': diskid})
        if disks:
            yamlinfo['disks'] = disks
        metadata = vm.metadata
        if metadata is not None:
            for entry in metadata:
                yamlinfo[entry] = metadata[entry]
        if debug:
            yamlinfo['debug'] = str(vars(vm))
        return yamlinfo

    def ip(self, name):
        print("not implemented")

    def volumes(self, iso=False):
        images = []
        isos = []
        glance = self.glance
        for img in glance.images.list():
            imagename = img.name
            if imagename.endswith('.iso'):
                isos.append(imagename)
            else:
                images.append(imagename)
        if iso:
            return sorted(isos)
        else:
            return sorted(images)

    def delete(self, name, snapshots=False):
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        floating_ips = {}
        try:
            fips = self.neutron.list_floatingips()
            floating_ips.update({f['floating_ip_address']: f['id'] for f in fips['floatingips']})
        except:
            # OVH does not provide floating ip networks, so the next error will occur
            # if some tries to get floating ip list:
            # neutronclient.common.exceptions.NotFound: The resource could not be found
            pass
        vm_floating_ips = []
        for key in list(vm.addresses):
            entry1 = vm.addresses[key]
            for entry2 in entry1:
                if entry2['OS-EXT-IPS:type'] == 'floating':
                    vm_floating_ips.append(entry2['addr'])
        vm.delete()
        for floating in vm_floating_ips:
            floatingid = floating_ips[floating]
            try:
                self.neutron.delete_floatingip(floatingid)
            except Exception as e:
                error(f"Hit {str(e)} when trying to delete floating {floating}")
        index = 0
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            try:
                volume = cinder.volumes.get(disk['id'])
            except cinderclient.exceptions.NotFound:
                continue
            for attachment in volume.attachments:
                if attachment['server_id'] == vm.id:
                    cinder.volumes.detach(volume, attachment['attachment_id'])
            cinder.volumes.delete(disk['id'])
            index += 1
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")

    def update_metadata(self, name, metatype, metavalue, append=False):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return
        metadata = vm.metadata
        if append and metatype in metadata:
            metadata[metatype] += f",{metavalue}"
        else:
            metadata[metatype] = metavalue
        nova.servers.set_meta(vm.id, metadata)
        return {'result': 'success'}

    def update_memory(self, name, memory):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        currentflavor = nova.flavors.get(vm.flavor['id'])
        if currentflavor.ram >= int(memory):
            warning("No need to resize")
            return {'result': 'success'}
        allflavors = [f for f in nova.flavors.list() if f != currentflavor]
        flavors = [flavor for flavor in allflavors if flavor.ram >= int(memory) and flavor.vcpus >= currentflavor.vcpus]
        if flavors:
            flavor = flavors[0]
            pprint(f"Using flavor {flavor.name}")
            vm.resize(flavor.id)
            resizetimeout = 40
            resizeruntime = 0
            vmstatus = ''
            while vmstatus != 'VERIFY_RESIZE':
                if resizeruntime >= resizetimeout:
                    error("Time out waiting for resize to finish")
                    return {'result': 'failure', 'reason': "Time out waiting for resize to finish"}
                vm = nova.servers.find(name=name)
                vmstatus = vm.status
                sleep(2)
                pprint(f"Waiting for vm {name} to be in verify_resize")
                resizeruntime += 2
            vm.confirm_resize()
            return {'result': 'success'}
        else:
            error("Couldn't find matching flavor for this amount of memory")
            return {'result': 'failure', 'reason': "Couldn't find matching flavor for this amount of memory"}

    def update_flavor(self, name, flavor):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        currentflavor = nova.flavors.get(vm.flavor['id'])
        if currentflavor == flavor:
            return {'result': 'success'}
        flavors = [f for f in nova.flavors.list() if f.name == flavor]
        if not flavors:
            error(f"Flavor {flavor} doesn't exist")
            return {'result': 'failure', 'reason': f"Flavor {flavor} doesn't exist"}
        else:
            flavorid = flavors[0].id
            vm.resize(flavorid)
            resizetimeout = 40
            resizeruntime = 0
            vmstatus = ''
            while vmstatus != 'VERIFY_RESIZE':
                if resizeruntime >= resizetimeout:
                    error("Time out waiting for resize to finish")
                    return {'result': 'failure', 'reason': "Time out waiting for resize to finish"}
                vm = nova.servers.find(name=name)
                vmstatus = vm.status
                sleep(2)
                pprint(f"Waiting for vm {name} to be in verify_resize")
                resizeruntime += 2
            vm.confirm_resize()
            return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        currentflavor = nova.flavors.get(vm.flavor['id'])
        if currentflavor.vcpus >= numcpus:
            warning("No need to resize")
            return {'result': 'success'}
        allflavors = [f for f in nova.flavors.list() if f != currentflavor]
        flavors = [flavor for flavor in allflavors if flavor.ram >= currentflavor.ram and flavor.vcpus >= numcpus]
        if flavors:
            flavor = flavors[0]
            pprint(f"Using flavor {flavor.name}")
            vm.resize(flavor.id)
            resizetimeout = 40
            resizeruntime = 0
            vmstatus = ''
            while vmstatus != 'VERIFY_RESIZE':
                if resizeruntime >= resizetimeout:
                    error("Time out waiting for resize to finish")
                    return {'result': 'failure', 'reason': "Time out waiting for resize to finish"}
                vm = nova.servers.find(name=name)
                vmstatus = vm.status
                sleep(2)
                pprint(f"Waiting for vm {name} to be in verify_resize")
                resizeruntime += 2
            vm.confirm_resize()
            return {'result': 'success'}
        else:
            error("Couldn't find matching flavor for this number of cpus")
            return {'result': 'failure', 'reason': "Couldn't find matching flavor for this number of cpus"}

    def update_start(self, name, start=True):
        print("not implemented")

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)

    def update_iso(self, name, iso):
        if iso is not None:
            iso_images = [img for img in self.glance.images.list() if img.name == iso]
            if iso_images:
                iso_image = iso_images[0]
                iso_id = iso_image.id
            else:
                msg = f"Iso {iso} not found.Leaving..."
                error(msg)
                return {'result': 'failure', 'reason': msg}
        nova = self.nova
        cinder = self.cinder
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return
        currentiso = None
        if 'id' in vm.image:
            source = vm.image['id']
            try:
                source = self.glance.images.get(vm.image['id']).name
                if source.endswith('.iso'):
                    currentiso = source
                    warning("Update of iso set with glance are not supported")
                    return
            except:
                pass
        iso_name = ''
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            diskid = disk['id']
            try:
                volume = cinder.volumes.get(diskid)
            except cinderclient.exceptions.NotFound:
                continue
            volinfo = volume.to_dict()
            if 'volume_image_metadata' in volinfo and 'image_name' in volinfo['volume_image_metadata']:
                source = volinfo['volume_image_metadata']['image_name']
                if source.endswith('.iso'):
                    currentiso = source
                    iso_name = volume.name
        if iso is None:
            if currentiso is None:
                return
            else:
                iso_volume = [volume for volume in cinder.volumes.list() if volume.name == iso_name][0]
                iso_volume.detach()
                iso_volume.delete()
        elif currentiso is not None and currentiso == iso:
            return
        else:
            volumes = [volume for volume in cinder.volumes.list() if volume.name == iso_name]
            if volumes:
                iso_volume = volumes[0]
                iso_volume.detach()
                iso_volume.delete()
            index = len(vm._info.get('os-extended-volumes:volumes_attached', []))
            diskname = f"{name}-disk{index}"
            letter = chr(index + ord('a'))
            volume = cinder.volumes.create(name=diskname, size=10, imageRef=iso_id)
            self.cinder.volumes.set_bootable(volume.id, True)
            cinder.volumes.attach(volume, vm.id, f'/dev/vd{letter}', mode='rw')
            return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        glance = self.glance
        cinder = self.cinder
        glanceimage = None
        if image is not None:
            glanceimages = [img for img in glance.images.list() if img.name == image]
            if glanceimages:
                glanceimage = glanceimages[0]
            else:
                msg = f"you don't have image {image}"
                return {'result': 'failure', 'reason': msg}
        cinder.volumes.create(name=name, size=size, imageRef=glanceimage)
        return {'result': 'success'}

    def add_disk(self, name, size, pool=None, thin=True, image=None,
                 shareable=False, existing=None, interface='virtio', novm=False, overrides={}, diskname=None):
        glance = self.glance
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        glanceimage = None
        if image is not None:
            glanceimages = [img for img in glance.images.list() if img.name == image]
            if glanceimages:
                glanceimage = glanceimages[0]
            else:
                msg = f"you don't have image {image}"
                return {'result': 'failure', 'reason': msg}
        index = len(vm._info.get('os-extended-volumes:volumes_attached', []))
        diskname = f"{name}-disk{index}"
        letter = chr(index + ord('a'))
        volume = cinder.volumes.create(name=diskname, size=size, imageRef=glanceimage.id)
        cinder.volumes.attach(volume, vm.id, f'/dev/vd{letter}', mode='rw')
        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        cinder = self.cinder
        nova = self.nova
        if name is None:
            volumes = [volume for volume in cinder.volumes.list() if volume.name == diskname]
            if volumes:
                volume = volumes[0]
            else:
                msg = f"Disk {diskname} not found"
                return {'result': 'failure', 'reason': msg}
            if volume.attachments:
                volume.detach()
            cinder.volumes.delete(volume.id)
            return {'result': 'success'}
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            volume = cinder.volumes.get(disk['id'])
            if diskname == volume.name:
                for attachment in volume.attachments:
                    if attachment['server_id'] == vm.id:
                        cinder.volumes.detach(volume, attachment['attachment_id'])
                cinder.volumes.delete(disk['id'])
                return {'result': 'success'}
        msg = f"Disk {diskname} not found in {name}"
        error(msg)
        return {'result': 'failure', 'reason': msg}

    def list_disks(self):
        volumes = {}
        cinder = self.cinder
        for volume in cinder.volumes.list():
            volumes[volume.name] = {'pool': volume.volume_type, 'path': volume.id}
        return volumes

    def add_nic(self, name, network, model='virtio'):
        print("not implemented")

    def delete_nic(self, name, interface):
        print("not implemented")

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")

    def delete_image(self, image, pool=None):
        pprint(f"Deleting image {image}")
        glance = self.glance
        for img in glance.images.list():
            if img.name == image:
                glance.images.delete(img.id)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': f"Image {image} not found"}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
        downloaded = False
        shortimage = os.path.basename(url).split('?')[0]
        if name is not None and name.endswith('iso'):
            shortimage = name
        if [i for i in self.glance.images.list() if i['name'] == shortimage]:
            pprint(f"Image {shortimage} already there")
            return {'result': 'success'}
        if os.path.exists(url):
            pprint(f"Using {url} as path")
        elif not os.path.exists(f'/tmp/{shortimage}'):
            downloaded = True
            downloadcmd = f"curl -Lo /tmp/{shortimage} -f '{url}'"
            code = os.system(downloadcmd)
            if code != 0:
                return {'result': 'failure', 'reason': "Unable to download indicated image"}
        image_path = os.path.abspath(url) if os.path.exists(url) else f'/tmp/{shortimage}'
        need_uncompress = any(shortimage.endswith(suffix) for suffix in ['.gz', '.xz', '.bz2', '.zst'])
        if need_uncompress:
            extension = os.path.splitext(shortimage)[1].replace('.', '')
            executable = {'xz': 'unxz', 'gz': 'gunzip', 'bz2': 'bunzip2', 'zst': 'zstd'}
            flag = '--decompress' if extension == 'zstd' else '-f'
            executable = executable[extension]
            if which(executable) is not None:
                uncompresscmd = f"{executable} {flag} {image_path}"
                os.system(uncompresscmd)
            else:
                error(f"{executable} not found. Can't uncompress image")
                return {'result': 'failure', 'reason': f"{executable} not found. Can't uncompress image"}
            shortimage = shortimage.replace('.gz', '').replace('.xz', '').replace('.bz2', '').replace('.zst', '')
            image_path = image_path.replace('.gz', '').replace('.xz', '').replace('.bz2', '').replace('.zst', '')
        disk_format = 'iso' if shortimage.endswith('iso') else 'qcow2'
        if cmd is not None:
            pprint(f"Running {cmd} on {image_path}")
            if disk_format == 'iso':
                if image_path not in cmd:
                    cmd += f" {image_path}"
                os.system(cmd)
            elif which('virt-customize') is not None:
                cmd = f"virt-customize -a {image_path} --run-command '{cmd}'"
                os.system(cmd)
        glanceimage = self.glance.images.create(name=shortimage, disk_format=disk_format, container_format='bare')
        self.glance.images.upload(glanceimage.id, open(image_path, 'rb'))
        if downloaded:
            os.remove(f'/tmp/{shortimage}')
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        if nat:
            externalnets = [n for n in self.neutron.list_networks()['networks'] if n['router:external']]
            externalnet_id = externalnets[0]['id'] if externalnets else None
            routers = [router for router in self.neutron.list_routers()['routers'] if router['name'] == 'kvirt']
            router_id = routers[0]['id'] if routers else None
        try:
            ip_network(cidr)
        except:
            return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
        neutron = self.neutron
        network_id = None
        networks = {net['name']: net['id'] for net in neutron.list_networks()['networks']}
        if name not in networks:
            network = {'name': name, 'admin_state_up': True}
            if 'port_security_enabled' in overrides:
                network['port_security_enabled'] = bool(overrides['port_security_enabled'])
            network = neutron.create_network({'network': network})
            network_id = network['network']['id']
            tenant_id = network['network']['tenant_id']
        else:
            warning("Network already there. Creating subnet")
        if cidr is not None:
            if network_id is None:
                network_id = networks[name]
            cidrs = [s['cidr'] for s in neutron.list_subnets()['subnets'] if s['network_id'] == network_id]
            if cidr not in cidrs:
                subnet = {'name': cidr, 'network_id': network_id, 'ip_version': 4, "cidr": cidr, 'enable_dhcp': dhcp}
                if domain is not None:
                    subnet['dns_nameservers'] = [domain]
                subnet = neutron.create_subnet({'subnet': subnet})
                subnet_id = subnet['subnet']['id']
                tenant_id = subnet['subnet']['tenant_id']
            else:
                warning("Subnet already there. Leaving")
                return {'result': 'success'}
        if nat:
            if externalnet_id is not None:
                if router_id is None:
                    router = {'name': 'kvirt', 'tenant_id': tenant_id}
                    # router['external_gateway_info'] = {"network_id": externalnet_id, "enable_snat": True}
                    router = neutron.create_router({'router': router})
                    router_id = router['router']['id']
                    router_dict = {"network_id": externalnet_id}
                    neutron.add_gateway_router(router_id, router_dict)
                neutron.add_interface_router(router_id, {'subnet_id': subnet_id})
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        neutron = self.neutron
        routers = [router for router in self.neutron.list_routers()['routers'] if router['name'] == 'kvirt']
        router_id = routers[0]['id'] if routers else None
        if router_id is not None:
            router = routers[0]
        networks = neutron.list_networks(name=name)
        if not networks:
            return {'result': 'failure', 'reason': f'Network {name} not found'}
        network_id = networks['networks'][0]['id']
        if cidr is None:
            ports = [p for p in neutron.list_ports()['ports']
                     if p['device_owner'] != 'network:router_interface' and network_id == network_id]
            if ports:
                return {'result': 'failure', 'reason': 'Non router ports still present in this network'}
            if router_id is not None:
                floating_ips = [f['id'] for f in neutron.list_floatingips()['floatingips']
                                if f['router_id'] == router_id]
                if floating_ips:
                    return {'result': 'failure', 'reason': 'Floating ips still in use through router on this network'}
                ports = [p for p in neutron.list_ports()['ports']
                         if p['device_id'] == router_id and network_id == network_id]
                routerports = len(ports)
                for port in ports:
                    neutron.remove_interface_router(router_id, {'port_id': port['id']})
                    routerports -= 1
            neutron.delete_network(network_id)
        else:
            subnets = [s['id'] for s in neutron.list_subnets()['subnets']
                       if s['network_id'] == network_id and s['cidr'] == cidr]
            if subnets:
                subnet_id = subnets[0]
                if router_id is not None:
                    floating_ips = [f['id'] for f in neutron.list_floatingips()['floatingips']
                                    if f['router_id'] == router_id]
                    if floating_ips:
                        return {'result': 'failure',
                                'reason': 'Floating ips still in use through router on this network'}
                    ports = [p for p in neutron.list_ports()['ports'] if p['device_id'] == router_id]
                    routerports = len(ports)
                    for port in ports:
                        if 'fixed_ips' in port and subnet_id in port['fixed_ips'][0].values():
                            neutron.remove_interface_router(router_id, {'port_id': port['id']})
                            routerports -= 1
                neutron.delete_subnet(subnet_id)
        if routerports == 0:
            if router['external_gateway_info']:
                neutron.remove_gateway_router(router_id)
            pprint("Removing unused router kvirt")
            neutron.delete_router(router_id)
        return {'result': 'success'}

    def list_pools(self):
        print("not implemented")
        return []

    def list_networks(self):
        networks = {}
        neutron = self.neutron
        for subnet in neutron.list_subnets()['subnets']:
            subnetname = subnet['name']
            subnet_id = subnet['id']
            cidr = subnet['cidr']
            dhcp = subnet['enable_dhcp']
            network_id = subnet['network_id']
            network = neutron.show_network(network_id)
            mode = 'external' if network['network']['router:external'] else 'isolated'
            # networks = [n for n in neutron.list_networks()['networks'] if n['router:external']]
            networkname = neutron.show_network(network_id)['network']['name']
            ports = [p for p in neutron.list_ports()['ports']
                     if p['device_owner'] == 'network:router_interface' and network_id == network_id]
            for port in ports:
                if 'fixed_ips' in port and subnet_id in port['fixed_ips'][0].values():
                    mode = 'nat'
                    break
            if networkname in networks:
                networks[networkname]['domain'] = f"{networks[networkname]['domain']}, {subnetname}"
            else:
                networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': subnetname, 'type': 'routed',
                                         'mode': mode}
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        if self.debug and networkinfo:
            network = [net for net in self.neutron.list_networks()['networks'] if net['name'] == name][0]
            print(network)
            subnets = [sub for sub in self.neutron.list_subnets()['subnets'] if sub['id'] in network['subnets']]
            for subnet in subnets:
                print(subnet)
        return networkinfo

    def list_subnets(self):
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        print("not implemented")

    def network_ports(self, name):
        print("not implemented")

    def vm_ports(self, name):
        return ['default']

    def get_pool_path(self, pool):
        print("not implemented")

    def list_flavors(self):
        nova = self.nova
        nova.flavors.list
        flavors = [[flavor.name, flavor.vcpus, flavor.ram] for flavor in nova.flavors.list()]
        return flavors

    def export(self, name, image=None):
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            volume = cinder.volumes.get(disk['id'])
            for attachment in volume.attachments:
                newname = image if image is not None else volume.name.replace('-disk0', '')
                volume.upload_to_image(True, newname, 'bare', 'qcow2')
                status = ''
                timeout = 0
                while status != 'available':
                    status = cinder.volumes.get(disk['id']).status
                    pprint("Waiting 5 seconds for export to complete")
                    sleep(5)
                    timeout += 5
                    if timeout >= 90:
                        error("Time out waiting for export to complete")
                        break
                break
        return {'result': 'success'}

    def list_dns(self, domain):
        return []

    def create_network_port(self, name, network, ip=None, floating=False, security=True):
        neutron = self.neutron
        matchingports = [i for i in neutron.list_ports()['ports'] if i['name'] == name]
        if matchingports:
            msg = f"Port {name} already exists"
            pprint(msg)
            return {'result': 'success'}
        networks = [net for net in neutron.list_networks()['networks'] if net['name'] == network]
        if not networks:
            msg = f"Network {network} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        else:
            network = networks[0]
        network_id = network['id']
        port = {'name': name, "admin_state_up": True, "network_id": network_id, 'port_security_enabled': security}
        if ip is not None:
            for subnet in neutron.list_subnets()['subnets']:
                subnet_name = subnet['name']
                subnet_id = subnet['id']
                cidr = subnet['cidr']
                if network_id == subnet['network_id'] and ip_address(ip) in ip_network(cidr):
                    msg = f"Using matching subnet {subnet_name} with cidr {cidr}"
                    pprint(msg)
                    port['fixed_ips'] = [{'ip_address': ip, 'subnet_id': subnet_id}]
        result = neutron.create_port({'port': port})
        port_id = result['port']['id']
        result = {'result': 'success'}
        if floating:
            tenant_id = network['tenant_id']
            if self.external_network is not None:
                network_id = self.external_network
                external_networks = [n for n in neutron.list_networks()['networks'] if n['router:external']
                                     if n['name'] == self.external_network]
            else:
                external_networks = [n for n in neutron.list_networks()['networks'] if n['router:external']]
            if external_networks:
                network_id = external_networks[0]['id']
            else:
                msg = "No valid external network found for floating ips"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            args = dict(floating_network_id=network_id, tenant_id=tenant_id, port_id=port_id)
            floating_ip = neutron.create_floatingip(body={'floatingip': args})
            floatingip_ip = floating_ip['floatingip']['floating_ip_address']
            pprint(f'Assigning new floating ip {floatingip_ip} for this port')
            result['floating'] = floatingip_ip
        return result

    def delete_network_port(self, name):
        neutron = self.neutron
        matchingports = [i for i in neutron.list_ports()['ports'] if i['name'] == name]
        if not matchingports:
            msg = f"Port {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        self.neutron.delete_port(matchingports[0]['id'])

    def create_bucket(self, bucket, public=False):
        swift = self.swift
        if bucket in self.list_buckets():
            error(f"Bucket {bucket} already exists")
            return
        headers = {"X-Container-Read": ".r:*"} if public else {}
        swift.put_container(bucket, headers=headers)

    def delete_bucket(self, bucket):
        swift = self.swift
        try:
            containerinfo = swift.get_container(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return
        for obj in containerinfo[1]:
            obj_name = obj['name']
            pprint(f"Deleting object {obj_name} in bucket {bucket}")
            swift.delete_object(bucket, obj_name)
        swift.delete_container(bucket)

    def delete_from_bucket(self, bucket, path):
        swift = self.swift
        try:
            containerinfo = swift.get_container(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return
        for obj in containerinfo[1]:
            obj_name = obj['name']
            if path == obj_name:
                swift.delete_object(bucket, obj_name)
                break

    def download_from_bucket(self, bucket, path):
        swift = self.swift
        try:
            resp_headers, obj_contents = swift.get_object(bucket, path)
        except Exception as e:
            error(f"Got {e}")
            return
        with open(path, 'wb') as f:
            f.write(obj_contents)

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        swift = self.swift
        if not os.path.exists(path):
            error(f"Invalid path {path}")
            return
        dest = os.path.basename(path)
        with open(path, 'rb') as f:
            swift.put_object(bucket, dest, contents=f, content_type='text/plain')
        if public:
            headers = {"X-Container-Read": ".r:*"}
            swift.post_container(bucket, headers=headers)

    def list_buckets(self):
        swift = self.swift
        return [container['name'] for container in swift.get_account()[1]]

    def list_bucketfiles(self, bucket):
        swift = self.swift
        try:
            containerinfo = swift.get_container(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return []
        return [obj['name'] for obj in containerinfo[1]]

    def public_bucketfile_url(self, bucket, path):
        swift_url = self.swift.http_connection()[0].geturl()
        return f"{swift_url}/{bucket}/{path}"

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        print("not implemented")

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        neutron = self.neutron
        networks = [net for net in neutron.list_networks()['networks'] if net['name'] == name]
        if not networks:
            msg = f"Network {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        else:
            network = networks[0]
            network_id = network['id']
        network_data = {}
        if 'port_security_enabled' in overrides and isinstance(overrides['port_security_enabled'], bool):
            network_data['port_security_enabled'] = overrides['port_security_enabled']
        if 'mtu' in overrides and isinstance(overrides['port_security_enabled'], int):
            network_data['mtu'] = overrides['mtu']
        if 'description' in overrides:
            network_data['description'] = str(overrides['description'])
        if 'tags' in overrides and isinstance(overrides['tags'], list):
            network_data['tags'] = overrides['tags']
        if 'availability_zones' in overrides and isinstance(overrides['availability_zones'], list):
            network_data['availability_zones'] = overrides['availability_zones']
        if 'availability_zone_hints' in overrides and isinstance(overrides['availability_zone_hints'], list):
            network_data['availability_zone_hints'] = overrides['availability_zone_hints']
        if network_data:
            neutron.update_network(network_id, {'network': network_data})
        subnets = [sub for sub in self.neutron.list_subnets()['subnets'] if sub['id'] in network['subnets']]
        if subnets:
            subnet_data = {}
            subnet = subnets[0]
            subnet_id = subnet['id']
            currentdhcp = subnet['enable_dhcp']
            if dhcp is not None:
                if not dhcp and currentdhcp:
                    subnet_data['enable_dhcp'] = False
                if dhcp and not currentdhcp:
                    subnet_data['enable_dhcp'] = True
            if 'dns_nameservers' in overrides and isinstance(overrides['dns_nameservers'], list):
                subnet_data['dns_nameservers'] = overrides['dns_nameservers']
            if 'dns' in overrides and isinstance(overrides['dns'], list):
                subnet_data['dns_nameservers'] = overrides['dns']
            if subnet_data:
                neutron.update_subnet(subnet_id, {'subnet': subnet_data})
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        neutron = self.neutron
        return [s['name'] for s in neutron.list_security_groups()['security_groups']]

    def create_security_group(self, name, overrides={}):
        neutron = self.neutron
        security_group = {'name': name}
        sg = neutron.create_security_group({'security_group': security_group})
        sgid = sg['security_group']['id']
        icmprule = {'security_group_rule': {'direction': 'ingress', 'security_group_id': sgid,
                                            'protocol': 'icmp', 'remote_group_id': None,
                                            'remote_ip_prefix': '0.0.0.0/0'}}
        neutron.create_security_group_rule(icmprule)
        ports = overrides.get('ports', [])
        for port in ports:
            if isinstance(port, str) or isinstance(port, int):
                protocol = 'tcp'
                fromport, toport = port, port
            elif isinstance(port, dict):
                protocol = port.get('protocol', 'tcp')
                fromport = port.get('from')
                toport = port.get('to') or fromport
                if fromport is None:
                    warning(f"Missing from in {ports}. Skipping")
                    continue
            pprint(f"Adding rule from {fromport} to {toport} protocol {protocol}")
            rule = {'security_group_rule': {'direction': 'ingress', 'security_group_id': sgid,
                                            'port_range_min': str(fromport), 'port_range_max': str(toport),
                                            'protocol': protocol, 'remote_group_id': None,
                                            'remote_ip_prefix': '0.0.0.0/0'}}
            neutron.create_security_group_rule(rule)
        return {'result': 'success'}

    def delete_security_group(self, name):
        sgs = [sg for sg in self.neutron.list_security_groups()['security_groups'] if sg['name'] == name]
        if sgs:
            sgs[0].delete()
        return {'result': 'success'}

    def update_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def provider_network(self, name):
        net = self.nova.neutron.find_network(name=name)
        return True if net.to_dict()['router:external'] else False

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
