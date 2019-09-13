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
        self.distributed = False
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

#    def create(self, name, ds, numcpus=2, memory=512, guestid='', pool='default', disks=[{'size': 10}], disksize=10,
#               diskthin=False, diskinterface='virtio', nets=['default'], distributed=False, vnc=False, iso=None):
    def create(self, name, virttype='kvm', profile='kvirt', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None,
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags={}, dnsclient=None, storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False):
        distributed = self.distributed
        diskmode = 'persistent'
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        memory = int(memory)
        numcpus = int(numcpus)
        if guestid in guests.keys():
            guestid = guests[guestid]
        si = self.conn
        dc = self.dc
        rootFolder = self.rootFolder
        vmfolder = dc.vmFolder
        si = self.conn
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        pool = clu.resourcePool
        if template is not None:
            rootFolder = self.rootFolder
            templatename = template
            template = findvm(si, rootFolder, template)
            clu = find(si, rootFolder, vim.ComputeResource, self.clu)
            pool = clu.resourcePool
            clonespec = createclonespec(pool)
            customspec = makecuspec(name, nets=nets, gateway=gateway, dns=dns, domain=domain)
            clonespec.customization = customspec
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
            templateopt = vim.option.OptionValue()
            templateopt.key = 'template'
            templateopt.value = templatename
            confspec.extraConfig = [templateopt, planopt, profileopt]
            clonespec.config = confspec
            clonespec.powerOn = start
            t = template.CloneVM_Task(folder=template.parent, name=name, spec=clonespec)
            # t = template.Clone(folder=template.parent, name=name, spec=clonespec)
            waitForMe(t)
            return {'result': 'success'}
        datastores = {}
        # define specifications for the VM
        confspec = vim.vm.ConfigSpec()
        confspec.name = name
        confspec.annotation = name
        confspec.memoryMB = memory
        confspec.numCPUs = numcpus
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
            disksize = disksize * 1048576
            if diskpool not in datastores:
                datastore = find(si, rootFolder, vim.Datastore, diskpool)
                if not datastore:
                    return {'result': 'failure', 'reason': "Pool %s not found" % diskpool}
                else:
                    datastores[diskpool] = datastore
            # scsispec1, diskspec1, filename1 = creatediskspec(disksize1, datastore, diskmode1, thin)
            if index == 0:
                disksizeg = convert(1000 * disksize)
                # # TODO:change this if to a test sum of all possible disks to be added to this datastore
                if float(dssize(datastore)[1].replace("GB", "")) - float(disksizeg.replace("GB", "")) <= 0:
                    return "New Disk too large to fit in selected Datastore,aborting..."
                scsispec = createscsispec()
                devconfspec = [scsispec]
            diskspec = creatediskspec(index, disksize, datastore, diskmode, diskthin)
            devconfspec.append(diskspec)
        # NICSPEC
        for index, net in enumerate(nets):
            nicname = 'Network Adapter %d' % index + 1
            nicspec = createnicspec(nicname, net, guestid)
            devconfspec.append(nicspec)
        if iso:
            # add iso
            cdspec = createisospec(iso)
            devconfspec.append(cdspec)
        confspec.deviceChange = devconfspec
        vmfi = vim.vm.FileInfo()
        filename = "[" + default_pool + "]"
        vmfi.vmPathName = filename
        confspec.files = vmfi
        t = vmfolder.CreateVM_Task(confspec, pool, None)
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
        return {'result': 'success'}

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
        yamlinfo['nets'] = []
        devices = vm.config.hardware.device
        for devnumber, dev in enumerate(devices):
            if "addressType" in dir(dev):
                network = dev.backing.deviceName
                device = dev.deviceInfo.label
                networktype = 'N/A'
                mac = dev.macAddress
                yamlinfo['nets'].append({'device': device, 'mac': mac, 'net': network, 'type': networktype})
        for entry in vm.config.extraConfig:
            if entry.key == 'plan':
                yamlinfo['plan'] = entry.value
            if entry.key == 'profile':
                yamlinfo['profile'] = entry.value
            if entry.key == 'template':
                yamlinfo['template'] = entry.value
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

    def update_metadata(self, name, metatype, metavalue, append=False):
        si = self.conn
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
