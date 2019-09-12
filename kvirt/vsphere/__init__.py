#!/usr/bin/python

from kvirt import common
import os
import random
from pyVmomi import vim
from pyVim import connect
import time
import pyVmomi
import webbrowser
from ssl import _create_unverified_context


def waitForMe(t):
    while t.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(1)


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
    vmlist = o.view
    o.Destroy()
    vm = None
    for v in vmlist:
        if v.name == name:
            vm = v
            break
    return vm


def findvm(si, folder, name):
    view = si.content.viewManager.CreateContainerView(folder, [vim.VirtualMachine], True)
    vmlist = collectproperties(si, view=view, objtype=vim.VirtualMachine, pathset=['name'], includemors=True)
    vm = list(filter(lambda v: v['name'] == name, vmlist))
    if len(vm) == 1:
        return vm[0]['obj']
    else:
        if len(vm) >= 1:
            common.pprint("Several VMS with name %s found..." % name, color='red')
        return None


def convert(octets):
    return str(float(octets) / 1024 / 1024 / 1024) + "GB"


def dssize(ds):
    di = ds.summary
    return convert(di.capacity), convert(di.freeSpace)


def makecuspec(name, ip1=None, netmask1=None, gateway1=None, ip2=None, netmask2=None, ip3=None, netmask3=None, ip4=None,
               netmask4=None, dns1=None, dns2=None, domain=None):
    customspec = vim.vm.customization.Specification()
    ident = vim.vm.customization.LinuxPrep()
    if domain:
        ident.domain = domain
        ident.hostName = vim.vm.customization.FixedName()
        ident.hostName.name = name
    customspec.identity = ident
    if dns1 or dns2 or domain:
        globalip = vim.vm.customization.GlobalIPSettings()
        if dns1:
            globalip.dnsServerList = [dns1]
        if dns2:
            globalip.dnsServerList.append(dns2)
        if domain:
            globalip.dnsSuffixList = domain
        customspec.globalIPSettings = globalip
    adaptermaps = []
    if ip1 and netmask1 and gateway1 and domain:
        guestmap = vim.vm.customization.AdapterMapping()
        guestmap.adapter = vim.vm.customization.IPSettings()
        guestmap.adapter.ip = vim.vm.customization.FixedIp()
        guestmap.adapter.ip.ipAddress = ip1
        guestmap.adapter.subnetMask = netmask1
        guestmap.adapter.gateway = gateway1
        guestmap.adapter.dnsDomain = domain
        adaptermaps.append(guestmap)
    if ip2 and netmask2:
        guestmap = vim.vm.customization.AdapterMapping()
        guestmap.adapter = vim.vm.customization.IPSettings()
        guestmap.adapter.ip = vim.vm.customization.FixedIp()
        guestmap.adapter.ip.ipAddress = ip2
        guestmap.adapter.subnetMask = netmask2
        adaptermaps.append(guestmap)
    if ip3 and netmask3:
        guestmap = vim.vm.customization.AdapterMapping()
        guestmap.adapter = vim.vm.customization.IPSettings()
        guestmap.adapter.ip = vim.vm.customization.FixedIp()
        guestmap.adapter.ip.ipAddress = ip3
        guestmap.adapter.subnetMask = netmask3
        adaptermaps.append(guestmap)
    if ip4 and netmask4:
        guestmap = vim.vm.customization.AdapterMapping()
        guestmap.adapter = vim.vm.customization.IPSettings()
        guestmap.adapter.ip = vim.vm.customization.FixedIp()
        guestmap.adapter.ip.ipAddress = ip4
        guestmap.adapter.subnetMask = netmask4
        adaptermaps.append(guestmap)
    customspec.nicSettingMap = adaptermaps
    return customspec


def createnicspec(nicname, netname, guestid):
    nicspec = vim.vm.device.VirtualDeviceSpec()
    nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    if guestid in ['rhel4guest', 'rhel4_64guest']:
        nic = vim.vm.device.VirtualVmxnet()
    else:
        nic = vim.vm.device.VirtualVmxnet3()
    desc = vim.Description()
    desc.label = nicname
    nicbacking = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
    desc.summary = netname
    nicbacking.deviceName = netname
    nic.backing = nicbacking
    nic.key = 0
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
    connect = vim.vm.device.VirtualDeviceConnectInfo()
    connect.startConnected = True
    connect.allowGuestControl = True
    connect.connected = False
    cd = vim.vm.device.VirtualCdrom()
    cd.connectable = connect
    cdbacking = vim.vm.device.VirtualCdrom.IsoBackingInfo()
    if iso:
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


guestid532 = 'rhel5guest'
guestid564 = 'rhel5_64Guest'
guestid632 = 'rhel6guest'
guestid664 = 'rhel6_64Guest'
guestid764 = 'rhel7_64Guest'
nicname1 = 'Network Adapter 1'
nicname2 = 'Network Adapter 2'
nicname3 = 'Network Adapter 3'
nicname4 = 'Network Adapter 4'
guests = {'rhel_5': guestid532, 'rhel_5x64': guestid564, 'rhel_6': guestid632, 'rhel_6x64': guestid664,
          'rhel_7x64': guestid764}


class Ksphere:
    def __init__(self, host, user, password, datacenter, cluster, debug=False):
        # 4-1-CONNECT
        si = connect.SmartConnect(host=host, port=443, user=user, pwd=password, sslContext=_create_unverified_context())
        self.conn = si
        self.vcip = host
        self.rootFolder = si.content.rootFolder
        self.dc = find(si, self.rootFolder, vim.Datacenter, datacenter)
        self.macaddr = []
        self.clu = cluster
        return

    def close(self):
        self.conn.content.sessionManager.Logout()

    def exists(self, name):
        si = self.conn
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        return True if vm is not None else False

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

    def create(self, name, numcpu, numinterfaces, diskmode1, disksize1, ds, memory, guestid, net1, net2=None, net3=None,
               net4=None, thin=False, distributed=False, disksize2=None, diskmode2=None, vnc=False, iso=None):
        nets = []
        for net in net1, net2, net3, net4:
            if net is not None:
                nets.append(net)
            else:
                break
        memory = int(memory)
        numcpu = int(numcpu)
        disksize1 = int(disksize1)
        if disksize2:
            disksize2 = int(disksize2)
        numinterfaces = int(numinterfaces)
        if guestid in guests.keys():
            guestid = guests[guestid]
        disksize1 = disksize1 * 1048576
        disksizeg1 = convert(1000 * disksize1)
        if disksize2:
            disksize2 = disksize2 * 1048576
            # disksizeg2 = convert(1000 * disksize2)
        si = self.conn
        dc = self.dc
        rootFolder = self.rootFolder
        vmfolder = dc.vmFolder
        si = self.conn
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        pool = clu.resourcePool
        # SELECT DS
        datastore = find(si, rootFolder, vim.Datastore, ds)
        if not datastore:
            return "%s not found,aborting" % (ds)
        # TODO:change this if to a test sum of all possible disks to be added to this datastore
        if float(dssize(datastore)[1].replace("GB", "")) - float(disksizeg1.replace("GB", "")) <= 0:
            return "New Disk too large to fit in selected Datastore,aborting..."
        # define specifications for the VM
        confspec = vim.vm.ConfigSpec()
        confspec.name = name
        confspec.annotation = name
        confspec.memoryMB = memory
        confspec.numCPUs = numcpu
        confspec.guestId = guestid
        if vnc:
            # enable VNC
            vncport = random.randint(5900, 7000)
            opt1 = vim.option.OptionValue()
            opt1.key = 'RemoteDisplay.vnc.port'
            opt1.value = vncport
            opt2 = vim.option.OptionValue()
            opt2.key = 'RemoteDisplay.vnc.enabled'
            opt2.value = "TRUE"
            confspec.extraConfig = [opt1, opt2]
        # scsispec1, diskspec1, filename1 = creatediskspec(disksize1, datastore, diskmode1, thin)
        scsispec1 = createscsispec()
        diskspec1 = creatediskspec(0, disksize1, datastore, diskmode1, thin)
        devconfspec = [scsispec1, diskspec1]
        if disksize2:
            diskspec2 = creatediskspec(1, disksize2, datastore, diskmode2, thin)
            devconfspec.append(diskspec2)
        # NICSPEC
        if numinterfaces >= 1:
            # NIC 1
            nicspec1 = createnicspec(nicname1, net1, guestid)
        if numinterfaces >= 2:
            # NIC 2
            nicspec2 = createnicspec(nicname2, net2, guestid)
        if numinterfaces >= 3:
            # NIC 3
            nicspec3 = createnicspec(nicname3, net3, guestid)
        if numinterfaces >= 4:
            # NIC 4
            nicspec4 = createnicspec(nicname4, net4, guestid)
        if numinterfaces >= 1:
            devconfspec.append(nicspec1)
        if numinterfaces >= 2:
            devconfspec.append(nicspec2)
        if numinterfaces >= 3:
            devconfspec.append(nicspec3)
        if numinterfaces >= 4:
            devconfspec.append(nicspec4)
        if iso:
            # add iso
            cdspec = createisospec(iso)
            devconfspec.append(cdspec)
        confspec.deviceChange = devconfspec
        vmfi = vim.vm.FileInfo()
        filename = "[" + ds + "]"
        vmfi.vmPathName = filename
        confspec.files = vmfi
        t = vmfolder.CreateVM_Task(confspec, pool, None)
        waitForMe(t)
        return 'success'

        # 2-GETMAC
        vm = findvm(si, vmfolder, name)
        if vm is None:
            return "%s not found" % (name)
        devices = vm.config.hardware.device
        macaddr = []
        for dev in devices:
            if "addressType" in dir(dev):
                macaddr.append(dev.macAddress)
        self.macaddr = macaddr
        # HANDLE DVS
        if distributed:
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
        self.macaddr = macaddr
        return macaddr

    def getmacs(self, name):
        si = self.conn
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return None
        devices = vm.config.hardware.device
        macs = []
        for dev in devices:
            if "addressType" in dir(dev):
                netname = dev.backing.deviceName
                macaddress = dev.macAddress
                macs.append("%s=%s" % (netname, macaddress))
        return macs

    def start(self, name):
        si = self.conn
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
        si = self.conn
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
        si = self.conn
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        return vm.runtime.powerState if vm is not None else ''

    def delete(self, name, snapshots=False):
        si = self.conn
        dc = self.dc
        vmFolder = dc.vmFolder
        vm = findvm(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if vm.runtime.powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        t = vm.Destroy_Task()
        waitForMe(t)
        return {'result': 'success'}

    def console(self, name, tunnel=False):
        si = self.conn
        dc = self.dc
        vcip = self.vcip
        sha1 = self.sha1
        fqdn = self.fqdn
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
            consolecommand = "remote-viewer vnc://%s:%s &" % (host, vncport)
            if self.debug or os.path.exists("/i_am_a_container"):
                print(consolecommand)
            if not os.path.exists("/i_am_a_container"):
                os.popen(consolecommand)
        else:
            sessionmanager = si.content.sessionManager
            session = sessionmanager.AcquireCloneTicket()
            vmid = vm._moId
            vcconsoleport = "7343"
            vmurl = "http://%s:%s/console/?vmId=%s&vmName=%s&host=%s&sessionTicket=%s&thumbprint=%s" % (vcip,
                                                                                                        vcconsoleport,
                                                                                                        vmid, name,
                                                                                                        fqdn, session,
                                                                                                        sha1)
            webbrowser.open(vmurl, new=2, autoraise=True)

    def info(self, name, output='plain', fields=[], values=False, vm=None):
        translation = {'poweredOff': 'down', 'poweredOn': 'up', 'suspended': 'suspended'}
        yamlinfo = {}
        si = self.conn
        dc = self.dc
        vmFolder = dc.vmFolder
        if vm is None:
            vm = findvm(si, vmFolder, name)
            if vm is None:
                common.pprint("VM %s not found" % name, color='red')
                return {}
        summary = vm.summary
        yamlinfo['name'] = name
        yamlinfo['id'] = summary.config.instanceUuid
        yamlinfo['cpus'] = vm.config.hardware.numCPU
        yamlinfo['memory'] = vm.config.hardware.memoryMB
        # yamlinfo['annotation'] = summary.config.annotation
        if summary.guest is not None:
            yamlinfo['ip'] = summary.guest.ipAddress
        yamlinfo['status'] = translation[vm.runtime.powerState]
        return yamlinfo

    def list(self):
        rootFolder = self.rootFolder
        si = self.conn
        vms = []
        view = si.content.viewManager.CreateContainerView(rootFolder, [vim.VirtualMachine], True)
        vmlist = collectproperties(si, view=view, objtype=vim.VirtualMachine, pathset=['name'], includemors=True)
        for o in vmlist:
            vm = o['obj']
            vms.append(self.info(o['name'], vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def getstorage(self):
        rootFolder = self.rootFolder
        si = self.conn
        dc = self.dc
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        results = {}
        for dts in clu.datastore:
            datastorename = dts.name
            total = dssize(dts)[0].replace('GB', '')
            available = dssize(dts)[1].replace('GB', '')
            results[datastorename] = [float(total), float(available), dc.name]
        return results

    def beststorage(self):
        rootFolder = self.rootFolder
        si = self.conn
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
        si = self.conn
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
        si = self.conn
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.VirtualMachine], True)
        vmlist = o.view
        o.Destroy()
        # return map(lambda v: v.name, filter(lambda v: v.config.template, vmlist))
        return [v.name for v in vmlist if v.config.template]

    def createfromtemplate(self, name, templatename, customisation=False, ip1=None, netmask1=None, gateway1=None,
                           ip2=None, netmask2=None, ip3=None, netmask3=None, ip4=None, netmask4=None, dns1=None,
                           dns2=None, domain=None):
        si = self.conn
        rootFolder = self.rootFolder
        template = findvm(si, rootFolder, name)
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        pool = clu.resourcePool
        clonespec = createclonespec(pool)
        if customisation:
            customspec = makecuspec(name, ip1=ip1, netmask1=netmask1, gateway1=gateway1, ip2=ip2, netmask2=netmask2,
                                    ip3=ip3, netmask3=netmask3, ip4=ip4, netmask4=netmask4, dns1=dns1, dns2=dns2,
                                    domain=domain)
            clonespec.customization = customspec
        t = template.CloneVM_Task(template.parent, name, clonespec)
        waitForMe(t)
        return "%s on deploying %s from template" % ('success', name)
