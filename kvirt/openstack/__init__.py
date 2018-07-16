#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Kvirt serving as interface for the virtualisation providers
"""

from iptools import IpRange
from kvirt import common
from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client as glanceclient
from novaclient import client as novaclient
from neutronclient.v2_0.client import Client as neutronclient
import os
from time import sleep
import webbrowser


# general notes
# most functions should either return
# return {'result': 'success'}
# or
# return {'result': 'failure', 'reason': reason}
# for instance
# return {'result': 'failure', 'reason': "VM %s not found" % name}


class Kopenstack(object):
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
        self.neutron = neutronclient(session=sess)
        self.conn = self.nova
        self.project = project
        return

# should cleanly close your connection, if needed
    def close(self):
        print("not implemented")
        return

    def exists(self, name):
        return

    def net_exists(self, name):
        print("not implemented")
        return

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype='kvm', profile='', plan='kvirt',
               cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', template=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=None, cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=None):
        glance = self.glance
        nova = self.nova
        neutron = self.neutron
        try:
            nova.servers.find(name=name)
            common.pprint("VM %s already exists" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        except:
            pass
        images = [image for image in glance.images.list() if image.name == template]
        if images:
            image = images[0]
        else:
            msg = "you don't have template %s" % template
            return {'result': 'failure', 'reason': msg}
        flavors = [flavor for flavor in nova.flavors.list() if flavor.ram == memory and flavor.vcpus == numcpus]
        flavor = flavors[0] if flavors else nova.flavors.find(name="m1.tiny")
        common.pprint("Using flavor %s" % flavor.name, color='green')
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
                                       userdata=userdata)
        floating_ips = [f['id'] for f in neutron.list_floatingips()['floatingips']
                        if f['port_id'] is None]
        if not floating_ips:
            tenant_id = None
            network_id = None
            networks = [n for n in neutron.list_networks()['networks'] if n['router:external']]
            if networks:
                tenant_id = networks[0]['tenant_id']
                network_id = networks[0]['id']
            if network_id is not None and tenant_id is not None:
                args = dict(floating_network_id=network_id, tenant_id=tenant_id)
                floating_ip = neutron.create_floatingip(body={'floatingip': args})
                floatingip_id = floating_ip['id']
        else:
            floatingip_id = floating_ips[0]
        fixed_ip = None
        timeout = 0
        while fixed_ip is None:
            common.pprint("Waiting 5 seconds for vm to get an ip", color='green')
            sleep(5)
            timeout += 5
            if timeout >= 15:
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
        return {'result': 'success'}

    def start(self, name):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.start()
        return {'result': 'success'}

    def stop(self, name):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
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
            common.pprint("VM %s not found" % name, color='red')
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
            source = glance.images.get(vm.image['id']).name
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
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        print(vm.get_console_output())
        return

# disks list of
# {'device': device, 'size': disksize, 'format': diskformat,
# 'type': drivertype, 'path': path}
# snapshots list of {'snapshot': snapshot, current: current}
# fields should be split with fields.split(',')
    def info(self, name, output='plain', fields=None, values=False):
        if fields is not None:
            fields = fields.split(',')
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.debug:
            print(vars(vm))
        yamlinfo = {'name': vm.name, 'status': vm.status, 'template': self.glance.images.get(vm.image['id']).name}
        flavor = nova.flavors.get(vm.flavor['id'])
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
        print("not implemented")
        return None

# should return a list of available templates, or isos ( if iso is set to True
    def volumes(self, iso=False):
        images = []
        glance = self.glance
        for image in glance.images.list():
            images.append(image.name)
        return images

    def delete(self, name, snapshots=False):
        nova = self.nova
        try:
            vm = nova.servers.find(name=name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.delete()
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

    def add_disk(self, name, size, pool=None, thin=True, template=None,
                 shareable=False, existing=None):
        print("not implemented")
        return

    def delete_disk(self, name, diskname):
        print("not implemented")
        return

# should return a dict of {'pool': poolname, 'path': name}
    def list_disks(self):
        print("not implemented")
        return

    def add_nic(self, name, network):
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        print("not implemented")
        return

# should return (user, ip)
    def _ssh_credentials(self, name):
        print("not implemented")
        return

# should leverage if possible
# should return a sshcommand string
# u, ip = self._ssh_credentials(name)
# sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port,
# hostuser=self.user, user=u, local=local,
# remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X,
# debug=self.debug)
    def ssh(self, name, user=None, local=None, remote=None, tunnel=False,
            insecure=False, cmd=None, X=False, D=None):
        print("not implemented")
        return

# should leverage if possible
# should return a scpcommand string
# u, ip = self._ssh_credentials(name)
# scpcommand = common.scp(name, ip='', host=self.host, port=self.port,
# hostuser=self.user, user=user,
# source=source, destination=destination, recursive=recursive, tunnel=tunnel,
# debug=self.debug, download=False)
    def scp(self, name, user=None, source=None, destination=None, tunnel=False,
            download=False, recursive=False):
        print("not implemented")
        return

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None,
                       plan='kvirt', pxe=None):
        try:
            IpRange(cidr)
        except TypeError:
            return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
        neutron = self.neutron
        network = {'name': name, 'admin_state_up': True}
        network = neutron.create_network({'network': network})
        networkid = network['network']['id']
        subnet = {'name': name, 'network_id': networkid, 'ip_version': 4, "cidr": cidr}
        subnet = neutron.create_subnet({'subnet': subnet})
        return {'result': 'success'}

    def delete_network(self, name=None):
        neutron = self.neutron
        networks = neutron.list_networks(name=name)
        if networks:
            network_id = networks['networks'][0]['id']
            neutron.delete_network(network_id)
        return

# should return a dict of pool strings
    def list_pools(self):
        print("not implemented")
        return

    def list_networks(self):
        networks = {}
        # neutron = self.neutron
        # allnetworks = neutron.list_networks()
        # for network in allnetworks:
        #     networkname = network['name']
        #    networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
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
        print("not implemented")
        return

# returns the path of the pool, if it makes sense. used by kcli list --pools
    def get_pool_path(self, pool):
        print("not implemented")
        return
