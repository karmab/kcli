#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvm Provider class
"""

from distutils.spawn import find_executable
# from urllib.request import urlopen, urlretrieve
from urllib.request import urlopen
from kvirt import defaults
from kvirt.defaults import UBUNTUS, METADATA_FIELDS
from kvirt import common
from netaddr import IPAddress, IPNetwork
from libvirt import open as libvirtopen, registerErrorHandler
from libvirt import VIR_DOMAIN_AFFECT_LIVE, VIR_DOMAIN_AFFECT_CONFIG
from libvirt import VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT as vir_src_agent
from libvirt import VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE as vir_src_lease
from libvirt import (VIR_DOMAIN_NOSTATE, VIR_DOMAIN_RUNNING, VIR_DOMAIN_BLOCKED, VIR_DOMAIN_PAUSED,
                     VIR_DOMAIN_SHUTDOWN, VIR_DOMAIN_SHUTOFF, VIR_DOMAIN_CRASHED)
from pwd import getpwuid
import json
import os
from subprocess import call
import re
import string
from tempfile import TemporaryDirectory
import time
import xml.etree.ElementTree as ET


LIBVIRT_CMD_NONE = 0
LIBVIRT_CMD_MODIFY = 1
LIBVIRT_CMD_DELETE = 2
LIBVIRT_CMD_ADD_FIRST = 4
LIBVIRT_SECTION_NONE = 0
LIBVIRT_SECTION_BRIDGE = 1
LIBVIRT_SECTION_DOMAIN = 2
LIBVIRT_SECTION_IP = 3
LIBVIRT_SECTION_IP_DHCP_HOST = 4
LIBVIRT_SECTION_IP_DHCP_RANGE = 5
LIBVIRT_SECTION_FORWARD = 6
LIBVIRT_SECTION_FORWARD_INTERFACE = 7
LIBVIRT_SECTION_FORWARD_PF = 8
LIBVIRT_SECTION_PORTGROUP = 9
LIBVIRT_SECTION_DNS_HOST = 10
LIBVIRT_SECTION_DNS_TXT = 11
LIBVIRT_SECTION_DNS_SRV = 12
LIBVIRT_FLAGS_CURRENT = 0
LIBVIRT_FLAGS_LIVE = 1
LIBVIRT_FLAGS_CONFIG = 2

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
states = {VIR_DOMAIN_NOSTATE: 'nostate', VIR_DOMAIN_RUNNING: 'up',
          VIR_DOMAIN_BLOCKED: 'blocked', VIR_DOMAIN_PAUSED: 'paused',
          VIR_DOMAIN_SHUTDOWN: 'shuttingdown', VIR_DOMAIN_SHUTOFF: 'down',
          VIR_DOMAIN_CRASHED: 'crashed'}


def libvirt_callback(ignore, err):
    """

    :param ignore:
    :param err:
    :return:
    """
    return


registerErrorHandler(f=libvirt_callback, ctx=None)


class Kvirt(object):
    """

    """
    def __init__(self, host='127.0.0.1', port=None, user='root', protocol='ssh', url=None, debug=False, insecure=False,
                 session=False):
        if url is None:
            socketf = '/var/run/libvirt/libvirt-sock' if not session else '/home/%s/.cache/libvirt/libvirt-sock' % user
            conntype = 'system' if not session else 'session'
            if host == '127.0.0.1' or host == 'localhost':
                url = "qemu:///%s" % conntype
                if os.path.exists("/i_am_a_container") and not os.path.exists(socketf):
                    common.pprint("You need to add -v /var/run/libvirt:/var/run/libvirt to container alias",
                                  color='red')
                    self.conn = None
                    return
            elif protocol == 'ssh':
                if port != 22:
                    url = "qemu+%s://%s@%s:%s/%s?socket=%s" % (protocol, user, host, port, conntype, socketf)
                else:
                    url = "qemu+%s://%s@%s/%s?socket=%s" % (protocol, user, host, conntype, socketf)
            elif port:
                url = "qemu+%s://%s@%s:%s/%s?socket=%s" % (protocol, user, host, port, conntype, socketf)
            else:
                url = "qemu:///%s" % conntype
            if url.startswith('qemu+ssh'):
                if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                    url = "%s&no_verify=1&keyfile=%s" % (url, os.path.expanduser("~/.kcli/id_rsa"))
                elif os.path.exists(os.path.expanduser("~/.kcli/id_dsa")):
                    url = "%s&no_verify=1&keyfile=%s" % (url, os.path.expanduser("~/.kcli/id_dsa"))
                elif insecure:
                    url = "%s&no_verify=1" % url
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
        identityfile = None
        if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        if identityfile is not None:
            self.identitycommand = "-i %s" % identityfile
        else:
            self.identitycommand = ""

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

    def create(self, name, virttype=None, profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None,
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[],
               kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False,
               memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={}):
        namespace = ''
        ignition = False
        usermode = False
        macosx = False
        diskpath = None
        qemuextra = overrides.get('qemuextra')
        if 'session' in self.url:
            usermode = True
            userport = common.get_free_port()
            metadata['ip'] = userport
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        # if start and self.no_memory(memory):
        #    return {'result': 'failure', 'reason': "Not enough memory to run this vm"}
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
        metadata['creationdate'] = creationdate
        metadataxml = """<metadata>
        <kvirt:info xmlns:kvirt="kvirt">
        <kvirt:creationdate>%s</kvirt:creationdate>""" % creationdate
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            metadataxml += "\n<kvirt:%s>%s</kvirt:%s>" % (entry, metadata[entry], entry)
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
        allnetworks = self.list_networks()
        bridges = []
        networks = []
        ipv6networks = []
        for n in allnetworks:
            if allnetworks[n]['type'] == 'bridged':
                bridges.append(n)
            elif isinstance(allnetworks[n]['cidr'], str):
                networks.append(n)
            elif ':' not in str(allnetworks[n]['cidr'].cidr):
                networks.append(n)
            else:
                ipv6networks.append(n)
        ipv6 = []
        machine = 'pc'
        # sysinfo = "<smbios mode='sysinfo'/>"
        disksxml = ''
        fixqcow2path, fixqcow2backing = None, None
        volsxml = {}
        virtio_index, ide_index, scsi_index = 0, 0, 0
        for index, disk in enumerate(disks):
            if disk is None:
                disksize = default_disksize
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                diskpooltype = default_pooltype
                diskpoolpath = default_poolpath
                diskthinpool = default_thinpool
                diskname = None
                diskwwn = None
                diskimage = None
                diskmacosx = False
            elif isinstance(disk, int):
                disksize = disk
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                diskpooltype = default_pooltype
                diskpoolpath = default_poolpath
                diskthinpool = default_thinpool
                diskwwn = None
                diskimage = None
                diskname = None
                diskmacosx = False
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
                diskpooltype = default_pooltype
                diskpoolpath = default_poolpath
                diskthinpool = default_thinpool
                diskwwn = None
                diskimage = None
                diskname = None
                diskmacosx = False
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskthin = disk.get('thin', default_diskthin)
                diskinterface = disk.get('interface', default_diskinterface)
                diskpool = disk.get('pool', default_pool)
                diskwwn = disk.get('wwn')
                diskimage = disk.get('image')
                diskname = disk.get('name')
                diskmacosx = disk.get('macosx', False)
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
            diskbus = diskinterface
            if diskinterface == 'ide':
                diskdev = 'hd%s' % chr(ide_index + ord('a'))
                ide_index += 1
            elif diskinterface in ['scsi', 'sata']:
                diskdev = 'sd%s' % chr(scsi_index + ord('a'))
                scsi_index += 1
            else:
                diskdev = 'vd%s' % chr(virtio_index + ord('a'))
                virtio_index += 1
            diskformat = 'qcow2'
            if not diskthin:
                diskformat = 'raw'
            storagename = "%s_%d.img" % (name, index) if diskname is None else diskname
            diskpath = "%s/%s" % (diskpoolpath, storagename)
            if image is not None and index == 0:
                diskimage = image
            if diskimage is not None:
                try:
                    if diskthinpool is not None:
                        matchingthinimages = self.thinimages(diskpoolpath, diskthinpool)
                        if diskimage not in matchingthinimages:
                            raise NameError('No Template found')
                    else:
                        default_storagepool.refresh(0)
                        if '/' in diskimage:
                            backingvolume = volumespaths[diskimage]['object']
                        else:
                            backingvolume = volumes[diskimage]['object']
                        backingxml = backingvolume.XMLDesc(0)
                        root = ET.fromstring(backingxml)
                except:
                    shortname = [t for t in defaults.IMAGES if defaults.IMAGES[t] == diskimage]
                    if shortname:
                        msg = "you don't have image %s. Use kcli download %s" % (diskimage, shortname[0])
                    else:
                        msg = "you don't have image %s" % diskimage
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
            if backing is not None and not diskthin:
                diskformat = 'qcow2'
                common.pprint("Raw disks don't support a backing, so using thin mode instead", color='yellow')
            volxml = self._xmlvolume(path=diskpath, size=disksize, pooltype=diskpooltype, backing=backing,
                                     diskformat=diskformat)
            if index == 0 and image is not None and diskpooltype in ['logical', 'zfs']\
                    and diskpool is None and not backing.startswith('/dev'):
                fixqcow2path = diskpath
                fixqcow2backing = backing
            if diskpooltype == 'logical' and diskthinpool is not None:
                thinsource = image if index == 0 and image is not None else None
                self._createthinlvm(storagename, diskpoolpath, diskthinpool, backing=thinsource, size=disksize)
            elif not self.disk_exists(pool, storagename):
                if diskpool in volsxml:
                    volsxml[diskpool].append(volxml)
                else:
                    volsxml[diskpool] = [volxml]
            else:
                common.pprint("Using existing disk %s..." % storagename, color='blue')
                if index == 0 and diskmacosx:
                    macosx = True
                    machine = 'pc-q35-2.11'
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
        nicslots = {k: 0 for k in range(0, 20)}
        alias = []
        guestagent = False
        for index, net in enumerate(nets):
            if usermode:
                continue
            ovs = False
            nicnuma = None
            macxml = ''
            ovsxml = ''
            nettype = 'virtio'
            if isinstance(net, str):
                netname = net
                nets[index] = {'name': netname}
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                if 'mac' in nets[index]:
                    mac = nets[index]['mac']
                    macxml = "<mac address='%s'/>" % mac
                if 'type' in nets[index]:
                    nettype = nets[index]['type']
                if index == 0 and 'alias' in nets[index] and isinstance(nets[index]['alias'], list):
                    reservedns = True
                    alias = nets[index]['alias']
                if 'ovs' in nets[index] and nets[index]['ovs']:
                    ovs = True
                if 'ip' in nets[index] and index == 0:
                    metadataxml += "<kvirt:ip >%s</kvirt:ip>" % nets[index]['ip']
                if 'numa' in nets[index] and numa:
                    nicnuma = nets[index]['numa']
            if ips and len(ips) > index and ips[index] is not None and\
                    netmasks and len(netmasks) > index and netmasks[index] is not None and gateway is not None:
                nets[index]['ip'] = ips[index]
                nets[index]['netmask'] = netmasks[index]
            if netname in networks:
                iftype = 'network'
                sourcexml = "<source network='%s'/>" % netname
            elif netname in bridges or ovs:
                if 'ip' in allnetworks[netname] and 'config_host' not in overrides:
                    overrides['config_host'] = allnetworks[netname]['ip']
                iftype = 'bridge'
                sourcexml = "<source bridge='%s'/>" % netname
                guestagent = True
                if reservedns and index == 0:
                    dnscmdhost = dns if dns is not None else self.host
                    dnscmd = "sed -i 's/nameserver .*/nameserver %s/' /etc/resolv.conf" % dnscmdhost
                    cmds = cmds[:index] + [dnscmd] + cmds[index:]
            elif netname in ipv6networks:
                iftype = 'network'
                sourcexml = "<source network='%s'/>" % netname
                ipv6.append(netname)
            else:
                return {'result': 'failure', 'reason': "Invalid network %s" % netname}
            if ovs:
                ovsxml = "<virtualport type='openvswitch'/>{}"
                if "port_name" in nets[index] and nets[index]["port_name"]:
                    port_name = "<target dev='{port_name}'/>".format(**nets[index])
                    ovsxml.format(port_name)
                else:
                    ovsxml.format("")
            if nicnuma is not None:
                bus = nicnuma + 1
                slot = nicslots[int(nicnuma)]
                nicnumaxml = "<address type='pci' domain='0x0000' bus='0x0%s' slot='0x0%s' function='0x0'/>" % (bus,
                                                                                                                slot)
                nicslots[int(nicnuma)] += 1
            else:
                nicnumaxml = ""
            netxml = """%s
                     <interface type='%s'>
                     %s
                     %s
                     %s
                     %s
                     <model type='%s'/>
                     </interface>""" % (netxml, iftype, macxml, sourcexml, ovsxml, nicnumaxml, nettype)
        metadataxml += "</kvirt:info></metadata>"
        if guestagent:
            gcmds = []
            if image is not None and 'cos' not in image and 'fedora-coreos' not in image:
                lower = image.lower()
                if lower.startswith('fedora') or lower.startswith('rhel') or lower.startswith('centos'):
                    gcmds.append('yum -y install qemu-guest-agent')
                    gcmds.append('systemctl enable qemu-guest-agent')
                    gcmds.append('systemctl start qemu-guest-agent')
                elif lower.startswith('debian') or [x for x in UBUNTUS if x in lower] or 'ubuntu' in lower:
                    gcmds.append('apt-get update')
                    gcmds.append('apt-get -f install qemu-guest-agent')
                    gcmds.append('/etc/init.d/qemu-guest-agent start')
                    gcmds.append('update-rc.d  qemu-guest-agent defaults')
            index = 0
            if image is not None and image.startswith('rhel'):
                subindex = [i for i, value in enumerate(cmds) if value.startswith('subscription-manager')]
                if subindex:
                    index = subindex.pop() + 1
            cmds = cmds[:index] + gcmds + cmds[index:]
        isoxml = ''
        if iso is not None:
            if os.path.isabs(iso):
                if self.protocol == 'ssh' and self.host not in ['localhost', '127.0.0.1']:
                    isocheckcmd = 'ssh %s -p %s %s@%s "ls %s >/dev/null 2>&1"' % (self.identitycommand, self.port,
                                                                                  self.user, self.host, iso)
                    code = os.system(isocheckcmd)
                    if code != 0:
                        if start:
                            return {'result': 'failure', 'reason': "Iso %s not found" % iso}
                        else:
                            common.pprint("Iso %s not found. Make sure it's there before booting" % iso, color='yellow')
                elif not os.path.exists(iso):
                    if start:
                        return {'result': 'failure', 'reason': "Iso %s not found" % iso}
                    else:
                        common.pprint("Iso %s not found. Make sure it's there before booting" % iso, color='yellow')
            else:
                if iso not in volumes:
                    if start:
                        return {'result': 'failure', 'reason': "Iso %s not found" % iso}
                    else:
                        common.pprint("Iso %s not found. Make sure it's there before booting" % iso, color='yellow')
                        iso = "%s/%s" % (default_poolpath, iso)
                        common.pprint("Setting iso full path to %s" % iso, color='yellow')
                else:
                    isovolume = volumes[iso]['object']
                    iso = isovolume.path()
            isoxml = """<disk type='file' device='cdrom'>
                        <driver name='qemu' type='raw'/>
                        <source file='%s'/>
                        <target dev='hdc' bus='ide'/>
                        <readonly/>
                        </disk>""" % iso
        if cloudinit:
            if image is not None and common.needs_ignition(image):
                localhosts = ['localhost', '127.0.0.1']
                ignition = True
                ignitiondir = '/var/tmp'
                k8sdir = '/var/run/secrets/kubernetes.io'
                if os.path.exists("/i_am_a_container") and not os.path.exists(k8sdir):
                    ignitiondir = '/ignitiondir'
                    if not os.path.exists(ignitiondir):
                        msg = "You need to add -v /var/tmp:/ignitiondir to container alias"
                        return {'result': 'failure', 'reason': msg}
                elif self.protocol == 'ssh' and self.host not in localhosts:
                    ignitiontmpdir = TemporaryDirectory()
                    ignitiondir = ignitiontmpdir.name
                version = common.ignition_version(image)
                ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                               domain=domain, reserveip=reserveip, files=files,
                                               enableroot=enableroot, overrides=overrides, version=version, plan=plan,
                                               ipv6=ipv6, image=image)
                with open('%s/%s.ign' % (ignitiondir, name), 'w') as ignitionfile:
                    ignitionfile.write(ignitiondata)
                    identityfile = None
                if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                    identityfile = os.path.expanduser("~/.kcli/id_rsa")
                elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                    identityfile = os.path.expanduser("~/.kcli/id_rsa")
                if identityfile is not None:
                    identitycommand = "-i %s" % identityfile
                else:
                    identitycommand = ""
                if self.protocol == 'ssh' and self.host not in localhosts:
                    ignitioncmd1 = 'scp %s -qP %s %s/%s.ign %s@%s:/var/tmp' % (identitycommand, self.port, ignitiondir,
                                                                               name, self.user, self.host)
                    code = os.system(ignitioncmd1)
                    if code != 0:
                        return {'result': 'failure', 'reason': "Unable to create ignition data file in /var/tmp"}
                    ignitiontmpdir.cleanup()
            elif image is not None and not ignition and diskpath is not None:
                cloudinitiso = "%s/%s.ISO" % (default_poolpath, name)
                dtype = 'block' if '/dev' in diskpath else 'file'
                dsource = 'dev' if '/dev' in diskpath else 'file'
                isoxml = """%s<disk type='%s' device='cdrom'>
                        <driver name='qemu' type='raw'/>
                        <source %s='%s'/>
                        <target dev='hdd' bus='ide'/>
                        <readonly/>
                        </disk>""" % (isoxml, dtype, dsource, cloudinitiso)
                userdata, metadata, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                               gateway=gateway, dns=dns, domain=domain,
                                                               reserveip=reserveip, files=files, enableroot=enableroot,
                                                               overrides=overrides, storemetadata=storemetadata,
                                                               image=image, ipv6=ipv6)
                with TemporaryDirectory() as tmpdir:
                        common.make_iso(name, tmpdir, userdata, metadata, netdata)
                        self._uploadimage(name, pool=default_storagepool, origin=tmpdir)
        listen = '0.0.0.0' if self.host not in ['localhost', '127.0.0.1'] else '127.0.0.1'
        displayxml = """<input type='tablet' bus='usb'/>
                        <input type='mouse' bus='ps2'/>
                        <graphics type='%s' port='-1' autoport='yes' listen='%s'>
                        <listen type='address' address='%s'/>
                        </graphics>
                        <memballoon model='virtio'/>""" % (display, listen, listen)
        if cpumodel == 'host-model':
            cpuxml = """<cpu mode='host-model'>
                        <model fallback='allow'/>"""
        elif cpumodel == 'host-passthrough':
            cpuxml = """<cpu mode='host-passthrough'>
                        <model fallback='allow'/>"""
        else:
            cpuxml = """<cpu mode='custom' match='exact'>
                        <model fallback='allow'>%s</model>""" % cpumodel
        capabilities = self.conn.getCapabilities()
        nestedfeature = 'vmx' if 'vmx' in capabilities else 'svm'
        nestedflag = 'require' if nested else 'disable'
        if virttype is None:
            if "<domain type='kvm'" not in capabilities:
                virttype = 'qemu'
                nestedflag = 'disable'
            else:
                virttype = 'kvm'
        elif virttype not in ['qemu', 'kvm', 'xen', 'lxc']:
            msg = "Incorrect virttype %s" % virttype
            return {'result': 'failure', 'reason': msg}
        cpuxml += "<feature policy='%s' name='%s'/>" % (nestedflag, nestedfeature)
        if cpuflags:
            for flag in cpuflags:
                if isinstance(flag, str):
                    if flag == 'vmx':
                        continue
                    cpuxml += "<feature policy='optional' name='%s'/>" % flag
                elif isinstance(flag, dict):
                    feature = flag.get('name')
                    policy = flag.get('policy', 'optional')
                    if feature is None:
                        continue
                    elif feature == 'vmx':
                        continue
                    elif policy in ['force', 'require', 'optional', 'disable', 'forbid']:
                        cpuxml += "<feature policy='%s' name='%s'/>" % (policy, feature)
        busxml = ""
        if cpuxml != '':
            if numa:
                numamemory = 0
                numaxml = '<numa>'
                for index, cell in enumerate(numa):
                    if not isinstance(cell, dict):
                        msg = "Can't process entry %s in numa block" % index
                        return {'result': 'failure', 'reason': msg}
                    else:
                        cellid = cell.get('id', index)
                        cellcpus = cell.get('vcpus')
                        cellmemory = cell.get('memory')
                        if cellcpus is None or cellmemory is None:
                            msg = "Can't properly use cell %s in numa block" % index
                            return {'result': 'failure', 'reason': msg}
                        numaxml += "<cell id='%s' cpus='%s' memory='%s' unit='MiB'/>" % (cellid, cellcpus, cellmemory)
                        numamemory += int(cellmemory)
                        busxml += """<controller type='pci' index='%s' model='pci-expander-bus'>
                        <model name='pxb'/>
                        <target busNr='%s'>
                        <node>%s</node>
                        </target>
                        <alias name='pci.%s'/>
                        <address type='pci' domain='0x0000' bus='0x00' function='0x0'/>
                        </controller>""" % (index + 1, 254 - index * 2, cellid, index + 1)
                cpuxml += '%s</numa>' % numaxml
                if numamemory > memory:
                    msg = "Can't use more memory for numa than assigned memory"
                    return {'result': 'failure', 'reason': msg}
            elif memoryhotplug:
                lastcpu = int(numcpus) - 1
                cpuxml += "<numa><cell id='0' cpus='0-%s' memory='%d' unit='KiB'/></numa>" % (lastcpu, memory * 1024)
            cpuxml += "</cpu>"
        cpupinningxml = ''
        if cpupinning:
            for entry in cpupinning:
                if not isinstance(entry, dict):
                    msg = "Can't process entry %s in numa block" % index
                    return {'result': 'failure', 'reason': msg}
                else:
                    vcpus = entry.get('vcpus')
                    hostcpus = entry.get('hostcpus')
                    if vcpus is None or hostcpus is None:
                        msg = "Can't process entry %s in cpupinning block" % index
                        return {'result': 'failure', 'reason': msg}
                    if '-' in str(vcpus):
                        if len(vcpus.split('-')) != 2:
                            msg = "Can't properly split vcpu in cpupinning block"
                            return {'result': 'failure', 'reason': msg}
                        else:
                            idmin, idmax = vcpus.split('-')
                    else:
                        try:
                            idmin, idmax = vcpus, vcpus
                        except ValueError:
                            msg = "Can't properly use vcpu as integer in cpunning block"
                            return {'result': 'failure', 'reason': msg}
                    idmin, idmax = int(idmin), int(idmax) + 1
                    if idmax > numcpus:
                        msg = "Can't use more cpus for pinning than assigned numcpus"
                        return {'result': 'failure', 'reason': msg}
                    for cpunum in range(idmin, idmax):
                        cpupinningxml += "<vcpupin vcpu='%s' cpuset='%s'/>\n" % (cpunum, hostcpus)
            cpupinningxml = "<cputune>%s</cputune>" % cpupinningxml
        numatunexml = ''
        if numamode is not None:
            numatunexml += "<numatune><memory mode='%s' nodeset='0'/></numatune>" % numamode
        if macosx:
            cpuxml = ""
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
        guestxml = """<channel type='unix'>
                      <source mode='bind'/>
                      <target type='virtio' name='org.qemu.guest_agent.0'/>
                      </channel>"""
        if cpuhotplug:
            vcpuxml = "<vcpu  placement='static' current='%d'>64</vcpu>" % (numcpus)
        else:
            vcpuxml = "<vcpu>%d</vcpu>" % numcpus
        qemuextraxml = ''
        if ignition or usermode or macosx or tpm or qemuextra is not None:
            namespace = "xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'"
            ignitionxml = ""
            if ignition:
                ignitionxml = """<qemu:arg value='-fw_cfg' />
                                  <qemu:arg value='name=opt/com.coreos/config,file=/var/tmp/%s.ign' />""" % name
            usermodexml = ""
            if usermode:
                netmodel = 'virtio-net-pci' if not macosx else 'e1000-82545em'
                usermodexml = """<qemu:arg value='-netdev'/>
                                 <qemu:arg value='user,id=mynet.0,net=10.0.10.0/24,hostfwd=tcp::%s-:22'/>
                                 <qemu:arg value='-device'/>
                                 <qemu:arg value='%s,netdev=mynet.0'/>""" % (userport, netmodel)
            macosxml = ""
            if macosx:
                osk = "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
                cpuflags = "+invtsc,vmware-cpuid-freq=on,+pcid,+ssse3,+sse4.2,+popcnt,+avx,+aes,+xsave,+xsaveopt"
                cpuinfo = "Penryn,kvm=on,vendor=GenuineIntel,%s,check" % cpuflags
                macosxml = """<qemu:arg value='-cpu'/>
                              <qemu:arg value='%s'/>
                              <qemu:arg value='-device'/>
                              <qemu:arg value='isa-applesmc,osk=%s'/>
                             <qemu:arg value='-smbios'/>
                             <qemu:arg value='type=2'/>""" % (cpuinfo, osk)
            if qemuextra is not None:
                freeformxml = ""
                freeform = qemuextra.split(" ")
                for entry in freeform:
                    freeformxml += "<qemu:arg value='%s'/>\n" % entry
            else:
                freeformxml = ""
            qemuextraxml = """<qemu:commandline>
                              %s
                              %s
                              %s
                              %s
                              </qemu:commandline>""" % (ignitionxml, usermodexml, macosxml, freeformxml)
        sharedxml = ""
        if sharedfolders:
            for folder in sharedfolders:
                # accessmode = "passthrough"
                accessmode = "mapped"
                sharedxml += "<filesystem type='mount' accessmode='%s'>" % accessmode
                sharedxml += "<source dir='%s'/><target dir='%s'/>" % (folder, os.path.basename(folder))
                sharedxml += "</filesystem>"
                foldercmd = "sudo mkdir %s ; sudo chmod 777 %s" % (folder, folder)
                if self.host == 'localhost' or self.host == '127.0.0.1' and not os.path.exists(folder):
                    oldmask = os.umask(000)
                    os.makedirs(folder)
                    os.umask(oldmask)
                elif self.protocol == 'ssh':
                    foldercmd = 'ssh %s -p %s %s@%s "test -d %s || (%s)"' % (self.identitycommand, self.port,
                                                                             self.user, self.host, folder, foldercmd)
                    code = os.system(foldercmd)
        kernelxml = ""
        if kernel is not None:
            locationdir = os.path.basename(kernel)
            locationdir = "%s/%s" % (default_poolpath, locationdir)
            if self.host == 'localhost' or self.host == '127.0.0.1':
                os.mkdir(locationdir)
            elif self.protocol == 'ssh':
                locationcmd = 'ssh %s -p %s %s@%s "mkdir %s"' % (self.identitycommand, self.port, self.user,
                                                                 self.host, locationdir)
                code = os.system(locationcmd)
            else:
                return {'result': 'failure', 'reason': "Couldn't create dir to hold kernel and initrd"}
            if kernel.startswith('http') or kernel.startswith('ftp'):
                if 'rhcos' in kernel:
                    if self.host == 'localhost' or self.host == '127.0.0.1':
                        kernelcmd = "curl -Lo %s/vmlinuz -f '%s'" % (locationdir, kernel)
                        initrdcmd = "curl -Lo %s/initrd.img -f '%s'" % (locationdir, initrd)
                    elif self.protocol == 'ssh':
                        kernelcmd = 'ssh %s -p %s %s@%s "curl -Lo %s/vmlinuz -f \'%s\'"' % (self.identitycommand,
                                                                                            self.port, self.user,
                                                                                            self.host, locationdir,
                                                                                            kernel)
                        initrdcmd = 'ssh %s -p %s %s@%s "curl -Lo %s/initrd.img -f \'%s\'"' % (self.identitycommand,
                                                                                               self.port, self.user,
                                                                                               self.host, locationdir,
                                                                                               initrd)
                    code = os.system(kernelcmd)
                    code = os.system(initrdcmd)
                else:
                    try:
                        location = urlopen(kernel).readlines()
                    except Exception as e:
                        return {'result': 'failure', 'reason': e}
                    for line in location:
                        if 'init' in str(line):
                            p = re.compile(r'.*<a href="(.*)">\1.*')
                            m = p.match(str(line))
                            if m is not None and initrd is None:
                                initrdfile = m.group(1)
                                initrdurl = "%s/%s" % (kernel, initrdfile)
                                initrd = "%s/initrd" % locationdir
                                if self.host == 'localhost' or self.host == '127.0.0.1':
                                    initrdcmd = "curl -Lo %s -f '%s'" % (initrd, initrdurl)
                                elif self.protocol == 'ssh':
                                    initrdcmd = 'ssh %s -p %s %s@%s "curl -Lo %s -f \'%s\'"' % (self.identitycommand,
                                                                                                self.port, self.user,
                                                                                                self.host, initrd,
                                                                                                initrdurl)
                                code = os.system(initrdcmd)
                    kernelurl = '%s/vmlinuz' % kernel
                    kernel = "%s/vmlinuz" % locationdir
                    if self.host == 'localhost' or self.host == '127.0.0.1':
                        kernelcmd = "curl -Lo %s -f '%s'" % (kernel, kernelurl)
                    elif self.protocol == 'ssh':
                        kernelcmd = 'ssh %s -p %s %s@%s "curl -Lo %s -f \'%s\'"' % (self.identitycommand,
                                                                                    self.port, self.user, self.host,
                                                                                    kernel, kernelurl)
                    code = os.system(kernelcmd)
            elif initrd is None:
                return {'result': 'failure', 'reason': "Missing initrd"}
            kernel = "%s/vmlinuz" % locationdir
            initrd = "%s/initrd.img" % locationdir
            kernelxml = "<kernel>%s</kernel><initrd>%s</initrd>" % (kernel, initrd)
            if cmdline is not None:
                kernelxml += "<cmdline>%s</cmdline>" % cmdline
        bootdev = "<boot dev='hd'/>"
        if iso:
            bootdev += "<boot dev='cdrom'/>"
        memoryhotplugxml = "<maxMemory slots='16' unit='MiB'>1524288</maxMemory>" if memoryhotplug else ""
        videoxml = ""
        firmwarexml = ""
        if macosx:
            firmwarexml = """<loader readonly='yes' type='pflash'>%s/OVMF_CODE.fd</loader>
                             <nvram>%s/OVMF_VARS-1024x768.fd</nvram>""" % (default_poolpath, default_poolpath)
            videoxml = """<video><model type='qxl' vram='65536'/></video>"""
            guestxml = ""
        hostdevxml = ""
        if pcidevices:
            for index, pcidevice in enumerate(pcidevices):
                pcidevice = str(pcidevice)
                newdomain = "0000"
                if len(pcidevice.split(':')) != 2:
                    return {'result': 'failure', 'reason': "Incorrect pcidevice entry %s" % index}
                newbus = pcidevice.split(':')[0]
                if len(pcidevice.split('.')) != 2:
                    return {'result': 'failure', 'reason': "Incorrect pcidevice entry %s" % index}
                newslot = pcidevice.split('.')[0].replace('%s:' % newbus, '')
                newfunction = pcidevice.split('.')[1]
                newhostdev = """<hostdev mode='subsystem' type='pci' managed='yes'>
                                <source><address domain='0x%s' bus='0x%s' slot='0x%s' function='0x%s'/></source>
                                </hostdev>""" % (newdomain, newbus, newslot, newfunction)
                hostdevxml += newhostdev
        rngxml = ""
        if rng:
            rngxml = """<rng model='virtio'>
                        <rate bytes='1024' period='1000'/>
                        <backend model='random'>/dev/random</backend>
                        <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
                        </rng>"""
        tpmxml = ""
        if tpm:
            tpmxml = """<tpm model='tpm-tis'>
                        <backend type='emulator' version='2.0'>
                        </backend>
                        </tpm>"""
        vmxml = """<domain type='%s' %s>
                  <name>%s</name>
                  %s
                  %s
                  %s
                  %s
                  <memory unit='MiB'>%d</memory>
                  %s
                  <os>
                    <type arch='x86_64' machine='%s'>hvm</type>
                    %s
                    %s
                    %s
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
                    %s
                    %s
                    %s
                    %s
                    %s
                    %s
                    %s
                  </devices>
                    %s
                    %s
                    </domain>""" % (virttype, namespace, name, metadataxml, memoryhotplugxml, cpupinningxml,
                                    numatunexml, memory, vcpuxml, machine, firmwarexml, bootdev, kernelxml, disksxml,
                                    busxml, netxml, isoxml, displayxml, serialxml, sharedxml, guestxml, videoxml,
                                    hostdevxml, rngxml, tpmxml, cpuxml, qemuextraxml)
        if self.debug:
            common.pprint(vmxml, color='blue')
        conn.defineXML(vmxml)
        vm = conn.lookupByName(name)
        autostart = 1 if autostart else 0
        vm.setAutostart(autostart)
        for pool in volsxml:
            storagepool = conn.storagePoolLookupByName(pool)
            storagepool.refresh(0)
            for volxml in volsxml[pool]:
                storagepool.createXML(volxml, 0)
        if fixqcow2path is not None and fixqcow2backing is not None:
            self._fixqcow2(fixqcow2path, fixqcow2backing)
        xml = vm.XMLDesc(0)
        vmxml = ET.fromstring(xml)
        self._reserve_ip(name, vmxml, nets, primary=reserveip)
        if start:
            try:
                vm.create()
            except Exception as e:
                return {'result': 'failure', 'reason': e}
        self.reserve_dns(name, nets=nets, domain=domain, alias=alias, force=True, primary=reservedns)
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
            try:
                vm.create()
            except Exception as e:
                return {'result': 'failure', 'reason': e}
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

    def no_memory(self, memory):
        conn = self.conn
        totalmemory = conn.getInfo()[1]
        usedmemory = 0
        for vm in conn.listAllDomains(0):
            if vm.isActive() == 0:
                continue
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            mem = list(root.getiterator('memory'))[0]
            unit = mem.attrib['unit']
            mem = mem.text
            if unit == 'KiB':
                mem = float(mem) / 1024
                mem = int(mem)
            usedmemory += mem
        return True if usedmemory + memory > totalmemory else False

    def report(self):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        hostname = conn.getHostname()
        cpus = conn.getCPUMap()[0]
        totalmemory = conn.getInfo()[1]
        print("Connection: %s" % self.url)
        print("Host: %s" % hostname)
        print("Cpus: %s" % cpus)
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
        print("Vms Running: %s" % totalvms)
        print("Memory Used: %sMB of %sMB" % (usedmemory, totalmemory))
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
            print(("Storage:%s Type: %s Path:%s Used space: %sGB Available space: %sGB" % (poolname, pooltype, poolpath,
                                                                                           used, available)))
        for interface in conn.listInterfaces():
            if interface == 'lo':
                continue
            print("Network: %s Type: bridged" % interface)
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
            print("Network: %s Type: routed Cidr: %s Dhcp: %s" % (networkname, cidr, dhcp))

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
        for vm in conn.listAllDomains(0):
            vms.append(self.info(vm.name(), vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if not vm.isActive():
            common.pprint("VM down", color='red')
            return
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            host = self.host
            for element in list(root.getiterator('graphics')):
                attributes = element.attrib
                if attributes['listen'] == '127.0.0.1':
                    if not os.path.exists("i_am_a_container") or self.host not in ['127.0.0.1', 'localhost']:
                        tunnel = True
                        host = '127.0.0.1'
                protocol = attributes['type']
                port = attributes['port']
                localport = port
                consolecommand = ''
                if os.path.exists("/i_am_a_container"):
                    self.identitycommand = self.identitycommand.replace('/root', '$HOME')
                if tunnel:
                    localport = common.get_free_port()
                    consolecommand += "ssh %s -o LogLevel=QUIET -f -p %s -L %s:127.0.0.1:%s %s@%s sleep 10;"\
                        % (self.identitycommand, self.port, localport, port, self.user, self.host)
                    host = '127.0.0.1'
                url = "%s://%s:%s" % (protocol, host, localport)
                if web:
                    if tunnel:
                        os.popen(consolecommand)
                    return url
                consolecommand += "remote-viewer %s &" % url
                if self.debug or os.path.exists("/i_am_a_container"):
                    msg = "Run the following command:\n%s" % consolecommand if not self.debug else consolecommand
                    common.pprint(msg)
                else:
                    os.popen(consolecommand)

    def serialconsole(self, name, web=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if not vm.isActive():
            common.pprint("VM down", color='red')
            return
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            serial = list(root.getiterator('serial'))
            if not serial:
                common.pprint("No serial Console found. Leaving...", color='red')
                return
            elif self.host in ['localhost', '127.0.0.1']:
                cmd = 'virsh -c %s console %s' % (self.url, name)
                if self.debug or os.path.exists("/i_am_a_container"):
                    msg = "Run the following command:\n%s" % cmd
                    common.pprint(msg)
                else:
                    os.system(cmd)
            else:
                for element in serial:
                    serialport = element.find('source').get('service')
                    if serialport:
                        if self.protocol != 'ssh':
                            common.pprint("Remote serial Console requires using ssh . Leaving...", color='red')
                            return
                        else:
                            if os.path.exists("/i_am_a_container"):
                                self.identitycommand = self.identitycommand.replace('/root', '$HOME')
                            serialcommand = "ssh %s -o LogLevel=QUIET -p %s %s@%s nc 127.0.0.1 %s" %\
                                (self.identitycommand, self.port, self.user, self.host, serialport)
                        if web:
                            return serialcommand
                        if self.debug or os.path.exists("/i_am_a_container"):
                            msg = "Run the following command:\n%s" % serialcommand if not self.debug else serialcommand
                            common.pprint(msg)
                        else:
                            os.system(serialcommand)
                            # os.system(serialcommand)

    def info(self, name, vm=None, debug=False):
        starts = {0: False, 1: True}
        conn = self.conn
        if vm is None:
            try:
                vm = conn.lookupByName(name)
            except:
                common.pprint("VM %s not found" % name, color='red')
                return {}
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        status = 'down'
        autostart = starts[vm.autostart()]
        description = list(root.getiterator('description'))
        if description:
            description = description[0].text
        else:
            description = ''
        [state, maxmem, memory, numcpus, cputime] = vm.info()
        status = states.get(state)
        memory = int(float(memory) / 1024)
        yamlinfo = {'name': name, 'autostart': autostart, 'nets': [], 'disks': [], 'status': status}
        plan, profile, image, ip, creationdate = '', None, None, None, None
        kube, kubetype = None, None
        for element in list(root.getiterator('{kvirt}info')):
            e = element.find('{kvirt}plan')
            if e is not None:
                plan = e.text
            e = element.find('{kvirt}kube')
            if e is not None:
                kube = e.text
            e = element.find('{kvirt}kubetype')
            if e is not None:
                kubetype = e.text
            e = element.find('{kvirt}profile')
            if e is not None:
                profile = e.text
            e = element.find('{kvirt}image')
            if e is not None:
                image = e.text
                yamlinfo['user'] = common.get_user(image)
            e = element.find('{kvirt}ip')
            if e is not None:
                ip = e.text
            e = element.find('{kvirt}creationdate')
            if e is not None:
                creationdate = e.text
            e = element.find('{kvirt}owner')
            if e is not None:
                yamlinfo['owner'] = e.text
        if image is not None:
            yamlinfo['image'] = image
        yamlinfo['plan'] = plan
        if profile is not None:
            yamlinfo['profile'] = profile
        if kube is not None and kubetype is not None:
            yamlinfo['kube'] = kube
            yamlinfo['kubetype'] = kubetype
        if creationdate is not None:
            yamlinfo['creationdate'] = creationdate
        yamlinfo['cpus'] = numcpus
        yamlinfo['memory'] = memory
        agentfaces = {}
        leasefaces = {}
        ifaces = {}
        if vm.isActive():
            networktypes = [element.get('type') for element in list(root.getiterator('interface'))]
            if 'bridge' in networktypes:
                try:
                    agentfaces = vm.interfaceAddresses(vir_src_agent, 0)
                except:
                    pass
            if 'network' in networktypes:
                leasefaces = vm.interfaceAddresses(vir_src_lease, 0)
            ifaces = {**agentfaces, **leasefaces}
        interfaces = list(root.getiterator('interface'))
        for index, element in enumerate(interfaces):
            networktype = element.get('type').replace('network', 'routed')
            device = "eth%s" % index
            mac = element.find('mac').get('address')
            if networktype == 'user':
                network = 'user'
            else:
                if networktype == 'bridge':
                    network = element.find('source').get('bridge')
                else:
                    network = element.find('source').get('network')
                if ip is None:
                    try:
                        networkdata = conn.networkLookupByName(network)
                        netxml = networkdata.XMLDesc()
                        netroot = ET.fromstring(netxml)
                        hostentries = list(netroot.getiterator('host'))
                        for host in hostentries:
                            if host.get('mac') == mac:
                                ip = host.get('ip')
                    except:
                        pass
            if ifaces and ip is None:
                ips = []
                for x in ifaces:
                    if ifaces[x]['hwaddr'] == mac and ifaces[x]['addrs'] is not None:
                        for entry in ifaces[x]['addrs']:
                            if entry['addr'].startswith('fe80::'):
                                continue
                            ip = entry['addr']
                            ips.append(ip)
                if ips:
                    ip4s = [i for i in ips if ':' not in i]
                    ip6s = [i for i in ips if i not in ip4s]
                    ip = ip4s[0] if ip4s else ip6s[0]
            yamlinfo['nets'].append({'device': device, 'mac': mac, 'net': network, 'type': networktype})
        if ip is not None:
            yamlinfo['ip'] = ip
            # better filter to detect user nets needed here
            if '.' not in ip and ':' not in ip:
                usernetinfo = {'device': 'eth%s' % len(yamlinfo['nets']), 'mac': 'N/A', 'net': 'user', 'type': 'user'}
                yamlinfo['nets'].append(usernetinfo)
        for element in list(root.getiterator('disk')):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            device = element.find('target').get('dev')
            diskformat = 'file'
            drivertype = element.find('driver').get('type')
            imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                          element.find('source').get('volume')]
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
        snapshots = []
        for snapshot in vm.snapshotListNames():
            if snapshot == currentsnapshot:
                current = True
            else:
                current = False
            snapshots.append({'snapshot': snapshot, 'current': current})
        if snapshots:
            yamlinfo['snapshots'] = snapshots
        if debug:
            yamlinfo['debug'] = xml
        return yamlinfo

    def ip(self, name):
        ifaces = []
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            return None
        if not vm.isActive():
            return None
        else:
            mac = None
            interfaces = list(root.getiterator('interface'))
            for element in interfaces:
                networktype = element.get('type')
                if mac is None:
                    mac = element.find('mac').get('address')
                if networktype == 'user':
                    continue
                if networktype == 'bridge':
                    network = element.find('source').get('bridge')
                else:
                    network = element.find('source').get('network')
                    try:
                        networkdata = conn.networkLookupByName(network)
                        netxml = networkdata.XMLDesc()
                        netroot = ET.fromstring(netxml)
                        hostentries = list(netroot.getiterator('host'))
                        for host in hostentries:
                            if host.get('mac') == mac:
                                return host.get('ip')
                    except:
                        continue
            agentfaces = {}
            leasefaces = {}
            ifaces = {}
            networktypes = [element.get('type') for element in list(root.getiterator('interface'))]
            if 'bridge' in networktypes:
                try:
                    agentfaces = vm.interfaceAddresses(vir_src_agent, 0)
                except:
                    pass
            if 'network' in networktypes:
                leasefaces = vm.interfaceAddresses(vir_src_lease, 0)
            ifaces = {**agentfaces, **leasefaces}
            ips = []
            for x in ifaces:
                if ifaces[x]['hwaddr'] == mac and ifaces[x]['addrs'] is not None:
                    for entry in ifaces[x]['addrs']:
                        if entry['addr'].startswith('fe80::'):
                            continue
                        ip = entry['addr']
                        ips.append(ip)
            if ips:
                ip4s = [i for i in ips if ':' not in i]
                ip6s = [i for i in ips if i not in ip4s]
                ip = ip4s[0] if ip4s else ip6s[0]
                return ip
            else:
                return None

    def volumes(self, iso=False):
        isos = []
        images = []
        default_images = [os.path.basename(t).replace('.bz2', '') for t in list(defaults.IMAGES.values())
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
                for volume in self.thinimages(poolpath, thinpool):
                    if volume.endswith('qcow2') or volume.endswith('qc2') or volume in default_images:
                        images.extend("%s/%s" % (poolpath, volume))
            for volume in pool.listVolumes():
                if volume.endswith('iso'):
                    isos.append("%s/%s" % (poolpath, volume))
                elif volume.endswith('qcow2') or volume.endswith('qc2') or volume in default_images:
                    images.append("%s/%s" % (poolpath, volume))
        if iso:
            return sorted(isos, key=lambda s: s.lower())
        else:
            return sorted(images, key=lambda s: s.lower())

    def dnsinfo(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            return None, None
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        dnsclient, domain = None, None
        for element in list(root.getiterator('{kvirt}info')):
            e = element.find('{kvirt}dnsclient')
            if e is not None:
                dnsclient = e.text
            e = element.find('{kvirt}domain')
            if e is not None:
                domain = e.text
        return dnsclient, domain

    def delete(self, name, snapshots=False):
        bridged = False
        ignition = False
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
                    common.pprint("Deleting snapshot %s" % snapshot, color='blue')
                    snap = vm.snapshotLookupByName(snapshot)
                    snap.delete()
        ip = self.ip(name)
        status = {0: 'down', 1: 'up'}
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        disks = []
        for element in list(root.getiterator('{kvirt}info')):
            e = element.find('{kvirt}image')
            if e is not None:
                image = e.text
                if image is not None and ('coreos' in image or 'rhcos' in image):
                    ignition = True
                break
        for index, element in enumerate(list(root.getiterator('disk'))):
            source = element.find('source')
            if source is not None:
                imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                              element.find('source').get('volume')]
                imagefile = next(item for item in imagefiles if item is not None)
                if imagefile.endswith('.iso'):
                    continue
                elif imagefile.endswith("%s.ISO" % name) or "%s_" % name in imagefile or "%s.img" % name in imagefile:
                    disks.append(imagefile)
                elif imagefile == name:
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
            storageroot = ET.fromstring(poolxml)
            for element in list(storageroot.getiterator('path')):
                poolpath = element.text
                break
            product = list(storageroot.getiterator('product'))
            if product:
                thinpools.append(poolpath)
            for stor in storage.listVolumes():
                for disk in disks:
                    if stor == os.path.basename(disk):
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
            if networktype == 'user':
                continue
            try:
                network = element.find('source').get('network')
                network = conn.networkLookupByName(network)
                netxml = network.XMLDesc(0)
                netroot = ET.fromstring(netxml)
                for host in list(netroot.getiterator('host')):
                    hostmac = host.get('mac')
                    iphost = host.get('ip')
                    hostname = host.get('name')
                    if hostmac == mac:
                        hostentry = "<host mac='%s' name='%s' ip='%s'/>" % (mac, hostname, iphost)
                        network.update(2, 4, 0, hostentry, 1)
                    hostname = host.find('hostname')
                    if hostname is not None and hostname.text == name:
                        hostentry = '<host ip="%s"><hostname>%s</hostname></host>' % (iphost, name)
                        network.update(2, 10, 0, hostentry, 1)
            except:
                if networktype == 'bridge':
                    bridged = True
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
                print("Deleting host entry. sudo password might be asked")
                call("sudo sed -i '/%s/d' /etc/hosts" % hostentry, shell=True)
                if bridged and self.host in ['localhost', '127.0.0.1']:
                    try:
                        call("sudo /usr/bin/systemctl restart dnsmasq", shell=True)
                    except:
                        pass
            if bridged and self.protocol == 'ssh' and self.host not in ['localhost', '127.0.0.1']:
                deletecmd = "sed -i '/%s/d' /etc/hosts" % hostentry
                if self.user != 'root':
                    deletecmd = "sudo %s" % deletecmd
                deletecmd = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host,
                                                           deletecmd)
                common.pprint("Checking if a remote host entry exists. sudo password for remote user %s might be asked"
                              % self.user, color='blue')
                call(deletecmd, shell=True)
                try:
                    dnsmasqcmd = "/usr/bin/systemctl restart dnsmasq"
                    if self.user != 'root':
                        dnsmasqcmd = "sudo %s" % dnsmasqcmd
                    dnsmasqcmd = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host,
                                                                dnsmasqcmd)
                    call(dnsmasqcmd, shell=True)
                except:
                    pass
        if ignition:
            ignitiondir = '/var/tmp' if os.path.exists("/i_am_a_container") else '/var/tmp'
            if self.protocol == 'ssh' and self.host not in ['localhost', '127.0.0.1']:
                ignitiondeletecmd = "ls /var/tmp/%s.ign >/dev/null 2>&1 && rm -f  /var/tmp/%s.ign" % (name, name)
                ignitiondeletecmd = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user,
                                                                   self.host, ignitiondeletecmd)
                call(ignitiondeletecmd, shell=True)
            elif os.path.exists('%s/%s.ign' % (ignitiondir, name)):
                os.remove('%s/%s.ign' % (ignitiondir, name))
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
        """

        :param old:
        :param new:
        :param full:
        :param start:
        """
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

    def _reserve_ip(self, name, vmxml, nets, force=True, primary=False):
        conn = self.conn
        macs = []
        for element in list(vmxml.getiterator('interface')):
            mac = element.find('mac').get('address')
            macs.append(mac)
        for index, net in enumerate(nets):
            ip = net.get('ip')
            network = net.get('name')
            mac = macs[index]
            reserveip = True if index == 0 and primary else False
            reserveip = net.get('reserveip', reserveip)
            if not reserveip or ip is None or network is None:
                continue
            network = conn.networkLookupByName(network)
            oldnetxml = network.XMLDesc()
            root = ET.fromstring(oldnetxml)
            oldentry = "<host name='%s'/>" % name
            try:
                network.update(2, 4, 0, oldentry, 1)
            except:
                pass
            try:
                network.update(2, 4, 0, oldentry, 2)
            except:
                pass
            ipentry = list(root.getiterator('ip'))
            if ipentry:
                attributes = ipentry[0].attrib
                firstip = attributes.get('address')
                netmask = next(a for a in [attributes.get('netmask'), attributes.get('prefix')] if a is not None)
                netip = IPNetwork('%s/%s' % (firstip, netmask))
            dhcp = list(root.getiterator('dhcp'))
            if not dhcp:
                continue
            if not IPAddress(ip) in netip:
                continue
            common.pprint("Adding a reserved ip entry for ip %s and mac %s " % (ip, mac), color='blue')
            network.update(4, 4, 0, '<host mac="%s" name="%s" ip="%s" />' % (mac, name, ip), 1)
            network.update(4, 4, 0, '<host mac="%s" name="%s" ip="%s" />' % (mac, name, ip), 2)

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        conn = self.conn
        bridged = False
        for index, net in enumerate(nets):
            if isinstance(net, str):
                netname = net
                net = {'name': netname}
            reservedns = True if index == 0 and primary else False
            reservedns = net.get('reservedns', reservedns)
            if not reservedns:
                continue
            netname = net.get('name')
            common.pprint("Creating Dns entry for %s.%s" % (name, netname), color='blue')
            if domain is not None and domain != netname:
                common.pprint("Creating Dns entry for %s.%s" % (name, domain), color='blue')
            try:
                network = conn.networkLookupByName(netname)
            except:
                bridged = True
            if ip is None:
                if isinstance(net, dict):
                    ip = net.get('ip')
                if ip is None:
                    counter = 0
                    while counter != 240:
                        ip = self.ip(name)
                        if ip is None:
                            time.sleep(5)
                            common.pprint("Waiting 5 seconds to grab ip...", color='blue')
                            counter += 5
                        else:
                            break
            if ip is None:
                common.pprint("Couldn't assign DNS for net %s" % index, color='red')
                continue
            if bridged:
                self._create_host_entry(name, ip, netname, domain, dnsmasq=True)
            else:
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
                dnsentry += '<hostname>%s.%s</hostname>' % (name, netname)
                if domain is not None and domain != netname:
                    dnsentry += '<hostname>%s.%s</hostname>' % (name, domain)
                for entry in alias:
                    dnsentry += "%s<hostname>%s</hostname>" % (entry, entry)
                dnsentry += "</host>"
                if force:
                    for host in list(root.getiterator('host')):
                        iphost = host.get('ip')
                        machost = host.get('mac')
                        if iphost == ip and machost is None:
                            existing = []
                            for hostname in list(host.getiterator('hostname')):
                                existing.append(hostname.text)
                            if name in existing:
                                common.pprint("Skipping existing dns entry for %s" % name, color='blue')
                            oldentry = '<host ip="%s"></host>' % iphost
                            common.pprint("Removing old dns entry for ip %s" % ip, color='blue')
                            network.update(2, 10, 0, oldentry, 1)
                try:
                    network.update(4, 10, 0, dnsentry, 1)
                except:
                    common.pprint("Skipping existing dns entry for %s" % name, color='red')

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
                    common.pprint("Waiting 5 seconds to grab ip and create Host record...", color='blue')
                    counter += 10
                else:
                    break
        if ip is None:
            common.pprint("Couldn't assign Host", color='red')
            return
        self._create_host_entry(name, ip, netname, domain)

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

    def update_metadata(self, name, metatype, metavalue, append=False):
        ET.register_namespace('kvirt', 'kvirt')
        conn = self.conn
        vm = conn.lookupByName(name)
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        if not vm:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.isActive() == 1:
            common.pprint("Machine up. Change will only appear upon next reboot", color='yellow')
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
        if append and kmeta.text is not None:
            kmeta.text += ",%s" % metavalue
        else:
            kmeta.text = metavalue
        newxml = ET.tostring(root)
        conn.defineXML(newxml.decode("utf-8"))
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
        conn.defineXML(newxml.decode("utf-8"))
        return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            common.print("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        cpunode = list(root.getiterator('vcpu'))[0]
        cpuattributes = cpunode.attrib
        if not vm.isActive():
            cpunode.text = str(numcpus)
            newxml = ET.tostring(root)
            conn.defineXML(newxml.decode("utf-8"))
            return {'result': 'success'}
        elif 'current' in cpuattributes and cpuattributes['current'] != numcpus:
            if numcpus < int(cpuattributes['current']):
                common.pprint("Can't remove cpus while vm is up", color='red')
                return {'result': 'failure', 'reason': "VM %s not found" % name}
            else:
                vm.setVcpus(numcpus)
                return {'result': 'success'}
        else:
            common.pprint("Note it will only be effective upon next start", color='yellow')
            cpunode.text = str(numcpus)
            newxml = ET.tostring(root)
            conn.defineXML(newxml.decode("utf-8"))
            return {'result': 'success'}

    def update_memory(self, name, memory):
        conn = self.conn
        memory = str(int(memory) * 1024)
        try:
            vm = conn.lookupByName(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        memorynode = list(root.getiterator('memory'))[0]
        memorynode.text = memory
        currentmemory = list(root.getiterator('currentMemory'))[0]
        maxmemory = list(root.getiterator('maxMemory'))
        if maxmemory:
            diff = int(memory) - int(currentmemory.text)
            if diff > 0:
                xml = "<memory model='dimm'><target><size unit='KiB'>%s</size><node>0</node></target></memory>" % diff
                vm.attachDeviceFlags(xml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
        elif vm.isActive():
            common.pprint("Note it will only be effective upon next start", color='yellow')
        currentmemory.text = memory
        newxml = ET.tostring(root)
        conn.defineXML(newxml.decode("utf-8"))
        return {'result': 'success'}

    def update_iso(self, name, iso):
        common.pprint("Note it will only be effective upon next start", color='yellow')
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
            common.pprint("Iso %s not found.Leaving..." % iso, color='red')
            return {'result': 'failure', 'reason': "Iso %s not found" % iso}
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for element in list(root.getiterator('disk')):
            disktype = element.get('device')
            if disktype != 'cdrom':
                continue
            source = element.find('source')
            source.set('file', iso)
            break
        newxml = ET.tostring(root)
        conn.defineXML(newxml.decode("utf-8"))
        return {'result': 'success'}

    def update_flavor(self, name, flavor):
        common.pprint("Not implemented", color='blue')
        return {'result': 'success'}

    def remove_cloudinit(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            common.pprint("VM %s not found" % name, color='red')
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
        conn.defineXML(newxml.decode("utf-8"))

    def update_start(self, name, start=True):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if start:
            vm.setAutostart(1)
        else:
            vm.setAutostart(0)
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        conn = self.conn
        diskformat = 'qcow2'
        if size < 1:
            common.pprint("Incorrect disk size for disk %s" % name, color='red')
            return None
        if not thin:
            diskformat = 'raw'
        if pool is None:
            common.pprint("Missing Pool for disk %s" % name, color='red')
            return None
        elif '/' in pool:
            pools = [p for p in conn.listStoragePools() if self.get_pool_path(p) == pool]
            if not pools:
                common.pprint("Pool not found for disk %s" % name, color='red')
                return None
            else:
                pool = pools[0]
        else:
            try:
                pool = conn.storagePoolLookupByName(pool)
            except:
                common.pprint("Pool %s not found for disk %s" % (pool, name), color='red')
                return None
        poolxml = pool.XMLDesc(0)
        poolroot = ET.fromstring(poolxml)
        pooltype = list(poolroot.getiterator('pool'))[0].get('type')
        for element in list(poolroot.getiterator('path')):
            poolpath = element.text
            break
        if image is not None:
            volumes = {}
            for p in conn.listStoragePools():
                poo = conn.storagePoolLookupByName(p)
                for vol in poo.listAllVolumes():
                    volumes[vol.name()] = vol.path()
            if image not in volumes and image not in list(volumes.values()):
                common.pprint("Invalid image %s for disk %s" % (image, name), color='red')
                return None
            if image in volumes:
                image = volumes[image]
        pool.refresh(0)
        diskpath = "%s/%s" % (poolpath, name)
        if pooltype == 'logical':
            diskformat = 'raw'
        volxml = self._xmlvolume(path=diskpath, size=size, pooltype=pooltype,
                                 diskformat=diskformat, backing=image)
        pool.createXML(volxml, 0)
        return diskpath

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio'):
        conn = self.conn
        diskformat = 'qcow2'
        diskbus = interface
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
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        currentdisk = 0
        diskpaths = []
        virtio_index, scsi_index, ide_index = 0, 0, 0
        for element in list(root.getiterator('disk')):
            disktype = element.get('device')
            device = element.find('target').get('dev')
            imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                          element.find('source').get('volume')]
            path = next(item for item in imagefiles if item is not None)
            diskpaths.append(path)
            if disktype == 'cdrom':
                continue
            elif device.startswith('sd'):
                scsi_index += 1
            elif device.startswith('hd'):
                ide_index += 1
            else:
                virtio_index += 1
            currentdisk += 1
        diskindex = currentdisk
        if interface == 'scsi':
            diskdev = "sd%s" % string.ascii_lowercase[scsi_index]
        elif interface == 'ide':
            diskdev = "hd%s" % string.ascii_lowercase[ide_index]
        else:
            diskdev = "vd%s" % string.ascii_lowercase[virtio_index]
        if existing is None:
            storagename = "%s_%d.img" % (name, diskindex)
            diskpath = self.create_disk(name=storagename, size=size, pool=pool, thin=thin, image=image)
        elif existing in diskpaths:
            common.pprint("Disk %s already in VM %s" % (existing, name), color='blue')
            return {'result': 'success'}
        else:
            diskpath = existing
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat,
                                shareable=shareable)
        if vm.isActive() == 1:
            vm.attachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_LIVE)
            vm = conn.lookupByName(name)
            vmxml = vm.XMLDesc(0)
            conn.defineXML(vmxml)
        else:
            vm.attachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_CONFIG)
        return {'result': 'success'}

    def delete_disk_by_name(self, name, pool):
        conn = self.conn
        poolname = pool
        try:
            pool = conn.storagePoolLookupByName(pool)
        except:
            common.pprint("Pool %s not found. Leaving..." % poolname, color='red')
            return {'result': 'failure', 'reason': "Pool %s not found" % poolname}
        try:
            volume = pool.storageVolLookupByName(name)
            volume.delete()
        except:
            common.pprint("Disk %s not found in pool %s. Leaving..." % (name, poolname), color='red')
            return {'result': 'failure', 'reason': "Disk %s not found in pool %s. Leaving..." % (name, poolname)}

    def delete_disk(self, name=None, diskname=None, pool=None):
        conn = self.conn
        if name is None:
            if '_' in os.path.basename(diskname) and diskname.endswith('.img'):
                name = os.path.basename(diskname).split('_')[0]
                common.pprint("Using %s as vm associated to this disk" % name, color='blue')
            else:
                common.pprint("Couldn't find a vm associated to this disk", color='yellow')
                result = self.delete_disk_by_name(diskname, pool)
                return result
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        found = False
        missing_disks = []
        for element in list(root.getiterator('disk')):
            disktype = element.get('device')
            diskdev = element.find('target').get('dev')
            diskbus = element.find('target').get('bus')
            diskformat = element.find('driver').get('type')
            if disktype == 'cdrom':
                continue
            diskpath = element.find('source').get('file')
            try:
                volume = self.conn.storageVolLookupByPath(diskpath)
                volume.info()
            except:
                common.pprint("Disk %s was not found.Removing it from vm's definition" % diskpath, color='yellow')
                diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
                missing_disks.append(diskxml)
                continue
            if volume.name() == diskname or volume.path() == diskname or diskdev == diskname:
                diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
                vm.detachDevice(diskxml)
                volume.delete(0)
                vm = conn.lookupByName(name)
                vmxml = vm.XMLDesc(0)
                conn.defineXML(vmxml)
                found = True
        if missing_disks:
            for diskxml in missing_disks:
                vm.detachDevice(diskxml)
            vm = conn.lookupByName(name)
            vmxml = vm.XMLDesc(0)
            conn.defineXML(vmxml)
        if not found:
            common.pprint("Disk %s not found in %s" % (diskname, name), color='red')
            return {'result': 'failure', 'reason': "Disk %s not found in %s" % (diskname, name)}
        return {'result': 'success'}

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
        for interface in conn.listInterfaces():
            networks[interface] = 'bridge'
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
        for n in conn.listInterfaces():
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
        networktype, mac, source = None, None, None
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
        if networktype is None or mac is None or source is None:
            common.pprint("Interface %s not found" % interface, color='red')
            return {'result': 'failure', 'reason': "Interface %s not found" % interface}
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

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        conn = self.conn
        for pool in conn.listStoragePools():
            if pool == name:
                common.pprint("Pool %s already there.Leaving..." % name, color='blue')
                return {'result': 'success'}
        if pooltype == 'dir':
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if not os.path.exists(poolpath):
                    try:
                        os.makedirs(poolpath)
                    except OSError:
                        reason = "Couldn't create directory %s.Leaving..." % poolpath
                        common.pprint(reason, color='red')
                        return {'result': 'failure', 'reason': reason}
            elif self.protocol == 'ssh':
                cmd1 = 'ssh %s -p %s %s@%s "test -d %s || sudo mkdir %s"' % (self.identitycommand, self.port, self.user,
                                                                             self.host, poolpath, poolpath)
                cmd2 = 'ssh %s -p %s -t %s@%s "sudo chown %s %s"' % (self.identitycommand, self.port, self.user,
                                                                     self.host, user, poolpath)
                if self.user != 'root':
                    setfacl = "sudo setfacl -m u:%s:rwx %s" % (self.user, poolpath)
                    cmd3 = 'ssh %s -p %s -t %s@%s "%s"' % (self.identitycommand, self.port, self.user, self.host,
                                                           setfacl)

                return1 = os.system(cmd1)
                if return1 > 0:
                    reason = "Couldn't create directory %s.Leaving..." % poolpath
                    common.pprint(reason, color='red')
                    return {'result': 'failure', 'reason': reason}
                return2 = os.system(cmd2)
                if return2 > 0:
                    reason = "Couldn't change permission of directory %s to qemu" % poolpath
                    common.pprint(reason, color='red')
                    return {'result': 'failure', 'reason': reason}
                if self.user != 'root':
                    return3 = os.system(cmd3)
                    if return3 > 0:
                        reason = "Couldn't run setfacl for user %s in %s" % (self.user, poolpath)
                        common.pprint(reason, color='red')
                        return {'result': 'failure', 'reason': reason}
            else:
                reason = "Make sure %s directory exists on hypervisor" % name
                common.pprint(reason, color='red')
                return {'result': 'failure', 'reason': reason}
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
            reason = "Invalid pool type %s.Leaving..." % pooltype
            common.pprint(reason, color='red')
            return {'result': 'failure', 'reason': reason}
        pool = conn.storagePoolDefineXML(poolxml, 0)
        pool.setAutostart(True)
        # if pooltype == 'lvm':
        #    pool.build()
        pool.create()
        return {'result': 'success'}

    def delete_image(self, image):
        conn = self.conn
        shortname = os.path.basename(image)
        for poolname in conn.listStoragePools():
            try:
                pool = conn.storagePoolLookupByName(poolname)
                pool.refresh(0)
                volume = pool.storageVolLookupByName(shortname)
                volume.delete(0)
                return {'result': 'success'}
            except:
                continue
        return {'result': 'failure', 'reason': 'Image %s not found' % image}

    def add_image(self, image, pool, cmd=None, name=None, size=1):
        poolname = pool
        shortimage = os.path.basename(image).split('?')[0]
        shortimage_uncompressed = shortimage.replace('.gz', '').replace('.xz', '').replace('.bz2', '')
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
        if shortimage_uncompressed in volumes:
            common.pprint("Image %s already there.Leaving..." % shortimage_uncompressed, color="blue")
            return {'result': 'success'}
        if name == 'rhcos42':
            shortimage += '.gz'
        if self.host == 'localhost' or self.host == '127.0.0.1':
            downloadcmd = "curl -Lo %s/%s -f '%s'" % (downloadpath, shortimage, image)
        elif self.protocol == 'ssh':
            downloadcmd = 'ssh %s -p %s %s@%s "curl -Lo %s/%s -f \'%s\'"' % (self.identitycommand, self.port, self.user,
                                                                             self.host, downloadpath, shortimage, image)
        code = call(downloadcmd, shell=True)
        if code == 23:
            common.pprint("Consider running the following command on the hypervisor:", color="blue")
            setfacluser = self.user
            if self.host in ['localhost', '127.0.0.1']:
                if not os.path.exists("/i_am_a_container"):
                    setfacluser = getpwuid(os.getuid()).pw_name
                else:
                    setfacluser = "your_user"
            common.pprint("sudo setfacl -m u:%s:rwx %s" % (setfacluser, downloadpath), color="blue")
            return {'result': 'failure', 'reason': "of Permission issues"}
        elif code != 0:
            return {'result': 'failure', 'reason': "Unable to download indicated image"}
        if shortimage.endswith('xz') or shortimage.endswith('gz') or shortimage.endswith('bz2') or name == 'rhcos42':
            executable = {'xz': 'unxz', 'gz': 'gunzip', 'bz2': 'bunzip2'}
            extension = os.path.splitext(shortimage)[1].replace('.', '')
            executable = executable[extension] if name != 'rhcos42' else 'gunzip'
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if find_executable(executable) is not None:
                    uncompresscmd = "%s %s/%s" % (executable, poolpath, shortimage)
                    os.system(uncompresscmd)
                else:
                    common.pprint("%s not found. Can't uncompress image" % executable, color="red")
                    return {'result': 'failure', 'reason': "%snot found. Can't uncompress image" % executable}
            elif self.protocol == 'ssh':
                uncompresscmd = 'ssh %s -p %s %s@%s "%s %s/%s"' % (self.identitycommand, self.port, self.user,
                                                                   self.host, executable, poolpath, shortimage)
                os.system(uncompresscmd)
        if cmd is not None:
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if find_executable('virt-customize') is not None:
                    cmd = "virt-customize -a %s/%s --run-command '%s'" % (poolpath, shortimage_uncompressed, cmd)
                    os.system(cmd)
            elif self.protocol == 'ssh':
                cmd = 'ssh %s -p %s %s@%s "virt-customize -a %s/%s --run-command \'%s\'"' % (self.identitycommand,
                                                                                             self.port, self.user,
                                                                                             self.host, poolpath,
                                                                                             shortimage_uncompressed,
                                                                                             cmd)
                os.system(cmd)
        if pooltype in ['logical', 'zfs']:
            product = list(root.getiterator('product'))
            if product:
                thinpool = list(root.getiterator('product'))[0].get('name')
            else:
                thinpool = None
            self.add_image_to_deadpool(poolname, pooltype, poolpath, shortimage_uncompressed, thinpool)
            return {'result': 'success'}
        pool.refresh()
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        conn = self.conn
        networks = self.list_networks()
        if name in networks:
            common.pprint("Network %s already exists" % name, color='blue')
            return {'result': 'exist'}
        if 'macvtap' in overrides and overrides['macvtap']:
            if 'nic' not in overrides:
                return {'result': 'failure', 'reason': "Missing nic parameter"}
            else:
                nic = overrides['nic']
                networkxml = """<network>
                                <name>%s</name>
                                <forward mode="bridge">
                                <interface dev="%s"/>
                                </forward>
                                </network>""" % (name, nic)
                new_net = conn.networkDefineXML(networkxml)
                new_net.setAutostart(True)
                new_net.create()
                return {'result': 'success'}
        if cidr is None:
            return {'result': 'failure', 'reason': "Missing Cidr"}
        cidrs = [network['cidr'] for network in list(networks.values())]
        try:
            range = IPNetwork(cidr)
        except:
            return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
        if IPNetwork(cidr) in cidrs:
            return {'result': 'failure', 'reason': "Cidr %s already exists" % cidr}
        gateway = str(range[1])
        family = 'ipv6' if ':' in gateway else 'ipv4'
        if dhcp:
            start = str(range[2])
            end = str(range[-2]) if family == 'ipv4' else str(range[1000])
            dhcpxml = """<dhcp>
                    <range start='%s' end='%s'/>""" % (start, end)
            if 'pxe' in overrides:
                pxe = overrides['pxe']
                dhcpxml = """%s
                          <bootp file='pxelinux.0' server='%s'/>""" % (dhcpxml, pxe)
            dhcpxml = "%s</dhcp>" % dhcpxml
        else:
            dhcpxml = ''
        if nat:
            natxml = "<forward mode='nat'><nat><port start='1024' end='65535'/></nat></forward>"
        elif dhcp:
            natxml = "<forward mode='route'></forward>"
        else:
            natxml = ''
        if domain is not None:
            domainxml = "<domain name='%s'/>" % domain
        else:
            domainxml = "<domain name='%s'/>" % name
        bridgexml = "<bridge name='%s' stp='on' delay='0'/>" % name if len(name) < 16 else ''
        cidr = cidr.split('/')[1]
        metadata = """<metadata>
        <kvirt:info xmlns:kvirt="kvirt">
        <kvirt:plan>%s</kvirt:plan>
        </kvirt:info>
        </metadata>""" % plan
        networkxml = """<network><name>%s</name>
                    %s
                    %s
                    %s
                    %s
                    <ip address='%s' prefix='%s' family='%s'>
                    %s
                    </ip>
                    </network>""" % (name, metadata, natxml, bridgexml, domainxml, gateway, cidr, family, dhcpxml)
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
                netmask = attributes.get('prefix') if netmask is None else netmask
                ipnet = '%s/%s' % (firstip, netmask) if netmask is not None else firstip
                ipnet = IPNetwork(ipnet)
                cidr = ipnet.cidr
            else:
                ip = None
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
            # if ip is not None:
            #    networks[networkname]['ip'] = ip
            plan = 'N/A'
            for element in list(root.getiterator('{kvirt}info')):
                e = element.find('{kvirt}plan')
                if e is not None:
                    plan = e.text
            networks[networkname]['plan'] = plan
        for interface in conn.listInterfaces():
            if interface == 'lo' or interface in networks:
                continue
            netxml = conn.interfaceLookupByName(interface).XMLDesc(0)
            root = ET.fromstring(netxml)
            bridge = list(root.getiterator('bridge'))
            if not bridge:
                continue
            ip = list(root.getiterator('ip'))
            if ip:
                attributes = ip[0].attrib
                ip = attributes.get('address')
                prefix = attributes.get('prefix')
                ipnet = IPNetwork('%s/%s' % (ip, prefix))
                cidr = ipnet.cidr
            else:
                ip = None
                cidr = 'N/A'
            networks[interface] = {'cidr': cidr, 'dhcp': 'N/A', 'type': 'bridged', 'mode': 'N/A'}
            if ip is not None:
                networks[interface]['ip'] = ip
            plan = 'N/A'
            for element in list(root.getiterator('{kvirt}info')):
                e = element.find('{kvirt}plan')
                if e is not None:
                    plan = e.text
            networks[interface]['plan'] = plan
        return networks

    def list_subnets(self):
        common.pprint("not implemented", color='blue')
        return {}

    def delete_pool(self, name, full=False):
        conn = self.conn
        try:
            pool = conn.storagePoolLookupByName(name)
        except:
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
        bridges = [interface for interface in conn.listInterfaces()]
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

    def thinimages(self, path, thinpool):
        thincommand = ("lvs -o lv_name  %s -S 'lv_attr =~ ^V && origin = \"\" && pool_lv = \"%s\"'  --noheadings"
                       % (path, thinpool))
        if self.protocol == 'ssh':
            thincommand = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host,
                                                         thincommand)
        results = os.popen(thincommand).read().strip()
        if results == '':
            return []
        return [name.strip() for name in results.split('\n')]

    def _fixqcow2(self, path, backing):
        command = "qemu-img create -q -f qcow2 -b %s -F qcow2 %s" % (backing, path)
        if self.protocol == 'ssh':
            command = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host, command)
        os.system(command)

    def add_image_to_deadpool(self, poolname, pooltype, poolpath, shortimage, thinpool=None):
        sizecommand = "qemu-img info /tmp/%s --output=json" % shortimage
        if self.protocol == 'ssh':
            sizecommand = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host,
                                                         sizecommand)
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
            command = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host, command)
        os.system(command)

    def _createthinlvm(self, name, path, thinpool, backing=None, size=None):
        if backing is not None:
            command = "lvcreate -qq -ay -K -s --name %s %s/%s" % (name, path, backing)
        else:
            command = "lvcreate -qq -V %sG -T %s/%s -n %s" % (size, path, thinpool, name)
        if self.protocol == 'ssh':
            command = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host, command)
        os.system(command)

    def _deletelvm(self, disk):
        command = "lvremove -qqy %s" % disk
        if self.protocol == 'ssh':
            command = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host, command)
        os.system(command)

    def export(self, name, image=None):
        newname = image if image is not None else "image-%s" % name
        conn = self.conn
        oldvm = conn.lookupByName(name)
        oldxml = oldvm.XMLDesc(0)
        tree = ET.fromstring(oldxml)
        for disk in list(tree.getiterator('disk')):
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
            newpath = oldpath.replace(name, newname).replace('.img', '.qcow2')
            source.set('file', newpath)
            newvolumexml = self._xmlvolume(newpath, oldvolumesize, backing=backing)
            pool.createXMLFrom(newvolumexml, oldvolume, 0)
            break
        return {'result': 'success'}

    def _create_host_entry(self, name, ip, netname, domain, dnsmasq=False):
        hosts = "%s %s %s.%s" % (ip, name, name, netname)
        if domain is not None and domain != netname:
            hosts = "%s %s.%s" % (hosts, name, domain)
        hosts = '"%s # KVIRT"' % hosts
        oldentry = "%s %s.* # KVIRT" % (ip, name)
        for line in open('/etc/hosts'):
            if re.findall(oldentry, line):
                common.pprint("Old entry found.Leaving...", color='yellow')
                return
        if not dnsmasq:
            hostscmd = "sh -c 'echo %s >>/etc/hosts'" % hosts
        else:
            hostscmd = "sh -c 'echo %s >>/etc/hosts'" % hosts.replace('"', '\\"')
        common.pprint("Creating hosts entry. Password for sudo might be asked", color='blue')
        if not dnsmasq or self.user != 'root':
            hostscmd = "sudo %s" % hostscmd
        elif self.protocol == 'ssh' and self.host not in ['localhost', '127.0.0.1']:
            hostscmd = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host, hostscmd)
        call(hostscmd, shell=True)
        if dnsmasq:
            dnsmasqcmd = "/usr/bin/systemctl restart dnsmasq"
            if self.user != 'root':
                dnsmasqcmd = "sudo %s" % dnsmasqcmd
            dnsmasqcmd = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host,
                                                        dnsmasqcmd)
            call(dnsmasqcmd, shell=True)

    def delete_dns(self, name, domain):
        conn = self.conn
        try:
            network = conn.networkLookupByName(domain)
        except:
            common.pprint("Network %s not found" % domain)
            return
        netxml = network.XMLDesc()
        netroot = ET.fromstring(netxml)
        for host in list(netroot.getiterator('host')):
            iphost = host.get('ip')
            for host in list(netroot.getiterator('host')):
                iphost = host.get('ip')
                hostname = host.find('hostname')
                if hostname is not None and hostname.text == name:
                    hostentry = '<host ip="%s"><hostname>%s</hostname></host>' % (iphost, name)
                    network.update(2, 10, 0, hostentry, 1)
                return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        conn = self.conn
        try:
            network = conn.networkLookupByName(domain)
        except:
            return {'result': 'failure', 'reason': "Network %s not found" % domain}
        netxml = network.XMLDesc()
        netroot = ET.fromstring(netxml)
        for host in list(netroot.getiterator('host')):
            iphost = host.get('ip')
            for host in list(netroot.getiterator('host')):
                iphost = host.get('ip')
                hostname = host.find('hostname')
                results.append([hostname.text, 'A', '0', iphost])
        return results
