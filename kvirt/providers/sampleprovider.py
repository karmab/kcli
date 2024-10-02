# -*- coding: utf-8 -*-

from kvirt import common

# general notes
# most functions should either return
# return {'result': 'success'}
# or
# return {'result': 'failure', 'reason': reason}
# for instance
# return {'result': 'failure', 'reason': "VM %s not found" % name}


# your base class __init__ needs to define conn attribute and set it to None
# when backend cannot be reached
# it should also set debug from the debug variable passed in kcli client
class Kbase(object):
    def __init__(self, host='127.0.0.1', port=None, user='root', debug=False):
        self.conn = 'base'

# should cleanly close your connection, if needed
    def close(self):
        print("not implemented")

    def exists(self, name):
        print("not implemented")

    def net_exists(self, name):
        print("not implemented")

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[],
               cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False,
               numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[],
               vmuser=None, guestagent=True):
        print("not implemented")
        return {'result': 'success'}

    def start(self, name):
        print("not implemented")
        return {'result': 'success'}

    def stop(self, name, soft=False):
        print("not implemented")
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
        return self.start(name)

    def info_host(self):
        print("not implemented")
        return {}

    def status(self, name):
        print("not implemented")

# should return a sorted list of name, state, ip, source, plan, profile
    def list(self):
        print("not implemented")
        return []

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        print("not implemented")

    def serialconsole(self, name, web=False):
        print("not implemented")

# should generate info in a dict and then pass it to
# print_info(yamlinfo, output=output, fields=fields, values=values)
# from kvirt.common where:
# yamlinfo is the dict
# with the following keys (you can omit the ones you want)
# name
# autostart
# plan
# profile
# image
# ip
# memory
# numcpus
# creationdate
# nets list  of
# {'device': device, 'mac': mac, 'net': network, 'type': network_type}
# disks list of
# {'device': device, 'size': disksize, 'format': diskformat,
# 'type': drivertype, 'path': path}
# snapshots list of {'snapshot': snapshot, current: current}
# fields should be split with fields.split(',')
    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        print("not implemented")
        return {'result': 'success'}

# should return ip string
    def ip(self, name):
        print("not implemented")

# should return a list of available images, or isos ( if iso is set to True
    def volumes(self, iso=False):
        print("not implemented")
        return []

    def delete(self, name, snapshots=False):
        print("not implemented")
        return {'result': 'success'}

# should return dnsclient, domain for the given vm
    def dnsinfo(self, name):
        return None, None

    def clone(self, old, new, full=False, start=False):
        print("not implemented")

    def update_metadata(self, name, metatype, metavalue, append=False):
        print("not implemented")

    def update_memory(self, name, memory):
        print("not implemented")

    def update_cpus(self, name, numcpus):
        print("not implemented")

    def update_start(self, name, start=True):
        print("not implemented")

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)

    def update_iso(self, name, iso):
        print("not implemented")

    def update_flavor(self, name, flavor):
        print("Not implemented")
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        print("not implemented")

    def delete_disk(self, name, diskname, pool=None, novm=False):
        print("not implemented")

# should return a dict of {'diskname': {'pool': poolname, 'path': name}}
    def list_disks(self):
        print("not implemented")
        return []

    def add_nic(self, name, network, model='virtio'):
        print("not implemented")

    def delete_nic(self, name, interface):
        print("not implemented")

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")

    def delete_image(self, image, pool=None):
        print("not implemented")
        return {'result': 'success'}

    def add_image(self, url, pool, short=None, cmds=[], name=None, size=None, convert=False):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        print("not implemented")
        return {'result': 'success'}

# should return a list of pools
    def list_pools(self):
        print("not implemented")
        return []

    def list_networks(self):
        print("not implemented")
        return {}

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        return networkinfo

    def info_subnet(self, name):
        print("not implemented")
        return {}

    def list_subnets(self):
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        print("not implemented")

    def network_ports(self, name):
        print("not implemented")

    def vm_ports(self, name):
        print("not implemented")
        return ['default']

    def get_pool_path(self, pool):
        print("not implemented")

# return a list of [name, numcpus, memory] for each flavor, if the platform has this concept
    def list_flavors(self):
        return []

# export the primary disk of the corresponding instance so it's available as a image
    def export(self, name, image=None):
        print("not implemented")

    def create_bucket(self, bucket, public=False):
        print("not implemented")

    def delete_bucket(self, bucket):
        print("not implemented")

    def delete_from_bucket(self, bucket, path):
        print("not implemented")

    def download_from_bucket(self, bucket, path):
        print("not implemented")

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        print("not implemented")

    def list_buckets(self):
        print("not implemented")
        return []

    def list_bucketfiles(self, bucket):
        print("not implemented")
        return []

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None):
        print("not implemented")

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
