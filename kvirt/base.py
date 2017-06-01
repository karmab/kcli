#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Kvirt serving as interface for the virtualisation providers
"""


class Kbase(object):
    def __init__(self):
        return

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
        return

    def create(self, name, virttype='kvm', profile='', plan='kvirt', cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[]):
        print("not implemented")
        return

    def start(self, name):
        print("not implemented")
        return

    def stop(self, name):
        print("not implemented")
        return

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")
        return

    def restart(self, name):
        print("not implemented")
        return

    def report(self):
        print("not implemented")
        return

    def status(self, name):
        print("not implemented")
        return

    def list(self):
        print("not implemented")
        return

    def console(self, name, tunnel=False):
        print("not implemented")
        return

    def serialconsole(self, name):
        print("not implemented")
        return

    def info(self, name):
        print("not implemented")
        return

    def ip(self, name):
        print("not implemented")
        return

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

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        print("not implemented")
        return

    def delete_disk(self, name, diskname):
        print("not implemented")
        return

    def list_disks(self):
        print("not implemented")
        return

    def add_nic(self, name, network):
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        print("not implemented")
        return

    def _ssh_credentials(self, name):
        print("not implemented")
        return

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False):
        print("not implemented")
        return

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        print("not implemented")
        return

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None):
        print("not implemented")
        return

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt'):
        print("not implemented")
        return

    def delete_network(self, name=None):
        print("not implemented")
        return

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

    def get_pool_path(self, pool):
        print("not implemented")
        return
