#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvm Provider class
"""

from distutils.spawn import find_executable
from kvirt import defaults
from kvirt import common
from netaddr import IPAddress, IPNetwork
from libvirt import open as libvirtopen, registerErrorHandler, VIR_DOMAIN_AFFECT_LIVE, VIR_DOMAIN_AFFECT_CONFIG
import json
import os
from subprocess import call
import re
import string
import time
import xml.etree.ElementTree as ET


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


class Kvirt(object):
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
        except Exception as e:
            common.pprint(e, color='red')
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
        if conn is not None:
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

    def create(self, name, virttype='kvm', profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None,
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=None):
        namespace = ''
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        conn = self.conn
        try:
            default_storagepool = conn.storagePoolLookupByName(default_pool)
        except:
            return {'result': 'failure', 'reason': "Pool %s not found" % default_pool}
        creationdate = time.strftime("%d-%m-%Y %H:%M", time.gmtime())
        metadata = """<metadata>
        <kvirt:info xmlns:kvirt="kvirt">
        <kvirt:creationdate>%s</kvirt:creationdate>
        <kvirt:profile>%s</kvirt:profile>""" % (creationdate, profile)
        if template:
            metadata = """%s
                        <kvirt:template>%s</kvirt:template>""" % (metadata, template)
        default_poolxml = default_storagepool.XMLDesc(0)
        root = ET.fromstring(default_poolxml)
        default_pooltype = list(root.getiterator('pool'))[0].get('type')
        default_poolpath = None
        product = list(root.getiterator('product'))
        if product:
            default_thinpool = list(root.getiterator('product'))[0].get('name')
        else:
            default_thinpool = None
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
        fixqcow2path, fixqcow2backing = None, None
        volsxml = {}
        for index, disk in enumerate(disks):
            if disk is None:
                disksize = default_disksize
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                diskpooltype = default_pooltype
                diskpoolpath = default_poolpath
                diskthinpool = default_thinpool
                diskwwn = None
                disktemplate = None
            elif isinstance(disk, int):
                disksize = disk
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                diskpooltype = default_pooltype
                diskpoolpath = default_poolpath
                diskthinpool = default_thinpool
                diskwwn = None
                disktemplate = None
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskthin = disk.get('thin', default_diskthin)
                diskinterface = disk.get('interface', default_diskinterface)
                diskpool = disk.get('pool', default_pool)
                diskwwn = disk.get('wwn')
                disktemplate = disk.get('template')
                try:
                    storagediskpool = conn.storagePoolLookupByName(diskpool)
                except:
                    return {'result': 'failure', 'reason': "Pool %s not found" % diskpool}
                diskpoolxml = storagediskpool.XMLDesc(0)
                root = ET.fromstring(diskpoolxml)
                diskpooltype = list(root.getiterator('pool'))[0].get('type')
                diskpoolpath = None
                for element in list(root.getiterator('path')):
                    diskpoolpath = element.text
                    break
                product = list(root.getiterator('product'))
                if product:
                    diskthinpool = list(root.getiterator('product'))[0].get('name')
                else:
                    diskthinpool = None
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
                disktemplate = template
            if disktemplate is not None:
                try:
                    if diskthinpool is not None:
                        matchingthintemplates = self.thintemplates(diskpoolpath, diskthinpool)
                        if disktemplate not in matchingthintemplates:
                            raise NameError('No Template found')
                    else:
                        default_storagepool.refresh(0)
                        if '/' in disktemplate:
                            backingvolume = volumespaths[disktemplate]['object']
                        else:
                            backingvolume = volumes[disktemplate]['object']
                        backingxml = backingvolume.XMLDesc(0)
                        root = ET.fromstring(backingxml)
                except:
                    shortname = [t for t in defaults.TEMPLATES if defaults.TEMPLATES[t] == disktemplate]
                    if shortname:
                        msg = "you don't have template %s. Use kcli download %s" % (disktemplate, shortname[0])
                    else:
                        msg = "you don't have template %s" % disktemplate
                    return {'result': 'failure', 'reason': msg}
                if diskthinpool is not None:
                    backing = None
                    backingxml = '<backingStore/>'
                else:
                    backing = backingvolume.path()
                    if '/dev' in backing:
                        backingxml = """<backingStore type='block' index='1'>
                                        <format type='raw'/>
                                        <source dev='%s'/>
                                        </backingStore>""" % backing
                    else:
                        backingxml = """<backingStore type='file' index='1'>
                                        <format type='qcow2'/>
                                        <source file='%s'/>
                                        </backingStore>""" % backing
            else:
                backing = None
                backingxml = '<backingStore/>'
            volxml = self._xmlvolume(path=diskpath, size=disksize, pooltype=diskpooltype, backing=backing,
                                     diskformat=diskformat)
            if index == 0 and template is not None and diskpooltype in ['logical', 'zfs']\
                    and diskpool is None and not backing.startswith('/dev'):
                fixqcow2path = diskpath
                fixqcow2backing = backing
            if diskpooltype == 'logical' and diskthinpool is not None:
                thinsource = template if index == 0 and template is not None else None
                self._createthinlvm(storagename, diskpoolpath, diskthinpool, backing=thinsource, size=disksize)
            elif diskpool in volsxml:
                volsxml[diskpool].append(volxml)
            else:
                volsxml[diskpool] = [volxml]
            if diskwwn is not None and diskbus == 'ide':
                diskwwn = '0x%016x' % diskwwn
                diskwwn = "<wwn>%s</wwn>" % diskwwn
            else:
                diskwwn = ''
            dtype = 'block' if '/dev' in diskpath else 'file'
            dsource = 'dev' if '/dev' in diskpath else 'file'
            if diskpooltype in ['logical', 'zfs'] and (backing is None or backing.startswith('/dev')):
                diskformat = 'raw'
            disksxml = """%s<disk type='%s' device='disk'>
                    <driver name='qemu' type='%s'/>
                    <source %s='%s'/>
                    %s
                    <target dev='%s' bus='%s'/>
                    %s
                    </disk>""" % (disksxml, dtype, diskformat, dsource, diskpath, backingxml, diskdev, diskbus,
                                  diskwwn)
        netxml = ''
        alias = []
        etcd = None
        for index, net in enumerate(nets):
            ovs = False
            macxml = ''
            nettype = 'virtio'
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
                if 'type' in nets[index]:
                    nettype = nets[index]['type']
                if index == 0 and ip is not None:
                    metadata = """%s<kvirt:ip >%s</kvirt:ip>""" % (metadata, ip)
                if reservedns and index == 0 and 'alias' in nets[index] and isinstance(nets[index]['alias'], list):
                    alias = nets[index]['alias']
                if 'etcd' in nets[index] and nets[index]['etcd']:
                    etcd = "eth%s" % index
                if 'ovs' in nets[index] and nets[index]['ovs']:
                    ovs = True
            if netname in bridges or ovs:
                sourcenet = 'bridge'
            elif netname in networks:
                sourcenet = 'network'
            else:
                return {'result': 'failure', 'reason': "Invalid network %s" % netname}
            ovsxml = "<virtualport type='openvswitch'/>" if ovs else ''
            netxml = """%s
                     <interface type='%s'>
                     %s
                     <source %s='%s'/>
                     %s
                     <model type='%s'/>
                     </interface>""" % (netxml, sourcenet, macxml, sourcenet, netname, ovsxml, nettype)
        metadata = """%s
                    <kvirt:plan>%s</kvirt:plan>
                    </kvirt:info>
                    </metadata>""" % (metadata, plan)
        qemuextraxml = ''
        isoxml = ''
        if iso is not None:
            try:
                if os.path.isabs(iso):
                    shortiso = os.path.basename(iso)
                else:
                    shortiso = iso
                isovolume = volumes[shortiso]['object']
                iso = isovolume.path()
            except:
                return {'result': 'failure', 'reason': "Invalid iso %s" % iso}
            isoxml = """<disk type='file' device='cdrom'>
                      <driver name='qemu' type='raw'/>
                      <source file='%s'/>
                      <target dev='hdc' bus='ide'/>
                      <readonly/>
                    </disk>""" % iso
        if cloudinit:
            if template is not None and (template.startswith('coreos') or template.startswith('rhcos')):
                namespace = "xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'"
                ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                               domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                               overrides=overrides, etcd=etcd)
                with open('/tmp/ignition', 'w') as ignitionfile:
                    ignitionfile.write(ignitiondata)
                if self.protocol == 'ssh':
                    ignitioncmd = 'scp -qP %s /tmp/ignition %s@%s:/tmp' % (self.port, self.user, self.host)
                    code = os.system(ignitioncmd)
                    if code != 0:
                        return {'result': 'failure', 'reason': "Unable to creation ignition data file in hypervisor"}
                qemuextraxml = """<qemu:commandline>
                                  <qemu:arg value='-fw_cfg' />
                                  <qemu:arg value='name=opt/com.coreos/config,file=/tmp/ignition' />
                                  </qemu:commandline>"""
            else:
                cloudinitiso = "%s/%s.ISO" % (default_poolpath, name)
                dtype = 'block' if '/dev' in diskpath else 'file'
                dsource = 'dev' if '/dev' in diskpath else 'file'
                isoxml = """%s<disk type='%s' device='cdrom'>
                        <driver name='qemu' type='raw'/>
                        <source %s='%s'/>
                        <target dev='hdd' bus='ide'/>
                        <readonly/>
                        </disk>""" % (isoxml, dtype, dsource, cloudinitiso)
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
        if cpumodel == 'host-model':
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
        vmxml = """<domain type='%s' %s>
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
                    %s
                    </domain>""" % (virttype, namespace, name, metadata, memory, numcpus, machine, disksxml, netxml,
                                    isoxml, displayxml, serialxml, cpuxml, qemuextraxml)
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
        if fixqcow2path is not None and fixqcow2backing is not None:
            self._fixqcow2(fixqcow2path, fixqcow2backing)
        if cloudinit:
            if template is not None and not template.startswith('coreos') and not template.startswith('rhcos'):
                common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain,
                                 reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides)
                self._uploadimage(name, pool=default_storagepool)
        if reserveip:
            xml = vm.XMLDesc(0)
            vmxml = ET.fromstring(xml)
            macs = []
            for element in list(vmxml.getiterator('interface')):
                mac = element.find('mac').get('address')
                macs.append(mac)
            self._reserve_ip(name, nets, macs)
        if start:
            vm.create()
        if reservedns:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias)
        if reservehost:
            self.reserve_host(name, nets, domain)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if status[vm.isActive()] == "up":
            return {'result': 'success'}
        else:
            vm.create()
            return {'result': 'success'}

    def stop(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if status[vm.isActive()] == "down":
            return {'result': 'success'}
        else:
            vm.destroy()
            return {'result': 'success'}

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
            return {'result': 'failure', 'reason': "Snapshot %s already exists" % name}
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
          </disks>
          %s
          </domainsnapshot>""" % (name, memoryxml, vmxml)
        # <disk name='hdc' snapshot='no'/>
        vm.snapshotCreateXML(snapxml)
        return {'result': 'success'}

    def restart(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if status[vm.isActive()] == "down":
            return {'result': 'success'}
        else:
            vm.reboot()
            return {'result': 'success'}

    def report(self):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        hostname = conn.getHostname()
        cpus = conn.getCPUMap()[0]
        totalmemory = conn.getInfo()[1]
        print(("Host:%s Cpu:%s\n" % (hostname, cpus)))
        totalvms = 0
        usedmemory = 0
        for vm in conn.listAllDomains(0):
            if status[vm.isActive()] == "down":
                continue
            totalvms += 1
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            memory = list(root.getiterator('memory'))[0]
            unit = memory.attrib['unit']
            memory = memory.text
            if unit == 'KiB':
                memory = float(memory) / 1024
                memory = int(memory)
            usedmemory += memory
        print(("Vms Running : %s\n" % (totalvms)))
        print(("Memory Used : %sMB of %sMB\n" % (usedmemory, totalmemory)))
        for pool in conn.listStoragePools():
            poolname = pool
            pool = conn.storagePoolLookupByName(pool)
            poolxml = pool.XMLDesc(0)
            root = ET.fromstring(poolxml)
            pooltype = list(root.getiterator('pool'))[0].get('type')
            if pooltype in ['dir', 'zfs']:
                poolpath = list(root.getiterator('path'))[0].text
            else:
                poolpath = list(root.getiterator('device'))[0].get('path')
            s = pool.info()
            used = "%.2f" % (float(s[2]) / 1024 / 1024 / 1024)
            available = "%.2f" % (float(s[3]) / 1024 / 1024 / 1024)
            # Type,Status, Total space in Gb, Available space in Gb
            used = float(used)
            available = float(available)
            print(("Storage:%s Type:%s Path:%s Used space:%sGB Available space:%sGB" % (poolname, pooltype, poolpath,
                                                                                        used, available)))
        print()
        for interface in conn.listAllInterfaces():
            interfacename = interface.name()
            if interfacename == 'lo':
                continue
            print(("Network:%s Type:bridged" % (interfacename)))
        for network in conn.listAllNetworks():
            networkname = network.name()
            netxml = network.XMLDesc(0)
            cidr = 'N/A'
            root = ET.fromstring(netxml)
            ip = list(root.getiterator('ip'))
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
            dhcp = list(root.getiterator('dhcp'))
            if dhcp:
                dhcp = True
            else:
                dhcp = False
            print(("Network:%s Type:routed Cidr:%s Dhcp:%s" % (networkname, cidr, dhcp)))

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
            for element in list(root.getiterator('interface')):
                mac = element.find('mac').get('address')
                if vm.isActive():
                    if mac in leases:
                        ips.append(leases[mac])
                if ips:
                    ip = ips[0]
                else:
                    ip = ''
            plan, profile, template, report = '', '', '', ''
            for element in list(root.getiterator('{kvirt}info')):
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
        return sorted(vms)

    def console(self, name, tunnel=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if not vm.isActive():
            print("VM down")
            return
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            for element in list(root.getiterator('graphics')):
                attributes = element.attrib
                if attributes['listen'] == '127.0.0.1' or tunnel:
                    host = '127.0.0.1'
                else:
                    host = self.host
                protocol = attributes['type']
                port = attributes['port']
                localport = port
                consolecommand = ''
                if tunnel:
                    localport = common.get_free_port()
                    consolecommand += "ssh -o LogLevel=QUIET -f -p %s -L %s:127.0.0.1:%s %s@%s sleep 10" % (self.port,
                                                                                                            localport,
                                                                                                            port,
                                                                                                            self.user,
                                                                                                            self.host)
                    if self.debug:
                        print(consolecommand)
                    # os.system(consolecommand)
                url = "%s://%s:%s" % (protocol, host, localport)
                if self.debug:
                    print(url)
                consolecommand += "; remote-viewer %s &" % url
                # os.popen("remote-viewer %s &" % url)
                os.popen(consolecommand)

    def serialconsole(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if not vm.isActive():
            print("VM down")
            return
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            serial = list(root.getiterator('serial'))
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
                            serialcommand = "ssh -o LogLevel=QUIET -p %s %s@%s nc 127.0.0.1 %s" % (self.port, self.user,
                                                                                                   self.host,
                                                                                                   serialport)
                        os.system(serialcommand)

    def info(self, name, output='plain', fields=None, values=False):
        if fields is not None:
            fields = fields.split(',')
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
        status = 'down'
        autostart = starts[vm.autostart()]
        memory = list(root.getiterator('memory'))[0]
        unit = memory.attrib['unit']
        memory = memory.text
        if unit == 'KiB':
            memory = float(memory) / 1024
            memory = int(memory)
        numcpus = list(root.getiterator('vcpu'))[0]
        numcpus = numcpus.text
        description = list(root.getiterator('description'))
        if description:
            description = description[0].text
        else:
            description = ''
        if vm.isActive():
            status = 'up'
        yamlinfo = {'name': name, 'autostart': autostart, 'nets': [], 'disks': [], 'snapshots': [], 'status': status}
        plan, profile, template, ip, creationdate = None, None, None, None, None
        for element in list(root.getiterator('{kvirt}info')):
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
            e = element.find('{kvirt}creationdate')
            if e is not None:
                creationdate = e.text
        if template is not None:
            yamlinfo['template'] = template
        if plan is not None:
            yamlinfo['plan'] = plan
        if profile is not None:
            yamlinfo['profile'] = profile
        if creationdate is not None:
            yamlinfo['creationdate'] = creationdate
        yamlinfo['cpus'] = numcpus
        yamlinfo['memory'] = memory
        nicnumber = 0
        for element in list(root.getiterator('interface')):
            networktype = element.get('type')
            device = "eth%s" % nicnumber
            mac = element.find('mac').get('address')
            if networktype == 'bridge':
                network = element.find('source').get('bridge')
                network_type = 'bridge'
            else:
                network = element.find('source').get('network')
                network_type = 'routed'
            yamlinfo['nets'].append({'device': device, 'mac': mac, 'net': network, 'type': network_type})
            if vm.isActive():
                if mac in leases:
                    yamlinfo['ip'] = leases[mac]
            nicnumber = nicnumber + 1
        if ip is not None:
            yamlinfo['ip'] = ip
        for element in list(root.getiterator('disk')):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            device = element.find('target').get('dev')
            diskformat = 'file'
            drivertype = element.find('driver').get('type')
            # path = element.find('source').get('file')
            imagefiles = [element.find('source').get('file'), element.find('source').get('dev')]
            path = next(item for item in imagefiles if item is not None)
            try:
                volume = conn.storageVolLookupByPath(path)
                disksize = int(float(volume.info()[1]) / 1024 / 1024 / 1024)
            except:
                disksize = 'N/A'
            yamlinfo['disks'].append({'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype,
                                      'path': path})
        if vm.hasCurrentSnapshot():
            currentsnapshot = vm.snapshotCurrent().getName()
        else:
            currentsnapshot = ''
        for snapshot in vm.snapshotListNames():
            if snapshot == currentsnapshot:
                current = True
            else:
                current = False
            yamlinfo['snapshots'].append({'snapshot': snapshot, current: current})
        common.print_info(yamlinfo, output=output, fields=fields, values=values)
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
        for element in list(root.getiterator('{kvirt}info')):
            e = element.find('{kvirt}ip')
            if e is not None:
                return e.text
        nic = list(root.getiterator('interface'))[0]
        mac = nic.find('mac').get('address')
        if vm.isActive() and mac in leases:
            return leases[mac]
        else:
            return None

    def volumes(self, iso=False):
        isos = []
        templates = []
        default_templates = [os.path.basename(t).replace('.bz2', '') for t in list(defaults.TEMPLATES.values())
                             if t is not None and 'product-software' not in t]
        conn = self.conn
        for poolname in conn.listStoragePools():
            pool = conn.storagePoolLookupByName(poolname)
            pool.refresh(0)
            poolxml = pool.XMLDesc(0)
            root = ET.fromstring(poolxml)
            for element in list(root.getiterator('path')):
                poolpath = element.text
                break
            product = list(root.getiterator('product'))
            if product:
                thinpool = list(root.getiterator('product'))[0].get('name')
                matchingtemplates = ["%s/%s" % (poolpath, volume) for volume in self.thintemplates(poolpath, thinpool)
                                     if volume.endswith('qcow2') or volume.endswith('qc2') or
                                     volume in default_templates]
                if matchingtemplates:
                    templates.extend(matchingtemplates)
            for volume in pool.listVolumes():
                if volume.endswith('iso'):
                    isos.append("%s/%s" % (poolpath, volume))
                elif volume.endswith('qcow2') or volume.endswith('qc2') or volume in default_templates:
                    templates.append("%s/%s" % (poolpath, volume))
        if iso:
            return sorted(isos, key=lambda s: s.lower())
        else:
            return sorted(templates, key=lambda s: s.lower())

    def delete(self, name, snapshots=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.snapshotListNames():
            if not snapshots:
                return {'result': 'failure', 'reason': "VM %s has snapshots" % name}
            else:
                for snapshot in vm.snapshotListNames():
                    print(("Deleting snapshot %s" % snapshot))
                    snap = vm.snapshotLookupByName(snapshot)
                    snap.delete()
        ip = self.ip(name)
        status = {0: 'down', 1: 'up'}
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        disks = []
        for element in list(root.getiterator('disk')):
            source = element.find('source')
            if source is not None:
                # imagefile = element.find('source').get('file')
                imagefiles = [element.find('source').get('file'), element.find('source').get('dev')]
                imagefile = next(item for item in imagefiles if item is not None)
                if imagefile.endswith('.iso'):
                    continue
                elif imagefile.endswith("%s.ISO" % name) or "%s_" % name in imagefile or "%s.img" % name in imagefile:
                    disks.append(imagefile)
                else:
                    continue
        if status[vm.isActive()] != "down":
            vm.destroy()
        vm.undefine()
        founddisks = []
        thinpools = []
        for storage in conn.listStoragePools():
            deleted = False
            storage = conn.storagePoolLookupByName(storage)
            storage.refresh(0)
            poolxml = storage.XMLDesc(0)
            root = ET.fromstring(poolxml)
            for element in list(root.getiterator('path')):
                poolpath = element.text
                break
            product = list(root.getiterator('product'))
            if product:
                thinpools.append(poolpath)
            for stor in storage.listVolumes():
                for disk in disks:
                    if stor in disk:
                        try:
                            volume = storage.storageVolLookupByName(stor)
                        except:
                            continue
                        volume.delete(0)
                        deleted = True
                        founddisks.append(disk)
            if deleted:
                storage.refresh(0)
        remainingdisks = list(set(disks) - set(founddisks))
        for p in thinpools:
            for disk in remainingdisks:
                if disk.startswith(p):
                    self._deletelvm(disk)
        for element in list(root.getiterator('interface')):
            mac = element.find('mac').get('address')
            networktype = element.get('type')
            if networktype != 'bridge':
                network = element.find('source').get('network')
                network = conn.networkLookupByName(network)
                netxml = network.XMLDesc(0)
                root = ET.fromstring(netxml)
                for host in list(root.getiterator('host')):
                    hostmac = host.get('mac')
                    iphost = host.get('ip')
                    hostname = host.get('name')
                    if hostmac == mac:
                        hostentry = "<host mac='%s' name='%s' ip='%s'/>" % (mac, hostname, iphost)
                        network.update(2, 4, 0, hostentry, 1)
                for host in list(root.getiterator('host')):
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
                call("sudo sed -i '/%s/d' /etc/hosts" % hostentry, shell=True)
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
        disktype = 'file' if pooltype == 'file' else 'block'
        size = int(size) * MB
        if int(size) == 0:
            size = 512 * 1024
        name = os.path.basename(path)
        if pooltype == 'zfs':
            volume = """<volume type='block'>
                        <name>%s</name>
                        <key>%s/%s</key>
                        <source>
                        </source>
                        <capacity unit='bytes'>%d</capacity>
                        <target>
                        <path>/%s/%s</path>
                        </target>
                        </volume>""" % (name, path, name, size, path, name)
            return volume
        if backing is not None and pooltype in ['logical', 'zfs'] and backing.startswith('/dev'):
            diskformat = 'qcow2'
        if backing is not None and pooltype in ['logical', 'zfs'] and not backing.startswith('/dev'):
            backingstore = "<backingStore/>"
        elif backing is not None:
            backingstore = """
<backingStore>
<path>%s</path>
<format type='%s'/>
</backingStore>""" % (backing, diskformat)
        else:
            backingstore = "<backingStore/>"
        volume = """
<volume type='%s'>
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
</volume>""" % (disktype, name, size, path, diskformat, backingstore)
        return volume

    def clone(self, old, new, full=False, start=False):
        conn = self.conn
        oldvm = conn.lookupByName(old)
        oldxml = oldvm.XMLDesc(0)
        tree = ET.fromstring(oldxml)
        uuid = list(tree.getiterator('uuid'))[0]
        tree.remove(uuid)
        for vmname in list(tree.getiterator('name')):
            vmname.text = new
        firstdisk = True
        for disk in list(tree.getiterator('disk')):
            if firstdisk or full:
                source = disk.find('source')
                oldpath = source.get('file')
                oldvolume = self.conn.storageVolLookupByPath(oldpath)
                pool = oldvolume.storagePoolLookupByVolume()
                oldinfo = oldvolume.info()
                oldvolumesize = (float(oldinfo[1]) / 1024 / 1024 / 1024)
                oldvolumexml = oldvolume.XMLDesc(0)
                backing = None
                voltree = ET.fromstring(oldvolumexml)
                for b in list(voltree.getiterator('backingStore')):
                    backingstoresource = b.find('path')
                    if backingstoresource is not None:
                        backing = backingstoresource.text
                newpath = oldpath.replace(old, new)
                source.set('file', newpath)
                newvolumexml = self._xmlvolume(newpath, oldvolumesize, backing=backing)
                pool.createXMLFrom(newvolumexml, oldvolume, 0)
                firstdisk = False
            else:
                devices = list(tree.getiterator('devices'))[0]
                devices.remove(disk)
        for interface in list(tree.getiterator('interface')):
            mac = interface.find('mac')
            interface.remove(mac)
        if self.host not in ['127.0.0.1', 'localhost']:
            for serial in list(tree.getiterator('serial')):
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
            ipentry = list(root.getiterator('ip'))
            if ipentry:
                attributes = ipentry[0].attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                netip = IPNetwork('%s/%s' % (firstip, netmask))
            dhcp = list(root.getiterator('dhcp'))
            if not dhcp:
                continue
            if not IPAddress(ip) in netip:
                continue
            network.update(4, 4, 0, '<host mac="%s" name="%s" ip="%s" />' % (mac, name, ip), 1)
            # network.update(4, 4, 0, '<host mac="%s" name="%s" ip="%s" />' % (mac, name, ip), 2)

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False):
        conn = self.conn
        net = nets[0]
        if isinstance(net, dict):
            network = net.get('name')
        else:
            network = net
        if ip is None:
            if isinstance(net, dict):
                ip = net.get('ip')
            if ip is None:
                counter = 0
                while counter != 100:
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
        dns = list(root.getiterator('dns'))
        if not dns:
            base = list(root.getiterator('network'))[0]
            dns = ET.Element("dns")
            base.append(dns)
            newxml = ET.tostring(root)
            conn.networkDefineXML(newxml.decode("utf-8"))
        dnsentry = '<host ip="%s"><hostname>%s</hostname>' % (ip, name)
        if domain is not None:
            dnsentry = '%s<hostname>%s.%s</hostname>' % (dnsentry, name, domain)
        for entry in alias:
            dnsentry = "%s<hostname>%s</hostname>" % (dnsentry, entry)
        dnsentry = "%s</host>" % dnsentry
        if force:
            for host in list(root.getiterator('host')):
                iphost = host.get('ip')
                if iphost == ip:
                    existing = []
                    for hostname in list(host.getiterator('hostname')):
                        existing.append(hostname.text)
                    if name in existing:
                        print(("Entry already found for %s" % name))
                        return {'result': 'failure', 'reason': "Entry already found found for %s" % name}
                    oldentry = '<host ip="%s"></host>' % (iphost)
                    print(("Removing old dns entry for ip %s" % ip))
                    network.update(2, 10, 0, oldentry, 1)
        try:
            network.update(4, 10, 0, dnsentry, 1)
            # network.update(4, 10, 0, dnsentry, 2)
            return 0
        except:
            print(("Entry already found for %s" % name))
            return {'result': 'failure', 'reason': "Entry already found found for %s" % name}

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
        call(hostscmd, shell=True)

    def handler(self, stream, data, file_):
        return file_.read(data)

    def _uploadimage(self, name, pool='default', pooltype='file', origin='/tmp', suffix='.ISO', size=0):
        name = "%s%s" % (name, suffix)
        conn = self.conn
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in list(root.getiterator('path')):
            poolpath = element.text
            break
        imagepath = "%s/%s" % (poolpath, name)
        imagexml = self._xmlvolume(path=imagepath, size=size, diskformat='raw', pooltype=pooltype)
        pool.createXML(imagexml, 0)
        imagevolume = conn.storageVolLookupByPath(imagepath)
        stream = conn.newStream(0)
        imagevolume.upload(stream, 0, 0)
        with open("%s/%s" % (origin, name), 'rb') as ori:
            stream.sendAll(self.handler, ori)
            stream.finish()

    def update_metadata(self, name, metatype, metavalue):
        ET.register_namespace('kvirt', 'kvirt')
        conn = self.conn
        vm = conn.lookupByName(name)
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        if not vm:
            print(("VM %s not found" % name))
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.isActive() == 1:
            print("Machine up. Change will only appear upon next reboot")
        metadata = root.find('metadata')
        kroot, kmeta = None, None
        for element in list(root.getiterator('{kvirt}info')):
            kroot = element
            break
        for element in list(root.getiterator('{kvirt}%s' % metatype)):
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

    def update_information(self, name, information):
        conn = self.conn
        vm = conn.lookupByName(name)
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        description = root.find('description')
        if not description:
            description = ET.Element("description")
            description.text = information
            root.append(description)
        else:
            description.text = information
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
            print(("VM %s not found" % name))
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        memorynode = list(root.getiterator('memory'))[0]
        memorynode.text = memory
        currentmemory = list(root.getiterator('currentMemory'))[0]
        currentmemory.text = memory
        newxml = ET.tostring(root)
        conn.defineXML(newxml.decode("utf-8"))
        return {'result': 'success'}

    def update_iso(self, name, iso):
        isos = self.volumes(iso=True)
        isofound = False
        for i in isos:
            if i == iso:
                isofound = True
                break
            elif i.endswith(iso):
                iso = i
                isofound = True
                break
        if not isofound:
            print(("Iso %s not found.Leaving..." % iso))
            return {'result': 'failure', 'reason': "Iso %s not found" % iso}
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print(("VM %s not found" % name))
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for element in list(root.getiterator('disk')):
            disktype = element.get('device')
            if disktype != 'cdrom':
                continue
            source = element.find('source')
            source.set('file', iso)
            break
        newxml = ET.tostring(root)
        conn.defineXML(newxml)
        return {'result': 'success'}

    def remove_cloudinit(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print(("VM %s not found" % name))
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for element in list(root.getiterator('disk')):
            disktype = element.get('device')
            if disktype == 'cdrom':
                source = element.find('source')
                path = source.get('file')
                if source is None:
                    break
                volume = conn.storageVolLookupByPath(path)
                volume.delete(0)
                element.remove(source)
        newxml = ET.tostring(root)
        conn.defineXML(newxml)

    def update_start(self, name, start=True):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            print(("VM %s not found" % name))
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
            pooltype = list(poolroot.getiterator('pool'))[0].get('type')
            for element in list(poolroot.getiterator('path')):
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
            if template not in volumes and template not in list(volumes.values()):
                print(("Invalid template %s.Leaving..." % template))
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

    def add_disk(self, name, size=1, pool=None, thin=True, template=None, shareable=False, existing=None):
        conn = self.conn
        diskformat = 'qcow2'
        diskbus = 'virtio'
        if size < 1:
            common.pprint("Incorrect size.Leaving...", color='red')
            return {'result': 'failure', 'reason': "Incorrect size"}
        if not thin:
            diskformat = 'raw'
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print(("VM %s not found" % name))
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        currentdisk = 0
        for element in list(root.getiterator('disk')):
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
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat,
                                shareable=shareable)
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
            print(("VM %s not found" % name))
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for element in list(root.getiterator('disk')):
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
        print(("Disk %s not found in %s" % (diskname, name)))
        return {'result': 'failure', 'reason': "Disk %s not found in %s" % (diskname, name)}

    def list_disks(self):
        volumes = {}
        for p in self.conn.listStoragePools():
            poo = self.conn.storagePoolLookupByName(p)
            for volume in poo.listAllVolumes():
                if volume.name().endswith('.ISO'):
                    continue
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
        if vm.isActive() == 1:
            # vm.attachDevice(nicxml)
            vm.attachDeviceFlags(nicxml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
        else:
            vm.attachDeviceFlags(nicxml, VIR_DOMAIN_AFFECT_CONFIG)
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
        for element in list(root.getiterator('interface')):
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
        # vm.detachDevice(nicxml)
        if vm.isActive() == 1:
            vm.detachDeviceFlags(nicxml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
        else:
            vm.detachDeviceFlags(nicxml, VIR_DOMAIN_AFFECT_CONFIG)
        vm = conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)
        return {'result': 'success'}

    def _ssh_credentials(self, name):
        user = 'root'
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            print(("VM %s not found" % name))
            return '', ''
        if vm.isActive() != 1:
            print("Machine down. Cannot ssh...")
            return '', ''
        vm = [v for v in self.list() if v[0] == name][0]
        template = vm[3]
        if template != '':
            user = common.get_user(template)
        ip = vm[2]
        if ip == '':
            print("No ip found. Cannot ssh...")
        return user, ip

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False,
            D=None):
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        if ip == '':
            return None
        else:
            sshcommand = "-A %s@%s" % (user, ip)
            if X:
                sshcommand = "-X %s" % (sshcommand)
            if Y:
                sshcommand = "-Y %s" % (sshcommand)
            if D is not None:
                sshcommand = "-D %s %s" % (D, sshcommand)
            if cmd:
                sshcommand = "%s %s" % (sshcommand, cmd)
            if self.host not in ['localhost', '127.0.0.1'] and tunnel:
                sshcommand = "-o ProxyCommand='ssh -qp %s -W %%h:%%p %s@%s' %s" % (self.port, self.user, self.host,
                                                                                   sshcommand)
            if local is not None:
                sshcommand = "-L %s %s" % (local, sshcommand)
            if remote is not None:
                sshcommand = "-R %s %s" % (remote, sshcommand)
            if insecure:
                sshcommand = "ssh -o LogLevel=quiet -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' %s"\
                    % sshcommand
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
                arguments = "-o ProxyCommand='ssh -qp %s -W %%h:%%p %s@%s'" % (self.port, self.user, self.host)
            else:
                arguments = ''
            scpcommand = 'scp'
            if recursive:
                scpcommand = "%s -r" % scpcommand
            if download:
                scpcommand = "%s %s %s@%s:%s %s" % (scpcommand, arguments, user, ip, source, destination)
            else:
                scpcommand = "%s %s %s %s@%s:%s" % (scpcommand, arguments, source, user, ip, destination)
            if self.debug:
                print(scpcommand)
            return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        conn = self.conn
        for pool in conn.listStoragePools():
            if pool == name:
                print(("Pool %s already there.Leaving..." % name))
                return
        if pooltype == 'dir':
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if not os.path.exists(poolpath):
                    try:
                        os.makedirs(poolpath)
                    except OSError:
                        print(("Couldn't create directory %s.Leaving..." % poolpath))
                        return 1
            elif self.protocol == 'ssh':
                cmd1 = 'ssh -p %s %s@%s "test -d %s || mkdir %s"' % (self.port, self.user, self.host, poolpath,
                                                                     poolpath)
                cmd2 = 'ssh -p %s -t %s@%s "sudo chown %s %s"' % (self.port, self.user, self.host, user, poolpath)
                return1 = os.system(cmd1)
                if return1 > 0:
                    print(("Couldn't create directory %s.Leaving..." % poolpath))
                    return
                return2 = os.system(cmd2)
                if return2 > 0:
                    print(("Couldn't change permission of directory %s to qemu" % poolpath))
            else:
                print(("Make sur %s directory exists on hypervisor" % name))
            poolxml = """<pool type='dir'>
                         <name>%s</name>
                         <source>
                         </source>
                         <target>
                         <path>%s</path>
                         </target>
                         </pool>""" % (name, poolpath)
        elif pooltype == 'lvm':
            thinpoolxml = "<product name='%s'/>" % thinpool if thinpool is not None else ''
            poolxml = """<pool type='logical'>
                         <name>%s</name>
                         <source>
                         <name>%s</name>
                         <format type='lvm2'/>
                         %s
                         </source>
                         <target>
                         <path>/dev/%s</path>
                         </target>
                         </pool>""" % (name, poolpath, thinpoolxml, poolpath)
        elif pooltype == 'zfs':
            poolxml = """<pool type='zfs'>
                         <name>%s</name>
                         <source>
                         <name>%s</name>
                         </source>
                         </pool>""" % (name, poolpath)
        else:
            print(("Invalid pool type %s.Leaving..." % pooltype))
            return {'result': 'failure', 'reason': "Invalid pool type %s" % pooltype}
        pool = conn.storagePoolDefineXML(poolxml, 0)
        pool.setAutostart(True)
        # if pooltype == 'lvm':
        #    pool.build()
        pool.create()
        return {'result': 'success'}

    def add_image(self, image, pool, cmd=None, name=None, size=1):
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
        pooltype = list(root.getiterator('pool'))[0].get('type')
        poolpath = list(root.getiterator('path'))[0].text
        downloadpath = poolpath if pooltype == 'dir' else '/tmp'
        if shortimage in volumes:
            return {'result': 'failure', 'reason': "Template %s already exists in pool %s" % (shortimage, poolname)}
        if self.host == 'localhost' or self.host == '127.0.0.1':
            downloadcmd = 'curl -Lo %s/%s -f %s' % (downloadpath, shortimage, image)
        elif self.protocol == 'ssh':
            downloadcmd = 'ssh -p %s %s@%s "curl -Lo %s/%s -f %s"' % (self.port, self.user, self.host, downloadpath,
                                                                      shortimage, image)
        code = os.system(downloadcmd)
        if code != 0:
            return {'result': 'failure', 'reason': "Unable to download indicated template"}
        if shortimage.endswith('bz2'):
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if find_executable('bunzip2') is not None:
                    cmd = "bunzip2 %s/%s" % (poolpath, shortimage)
                    os.system(cmd)
            elif self.protocol == 'ssh':
                cmd = 'ssh -p %s %s@%s "bunzip2 %s/%s"' % (self.port, self.user, self.host, poolpath, shortimage)
                os.system(cmd)
            shortimage = shortimage.replace('.bz2', '')
        if shortimage.endswith('gz'):
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if find_executable('gunzip') is not None:
                    cmd = "gunzip %s/%s" % (poolpath, shortimage)
                    os.system(cmd)
            elif self.protocol == 'ssh':
                cmd = 'ssh -p %s %s@%s "bunzip2 %s/%s"' % (self.port, self.user, self.host, poolpath, shortimage)
                os.system(cmd)
            shortimage = shortimage.replace('.gz', '')
        if shortimage.endswith('xz'):
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if find_executable('unxz') is not None:
                    cmd = "unxz %s/%s" % (poolpath, shortimage)
                    os.system(cmd)
            elif self.protocol == 'ssh':
                cmd = 'ssh -p %s %s@%s "unxz %s/%s"' % (self.port, self.user, self.host, poolpath, shortimage)
                os.system(cmd)
            shortimage = shortimage.replace('.xz', '')
        if cmd is not None:
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if find_executable('virt-customize') is not None:
                    cmd = "virt-customize -a %s/%s --run-command '%s'" % (poolpath, shortimage, cmd)
                    os.system(cmd)
            elif self.protocol == 'ssh':
                cmd = 'ssh -p %s %s@%s "virt-customize -a %s/%s --run-command \'%s\'"' % (self.port, self.user,
                                                                                          self.host, poolpath,
                                                                                          shortimage, cmd)
                os.system(cmd)
        if pooltype in ['logical', 'zfs']:
            product = list(root.getiterator('product'))
            if product:
                thinpool = list(root.getiterator('product'))[0].get('name')
            else:
                thinpool = None
            self.add_image_to_deadpool(poolname, pooltype, poolpath, shortimage, thinpool)
            return {'result': 'success'}
        pool.refresh()
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None, vlan=None):
        conn = self.conn
        networks = self.list_networks()
        if cidr is None:
            return {'result': 'failure', 'reason': "Missing Cidr"}
        cidrs = [network['cidr'] for network in list(networks.values())]
        if name in networks:
            return {'result': 'failure', 'reason': "Network %s already exists" % name}
        try:
            range = IPNetwork(cidr)
        except:
            return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
        if IPNetwork(cidr) in cidrs:
            return {'result': 'failure', 'reason': "Cidr %s already exists" % cidr}
        netmask = IPNetwork(cidr).netmask
        gateway = str(range[1])
        if dhcp:
            start = str(range[2])
            end = str(range[-2])
            dhcpxml = """<dhcp>
                    <range start='%s' end='%s'/>""" % (start, end)
            if pxe is not None:
                dhcpxml = """%s
                          <bootp file='pxelinux.0' server='%s'/>""" % (dhcpxml, pxe)
            dhcpxml = "%s</dhcp>" % dhcpxml
        else:
            dhcpxml = ''
        if nat:
            natxml = "<forward mode='nat'><nat><port start='1024' end='65535'/></nat></forward>"
        else:
            natxml = ''
        if domain is not None:
            domainxml = "<domain name='%s'/>" % domain
        else:
            domainxml = "<domain name='%s'/>" % name
        metadata = """<metadata>
        <kvirt:info xmlns:kvirt="kvirt">
        <kvirt:plan>%s</kvirt:plan>
        </kvirt:info>
        </metadata>""" % (plan)
        networkxml = """<network><name>%s</name>
                    %s
                    %s
                    %s
                    <ip address='%s' netmask='%s'>
                    %s
                    </ip>
                    </network>""" % (name, metadata, natxml, domainxml, gateway, netmask, dhcpxml)
        new_net = conn.networkDefineXML(networkxml)
        new_net.setAutostart(True)
        new_net.create()
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
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
            ip = list(root.getiterator('ip'))
            if ip:
                attributes = ip[0].attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                ip = IPNetwork('%s/%s' % (firstip, netmask))
                cidr = ip.cidr
            dhcp = list(root.getiterator('dhcp'))
            if dhcp:
                dhcp = True
            else:
                dhcp = False
            domain = list(root.getiterator('domain'))
            if domain:
                attributes = domain[0].attrib
                domainname = attributes.get('name')
            else:
                domainname = networkname
            forward = list(root.getiterator('forward'))
            if forward:
                attributes = forward[0].attrib
                mode = attributes.get('mode')
            else:
                mode = 'isolated'
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
            plan = 'N/A'
            for element in list(root.getiterator('{kvirt}info')):
                e = element.find('{kvirt}plan')
                if e is not None:
                    plan = e.text
            networks[networkname]['plan'] = plan
        for interface in conn.listAllInterfaces():
            interfacename = interface.name()
            if interfacename == 'lo':
                continue
            netxml = interface.XMLDesc(0)
            root = ET.fromstring(netxml)
            ip = list(root.getiterator('ip'))
            if ip:
                attributes = ip[0].attrib
                ip = attributes.get('address')
                prefix = attributes.get('prefix')
                ip = IPNetwork('%s/%s' % (ip, prefix))
                cidr = ip.cidr
            else:
                cidr = 'N/A'
            networks[interfacename] = {'cidr': cidr, 'dhcp': 'N/A', 'type': 'bridged', 'mode': 'N/A'}
            plan = 'N/A'
            for element in list(root.getiterator('{kvirt}info')):
                e = element.find('{kvirt}plan')
                if e is not None:
                    plan = e.text
            networks[interfacename]['plan'] = plan
        return networks

    def list_subnets(self):
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        conn = self.conn
        try:
            pool = conn.storagePoolLookupByName(name)
        except:
            print(("Pool %s not found. Leaving..." % name))
            return {'result': 'failure', 'reason': "Pool %s not found" % name}
        if pool.isActive() and full:
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
            for element in list(root.getiterator('interface')):
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
        for element in list(root.getiterator('interface')):
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
        bridge = list(root.getiterator('bridge'))
        if bridge:
            attributes = bridge[0].attrib
            bridge = attributes.get('name')
        return bridge

    def get_pool_path(self, pool):
        conn = self.conn
        pool = conn.storagePoolLookupByName(pool)
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        pooltype = list(root.getiterator('pool'))[0].get('type')
        if pooltype in ['dir', 'logical', 'zfs']:
            poolpath = list(root.getiterator('path'))[0].text
        else:
            poolpath = list(root.getiterator('device'))[0].get('path')
        if pooltype == 'logical':
            product = list(root.getiterator('product'))
            if product:
                thinpool = list(root.getiterator('product'))[0].get('name')
                poolpath += " (thinpool:%s)" % thinpool
        return poolpath

    def flavors(self):
        return []

    def thintemplates(self, path, thinpool):
        thincommand = ("lvs -o lv_name  %s -S 'lv_attr =~ ^V && origin = \"\" && pool_lv = \"%s\"'  --noheadings"
                       % (path, thinpool))
        if self.protocol == 'ssh':
            thincommand = "ssh -p %s %s@%s \"%s\"" % (self.port, self.user, self.host, thincommand)
        results = os.popen(thincommand).read().strip()
        if results == '':
            return []
        return [name.strip() for name in results.split('\n')]

    def _fixqcow2(self, path, backing):
        command = "qemu-img create -q -f qcow2 -b %s -F qcow2 %s" % (backing, path)
        if self.protocol == 'ssh':
            command = "ssh -p %s %s@%s \"%s\"" % (self.port, self.user, self.host, command)
        os.system(command)

    def add_image_to_deadpool(self, poolname, pooltype, poolpath, shortimage, thinpool=None):
        sizecommand = "qemu-img info /tmp/%s --output=json" % shortimage
        if self.protocol == 'ssh':
            sizecommand = "ssh -p %s %s@%s \"%s\"" % (self.port, self.user, self.host, sizecommand)
        size = os.popen(sizecommand).read().strip()
        virtualsize = json.loads(size)['virtual-size']
        if pooltype == 'logical':
            if thinpool is not None:
                command = "lvcreate -qq -V %sb -T %s/%s -n %s" % (virtualsize, poolpath, thinpool, shortimage)
            else:
                command = "lvcreate -qq -L %sb -n %s %s" % (virtualsize, shortimage, poolpath)
        elif pooltype == 'zfs':
            command = "zfs create -V %s %s/%s" % (virtualsize, poolname, shortimage)
        else:
            common.pprint("Invalid pooltype %s" % pooltype, color='red')
            return
        command += "; qemu-img convert -p -f qcow2 -O raw -t none -T none /tmp/%s %s/%s" % (shortimage, poolpath,
                                                                                            shortimage)
        command += "; rm -rf /tmp/%s" % shortimage
        if self.protocol == 'ssh':
            command = "ssh -p %s %s@%s \"%s\"" % (self.port, self.user, self.host, command)
        os.system(command)

    def _createthinlvm(self, name, path, thinpool, backing=None, size=None):
        if backing is not None:
            command = "lvcreate -qq -ay -K -s --name %s %s/%s" % (name, path, backing)
        else:
            command = "lvcreate -qq -V %sG -T %s/%s -n %s" % (size, path, thinpool, name)
        if self.protocol == 'ssh':
            command = "ssh -p %s %s@%s \"%s\"" % (self.port, self.user, self.host, command)
        os.system(command)

    def _deletelvm(self, disk):
        command = "lvremove -qqy %s" % (disk)
        if self.protocol == 'ssh':
            command = "ssh -p %s %s@%s \"%s\"" % (self.port, self.user, self.host, command)
        os.system(command)
