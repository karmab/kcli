#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

from defaults import TEMPLATES
import docker
from distutils.spawn import find_executable
from iptools import IpRange
from netaddr import IPAddress, IPNetwork
from libvirt import open as libvirtopen
import os
import socket
import string
import xml.etree.ElementTree as ET

__version__ = "4.2"

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
        for vm in conn.listAllDomains():
            if vm.name() == name:
                return True
        return False

    def net_exists(self, name):
        conn = self.conn
        try:
            conn.networkLookupByName(name)
            return True
        except:
            return False

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

    def create(self, name, virttype='kvm', title='', description='kvirt', numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, start=True, keys=None, cmds=None, ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None):
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        conn = self.conn
        try:
            default_storagepool = conn.storagePoolLookupByName(default_pool)
        except:
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
                    return {'result': 'failure', 'reason': "Pool %s not found" % diskpool}
                diskpoolxml = storagediskpool.XMLDesc(0)
                root = ET.fromstring(diskpoolxml)
                diskpooltype = root.getiterator('pool')[0].get('type')
                diskpoolpath = None
                for element in root.getiterator('path'):
                    diskpoolpath = element.text
                    break
            else:
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
                    if '/' in template:
                        backingvolume = volumespaths[template]['object']
                    else:
                        backingvolume = volumes[template]['object']
                    backingxml = backingvolume.XMLDesc(0)
                    root = ET.fromstring(backingxml)
                except:
                    return {'result': 'failure', 'reason': "Invalid template %s" % template}
                backing = backingvolume.path()
                if '/dev' in backing and diskpooltype == 'dir':
                    return {'result': 'failure', 'reason': "lvm template can not be used with a dir pool.Leaving..."}
                if '/dev' not in backing and diskpooltype == 'logical':
                    return {'result': 'failure', 'reason': "file template can not be used with a lvm pool.Leaving..."}
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
            macxml = ''
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
                if 'mac' in nets[index]:
                    mac = nets[index]['mac']
                    macxml = "<mac address='%s'/>" % mac
                if index == 0 and ip is not None:
                    version = "<entry name='version'>%s</entry>" % ip
            if netname in bridges:
                sourcenet = 'bridge'
            elif netname in networks:
                sourcenet = 'network'
            else:
                return {'result': 'failure', 'reason': "Invalid network %s" % netname}
            netxml = """%s
                     <interface type='%s'>
                     %s
                     <source %s='%s'/>
                     <model type='virtio'/>
                     </interface>""" % (netxml, sourcenet, macxml, sourcenet, netname)
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
                if os.path.isabs(iso):
                    shortiso = os.path.basename(iso)
                else:
                    shortiso = iso
                isovolume = volumes[shortiso]['object']
                iso = isovolume.path()
                # iso = "%s/%s" % (default_poolpath, iso)
                # iso = "%s/%s" % (isopath, iso)
            except:
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
            self._cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain, reserveip=reserveip)
            self._uploadimage(name, pool=default_storagepool)
        if reserveip:
            xml = vm.XMLDesc(0)
            vmxml = ET.fromstring(xml)
            macs = []
            for element in vmxml.getiterator('interface'):
                mac = element.find('mac').get('address')
                macs.append(mac)
            self._reserve_ip(name, nets, macs)
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
                return {'result': 'success'}
            else:
                vm.create()
                return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def stop(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
            if status[vm.isActive()] == "down":
                return {'result': 'success'}
            else:
                vm.destroy()
                return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}

    def restart(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        vm = conn.lookupByName(name)
        if status[vm.isActive()] == "down":
            return {'result': 'success'}
        else:
            vm.restart()
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
            elif self.host in ['localhost', '127.0.0.1']:
                os.system('virsh console %s' % name)
            else:
                for element in serial:
                    serialport = element.find('source').get('service')
                    if serialport:
                        if self.protocol != 'ssh':
                            print("Remote serial Console requires using ssh . Leaving...")
                            return
                        else:
                            serialcommand = "ssh -p %s %s@%s nc 127.0.0.1 %s" % (self.port, self.user, self.host, serialport)
                        os.system(serialcommand)

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

    def volumes(self, iso=False):
        isos = []
        templates = []
        default_templates = [os.path.basename(t) for t in TEMPLATES.values()]
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
                elif volume.endswith('qcow2') or volume in default_templates:
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
                if imagefile == "%s.iso" % name or name in imagefile:
                    disks.append(imagefile)
                else:
                    continue
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
                        try:
                            volume = storage.storageVolLookupByName(stor)
                        except:
                            continue
                        volume.delete(0)
                        deleted = True
            if deleted:
                storage.refresh(0)
        for element in root.getiterator('interface'):
            mac = element.find('mac').get('address')
            networktype = element.get('type')
            if networktype != 'bridge':
                network = element.find('source').get('network')
                network = conn.networkLookupByName(network)
                netxml = network.XMLDesc(0)
                root = ET.fromstring(netxml)
                for host in root.getiterator('host'):
                    hostmac = host.get('mac')
                    ip = host.get('ip')
                    name = host.get('name')
                    if hostmac == mac:
                        hostentry = "<host mac='%s' name='%s' ip='%s'/>" % (mac, name, ip)
                        network.update(2, 4, 0, hostentry, 1)

    def _xmldisk(self, diskpath, diskdev, diskbus='virtio', diskformat='qcow2', shareable=False):
        if shareable:
            sharexml = '<shareable/>'
        else:
            sharexml = ''
        diskxml = """<disk type='file' device='disk'>
        <driver name='qemu' type='%s' cache='none'/>
        <source file='%s'/>
        <target bus='%s' dev='%s'/>
        %s
        </disk>""" % (diskformat, diskpath, diskbus, diskdev, sharexml)
        return diskxml

    def _xmlvolume(self, path, size, pooltype='file', backing=None, diskformat='qcow2'):
        size = int(size) * MB
        if int(size) == 0:
            size = 500 * 1024
        name = os.path.basename(path)
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

    def _reserve_ip(self, name, nets, macs):
        conn = self.conn
        for index, net in enumerate(nets):
            if not isinstance(net, dict):
                continue
            ip = net.get('ip')
            network = net.get('name')
            mac = macs[index]
            if ip is None or network is None:
                continue
            network = conn.networkLookupByName(network)
            oldnetxml = network.XMLDesc()
            root = ET.fromstring(oldnetxml)
            ipentry = root.getiterator('ip')
            if ipentry:
                attributes = ipentry[0].attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                netip = IPNetwork('%s/%s' % (firstip, netmask))
            dhcp = root.getiterator('dhcp')
            if not dhcp:
                continue
            if not IPAddress(ip) in netip:
                continue
            network.update(4, 4, 0, '<host mac="%s" name="%s" ip="%s" />' % (mac, name, ip), 1)

    def _cloudinit(self, name, keys=None, cmds=None, nets=[], gateway=None, dns=None, domain=None, reserveip=False):
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
                    if ip is not None and netmask is not None and not reserveip:
                        metadata += "  iface %s inet static\n" % nicname
                        metadata += "  address %s\n" % ip
                        metadata += "  netmask %s\n" % netmask
                        gateway = net.get('gateway')
                        if index == 0 and default_gateway is not None:
                            metadata += "  gateway %s\n" % default_gateway
                        elif gateway is not None:
                            metadata += "  gateway %s\n" % gateway
                        dns = net.get('dns')
                        if dns is not None:
                            metadata += "  dns-nameservers %s\n" % dns
                        domain = net.get('domain')
                        if domain is not None:
                            metadatafile.write("  dns-search %s\n" % domain)
                    else:
                        metadata += "  iface %s inet dhcp\n" % nicname
                if metadata:
                    metadatafile.write("network-interfaces: |\n")
                    metadatafile.write(metadata)
                    # if dns is not None:
                    #    metadatafile.write("  dns-nameservers %s\n" % dns)
                    # if domain is not None:
                    #    metadatafile.write("  dns-search %s\n" % domain)
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
            elif os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
                publickeyfile = "%s/.ssh/id_dsa.pub" % os.environ['HOME']
                with open(publickeyfile, 'r') as ssh:
                    key = ssh.read().rstrip()
                    userdata.write("ssh_authorized_keys:\n")
                    userdata.write("- %s\n" % key)
            else:
                print("neither id_rsa.pub or id_dsa public keys found in your .ssh directory, you might have trouble accessing the vm")
            if cmds is not None:
                    userdata.write("runcmd:\n")
                    for cmd in cmds:
                        if cmd.startswith('#'):
                            continue
                        else:
                            userdata.write("- %s\n" % cmd)
        isocmd = 'mkisofs'
        if find_executable('genisoimage') is not None:
            isocmd = 'genisoimage'
        os.system("%s --quiet -o /tmp/%s.iso --volid cidata --joliet --rock /tmp/user-data /tmp/meta-data" % (isocmd, name))

    def handler(self, stream, data, file_):
        return file_.read(data)

    def _uploadimage(self, name, pool='default', origin='/tmp', suffix='.iso'):
        name = "%s%s" % (name, suffix)
        conn = self.conn
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in root.getiterator('path'):
            poolpath = element.text
            break
        imagepath = "%s/%s" % (poolpath, name)
        imagexml = self._xmlvolume(path=imagepath, size=0, diskformat='raw')
        pool.createXML(imagexml, 0)
        imagevolume = conn.storageVolLookupByPath(imagepath)
        stream = conn.newStream(0)
        imagevolume.upload(stream, 0, 0)
        with open("%s/%s" % (origin, name)) as ori:
            stream.sendAll(self.handler, ori)
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
        osentry = root.getiterator('os')[0]
        smbios = osentry.find('smbios')
        if smbios is None:
            newsmbios = ET.Element("smbios", mode="sysinfo")
            osentry.append(newsmbios)
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

    def update_start(self, name, start=True):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if start:
            vm.setAutostart(1)
        else:
            vm.setAutostart(0)
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
        diskpath = "%s/%s" % (poolpath, name)
        if pooltype == 'logical':
            diskformat = 'raw'
        volxml = self._xmlvolume(path=diskpath, size=size, pooltype=pooltype,
                                 diskformat=diskformat, backing=template)
        pool.createXML(volxml, 0)
        return diskpath

#    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False):
#        conn = self.conn
#        diskformat = 'qcow2'
#        diskbus = 'virtio'
#        if size < 1:
#            print("Incorrect size.Leaving...")
#            return
#        if not thin:
#            diskformat = 'raw'
#        try:
#            vm = conn.lookupByName(name)
#            xml = vm.XMLDesc(0)
#            root = ET.fromstring(xml)
#        except:
#            print("VM %s not found" % name)
#            return
#        currentdisk = 0
#        for element in root.getiterator('disk'):
#            disktype = element.get('device')
#            if disktype == 'cdrom':
#                continue
#            currentdisk = currentdisk + 1
#        diskindex = currentdisk + 1
#        diskdev = "vd%s" % string.ascii_lowercase[currentdisk]
#        if pool is not None:
#            pool = conn.storagePoolLookupByName(pool)
#            poolxml = pool.XMLDesc(0)
#            poolroot = ET.fromstring(poolxml)
#            pooltype = poolroot.getiterator('pool')[0].get('type')
#            for element in poolroot.getiterator('path'):
#                poolpath = element.text
#                break
#        else:
#            print("Pool not found. Leaving....")
#            return
#        if template is not None:
#            volumes = {}
#            for p in conn.listStoragePools():
#                poo = conn.storagePoolLookupByName(p)
#                for vol in poo.listAllVolumes():
#                    volumes[vol.name()] = vol.path()
#            if template not in volumes and template not in volumes.values():
#                print("Invalid template %s.Leaving..." % template)
#            if template in volumes:
#                template = volumes[template]
#        pool.refresh(0)
#        storagename = "%s_%d.img" % (name, diskindex)
#        diskpath = "%s/%s" % (poolpath, storagename)
#        volxml = self._xmlvolume(path=diskpath, size=size, pooltype=pooltype,
#                                 diskformat=diskformat, backing=template)
#        if pooltype == 'logical':
#            diskformat = 'raw'
#        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat, shareable=shareable)
#        pool.createXML(volxml, 0)
#        vm.attachDevice(diskxml)
#        vm = conn.lookupByName(name)
#        vmxml = vm.XMLDesc(0)
#        conn.defineXML(vmxml)

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
        if existing is None:
            storagename = "%s_%d.img" % (name, diskindex)
            diskpath = self.create_disk(name=storagename, size=size, pool=pool, thin=thin, template=template)
        else:
            diskpath = existing
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat, shareable=shareable)
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

    def ssh(self, name, local=None, remote=None):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            print("VM %s not found" % name)
            return
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
            sshcommand = "%s@%s" % (user, ip)
            if local is not None:
                sshcommand = "-L %s %s" % (local, sshcommand)
            if remote is not None:
                sshcommand = "-R %s %s" % (remote, sshcommand)
            sshcommand = "ssh %s" % sshcommand
            os.system(sshcommand)

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

    def add_image(self, image, pool):
        poolname = pool
        shortimage = os.path.basename(image)
        conn = self.conn
        volumes = []
        try:
            pool = conn.storagePoolLookupByName(pool)
            for vol in pool.listAllVolumes():
                volumes.append(vol.name())
        except:
            return {'result': 'failure', 'reason': "Pool %s not found" % poolname}
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        pooltype = root.getiterator('pool')[0].get('type')
        if pooltype == 'dir':
            poolpath = root.getiterator('path')[0].text
        else:
            poolpath = root.getiterator('device')[0].get('path')
            return {'result': 'failure', 'reason': "Upload to a lvm pool not implemented not found"}
        if shortimage in volumes:
            return {'result': 'failure', 'reason': "Template %s already exists in pool %s" % (shortimage, poolname)}
        if self.host == 'localhost' or self.host == '127.0.0.1':
            cmd = 'wget -P %s %s' % (poolpath, image)
        elif self.protocol == 'ssh':
            cmd = 'ssh -p %s %s@%s "wget -P %s %s"' % (self.port, self.user, self.host, poolpath, image)
        os.system(cmd)
        pool.refresh()
        # self._uploadimage(shortimage, pool=pool, suffix='')
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True):
        conn = self.conn
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
            return {'result': 'failure', 'reason': "Network %s is beeing used by %s" % (name, machines)}
        if network.isActive():
            network.destroy()
        network.undefine()
        return {'result': 'success'}

    def list_pools(self):
        pools = []
        conn = self.conn
        for pool in conn.listStoragePools():
            pools.append(pool)
        return pools

    def list_networks(self):
        networks = {}
        conn = self.conn
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
            netxml = interface.XMLDesc(0)
            root = ET.fromstring(netxml)
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

    def bootstrap(self, pool=None, poolpath=None, pooltype='dir', nets={}, image=None):
        conn = self.conn
        volumes = {}
        try:
            poolname = pool
            pool = conn.storagePoolLookupByName(pool)
            for vol in pool.listAllVolumes():
                volumes[vol.name()] = {'object': vol}
        except:
            if poolpath is not None:
                print("Pool %s not found...Creating it" % pool)
                self.create_pool(name=pool, poolpath=poolpath, pooltype=pooltype)
        if image is not None and os.path.basename(image) not in volumes:
            self.add_image(image, poolname)
        networks = []
        for net in conn.listNetworks():
            networks.append(net)
        for net in nets:
            if net not in networks:
                print("Network %s not found...Creating it" % net)
                cidr = nets[net].get('cidr')
                dhcp = bool(nets[net].get('dchp', True))
                self.create_network(name=net, cidr=cidr, dhcp=dhcp)

    def network_ports(self, name):
        conn = self.conn
        machines = []
        for vm in conn.listAllDomains(0):
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            for element in root.getiterator('interface'):
                networktype = element.get('type')
                if networktype == 'bridge':
                    network = element.find('source').get('bridge')
                else:
                    network = element.find('source').get('network')
            if network == name:
                machines.append(vm.name())
        return machines

    def vm_ports(self, name):
        conn = self.conn
        networks = []
        try:
            vm = conn.lookupByName(name)
        except:
            print("VM %s not found" % name)
            return
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        for element in root.getiterator('interface'):
            networktype = element.get('type')
            if networktype == 'bridge':
                network = element.find('source').get('bridge')
            else:
                network = element.find('source').get('network')
            networks.append(network)
        return networks

    def create_container(self, name, image, nets=None, cmd=None, ports=[], volumes=[], label=None):
        # if not nets:
        #    return
        # for i, net in enumerate(nets):
        #    print net
        #    if isinstance(net, str):
        #        netname = net
        #    elif isinstance(net, dict) and 'name' in net:
        #        netname = net['name']
        #    nets[i] = self._get_bridge(netname)
        if self.host == '127.0.0.1':
            for i, volume in enumerate(volumes):
                if isinstance(volume, str):
                    if len(volume.split(':')) == 2:
                        origin, destination = volume.split(':')
                        volumes[i] = {origin: {'bind': destination, 'mode': 'rw'}}
                    else:
                        volumes[i] = {volume: {'bind': volume, 'mode': 'rw'}}
                elif isinstance(volume, dict):
                    path = volume.get('path')
                    origin = volume.get('origin')
                    destination = volume.get('destination')
                    mode = volume.get('mode', 'rw')
                    if origin is None or destination is None:
                        if path is None:
                            continue
                        volumes[i] = {path: {'bind': path, 'mode': mode}}
                    else:
                        volumes[i] = {origin: {'bind': destination, 'mode': mode}}
            if ports is not None:
                ports = {'%s/tcp' % k: k for k in ports}
            if label is not None and isinstance(label, str) and len(label.split('=')) == 2:
                key, value = label.split('=')
                labels = {key: value}
            else:
                labels = None
            base_url = 'unix://var/run/docker.sock'

            d = docker.DockerClient(base_url=base_url, version='1.22')
            # d.containers.run(image, name=name, command=cmd, networks=nets, detach=True, ports=ports)
            d.containers.run(image, name=name, command=cmd, detach=True, ports=ports, volumes=volumes, stdin_open=True, tty=True, labels=labels)
        else:
            # netinfo = ''
            # for net in nets:
            #    netinfo = "%s --net=%s" % (netinfo, net)
            portinfo = ''
            if ports is not None:
                for port in ports:
                    if isinstance(port, int):
                        oriport = port
                        destport = port
                    elif isinstance(port, str):
                        if len(port.split(':')) == 2:
                            oriport, destport = port.split(':')
                        else:
                            oriport = port
                            destport = port
                    elif isinstance(port, dict) and 'origin' in port and 'destination' in port:
                        oriport = port['origin']
                        destport = port['destination']
                    else:
                        continue
                    portinfo = "%s -p %s:%s" % (portinfo, oriport, destport)
            volumeinfo = ''
            if volumes is not None:
                for volume in volumes:
                    if isinstance(volume, str):
                        if len(volume.split(':')) == 2:
                            origin, destination = volume.split(':')
                        else:
                            origin = volume
                            destination = volume
                    elif isinstance(volume, dict):
                        path = volume.get('path')
                        origin = volume.get('origin')
                        destination = volume.get('destination')
                        if origin is None or destination is None:
                            if path is None:
                                continue
                            origin = path
                            destination = path
                    volumeinfo = "%s -v %s:%s" % (volumeinfo, origin, destination)
            dockercommand = "docker run -it %s %s --name %s -l %s -d %s" % (volumeinfo, portinfo, name, label, image)
            if cmd is not None:
                dockercommand = "%s %s" % (dockercommand, cmd)
            command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
            os.system(command)

    def delete_container(self, name):
        if self.host == '127.0.0.1':
            base_url = 'unix://var/run/docker.sock'
            d = docker.DockerClient(base_url=base_url, version='1.22')
            containers = [container for container in d.containers.list() if container.name == name]
            if containers:
                for container in containers:
                    container.remove(force=True)
        else:
            dockercommand = "docker rm -f %s" % name
            command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
            os.system(command)

    def start_container(self, name):
        if self.host == '127.0.0.1':
            base_url = 'unix://var/run/docker.sock'
            d = docker.DockerClient(base_url=base_url, version='1.22')
            containers = [container for container in d.containers.list(all=True) if container.name == name]
            if containers:
                for container in containers:
                    container.start()
        else:
            dockercommand = "docker start %s" % name
            command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
            os.system(command)

    def stop_container(self, name):
        if self.host == '127.0.0.1':
            base_url = 'unix://var/run/docker.sock'
            d = docker.DockerClient(base_url=base_url, version='1.22')
            containers = [container for container in d.containers.list() if container.name == name]
            if containers:
                for container in containers:
                    container.stop()
        else:
            dockercommand = "docker stop %s" % name
            command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
            os.system(command)

    def console_container(self, name):
        if self.host == '127.0.0.1':
            # base_url = 'unix://var/run/docker.sock'
            dockercommand = "docker attach %s" % name
            os.system(dockercommand)
            # d = docker.DockerClient(base_url=base_url)
            # containers = [container.id for container in d.containers.list() if container.name == name]
            # if containers:
            #    for container in containers:
            #        container.attach()
        else:
            dockercommand = "docker attach %s" % name
            command = "ssh -t -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
            os.system(command)

    def list_containers(self):
        containers = []
        if self.host == '127.0.0.1':
            base_url = 'unix://var/run/docker.sock'
            d = docker.DockerClient(base_url=base_url, version='1.22')
            # containers = [container.name for container in d.containers.list()]
            for container in d.containers.list(all=True):
                name = container.name
                state = container.status
                state = state.split(' ')[0]
                if state.startswith('running'):
                    state = 'up'
                else:
                    state = 'down'
                source = container.attrs['Config']['Image']
                labels = container.attrs['Config']['Labels']
                if 'plan' in labels:
                    plan = labels['plan']
                else:
                    plan = ''
                command = container.attrs['Config']['Cmd']
                if command is None:
                    command = ''
                else:
                    command = command[0]
                ports = container.attrs['NetworkSettings']['Ports']
                if ports:
                    portinfo = []
                    for port in ports:
                        if ports[port] is None:
                            newport = port
                        else:
                            hostport = ports[port][0]['HostPort']
                            hostip = ports[port][0]['HostIp']
                            newport = "%s:%s->%s" % (hostip, hostport, port)
                        portinfo.append(newport)
                    portinfo = ','.join(portinfo)
                else:
                    portinfo = ''
                containers.append([name, state, source, plan, command, portinfo])
        else:
            containers = []
            # dockercommand = "docker ps --format '{{.Names}}'"
            dockercommand = "docker ps -a --format \"'{{.Names}}?{{.Status}}?{{.Image}}?{{.Command}}?{{.Ports}}?{{.Label \\\"plan\\\"}}'\""
            command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
            results = os.popen(command).readlines()
            for container in results:
                #    containers.append(container.strip())
                name, state, source, command, ports, plan = container.split('?')
                if state.startswith('Up'):
                    state = 'up'
                else:
                    state = 'down'
                # labels = {i.split('=')[0]: i.split('=')[1] for i in labels.split(',')}
                # if 'plan' in labels:
                #    plan = labels['plan']
                # else:
                #     plan = ''
                command = command.strip().replace('"', '')
                containers.append([name, state, source, plan, command, ports])
        return containers

    def exists_container(self, name):
        if self.host == '127.0.0.1':
            base_url = 'unix://var/run/docker.sock'
            d = docker.DockerClient(base_url=base_url, version='1.22')
            containers = [container.id for container in d.containers.list(all=True) if container.name == name]
            if containers:
                return True
        else:
            dockercommand = "docker ps -a --format '{{.Names}}'"
            command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
            results = os.popen(command).readlines()
            for container in results:
                containername = container.strip()
                if containername == name:
                    return True
        return False

    def _get_bridge(self, name):
        conn = self.conn
        bridges = [interface.name() for interface in conn.listAllInterfaces()]
        if name in bridges:
            return name
        try:
            net = self.conn.networkLookupByName(name)
        except:
            return None
        netxml = net.XMLDesc(0)
        root = ET.fromstring(netxml)
        bridge = root.getiterator('bridge')
        if bridge:
            attributes = bridge[0].attrib
            bridge = attributes.get('name')
        return bridge
