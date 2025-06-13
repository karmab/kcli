# -*- coding: utf-8 -*-

from getpass import getuser
from kvirt.defaults import IMAGES, METADATA_FIELDS, UBUNTUS
from kvirt import common
from kvirt.common import error, pprint, warning, get_ssh_pub_key, success
from kvirt.providers.kvm.helpers import DHCPKEYWORDS
from ipaddress import ip_address, ip_network
from libvirt import open as libvirtopen, registerErrorHandler, libvirtError
from libvirt import VIR_DOMAIN_AFFECT_LIVE, VIR_DOMAIN_AFFECT_CONFIG
from libvirt import VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT as vir_src_agent
from libvirt import VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE as vir_src_lease
from libvirt import (VIR_DOMAIN_NOSTATE, VIR_DOMAIN_RUNNING, VIR_DOMAIN_BLOCKED, VIR_DOMAIN_PAUSED,
                     VIR_DOMAIN_SHUTDOWN, VIR_DOMAIN_SHUTOFF, VIR_DOMAIN_CRASHED)
from libvirt import VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE
from libvirt import VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY, VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC
from libvirt import VIR_DOMAIN_BLOCK_COMMIT_ACTIVE, VIR_DOMAIN_BLOCK_JOB_ABORT_PIVOT
try:
    from libvirt import VIR_DOMAIN_UNDEFINE_KEEP_NVRAM
except:
    pass
from pwd import getpwuid
import json
import os
from subprocess import call
import re
import string
import sys
from shutil import which
from tempfile import TemporaryDirectory
import time
from uuid import UUID
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

KiB = 1024
MiB = 1024 * KiB
GiB = 1024 * MiB
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
    return


registerErrorHandler(f=libvirt_callback, ctx=None)


class Kvirt(object):
    def __init__(self, host='127.0.0.1', port=None, user='root', protocol='ssh', url=None, debug=False, insecure=False,
                 session=False, legacy=False):
        if url is None:
            connectiontype = 'system' if not session else 'session'
            if host == '127.0.0.1' or host == 'localhost':
                url = f"qemu:///{connectiontype}"
                if os.path.exists("/i_am_a_container") and not os.path.exists('/var/run/libvirt'):
                    error("You need to add -v /var/run/libvirt:/var/run/libvirt to container alias")
                    self.conn = None
                    return
            elif protocol == 'ssh':
                if port != 22:
                    url = f"qemu+{protocol}://{user}@{host}:{port}/{connectiontype}"
                else:
                    url = f"qemu+{protocol}://{user}@{host}/{connectiontype}"
            elif port:
                url = f"qemu+{protocol}://{user}@{host}:{port}/{connectiontype}"
            else:
                url = f"qemu:///{connectiontype}"
            if url.startswith('qemu+ssh'):
                url = f"{url}?no_verify=1"
                publickeyfile = get_ssh_pub_key()
                if publickeyfile is not None:
                    privkeyfile = publickeyfile.replace('.pub', '')
                    url = f"{url}&keyfile={privkeyfile}"
                if legacy:
                    url += '&socket=/var/run/libvirt/libvirt-sock'
            elif os.path.exists("/i_am_a_container"):
                socketdir = '/var/run/libvirt' if not session else f'/home/{user}/.cache/libvirt'
                url += f"?socket={socketdir}/libvirt-sock"
        try:
            self.conn = libvirtopen(url)
            self.debug = debug
        except Exception as e:
            error(e)
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
        elif os.path.exists(os.path.expanduser("~/.kcli/id_dsa")):
            identityfile = os.path.expanduser("~/.kcli/id_dsa")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_ed25519")):
            identityfile = os.path.expanduser("~/.kcli/id_ed25519")
        elif os.path.exists(os.path.expanduser("~/.ssh/id_rsa")):
            identityfile = os.path.expanduser("~/.ssh/id_rsa")
        elif os.path.exists(os.path.expanduser("~/.ssh/id_dsa")):
            identityfile = os.path.expanduser("~/.ssh/id_dsa")
        elif os.path.exists(os.path.expanduser("~/.ssh/id_ed25519")):
            identityfile = os.path.expanduser("~/.ssh/id_ed25519")
        if identityfile is not None:
            self.identitycommand = f"-i {identityfile}"
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

    def get_capabilities(self, arch=None):
        results = {'kvm': False, 'nestedfeature': None, 'machines': [], 'arch': arch}
        capabilitiesxml = self.conn.getCapabilities()
        root = ET.fromstring(capabilitiesxml)
        cpuxml = ''
        if arch is None:
            host = root.find('host')
            cpu = host.find('cpu')
            try:
                cpuxml = self.conn.baselineCPU([ET.tostring(cpu, encoding='unicode')], 1)
            except:
                pass
            arch = cpu.find('arch').text
            results['arch'] = arch
        for guest in list(root.iter('guest')):
            currentarch = guest.find('arch')
            if currentarch.get('name') != arch:
                continue
            results['emulator'] = currentarch.find('emulator').text
            for domain in list(guest.iter('domain')):
                if domain.get('type') == 'kvm':
                    results['kvm'] = True
                    break
            for machine in list(guest.iter('machine')):
                results['machines'].append(machine.text)
        if 'vmx' in cpuxml:
            results['nestedfeature'] = 'vmx'
        elif 'svm' in cpuxml:
            results['nestedfeature'] = 'svm'
        return results

    def create(self, name, virttype=None, profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[],
               cmdline=None, placement=[], autostart=False, cpuhotplug=False,
               memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={},
               securitygroups=[], vmuser=None, guestagent=True):
        bootdev = 1
        namespace = ''
        ignition = False
        usermode = False
        macosx = False
        diskpath = None
        qemuextra = overrides.get('qemuextra')
        enableiommu = overrides.get('iommu', False)
        needs_ignition = image is not None and (common.needs_ignition(image) or 'ignition_file' in overrides)
        iommuxml = ""
        ioapicxml = ""
        if 'session' in self.url:
            usermode = True
            userport = common.get_free_port()
            metadata['ip'] = userport
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        conn = self.conn
        custom_emulator = overrides.get('emulator')
        default_arch = overrides.get('arch')
        arch = default_arch
        if custom_emulator is not None and custom_emulator.endswith('aarch64'):
            arch = 'aarch64'
            pprint(f"Using arch {arch} as per custom emulator suffix")
        capabilities = self.get_capabilities(arch)
        arch = arch or capabilities['arch']
        if custom_emulator is not None:
            if os.path.exists(custom_emulator):
                emulator = custom_emulator
            elif which(custom_emulator) is None:
                return {'result': 'failure', 'reason': f"Emulator {custom_emulator} not found in your path"}
            else:
                emulator = which(custom_emulator)
        elif 'emulator' not in capabilities:
            return {'result': 'failure', 'reason': f"No valid emulator found for target arch {arch}"}
        else:
            emulator = capabilities['emulator']
            if 'machine' in overrides and overrides['machine'] not in capabilities['machines']:
                machines = ','.join(sorted(capabilities['machines']))
                return {'result': 'failure', 'reason': f"Incorrect machine. Choose between {machines}"}
        uefi_firmware = overrides.get('uefi_firmware')
        uefi_nvtemplate = overrides.get('uefi_nvtemplate')
        uefi = overrides.get('uefi', False) or uefi_firmware is not None or uefi_nvtemplate is not None
        uefi_legacy = overrides.get('uefi_legacy', False) or (uefi and self._rhel_legacy(capabilities['machines']))
        iommu_model = 'smmuv3' if arch == 'aarch64' else 'intel'
        aarch64 = arch == 'aarch64'
        aarch64_full = aarch64 and capabilities['kvm']
        as390x = arch == 's390x'
        if aarch64:
            if custom_emulator is not None:
                warning("Not checking whether a valid machine is provided")
            elif 'machine' not in overrides:
                virtmachines = [m for m in sorted(capabilities['machines']) if m.startswith('virt-')]
                if not virtmachines:
                    return {'result': 'failure', 'reason': "Couldn't find a valid machine"}
                else:
                    warning(f"Using machine {virtmachines[-1]}")
                    overrides['machine'] = virtmachines[-1]
        if aarch64_full and not uefi and not uefi_legacy:
            warning("Forcing uefi")
            uefi = True
        try:
            default_storagepool = conn.storagePoolLookupByName(default_pool)
        except:
            return {'result': 'failure', 'reason': f"Pool {default_pool} not found"}
        creationdate = time.strftime("%d-%m-%Y %H:%M", time.gmtime())
        metadata['creationdate'] = creationdate
        metadataxml = """<metadata>
<kvirt:info xmlns:kvirt="kvirt">
<kvirt:creationdate>%s</kvirt:creationdate>""" % creationdate
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            metadataxml += f"\n<kvirt:{entry}>{metadata[entry]}</kvirt:{entry}>"
        default_poolxml = default_storagepool.XMLDesc(0)
        root = ET.fromstring(default_poolxml)
        default_pooltype = list(root.iter('pool'))[0].get('type')
        default_poolpath = None
        product = list(root.iter('product'))
        if product:
            default_thinpool = list(root.iter('product'))[0].get('name')
        else:
            default_thinpool = None
        for element in root.iter('path'):
            default_poolpath = element.text
            break
        volumes = {}
        volumespaths = {}
        for poo in conn.listAllStoragePools(VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE):
            try:
                poo.refresh(0)
            except Exception as e:
                warning(f"Hit {e} when refreshing pool {poo.name()}")
                pass
            for vol in poo.listAllVolumes():
                volumes[vol.name()] = {'pool': poo, 'object': vol}
                volumespaths[vol.path()] = {'pool': poo, 'object': vol}
        allnetworks = self.list_networks()
        bridges = []
        forward_bridges = []
        networks = []
        ovsnetworks = []
        nics = []
        ipv6networks = []
        for n in allnetworks:
            if allnetworks[n]['type'] == 'bridged':
                bridges.append(n)
            elif allnetworks[n]['type'] == 'ovs':
                ovsnetworks.append(n)
            elif allnetworks[n]['type'] == 'nic':
                nics.append(n)
            else:
                networks.append(n)
                if allnetworks[n]['mode'] == 'bridge':
                    forward_bridges.append(n)
            if ':' in allnetworks[n]['cidr']:
                ipv6networks.append(n)
        ipv6 = []
        machine = 'pc'
        if 'machine' in overrides:
            machine = overrides['machine']
        secureboot = overrides.get('secureboot', False)
        if machine == 'pc' and (uefi or uefi_legacy or secureboot or aarch64 or enableiommu):
            machine = 'q35'
        if as390x:
            machine = 's390-ccw-virtio'
        disksxml = ''
        fixqcow2path, fixqcow2backing = None, None
        volsxml = {}
        virtio_index, ide_index, scsi_index = 0, 0, 0
        boot_order = overrides.get('boot_order', False)
        bootxml = "<boot dev='hd'/><boot dev='cdrom'/><boot dev='network'/>" if not boot_order else ''
        firstdisk = None
        nvmedisks = []
        for index, disk in enumerate(disks):
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
            nvme = False
            ssd = False
            dextra = ''
            diskserial = None
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str):
                if disk.isdigit():
                    disksize = int(disk)
                else:
                    diskname = disk
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskthin = disk.get('thin', default_diskthin)
                diskinterface = disk.get('interface', default_diskinterface)
                if diskinterface == 'nvme':
                    diskinterface = default_diskinterface
                    if index == 0:
                        warning("Nvme on primary disk is not supported. Skipping")
                    else:
                        nvme = True
                if diskinterface == 'ssd':
                    diskinterface = 'sata'
                    ssd = True
                diskpool = disk.get('pool', default_pool)
                diskwwn = disk.get('wwn')
                diskserial = disk.get('serial')
                diskimage = disk.get('image')
                diskname = disk.get('name')
                diskmacosx = disk.get('macosx', False)
                dextra = disk.get('driver_extra', '')
                try:
                    storagediskpool = conn.storagePoolLookupByName(diskpool)
                except:
                    return {'result': 'failure', 'reason': f"Pool {diskpool} not found"}
                diskpoolxml = storagediskpool.XMLDesc(0)
                root = ET.fromstring(diskpoolxml)
                diskpooltype = list(root.iter('pool'))[0].get('type')
                diskpoolpath = None
                for element in list(root.iter('path')):
                    diskpoolpath = element.text
                    break
                product = list(root.iter('product'))
                if product:
                    diskthinpool = list(root.iter('product'))[0].get('name')
                else:
                    diskthinpool = None
            else:
                return {'result': 'failure', 'reason': "Invalid disk entry"}
            diskbus = diskinterface
            if diskinterface == 'ide':
                ide_letter = chr(ide_index + ord('a'))
                diskdev = f'hd{ide_letter}'
                ide_index += 1
            elif diskinterface in ['scsi', 'sata']:
                scsi_letter = chr(scsi_index + ord('a'))
                diskdev = f'sd{scsi_letter}'
                scsi_index += 1
            else:
                virtio_letter = chr(virtio_index + ord('a'))
                diskdev = f'vd{virtio_letter}'
                virtio_index += 1
            diskformat = 'qcow2'
            if not diskthin:
                diskformat = 'raw'
            storagename = f"{name}_{index}.img" if diskname is None else diskname
            diskpath = f"{diskpoolpath}/{storagename}"
            if image is not None and index == 0:
                diskimage = image
                firstdisk = diskpath
            if diskimage is not None:
                if index != 0 and diskimage.endswith('qcow2'):
                    image = diskimage
                manual_disk_path = False
                try:
                    if diskthinpool is not None:
                        matchingthinimages = self.thinimages(diskpoolpath, diskthinpool)
                        if diskimage not in matchingthinimages:
                            raise NameError('No Image found')
                    else:
                        default_storagepool.refresh(0)
                        if '/' in diskimage:
                            backingvolume = volumespaths[diskimage]['object']
                        else:
                            backingvolume = volumes[diskimage]['object']
                        backingxml = backingvolume.XMLDesc(0)
                        root = ET.fromstring(backingxml)
                except:
                    if self.host in ['localhost', '127.0.0.1'] and os.path.exists(diskimage):
                        warning("Using image path although it's not in a pool")
                        manual_disk_path = True
                        backing = os.path.abspath(diskimage)
                        backingxml = """<backingStore type='file' index='1'>
<format type='qcow2'/>
<source file='%s'/>
</backingStore>""" % backing
                    else:
                        shortname = [t for t in IMAGES if IMAGES[t] == diskimage]
                        if shortname:
                            msg = f"you don't have image {diskimage}. Use kcli download {shortname[0]}"
                        else:
                            msg = f"you don't have image {diskimage}"
                        return {'result': 'failure', 'reason': msg}
                if diskthinpool is not None:
                    backing = None
                    backingxml = '<backingStore/>'
                elif not manual_disk_path:
                    backing = backingvolume.path()
                    if backing.startswith('/dev'):
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
                warning("Raw disks don't support a backing, so using thin mode instead")
            owner = '107' if nvme else None
            volxml = self._xmlvolume(path=diskpath, size=disksize, pooltype=diskpooltype, backing=backing,
                                     diskformat=diskformat, owner=owner)
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
                pprint(f"Using existing disk {storagename}...")
                if diskmacosx or diskname in ['BaseSystem.img', 'OpenCore.qcow2']:
                    macosx = True
                    machine = 'q35'
            if diskwwn is None:
                diskwwn = ''
            elif diskbus not in ['ide', 'scsi']:
                msg = f"Not setting disk wwn as disk uses {diskbus}"
                return {'result': 'failure', 'reason': msg}
            else:
                diskwwn = f"<wwn>{diskwwn}</wwn>"
            diskserial = f'<serial>{diskserial}</serial>' if diskserial is not None else ''
            dtype = 'block' if diskpath.startswith('/dev') else 'file'
            dsource = 'dev' if diskpath.startswith('/dev') else 'file'
            if diskpooltype in ['logical', 'zfs'] and (backing is None or backing.startswith('/dev')):
                diskformat = 'raw'
            if not nvme:
                bootdevxml = f'<boot order="{bootdev}"/>' if boot_order else ''
                bootdev += 1
                ssdxml = "rotation_rate='1'" if ssd else ''
                if diskinterface in ['scsi', 'sata']:
                    addressxml = f"<address type='drive' controller='0' bus='0' target='0' unit='{scsi_index}'/>"
                else:
                    addressxml = ''
                disksxml = """%s<disk type='%s' device='disk'>
<driver name='qemu' type='%s' %s/>
<source %s='%s'/>
%s
<target dev='%s' bus='%s' %s/>
%s
%s
%s
%s
</disk>""" % (disksxml, dtype, diskformat, dextra, dsource, diskpath, backingxml, diskdev, diskbus, ssdxml, diskwwn,
                    diskserial, bootdevxml, addressxml)
            else:
                nvmedisks.append(diskpath)
        if iso is not None:
            if os.path.exists(iso):
                iso = os.path.abspath(iso)
            if os.path.isabs(iso):
                if self.protocol == 'ssh' and self.host not in ['localhost', '127.0.0.1']:
                    isocheckcmd = 'ssh %s -p %s %s@%s "ls %s >/dev/null 2>&1"' % (self.identitycommand, self.port,
                                                                                  self.user, self.host, iso)
                    code = os.system(isocheckcmd)
                    if code != 0:
                        if start:
                            return {'result': 'failure', 'reason': f"Iso {iso} not found"}
                        else:
                            warning(f"Iso {iso} not found. Make sure it's there before booting")
                elif not os.path.exists(iso):
                    if start:
                        return {'result': 'failure', 'reason': f"Iso {iso} not found"}
                    else:
                        warning(f"Iso {iso} not found. Make sure it's there before booting")
            else:
                if iso not in volumes:
                    if 'http' in iso:
                        if os.path.basename(iso) in volumes:
                            self.delete_image(os.path.basename(iso))
                        pprint(f"Trying to gather {iso}")
                        self.add_image(iso, pool=default_pool)
                        conn.storagePoolLookupByName(default_pool).refresh()
                        iso = f"{default_poolpath}/{os.path.basename(iso)}"
                    elif start:
                        return {'result': 'failure', 'reason': f"Iso {iso} not found"}
                    else:
                        warning(f"Iso {iso} not found. Make sure it's there before booting")
                        iso = f"{default_poolpath}/{iso}"
                        warning(f"Setting iso full path to {iso}")
                else:
                    isovolume = volumes[iso]['object']
                    iso = isovolume.path()
        isobus = 'scsi' if (aarch64_full or as390x) else 'sata'
        isosourcexml = f"<source file='{iso}'/>" if iso is not None else ''
        bootdevxml = f'<boot order="{bootdev}"/>' if boot_order else ''
        bootdev_iso = bootdev
        bootdev += 1
        isoxml = """<disk type='file' device='cdrom'>
<driver name='qemu' type='raw'/>%s
<target dev='hdc' bus='%s'/>
<readonly/>
%s
<address type='drive' controller='0' bus='0' target='0' unit='0'/>
</disk>
<controller type='scsi' index='0' model='virtio-scsi'>
<alias name='scsi0'/>
</controller>""" % (isosourcexml, isobus, bootdevxml)
        extraisoxml = ''
        extra_iso = overrides.get('extra_iso')
        if iso is not None and extra_iso is not None:
            if extra_iso not in volumes:
                if 'http' in extra_iso:
                    if os.path.basename(extra_iso) in volumes:
                        self.delete_image(os.path.basename(extra_iso))
                    pprint(f"Trying to gather {extra_iso}")
                    self.add_image(extra_iso, pool=default_pool)
                    conn.storagePoolLookupByName(default_pool).refresh()
                    floppy = f"{default_poolpath}/{os.path.basename(extra_iso)}"
                elif not extra_iso.startswith('/'):
                    return {'result': 'failure', 'reason': f"Extra iso {extra_iso} not found"}
            else:
                extra_iso_volume = volumes[extra_iso]['object']
                extra_iso = extra_iso_volume.path()
            extraisoxml = """  <disk type='file' device='cdrom'>
<driver name='qemu' type='raw'/>
<source file='%s'/>
<target dev='hde' bus='%s'/>
<address type='drive' controller='0' bus='0' target='0' unit='%s'/>
</disk>""" % (extra_iso, isobus, scsi_index + 1)
        floppyxml = ''
        floppy = overrides.get('floppy')
        if floppy is not None:
            if floppy not in volumes:
                if 'http' in floppy:
                    if os.path.basename(floppy) in volumes:
                        self.delete_image(os.path.basename(floppy))
                    pprint(f"Trying to gather {floppy}")
                    self.add_image(floppy, pool=default_pool)
                    conn.storagePoolLookupByName(default_pool).refresh()
                    floppy = f"{default_poolpath}/{os.path.basename(floppy)}"
                elif not floppy.startswith('/'):
                    return {'result': 'failure', 'reason': f"Floppy {floppy} not found"}
            else:
                floppyvolume = volumes[floppy]['object']
                floppy = floppyvolume.path()
            floppyxml = """  <disk type='file' device='floppy'>
<source file='%s'/>
<target dev='fda' bus='fdc'/>
</disk>""" % floppy
        expanderinfo = {}
        for index, cell in enumerate(numa):
            if not isinstance(cell, dict) or 'id' not in cell:
                msg = f"Can't process entry {index} in numa block"
                return {'result': 'failure', 'reason': msg}
            else:
                _id = cell['id']
                matchingnics = [nic for nic in nets if isinstance(nic, dict) and 'numa' in nic and nic['numa'] == _id]
                vfio = [nic for nic in matchingnics if 'vfio' in nic and nic['vfio']]
                sriov = [nic for nic in matchingnics if 'sriov' in nic and nic['sriov']]
                if 'machine' not in overrides and (vfio or sriov):
                    machine = 'q35'
                    warning(f"Forcing machine type to {machine}")
                newindex = 1
                if expanderinfo:
                    for key in expanderinfo:
                        newindex += expanderinfo[key]['slots']
                    newindex += len(expanderinfo)
                expanderinfo[_id] = {'index': newindex, 'slots': len(matchingnics)}
        netxml = ''
        nicslots = {k: 0 for k in range(0, 20)}
        alias = []
        vhostindex = 0
        need_guestagent = False
        sriov_nic = False
        default_netmask = overrides.get('netmask') or overrides.get('prefix')
        default_gateway = overrides.get('gateway')
        default_dns = overrides.get('dns')
        for index, net in enumerate(nets):
            if usermode:
                continue
            ovs = False
            nicnuma = None
            macxml = ''
            ovsxml = ''
            mtuxml = ''
            multiqueuexml = ''
            nettype = 'virtio'
            vhost = False
            filterxml = ''
            if isinstance(net, str):
                netname = net
                nets[index] = {'name': netname}
            elif isinstance(net, dict):
                netname = net.get('name', 'default')
                if net.get('sriov', False):
                    nets[index]['type'] = 'igb'
                    nets[index]['vfio'] = True
                    nets[index]['noconf'] = True
                    sriov_nic = True
                if 'mac' in nets[index]:
                    mac = nets[index]['mac']
                    macxml = f"<mac address='{mac}'/>"
                if 'type' in nets[index]:
                    nettype = nets[index]['type']
                if index == 0 and 'alias' in nets[index] and isinstance(nets[index]['alias'], list):
                    reservedns = True
                    alias = nets[index]['alias']
                if 'ovs' in nets[index] and nets[index]['ovs']:
                    ovs = True
                if 'ip' in nets[index] and index == 0:
                    metadataxml += f"<kvirt:ip >{nets[index]['ip']}</kvirt:ip>"
                    ip = nets[index].get('ip')
                    netmask = net.get('mask') or net.get('netmask') or net.get('prefix') or default_netmask
                    gateway = nets[index].get('gateway') or default_gateway
                    nameserver = nets[index].get('dns') or default_dns or gateway
                    nic = nets[index].get('nic', 'ens3')
                    if needs_ignition and ip is not None and netmask is not None and gateway is not None:
                        nameservers = [nameserver] if isinstance(nameserver, str) else nameserver
                        nameservers = ' '.join([f"nameserver={name}" for name in nameservers])
                        warning("Injecting static networking via cmdline")
                        cmdline = f'ip={ip}::{gateway}:{netmask}::{nic}:none {nameservers}'
                        del nets[index]['ip']
                if 'numa' in nets[index] and numa:
                    nicnuma = nets[index]['numa']
                if 'filter' in nets[index]:
                    filterref = nets[index]['filter']
                    filterxml = f'<filterref filter="{filterref}"/>'
                if 'vhost' in nets[index] and nets[index]['vhost']:
                    vhost = True
                if 'mtu' in nets[index]:
                    mtuxml = f"<mtu size='{nets[index]['mtu']}'/>"
                if 'vfio' in nets[index] and nets[index]['vfio']:
                    iommuxml = f"<iommu model='{iommu_model}'/>"
                if 'multiqueues' in nets[index]:
                    multiqueues = nets[index]['multiqueues']
                    if not isinstance(multiqueues, int):
                        return {'result': 'failure',
                                'reason': f"Invalid multiqueues value in nic {index}. Must be an int"}
                    elif not 0 < multiqueues < 257:
                        return {'result': 'failure',
                                'reason': f"multiqueues value in nic {index} not between 0 and 256 "}
                    else:
                        multiqueuexml = f"<driver name='vhost' queues='{multiqueues}'/>"
            if ips and len(ips) > index and ips[index] is not None and\
                    netmasks and len(netmasks) > index and netmasks[index] is not None and gateway is not None:
                nets[index]['ip'] = ips[index]
                nets[index]['netmask'] = netmasks[index]
            if netname in ovsnetworks:
                ovs = True
            if netname in networks:
                iftype = 'network'
                sourcexml = f"<source network='{netname}'/>"
                if netname in forward_bridges:
                    need_guestagent = True
                if index == 0 and not allnetworks[netname]['dhcp']:
                    metadataxml += "\n<kvirt:nodhcp>True</kvirt:nodhcp>"
            elif netname in bridges or ovs:
                if netname in bridges and 'ip' in allnetworks[netname] and 'config_host' not in overrides:
                    overrides['config_host'] = allnetworks[netname]['ip']
                iftype = 'bridge'
                sourcexml = f"<source bridge='{netname}'/>"
                need_guestagent = True
                if reservedns and index == 0 and dns is not None:
                    dnscmd = f"sed -i 's/nameserver .*/nameserver {dns}/' /etc/resolv.conf"
                    cmds = cmds[:index] + [dnscmd] + cmds[index:]
            elif netname in nics:
                iftype = 'direct'
                sourcexml = f"<source dev='{netname}' mode='bridge'/>"
                need_guestagent = True
                warning("Using macvtap. The vm will most likely be unaccessible from your hypervisor")
            else:
                return {'result': 'failure', 'reason': f"Invalid network {netname}"}
            if netname in ipv6networks:
                ipv6.append(netname)
            if ovs:
                ovsxml = "<virtualport type='openvswitch'/>{}"
                if "port_name" in nets[index] and nets[index]["port_name"]:
                    port_name = "<target dev='{port_name}'/>".format(**nets[index])
                    ovsxml.format(port_name)
                elif "ovs_vlan" in nets[index]:
                    port_name = "<target dev='vlan-{vlan}'/>".format(vlan=nets[index]['ovs_vlan'])
                    ovsxml.format(port_name)
                else:
                    ovsxml.format("")
            if nettype == 'igb' and machine == 'pc':
                machine = 'q35'
                warning("Forcing machine type to q35")
            if nicnuma is not None:
                slot = nicslots[nicnuma] + 1
                nicslots[nicnuma] = slot
                if 'q35' in machine:
                    bus = expanderinfo[nicnuma]['index'] + slot
                    slot = 0
                else:
                    bus = nicnuma + 1
                nicnumaxml = f"<address type='pci' domain='0x0000' bus='0x0{bus}' slot='0x0{slot}' function='0x0'/>"
            else:
                nicnumaxml = ""
            if vhost:
                iftype = 'vhostuser'
                vhostindex += 1
                vhostdir = default_poolpath
                vhostpath = nets[index].get('vhostpath', f"{vhostdir}/vhost-user{vhostindex}")
                sourcexml = f"<source type='unix' path='{vhostpath}' mode='client'/>"
                sourcexml += "<driver name='vhost' rx_queue_size='256'/>"
            bootdevxml = f'<boot order="{bootdev}"/>' if boot_order else ''
            bootdev += 1
            addressxml = ''
            if index == 0 and macosx:
                addressxml = """<address type="pci" domain="0x0000" bus="0x00" slot="0x05" function="0x0"/>"""
            netxml = """%s
<interface type='%s'>
%s
%s
%s
%s
%s
%s
<model type='%s'/>
%s
%s
%s
</interface>""" % (netxml, iftype, mtuxml, macxml, sourcexml, ovsxml, nicnumaxml, filterxml, nettype, multiqueuexml,
                   bootdevxml, addressxml)
        if need_guestagent and guestagent:
            gcmds = []
            if image is not None and 'cos' not in image and 'fedora-coreos' not in image:
                lower = image.lower()
                if lower.startswith('fedora') or lower.startswith('rhel') or lower.startswith('centos'):
                    gcmds.append('yum -y install qemu-guest-agent')
                    gcmds.append('systemctl enable qemu-guest-agent')
                    gcmds.append('systemctl start qemu-guest-agent')
                elif lower.startswith('debian') or [x for x in UBUNTUS if x in lower] or 'ubuntu' in lower:
                    gcmds.append('apt-get update')
                    gcmds.append('apt-get -y install qemu-guest-agent')
                    gcmds.append('/etc/init.d/qemu-guest-agent start')
                    gcmds.append('update-rc.d qemu-guest-agent defaults')
            index = 1 if cmds and 'sleep' in cmds[0] else 0
            if image is not None and image.startswith('rhel'):
                subindex = [i for i, value in enumerate(cmds) if value.startswith('subscription-manager')]
                if subindex:
                    index = subindex.pop() + 1
            cmds = cmds[:index] + gcmds + cmds[index:]
        if cloudinit:
            ignitiondata = None
            openstack = False
            if needs_ignition:
                ignition = 'qemu' in image
                combustion = common.needs_combustion(image)
                openstack = not ignition
                localhosts = ['localhost', '127.0.0.1']
                ignitiondir = default_poolpath
                if self.protocol == 'ssh' and self.host not in localhosts:
                    ignitiontmpdir = TemporaryDirectory()
                    ignitiondir = ignitiontmpdir.name
                version = common.ignition_version(image)
                ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                               domain=domain, files=files, enableroot=enableroot,
                                               overrides=overrides, version=version, plan=plan, ipv6=ipv6, image=image,
                                               vmuser=vmuser)
                try:
                    with open(f'{ignitiondir}/{name}.ign', 'w') as ignitionfile:
                        ignitionfile.write(ignitiondata)
                        identityfile = None
                except PermissionError:
                    pprint("Consider running the following command on the hypervisor:")
                    setfacluser = self.user
                    if self.host in ['localhost', '127.0.0.1']:
                        if not os.path.exists("/i_am_a_container"):
                            setfacluser = getpwuid(os.getuid()).pw_name
                    else:
                        setfacluser = "your_user"
                    pprint(f"sudo setfacl -m u:{setfacluser}:rwx {ignitiondir}")
                    return {'result': 'failure', 'reason': "Permission issues"}
                if self.protocol == 'ssh' and self.host not in localhosts:
                    publickeyfile = get_ssh_pub_key()
                    if publickeyfile is not None:
                        identityfile = publickeyfile.replace('.pub', '')
                        identitycommand = f"-i {identityfile}"
                    else:
                        identitycommand = ""
                    ignitioncmd1 = 'scp %s -qP %s %s/%s.ign %s@%s:%s' % (identitycommand,
                                                                         self.port, ignitiondir,
                                                                         name, self.user,
                                                                         self.host,
                                                                         default_poolpath)
                    code = os.system(ignitioncmd1)
                    if code != 0:
                        msg = f"Unable to create ignition data file in {default_poolpath}"
                        return {'result': 'failure', 'reason': msg}
                    ignitiontmpdir.cleanup()
            if image is not None and not ignition and diskpath is not None:
                cloudinitiso = f"{default_poolpath}/{name}.ISO"
                dtype = 'block' if diskpath.startswith('/dev') else 'file'
                dsource = 'dev' if diskpath.startswith('/dev') else 'file'
                isobus = 'scsi' if (aarch64_full or as390x) else 'sata'
                bootdevxml = f'<boot order="{bootdev_iso}"/>' if boot_order else ''
                isoxml = """<disk type='%s' device='cdrom'>
<driver name='qemu' type='raw'/>
<source %s='%s'/>
<target dev='hdd' bus='%s'/>
<readonly/>
%s
</disk>
<controller type='scsi' index='0' model='virtio-scsi'>
<alias name='scsi0'/>
</controller>""" % (dtype, dsource, cloudinitiso, isobus, bootdevxml)
                dest_machine = 'q99' if aarch64_full else machine
                if ignitiondata is not None:
                    userdata, metadata, netdata = ignitiondata, '', None
                else:
                    userdata, metadata, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                                   gateway=gateway, dns=dns, domain=domain,
                                                                   files=files, enableroot=enableroot,
                                                                   overrides=overrides, storemetadata=storemetadata,
                                                                   image=image, ipv6=ipv6, machine=dest_machine,
                                                                   vmuser=vmuser)
                with TemporaryDirectory() as tmpdir:
                    combustion = common.needs_combustion(image)
                    if combustion:
                        cmdsdata = common.process_combustion_cmds(cmds, overrides)
                        if cmdsdata != '':
                            with open(f'{tmpdir}/combustion_script', 'w') as combustionfile:
                                combustionfile.write(cmdsdata)
                    result = common.make_iso(name, tmpdir, userdata, metadata, netdata, openstack=openstack,
                                             combustion=combustion)
                    if result != 0:
                        error("Hit issue when creating user data iso")
                        msg = open(f'{tmpdir}/error.log').read()
                        return {'result': 'failure', 'reason': msg}
                    self._uploadimage(name, pool=default_storagepool, origin=tmpdir)
        listen = '0.0.0.0' if self.host not in ['localhost', '127.0.0.1'] else '127.0.0.1'
        if not vnc:
            displayxml = ''
        else:
            displayxml = """<input type='mouse' bus='virtio'/>"""
            vncviewerpath = '/Applications/VNC Viewer.app'
            passwd = "passwd='kcli'" if os.path.exists('/Applications') and not os.path.exists(vncviewerpath) else ''
            displayxml += """<graphics type='vnc' port='-1' autoport='yes' listen='%s' %s>
<listen type='address' address='%s'/>
</graphics>
<memballoon model='virtio'/>""" % (listen, passwd, listen)
            if aarch64_full:
                displayxml += "<video><model type='virtio' vram='16384' heads='1' primary='yes'/></video>"
        if cpumodel == 'host-model' and not aarch64:
            cpuxml = "<cpu mode='host-model'><model fallback='allow'/>"
        elif cpumodel == 'host-passthrough' or aarch64_full:
            cpuxml = "<cpu mode='host-passthrough'>model fallback='allow'/>"
        else:
            cpuxml = f"<cpu mode='custom' match='exact'><model fallback='allow'>{cpumodel}</model>"
        if virttype is None:
            if not capabilities['kvm']:
                warning("No acceleration available with this hypervisor")
                virttype = 'qemu'
                nested = False
            else:
                virttype = 'kvm'
        elif virttype not in ['qemu', 'kvm', 'xen', 'lxc']:
            msg = f"Incorrect virttype {virttype}"
            return {'result': 'failure', 'reason': msg}
        nestedfeature = capabilities['nestedfeature']
        if nested:
            if nestedfeature is not None:
                cpuxml += f"<feature policy='require' name='{nestedfeature}'/>"
            else:
                warning("Hypervisor not compatible with nesting. Skipping")
        elif nestedfeature is not None:
            cpuxml += f"<feature policy='disable' name='{nestedfeature}'/>"
        if cpuflags:
            for flag in cpuflags:
                if isinstance(flag, str):
                    if flag == 'vmx':
                        continue
                    cpuxml += f"<feature policy='optional' name='{flag}'/>"
                elif isinstance(flag, dict):
                    feature = flag.get('name')
                    policy = flag.get('policy', 'optional')
                    if feature is None:
                        continue
                    elif feature == 'vmx':
                        continue
                    elif policy in ['force', 'require', 'optional', 'disable', 'forbid']:
                        cpuxml += f"<feature policy='{policy}' name='{feature}'/>"
        sockets, cores, threads = overrides.get('sockets'), overrides.get('cores'), overrides.get('threads', 1)
        if sockets is not None and isinstance(sockets, int) and cores is not None and isinstance(cores, int)\
           and isinstance(threads, int):
            numcpus = sockets * cores * threads
            cpuxml += f"<topology sockets='{sockets}' cores='{cores}' threads='{threads}'/>"
        busxml = ""
        if cpuxml != '':
            if numa:
                expander = 'pci-expander-bus' if machine == 'pc' else 'pcie-expander-bus'
                pxb = 'pxb' if machine == 'pc' else 'pxb-pcie'
                numamemory = 0
                numaxml = '<numa>'
                count = 1
                for index, cell in enumerate(numa):
                    cellid = cell.get('id', index)
                    cellcpus = cell.get('vcpus')
                    cellmemory = cell.get('memory')
                    siblings = cell.get('siblings', [])
                    if cellcpus is None or cellmemory is None:
                        msg = f"Can't properly use cell {index} in numa block"
                        return {'result': 'failure', 'reason': msg}
                    numaxml += f"<cell id='{cellid}' cpus='{cellcpus}' memory='{cellmemory}' unit='MiB'>"
                    if siblings:
                        numaxml += "<distances>"
                        for sibling in siblings:
                            if not isinstance(sibling, dict) or 'id' not in sibling or 'value' not in sibling:
                                warning("Wrong sibling entry in cell {cellid}, ignoring")
                                continue
                            sibling_id, sibling_value = sibling['id'], sibling['value']
                            numaxml += f"<sibling id='{sibling_id}' value='{sibling_value}'/>"
                        numaxml += "</distances>"
                    numaxml += '</cell>'
                    numamemory += int(cellmemory)
                    if machine != 'pc':
                        busindex = expanderinfo[cellid]['index']
                    else:
                        busindex = count
                    busxml += """<controller type='pci' index='%s' model='%s'>
<model name='%s'/>
<target busNr='%s'>
<node>%s</node>
</target>
<alias name='pci.%s'/>
<address type='pci' domain='0x0000' bus='0x00' function='0x0'/>
</controller>\n""" % (busindex, expander, pxb, 20 * (index + 1), cellid, busindex)
                    count += 1
                    if machine != 'pc':
                        nicslots = expanderinfo[cellid]['slots']
                        for slot in range(expanderinfo[cellid]['slots']):
                            slotindex = busindex + slot + 1
                            busxml += """<controller type='pci' index='%s' model='pcie-root-port'>
<target chassis='%s' port='0x0'/>
<alias name='pci.%s'/>
<address type='pci' domain='0x0000' bus='0x0%s' slot='0x0%s' function='0x0'/>
</controller>\n""" % (slotindex, slotindex, slotindex, busindex, slotindex)
                        count += 1
                cpuxml += f'{numaxml}</numa>'
                if numamemory > memory:
                    msg = "Can't use more memory for numa than assigned one ({memory})"
                    return {'result': 'failure', 'reason': msg}
            elif memoryhotplug:
                lastcpu = int(numcpus) - 1
                cpuxml += f"<numa><cell id='0' cpus='0-{lastcpu}' memory='{memory * 1024}' unit='KiB'/></numa>"
            cpuxml += "</cpu>"
        cpupinningxml = ''
        if cpupinning:
            for entry in cpupinning:
                if not isinstance(entry, dict):
                    msg = f"Can't process entry {index} in numa block"
                    return {'result': 'failure', 'reason': msg}
                else:
                    vcpus = entry.get('vcpus')
                    hostcpus = entry.get('hostcpus')
                    if vcpus is None or hostcpus is None:
                        msg = f"Can't process entry {index} in cpupinning block"
                        return {'result': 'failure', 'reason': msg}
                    for vcpu in str(vcpus).split(','):
                        if '-' in vcpu:
                            if len(vcpu.split('-')) != 2:
                                msg = "Can't properly split vcpu in cpupinning block"
                                return {'result': 'failure', 'reason': msg}
                            else:
                                idmin, idmax = vcpu.split('-')
                        else:
                            try:
                                idmin, idmax = vcpu, vcpu
                            except ValueError:
                                msg = "Can't properly use vcpu as integer in cpunning block"
                                return {'result': 'failure', 'reason': msg}
                        idmin, idmax = int(idmin), int(idmax) + 1
                        if idmax > numcpus:
                            msg = "Can't use more cpus for pinning than assigned numcpus"
                            return {'result': 'failure', 'reason': msg}
                        for cpunum in range(idmin, idmax):
                            cpupinningxml += f"<vcpupin vcpu='{cpunum}' cpuset='{hostcpus}'/>\n"
            cpupinningxml = f"<cputune>{cpupinningxml}</cputune>"
        numatunexml = ''
        if numamode is not None:
            numatunexml += f"<numatune><memory mode='{numamode}' nodeset='0'/></numatune>"
        if macosx:
            cpuxml = ""
        if self.host in ['localhost', '127.0.0.1']:
            serialxml = """<serial type='pty'>
<target port='0'/>
</serial>
<console type='pty'>
<target type='serial' port='0'/>
</console>"""
        elif aarch64 and not aarch64_full:
            serialxml = ''
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
            vcpuxml = f"<vcpu  placement='static' current='{numcpus}'>64</vcpu>"
        else:
            vcpuxml = f"<vcpu>{numcpus}</vcpu>"
        clockxml = "<clock offset='utc'/>"
        qemuextraxml = ''
        if ignition or usermode or macosx or tpm or qemuextra is not None or nvmedisks:
            namespace = "xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'"
            ignitionxml = ""
            if ignition:
                ignitionxml = """<qemu:arg value='-fw_cfg' />
<qemu:arg value='name=opt/com.coreos/config,file=%s/%s.ign' />""" % (default_poolpath, name)
            usermodexml = ""
            if usermode:
                netmodel = 'virtio-net-pci' if not macosx else 'e1000-82545em'
                usermodexml = """<qemu:arg value='-netdev'/>
<qemu:arg value='user,id=mynet.0,net=10.0.10.0/24,hostfwd=tcp::%s-:22'/>
<qemu:arg value='-device'/>
<qemu:arg value='%s,netdev=mynet.0'/>""" % (userport, netmodel)
            macosxml = ""
            if macosx:
                clockxml = """<clock offset='utc'>
<timer name='rtc' tickpolicy='catchup'/>
<timer name='pit' tickpolicy='delay'/>
<timer name='hpet' present='no'/>
</clock>"""
                osk = "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
                cpuflags = "+invtsc,vmware-cpuid-freq=on,+pcid,+ssse3,+sse4.2,+popcnt,+avx,+aes,+xsave,+xsaveopt"
                cpuinfo = f"Penryn,kvm=on,vendor=GenuineIntel,{cpuflags},check"
                macosxml = """<qemu:arg value='-cpu'/>
<qemu:arg value='%s'/>
<qemu:arg value='-device'/>
<qemu:arg value='isa-applesmc,osk=%s'/>
<qemu:arg value='-smbios'/>
<qemu:arg value='type=2'/>
<qemu:arg value="-usb"/>
<qemu:arg value='-device'/>
<qemu:arg value='usb-tablet'/>
<qemu:arg value='-device'/>
<qemu:arg value='usb-kbd'/>""" % (cpuinfo, osk)
            if qemuextra is not None:
                freeformxml = ""
                freeform = qemuextra.split(" ")
                for entry in freeform:
                    freeformxml += f"<qemu:arg value='{entry}'/>\n"
            else:
                freeformxml = ""
            nvmexml = ""
            if nvmedisks:
                metadataxml += "\n<kvirt:nvmedisks>{nvmedisks}</kvirt:nvmedisks>".format(nvmedisks=','.join(nvmedisks))
                for index, diskpath in enumerate(nvmedisks):
                    nvmexml += """<qemu:arg value='-drive'/>
<qemu:arg value='file={diskpath},format=qcow2,if=none,id=NVME{index}'/>
<qemu:arg value='-device'/>
<qemu:arg value='nvme,drive=NVME{index},serial=nvme-{index}'/>""".format(index=index, diskpath=diskpath)
            qemuextraxml = """<qemu:commandline>
{ignitionxml}
{usermodexml}
{macosxml}
{freeformxml}
{nvmexml}
</qemu:commandline>""".format(ignitionxml=ignitionxml, usermodexml=usermodexml, macosxml=macosxml,
                              freeformxml=freeformxml, nvmexml=nvmexml)
        sharedxml = ""
        if sharedfolders:
            for folder in sharedfolders:
                # accessmode = "passthrough"
                accessmode = "mapped"
                sharedxml += f"<filesystem type='mount' accessmode='{accessmode}'>"
                sharedxml += f"<source dir='{folder}'/><target dir='{os.path.basename(folder)}'/>"
                sharedxml += "<address type='pci' domain='0x0000' bus='0x00' slot='0x09' function='0x0'/>"
                sharedxml += "</filesystem>"
                foldercmd = f"sudo mkdir {folder} ; sudo chmod 777 {folder}"
                if not os.path.exists(folder) and self.host in ['localhost', '127.0.0.1']:
                    oldmask = os.umask(000)
                    os.makedirs(folder)
                    os.umask(oldmask)
                elif self.protocol == 'ssh':
                    foldercmd = 'ssh %s -p %s %s@%s "test -d %s || (%s)"' % (self.identitycommand, self.port,
                                                                             self.user, self.host, folder, foldercmd)
                    code = os.system(foldercmd)
        memoryhotplugxml = "<maxMemory slots='16' unit='MiB'>1524288</maxMemory>" if memoryhotplug else ""
        videoxml = ""
        firmwarexml = ""
        if macosx:
            guestxml = ""
            videoxml = """<video><model type='vmvga' vram='65536'/></video>"""
        hostdevxml = ""
        for index, pcidevice in enumerate(pcidevices):
            pcidevice = str(pcidevice)
            if pcidevice.startswith('000'):
                newdomain = pcidevice.split(':')[0]
                pcidevice = pcidevice.replace(f'{newdomain}:', '')
            else:
                newdomain = "0000"
            if len(pcidevice.split(':')) != 2:
                return {'result': 'failure', 'reason': f"Incorrect pcidevice entry {index}"}
            newbus = pcidevice.split(':')[0]
            if len(pcidevice.split('.')) != 2:
                return {'result': 'failure', 'reason': "Incorrect pcidevice entry {index}"}
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
        ramxml = ""
        smmxml = ""
        osfirmware = ""
        if uefi or uefi_firmware is not None or secureboot:
            secure = 'yes' if secureboot else 'no'
            uefi_firmware = '/usr/share/OVMF/OVMF_CODE.secboot.fd' if uefi_legacy else uefi_firmware
            if uefi_firmware is not None:
                ramxml = f"<loader secure='{secure}' readonly='yes' type='pflash'>{uefi_firmware}</loader>"
                if secureboot:
                    smmxml = "<smm state='on'/>"
                    sectemplate = '/usr/share/OVMF/OVMF_VARS.secboot.fd'
                    ramxml += f'<nvram template="{sectemplate}">/var/lib/libvirt/qemu/nvram/{name}.fd</nvram>'
                elif uefi_firmware is not None and ('arm' in uefi_firmware or 'aarch64' in uefi_firmware):
                    nvtemplate = uefi_nvtemplate or uefi_firmware.replace('-code', '-vars')
                    ramxml += f'<nvram template="{nvtemplate}">/var/lib/libvirt/qemu/nvram/{name}.fd</nvram>'
                else:
                    ramxml += f'<nvram>/var/lib/libvirt/qemu/nvram/{name}.fd</nvram>'
            else:
                osfirmware = "firmware='efi'"
                if secureboot:
                    smmxml = "<smm state='on'/>"
                    ramxml += "<firmware><feature enabled='yes' name='secure-boot'/>"
                    ramxml += "<feature enabled='yes' name='enrolled-keys'/></firmware>"
                else:
                    ramxml += "<firmware><feature enabled='no' name='secure-boot'/></firmware>"
        arch = 'aarch64' if aarch64 else overrides.get('arch', 'x86_64')
        if sriov_nic or (not aarch64 and not as390x):
            acpixml = '<acpi/>\n<apic/>'
        elif aarch64_full:
            acpixml = "<acpi/><gic version='3'/>"
        else:
            acpixml = ''
        hugepagesxml = ""
        hugepages = overrides.get('hugepages', False)
        hugepages_1gb = overrides.get('hugepages_1gb', False)
        hugepages_2mb = overrides.get('hugepages_2mb', False)
        need_hugepages = hugepages or hugepages_1gb or hugepages_2mb
        if need_hugepages:
            if hugepages_1gb:
                sizexml = "<hugepages><page size='1048576' unit='KiB'/></hugepages>"
            elif hugepages_2mb:
                sizexml = "<hugepages><page size='2' unit='MiB'/></hugepages>"
            else:
                sizexml = '<hugepages/>'
            hugepagesxml = f"<memoryBacking>{sizexml}</memoryBacking>"
        machine = f"machine='{machine}'"
        emulatorxml = f"<emulator>{emulator}</emulator>"
        uuidxml = ""
        if 'uuid' in overrides:
            uuid = str(overrides['uuid'])
            try:
                UUID(uuid)
                uuidxml = f"<uuid>{uuid}</uuid>"
            except:
                warning(f"couldn't use {uuid} as uuid")
        metadataxml += "</kvirt:info></metadata>"
        iommumemxml = ''
        iommufeaturesxml = ''
        iommudevicexml = ''
        if enableiommu:
            iommumemxml = "<memtune><hard_limit unit='KiB'>104857600</hard_limit></memtune>"
            iommufeaturesxml = "<acpi/><apic/><pae/><apic/><pae/><ioapic driver='qemu'/>"
            iommudevicexml = f"<iommu model='{iommu_model}'><driver intremap='on' caching_mode='on'/></iommu>"
        controllerxml = ''
        if uefi or uefi_legacy:
            controllerxml = "<controller type='pci' model='pcie-root'/>"
            controllerxml += ''.join(["<controller type='pci' model='pcie-root-port'/>" for i in range(5)])
            pciexml = "<controller type='pci' model='pcie-to-pci-bridge'><model name='pcie-pci-bridge'/></controller>"
            controllerxml += pciexml
        vmxml = """<domain type='{virttype}' {namespace}>
<name>{name}</name>
{uuidxml}
{metadataxml}
{memoryhotplugxml}
{cpupinningxml}
{numatunexml}
{hugepagesxml}
{iommumemxml}
<memory unit='MiB'>{memory}</memory>
{vcpuxml}
<os {osfirmware}>
<type arch='{arch}' {machine}>hvm</type>
{ramxml}
{firmwarexml}
{bootxml}
<bootmenu enable="yes" timeout="60"/>
</os>
<features>
{smmxml}
{ioapicxml}
{acpixml}
{iommufeaturesxml}
<pae/>
</features>
{clockxml}
<on_poweroff>destroy</on_poweroff>
<on_reboot>restart</on_reboot>
<on_crash>restart</on_crash>
<devices>
{emulatorxml}
{disksxml}
{controllerxml}
{busxml}
{netxml}
{isoxml}
{extraisoxml}
{floppyxml}
{displayxml}
{serialxml}
{sharedxml}
{guestxml}
{videoxml}
{hostdevxml}
{rngxml}
{tpmxml}
{iommuxml}
{iommudevicexml}
</devices>
{cpuxml}
{qemuextraxml}
</domain>""".format(virttype=virttype, namespace=namespace, name=name, uuidxml=uuidxml, metadataxml=metadataxml,
                    memoryhotplugxml=memoryhotplugxml, cpupinningxml=cpupinningxml, numatunexml=numatunexml,
                    hugepagesxml=hugepagesxml, memory=memory, vcpuxml=vcpuxml, osfirmware=osfirmware, arch=arch,
                    machine=machine, ramxml=ramxml, firmwarexml=firmwarexml, bootxml=bootxml,
                    smmxml=smmxml, emulatorxml=emulatorxml, disksxml=disksxml, busxml=busxml, netxml=netxml,
                    isoxml=isoxml, extraisoxml=extraisoxml, floppyxml=floppyxml, displayxml=displayxml,
                    serialxml=serialxml, sharedxml=sharedxml, guestxml=guestxml, videoxml=videoxml,
                    hostdevxml=hostdevxml, rngxml=rngxml, tpmxml=tpmxml, cpuxml=cpuxml, qemuextraxml=qemuextraxml,
                    ioapicxml=ioapicxml, acpixml=acpixml, iommuxml=iommuxml, iommumemxml=iommumemxml,
                    iommufeaturesxml=iommufeaturesxml, iommudevicexml=iommudevicexml, controllerxml=controllerxml,
                    clockxml=clockxml)
        if self.debug:
            print(vmxml.replace('\n\n', ''))
        conn.defineXML(vmxml)
        vm = conn.lookupByName(name)
        autostart = 1 if autostart else 0
        vm.setAutostart(autostart)
        for pool in volsxml:
            storagepool = conn.storagePoolLookupByName(pool)
            try:
                storagepool.refresh(0)
            except Exception as e:
                warning(f"Hit {e} when refreshing pool {pool}")
                pass
            for volxml in volsxml[pool]:
                storagepool.createXML(volxml, 0)
        if fixqcow2path is not None and fixqcow2backing is not None:
            self._fixqcow2(fixqcow2path, fixqcow2backing)
        if cmdline is not None and firstdisk is not None:
            pprint("Injecting cmdline in vm image")
            if 'rhcos' in image or 'fcos' in image:
                virtcmd = 'virt-edit'
                bootdisk = '/dev/sda3'
                bootfile = "/boot/loader/entries/ostree-1.conf"
                cmd = f"sudo {virtcmd} -a {firstdisk} -m {bootdisk} {bootfile} -e 's@^options@options {cmdline}@'"
            elif common.is_ubuntu(image) or 'debian' in image or 'openeuler' in image.lower():
                virtcmd = 'virt-customize'
                updatecmd = 'grub2-mkconfig -o /boot/grub2/grub.cfg' if 'openeuler' in image.lower() else 'update-grub'
                runcmd = rf'echo GRUB_CMDLINE_LINUX_DEFAULT=\"\$GRUB_CMDLINE_LINUX_DEFAULT {cmdline}\"'
                runcmd += f' > /etc/default/grub.d/kcli.cfg ; {updatecmd}'
                cmd = f"sudo {virtcmd} -a {firstdisk} --run-command '{runcmd}'"
            else:
                virtcmd = 'virt-customize'
                cmd = f"sudo {virtcmd} -a {firstdisk} --run-command 'grubby --update-kernel=ALL --args={cmdline}'"
            if os.path.exists("/i_am_a_container") and which(virtcmd) is None:
                os.system('apt-get install -y libguestfs-tools')
                os.system(cmd.replace('sudo ', ''))
            elif self.host == 'localhost' or self.host == '127.0.0.1':
                if which(virtcmd) is not None:
                    os.system(cmd)
                else:
                    warning(f"{virtcmd} missing from PATH. cmdline won't be injected")
            elif self.protocol == 'ssh':
                cmd = cmd.replace("'", "\'")
                cmd = f'ssh {self.identitycommand} -p {self.port} {self.user}@{self.host} "{cmd}"'
                os.system(cmd)
        xml = vm.XMLDesc(0)
        vmxml = ET.fromstring(xml)
        self._reserve_ip(name, domain, vmxml, nets, primary=reserveip, networks=allnetworks)
        if start:
            try:
                vm.create()
            except Exception as e:
                return {'result': 'failure', 'reason': e}
        self.reserve_dns(name, nets=nets, domain=domain, alias=alias, force=True, primary=reservedns, start=start)
        if reservehost:
            self.reserve_host(name, nets, domain)
        if '<kernel>' in xml:
            root = ET.fromstring(xml)
            os_tag = root.find('os')
            kernel, initrd, cmdline = os_tag.find('kernel'), os_tag.find('initrd'), os_tag.find('cmdline')
            if kernel is not None:
                os_tag.remove(kernel)
            if initrd is not None:
                os_tag.remove(initrd)
            if cmdline is not None:
                os_tag.remove(cmdline)
            newxml = ET.tostring(root).decode("utf-8")
            conn.defineXML(newxml)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        status = vm.state()[0]
        if status == 3:
            try:
                vm.resume()
            except Exception as e:
                return {'result': 'failure', 'reason': e}
        elif status != 1:
            try:
                vm.create()
            except Exception as e:
                if 'Cannot access storage file' in str(e) and '.iso' in str(e):
                    warning(f"Removing attached iso. Hit {e}")
                    self.update_iso(name, None)
                    vm.create()
                else:
                    return {'result': 'failure', 'reason': e}
        return {'result': 'success'}

    def force_cdrom(self, name):
        self.stop(name)
        conn = self.conn
        vm = conn.lookupByName(name)
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        for _os in list(root.iter('os')):
            if list(_os.iter('boot'))[0].get('dev') == 'cdrom':
                return {'result': 'success'}
        newxml = ET.tostring(root).decode("utf-8")
        newxml = newxml.replace('dev="cdrom"', 'dev="TEMP"')
        newxml = newxml.replace('dev="hd"', 'dev="cdrom"')
        newxml = newxml.replace('dev="TEMP"', 'dev="hd"')
        for element in list(root.iter('disk')):
            if element.get('device') == 'cdrom':
                boot = element.find('boot')
                if boot is not None:
                    cd_order = boot.get('order')
                    newxml = newxml.replace('<boot order="1"/> ', '<boot order="TEMP" />')
                    newxml = newxml.replace(f'<boot order="{cd_order}" />', '<boot order="1" />')
                    newxml = newxml.replace('<boot order="TEMP"/> ', f'<boot order="{cd_order}" />')
                break
        conn.defineXML(newxml)
        return {'result': 'success'}

    def stop(self, name, soft=False):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if status[vm.isActive()] != "down":
            if soft:
                timeout = 0
                vm.shutdown()
                while status[vm.isActive()] != "down":
                    if timeout > 240:
                        pprint(f"Timeout waiting for {name} to gracefully shutdown")
                        break
                    pprint(f"Waiting for {name} to gracefully shutdown")
                    time.sleep(5)
                    timeout += 5
            else:
                vm.destroy()
        return {'result': 'success'}

    def create_snapshot(self, name, base):
        conn = self.conn
        try:
            vm = conn.lookupByName(base)
            vmxml = vm.XMLDesc(0)
        except:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        if name in vm.snapshotListNames():
            return {'result': 'failure', 'reason': f"Snapshot {name} already exists"}
        raw_disks, primary_disk = self._get_raw_disks(vm)
        memory_snapshot = 'internal' if vm.isActive() != 0 and not raw_disks else 'no'
        snapshot_type = 'external' if raw_disks else 'internal'
        disksxml = f"<disk name='{primary_disk}' snapshot='{snapshot_type}'/>"
        for disk in raw_disks:
            disksxml += f"<disk name='{disk}' snapshot='no'/>"
        memoryxml = f"<memory snapshot='{memory_snapshot}'/>"
        snapxml = """<domainsnapshot>
          <name>%s</name>
          %s
          <disks>
          %s
          </disks>
          %s
          </domainsnapshot>""" % (name, memoryxml, disksxml, vmxml)
        flags = VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY | VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC\
            if snapshot_type == 'external' else 0
        vm.snapshotCreateXML(snapxml, flags=flags)
        return {'result': 'success'}

    def delete_snapshot(self, name, base):
        conn = self.conn
        try:
            vm = conn.lookupByName(base)
        except:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        if name not in vm.snapshotListNames():
            return {'result': 'failure', 'reason': f"Snapshot {name} doesn't exist"}
        snap_metadata = 0
        snap = vm.snapshotLookupByName(name)
        raw_disks = self._get_raw_disks(vm)[0]
        if raw_disks:
            if not vm.isActive():
                msg = f"VM {base} needs to be up for deleting an external snapshot"
                return {'result': 'failure', 'reason': msg}
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            disk = list(root.iter('disk'))[0]
            disk_name = disk.find('target').get('dev')
            imagefiles = [disk.find('source').get('file'), disk.find('source').get('dev'),
                          disk.find('source').get('volume')]
            snapshot_path = next(item for item in imagefiles if item is not None)
            base_path = snapshot_path.replace(f'.{name}', '.img')
            vm.blockCommit(disk_name, base_path, snapshot_path, 0, VIR_DOMAIN_BLOCK_COMMIT_ACTIVE)
            while True:
                info = vm.blockJobInfo(disk_name, 0)
                if not info or info["cur"] == info["end"]:
                    break
                pprint(f"Progress: {info['cur']}/{info['end']} bytes committed")
                time.sleep(1)
            vm.blockJobAbort(disk_name, VIR_DOMAIN_BLOCK_JOB_ABORT_PIVOT)
            pool = conn.storageVolLookupByPath(base_path).storagePoolLookupByVolume()
            pool.refresh()
            self.delete_disk(diskname=snapshot_path, pool=pool.name())
            snap_metadata = 2
        snap.delete(snap_metadata)
        return {'result': 'success'}

    def list_snapshots(self, base):
        conn = self.conn
        try:
            vm = conn.lookupByName(base)
        except:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        return vm.snapshotListNames()

    def revert_snapshot(self, name, base):
        conn = self.conn
        try:
            vm = conn.lookupByName(base)
        except:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        if name not in vm.snapshotListNames():
            return {'result': 'failure', 'reason': f"Snapshot {name} doesn't exist"}
        snap = vm.snapshotLookupByName(name)
        raw_disks = self._get_raw_disks(vm)[0]
        if raw_disks:
            if vm.isActive():
                msg = f"VM {base} needs to be down for reverting to an external snapshot"
                return {'result': 'failure', 'reason': msg}
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            disk = list(root.iter('disk'))[0]
            snapshot_path = disk.find('source').get('file')
            if not snapshot_path.endswith(f'.{name}'):
                return {'result': 'failure', 'reason': f"Snapshot {name} was not found in {base}"}
            top_backingstore = disk.find('backingStore')
            original_path = top_backingstore.find('source').get('file')
            child_backingstore = top_backingstore.find('backingStore')
            original_image_path = child_backingstore.find('source').get('file')
            disk.find('source').set('file', original_path)
            top_backingstore.find('source').set('file', original_image_path)
            top_backingstore.remove(child_backingstore)
            new_xml = ET.tostring(root, encoding='unicode')
            conn.defineXML(new_xml)
            warning(f"Deleting external snapshot {name}")
            pool = conn.storageVolLookupByPath(original_path).storagePoolLookupByVolume()
            pool.refresh()
            self.delete_disk(diskname=snapshot_path, pool=pool.name())
            snap.delete(2)
        else:
            vm.revertToSnapshot(snap)
        return {'result': 'success'}

    def restart(self, name):
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        try:
            vm = conn.lookupByName(name)
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if status[vm.isActive()] == "down":
            vm.create()
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
            mem = list(root.iter('memory'))[0]
            unit = mem.attrib['unit']
            mem = mem.text
            if unit == 'KiB':
                mem = float(mem) / 1024
                mem = int(mem)
            usedmemory += mem
        return usedmemory + memory > totalmemory

    def info_host(self):
        data = {}
        conn = self.conn
        status = {0: 'down', 1: 'up'}
        hostname = conn.getHostname()
        totalcpus = conn.getCPUMap()[0]
        totalmemory = conn.getInfo()[1]
        data["connection"] = self.url
        data["host"] = hostname
        totalvms = 0
        usedcpus = 0
        usedmemory = 0
        for vm in conn.listAllDomains(0):
            if status[vm.isActive()] == "down":
                continue
            totalvms += 1
            memory, numcpus = vm.info()[2:4]
            usedcpus += numcpus
            usedmemory += int(float(memory) / 1024)
        data["vms_running"] = totalvms
        data["cpus_total"] = totalcpus
        data["cpus_used"] = usedcpus
        data["memory_used"] = usedmemory
        data["memory_total"] = totalmemory
        storage = []
        for pool in conn.listAllStoragePools(VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE):
            poolname = pool.name()
            poolxml = pool.XMLDesc(0)
            root = ET.fromstring(poolxml)
            pooltype = list(root.iter('pool'))[0].get('type')
            if pooltype in ['dir', 'zfs']:
                poolpath = list(root.iter('path'))[0].text
            else:
                poolpath = list(root.iter('device'))[0].get('path')
            s = pool.info()
            used = "%.2f" % (float(s[2]) / GiB)
            avail = "%.2f" % (float(s[3]) / GiB)
            used = float(used)
            avail = float(avail)
            new_data = f"storage: {poolname}, type: {pooltype}, path: {poolpath}, used_space: {used}GB,"
            new_data += f" available_space: {avail}GB"
            storage.append(new_data)
        data['storage'] = storage
        networks = []
        try:
            for interface in conn.listInterfaces():
                if interface == 'lo':
                    continue
                networks.append(f"name: {interface}, type: bridged")
        except libvirtError as e:
            error(e)
        for network in conn.listAllNetworks():
            networkname = network.name()
            netxml = network.XMLDesc(0)
            cidr = 'N/A'
            root = ET.fromstring(netxml)
            ip = list(root.iter('ip'))
            if ip:
                attributes = ip[0].attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                if netmask is None:
                    netmask = attributes.get('prefix')
                try:
                    ip = ip_network(f'{firstip}/{netmask}', strict=False)
                    cidr = str(ip)
                except:
                    cidr = "N/A"
            dhcp = list(root.iter('dhcp'))
            if dhcp:
                dhcp = True
            else:
                dhcp = False
            networks.append(f"name: {networkname}, type: routed, cidr: {cidr}, dhcp: {dhcp}")
        data['networks'] = networks
        return data

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
            try:
                vms.append(self.info(vm.name(), vm=vm))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if not vm.isActive():
            error(f"VM {name} down")
            return
        else:
            xml = vm.XMLDesc(1)
            root = ET.fromstring(xml)
            host = self.host
            graphics = list(root.iter('graphics'))
            if not graphics:
                error(f"No graphics found in vm {name}")
                return
            for element in graphics:
                attributes = element.attrib
                if attributes['listen'] == '127.0.0.1' and not os.path.exists("i_am_a_container")\
                   and self.host not in ['127.0.0.1', 'localhost']:
                    tunnel = True
                    host = '127.0.0.1'
                protocol = attributes['type']
                port = attributes['port']
                passwd = attributes.get('passwd')
                localport = port
                consolecommand = ''
                if os.path.exists("/i_am_a_container"):
                    self.identitycommand = self.identitycommand.replace('/root', '$HOME')
                if tunnel:
                    localport = common.get_free_port()
                    consolecommand += "ssh %s -o LogLevel=QUIET -f -p %s -L %s:127.0.0.1:%s %s@%s sleep 10;"\
                        % (self.identitycommand, self.port, localport, port, self.user, self.host)
                    host = '127.0.0.1'
                if passwd is not None:
                    url = f"{protocol}://kcli:{passwd}@{host}:{localport}"
                else:
                    url = f"{protocol}://{host}:{localport}"
                if web:
                    if tunnel:
                        os.popen(consolecommand)
                    return url
                if os.path.exists('/Applications'):
                    if protocol == 'spice' and os.path.exists('/Applications/RemoteViewer.app'):
                        consolecommand += f"open -a RemoteViewer --args {url} &"
                    elif protocol == 'vnc' and os.path.exists('/Applications/VNC Viewer.app'):
                        consolecommand += f"open -a 'VNC Viewer' --args {url.replace('vnc://', '')} &"
                    else:
                        consolecommand += f"open -a 'Screen Sharing' {url} &"
                else:
                    consolecommand += f"remote-viewer {url} &"
                if self.debug or os.path.exists("/i_am_a_container"):
                    msg = f"Run the following command:\n{consolecommand}" if not self.debug else consolecommand
                    pprint(msg)
                else:
                    os.popen(consolecommand)

    def serialconsole(self, name, web=False):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if not vm.isActive():
            error(f"VM {name} down")
            return
        else:
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
            serial = list(root.iter('serial'))
            if not serial:
                error("No serial Console found. Leaving...")
                return
            for element in serial:
                serialport = element.find('source').get('service')
            if serialport is not None:
                if self.host in ['localhost', '127.0.0.1']:
                    serialcommand = f"nc 127.0.0.1 {serialport}"
                elif self.protocol != 'ssh':
                    error("Remote serial Console requires using ssh . Leaving...")
                    return
                else:
                    if os.path.exists("/i_am_a_container"):
                        self.identitycommand = self.identitycommand.replace('/root', '$HOME')
                    serialcommand = "ssh %s -o LogLevel=QUIET -p %s %s@%s nc 127.0.0.1 %s" %\
                        (self.identitycommand, self.port, self.user, self.host, serialport)
                if web:
                    return serialcommand
                if self.debug or os.path.exists("/i_am_a_container"):
                    msg = f"Run the following command:\n{serialcommand}" if not self.debug else serialcommand
                    pprint(msg)
                else:
                    os.system(serialcommand)
            elif self.host in ['localhost', '127.0.0.1']:
                cmd = f'virsh -c {self.url} console {name}'
                if self.debug or os.path.exists("/i_am_a_container"):
                    msg = f"Run the following command:\n{cmd}"
                    pprint(msg)
                else:
                    os.system(cmd)
            else:
                error("No serial Console port found. Leaving...")
                return

    def info(self, name, vm=None, debug=False):
        starts = {0: False, 1: True}
        conn = self.conn
        if vm is None:
            listinfo = False
            try:
                vm = conn.lookupByName(name)
            except:
                error(f"VM {name} not found")
                return {}
        else:
            listinfo = True
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        uuid = vm.UUIDString()
        yamlinfo = {'name': name, 'nets': [], 'disks': [], 'id': uuid}
        plan, profile, image, ip, creationdate = '', None, None, None, None
        nvmedisks = []
        kube, kubetype = None, None
        nodhcp = False
        for element in list(root.iter('{kvirt}info')):
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
                yamlinfo['ip'] = ip
            e = element.find('{kvirt}creationdate')
            if e is not None:
                creationdate = e.text
            e = element.find('{kvirt}owner')
            if e is not None:
                yamlinfo['owner'] = e.text
            e = element.find('{kvirt}redfish_iso')
            if e is not None:
                yamlinfo['redfish_iso'] = e.text
            e = element.find('{kvirt}user')
            if e is not None:
                yamlinfo['user'] = e.text
            e = element.find('{kvirt}domain')
            if e is not None:
                yamlinfo['domain'] = e.text
            e = element.find('{kvirt}nvmedisks')
            if e is not None:
                nvmedisks = e.text.split(',')
            e = element.find('{kvirt}nodhcp')
            if e is not None:
                nodhcp = True
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
        interfaces = list(root.iter('interface'))
        macs = []
        bridged = False
        for index, element in enumerate(interfaces):
            networktype = element.get('type').replace('network', 'routed')
            device = f"eth{index}"
            mac = element.find('mac').get('address')
            macs.append(mac)
            if networktype == 'user':
                network = 'user'
            elif networktype == 'bridge':
                network = element.find('source').get('bridge')
                bridged = True
            elif networktype == 'direct':
                network = element.find('source').get('dev')
                bridged = True
            else:
                network = element.find('source').get('network')
            yamlinfo['nets'].append({'device': device, 'mac': mac, 'net': network, 'type': networktype})
        all_ips = [ip] if ip is not None else []
        if vm.isActive():
            source_first = vir_src_agent if bridged or nodhcp else vir_src_lease
            source_second = vir_src_agent if source_first == vir_src_lease else vir_src_lease
            try:
                ifaces = vm.interfaceAddresses(source_first, 0)
            except:
                ifaces = {}
            if not ifaces:
                try:
                    ifaces = vm.interfaceAddresses(source_second, 0)
                except:
                    ifaces = {}
            if ifaces:
                ips = []
                for mac in macs:
                    for x in ifaces:
                        if ifaces[x]['hwaddr'] == mac and ifaces[x]['addrs'] is not None:
                            for entry in ifaces[x]['addrs']:
                                if entry['addr'].startswith(tuple(['fe80::', '169.254.169', 'fd69'])):
                                    continue
                                ip = entry['addr']
                                if ip not in ips:
                                    ips.append(ip)
                                if ip not in all_ips:
                                    all_ips.append(ip)
                if ips and 'ip' not in yamlinfo:
                    ip4s = [i for i in ips if ':' not in i]
                    ip6s = [i for i in ips if i not in ip4s]
                    yamlinfo['ip'] = ip4s[0] if ip4s else ip6s[0]
        if len(all_ips) > 1:
            yamlinfo['ips'] = all_ips
        pcidevices = []
        hostdevs = list(set(list(root.iter('hostdev'))))
        for index, element in enumerate(hostdevs):
            address = element.find('source').find('address')
            if address is not None:
                bus, slot, function = address.get('bus'), address.get('slot'), address.get('function')
                address = f'{bus}:{slot}.{function}'.replace('0x', '')
                pcidevices.append(address)
        if pcidevices:
            yamlinfo['pcidevices'] = list(set(list(pcidevices)))
        if 'ip' in yamlinfo:
            ip = yamlinfo['ip']
            # better filter to detect user nets needed here
            if '.' not in ip and ':' not in ip:
                usernetinfo = {'device': f"eth{len(yamlinfo['nets'])}", 'mac': 'N/A', 'net': 'user', 'type': 'user'}
                yamlinfo['nets'].append(usernetinfo)
        if listinfo:
            state = vm.state()[0]
            yamlinfo['status'] = states.get(state)
            return yamlinfo
        [state, maxmem, memory, numcpus, cputime] = vm.info()
        yamlinfo['status'] = states.get(state)
        yamlinfo['autostart'] = starts[vm.autostart()]
        memory = int(float(memory) / 1024)
        yamlinfo['numcpus'] = numcpus
        yamlinfo['memory'] = memory
        for element in list(root.iter('disk')):
            disktype = element.get('device')
            if disktype == 'cdrom':
                iso_file = element.find('source').get('file') if element.find('source') is not None else None
                if iso_file is not None and not iso_file.endswith(f'{name}.ISO'):
                    yamlinfo['iso'] = iso_file
                continue
            device = element.find('target').get('dev')
            diskformat = element.find('target').get('bus')
            # diskformat = 'file'
            drivertype = element.find('driver').get('type')
            imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                          element.find('source').get('volume')]
            path = next(item for item in imagefiles if item is not None)
            try:
                volume = conn.storageVolLookupByPath(path)
                disksize = int(float(volume.info()[1]) / GiB)
            except:
                disksize = 'N/A'
            yamlinfo['disks'].append({'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype,
                                      'path': path})
        if nvmedisks:
            for index, diskpath in enumerate(nvmedisks):
                yamlinfo['disks'].append({'device': f'nvme{index}', 'size': 'N/A', 'format': 'nvme', 'type': 'qcow2',
                                          'path': diskpath})
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
        if image is None and 'kubetype' in yamlinfo and yamlinfo['kubetype'] == 'openshift':
            yamlinfo['user'] = 'core'
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
            bridged = False
            interfaces = list(root.iter('interface'))
            for element in interfaces:
                networktype = element.get('type')
                if mac is None:
                    mac = element.find('mac').get('address')
                if networktype == 'user':
                    continue
                if networktype == 'bridge':
                    network = element.find('source').get('bridge')
                    bridged = True
                else:
                    network = element.find('source').get('network')
                    try:
                        networkdata = conn.networkLookupByName(network)
                        netxml = networkdata.XMLDesc()
                        netroot = ET.fromstring(netxml)
                        hostentries = list(netroot.iter('host'))
                        for host in hostentries:
                            if host.get('mac') == mac:
                                return host.get('ip')
                    except:
                        continue
            try:
                ifaces = vm.interfaceAddresses(vir_src_agent if bridged else vir_src_lease, 0)
            except:
                ifaces = {}
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
        conn = self.conn
        if self.get_capabilities()['arch'] == 'aarch64':
            IMAGES.update({i: IMAGES[i].replace('x86_64', 'aarch64').replace('amd64', 'arm64') for i in IMAGES})
        for pool in conn.listAllStoragePools(VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE):
            poolname = pool.name()
            refreshed = False
            while not refreshed:
                try:
                    pool.refresh(0)
                    refreshed = True
                except Exception as e:
                    warning(f"Hit {e} when refreshing pool {poolname}")
                    time.sleep(2)
            poolxml = pool.XMLDesc(0)
            root = ET.fromstring(poolxml)
            for element in list(root.iter('path')):
                poolpath = element.text
                break
            product = list(root.iter('product'))
            if product:
                thinpool = list(root.iter('product'))[0].get('name')
                for volume in self.thinimages(poolpath, thinpool):
                    if volume.endswith('qcow2') or volume.endswith('qc2') or '.' not in volume:
                        images.extend(f"{poolpath}/{volume}")
            for volume in pool.listVolumes():
                if volume.endswith('iso') or volume.endswith('fd'):
                    isos.append(f"{poolpath}/{volume}")
                elif volume.endswith('qcow2') or volume.endswith('qc2') or '.' not in volume:
                    images.append(f"{poolpath}/{volume}")
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
        for element in list(root.iter('{kvirt}info')):
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
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm.snapshotListNames():
            if not snapshots:
                return {'result': 'failure', 'reason': f"VM {name} has snapshots"}
            else:
                for snapshot in vm.snapshotListNames():
                    pprint(f"Deleting snapshot {snapshot}")
                    self.delete_snapshot(snapshot, name)
        ip = self.ip(name)
        status = {0: 'down', 1: 'up'}
        vmxml = vm.XMLDesc(0)
        uuid = vm.UUIDString()
        root = ET.fromstring(vmxml)
        disks = []
        domain, image = None, None
        for element in list(root.iter('{kvirt}info')):
            e = element.find('{kvirt}nvmedisks')
            if e is not None:
                disks.extend(e.text.split(','))
            e = element.find('{kvirt}domain')
            if e is not None:
                domain = e.text
            e = element.find('{kvirt}image')
            if e is not None:
                image = e.text
                if image is not None and ('coreos' in image or 'rhcos' in image or 'fcos' in image):
                    ignition = True
            if domain is not None and image is not None:
                break
        for index, element in enumerate(list(root.iter('disk'))):
            source = element.find('source')
            if source is not None:
                imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                              element.find('source').get('volume')]
                imagefile = next(item for item in imagefiles if item is not None)
                if imagefile.endswith(f"{name}.ISO") or f"{name}.img" in imagefile or f"{name}_" in imagefile:
                    disks.append(imagefile)
                elif imagefile == name:
                    disks.append(imagefile)
                elif uuid in imagefile:
                    disks.append(imagefile)
                else:
                    continue
        if status[vm.isActive()] != "down":
            vm.destroy()
        nvram = False
        for element in list(root.iter('os')):
            firmware = element.get('firmware')
            if element.find('nvram') is not None or (firmware is not None and firmware == 'efi'):
                nvram = True
                break
        if nvram:
            vm.undefineFlags(flags=VIR_DOMAIN_UNDEFINE_KEEP_NVRAM)
        else:
            vm.undefine()
        remainingdisks = []
        pools = []
        thinpools = []
        for disk in disks:
            try:
                volume = conn.storageVolLookupByPath(disk)
                pool = volume.storagePoolLookupByVolume()
                volume.delete(0)
                if pool not in pools:
                    pools.append(pool)
            except:
                remainingdisks.append(disk)
                continue
        if remainingdisks:
            for storage in conn.listAllStoragePools(VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE):
                poolxml = storage.XMLDesc(0)
                storageroot = ET.fromstring(poolxml)
                if list(storageroot.iter('product')):
                    for element in list(storageroot.iter('path')):
                        poolpath = element.text
                        break
                    thinpools.append(poolpath)
            for disk in remainingdisks:
                for p in thinpools:
                    if disk.startswith(p):
                        self._deletelvm(disk)
                        break
        for pool in pools:
            pool.refresh(0)
        for element in list(root.iter('interface')):
            mac = element.find('mac').get('address')
            networktype = element.get('type')
            if networktype == 'user':
                continue
            try:
                network = element.find('source').get('network')
                network = conn.networkLookupByName(network)
                netxml = network.XMLDesc(0)
                netroot = ET.fromstring(netxml)
                for host in list(netroot.iter('host')):
                    hostmac = host.get('mac')
                    iphost = host.get('ip')
                    hostname = host.get('name')
                    if hostmac == mac:
                        hostentry = f"<host mac='{mac}' name='{hostname}' ip='{iphost}'/>"
                        network.update(2, 4, 0, hostentry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                    hostname = host.find('hostname')
                    matchinghostname = f"{name}.{domain}" if domain is not None else name
                    if hostname is not None and (hostname.text == matchinghostname):
                        hostentry = f'<host ip="{iphost}"><hostname>{matchinghostname}</hostname></host>'
                        network.update(2, 10, 0, hostentry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
            except:
                if networktype == 'bridge':
                    bridged = True
        if ip is not None:
            os.system(f"ssh-keygen -q -R {ip} >/dev/null 2>&1")
            # delete hosts entry
            found = False
            hostentry = f"{ip} {name}.* # KVIRT"
            for line in open('/etc/hosts'):
                if re.findall(hostentry, line):
                    found = True
                    break
            if found:
                pprint("Deleting host entry. sudo password might be asked")
                call(f"sudo sed -i '/{hostentry}/d' /etc/hosts", shell=True)
                if bridged and self.host in ['localhost', '127.0.0.1']:
                    try:
                        call("sudo /usr/bin/systemctl restart dnsmasq", shell=True)
                    except:
                        pass
        if ignition:
            ignitionpath = f'/var/lib/libvirt/images/{name}.ign'
            if self.protocol == 'ssh' and self.host not in ['localhost', '127.0.0.1']:
                ignitiondeletecmd = f"ls {ignitionpath} >/dev/null 2>&1 && rm -f {ignitionpath}"
                ignitiondeletecmd = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user,
                                                                   self.host, ignitiondeletecmd)
                call(ignitiondeletecmd, shell=True)
            elif os.path.exists(ignitionpath):
                os.remove(ignitionpath)
        return {'result': 'success'}

    def _xmldisk(self, diskpath, diskdev, diskbus='virtio', diskformat='qcow2', shareable=False, bus=None, slot=None):
        sharexml = '<shareable/>' if shareable else ''
        addressxml = ''
        if bus is not None and slot is not None:
            addressxml = f"<address type='pci' domain='0x0000' bus='0x0{bus}' slot='0x{slot:02x}' function='0x0'/>"
        diskxml = """<disk type='file' device='disk'>
        <driver name='qemu' type='%s' cache='none'/>
        <source file='%s'/>
        <target bus='%s' dev='%s'/>
        %s
        %s
        </disk>""" % (diskformat, diskpath, diskbus, diskdev, addressxml, sharexml)
        return diskxml

    def _xmlvolume(self, path, size, pooltype='file', backing=None, diskformat='qcow2', owner=None):
        ownerxml = f"<owner>{owner}</owner>" if owner is not None else ''
        disktype = 'file' if pooltype == 'file' else 'block'
        size = int(size) * GiB
        if int(size) == 0:
            size = 512 * KiB
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
%s
<mode>0644</mode>
</permissions>
<compat>1.1</compat>
</target>
%s
</volume>""" % (disktype, name, size, path, diskformat, ownerxml, backingstore)
        return volume

    def clone(self, old, new, full=False, start=False):
        conn = self.conn
        try:
            conn.lookupByName(new)
            msg = f"VM {new} already exists"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        except:
            pass
        try:
            oldvm = conn.lookupByName(old)
        except:
            msg = f"Base VM {old} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        if oldvm.isActive() != 0:
            msg = f"Base VM {old} needs to be down"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        oldautostart = oldvm.autostart()
        oldxml = oldvm.XMLDesc(0)
        tree = ET.fromstring(oldxml)
        uuid = list(tree.iter('uuid'))[0]
        tree.remove(uuid)
        for vmname in list(tree.iter('name')):
            vmname.text = new
        firstdisk = True
        for disk in list(tree.iter('disk')):
            if firstdisk or full:
                source = disk.find('source')
                if source is None:
                    continue
                oldpath = source.get('file')
                oldvolume = self.conn.storageVolLookupByPath(oldpath)
                pool = oldvolume.storagePoolLookupByVolume()
                oldinfo = oldvolume.info()
                oldvolumesize = (float(oldinfo[1]) / GiB)
                oldvolumexml = oldvolume.XMLDesc(0)
                backing = None
                voltree = ET.fromstring(oldvolumexml)
                for b in list(voltree.iter('backingStore')):
                    backingstoresource = b.find('path')
                    if backingstoresource is not None:
                        backing = backingstoresource.text
                newpath = oldpath.replace(old, new)
                source.set('file', newpath)
                newvolumexml = self._xmlvolume(newpath, oldvolumesize, backing=backing)
                pool.createXMLFrom(newvolumexml, oldvolume, 0)
                firstdisk = False
            else:
                devices = list(tree.iter('devices'))[0]
                devices.remove(disk)
        for interface in list(tree.iter('interface')):
            mac = interface.find('mac')
            interface.remove(mac)
        if self.host not in ['127.0.0.1', 'localhost']:
            for serial in list(tree.iter('serial')):
                source = serial.find('source')
                source.set('service', str(common.get_free_port()))
        newxml = ET.tostring(tree).decode("utf-8")
        conn.defineXML(newxml)
        vm = conn.lookupByName(new)
        vm.setAutostart(oldautostart)
        if start:
            vm.create()
        return {'result': 'success'}

    def _reserve_ip(self, name, domain, vmxml, nets, force=True, primary=False, networks={}):
        conn = self.conn
        macs = []
        if domain is not None:
            name += f".{domain}"
        for element in list(vmxml.iter('interface')):
            mac = element.find('mac').get('address')
            macs.append(mac)
        for index, net in enumerate(nets):
            ip = net.get('ip')
            netname = net.get('name')
            mac = macs[index]
            reserveip = index == 0 and primary
            reserveip = net.get('reserveip', reserveip)
            if not reserveip or ip is None or netname is None:
                continue
            elif reserveip and ip is None:
                warning("Skipping reserveip because no ip was provided")
                continue
            if netname not in networks:
                warning(f"Skipping incorrect network {netname}")
                continue
            elif networks[netname]['type'] == 'bridged':
                warning(f"Skipping bridge {netname}")
                continue
            network = conn.networkLookupByName(netname)
            oldnetxml = network.XMLDesc()
            root = ET.fromstring(oldnetxml)
            dhcplist = list(root.iter('dhcp'))
            if not dhcplist:
                warning(f"Skipping network {netname} as it doesnt have dhcp")
                continue
            dhcp = dhcplist[0]
            for hostentry in list(dhcp.iter('host')):
                currentip = hostentry.get('ip')
                currentname = hostentry.get('name')
                currentmac = hostentry.get('mac')
                if currentip == ip:
                    if currentname == name and currentmac is not None and currentmac == mac:
                        warning(f"Skipping reserved ip as there is an existing entry for ip {ip} and mac {mac}")
                        return
                    else:
                        warning(f"Removing old ip entry for ip {ip} and name {currentname}")
                        hostentryxml = f"<host name='{currentname}' ip='{ip}'/>"
                        network.update(2, 4, 0, hostentryxml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
            for ipentry in list(root.iter('ip')):
                attributes = ipentry.attrib
                firstip = attributes.get('address')
                netmask = next(a for a in [attributes.get('netmask'), attributes.get('prefix')] if a is not None)
                netip = ip_network(f'{firstip}/{netmask}', strict=False)
                dhcp = list(root.iter('dhcp'))
                if not dhcp:
                    continue
                if not ip_address(ip) in netip:
                    continue
                pprint(f"Adding a reserved ip entry for ip {ip} and mac {mac}")
                if ':' in ip:
                    entry = f'<host id="00:03:00:01:{mac}" name="{name}" ip="{ip}" />'
                else:
                    entry = f'<host mac="{mac}" name="{name}" ip="{ip}" />'
                try:
                    network.update(4, 4, 0, entry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                except Exception as e:
                    warning(e)

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, start=True):
        conn = self.conn
        bridged = False
        for index, net in enumerate(nets):
            if isinstance(net, str):
                netname = net
                net = {'name': netname}
            reservedns = index == 0 and primary
            reservedns = net.get('reservedns', reservedns)
            if not reservedns:
                continue
            netname = net.get('name')
            if domain is not None and domain != netname:
                pprint(f"Creating dns entry for {name}.{domain} in network {netname}")
            else:
                pprint(f"Creating dns entry for {name} in network {netname}")
            try:
                network = conn.networkLookupByName(netname)
            except:
                warning(f"Bridged network {netname} can't be used for dns entries")
                return
            if ip is None:
                if isinstance(net, dict) and 'ip' in net:
                    ip = net['ip']
                elif not start:
                    warning("Ignoring reservedns as vm won't be powered up")
                    continue
                else:
                    counter = 0
                    while counter != 300:
                        ip = self.ip(name)
                        if ip is None:
                            time.sleep(5)
                            pprint("Waiting 5 seconds to grab ip...")
                            counter += 5
                        else:
                            break
                if ip is None:
                    error(f"Couldn't figure ip to assign dns entry {name} in net {netname}")
                    continue
            if bridged:
                self._create_host_entry(name, ip, netname, domain)
            else:
                oldnetxml = network.XMLDesc()
                root = ET.fromstring(oldnetxml)
                dns = list(root.iter('dns'))
                if not dns:
                    base = list(root.iter('network'))[0]
                    dns = ET.Element("dns")
                    base.append(dns)
                    newxml = ET.tostring(root).decode("utf-8")
                    conn.networkDefineXML(newxml)
                elif dns[0].get('enable', 'yes') == 'no':
                    warning("Ignoring reservedns as network was created with dns explicitely disabled")
                    continue
                fqdn = f"{name}.{domain}" if domain is not None and not name.endswith(domain) else name
                hostnamexml = f'<hostname>{fqdn}</hostname>'
                alias = [f"{entry}.{domain}" if domain is not None and
                         not entry.endswith(domain) else entry for entry in alias]
                aliasxml = [f"<hostname>{entry}</hostname>" for entry in alias]
                if dns:
                    for hostentry in list(dns[0].iter('host')):
                        currentip = hostentry.get('ip')
                        if currentip == ip:
                            currenthostnames = []
                            for hostnameentry in list(hostentry.iter('hostname')):
                                currenthostnames.append(hostnameentry.text)
                            newalias = [a for a in alias if a not in currenthostnames]
                            if fqdn not in currenthostnames or newalias:
                                if fqdn not in currenthostnames:
                                    hostentry.append((ET.fromstring(hostnamexml)))
                                if newalias:
                                    newaliasxml = [f"<hostname>{entry}</hostname>" for entry in newalias]
                                    for entry in newaliasxml:
                                        hostentry.append((ET.fromstring(entry)))
                                newhostxml = ET.tostring(hostentry).decode("utf-8")
                                network.update(2, 10, 0, newhostxml, 0)
                                network.update(4, 10, 0, newhostxml, 0)
                            else:
                                pprint(f"Skipping existing entry for ip {ip} and name {fqdn}")
                            return
                for entry in aliasxml:
                    hostnamexml += entry
                dnsentry = f'<host ip="{ip}">{hostnamexml}</host>'
                if force:
                    for host in list(root.iter('host')):
                        iphost = host.get('ip')
                        machost = host.get('mac')
                        if machost is None:
                            existing = []
                            for hostname in list(host.iter('hostname')):
                                existing.append(hostname.text)
                            if fqdn in existing:
                                if iphost == ip:
                                    pprint(f"Skipping existing dns entry for {fqdn}")
                                else:
                                    oldentry = f'<host ip="{iphost}"></host>'
                                    pprint(f"Removing old dns entry for ip {iphost}")
                                    network.update(2, 10, 0, oldentry,
                                                   VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                try:
                    network.update(4, 10, 0, dnsentry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                except Exception as e:
                    error(e)

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
                    pprint("Waiting 5 seconds to grab ip and create /etc/host entry...")
                    counter += 5
                else:
                    break
        if ip is None:
            error("Couldn't assign Host")
            return
        self._create_host_entry(name, ip, netname, domain)

    def handler(self, stream, data, file_):
        return file_.read(data)

    def _uploadimage(self, name, pool='default', pooltype='file', origin='/tmp', suffix='.ISO', size=0):
        name = f"{name}{suffix}"
        conn = self.conn
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in list(root.iter('path')):
            poolpath = element.text
            break
        imagepath = f"{poolpath}/{name}"
        imagexml = self._xmlvolume(path=imagepath, size=size, diskformat='raw', pooltype=pooltype)
        try:
            pool.createXML(imagexml, 0)
        except libvirtError as e:
            warning(f"Got {e} when creating iso")
        imagevolume = conn.storageVolLookupByPath(imagepath)
        stream = conn.newStream(0)
        imagevolume.upload(stream, 0, 0)
        with open(f"{origin}/{name}", 'rb') as ori:
            stream.sendAll(self.handler, ori)
            stream.finish()

    def update_metadata(self, name, metatype, metavalue, append=False):
        ET.register_namespace('kvirt', 'kvirt')
        conn = self.conn
        vm = conn.lookupByName(name)
        if not vm:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        flags = VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG if vm.isActive() == 1 else VIR_DOMAIN_AFFECT_CONFIG
        try:
            metadataxml = vm.metadata(2, 'kvirt', 0)
        except:
            return {'result': 'failure', 'reason': f"missing metadata field in VM {name} xml"}
        root = ET.fromstring(metadataxml)
        kroot, kmeta = None, None
        for element in list(root.iter('info')):
            kroot = element
            break
        for element in list(root.iter(metatype)):
            kmeta = element
            break
        if kmeta is None:
            kmeta = ET.Element(metatype)
            kroot.append(kmeta)
        if append and kmeta.text is not None:
            kmeta.text += f",{str(metavalue)}"
        else:
            kmeta.text = str(metavalue)
        metadataxml = ET.tostring(root).decode("utf-8")
        vm.setMetadata(2, metadataxml, 'kvirt', 'kvirt', flags=flags)
        return {'result': 'success'}

    def update_information(self, name, information):
        conn = self.conn
        vm = conn.lookupByName(name)
        vm.setMetadata(0, information, None, None)
        return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        cpunode = list(root.iter('vcpu'))[0]
        cpuattributes = cpunode.attrib
        if vm.isActive() == 0:
            if 'current' in cpuattributes and cpuattributes['current'] != numcpus:
                if numcpus < int(cpuattributes['current']):
                    error("Can't remove cpus while vm is up")
                    return {'result': 'failure', 'reason': f"VM {name} not found"}
                else:
                    vm.setVcpus(numcpus)
                    return {'result': 'success'}
            warning("Note it will only be effective upon next start")
        cpunode.text = str(numcpus)
        newxml = ET.tostring(root).decode("utf-8")
        conn.defineXML(newxml)
        return {'result': 'success'}

    def update_cpuflags(self, name, cpuflags, disable=False):
        addflags, removeflags = [], []
        for flag in cpuflags:
            if isinstance(flag, str):
                if disable:
                    removeflags.append(flag)
                else:
                    addflags.append(flag)
            elif isinstance(flag, dict) and 'name' in flag:
                flagname = flag['name']
                if 'policy' in flag and isinstance(flag['policy'], str) and flag['policy'] == 'disable':
                    removeflags.append(flagname)
                elif 'enable' in flag and isinstance(flag['enable'], bool):
                    if flag['enable']:
                        addflags.append(flagname)
                    else:
                        removeflags.append(flagname)
                else:
                    addflags.append(flagname)
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        cpu = list(root.iter('cpu'))[0]
        if vm.isActive() != 0:
            warning("Note it will only be effective upon next start")
        for entry in list(cpu.iter('feature')):
            attrib = entry.attrib
            feature, policy = attrib['name'], attrib['policy']
            if feature in removeflags and policy not in ['disable', 'forbid']:
                pprint(f"Removing flag {feature}")
                cpu.remove(entry)
            elif feature in addflags:
                if policy in ['enable', 'require', 'force']:
                    del addflags[feature]
                else:
                    cpu.remove(entry)
                    pprint(f"Removing flag {feature}")
        for feature in addflags:
            pprint(f"Adding flag {feature}")
            new_entry = f"<feature policy='require' name='{feature}'/>"
            cpu.append((ET.fromstring(new_entry)))
        newxml = ET.tostring(root).decode("utf-8")
        conn.defineXML(newxml)
        return {'result': 'success'}

    def update_memory(self, name, memory):
        conn = self.conn
        memory = str(int(memory) * 1024)
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        memorynode = list(root.iter('memory'))[0]
        memorynode.text = memory
        currentmemory = list(root.iter('currentMemory'))[0]
        maxmemory = list(root.iter('maxMemory'))
        if maxmemory:
            diff = int(memory) - int(currentmemory.text)
            if diff > 0:
                xml = f"<memory model='dimm'><target><size unit='KiB'>{diff}</size><node>0</node></target></memory>"
                vm.attachDeviceFlags(xml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
        elif vm.isActive() != 0:
            warning("Note it will only be effective upon next start")
        currentmemory.text = memory
        newxml = ET.tostring(root).decode("utf-8")
        conn.defineXML(newxml)
        return {'result': 'success'}

    def update_iso(self, name, iso):
        source = None
        if iso is not None:
            if self.host in ['localhost', '127.0.0.1'] and os.path.exists(iso):
                iso = os.path.abspath(iso)
            else:
                source = None
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
                    error(f"Iso {iso} not found.Leaving...")
                    return {'result': 'failure', 'reason': f"Iso {iso} not found"}
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        cdromfound = False
        for element in list(root.iter('disk')):
            disktype = element.get('device')
            if disktype != 'cdrom':
                continue
            cdromfound = True
            if source is None:
                source = element.find('source')
            if iso is None:
                if source is not None:
                    element.remove(source)
            elif source is not None:
                source.set('file', iso)
            else:
                isoxml = f"<source file='{iso}'/>"
                element.append((ET.fromstring(isoxml)))
            break
        if not cdromfound:
            isoxml = """<disk type='file' device='cdrom'>
<driver name='qemu' type='raw'/>
<source file='%s'/>
<target dev='hdc' bus='sata'/>
<address type='drive' controller='0' bus='0' target='0' unit='20'/>
<readonly/>
</disk>""" % iso
            base = list(root.iter('devices'))[-1]
            base.append((ET.fromstring(isoxml)))
        newxml = ET.tostring(root).decode("utf-8")
        if vm.isActive() != 0:
            warning("Note it will only be effective upon next start")
        conn.defineXML(newxml)
        return {'result': 'success'}

    def update_flavor(self, name, flavor):
        pprint("Not implemented")
        return {'result': 'success'}

    def remove_cloudinit(self, name):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        for element in list(root.iter('disk')):
            disktype = element.get('device')
            if disktype == 'cdrom':
                source = element.find('source')
                path = source.get('file')
                if source is None:
                    break
                volume = conn.storageVolLookupByPath(path)
                volume.delete(0)
                element.remove(source)
        newxml = ET.tostring(root).decode("utf-8")
        conn.defineXML(newxml)

    def update_start(self, name, start=True):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if start:
            vm.setAutostart(1)
        else:
            vm.setAutostart(0)
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        conn = self.conn
        diskformat = 'qcow2'
        if size < 1:
            error(f"Incorrect disk size for disk {name}")
            return None
        if not thin:
            diskformat = 'raw'
        if pool is None:
            error(f"Missing Pool for disk {name}")
            return None
        elif '/' in pool:
            pools = [p for p in conn.listStoragePools() if self.get_pool_path(p) == pool]
            if not pools:
                error(f"Pool not found for disk {name}")
                return None
            else:
                pool = pools[0]
        else:
            try:
                pool = conn.storagePoolLookupByName(pool)
            except:
                error(f"Pool {pool} not found for disk {name}")
                return None
        poolxml = pool.XMLDesc(0)
        poolroot = ET.fromstring(poolxml)
        pooltype = list(poolroot.iter('pool'))[0].get('type')
        for element in list(poolroot.iter('path')):
            poolpath = element.text
            break
        if image is not None:
            volumes = {}
            for p in conn.listStoragePools():
                poo = conn.storagePoolLookupByName(p)
                for vol in poo.listAllVolumes():
                    volumes[vol.name()] = vol.path()
            if image not in volumes and image not in list(volumes.values()):
                error(f"Invalid image {image} for disk {name}")
                return None
            if image in volumes:
                image = volumes[image]
        pool.refresh(0)
        diskpath = f"{poolpath}/{name}"
        if pooltype == 'logical':
            diskformat = 'raw'
        volxml = self._xmlvolume(path=diskpath, size=size, pooltype=pooltype,
                                 diskformat=diskformat, backing=image)
        pool.createXML(volxml, 0)
        return diskpath

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}, diskname=None):
        conn = self.conn
        diskformat = 'qcow2'
        diskbus = interface
        if size < 1:
            error("Incorrect size.Leaving...")
            return {'result': 'failure', 'reason': "Incorrect size"}
        if not thin:
            diskformat = 'raw'
        if novm:
            try:
                return self.create_disk(name=name, size=size, pool=pool, thin=thin, image=image)
            except Exception as e:
                error(f"Couldn't create disk. Hit {e}")
                return {'result': 'failure', 'reason': f"Couldn't create disk. Hit {e}"}
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        currentdisk = 0
        diskpaths = []
        virtio_index, scsi_index, ide_index = 0, 0, 0
        for element in list(root.iter('disk')):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            device = element.find('target').get('dev')
            imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                          element.find('source').get('volume')]
            path = next(item for item in imagefiles if item is not None)
            diskpaths.append(path)
            if device.startswith('sd'):
                scsi_index += 1
            elif device.startswith('hd'):
                ide_index += 1
            else:
                virtio_index += 1
            currentdisk += 1
        if diskname is not None and '_' in diskname:
            diskindex = int(os.path.splitext(diskname)[0].split('_')[-1])
            virtio_index, scsi_index, ide_index = diskindex, diskindex, diskindex
        else:
            diskindex = currentdisk
        if interface == 'scsi':
            diskdev = f"sd{string.ascii_lowercase[scsi_index]}"
        elif interface == 'ide':
            diskdev = f"hd{string.ascii_lowercase[ide_index]}"
        else:
            diskdev = f"vd{string.ascii_lowercase[virtio_index]}"
        if existing is None:
            storagename = f"{name}_{diskindex}.img"
            diskpath = self.create_disk(name=storagename, size=size, pool=pool, thin=thin, image=image)
        elif existing in diskpaths:
            error(f"Disk {existing} already in VM {name}")
            return {'result': 'success'}
        else:
            if '/' not in existing:
                existing = f"{self.get_pool_path(pool)}/{existing}"
            diskpath = existing
        bus, slot = None, None
        if vm.isActive() == 1 and 'q35' in vm.XMLDesc(0):
            bus, slot = self._get_pcie_data(vm)
            if bus is None:
                msg = f"Missing pcie-to-pci-bridge in vm. Shutdown {name} first"
                error(msg)
                return {'result': 'failure', 'reason': msg}
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat,
                                shareable=shareable, bus=bus, slot=slot)
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
            error(f"Pool {poolname} not found. Leaving...")
            return {'result': 'failure', 'reason': f"Pool {poolname} not found"}
        try:
            volume = pool.storageVolLookupByName(name)
            volume.delete()
        except:
            error(f"Disk {name} not found in pool {poolname}. Leaving...")
            return {'result': 'failure', 'reason': f"Disk {name} not found in pool {poolname}. Leaving..."}

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        conn = self.conn
        if name is None:
            if diskname is None:
                msg = "Neither vm name or diskname was provided"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            if '_' in os.path.basename(diskname) and diskname.endswith('.img'):
                name = os.path.basename(diskname).split('_')[0]
                pprint(f"Using {name} as vm associated to this disk")
            else:
                result = self.delete_disk_by_name(os.path.basename(diskname), pool)
                return result
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        found = False
        missing_disks = []
        for element in list(root.iter('disk')):
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
                warning(f"Disk {diskpath} was not found.Removing it from vm's definition")
                diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
                missing_disks.append(diskxml)
                found = True
                continue
            if volume.name() == diskname or volume.path() == diskname or diskdev == os.path.basename(diskname):
                diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
                if vm.isActive() == 1:
                    vm.detachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                else:
                    vm.detachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_CONFIG)
                volume.delete(0)
                vm = conn.lookupByName(name)
                vmxml = vm.XMLDesc(0)
                conn.defineXML(vmxml)
                found = True
        if missing_disks:
            for diskxml in missing_disks:
                if vm.isActive() == 1:
                    vm.detachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                else:
                    vm.detachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_CONFIG)
            vm = conn.lookupByName(name)
            vmxml = vm.XMLDesc(0)
            conn.defineXML(vmxml)
        if not found:
            error(f"Disk {diskname} not found in {name}")
            return {'result': 'failure', 'reason': f"Disk {diskname} not found in {name}"}
        return {'result': 'success'}

    def detach_disks(self, name):
        pprint(f"Detaching non primary disks from {name}")
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        all_disks = list(root.iter('disk'))
        vm_disks = all_disks[1:] if len(all_disks) > 1 else []
        for element in vm_disks:
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            diskdev = element.find('target').get('dev')
            diskbus = element.find('target').get('bus')
            diskformat = element.find('driver').get('type')
            imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                          element.find('source').get('volume')]
            diskpath = next(item for item in imagefiles if item is not None)
            diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
            if vm.isActive() == 1:
                vm.detachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
            else:
                vm.detachDeviceFlags(diskxml, VIR_DOMAIN_AFFECT_CONFIG)
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

    def add_nic(self, name, network, model='virtio'):
        conn = self.conn
        networks = {}
        try:
            for interface in conn.listInterfaces():
                networks[interface] = 'bridge'
        except:
            pass
        for net in conn.listAllNetworks():
            networks[net.name()] = 'network'
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if network not in networks:
            error(f"Network {network} not found")
            return {'result': 'failure', 'reason': f"Network {network} not found"}
        else:
            networktype = networks[network]
            source = f"<source {networktype}='{network}'/>"
        modelxml = f"<model type='{model}'/>"
        addressxml = ""
        if vm.isActive() == 1 and 'q35' in vm.XMLDesc(0):
            bus, slot = self._get_pcie_data(vm)
            if bus is None:
                msg = f"Missing pcie-to-pci-bridge in vm. Shutdown {name} first"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            addressxml = f"<address type='pci' domain='0x0000' bus='0x0{bus}' slot='0x{slot:02x}' function='0x0'/>"
        nicxml = """<interface type='%s'>
                    %s
                    %s
                    %s
                    </interface>""" % (networktype, modelxml, addressxml, source)
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
            networks[n] = 'bridge'
        for n in conn.listAllNetworks():
            networks[n.name()] = 'network'
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        networktype, mac, source = None, None, None
        for element in list(root.iter('interface')):
            device = f"eth{nicnumber}"
            if device == interface:
                mac = element.find('mac').get('address')
                networktype = element.get('type')
                if networktype == 'bridge':
                    network = element.find('source').get('bridge')
                    source = f"<source {networktype}='{network}'/>"
                else:
                    network = element.find('source').get('network')
                    source = f"<source {networktype}='{network}'/>"
                break
            else:
                nicnumber += 1
        if networktype is None or mac is None or source is None:
            error(f"Interface {interface} not found")
            return {'result': 'failure', 'reason': f"Interface {interface} not found"}
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
                pprint(f"Pool {name} already there.Leaving...")
                return {'result': 'success'}
        if pooltype == 'dir':
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if not os.path.exists(poolpath):
                    try:
                        os.makedirs(poolpath)
                    except OSError:
                        reason = f"Couldn't create directory {poolpath}.Leaving..."
                        error(reason)
                        return {'result': 'failure', 'reason': reason}
            elif self.protocol == 'ssh':
                cmd1 = 'ssh %s -p %s %s@%s "test -d %s || sudo mkdir %s"' % (self.identitycommand, self.port, self.user,
                                                                             self.host, poolpath, poolpath)
                cmd2 = 'ssh %s -p %s -t %s@%s "sudo chown %s %s"' % (self.identitycommand, self.port, self.user,
                                                                     self.host, user, poolpath)
                if self.user != 'root':
                    setfacl = f"sudo setfacl -m u:{self.user}:rwx {poolpath}"
                    cmd3 = 'ssh %s -p %s -t %s@%s "%s"' % (self.identitycommand, self.port, self.user, self.host,
                                                           setfacl)

                return1 = os.system(cmd1)
                if return1 > 0:
                    reason = f"Couldn't create directory {poolpath}.Leaving..."
                    error(reason)
                    return {'result': 'failure', 'reason': reason}
                return2 = os.system(cmd2)
                if return2 > 0:
                    reason = f"Couldn't change permission of directory {poolpath} to qemu"
                    error(reason)
                    return {'result': 'failure', 'reason': reason}
                if self.user != 'root':
                    return3 = os.system(cmd3)
                    if return3 > 0:
                        reason = f"Couldn't run setfacl for user {self.user} in {poolpath}"
                        error(reason)
                        return {'result': 'failure', 'reason': reason}
            else:
                reason = f"Make sure {name} directory exists on hypervisor"
                error(reason)
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
            thinpoolxml = f"<product name='{thinpool}'/>" if thinpool is not None else ''
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
            reason = f"Invalid pool type {pooltype}.Leaving..."
            error(reason)
            return {'result': 'failure', 'reason': reason}
        try:
            pool = conn.storagePoolDefineXML(poolxml, 0)
            pool.setAutostart(True)
            pool.create()
            return {'result': 'success'}
        except Exception as e:
            error(e)
            return {'result': 'failure', 'reason': e}

    def delete_image(self, image, pool=None):
        conn = self.conn
        shortname = os.path.basename(image)
        if pool is not None:
            try:
                poolname = pool
                pool = conn.storagePoolLookupByName(pool)
                pool.refresh(0)
            except:
                return {'result': 'failure', 'reason': f'Pool {poolname} not found'}
            try:
                volume = pool.storageVolLookupByName(shortname)
                volume.delete(0)
                return {'result': 'success'}
            except:
                return {'result': 'failure', 'reason': f'Image {image} not found'}
        else:
            for poolname in conn.listStoragePools():
                try:
                    pool = conn.storagePoolLookupByName(poolname)
                    try:
                        pool.refresh(0)
                    except Exception as e:
                        warning(f"Hit {e} when refreshing pool {poolname}")
                        continue
                    volume = pool.storageVolLookupByName(shortname)
                    volume.delete(0)
                    return {'result': 'success'}
                except:
                    continue
        return {'result': 'failure', 'reason': f'Image {image} not found'}

    def add_image(self, url, pool, cmds=[], name=None, size=None, convert=False):
        poolname = pool
        shortimage = os.path.basename(url).split('?')[0]
        need_uncompress = any(shortimage.endswith(suffix) for suffix in ['.gz', '.xz', '.bz2', '.zst'])
        extension = os.path.splitext(shortimage)[1].replace('.', '') if need_uncompress else None
        if name is None:
            name = shortimage.replace('.gz', '').replace('.xz', '').replace('.bz2', '').replace('.zst', '')
        if convert:
            name += '.raw'
        full_name = f"{name}.{extension}" if need_uncompress else name
        conn = self.conn
        volumes = []
        try:
            pool = conn.storagePoolLookupByName(pool)
            for vol in pool.listAllVolumes():
                volumes.append(vol.name())
        except:
            return {'result': 'failure', 'reason': f"Pool {poolname} not found"}
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        pooltype = list(root.iter('pool'))[0].get('type')
        poolpath = list(root.iter('path'))[0].text
        downloadpath = poolpath if pooltype == 'dir' else '/tmp'
        if name in volumes:
            pprint(f"Image {name} already there.Leaving...")
            return {'result': 'success', 'found': True}
        if self.host == 'localhost' or self.host == '127.0.0.1':
            downloadcmd = f"curl -C - -Lko {downloadpath}/{full_name} -f '{url}'"
        elif self.protocol == 'ssh':
            host = self.host.replace('[', '').replace(']', '')
            downloadcmd = 'ssh %s -p %s %s@%s "curl -C - -Lko %s/%s -f \'%s\'"' % (self.identitycommand, self.port,
                                                                                   self.user, host, downloadpath,
                                                                                   full_name, url)
        code = call(downloadcmd, shell=True)
        if code == 23:
            pprint("Consider running the following command on the hypervisor:")
            setfacluser = self.user
            if self.host in ['localhost', '127.0.0.1']:
                if not os.path.exists("/i_am_a_container"):
                    setfacluser = getpwuid(os.getuid()).pw_name
                else:
                    setfacluser = "your_user"
            pprint(f"sudo setfacl -m u:{setfacluser}:rwx {downloadpath}")
            return {'result': 'failure', 'reason': "Permission issues"}
        elif code != 0:
            return {'result': 'failure', 'reason': "Unable to download indicated image"}
        if need_uncompress:
            executable = {'xz': 'unxz', 'gz': 'gunzip', 'bz2': 'bunzip2', 'zst': 'zstd'}
            flag = '--decompress' if extension == 'zstd' else '-f'
            executable = executable[extension]
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if which(executable) is not None:
                    uncompresscmd = f"{executable} {flag} {poolpath}/{full_name}"
                    os.system(uncompresscmd)
                else:
                    error(f"{executable} not found. Can't uncompress image")
                    return {'result': 'failure', 'reason': f"{executable} not found. Can't uncompress image"}
            elif self.protocol == 'ssh':
                uncompresscmd = 'ssh %s -p %s %s@%s "%s %s %s/%s"' % (self.identitycommand, self.port, self.user,
                                                                      self.host, executable, flag, poolpath, full_name)
                os.system(uncompresscmd)
        if cmds:
            if self.host == 'localhost' or self.host == '127.0.0.1':
                if which('virt-customize') is not None:
                    for cmd in cmds:
                        cmd = f"virt-customize -a {poolpath}/{name} --run-command '{cmd}'"
                        os.system(cmd)
            elif self.protocol == 'ssh':
                for cmd in cmds:
                    cmd = 'ssh %s -p %s %s@%s "virt-customize -a %s/%s --run-command \'%s\'"' % (self.identitycommand,
                                                                                                 self.port, self.user,
                                                                                                 self.host, poolpath,
                                                                                                 name, cmd)
                    os.system(cmd)
        if convert:
            name = name.replace('.raw', '')
            cmd = f"qemu-img convert -O qcow2 {poolpath}/{name}.raw {poolpath}/{name}"
            if self.host == 'localhost' or self.host == '127.0.0.1':
                os.system(cmd)
            elif self.protocol == 'ssh':
                cmd = 'ssh %s -p %s %s@%s "%s"' % (self.identitycommand, self.port, self.user, self.host, cmd)
                os.system(cmd)
        if pooltype in ['logical', 'zfs']:
            product = list(root.iter('product'))
            if product:
                thinpool = list(root.iter('product'))[0].get('name')
            else:
                thinpool = None
            self.add_image_to_deadpool(poolname, pooltype, poolpath, name, thinpool)
            return {'result': 'success'}
        pool.refresh()
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        conn = self.conn
        networks = self.list_networks()
        if name in networks:
            msg = f"Network {name} already exists"
            return {'result': 'failure', 'reason': msg}
        if 'macvtap' in overrides and overrides['macvtap']:
            if 'nic' not in overrides:
                return {'result': 'failure', 'reason': "Missing nic parameter"}
            else:
                nic = overrides['nic']
                networkxml = """<network>
                                <name>{name}</name>
                                <forward mode="bridge">
                                <interface dev="{nic}"/>
                                </forward>
                                </network>""".format(name=name, nic=nic)
                if self.debug:
                    print(networkxml)
                new_net = conn.networkDefineXML(networkxml)
                new_net.setAutostart(True)
                new_net.create()
                return {'result': 'success'}
        if 'ovs' in overrides and overrides['ovs']:
            bridgescmd = f"ovs-vsctl list-br | grep name || ovs-vsctl add-br {name}"
            if self.protocol == 'ssh' and self.host not in ['localhost', '127.0.0.1']:
                bridgescmd = 'ssh %s -p %s %s@%s "%s"' % (self.identitycommand, self.port, self.user, self.host,
                                                          bridgescmd)
            os.system(bridgescmd)
            portgroupxml = "<portgroup name='default' default='yes'/>"
            if 'vlans' in overrides and isinstance(overrides['vlans'], list) and overrides['vlans']:
                for vlan in overrides['vlans']:
                    if not str(vlan).isnumeric():
                        warning(f"Ignoring vlan {vlan}")
                    else:
                        portgroupxml += f"<portgroup name='vlan-{vlan}'><vlan><tag id='{vlan}'/></vlan></portgroup>"
            networkxml = """<network>
                            <metadata>
                            <kvirt:info xmlns:kvirt="kvirt">
                            <kvirt:ovs>true</kvirt:ovs>
                            </kvirt:info>
                            </metadata>
                            <name>{name}</name>
                            <bridge name='{name}'/>
                            <forward mode="bridge">
                            <virtualport type='openvswitch'/>
                            {portgroupxml}
                            </forward>
                            </network>""".format(name=name, portgroupxml=portgroupxml)
            if self.debug:
                print(networkxml)
            new_net = conn.networkDefineXML(networkxml)
            new_net.setAutostart(True)
            new_net.create()
            return {'result': 'success'}
        if 'bridge' in overrides and overrides['bridge']:
            bridgename = overrides.get('bridgename', name)
            networkxml = """<network>
                            <name>{name}</name>
                            <bridge name='{bridgename}'/>
                            <forward mode="bridge"/>
                            </network>""".format(name=name, bridgename=bridgename)
            if self.debug:
                print(networkxml)
            new_net = conn.networkDefineXML(networkxml)
            new_net.setAutostart(True)
            new_net.create()
            return {'result': 'success'}
        if cidr is None:
            return {'result': 'failure', 'reason': "Missing Cidr"}
        cidrs = [networks[n]['cidr'] for n in networks]
        cidrs.extend([networks[n]['dual_cidr'] for n in networks if 'dual_cidr' in networks[n]])
        try:
            cidr_range = ip_network(cidr)
        except:
            return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
        if cidr in cidrs:
            return {'result': 'failure', 'reason': f"Cidr {cidr} already exists"}
        gateway = str(cidr_range[1])
        family = 'ipv6' if ':' in gateway else 'ipv4'
        if dhcp:
            start = overrides.get('dhcp_start') or str(cidr_range[2])
            end = overrides.get('dhcp_end') or str(cidr_range[65535 if family == 'ipv6' else -2])
            dhcpxml = f"<dhcp><range start='{start}' end='{end}'/>"
            if 'pxe' in overrides:
                pxe = overrides['pxe']
                del overrides['pxe']
                dhcpxml = f"{dhcpxml}<bootp file='pxelinux.0' server='{pxe}'/>"
            dhcpxml = f"{dhcpxml}</dhcp>"
        else:
            dhcpxml = ''
        if 'forward_mode' in overrides:
            forward_mode = overrides['forward_mode']
            if forward_mode not in ['open', 'route']:
                return {'result': 'failure', 'reason': f"Invalid forward_mode {forward_mode}"}
            forwardxml = f"<forward mode='{forward_mode}'></forward>"
        elif nat:
            forwardxml = "<forward mode='nat'><nat><port start='1024' end='65535'/></nat></forward>"
        else:
            forwardxml = ''
        localdomain = "no"
        if 'localdomain' in overrides and overrides['localdomain']:
            localdomain = "yes"
        if domain is not None:
            domainxml = f"<domain name='{domain}' localOnly='{localdomain}'/>"
        else:
            domainxml = f"<domain name='{name}' localOnly='{localdomain}'/>"
        if len(name) < 16:
            bridgename = name if name != 'default' else 'virbr0'
            bridgexml = f"<bridge name='{bridgename}' stp='on' delay='0'/>"
        else:
            return {'result': 'failure', 'reason': f"network {name} is more than 16 characters"}
        prefix = cidr.split('/')[1]
        metadata = """<metadata>
<kvirt:info xmlns:kvirt="kvirt">
<kvirt:plan>{plan}</kvirt:plan>
</kvirt:info>
</metadata>""".format(plan=plan)
        mtuxml = f'<mtu size="{overrides["mtu"]}"/>'if 'mtu' in overrides else ''
        dualxml = ''
        if 'dual_cidr' in overrides:
            dualcidr = overrides['dual_cidr']
            dualfamily = 'ipv6' if ':' in dualcidr else 'ipv4'
            if dualfamily == family:
                return {'result': 'failure', 'reason': f"Dual Cidr {dualfamily} needs to be of a different family"}
            try:
                dual_range = ip_network(dualcidr)
            except:
                return {'result': 'failure', 'reason': f"Invalid Dual Cidr {dualcidr}"}
            dualgateway = str(dual_range[1])
            dualstart = str(dual_range[2])
            dualend = str(dual_range[65535 if dualfamily == 'ipv6' else -2])
            dualprefix = dualcidr.split('/')[1]
            if dhcp:
                dualdhcpxml = f"<dhcp><range start='{dualstart}' end='{dualend}' /></dhcp>"
            else:
                dualdhcpxml = ""
            dualxml = f"<ip address='{dualgateway}' prefix='{dualprefix}' family='{dualfamily}'>{dualdhcpxml}</ip>"
        dnsxml = ''
        if 'forwarders' in overrides:
            forwarders = overrides['forwarders']
            forwarderxml = '\n'.join("<forwarder domain='%s' addr='%s'/>" % (entry['domain'],
                                                                             entry['address']) for entry in forwarders)
            dnsxml = f"<dns>{forwarderxml}</dns>"
        elif 'dns' in overrides and isinstance(overrides['dns'], bool):
            dnsvalue = 'yes' if overrides['dns'] else 'no'
            dnsxml = f"<dns enable='{dnsvalue}' />"
        namespace = ''
        dnsmasqxml = ''
        dhcpoptions = {key: overrides[key] for key in overrides if key in DHCPKEYWORDS or key.isdigit()}
        if dhcpoptions:
            namespace = "xmlns:dnsmasq='http://libvirt.org/schemas/network/dnsmasq/1.0'"
            dnsmasqxml = "<dnsmasq:options>"
            for key in dhcpoptions:
                option = 'option'
                if family == 'ipv6':
                    option += '6'
                option = key if key.isdigit() else f"{option}:{key}"
                dnsmasqxml += f'<dnsmasq:option value="dhcp-option={option},{dhcpoptions[key]}"/>'
            dnsmasqxml += "</dnsmasq:options>"
        in_average = overrides.get('bandwidth_inbound_average')
        in_peak = overrides.get('bandwidth_inbound_peak')
        in_burst = overrides.get('bandwidth_inbound_burst')
        if in_average is not None and in_peak is not None and in_burst is not None:
            out_average = overrides.get('bandwidth_outbound_average') or in_average
            out_peak = overrides.get('bandwidth_outbound_peak') or in_peak
            out_burst = overrides.get('bandwidth_outbound_burst') or in_burst
            bandwidthxml = '<bandwidth>'
            bandwidthxml += f'<inbound average="{in_average}" peak="{in_peak}" burst="{in_burst}" />'
            bandwidthxml += f'<outbound average="{out_average}" peak="{out_peak}" burst="{out_burst}" />'
            bandwidthxml += '</bandwidth>'
        else:
            bandwidthxml = ""
        networkxml = """<network {namespace}><name>{name}</name>
{dnsmasqxml}
{metadata}
{mtuxml}
{forwardxml}
{bandwidthxml}
{bridgexml}
{domainxml}
{dnsxml}
<ip address='{gateway}' prefix='{prefix}' family='{family}'>
{dhcpxml}
</ip>
{dualxml}
</network>""".format(name=name, metadata=metadata, mtuxml=mtuxml, forwardxml=forwardxml,
                     bandwidthxml=bandwidthxml, bridgexml=bridgexml, domainxml=domainxml,
                     dnsxml=dnsxml, gateway=gateway, prefix=prefix, family=family, dhcpxml=dhcpxml,
                     dualxml=dualxml, namespace=namespace, dnsmasqxml=dnsmasqxml)
        if self.debug:
            print(networkxml)
        new_net = conn.networkDefineXML(networkxml)
        new_net.setAutostart(True)
        new_net.create()
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        conn = self.conn
        try:
            network = conn.networkLookupByName(name)
        except:
            return {'result': 'failure', 'reason': f"Network {name} not found"}
        vms = self.network_ports(name)
        if vms:
            if not force:
                vms = ','.join(vms)
                return {'result': 'failure', 'reason': f"Network {name} is being used by the following vms: {vms}"}
            for vm in vms:
                self.delete(vm)
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
            dual_cidr = None
            networkname = network.name()
            netxml = network.XMLDesc(0)
            cidr = 'N/A'
            root = ET.fromstring(netxml)
            ip = None
            for index, entry in enumerate(list(root.iter('ip'))):
                attributes = entry.attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                netmask = attributes.get('prefix') if netmask is None else netmask
                ipnet = f'{firstip}/{netmask}' if netmask is not None else firstip
                ipnet = ip_network(ipnet, strict=False)
                if index > 0:
                    dual_cidr = str(ipnet)
                else:
                    cidr = str(ipnet)
            dhcp = list(root.iter('dhcp'))
            if dhcp:
                dhcp = True
            else:
                dhcp = False
            domain = list(root.iter('domain'))
            if domain:
                attributes = domain[0].attrib
                domainname = attributes.get('name')
            else:
                domainname = networkname
            forward = list(root.iter('forward'))
            if forward:
                attributes = forward[0].attrib
                mode = attributes.get('mode')
            else:
                mode = 'isolated'
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
            if dual_cidr is not None:
                networks[networkname]['dual_cidr'] = dual_cidr
            plan = 'N/A'
            for element in list(root.iter('{kvirt}info')):
                e = element.find('{kvirt}ovs')
                if e is not None:
                    networks[networkname]['type'] = 'ovs'
                e = element.find('{kvirt}plan')
                if e is not None:
                    plan = e.text
            networks[networkname]['plan'] = plan
        try:
            interfaces = conn.listInterfaces()
        except:
            return networks
        for interface in interfaces:
            if interface == 'lo' or interface in networks:
                continue
            try:
                netxml = conn.interfaceLookupByName(interface).XMLDesc(0)
                root = ET.fromstring(netxml)
            except Exception as e:
                warning(f"Skipping interface {interface} {e if self.debug else ''}")
                continue
            bridge = list(root.iter('bridge'))
            if not bridge:
                if not interface.startswith('macvtap'):
                    networks[interface] = {'cidr': 'N/A', 'dhcp': 'N/A', 'type': 'nic', 'mode': 'N/A'}
                continue
            ip = None
            cidr = 'N/A'
            for entry in list(root.iter('ip')):
                attributes = entry.attrib
                ip = attributes.get('address')
                if ip.startswith('fe80'):
                    continue
                prefix = attributes.get('prefix')
                ipnet = ip_network(f'{ip}/{prefix}', strict=False)
                cidr = str(ipnet)
                if ':' not in ip:
                    break
            networks[interface] = {'cidr': cidr, 'dhcp': 'N/A', 'type': 'bridged', 'mode': 'N/A'}
            if ip is not None:
                networks[interface]['ip'] = ip
            plan = 'N/A'
            for element in list(root.iter('{kvirt}info')):
                e = element.find('{kvirt}plan')
                if e is not None:
                    plan = e.text
            networks[interface]['plan'] = plan
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        if self.debug and networkinfo:
            conn = self.conn
            if networkinfo['type'] == 'routed':
                network = conn.networkLookupByName(name)
            else:
                network = conn.interfaceLookupByName(name)
            netxml = network.XMLDesc(0)
            print(netxml)
        return networkinfo

    def list_subnets(self):
        pprint("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        conn = self.conn
        try:
            pool = conn.storagePoolLookupByName(name)
        except:
            return {'result': 'failure', 'reason': f"Pool {name} not found"}
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
            for element in list(root.iter('interface')):
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
            error(f"VM {name} not found")
            return networks
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        for element in list(root.iter('interface')):
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
        bridge = list(root.iter('bridge'))
        if bridge:
            attributes = bridge[0].attrib
            bridge = attributes.get('name')
        return bridge

    def get_pool_path(self, pool):
        conn = self.conn
        pool = conn.storagePoolLookupByName(pool)
        poolxml = pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        pooltype = list(root.iter('pool'))[0].get('type')
        if pooltype in ['dir', 'logical', 'zfs']:
            poolpath = list(root.iter('path'))[0].text
        else:
            poolpath = list(root.iter('device'))[0].get('path')
        if pooltype == 'logical':
            product = list(root.iter('product'))
            if product:
                thinpool = list(root.iter('product'))[0].get('name')
                poolpath += f" (thinpool:{thinpool})"
        return poolpath

    def list_flavors(self):
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
        command = f"qemu-img create -q -f qcow2 -b {backing} -F qcow2 {path}"
        if self.protocol == 'ssh':
            command = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host, command)
        os.system(command)

    def add_image_to_deadpool(self, poolname, pooltype, poolpath, shortimage, thinpool=None):
        sizecommand = f"qemu-img info /tmp/{shortimage} --output=json"
        if self.protocol == 'ssh':
            sizecommand = "ssh %s -p %s %s@%s \"%s\"" % (self.identitycommand, self.port, self.user, self.host,
                                                         sizecommand)
        size = os.popen(sizecommand).read().strip()
        virtualsize = json.loads(size)['virtual-size']
        if pooltype == 'logical':
            if thinpool is not None:
                command = f"lvcreate -qq -V {virtualsize}b -T {poolpath}/{thinpool} -n {shortimage}"
            else:
                command = f"lvcreate -qq -L {virtualsize}b -n {shortimage} {poolpath}"
        elif pooltype == 'zfs':
            command = f"zfs create -V {virtualsize} {poolname}/{shortimage}"
        else:
            error(f"Invalid pooltype {pooltype}")
            return
        command += "; qemu-img convert -p -f qcow2 -O raw -t none -T none /tmp/%s %s/%s" % (shortimage, poolpath,
                                                                                            shortimage)
        command += f"; rm -rf /tmp/{shortimage}"
        if self.protocol == 'ssh':
            command = f"ssh {self.identitycommand} -p {self.port} {self.user}@{self.host} \"{command}\""
        os.system(command)

    def _createthinlvm(self, name, path, thinpool, backing=None, size=None):
        if backing is not None:
            command = f"lvcreate -qq -ay -K -s --name {name} {path}/{backing}"
        else:
            command = f"lvcreate -qq -V {size}G -T {path}/{thinpool} -n {name}"
        if self.protocol == 'ssh':
            command = f"ssh {self.identitycommand} -p {self.port} {self.user}@{self.host} \"{command}\""
        os.system(command)

    def _deletelvm(self, disk):
        command = f"lvremove -qqy {disk}"
        if self.protocol == 'ssh':
            command = f"ssh {self.identitycommand} -p {self.port} {self.user}@{self.host} \"{command}\""
        os.system(command)

    def export(self, name, image=None):
        self.stop(name, soft=True)
        newname = image if image is not None else f"image-{name}"
        conn = self.conn
        oldvm = conn.lookupByName(name)
        oldxml = oldvm.XMLDesc(0)
        tree = ET.fromstring(oldxml)
        for disk in list(tree.iter('disk')):
            source = disk.find('source')
            oldpath = source.get('file')
            oldvolume = self.conn.storageVolLookupByPath(oldpath)
            pool = oldvolume.storagePoolLookupByVolume()
            oldinfo = oldvolume.info()
            oldvolumesize = (float(oldinfo[1]) / GiB)
            oldvolumexml = oldvolume.XMLDesc(0)
            backing = None
            voltree = ET.fromstring(oldvolumexml)
            for b in list(voltree.iter('backingStore')):
                backingstoresource = b.find('path')
                if backingstoresource is not None:
                    backing = backingstoresource.text
            newpath = oldpath.replace(name, newname).replace('.img', '.qcow2')
            source.set('file', newpath)
            newvolumexml = self._xmlvolume(newpath, oldvolumesize, backing=backing)
            pool.createXMLFrom(newvolumexml, oldvolume, 0)
            break
        success(f"{newpath} generated")
        return {'result': 'success'}

    def _create_host_entry(self, name, ip, netname, domain):
        if os.path.exists("/i_am_a_container"):
            if not os.path.exists('/etcdir'):
                error("Missing -v /etcdir:/etc in your container alias")
                sys.exit(1)
            hostsfile = '/etcdir/hosts'
        else:
            hostsfile = '/etc/hosts'
        hosts = f"{ip} {name} {name}.{netname}"
        if domain is not None and domain != netname:
            hosts = f"{hosts} {name}.{domain}"
        hosts = f'"{hosts} # KVIRT"'
        oldentry = f"{ip} {name}.* # KVIRT"
        for line in open(hostsfile):
            if re.findall(oldentry, line):
                warning("Old entry found.Leaving...")
                return
        pprint("Creating hosts entry. Password for sudo might be asked")
        hostscmd = f"sh -c 'echo {hosts} >>{hostsfile}'"
        if getuser() != 'root':
            hostscmd = f"sudo {hostscmd}"
        call(hostscmd, shell=True)

    def delete_dns(self, name, domain, allentries=False):
        conn = self.conn
        if domain is None:
            for network in conn.listAllNetworks():
                netname = network.name()
                netxml = network.XMLDesc()
                netroot = ET.fromstring(netxml)
                dns = list(netroot.iter('dns'))
                if not dns:
                    continue
                dnsinfo = {}
                ip = None
                for host in list(dns[0].iter('host')):
                    iphost = host.get('ip')
                    dnsinfo[iphost] = []
                    for hostname in list(host.iter('hostname')):
                        if hostname.text == name:
                            ip = iphost
                        dnsinfo[iphost].append(hostname.text)
                if ip is not None:
                    currentries = dnsinfo[ip]
                    hostentry = f'<host ip="{ip}"><hostname>{name}</hostname></host>'
                    network.update(2, 10, 0, hostentry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                    if not allentries and len(currentries) != 1:
                        others = [f"<hostname>{hostname}</hostname>" for hostname in currentries if hostname != name]
                        if others:
                            newhostentry = '<host ip="%s">%s</host>' % (ip, ''.join(others))
                            network.update(4, 10, 0, newhostentry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                    pprint(f"Entry {name} with ip {iphost} deleted in network {netname}")
        else:
            network = conn.networkLookupByName(domain)
            netxml = network.XMLDesc()
            netroot = ET.fromstring(netxml)
            dns = list(netroot.iter('dns'))
            if not dns:
                warning(f"No dns information found in network {domain}")
                return
            dnsinfo = {}
            ip = None
            for host in list(dns[0].iter('host')):
                iphost = host.get('ip')
                dnsinfo[iphost] = []
                for hostname in list(host.iter('hostname')):
                    if hostname.text == name:
                        ip = iphost
                    dnsinfo[iphost].append(hostname.text)
            if ip is not None:
                currentries = dnsinfo[ip]
                hostentry = f'<host ip="{ip}"><hostname>{name}</hostname></host>'
                network.update(2, 10, 0, hostentry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                if not allentries and len(currentries) != 1:
                    others = ["f<hostname>{hostname}</hostname>" for hostname in currentries if hostname != name]
                    newhostentry = '<host ip="%s">%s</host>' % (ip, ''.join(others))
                    network.update(4, 10, 0, newhostentry, VIR_DOMAIN_AFFECT_LIVE | VIR_DOMAIN_AFFECT_CONFIG)
                pprint(f"Entry {name} with ip {iphost} deleted")
                return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        conn = self.conn
        try:
            network = conn.networkLookupByName(domain)
            netxml = network.XMLDesc()
            netroot = ET.fromstring(netxml)
            for host in list(netroot.iter('host')):
                iphost = host.get('ip')
                for hostname in list(host.iter('hostname')):
                    results.append([hostname.text, 'A', '0', iphost])
        except:
            for network in conn.listAllNetworks():
                netname = network.name()
                netxml = network.XMLDesc(0)
                netxml = network.XMLDesc()
                netroot = ET.fromstring(netxml)
                for host in list(netroot.iter('host')):
                    iphost = host.get('ip')
                    for hostname in list(host.iter('hostname')):
                        if hostname.text.endswith(domain):
                            results.append([hostname.text, 'A', '0', f"{iphost} ({netname})"])
        return results

    def create_bucket(self, bucket, public=False):
        print("not implemented")
        return

    def delete_bucket(self, bucket):
        print("not implemented")
        return

    def delete_from_bucket(self, bucket, path):
        print("not implemented")
        return

    def download_from_bucket(self, bucket, path):
        print("not implemented")
        return

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        print("not implemented")
        return

    def list_buckets(self):
        print("not implemented")
        return []

    def list_bucketfiles(self, bucket):
        print("not implemented")
        return []

    def resize_disk(self, path, size):
        conn = self.conn
        volume = conn.storageVolLookupByPath(path)
        size = int(size) * GiB
        volume.resize(size)

    def update_nic(self, name, index, network):
        conn = self.conn
        networks = {}
        for interface in conn.listInterfaces():
            networks[interface] = 'bridge'
        for net in conn.listAllNetworks():
            networks[net.name()] = 'network'
        try:
            vm = conn.lookupByName(name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if network not in networks:
            error(f"Network {network} not found")
            return {'result': 'failure', 'reason': f"Network {network} not found"}
        else:
            networktype = networks[network]
        vm = conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        root = ET.fromstring(vmxml)
        for netindex, element in enumerate(list(root.iter('interface'))):
            if netindex == index:
                current_networktype = element.get('type')
                if current_networktype != networktype:
                    msg = f"Network type can't be changed from {current_networktype} to {networktype}"
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
                elif networktype == 'bridge':
                    element.find('source').set('bridge', network)
                else:
                    element.find('source').set('network', network)
                break
        if vm.isActive() != 0:
            warning("Note it will only be effective upon next start")
        newxml = ET.tostring(root).decode("utf-8")
        conn.defineXML(newxml)
        return {'result': 'success'}

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        modified = False
        conn = self.conn
        try:
            network = conn.networkLookupByName(name)
        except:
            error(f"Network {name} not found")
            return {'result': 'not found'}
        netxml = network.XMLDesc(0)
        root = ET.fromstring(netxml)
        forward = root.find('forward')
        if nat is not None:
            if not isinstance(nat, bool):
                error("Nat not set to correct value")
            elif nat and forward is None:
                forward = ET.fromstring("<forward mode='nat'><nat><port start='1024' end='65535'/></nat></forward>")
                root.append(forward)
                modified = True
            if not nat and forward is not None:
                root.remove(forward)
                modified = True
        currentdomain = root.find('domain')
        if domain is not None:
            if currentdomain is None:
                domain = ET.fromstring(f"<domain name='{domain}'</>")
                root.append(domain)
                modified = True
            elif currentdomain.get('name') != domain:
                currentdomain.set('name', domain)
                modified = True
        currentip = root.find('ip')
        currentdhcp = currentip.find('dhcp')
        if dhcp is not None:
            if not dhcp and currentdhcp is not None:
                currentip.remove(currentdhcp)
                modified = True
            if dhcp and currentdhcp is None:
                for entry in list(root.iter('ip')):
                    attributes = entry.attrib
                    firstip = attributes.get('address')
                    netmask = attributes.get('netmask')
                    netmask = attributes.get('prefix') if netmask is None else netmask
                    ipnet = f'{firstip}/{netmask}' if netmask is not None else firstip
                    ipnet = ip_network(ipnet, strict=False)
                    cidr = str(ipnet)
                cidr_range = ip_network(cidr)
                gateway = str(cidr_range[1])
                family = 'ipv6' if ':' in gateway else 'ipv4'
                start = str(cidr_range[2])
                end = str(cidr_range[65535 if family == 'ipv6' else -2])
                dhcp = ET.fromstring(f"<dhcp><range start='{start}' end='{end}'/></dhcp>")
                currentip.append(dhcp)
                modified = True
        if plan is not None:
            for element in list(root.iter('{kvirt}info')):
                e = element.find('{kvirt}plan')
                if e is not None:
                    if e.text != plan:
                        e.text = plan
                        modified = True
                else:
                    plan = ET.fromstring(f"<kvirt:plan>{plan}</kvirt:plan>")
                    root.find('{kvirt}info').append(plan)
                    modified = True
        currentdns = root.find('dns')
        dns = overrides.get('dns', True)
        if currentdns is None and not dns:
            root.append(ET.fromstring("<dns enable='no'/>"))
            modified = True
        elif currentdns is not None and dns and currentdns.attrib.get('enable', 'xxx') == 'no':
            root.remove(currentdns)
            modified = True
        if modified:
            warning("Network will be restarted")
            network.destroy()
            newxml = ET.tostring(root).decode("utf-8")
            conn.networkDefineXML(newxml)
            network.create()
        else:
            return {'result': 'failure', 'reason': 'No changes needed'}
        return {'result': 'success'}

    def update_pool(self, name, pool):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
        except:
            reason = f"VM {name} not found"
            error(reason)
            return {'result': 'failure', 'reason': reason}
        try:
            poolname = pool
            pool = conn.storagePoolLookupByName(pool)
        except:
            reason = f"Pool {pool} not found"
            error(reason)
            return {'result': 'failure', 'reason': reason}
        status = {0: 'down', 1: 'up'}
        if status[vm.isActive()] != "down":
            vm.destroy()
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        for element in list(root.iter('disk')):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            imagefiles = [element.find('source').get('file'), element.find('source').get('dev'),
                          element.find('source').get('volume')]
            path = next(item for item in imagefiles if item is not None)
            volume = conn.storageVolLookupByPath(path)
            old_pool = volume.storagePoolLookupByVolume()
            old_poolname = old_pool.name()
            if poolname == old_poolname:
                reason = "Target pool is identical to Origin one"
                error(reason)
                return {'result': 'failure', 'reason': reason}
            else:
                pprint(f"Migrating {path} to {poolname}")
            old_poolpath = self.get_pool_path(old_poolname)
            new_poolpath = self.get_pool_path(poolname)
            new_path = path.replace(old_poolpath, new_poolpath)
            old_xml = volume.XMLDesc(0)
            new_xml = old_xml.replace(path, new_path)
            pool.createXMLFrom(new_xml, volume, 0)
            volume.delete()
            for _type in ['file', 'dev', 'volume']:
                if element.find('source').get(_type) is not None:
                    element.find('source').set(_type, new_path)
                    break
        newxml = ET.tostring(root).decode("utf-8")
        conn.defineXML(newxml)
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        print("not implemented")
        return []

    def create_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_security_group(self, name):
        print("not implemented")
        return {'result': 'success'}

    def update_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def info_subnet(self, name):
        print("not implemented")
        return {}

    def create_subnet(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        print("not implemented")
        return {'result': 'success'}

    def update_subnet(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_dns_zones(self):
        results = []
        conn = self.conn
        for network in conn.listAllNetworks():
            netxml = network.XMLDesc(0)
            netxml = network.XMLDesc()
            netroot = ET.fromstring(netxml)
            for host in list(netroot.iter('host')):
                for hostname in list(host.iter('hostname')):
                    if len(hostname.text.split('.')) > 1 and hostname.text.partition('.')[2] not in results:
                        results.append(hostname.text.partition('.')[2])
        return results

    def _rhel_legacy(self, machines):
        rhel7 = False
        for m in machines:
            if 'rhel7' in m:
                rhel7 = True
            elif 'rhel9' in m:
                return False
        return rhel7

    def _get_pcie_data(self, vm):
        bus, slot = None, None
        if vm.isActive() == 1 and 'q35' in vm.XMLDesc(0):
            vmxml = vm.XMLDesc(0)
            root = ET.fromstring(vmxml)
            bus, slot = None, 0
            for element in list(root.iter('controller')):
                if element.get('model') == 'pcie-to-pci-bridge':
                    bus = int(element.get('index'))
                    break
            if bus is None:
                return bus, slot
            for element in list(root.iter('disk')) + list(root.iter('interface')):
                address = element.find('address')
                if int(address.get('bus'), 16) != bus:
                    continue
                current_slot = int(address.get('slot'), 16)
                if current_slot > slot:
                    slot = current_slot
            slot += 1
        return bus, slot

    def _get_raw_disks(self, vm):
        primary_disk = None
        raw_disks = []
        xml = vm.XMLDesc(0)
        root = ET.fromstring(xml)
        for index, element in enumerate(list(root.iter('disk'))):
            if element.get('device') == 'cdrom':
                continue
            device = element.find('target').get('dev')
            if index == 0:
                primary_disk = device
            if element.find('driver').get('type') == 'raw':
                raw_disks.append(device)
        return raw_disks, primary_disk
