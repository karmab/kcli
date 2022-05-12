#!/usr/bin/python

import base64
from binascii import hexlify
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from distutils.spawn import find_executable
from kvirt import common
from kvirt.common import error, pprint, warning
from kvirt.defaults import UBUNTUS, METADATA_FIELDS
from pyVmomi import vim, vmodl
from pyVim import connect
import json
import os
import re
import requests
import random
from ssl import get_server_certificate
import sys
import tarfile
from tempfile import TemporaryDirectory
from threading import Thread
import time
import webbrowser
from zipfile import ZipFile
from kvirt.providers.vsphere.helpers import find, collectproperties, findvm, createfolder, changecd, convert, waitForMe
from kvirt.providers.vsphere.helpers import createscsispec, creatediskspec, createdvsnicspec, createclonespec
from kvirt.providers.vsphere.helpers import createnicspec, createisospec, deletedirectory, dssize, keep_lease_alive
from kvirt.providers.vsphere.helpers import create_filter_spec, get_all_obj, convert_properties, findvm2


class Ksphere:
    def __init__(self, host, user, password, datacenter, cluster, debug=False, isofolder=None,
                 filtervms=False, filteruser=False, filtertag=None, category='kcli', basefolder=None, dvs=True):
        si = connect.SmartConnectNoSSL(host=host, port=443, user=user, pwd=password)
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
        self.basefolder = basefolder
        return

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
        diskmode = 'persistent'
        default_diskinterface = diskinterface
        default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        memory = int(memory)
        numcpus = int(numcpus)
        si = self.si
        basefolder = self.basefolder
        rootFolder = self.rootFolder
        if basefolder is not None:
            createfolder(si, dc.vmFolder, basefolder)
            basefolder = find(si, dc.vmFolder, vim.Folder, basefolder)
        else:
            basefolder = dc.vmFolder
        cluster = overrides.get('cluster')
        if cluster is not None:
            createfolder(si, basefolder, cluster)
            vmfolder = find(si, basefolder, vim.Folder, cluster)
        elif plan != 'kvirt':
            createfolder(si, basefolder, plan)
            vmfolder = find(si, basefolder, vim.Folder, plan)
        else:
            vmfolder = basefolder
        si = self.si
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        resourcepool = clu.resourcePool
        if image is not None:
            rootFolder = self.rootFolder
            imageobj = findvm(si, rootFolder, image)
            if imageobj is None:
                return {'result': 'failure', 'reason': f"Image {image} not found"}
            clonespec = createclonespec(resourcepool)
            confspec = vim.vm.ConfigSpec()
            confspec.annotation = name
            confspec.memoryMB = memory
            confspec.numCPUs = numcpus
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
            cloudinitiso = None
            if cloudinit:
                if image is not None and common.needs_ignition(image):
                    version = common.ignition_version(image)
                    ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                                   domain=domain, files=files, enableroot=enableroot,
                                                   overrides=overrides, version=version, plan=plan, image=image)
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
                    # customspec = makecuspec(name, nets=nets, gateway=gateway, dns=dns, domain=domain)
                    # clonespec.customization = customspec
                    isofolder = self.isofolder if self.isofolder is not None else f"[{default_pool}]/{name}"
                    cloudinitiso = f"{isofolder}/{name}.ISO"
                    userdata, meta, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                               gateway=gateway, dns=dns, domain=domain,
                                                               files=files, enableroot=enableroot, overrides=overrides,
                                                               storemetadata=storemetadata, machine='vsphere',
                                                               image=image)
            for key in overrides:
                if key.startswith('guestinfo.'):
                    guestopt = vim.option.OptionValue()
                    guestopt.key = key
                    # guestopt.value = base64.b64encode(overrides[key].encode()).decode()
                    guestopt.value = overrides[key]
                    extraconfig.append(guestopt)
            confspec.extraConfig = extraconfig
            t = imageobj.CloneVM_Task(folder=vmfolder, name=name, spec=clonespec)
            waitForMe(t)
            if cloudinitiso is not None:
                with TemporaryDirectory() as tmpdir:
                    common.make_iso(name, tmpdir, userdata, meta, netdata)
                    cloudinitisofile = f"{tmpdir}/{name}.ISO"
                    if self.isofolder is not None:
                        isofolder = self.isofolder.split('/')
                        isopool = re.sub(r"[\[\]]", '', isofolder[0])
                        isofolder = isofolder[1]
                    else:
                        isopool = default_pool
                        isofolder = None
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
            if index == 0:
                scsispec = createscsispec()
                devconfspec.append(scsispec)
            diskspec = creatediskspec(index, disksize, datastore, diskmode, diskthin, index)
            devconfspec.append(diskspec)
        # NICSPEC
        if not self.networks:
            self.set_networks()
        for index, net in enumerate(nets):
            netname = net['name'] if isinstance(net, dict) else net
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
                        nicspec = vim.vm.device.VirtualDeviceSpec(device=currentnic, operation="edit")
                        devconfspec.append(nicspec)
                    elif netname in self.networks:
                        currentnic.backing.deviceName = netname
                        nicspec = vim.vm.device.VirtualDeviceSpec(device=currentnic, operation="edit")
                        devconfspec.append(nicspec)
                    else:
                        return {'result': 'failure', 'reason': f"Invalid network {netname}"}
                continue
            nicname = 'Network Adapter %d' % (index + 1)
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
        if iso:
            if '/' not in iso:
                matchingisos = [i for i in self._getisos() if i.endswith(iso)]
                if matchingisos:
                    iso = matchingisos[0]
                else:
                    return {'result': 'failure', 'reason': f"Iso {iso} not found"}
            cdspec = createisospec(iso)
            devconfspec.append(cdspec)
            # bootoptions = vim.option.OptionValue(key='bios.bootDeviceClasses',value='allow:hd,cd,fd,net')
            # confspec.bootOptions = vim.vm.BootOptions(bootOrder=[vim.vm.BootOptions.BootableCdromDevice()])
        confspec.deviceChange = devconfspec
        if nested:
            confspec.nestedHVEnabled = True
        t = vm.Reconfigure(confspec)
        waitForMe(t)
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
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
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
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        runtime = info['runtime']
        if runtime.powerState == "poweredOn":
            t = vm.PowerOffVM_Task()
            waitForMe(t)
        return {'result': 'success'}

    def status(self, name):
        si = self.si
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
        vm, info = findvm2(si, vmFolder, name)
        runtime = info['runtime']
        return runtime.powerState if vm is not None else ''

    def delete(self, name, snapshots=False):
        si = self.si
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
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
            deletedirectory(si, dc, isopath)
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

    def console(self, name, tunnel=False, web=False):
        si = self.si
        vcip = self.vcip
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
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
            host = runtime.host.name
            url = f"vnc://{host}:{vncport}"
            consolecommand = f"remote-viewer {url} &"
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
            dc = self.dc
            basefolder = self.basefolder
            vmFolder = find(si, dc.vmFolder, vim.Folder, basefolder) if basefolder is not None else dc.vmFolder
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
        yamlinfo['cpus'] = config.hardware.numCPU
        yamlinfo['memory'] = config.hardware.memoryMB
        yamlinfo['status'] = translation[runtime.powerState]
        yamlinfo['nets'] = []
        yamlinfo['disks'] = []
        if runtime.powerState == "poweredOn":
            yamlinfo['host'] = runtime.host.name
            for nic in guest.net:
                if 'ip' not in yamlinfo and nic.ipAddress:
                    yamlinfo['ip'] = nic.ipAddress[0]
        for entry in config.extraConfig:
            if entry.key in METADATA_FIELDS:
                yamlinfo[entry.key] = entry.value
            if entry.key == 'image':
                image = entry.value
                yamlinfo['user'] = common.get_user(entry.value)
            if entry.key == 'tags':
                yamlinfo['tags'] = entry.value
        if listinfo:
            return yamlinfo
        if image is None and 'kubetype' in yamlinfo and yamlinfo['kubetype'] == 'openshift':
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
        return yamlinfo

    def list(self):
        si = self.si
        dc = self.dc
        content = si.content
        vms = []
        folder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
        all_vms = get_all_obj(content, [vim.VirtualMachine], folder=folder)
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
            summary, config = vm['summary'], vm['config']
            if summary.runtime.connectionState != 'orphaned' and not config.template:
                if self.filtervms and 'plan' not in [x.key for x in config.extraConfig]:
                    continue
                vms.append(self.info(vmname, vm=vm))
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
                    t = browser.SearchDatastoreSubFolders_Task(f"{datastorepath}{folderpath}", searchspec)
                    waitForMe(t)
                    results = t.info.result
                    for r in results:
                        fileinfo = r.file
                        for isofile in fileinfo:
                            path = isofile.path
                            if path.endswith('.iso'):
                                isos.append(f"{datastorepath}/{folderpath}/{path}")
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
            return {'result': 'failure', 'reason': f"VM {name} not found"}
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
        if iso is not None:
            isos = [i for i in self._getisos() if i.endswith(iso)]
            if not isos:
                error(f"Iso {iso} not found.Leaving...")
                return {'result': 'failure', 'reason': f"Iso {iso} not found"}
            else:
                iso = isos[0]
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
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

    def dnsinfo(self, name):
        return None, None

    def _uploadimage(self, pool, origin, directory, isofolder=None):
        si = self.si
        rootFolder = self.rootFolder
        datastore = find(si, rootFolder, vim.Datastore, pool)
        if not datastore:
            return {'result': 'failure', 'reason': f"Pool {pool} not found"}
        destination = os.path.basename(origin)
        if isofolder is not None:
            directory = isofolder
        url = f"https://{self.vcip}:443/folder/{directory}/{destination}?dcPath={self.dc.name}&dsName={pool}"
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
                try:
                    r = requests.put(url, data=f, headers=headers, cookies=cookie, verify=False)
                except:
                    url = url.replace('/folder', '')
                    r = requests.put(url, data=f, headers=headers, cookies=cookie, verify=False)
                if r.status_code not in [200, 201]:
                    error(f"Got status {r.status_code} with reason: {r.reason}")

    def get_pool_path(self, pool):
        return pool

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        si = self.si
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
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
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
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

    def add_nic(self, name, network):
        if network == 'default':
            network = 'VM Network'
        si = self.si
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
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
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
        vm, info = findvm2(si, vmFolder, name)
        if vm is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
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
            return {'result': 'failure', 'reason': f"Network {name} already there"}
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.DistributedVirtualSwitch], True)
        dvnetworks = o.view
        o.Destroy()
        for dvnetw in dvnetworks:
            for portg in dvnetw.portgroup:
                if portg.name == name:
                    return {'result': 'failure', 'reason': f"Network {name} already there"}
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

    def delete_network(self, name=None, cidr=None):
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
                return {'result': 'failure', 'reason': f"Network {name} not found"}
        return {'result': 'success'}

    def vm_ports(self, name):
        return []

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None):
        si = self.si
        rootFolder = self.rootFolder
        clu = find(si, rootFolder, vim.ComputeResource, self.clu)
        resourcepool = clu.resourcePool
        vmFolder = self.dc.vmFolder
        manager = si.content.ovfManager
        shortimage = os.path.basename(url).split('?')[0]
        name = name.replace('.ova', '').replace('.x86_64', '') if name is not None else shortimage
        iso = True if shortimage.endswith('.iso') or name.endswith('.iso') else False
        if not shortimage.endswith('ova') and not shortimage.endswith('zip') and not iso\
           and find_executable('qemu-img') is None:
            msg = "qemu-img is required for conversion"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        if shortimage in self.volumes():
            pprint(f"Template {shortimage} already there")
            return {'result': 'success'}
        if not find(si, rootFolder, vim.Datastore, pool):
            return {'result': 'failure', 'reason': f"Pool {pool} not found"}
        if not os.path.exists(f'/tmp/{shortimage}'):
            pprint(f"Downloading locally {shortimage}")
            downloadcmd = f"curl -Lo /tmp/{shortimage} -f '{url}'"
            code = os.system(downloadcmd)
            if code != 0:
                return {'result': 'failure', 'reason': "Unable to download indicated image"}
        else:
            pprint(f"Using found /tmp/{shortimage}")
        if iso:
            isofile = f"/tmp/{shortimage}"
            if name is not None:
                os.rename(f"/tmp/{shortimage}", f"/tmp/{name}")
                isofile = f"/tmp/{name}"
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
        if url.endswith('zip'):
            with ZipFile(f"/tmp/{shortimage}") as zipf:
                for _fil in zipf.namelist():
                    if _fil.endswith('vmdk'):
                        vmdk_path = f'/tmp/{_fil}'
                    elif _fil.endswith('ovf'):
                        ovf_path = f'/tmp/{_fil}'
                if vmdk_path is None or ovf_path is None:
                    return {'result': 'failure', 'reason': "Incorrect ova file"}
                zipf.extractall('/tmp')
        elif url.endswith('ova'):
            with tarfile.open(f"/tmp/{shortimage}") as tar:
                for _fil in [x.name for x in tar.getmembers()]:
                    if _fil.endswith('vmdk'):
                        vmdk_path = f'/tmp/{_fil}'
                    elif _fil.endswith('ovf'):
                        ovf_path = f'/tmp/{_fil}'
                if vmdk_path is None or ovf_path is None:
                    return {'result': 'failure', 'reason': "Incorrect ova file"}
                tar.extractall('/tmp')
        else:
            extension = os.path.splitext(shortimage)[1].replace('.', '')
            vmdk_file = shortimage.replace(extension, 'vmdk')
            vmdk_path = f"/tmp/{vmdk_file}"
            if not os.path.exists(vmdk_path):
                pprint("Converting qcow2 file to vmdk")
                os.popen(f"qemu-img convert -O vmdk -o subformat=streamOptimized /tmp/{shortimage} {vmdk_path}")
            ovf_path = "/tmp/%s" % shortimage.replace(extension, 'ovf')
            commondir = os.path.dirname(common.pprint.__code__.co_filename)
            time.sleep(5)
            vmdk_info = json.loads(os.popen(f"qemu-img info {vmdk_path} --output json").read())
            virtual_size = vmdk_info['virtual-size']
            actual_size = vmdk_info['actual-size']
            ovfcontent = open(f"{commondir}/vm.ovf.j2").read().format(name=shortimage, virtual_size=virtual_size,
                                                                      actual_size=actual_size, vmdk_file=vmdk_file)
            with open(ovf_path, 'w') as f:
                f.write(ovfcontent)
        ovfd = open(ovf_path).read()
        ovfd = re.sub('<Name>.*</Name>', f'<Name>{name}</Name>', ovfd)
        datastore = find(si, rootFolder, vim.Datastore, pool)
        network = find(si, rootFolder, vim.Network, 'VM Network')
        networkmapping = vim.OvfManager.NetworkMapping.Array()
        nm = vim.OvfManager.NetworkMapping(name="VM Network", network=network)
        networkmapping.append(nm)
        spec_params = vim.OvfManager.CreateImportSpecParams(diskProvisioning="thin", networkMapping=networkmapping)
        import_spec = manager.CreateImportSpec(ovfd, resourcepool, datastore, spec_params)
        lease = resourcepool.ImportVApp(import_spec.importSpec, vmFolder)
        while True:
            if lease.state == vim.HttpNfcLease.State.ready:
                pprint("Uploading vmdk")
                host = self._getfirshost()
                url = lease.info.deviceUrl[0].url.replace('*', host.name)
                keepalive_thread = Thread(target=keep_lease_alive, args=(lease,))
                keepalive_thread.start()
                upload_cmd = (
                    "curl -sS -X POST --insecure -T %s -H 'Content-Type: \
                    application/x-vnd.vmware-streamVmdk' %s" % (vmdk_path, url))
                os.system(upload_cmd)
                lease.HttpNfcLeaseComplete()
                keepalive_thread.join()
                return {'result': 'success'}
            elif lease.state == vim.HttpNfcLease.State.error:
                error(f"Lease error: {lease.error}")
                sys.exit(1)

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
        print(f"Host: {self.vcip}")
        print(f"Datacenter: {self.dc.name}")
        print(f"Version: {about.version}")
        print(f"Api Version: {about.apiVersion}")
        print(f"Datacenter: {self.dc.name}")
        rootFolder = self.rootFolder
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.HostSystem], True)
        view = o.view
        o.Destroy()
        for h in view:
            print(f"Host: {h.name}")
        o = si.content.viewManager.CreateContainerView(rootFolder, [vim.ComputeResource], True)
        view = o.view
        o.Destroy()
        for clu in view:
            print(f"Cluster: {clu.name}")
            for dts in clu.datastore:
                print(f"Pool: {dts.name}")

    def delete_image(self, image, pool=None):
        si = self.si
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
        vm, info = findvm2(si, vmFolder, image)
        if vm is None or not info['config'].template:
            return {'result': 'failure', 'reason': f'Image {image} not found'}
        else:
            t = vm.Destroy_Task()
            waitForMe(t)
            return {'result': 'success'}

    def export(self, name, image=None):
        si = self.si
        dc = self.dc
        vmFolder = find(si, dc.vmFolder, vim.Folder, self.basefolder) if self.basefolder is not None else dc.vmFolder
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
            guestid = 'rhel7_64Guest'
        return guestid

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        print("not implemented")
        return

    def update_nic(self, name, index, network):
        print("not implemented")
