import base64
from binascii import hexlify
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from getpass import getpass
import json
from kvirt import common
from kvirt.common import error, pprint, warning, sdn_ip
from kvirt.defaults import UBUNTUS, METADATA_FIELDS
from kvirt.providers.vsphere.helpers import find, collectproperties, findvm, createfolder, changecd, convert, waitForMe
from kvirt.providers.vsphere.helpers import createscsispec, creatediskspec, createdvsnicspec, createclonespec
from kvirt.providers.vsphere.helpers import createnicspec, createisospec, createcdspec, deletedirectory
from kvirt.providers.vsphere.helpers import dssize, keep_lease_alive, folder_exists
from kvirt.providers.vsphere.helpers import create_filter_spec, get_all_obj, convert_properties, findvm2, findvmdc
import os
from pyVmomi import vim, vmodl
from pyVim import connect
from pyVim.task import WaitForTask
import random
import re
import ssl
from ssl import _create_unverified_context, get_server_certificate
import sys
from shutil import which
from subprocess import call
import tarfile
from tempfile import TemporaryDirectory
from threading import Thread
import time
import urllib.request
from uuid import UUID
import webbrowser
from zipfile import ZipFile


class Ksphere:
    def __init__(self, host, user, password, datacenter, cluster, debug=False, isofolder=None,
                 filtervms=False, filteruser=False, filtertag=None, category='kcli', basefolder=None, dvs=True,
                 import_network='VM Network', timeout=3600, force_pool=False, restricted=False, serial=False):
        password = password or getpass()
        if timeout < 1:
            smart_stub = connect.SmartStubAdapter(host=host, port=443, sslContext=_create_unverified_context(),
                                                  connectionPoolTimeout=0)
            session_stub = connect.VimSessionOrientedStub(smart_stub,
                                                          connect.VimSessionOrientedStub.makeUserLoginMethod(user,
                                                                                                             password))
            si = vim.ServiceInstance('ServiceInstance', session_stub)
        elif hasattr(connect, 'SmartConnectNoSSL'):
            si = connect.SmartConnectNoSSL(host=host, port=443, user=user, pwd=password,
                                           connectionPoolTimeout=timeout)
        else:
            si = connect.SmartConnect(host=host, port=443, user=user, pwd=password, disableSslCertValidation=True,
                                      connectionPoolTimeout=timeout)
        self.conn = si
        self.si = si
        self.vcip = host
        self.category = category
        self.url = f"https://{user}:{password}@{host}/sdk"
        self.user = user
        self.password = password
        self.rootFolder = si.content.rootFolder
        self.dc = find(si, self.rootFolder, vim.Datacenter, datacenter)
        self.macaddr = []
        self.clu = cluster
        self.isofolder = isofolder
        self.filtervms = filtervms
        self.filtervms = filtervms
        self.filteruser = filteruser
        self.filtertag = filtertag
        self.debug = debug
        self.networks = []
        self.dvs = dvs
        self.portgs = {}
        self.esx = '.' in cluster and datacenter == 'ha-datacenter'
        self.restricted = restricted or self.esx
        self.serial = serial
        self.import_network = import_network
        self.force_pool = force_pool
        if basefolder is not None:
            if '/' in basefolder:
                topfolder = os.path.dirname(basefolder)
                vmFolder = find(si, self.dc.vmFolder, vim.Folder, topfolder)
                if vmFolder is None:
                    error(f"Couldnt find topfolder {topfolder}")
                    self.conn = None
                    return
                lowFolder = os.path.basename(basefolder)
            else:
                vmFolder = self.dc.vmFolder
                lowFolder = basefolder
            self.basefolder = find(si, vmFolder, vim.Folder, lowFolder)
            if self.basefolder is None:
                if not self.restricted:
                    try:
                        createfolder(si, vmFolder, lowFolder)
                        self.basefolder = find(si, vmFolder, vim.Folder, lowFolder)
                    except Exception as e:
                        error(f"Couldnt create basefolder {basefolder}. Hit {e}")
                        self.conn = None
                        return
                else:
                    error(f"Couldnt find basefolder {basefolder}")
                    self.conn = None
                    return
        else:
            self.basefolder = self.dc.vmFolder

    def set_networks(self):
        si = self.si
        view = si.content.viewManager.CreateContainerView(self.rootFolder, [vim.Network], True)
        netlist = collectproperties(si, view=view, objtype=vim.Network, pathset=['name'], includemors=True)
        self.networks = [o['obj'].name for o in netlist]
        if self.dvs:
            portgs = {}
            o = si.content.viewManager.CreateContainerView(self.rootFolder, [vim.DistributedVirtualSwitch], True)
            dvnetworks = o.view
            o.Destroy()
            for dvnetw in dvnetworks:
                uuid = dvnetw.uuid
                for portg in dvnetw.portgroup:
                    portgs[portg.name] = [uuid, portg.key]
            self.portgs = portgs

    def close(self):
        self.si.content.sessionManager.Logout()

    def exists(self, name):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        return findvm(si, vmFolder, name) is not None

    def net_exists(self, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='centos7_64Guest', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[],
               cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False,
               numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[],
               vmuser=None, guestagent=True):
        if not self.esx and self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        dc = self.dc
        vmFolder = dc.vmFolder
        diskmode = 'persistent'
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        memory = int(memory)
        numcpus = int(numcpus)
        si = self.si
        basefolder = self.basefolder
        restricted = self.restricted
        rootFolder = self.rootFolder
        basefolder = self.basefolder
        cluster = overrides.get('cluster')
        vmfolder = basefolder
        if not restricted:
            if cluster is not None:
                createfolder(si, basefolder, cluster)
                vmfolder = find(si, basefolder, vim.Folder, cluster)
            elif plan != 'kvirt':
                createfolder(si, basefolder, plan)
                vmfolder = find(si, basefolder, vim.Folder, plan)
        si = self.si
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        if 'resourcepool' in overrides:
            resourcepoolname = overrides['resourcepool']
            resourcepool = find(si, rootFolder, vim.ResourcePool, resourcepoolname)
            if resourcepool is None:
                return {'result': 'failure', 'reason': f"Resourcepool {resourcepoolname} not found"}
        else:
            resourcepool = clu.resourcePool
        if image is not None:
            imagepool = image.split('/')[0] if '/' in image else None
            image = os.path.basename(image)
            clonespec = createclonespec(resourcepool)
            rootFolder = self.rootFolder
            imageobj, imagedc = findvmdc(si, rootFolder, image, dc)
            if self.esx:
                imagepool = pool
                imagedc = dc.name
            elif imageobj is None:
                return {'result': 'failure', 'reason': f"Image {image} not found"}
            datastores = self._datastores_datacenters()
            if os.path.basename(datastores[pool]) != dc.name:
                return {'result': 'failure', 'reason': f"Pool {pool} doesn't belong to Datacenter {dc.name}"}
            if imagepool is None:
                devices = imageobj.config.hardware.device
                for number, dev in enumerate(devices):
                    if type(dev).__name__ == 'vim.vm.device.VirtualDisk':
                        imagepool = dev.backing.datastore.name
            if imagedc != dc.name or (overrides.get('force_pool', self.force_pool) and imagepool != pool):
                warning(f"Vm {name} will be relocated from pool {imagepool} to {pool}")
                relospec = vim.vm.RelocateSpec()
                relospec.datastore = find(si, rootFolder, vim.Datastore, pool)
                relospec.pool = resourcepool
                clonespec.location = relospec
            confspec = vim.vm.ConfigSpec()
            confspec.flags = vim.vm.FlagInfo()
            confspec.flags.diskUuidEnabled = True
            confspec.annotation = name
            if memory % 1024 != 0:
                warning("Rounding up memory to be multiple of 1024")
                memory += (1024 - memory) % 1024
            confspec.memoryMB = memory
            confspec.memoryHotAddEnabled = memoryhotplug
            cores = overrides.get('cores')
            sockets, cores = overrides.get('sockets', 1), overrides.get('cores')
            if cores is not None and isinstance(cores, int) and isinstance(sockets, int):
                confspec.numCoresPerSocket = cores
                numcpus = cores * sockets
            threads = overrides.get('threads')
            if threads is not None and isinstance(threads, int):
                confspec.simultaneousThreads = threads
            confspec.numCPUs = numcpus
            confspec.cpuHotAddEnabled = cpuhotplug
            confspec.cpuHotRemoveEnabled = cpuhotplug
            extraconfig = []
            for entry in [field for field in metadata if field in METADATA_FIELDS]:
                opt = vim.option.OptionValue()
                opt.key = entry
                opt.value = metadata[entry]
                extraconfig.append(opt)
            if tags:
                opt = vim.option.OptionValue()
                opt.key = 'tags'
                opt.value = ','.join(tags)
                extraconfig.append(opt)
            clonespec.config = confspec
            clonespec.powerOn = False
            isofolder = self.isofolder if self.isofolder is not None else f"[{default_pool}]/{name}"
            cloudinitiso = f"{isofolder}/{name}.ISO"
            combustion = common.needs_combustion(image)
            if cloudinit:
                if image is not None and common.needs_ignition(image):
                    version = common.ignition_version(image)
                    meta, netdata = '', None
                    ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                                   domain=domain, files=files, enableroot=enableroot,
                                                   overrides=overrides, version=version, plan=plan, image=image,
                                                   vmuser=vmuser)
                    if combustion:
                        userdata, meta, netdata = ignitiondata, '', None
                    else:
                        cloudinitiso = None
                        ignitionopt = vim.option.OptionValue()
                        ignitionopt.key = 'guestinfo.ignition.config.data'
                        ignitionopt.value = base64.b64encode(ignitiondata.encode()).decode()
                        encodingopt = vim.option.OptionValue()
                        encodingopt.key = 'guestinfo.ignition.config.data.encoding'
                        encodingopt.value = 'base64'
                        extraconfig.extend([ignitionopt, encodingopt])
                else:
                    gcmds = []
                    if image is not None and 'cos' not in image and 'fedora-coreos' not in image:
                        lower = image.lower()
                        if lower.startswith('fedora') or lower.startswith('rhel') or lower.startswith('centos'):
                            gcmds.append('yum -y install open-vm-tools')
                        elif lower.startswith('debian') or [x for x in UBUNTUS if x in lower] or 'ubuntu' in lower:
                            gcmds.append('apt-get update')
                            gcmds.append('apt-get -f install open-vm-tools')
                        gcmds.append('systemctl enable --now vmtoolsd')
                    index = 0
                    if image is not None and image.startswith('rhel'):
                        subindex = [i for i, value in enumerate(cmds) if value.startswith('subscription-manager')]
                        if subindex:
                            index = subindex.pop() + 1
                    cmds = cmds[:index] + gcmds + cmds[index:]
                    userdata, meta, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                               gateway=gateway, dns=dns, domain=domain,
                                                               files=files, enableroot=enableroot, overrides=overrides,
                                                               storemetadata=storemetadata, machine='vsphere',
                                                               image=image, vmuser=vmuser)
            for key in overrides:
                if key.startswith('guestinfo.'):
                    guestopt = vim.option.OptionValue()
                    guestopt.key = key
                    guestopt.value = overrides[key]
                    extraconfig.append(guestopt)
            confspec.extraConfig = extraconfig
            if not self.esx:
                t = imageobj.CloneVM_Task(folder=vmfolder, name=name, spec=clonespec)
            else:
                vm = findvm(si, vmFolder, name)
                t = vm.ReconfigVM_Task(confspec)
            waitForMe(t)
            if cloudinit and cloudinitiso is not None:
                with TemporaryDirectory() as tmpdir:
                    if combustion:
                        cmdsdata = common.process_combustion_cmds(cmds, overrides)
                        if cmdsdata != '':
                            with open(f'{tmpdir}/combustion_script', 'w') as combustionfile:
                                combustionfile.write(cmdsdata)
                    common.make_iso(name, tmpdir, userdata, meta, netdata, openstack=False, combustion=combustion)
                    cloudinitisofile = f"{tmpdir}/{name}.ISO"
                    isopool = default_pool
                    isofolder = None
                    if self.isofolder is not None:
                        isofolder = self.isofolder.split('/')
                        isopool = re.sub(r"[\[\]]", '', isofolder[0])
                        isofolder = isofolder[1]
                    self._uploadimage(isopool, cloudinitisofile, name, isofolder=isofolder)
                vm = findvm(si, vmFolder, name)
                c = changecd(self.si, vm, cloudinitiso)
                waitForMe(c)
        datastores = {}
        confspec = vim.vm.ConfigSpec()
        confspec.name = name
        confspec.annotation = name
        confspec.memoryMB = memory
        confspec.numCPUs = numcpus
        if 'uuid' in overrides:
            uuid = str(overrides['uuid'])
            try:
                UUID(uuid)
                confspec.uuid = uuid
            except:
                warning(f"couldn't use {uuid} as uuid")
        confspec.flags = vim.vm.FlagInfo()
        confspec.flags.diskUuidEnabled = True
        confspec.extraConfig = []
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            opt = vim.option.OptionValue()
            opt.key = entry
            opt.value = metadata[entry]
            confspec.extraConfig.append(opt)
        confspec.guestId = 'centos7_64Guest'
        vmfi = vim.vm.FileInfo()
        filename = "[" + default_pool + "]"
        vmfi.vmPathName = filename
        confspec.files = vmfi
        if vnc:
            vncport = random.randint(5900, 7000)
            opt1 = vim.option.OptionValue()
            opt1.key = 'RemoteDisplay.vnc.port'
            opt1.value = vncport
            opt2 = vim.option.OptionValue()
            opt2.key = 'RemoteDisplay.vnc.enabled'
            opt2.value = "TRUE"
            confspec.extraConfig.extend([opt1, opt2])
        if image is None:
            t = vmfolder.CreateVM_Task(confspec, resourcepool)
            waitForMe(t)
        vm = find(si, dc.vmFolder, vim.VirtualMachine, name)
        currentdevices = vm.config.hardware.device
        currentdisks = [d for d in currentdevices if isinstance(d, vim.vm.device.VirtualDisk)]
        currentnics = [d for d in currentdevices if isinstance(d, vim.vm.device.VirtualEthernetCard)]
        confspec = vim.vm.ConfigSpec()
        devconfspec = []
        unit_number = 1
        for index, disk in enumerate(disks):
            diskuuid = None
            if disk is None:
                disksize = default_disksize
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
            elif isinstance(disk, int):
                disksize = disk
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
                diskthin = default_diskthin
                diskinterface = default_diskinterface
                diskpool = default_pool
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskthin = disk.get('thin', default_diskthin)
                diskinterface = disk.get('interface', default_diskinterface)
                diskpool = disk.get('pool', default_pool)
                diskuuid = disk.get('uuid') or disk.get('wwn')
                if diskuuid is not None:
                    try:
                        UUID(diskuuid)
                    except:
                        warning(f"{diskuuid} it not a valid disk uuid")
                        diskuuid = None
            if index < len(currentdisks) and image is not None:
                currentdisk = currentdisks[index]
                currentsize = convert(1000 * currentdisk.capacityInKB, GB=False)
                if int(currentsize) < disksize:
                    pprint(f"Waiting for image disk {index} to be resized")
                    currentdisk.capacityInKB = disksize * 1048576
                    diskspec = vim.vm.ConfigSpec()
                    diskspec = vim.vm.device.VirtualDeviceSpec(device=currentdisk, operation="edit")
                    devconfspec.append(diskspec)
                continue
            disksize = disksize * 1048576
            if diskpool not in datastores:
                datastore = find(si, rootFolder, vim.Datastore, diskpool)
                if not datastore:
                    return {'result': 'failure', 'reason': f"Pool {diskpool} not found"}
                else:
                    datastores[diskpool] = datastore
            kept_disks = folder_exists(datastores[diskpool], f'{name}_keep')
            if index == 0:
                scsispec = createscsispec()
                devconfspec.append(scsispec)
            elif kept_disks:
                pprint("Using existing data disks")
                path = f"[{diskpool}] {name}"
                keep_path = f"[{diskpool}] {name}_keep"
                browser = datastore.browser
                task = browser.SearchDatastore_Task(datastorePath=keep_path, searchSpec=None)
                fileManager = self.si.content.fileManager
                WaitForTask(task)
                result = task.info.result
                files = result.file if hasattr(result, 'file') else []
                for file in files:
                    t = fileManager.MoveDatastoreFile_Task(sourceName=f"{keep_path}/{file.path}",
                                                           sourceDatacenter=dc,
                                                           destinationName=f"{path}/{file.path}",
                                                           destinationDatacenter=dc,
                                                           force=True)
                    WaitForTask(t)
                task = fileManager.DeleteDatastoreFile_Task(name=keep_path, datacenter=dc)
                WaitForTask(task)
            if unit_number == 7:
                unit_number = 8
            diskpath = f'{name}/{name}_{index}.vmdk' if kept_disks else None
            diskspec = creatediskspec(unit_number, disksize, datastore, diskmode, diskthin, diskuuid, diskpath)
            devconfspec.append(diskspec)
            unit_number += 1
        for index, _ in enumerate(disks):
            confspec.extraConfig.append(vim.option.OptionValue(key=f'scsi0:{index}.enableUUID', value='TRUE'))
        # NICSPEC
        if not self.networks:
            self.set_networks()
        macs = {}
        for index, net in enumerate(nets):
            netname = net['name'] if isinstance(net, dict) else net
            if isinstance(net, dict) and 'mac' in net:
                macs[index] = net['mac']
            if netname == 'default':
                if image is not None:
                    continue
                else:
                    netname = 'VM Network'
            if index < len(currentnics):
                currentnetwork = None
                currentnic = currentnics[index]
                try:
                    currentnetwork = currentnic.backing.deviceName
                except:
                    currentswitchuuid = currentnic.backing.port.switchUuid
                    currentportgroupkey = currentnic.backing.port.portgroupKey
                    for dvsnet in self.portgs:
                        if self.portgs[dvsnet][0] == currentswitchuuid and\
                                self.portgs[dvsnet][1] == currentportgroupkey:
                            currentnetwork = dvsnet
                if currentnetwork is None:
                    warning(f"Couldn't figure out network associated to nic {index}")
                elif currentnetwork != netname:
                    if netname in self.portgs:
                        switchuuid = self.portgs[netname][0]
                        portgroupkey = self.portgs[netname][1]
                        currentnic.backing.port.switchUuid = switchuuid
                        currentnic.backing.port.portgroupKey = portgroupkey
                        currentnic.backing.port.portKey = None
                    elif netname in self.networks:
                        currentnic.backing.deviceName = netname
                    else:
                        return {'result': 'failure', 'reason': f"Invalid network {netname}"}
                    nicspec = vim.vm.device.VirtualDeviceSpec(device=currentnic, operation="edit")
                    devconfspec.append(nicspec)
                continue
            nicname = f'Network Adapter {index + 1}'
            nictype = net['type'] if isinstance(net, dict) and 'type' in net else None
            if netname in self.portgs:
                switchuuid = self.portgs[netname][0]
                portgroupkey = self.portgs[netname][1]
                nicspec = createdvsnicspec(nicname, netname, switchuuid, portgroupkey, nictype=nictype)
            elif netname in self.networks:
                nicspec = createnicspec(nicname, netname, nictype=nictype)
            else:
                return {'result': 'failure', 'reason': f"Invalid network {netname}"}
            devconfspec.append(nicspec)
        need_cdrom = iso is not None or not cloudinit or image is None or common.needs_ignition(image)
        if iso is not None:
            matchingisos = [i for i in self._getisos() if i.endswith(iso)]
            if matchingisos:
                iso = matchingisos[0]
            else:
                return {'result': 'failure', 'reason': f"Iso {iso} not found"}
        if need_cdrom:
            cdspec = createcdspec() if iso is None and self.esx else createisospec(iso)
            devconfspec.append(cdspec)
        serial = overrides.get('serial', self.serial)
        if serial:
            serialdevice = vim.vm.device.VirtualSerialPort()
            backing = vim.vm.device.VirtualSerialPort.URIBackingInfo()
            backing.serviceURI = f'tcp://:{common.get_free_port()}'
            backing.direction = 'server'
            serialdevice.backing = backing
            serialdevice.key = len(devconfspec) + 1
            serialspec = vim.vm.device.VirtualDeviceSpec(device=serialdevice, operation="add")
            devconfspec.append(serialspec)
        confspec.deviceChange = devconfspec
        if nested:
            confspec.nestedHVEnabled = True
        uefi = overrides.get('uefi', False)
        uefi_legacy = overrides.get('uefi_legacy', False)
        secureboot = overrides.get('secureboot', False)
        if secureboot or uefi or uefi_legacy:
            confspec.firmware = 'efi'
            if secureboot:
                confspec.bootOptions = vim.vm.BootOptions(efiSecureBootEnabled=True)
        confspec.vAppConfigRemoved = True
        t = vm.Reconfigure(confspec)
        waitForMe(t)
        if overrides.get('boot_order', False):
            key_disks = [d.key for d in vm.config.hardware.device if isinstance(d, vim.vm.device.VirtualDisk)]
            boot_disks = [vim.vm.BootOptions.BootableDiskDevice(deviceKey=key) for key in key_disks]
            confspec = vim.vm.ConfigSpec()
            confspec.bootOptions = vim.vm.BootOptions(bootOrder=boot_disks)
            t = vm.Reconfigure(confspec)
            waitForMe(t)
        if macs:
            self.set_macs(name, macs)
        if 'vmgroup' in overrides:
            vmgroup = overrides['vmgroup']
            vmgroups = {}
            hostgroups = {}
            for group in clu.configurationEx.group:
                if hasattr(group, 'vm'):
                    vmgroups[group.name] = group
                else:
                    hostgroups[group.name] = group
            if vmgroup in vmgroups:
                vmgroup = vmgroups[vmgroup]
                vmgroup.vm.append(vm)
                vmgroupspec = vim.cluster.GroupSpec(info=vmgroup, operation='edit')
                groups_spec = vim.cluster.ConfigSpecEx(groupSpec=[vmgroupspec])
                t = clu.ReconfigureEx(groups_spec, modify=True)
                waitForMe(t)
            else:
                vmgroup = vim.cluster.VmGroup(name=vmgroup, vm=[vm])
                vmgroupspec = vim.cluster.GroupSpec(info=vmgroup, operation='add')
                groups_spec = vim.cluster.ConfigSpecEx(groupSpec=[vmgroupspec])
                t = clu.ReconfigureEx(groups_spec, modify=True)
                waitForMe(t)
            if 'hostgroup' in overrides and 'hostrule' in overrides:
                hostgroup = overrides['hostgroup']
                hostrule = overrides['hostrule']
                if hostgroup not in hostgroups:
                    msg = f"Hostgroup {hostgroup} not found. It needs to exist prior to vm's creation"
                    return {'result': 'failure', 'reason': msg}
                else:
                    hostgroup = hostgroups[hostgroup]
                    vmhostrulefound = False
                    for vmhostrule in clu.configurationEx.rule:
                        if vmhostrule.name == hostrule:
                            vmhostrulefound = True
                            break
                    if not vmhostrulefound:
                        pprint(f"Creating vmhost rule {hostrule}")
                        rule_obj = vim.cluster.VmHostRuleInfo(vmGroupName=hostrule, affineHostGroupName=hostgroup.name,
                                                              name=vmgroup.name, enabled=True, mandatory=True)
                        rulespec = vim.cluster.RuleSpec(info=rule_obj, operation='add')
                        groups_spec = vim.cluster.ConfigSpecEx(rulesSpec=[rulespec])
                        t = clu.ReconfigureEx(groups_spec, modify=True)
                        waitForMe(t)
        antipeers = overrides.get('antipeers', [])
        if antipeers and antipeers[-1] == name:
            antipeers_rule = '-'.join(antipeers)
            pprint(f"Creating anti affinity rule {antipeers_rule}")
            vms = []
            for member in antipeers:
                vm = findvm(si, vmFolder, member)
                if vm is None:
                    error(f"VM {member} not found")
                else:
                    vms.append(vm)
            if len(vms) > 1:
                rule_obj = vim.cluster.AntiAffinityRuleSpec(vm=vms, enabled=True, mandatory=True, name=antipeers_rule)
                rulespec = vim.cluster.RuleSpec(info=rule_obj, operation='add')
                groups_spec = vim.cluster.ConfigSpecEx(rulesSpec=[rulespec])
                t = clu.ReconfigureEx(groups_spec, modify=True)
                waitForMe(t)
        if start:
            t = vm.PowerOnVM_Task(None)
            waitForMe(t)
        if tags:
            pprint("Assigning tags")
            from kvirt.providers.vsphere.tagging import KsphereTag
            ktag = KsphereTag(self.vcip, self.user, self.password)
            categories = {}
            tags_ids = []
            for entry in tags:
                if isinstance(entry, str) and '=' in entry:
                    category, tag = entry.split('=')
                elif isinstance(entry, dict) and len(list(entry.keys())) == 1:
                    category, tag = list(entry.keys())[0], list(entry.values())[0]
                else:
                    category, tag = self.category, entry
                if category not in categories:
                    category_id = ktag.get_category_id(category)
                    if category_id is None:
                        category_id = ktag.create_category(category)
                    categories[category] = category_id
                category_id = categories[category]
                tag_id = ktag.get_tag_id(tag)
                if tag_id is None:
                    tag_id = ktag.create_tag(category_id, tag)
                tags_ids.append(tag_id)
            if tags_ids:
                vm_id = vm._moId
                ktag.add_tags(vm_id, tags_ids)
        return {'result': 'success'}

    def start(self, name):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        runtime = info['runtime']
        if runtime.powerState == "poweredOff":
            t = vm.PowerOnVM_Task(None)
            waitForMe(t)
        return {'result': 'success'}

    def stop(self, name, soft=False):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        runtime = info['runtime']
        if runtime.powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        return {'result': 'success'}

    def restart(self, name):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        try:
            vm.RebootGuest()
        except:
            vm.ResetVM_Task()
        return {'result': 'success'}

    def status(self, name):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        runtime = info['runtime']
        return runtime.powerState if vm is not None else ''

    def delete(self, name, snapshots=False):
        si = self.si
        dc = self.dc
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        summary = info['summary']
        config = info['config']
        runtime = info['runtime']
        plan, image, kube = 'kvirt', None, None
        vmpath = summary.config.vmPathName.replace(f'/{name}.vmx', '')
        if config is not None:
            for entry in config.extraConfig:
                if entry.key == 'image':
                    image = entry.value
                if entry.key == 'plan':
                    plan = entry.value
                if entry.key == 'kube':
                    kube = entry.value
        if runtime.powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        t = vm.Destroy_Task()
        waitForMe(t)
        if image is not None and 'coreos' not in image and 'rhcos' not in image and\
                'fcos' not in image and vmpath.endswith(name):
            isopath = f"{self.isofolder}/{name}.ISO" if self.isofolder is not None else vmpath
            try:
                deletedirectory(si, dc, isopath)
            except:
                pass
        if kube is not None:
            clusterfolder = find(si, vmFolder, vim.Folder, kube)
            if clusterfolder is not None and len(clusterfolder.childEntity) == 0:
                clusterfolder.Destroy()
        elif plan != 'kvirt':
            planfolder = find(si, vmFolder, vim.Folder, plan)
            if planfolder is not None and len(planfolder.childEntity) == 0:
                try:
                    planfolder.Destroy()
                except Exception as e:
                    error(f"Couldn't delete plan folder {plan}. Hit {e}")
        return {'result': 'success'}

    def serialconsole(self, name, web=False):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            print(f"VM {name} not found")
            return
        runtime = info['runtime']
        config = info['config']
        if runtime.powerState == "poweredOff":
            print("VM down")
        serialfound = False
        devices = config.hardware.device
        for dev in devices:
            if type(dev).__name__ == 'vim.vm.device.VirtualSerialPort':
                serialfound = True
                serialport = dev.backing.serviceURI.split(':')[2]
                break
        if serialfound:
            host = runtime.host.name
            url = f"{host} {serialport}"
            consolecommand = f"nc {url}"
            if web:
                return url
            if self.debug or os.path.exists("/i_am_a_container"):
                print(consolecommand)
            if not os.path.exists("/i_am_a_container"):
                call(consolecommand, shell=True)

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        si = self.si
        vcip = self.vcip
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            print(f"VM {name} not found")
            return
        runtime = info['runtime']
        config = info['config']
        if runtime.powerState == "poweredOff":
            print("VM down")
            return
        extraconfig = config.extraConfig
        vncfound = False
        for extra in extraconfig:
            key, value = extra.key, extra.value
            if 'vnc' in key and 'port' in key:
                vncfound = True
                vncport = value
                break
            else:
                continue
        if vncfound:
            consolecommand = ''
            host = runtime.host.name
            if tunnel and tunnelhost is not None:
                localport = common.get_free_port()
                consolecommand += "ssh -o LogLevel=QUIET -f -p "
                consolecommand += f"{tunnelport} -L {localport}:{host}:{vncport} {tunneluser}@{tunnelhost} sleep 10;"
                host = '127.0.0.1'
                vncport = localport
            url = f"vnc://{host}:{vncport}"
            if os.path.exists('/Applications'):
                if os.path.exists('/Applications/VNC Viewer.app'):
                    consolecommand += f"open -a 'VNC Viewer' --args {url.replace('vnc://', '')} &"
                else:
                    consolecommand += f"open -a 'Screen Sharing' {url} &"
            else:
                consolecommand += f"remote-viewer {url} &"
            if web:
                return url
            if self.debug or os.path.exists("/i_am_a_container"):
                print(consolecommand)
            if not os.path.exists("/i_am_a_container"):
                os.popen(consolecommand)
        elif self.esx:
            vmnumber = None
            devices = config.hardware.device
            for dev in devices:
                if type(dev).__name__ == 'vim.vm.device.VirtualDisk':
                    vmnumber = dev.diskObjectId.split('-')[0]
                    break
            if vmnumber is not None:
                vmurl = f"https://{self.vcip}/ui/#/console/{vmnumber}"
                if self.debug or os.path.exists("/i_am_a_container"):
                    msg = f"Open the following url:\n{vmurl}" if os.path.exists("/i_am_a_container") else vmurl
                    pprint(msg)
                else:
                    pprint(f"Opening url {vmurl}")
                    webbrowser.open(vmurl, new=2, autoraise=True)
        else:
            content = si.RetrieveContent()
            sgid = content.about.instanceUuid
            cert = get_server_certificate((self.vcip, 443))
            cert_deserialize = x509.load_pem_x509_certificate(cert.encode(), default_backend())
            finger_print = hexlify(cert_deserialize.fingerprint(hashes.SHA1())).decode('utf-8')
            sha = ":".join([finger_print[i: i + 2] for i in range(0, len(finger_print), 2)])
            vcenter_data = content.setting
            vcenter_settings = vcenter_data.setting
            for item in vcenter_settings:
                key = getattr(item, 'key')
                if key == 'VirtualCenter.FQDN':
                    fqdn = getattr(item, 'value')
            sessionmanager = si.content.sessionManager
            session = sessionmanager.AcquireCloneTicket()
            vmid = vm._moId
            vmurl = f"https://{vcip}/ui/webconsole.html?"
            vmurl += f"vmId={vmid}&vmName={name}&serverGuid={sgid}&host={fqdn}&sessionTicket={session}&thumbprint={sha}"
            if web:
                return vmurl
            if self.debug or os.path.exists("/i_am_a_container"):
                msg = f"Open the following url:\n{vmurl}" if os.path.exists("/i_am_a_container") else vmurl
                pprint(msg)
            else:
                pprint(f"Opening url {vmurl}")
                webbrowser.open(vmurl, new=2, autoraise=True)

    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        translation = {'poweredOff': 'down', 'poweredOn': 'up', 'suspended': 'suspended'}
        image = None
        yamlinfo = {}
        si = self.si
        if vm is None:
            listinfo = False
            vmFolder = self.basefolder
            obj, vm = findvm2(si, vmFolder, name)
            if vm is None:
                error(f"VM {name} not found")
                return {}
        else:
            listinfo = True
        summary = vm['summary']
        config = vm['config']
        runtime = vm['runtime']
        guest = vm['guest']
        yamlinfo['name'] = name
        yamlinfo['id'] = summary.config.instanceUuid
        yamlinfo['numcpus'] = config.hardware.numCPU
        yamlinfo['memory'] = config.hardware.memoryMB
        yamlinfo['status'] = translation[runtime.powerState]
        yamlinfo['nets'] = []
        yamlinfo['disks'] = []
        for entry in config.extraConfig:
            if entry.key in METADATA_FIELDS:
                yamlinfo[entry.key] = entry.value
            if entry.key == 'image':
                image = entry.value
                yamlinfo['user'] = common.get_user(entry.value)
            if entry.key == 'tags':
                yamlinfo['tags'] = entry.value
            if entry.key == 'ip':
                yamlinfo['ip'] = entry.value
        kubetype = yamlinfo.get('kubetype')
        cluster_network = yamlinfo.get('cluster_network')
        ips = []
        if runtime.powerState == "poweredOn":
            yamlinfo['host'] = runtime.host.name
            for nic in guest.net:
                if nic.ipAddress:
                    ip = nic.ipAddress[0]
                    if not ip.startswith('fe80::') and not ip.startswith('169.254') and not sdn_ip(ip, kubetype,
                                                                                                   cluster_network):
                        ips.append(ip)
                        if 'ip' not in yamlinfo:
                            yamlinfo['ip'] = ip
        if len(ips) > 1:
            yamlinfo['ips'] = ips
        if listinfo:
            return yamlinfo
        if image is None and kubetype is not None and kubetype == 'openshift':
            yamlinfo['user'] = 'core'
        if debug:
            yamlinfo['debug'] = config
        if not self.networks:
            self.set_networks()
        devices = config.hardware.device
        for number, dev in enumerate(devices):
            if "addressType" in dir(dev):
                try:
                    network = dev.backing.deviceName
                except:
                    switchuuid = dev.backing.port.switchUuid
                    portgroupkey = dev.backing.port.portgroupKey
                    for dvsnet in self.portgs:
                        if self.portgs[dvsnet][0] == switchuuid and self.portgs[dvsnet][1] == portgroupkey:
                            network = dvsnet
                device = dev.deviceInfo.label
                devicename = type(dev).__name__.replace('vim.vm.device.Virtual', '').lower()
                networktype = devicename
                mac = dev.macAddress
                net = {'device': device, 'mac': mac, 'net': network, 'type': networktype}
                yamlinfo['nets'].append(net)
            if type(dev).__name__ == 'vim.vm.device.VirtualDisk':
                device = dev.deviceInfo.label
                disksize = convert(1000 * dev.capacityInKB, GB=False)
                diskformat = dev.backing.diskMode
                drivertype = 'thin' if dev.backing.thinProvisioned else 'thick'
                path = dev.backing.datastore.name
                disk = {'device': device, 'size': int(disksize), 'format': diskformat, 'type': drivertype,
                        'path': path}
                yamlinfo['disks'].append(disk)
            if isinstance(dev, vim.vm.device.VirtualCdrom)\
               and hasattr(dev.backing, 'fileName') and dev.backing.fileName is not None\
               and dev.backing.fileName.endswith('.iso'):
                yamlinfo['iso'] = dev.backing.fileName
        if obj.snapshot is not None and obj.snapshot.currentSnapshot is not None:
            yamlinfo['snapshot'] = obj.snapshot.rootSnapshotList[0].name
        return yamlinfo

    def list(self):
        si = self.si
        content = si.content
        vms = []
        vmFolder = self.basefolder
        all_vms = get_all_obj(content, [vim.VirtualMachine], folder=vmFolder)
        if not all_vms:
            return vms
        prop_collector = content.propertyCollector
        props = ['runtime', 'config', 'summary', 'guest']
        filter_spec = create_filter_spec(all_vms, props)
        options = vmodl.query.PropertyCollector.RetrieveOptions()
        vmlist = prop_collector.RetrievePropertiesEx([filter_spec], options)
        for o in vmlist.objects:
            obj = o.obj
            vmname = obj.name
            vm = convert_properties(o)
            summary, config = vm.get('summary'), vm.get('config')
            if summary is None or config is None:
                continue
            elif summary.runtime.connectionState != 'orphaned' and not config.template:
                if self.filtervms and 'plan' not in [x.key for x in config.extraConfig]:
                    continue
                try:
                    vms.append(self.info(vmname, vm=vm))
                except:
                    continue
        return sorted(vms, key=lambda x: x['name'])

    def list_pools(self):
        pools = []
        rootFolder = self.rootFolder
        si = self.si
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        for dts in clu.datastore:
            pools.append(dts.name)
            # datastorename = dts.name
            # total = dssize(dts)[0].replace('GB', '')
            # available = dssize(dts)[1].replace('GB', '')
            # results[datastorename] = [float(total), float(available), dc.name]
        return pools

    def beststorage(self):
        rootFolder = self.rootFolder
        si = self.si
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        bestds = ''
        bestsize = 0
        for dts in clu.datastore:
            datastorename = dts.name
            available = float(dssize(dts)[1].replace('GB', ''))
            if available > bestsize:
                bestsize = available
                bestds = datastorename
        return bestds

    def _getisos(self):
        rootFolder = self.rootFolder
        si = self.si
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        isos = []
        searchspec = vim.host.DatastoreBrowser.SearchSpec()
        filequery = [vim.host.DatastoreBrowser.IsoImageQuery(), vim.host.DatastoreBrowser.FolderQuery()]
        filequeryflags = vim.host.DatastoreBrowser.FileInfo.Details()
        filequeryflags.fileSize = True
        filequeryflags.modification = False
        filequeryflags.fileOwner = False
        filequeryflags.fileType = False
        searchspec.query = filequery
        searchspec.details = filequeryflags
        searchspec.sortFoldersFirst = True
        searchspec.searchCaseInsensitive = True
        for dts in clu.datastore:
            datastorename = dts.name
            datastorepath = f'[{datastorename}]'
            browser = dts.browser
            t = browser.SearchDatastore_Task(datastorepath, searchspec)
            waitForMe(t)
            result = t.info.result
            for element in result.file:
                folderpath = element.path
                if 'iso' in folderpath.lower():
                    t = browser.SearchDatastoreSubFolders_Task(f"{datastorepath}{folderpath}", searchspec)
                    waitForMe(t)
                    for r in t.info.result:
                        for isofile in r.file:
                            iso_path = f"{datastorepath}/{folderpath}/{isofile.path}"
                            if iso_path.endswith('.iso') and iso_path not in isos:
                                isos.append(iso_path)
        return isos

    def volumes(self, iso=False):
        if iso:
            return self._getisos()
        results = []
        si = self.si
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.VirtualMachine], True)
        vmlist = o.view
        o.Destroy()
        vms = [v for v in vmlist if v.config.template and
               (v.summary is None or (v.summary is not None and v.summary.runtime.connectionState != 'orphaned'))]
        for v in sorted(vms, key=lambda x: x.name):
            devices = v.config.hardware.device
            for number, dev in enumerate(devices):
                if type(dev).__name__ == 'vim.vm.device.VirtualDisk':
                    prefix = '' if self.restricted else f'{dev.backing.datastore.name}/'
                    results.append(f'{prefix}{v.name}')
        return sorted(results)

    def update_metadata(self, name, metatype, metavalue, append=False):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        configspec = vim.vm.ConfigSpec()
        opt = vim.option.OptionValue()
        opt.key = metatype
        opt.value = metavalue
        configspec.extraConfig = [opt]
        t = vm.ReconfigVM_Task(configspec)
        waitForMe(t)

    def update_memory(self, name, memory):
        if memory % 1024 != 0:
            warning("Rounding up memory to be multiple of 1024")
            memory += (1024 - memory) % 1024
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        configspec = vim.vm.ConfigSpec()
        configspec.memoryMB = memory
        t = vm.ReconfigVM_Task(configspec)
        waitForMe(t)

    def update_cpus(self, name, numcpus):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        configspec = vim.vm.ConfigSpec()
        configspec.numCPUs = numcpus
        t = vm.ReconfigVM_Task(configspec)
        waitForMe(t)

    def update_start(self, name, start=True):
        print("not implemented")

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if iso is not None:
            isos = [i for i in self._getisos() if i.endswith(iso)]
            if not isos:
                error(f"Iso {iso} not found.Leaving...")
                return {'result': 'failure', 'reason': f"Iso {iso} not found"}
            else:
                iso = isos[0]
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        c = changecd(self.si, vm, iso)
        if iso is None:
            answered = False
            timeout = 0
            while not answered:
                question = vm.runtime.question
                if question is not None:
                    pprint(f"Answering the following question automatically\n{vm.runtime.question.text}")
                    choice = vm.runtime.question.choice.choiceInfo[0].key
                    vm.AnswerVM(question.id, choice)
                    answered = True
                elif timeout > 20:
                    break
                else:
                    time.sleep(5)
        waitForMe(c)
        return {'result': 'success'}

    def convert_to_template(self, name):
        if self.esx:
            msg = "Operation not supported on single ESX"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        elif not self.esx:
            vm.MarkAsTemplate()

    def convert_to_vm(self, name):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        else:
            rootFolder = self.rootFolder
            clu = find(si, rootFolder, vim.ComputeResource, self.clu)
            vm.MarkAsVirtualMachine(pool=clu.resourcePool)

    def dnsinfo(self, name):
        return None, None

    def _uploadimage(self, pool, origin, directory, isofolder=None):
        si = self.si
        dc = self.dc
        rootFolder = self.rootFolder
        datastore = find(si, rootFolder, vim.Datastore, pool)
        if not datastore:
            msg = f"Pool {pool} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        destination = os.path.basename(origin)
        if isofolder is not None:
            directory = isofolder
        url = f"https://{self.vcip}:443/folder/{directory}/{destination}?dcPath={dc.name}&dsName={pool}"
        client_cookie = si._stub.cookie
        cookie_name = client_cookie.split("=", 1)[0]
        cookie_value = client_cookie.split("=", 1)[1].split(";", 1)[0]
        cookie_path = client_cookie.split("=", 1)[1].split(";", 1)[1].split(";", 1)[0].lstrip()
        cookie_text = " " + cookie_value + "; $" + cookie_path
        headers = {'Content-Type': 'application/octet-stream', 'Cookie': f"{cookie_name}={cookie_text}"}
        with open(origin, "rb") as f:
            context = ssl._create_unverified_context()
            try:
                req = urllib.request.Request(url, data=f, headers=headers, method='PUT')
                urllib.request.urlopen(req, context=context)
            except:
                url = url.replace('/folder', '')
                req = urllib.request.Request(url, data=f, headers=headers, method='PUT')
                try:
                    urllib.request.urlopen(req, context=context)
                except Exception as e:
                    error(f"Hit issue with with reason: {e}")

    def get_pool_path(self, pool):
        return pool

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}, diskname=None):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        config = info['config']
        spec = vim.vm.ConfigSpec()
        unit_number = 0
        for dev in config.hardware.device:
            if hasattr(dev.backing, 'fileName'):
                unit_number = int(dev.unitNumber) + 1
                if unit_number == 7:
                    unit_number = 8
            if isinstance(dev, vim.vm.device.VirtualSCSIController):
                controller = dev
        new_disk_kb = int(size) * 1024 * 1024
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = "create"
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.thinProvisioned = thin
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.capacityInKB = new_disk_kb
        disk_spec.device.controllerKey = controller.key
        dev_changes = [disk_spec]
        spec.deviceChange = dev_changes
        t = vm.ReconfigVM_Task(spec=spec)
        waitForMe(t)
        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        config = info['config']
        for dev in config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualDisk) and dev.deviceInfo.label == diskname:
                devspec = vim.vm.device.VirtualDeviceSpec()
                devspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                devspec.device = dev
                spec = vim.vm.ConfigSpec()
                spec.deviceChange = [devspec]
                t = vm.ReconfigVM_Task(spec=spec)
                waitForMe(t)
                return {'result': 'success'}
        msg = f"Disk {diskname} not found in {name}"
        error(msg)
        return {'result': 'failure', 'reason': error}

    def detach_disks(self, name):
        pprint(f"Detaching data disks from {name}")
        si = self.si
        dc = self.dc
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        config = info['config']
        disks = [dev for dev in config.hardware.device if isinstance(dev, vim.vm.device.VirtualDisk)]
        if len(disks) > 1:
            for index, disk in enumerate(disks[1:]):
                devspec = vim.vm.device.VirtualDeviceSpec()
                devspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                devspec.device = disk
                spec = vim.vm.ConfigSpec()
                spec.deviceChange = [devspec]
                t = vm.ReconfigVM_Task(spec=spec)
                waitForMe(t)
                datastore = disk.backing.datastore.name
                path = f"[{datastore}] {name}"
                keep_path = f"[{datastore}] {name}_keep"
                fileManager = self.si.content.fileManager
                if index == 0:
                    fileManager.MakeDirectory(name=keep_path, datacenter=dc)
                file_name = f"{name}_{index + 1}"
                for entry in [f"{file_name}.vmdk", f"{file_name}-flat.vmdk"]:
                    t = fileManager.MoveDatastoreFile_Task(sourceName=f"{path}/{entry}",
                                                           sourceDatacenter=dc,
                                                           destinationName=f"{keep_path}/{entry}",
                                                           destinationDatacenter=dc,
                                                           force=True)
                    WaitForTask(t)
        return {'result': 'success'}

    def add_nic(self, name, network, model='virtio'):
        if network == 'default':
            network = 'VM Network'
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        config = info['config']
        spec = vim.vm.ConfigSpec()
        nicnumber = len([dev for dev in config.hardware.device if "addressType" in dir(dev)])
        nicname = 'Network adapter %d' % (nicnumber + 1)
        nicspec = createnicspec(nicname, network)
        nic_changes = [nicspec]
        spec.deviceChange = nic_changes
        t = vm.ReconfigVM_Task(spec=spec)
        waitForMe(t)
        return {'result': 'success'}

    def delete_nic(self, name, interface):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        config = info['config']
        for dev in config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard) and dev.deviceInfo.label == interface:
                devspec = vim.vm.device.VirtualDeviceSpec()
                devspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                devspec.device = dev
                spec = vim.vm.ConfigSpec()
                spec.deviceChange = [devspec]
                t = vm.ReconfigVM_Task(spec=spec)
                waitForMe(t)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': f"Nic {interface} not found in {name}"}

    def list_networks(self):
        si = self.si
        rootFolder = si.content.rootFolder
        networks = {}
        view = si.content.viewManager.CreateContainerView(rootFolder, [vim.Network], True)
        netlist = collectproperties(si, view=view, objtype=vim.Network, pathset=['name'], includemors=True)
        for o in netlist:
            network = o['obj']
            cidr, dhcp, domainname = '', '', ''
            mode = 'accessible' if network.summary.accessible else 'notaccessible'
            networks[network.name] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
        if self.dvs:
            view = si.content.viewManager.CreateContainerView(rootFolder, [vim.dvs.DistributedVirtualPortgroup], True)
            dvslist = collectproperties(si, view=view, objtype=vim.dvs.DistributedVirtualPortgroup, pathset=['name'],
                                        includemors=True)
            for o in dvslist:
                network = o['obj']
                cidr, dhcp, domainname, mode = '', '', '', ''
                networks[network.name] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed',
                                          'mode': mode}
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        return networkinfo

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        si = self.si
        cluster = self.clu
        networkFolder = self.dc.networkFolder
        rootFolder = self.rootFolder
        net = find(si, rootFolder, vim.Network, name)
        if net is not None:
            msg = f"Network {name} already there"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.DistributedVirtualSwitch], True)
        dvnetworks = o.view
        o.Destroy()
        for dvnetw in dvnetworks:
            for portg in dvnetw.portgroup:
                if portg.name == name:
                    msg = f"Network {name} already there"
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
        if overrides.get('distributed', False):
            pnic_specs = []
            dvs_host_configs = []
            uplink_port_names = []
            dvs_create_spec = vim.DistributedVirtualSwitch.CreateSpec()
            dvs_config_spec = vim.DistributedVirtualSwitch.ConfigSpec()
            dvs_config_spec.name = name
            dvs_config_spec.uplinkPortPolicy = vim.DistributedVirtualSwitch.NameArrayUplinkPortPolicy()
            for x in range(len(cluster.host)):
                uplink_port_names.append("dvUplink%d" % x)
            for host in cluster.host:
                dvs_config_spec.uplinkPortPolicy.uplinkPortName = uplink_port_names
                dvs_config_spec.maxPorts = 2000
                pnic_spec = vim.dvs.HostMember.PnicSpec()
                pnic_spec.pnicDevice = 'vmnic1'
                pnic_specs.append(pnic_spec)
                dvs_host_config = vim.dvs.HostMember.ConfigSpec()
                dvs_host_config.operation = vim.ConfigSpecOperation.add
                dvs_host_config.host = host
                dvs_host_configs.append(dvs_host_config)
                dvs_host_config.backing = vim.dvs.HostMember.PnicBacking()
                dvs_host_config.backing.pnicSpec = pnic_specs
                dvs_config_spec.host = dvs_host_configs
                dvs_create_spec.configSpec = dvs_config_spec
            dvs_create_spec.productInfo = vim.dvs.ProductSpec(version='5.1.0')
            networkFolder.CreateDistributedVirtualSwitch()
        else:
            return {'result': 'failure', 'reason': "Not implemented yet for non dvs networks"}
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        si = self.si
        rootFolder = self.rootFolder
        try:
            net = find(si, rootFolder, vim.dvs.DistributedVirtualPortgroup, name)
            net.Destroy()
        except:
            try:
                net = find(si, rootFolder, vim.Network, name)
                net.Destroy()
            except:
                msg = f"Network {name} not found"
                error(msg)
                return {'result': 'failure', 'reason': msg}
        return {'result': 'success'}

    def vm_ports(self, name):
        return ['default']

    def add_image(self, url, pool, short=None, cmds=[], name=None, size=None, convert=False):
        si = self.si
        rootFolder = self.rootFolder
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        resourcepool = clu.resourcePool
        vmFolder = self.basefolder
        manager = si.content.ovfManager
        shortimage = os.path.basename(url).split('?')[0]
        name = name.replace('.ova', '').replace('.x86_64', '') if name is not None else shortimage
        iso = True if shortimage.endswith('.iso') or name.endswith('.iso') else False
        if not shortimage.endswith('ova') and not shortimage.endswith('zip') and not iso\
           and which('qemu-img') is None:
            msg = "qemu-img is required for conversion"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        if shortimage in [os.path.basename(v) for v in self.volumes()]:
            pprint(f"Template {shortimage} already there")
            return {'result': 'success'}
        if not find(si, rootFolder, vim.Datastore, pool):
            msg = f"Pool {pool} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        if os.path.exists(url):
            pprint(f"Using {url} as path")
        elif not os.path.exists(f'/tmp/{shortimage}'):
            pprint(f"Downloading locally {shortimage}")
            downloadcmd = f"curl -kLo /tmp/{shortimage} -f '{url}'"
            code = os.system(downloadcmd)
            if code != 0:
                msg = "Unable to download indicated image"
                error(msg)
                return {'result': 'failure', 'reason': msg}
        else:
            pprint(f"Using found /tmp/{shortimage}")
        if iso:
            isofile = os.path.abspath(url) if os.path.exists(url) else f"/tmp/{shortimage}"
            if name is not None:
                new_file = f"{os.path.dirname(isofile)}/{name}"
                os.rename(isofile, new_file)
                isofile = new_file
            if self.isofolder is not None:
                isofolder = self.isofolder.split('/')
                isopool = re.sub(r"[\[\]]", '', isofolder[0])
                isofolder = isofolder[1]
            else:
                isopool = pool
                isofolder = None
            destination = '' if isofolder is not None else name
            self._uploadimage(isopool, isofile, destination, isofolder=isofolder)
            return {'result': 'success'}
        vmdk_path = None
        ovf_path = None
        basedir = os.path.dirname(os.path.abspath(url)) if os.path.exists(url) else '/tmp'
        if url.endswith('zip'):
            with ZipFile(f"{basedir}/{shortimage}") as zipf:
                for _fil in zipf.namelist():
                    if _fil.endswith('vmdk'):
                        vmdk_path = f'{basedir}/{_fil}'
                    elif _fil.endswith('ovf'):
                        ovf_path = f'{basedir}/{_fil}'
                if vmdk_path is None or ovf_path is None:
                    msg = "Incorrect ova file"
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
                zipf.extractall(basedir)
        elif url.endswith('ova'):
            with tarfile.open(f"{basedir}/{shortimage}") as tar:
                for _fil in [x.name for x in tar.getmembers()]:
                    if _fil.endswith('vmdk'):
                        vmdk_path = f'{basedir}/{_fil}'
                    elif _fil.endswith('ovf'):
                        ovf_path = f'{basedir}/{_fil}'
                if vmdk_path is None or ovf_path is None:
                    msg = "Incorrect ova file"
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
                tar.extractall(basedir)
        else:
            need_uncompress = any(shortimage.endswith(suffix) for suffix in ['.gz', '.xz', '.bz2', '.zst'])
            if need_uncompress:
                extension = os.path.splitext(shortimage)[1].replace('.', '')
                executable = {'xz': 'unxz', 'gz': 'gunzip', 'bz2': 'bunzip2', 'zst': 'zstd'}
                flag = '--decompress' if extension == 'zstd' else '-f'
                executable = executable[extension]
                uncompresscmd = f"{executable} {flag} {basedir}/{shortimage}"
                os.system(uncompresscmd)
                shortimage = shortimage.replace(f'.{extension}', '')
            if '.' in shortimage:
                extension = os.path.splitext(shortimage)[1].replace('.', '')
                vmdk_file = shortimage.replace(extension, 'vmdk')
            else:
                vmdk_file = f"{shortimage}.vmdk"
            vmdk_path = f"{basedir}/{vmdk_file}"
            if cmds and shortimage.endswith('qcow2') and which('virt-customize') is not None:
                for cmd in cmds:
                    cmd = f"virt-customize -a {basedir}/{shortimage} --run-command '{cmd}'"
                    os.system(cmd)
            if not os.path.exists(vmdk_path):
                pprint("Converting qcow2 file to vmdk")
                cmd = f"qemu-img convert -O vmdk -o subformat=streamOptimized {basedir}/{shortimage} {vmdk_path}"
                os.popen(cmd).read()
            ovf_path = vmdk_path.replace('.vmdk', '.ovf')
            commondir = os.path.dirname(common.pprint.__code__.co_filename)
            vmdk_info = json.loads(os.popen(f"qemu-img info {vmdk_path} --output json").read())
            virtual_size = vmdk_info['virtual-size']
            actual_size = vmdk_info['actual-size']
            ovfcontent = open(f"{commondir}/vm.ovf.j2").read().format(name=shortimage, virtual_size=virtual_size,
                                                                      actual_size=actual_size, vmdk_file=vmdk_file,
                                                                      import_network=self.import_network)
            with open(ovf_path, 'w') as f:
                f.write(ovfcontent)
        ovfd = open(ovf_path).read()
        ovfd = re.sub('<Name>.*</Name>', f'<Name>{name}</Name>', ovfd)
        datastore = find(si, rootFolder, vim.Datastore, pool)
        network = None
        for host in self._get_hosts(self.clu):
            networks = [n for n in host.network if n.name == self.import_network]
            if networks:
                pprint(f"Using esxi host {host.name} for import")
                network = networks[0]
                break
        if network is None:
            error(f"Couldn't find any esxi host in the cluster with network {self.import_network}")
            error("Set import_network to a valid value")
            sys.exit(1)
        networkmapping = vim.OvfManager.NetworkMapping.Array()
        nm = vim.OvfManager.NetworkMapping(name="VM Network", network=network)
        networkmapping.append(nm)
        spec_params = vim.OvfManager.CreateImportSpecParams(diskProvisioning="thin", networkMapping=networkmapping,
                                                            hostSystem=host)
        import_spec = manager.CreateImportSpec(ovfd, resourcepool, datastore, spec_params)
        if import_spec.error:
            error(f"Import spec error: {import_spec.error}")
            sys.exit(1)
        lease = resourcepool.ImportVApp(import_spec.importSpec, vmFolder)
        while True:
            if lease.state == vim.HttpNfcLease.State.ready:
                url = lease.info.deviceUrl[0].url.replace('*', host.name)
                pprint(f"Uploading {vmdk_path} to {url}")
                keepalive_thread = Thread(target=keep_lease_alive, args=(lease,))
                keepalive_thread.start()
                cmd = f'curl -k -# -X POST -T {vmdk_path} -H "Content-Type: application/x-vnd.vmware-streamVmdk" {url}'
                call(cmd, shell=True)
                lease.HttpNfcLeaseComplete()
                keepalive_thread.join()
                break
            elif lease.state == vim.HttpNfcLease.State.error:
                error(f"Lease error: {lease.error}")
                sys.exit(1)
        if not self.esx:
            self.convert_to_template(name)
            if os.path.exists(f'{basedir}/{shortimage}'):
                os.remove(f'{basedir}/{shortimage}')
            if os.path.exists(vmdk_path):
                os.remove(vmdk_path)
        return {'result': 'success'}

    def _get_hosts(self, cluster):
        si = self.si
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.ComputeResource], True)
        view = o.view
        o.Destroy()
        for clu in view:
            if clu.name == cluster:
                return clu.host
        return []

    def info_host(self):
        data = {}
        si = self.si
        about = si.content.about
        data['vcenter'] = self.vcip
        data['version'] = about.version
        data['api_version'] = about.apiVersion
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.Datacenter], True)
        view = o.view
        o.Destroy()
        datacenters = []
        for datacenter in view:
            new_datacenter = {}
            new_datacenter['datacenter'] = datacenter.name
            clusters = []
            for clu in datacenter.hostFolder.childEntity:
                new_clu = {}
                new_clu['cluster'] = clu.name
                datastores = []
                for dts in clu.datastore:
                    datastores.append(dts.name)
                new_clu['datastores'] = datastores
                hosts = []
                for h in clu.host:
                    hosts.append(h.name)
                new_clu['datastores'] = datastores
                networks = []
                for n in clu.network:
                    networks.append(n.name)
                new_clu['networks'] = networks
                clusters.append(new_clu)
            new_datacenter['clusters'] = clusters
            datacenters.append(new_datacenter)
        data['datacenters'] = datacenters
        return data

    def delete_image(self, image, pool=None):
        si = self.si
        if image.endswith('.iso'):
            matching_isos = [iso for iso in self._getisos() if iso.endswith(image)]
            if not matching_isos:
                return {'result': 'failure', 'reason': f'Iso {image} not found'}
            else:
                isopath = matching_isos[0]
                deletedirectory(si, self.dc, isopath)
                return {'result': 'success'}
        if '/' in image:
            pool, image = image.split('/')
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, image)
        if vm is None or not info['config'].template:
            return {'result': 'failure', 'reason': f'Image {image} not found'}
        else:
            t = vm.Destroy_Task()
            waitForMe(t)
            return {'result': 'success'}

    def export(self, name, image=None):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if info['runtime'].powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        vm.MarkAsTemplate()
        if image is not None:
            vm.Rename(image)
        return {'result': 'success'}

    def list_dns(self, domain):
        return []

    def create_bucket(self, bucket, public=False):
        print("not implemented")

    def delete_bucket(self, bucket):
        print("not implemented")

    def delete_from_bucket(self, bucket, path):
        print("not implemented")

    def download_from_bucket(self, bucket, path):
        print("not implemented")

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        print("not implemented")

    def list_buckets(self):
        print("not implemented")
        return []

    def list_bucketfiles(self, bucket):
        print("not implemented")
        return []

    def get_guestid(image):
        if 'centos' in image.lower():
            guestid = 'centos8_64Guest'
        elif 'rhel' in image.lower() or 'rhcos' in image.lower():
            guestid = 'rhel8_64Guest'
        elif 'fedora' in image.lower() or 'fos' in image.lower():
            guestid = 'fedora64Guest'
        elif 'ubuntu' in image.lower():
            guestid = 'ubuntu64Guest'
        elif 'debian' in image.lower():
            guestid = 'debian10_64Guest'
        else:
            guestid = 'genericLinuxGuest'
        return guestid

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        print("not implemented")

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        si = self.si
        restricted = self.restricted
        rootFolder = self.rootFolder
        vmFolder = self.basefolder
        old_info = self.info(old)
        plan, cluster = old_info.get('plan'), old_info.get('cluster')
        if not restricted:
            if cluster is not None:
                createfolder(si, vmFolder, cluster)
                vmFolder = find(si, vmFolder, vim.Folder, cluster)
            elif plan != 'kvirt':
                createfolder(si, vmFolder, plan)
                vmFolder = find(si, vmFolder, vim.Folder, plan)
        si = self.si
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        resourcepool = clu.resourcePool
        imageobj = findvm(si, rootFolder, old)
        if imageobj is None:
            return {'result': 'failure', 'reason': f"VM {old} not found"}
        clonespec = createclonespec(resourcepool)
        confspec = vim.vm.ConfigSpec()
        confspec.annotation = new
        extraconfig = []
        clonespec.powerOn = start
        confspec.extraConfig = extraconfig
        t = imageobj.CloneVM_Task(folder=vmFolder, name=new, spec=clonespec)
        waitForMe(t)
        return {'result': 'success'}

    def create_snapshot(self, name, base):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, base)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        description = f"Snapshot {name}"
        dump_memory = False
        quiesce = False
        t = vm.CreateSnapshot(name, description, dump_memory, quiesce)
        waitForMe(t)
        return {'result': 'success'}

    def delete_snapshot(self, name, base):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, base)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        snapshots = vm.snapshot.rootSnapshotList if vm.snapshot is not None else []
        for snapshot in snapshots:
            if snapshot.name == name:
                t = snapshot.snapshot.RemoveSnapshot_Task(True)
                waitForMe(t)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': f'Snapshot {name} not found'}

    def list_snapshots(self, base):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, base)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        snapshots = vm.snapshot.rootSnapshotList if vm.snapshot is not None else []
        return [snapshot.name for snapshot in snapshots]

    def revert_snapshot(self, name, base):
        si = self.si
        vmFolder = self.basefolder
        vm, info = findvm2(si, vmFolder, base)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        snapshots = vm.snapshot.rootSnapshotList if vm.snapshot is not None else []
        for snapshot in snapshots:
            if snapshot.name == name:
                t = snapshot.snapshot.RevertToSnapshot_Task()
                waitForMe(t)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': f'Snapshot {name} not found'}

    def ip(self, name):
        result = None
        si = self.si
        vmFolder = self.basefolder
        obj, vm = findvm2(si, vmFolder, name)
        guest = vm['guest']
        if vm is not None:
            runtime = vm['runtime']
            guest = vm['guest']
            if runtime.powerState == "poweredOn":
                for nic in guest.net:
                    if nic.ipAddress:
                        result = nic.ipAddress[0]
                        break
        return result

    def create_vm_folder(self, name):
        si = self.si
        vmFolder = self.basefolder
        if find(si, vmFolder, vim.Folder, name) is None:
            createfolder(si, vmFolder, name)

    def list_flavors(self):
        return []

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

    def list_disks(self):
        print("not implemented")

    def list_subnets(self):
        print("not implemented")
        return {}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")

    def delete_pool(self, name, full=False):
        print("not implemented")

    def disk_exists(self, pool, name):
        print("not implemented")

    def network_ports(self, name):
        print("not implemented")

    def update_flavor(self, name, flavor):
        print("not implemented")
        return {'result': 'success'}

    def _datastores_datacenters(self):
        si = self.si
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.Datacenter], True)
        view = o.view
        o.Destroy()
        datastores = {}
        for datacenter in view:
            for clu in datacenter.hostFolder.childEntity:
                if 'ClusterComputeResource' not in str(clu.__class__):
                    continue
                for datastore in clu.datastore:
                    datastores[datastore.name] = datacenter.name
        return datastores

    def info_subnet(self, name):
        print("not implemented")
        return {}

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        print("not implemented")
        return {'result': 'success'}

    def update_subnet(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_dns_zones(self):
        print("not implemented")
        return []

    def set_macs(self, name, macs):
        vm = find(self.si, self.dc.vmFolder, vim.VirtualMachine, name)
        currentdevices = vm.config.hardware.device
        currentnics = [d for d in currentdevices if isinstance(d, vim.vm.device.VirtualEthernetCard)]
        confspec = vim.vm.ConfigSpec()
        devconfspec = []
        for index in macs:
            currentnic = currentnics[index]
            currentnic.macAddress = macs[index]
            currentnic.addressType = vim.vm.device.VirtualEthernetCardOption.MacTypes.manual
            nicspec = vim.vm.device.VirtualDeviceSpec(device=currentnic, operation="edit")
            devconfspec.append(nicspec)
        confspec.deviceChange = devconfspec
        t = vm.Reconfigure(confspec)
        waitForMe(t)

    def reconnect_hosts(self):
        si = self.si
        rootFolder = self.rootFolder
        view = si.content.viewManager.CreateContainerView(rootFolder, [vim.HostSystem], True)
        for host in view.view:
            pprint(f"Reconnecting Host {host.name}")
            host.Reconnect()
