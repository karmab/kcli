#!/usr/bin/python

import base64
from binascii import hexlify
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from kvirt import common
from kvirt.common import error, pprint, success
from kvirt.defaults import METADATA_FIELDS
from math import ceil
from pyVmomi import vim, vmodl
from pyVim import connect
import os
import requests
import random
from ssl import _create_unverified_context, get_server_certificate
from tempfile import TemporaryDirectory
import time
import pyVmomi
import webbrowser

GOVC_LINUX = "https://github.com/vmware/govmomi/releases/download/v0.21.0/govc_linux_amd64.gz"
GOVC_MACOSX = GOVC_LINUX.replace('linux', 'darwin')


def waitForMe(t):
    while t.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(1)
    if t.info.state == vim.TaskInfo.State.error:
        error(t.info.description)
        error(t.info.error)
        os._exit(1)


def collectproperties(si, view, objtype, pathset=None, includemors=False):
    collector = si.content.propertyCollector
    # Create object specification to define the starting point of
    # inventory navigation
    objspec = pyVmomi.vmodl.query.PropertyCollector.ObjectSpec()
    objspec.obj = view
    objspec.skip = True
    # Create a traversal specification to identify the path for collection
    traversalspec = pyVmomi.vmodl.query.PropertyCollector.TraversalSpec()
    traversalspec.name = 'traverseEntities'
    traversalspec.path = 'view'
    traversalspec.skip = False
    traversalspec.type = view.__class__
    objspec.selectSet = [traversalspec]
    # Identify the properties to the retrieved
    propertyspec = pyVmomi.vmodl.query.PropertyCollector.PropertySpec()
    propertyspec.type = objtype
    if not pathset:
        propertyspec.all = True
    propertyspec.pathSet = pathset
    # Add the object and property specification to the
    # property filter specification
    filterspec = pyVmomi.vmodl.query.PropertyCollector.FilterSpec()
    filterspec.objectSet = [objspec]
    filterspec.propSet = [propertyspec]
    # Retrieve properties
    props = collector.RetrieveContents([filterspec])
    data = []
    for obj in props:
        properties = {}
        for prop in obj.propSet:
            properties[prop.name] = prop.val
        if includemors:
            properties['obj'] = obj.obj
        data.append(properties)
    return data


def find(si, folder, vimtype, name):
    o = si.content.viewManager.CreateContainerView(folder, [vimtype], True)
    view = o.view
    o.Destroy()
    element = None
    for e in view:
        if e.name == name:
            element = e
            break
    return element


def findvm(si, folder, name):
    view = si.content.viewManager.CreateContainerView(folder, [vim.VirtualMachine], True)
    vmlist = collectproperties(si, view=view, objtype=vim.VirtualMachine, pathset=['name'], includemors=True)
    vm = list(filter(lambda v: v['name'] == name, vmlist))
    if len(vm) >= 1:
        return vm[-1]['obj']
    else:
        return None


def convert(octets, GB=True):
    # return str(float(octets) / 1024 / 1024 / 1024) + "GB"
    result = str(ceil(float(octets) / 1024 / 1024 / 1024))
    if GB:
        result += "GB"
    return result


def dssize(ds):
    di = ds.summary
    return convert(di.capacity), convert(di.freeSpace)


def makecuspec(name, nets=[], gateway=None, dns=None, domain=None):
    customspec = vim.vm.customization.Specification()
    ident = vim.vm.customization.LinuxPrep()
    ident.hostName = vim.vm.customization.FixedName()
    ident.hostName.name = name
    globalip = vim.vm.customization.GlobalIPSettings()
    if domain:
        ident.domain = domain
    customspec.identity = ident
    if dns is not None or domain is not None:
        if dns is not None:
            globalip.dnsServerList = [dns]
        # if dns2:
        #    globalip.dnsServerList.append(dns2)
        if domain is not None:
            globalip.dnsSuffixList = domain
    customspec.globalIPSettings = globalip
    adaptermaps = []
    for index, net in enumerate(nets):
        if isinstance(net, str) or (len(net) == 1 and 'name' in net):
            if index == 0:
                continue
            # nicname = "eth%d" % index
            ip = None
            netmask = None
            # noconf = None
            # vips = []
        elif isinstance(net, dict):
            # nicname = net.get('nic', "eth%d" % index)
            ip = net.get('ip')
            netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
            # noconf = net.get('noconf')
            # vips = net.get('vips')
        if ip is not None and netmask is not None and gateway is not None and domain is not None:
            guestmap = vim.vm.customization.AdapterMapping()
            guestmap.adapter = vim.vm.customization.IPSettings()
            guestmap.adapter.ip = vim.vm.customization.FixedIp()
            guestmap.adapter.ip.ipAddress = ip
            guestmap.adapter.subnetMask = netmask
            guestmap.adapter.gateway = gateway
            guestmap.adapter.dnsDomain = domain
            adaptermaps.append(guestmap)
    customspec.nicSettingMap = adaptermaps
    return customspec


def createnicspec(nicname, netname):
    nicspec = vim.vm.device.VirtualDeviceSpec()
    nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    nic = vim.vm.device.VirtualVmxnet3()
    desc = vim.Description()
    desc.label = nicname
    nicbacking = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
    desc.summary = netname
    nicbacking.deviceName = netname
    nic.backing = nicbacking
    # nic.key = 0
    nic.deviceInfo = desc
    nic.addressType = 'generated'
    nicspec.device = nic
    return nicspec


def createscsispec():
    ckey = 1000
    # SCSISPEC
    scsispec = vim.vm.device.VirtualDeviceSpec()
    scsispec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    # scsictrl          = vim.vm.device.VirtualLsiLogicController()
    scsictrl = vim.vm.device.ParaVirtualSCSIController()
    scsictrl.key = ckey
    scsictrl.busNumber = 0
    scsictrl.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
    scsispec.device = scsictrl
    return scsispec


def creatediskspec(number, disksize, ds, diskmode, thin=False):
    ckey = 1000
    diskspec = vim.vm.device.VirtualDeviceSpec()
    diskspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    diskspec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
    vd = vim.vm.device.VirtualDisk()
    vd.capacityInKB = disksize
    diskspec.device = vd
    vd.unitNumber = number
    vd.controllerKey = ckey
    diskfilebacking = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    filename = "[" + ds.name + "]"
    diskfilebacking.fileName = filename
    diskfilebacking.diskMode = diskmode
    diskfilebacking.thinProvisioned = True if thin else False
    vd.backing = diskfilebacking
    return diskspec


def createcdspec():
    # http://books.google.es/books?id=SdsnGmhF0QEC&pg=PA145&lpg=PA145&dq=VirtualCdrom%2Bspec&source=bl&ots=s8O2mw437-&sig=JpEo-AqmDV42b3fxpTcCt4xknEA&hl=es&sa=X&ei=KgGfT_DqApOy8QOl07X6Dg&redir_esc=y#v=onepage&q=VirtualCdrom%2Bspec&f=false
    cdspec = vim.vm.device.VirtualDeviceSpec()
    cdspec.setOperation(vim.vm.device.VirtualDeviceSpec.Operation.add)
    cd = vim.vm.device.VirtualCdrom()
    cdbacking = vim.vm.device.VirtualCdrom.AtapiBackingInfo()
    cd.backing = cdbacking
    cd.controllerKey = 201
    cd.unitNumber = 0
    cd.key = -1
    cdspec.device = cd
    return cdspec


def createisospec(iso=None):
    cdspec = vim.vm.device.VirtualDeviceSpec()
    cdspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    connect = vim.vm.device.VirtualDevice.ConnectInfo()
    connect.startConnected = True
    connect.allowGuestControl = True
    connect.connected = False
    cd = vim.vm.device.VirtualCdrom()
    cd.connectable = connect
    cdbacking = vim.vm.device.VirtualCdrom.IsoBackingInfo()
    if iso is not None:
        cdbacking.fileName = iso
    cd.backing = cdbacking
    cd.controllerKey = 201
    cd.unitNumber = 0
    cd.key = -1
    cdspec.device = cd
    return cdspec


def createclonespec(pool):
    clonespec = vim.vm.CloneSpec()
    relocatespec = vim.vm.RelocateSpec()
    relocatespec.pool = pool
    clonespec.location = relocatespec
    clonespec.powerOn = False
    clonespec.template = False
    return clonespec


def create_filter_spec(pc, vms):
    objSpecs = []
    for vm in vms:
        objSpec = vmodl.query.PropertyCollector.ObjectSpec(obj=vm)
        objSpecs.append(objSpec)
    filterSpec = vmodl.query.PropertyCollector.FilterSpec()
    filterSpec.objectSet = objSpecs
    propSet = vmodl.query.PropertyCollector.PropertySpec(all=False)
    propSet.type = vim.VirtualMachine
    propSet.pathSet = ['config.extraConfig.plan']
    filterSpec.propSet = [propSet]
    return filterSpec


def filter_results(results):
    vms = []
    for o in results.objects:
        if o.propSet[0].val is not None:
            vms.append(o.obj)
    return vms


def changecd(si, vm, iso):
    virtual_cdrom_device = None
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualCdrom):
            virtual_cdrom_device = dev
            cdromspec = vim.vm.device.VirtualDeviceSpec()
            cdromspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            cdromspec.device = vim.vm.device.VirtualCdrom()
            cdromspec.device.controllerKey = virtual_cdrom_device.controllerKey
            cdromspec.device.key = virtual_cdrom_device.key
            cdromspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            cdromspec.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
            cdromspec.device.backing.fileName = iso
            cdromspec.device.connectable.connected = True
            cdromspec.device.connectable.startConnected = True
            cdromspec.device.connectable.allowGuestControl = True
            dev_changes = []
            dev_changes.append(cdromspec)
            spec = vim.vm.ConfigSpec()
            spec.deviceChange = dev_changes
            task = vm.ReconfigVM_Task(spec=spec)
            return task
    raise RuntimeError("No cdrom found")


def createfolder(si, parentfolder, folder):
    if find(si, parentfolder, vim.Folder, folder) is None:
        parentfolder.CreateFolder(folder)
    return None


def deletefolder(si, parentfolder, folder):
    folder = find(si, parentfolder, vim.Folder, folder)
    if folder is not None:
        folder.Destroy()


def deletedirectory(si, dc, path):
    d = si.content.fileManager.DeleteFile(path, dc)
    waitForMe(d)


class Ksphere:
    def __init__(self, host, user, password, datacenter, cluster, debug=False, filtervms=False, filteruser=False,
                 filtertag=None):
        # 4-1-CONNECT
        si = connect.SmartConnect(host=host, port=443, user=user, pwd=password, sslContext=_create_unverified_context())
        self.conn = si
        self.si = si
        self.vcip = host
        self.url = "https://%s:%s@%s/sdk" % (user, password, host)
        self.rootFolder = si.content.rootFolder
        self.dc = find(si, self.rootFolder, vim.Datacenter, datacenter)
        self.macaddr = []
        self.clu = cluster
        self.distributed = False
        self.filtervms = filtervms
        self.filtervms = filtervms
        self.filteruser = filteruser
        self.filtertag = filtertag
        self.debug = debug
        return

    def close(self):
        self.si.content.sessionManager.Logout()

    def exists(self, name):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        return True if vm is not None else False

    def net_exists(self, name):
        print("not implemented")
        return

    def create(self, name, virttype=None, profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='centos7_64Guest', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None,
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[],
               kernel=None, initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False,
               memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={},
               securitygroups=[]):
        dc = self.dc
        vmFolder = dc.vmFolder
        distributed = self.distributed
        diskmode = 'persistent'
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        memory = int(memory)
        numcpus = int(numcpus)
        si = self.si
        dc = self.dc
        rootFolder = self.rootFolder
        if plan != 'kvirt':
            createfolder(si, dc.vmFolder, plan)
            vmfolder = find(si, dc.vmFolder, vim.Folder, plan)
        else:
            vmfolder = dc.vmFolder
        si = self.si
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        resourcepool = clu.resourcePool
        if image is not None:
            rootFolder = self.rootFolder
            imageobj = findvm(si, rootFolder, image)
            if imageobj is None:
                return {'result': 'failure', 'reason': "Image %s not found" % image}
            clonespec = createclonespec(resourcepool)
            confspec = vim.vm.ConfigSpec()
            confspec.annotation = name
            confspec.memoryMB = memory
            confspec.numCPUs = numcpus
            planopt = vim.option.OptionValue()
            planopt.key = 'plan'
            planopt.value = plan
            profileopt = vim.option.OptionValue()
            profileopt.key = 'profile'
            profileopt.value = profile
            imageopt = vim.option.OptionValue()
            imageopt.key = 'image'
            imageopt.value = image
            extraconfig = [imageopt, planopt, profileopt]
            clonespec.config = confspec
            clonespec.powerOn = False
            cloudinitiso = None
            if cloudinit:
                if image is not None and common.needs_ignition(image):
                    version = common.ignition_version(image)
                    ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                                   domain=domain, reserveip=reserveip, files=files,
                                                   enableroot=enableroot, overrides=overrides, version=version,
                                                   plan=plan, image=image)
                    ignitionopt = vim.option.OptionValue()
                    ignitionopt.key = 'guestinfo.ignition.config.data'
                    ignitionopt.value = base64.b64encode(ignitiondata.encode()).decode()
                    encodingopt = vim.option.OptionValue()
                    encodingopt.key = 'guestinfo.ignition.config.data.encoding'
                    encodingopt.value = 'base64'
                    extraconfig.extend([ignitionopt, encodingopt])
                else:
                    # customspec = makecuspec(name, nets=nets, gateway=gateway, dns=dns, domain=domain)
                    # clonespec.customization = customspec
                    cloudinitiso = "[%s]/%s/%s.ISO" % (default_pool, name, name)
                    userdata, metadata, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                                   gateway=gateway, dns=dns, domain=domain,
                                                                   reserveip=reserveip, files=files,
                                                                   enableroot=enableroot, overrides=overrides,
                                                                   storemetadata=storemetadata)
            confspec.extraConfig = extraconfig
            t = imageobj.CloneVM_Task(folder=vmfolder, name=name, spec=clonespec)
            waitForMe(t)
            if cloudinitiso is not None:
                with TemporaryDirectory() as tmpdir:
                    common.make_iso(name, tmpdir, userdata, metadata, netdata)
                    cloudinitisofile = "%s/%s.ISO" % (tmpdir, name)
                    self._uploadimage(default_pool, cloudinitisofile, name)
                vm = findvm(si, vmFolder, name)
                c = changecd(self.si, vm, cloudinitiso)
                waitForMe(c)
        datastores = {}
        confspec = vim.vm.ConfigSpec()
        confspec.name = name
        confspec.annotation = name
        confspec.memoryMB = memory
        confspec.numCPUs = numcpus
        confspec.extraConfig = []
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            opt = vim.option.OptionValue()
            opt.key = entry
            opt.value = metadata[entry]
            confspec.extraConfig.append(opt)
        if nested:
            confspec.nestedHVEnabled = True
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
            confspec.extraConfig = [opt1, opt2]
        if image is None:
            t = vmfolder.CreateVM_Task(confspec, resourcepool)
            waitForMe(t)
        vm = find(si, dc.vmFolder, vim.VirtualMachine, name)
        currentdevices = vm.config.hardware.device
        currentdisks = [d for d in currentdevices if isinstance(d, vim.vm.device.VirtualDisk)]
        currentnics = [d for d in currentdevices if isinstance(d, vim.vm.device.VirtualEthernetCard)]
        confspec = vim.vm.ConfigSpec()
        devconfspec = []
        for index, disk in enumerate(disks):
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
            if index < len(currentdisks) and image is not None:
                currentdisk = currentdisks[index]
                currentsize = convert(1000 * currentdisk.capacityInKB, GB=False)
                if int(currentsize) < disksize:
                    pprint("Waiting for image disk %s to be resized" % index)
                    currentdisk.capacityInKB = disksize * 1048576
                    diskspec = vim.vm.ConfigSpec()
                    diskspec = vim.vm.device.VirtualDeviceSpec(device=currentdisk, operation="edit")
                    devconfspec.append(diskspec)
                continue
            disksize = disksize * 1048576
            if diskpool not in datastores:
                datastore = find(si, rootFolder, vim.Datastore, diskpool)
                if not datastore:
                    return {'result': 'failure', 'reason': "Pool %s not found" % diskpool}
                else:
                    datastores[diskpool] = datastore
            if index == 0:
                scsispec = createscsispec()
                devconfspec.append(scsispec)
            diskspec = creatediskspec(index, disksize, datastore, diskmode, diskthin)
            devconfspec.append(diskspec)
        # NICSPEC
        for index, net in enumerate(nets):
            if index < len(currentnics):
                continue
            nicname = 'Network Adapter %d' % (index + 1)
            if net == 'default':
                net = 'VM Network'
            nicspec = createnicspec(nicname, net)
            devconfspec.append(nicspec)
        if iso:
            if '/' not in iso:
                matchingisos = [i for i in self._getisos() if i.endswith(iso)]
                if matchingisos:
                    iso = matchingisos[0]
                else:
                    return {'result': 'failure', 'reason': "Iso %s not found" % iso}
            cdspec = createisospec(iso)
            devconfspec.append(cdspec)
            # bootoptions = vim.option.OptionValue(key='bios.bootDeviceClasses',value='allow:hd,cd,fd,net')
            # confspec.bootOptions = vim.vm.BootOptions(bootOrder=[vim.vm.BootOptions.BootableCdromDevice()])
        confspec.deviceChange = devconfspec
        t = vm.Reconfigure(confspec)
        waitForMe(t)
        # HANDLE DVS
        if distributed:
            # 2-GETMAC
            vm = findvm(si, vmfolder, name)
            if vm is None:
                return "%s not found" % (name)
            devices = vm.config.hardware.device
            macaddr = []
            for dev in devices:
                if "addressType" in dir(dev):
                    macaddr.append(dev.macAddress)
            portgs = {}
            o = si.content.viewManager.CreateContainerView(rootFolder, [vim.DistributedVirtualSwitch], True)
            dvnetworks = o.view
            o.Destroy()
            for dvnetw in dvnetworks:
                uuid = dvnetw.uuid
                for portg in dvnetw.portgroup:
                    portgs[portg.name] = [uuid, portg.key]
            for k in range(len(nets)):
                net = nets[k]
                mactochange = macaddr[k]
                if net in portgs.keys():
                    confspec = vim.vm.VirtualMachineSpec()
                    nicspec = vim.vm.device.VirtualDeviceSpec()
                    nicspec.operation = vim.ConfigSpecOperation.edit
                    nic = vim.vm.device.VirtualPCNet32()
                    dnicbacking = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                    dvconnection = vim.dvs.DistributedVirtualSwitchPortConnection()
                    dvconnection.switchUuid = portgs[net][0]
                    dvconnection.portgroupKey = portgs[net][1]
                    dnicbacking.port = dvconnection
                    nic.backing = dnicbacking
                    nicspec.device = nic
                    # 2-GETMAC
                    vm = findvm(si, vmfolder, name)
                    if vm is None:
                        return "%s not found" % (name)
                    devices = vm.config.hardware.device
                    for dev in devices:
                        if "addressType" in dir(dev):
                            mac = dev.macAddress
                            if mac == mactochange:
                                dev.backing = dnicbacking
                                nicspec.device = dev
                                devconfspec = [nicspec]
                                confspec.deviceChange = devconfspec
                                t = vm.reconfigVM_Task(confspec)
                                waitForMe(t)
                                t = vm.PowerOnVM_Task(None)
                                waitForMe(t)
        if start:
            t = vm.PowerOnVM_Task(None)
            waitForMe(t)
        return {'result': 'success'}

    def start(self, name):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.runtime.powerState == "poweredOff":
            t = vm.PowerOnVM_Task(None)
            waitForMe(t)
        return {'result': 'success'}

    def stop(self, name):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.runtime.powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        return {'result': 'success'}

    def status(self, name):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        return vm.runtime.powerState if vm is not None else ''

    def delete(self, name, snapshots=False):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        plan, image = 'kvirt', None
        vmpath = vm.summary.config.vmPathName.replace('/%s.vmx' % name, '')
        for entry in vm.config.extraConfig:
            if entry.key == 'image':
                image = entry.value
            if entry.key == 'plan':
                plan = entry.value
        if vm.runtime.powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        t = vm.Destroy_Task()
        waitForMe(t)
        if image is not None and 'coreos' not in image and 'rhcos' not in image and\
                'fcos' not in image and vmpath.endswith(name):
            deletedirectory(si, dc, vmpath)
        if plan != 'kvirt':
            planfolder = find(si, vmFolder, vim.Folder, plan)
            if planfolder is not None and len(planfolder.childEntity) == 0:
                planfolder.Destroy()
        return {'result': 'success'}

    def console(self, name, tunnel=False, web=False):
        si = self.si
        dc = self.dc
        vcip = self.vcip
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            print("VM %s not found" % name)
            return
        elif vm.runtime.powerState == "poweredOff":
            print("VM down")
            return
        extraconfig = vm.config.extraConfig
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
            host = vm.runtime.host.name
            url = "vnc://%s:%s" % (host, vncport)
            consolecommand = "remote-viewer %s &" % (url)
            if web:
                return url
            if self.debug or os.path.exists("/i_am_a_container"):
                print(consolecommand)
            if not os.path.exists("/i_am_a_container"):
                os.popen(consolecommand)
        else:
            content = si.RetrieveContent()
            sgid = content.about.instanceUuid
            cert = get_server_certificate((self.vcip, 443))
            cert_deserialize = x509.load_pem_x509_certificate(cert.encode(), default_backend())
            finger_print = hexlify(cert_deserialize.fingerprint(hashes.SHA1())).decode('utf-8')
            sha1 = ":".join([finger_print[i: i + 2] for i in range(0, len(finger_print), 2)])
            vcenter_data = content.setting
            vcenter_settings = vcenter_data.setting
            for item in vcenter_settings:
                key = getattr(item, 'key')
                if key == 'VirtualCenter.FQDN':
                    fqdn = getattr(item, 'value')
            sessionmanager = si.content.sessionManager
            session = sessionmanager.AcquireCloneTicket()
            vmid = vm._moId
            vmurl = "https://%s/ui/webconsole.html?" % vcip
            vmurl += "vmId=%s&vmName=%s&serverGuid=%s&host=%s&sessionTicket=%s&thumbprint=%s" % (vmid, name, sgid, fqdn,
                                                                                                 session, sha1)
            if web:
                return vmurl
            if self.debug or os.path.exists("/i_am_a_container"):
                msg = "Open the following url:\n%s" % vmurl if os.path.exists("/i_am_a_container") else vmurl
                pprint(msg)
            else:
                pprint("Opening url %s" % vmurl)
                webbrowser.open(vmurl, new=2, autoraise=True)

    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        translation = {'poweredOff': 'down', 'poweredOn': 'up', 'suspended': 'suspended'}
        yamlinfo = {}
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        if vm is None:
            vm = findvm(si, vmFolder, name)
            if vm is None:
                error("VM %s not found" % name)
                return {}
        summary = vm.summary
        yamlinfo['name'] = name
        yamlinfo['id'] = summary.config.instanceUuid
        yamlinfo['cpus'] = vm.config.hardware.numCPU
        yamlinfo['memory'] = vm.config.hardware.memoryMB
        yamlinfo['status'] = translation[vm.runtime.powerState]
        yamlinfo['nets'] = []
        yamlinfo['disks'] = []
        devices = vm.config.hardware.device
        mainmac = None
        for number, dev in enumerate(devices):
            if "addressType" in dir(dev):
                network = dev.backing.deviceName
                device = dev.deviceInfo.label
                networktype = 'N/A'
                mac = dev.macAddress
                if mainmac is None:
                    mainmac = mac
                net = {'device': device, 'mac': mac, 'net': network, 'type': networktype}
                yamlinfo['nets'].append(net)
            if type(dev).__name__ == 'vim.vm.device.VirtualDisk':
                device = "disk%s" % dev.unitNumber
                disksize = convert(1000 * dev.capacityInKB, GB=False)
                diskformat = dev.backing.diskMode
                drivertype = 'thin' if dev.backing.thinProvisioned else 'thick'
                path = dev.backing.datastore.name
                disk = {'device': device, 'size': int(disksize), 'format': diskformat, 'type': drivertype, 'path': path}
                yamlinfo['disks'].append(disk)
        if vm.runtime.powerState == "poweredOn":
            yamlinfo['host'] = vm.runtime.host.name
            for nic in vm.guest.net:
                currentmac = nic.macAddress
                currentips = nic.ipAddress
                if currentmac == mainmac and currentips:
                    yamlinfo['ip'] = currentips[0]
        for entry in vm.config.extraConfig:
            if entry.key in METADATA_FIELDS:
                yamlinfo[entry.key] = entry.value
            if entry.key == 'image':
                yamlinfo['user'] = common.get_user(entry.value)
        if debug:
            yamlinfo['debug'] = vm.config.extraConfig
        return yamlinfo

    def list(self):
        rootFolder = self.rootFolder
        si = self.si
        vms = []
        view = si.content.viewManager.CreateContainerView(rootFolder, [vim.VirtualMachine], True)
        vmlist = collectproperties(si, view=view, objtype=vim.VirtualMachine, pathset=['name'], includemors=True)
        for o in vmlist:
            vm = o['obj']
            if vm.summary.runtime.connectionState != 'orphaned' and not vm.config.template:
                if self.filtervms and 'plan' not in [x.key for x in vm.config.extraConfig]:
                    continue
                vms.append(self.info(o['name'], vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def list_pools(self):
        pools = []
        rootFolder = self.rootFolder
        si = self.si
        # dc = self.dc
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
        results = {}
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
            datastorepath = "[" + datastorename + "]"
            browser = dts.browser
            t = browser.SearchDatastore_Task(datastorepath, searchspec)
            waitForMe(t)
            result = t.info.result
            fileinfo = result.file
            for element in fileinfo:
                folderpath = element.path
                if not folderpath.endswith('iso') and 'ISO' in folderpath.upper():
                    t = browser.SearchDatastoreSubFolders_Task("%s%s" % (datastorepath, folderpath), searchspec)
                    waitForMe(t)
                    results = t.info.result
                    for r in results:
                        fileinfo = r.file
                        for isofile in fileinfo:
                            path = isofile.path
                            if path.endswith('.iso'):
                                isos.append("%s/%s/%s" % (datastorepath, folderpath, path))
        return isos

    def volumes(self, iso=False):
        if iso:
            return self._getisos()
        si = self.si
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.VirtualMachine], True)
        vmlist = o.view
        o.Destroy()
        return [v.name for v
                in vmlist if v.config.template and v.summary is not
                None and v.summary.runtime.connectionState != 'orphaned']

    def update_metadata(self, name, metatype, metavalue, append=False):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        configspec = vim.vm.ConfigSpec()
        opt = vim.option.OptionValue()
        opt.key = metatype
        opt.value = metavalue
        configspec.extraConfig = [opt]
        t = vm.ReconfigVM_Task(configspec)
        waitForMe(t)

    def update_memory(self, name, memory):
        print("not implemented")
        return

    def update_cpus(self, name, numcpus):
        print("not implemented")
        return

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        isos = [i for i in self._getisos() if i.endswith(iso)]
        if not isos:
            error("Iso %s not found.Leaving..." % iso)
            return {'result': 'failure', 'reason': "Iso %s not found" % iso}
        else:
            iso = isos[0]
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        c = changecd(self.si, vm, iso)
        waitForMe(c)
        return {'result': 'success'}

    def dnsinfo(self, name):
        return None, None

    def _uploadimage(self, pool, origin, directory, verbose=False, temp=False):
        if verbose:
            pprint("Uploading %s to %s/%s" % (origin, pool, directory))
        si = self.si
        rootFolder = self.rootFolder
        datastore = find(si, rootFolder, vim.Datastore, pool)
        if not datastore:
            return {'result': 'failure', 'reason': "Pool %s not found" % pool}
        destination = os.path.basename(origin)
        if temp:
            destination = "temp-%s" % destination
        url = "https://%s:443/folder/%s/%s?dcPath=%s&dsName=%s" % (self.vcip, directory, destination, self.dc.name,
                                                                   pool)
        client_cookie = si._stub.cookie
        cookie_name = client_cookie.split("=", 1)[0]
        cookie_value = client_cookie.split("=", 1)[1].split(";", 1)[0]
        cookie_path = client_cookie.split("=", 1)[1].split(";", 1)[1].split(";", 1)[0].lstrip()
        cookie_text = " " + cookie_value + "; $" + cookie_path
        cookie = {cookie_name: cookie_text}
        headers = {'Content-Type': 'application/octet-stream'}
        with open(origin, "rb") as f:
            if hasattr(requests.packages.urllib3, 'disable_warnings'):
                requests.packages.urllib3.disable_warnings()
                r = requests.put(url, data=f, headers=headers, cookies=cookie, verify=False)
                if verbose:
                    if r.status_code not in [200, 201]:
                        error(r.status_code, r.text)
                    else:
                        success("Successfull upload of %s to %s" % (origin, pool))

    def get_pool_path(self, pool):
        return pool

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        spec = vim.vm.ConfigSpec()
        unit_number = 0
        for dev in vm.config.hardware.device:
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
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualDisk) and dev.deviceInfo.label == diskname:
                devspec = vim.vm.device.VirtualDeviceSpec()
                devspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                devspec.device = dev
                spec = vim.vm.ConfigSpec()
                spec.deviceChange = [devspec]
                t = vm.ReconfigVM_Task(spec=spec)
                waitForMe(t)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': "Disk %s not found in %s" % (diskname, name)}

    def add_nic(self, name, network):
        if network == 'default':
            network = 'VM Network'
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        spec = vim.vm.ConfigSpec()
        nicnumber = len([dev for dev in vm.config.hardware.device if "addressType" in dir(dev)])
        nicname = 'Network adapter %d' % (nicnumber + 1)
        nicspec = createnicspec(nicname, network)
        nic_changes = [nicspec]
        spec.deviceChange = nic_changes
        t = vm.ReconfigVM_Task(spec=spec)
        waitForMe(t)
        return {'result': 'success'}

    def delete_nic(self, name, interface):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard) and dev.deviceInfo.label == interface:
                devspec = vim.vm.device.VirtualDeviceSpec()
                devspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                devspec.device = dev
                spec = vim.vm.ConfigSpec()
                spec.deviceChange = [devspec]
                t = vm.ReconfigVM_Task(spec=spec)
                waitForMe(t)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': "Nic %s not found in %s" % (interface, name)}

    def list_networks(self):
        si = self.si
        rootFolder = si.content.rootFolder
        networks = {}
        view = si.content.viewManager.CreateContainerView(rootFolder, [vim.dvs.DistributedVirtualPortgroup], True)
        dvslist = collectproperties(si, view=view, objtype=vim.dvs.DistributedVirtualPortgroup, pathset=['name'],
                                    includemors=True)
        view = si.content.viewManager.CreateContainerView(rootFolder, [vim.Network], True)
        netlist = collectproperties(si, view=view, objtype=vim.Network, pathset=['name'], includemors=True)
        for o in netlist:
            network = o['obj']
            cidr, dhcp, domainname = '', '', ''
            mode = 'accesible' if network.summary.accessible else 'notaccessible'
            networks[network.name] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
        for o in dvslist:
            network = o['obj']
            cidr, dhcp, domainname, mode = '', '', '', ''
            networks[network.name] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
        return networks

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        return {'result': 'failure', 'reason': "Not implemented yet..."}
        si = self.si
        cluster = self.clu
        networkFolder = self.dc.networkFolder
        rootFolder = self.rootFolder
        net = find(si, rootFolder, vim.Network, name)
        if net is not None:
            return {'result': 'failure', 'reason': "Network %s already there" % name}
        if self.distributed:
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
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        si = self.si
        rootFolder = self.rootFolder
        if self.distributed:
            net = find(si, rootFolder, vim.dvs.DistributedVirtualPortgroup, name)
        else:
            net = find(si, rootFolder, vim.Network, name)
        if net is None:
            return {'result': 'failure', 'reason': "Network %s not found" % name}
        net.Destroy()
        return {'result': 'success'}

    def vm_ports(self, name):
        return []

    def add_image(self, url, pool, short=None, cmd=None, name=None):
        si = self.si
        rootFolder = self.rootFolder
        shortimage = os.path.basename(url).split('?')[0]
        if name is None:
            name = name.replace('.ova', '').replace('.x86_64', '')
        if not url.endswith('ova'):
            return {'result': 'failure', 'reason': "Invalid image. Only ovas are supported"}
        if shortimage in self.volumes():
            pprint("Template %s already there" % shortimage)
            return {'result': 'success'}
        if not find(si, rootFolder, vim.Datastore, pool):
            return {'result': 'failure', 'reason': "Pool %s not found" % pool}
        if not os.path.exists('/tmp/%s' % shortimage):
            pprint("Downloading locally %s" % shortimage)
            downloadcmd = "curl -Lo /tmp/%s -f '%s'" % (shortimage, url)
            code = os.system(downloadcmd)
            if code != 0:
                return {'result': 'failure', 'reason': "Unable to download indicated image"}
        else:
            pprint("Using found /tmp/%s" % shortimage)
        govc = common.get_binary('govc', GOVC_LINUX, GOVC_MACOSX, compressed=True)
        opts = "-name=%s -ds=%s -k=true -u=%s" % (name, pool, self.url)
        ovacmd = "%s import.ova %s /tmp/%s" % (govc, opts, shortimage)
        os.system(ovacmd)
        self.export(name)
        os.remove('/tmp/%s' % shortimage)
        return {'result': 'success'}

    def _getfirshost(self):
        si = self.si
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.HostSystem], True)
        view = o.view
        o.Destroy()
        host = view[0] if view else None
        return host

    def report(self):
        si = self.si
        about = si.content.about
        print("Host: %s" % self.vcip)
        print("Datacenter: %s" % self.dc.name)
        print("Version: %s" % about.version)
        print("Api Version: %s" % about.apiVersion)
        print("Datacenter: %s" % self.dc.name)
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.HostSystem], True)
        view = o.view
        o.Destroy()
        for h in view:
            print("Host: %s" % h.name)
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.ComputeResource], True)
        view = o.view
        o.Destroy()
        for clu in view:
            print("Cluster: %s" % clu.name)
            for dts in clu.datastore:
                print("Pool: %s" % dts.name)

    def delete_image(self, image, pool=None):
        si = self.si
        vmFolder = self.dc.vmFolder
        pprint("Deleting image %s" % image)
        vm = findvm(si, vmFolder, image)
        if vm is None or not vm.config.template:
            return {'result': 'failure', 'reason': 'Image %s not found' % image}
        else:
            t = vm.Destroy_Task()
            waitForMe(t)
            return {'result': 'success'}

    def export(self, name, image=None):
        si = self.si
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.runtime.powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        vm.MarkAsTemplate()
        if image is not None:
            vm.Rename(image)
        return {'result': 'success'}

    def list_dns(self, domain):
        return []
