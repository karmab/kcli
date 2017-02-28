#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

# from defaults import TEMPLATES
# from distutils.spawn import find_executable
from iptools import IpRange
from netaddr import IPNetwork
import os
import string
import time
from virtualbox import VirtualBox, library, Session
from kvirt import common
import yaml


__version__ = "5.3"

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


class Kbox:
    def __init__(self):
        try:
            self.conn = VirtualBox()
        except Exception:
            self.conn = None

    def close(self):
        conn = self.conn
        conn.close()
        self.conn = None

    def exists(self, name):
        conn = self.conn
        for vmname in conn.machines:
            if str(vmname) == name:
                return True
        return False

#    def net_exists(self, name):
#        conn = self.conn
#        try:
#            conn.networkLookupByName(name)
#            return True
#        except:
#            return False

    def disk_exists(self, pool, name):
        conn = self.conn
        try:
            storage = conn.storagePoolLookupByName(pool)
            storage.refresh()
            for stor in sorted(storage.listVolumes()):
                if stor == name:
                    return True
        except:
            return False

    def create(self, name, virttype='vbox', title='', description='kvirt', numcpus=2, memory=512, guestid='Linux', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, start=True, keys=None, cmds=None, ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[]):
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        default_pooltype = 'file'
        default_poolpath = '/tmp'
        conn = self.conn
        vm = conn.create_machine("", name, [], guestid, "")
        vm.cpu_count = numcpus
        vm.add_storage_controller('SATA', library.StorageBus(2))
        # interface = library.IVirtualBox()
        # medium = conn.create_hard_disk("VDI", "/tmp/proutos.vdi")
        # progress = medium.create_base_storage(1024 * 1024, [library.MediumVariant.fixed])
        # progress.wait_for_completion()
        # opened_medium = conn.open_medium("rhel-guest-image-7.2-20160302.0.x86_64.vdi", library.DeviceType.hard_disk, library.AccessMode.read_write, False)
        # print opened_medium
        # session.machine.attach_device("SAS", 2, 0, library.DeviceType.hard_disk, opened_medium)
        # vm.add_storage_controller('IDE', library.StorageBus(1))
        vm.memory_size = memory
        vm.description = description
        serial = vm.get_serial_port(0)
        serial.server = True
        serial.enabled = True
        serial.path = str(common.get_free_port())
        serial.host_mode = library.PortMode.tcp
        for index, net in enumerate(nets):
            nic = vm.get_network_adapter(index)
            nic.enabled = True
            if isinstance(net, str):
                # nic.nat_network = net
                nic.internal_network = net
                # network = nic.internal_network
            elif isinstance(net, dict) and 'name' in net:
                nic.nat_network = net['name']
                ip = None
                if ips and len(ips) > index and ips[index] is not None:
                    ip = ips[index]
                    nets[index]['ip'] = ip
                elif 'ip' in nets[index]:
                    ip = nets[index]['ip']
                if 'mac' in nets[index]:
                    nic.mac_address = nets[index]['mac'].replace(':', '')
        vm.save_settings()
        conn.register_machine(vm)
        session = Session()
        vm.lock_machine(session, library.LockType.write)
        machine = session.machine
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain, reserveip=reserveip, files=files)
            medium = conn.create_medium('RAW', '/tmp/%s.iso' % name, library.AccessMode.read_only, library.DeviceType.dvd)
            progress = medium.create_base_storage(368, [library.MediumVariant.fixed])
            progress.wait_for_completion()
            dvd = conn.open_medium('/tmp/%s.iso' % name, library.DeviceType.dvd, library.AccessMode.read_only, False)
            machine.attach_device("SATA", 0, 0, library.DeviceType.dvd, dvd)
        machine.save_settings()
        session.unlock_machine()
        return
        # for index, dev in enumerate(['a', 'b', 'c', 'd', 'e']):
        #    try:
        #        disk = vm.get_medium('SATA', index, 0)
        #    except:
        #        break
        #    device = 'sd%s' % dev
        #    path = disk.name
        #    disksize = disk.logical_size / 1024 / 1024 / 1024
        #    drivertype = os.path.splitext(disk.name)[1].replace('.', '')
        #    diskformat = 'file'
        #    return
        # if vnc:
        #    display = 'vnc'
        # else:
        #    display = 'spice'
        volumes = {}
        volumespaths = {}
        for p in conn.listStoragePools():
            poo = conn.storagePoolLookupByName(p)
            poo.refresh(0)
            for vol in poo.listAllVolumes():
                volumes[vol.name()] = {'pool': poo, 'object': vol}
                volumespaths[vol.path()] = {'pool': poo, 'object': vol}
        networks = []
        bridges = []
        for net in conn.listNetworks():
            networks.append(net)
        for net in conn.listInterfaces():
            if net != 'lo':
                bridges.append(net)
        for index, disk in enumerate(disks):
            if disk is None:
                disksize = default_disksize
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                diskpooltype = default_pooltype
                diskpoolpath = default_poolpath
            elif isinstance(disk, int):
                disksize = disk
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                diskpooltype = default_pooltype
                diskpoolpath = default_poolpath
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskthin = disk.get('thin', default_diskthin)
                diskinterface = disk.get('interface', default_diskinterface)
                diskpool = disk.get('pool', default_pool)
                diskwwn = disk.get('wwn')
            else:
                return {'result': 'failure', 'reason': "Invalid disk entry"}
            if template is not None and index == 0:
                print diskpooltype, diskpoolpath, diskpool, diskwwn
                print "prout"
                # return {'result': 'failure', 'reason': "Invalid template %s" % template}
            else:
                print "prout"
                # storagename = "%s_%d.img" % (name, index + 1)
                # diskpath = "%s/%s" % (diskpoolpath, storagename)
                # medium = conn.create_medium('RAW', '/tmp/%s.iso' % name, library.AccessMode.read_only, library.DeviceType.dvd)
                # progress = medium.create_base_storage(368, [library.MediumVariant.fixed])
                # progress.wait_for_completion()
                # dvd = conn.open_medium('/tmp/%s.iso' % name, library.DeviceType.dvd, library.AccessMode.read_only, False)
                # machine.attach_device("SATA", 0, 0, library.DeviceType.dvd, dvd)
                # try:
                #    print('x')
                # except:
                #    return {'result': 'failure', 'reason': "Pool %s not found" % diskpool}
                # diskpooltype = ''
                # diskpoolpath = None
            # if netname in bridges:
            #    sourcenet = 'bridge'
            # elif netname in networks:
            #    sourcenet = 'network'
            # else:
            #    return {'result': 'failure', 'reason': "Invalid network %s" % netname}
        if iso is None:
            if cloudinit:
                iso = "%s/%s.iso" % (default_poolpath, name)
            else:
                iso = ''
        else:
            try:
                if os.path.isabs(iso):
                    shortiso = os.path.basename(iso)
                else:
                    shortiso = iso
                # iso = "%s/%s" % (default_poolpath, iso)
                # iso = "%s/%s" % (isopath, iso)
                print shortiso
            except:
                return {'result': 'failure', 'reason': "Invalid iso %s" % iso}
        # if nested and virttype == 'kvm':
        #    print "prout"
        # else:
        #    print "prout"
        vm.setAutostart(1)
        # if reserveip:
        #    vmxml = ''
        #    macs = []
        #    for element in vmxml.getiterator('interface'):
        #        mac = element.find('mac').get('address')
        #        macs.append(mac)
        #    self._reserve_ip(name, nets, macs)
        # if start:
        #    vm.create()
        # if reservedns:
        #    self._reserve_dns(name, nets, domain)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
            if status[str(vm.state)] == "up":
                return {'result': 'success'}
            else:
                vm = conn.find_machine(name)
                vm.launch_vm_process(None, 'headless', '')

                return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def stop(self, name):
        conn = self.conn
        vm = conn.find_machine(name)
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
        hostname = conn.getHostname()
        cpus = conn.getCPUMap()[0]
        memory = conn.getInfo()[1]
        print("Host:%s Cpu:%s Memory:%sMB\n" % (hostname, cpus, memory))
        for pool in conn.listStoragePools():
            poolname = pool
            pool = conn.storagePoolLookupByName(pool)
            pooltype = ''
            if pooltype == 'dir':
                poolpath = ''
            else:
                poolpath = ''
            s = pool.info()
            used = "%.2f" % (float(s[2]) / 1024 / 1024 / 1024)
            available = "%.2f" % (float(s[3]) / 1024 / 1024 / 1024)
            # Type,Status, Total space in Gb, Available space in Gb
            used = float(used)
            available = float(available)
            print("Storage:%s Type:%s Path:%s Used space:%sGB Available space:%sGB" % (poolname, pooltype, poolpath, used, available))
        print
        for interface in conn.listAllInterfaces():
            interfacename = interface.name()
            if interfacename == 'lo':
                continue
            print("Network:%s Type:bridged" % (interfacename))
        for network in conn.listAllNetworks():
            networkname = network.name()
            cidr = 'N/A'
            ip = ''
            if ip:
                attributes = ip[0].attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                if netmask is None:
                    netmask = attributes.get('prefix')
                try:
                    ip = IPNetwork('%s/%s' % (firstip, netmask))
                    cidr = ip.cidr
                except:
                    cidr = "N/A"
            dhcp = ''
            if dhcp:
                dhcp = True
            else:
                dhcp = False
            print("Network:%s Type:routed Cidr:%s Dhcp:%s" % (networkname, cidr, dhcp))

    def status(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
            print dir(vm)
        except:
            return None
        return status[str(str(vm.state))]

    def list(self):
        vms = []
        # leases = {}
        conn = self.conn
        for vm in conn.machines:
            name = vm.name
            state = status[str(vm.state)]
            ip = ''
            source = ''
            description = vm.description
            title = 'N/A'
            vms.append([name, state, ip, source, description, title])
        return vms

    def console(self, name, tunnel=False):
        conn = self.conn
        vm = conn.find_machine(name)
        if not str(vm.state):
            print("VM down")
            return
        else:
            vm.launch_vm_process(None, 'gui', '')

    def serialconsole(self, name):
        conn = self.conn
        vm = conn.find_machine(name)
        if not str(vm.state):
            print("VM down")
            return
        else:
            serial = vm.get_serial_port(0)
            if not serial.enabled:
                print("No serial Console found. Leaving...")
                return
            serialport = serial.path
            os.system("nc 127.0.0.1 %s" % serialport)

    def info(self, name):
        # ips = []
        # leases = {}
        starts = {False: 'no', True: 'yes'}
        conn = self.conn
        # for network in conn.listAllNetworks():
        #    for lease in network.DHCPLeases():
        #        ip = lease['ipaddr']
        #        mac = lease['mac']
        #        leases[mac] = ip
        try:
            vm = conn.find_machine(name)
        except:
            print("VM %s not found" % name)
            return
        state = 'down'
        autostart = starts[vm.autostart_enabled]
        memory = vm.memory_size
        numcpus = vm.cpu_count
        state = status[str(vm.state)]
        print("name: %s" % name)
        print("status: %s" % state)
        print("autostart: %s" % autostart)
        description = vm.description
        print("description: %s" % description)
        title = 'N/A'
        if title is not None:
            print("profile: %s" % title)
        print("cpus: %s" % numcpus)
        print("memory: %sMB" % memory)
        for n in range(7):
            nic = vm.get_network_adapter(n)
            enabled = nic.enabled
            if not enabled:
                break
            device = "eth%s" % n
            mac = ':'.join(nic.mac_address[i: i + 2] for i in range(0, len(nic.mac_address), 2))
            network = 'default'
            networktype = 'routed'
            if nic.nat_network != '':
                networktype = 'internal'
                network = nic.internal_network
            print("net interfaces:%s mac: %s net: %s type: %s" % (device, mac, network, networktype))
        for index, dev in enumerate(['a', 'b', 'c', 'd', 'e']):
            try:
                disk = vm.get_medium('SATA', index, 0)
            except:
                break
            print disk.type_p
            device = 'sd%s' % dev
            path = disk.name
            disksize = disk.logical_size / 1024 / 1024 / 1024
            drivertype = os.path.splitext(disk.name)[1].replace('.', '')
            diskformat = 'file'
            print("diskname: %s disksize: %sGB diskformat: %s type: %s path: %s" % (device, disksize, diskformat, drivertype, path))
            return

    def ip(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            print("VM %s not found" % name)
            return None
        # session = vm.create_session()
        # guest = session.console.guest
        properties = vm.get_guest_property('/VirtualBox/GuestInfo/Net/0/V4/IP')
        print properties

    def volumes(self, iso=False):
        isos = []
        templates = []
        poolinfo = self._pool_info()
        # if iso:
        #    for iso in conn.dvd_images:
        #        isos.append(iso.name)
        #    return isos
        for pool in poolinfo:
            path = pool['path']
            for entry in os.listdir(path):
                if entry.endswith('qcow2'):
                    templates.append(entry)
                elif entry.endswith('iso'):
                    isos.append(entry)
        if iso:
            return isos
        else:
            return templates

    def delete(self, name):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            return
        vm.remove(True)

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

    def update_ip(self, name, ip):
        conn = self.conn
        vm = conn.find_machine(name)
        root = ''
        if not vm:
            print("VM %s not found" % name)
        if str(vm.state) == 1:
            print("Machine up. Change will only appear upon next reboot")
        osentry = root.getiterator('os')[0]
        smbios = osentry.find('smbios')
        if smbios is None:
            newsmbios = ''
            osentry.append(newsmbios)
        sysinfo = root.getiterator('sysinfo')
        system = root.getiterator('system')
        if not sysinfo:
            sysinfo = ''
            root.append(sysinfo)
        sysinfo = root.getiterator('sysinfo')[0]
        if not system:
            system = ''
            sysinfo.append(system)
        system = root.getiterator('system')[0]
        versionfound = False
        for entry in root.getiterator('entry'):
            attributes = entry.attrib
            if attributes['name'] == 'version':
                entry.text = ip
                versionfound = True
        if not versionfound:
            version = ''
            version.text = ip
            system.append(version)
        newxml = ''
        conn.defineXML(newxml)

    def update_memory(self, name, memory):
        conn = self.conn
        memory = str(int(memory) * 1024)
        try:
            vm = conn.find_machine(name)
            root = ''
            print vm
        except:
            print("VM %s not found" % name)
            return
        memorynode = root.getiterator('memory')[0]
        memorynode.text = memory
        currentmemory = root.getiterator('currentMemory')[0]
        currentmemory.text = memory
        newxml = ''
        conn.defineXML(newxml)

    def update_cpu(self, name, numcpus):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
            print vm
            root = ''
        except:
            print("VM %s not found" % name)
            return
        cpunode = root.getiterator('vcpu')[0]
        cpunode.text = numcpus
        newxml = ''
        conn.defineXML(newxml)

    def update_start(self, name, start=True):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if start:
            vm.autostart_enabled = True
        else:
            vm.autostart_enabled = False
        vm.save_settings()
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        conn = self.conn
        diskformat = 'qcow2'
        if size < 1:
            print("Incorrect size.Leaving...")
            return
        if not thin:
            diskformat = 'raw'
        if pool is not None:
            pool = conn.storagePoolLookupByName(pool)
            poolroot = ''
            pooltype = poolroot.getiterator('pool')[0].get('type')
            for element in poolroot.getiterator('path'):
                poolpath = element.text
                break
        else:
            print("Pool not found. Leaving....")
            return
        if template is not None:
            volumes = {}
            for p in conn.listStoragePools():
                poo = conn.storagePoolLookupByName(p)
                for vol in poo.listAllVolumes():
                    volumes[vol.name()] = vol.path()
            if template not in volumes and template not in volumes.values():
                print("Invalid template %s.Leaving..." % template)
            if template in volumes:
                template = volumes[template]
        pool.refresh(0)
        diskpath = "%s/%s" % (poolpath, name)
        if pooltype == 'logical':
            diskformat = 'raw'
        volxml = self._xmlvolume(path=diskpath, size=size, pooltype=pooltype,
                                 diskformat=diskformat, backing=template)
        pool.createXML(volxml, 0)
        return diskpath

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        conn = self.conn
        diskformat = 'qcow2'
        diskbus = 'virtio'
        if size < 1:
            print("Incorrect size.Leaving...")
            return
        if not thin:
            diskformat = 'raw'
        try:
            vm = conn.find_machine(name)
            root = ''
        except:
            print("VM %s not found" % name)
            return
        currentdisk = 0
        for element in root.getiterator('disk'):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            currentdisk = currentdisk + 1
        diskindex = currentdisk + 1
        diskdev = "vd%s" % string.ascii_lowercase[currentdisk]
        if existing is None:
            storagename = "%s_%d.img" % (name, diskindex)
            diskpath = self.create_disk(name=storagename, size=size, pool=pool, thin=thin, template=template)
        else:
            diskpath = existing
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat, shareable=shareable)
        vm.attachDevice(diskxml)
        vm = conn.find_machine(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)

    def delete_disk(self, name, diskname):
        conn = self.conn
        try:
            vm = conn.find_machine(name)
            root = ''
        except:
            print("VM %s not found" % name)
            return
        for element in root.getiterator('disk'):
            disktype = element.get('device')
            diskdev = element.find('target').get('dev')
            diskbus = element.find('target').get('bus')
            diskformat = element.find('driver').get('type')
            if disktype == 'cdrom':
                continue
            diskpath = element.find('source').get('file')
            volume = self.conn.storageVolLookupByPath(diskpath)
            if volume.name() == diskname or volume.path() == diskname:
                diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
                vm.detachDevice(diskxml)
                volume.delete(0)
                vm = conn.find_machine(name)
                vmxml = vm.XMLDesc(0)
                conn.defineXML(vmxml)
                return
        print("Disk %s not found in %s" % (diskname, name))

    def list_disks(self):
        volumes = {}
        interface = library.IVirtualBox()
        poolinfo = self._pool_info()
        for disk in interface.hard_disks:
            path = disk.location
            if poolinfo is not None:
                pathdir = os.path.dirname(path)
                pools = [pool['name'] for pool in poolinfo if pool['path'] == pathdir]
                if pools:
                    pool = pools[0]
                else:
                    pool = ''
            else:
                pool = ''
            volumes[disk.name] = {'pool': pool, 'path': disk.location}
        return volumes

    def add_nic(self, name, network):
        conn = self.conn
        networks = {}
        for interface in conn.listAllInterfaces():
            networks[interface.name()] = 'bridge'
        for net in conn.listAllNetworks():
            networks[net.name()] = 'network'
        try:
            vm = conn.find_machine(name)
        except:
            print("VM %s not found" % name)
            return
        if network not in networks:
            print("Network %s not found" % network)
            return
        else:
            networktype = networks[network]
            source = "<source %s='%s'/>" % (networktype, network)
        nicxml = """<interface type='%s'>
                    %s
                    <model type='virtio'/>
                    </interface>""" % (networktype, source)
        vm.attachDevice(nicxml)
        vm = conn.find_machine(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)

    def delete_nic(self, name, interface):
        conn = self.conn
        networks = {}
        nicnumber = 0
        for n in conn.listAllInterfaces():
            networks[n.name()] = 'bridge'
        for n in conn.listAllNetworks():
            networks[n.name()] = 'network'
        try:
            vm = conn.find_machine(name)
            root = ''
        except:
            print("VM %s not found" % name)
            return
        for element in root.getiterator('interface'):
            device = "eth%s" % nicnumber
            if device == interface:
                mac = element.find('mac').get('address')
                networktype = element.get('type')
                if networktype == 'bridge':
                    network = element.find('source').get('bridge')
                    source = "<source %s='%s'/>" % (networktype, network)
                else:
                    network = element.find('source').get('network')
                    source = "<source %s='%s'/>" % (networktype, network)
                break
            else:
                nicnumber += 1
        nicxml = """<interface type='%s'>
                    <mac address='%s'/>
                    %s
                    <model type='virtio'/>
                    </interface>""" % (networktype, mac, source)
        print nicxml
        vm.detachDevice(nicxml)
        vm = conn.find_machine(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)

    def _ssh_credentials(self, name):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        conn = self.conn
        try:
            vm = conn.find_machine(name)
        except:
            print("VM %s not found" % name)
            return '', ''
        if str(vm.state) != 1:
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
        ip = vm[2]
        if ip == '':
            print("No ip found. Cannot ssh...")
        return user, ip

    def ssh(self, name, local=None, remote=None, tunnel=False):
        user, ip = self._ssh_credentials(name)
        if ip == '':
            return
        else:
            sshcommand = "%s@%s" % (user, ip)
            if self.host not in ['localhost', '127.0.0.1'] and tunnel:
                sshcommand = "-o ProxyCommand='ssh -p %s -W %%h:%%p %s@%s' %s" % (self.port, self.user, self.host, sshcommand)
            if local is not None:
                sshcommand = "-L %s %s" % (local, sshcommand)
            if remote is not None:
                sshcommand = "-R %s %s" % (remote, sshcommand)
            sshcommand = "ssh %s" % sshcommand
            os.system(sshcommand)

    def scp(self, name, source=None, destination=None, tunnel=False, download=False, recursive=False):
        user, ip = self._ssh_credentials(name)
        if ip == '':
            print("No ip found. Cannot scp...")
        else:
            if self.host not in ['localhost', '127.0.0.1'] and tunnel:
                arguments = "-o ProxyCommand='ssh -p %s -W %%h:%%p %s@%s'" % (self.port, self.user, self.host)
            else:
                arguments = ''
            scpcommand = 'scp'
            if recursive:
                scpcommand = "%s -r" % scpcommand
            if download:
                scpcommand = "%s %s %s@%s:%s %s" % (scpcommand, arguments, user, ip, source, destination)
            else:
                scpcommand = "%s %s %s %s@%s:%s" % (scpcommand, arguments, source, user, ip, destination)
            os.system(scpcommand)

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        pools = self.list_pools()
        poolpath = os.path.expanduser(poolpath)
        if name in pools:
            return
        if not os.path.exists(poolpath):
            os.makedirs(poolpath)
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

    def add_image(self, image, pool):
        poolname = pool
        conn = self.conn
        volumes = []
        try:
            pool = conn.storagePoolLookupByName(pool)
            for vol in pool.listAllVolumes():
                volumes.append(vol.name())
        except:
            return {'result': 'failure', 'reason': "Pool %s not found" % poolname}
        poolpath = ''
        if self.host == 'localhost' or self.host == '127.0.0.1':
            cmd = 'wget -P %s %s' % (poolpath, image)
        elif self.protocol == 'ssh':
            cmd = 'ssh -p %s %s@%s "wget -P %s %s"' % (self.port, self.user, self.host, poolpath, image)
        os.system(cmd)
        pool.refresh()
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True):
        conn = self.conn
        print dir(conn)
        natnetworks = conn.nat_networks
        internalnetworks = conn.internal_networks
        print natnetworks, internalnetworks
        return
        networks = self.list_networks()
        cidrs = [network['cidr'] for network in networks.values()]
        if name in networks:
            return {'result': 'failure', 'reason': "Network %s already exists" % name}
        try:
            range = IpRange(cidr)
        except TypeError:
            return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
        if IPNetwork(cidr) in cidrs:
            return {'result': 'failure', 'reason': "Cidr %s already exists" % cidr}
        netmask = IPNetwork(cidr).netmask
        gateway = range[1]
        if dhcp:
            start = range[2]
            end = range[-2]
            dhcpxml = """<dhcp>
                    <range start='%s' end='%s'/>
                    </dhcp>""" % (start, end)
        else:
            dhcpxml = ''
        if nat:
            natxml = "<forward mode='nat'><nat><port start='1024' end='65535'/></nat></forward>"
        else:
            natxml = ''
        networkxml = """<network><name>%s</name>
                    %s
                    <domain name='%s'/>
                    <ip address='%s' netmask='%s'>
                    %s
                    </ip>
                    </network>""" % (name, natxml, name, gateway, netmask, dhcpxml)
        new_net = conn.networkDefineXML(networkxml)
        new_net.setAutostart(True)
        new_net.create()
        return {'result': 'success'}

    def delete_network(self, name=None):
        conn = self.conn
        try:
            network = conn.networkLookupByName(name)
        except:
            return {'result': 'failure', 'reason': "Network %s not found" % name}
        machines = self.network_ports(name)
        if machines:
            machines = ','.join(machines)
            return {'result': 'failure', 'reason': "Network %s is being used by %s" % (name, machines)}
        if network.isActive():
            network.destroy()
        network.undefine()
        return {'result': 'success'}

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
        for network in conn.listAllNetworks():
            networkname = network.name()
            cidr = 'N/A'
            root = ''
            ip = root.getiterator('ip')
            if ip:
                attributes = ip[0].attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                ip = IPNetwork('%s/%s' % (firstip, netmask))
                cidr = ip.cidr
            dhcp = root.getiterator('dhcp')
            if dhcp:
                dhcp = True
            else:
                dhcp = False
            forward = root.getiterator('forward')
            if forward:
                attributes = forward[0].attrib
                mode = attributes.get('mode')
            else:
                mode = 'isolated'
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'type': 'routed', 'mode': mode}
        for interface in conn.listAllInterfaces():
            interfacename = interface.name()
            if interfacename == 'lo':
                continue
            root = ''
            ip = root.getiterator('ip')
            if ip:
                attributes = ip[0].attrib
                ip = attributes.get('address')
                prefix = attributes.get('prefix')
                ip = IPNetwork('%s/%s' % (ip, prefix))
                cidr = ip.cidr
            else:
                cidr = 'N/A'
            networks[interfacename] = {'cidr': cidr, 'dhcp': 'N/A', 'type': 'bridged', 'mode': 'N/A'}
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

    def bootstrap(self, pool=None, poolpath=None, pooltype='dir', nets={}, image=None):
        print "Nothing to do"
