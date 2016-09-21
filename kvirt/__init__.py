#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

from libvirt import open as libvirtopen
from libvirt import VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE
import os
import string
import xml.etree.ElementTree as ET

__version__ = "1.0.10"

KB = 1024 * 1024
MB = 1024 * KB
GB = 1024 * MB
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
    def __init__(self, host='127.0.0.1', port=None, user='root', protocol='ssh'):
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

    def create(self, name, title='', description='kvirt', numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disksize1=10, diskthin1=True, diskinterface1='virtio', disksize2=0, diskthin2=True, diskinterface2='virtio', disksize3=0, diskthin3=True, diskinterface3='virtio', disksize4=0, diskthin4=True, diskinterface4='virtio', net1='default', net2=None, net3=None, net4=None, iso=None, vnc=False, cloudinit=True, start=True, keys=None, cmds=None, ip1=None, netmask1=None, gateway1=None, ip2=None, netmask2=None, ip3=None, netmask3=None, ip4=None, netmask4=None, nested=True, dns=None, domain=None):
        if vnc:
            display = 'vnc'
        else:
            display = 'spice'
        conn = self.conn
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
        if net1 in bridges:
            sourcenet1 = 'bridge'
        elif net1 in networks:
            sourcenet1 = 'network'
        else:
            print "Invalid network %s .Leaving..." % net1
            return
        virttype, machine, emulator = 'kvm', 'pc', '/usr/libexec/qemu-kvm'
        # type, machine, emulator = 'kvm', 'pc', '/usr/bin/qemu-system-x86_64'
        diskformat1, diskformat2 = 'qcow2', 'qcow2'
        diskformat3, diskformat4 = 'qcow2', 'qcow2'
        if not diskthin1:
            diskformat1 = 'raw'
        if disksize2 > 0:
            if not diskthin2:
                diskformat2 = 'raw'
        if disksize3 > 0:
            if not diskthin3:
                diskformat3 = 'raw'
        if disksize4 > 0:
            if not diskthin4:
                diskformat4 = 'raw'
        storagename1 = "%s_1.img" % name
        pool = conn.storagePoolLookupByName(pool)
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in root.getiterator('path'):
            poolpath = element.text
            break
        diskpath1 = "%s/%s" % (poolpath, storagename1)
        if template is not None:
            try:
                pool.refresh(0)
                # backingvolume = pool.storageVolLookupByName(template)
                backingvolume = volumes[template]['object']
                backingxml = backingvolume.XMLDesc(0)
                root = ET.fromstring(backingxml)
            except:
                print "Invalid template %s.Leaving..." % template
                return
            backing = backingvolume.path()
            backingxml = """<backingStore type='file' index='1'>
        <format type='raw'/>
        <source file='%s'/>
        <backingStore/>
      </backingStore>""" % backing
        else:
            backing = None
            backingxml = '<backingStore/>'
        volxml1 = self._xmlvolume(path=diskpath1, size=disksize1, backing=backing, diskformat=diskformat1)
        if disksize2 > 0:
            storagename2 = "%s_2.img" % name
            diskpath2 = "%s/%s" % (poolpath, storagename2)
            volxml2 = self._xmlvolume(path=diskpath2, size=disksize2, diskformat=diskformat2, backing=None)
        if disksize3 > 0:
            storagename3 = "%s_3.img" % name
            diskpath3 = "%s/%s" % (poolpath, storagename3)
            volxml3 = self._xmlvolume(path=diskpath3, size=disksize3, diskformat=diskformat3, backing=None)
        if disksize4 > 0:
            storagename4 = "%s_4.img" % name
            diskpath4 = "%s/%s" % (poolpath, storagename4)
            volxml4 = self._xmlvolume(path=diskpath4, size=disksize4, diskformat=diskformat4, backing=None)
        pool.refresh(0)
        diskdev1, diskbus1 = 'vda', 'virtio'
        diskdev2, diskbus2 = 'vdb', 'virtio'
        diskdev3, diskbus3 = 'vdc', 'virtio'
        diskdev4, diskbus4 = 'vdd', 'virtio'
        if diskinterface1 != 'virtio':
            diskdev1, diskbus1 = 'hda', 'ide'
        if diskinterface2 != 'virtio':
            diskdev2, diskbus2 = 'hdb', 'ide'
        if diskinterface3 != 'virtio':
            diskdev3, diskbus3 = 'hdb', 'ide'
        if diskinterface4 != 'virtio':
            diskdev4, diskbus4 = 'hdb', 'ide'
        if iso is None:
            if cloudinit:
                iso = "%s/%s.iso" % (poolpath, name)
            else:
                iso = ''
        else:
            try:
                iso = "%s/%s" % (poolpath, iso)
                isovolume = volumes[template][iso]
                iso = isovolume.path()
            except:
                print "Invalid Iso %s.Leaving..." % iso
                return
        if ip1 is not None:
            version = "<entry name='version'>%s</entry>" % ip1
        else:
            version = ''
        version = """<sysinfo type='smbios'>
                    <system>
                    %s
                    <entry name='product'>%s</entry>
                    </system>
                    </sysinfo>""" % (version, title)
        sysinfo = "<smbios mode='sysinfo'/>"
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
                    <emulator>%s</emulator>
                    <disk type='file' device='disk'>
                    <driver name='qemu' type='%s'/>
                    <source file='%s'/>
                    %s
                    <target dev='%s' bus='%s'/>
                    </disk>""" % (virttype, name, description, version, memory, numcpus, machine, sysinfo, emulator, diskformat1, diskpath1, backingxml, diskdev1, diskbus1)
        if disksize2:
            diskxml2 = self._xmldisk(diskpath=diskpath2, diskdev=diskdev2, diskbus=diskbus2, diskformat=diskformat2)
            vmxml = "%s%s" % (vmxml, diskxml2)
        if disksize3:
            diskxml3 = self._xmldisk(diskpath=diskpath3, diskdev=diskdev3, diskbus=diskbus3, diskformat=diskformat3)
            vmxml = "%s%s" % (vmxml, diskxml3)
        if disksize4:
            diskxml4 = self._xmldisk(diskpath=diskpath4, diskdev=diskdev4, diskbus=diskbus4, diskformat=diskformat4)
            vmxml = "%s%s" % (vmxml, diskxml4)
        vmxml = """%s
                <disk type='file' device='cdrom'>
                      <driver name='qemu' type='raw'/>
                      <source file='%s'/>
                      <target dev='hdc' bus='ide'/>
                      <readonly/>
                  </disk>
                 <interface type='%s'>
                  <source %s='%s'/>
                <model type='virtio'/>
                </interface>""" % (vmxml, iso, sourcenet1, sourcenet1, net1)
        if net2:
            if net2 in bridges:
                sourcenet2 = 'bridge'
            elif net2 in networks:
                sourcenet2 = 'network'
            else:
                print "Invalid network %s.Leaving..." % net2
                return
            vmxml = """%s
             <interface type='%s'>
              <source %s='%s'/>
            <model type='virtio'/>
            </interface>""" % (vmxml, sourcenet2, sourcenet2, net2)
        if net3:
            if net3 in bridges:
                sourcenet3 = 'bridge'
            elif net3 in networks:
                sourcenet3 = 'network'
            else:
                print "Invalid network %s.Leaving..." % net3
                return
            vmxml = """%s
             <interface type='%s'>
              <source %s='%s'/>
            <model type='virtio'/>
            </interface>""" % (vmxml, sourcenet3, sourcenet3, net3)
        if net4:
            if net4 in bridges:
                sourcenet4 = 'bridge'
            elif net4 in networks:
                sourcenet4 = 'network'
            else:
                print "Invalid network %s.Leaving..." % net4
                return
            vmxml = """%s
             <interface type='%s'>
              <source %s='%s'/>
            <model type='virtio'/>
            </interface>""" % (vmxml, sourcenet4, sourcenet4, net4)
        if nested:
            nestedxml = """<cpu match='exact'>
                  <model>Westmere</model>
                   <feature policy='require' name='vmx'/>
                </cpu>"""
        else:
            nestedxml = ""
        vmxml = """%s
                <input type='tablet' bus='usb'/>
                 <input type='mouse' bus='ps2'/>
                <graphics type='%s' port='-1' autoport='yes' listen='0.0.0.0'>
                 <listen type='address' address='0.0.0.0'/>
                </graphics>
                <memballoon model='virtio'/>
                </devices>
                %s
                </domain>""" % (vmxml, display, nestedxml)
        pool.createXML(volxml1, 0)
        if disksize2 > 0:
            pool.createXML(volxml2, 0)
        if disksize3 > 0:
            pool.createXML(volxml3, 0)
        if disksize4 > 0:
            pool.createXML(volxml4, 0)
        conn.defineXML(vmxml)
        vm = conn.lookupByName(name)
        vm.setAutostart(1)
        if cloudinit:
            self._cloudinit(name=name, keys=keys, cmds=cmds, ip1=ip1, netmask1=netmask1, gateway1=gateway1, ip2=ip2, netmask2=netmask2, ip3=ip3, netmask3=netmask3, ip4=ip4, netmask4=netmask4, dns=dns, domain=domain)
            self._uploadiso(name, pool=pool)
        if start:
            vm.create()

    def start(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        vm = conn.lookupByName(name)
        vm = conn.lookupByName(name)
        if status[vm.isActive()] == "up":
            return
        else:
            vm.create()

    def stop(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        vm = conn.lookupByName(name)
        if status[vm.isActive()] == "down":
            return
        else:
            vm.destroy()

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
        print "Host: %s Cpu:%s Memory:%sMB" % (hostname, cpus, memory)
        for storage in conn.listStoragePools():
            storagename = storage
            storage = conn.storagePoolLookupByName(storage)
            s = storage.info()
            used = "%.2f" % (float(s[2]) / 1024 / 1024 / 1024)
            available = "%.2f" % (float(s[3]) / 1024 / 1024 / 1024)
            # Type,Status, Total space in Gb, Available space in Gb
            used = float(used)
            available = float(available)
            print "Storage: %s Used space: %sGB Available space:%sGB" % (storagename, used, available)
        for interface in conn.listAllInterfaces():
            interfacename = interface.name()
            if interfacename == 'lo':
                continue
            print "Network: %s Type: bridged" % (interfacename)
        for network in conn.listAllNetworks():
            networkname = network.name()
            print "Network: %s Type: routed" % (networkname)

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
        conn = self.conn
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
            ip = ''
            title = ''
            if vm.isActive():
                try:
                    for address in vm.interfaceAddresses(VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE).values():
                        ip = address['addrs'][0]['addr']
                        break
                except:
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
            print "VM down"
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

    def info(self, name):
        ips = []
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print "VM %s not found" % name
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
        print "name: %s" % name
        print "status: %s" % state
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
        print "description: %s" % description
        if title is not None:
            print "profile: %s" % title
        print "cpus: %s" % numcpus
        print "memory: %sMB" % memory
        nicnumber = 0
        for element in root.getiterator('interface'):
            networktype = element.get('type')
            device = "eth%s" % nicnumber
            mac = element.find('mac').get('address')
            if networktype == 'bridge':
                bridge = element.find('source').get('bridge')
                print "net interfaces: %s mac: %s net: %s type: bridge" % (device, mac, bridge)
            else:
                network = element.find('source').get('network')
                print "net interfaces: %s mac: %s net: %s type: routed" % (device, mac, network)
                network = conn.networkLookupByName(network)
            if vm.isActive():
                for address in vm.interfaceAddresses(VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE).values():
                    if address['hwaddr'] == mac:
                        ip = address['addrs'][0]['addr']
                        ips.append(ip)
        for entry in root.getiterator('entry'):
            attributes = entry.attrib
            if attributes['name'] == 'version':
                ip = entry.text
                ips.append(ip)
                break
            nicnumber = nicnumber + 1
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
            print "diskname: %s disksize: %sGB diskformat: %s type: %s  path: %s" % (device, disksize, diskformat, drivertype, path)
        for ip in ips:
            print "ip: %s" % ip

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

    def _xmlvolume(self, path, size, backing=None, diskformat='qcow2'):
        size = int(size) * MB
        name = path.split('/')[-1]
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

    def clone(self, old, new, full=False):
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
        newxml = ET.tostring(tree)
        conn.defineXML(newxml)
        vm = conn.lookupByName(new)
        vm.setAutostart(1)
        vm.create()

    def _cloudinit(self, name, keys=None, cmds=None, ip1=None, netmask1=None, gateway1=None, ip2=None, netmask2=None, ip3=None, netmask3=None, ip4=None, netmask4=None, dns=None, domain=None):
        with open('/tmp/meta-data', 'w') as metadata:
            if domain is not None:
                localhostname = "%s.%s" % (name, domain)
            else:
                localhostname = name
            metadata.write('instance-id: XXX\nlocal-hostname: %s\n' % localhostname)
            if ip1 is not None and netmask1 is not None and gateway1 is not None:
                metadata.write("network-interfaces: |\n")
                metadata.write("  iface eth0 inet static\n")
                metadata.write("  address %s\n" % ip1)
                metadata.write("  netmask %s\n" % netmask1)
                metadata.write("  gateway %s\n" % gateway1)
                if ip2 is not None and netmask2 is not None:
                    metadata.write("  iface eth1 inet static\n")
                    metadata.write("  address %s\n" % ip2)
                    metadata.write("  netmask %s\n" % netmask2)
                if ip3 is not None and netmask3 is not None:
                    metadata.write("  iface eth2 inet static\n")
                    metadata.write("  address %s\n" % ip3)
                    metadata.write("  netmask %s\n" % netmask3)
                if ip4 is not None and netmask4 is not None:
                    metadata.write("  iface eth3 inet static\n")
                    metadata.write("  address %s\n" % ip4)
                    metadata.write("  netmask %s\n" % netmask4)
                if dns is not None:
                    metadata.write("  dns-nameservers %s\n" % dns)
                if domain is not None:
                    metadata.write("  dns-search %s\n" % domain)
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
        os.system("mkisofs --quiet -o /tmp/%s.iso --volid cidata --joliet --rock /tmp/user-data /tmp/meta-data" % name)

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
            print "VM %s not found" % name
        if vm.isActive() == 1:
            print "Machine up. Change will only appear upon next reboot"
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
        memory = str(int(memory) * KB)
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print "VM %s not found" % name
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
            print "VM %s not found" % name
            return
        cpunode = root.getiterator('vcpu')[0]
        cpunode.text = numcpus
        newxml = ET.tostring(root)
        conn.defineXML(newxml)

    def add_disk(self, name, size, pool=None, thin=True):
        conn = self.conn
        diskformat = 'qcow2'
        diskbus = 'virtio'
        if size < 1:
            print "Incorrect size.Leaving..."
            return
        if not thin:
            diskformat = 'raw'
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print "VM %s not found" % name
            return
        currentdisk = 0
        for element in root.getiterator('disk'):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            path = element.find('source').get('file')
            currentpoolpath = os.path.dirname(path)
            currentdisk = currentdisk + 1
        diskindex = currentdisk + 1
        diskdev = "vd%s" % string.ascii_lowercase[currentdisk]
        if pool is not None:
            pool = conn.storagePoolLookupByName(pool)
            poolxml = pool.XMLDesc(0)
            poolroot = ET.fromstring(poolxml)
            for element in poolroot.getiterator('path'):
                poolpath = element.text
                break
        elif currentpoolpath is not None:
            poolpath = currentpoolpath
            for p in conn.listStoragePools():
                poo = conn.storagePoolLookupByName(p)
                poolxml = poo.XMLDesc(0)
                poolroot = ET.fromstring(poolxml)
                for element in poolroot.getiterator('path'):
                    if poolpath == currentpoolpath:
                        pool = poo
                        break
        else:
            print "Pool not found. Leaving...."
            return
        pool.refresh(0)
        storagename = "%s_%d.img" % (name, diskindex)
        diskpath = "%s/%s" % (poolpath, storagename)
        volxml = self._xmlvolume(path=diskpath, size=size, diskformat=diskformat, backing=None)
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
        pool.createXML(volxml, 0)
        vm.attachDevice(diskxml)

    def ssh(self, name):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        conn = self.conn
        vm = conn.lookupByName(name)
        if not vm:
            print "VM %s not found" % name
        if vm.isActive() != 1:
            print "Machine down. Cant ssh..."
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
        ip = vm[2]
        if ip == '':
            print "No ip found. Cant ssh..."
        else:
            os.system("ssh %s@%s" % (user, ip))
