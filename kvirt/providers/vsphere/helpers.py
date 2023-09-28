from kvirt.common import error
from math import ceil
from pyVmomi import vim, vmodl
import sys
import time
import pyVmomi


def waitForMe(t):
    while t.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(1)
    if t.info.state == vim.TaskInfo.State.error:
        error(t.info.description)
        error(t.info.error)
        sys.exit(1)


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
    return vm[-1]['obj'] if len(vm) >= 1 else None


def findvm2(si, folder, name, props=['runtime', 'config', 'summary', 'guest']):
    content = si.content
    all_vms = get_all_obj(content, [vim.VirtualMachine], folder=folder)
    if not all_vms:
        return None, None
    prop_collector = content.propertyCollector
    filter_spec = create_filter_spec(all_vms, props)
    options = vmodl.query.PropertyCollector.RetrieveOptions()
    vmlist = prop_collector.RetrievePropertiesEx([filter_spec], options)
    vms = [o for o in vmlist.objects if o.obj.name == name]
    return (vms[0].obj, convert_properties(vms[0])) if vms else (None, None)


def findvmdc(si, folder, name, datacenter):
    view = si.content.viewManager.CreateContainerView(folder, [vim.VirtualMachine], True)
    vmlist = collectproperties(si, view=view, objtype=vim.VirtualMachine, pathset=['name'], includemors=True)
    vms = list(filter(lambda v: v['name'] == name, vmlist))
    result = None, None
    for vm in vms:
        obj = vm['obj'].parent
        while not isinstance(obj, vim.Datacenter):
            obj = obj.parent
        result = vm['obj'], obj.name
        if obj.name == datacenter.name:
            return result
    return result


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


def createnicspec(nicname, netname, nictype=None):
    nicspec = vim.vm.device.VirtualDeviceSpec()
    nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    if nictype == 'pcnet32':
        nic = vim.vm.device.VirtualPCNet32()
    elif nictype == 'e1000':
        nic = vim.vm.device.VirtualE1000()
    elif nictype == 'e1000e':
        nic = vim.vm.device.VirtualE1000e()
    else:
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


def createdvsnicspec(nicname, netname, switchuuid, portgroupkey, nictype=None):
    nicspec = vim.vm.device.VirtualDeviceSpec()
    nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    if nictype == 'pcnet32':
        nic = vim.vm.device.VirtualPCNet32()
    elif nictype == 'e1000':
        nic = vim.vm.device.VirtualE1000()
    elif nictype == 'e1000e':
        nic = vim.vm.device.VirtualE1000e()
    else:
        nic = vim.vm.device.VirtualVmxnet3()
    dnicbacking = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
    dvconnection = vim.dvs.DistributedVirtualSwitchPortConnection()
    dvconnection.switchUuid = switchuuid
    dvconnection.portgroupKey = portgroupkey
    dnicbacking.port = dvconnection
    nic.backing = dnicbacking
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


def creatediskspec(unit_number, disksize, ds, diskmode, thin=False):
    ckey = 1000
    diskspec = vim.vm.device.VirtualDeviceSpec()
    diskspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    diskspec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
    vd = vim.vm.device.VirtualDisk()
    vd.capacityInKB = disksize
    vd.key = 2000 + unit_number
    diskspec.device = vd
    vd.unitNumber = unit_number
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
            cdromspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            cdromspec.device.connectable.allowGuestControl = True
            cdromspec.device.controllerKey = virtual_cdrom_device.controllerKey
            cdromspec.device.key = virtual_cdrom_device.key
            if iso is not None:
                cdromspec.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
                cdromspec.device.backing.fileName = iso
                cdromspec.device.connectable.connected = True
                cdromspec.device.connectable.startConnected = True
            else:
                cdromspec.device.backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
                cdromspec.device.connectable.connected = False
                cdromspec.device.connectable.startConnected = False
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


def keep_lease_alive(lease):
    while True:
        time.sleep(5)
        try:
            lease.HttpNfcLeaseProgress(50)
            if (lease.state == vim.HttpNfcLease.State.done):
                return
        except:
            return


def get_all_obj(content, vim_type, folder=None, recurse=True):
    if not folder:
        folder = content.rootFolder

    obj = {}
    container = content.viewManager.CreateContainerView(folder, vim_type, recurse)

    for managed_object_ref in container.view:
        obj[managed_object_ref] = managed_object_ref.name

    container.Destroy()
    return obj


def create_filter_spec(vms, props=[]):
    obj_specs = []
    for vm in vms:
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec(obj=vm)
        obj_specs.append(obj_spec)
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = obj_specs
    prop_set = vmodl.query.PropertyCollector.PropertySpec(all=False)
    prop_set.type = vim.VirtualMachine
    prop_set.pathSet = props
    filter_spec.propSet = [prop_set]
    return filter_spec


def convert_properties(obj):
    result = {}
    for prop in obj.propSet:
        result[prop.name] = prop.val
    return result
