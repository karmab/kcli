#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Openstack Provider Class
"""

from distutils.spawn import find_executable
from netaddr import IPNetwork
from kvirt import common
from kvirt.common import pprint, error, warning
from kvirt.defaults import METADATA_FIELDS
from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client as glanceclient
from cinderclient import client as cinderclient
from novaclient import client as novaclient
from neutronclient.v2_0.client import Client as neutronclient
import os
from time import sleep
import webbrowser
from ipaddress import ip_address, ip_network


class Kopenstack(object):
    """

    """
    def __init__(self, host='127.0.0.1', version='2', port=None, user='root', password=None, debug=False, project=None,
                 domain='Default', auth_url=None, ca_file=None, external_network=None):
        self.debug = debug
        self.host = host
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(auth_url=auth_url, username=user, password=password, project_name=project,
                                        user_domain_name=domain, project_domain_name=domain)
        if ca_file is not None:
            sess = session.Session(auth=auth, verify=os.path.expanduser(ca_file))
        else:
            sess = session.Session(auth=auth)
        self.nova = novaclient.Client(version, session=sess)
        self.glance = glanceclient(version, session=sess)
        self.cinder = cinderclient.Client(version, session=sess)
        self.neutron = neutronclient(session=sess)
        self.conn = self.nova
        self.project = project
        self.external_network = external_network
        return

# should cleanly close your connection, if needed
    def close(self):
        print("not implemented")
        return

    def exists(self, name):
        return

    def net_exists(self, name):
        neutron = self.neutron
        networks = neutron.list_networks(name=name)
        if not networks:
            False
        return True

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', plan='kvirt', flavor=None,
               cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=None, cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=[], storemetadata=False, sharedfolders=[], kernel=None, initrd=None,
               cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False, numamode=None,
               numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[]):
        glance = self.glance
        nova = self.nova
        neutron = self.neutron
        try:
            nova.servers.find(name=name)
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        except:
            pass
        allflavors = [f for f in nova.flavors.list()]
        allflavornames = [flavor.name for flavor in allflavors]
        if flavor is None:
            flavors = [flavor for flavor in allflavors if flavor.ram >= memory and flavor.vcpus >= numcpus]
            flavor = flavors[0] if flavors else nova.flavors.find(name="m1.tiny")
            pprint("Using flavor %s" % flavor.name)
        elif flavor not in allflavornames:
            return {'result': 'failure', 'reason': "Flavor %s not found" % flavor}
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
                return {'result': 'failure', 'reason': "Network %s not found" % netname}
            nics.append({'net-id': net.id})
        if image is not None:
            glanceimages = [img for img in glance.images.list() if img.name == image]
            if glanceimages:
                glanceimage = glanceimages[0]
            else:
                msg = "you don't have image %s" % image
                return {'result': 'failure', 'reason': msg}
        block_dev_mapping = {}
        for index, disk in enumerate(disks):
            imageref = None
            diskname = "%s-disk%s" % (name, index)
            letter = chr(index + ord('a'))
            if isinstance(disk, int):
                disksize = disk
                diskthin = True
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
                diskthin = True
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
                diskthin = disk.get('thin', True)
            if index == 0 and image is not None:
                if not diskthin:
                    imageref = glanceimage.id
                else:
                    continue
            newvol = self.cinder.volumes.create(name=diskname, size=disksize, imageRef=imageref)
            block_dev_mapping['vd%s' % letter] = newvol.id
        key_name = 'kvirt'
        keypairs = [k.name for k in nova.keypairs.list()]
        if key_name not in keypairs:
            homekey = None
            if not os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME'])\
                    and not os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
                print("neither id_rsa.pub or id_dsa public keys found in your .ssh directory, you might have trouble "
                      "accessing the vm")
            else:
                if os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
                    homekey = open("%s/.ssh/id_rsa.pub" % os.environ['HOME']).read()
                else:
                    homekey = open("%s/.ssh/id_dsa.pub" % os.environ['HOME']).read()
                nova.keypairs.create(key_name, homekey)
        elif keypairs:
            key_name = keypairs[0]
            if key_name != 'kvirt':
                pprint('Using keypair %s' % key_name)
        else:
            error("Couldn't locate or create keypair for use. Leaving...")
            return {'result': 'failure', 'reason': "No usable keypair found"}
        userdata = None
        if cloudinit:
            if image is not None and common.needs_ignition(image):
                version = common.ignition_version(image)
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                           overrides=overrides, version=version, plan=plan, image=image)
            else:
                userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                            domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                            overrides=overrides, storemetadata=storemetadata)[0]
        meta = {x: metadata[x] for x in metadata if x in METADATA_FIELDS}
        instance = nova.servers.create(name=name, image=glanceimage, flavor=flavor, key_name=key_name, nics=nics,
                                       meta=meta, userdata=userdata, block_device_mapping=block_dev_mapping,
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
                    pprint('Assigning new floating ip %s for this vm' % floatingip_ip)
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
        return {'result': 'success'}

    def start(self, name):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.start()
        return {'result': 'success'}

    def stop(self, name):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.stop()
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")
        return

    def restart(self, name):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.reboot()
        return {'result': 'success'}

    def report(self):
        print("not implemented")
        return

    def status(self, name):
        print("not implemented")
        return

# should return a sorted list of name, state, ip, source, plan, profile, report
    def list(self):
        vms = []
        nova = self.nova
        vmslist = nova.servers.list()
        for vm in vmslist:
            vms.append(self.info(vm.name, vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        url = vm.get_vnc_console('novnc')['console']['url']
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
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        cmd = vm.get_console_output()
        if web:
            return cmd
        print(cmd)
        return

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
                error("VM %s not found" % name)
                return {}
        yamlinfo = {'name': vm.name, 'status': vm.status, 'project': self.project}
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
        yamlinfo['image'] = source
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
                    net = {'device': 'eth%s' % index, 'mac': mac, 'net': key, 'type': entry2['addr']}
                    if index == 0:
                        yamlinfo['privateip'] = entry2['addr']
                    yamlinfo['nets'].append(net)
                    index += 1
        if 'ip' not in yamlinfo and 'privateip' in yamlinfo:
            yamlinfo['ip'] = yamlinfo['privateip']
        disks = []
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            diskid = disk['id']
            volume = cinder.volumes.get(diskid)
            disksize = volume.size
            devname = volume.name
            disks.append({'device': devname, 'size': disksize, 'format': '', 'type': '', 'path': diskid})
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
        return None

    def volumes(self, iso=False):
        glanceimages = []
        glance = self.glance
        for img in glance.images.list():
            glanceimages.append(img.name)
        return sorted(glanceimages)

    def delete(self, name, snapshots=False):
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        floating_ips = {f['floating_ip_address']: f['id'] for f in self.neutron.list_floatingips()['floatingips']}
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
                error("Hit %s when trying to delete floating %s" % (str(e), floating))
        index = 0
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            volume = cinder.volumes.get(disk['id'])
            for attachment in volume.attachments:
                if attachment['server_id'] == vm.id:
                    cinder.volumes.detach(volume, attachment['attachment_id'])
            cinder.volumes.delete(disk['id'])
            index += 1
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return
        metadata = vm.metadata
        if append and metatype in metadata:
            metadata[metatype] += ",%s" % metavalue
        else:
            metadata[metatype] = metavalue
        nova.servers.set_meta(vm.id, metadata)
        return {'result': 'success'}

    def update_memory(self, name, memory):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        currentflavor = nova.flavors.get(vm.flavor['id'])
        if currentflavor.ram >= int(memory):
            warning("No need to resize")
            return {'result': 'success'}
        allflavors = [f for f in nova.flavors.list() if f != currentflavor]
        flavors = [flavor for flavor in allflavors if flavor.ram >= int(memory) and flavor.vcpus >= currentflavor.vcpus]
        if flavors:
            flavor = flavors[0]
            pprint("Using flavor %s" % flavor.name)
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
                pprint("Waiting for vm %s to be in verify_resize" % name)
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
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        currentflavor = nova.flavors.get(vm.flavor['id'])
        if currentflavor == flavor:
            return {'result': 'success'}
        flavors = [f for f in nova.flavors.list() if f.name == flavor]
        if not flavors:
            error("Flavor %s doesn't exist" % flavor)
            return {'result': 'failure', 'reason': "Flavor %s doesn't exist" % flavor}
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
                pprint("Waiting for vm %s to be in verify_resize" % name)
                resizeruntime += 2
            vm.confirm_resize()
            return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        currentflavor = nova.flavors.get(vm.flavor['id'])
        if currentflavor.vcpus >= numcpus:
            warning("No need to resize")
            return {'result': 'success'}
        allflavors = [f for f in nova.flavors.list() if f != currentflavor]
        flavors = [flavor for flavor in allflavors if flavor.ram >= currentflavor.ram and flavor.vcpus >= numcpus]
        if flavors:
            flavor = flavors[0]
            pprint("Using flavor %s" % flavor.name)
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
                pprint("Waiting for vm %s to be in verify_resize" % name)
                resizeruntime += 2
            vm.confirm_resize()
            return {'result': 'success'}
        else:
            error("Couldn't find matching flavor for this number of cpus")
            return {'result': 'failure', 'reason': "Couldn't find matching flavor for this number of cpus"}

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
        glance = self.glance
        cinder = self.cinder
        image = None
        if image is not None:
            glanceimages = [img for img in glance.images.list() if img.name == image]
            if glanceimages:
                glanceimage = glanceimages[0]
            else:
                msg = "you don't have image %s" % image
                return {'result': 'failure', 'reason': msg}
        cinder.volumes.create(name=name, size=size, imageRef=glanceimage)
        return {'result': 'success'}

    def add_disk(self, name, size, pool=None, thin=True, image=None,
                 shareable=False, existing=None, interface='virtio', novm=False):
        glance = self.glance
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if image is not None:
            glanceimages = [img for img in glance.images.list() if img.name == image]
            if glanceimages:
                glanceimage = glanceimages[0]
            else:
                msg = "you don't have image %s" % image
                return {'result': 'failure', 'reason': msg}
        volume = cinder.volumes.create(name=name, size=size, imageRef=glanceimage)
        cinder.volumes.attach(volume, vm.id, '/dev/vdi', mode='rw')
        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        cinder = self.cinder
        nova = self.nova
        if name is None:
            volumes = [volume for volume in cinder.volumes.list() if volume.name == diskname]
            if volumes:
                volume = volumes[0]
            else:
                msg = "Disk %s not found" % diskname
                return {'result': 'failure', 'reason': msg}
            cinder.volumes.delete(volume.id)
            return {'result': 'success'}
        try:
            vm = nova.servers.find(name=name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            volume = cinder.volumes.get(disk['id'])
            if diskname == volume.name:
                for attachment in volume.attachments:
                    if attachment['server_id'] == vm.id:
                        cinder.volumes.detach(volume, attachment['attachment_id'])
                cinder.volumes.delete(disk['id'])
            return {'result': 'success'}

    def list_disks(self):
        volumes = {}
        cinder = self.cinder
        for volume in cinder.volumes.list():
            volumes[volume.name] = {'pool': 'default', 'path': volume.id}
        return volumes

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
        glance = self.glance
        for img in glance.images.list():
            if img.name == image:
                glance.images.delete(img.id)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': "Image %s not found" % image}

    def add_image(self, image, pool, short=None, cmd=None, name=None):
        shortimage = os.path.basename(image).split('?')[0]
        if [i for i in self.glance.images.list() if i['name'] == shortimage]:
            return {'result': 'success'}
        if not os.path.exists('/tmp/%s' % shortimage):
            downloadcmd = "curl -Lo /tmp/%s -f '%s'" % (shortimage, image)
            code = os.system(downloadcmd)
            if code != 0:
                return {'result': 'failure', 'reason': "Unable to download indicated image"}
        if shortimage.endswith('gz'):
            if find_executable('gunzip') is not None:
                uncompresscmd = "gunzip /tmp/%s" % (shortimage)
                os.system(uncompresscmd)
            else:
                error("gunzip not found. Can't uncompress image")
                return {'result': 'failure', 'reason': "gunzip not found. Can't uncompress image"}
            shortimage = shortimage.replace('.gz', '')
        glanceimage = self.glance.images.create(name=shortimage, disk_format='qcow2', container_format='bare')
        self.glance.images.upload(glanceimage.id, open('/tmp/%s' % shortimage, 'rb'))
        os.remove('/tmp/%s' % shortimage)
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        if nat:
            externalnets = [n for n in self.neutron.list_networks()['networks'] if n['router:external']]
            externalnet_id = externalnets[0]['id'] if externalnets else None
            routers = [router for router in self.neutron.list_routers()['routers'] if router['name'] == 'kvirt']
            router_id = routers[0]['id'] if routers else None
        try:
            IPNetwork(cidr)
        except:
            return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
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

    def delete_network(self, name=None, cidr=None):
        neutron = self.neutron
        routers = [router for router in self.neutron.list_routers()['routers'] if router['name'] == 'kvirt']
        router_id = routers[0]['id'] if routers else None
        if router_id is not None:
            router = routers[0]
        networks = neutron.list_networks(name=name)
        if not networks:
            return {'result': 'failure', 'reason': 'Network %s not found' % name}
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
        return

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
                networks[networkname]['domain'] = "%s, %s" % (networks[networkname]['domain'], subnetname)
            else:
                networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': subnetname, 'type': 'routed',
                                         'mode': mode}
        return networks

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
        print("not implemented")
        return

    def flavors(self):
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
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
            msg = "Port %s already exists" % name
            pprint(msg)
            return {'result': 'success'}
        networks = [net for net in neutron.list_networks()['networks'] if net['name'] == network]
        if not networks:
            msg = "Network %s not found" % network
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
                    msg = "Using matching subnet %s with cidr %s" % (subnet_name, cidr)
                    pprint(msg)
                    port['fixed_ips'] = [{'ip_address': ip, 'subnet_id': subnet_id}]
        result = neutron.create_port({'port': port})
        port_id = result['port']['id']
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
            pprint('Assigning new floating ip %s for this port' % floatingip_ip)
        return {'result': 'success'}

    def delete_network_port(self, name, network=None, floating=False):
        neutron = self.neutron
        matchingports = [i for i in neutron.list_ports()['ports'] if i['name'] == name]
        if not matchingports:
            msg = "Port %s not found" % name
            error(msg)
            return {'result': 'failure', 'reason': msg}
        self.neutron.delete_port(matchingports[0]['id'])
