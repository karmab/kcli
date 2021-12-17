#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kubevirt Provider Class
"""

import base64
from kubernetes import client
# from kubernetes.stream import stream
from kvirt.kubecommon import Kubecommon
from netaddr import IPAddress
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

DOMAIN = "kubevirt.io"
CDIDOMAIN = "cdi.kubevirt.io"
CDIVERSION = "v1beta1"
KUBEVIRTNAMESPACE = "kube-system"
VERSION = 'v1alpha3'
MULTUSDOMAIN = 'k8s.cni.cncf.io'
MULTUSVERSION = 'v1'
HDOMAIN = "harvesterhci.io"
HVERSION = "v1beta1"
CONTAINERDISKS = ['quay.io/kubevirt/alpine-container-disk-demo', 'quay.io/kubevirt/cirros-container-disk-demo',
                  'quay.io/karmab/debian-container-disk-demo', 'quay.io/karmab/freebsd-container-disk-demo',
                  'quay.io/kubevirt/fedora-cloud-container-disk-demo',
                  'quay.io/karmab/fedora-coreos-container-disk-demo', 'quay.io/karmab/gentoo-container-disk-demo',
                  'quay.io/karmab/ubuntu-container-disk-demo']
KUBECTL_LINUX = "https://storage.googleapis.com/kubernetes-release/release/v1.16.1/bin/linux/amd64/kubectl"
KUBECTL_MACOSX = KUBECTL_LINUX.replace('linux', 'darwin')


def _base_image_size(image):
    if 'rhcos' in image.lower():
        size = 20
    elif 'centos' in image.lower():
        size = 11
    else:
        size = 9
    return size


class Kubevirt(Kubecommon):
    """

    """
    def __init__(self, token=None, ca_file=None, context=None, host='127.0.0.1', port=6443, user='root', debug=False,
                 namespace=None, cdi=True, datavolumes=False, disk_hotplug=False, readwritemany=False, registry=None,
                 access_mode='NodePort', volume_mode='Filesystem', volume_access='ReadWriteOnce', harvester=False):
        Kubecommon.__init__(self, token=token, ca_file=ca_file, context=context, host=host, port=port,
                            namespace=namespace, readwritemany=readwritemany)
        self.crds = client.CustomObjectsApi(api_client=self.api_client)
        self.debug = debug
        self.cdi = cdi
        self.datavolumes = datavolumes
        self.registry = registry
        self.access_mode = access_mode
        self.volume_mode = volume_mode
        self.volume_access = volume_access
        self.cdi = cdi
        self.disk_hotplug = disk_hotplug
        self.harvester = harvester
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
               vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None,
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, alias=[], overrides={}, tags=[], storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False,
               metadata={}, securitygroups=[]):
        guestagent = False
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        if image is not None:
            containerdisk = True if '/' in image else False
            if image not in self.volumes():
                if image in ['alpine', 'cirros', 'fedora-cloud']:
                    image = "kubevirt/%s-container-disk-demo" % image
                    pprint("Using container disk %s as image" % image)
                elif image in ['debian', 'gentoo', 'ubuntu']:
                    image = "karmab/%s-container-disk-demo" % image
                    pprint("Using container disk %s as image" % image)
                elif '/' not in image:
                    return {'result': 'failure', 'reason': "you don't have image %s" % image}
            if image.startswith('kubevirt/fedora-cloud-registry-disk-demo') and memory <= 512:
                memory = 1024
        default_disksize = disksize
        default_diskinterface = diskinterface
        default_pool = pool
        crds = self.crds
        core = self.core
        cdi = self.cdi
        harvester = self.harvester
        datavolumes = self.datavolumes
        namespace = self.namespace
        if harvester:
            images = {}
            virtualimages = crds.list_namespaced_custom_object(HDOMAIN, HVERSION, namespace,
                                                               'virtualmachineimages')["items"]
            for img in virtualimages:
                imagename = img['metadata']['name']
                images[common.filter_compression_extension(os.path.basename(img['spec']['url']))] = imagename
        elif cdi:
            allpvc = core.list_namespaced_persistent_volume_claim(namespace)
            images = {}
            for p in core.list_namespaced_persistent_volume_claim(namespace).items:
                if p.metadata.annotations is not None\
                        and 'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations:
                    cdiname = self.get_image_name(p.metadata.annotations['cdi.kubevirt.io/storage.import.endpoint'])
                    images[common.filter_compression_extension(cdiname)] = p.metadata.name
        else:
            allpvc = core.list_namespaced_persistent_volume_claim(namespace)
            images = {p.metadata.annotations['kcli/image']: p.metadata.name for p in allpvc.items
                      if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations}
        labels = {'kubevirt.io/provider': 'kcli', 'kubevirt.io/domain': name}
        vm = {'kind': 'VirtualMachine', 'spec': {'running': start, 'template':
                                                 {'metadata': {'labels': labels},
                                                  'spec': {'domain': {'resources':
                                                                      {'requests': {'memory': '%sM' % memory}},
                                                                      # 'cpu': {'cores': numcpus, 'model': cpumodel},
                                                                      'cpu': {'cores': numcpus},
                                                                      'devices': {'disks': []}}, 'volumes': []}}},
              'apiVersion': 'kubevirt.io/%s' % VERSION, 'metadata': {'name': name, 'namespace': namespace,
                                                                     'labels': {'kubevirt.io/os': 'linux',
                                                                                'special': 'vmi-migratable'},
                                                                     'annotations': {}}}
        kube = False
        for entry in sorted([field for field in metadata if field in METADATA_FIELDS]):
            vm['metadata']['annotations']['kcli/%s' % entry] = metadata[entry]
            if entry == 'kube':
                kube = True
                role = name.split('-')[1]
                if role == 'bootstrap':
                    role = 'master'
                vm['spec']['template']['metadata']['labels']['kcli/role'] = role
            if entry == 'plan' and kube:
                vm['spec']['template']['metadata']['labels']['kcli/plan'] = metadata[entry]
        if domain is not None:
            if reservedns:
                vm['spec']['template']['spec']['hostname'] = name
                vm['spec']['template']['spec']['subdomain'] = domain
                vm['spec']['template']['metadata']['labels']['subdomain'] = domain
        features = {}
        machine = 'q35'
        if 'machine' in overrides:
            warning("Forcing machine type to %s" % machine)
            machine = overrides['machine']
        vm['spec']['template']['spec']['domain']['machine'] = {'type': machine}
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
        if tags:
            final_tags = {}
            if isinstance(tags, dict):
                final_tags.update(tags)
            else:
                for tag in tags:
                    if isinstance(tag, str) and len(tag.split('=')) == 2:
                        final_tags[tag.split('=')[0]] = tag.split('=')[1]
                    elif isinstance(tag, dict):
                        final_tags.update(tag)
                    else:
                        warning("Couldn't process tag %s. Skipping..." % tag)
                        continue
            if final_tags:
                vm['spec']['template']['metadata']['labels'].update(final_tags)
        node_selector = overrides.get('nodeSelector', {})
        if isinstance(node_selector, dict) and node_selector:
            vm['spec']['template']['spec']['nodeSelector'] = node_selector
        interfaces = []
        networks = []
        allnetworks = {}
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
                if 'sriov' in net and net['sriov']:
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
                if not allnetworks:
                    allnetworks = self.list_networks()
                if netname not in allnetworks:
                    return {'result': 'failure', 'reason': "network %s not found" % netname}
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
            diskname = '%s-disk%d' % (name, index)
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
                if 'name' in disk:
                    existingpvc = True
            myvolume = {'name': diskname}
            if image is not None and index == 0:
                if image in CONTAINERDISKS or '/' in image:
                    containerdiskimage = "%s/%s" % (self.registry, image) if self.registry is not None else image
                    myvolume['containerDisk'] = {'image': containerdiskimage}
                elif harvester:
                    myvolume['dataVolume'] = {'name': diskname}
                else:
                    if cdi and datavolumes:
                        base_image_pvc = core.read_namespaced_persistent_volume_claim(images[image], namespace)
                        disksize = base_image_pvc.spec.resources.requests['storage']
                        volume_mode = base_image_pvc.spec.volume_mode
                        myvolume['dataVolume'] = {'name': diskname}
                    else:
                        myvolume['persistentVolumeClaim'] = {'claimName': diskname}
            if index > 0 or image is None:
                myvolume['persistentVolumeClaim'] = {'claimName': diskname}
            newdisk = {'disk': {'bus': diskinterface}, 'name': diskname}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec']['template']['spec']['volumes'].append(myvolume)
            if index == 0 and image is not None and containerdisk:
                continue
            if existingpvc:
                continue
            diskpool = self.check_pool(pool)
            pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': diskpool,
                                                             'volumeMode': volume_mode,
                                                             'accessModes': [volume_access],
                                                             'resources': {'requests': {'storage': '%sGi' % disksize}}},
                   'apiVersion': 'v1', 'metadata': {'name': diskname}}
            if image is not None and index == 0 and image not in CONTAINERDISKS and cdi and not harvester:
                annotation = "%s/%s" % (namespace, images[image])
                pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': annotation}
                pvc['metadata']['labels'] = {'app': 'Host-Assisted-Cloning'}
            pvcs.append(pvc)
            sizes.append(disksize)
        if iso is not None:
            if iso not in self.volumes(iso=True):
                return {'result': 'failure', 'reason': "you don't have iso %s" % iso}
            diskname = '%s-iso' % name
            newdisk = {'bootOrder': 1, 'cdrom': {'readOnly': False, 'bus': 'sata'}, 'name': diskname}
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
                                           domain=domain, reserveip=reserveip, files=files,
                                           enableroot=enableroot, overrides=overrides, version=version,
                                           plan=plan, compact=True, image=image)
            else:
                cloudinitsource = "cloudInitNoCloud"
                userdata, metadata, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                               gateway=gateway, dns=dns, domain=domain,
                                                               reserveip=reserveip, files=files, enableroot=enableroot,
                                                               overrides=overrides, storemetadata=storemetadata,
                                                               image=image, machine=machine)
                if 'static' in metadata:
                    warning("Legacy network not supported in kubevirt. Ignoring")
                    netdata = None
            cloudinitdisk = {'cdrom': {'bus': 'sata'}, 'name': 'cloudinitdisk'}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(cloudinitdisk)
            self.create_secret("%s-userdata-secret" % name, namespace, userdata, field='userdata')
            cloudinitvolume = {cloudinitsource: {'secretRef': {'name': "%s-userdata-secret" % name}},
                               'name': 'cloudinitdisk'}
            if netdata is not None and netdata != '':
                cloudinitvolume[cloudinitsource]['networkDataSecretRef'] = {'name': "%s-netdata-secret" % name}
                self.create_secret("%s-netdata-secret" % name, namespace, netdata, field='networkdata')
            vm['spec']['template']['spec']['volumes'].append(cloudinitvolume)
        if self.debug:
            common.pretty_print(vm)
        for index, pvc in enumerate(pvcs):
            pvcname = pvc['metadata']['name']
            try:
                core.read_namespaced_persistent_volume_claim(pvcname, namespace)
                pprint("Using existing pvc %s" % pvcname)
                continue
            except:
                pass
            pvcsize = pvc['spec']['resources']['requests']['storage'].replace('Gi', '')
            pvc_volume_mode = pvc['spec']['volumeMode']
            pvc_access_mode = pvc['spec']['accessModes']
            if index == 0 and image is not None and image not in CONTAINERDISKS:
                if cdi:
                    if datavolumes:
                        dvt = {'metadata': {'name': pvcname, 'annotations': {'sidecar.istio.io/inject': 'false'}},
                               'spec': {'pvc': {'volumeMode': pvc_volume_mode,
                                                'accessModes': pvc_access_mode,
                                                'resources':
                                                {'requests': {'storage': '%sGi' % pvcsize}}},
                                        'source': {'pvc': {'name': images[image], 'namespace': self.namespace}}},
                               'status': {}}
                        if harvester:
                            dvt['kind'] = 'DataVolume'
                            dvt['apiVersion'] = "%s/%s" % (CDIDOMAIN, CDIVERSION)
                            dvt['metadata']['annotations']['harvesterhci.io/imageId'] = "%s/%s" % (namespace,
                                                                                                   images[image])
                            dvt['spec']['pvc']['storageClassName'] = "longhorn-%s" % images[image]
                            dvt['spec']['source'] = {'blank': {}}
                            dvt['spec']['pvc']['volumeMode'] = 'Block'
                        vm['spec']['dataVolumeTemplates'] = [dvt]
                    else:
                        core.create_namespaced_persistent_volume_claim(namespace, pvc)
                        bound = self.pvc_bound(pvcname, namespace)
                        if not bound:
                            return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % pvcname}
                        completed = self.import_completed(pvcname, namespace)
                        if not completed:
                            error("Issue with cdi import")
                            return {'result': 'failure', 'reason': 'timeout waiting for cdi importer pod to complete'}
                else:
                    copy = self.copy_image(diskpool, images[image], diskname, size=int(pvcsize))
                    if copy['result'] == 'failure':
                        reason = copy['reason']
                        error(reason)
                        return {'result': 'failure', 'reason': reason}
                continue
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(pvcname, namespace)
            if not bound:
                error('timeout waiting for pvc %s to get bound' % pvcname)
                return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % pvcname}
        if 'affinity' in overrides and isinstance(overrides['affinity'], dict):
            vm['spec']['template']['spec']['affinity'] = overrides['affinity']
        crds.create_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', vm)
        if reservedns and domain is not None:
            try:
                core.read_namespaced_service(domain, namespace)
            except:
                dnsspec = {'apiVersion': 'v1', 'kind': 'Service', 'metadata': {'name': domain},
                           'spec': {'selector': {'subdomain': domain}, 'clusterIP': 'None',
                                    'ports': [{'name': 'foo', 'port': 1234, 'targetPort': 1234}]}}
                core.create_namespaced_service(namespace, dnsspec)
        if not tunnel and self.access_mode != 'External':
            try:
                core.read_namespaced_service('%s-ssh' % name, namespace)
            except:
                localport = common.get_free_nodeport() if self.access_mode == 'NodePort' else None
                selector = {'kubevirt.io/provider': 'kcli', 'kubevirt.io/domain': name}
                self.create_service('%s-ssh' % name, namespace, selector, _type=self.access_mode,
                                    ports=[{'port': 22, 'nodePort': localport}])
        return {'result': 'success'}

    def start(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm['spec']['running'] = True
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return {'result': 'success'}

    def stop(self, name, soft=False):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm["spec"]['running'] = False
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")
        return

    def restart(self, name):
        print("not implemented")
        return {'result': 'success'}

    def report(self):
        cdi = self.cdi
        if self.token is not None:
            print("Connection: https://%s:%s" % (self.host, self.port))
        else:
            print("Context: %s" % self.contextname)
        print("Namespace: %s" % self.namespace)
        print("Cdi: %s" % cdi)
        return

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
            vms.append(self.info(name, vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
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
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        uid = vm.get("metadata")['uid']
        for pod in core.list_namespaced_pod(namespace).items:
            if pod.metadata.name.startswith("virt-launcher-%s-" % name) and\
                    pod.metadata.labels['kubevirt.io/domain'] == name:
                podname = pod.metadata.name
                localport = common.get_free_port()
                break
        nccmd = "%s exec -n %s %s -- /bin/sh -c " % (kubectl, namespace, podname)
        nccmd += "'nc -l %s --sh-exec \"nc -U /var/run/kubevirt-private/%s/virt-vnc\"'" % (localport, uid)
        nccmd += " &"
        os.system(nccmd)
        forwardcmd = "%s port-forward %s %s:%s &" % (kubectl, podname, localport, localport)
        os.system(forwardcmd)
        time.sleep(5)
        if web:
            return "vnc://127.0.0.1:%s" % localport
        consolecommand = "remote-viewer vnc://127.0.0.1:%s &" % localport
        if self.debug:
            msg = "Run the following command:\n%s" % consolecommand if not self.debug else consolecommand
            pprint(msg)
        else:
            os.system(consolecommand)
        return

    def serialconsole(self, name, web=False):
        """

        :param name:
        :return:
        """
        kubectl = common.get_binary('kubectl', KUBECTL_LINUX, KUBECTL_MACOSX, compressed=True)
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        uid = vm.get("metadata")['uid']
        for pod in core.list_namespaced_pod(namespace).items:
            if pod.metadata.name.startswith("virt-launcher-%s-" % name) and\
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
                error("VM %s not found" % name)
                return {}
        else:
            listinfo = True
        metadata = vm.get("metadata")
        spec = vm.get("spec")
        running = spec.get("running")
        annotations = metadata.get("annotations")
        spectemplate = vm['spec'].get('template')
        volumes = spectemplate['spec']['volumes']
        name = metadata["name"]
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
            ip4s = [i for i in ips if ':' not in i]
            ip6s = [i for i in ips if i not in ip4s]
            ip = ip4s[0] if ip4s else ip6s[0]
        yamlinfo = {'name': name, 'nets': [], 'disks': [], 'status': state, 'creationdate': creationdate, 'host': host,
                    'namespace': namespace}
        if 'cpu' in spectemplate['spec']['domain']:
            numcpus = spectemplate['spec']['domain']['cpu']['cores']
            yamlinfo['cpus'] = numcpus
        if 'resources' in spectemplate['spec']['domain'] and 'requests' in spectemplate['spec']['domain']['resources']:
            memory = spectemplate['spec']['domain']['resources']['requests']['memory'].replace('M', '').replace('G', '')
            memory = memory.replace('Mi', 'Mi').replace('Gi', '').replace('i', '')
            memory = int(memory)
            if harvester:
                memory = 1024 * memory
            yamlinfo['memory'] = memory
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
                    size = pvc.spec.resources.requests['storage'].replace('Gi', '')
                except:
                    error("pvc %s not found. That can't be good" % pvcname)
                    pvc = 'N/A'
                    size = "0"
                if 'Mi' in size:
                    size = int(size.replace('Mi', '')) / 1024
                else:
                    size = int(size)
                if image != 'N/A' and self.cdi:
                    size -= 1
            elif 'cloudInitNoCloud' in volumeinfo or 'cloudInitConfigDrive' in volumeinfo:
                continue
            elif 'containerDisk' in volumeinfo:
                _type = 'containerdisk'
            else:
                _type = 'other'
            disk = {'device': d['name'], 'size': size, 'format': bus, 'type': _type, 'path': volumename}
            disks.append(disk)
        yamlinfo['disks'] = disks
        interfaces = vm['spec']['template']['spec']['domain']['devices']['interfaces']
        networks = vm['spec']['template']['spec']['networks']
        for index, interface in enumerate(interfaces):
            device = 'eth%s' % index
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
                    if 'ipAddress' in interface and IPAddress(interface['ipAddress'].split('/')[0]).version == 4:
                        ip = interface['ipAddress'].split('/')[0]
                        break
        except Exception:
            error("VM %s not found" % name)
            sys.exit(1)
        return ip

    def volumes(self, iso=False):
        core = self.core
        namespace = self.namespace
        cdi = self.cdi
        crds = self.crds
        isos = []
        allimages = []
        allimages = []
        harvester = self.harvester
        if harvester:
            virtualimages = crds.list_namespaced_custom_object(HDOMAIN, HVERSION, namespace,
                                                               'virtualmachineimages')["items"]
            allimages = [os.path.basename(image['spec']['url']) for image in virtualimages]
        elif cdi:
            pvc = core.list_namespaced_persistent_volume_claim(namespace)
            allimages = [self.get_image_name(p.metadata.annotations['cdi.kubevirt.io/storage.import.endpoint'])
                         for p in pvc.items if p.metadata.annotations is not None and
                         'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations]
        else:
            pvc = core.list_namespaced_persistent_volume_claim(namespace)
            allimages = [p.metadata.annotations['kcli/image'] for p in pvc.items
                         if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations]
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
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
                    pprint("Waiting 5s for pvcs associated to datavolumes of %s to disappear" % name)
                    time.sleep(5)
                    timeout += 5
        pvcvolumes = [v['persistentVolumeClaim']['claimName'] for v in vm['spec']['template']['spec']['volumes'] if
                      'persistentVolumeClaim' in v]
        pvcs = [pvc for pvc in core.list_namespaced_persistent_volume_claim(namespace).items
                if pvc.metadata.name in pvcvolumes]
        for p in pvcs:
            pvcname = p.metadata.name
            if pvcname.endswith('iso'):
                continue
            pprint("Deleting pvc %s" % pvcname)
            core.delete_namespaced_persistent_volume_claim(pvcname, namespace)
        try:
            core.delete_namespaced_service('%s-ssh-svc' % name, namespace)
        except:
            pass
        try:
            core.delete_namespaced_secret('%s-userdata-secret' % name, namespace)
        except:
            pass
        try:
            core.delete_namespaced_secret('%s-netdata-secret' % name, namespace)
        except:
            pass
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
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if append and "kcli/%s" % metatype in vm["metadata"]["annotations"]:
            oldvalue = vm["metadata"]["annotations"]["kcli/%s" % metatype]
            metavalue = "%s,%s" % (oldvalue, metavalue)
        vm["metadata"]["annotations"]["kcli/%s" % metatype] = metavalue
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def update_memory(self, name, memory):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['resources']['requests']['memory'] = "%sM" % memory
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        warning("Change will only appear next full lifeclyclereboot")
        return

    def update_cpus(self, name, numcpus):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        for diskindex, disk in enumerate(vm['spec']['template']['spec']['domain']['devices']['disks']):
            diskname = vm['spec']['template']['spec']['domain']['devices']['disks'][diskindex]['name']
            if iso is None and diskname.endswith('-iso'):
                del vm['spec']['template']['spec']['domain']['devices']['disks'][diskindex]
                for volindex, vol in enumerate(vm['spec']['template']['spec']['volumes']):
                    if vol['name'] == diskname:
                        del vm['spec']['template']['spec']['volumes'][volindex]
                crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
                return
        return

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
            error("Disk %s already there" % name)
            return 1
        except:
            pass
        volume_mode = overrides.get('volume_mode', self.volume_mode)
        volume_access = overrides.get('volume_access', self.volume_access)
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'volumeMode': volume_mode,
                                                         'accessModes': [volume_access],
                                                         'resources': {'requests': {'storage': '%sGi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': name}}
        if image is not None:
            pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': images[image]}
        core.create_namespaced_persistent_volume_claim(namespace, pvc)
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        currentdisks = [disk for disk in vm['spec'][t]['spec']['domain']['devices']['disks']
                        if disk['name'] != 'cloudinitdisk']
        index = len(currentdisks)
        diskname = '%s-disk%d' % (name, index)
        diskpool = self.check_pool(pool)
        myvolume = {'name': diskname, 'persistentVolumeClaim': {'claimName': diskname}}
        if self.disk_hotplug:
            pprint("Hotplugging disk %s" % diskname)
            dv = {'kind': 'DataVolume', 'apiVersion': "%s/%s" % (CDIDOMAIN, CDIVERSION),
                  'metadata': {'name': diskname, 'annotations': {'sidecar.istio.io/inject': 'false'}},
                  'spec': {'pvc': {'volumeMode': self.volume_mode,
                                   'accessModes': [self.volume_access],
                                   'resources': {'requests': {'storage': '%sGi' % size}}},
                           'source': {'blank': {}}}, 'status': {}}
            crds.create_namespaced_custom_object(CDIDOMAIN, CDIVERSION, namespace, 'datavolumes', dv)
            subresource = "/apis/subresources.kubevirt.io/v1alpha3/namespaces/%s" % namespace
            subresource += "/virtualmachines/%s/addvolume" % name
            body = {"name": diskname, "volumesource": myvolume, "disk": {"disk": {"bus": "scsi"}}}
            if 'serial' in overrides:
                body['disk']['serial'] = str(overrides['serial'])
            self.core.api_client.call_api(subresource, 'PUT', body=body)
        else:
            self.create_disk(diskname, size=size, pool=diskpool, thin=thin, image=image, overrides=overrides)
            bound = self.pvc_bound(diskname, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % diskname}
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
                error("VM %s not found" % name)
                return {'result': 'failure', 'reason': "VM %s not found" % name}
            t = 'Template' if 'Template' in vm['spec'] else 'template'
            diskindex = [i for i, disk in enumerate(vm['spec'][t]['spec']['domain']['devices']['disks'])
                         if disk['name'] == diskname]
            if not diskindex:
                error("Disk %s not found" % diskname)
                return {'result': 'failure', 'reason': "disk %s not found in VM" % diskname}
            diskindex = diskindex[0]
            if self.disk_hotplug:
                pprint("Hotunplugging disk %s" % diskname)
                myvolume = {'name': diskname, 'persistentVolumeClaim': {'claimName': diskname}}
                subresource = "/apis/subresources.kubevirt.io/v1alpha3/namespaces/%s" % namespace
                subresource += "/virtualmachines/%s/removevolume" % name
                bus = 'scsi'
                body = {"name": diskname, "volumesource": myvolume, "disk": {"disk": {"bus": bus}}}
                self.core.api_client.call_api(subresource, 'PUT', body=body)
                try:
                    crds.delete_namespaced_custom_object(CDIDOMAIN, CDIVERSION, namespace, 'datavolumes', diskname)
                except:
                    error("Disk %s not found" % diskname)
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
            error("Disk %s not found" % volname)
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

    def add_nic(self, name, network):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            error("VM %s not found" % name)
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        newif = {'bridge': {}, 'name': network}
        newnet = {'name': network}
        if network != 'default':
            if network not in self.list_networks():
                error("network %s not found" % network)
                return {'result': 'failure', 'reason': "network %s not found" % network}
            elif [entry for entry in vm['spec']['template']['spec']['networks'] if entry['name'] == network]:
                error("vm already connected to network %s" % network)
                return {'result': 'failure', 'reason': "vm already connected to network %s" % network}
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
        elif self.cdi:
            pvc = core.list_namespaced_persistent_volume_claim(self.namespace)
            images = [p.metadata.name for p in pvc.items if p.metadata.annotations is not None and
                      'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations and
                      self.get_image_name(p.metadata.annotations['cdi.kubevirt.io/storage.import.endpoint']) ==
                      image]
            if images:
                core.delete_namespaced_persistent_volume_claim(images[0], self.namespace)
                return {'result': 'success'}
        else:
            pvc = core.list_namespaced_persistent_volume_claim(self.namespace)
            images = [p.metadata.name for p in pvc.items
                      if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations and
                      p.metadata.annotations['kcli/image'] == image]
            if images:
                core.delete_namespaced_persistent_volume_claim(images[0], self.namespace)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': 'image %s not found' % image}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None):
        if size is None:
            size = _base_image_size(url)
            if self.cdi:
                warning("Setting size of image to %sG. This will be the size of primary disks using this" % size)
        core = self.core
        crds = self.crds
        pool = self.check_pool(pool)
        namespace = self.namespace
        cdi = self.cdi
        harvester = self.harvester
        shortimage = os.path.basename(url).split('?')[0]
        uncompressed = shortimage.replace('.gz', '').replace('.xz', '').replace('.bz2', '')
        if name is None:
            volname = [k for k in IMAGES if IMAGES[k] == url][0]
        else:
            volname = name.replace('_', '-').replace('.', '-').lower()
        if harvester:
            virtualmachineimage = {'kind': 'VirtualMachineImage', 'spec': {'url': url, "displayName": uncompressed},
                                   'apiVersion': '%s/%s' % (HDOMAIN, HVERSION), 'metadata': {'name': volname}}
            crds.create_namespaced_custom_object(HDOMAIN, HVERSION, self.namespace, 'virtualmachineimages',
                                                 virtualmachineimage)
            return {'result': 'success'}
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        podname = '%s-%s-importer' % (now, volname)
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'volumeMode': self.volume_mode,
                                                         'accessModes': [self.volume_access],
                                                         'resources': {'requests': {'storage': '%sGi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': volname, 'annotations': {'kcli/image': uncompressed}}}
        if cdi:
            pprint("Cloning in namespace %s" % namespace)
            pvc['metadata']['annotations'] = {'cdi.kubevirt.io/storage.import.endpoint': url}
        else:
            container = {'image': 'kubevirtci/disk-importer', 'name': 'importer'}
            if self.volume_mode == 'Filesystem':
                container['volumeMounts'] = [{'mountPath': '/storage', 'name': 'storage1'}]
                targetpath = '/storage/disk.img'
            else:
                container['volumeDevices'] = [{'devicePath': '/dev/block', 'name': 'storage1'}]
                targetpath = '/dev/block'
            container['env'] = [{'name': 'CURL_OPTS', 'value': '-L'},
                                {'name': 'INSTALL_TO', 'value': targetpath},
                                {'name': 'URL', 'value': url}]
            pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never',
                                           'containers': [container],
                                           'volumes': [{'name': 'storage1',
                                                        'persistentVolumeClaim': {'claimName': volname}}]},
                   'apiVersion': 'v1', 'metadata': {'name': podname}}
        try:
            core.read_namespaced_persistent_volume_claim(volname, namespace)
            pprint("Using existing pvc")
        except:
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(volname, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc to get bound'}
        if cdi:
            completed = self.import_completed(volname, namespace)
            if not completed:
                error("Issue with cdi import")
                return {'result': 'failure', 'reason': 'timeout waiting for cdi importer pod to complete'}
        else:
            core.create_namespaced_pod(namespace, pod)
            completed = self.pod_completed(podname, namespace)
            if not completed:
                error("Issue with pod %s. Leaving it for debugging purposes" % podname)
                return {'result': 'failure', 'reason': 'timeout waiting for importer pod to complete'}
            else:
                core.delete_namespaced_pod(podname, namespace)
        return {'result': 'success'}

    def copy_image(self, pool, ori, dest, size=1):
        core = self.core
        namespace = self.namespace
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        podname = '%s-%s-copy' % (now, dest)
        container = {'image': 'kubevirtci/disk-importer', 'name': 'copy', 'command': ['/bin/sh', '-c']}
        if self.volume_mode == 'Filesystem':
            container['volumeMounts'] = [{'mountPath': '/storage1', 'name': 'storage1'},
                                         {'mountPath': '/storage2', 'name': 'storage2'}]
            command = 'cp -u /storage1/disk.img /storage2 ; qemu-img resize /storage2/disk.img %sG' % size
        else:
            container['volumeDevices'] = [{'devicePath': '/dev/ori', 'name': 'storage1'},
                                          {'devicePath': '/dev/dest', 'name': 'storage2'}]
            command = 'dd if=/dev/ori1 of=/dev/dest bs=4M status=progress'
            command += '| dd if=/dev/ori of=/dev/dest bs=4M status=progress'
            command += '; qemu-img resize /dev/dest %sG' % size
        container['args'] = [command]
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool, 'accessModes': [self.volume_access],
                                                         'volumeMode': self.volume_mode,
                                                         'resources': {'requests': {'storage': '%sMi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': dest}}
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never', 'containers': [container],
                                       'volumes': [{'name': 'storage1', 'persistentVolumeClaim': {'claimName': ori}},
                                                   {'name': 'storage2', 'persistentVolumeClaim': {'claimName': dest}}]},
               'apiVersion': 'v1', 'metadata': {'name': podname}}
        try:
            core.read_namespaced_persistent_volume_claim(dest, namespace)
            pprint("Using existing pvc")
        except:
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(dest, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc to get bound'}
        core.create_namespaced_pod(namespace, pod)
        completed = self.pod_completed(podname, namespace)
        if not completed:
            error("Using with pod %s. Leaving it for debugging purposes" % podname)
            return {'result': 'failure', 'reason': 'timeout waiting for copy to finish'}
        else:
            core.delete_namespaced_pod(podname, namespace)
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        crds = self.crds
        namespace = self.namespace
        apiversion = "%s/%s" % (MULTUSDOMAIN, MULTUSVERSION)
        vlanconfig = '"vlan": %s' % overrides['vlan'] if 'vlan' in overrides is not None else ''
        if 'type' in overrides:
            _type = overrides['type']
        else:
            pprint("Using default type bridge for network")
            _type = 'bridge'
        config = '{ "cniVersion": "0.3.1", "type": "%s", "bridge": "%s" %s}' % (_type, name, vlanconfig)
        if cidr is not None and dhcp:
            ipam = '"ipam": { "type": "host-local", "subnet": "%s" }' % cidr
            details = '"isDefaultGateway": true, "forceAddress": false, "ipMasq": true, "hairpinMode": true, %s' % ipam
            config = '{ "type": "bridge", "bridge": "%s", %s}' % (name, details)
        network = {'kind': 'NetworkAttachmentDefinition', 'spec': {'config': config}, 'apiVersion': apiversion,
                   'metadata': {'name': name}}
        crds.create_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace, 'network-attachment-definitions',
                                             network)
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        crds = self.crds
        namespace = self.namespace
        try:
            crds.delete_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace,
                                                 'network-attachment-definitions', name)
        except:
            return {'result': 'failure', 'reason': "network %s not found" % name}
        return {'result': 'success'}

    def list_pools(self):
        storageapi = self.storageapi
        pools = [x.metadata.name for x in storageapi.list_storage_class().items]
        return pools

    def list_networks(self):
        core = self.core
        cidr = 'N/A'
        for node in core.list_node().items:
            cidr = node.spec.pod_cidr
            break
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
            _type = config['type']
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

    def pvc_bound(self, volname, namespace):
        core = self.core
        pvctimeout = 40
        pvcruntime = 0
        pvcstatus = ''
        while pvcstatus != 'Bound':
            if pvcruntime >= pvctimeout:
                return False
            pvc = core.read_namespaced_persistent_volume_claim(volname, namespace)
            pvcstatus = pvc.status.phase
            time.sleep(2)
            pprint("Waiting for pvc %s to get bound..." % volname)
            pvcruntime += 2
        return True

    def import_completed(self, volname, namespace):
        core = self.core
        pvctimeout = 900
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
        podtimeout = 600
        podruntime = 0
        podstatus = ''
        while podstatus != 'Succeeded':
            if podruntime >= podtimeout or podstatus == 'Error' or podstatus == 'Failed':
                return False
            pod = core.read_namespaced_pod(podname, namespace)
            podstatus = pod.status.phase
            time.sleep(5)
            pprint("Waiting for pod %s to complete..." % podname)
            podruntime += 5
        return True

    def prepare_pvc(self, name, size=1):
        core = self.core
        namespace = self.namespace
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        podname = '%s-%s-prepare' % (now, name)
        size = 1024 * int(size) - 48
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'OnFailure',
                                       'containers': [{'image': 'alpine', 'volumeMounts': [{'mountPath': '/storage1',
                                                                                            'name': 'storage1'}],
                                                       'name': 'prepare', 'command': ['fallocate'],
                                                       'args': ['-l', '%sM' % size, '/storage1/disk.img']}],
                                       'volumes': [{'name': 'storage1', 'persistentVolumeClaim': {'claimName': name}}]},
               'apiVersion': 'v1', 'metadata': {'name': podname}}
        core.create_namespaced_pod(namespace, pod)
        completed = self.pod_completed(podname, namespace)
        if not completed:
            error("Using with pod %s. Leaving it for debugging purposes" % podname)
            return {'result': 'failure', 'reason': 'timeout waiting for preparation of disk to finish'}
        else:
            core.delete_namespaced_pod(podname, namespace)
        return {'result': 'success'}

    def check_pool(self, pool):
        storageapi = self.storageapi
        storageclasses = storageapi.list_storage_class().items
        if storageclasses:
            storageclasses = [s.metadata.name for s in storageclasses]
            if pool in storageclasses:
                return pool
        return None

    def flavors(self):
        return []

    def get_image_name(self, name):
        if name.endswith('.gz'):
            name = name.replace('.gz', '')
        if '?' in name:
            return os.path.basename(name).split('?')[0]
        else:
            return os.path.basename(name)

    def ssh_node_port(self, name, namespace):
        try:
            sshservice = self.core.read_namespaced_service('%s-ssh-svc' % name, namespace)
        except:
            return None
        return sshservice.spec.ports[0].node_port

    def list_dns(self, domain):
        return []

    def node_host(self, name=None):
        ip = None
        for node in self.core.list_node().items:
            if name is not None and node.metadata.name != name:
                continue
            addresses = [x.address for x in node.status.addresses if x.type == 'InternalIP']
            if addresses:
                ip = addresses[0]
                break
        return ip

    def create_service(self, name, namespace, selector, _type="NodePort", ports=[], wait=True):
        spec = {'kind': 'Service', 'apiVersion': 'v1', 'metadata': {'namespace': namespace, 'name': '%s-svc' % name},
                'spec': {'sessionAffinity': 'None', 'selector': selector}}
        spec['spec']['type'] = _type
        if _type in ['NodePort', 'LoadBalancer']:
            spec['spec']['externalTrafficPolicy'] = 'Cluster'
        portspec = []
        portname = True if len(ports) > 1 else False
        for portinfo in ports:
            newportspec = {}
            if isinstance(portinfo, int):
                port = portinfo
                targetport = port
                protocol = 'TCP'
            elif isinstance(portinfo, dict):
                port = portinfo.get('port')
                protocol = portinfo.get('protocol', 'TCP')
                targetport = portinfo.get('targetPort', port)
                if _type == 'NodePort' and 'nodePort' in portinfo:
                    newportspec['nodePort'] = portinfo['nodePort']
            newportspec['protocol'] = protocol
            newportspec['port'] = port
            newportspec['targetPort'] = targetport
            if portname:
                newportspec['name'] = "port-%s" % port
            portspec.append(newportspec)
        spec['spec']['ports'] = portspec
        self.core.create_namespaced_service(namespace, spec)
        if _type == 'LoadBalancer' and wait:
            ipassigned = False
            timeout = 60
            runtime = 0
            while not ipassigned:
                if runtime >= timeout:
                    error("Time out waiting for a loadbalancer ip for service %s-svc" % name)
                    return
                else:
                    try:
                        api_service = self.core.read_namespaced_service('%s-svc' % name, namespace)
                        return api_service.status.load_balancer.ingress[0].ip
                    except:
                        time.sleep(5)
                        pprint("Waiting to get a loadbalancer ip for service %s..." % name)
                        runtime += 5
        elif _type == 'ClusterIP':
            api_service = self.core.read_namespaced_service('%s-svc' % name, namespace)
            return api_service.spec.cluster_ip

    def delete_service(self, name, namespace):
        try:
            self.core.delete_namespaced_service(name, namespace)
        except Exception as e:
            error("Couldn't delete service %s. Hit %s" % (name, e))

    def ssh_loadbalancer_ip(self, name, namespace):
        try:
            api_service = self.core.read_namespaced_service('%s-ssh-svc' % name, namespace)
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
            error("Couldn't delete service %s. Hit %s" % (name, e))

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
