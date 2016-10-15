#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

from distutils.spawn import find_executable
from iptools import IpRange
from netaddr import IPNetwork
from libvirt import open as libvirtopen
import os
import socket
import string
import xml.etree.ElementTree as ET

__version__ = "1.0.49"

KB = 1024 * 1024
MB = 1024 * KB
guestrhel532 = "rhel_5"
guestrhel564 = "rhel_5x64"
guestrhel632 = "rhel_6"
guestrhel664 = "rhel_6x64"
guestrhel764 = "rhel_7x64"
guestother = "other"
guestotherlinux = "other_linux"
guestwindowsxp = "windows_xp"
guestwindows7 = "windows_7"
guestwindows764 = "windows_7x64"
guestwindows2003 = "windows_2003"
guestwindows200364 = "windows_2003x64"
guestwindows2008 = "windows_2008"
guestwindows200864 = "windows_2008x64"


class Kvirt:
    def __init__(self, host='127.0.0.1', port=None, user='root', protocol='ssh', url=None):
        if url is None:
            if host == '127.0.0.1' or host == 'localhost':
                url = "qemu:///system"
            elif protocol == 'ssh':
                url = "qemu+%s://%s@%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, user, host)
            elif user and port:
                url = "qemu+%s://%s@%s:%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, user, host, port)
            elif port:
                url = "qemu+%s://%s:%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, host, port)
            else:
                url = "qemu:///system"
        try:
            self.conn = libvirtopen(url)
        except Exception:
            self.conn = None
        self.host = host
        self.user = user
        self.port = port
        self.protocol = protocol
        if self.protocol == 'ssh' and port is None:
            self.port = '22'

    def close(self):
        conn = self.conn
        conn.close()
        self.conn = None

    def exists(self, name):
        conn = self.conn
        try:
            conn.lookupByName(name)
            return True
        except:
            return False

    def create(self, name, virttype='kvm', title='', description='kvirt', numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, start=True, keys=None, cmds=None, ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None):
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        conn = self.conn
        try:
            default_storagepool = conn.storagePoolLookupByName(default_pool)
        except:
            print("Pool %s not found.Leaving..." % default_pool)
            return {'result': 'failure', 'reason': "Pool %s not found" % default_pool}
        default_poolxml = default_storagepool.XMLDesc(0)
        root = ET.fromstring(default_poolxml)
        default_pooltype = root.getiterator('pool')[0].get('type')
        default_poolpath = None
        for element in root.getiterator('path'):
            default_poolpath = element.text
            break
        if vnc:
            display = 'vnc'
        else:
            display = 'spice'
        volumes = {}
        for p in conn.listStoragePools():
            poo = conn.storagePoolLookupByName(p)
            for vol in poo.listAllVolumes():
                volumes[vol.name()] = {'pool': poo, 'object': vol}
        networks = []
        bridges = []
        for net in conn.listNetworks():
            networks.append(net)
        for net in conn.listInterfaces():
            if net != 'lo':
                bridges.append(net)
        machine = 'pc'
        sysinfo = "<smbios mode='sysinfo'/>"
        disksxml = ''
        volsxml = {}
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
                try:
                    storagediskpool = conn.storagePoolLookupByName(diskpool)
                except:
                    print("Pool %s not found.Leaving..." % diskpool)
                    return {'result': 'failure', 'reason': "Pool %s not found" % diskpool}
                diskpoolxml = storagediskpool.XMLDesc(0)
                root = ET.fromstring(diskpoolxml)
                diskpooltype = root.getiterator('pool')[0].get('type')
                diskpoolpath = None
                for element in root.getiterator('path'):
                    diskpoolpath = element.text
                    break
            else:
                print("Invalid disk entry.Leaving...")
                return {'result': 'failure', 'reason': "Invalid disk entry"}
            letter = chr(index + ord('a'))
            diskdev, diskbus = 'vd%s' % letter, 'virtio'
            if diskinterface != 'virtio':
                diskdev, diskbus = 'hd%s' % letter, 'ide'
            diskformat = 'qcow2'
            if not diskthin:
                diskformat = 'raw'
            storagename = "%s_%d.img" % (name, index + 1)
            diskpath = "%s/%s" % (diskpoolpath, storagename)
            if template is not None and index == 0:
                try:
                    default_storagepool.refresh(0)
                    backingvolume = volumes[template]['object']
                    backingxml = backingvolume.XMLDesc(0)
                    root = ET.fromstring(backingxml)
                except:
                    print("Invalid template %s.Leaving..." % template)
                    return {'result': 'failure', 'reason': "Invalid template %s" % template}
                backing = backingvolume.path()
                if '/dev' in backing and diskpooltype == 'dir':
                    print("lvm template cant be used with a dir pool.Leaving...")
                    return {'result': 'failure', 'reason': "lvm template cant be used with a dir pool.Leaving..."}
                if '/dev' not in backing and diskpooltype == 'logical':
                    print("file template cant be used with a lvm pool.Leaving...")
                    return {'result': 'failure', 'reason': "file template cant be used with a lvm pool.Leaving..."}
                backingxml = """<backingStore type='file' index='1'>
                                <format type='qcow2'/>
                                <source file='%s'/>
                                <backingStore/>
                                </backingStore>""" % backing
            else:
                backing = None
                backingxml = '<backingStore/>'
            volxml = self._xmlvolume(path=diskpath, size=disksize, pooltype=diskpooltype, backing=backing, diskformat=diskformat)
            if diskpool in volsxml:
                volsxml[diskpool].append(volxml)
            else:
                volsxml[diskpool] = [volxml]
            if diskpooltype == 'logical':
                diskformat = 'raw'
            disksxml = """%s<disk type='file' device='disk'>
                    <driver name='qemu' type='%s'/>
                    <source file='%s'/>
                    %s
                    <target dev='%s' bus='%s'/>
                    </disk>""" % (disksxml, diskformat, diskpath, backingxml, diskdev, diskbus)
        netxml = ''
        version = ''
        for index, net in enumerate(nets):
            if isinstance(net, str):
                netname = net
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                ip = None
                if ips and len(ips) > index and ips[index] is not None:
                    ip = ips[index]
                    nets[index]['ip'] = ip
                elif 'ip' in nets[index]:
                    ip = nets[index]['ip']
                if index == 0 and ip is not None:
                    version = "<entry name='version'>%s</entry>" % ips[0]
            if netname in bridges:
                sourcenet = 'bridge'
            elif netname in networks:
                sourcenet = 'network'
            else:
                print("Invalid network %s.Leaving..." % netname)
            netxml = """%s
                     <interface type='%s'>
                     <source %s='%s'/>
                     <model type='virtio'/>
                     </interface>""" % (netxml, sourcenet, sourcenet, netname)
        version = """<sysinfo type='smbios'>
                     <system>
                     %s
                     <entry name='product'>%s</entry>
                     </system>
                     </sysinfo>""" % (version, title)
        if iso is None:
            if cloudinit:
                iso = "%s/%s.iso" % (default_poolpath, name)
            else:
                iso = ''
        else:
            try:
                iso = "%s/%s" % (default_poolpath, iso)
                isovolume = volumes[template][iso]
                iso = isovolume.path()
            except:
                print("Invalid Iso %s.Leaving..." % iso)
                return {'result': 'failure', 'reason': "Invalid iso %s" % iso}
        isoxml = """<disk type='file' device='cdrom'>
                      <driver name='qemu' type='raw'/>
                      <source file='%s'/>
                      <target dev='hdc' bus='ide'/>
                      <readonly/>
                    </disk>""" % (iso)
        displayxml = """<input type='tablet' bus='usb'/>
                        <input type='mouse' bus='ps2'/>
                        <graphics type='%s' port='-1' autoport='yes' listen='0.0.0.0'>
                        <listen type='address' address='0.0.0.0'/>
                        </graphics>
                        <memballoon model='virtio'/>""" % (display)
        if nested and virttype == 'kvm':
            nestedxml = """<cpu match='exact'>
                  <model>Westmere</model>
                   <feature policy='require' name='vmx'/>
                </cpu>"""
        else:
            nestedxml = ""
        if self.host in ['localhost', '127.0.0.1']:
            serialxml = """<serial type='pty'>
                       <target port='0'/>
                       </serial>
                       <console type='pty'>
                       <target type='serial' port='0'/>
                       </console>"""
        else:
            serialxml = """ <serial type="tcp">
                     <source mode="bind" host="127.0.0.1" service="%s"/>
                     <protocol type="telnet"/>
                     <target port="0"/>
                     </serial>""" % self._get_free_port()
        vmxml = """<domain type='%s'>
                  <name>%s</name>
                  <description>%s</description>
                  %s
                  <memory unit='MiB'>%d</memory>
                  <vcpu>%d</vcpu>
                  <os>
                    <type arch='x86_64' machine='%s'>hvm</type>
                    <boot dev='hd'/>
                    <boot dev='cdrom'/>
                    <bootmenu enable='yes'/>
                    %s
                  </os>
                  <features>
                    <acpi/>
                    <apic/>
                    <pae/>
                  </features>
                  <clock offset='utc'/>
                  <on_poweroff>destroy</on_poweroff>
                  <on_reboot>restart</on_reboot>
                  <on_crash>restart</on_crash>
                  <devices>
                    %s
                    %s
                    %s
                    %s
                    %s
                  </devices>
                    %s
                    </domain>""" % (virttype, name, description, version, memory, numcpus, machine, sysinfo, disksxml, netxml, isoxml, displayxml, serialxml, nestedxml)
        for pool in volsxml:
            storagepool = conn.storagePoolLookupByName(pool)
            storagepool.refresh(0)
            for volxml in volsxml[pool]:
                storagepool.createXML(volxml, 0)
        conn.defineXML(vmxml)
        vm = conn.lookupByName(name)
        vm.setAutostart(1)
        if cloudinit:
            self._cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain)
            self._uploadiso(name, pool=default_storagepool)
        if start:
            vm.create()
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
            vm = conn.lookupByName(name)
            if status[vm.isActive()] == "up":
                return 1
            else:
                vm.create()
        except:
            print("VM %s not found" % name)

    def stop(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
            if status[vm.isActive()] == "down":
                return
            else:
                vm.destroy()
        except:
            print("VM %s not found" % name)

    def restart(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        vm = conn.lookupByName(name)
        if status[vm.isActive()] == "down":
            return
        else:
            vm.restart()

    def report(self):
        conn = self.conn
        hostname = conn.getHostname()
        cpus = conn.getCPUMap()[0]
        memory = conn.getInfo()[1]
        print("Host:%s Cpu:%s Memory:%sMB\n" % (hostname, cpus, memory))
        for pool in conn.listStoragePools():
            poolname = pool
            pool = conn.storagePoolLookupByName(pool)
            poolxml = pool.XMLDesc(0)
            root = ET.fromstring(poolxml)
            pooltype = root.getiterator('pool')[0].get('type')
            if pooltype == 'dir':
                poolpath = root.getiterator('path')[0].text
            else:
                poolpath = root.getiterator('device')[0].get('path')
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
            netxml = network.XMLDesc(0)
            cidr = 'N/A'
            root = ET.fromstring(netxml)
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
            print("Network:%s Type:routed Cidr:%s Dhcp:%s" % (networkname, cidr, dhcp))

    def status(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
        except:
            return None
        return status[vm.isActive()]

    def list(self):
        vms = []
        leases = {}
        conn = self.conn
        for network in conn.listAllNetworks():
            for lease in network.DHCPLeases():
                ip = lease['ipaddr']
                mac = lease['mac']
                leases[mac] = ip
        status = {0: 'down', 1: 'up'}
        for vm in conn.listAllDomains(0):
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            description = root.getiterator('description')
            if description:
                description = description[0].text
            else:
                description = ''
            name = vm.name()
            state = status[vm.isActive()]
            ips = []
            title = ''
            for element in root.getiterator('interface'):
                mac = element.find('mac').get('address')
                if vm.isActive():
                    if mac in leases:
                        ips.append(leases[mac])
                if ips:
                    ip = ips[-1]
                else:
                    ip = ''
            for entry in root.getiterator('entry'):
                attributes = entry.attrib
                if attributes['name'] == 'version':
                    ip = entry.text
                if attributes['name'] == 'product':
                    title = entry.text
            source = ''
            for element in root.getiterator('backingStore'):
                s = element.find('source')
                if s is not None:
                    source = os.path.basename(s.get('file'))
                    break
            vms.append([name, state, ip, source, description, title])
        return vms

    def console(self, name):
        conn = self.conn
        vm = conn.lookupByName(name)
        if not vm.isActive():
            print("VM down")
            return
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            for element in root.getiterator('graphics'):
                attributes = element.attrib
                if attributes['listen'] == '127.0.0.1':
                    host = '127.0.0.1'
                else:
                    host = self.host
                protocol = attributes['type']
                port = attributes['port']
                url = "%s://%s:%s" % (protocol, host, port)
                os.popen("remote-viewer %s &" % url)

    def serialconsole(self, name):
        conn = self.conn
        vm = conn.lookupByName(name)
        if not vm.isActive():
            print("VM down")
            return
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            serial = root.getiterator('serial')
            if not serial:
                print("No serial Console found. Leaving...")
                return
            for element in serial:
                serialport = element.find('source').get('service')
                if serialport:
                    if self.protocol != 'ssh':
                        print("Remote serial Console requires using ssh . Leaving...")
                        return
                    else:
                        serialcommand = "ssh -p %s %s@%s nc 127.0.0.1 %s" % (self.port, self.user, self.host, serialport)
                    os.system(serialcommand)
                elif self.host in ['localhost', '127.0.0.1']:
                    os.system('virsh console %s' % name)

    def info(self, name):
        # ips = []
        leases = {}
        conn = self.conn
        for network in conn.listAllNetworks():
            for lease in network.DHCPLeases():
                ip = lease['ipaddr']
                mac = lease['mac']
                leases[mac] = ip
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return
        state = 'down'
        memory = root.getiterator('memory')[0]
        unit = memory.attrib['unit']
        memory = memory.text
        if unit == 'KiB':
            memory = float(memory) / 1024
            memory = int(memory)
        numcpus = root.getiterator('vcpu')[0]
        numcpus = numcpus.text
        if vm.isActive():
            state = 'up'
        print("name: %s" % name)
        print("status: %s" % state)
        description = root.getiterator('description')
        if description:
            description = description[0].text
        else:
            description = ''
        title = None
        for entry in root.getiterator('entry'):
            attributes = entry.attrib
            if attributes['name'] == 'product':
                title = entry.text
        print("description: %s" % description)
        if title is not None:
            print("profile: %s" % title)
        print("cpus: %s" % numcpus)
        print("memory: %sMB" % memory)
        nicnumber = 0
        for element in root.getiterator('interface'):
            networktype = element.get('type')
            device = "eth%s" % nicnumber
            mac = element.find('mac').get('address')
            if networktype == 'bridge':
                bridge = element.find('source').get('bridge')
                print("net interfaces: %s mac: %s net: %s type: bridge" % (device, mac, bridge))
            else:
                network = element.find('source').get('network')
                print("net interfaces:%s mac: %s net: %s type: routed" % (device, mac, network))
                network = conn.networkLookupByName(network)
            if vm.isActive():
                if mac in leases:
                    # ips.append(leases[mac])
                    print("ip: %s" % leases[mac])
            nicnumber = nicnumber + 1
        for entry in root.getiterator('entry'):
            attributes = entry.attrib
            if attributes['name'] == 'version':
                ip = entry.text
                print("ip: %s" % ip)
                break
        for element in root.getiterator('disk'):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            device = element.find('target').get('dev')
            diskformat = 'file'
            drivertype = element.find('driver').get('type')
            path = element.find('source').get('file')
            volume = conn.storageVolLookupByPath(path)
            disksize = int(float(volume.info()[1]) / 1024 / 1024 / 1024)
            print("diskname: %s disksize: %sGB diskformat: %s type: %s path: %s" % (device, disksize, diskformat, drivertype, path))
        # for ip in ips:
        #    print("ip:%s" % ip)

    def volumes(self, iso=False):
        isos = []
        templates = []
        conn = self.conn
        for storage in conn.listStoragePools():
            storage = conn.storagePoolLookupByName(storage)
            storage.refresh(0)
            storagexml = storage.XMLDesc(0)
            root = ET.fromstring(storagexml)
            for element in root.getiterator('path'):
                storagepath = element.text
                break
            for volume in storage.listVolumes():
                if volume.endswith('iso'):
                    isos.append("%s/%s" % (storagepath, volume))
                elif volume.endswith('qcow2'):
                    templates.append("%s/%s" % (storagepath, volume))
        if iso:
            return isos
        else:
            return templates

    def delete(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            return
        status = {0: 'down', 1: 'up'}
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        disks = []
        for element in root.getiterator('disk'):
            source = element.find('source')
            if source is not None:
                imagefile = element.find('source').get('file')
                if 'iso' not in imagefile or name in imagefile:
                    disks.append(imagefile)
        if status[vm.isActive()] != "down":
            vm.destroy()
        vm.undefine()
        for storage in conn.listStoragePools():
            deleted = False
            storage = conn.storagePoolLookupByName(storage)
            storage.refresh(0)
            for stor in storage.listVolumes():
                for disk in disks:
                    if stor in disk:
                        volume = storage.storageVolLookupByName(stor)
                        volume.delete(0)
                        deleted = True
            if deleted:
                storage.refresh(0)

    def _xmldisk(self, diskpath, diskdev, diskbus='virtio', diskformat='qcow2'):
        diskxml = """<disk type='file' device='disk'>
        <driver name='qemu' type='%s' cache='none'/>
        <source file='%s'/>
        <target bus='%s' dev='%s'/>
        </disk>""" % (diskformat, diskpath, diskbus, diskdev)
        return diskxml

    def _xmlvolume(self, path, size, pooltype='file', backing=None, diskformat='qcow2'):
        size = int(size) * MB
        if int(size) == 0:
            size = 500 * 1024
        name = path.split('/')[-1]
        if pooltype == 'block':
            volume = """<volume type='block'>
                        <name>%s</name>
                        <capacity unit="bytes">%d</capacity>
                        <target>
                        <path>%s</path>
                        <compat>1.1</compat>
                      </target>
                    </volume>""" % (name, size, path)
            return volume
        if backing is not None:
            backingstore = """
<backingStore>
<path>%s</path>
<format type='%s'/>
</backingStore>""" % (backing, diskformat)
        else:
            backingstore = "<backingStore/>"
        volume = """
<volume type='file'>
<name>%s</name>
<capacity unit="bytes">%d</capacity>
<target>
<path>%s</path>
<format type='%s'/>
<permissions>
<mode>0644</mode>
</permissions>
<compat>1.1</compat>
</target>
%s
</volume>""" % (name, size, path, diskformat, backingstore)
        return volume

    def clone(self, old, new, full=False, start=False):
        conn = self.conn
        oldvm = conn.lookupByName(old)
        oldxml = oldvm.XMLDesc(0)
        tree = ET.fromstring(oldxml)
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
                source.set('service', str(self._get_free_port()))
        newxml = ET.tostring(tree)
        conn.defineXML(newxml)
        vm = conn.lookupByName(new)
        if start:
            vm.setAutostart(1)
            vm.create()

    def _cloudinit(self, name, keys=None, cmds=None, nets=[], gateway=None, dns=None, domain=None):
        default_gateway = gateway
        with open('/tmp/meta-data', 'w') as metadatafile:
            if domain is not None:
                localhostname = "%s.%s" % (name, domain)
            else:
                localhostname = name
            metadatafile.write('instance-id: XXX\nlocal-hostname: %s\n' % localhostname)
            metadata = ''
            if nets:
                for index, net in enumerate(nets):
                    if isinstance(net, str):
                        if index == 0:
                            continue
                        nicname = "eth%d" % index
                        ip = None
                        netmask = None
                    elif isinstance(net, dict):
                        nicname = net.get('nic', "eth%d" % index)
                        ip = net.get('ip')
                        netmask = net.get('mask')
                    metadata += "  auto %s\n" % nicname
                    if ip is not None and netmask is not None:
                        metadata += "  iface %s inet static\n" % nicname
                        metadata += "  address %s\n" % ip
                        metadata += "  netmask %s\n" % netmask
                        gateway = net.get('gateway')
                        if index == 0 and default_gateway is not None:
                            metadata += "  gateway %s\n" % default_gateway
                        elif gateway is not None:
                            metadata += "  gateway %s\n" % gateway
                    else:
                        metadata += "  iface %s inet dhcp\n" % nicname
                if metadata:
                    metadatafile.write("network-interfaces: |\n")
                    metadatafile.write(metadata)
                    if dns is not None:
                        metadatafile.write("  dns-nameservers %s\n" % dns)
                    if domain is not None:
                        metadatafile.write("  dns-search %s\n" % domain)
        with open('/tmp/user-data', 'w') as userdata:
            userdata.write('#cloud-config\nhostname: %s\n' % name)
            if domain is not None:
                userdata.write("fqdn: %s.%s\n" % (name, domain))
            if keys is not None:
                userdata.write("ssh_authorized_keys:\n")
                for key in keys:
                    userdata.write("- %s\n" % key)
            elif os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
                publickeyfile = "%s/.ssh/id_rsa.pub" % os.environ['HOME']
                with open(publickeyfile, 'r') as ssh:
                    key = ssh.read().rstrip()
                    userdata.write("ssh_authorized_keys:\n")
                    userdata.write("- %s\n" % key)
            if cmds is not None:
                    userdata.write("runcmd:\n")
                    for cmd in cmds:
                        userdata.write("- %s\n" % cmd)
        isocmd = 'mkisofs'
        if find_executable('genisoimage') is not None:
            isocmd = 'genisoimage'
        os.system("%s --quiet -o /tmp/%s.iso --volid cidata --joliet --rock /tmp/user-data /tmp/meta-data" % (isocmd, name))

    def handler(self, stream, data, file_):
        return file_.read(data)

    def _uploadiso(self, name, pool='default'):
        conn = self.conn
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in root.getiterator('path'):
            poolpath = element.text
            break
        isopath = "%s/%s.iso" % (poolpath, name)
        isoxml = self._xmlvolume(path=isopath, size=0, diskformat='raw')
        pool.createXML(isoxml, 0)
        isovolume = conn.storageVolLookupByPath(isopath)
        stream = conn.newStream(0)
        isovolume.upload(stream, 0, 0)
        with open("/tmp/%s.iso" % name) as origin:
            stream.sendAll(self.handler, origin)
            stream.finish()

    def update_ip(self, name, ip):
        conn = self.conn
        vm = conn.lookupByName(name)
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        if not vm:
            print("VM %s not found" % name)
        if vm.isActive() == 1:
            print("Machine up. Change will only appear upon next reboot")
        os = root.getiterator('os')[0]
        smbios = os.find('smbios')
        if smbios is None:
            newsmbios = ET.Element("smbios", mode="sysinfo")
            os.append(newsmbios)
        sysinfo = root.getiterator('sysinfo')
        system = root.getiterator('system')
        if not sysinfo:
            sysinfo = ET.Element("sysinfo", type="smbios")
            root.append(sysinfo)
        sysinfo = root.getiterator('sysinfo')[0]
        if not system:
            system = ET.Element("system")
            sysinfo.append(system)
        system = root.getiterator('system')[0]
        versionfound = False
        for entry in root.getiterator('entry'):
            attributes = entry.attrib
            if attributes['name'] == 'version':
                entry.text = ip
                versionfound = True
        if not versionfound:
            version = ET.Element("entry", name="version")
            version.text = ip
            system.append(version)
        newxml = ET.tostring(root)
        conn.defineXML(newxml)

    def update_memory(self, name, memory):
        conn = self.conn
        memory = str(int(memory) * 1024)
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return
        memorynode = root.getiterator('memory')[0]
        memorynode.text = memory
        currentmemory = root.getiterator('currentMemory')[0]
        currentmemory.text = memory
        newxml = ET.tostring(root)
        conn.defineXML(newxml)

    def update_cpu(self, name, numcpus):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return
        cpunode = root.getiterator('vcpu')[0]
        cpunode.text = numcpus
        newxml = ET.tostring(root)
        conn.defineXML(newxml)

    def add_disk(self, name, size, pool=None, thin=True, template=None):
        conn = self.conn
        diskformat = 'qcow2'
        diskbus = 'virtio'
        if size < 1:
            print("Incorrect size.Leaving...")
            return
        if not thin:
            diskformat = 'raw'
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
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
        if pool is not None:
            pool = conn.storagePoolLookupByName(pool)
            poolxml = pool.XMLDesc(0)
            poolroot = ET.fromstring(poolxml)
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
        storagename = "%s_%d.img" % (name, diskindex)
        diskpath = "%s/%s" % (poolpath, storagename)
        volxml = self._xmlvolume(path=diskpath, size=size, pooltype=pooltype,
                                 diskformat=diskformat, backing=template)
        if pooltype == 'logical':
            diskformat = 'raw'
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
        pool.createXML(volxml, 0)
        vm.attachDevice(diskxml)
        vm = conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)

    def delete_disk(self, name, diskname):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
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
                vm = conn.lookupByName(name)
                vmxml = vm.XMLDesc(0)
                conn.defineXML(vmxml)
                return
        print("Disk %s not found in %s" % (diskname, name))

    def list_disks(self):
        volumes = {}
        for p in self.conn.listStoragePools():
            poo = self.conn.storagePoolLookupByName(p)
            for volume in poo.listAllVolumes():
                volumes[volume.name()] = {'pool': poo.name(), 'path': volume.path()}
        return volumes

    def add_nic(self, name, network):
        conn = self.conn
        networks = {}
        for interface in conn.listAllInterfaces():
            networks[interface.name()] = 'bridge'
        for net in conn.listAllNetworks():
            networks[net.name()] = 'network'
        try:
            vm = conn.lookupByName(name)
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
        vm = conn.lookupByName(name)
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
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
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
        vm = conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)

    def ssh(self, name):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        conn = self.conn
        vm = conn.lookupByName(name)
        if not vm:
            print("VM %s not found" % name)
        if vm.isActive() != 1:
            print("Machine down. Cannot ssh...")
            return
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
        else:
            os.system("ssh %s@%s" % (user, ip))

    def _get_free_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        addr, port = s.getsockname()
        s.close()
        return port

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        conn = self.conn
        for pool in conn.listStoragePools():
            if pool == name:
                print("Pool %s already there.Leaving..." % name)
                return
        if pooltype == 'dir':
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if not os.path.exists(poolpath):
                    os.makedirs(poolpath)
            elif self.protocol == 'ssh':
                cmd1 = 'ssh -p %s %s@%s "test -d %s || mkdir %s"' % (self.port, self.user, self.host, poolpath, poolpath)
                cmd2 = 'ssh %s@%s "chown %s %s"' % (self.user, self.host, user, poolpath)
                os.system(cmd1)
                os.system(cmd2)
            else:
                print("Make sur %s directory exists on hypervisor" % name)
            poolxml = """<pool type='dir'>
                         <name>%s</name>
                         <source>
                         </source>
                         <target>
                         <path>%s</path>
                         </target>
                         </pool>""" % (name, poolpath)
        elif pooltype == 'logical':
            poolxml = """<pool type='logical'>
                         <name>%s</name>
                         <source>
                         <device path='%s'/>
                         <name>%s</name>
                         <format type='lvm2'/>
                         </source>
                         <target>
                         <path>/dev/%s</path>
                         </target>
                         </pool>""" % (name, poolpath, name, name)
        else:
            print("Invalid pool type %s.Leaving..." % pooltype)
            return
        pool = conn.storagePoolDefineXML(poolxml, 0)
        pool.setAutostart(True)
        if pooltype == 'logical':
            pool.build()
        pool.create()

    def create_network(self, name, cidr, dhcp=True):
        conn = self.conn
        try:
            range = IpRange(cidr)
        except TypeError:
            print("Invalid Cidr %s.Leaving..." % cidr)
            return
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
        networkxml = """<network><name>%s</name>
                    <forward mode='nat'>
                    <nat>
                    <port start='1024' end='65535'/>
                    </nat>
                    </forward>
                    <domain name='%s'/>
                    <ip address='%s' netmask='%s'>
                    %s
                    </ip>
                    </network>""" % (name, name, gateway, netmask, dhcpxml)
        new_net = conn.networkDefineXML(networkxml)
        new_net.setAutostart(True)
        new_net.create()

    def delete_network(self, name=None):
        conn = self.conn
        try:
            network = conn.networkLookupByName(name)
        except:
            print("Network %s not found. Leaving..." % name)
            return
        network.destroy()
        network.undefine()

    def list_pools(self):
        pools = []
        conn = self.conn
        for pool in conn.listStoragePools():
            pools.append(pool)
        return pools

    def list_networks(self):
        networks = []
        conn = self.conn
        for network in conn.listAllNetworks():
            name = network.name()
            networks.append(name)
        return networks

    def delete_pool(self, name, full=False):
        conn = self.conn
        try:
            pool = conn.storagePoolLookupByName(name)
        except:
            print("Pool %s not found. Leaving..." % name)
            return
        if full:
            for vol in pool.listAllVolumes():
                vol.delete(0)
        if pool.isActive():
            pool.destroy()
        pool.undefine()

    def bootstrap(self, pool=None, poolpath=None, pooltype='dir', nets={}):
        conn = self.conn
        volumes = {}
        try:
            pool = conn.storagePoolLookupByName(pool)
            for vol in pool.listAllVolumes():
                volumes[vol.name()] = {'object': vol}
        except:
            if poolpath is not None:
                print("Pool %s not found...Creating it" % pool)
                self.create_pool(name=pool, poolpath=poolpath, pooltype=pooltype)
        networks = []
        for net in conn.listNetworks():
            networks.append(net)
        for net in nets:
            if net not in networks:
                print("Network %s not found...Creating it" % net)
                cidr = nets[net].get('cidr')
                dhcp = bool(nets[net].get('dchp', True))
                self.create_network(name=net, cidr=cidr, dhcp=dhcp)
