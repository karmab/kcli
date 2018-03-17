#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Kvirt serving as interface for the virtualisation providers
"""

# general notes
# most functions should either return
# return {'result': 'success'}
# or
# return {'result': 'failure', 'reason': reason}
# for instance
# return {'result': 'failure', 'reason': "VM %s not found" % name}


# your base class __init__ needs to define the conn attribute and set it to None when backend cannot be reached
# it should also set debug from the debug variable passed in kcli client
class Kbase(object):
    def __init__(self, host='127.0.0.1', port=None, user='root', debug=False):
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

    def create(self, name, virttype='kvm', profile='', plan='kvirt', cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags={}):
        print("not implemented")
        return {'result': 'success'}

    def start(self, name):
        print("not implemented")
        return {'result': 'success'}

    def stop(self, name):
        print("not implemented")
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")
        return

    def restart(self, name):
        print("not implemented")
        return {'result': 'success'}

    def report(self):
        print("not implemented")
        return

    def status(self, name):
        print("not implemented")
        return

# should return a list of name, state, ip, source, plan, profile, report
    def list(self):
        print("not implemented")
        return

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
        print("not implemented")
        return {'result': 'success'}

# should return ip string
    def ip(self, name):
        print("not implemented")
        return None

# should return a list of available templates, or isos ( if iso is set to True
    def volumes(self, iso=False):
        print("not implemented")
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
    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False):
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
        return

    def delete_network(self, name=None):
        print("not implemented")
        return

# should return a dict of pool strings
    def list_pools(self):
        print("not implemented")
        return

    def list_networks(self):
        print("not implemented")
        return

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
