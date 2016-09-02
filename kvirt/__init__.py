# -*- coding: utf-8 -*-

from prettytable import PrettyTable
import os
import sys
import time
import libvirt
import xml.etree.ElementTree as ET

KB = 1024 * 1024
MB = 1024 * 1024
GB = 1024 * MB
guestrhel332 = "rhel_3"
guestrhel364 = "rhel_3x64"
guestrhel432 = "rhel_4"
guestrhel464 = "rhel_4x64"
guestrhel532 = "rhel_5"
guestrhel564 = "rhel_5x64"
guestrhel632 = "rhel_6"
guestrhel664 = "rhel_6x64"
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
        if protocol == 'ssh':
            url = "qemu+%s://%s@%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, user, host)
        elif user and port:
            url = "qemu+%s://%s@%s:%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, user, host, port)
        elif port:
            url = "qemu+%s://%s:%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, host, port)
        else:
            url = "qemu///system"
            self.macaddr = []
        self.conn = libvirt.open(url)
        self.host = host
        self.macaddr = []

    def close(self):
        conn = self.conn
        conn.close()
        self.conn = None

    def exists(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            return True
        except:
            return False

    def create(self, name, clu, numcpu, numinterfaces, netinterface, diskthin1, disksize1, diskinterface, memory, storagedomain, guestid, net1, net2=None, net3=None, net4=None, mac1=None, mac2=None, launched=True, iso=None, diskthin2=None, disksize2=None, vnc=False):
        if vnc:
            display = 'vnc'
        else:
            display = 'spice'
        conn = self.conn
        networks = []
        bridges = []
        for net in conn.listNetworks():
            networks.append(net)
        for net in conn.listInterfaces():
            if net != 'lo':
                bridges.append(net)
        if net1 in bridges:
            sourcenet1 = 'bridge'
        else:
            sourcenet1 = 'network'
        # type,machine,emulator = 'kvm','pc','/usr/libexec/qemu-kvm'
        type, machine, emulator = 'kvm', 'pc', '/usr/bin/qemu-system-x86_64'
        memory = memory * 1024
        diskformat1, diskformat2 = 'raw', 'raw'
        disksize1 = disksize1 * GB
        if diskthin1:
            diskformat1 = 'cow'
        if disksize2:
            disksize2 = disksize2 * GB
            if diskthin2:
                diskformat2 = 'cow'
        storagename = "%s.img" % name
        storagepool = conn.storagePoolLookupByName(storagedomain)
        poolxml = storagepool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in root.getiterator('path'):
            storagepath = element.text
            break
        allocation = 0
        diskxml = """<volume>
                        <name>%s</name>
                        <key>%s/%s</key>
                        <source>
                        </source>
                        <capacity unit='bytes'>%s</capacity>
                        <allocation unit='bytes'>0</allocation>
                        <target>
                        <path>%s/%s</path>
                        <format type='%s'/>
                        </target>
                        </volume>""" % (storagename, storagepath, storagename, disksize1, storagepath, storagename, diskformat1)
        storagepool.createXML(diskxml, 0)
        if disksize2:
            storagename2 = "%s-1.img" % name
            diskxml = """<volume>
                    <name>%s</name>
                    <key>%s/%s</key>
                    <source>
                    </source>
                    <capacity unit='bytes'>%s</capacity>
                    <allocation unit='bytes'>0</allocation>
                    <target>
                    <path>%s/%s</path>
                    <format type='%s'/>
                    </target>
                    </volume>""" % (storagename2, storagepath, storagename2, disksize2, storagepath, storagename2, diskformat1)
            storagepool.createXML(diskxml, 0)
        storagepool.refresh(0)
        diskdev1, diskbus1 = 'vda', 'virtio'
        diskdev2, diskbus2 = 'vdb', 'virtio'
        if diskinterface != 'virtio':
            diskdev1, diskbus1 = 'hda', 'ide'
            diskdev2, diskbus2 = 'hdb', 'ide'
        if not iso:
            iso = ''
        vmxml = """<domain type='%s'>
                  <name>%s</name>
                  <memory>%d</memory>
                  <vcpu>%s</vcpu>
                  <os>
                    <type arch='x86_64' machine='%s'>hvm</type>
                    <boot dev='hd'/>
                    <boot dev='cdrom'/>
                    <bootmenu enable='yes'/>
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
                      <source file='%s/%s'/>
                      <target dev='%s' bus='%s'/>
                    </disk>""" % (type, name, memory, numcpu, machine, emulator, diskformat1, storagepath, storagename, diskdev1, diskbus1)
        if disksize2:
            vmxml = """%s
                    <disk type='file' device='disk'>
                    <driver name='qemu' type='%s'/>
                    <source file='%s/%s'/>
                    <target dev='%s' bus='%s'/>
                    </disk>""" % (vmxml, diskformat1, storagepath, storagename2, diskdev2, diskbus2)

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
            else:
                sourcenet2 = 'network'
            vmxml = """%s
             <interface type='%s'>
              <source %s='%s'/>
            <model type='virtio'/>
            </interface>""" % (vmxml, sourcenet2, sourcenet2, net2)
        if net3:
            if net3 in bridges:
                sourcenet3 = 'bridge'
            else:
                sourcenet3 = 'network'
            vmxml = """%s
             <interface type='%s'>
              <source %s='%s'/>
            <model type='virtio'/>
            </interface>""" % (vmxml, sourcenet3, sourcenet3, net3)
        if net4:
            if net4 in bridges:
                sourcenet4 = 'bridge'
            else:
                sourcenet4 = 'network'
            vmxml = """%s
             <interface type='%s'>
              <source %s='%s'/>
            <model type='virtio'/>
            </interface>""" % (vmxml, sourcenet4, sourcenet4, net4)
        vmxml = """%s
                <input type='tablet' bus='usb'/>
                 <input type='mouse' bus='ps2'/>
                <graphics type='%s' port='-1' autoport='yes' listen='0.0.0.0'>
                 <listen type='address' address='0.0.0.0'/>
                </graphics>
                <memballoon model='virtio'/>
                </devices>
                </domain>""" % (vmxml, display)
        conn.defineXML(vmxml)
        vm = conn.lookupByName(name)
        vm.setAutostart(1)
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        macs = {}
        for element in root.getiterator('interface'):
            mac = element.find('mac').get('address')
            network = element.find('source').get('network')
            bridge = element.find('source').get('bridge')
            if bridge:
                macs[bridge] = mac
            else:
                macs[network] = mac
        for net in [net1, net2, net3, net4]:
            if not net:
                break
            else:
                self.macaddr.append(macs[net])

    def getmacs(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            return None
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        macs = []
        for element in root.getiterator('interface'):
            mac = element.find('mac').get('address')
            network = element.find('source').get('network')
            bridge = element.find('source').get('bridge')
            if bridge:
                netname = bridge
            else:
                netname = network
            macs.append("%s=%s" % (netname, mac))
        return macs

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

    def getstorage(self):
        results = {}
        conn = self.conn
        for storage in conn.listStoragePools():
            storagename = storage
            storage = conn.storagePoolLookupByName(storage)
            s = storage.info()
            used = "%.2f" % (float(s[2]) / 1024 / 1024 / 1024)
            available = "%.2f" % (float(s[3]) / 1024 / 1024 / 1024)
            # Type,Status, Total space in Gb, Available space in Gb
            results[storagename] = [float(used), float(available), storagename]
        return results

    def beststorage(self):
        bestsize = 0
        beststoragedomain = ''
        conn = self.conn
        for stor in conn.listStoragePools():
            storagename = stor
            storage = conn.storagePoolLookupByName(stor)
            s = storage.info()
            used = float(s[2]) / 1024 / 1024 / 1024
            available = float(s[3]) / 1024 / 1024 / 1024
            if available > bestsize:
                beststoragedomain = storagename
                bestsize = available
        return beststoragedomain

    def status(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        vm = conn.lookupByName(name)
        if not vm:
            return None
        else:
            return status[vm.isActive()]

    def list(self):
        vms = PrettyTable(["Name", "Status", "Ips"])
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        for vm in conn.listAllDomains(0):
            name = vm.name()
            state = status[vm.isActive()]
            vms.add_row([name, state, ''])
        return vms

    def console(self, name):
        conn = self.conn
        vm = conn.lookupByName(name)
        if not vm or vm.isActive() == 0:
            return None, None, None, None
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
                if protocol == "spice":
                    # sport = attributes['tlsPort']
                    return host, port, None, protocol
                else:
                    return host, port, None, protocol

    def info(self, name):
        conn = self.conn
        vm = conn.lookupByName(name)
        if not vm:
            return None
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            print dir(vm)
            print "name: %s" % name
            for element in root.getiterator('interface'):
                mac = element.find('mac').get('address')
                network = element.find('source').get('network')
                bridge = element.find('source').get('bridge')
                if bridge:
                    macs[bridge] = mac
                else:
                    macs[network] = mac
            for net in [net1, net2, net3, net4]:
                if not net:
                    break
                else:
                    self.macaddr.append(macs[net])

    def getisos(self):
        isos = []
        conn = self.conn
        for storage in conn.listStoragePools():
            storage = conn.storagePoolLookupByName(storage)
            storagexml = storage.XMLDesc(0)
            root = ET.fromstring(storagexml)
            for element in root.getiterator('path'):
                storagepath = element.text
                break
            for volume in storage.listVolumes():
                if volume.endswith('iso'):
                    isos.append("%s/%s" % (storagepath, volume))
        return isos

    def remove(self, name):
        conn = self.conn
        vm = conn.lookupByName(name)
        status = {0: 'down', 1: 'up'}
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        disks = []
        for element in root.getiterator('disk'):
            source = element.find('source')
            if source is not None:
                imagefile = element.find('source').get('file')
                if 'iso' not in imagefile:
                    disks.append(imagefile)
        if status[vm.isActive()] != "down":
            vm.destroy()
        vm.undefine()
        for storage in conn.listStoragePools():
            deleted = False
            storage = conn.storagePoolLookupByName(storage)
            for stor in storage.listVolumes():
                for disk in disks:
                    if stor in disk:
                        volume = storage.storageVolLookupByName(stor)
                        volume.delete(0)
                        deleted = True
            if deleted:
                storage.refresh(0)
