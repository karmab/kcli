#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fake class
"""
from kvirt import common
from kvirt.defaults import TEMPLATES
from kvirt.nameutils import get_random_name, random_ip, right
import os
import random


# your base class __init__ needs to define the conn attribute and set it to None when backend cannot be reached
# it should also set debug from the debug variable passed in kcli client
class Kfake(object):
    def __init__(self, host='127.0.0.1', port=None, user='root', debug=False):
        self.conn = 'fake'
        templates = [os.path.basename(t) for t in TEMPLATES.values() if t is not None and (t.endswith('qcow2') or t.endswith('img'))]
        rheltemplates = ['rhel-guest-image-7.2-20160302.0.x86_64.qcow2', 'rhel-guest-image-7.3-35.x86_64.qcow2', 'rhel-server-7.4-x86_64-kvm.qcow2']
        self.templates = templates + rheltemplates
        return

    def close(self):
        return

    def exists(self, name):
        return random.choice([True, False])

    def net_exists(self, name):
        return random.choice([True, False])

    def disk_exists(self, pool, name):
        return random.choice([True, False])

    def create(self, name, virttype='kvm', profile='', plan='kvirt', cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags={}):
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain, reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides, iso=False)
        return {'result': 'success'}

    def start(self, name):
        return {'result': 'success'}

    def stop(self, name):
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")
        return

    def restart(self, name):
        return {'result': 'success'}

    def report(self):
        print("not implemented")
        return

    def status(self, name):
        return random.choice(['up', 'down'])

# should return a list of name, state, ip, source, plan, profile, report
    def list(self):
        vms = []
        number = random.randint(1, 10)
        for i in range(number):
            name = random.choice(right)
            state = self.status(name)
            if state == 'up':
                ip = random_ip()
            else:
                ip = ''
            source = random.choice(self.templates + [''])
            plan = get_random_name()
            profile = 'kvirt'
            report = ''
            vms.append([name, state, ip, source, plan, profile, report])
        return vms

    def console(self, name, tunnel=False):
        print("not implemented")
        return

    def serialconsole(self, name):
        print("not implemented")
        return

# should generate info in a dict and then pass it to print_info(yamlinfo, output=output, fields=fields, values=values)
# from kvirt.common where:
# yamlinfo is the dict
# with the following keys (you can omit the ones you want)
# name
# autostart
# plan
# profile
# template
# ip
# memory
# cpus
# creationdate
# nets list of {'device': device, 'mac': mac, 'net': network, 'type': network_type}
# disks list of {'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path}
# snapshots list of {'snapshot': snapshot, current: current}
# fields should be split with fields.split(',')
    def info(self, name, output='plain', fields=None, values=False):
        cpus = random.choice([1, 2, 4, 8])
        memory = random.choice([512, 1024, 2048, 4096, 8192])
        state = self.status(name)
        if state == 'up':
            ip = random_ip()
        else:
            ip = None
        template = random.choice(self.templates + [''])
        plan = get_random_name()
        profile = 'kvirt'
        yamlinfo = {'name': name, 'template': template, 'plan': plan, 'profile': profile, 'status': state, 'cpus': cpus, 'memory': memory}
        if ip is not None:
            yamlinfo['ip'] = ip
        disks, nets = [], []
        numnets = random.randint(1, 2)
        numdisks = random.randint(1, 3)
        for net in range(numnets):
            device = "eth%s" % net
            network = random.choice(right)
            network_type = 'routed'
            macs = []
            for i in range(6):
                element = random.choice('0123456789abcdef') + random.choice('0123456789abcdef')
                macs.append(element)
            mac = ':'.join(macs)
            nets.append({'device': device, 'mac': mac, 'net': network, 'type': network_type})
        for disk in range(numdisks):
            letter = chr(disk + ord('a'))
            device = 'vd%s' % letter
            disksize = random.choice([10, 20, 30, 40, 50])
            diskformat = 'file'
            drivertype = 'qcow2'
            path = '/var/lib/libvirt/images/%s_%s.img' % (name, disk)
            disks.append({'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        yamlinfo['nets'] = nets
        yamlinfo['disks'] = disks
        common.print_info(yamlinfo, output=output, fields=fields, values=values)
        return {'result': 'success'}

# should return ip string
    def ip(self, name):
        print("not implemented")
        return None

# should return a list of available templates, or isos ( if iso is set to True
    def volumes(self, iso=False):
        if iso:
            return []
        else:
            return sorted(self.templates)
        return

    def delete(self, name, snapshots=False):
        print("not implemented")
        return

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
# sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=u, local=local, remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, debug=self.debug)
    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, D=None):
        print("not implemented")
        return

# should leverage if possible
# should return a scpcommand string
# u, ip = self._ssh_credentials(name)
# scpcommand = common.scp(name, ip='', host=self.host, port=self.port, hostuser=self.user, user=user, source=source, destination=destination, recursive=recursive, tunnel=tunnel, deb    ug=self.debug, download=False)
    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        print("not implemented")
        return

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None):
        print("not implemented")
        return {'result': 'success'}

    def delete_network(self, name=None):
        print("not implemented")
        return {'result': 'success'}

# should return a dict of pool strings
    def list_pools(self):
        print("not implemented")
        return

    def list_networks(self):
        networks = {}
        number = random.randint(1, 6)
        for i in range(number):
            network = random.choice(right)
            cidr = '192.168.122.0/24'.replace('122', str(random.randint(1, 254)))
            dhcp = random.choice([True, False])
            domainname = network
            mode = random.choice(['isolated', 'nat'])
            networks[network] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
        return networks

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
