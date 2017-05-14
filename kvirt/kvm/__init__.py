#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

from distutils.spawn import find_executable
from kvirt import defaults
from iptools import IpRange
# from jinja2 import Environment
from kvirt import common
from kvirt.base import Kbase
from netaddr import IPAddress, IPNetwork
from libvirt import open as libvirtopen, registerErrorHandler
import os
import re
import string
import time
import xml.etree.ElementTree as ET
from StringIO import StringIO
from PIL import Image


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


def libvirt_callback(ignore, err):
    return
registerErrorHandler(f=libvirt_callback, ctx=None)


class Kvirt(Kbase):
    def __init__(self, host='127.0.0.1', port=None, user='root', protocol='ssh', url=None, debug=False):
        if url is None:
            if host == '127.0.0.1' or host == 'localhost':
                url = "qemu:///system"
            elif port:
                url = "qemu+%s://%s@%s:%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, user, host, port)
            elif protocol == 'ssh':
                url = "qemu+%s://%s@%s/system?socket=/var/run/libvirt/libvirt-sock" % (protocol, user, host)
            else:
                url = "qemu:///system"
        try:
            self.conn = libvirtopen(url)
            self.debug = debug
        except Exception:
            self.conn = None
        self.host = host
        self.user = user
        self.port = port
        self.protocol = protocol
        if self.protocol == 'ssh' and port is None:
            self.port = '22'
        self.url = url

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

    def create(self, name, virttype='kvm', profile='kvirt', plan='kvirt', cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[]):
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s allready exists" % name}
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        conn = self.conn
        try:
            default_storagepool = conn.storagePoolLookupByName(default_pool)
        except:
            return {'result': 'failure', 'reason': "Pool %s not found" % default_pool}
        metadata = """<metadata>
        <kvirt:info xmlns:kvirt="kvirt">
        <kvirt:profile>%s</kvirt:profile>""" % profile
        if template:
            metadata = """%s
                        <kvirt:template>%s</kvirt:template>""" % (metadata, template)
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
        # sysinfo = "<smbios mode='sysinfo'/>"
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
                diskwwn = disk.get('wwn')
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
            if diskwwn is not None and diskbus == 'ide':
                diskwwn = '0x%016x' % diskwwn
                diskwwn = "<wwn>%s</wwn>" % diskwwn
            else:
                diskwwn = ''
            disksxml = """%s<disk type='file' device='disk'>
                    <driver name='qemu' type='%s'/>
                    <source file='%s'/>
                    %s
                    <target dev='%s' bus='%s'/>
                    %s
                    </disk>""" % (disksxml, diskformat, diskpath, backingxml, diskdev, diskbus, diskwwn)
        netxml = ''
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
                    metadata = """%s<kvirt:ip >%s</kvirt:ip>""" % (metadata, ip)
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
        metadata = """%s
                    <kvirt:plan>%s</kvirt:plan>
                    </kvirt:info>
                    </metadata>""" % (metadata, plan)
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
        if tunnel:
            listen = '127.0.0.1'
        else:
            listen = '0.0.0.0'
        displayxml = """<input type='tablet' bus='usb'/>
                        <input type='mouse' bus='ps2'/>
                        <graphics type='%s' port='-1' autoport='yes' listen='%s'>
                        <listen type='address' address='%s'/>
                        </graphics>
                        <memballoon model='virtio'/>""" % (display, listen, listen)
        if cpumodel == '':
            cpuxml = ""
        elif cpumodel == 'host-model':
            cpuxml = """<cpu mode='host-model'>
                        <model fallback='allow'/>"""
        else:
            cpuxml = """<cpu mode='custom' match='exact'>
                        <model fallback='allow'>%s</model>""" % cpumodel
        if nested and virttype == 'kvm':
            capabilities = self.conn.getCapabilities()
            if 'vmx' in capabilities:
                nestedfeature = 'vmx'
            else:
                nestedfeature = 'svm'
            cpuxml = """%s<feature policy='require' name='%s'/>""" % (cpuxml, nestedfeature)
        if cpuflags:
            for flag in cpuflags:
                if isinstance(flag, str):
                    if flag == 'vmx':
                        continue
                    cpuxml = """%s<feature policy='require' name='%s'/>""" % (cpuxml, flag)
                elif isinstance(flag, dict):
                    feature = flag.get('name')
                    enable = flag.get('enable')
                    if feature is None or enable is None or not isinstance(enable, bool):
                        continue
                    elif feature == 'vmx':
                        continue
                    elif enable:
                        cpuxml = """%s<feature policy='require' name='%s'/>""" % (cpuxml, feature)
                    else:
                        cpuxml = """%s<feature policy='disable' name='%s'/>""" % (cpuxml, feature)
        if cpuxml != '':
            cpuxml = "%s</cpu>" % cpuxml
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
                     </serial>""" % common.get_free_port()
        vmxml = """<domain type='%s'>
                  <name>%s</name>
                  %s
                  <memory unit='MiB'>%d</memory>
                  <vcpu>%d</vcpu>
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
                    %s
                    %s
                    %s
                    %s
                    %s
                  </devices>
                    %s
                    </domain>""" % (virttype, name, metadata, memory, numcpus, machine, disksxml, netxml, isoxml, displayxml, serialxml, cpuxml)
        # for pool in volsxml:
        #     storagepool = conn.storagePoolLookupByName(pool)
        #     storagepool.refresh(0)
        #     for volxml in volsxml[pool]:
        #         storagepool.createXML(volxml, 0)
        if self.debug:
            print(vmxml)
        conn.defineXML(vmxml)
        vm = conn.lookupByName(name)
        vm.setAutostart(0)
        for pool in volsxml:
            storagepool = conn.storagePoolLookupByName(pool)
            storagepool.refresh(0)
            for volxml in volsxml[pool]:
                storagepool.createXML(volxml, 0)
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain, reserveip=reserveip, files=files)
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
        if reservedns:
            self.reserve_dns(name, nets, domain)
        if reservehost:
            self.reserve_host(name, nets, domain)
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

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(base)
            vmxml = vm.XMLDesc(0)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % base}
        if listing:
            return vm.snapshotListNames()
        if revert and name not in vm.snapshotListNames():
            return {'result': 'failure', 'reason': "Snapshot %s doesn't exist" % name}
        if delete and name not in vm.snapshotListNames():
            return {'result': 'failure', 'reason': "Snapshot %s doesn't exist" % name}
        if delete:
            snap = vm.snapshotLookupByName(name)
            snap.delete()
            return {'result': 'success'}
        if not revert and name in vm.snapshotListNames():
            return {'result': 'failure', 'reason': "Snapshot %s allready exists" % name}
        if revert:
            snap = vm.snapshotLookupByName(name)
            vm.revertToSnapshot(snap)
            return {'result': 'success'}
        if vm.isActive() == 0:
            memoryxml = ''
        else:
            memoryxml = "<memory snapshot='internal'/>"
        snapxml = """<domainsnapshot>
          <name>%s</name>
          %s
          <disks>
            <disk name='vda' snapshot='internal'/>
            <disk name='hdc' snapshot='no'/>
          </disks>
          %s
          </domainsnapshot>""" % (name, memoryxml, vmxml)
        vm.snapshotCreateXML(snapxml)
        return {'result': 'success'}

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
                if netmask is None:
                    netmask = attributes.get('prefix')
                try:
                    ip = IPNetwork('%s/%s' % (firstip, netmask))
                    cidr = ip.cidr
                except:
                    cidr = "N/A"
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
            template, plan, profile = '', '', ''
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            name = vm.name()
            state = status[vm.isActive()]
            ips = []
            for element in root.getiterator('interface'):
                mac = element.find('mac').get('address')
                if vm.isActive():
                    if mac in leases:
                        ips.append(leases[mac])
                if ips:
                    ip = ips[-1]
                else:
                    ip = ''
            plan, profile, template, report = '', '', '', ''
            for element in root.getiterator('{kvirt}info'):
                e = element.find('{kvirt}plan')
                if e is not None:
                    plan = e.text
                e = element.find('{kvirt}profile')
                if e is not None:
                    profile = e.text
                e = element.find('{kvirt}template')
                if e is not None:
                    template = e.text
                e = element.find('{kvirt}report')
                if e is not None:
                    report = e.text
                e = element.find('{kvirt}ip')
                if e is not None:
                    ip = e.text
            vms.append([name, state, ip, template, plan, profile, report])
        return vms

    def console(self, name, tunnel=False):
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
                if attributes['listen'] == '127.0.0.1' or tunnel:
                    host = '127.0.0.1'
                else:
                    host = self.host
                protocol = attributes['type']
                port = attributes['port']
                localport = port
                if tunnel:
                    localport = common.get_free_port()
                    consolecommand = "ssh -f -p %s -L %s:127.0.0.1:%s %s@%s sleep 10" % (self.port, localport, port, self.user, self.host)
                    os.popen(consolecommand)
                url = "%s://%s:%s" % (protocol, host, localport)
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
                os.system('virsh -c %s console %s' % (self.url, name))
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
        starts = {0: 'no', 1: 'yes'}
        conn = self.conn
        for network in conn.listAllNetworks():
            for lease in network.DHCPLeases():
                dhcpip = lease['ipaddr']
                mac = lease['mac']
                leases[mac] = dhcpip
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            if self.debug:
                print(xml)
            root = ET.fromstring(xml)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        state = 'down'
        autostart = starts[vm.autostart()]
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
        print("autostart: %s" % autostart)
        plan, profile, template, ip = None, None, None, None
        for element in root.getiterator('{kvirt}info'):
            e = element.find('{kvirt}plan')
            if e is not None:
                plan = e.text
            e = element.find('{kvirt}profile')
            if e is not None:
                profile = e.text
            e = element.find('{kvirt}template')
            if e is not None:
                template = e.text
            e = element.find('{kvirt}report')
            e = element.find('{kvirt}ip')
            if e is not None:
                ip = e.text
        if template is not None:
            print("template: %s" % template)
        if plan is not None:
            print("plan: %s" % plan)
        if profile is not None:
            print("profile: %s" % profile)
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
        if ip is not None:
            print("fixed ip: %s" % ip)
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
        if vm.hasCurrentSnapshot():
            currentsnapshot = vm.snapshotCurrent().getName()
        else:
            currentsnapshot = ''
        for snapshot in vm.snapshotListNames():
            if snapshot == currentsnapshot:
                current = True
            else:
                current = False
            print("snapshot: %s current: %s" % (snapshot, current))
        return {'result': 'success'}

    def ip(self, name):
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
            return None
        for element in root.getiterator('{kvirt}info'):
            e = element.find('{kvirt}ip')
            if e is not None:
                return e.text
        nic = root.getiterator('interface')[0]
        mac = nic.find('mac').get('address')
        if vm.isActive() and mac in leases:
            return leases[mac]
        else:
            return None

    def volumes(self, iso=False):
        isos = []
        templates = []
        default_templates = [os.path.basename(t) for t in defaults.TEMPLATES.values()]
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
                elif volume.endswith('qcow2') or volume.endswith('qc2') or volume in default_templates:
                    templates.append("%s/%s" % (storagepath, volume))
        if iso:
            return sorted(isos, key=lambda s: s.lower())
        else:
            return sorted(templates, key=lambda s: s.lower())

    def delete(self, name, force=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            # common.pprint("vm %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.snapshotListNames():
            if not force:
                # print("vm %s has snapshots" % name)
                return {'result': 'failure', 'reason': "VM %s has snapshots" % name}
            else:
                for snapshot in vm.snapshotListNames():
                    print("Deleting snapshot %s" % snapshot)
                    snap = vm.snapshotLookupByName(snapshot)
                    snap.delete()
        ip = self.ip(name)
        status = {0: 'down', 1: 'up'}
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        disks = []
        for element in root.getiterator('disk'):
            source = element.find('source')
            if source is not None:
                imagefile = element.find('source').get('file')
                if imagefile.endswith("%s.iso" % name) or "%s_" % name in imagefile:
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
                    iphost = host.get('ip')
                    hostname = host.get('name')
                    if hostmac == mac:
                        hostentry = "<host mac='%s' name='%s' ip='%s'/>" % (mac, hostname, iphost)
                        network.update(2, 4, 0, hostentry, 1)
                for host in root.getiterator('host'):
                    iphost = host.get('ip')
                    hostname = host.find('hostname')
                    if hostname is not None and hostname.text == name:
                        hostentry = '<host ip="%s"><hostname>%s</hostname></host>' % (iphost, name)
                        network.update(2, 10, 0, hostentry, 1)
        if ip is not None:
            os.system("ssh-keygen -q -R %s >/dev/null 2>&1" % ip)
            # delete hosts entry
            found = False
            hostentry = "%s %s.* # KVIRT" % (ip, name)
            for line in open('/etc/hosts'):
                if re.findall(hostentry, line):
                    found = True
                    break
            if found:
                print("Deleting hosts entry. sudo password might be asked")
                os.system("sudo sed -i '/%s/d' /etc/hosts" % hostentry)
        return {'result': 'success'}

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
                source.set('service', str(common.get_free_port()))
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

    def reserve_dns(self, name, nets, domain):
        conn = self.conn
        net = nets[0]
        ip = None
        if isinstance(net, dict):
            ip = net.get('ip')
            network = net.get('name')
        else:
            network = net
        if ip is None:
            counter = 0
            while counter != 80:
                ip = self.ip(name)
                if ip is None:
                    time.sleep(5)
                    print("Waiting 5 seconds to grab ip and create DNS record...")
                    counter += 10
                else:
                    break
        if ip is None:
            print("Couldn't assign DNS")
            return
        network = conn.networkLookupByName(network)
        oldnetxml = network.XMLDesc()
        root = ET.fromstring(oldnetxml)
        dns = root.getiterator('dns')
        if not dns:
            base = root.getiterator('network')[0]
            dns = ET.Element("dns")
            base.append(dns)
            newxml = ET.tostring(root)
            conn.networkDefineXML(newxml)
        if domain is not None:
            dnsentry = '<host ip="%s"><hostname>%s</hostname><hostname>%s.%s</hostname></host>' % (ip, name, name, domain)
        else:
            dnsentry = '<host ip="%s"><hostname>%s</hostname></host>' % (ip, name)
        try:
            network.update(4, 10, 0, dnsentry, 1)
            return 0
        except:
            print("Entry allready found for %s" % name)
            return {'result': 'failure', 'reason': "Entry allready found found for %s" % name}

    def reserve_host(self, name, nets, domain):
        net = nets[0]
        ip = None
        if isinstance(net, dict):
            ip = net.get('ip')
            netname = net.get('name')
        else:
            netname = net
        if ip is None:
            counter = 0
            while counter != 80:
                ip = self.ip(name)
                if ip is None:
                    time.sleep(5)
                    print("Waiting 5 seconds to grab ip and create HOST record...")
                    counter += 10
                else:
                    break
        if ip is None:
            print("Couldn't assign Host")
            return
        hosts = "%s %s %s.%s" % (ip, name, name, netname)
        if domain is not None and domain != netname:
            hosts = "%s %s.%s" % (hosts, name, domain)
        hosts = '"%s # KVIRT"' % hosts
        oldentry = "%s %s.* # KVIRT" % (ip, name)
        for line in open('/etc/hosts'):
            if re.findall(oldentry, line):
                common.pprint("Old entry found.Leaving...", color='blue')
                return
        hostscmd = "sudo sh -c 'echo %s >>/etc/hosts'" % hosts
        print("Creating hosts entry. sudo password might be asked")
        os.popen(hostscmd)

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

    def update_metadata(self, name, metatype, metavalue):
        ET.register_namespace('kvirt', 'kvirt')
        conn = self.conn
        vm = conn.lookupByName(name)
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        if not vm:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.isActive() == 1:
            print("Machine up. Change will only appear upon next reboot")
        metadata = root.find('metadata')
        kroot, kmeta = None, None
        for element in root.getiterator('{kvirt}info'):
            kroot = element
            break
        for element in root.getiterator('{kvirt}%s' % metatype):
            kmeta = element
            break
        if metadata is None:
            metadata = ET.Element("metadata")
            kroot = ET.Element("kvirt:info")
            kroot.set("xmlns:kvirt", "kvirt")
            kmeta = ET.Element("kvirt:%s" % metatype)
            root.append(metadata)
            metadata.append(kroot)
            kroot.append(kmeta)
        elif kroot is None:
            kroot = ET.Element("kvirt:info")
            kroot.set("xmlns:kvirt", "kvirt")
            kmeta = ET.Element("kvirt:%s" % metatype)
            metadata.append(kroot)
            kroot.append(kmeta)
        elif kmeta is None:
            kmeta = ET.Element("kvirt:%s" % metatype)
            kroot.append(kmeta)
        kmeta.text = metavalue
        newxml = ET.tostring(root)
        conn.defineXML(newxml)
        return {'result': 'success'}

    def update_memory(self, name, memory):
        conn = self.conn
        memory = str(int(memory) * 1024)
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        memorynode = root.getiterator('memory')[0]
        memorynode.text = memory
        currentmemory = root.getiterator('currentMemory')[0]
        currentmemory.text = memory
        newxml = ET.tostring(root)
        conn.defineXML(newxml)
        return {'result': 'success'}

    def update_cpu(self, name, numcpus):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        cpunode = root.getiterator('vcpu')[0]
        cpunode.text = numcpus
        newxml = ET.tostring(root)
        conn.defineXML(newxml)
        return {'result': 'success'}

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

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        conn = self.conn
        diskformat = 'qcow2'
        diskbus = 'virtio'
        if size < 1:
            print("Incorrect size.Leaving...")
            return {'result': 'failure', 'reason': "Incorrect size"}
        if not thin:
            diskformat = 'raw'
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
        return {'result': 'success'}

    def delete_disk(self, name, diskname):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
                return {'result': 'success'}
        print("Disk %s not found in %s" % (diskname, name))
        return {'result': 'failure', 'reason': "Disk %s not found in %s" % (diskname, name)}

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
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if network not in networks:
            common.pprint("Network %s not found" % network, color='red')
            return {'result': 'failure', 'reason': "Network %s not found" % network}
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
        return {'result': 'success'}

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
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
        if self.debug:
            print(nicxml)
        vm.detachDevice(nicxml)
        vm = conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)
        return {'result': 'success'}

    def _ssh_credentials(self, name):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            print("VM %s not found" % name)
            return '', ''
        if vm.isActive() != 1:
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

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False):
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        if ip == '':
            return None
        else:
            sshcommand = "%s@%s" % (user, ip)
            if self.host not in ['localhost', '127.0.0.1'] and tunnel:
                sshcommand = "-o ProxyCommand='ssh -p %s -W %%h:%%p %s@%s' %s" % (self.port, self.user, self.host, sshcommand)
            if local is not None:
                sshcommand = "-L %s %s" % (local, sshcommand)
            if remote is not None:
                sshcommand = "-R %s %s" % (remote, sshcommand)
            if insecure:
                sshcommand = "ssh -o LogLevel=quiet -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' %s" % sshcommand
            else:
                sshcommand = "ssh %s" % sshcommand
            if self.debug:
                print(sshcommand)
            return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
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
        conn = self.conn
        for pool in conn.listStoragePools():
            if pool == name:
                print("Pool %s already there.Leaving..." % name)
                return
        if pooltype == 'dir':
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if not os.path.exists(poolpath):
                    try:
                        os.makedirs(poolpath)
                    except OSError:
                        print("Couldn't create directory %s.Leaving..." % poolpath)
                        return 1
            elif self.protocol == 'ssh':
                cmd1 = 'ssh -p %s %s@%s "test -d %s || mkdir %s"' % (self.port, self.user, self.host, poolpath, poolpath)
                cmd2 = 'ssh -t %s@%s "sudo chown %s %s"' % (self.user, self.host, user, poolpath)
                return1 = os.system(cmd1)
                if return1 > 0:
                    print("Couldn't create directory %s.Leaving..." % poolpath)
                    return
                return2 = os.system(cmd2)
                if return2 > 0:
                    print("Couldn't change permission of directory %s to qemu.Leaving..." % poolpath)
                    return
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
            return {'result': 'failure', 'reason': "Invalid pool type %s" % pooltype}
        pool = conn.storagePoolDefineXML(poolxml, 0)
        pool.setAutostart(True)
        if pooltype == 'logical':
            pool.build()
        pool.create()
        return {'result': 'success'}

    def add_image(self, image, pool, cmd=None):
        poolname = pool
        shortimage = os.path.basename(image).split('?')[0]
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
            wgetcmd = 'wget -O %s/%s %s' % (poolpath, shortimage, image)
        elif self.protocol == 'ssh':
            wgetcmd = 'ssh -p %s %s@%s "wget -O %s/%s %s"' % (self.port, self.user, self.host, poolpath, shortimage, image)
        os.system(wgetcmd)
        if cmd is not None and find_executable('virt-customize') is not None:
            if self.host == 'localhost' or self.host == '127.0.0.1':
                cmd = "virt-customize -a %s/%s %s" % (poolpath, shortimage, cmd)
            elif self.protocol == 'ssh':
                cmd = 'ssh -p %s %s@%s "virt-customize -a %s/%s %s"' % (self.port, self.user, self.host, poolpath, shortimage, cmd)
            os.system(cmd)
        pool.refresh()
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
            return {'result': 'failure', 'reason': "Network %s is being used by %s" % (name, machines)}
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
            return {'result': 'failure', 'reason': "Pool %s not found" % name}
        if full:
            for vol in pool.listAllVolumes():
                vol.delete(0)
        if pool.isActive():
            pool.destroy()
        pool.undefine()
        return {'result': 'success'}

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
            common.pprint("VM %s not found" % name, color='red')
            return networks
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

    def get_pool_path(self, pool):
        conn = self.conn
        pool = conn.storagePoolLookupByName(pool)
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        pooltype = root.getiterator('pool')[0].get('type')
        if pooltype == 'dir':
            poolpath = root.getiterator('path')[0].text
        else:
            poolpath = root.getiterator('device')[0].get('path')
        return poolpath

    def _writer(self, stream, data, buf):
        buf.write(data)

    def screenshot(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            print("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        stream = conn.newStream()
        if vm.isActive():
            vm.screenshot(stream, 0)
            buf = StringIO()
            stream.recvAll(self._writer, buf)
            stream.finish()
            buf.seek(0)
            image = Image.open(buf)
            image.save("/tmp/%s.png" % name)
        imagecmd = 'open'
        if find_executable('xdg-open') is not None:
            imagecmd = 'xdg-open'
        os.system("%s /tmp/%s.png" % (imagecmd, name))
