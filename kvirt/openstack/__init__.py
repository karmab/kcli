#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Openstack Provider Class
"""

from netaddr import IPNetwork
from kvirt import common
from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client as glanceclient
from cinderclient import client as cinderclient
from novaclient import client as novaclient
from neutronclient.v2_0.client import Client as neutronclient
import os
from time import sleep
import webbrowser


class Kopenstack(object):
    """

    """
    def __init__(self, host='127.0.0.1', version='2', port=None, user='root', password=None, debug=False, project=None,
                 domain='Default', auth_url=None):
        self.debug = debug
        self.host = host
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(auth_url=auth_url, username=user, password=password, project_name=project,
                                        user_domain_name=domain, project_domain_name=domain)
        sess = session.Session(auth=auth)
        self.nova = novaclient.Client(version, session=sess)
        self.glance = glanceclient(version, session=sess)
        self.cinder = cinderclient.Client(version, session=sess)
        self.neutron = neutronclient(session=sess)
        self.conn = self.nova
        self.project = project
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
        return

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        neutron = self.neutron
        networks = neutron.list_networks(name=name)
        if not networks:
            False
        return True

    def disk_exists(self, pool, name):
        """

        :param pool:
        :param name:
        """
        print("not implemented")

    def create(self, name, virttype='kvm', profile='', plan='kvirt', flavor=None,
               cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', template=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=None, cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=None):
        """

        :param name:
        :param virttype:
        :param profile:
        :param plan:
        :param flavor:
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
        glance = self.glance
        nova = self.nova
        neutron = self.neutron
        try:
            nova.servers.find(name=name)
            common.pprint("VM %s already exists" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        except:
            pass
        allflavors = [f for f in nova.flavors.list()]
        allflavornames = [flavor.name for flavor in allflavors]
        if flavor is None:
            flavors = [flavor for flavor in allflavors if flavor.ram >= memory and flavor.vcpus == numcpus]
            flavor = flavors[0] if flavors else nova.flavors.find(name="m1.tiny")
            common.pprint("Using flavor %s" % flavor.name, color='green')
        elif flavor not in allflavornames:
            return {'result': 'failure', 'reason': "Flavor % not found" % flavor}
        else:
            flavor = nova.flavors.find(name=flavor)
        nics = []
        for net in nets:
            if isinstance(net, str):
                netname = net
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
            try:
                net = nova.neutron.find_network(name=netname)
            except Exception as e:
                common.pprint(e, color='red')
                return {'result': 'failure', 'reason': "Network %s not found" % netname}
            nics.append({'net-id': net.id})
        image = None
        if template is not None:
            images = [image for image in glance.images.list() if image.name == template]
            if images:
                image = images[0]
            else:
                msg = "you don't have template %s" % template
                return {'result': 'failure', 'reason': msg}
        block_dev_mapping = {}
        for index, disk in enumerate(disks):
            imageref = None
            diskname = "%s-disk%s" % (name, index)
            letter = chr(index + ord('a'))
            if isinstance(disk, int):
                disksize = disk
                diskthin = True
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
                diskthin = disk.get('thin', True)
            if index == 0 and template is not None:
                if not diskthin:
                    imageref = image.id
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
                common.pprint('Using keypair %s' % key_name, color='green')
        else:
            common.pprint('Couldnt locate or create keypair for use. Leaving...', color='red')
            return {'result': 'failure', 'reason': "No usable keypair found"}
        meta = {'plan': plan, 'profile': profile}
        userdata = None
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain,
                             reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides,
                             iso=False)
            userdata = open('/tmp/user-data', 'r').read().strip()
        instance = nova.servers.create(name=name, image=image, flavor=flavor, key_name=key_name, nics=nics, meta=meta,
                                       userdata=userdata, block_device_mapping=block_dev_mapping)
        tenant_id = instance.tenant_id
        floating_ips = [f['id'] for f in neutron.list_floatingips()['floatingips']
                        if f['port_id'] is None]
        if not floating_ips:
            network_id = None
            networks = [n for n in neutron.list_networks()['networks'] if n['router:external']]
            if networks:
                network_id = networks[0]['id']
            if network_id is not None and tenant_id is not None:
                args = dict(floating_network_id=network_id, tenant_id=tenant_id)
                floating_ip = neutron.create_floatingip(body={'floatingip': args})
                floatingip_id = floating_ip['floatingip']['id']
                floatingip_ip = floating_ip['floatingip']['floating_ip_address']
                common.pprint('Assigning new floating ip %s for this vm' % floatingip_ip, color='green')
        else:
            floatingip_id = floating_ips[0]
        fixed_ip = None
        timeout = 0
        while fixed_ip is None:
            common.pprint("Waiting 5 seconds for vm to get an ip", color='green')
            sleep(5)
            timeout += 5
            if timeout >= 80:
                common.pprint("Time out waiting for vm to get an ip", color='red')
                break
            vm = nova.servers.get(instance.id)
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
        securitygroups = [s for s in neutron.list_security_groups()['security_groups']
                          if s['name'] == 'default' and s['tenant_id'] == tenant_id]
        if securitygroups:
            securitygroup = securitygroups[0]
            securitygroupid = securitygroup['id']
            sshrule = {'security_group_rule': {'direction': 'ingress', 'security_group_id': securitygroupid,
                                               'port_range_min': '22', 'port_range_max': '22', 'protocol': 'tcp',
                                               'remote_group_id': None, 'remote_ip_prefix': '0.0.0.0/0'}}
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
        """

        :param name:
        :return:
        """
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.start()
        return {'result': 'success'}

    def stop(self, name):
        """

        :param name:
        :return:
        """
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.stop()
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
        print("not implemented")
        return

    def restart(self, name):
        """

        :param name:
        :return:
        """
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.reboot()
        return {'result': 'success'}

    def report(self):
        """

        :return:
        """
        print("not implemented")
        return

    def status(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

# should return a sorted list of name, state, ip, source, plan, profile, report
    def list(self):
        """

        :return:
        """
        vms = []
        nova = self.nova
        glance = self.glance
        vmslist = nova.servers.list()
        for vm in vmslist:
            ip = ''
            for entry1 in list(vm.addresses.values()):
                for entry2 in entry1:
                    if entry2['OS-EXT-IPS:type'] == 'floating':
                        ip = entry2['addr']
                        break
            name = vm.name
            state = vm.status
            source = glance.images.get(vm.image['id']).name if 'id' in vm.image else ''
            plan = ''
            profile = ''
            metadata = vm.metadata
            if metadata is not None:
                plan = metadata['plan'] if 'plan' in metadata else ''
                profile = metadata['profile'] if 'profile' in metadata else ''
            report = self.project
            vms.append([name, state, ip, source, plan, profile, report])
        return vms

    def console(self, name, tunnel=False):
        """

        :param name:
        :param tunnel:
        :return:
        """
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        url = vm.get_vnc_console('novnc')['console']['url']
        if self.debug:
            print(url)
        webbrowser.open(url, new=2, autoraise=True)
        return

    def serialconsole(self, name):
        """

        :param name:
        :return:
        """
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        print(vm.get_console_output())
        return

    def info(self, name, output='plain', fields=None, values=False):
        """

        :param name:
        :param output:
        :param fields:
        :param values:
        :return:
        """
        if fields is not None:
            fields = fields.split(',')
        nova = self.nova
        cinder = self.cinder
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.debug:
            print(vars(vm))
        yamlinfo = {'name': vm.name, 'status': vm.status}
        source = self.glance.images.get(vm.image['id']).name if 'id' in vm.image else ''
        yamlinfo['template'] = source
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
                    yamlinfo['nets'].append(net)
                    index += 1
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
            if 'plan' in metadata:
                yamlinfo['plan'] = metadata['plan']
            if 'profile' in metadata:
                yamlinfo['profile'] = metadata['profile']
        common.print_info(yamlinfo, output=output, fields=fields, values=values)
        return {'result': 'success'}

# should return ip string
    def ip(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return None

# should return a list of available templates, or isos ( if iso is set to True
    def volumes(self, iso=False):
        """

        :param iso:
        :return:
        """
        images = []
        glance = self.glance
        for image in glance.images.list():
            images.append(image.name)
        return images

    def delete(self, name, snapshots=False):
        """

        :param name:
        :param snapshots:
        :return:
        """
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
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
            self.neutron.delete_floatingip(floatingid)
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
        print("not implemented")
        return

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
        print("not implemented")
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
        glance = self.glance
        cinder = self.cinder
        image = None
        if template is not None:
            images = [image for image in glance.images.list() if image.name == template]
            if images:
                image = images[0]
            else:
                msg = "you don't have template %s" % template
                return {'result': 'failure', 'reason': msg}
        cinder.volumes.create(name=name, size=size, imageRef=image)
        return {'result': 'success'}

    def add_disk(self, name, size, pool=None, thin=True, template=None,
                 shareable=False, existing=None):
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
        glance = self.glance
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if template is not None:
            images = [image for image in glance.images.list() if image.name == template]
            if images:
                image = images[0]
            else:
                msg = "you don't have template %s" % template
                return {'result': 'failure', 'reason': msg}
        volume = cinder.volumes.create(name=name, size=size, imageRef=image)
        cinder.volumes.attach(volume, vm.id, '/dev/vdi', mode='rw')
        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None):
        """

        :param name:
        :param diskname:
        :param pool:
        :return:
        """
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
            common.pprint("VM %s not found" % name, color='red')
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
        """

        :return:
        """
        volumes = {}
        cinder = self.cinder
        for volume in cinder.volumes.list():
            volumes[volume.name] = {'pool': 'default', 'path': volume.id}
        return volumes

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
        user = 'root'
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            return None, None
        vm = [v for v in self.list() if v[0] == name][0]
        template = vm[3]
        if template != '':
            user = common.get_user(template)
        ip = vm[2]
        if ip == '':
            print("No ip found. Cannot ssh...")
        user = common.get_user(template)
        return user, ip

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False,
            insecure=False, cmd=None, X=False, Y=False, D=None):
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
        tunnel = False
        sshcommand = common.ssh(name, ip=ip, host=self.host, user=u, local=local, remote=remote,
                                tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, Y=Y, debug=self.debug)
        if self.debug:
            print(sshcommand)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False,
            download=False, recursive=False):
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
        tunnel = False
        u, ip = self._ssh_credentials(name)
        scpcommand = common.scp(name, ip=ip, host=self.host, user=u, source=source,
                                destination=destination, recursive=recursive, tunnel=tunnel,
                                debug=self.debug, download=False)
        if self.debug:
            print(scpcommand)
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
        shortimage = os.path.basename(image).split('?')[0]
        if [i for i in self.glance.images.list() if i['name'] == shortimage]:
            return {'result': 'success'}
        if not os.path.exists('/tmp/%s' % shortimage):
            downloadcmd = 'curl -Lo /tmp/%s -f %s' % (shortimage, image)
            code = os.system(downloadcmd)
            if code != 0:
                return {'result': 'failure', 'reason': "Unable to download indicated template"}
        image = self.glance.images.create(name=shortimage, disk_format='qcow2', container_format='bare')
        self.glance.images.upload(image.id, open('/tmp/%s' % shortimage, 'rb'))
        os.remove('/tmp/%s' % shortimage)
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None,
                       plan='kvirt', pxe=None, vlan=None):
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
            network = neutron.create_network({'network': network})
            network_id = network['network']['id']
            tenant_id = network['network']['tenant_id']
        else:
            common.pprint("Network already there. Creating subnet", color='blue')
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
                common.pprint("Subnet already there. Leaving", color='blue')
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
        """

        :param name:
        :param cidr:
        :return:
        """
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
            common.pprint("Removing unused router kvirt", color="green")
            neutron.delete_router(router_id)
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
        networks = {}
        neutron = self.neutron
        for subnet in neutron.list_subnets()['subnets']:
            networkname = subnet['name']
            subnet_id = subnet['id']
            cidr = subnet['cidr']
            dhcp = subnet['enable_dhcp']
            network_id = subnet['network_id']
            network = neutron.show_network(network_id)
            mode = 'external' if network['network']['router:external'] else 'isolated'
            # networks = [n for n in neutron.list_networks()['networks'] if n['router:external']]
            domainname = neutron.show_network(network_id)['network']['name']
            ports = [p for p in neutron.list_ports()['ports']
                     if p['device_owner'] == 'network:router_interface' and network_id == network_id]
            for port in ports:
                if 'fixed_ips' in port and subnet_id in port['fixed_ips'][0].values():
                    mode = 'nat'
                    break
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
        print("not implemented")
        return

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

    def flavors(self):
        """

        :return:
        """
        nova = self.nova
        nova.flavors.list
        flavors = [[flavor.name, flavor.vcpus, flavor.ram] for flavor in nova.flavors.list()]
        return flavors

    def export(self, name, template=None):
        """

        :param name:
        :param template:
        :return:
        """
        cinder = self.cinder
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for disk in vm._info['os-extended-volumes:volumes_attached']:
            volume = cinder.volumes.get(disk['id'])
            for attachment in volume.attachments:
                newname = template if template is not None else volume.name.replace('-disk0', '')
                volume.upload_to_image(True, newname, 'bare', 'qcow2')
                status = ''
                timeout = 0
                while status != 'available':
                    status = cinder.volumes.get(disk['id']).status
                    common.pprint("Waiting 5 seconds for export to complete", color='green')
                    sleep(5)
                    timeout += 5
                    if timeout >= 90:
                        common.pprint("Time out waiting for export to complete", color='red')
                        break
                break
        return {'result': 'success'}
