#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fake Provider Class
"""
from kvirt import common
from kvirt.defaults import IMAGES
from kvirt.nameutils import get_random_name, random_ip, right
import os
import random
from shutil import rmtree
import yaml


# your base class __init__ needs to define the conn attribute and set it to None when backend cannot be reached
# it should also set debug from the debug variable passed in kcli client
class Kfake(object):
    """

    """
    def __init__(self, host='127.0.0.1', port=None, user='root', debug=False):
        self.conn = 'fake'
        self.host = host
        images = []
        for t in list(IMAGES.values()):
            if t is not None and (t.endswith('qcow2') or t.endswith('img')):
                images.append(os.path.basename(t))
        rhelimages = ['rhel-guest-image-7.2-20160302.0.x86_64.qcow2', 'rhel-guest-image-7.3-35.x86_64.qcow2',
                      'rhel-server-7.4-x86_64-kvm.qcow2']
        self.images = images + rhelimages
        return

    def close(self):
        """

        :return:
        """
        return

    def exists(self, name):
        """

        :param name:
        :return:
        """
        return False

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        return False

    def disk_exists(self, pool, name):
        """

        :param pool:
        :param name:
        :return:
        """
        return False

    def create(self, name, virttype='kvm', profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[],
               numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None, disks=[{'size': 10}],
               disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[],
               ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[],
               enableroot=True, alias=[], overrides={}, tags={}, dnsclient=None, storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False):
        """

        :param name:
        :param virttype:
        :param profile:
        :param flavor:
        :param plan:
        :param cpumodel:
        :param cpuflags:
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
        :return:
        """
        plandir = "/tmp/%s" % plan
        namedir = "%s/%s" % (plandir, name)
        if not os.path.exists(plandir):
            common.pprint("Generating assets in %s" % plandir)
            os.mkdir(plandir)
        if os.path.exists(namedir):
            rmtree(namedir)
        os.mkdir(namedir)
        if cloudinit:
            if image is not None and ('coreos' in image or image.startswith('rhcos')):
                common.pprint("Data provided for a %s image" % image)
                version = '3.0.0' if image.startswith('fedora-coreos') else '2.2.0'
                ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                               domain=domain, reserveip=reserveip, files=files,
                                               enableroot=enableroot, overrides=overrides, version=version,
                                               plan=plan)
                with open('%s/%s.ign' % (namedir, name), 'w') as ignitionfile:
                    ignitionfile.write(ignitiondata)
            else:
                _files = yaml.safe_load(common.process_files(files=files, overrides=overrides))
                cmds = common.process_cmds(cmds, overrides).replace('- ', '')
                if cmds != "":
                    with open("%s/cmds.sh" % (namedir), "w") as f:
                        f.write(cmds)
                copycmds = ""
                permissioncmds = ""
                if _files is not None:
                    for entry in _files:
                        owner = entry.get("owner", 'root')
                        path = entry["path"]
                        origin = os.path.basename(entry["path"])
                        permissions = entry.get("permissions")
                        content = entry["content"]
                        with open("%s/%s" % (namedir, os.path.basename(path)), "w") as f:
                            f.write(content)
                        copycmds += "scp %s $host:%s\n" % (origin, path)
                        if owner != "root:root":
                            permissioncmds += "chown %s %s\n" % (owner, path)
                        if permissions is not None and permissions != '0600':
                            permissioncmds += "chmod %s %s\n" % (permissions, path)
                with open("%s/launch.sh" % namedir, "w") as f:
                    if 'host' in overrides:
                        host = overrides["host"]
                    else:
                        common.pprint("Set host in launch.sh", color="blue")
                        host = ""
                    user = "%s@" % overrides["user"] if "user" in overrides else "root"
                    f.write("#!/bin/bash\nhost=\"%s%s\"\n" % (user, host))
                    f.write(copycmds)
                    f.write(permissioncmds)
                    if cmds != "":
                        f.write("scp cmds.sh $host:\n")
                        f.write("ssh $host bash cmds.sh")
        return {'result': 'success'}

    def start(self, name):
        """

        :param name:
        :return:
        """
        return {'result': 'success'}

    def stop(self, name):
        """

        :param name:
        :return:
        """
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
        return 'up'

# should return a list of name, state, ip, source, plan, profile, report
    def list(self):
        """

        :return:
        """
        vms = []
        number = random.randint(1, 10)
        for i in range(number):
            name = get_random_name()
            vms.append(self.info(name))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        """

        :param name:
        :param tunnel:
        :return:
        """
        print("not implemented")
        return

    def serialconsole(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

    def dnsinfo(self, name):
        """

        :param name:
        :return:
        """
        return None, None

# should generate info in a dict and then pass it to print_info(yamlinfo, output=output, fields=fields, values=values)
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
# cpus
# creationdate
# nets list of {'device': device, 'mac': mac, 'net': network, 'type': network_type}
# disks list of {'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path}
# snapshots list of {'snapshot': snapshot, current: current}
# fields should be split with fields.split(',')
    def info(self, name, vm=None, debug=False):
        """

        :param name:
        :param vm:
        :return:
        """
        cpus = random.choice([1, 2, 4, 8])
        memory = random.choice([512, 1024, 2048, 4096, 8192])
        state = self.status(name)
        if state == 'up':
            ip = random_ip()
        else:
            ip = None
        image = random.choice(self.images + [''])
        plan = get_random_name()
        profile = 'kvirt'
        yamlinfo = {'name': name, 'image': image, 'plan': plan, 'profile': profile, 'status': state, 'cpus': cpus,
                    'memory': memory}
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
        if iso:
            return []
        else:
            return sorted(self.images)
        return

    def delete(self, name, snapshots=False):
        """

        :param name:
        :param snapshots:
        :return:
        """
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

    def update_metadata(self, name, metatype, metavalue, append=False):
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

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param image:
        :return:
        """
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None):
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
        print("not implemented")
        return

    def delete_disk(self, name=None, diskname=None, pool=None):
        """

        :param name:
        :param diskname:
        :param pool:
        :return:
        """
        print("not implemented")
        return

# should return a dict of {'pool': poolname, 'path': name}
    def list_disks(self):
        """

        :return:
        """
        print("not implemented")
        return

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
        return 'root', '127.0.0.1'

# should leverage if possible
# should return a sshcommand string
# u, ip = self._ssh_credentials(name)
# sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=u, local=local,
# remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, Y=Y, debug=self.debug)
    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False,
            D=None):
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
        print("not implemented")
        return

# should leverage if possible
# should return a scpcommand string
# u, ip = self._ssh_credentials(name)
# scpcommand = common.scp(name, ip='', host=self.host, port=self.port, hostuser=self.user, user=user, source=source,
# destination=destination, recursive=recursive, tunnel=tunnel, debug=self.debug, download=False)
    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
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
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        """

        :param name:
        :param cidr:
        :param dhcp:
        :param nat:
        :param domain:
        :param plan:
        :param overrides:
        :return:
        """
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        """

        :param name:
        :param cidr:
        :return:
        """
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
        number = random.randint(1, 6)
        for i in range(number):
            network = random.choice(right)
            cidr = '192.168.122.0/24'.replace('122', str(random.randint(1, 254)))
            dhcp = random.choice([True, False])
            domainname = network
            mode = random.choice(['isolated', 'nat'])
            networks[network] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
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
        print("not implemented")
        return

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
        return []

    def delete_image(self, image):
        return {'result': 'success'}

    def list_dns(self, domain):
        """

        :param domain:
        :return:
        """
        return []
