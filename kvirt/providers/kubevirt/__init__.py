# -*- coding: utf-8 -*-

import base64
from ipaddress import ip_address
from kubernetes import client
from kvirt.cluster.kubecommon import Kubecommon
from kvirt import common
from kvirt.common import error, pprint, warning
from kvirt.defaults import IMAGES, UBUNTUS, METADATA_FIELDS
import datetime
import os
import sys
import time
import yaml
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from uuid import UUID

DOMAIN = "kubevirt.io"
CDIDOMAIN = "cdi.kubevirt.io"
CDIVERSION = "v1beta1"
FLAVORDOMAIN = "instancetype.kubevirt.io"
FLAVORVERSION = "v1alpha2"
KUBEVIRTNAMESPACE = "kube-system"
VERSION = 'v1'
MULTUSDOMAIN = 'k8s.cni.cncf.io'
MULTUSVERSION = 'v1'
HDOMAIN = "harvesterhci.io"
HVERSION = "v1beta1"
SRIOVDOMAIN = 'sriovnetwork.openshift.io'
SRIOVVERSION = 'v1'
CONTAINERDISKS = ['quay.io/kubevirt/alpine-container-disk-demo', 'quay.io/kubevirt/cirros-container-disk-demo',
                  'quay.io/karmab/debian-container-disk-demo', 'quay.io/karmab/freebsd-container-disk-demo',
                  'quay.io/kubevirt/fedora-cloud-container-disk-demo',
                  'quay.io/karmab/fedora-coreos-container-disk-demo', 'quay.io/karmab/gentoo-container-disk-demo',
                  'quay.io/karmab/ubuntu-container-disk-demo', 'quay.io/repository/containerdisks/rhcos',
                  'quay.io/containerdisks/fedora']
CONTAINERDISKS = [f'{container}:latest' for container in CONTAINERDISKS]
KUBECTL_LINUX = "https://storage.googleapis.com/kubernetes-release/release/v1.16.1/bin/linux/amd64/kubectl"
KUBECTL_MACOSX = KUBECTL_LINUX.replace('linux', 'darwin')
DEFAULT_SC = 'storageclass.kubernetes.io/is-default-class'


def _base_image_size(image):
    if 'rhcos' in image.lower():
        size = 20
    elif 'centos' in image.lower():
        size = 11
    else:
        size = 9
    return size


class Kubevirt(Kubecommon):
    def __init__(self, token=None, ca_file=None, context=None, host='127.0.0.1', port=6443, user='root', debug=False,
                 namespace=None, disk_hotplug=False, readwritemany=False, access_mode='NodePort',
                 volume_mode='Filesystem', volume_access='ReadWriteOnce', harvester=False, embed_userdata=False,
                 first_consumer=False, kubeconfig_file=None):
        Kubecommon.__init__(self, token=token, ca_file=ca_file, context=context, host=host, port=port,
                            namespace=namespace, readwritemany=readwritemany, kubeconfig_file=kubeconfig_file)
        self.crds = client.CustomObjectsApi(api_client=self.api_client)
        self.debug = debug
        self.access_mode = access_mode
        self.volume_mode = volume_mode
        self.volume_access = volume_access
        self.disk_hotplug = disk_hotplug
        self.harvester = harvester
        self.embed_userdata = embed_userdata
        self.first_consumer = first_consumer
        self.kubeconfig_file = kubeconfig_file
        return

    def close(self):
        return

    def exists(self, name):
        crds = self.crds
        namespace = self.namespace
        allvms = crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines')["items"]
        for vm in allvms:
            if vm.get("metadata")["namespace"] == namespace and vm.get("metadata")["name"] == name:
                return True
        return False

    def net_exists(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace,
                                              'network-attachment-definitions', name)
        except:
            return False
        return True

    def disk_exists(self, pool, name):
        print("not implemented")
        return

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model', cpuflags=[],
               cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool=None, image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, alias=[], overrides={}, tags=[], storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False,
               metadata={}, securitygroups=[], vmuser=None):
        owners = []
        container_disk = overrides.get('container_disk', False)
        guestagent = False
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        if image is not None:
            if '/' not in image:
                image = image.replace('.', '-').replace('_', '-')
            elif ':' not in image:
                warning("Adding :latest to image")
                image += ':latest'
            if image not in self.volumes():
                if image in ['alpine', 'cirros', 'fedora-cloud']:
                    image = f"kubevirt/{image}-container-disk-demo"
                    pprint(f"Using container disk {image} as image")
                elif image in ['debian', 'gentoo', 'ubuntu']:
                    image = f"karmab/{image}-container-disk-demo"
                    pprint(f"Using container disk {image} as image")
                elif '/' not in image:
                    return {'result': 'failure', 'reason': f"you don't have image {image}"}
            if image.startswith('kubevirt/fedora-cloud-registry-disk-demo') and memory <= 512:
                memory = 1024
        default_disksize = disksize
        default_diskinterface = diskinterface
        default_pool = pool
        crds = self.crds
        core = self.core
        harvester = self.harvester
        namespace = self.namespace
        if harvester:
            harvester_images = {}
            virtualimages = crds.list_namespaced_custom_object(HDOMAIN, HVERSION, namespace,
                                                               'virtualmachineimages')["items"]
            for img in virtualimages:
                imagename = img['metadata']['name']
                harvester_images[common.filter_compression_extension(os.path.basename(img['spec']['url']))] = imagename
        confidential = 'confidential' in overrides and overrides['confidential']
        if confidential:
            uefi, secureboot = True, False
        final_tags = {}
        if tags:
            if isinstance(tags, dict):
                final_tags.update(tags)
            else:
                for tag in tags:
                    if isinstance(tag, str) and len(tag.split('=')) == 2:
                        final_tags[tag.split('=')[0]] = tag.split('=')[1]
                    elif isinstance(tag, dict):
                        final_tags.update(tag)
                    else:
                        warning(f"Couldn't process tag {tag}. Skipping...")
                        continue
        labels = {'kubevirt.io/provider': 'kcli', 'kubevirt.io/domain': name, 'kubevirt.io/os': 'linux'}
        labels.update(final_tags)
        vm = {'kind': 'VirtualMachine', 'spec': {'running': start, 'template':
                                                 {'metadata': {'labels': labels},
                                                  'spec': {'domain': {'resources':
                                                                      {'requests': {'memory': f'{memory}M'},
                                                                       'limits': {'memory': f'{memory}M'}},
                                                                      'cpu': {'cores': numcpus},
                                                                      'devices': {'disks': []}}, 'volumes': []}}},
              'apiVersion': f'kubevirt.io/{VERSION}', 'metadata': {'name': name, 'namespace': namespace,
                                                                   'labels': labels, 'annotations': {}}}
        if flavor is not None and flavor not in ['', 'None']:
            if flavor not in [f[0] for f in self.list_flavors()]:
                return {'result': 'failure', 'reason': f"Invalid flavor/instance type {flavor}"}
            else:
                vm['spec']['instancetype'] = {'name': flavor}
                del vm['spec']['template']['spec']['domain']['cpu']
                del vm['spec']['template']['spec']['domain']['resources']
        if 'annotations' in overrides:
            vm['metadata']['annotations'] = overrides['annotations']
        if 'uuid' in overrides:
            uuid = str(overrides['uuid'])
            try:
                UUID(uuid)
                vm['spec']['template']['spec']['domain']['firmware'] = {'uuid': uuid}
            except:
                warning(f"couldn't use {uuid} as uuid")
        if confidential:
            vm['spec']['template']['spec']['domain']['launchSecurity'] = {'sev': {}}
        if 'vsock' in overrides and overrides['vsock']:
            vm['spec']['template']['spec']['domain']['devices']['autoattachVSOCK'] = True
        kube = False
        for entry in sorted([field for field in metadata if field in METADATA_FIELDS]):
            vm['metadata']['annotations'][f'kcli/{entry}'] = metadata[entry]
            if entry == 'kube':
                kube = True
                role = 'ctlplane' if name.endswith('bootstrap') else name.split('-')[-2]
                vm['spec']['template']['metadata']['labels']['kcli/role'] = role
            if entry == 'plan' and kube:
                vm['spec']['template']['metadata']['labels']['kcli/plan'] = metadata[entry]
        if domain is not None:
            if reservedns:
                vm['spec']['template']['spec']['hostname'] = name
                vm['spec']['template']['spec']['subdomain'] = domain.replace('.', '-')
                vm['spec']['template']['metadata']['labels']['subdomain'] = domain.replace('.', '-')
        features = {}
        machine = 'q35'
        if 'machine' in overrides:
            machine = overrides['machine']
            warning(f"Forcing machine type to {machine}")
        vm['spec']['template']['spec']['domain']['machine'] = {'type': machine}
        if overrides.get('guest_memory', False):
            del vm['spec']['template']['spec']['domain']['resources']['requests']
            del vm['spec']['template']['spec']['domain']['resources']['limits']
            vm['spec']['template']['spec']['domain']['memory'] = {'guest': f'{memory}Mi'}
        if cpumodel != 'host-model':
            vm['spec']['template']['spec']['domain']['cpu']['model'] = cpumodel
        if 'rng' in overrides and overrides['rng']:
            vm['spec']['template']['spec']['domain']['devices']['rng'] = {}
        if numa:
            vm['spec']['template']['spec']['domain']['cpu']['dedicatedCpuPlacement'] = True
            vm['spec']['template']['spec']['domain']['cpu']['numa'] = {'guestMappingPassthrough': {}}
        if 'realtime' in overrides and overrides['realtime']:
            vm['spec']['template']['spec']['domain']['cpu']['realtime'] = True
        if 'hugepages' in overrides:
            hugepages = overrides['hugepages']
            if isinstance(hugepages, int):
                hugepages = f"{hugepages}Mi"
            if 'i' not in hugepages:
                hugepages = f"{hugepages}Mi"
            vm['spec']['template']['spec']['domain']['memory'] = {'hugepages': {'pageSize': hugepages}}
        if pcidevices:
            gpus, host_devices = [], []
            for pcidevice in pcidevices:
                if isinstance(pcidevice, str):
                    entry_name, device_name = os.path.basename(pcidevice), pcidevice
                else:
                    entry_name, device_name = pcidevice['name'], pcidevice['deviceName']
                if 'nvidia.com' in device_name or 'gpu' in entry_name:
                    gpus.append({'name': entry_name, 'deviceName': device_name})
                else:
                    host_devices.append({'name': entry_name, 'deviceName': device_name})
            if gpus:
                vm['spec']['template']['spec']['domain']['gpus'] = gpus
            if host_devices:
                vm['spec']['template']['spec']['domain']['hostDevices'] = host_devices
        uefi = overrides.get('uefi', False)
        secureboot = overrides.get('secureboot', False)
        if uefi or secureboot:
            if secureboot:
                features['smm'] = {'enabled': True}
            vm['spec']['template']['spec']['domain']['firmware'] = {'bootloader': {'efi': {'secure': secureboot}}}
        for flag in cpuflags:
            if isinstance(flag, str):
                feature = flag
                enable = True
            elif isinstance(flag, dict):
                feature = flag.get('name')
                enable = flag.get('enable', True)
                if flag.get('hyperv') is not None and isinstance(flag.get('hyperv'), dict):
                    features['hyperv'] = flag.get('hyperv')
                continue
            if feature is not None and enable is not None:
                features[feature] = {'enabled': enable}
        if features:
            vm['spec']['template']['spec']['domain']['features'] = features
        node_selector = overrides.get('nodeSelector', {})
        if isinstance(node_selector, dict) and node_selector:
            vm['spec']['template']['spec']['nodeSelector'] = node_selector
        interfaces = []
        networks = []
        allnetworks = self.list_networks()
        sriovnetworks = self.list_sriov_networks()
        for index, net in enumerate(nets):
            newif = {'bridge': {}}
            newnet = {}
            if isinstance(net, str):
                netname = net
                newif['name'] = netname
                newnet['name'] = netname
            elif isinstance(net, dict):
                if 'noconf' in net and net['noconf']:
                    vm['spec']['template']['spec']['domain']['devices']['autoattachPodInterface'] = False
                    break
                if 'name' in net:
                    netname = net['name']
                    newif['name'] = netname
                    newnet['name'] = netname
                if 'mac' in net:
                    newif['macAddress'] = net['mac']
                if netname in sriovnetworks or ('sriov' in net and net['sriov']):
                    newif['sriov'] = {}
                    del newif['bridge']
                elif 'macvtap' in net and net['macvtap']:
                    newif['macvtap'] = {}
                    del newif['bridge']
                elif 'masquerade' in net and net['masquerade']:
                    newif['masquerade'] = {}
                    del newif['bridge']
                elif 'slirp' in net and net['slirp']:
                    newif['slirp'] = {}
                    del newif['bridge']
                if 'type' in net:
                    newif['model'] = net['type']
                if 'model' in net:
                    newif['model'] = net['model']
                if index == 0:
                    if 'ip' in nets[index]:
                        vm['metadata']['annotations']['kcli/ip'] = nets[index]['ip']
            if netname != 'default':
                if netname not in allnetworks:
                    return {'result': 'failure', 'reason': f"network {netname} not found"}
                else:
                    newnet['multus'] = {'networkName': netname}
                    guestagent = True
            else:
                newnet['pod'] = {}
            interfaces.append(newif)
            networks.append(newnet)
        if interfaces and networks:
            vm['spec']['template']['spec']['domain']['devices']['interfaces'] = interfaces
            vm['spec']['template']['spec']['networks'] = networks
        pvcs = []
        sizes = []
        for index, disk in enumerate(disks):
            existingpvc = False
            lun = False
            diskname = f'{name}-disk{index}'
            volume_mode = self.volume_mode
            volume_access = self.volume_access
            if disk is None:
                disksize = default_disksize
                diskpool = default_pool
                diskinterface = default_diskinterface
            elif isinstance(disk, int):
                disksize = disk
                diskpool = default_pool
                diskinterface = default_diskinterface
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
                diskpool = default_pool
                diskinterface = default_diskinterface
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskpool = disk.get('pool', default_pool)
                diskinterface = disk.get('interface', default_diskinterface)
                volume_mode = disk.get('volume_mode', volume_mode)
                volume_access = disk.get('volume_access', volume_access)
                lun = disk.get('lun', False)
                if 'name' in disk:
                    existingpvc = True
            myvolume = {'name': diskname}
            if image is not None and index == 0:
                if '/' in image:
                    if container_disk:
                        myvolume['containerDisk'] = {'image': image}
                    else:
                        myvolume['dataVolume'] = {'name': diskname}
                elif harvester:
                    myvolume['dataVolume'] = {'name': diskname}
                else:
                    base_image_pvc = core.read_namespaced_persistent_volume_claim(image, namespace)
                    disksize = base_image_pvc.spec.resources.requests['storage']
                    volume_mode = base_image_pvc.spec.volume_mode
                    myvolume['dataVolume'] = {'name': diskname}
            if index > 0 or image is None:
                myvolume['persistentVolumeClaim'] = {'claimName': diskname}
            newdisk = {'disk': {}, 'name': diskname}
            if lun:
                newdisk['disk']['lun'] = {}
            else:
                newdisk['disk']['bus'] = diskinterface
            if index == 0:
                newdisk['bootOrder'] = 1
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec']['template']['spec']['volumes'].append(myvolume)
            if index == 0 and image is not None and '/' in image and container_disk:
                continue
            if existingpvc:
                continue
            diskpool = self.check_pool(pool)
            pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': diskpool,
                                                             'volumeMode': volume_mode,
                                                             'accessModes': [volume_access],
                                                             'resources': {'requests': {'storage': f'{disksize}Gi'}}},
                   'apiVersion': 'v1', 'metadata': {'name': diskname}}
            if image is not None and index == 0 and image not in CONTAINERDISKS and not harvester:
                annotation = f"{namespace}/{image}"
                pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': annotation}
                pvc['metadata']['labels'] = {'app': 'Host-Assisted-Cloning'}
            pvcs.append(pvc)
            sizes.append(disksize)
        if iso is not None:
            if iso not in self.volumes(iso=True):
                return {'result': 'failure', 'reason': f"you don't have iso {iso}"}
            diskname = f'{name}-iso'
            newdisk = {'bootOrder': 2, 'cdrom': {'readOnly': False, 'bus': 'sata'}, 'name': diskname}
            good_iso = iso.replace('_', '-').replace('.', '-').lower()
            myvolume = {'name': diskname, 'persistentVolumeClaim': {'claimName': good_iso}}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec']['template']['spec']['volumes'].append(myvolume)
            cloudinit = False
        if guestagent:
            gcmds = []
            if image is not None and common.need_guest_agent(image):
                gcmds.append('yum -y install qemu-guest-agent')
                gcmds.append('systemctl enable qemu-guest-agent')
                gcmds.append('systemctl restart qemu-guest-agent')
            elif image.lower().startswith('debian') or 'debian-' in image.lower():
                gcmds.append('apt-get -f install qemu-guest-agent')
            elif [x for x in UBUNTUS if x in image.lower()]:
                gcmds.append('apt-get update')
                gcmds.append('apt-get -f install qemu-guest-agent')
            idx = 1
            if image is not None and image.startswith('rhel'):
                subindex = [i for i, value in enumerate(cmds) if value.startswith('subscription-manager')]
                if subindex:
                    idx = subindex.pop() + 1
            cmds = cmds[:idx] + gcmds + cmds[idx:]
        if cloudinit:
            netdata = None
            if image is not None and common.needs_ignition(image):
                cloudinitsource = "cloudInitConfigDrive"
                version = common.ignition_version(image)
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, files=files, enableroot=enableroot, overrides=overrides,
                                           version=version, plan=plan, compact=True, image=image,
                                           vmuser=vmuser)
            else:
                cloudinitsource = "cloudInitNoCloud"
                userdata, metadata, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                               gateway=gateway, dns=dns, domain=domain,
                                                               files=files, enableroot=enableroot,
                                                               overrides=overrides, storemetadata=storemetadata,
                                                               image=image, machine=machine, vmuser=vmuser)
                if 'static' in metadata:
                    warning("Legacy network not supported in kubevirt. Ignoring")
                    netdata = None
            embed_userdata = overrides.get('embed_userdata', self.embed_userdata)
            cloudinitdisk = {'cdrom': {'bus': 'sata'}, 'name': 'cloudinitdisk'}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(cloudinitdisk)
            cloudinitvolume = {'name': 'cloudinitdisk'}
            if embed_userdata:
                cloudinitvolume[cloudinitsource] = {'userData': userdata}
                if netdata is not None and netdata != '':
                    cloudinitvolume[cloudinitsource]['networkData'] = netdata
            else:
                userdatasecretname = f"{name}-userdata-secret"
                self.create_secret(userdatasecretname, namespace, userdata, field='userdata')
                cloudinitvolume[cloudinitsource] = {'secretRef': {'name': userdatasecretname}}
                owners.append(userdatasecretname)
                if netdata is not None and netdata != '':
                    netdatasecretname = f"{name}-netdata-secret"
                    cloudinitvolume[cloudinitsource]['networkDataSecretRef'] = {'name': netdatasecretname}
                    self.create_secret(netdatasecretname, namespace, netdata, field='networkdata')
                    owners.append(netdatasecretname)
            vm['spec']['template']['spec']['volumes'].append(cloudinitvolume)
        if self.debug:
            common.pretty_print(vm)
        for index, pvc in enumerate(pvcs):
            pvcname = pvc['metadata']['name']
            if not pvcname.endswith('iso'):
                owners.append(pvcname)
            try:
                core.read_namespaced_persistent_volume_claim(pvcname, namespace)
                pprint(f"Using existing pvc {pvcname}")
                continue
            except:
                pass
            pvcsize = pvc['spec']['resources']['requests']['storage'].replace('Gi', '')
            pvc_volume_mode = pvc['spec']['volumeMode']
            pvc_access_mode = pvc['spec']['accessModes']
            if index == 0 and image is not None:
                owners.pop()
                dvt = {'metadata': {'name': pvcname, 'annotations': {'sidecar.istio.io/inject': 'false'}},
                       'spec': {'pvc': {'storageClassName': diskpool,
                                        'volumeMode': pvc_volume_mode,
                                        'accessModes': pvc_access_mode,
                                        'resources':
                                        {'requests': {'storage': f'{pvcsize}Gi'}}},
                                'source': {'pvc': {'name': image, 'namespace': self.namespace}}},
                       'status': {}}
                if harvester:
                    dvt['kind'] = 'DataVolume'
                    dvt['apiVersion'] = f"{CDIDOMAIN}/{CDIVERSION}"
                    harvester_image = harvester_images[image]
                    dvt['metadata']['annotations']['harvesterhci.io/imageId'] = f"{namespace}/{harvester_image}"
                    dvt['spec']['pvc']['storageClassName'] = f"longhorn-{harvester_image}"
                    dvt['spec']['source'] = {'blank': {}}
                    dvt['spec']['pvc']['volumeMode'] = 'Block'
                elif not container_disk and '/' in image and ':' in image:
                    dvt['kind'] = 'DataVolume'
                    dvt['apiVersion'] = f"{CDIDOMAIN}/{CDIVERSION}"
                    del dvt['spec']['pvc']
                    dvt['spec']['source'] = {'registry': {'pullMethod': 'node', 'url': f"docker://{image}"}}
                    dvt['spec']['storage'] = {'resources': {'requests': {'storage': f'{pvcsize}Gi'}}}
                vm['spec']['dataVolumeTemplates'] = [dvt]
                continue
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(pvcname, namespace, first_consumer=self.first_consumer)
            if not bound:
                error(f'timeout waiting for pvc {pvcname} to get bound')
                return {'result': 'failure', 'reason': f'timeout waiting for pvc {pvcname} to get bound'}
        if 'affinity' in overrides and isinstance(overrides['affinity'], dict):
            vm['spec']['template']['spec']['affinity'] = overrides['affinity']
        if 'checkport' in overrides and isinstance(overrides['checkport'], int):
            readinessprobe = {'initialDelaySeconds': 180, 'periodSeconds': 2, 'successThreshold': 3,
                              'failureThreshold': 2}
            checkport = overrides['checkport']
            checkpath = overrides.get('checkpath')
            checkscheme = overrides.get('checkscheme', 'HTTP').upper()
            checktype = 'httpGet' if checkpath is not None else 'tcpSocket'
            readinessprobe[checktype] = {'port': checkport}
            if checkpath is not None:
                readinessprobe[checktype]['path'] = checkpath
                readinessprobe[checktype]['scheme'] = checkscheme
            vm['spec']['template']['spec']['readinessProbe'] = readinessprobe
        vminfo = crds.create_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', vm)
        uid = vminfo.get("metadata")['uid']
        api_version = f"{DOMAIN}/{VERSION}"
        reference = {'apiVersion': api_version, 'kind': 'VirtualMachine', 'name': name, 'uid': uid}
        if reservedns and domain is not None:
            newdomain = domain.replace('.', '-')
            try:
                core.read_namespaced_service(newdomain, namespace)
            except:
                if newdomain != domain:
                    warning(f"converting dns domain {domain} to {newdomain}")
                dnsspec = {'apiVersion': 'v1', 'kind': 'Service', 'metadata': {'name': newdomain,
                                                                               'ownerReferences': [reference]},
                           'spec': {'selector': {'subdomain': newdomain}, 'clusterIP': 'None',
                                    'ports': [{'name': 'foo', 'port': 1234, 'targetPort': 1234}]}}
                core.create_namespaced_service(namespace, dnsspec)
        if not tunnel and self.access_mode != 'External':
            try:
                core.read_namespaced_service(f'{name}-ssh', namespace)
            except:
                selector = {'kubevirt.io/provider': 'kcli', 'kubevirt.io/domain': name}
                self.create_service(f'{name}-ssh', namespace, selector, _type=self.access_mode, ports=[{'port': 22}],
                                    reference=reference)
        if name.endswith('-sno') and metadata.get('kubetype', '') == 'openshift':
            selector = {'kubevirt.io/provider': 'kcli', 'kubevirt.io/domain': name}
            self.create_service(f'{name}-api', namespace, selector, _type=self.access_mode, ports=[{'port': 6443}],
                                reference=reference)
        self.update_reference(owners, namespace, reference)
        return {'result': 'success'}

    def start(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        vm['spec']['running'] = True
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return {'result': 'success'}

    def stop(self, name, soft=False):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        vm["spec"]['running'] = False
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return {'result': 'success'}

    def create_snapshot(self, name, base):
        print("not implemented")
        return {'result': 'success'}

    def delete_snapshot(self, name, base):
        print("not implemented")
        return {'result': 'success'}

    def list_snapshots(self, base):
        print("not implemented")
        return []

    def revert_snapshot(self, name, base):
        print("not implemented")
        return {'result': 'success'}

    def restart(self, name):
        return self.start(name)

    def info_host(self):
        data = {}
        if self.token is not None:
            data['connection'] = f"https://{self.host}:{self.port}"
        else:
            data['context'] = self.contextname
        data['namespace'] = self.namespace
        return data

    def status(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except Exception:
            return None
        allvms = crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstance')["items"]
        vms = [vm for vm in allvms if 'labels' in vm.get("metadata") and 'kubevirt-vm' in
               vm["metadata"]['labels'] and vm["metadata"]['labels']['kubevirt-vm'] == name]
        if vms:
            return 'up'
        return 'down'

    def list(self):
        crds = self.crds
        namespace = self.namespace
        vms = []
        for vm in crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines')["items"]:
            metadata = vm.get("metadata")
            name = metadata["name"]
            try:
                vms.append(self.info(name, vm=vm))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        if os.path.exists("/i_am_a_container"):
            error("This functionality is not supported in container mode")
            return
        kubectl = common.get_binary('kubectl', KUBECTL_LINUX, KUBECTL_MACOSX, compressed=True)
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        uid = vm.get("metadata")['uid']
        for pod in core.list_namespaced_pod(namespace).items:
            if pod.metadata.name.startswith(f"virt-launcher-{name}-") and\
                    pod.metadata.labels['kubevirt.io/domain'] == name:
                podname = pod.metadata.name
                localport = common.get_free_port()
                break
        nccmd = f'KUBECONFIG={self.kubeconfig_file} ' if self.kubeconfig_file is not None else ''
        nccmd += f"{kubectl} exec -n {namespace} {podname} -- /bin/sh -c "
        nccmd += f"'nc -l {localport} --sh-exec \"nc -U /var/run/kubevirt-private/{uid}/virt-vnc\"'"
        nccmd += " &"
        os.system(nccmd)
        forwardcmd = f'KUBECONFIG={self.kubeconfig_file} ' if self.kubeconfig_file is not None else ''
        forwardcmd += f"{kubectl} port-forward {podname} {localport}:{localport} &"
        os.system(forwardcmd)
        time.sleep(5)
        if web:
            return f"vnc://127.0.0.1:{localport}"
        url = f"vnc://127.0.0.1:{localport}"
        if os.path.exists('/Applications'):
            if os.path.exists('/Applications/VNC Viewer.app'):
                consolecommand = f"open -a 'VNC Viewer' --args {url.replace('vnc://', '')} &"
            else:
                consolecommand = f"open -a 'Screen Sharing' {url} &"
        else:
            consolecommand = f"remote-viewer {url} &"
        if self.debug:
            msg = f"Run the following command:\n{consolecommand}" if not self.debug else consolecommand
            pprint(msg)
        else:
            os.system(consolecommand)
        return

    def serialconsole(self, name, web=False):
        kubectl = common.get_binary('kubectl', KUBECTL_LINUX, KUBECTL_MACOSX, compressed=True)
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        uid = vm.get("metadata")['uid']
        for pod in core.list_namespaced_pod(namespace).items:
            if pod.metadata.name.startswith(f"virt-launcher-{name}-") and\
                    pod.metadata.labels['kubevirt.io/domain'] == name:
                podname = pod.metadata.name
                break
        nccmd = "%s exec -n %s -it %s -- /bin/sh -c 'nc -U /var/run/kubevirt-private/%s/virt-serial0'" % (kubectl,
                                                                                                          namespace,
                                                                                                          podname,
                                                                                                          uid)
        if web:
            return nccmd
        os.system(nccmd)
        return

    def dnsinfo(self, name):
        crds = self.crds
        namespace = self.namespace
        crds = self.crds
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return None, None
        if self.debug:
            common.pretty_print(vm)
        dnsclient, domain = None, None
        metadata = vm.get("metadata")
        annotations = metadata.get("annotations")
        if annotations is not None:
            if 'kcli/dnsclient' in annotations:
                dnsclient = annotations['kcli/dnsclient']
            if 'kcli/domain' in annotations:
                domain = annotations['kcli/domain']
        return dnsclient, domain

    def info(self, name, vm=None, debug=False):
        yamlinfo = {}
        core = self.core
        crds = self.crds
        namespace = self.namespace
        harvester = self.harvester
        crds = self.crds
        if vm is None:
            listinfo = False
            try:
                vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
            except:
                error(f"VM {name} not found")
                return {}
        else:
            listinfo = True
        metadata = vm.get("metadata")
        spec = vm.get("spec")
        running = spec.get("running", True)
        annotations = metadata.get("annotations")
        spectemplate = vm['spec'].get('template')
        volumes = spectemplate['spec']['volumes']
        name = metadata["name"]
        uid = metadata["uid"]
        creationdate = metadata["creationTimestamp"]
        profile, plan, image = 'N/A', 'N/A', 'N/A'
        kube, kubetype = None, None
        ip = None
        image = 'N/A'
        if harvester and 'dataVolumeTemplates' in spec and spec['dataVolumeTemplates'] and\
                'harvesterhci.io/imageId' in spec['dataVolumeTemplates'][0]['metadata']['annotations']:
            image = spec['dataVolumeTemplates'][0]['metadata']['annotations']['harvesterhci.io/imageId'].split('/')[1]
        if annotations is not None:
            profile = annotations['kcli/profile'] if 'kcli/profile' in annotations else 'N/A'
            plan = annotations['kcli/plan'] if 'kcli/plan' in annotations else 'N/A'
            ip = annotations['kcli/ip'] if 'kcli/ip' in annotations else None
            kube = annotations['kcli/kube'] if 'kcli/kube' in annotations else None
            kubetype = annotations['kcli/kubetype'] if 'kcli/kubetype' in annotations else None
            if 'kcli/image' in annotations:
                image = annotations['kcli/image']
        host = None
        state = 'down'
        foundmacs = {}
        ips = []
        if running:
            try:
                runvm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
                status = runvm.get('status')
                if status:
                    state = status.get('phase').replace('Running', 'up')
                    host = status['nodeName'] if 'nodeName' in status else None
                    if 'interfaces' in status:
                        interfaces = runvm['status']['interfaces']
                        for index, interface in enumerate(interfaces):
                            if 'ipAddress' in interface:
                                ips.append(interface['ipAddress'].split('/')[0])
                            if 'mac' in interface:
                                foundmacs[index] = interface['mac']

            except:
                pass
        else:
            state = 'down'
        if ips:
            if len(ips) > 1:
                yamlinfo['ips'] = ips
            ip4s = [i for i in ips if ':' not in i]
            ip6s = [i for i in ips if i not in ip4s]
            ip = ip4s[0] if ip4s else ip6s[0]
        yamlinfo = {'name': name, 'nets': [], 'disks': [], 'status': state, 'creationdate': creationdate, 'host': host,
                    'namespace': namespace, 'id': uid}
        if 'cpu' in spectemplate['spec']['domain']:
            numcpus = spectemplate['spec']['domain']['cpu']['cores']
            yamlinfo['cpus'] = numcpus
        memory = None
        if 'resources' in spectemplate['spec']['domain'] and 'requests' in spectemplate['spec']['domain']['resources']:
            memory = spectemplate['spec']['domain']['resources']['requests']['memory'].replace('M', '').replace('G', '')
            memory = memory.replace('Mi', 'Mi').replace('Gi', '').replace('i', '')
            memory = int(memory)
            if harvester:
                memory = memory * 1024
        elif 'memory' in spectemplate['spec']['domain']:
            memory = spectemplate['spec']['domain']['memory']['guest']
            if memory.endswith('Gi'):
                memory = int(memory.replace('Gi', '')) * 1024
            else:
                memory = int(memory.replace('Mi', ''))
        if memory is not None:
            yamlinfo['memory'] = memory
        if 'instancetype' in spec and spec['instancetype']['kind'] == 'virtualmachineclusterinstancetype':
            flavor = spec['instancetype']['name']
            yamlinfo['flavor'] = flavor
            yamlinfo['numcpus'], yamlinfo['memory'] = [f for f in self.list_flavors() if f[0] == flavor][0][1:]
        if image != 'N/A':
            yamlinfo['image'] = image
            yamlinfo['user'] = common.get_user(image)
        if ip is not None:
            yamlinfo['ip'] = ip
        if plan is not None:
            yamlinfo['plan'] = plan
        if profile is not None:
            yamlinfo['profile'] = profile
        if kube is not None and kubetype is not None:
            yamlinfo['kube'] = kube
            yamlinfo['kubetype'] = kubetype
        if listinfo:
            return yamlinfo
        plaindisks = spectemplate['spec']['domain']['devices']['disks']
        disks = []
        for d in plaindisks:
            bus = 'N/A'
            if 'disk' in d:
                bus = d['disk'].get('bus', 'N/A')
            volumename = d['name']
            volumeinfo = [volume for volume in volumes if volume['name'] == volumename][0]
            size = '0'
            if 'persistentVolumeClaim' in volumeinfo or 'dataVolume' in volumeinfo:
                if 'persistentVolumeClaim' in volumeinfo:
                    pvcname = volumeinfo['persistentVolumeClaim']['claimName']
                else:
                    pvcname = volumeinfo['dataVolume']['name']
                if pvcname.endswith('iso'):
                    yamlinfo['iso'] = pvcname.replace('-iso', '.iso')
                    continue
                _type = 'pvc'
                try:
                    pvc = core.read_namespaced_persistent_volume_claim(pvcname, namespace)
                    size = pvc.status.capacity['storage'].replace('Gi', '')
                except:
                    warning(f"pvc {pvcname} not found. That can't be good")
                    pvc = 'N/A'
                    size = "0"
                if 'Mi' in size:
                    size = int(size.replace('Mi', '')) / 1024
                else:
                    size = int(size)
            elif 'cloudInitNoCloud' in volumeinfo or 'cloudInitConfigDrive' in volumeinfo:
                continue
            elif 'containerDisk' in volumeinfo:
                _type = 'containerdisk'
            else:
                _type = 'other'
            disk = {'device': d['name'], 'size': size, 'format': bus, 'type': _type, 'path': volumename}
            disks.append(disk)
        yamlinfo['disks'] = disks
        interfaces = vm['spec']['template']['spec']['domain']['devices'].get('interfaces', [])
        networks = vm['spec']['template']['spec'].get('networks', [])
        for index, interface in enumerate(interfaces):
            device = f'eth{index}'
            net = networks[index]
            mac = interface['macAddress'] = interface['mac'] if 'mac' in interface else foundmacs.get(index, 'N/A')
            if 'multus' in net:
                network = net['multus']['networkName']
                network_type = 'multus'
            else:
                network = 'default'
                network_type = 'pod'
            yamlinfo['nets'].append({'device': device, 'mac': mac, 'net': network, 'type': network_type})
        if self.access_mode == 'NodePort':
            nodeport = self.ssh_node_port(name, namespace)
            if nodeport is not None:
                yamlinfo['nodeport'] = nodeport
        elif self.access_mode == 'LoadBalancer':
            loadbalancerip = self.ssh_loadbalancer_ip(name, namespace)
            if loadbalancerip is not None:
                yamlinfo['loadbalancerip'] = loadbalancerip
        if image == 'N/A' and 'kubetype' in yamlinfo and yamlinfo['kubetype'] == 'openshift':
            yamlinfo['user'] = 'core'
            if name.endswith('-sno'):
                api_port = self.api_node_port(name, namespace)
                if api_port is not None:
                    yamlinfo['apiport'] = api_port
        if debug:
            yamlinfo['debug'] = common.pretty_print(vm)
        return yamlinfo

    def ip(self, name):
        crds = self.crds
        namespace = self.namespace
        ip = None
        try:
            vmi = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
            try:
                vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
                metadata = vm.get("metadata")
                annotations = metadata.get("annotations")
                if annotations is not None and 'kcli/ip' in annotations:
                    return vm['metadata']['annotations']['kcli/ip']
            except:
                pass
            status = vmi['status']
            if 'interfaces' in status:
                interfaces = vmi['status']['interfaces']
                for interface in interfaces:
                    if 'ipAddress' in interface and ip_address(interface['ipAddress'].split('/')[0]).version == 4:
                        ip = interface['ipAddress'].split('/')[0]
                        break
        except Exception:
            error(f"VM {name} not found")
            sys.exit(1)
        return ip

    def volumes(self, iso=False):
        core = self.core
        namespace = self.namespace
        crds = self.crds
        isos = []
        allimages = []
        allimages = []
        harvester = self.harvester
        if harvester:
            virtualimages = crds.list_namespaced_custom_object(HDOMAIN, HVERSION, namespace,
                                                               'virtualmachineimages')["items"]
            allimages = [os.path.basename(image['spec']['url']) for image in virtualimages]
        else:
            pvc = core.list_namespaced_persistent_volume_claim(namespace)
            allimages = [p.metadata.name for p in pvc.items if p.metadata.annotations is not None and
                         'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations and
                         'cdi.kubevirt.io/storage.condition.running.reason' in p.metadata.annotations and
                         p.metadata.annotations['cdi.kubevirt.io/storage.condition.running.reason'] == 'Completed']
        if iso:
            isos = [i for i in allimages if i.endswith('iso')]
            return isos
        else:
            images = [common.filter_compression_extension(i) for i in allimages if not i.endswith('iso')]
            return sorted(images + CONTAINERDISKS)

    def delete(self, name, snapshots=False):
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        crds.delete_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        dvvolumes = [v['dataVolume']['name'] for v in vm['spec']['template']['spec']['volumes'] if
                     'dataVolume' in v]
        if dvvolumes:
            timeout = 0
            while True:
                dvpvcs = [pvc for pvc in core.list_namespaced_persistent_volume_claim(namespace).items
                          if pvc.metadata.name in dvvolumes]
                if not dvpvcs or timeout > 60:
                    break
                else:
                    pprint(f"Waiting 5s for pvcs associated to datavolumes of {name} to disappear")
                    time.sleep(5)
                    timeout += 5
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if append and f"kcli/{metatype}" in vm["metadata"]["annotations"]:
            oldvalue = vm["metadata"]["annotations"][f"kcli/{metatype}"]
            metavalue = f"{oldvalue},{metavalue}"
        vm["metadata"]["annotations"][f"kcli/{metatype}"] = metavalue
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def update_memory(self, name, memory):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['resources']['requests']['memory'] = f"{memory}M"
        vm['spec'][t]['spec']['domain']['resources']['limits']['memory'] = f"{memory}M"
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        warning("Change will only appear next full lifeclyclereboot")
        return

    def update_cpus(self, name, numcpus):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['cpu']['cores'] = int(numcpus)
        warning("Change will only appear next full lifeclyclereboot")
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if iso is not None:
            if iso not in self.volumes(iso=True):
                return {'result': 'failure', 'reason': f"you don't have iso {iso}"}
            good_iso = iso.replace('_', '-').replace('.', '-').lower()
        found = False
        diskname = f'{name}-iso'
        for diskindex, disk in enumerate(vm['spec']['template']['spec']['domain']['devices']['disks']):
            currentdiskname = vm['spec']['template']['spec']['domain']['devices']['disks'][diskindex]['name']
            if currentdiskname == diskname:
                found = True
                if iso is None:
                    del vm['spec']['template']['spec']['domain']['devices']['disks'][diskindex]
        for volindex, vol in enumerate(vm['spec']['template']['spec']['volumes']):
            if vol['name'] == diskname:
                if iso is None:
                    del vm['spec']['template']['spec']['volumes'][volindex]
                elif vol['persistentVolumeClaim']['claimName'] != good_iso:
                    vm['spec']['template']['spec']['volumes'][volindex]['persistentVolumeClaim']['claimName'] = good_iso
                else:
                    return
        if iso is not None and not found:
            newdisk = {'bootOrder': 2, 'cdrom': {'readOnly': False, 'bus': 'sata'}, 'name': diskname}
            myvolume = {'name': diskname, 'persistentVolumeClaim': {'claimName': good_iso}}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec']['template']['spec']['volumes'].append(myvolume)
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)

    def update_flavor(self, name, flavor):
        print("Not implemented")
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None, overrides={}):
        core = self.core
        namespace = self.namespace
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        images = {p.metadata.annotations['kcli/image']: p.metadata.name for p in pvc.items
                  if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations}
        try:
            pvc = core.read_namespaced_persistent_volume(name, namespace)
            error(f"Disk {name} already there")
            return 1
        except:
            pass
        volume_mode = overrides.get('volume_mode', self.volume_mode)
        volume_access = overrides.get('volume_access', self.volume_access)
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'volumeMode': volume_mode,
                                                         'accessModes': [volume_access],
                                                         'resources': {'requests': {'storage': f'{size}Gi'}}},
               'apiVersion': 'v1', 'metadata': {'name': name}}
        if image is not None:
            pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': images[image]}
        core.create_namespaced_persistent_volume_claim(namespace, pvc)
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}, diskname=None):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        currentdisks = [disk for disk in vm['spec'][t]['spec']['domain']['devices']['disks']
                        if disk['name'] != 'cloudinitdisk']
        index = len(currentdisks)
        diskname = f'{name}-disk{index}'
        diskpool = self.check_pool(pool)
        diskpool, volume_mode, volume_access = self.get_default_storage(diskpool, self.volume_mode, self.volume_access)
        myvolume = {'name': diskname, 'persistentVolumeClaim': {'claimName': diskname}}
        if self.disk_hotplug:
            pprint(f"Hotplugging disk {diskname}")
            dv = {'kind': 'DataVolume', 'apiVersion': f"{CDIDOMAIN}/{CDIVERSION}",
                  'metadata': {'name': diskname, 'annotations': {'sidecar.istio.io/inject': 'false'}},
                  'spec': {'pvc': {'volumeMode': volume_mode,
                                   'accessModes': [volume_access],
                                   'resources': {'requests': {'storage': f'{size}Gi'}}},
                           'source': {'blank': {}}}, 'status': {}}
            crds.create_namespaced_custom_object(CDIDOMAIN, CDIVERSION, namespace, 'datavolumes', dv)
            subresource = f"/apis/subresources.kubevirt.io/v1alpha3/namespaces/{namespace}"
            subresource += f"/virtualmachines/{name}/addvolume"
            body = {"name": diskname, "volumesource": myvolume, "disk": {"disk": {"bus": "scsi"}}}
            if 'serial' in overrides:
                body['disk']['serial'] = str(overrides['serial'])
            self.core.api_client.call_api(subresource, 'PUT', body=body)
        else:
            disk_overrides = overrides.copy()
            disk_overrides['volume_mode'] = volume_mode
            disk_overrides['volume_access'] = volume_access
            self.create_disk(diskname, size=size, pool=diskpool, thin=thin, image=image, overrides=disk_overrides)
            bound = self.pvc_bound(diskname, namespace, first_consumer=self.first_consumer)
            if not bound:
                return {'result': 'failure', 'reason': f'timeout waiting for pvc {diskname} to get bound'}
            bus = overrides.get('interface', 'virtio')
            newdisk = {'disk': {'bus': bus}, 'name': diskname}
            vm['spec'][t]['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec'][t]['spec']['volumes'].append(myvolume)
            crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        crds = self.crds
        core = self.core
        namespace = self.namespace
        if name is None:
            volname = diskname
        else:
            try:
                vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
            except:
                error(f"VM {name} not found")
                return {'result': 'failure', 'reason': f"VM {name} not found"}
            t = 'Template' if 'Template' in vm['spec'] else 'template'
            diskindex = [i for i, disk in enumerate(vm['spec'][t]['spec']['domain']['devices']['disks'])
                         if disk['name'] == diskname]
            if not diskindex:
                error(f"Disk {diskname} not found")
                return {'result': 'failure', 'reason': f"disk {diskname} not found in VM"}
            diskindex = diskindex[0]
            if self.disk_hotplug:
                pprint(f"Hotunplugging disk {diskname}")
                myvolume = {'name': diskname, 'persistentVolumeClaim': {'claimName': diskname}}
                subresource = f"/apis/subresources.kubevirt.io/v1alpha3/namespaces/{namespace}"
                subresource += f"/virtualmachines/{name}/removevolume"
                bus = 'scsi'
                body = {"name": diskname, "volumesource": myvolume, "disk": {"disk": {"bus": bus}}}
                self.core.api_client.call_api(subresource, 'PUT', body=body)
                try:
                    crds.delete_namespaced_custom_object(CDIDOMAIN, CDIVERSION, namespace, 'datavolumes', diskname)
                except:
                    error(f"Disk {diskname} not found")
                    return 1
                return
            volname = vm['spec'][t]['spec']['domain']['devices']['disks'][diskindex]['name']
            volindex = [i for i, vol in enumerate(vm['spec'][t]['spec']['volumes']) if vol['name'] == volname]
            if volindex:
                volindex = volindex[0]
                del vm['spec'][t]['spec']['volumes'][volindex]
            del vm['spec'][t]['spec']['domain']['devices']['disks'][diskindex]
            crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        try:
            core.delete_namespaced_persistent_volume_claim(volname, namespace)
        except:
            error(f"Disk {volname} not found")
            return 1
        return

    def list_disks(self):
        disks = {}
        namespace = self.namespace
        core = self.core
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        for p in pvc.items:
            metadata = p.metadata
            annotations = p.metadata.annotations
            if annotations is not None and 'kcli/image' in annotations:
                continue
            else:
                name = metadata.name
                storageclass = p.spec.storage_class_name
                pv = p.spec.volume_name
                disks[name] = {'pool': storageclass, 'path': pv}
        return disks

    def add_nic(self, name, network, model='virtio'):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        newif = {'bridge': {}, 'name': network}
        newnet = {'name': network}
        if network != 'default':
            if network not in self.list_networks():
                error(f"network {network} not found")
                return {'result': 'failure', 'reason': f"network {network} not found"}
            elif [entry for entry in vm['spec']['template']['spec']['networks'] if entry['name'] == network]:
                error(f"vm already connected to network {network}")
                return {'result': 'failure', 'reason': f"vm already connected to network {network}"}
            newnet['multus'] = {'networkName': network}
        elif [entry for entry in vm['spec']['template']['spec']['networks'] if 'pod' in entry]:
            error("only one nic is allowed to be connected to default pod network")
            return {'result': 'failure', 'reason': "only one nic is allowed to be connected to default pod network"}
        else:
            newnet['pod'] = {}
        vm['spec']['template']['spec']['domain']['devices']['interfaces'].append(newif)
        vm['spec']['template']['spec']['networks'].append(newnet)
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def delete_nic(self, name, interface):
        print("not implemented")
        return

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")
        return

    def delete_image(self, image, pool=None):
        core = self.core
        crds = self.crds
        harvester = self.harvester
        if harvester:
            virtualimages = crds.list_namespaced_custom_object(HDOMAIN, HVERSION, self.namespace,
                                                               'virtualmachineimages')["items"]
            images = [img['metadata']['name'] for img in virtualimages if
                      os.path.basename(img['spec']['url']) == image]
            if images:
                crds.delete_namespaced_custom_object(HDOMAIN, HVERSION, self.namespace, 'virtualmachineimages',
                                                     images[0])
                return {'result': 'success'}
        else:
            pvc = core.list_namespaced_persistent_volume_claim(self.namespace)
            images = [p.metadata.name for p in pvc.items if p.metadata.annotations is not None and
                      'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations and
                      self.get_image_name(p.metadata.annotations['cdi.kubevirt.io/storage.import.endpoint']) ==
                      image]
            if images:
                core.delete_namespaced_persistent_volume_claim(images[0], self.namespace)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': f'image {image} not found'}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
        if size is None:
            size = _base_image_size(url)
            warning(f"Setting size of image to {size}G. This will be the size of primary disks using this")
        core = self.core
        crds = self.crds
        pool = self.check_pool(pool)
        namespace = self.namespace
        harvester = self.harvester
        shortimage = os.path.basename(url).split('?')[0]
        uncompressed = shortimage.replace('.gz', '').replace('.xz', '').replace('.bz2', '').replace('.zst', '')
        if name is not None:
            volname = name.replace('_', '-').replace('.', '-').lower()
        elif url in IMAGES.values():
            volname = [key for key in IMAGES if IMAGES[key] == url][0]
        else:
            volname = os.path.basename(url).replace('_', '-').replace('.', '-').lower()
        if harvester:
            virtualmachineimage = {'kind': 'VirtualMachineImage', 'spec': {'url': url, "displayName": uncompressed},
                                   'apiVersion': f'{HDOMAIN}/{HVERSION}', 'metadata': {'name': volname}}
            crds.create_namespaced_custom_object(HDOMAIN, HVERSION, self.namespace, 'virtualmachineimages',
                                                 virtualmachineimage)
            return {'result': 'success'}
        pool, volume_mode, volume_access = self.get_default_storage(pool, self.volume_mode, self.volume_access)
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'volumeMode': volume_mode,
                                                         'accessModes': [volume_access],
                                                         'resources': {'requests': {'storage': f'{size}Gi'}}},
               'apiVersion': 'v1', 'metadata': {'name': volname, 'annotations': {'kcli/image': uncompressed}}}
        pprint(f"Cloning in namespace {namespace}")
        pvc['metadata']['annotations'] = {'cdi.kubevirt.io/storage.import.endpoint': url}
        try:
            core.read_namespaced_persistent_volume_claim(volname, namespace)
            pprint("Using existing pvc")
        except:
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(volname, namespace, first_consumer=self.first_consumer)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc to get bound'}
        completed = self.import_completed(volname, namespace)
        if not completed:
            error("Issue with cdi import")
            return {'result': 'failure', 'reason': 'timeout waiting for cdi importer pod to complete'}
        return {'result': 'success'}

    def patch_pvc(self, pvc, command, image="quay.io/karmab/curl", files=[]):
        core = self.core
        namespace = self.namespace
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        podname = f'{now}-{pvc}-patch'
        configmap = None
        if files:
            data = {}
            for entry in files:
                _fil = os.path.expanduser(entry)
                _fil_name = os.path.basename(entry)
                if os.path.exists(_fil):
                    data[_fil_name] = open(_fil).read()
                else:
                    warning(f"Skipping {entry} as it's not present")
            configmap = {'kind': 'ConfigMap', 'data': data, 'apiVersion': 'v1', 'metadata': {'name': podname}}
            core.create_namespaced_config_map(namespace, configmap)
        container = {'image': image, 'name': 'patch', 'command': ['/bin/sh', '-c']}
        if self.volume_mode == 'Filesystem':
            container['volumeMounts'] = [{'mountPath': '/storage', 'name': 'storage'}]
            if configmap is not None:
                container['volumeMounts'].append({'mountPath': '/files', 'name': 'files'})
        else:
            container['volumeDevices'] = [{'devicePath': '/dev/storage', 'name': 'storage'}]
            if configmap is not None:
                container['volumeDevices'] = [{'devicePath': '/dev/files', 'name': 'files'}]
        container['args'] = [command]
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never', 'containers': [container],
                                       'volumes': [{'name': 'storage', 'persistentVolumeClaim': {'claimName': pvc}}]},
               'apiVersion': 'v1', 'metadata': {'name': podname}}
        if configmap is not None:
            pod['spec']['volumes'].append({'name': 'files', 'configMap': {'name': podname}})
        core.create_namespaced_pod(namespace, pod)
        completed = self.pod_completed(podname, namespace)
        if not completed:
            error(f"Issue with pod {podname}. Leaving it for debugging purposes")
            return {'result': 'failure', 'reason': f'issue with pod {podname}'}
        else:
            core.delete_namespaced_pod(podname, namespace)
        if configmap is not None:
            core.delete_namespaced_config_map(podname, namespace)
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        crds = self.crds
        namespace = self.namespace
        apiversion = f"{MULTUSDOMAIN}/{MULTUSVERSION}"
        vlanconfig = '"vlan": %s' % overrides['vlan'] if 'vlan' in overrides is not None else ''
        bridge = 'bridge' in overrides and overrides['bridge']
        ovs = 'ovs' in overrides and overrides['ovs']
        ovn = 'ovn' in overrides and overrides['ovn']
        if 'type' in overrides:
            _type = overrides['type']
        elif ovs:
            _type = 'ovs'
        elif ovn:
            _type = 'bridge'
        else:
            pprint("Using ovn overlay for network")
            _type = 'ovn-k8s-cni-overlay'
        config = '{ "cniVersion": "0.3.1", "type": "%s", "bridge": "%s" %s}' % (_type, name, vlanconfig)
        if cidr is not None and dhcp:
            if bridge:
                ipam = '"isDefaultGateway": true, "forceAddress": false, "ipMasq": true, "hairpinMode": true'
                ipam += ', "ipam": { "type": "host-local", "subnet": "%s" }' % cidr
                config = '{ "type": "bridge", "bridge": "%s", %s }' % (name, ipam)
            else:
                nad = overrides.get('nad', f"{namespace}/{name}")
                layer = overrides.get('layer', "layer2" if not nat else "localnet")
                config = f'"name": "{name}", "netAttachDefName": "{nad}", "subnets": "{cidr}", "topology": "{layer}"'
                config = '{ "cniVersion": "0.3.1", "type": "ovn-k8s-cni-overlay", %s }' % config
                if layer == 'localnet' and nat:
                    bridge = overrides.get('bridge', 'br-ex')
                    policy = {'apiVersion': 'nmstate.io/v1', 'kind': 'NodeNetworkConfigurationPolicy',
                              'metadata': {'name': f'{name}-mapping'},
                              'spec': {'nodeSelector': {'node-role.kubernetes.io/worker': ''},
                                       'desiredState': {'ovn': {'bridge-mappings':
                                                                [{'localnet': name,
                                                                  'bridge': bridge, 'state': 'present'}]}}}}
                    try:
                        crds.create_cluster_custom_object('nmstate.io', 'v1', 'nodenetworkconfigurationpolicies',
                                                          policy)
                    except Exception as e:
                        error(f"Hit {e}. You might need to install kubernetes-nmstate-operator")
        nad = {'kind': 'NetworkAttachmentDefinition', 'spec': {'config': config}, 'apiVersion': apiversion,
               'metadata': {'name': name}}
        crds.create_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace, 'network-attachment-definitions',
                                             nad)
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        crds = self.crds
        namespace = self.namespace
        try:
            crds.delete_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace,
                                                 'network-attachment-definitions', name)
        except:
            return {'result': 'failure', 'reason': f"network {name} not found"}
        return {'result': 'success'}

    def list_pools(self):
        storageapi = self.storageapi
        pools = [x.metadata.name for x in storageapi.list_storage_class().items]
        return pools

    def list_networks(self):
        core = self.core
        try:
            for node in core.list_node().items:
                cidr = node.spec.pod_cidr
                break
        except:
            cidr = 'N/A'
        networks = {'default': {'cidr': cidr, 'dhcp': True, 'type': 'bridge', 'mode': 'N/A'}}
        crds = self.crds
        namespace = self.namespace
        try:
            nafs = crds.list_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace,
                                                      'network-attachment-definitions')["items"]
        except:
            nafs = []
        for naf in nafs:
            config = yaml.safe_load(naf['spec']['config'])
            name = naf['metadata']['name']
            _type = config.get('type', 'N/A')
            bridge = config.get('bridge')
            vlan = config.get('vlan', 'N/A')
            ipam_type = 'N/A'
            dhcp = False
            cidr = bridge
            if 'ipam' in config:
                ipam_type = config['ipam'].get('type', 'N/A')
                if ipam_type == 'dhcp':
                    dhcp = True
                    cidr = config['ipam'].get('subnet', bridge)
                elif ipam_type == 'whereabouts':
                    dhcp = True
                    cidr = config['ipam'].get('range', bridge)
            if 'subnets' in config:
                dhcp = True
                cidr = config['subnets']
            networks[name] = {'cidr': cidr, 'dhcp': dhcp, 'type': _type, 'mode': vlan, 'domain': ipam_type}
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        return networkinfo

    def list_subnets(self):
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        print("not implemented")
        return

    def network_ports(self, name):
        print("not implemented")
        return

    def vm_ports(self, name):
        return []

    def get_pool_path(self, pool):
        storageapi = self.storageapi
        storageclass = storageapi.read_storage_class(pool)
        return storageclass.provisioner

    def pvc_bound(self, volname, namespace, first_consumer=False):
        if first_consumer:
            job_name = f"temp-{volname}"
            container = {'name': 'hello', 'image': 'quay.io/karmab/kubectl', 'command': ["echo", "hello"]}
            volume = {'name': volname, 'persistentVolumeClaim': {'claimName': volname}}
            template = {'metadata': {'labels': {"app": "hello"}},
                        'spec': {'containers': [container], 'volumes': [volume], 'restartPolicy': "Never"}}
            spec = {'template': template, 'backoff_limit': 0, 'ttlSecondsAfterFinished': 10}
            job = {'api_version': 'batch/v1', 'kind': 'Job', 'metadata': {'name': job_name}, 'spec': spec}
            self.batch_v1.create_namespaced_job(body=job, namespace=namespace)
            completed = False
            while not completed:
                response = self.batch_v1.read_namespaced_job_status(name=job_name, namespace=namespace)
                if response.status.succeeded is not None or response.status.failed is not None:
                    completed = True
        core = self.core
        pvctimeout = 120
        pvcruntime = 0
        pvcstatus = ''
        while pvcstatus != 'Bound':
            if pvcruntime >= pvctimeout:
                return False
            pvc = core.read_namespaced_persistent_volume_claim(volname, namespace)
            pvcstatus = pvc.status.phase
            time.sleep(2)
            pprint(f"Waiting for pvc {volname} to get bound...")
            pvcruntime += 2
        return True

    def import_completed(self, volname, namespace):
        core = self.core
        pvctimeout = 1200
        pvcruntime = 0
        phase = ''
        while phase != 'Succeeded':
            if pvcruntime >= pvctimeout:
                return False
            pvc = core.read_namespaced_persistent_volume_claim(volname, namespace)
            # pod = pvc.metadata.annotations['cdi.kubevirt.io/storage.import.importPodName']
            if 'cdi.kubevirt.io/storage.pod.phase' not in pvc.metadata.annotations:
                phase = 'Pending'
            else:
                phase = pvc.metadata.annotations['cdi.kubevirt.io/storage.pod.phase']
            time.sleep(5)
            pprint("Waiting for import to complete...")
            pvcruntime += 5
        return True

    def pod_completed(self, podname, namespace):
        core = self.core
        podtimeout = 1200
        podruntime = 0
        podstatus = ''
        while podstatus != 'Succeeded':
            if podruntime >= podtimeout or podstatus == 'Error' or podstatus == 'Failed':
                return False
            pod = core.read_namespaced_pod(podname, namespace)
            podstatus = pod.status.phase
            time.sleep(5)
            pprint(f"Waiting for pod {podname} to complete...")
            podruntime += 5
        return True

    def check_pool(self, pool):
        storageapi = self.storageapi
        storageclasses = storageapi.list_storage_class().items
        if storageclasses:
            storageclasses = [s.metadata.name for s in storageclasses]
            if pool in storageclasses:
                return pool
        return None

    def list_flavors(self):
        crds = self.crds
        try:
            flavors = crds.list_cluster_custom_object(FLAVORDOMAIN, FLAVORVERSION,
                                                      'virtualmachineclusterinstancetypes')["items"]
        except:
            return []
        return [[f['metadata']['name'], f['spec']['cpu']['guest'], f['spec']['memory']['guest']] for f in flavors]

    def get_image_name(self, name, pvcname=None):
        if name.endswith('.gz'):
            name = name.replace('.gz', '')
        if 'api.openshift.com' in name and pvcname is not None:
            return pvcname.replace('-iso', '.iso')
        if '?' in name:
            return os.path.basename(name).split('?')[0]
        else:
            return os.path.basename(name)

    def ssh_node_port(self, name, namespace):
        try:
            sshservice = self.core.read_namespaced_service(f'{name}-ssh', namespace)
        except:
            return None
        return sshservice.spec.ports[0].node_port

    def api_node_port(self, name, namespace):
        try:
            apiservice = self.core.read_namespaced_service(f'{name}-api', namespace)
        except:
            return None
        return apiservice.spec.ports[0].node_port

    def list_dns(self, domain):
        return []

    def node_host(self, name=None):
        ip = None
        try:
            nodesinfo = self.core.list_node().items
        except:
            return ip
        for node in nodesinfo:
            if name is not None and node.metadata.name != name:
                continue
            addresses = [x.address for x in node.status.addresses if x.type == 'InternalIP']
            if addresses:
                ip = addresses[0]
                break
        return ip

    def create_service(self, name, namespace, selector, _type="NodePort", ports=[], wait=True, reference=None,
                       openshift_hack=False):
        spec = {'kind': 'Service', 'apiVersion': 'v1', 'metadata': {'namespace': namespace, 'name': f'{name}'},
                'spec': {'sessionAffinity': 'None', 'selector': selector}}
        if reference is not None:
            spec['metadata']['ownerReferences'] = [reference]
        spec['spec']['type'] = _type
        if _type in ['NodePort', 'LoadBalancer']:
            spec['spec']['externalTrafficPolicy'] = 'Cluster'
        portspec = []
        portname = True if len(ports) > 1 else False
        for portinfo in ports:
            newportspec = {}
            if isinstance(portinfo, int):
                port = portinfo
                targetport = portinfo + 1000 if openshift_hack else portinfo
                protocol = 'TCP'
            elif isinstance(portinfo, dict):
                port = int(portinfo.get('port'))
                targetport = port + 1000 if openshift_hack else port
                protocol = portinfo.get('protocol', 'TCP')
                targetport = portinfo.get('targetPort', targetport)
                if _type == 'NodePort' and 'nodePort' in portinfo:
                    newportspec['nodePort'] = portinfo['nodePort']
            newportspec['protocol'] = protocol
            newportspec['port'] = port
            newportspec['targetPort'] = targetport
            if portname:
                newportspec['name'] = f"port-{port}"
            portspec.append(newportspec)
        spec['spec']['ports'] = portspec
        self.core.create_namespaced_service(namespace, spec)
        if _type == 'LoadBalancer' and wait:
            ipassigned = False
            timeout = 60
            runtime = 0
            while not ipassigned:
                if runtime >= timeout:
                    error(f"Time out waiting for a loadbalancer ip for service {name}")
                    return
                else:
                    try:
                        api_service = self.core.read_namespaced_service(f'{name}', namespace)
                        return api_service.status.load_balancer.ingress[0].ip
                    except:
                        time.sleep(5)
                        pprint(f"Waiting to get a loadbalancer ip for service {name}...")
                        runtime += 5
        else:
            api_service = self.core.read_namespaced_service(f'{name}', namespace)
            return api_service.spec.cluster_ip

    def get_node_ports(self, service, namespace):
        results = {}
        api_service = self.core.read_namespaced_service(service, namespace)
        for port in api_service.spec.ports:
            results[port.port] = port.node_port
        return results

    def list_services(self, namespace):
        services = []
        for s in self.core.list_namespaced_service(namespace).items:
            services.append(s.metadata.name)
        return services

    def delete_service(self, name, namespace):
        try:
            self.core.delete_namespaced_service(name, namespace)
        except Exception as e:
            error(f"Couldn't delete service {name}. Hit {e}")

    def ssh_loadbalancer_ip(self, name, namespace):
        try:
            api_service = self.core.read_namespaced_service(f'{name}-ssh', namespace)
            return api_service.status.load_balancer.ingress[0].ip
        except:
            return None

    def create_secret(self, name, namespace, data, field='userdata'):
        data = base64.b64encode(data.encode()).decode("UTF-8")
        data = {field: data}
        spec = {'kind': 'Secret', 'apiVersion': 'v1', 'metadata': {'namespace': namespace, 'name': name},
                'data': data, 'type': 'Opaque'}
        self.core.create_namespaced_secret(namespace, spec)

    def delete_secret(self, name, namespace):
        try:
            self.core.delete_namespaced_secret(name, namespace)
        except Exception as e:
            error(f"Couldn't delete service {name}. Hit {e}")

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

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        print("not implemented")
        return

    def get_default_sc(self):
        default_sc = None
        storageapi = self.storageapi
        for sc in storageapi.list_storage_class().items:
            annotations = sc.metadata.annotations
            if annotations is not None and DEFAULT_SC in annotations and annotations[DEFAULT_SC] == 'true':
                default_sc = sc.metadata.name
        return default_sc

    def get_sc_details(self, name):
        volume_mode, volume_access = None, None
        crds = self.crds
        storageprofiles = crds.list_cluster_custom_object(CDIDOMAIN, CDIVERSION, 'storageprofiles')["items"]
        for entry in storageprofiles:
            if entry['metadata']['name'] == name and 'claimPropertySets' in entry['status']:
                claimset = entry['status']['claimPropertySets'][0]
                volume_mode, volume_access = claimset['volumeMode'], claimset['accessModes'][0]
        return volume_mode, volume_access

    def get_default_storage(self, pool, volume_mode, volume_access):
        if pool is None:
            default_pool = self.get_default_sc()
            if default_pool is not None:
                pool = default_pool
        if pool is not None:
            pool_volume_mode, pool_volume_access = self.get_sc_details(pool)
            if pool_volume_mode is not None and pool_volume_access is not None:
                volume_mode, volume_access = pool_volume_mode, pool_volume_access
        return pool, volume_mode, volume_access

    def update_reference(self, owners, namespace, reference):
        core = self.core
        body = {'metadata': {'ownerReferences': [reference]}}
        for entry in owners:
            if 'disk' in entry:
                core.patch_namespaced_persistent_volume_claim(entry, namespace, body)
            elif 'secret' in entry:
                core.patch_namespaced_secret(entry, namespace, body)

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_cdi_endpoint(self, pvc, endpoint):
        core = self.core
        body = {'metadata': {'annotations': {"cdi.kubevirt.io/storage.import.endpoint": endpoint}}}
        core.patch_namespaced_persistent_volume_claim(pvc, self.namespace, body)

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
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

    def list_sriov_networks(self):
        namespace = self.namespace
        crds = self.crds
        try:
            items = crds.list_namespaced_custom_object(SRIOVDOMAIN, SRIOVVERSION, namespace, 'sriovnetworks')["items"]
            sriov_networks = [n['metadata']['name'] for n in items]
        except:
            sriov_networks = []
        return sriov_networks

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
