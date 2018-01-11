#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

from distutils.spawn import find_executable
import os
import time
from virtualbox import VirtualBox, library, Session
from kvirt import common
from kvirt.base import Kbase
import string
import yaml


KB = 1024 * 1024
MB = 1024 * KB
guestrhel532 = "RedHat"
guestrhel564 = "RedHat_64"
guestrhel632 = "RedHat"
guestrhel664 = "RedHat_64"
guestrhel764 = "RedHat_64"
guestother = "Other"
guestotherlinux = "Linux"
guestwindowsxp = "WindowsXP"
guestwindows7 = "Windows7"
guestwindows764 = "Windows7_64"
guestwindows2003 = "Windows2003"
guestwindows200364 = "Windows2003_64"
guestwindows2008 = "Windows2008_64"
guestwindows200864 = "Windows2008_64"
status = {'PoweredOff': 'down', 'PoweredOn': 'up', 'FirstOnline': 'up', 'Aborted': 'down', 'Saved': 'down'}


class Kbox(Kbase):
    def __init__(self):
        try:
            self.conn = VirtualBox()
        except Exception as e:
            print(e)
            self.conn = None

    def close(self):
        self.conn = None

    def guestinstall(self, template):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        template = template.lower()
        version = self.conn.version
        commands = ['curl -O http://download.virtualbox.org/virtualbox/%s/VBoxGuestAdditions_%s.iso' % (version, version)]
        commands.append('mount -o loop VBoxGuestAdditions_5.1.14.iso /mnt')
        if 'centos' in template or 'rhel' in template or 'fedora' in template:
            commands.append('yum -y install gcc make kernel-devel-`uname -r`')
        elif 'debian' in template or [x for x in ubuntus if x in template]:
            commands.append('apt-get install build-essential linux-headers-`uname -r`')
        else:
            return []
        commands.append('sh /mnt/VBoxLinuxAdditions.run')
        commands.append('umount /mnt')
        return commands

    def exists(self, name):
        conn = self.conn
        for vmname in conn.machines:
            if str(vmname) == name:
                return True
        return False

    def net_exists(self, name):
        conn = self.conn
        networks = []
        for network in conn.internal_networks:
            networks.append(network)
        for network in conn.nat_networks:
            networks.append(network.network_name)
        if name in networks:
            return True
        else:
            return False

    def disk_exists(self, pool, name):
        disks = self.list_disks()
        if name in disks:
            return True
        else:
            return True

    def create(self, name, virttype='vbox', profile='kvirt', plan='kvirt', cpumodel='', cpuflags=[], numcpus=2, memory=512, guestid='Linux_64', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}):
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        guestid = 'Linux_64'
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        default_poolpath = '/tmp'
        conn = self.conn
        vm = conn.create_machine("", name, [], guestid, "")
        vm.cpu_count = numcpus
        vm.add_storage_controller('SATA', library.StorageBus(2))
        vm.add_storage_controller('IDE', library.StorageBus(1))
        vm.memory_size = memory
        vm.description = plan
        vm.set_extra_data('profile', profile)
        creationdate = time.strftime("%d-%m-%Y %H:%M", time.gmtime())
        vm.set_extra_data('creationdate', creationdate)
        serial = vm.get_serial_port(0)
        serial.server = True
        serial.enabled = True
        serial.path = str(common.get_free_port())
        serial.host_mode = library.PortMode.tcp
        nat_networks = [network.network_name for network in conn.nat_networks]
        internal_networks = [network for network in conn.internal_networks]
        for index, net in enumerate(nets):
            ip = None
            nic = vm.get_network_adapter(index)
            nic.adapter_type = library.NetworkAdapterType.virtio
            nic.enabled = True
            if isinstance(net, str):
                network = net
            elif isinstance(net, dict) and 'name' in net:
                network = net['name']
                if ips and len(ips) > index and ips[index] is not None:
                    ip = ips[index]
                    vm.set_extra_data('ip', ip)
                    nets[index]['ip'] = ip
                elif 'ip' in nets[index]:
                    ip = nets[index]['ip']
                    vm.set_extra_data('ip', ip)
                if 'mac' in nets[index]:
                    nic.mac_address = nets[index]['mac'].replace(':', '')
            if network in internal_networks:
                nic.attachment_type = library.NetworkAttachmentType.internal
                nic.internal_network = network
            elif network in nat_networks:
                nic.attachment_type = library.NetworkAttachmentType.nat_network
                nic.nat_network = network
                if index == 0:
                    natengine = nic.nat_engine
                    nat_network = [n for n in conn.nat_networks if n.network_name == network][0]
                    nat_network.add_port_forward_rule(False, 'ssh_%s' % name, library.NATProtocol.tcp, '', common.get_free_port(), '', 22)
            else:
                nic.attachment_type = library.NetworkAttachmentType.nat
                if index == 0:
                    natengine = nic.nat_engine
                    natengine.add_redirect('ssh_%s' % name, library.NATProtocol.tcp, '', common.get_free_port(), '', 22)
        vm.save_settings()
        conn.register_machine(vm)
        session = Session()
        vm.lock_machine(session, library.LockType.write)
        machine = session.machine
        if iso is None and cloudinit:
            if template is not None:
                guestcmds = self.guestinstall(template)
                if not cmds:
                    cmds = guestcmds
                elif 'rhel' in template:
                        register = [c for c in cmds if 'subscription-manager' in c]
                        if register:
                            index = cmds.index(register[-1])
                            cmds[index + 1:index + 1] = guestcmds
                        else:
                            cmds = guestcmds + cmds
                else:
                    cmds = guestcmds + cmds
                cmds = cmds + ['reboot']
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain, reserveip=reserveip, files=files, enableroot=enableroot)
            medium = conn.create_medium('RAW', '/tmp/%s.ISO' % name, library.AccessMode.read_only, library.DeviceType.dvd)
            progress = medium.create_base_storage(368, [library.MediumVariant.fixed])
            progress.wait_for_completion()
            dvd = conn.open_medium('/tmp/%s.ISO' % name, library.DeviceType.dvd, library.AccessMode.read_only, False)
            machine.attach_device("IDE", 0, 0, library.DeviceType.dvd, dvd)
        for index, disk in enumerate(disks):
            if disk is None:
                disksize = default_disksize
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                # diskpoolpath = default_poolpath
            elif isinstance(disk, int):
                disksize = disk
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                # diskpoolpath = default_poolpath
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskthin = disk.get('thin', default_diskthin)
                diskinterface = disk.get('interface', default_diskinterface)
                diskpool = disk.get('pool', default_pool)
                # diskpoolpath = default_poolpath
            else:
                return {'result': 'failure', 'reason': "Invalid disk entry"}
            diskname = "%s_%d" % (name, index)
            if template is not None and index == 0:
                diskpath = self.create_disk(diskname, disksize, pool=diskpool, thin=diskthin, template=template)
                machine.set_extra_data('template', template)
                # return {'result': 'failure', 'reason': "Invalid template %s" % template}
            else:
                diskpath = self.create_disk(diskname, disksize, pool=diskpool, thin=diskthin, template=None)
            disk = conn.open_medium(diskpath, library.DeviceType.hard_disk, library.AccessMode.read_write, False)
            disksize = disksize * 1024 * 1024 * 1024
            progress = disk.resize(disksize)
            progress.wait_for_completion()
            machine.attach_device("SATA", index, 0, library.DeviceType.hard_disk, disk)
        poolpath = default_poolpath
        for p in self._pool_info():
            poolname = p['name']
            if poolname == pool:
                poolpath = p['path']
        if iso is not None:
            if not os.path.isabs(iso):
                iso = "%s/%s" % (poolpath, iso)
            if not os.path.exists(iso):
                return {'result': 'failure', 'reason': "Invalid iso %s" % iso}
            medium = conn.create_medium('RAW', iso, library.AccessMode.read_only, library.DeviceType.dvd)
            Gb = 1 * 1024 * 1024 * 1024
            progress = medium.create_base_storage(Gb, [library.MediumVariant.fixed])
            progress.wait_for_completion()
            dvd = conn.open_medium(iso, library.DeviceType.dvd, library.AccessMode.read_only, False)
            machine.attach_device("IDE", 0, 0, library.DeviceType.dvd, dvd)
        # if nested and virttype == 'kvm':
        #    print "prout"
        # else:
        #    print "prout"
        # if reserveip:
        #    vmxml = ''
        #    macs = []
        #    for element in vmxml.getiterator('interface'):
        #        mac = element.find('mac').get('address')
        #        macs.append(mac)
        #    self._reserve_ip(name, nets, macs)
        # if reservedns:
        #    self.reserve_dns(name, nets, domain)
        machine.save_settings()
        session.unlock_machine()
        if start:
            self.start(name)
        # if reservehost:
        #    common.reserve_host(name, nets, domain)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except Exception:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if status[str(vm.state)] == "up":
            return {'result': 'success'}
        else:
            try:
                vm.launch_vm_process(None, 'headless', '')
                return {'result': 'success'}
            except Exception as e:
                return {'result': 'failure', 'reason': e}

    def stop(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
            if status[str(vm.state)] == "down":
                return {'result': 'success'}
            else:
                session = vm.create_session()
                console = session.console
                console.power_down()
                return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def restart(self, name):
        conn = self.conn
        vm = conn.find_machine(name)
        if status[str(vm.state)] == "down":
            return {'result': 'success'}
        else:
            self.stop(name)
            time.sleep(5)
            self.start(name)
            return {'result': 'success'}

    def report(self):
        conn = self.conn
        host = conn.host
        hostname = os.uname()[1]
        cpus = host.processor_count
        memory = host.memory_size
        print("Host:%s Cpu:%s Memory:%sMB\n" % (hostname, cpus, memory))
        for pool in self._pool_info():
            poolname = pool['name']
            pooltype = 'dir'
            poolpath = pool['path']
            # used = "%.2f" % (float(s[2]) / 1024 / 1024 / 1024)
            # available = "%.2f" % (float(s[3]) / 1024 / 1024 / 1024)
            # Type,Status, Total space in Gb, Available space in Gb
            # print("Storage:%s Type:%s Path:%s Used space:%sGB Available space:%sGB" % (poolname, pooltype, poolpath, used, available))
            print("Storage:%s Type:%s Path:%s" % (poolname, pooltype, poolpath))
        print
        dhcp = {}
        dhcpservers = conn.dhcp_servers
        for dhcpserver in dhcpservers:
            dhcp[dhcpserver.network_name] = dhcpserver.ip_address
        for network in conn.internal_networks:
            print("Network:%s Type:internal" % (network))
        for network in conn.nat_networks:
            print("Network:%s Type:routed" % (network.network_name))
        return {'result': 'success'}
        # print("Network:%s Type:routed Cidr:%s Dhcp:%s" % (networkname, cidr, dhcp))

    def status(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            return None
        return status[str(str(vm.state))]

    def list(self):
        vms = []
        conn = self.conn
        for vm in conn.machines:
            name = vm.name
            state = status[str(vm.state)]
            port = ''
            source = vm.get_extra_data('template')
            description = vm.description
            profile = vm.get_extra_data('profile')
            report = vm.get_extra_data('report')
            # ip = vm.get_extra_data('ip')
            for n in range(7):
                nic = vm.get_network_adapter(n)
                enabled = nic.enabled
                if not enabled:
                    continue
                if str(nic.attachment_type) == 'NAT':
                    for redirect in nic.nat_engine.redirects:
                        redirect = redirect.split(',')
                        hostport = redirect[3]
                        guestport = redirect[5]
                        if guestport == '22':
                            port = hostport
                            break
                elif str(nic.attachment_type) == 'NATNetwork':
                    nat_network = [n for n in conn.nat_networks if n.network_name == nic.nat_network][0]
                    for rule in nat_network.port_forward_rules4:
                        rule = rule.split(':')
                        rulename = rule[0]
                        hostport = rule[3]
                        guestip = rule[4][1:-1]
                        if guestip != '':
                            port = hostport
                            break
                        guestport = rule[5]
                        if rulename == "ssh_%s" % name and guestip == '':
                            guestip = self.guestip(name)
                            if guestip == '':
                                pass
                            else:
                                nat_network.remove_port_forward_rule(False, rulename)
                                nat_network.add_port_forward_rule(False, rulename, library.NATProtocol.tcp, '', int(hostport), guestip, 22)
                                port = hostport
            vms.append([name, state, port, source, description, profile, report])
        return vms

    def console(self, name, tunnel=False):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.status(name) == 'down':
            vm.launch_vm_process(None, 'gui', '')
        else:
            print "VM %s already running in headless mode.Use kcli console -s instead" % name

    def serialconsole(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if not str(vm.state):
            common.pprint("VM down", color='red')
            return {'result': 'failure', 'reason': "VM %s down" % name}
        else:
            serial = vm.get_serial_port(0)
            if not serial.enabled:
                print("No serial Console found. Leaving...")
                return
            serialport = serial.path
            os.system("nc 127.0.0.1 %s" % serialport)

    def info(self, name, output='plain', fields=None, values=False):
        starts = {False: 'no', True: 'yes'}
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        state = 'down'
        hostports = []
        autostart = starts[vm.autostart_enabled]
        memory = vm.memory_size
        numcpus = vm.cpu_count
        state = status[str(vm.state)]
        print("name: %s" % name)
        print("status: %s" % state)
        print("autostart: %s" % autostart)
        description = vm.description
        print("description: %s" % description)
        profile = vm.get_extra_data('profile')
        ip = vm.get_extra_data('ip')
        if profile != '':
            print("profile: %s" % profile)
        print("cpus: %s" % numcpus)
        print("memory: %sMB" % memory)
        for n in range(7):
            nic = vm.get_network_adapter(n)
            enabled = nic.enabled
            if not enabled:
                break
            device = "eth%s" % n
            mac = ':'.join(nic.mac_address[i: i + 2] for i in range(0, len(nic.mac_address), 2))
            if str(nic.attachment_type) == 'Internal':
                networktype = 'internal'
                network = nic.internal_network
            elif str(nic.attachment_type) == 'NATNetwork':
                networktype = 'natnetwork'
                network = nic.nat_network
                nat_network = [n for n in conn.nat_networks if n.network_name == network][0]
                if ip != '':
                    for rule in nat_network.port_forward_rules4:
                        rule = rule.split(':')
                        hostport = rule[3]
                        guestip = rule[4][1:-1]
                        guestport = rule[5]
                        if guestport == '22' and guestip == ip:
                            hostports.append(hostport)
            elif str(nic.attachment_type) == 'Null':
                networktype = 'unassigned'
                network = 'N/A'
            elif str(nic.attachment_type) == 'Bridged':
                networktype = 'bridged'
                network = nic.bridged_interface
            elif str(nic.attachment_type) == 'NAT':
                networktype = 'nat'
                network = 'N/A'
                for redirect in nic.nat_engine.redirects:
                    redirect = redirect.split(',')
                    hostport = redirect[3]
                    guestport = redirect[5]
                    if guestport == '22':
                        hostports.append(hostport)
            else:
                networktype = 'N/A'
                network = 'N/A'
            print("net interfaces:%s mac: %s net: %s type: %s" % (device, mac, network, networktype))
        disks = []
        for index in range(10):
            try:
                disk = vm.get_medium('SATA', index, 0)
            except:
                continue
            path = disk.name
            if path.endswith('.iso'):
                continue
            device = 'sd%s' % string.lowercase[len(disks)]
            disks.append(0)
            disksize = disk.size / 1024 / 1024 / 1024
            drivertype = os.path.splitext(disk.name)[1].replace('.', '')
            diskformat = 'file'
            print("diskname: %s disksize: %sGB diskformat: %s type: %s path: %s" % (device, disksize, diskformat, drivertype, path))
            if ip != '':
                print("ip: %s" % (ip))
            for hostport in hostports:
                print("ssh port: %s" % (hostport))
                break
        return {'result': 'success'}

    def ip(self, name):
        vm = [vm for vm in self.list() if vm[0] == name]
        if not vm:
            return None
        else:
            port = vm[0][2]
            return port

    def guestip(self, name):
        conn = self.conn
        vm = conn.find_machine(name)
        ip = vm.get_guest_property('/VirtualBox/GuestInfo/Net/0/V4/IP')[0]
        return ip

    def volumes(self, iso=False):
        isos = []
        templates = []
        poolinfo = self._pool_info()
        for pool in poolinfo:
            path = pool['path']
            for entry in os.listdir(path):
                if entry.endswith('qcow2') and entry not in templates:
                    templates.append(entry)
                elif entry.startswith('KVIRT'):
                    entry = entry.replace('KVIRT_', '').replace('.vdi', '.qcow2')
                    if entry not in templates:
                        templates.append(entry)
                elif entry.endswith('iso'):
                    isos.append(entry)
        if iso:
            return isos
        else:
            return templates

    def delete(self, name, snapshots=False):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("vm %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for n in range(7):
            nic = vm.get_network_adapter(n)
            enabled = nic.enabled
            if not enabled:
                continue
            if str(nic.attachment_type) == 'NAT':
                natengine = nic.nat_engine
                for redirect in natengine.redirects:
                    if redirect.startswith('ssh_'):
                        natengine.remove_redirect('ssh_%s' % name)
                        break
                # natengine.remove_redirect('ssh_%s' % name)
            if str(nic.attachment_type) == 'NATNetwork':
                nat_network = [n for n in conn.nat_networks if n.network_name == nic.nat_network][0]
                rule = [rule for rule in nat_network.port_forward_rules4 if rule.split(':')[0] == "ssh_%s" % name]
                if rule:
                    nat_network.remove_port_forward_rule(False, "ssh_%s" % name)
        vm.remove(True)
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        conn = self.conn
        tree = ''
        uuid = tree.getiterator('uuid')[0]
        tree.remove(uuid)
        for vmname in tree.getiterator('name'):
            vmname.text = new
        firstdisk = True
        for disk in tree.getiterator('disk'):
            if firstdisk or full:
                source = disk.find('source')
                oldpath = source.get('file')
                backingstore = disk.find('backingStore')
                backing = None
                for b in backingstore.getiterator():
                    backingstoresource = b.find('source')
                    if backingstoresource is not None:
                        backing = backingstoresource.get('file')
                newpath = oldpath.replace(old, new)
                source.set('file', newpath)
                oldvolume = conn.storageVolLookupByPath(oldpath)
                oldinfo = oldvolume.info()
                oldvolumesize = (float(oldinfo[1]) / 1024 / 1024 / 1024)
                newvolumexml = self._xmlvolume(newpath, oldvolumesize, backing)
                pool = oldvolume.storagePoolLookupByVolume()
                pool.createXMLFrom(newvolumexml, oldvolume, 0)
                firstdisk = False
            else:
                devices = tree.getiterator('devices')[0]
                devices.remove(disk)
        for interface in tree.getiterator('interface'):
            mac = interface.find('mac')
            interface.remove(mac)
        if self.host not in ['127.0.0.1', 'localhost']:
            for serial in tree.getiterator('serial'):
                source = serial.find('source')
                source.set('service', str(common.get_free_port()))
        vm = conn.lookupByName(new)
        if start:
            vm.setAutostart(1)
            vm.create()

    def update_metadata(self, name, metatype, metavalue):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        session = Session()
        vm.lock_machine(session, library.LockType.write)
        machine = session.machine
        machine.set_extra_data(metatype, metavalue)
        machine.save_settings()
        session.unlock_machine()
        return {'result': 'success'}

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)

    def update_memory(self, name, memory):
        conn = self.conn
        memory = int(memory)
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        session = Session()
        vm.lock_machine(session, library.LockType.write)
        machine = session.machine
        machine.memory_size = memory
        machine.save_settings()
        session.unlock_machine()
        return {'result': 'success'}

    def update_cpu(self, name, numcpus):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm.cpu_count = numcpus
        vm.save_settings()
        return {'result': 'success'}

    def update_start(self, name, start=True):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if start:
            vm.autostart_enabled = True
        else:
            vm.autostart_enabled = False
        vm.save_settings()
        return {'result': 'success'}

    def _convert_qcow2(self, name, newname=None):
        if newname is None:
            newname = "KVIRT_%s" % name.replace('qcow2', 'vdi')
        os.system("qemu-img convert -f qcow2 %s -O vdi %s" % (name, newname))

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        conn = self.conn
        # diskformat = 'qcow2'
        if size < 1:
            print("Incorrect size.Leaving...")
            return {'result': 'failure', 'reason': "Incorrect size"}
        size = int(size) * 1024 * 1024 * 1024
        # if not thin:
        #     diskformat = 'raw'
        if pool is not None:
            pool = [p['path'] for p in self._pool_info() if p['name'] == pool]
            if pool:
                poolpath = pool[0]
            else:
                print("Pool not found. Leaving....")
                return {'result': 'failure', 'reason': "Pool %s not found" % pool}
        diskpath = "%s/%s.vdi" % (poolpath, name)
        disk = conn.create_medium('VDI', diskpath, library.AccessMode.read_write, library.DeviceType.hard_disk)
        if template is not None:
            volumes = self.volumes()
            if template not in volumes and template not in volumes.values():
                print("you don't have template %s.Leaving..." % template)
                return
            templatepath = "%s/%s" % (poolpath, template)
            if template in volumes:
                self._convert_qcow2(templatepath, diskpath)
        else:
            progress = disk.create_base_storage(size, [library.MediumVariant.fixed])
            progress.wait_for_completion()
        return diskpath

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        conn = self.conn
        # diskformat = 'qcow2'
        if size < 1:
            print("Incorrect size.Leaving...")
            return {'result': 'failure', 'reason': "Incorrect size"}
        # if not thin:
        #     diskformat = 'raw'
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        disks = []
        for index, dev in enumerate(string.lowercase[:10]):
            try:
                vm.get_medium('SATA', index, 0)
                disks.append(0)
            except:
                continue
        index = len(disks)
        if existing is None:
            storagename = "%s_%d" % (name, index)
            diskpath = self.create_disk(name=storagename, size=size, pool=pool, thin=thin, template=template)
        else:
            disks = self.list_disks()
            if existing in disks:
                diskpath = disks[existing]['path']
            else:
                diskpath = existing
        session = Session()
        vm.lock_machine(session, library.LockType.write)
        machine = session.machine
        disk = conn.open_medium(diskpath, library.DeviceType.hard_disk, library.AccessMode.read_write, True)
        machine.attach_device("SATA", index, 0, library.DeviceType.hard_disk, disk)
        machine.save_settings()
        session.unlock_machine()
        return {'result': 'success'}

    def delete_disk(self, name, diskname):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if status[str(vm.state)] == "up":
            print("VM %s up. Leaving" % name)
            return {'result': 'failure', 'reason': "VM %s is up" % name}
        for index in range(10):
            try:
                disk = vm.get_medium('SATA', index, 0)
            except:
                continue
            if disk.name == diskname:
                session = Session()
                vm.lock_machine(session, library.LockType.write)
                machine = session.machine
                machine.detach_device("SATA", index, 0)
                machine.save_settings()
                session.unlock_machine()
                disk.delete_storage()
                return {'result': 'success'}
        print("Disk %s not found in %s" % (diskname, name))
        return {'result': 'failure', 'reason': "Disk %s not found in %s" % (diskname, name)}

    def list_disks(self):
        volumes = {}
        poolinfo = self._pool_info()
        for pool in poolinfo:
            poolname = pool['name']
            path = pool['path']
            for entry in os.listdir(path):
                if entry.endswith('vdi'):
                    volumes[entry] = {'pool': poolname, 'path': "%s/%s" % (path, entry)}
                else:
                    continue
        return volumes
        # volumes = {}
        # interface = library.IVirtualBox()
        # poolinfo = self._pool_info()
        # for disk in interface.hard_disks:
        #     path = disk.location
        #     if poolinfo is not None:
        #         pathdir = os.path.dirname(path)
        #         pools = [pool['name'] for pool in poolinfo if pool['path'] == pathdir]
        #         if pools:
        #             pool = pools[0]
        #         else:
        #             pool = ''
        #     else:
        #         pool = ''
        #     volumes[disk.name] = {'pool': pool, 'path': disk.location}
        # return volumes

    def add_nic(self, name, network):
        conn = self.conn
        networks = self.list_networks()
        if network not in networks:
            print("Network %s not found" % network)
            return {'result': 'failure', 'reason': "Network %s not found" % network}
        networktype = networks[network]['type']
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.status(name) == 'up':
            print("VM %s must be down" % name)
            return {'result': 'failure', 'reason': "VM %s must be down" % name}
        session = Session()
        vm.lock_machine(session, library.LockType.write)
        machine = session.machine
        for n in range(7):
            nic = machine.get_network_adapter(n)
            if not nic.enabled:
                nic.enabled = True
                nic.nat_network = network
                if networktype == 'internal':
                    nic.attachment_type = library.NetworkAttachmentType.internal
                    nic.internal_network = network
                else:
                    nic.attachment_type = library.NetworkAttachmentType.nat_network
                    nic.nat_network = network
                break
        machine.save_settings()
        session.unlock_machine()
        return {'result': 'success'}

    def delete_nic(self, name, interface):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.status(name) == 'up':
            print("VM %s must be down" % name)
            return {'result': 'failure', 'reason': "VM %s nust be down" % name}
        session = Session()
        vm.lock_machine(session, library.LockType.write)
        machine = session.machine
        number = int(interface[-1])
        nic = machine.get_network_adapter(number)
        nic.enabled = False
        machine.save_settings()
        session.unlock_machine()
        return {'result': 'success'}

    def _ssh_credentials(self, name):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return '', ''
        if str(vm.state) == 0:
            print("Machine down. Cannot ssh...")
            return '', ''
        vm = [v for v in self.list() if v[0] == name][0]
        template = vm[3]
        if template != '':
            if 'centos' in template.lower():
                user = 'centos'
            elif 'cirros' in template.lower():
                user = 'cirros'
            elif [x for x in ubuntus if x in template.lower()]:
                user = 'ubuntu'
            elif 'fedora' in template.lower():
                user = 'fedora'
            elif 'rhel' in template.lower():
                user = 'cloud-user'
            elif 'debian' in template.lower():
                user = 'debian'
            elif 'arch' in template.lower():
                user = 'arch'
        port = vm[2]
        # if port == '':
        #    print("No port found. Cannot ssh...")
        return user, port

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False):
        u, port = self._ssh_credentials(name)
        if user is None:
            user = u
        if port == '':
            return None
        else:
            sshcommand = "-p %s %s@127.0.0.1" % (port, user)
            if cmd:
                sshcommand = "%s %s" % (sshcommand, cmd)
            if local is not None:
                sshcommand = "-L %s %s" % (local, sshcommand)
            if remote is not None:
                sshcommand = "-R %s %s" % (remote, sshcommand)
            if insecure:
                sshcommand = "ssh -o LogLevel=quiet -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' %s" % sshcommand
            else:
                sshcommand = "ssh %s" % sshcommand
            return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        u, port = self._ssh_credentials(name)
        if user is None:
            user = u
        if port == '':
            print("No ip found. Cannot scp...")
            return None
        else:
            scpcommand = 'scp -P %s' % port
            if recursive:
                scpcommand = "%s -r" % scpcommand
            if download:
                scpcommand = "%s %s@127.0.0.1:%s %s" % (scpcommand, user, source, destination)
            else:
                scpcommand = "%s %s %s@127.0.0.1:%s" % (scpcommand, source, user, destination)
            return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        pools = self.list_pools()
        poolpath = os.path.expanduser(poolpath)
        if name in pools:
            return
        if not os.path.exists(poolpath):
            try:
                os.makedirs(poolpath)
            except OSError:
                print("Couldn't create directory %s.Leaving..." % poolpath)
                return
        poolfile = "%s/.vbox.yml" % os.environ.get('HOME')
        if not os.path.exists(poolfile):
            poolinfo = [{'name': name, 'path': poolpath}]
        else:
            poolinfo = self._pool_info()
            poolinfo.append({'name': name, 'path': poolpath})
        with open(poolfile, 'w') as f:
            for pool in poolinfo:
                f.write("\n- name: %s\n" % pool['name'])
                f.write("  path: %s" % pool['path'])

    def add_image(self, image, pool, cmd=None):
        shortimage = os.path.basename(image).split('?')[0]
        if pool is not None:
            pool = [p['path'] for p in self._pool_info() if p['name'] == pool]
            if pool:
                poolpath = pool[0]
            else:
                print("Pool not found. Leaving....")
                return
        downloadcmd = 'curl -Lo %s/%s -f %s' % (poolpath, shortimage, image)
        os.system(downloadcmd)
        if cmd is not None and find_executable('virt-customize') is not None:
            cmd = "virt-customize -a %s/%s %s" % (poolpath, image, cmd)
            os.system(cmd)
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None):
        conn = self.conn
        network = conn.create_nat_network(name)
        network.network = cidr
        if dhcp:
            network.need_dhcp_server = True
        return {'result': 'success'}

    def delete_network(self, name=None):
        conn = self.conn
        for network in conn.nat_networks:
            networkname = network.network_name
            if networkname == name:
                conn.remove_nat_network(network)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': "Network %s not found" % name}
        # machines = self.network_ports(name)
        # if machines:
        #     machines = ','.join(machines)
        #     return {'result': 'failure', 'reason': "Network %s is being used by %s" % (name, machines)}
        # if network.isActive():
        #     network.destroy()
        # network.undefine()
        # return {'result': 'success'}

    def _pool_info(self):
        poolfile = "%s/.vbox.yml" % os.environ.get('HOME')
        if not os.path.exists(poolfile):
            return None
        with open(poolfile, 'r') as entries:
            poolinfo = yaml.load(entries)
        return poolinfo

    def list_pools(self):
        poolinfo = self._pool_info()
        if poolinfo is None:
            return []
        else:
            return [pool['name'] for pool in poolinfo]

    def list_networks(self):
        networks = {}
        conn = self.conn
        for network in conn.internal_networks:
            networkname = network
            cidr = 'N/A'
            networks[networkname] = {'cidr': cidr, 'dhcp': False, 'type': 'internal', 'mode': 'isolated'}
        for network in conn.nat_networks:
            networkname = network.network_name
            if network.need_dhcp_server:
                dhcp = True
            else:
                dhcp = False
            cidr = network.network
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'type': 'routed', 'mode': 'nat'}
        return networks

    def delete_pool(self, name, full=False):
        poolfile = "%s/.vbox.yml" % os.environ.get('HOME')
        pools = self.list_pools()
        if not os.path.exists(poolfile) or name not in pools:
            return
        else:
            poolinfo = self._pool_info()
            with open(poolfile, 'w') as f:
                for pool in poolinfo:
                    if pool['name'] == name:
                        continue
                    else:
                        f.write("- name: %s\n" % pool['name'])
                        f.write("  path: %s" % pool['path'])

    def vm_ports(self, name):
        conn = self.conn
        networks = []
        try:
            vm = conn.find_machine(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for n in range(7):
            nic = vm.get_network_adapter(n)
            enabled = nic.enabled
            if not enabled:
                continue
            if str(nic.attachment_type) == 'Internal':
                networks.append(nic.internal_network)
            elif str(nic.attachment_type) == 'NATNetwork':
                networks.append(nic.nat_network)
            elif str(nic.attachment_type) == 'Bridged':
                networks.append(nic.bridged_interface)
        return networks

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        super(Kbox, self).snapshot(name, base, revert, delete, listing)
        # conn = self.conn
        # try:
        #    vm = conn.find_machine(base)
        # except:
        #    print("VM %s not found" % base)
        #    return 1
        # if listing:
        #    snapshot = vm.current_snapshot
        #    parent = snapshot.parent
        #    print parent.name
        #    if snapshot is not None:
        #        print snapshot.name
        #        for snap in snapshot.children:
        #            print snap.name
        # elif delete:
        #    print "not implemented in virtualbox api"
        #    return
        #    # vm.delete_snapshot(name)
        # else:
        #    print "not implemented in virtualbox api"
        #    return
        #    # progress = vm.take_snapshot(name, name, True)
        #    # progress.wait_for_completion()

    def get_pool_path(self, pool):
        path = [p['path'] for p in self._pool_info() if p['name'] == pool]
        if path:
            return path[0]
