#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kubevirt Provider Class
"""

from kubernetes import client
# from kubernetes.stream import stream
from kvirt.kubecommon import Kubecommon
from netaddr import IPAddress
from kvirt import common
from kvirt.defaults import IMAGES, UBUNTUS
import datetime
import os
import time
import yaml
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "kubevirt.io"
CDIDOMAIN = "cdi.kubevirt.io"
KUBEVIRTNAMESPACE = "kube-system"
VERSION = 'v1alpha3'
MULTUSDOMAIN = 'k8s.cni.cncf.io'
MULTUSVERSION = 'v1'
CONTAINERDISKS = ['kubevirt/alpine-container-disk-demo', 'kubevirt/cirros-container-disk-demo',
                  'karmab/debian-container-disk-demo', 'kubevirt/fedora-cloud-container-disk-demo',
                  'karmab/fedora-coreos-container-disk-demo', 'karmab/gentoo-container-disk-demo',
                  'karmab/ubuntu-container-disk-demo']
KUBECTL_LINUX = "https://storage.googleapis.com/kubernetes-release/release/v1.16.1/bin/linux/amd64/kubectl"
KUBECTL_MACOSX = KUBECTL_LINUX.replace('linux', 'darwin')


class Kubevirt(Kubecommon):
    """

    """
    def __init__(self, token=None, ca_file=None, context=None, multus=True, host='127.0.0.1', port=443,
                 user='root', debug=False, tags=None, namespace=None, cdi=False, datavolumes=True, readwritemany=False):
        Kubecommon.__init__(self, token=token, ca_file=ca_file, context=context, host=host, port=port,
                            namespace=namespace, readwritemany=readwritemany)
        self.crds = client.CustomObjectsApi(api_client=self.api_client)
        self.debug = debug
        self.multus = multus
        self.tags = tags
        self.cdi = False
        self.datavolumes = False
        if cdi:
            try:
                cdipods = self.core.list_pod_for_all_namespaces(label_selector='app=containerized-data-importer').items
                if cdipods:
                    for pod in cdipods:
                        if pod.metadata.name.startswith('cdi-deployment'):
                            self.cdinamespace = pod.metadata.namespace
                            self.cdi = True
                if self.cdi and datavolumes:
                    try:
                        cm = self.core.read_namespaced_config_map('kubevirt-config', KUBEVIRTNAMESPACE)
                        if 'feature-gates' in cm.data and 'DataVolumes' in cm.data['feature-gates']:
                            self.datavolumes = True
                    except:
                        pass
            except:
                pass
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
               files=[], enableroot=True, alias=[], overrides={}, tags=[], dnsclient=None, storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False,
               kube=None, kubetype=None):
        guestagent = False
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        if image is not None:
            containerdisk = True if '/' in image else False
            if image not in self.volumes():
                if image in ['alpine', 'cirros', 'fedora-cloud']:
                    image = "kubevirt/%s-container-disk-demo" % image
                    common.pprint("Using container disk %s as image" % image)
                elif image in ['debian', 'gentoo', 'ubuntu']:
                    image = "karmab/%s-container-disk-demo" % image
                    common.pprint("Using container disk %s as image" % image)
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
        datavolumes = self.datavolumes
        namespace = self.namespace
        if cdi:
            cdinamespace = self.cdinamespace
            allpvc = core.list_namespaced_persistent_volume_claim(cdinamespace)
            images = {}
            for p in core.list_namespaced_persistent_volume_claim(cdinamespace).items:
                if p.metadata.annotations is not None\
                        and 'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations:
                    cdiname = self.get_image_name(p.metadata.annotations['cdi.kubevirt.io/storage.import.endpoint'])
                    images[cdiname] = p.metadata.name
        else:
            allpvc = core.list_namespaced_persistent_volume_claim(namespace)
            images = {p.metadata.annotations['kcli/image']: p.metadata.name for p in allpvc.items
                      if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations}
        vm = {'kind': 'VirtualMachine', 'spec': {'running': start, 'template':
                                                 {'metadata': {'labels': {'kubevirt.io/provider': 'kcli',
                                                                          'kubevirt.io/domain': name}},
                                                  'spec': {'domain': {'resources':
                                                                      {'requests': {'memory': '%sM' % memory}},
                                                                      # 'cpu': {'cores': numcpus, 'model': cpumodel},
                                                                      'cpu': {'cores': numcpus},
                                                                      'devices': {'disks': []}}, 'volumes': []}}},
              'apiVersion': 'kubevirt.io/%s' % VERSION, 'metadata': {'name': name, 'namespace': namespace,
                                                                     'labels': {'kubevirt.io/os': 'linux',
                                                                                'special': 'vmi-migratable'},
                                                                     'annotations': {'kcli/plan': plan,
                                                                                     'kcli/profile': profile,
                                                                                     'kcli/image': image}}}
        if dnsclient is not None:
            vm['metadata']['annotations']['kcli/dnsclient'] = dnsclient
        if kube is not None and kubetype is not None:
            vm['metadata']['annotations']['kcli/kube'] = kube
            vm['metadata']['annotations']['kcli/kubetype'] = kubetype
        if domain is not None:
            vm['metadata']['annotations']['kcli/domain'] = domain
            if reservedns:
                vm['spec']['template']['spec']['hostname'] = name
                vm['spec']['template']['spec']['subdomain'] = domain
                vm['spec']['template']['metadata']['labels']['subdomain'] = domain
        vm['spec']['template']['spec']['domain']['machine'] = {'type': 'q35'}
        features = {}
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
            tags = {tag.split('=')[0]: tag.split('=')[1] for tag in tags}
            vm['spec']['template']['spec']['nodeSelector'] = tags
        interfaces = []
        networks = []
        allnetworks = {}
        for index, net in enumerate(nets):
            netpublic = False
            newif = {'bridge': {}}
            newnet = {}
            if isinstance(net, str):
                netname = net
                newif['name'] = netname
                newnet['name'] = netname
                if index == 0 and netname == 'default':
                    netpublic = True
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
                if index == 0:
                    netpublic = net.get('public', False)
                    if 'ip' in nets[index]:
                        vm['metadata']['annotations']['kcli/ip'] = nets[index]['ip']
            if netname != 'default':
                if not allnetworks:
                    allnetworks = self.list_networks()
                if netname not in allnetworks:
                    return {'result': 'failure', 'reason': "network %s not found" % netname}
                if index == 0:
                    netpublic = False
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
                if 'name' in disk:
                    existingpvc = True
            myvolume = {'name': diskname}
            if image is not None and index == 0:
                if image in CONTAINERDISKS or '/' in image:
                    myvolume['containerDisk'] = {'image': image}
                elif cdi and datavolumes:
                    myvolume['dataVolume'] = {'name': diskname}
                else:
                    myvolume['persistentVolumeClaim'] = {'claimName': diskname}
            if index > 0 or image is None:
                myvolume['persistentVolumeClaim'] = {'claimName': diskname}
            newdisk = {'disk': {'bus': diskinterface}, 'name': diskname}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec']['template']['spec']['volumes'].append(myvolume)
            if index == 0 and containerdisk:
                continue
            if existingpvc:
                continue
            diskpool = self.check_pool(pool)
            pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': diskpool,
                                                             'accessModes': [self.accessmode],
                                                             'resources': {'requests': {'storage': '%sGi' % disksize}}},
                   'apiVersion': 'v1', 'metadata': {'name': diskname}}
            if image is not None and index == 0 and image not in CONTAINERDISKS and cdi:
                annotation = "%s/%s" % (cdinamespace, images[image])
                pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': annotation}
                pvc['metadata']['labels'] = {'app': 'Host-Assisted-Cloning'}
            pvcs.append(pvc)
            sizes.append(disksize)
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
            if image is not None and common.needs_ignition(image):
                version = common.ignition_version(image)
                ignitiondata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                               domain=domain, reserveip=reserveip, files=files,
                                               enableroot=enableroot, overrides=overrides, version=version,
                                               plan=plan, compact=True, image=image)
                vm['spec']['template']['metadata']['annotations'] = {'kubevirt.io/ignitiondata': ignitiondata}
            else:
                common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain,
                                 reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides,
                                 iso=False, storemetadata=storemetadata)
                cloudinitdata = open('/tmp/user-data', 'r').read().strip()
                cloudinitdisk = {'cdrom': {'bus': 'sata'}, 'name': 'cloudinitdisk'}
                vm['spec']['template']['spec']['domain']['devices']['disks'].append(cloudinitdisk)
                cloudinitvolume = {'cloudInitNoCloud': {'userData': cloudinitdata}, 'name': 'cloudinitdisk'}
                vm['spec']['template']['spec']['volumes'].append(cloudinitvolume)
        if self.debug:
            common.pretty_print(vm)
        for pvc in pvcs:
            pvcname = pvc['metadata']['name']
            pvcsize = pvc['spec']['resources']['requests']['storage'].replace('Gi', '')
            if image not in CONTAINERDISKS and index == 0:
                if cdi:
                    if datavolumes:
                        dvt = {'metadata': {'name': diskname},
                               'spec': {'pvc': {'accessModes': [self.accessmode],
                                                'resources':
                                                {'requests': {'storage': '%sGi' % pvcsize}}},
                                        'source': {'pvc': {'name': image, 'namespace': self.cdinamespace}}},
                               'status': {}}
                        vm['spec']['dataVolumeTemplates'] = [dvt]
                        continue
                    else:
                        core.create_namespaced_persistent_volume_claim(namespace, pvc)
                        bound = self.pvc_bound(pvcname, namespace)
                        if not bound:
                            return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % pvcname}
                        completed = self.import_completed(pvcname, namespace)
                        if not completed:
                            common.pprint("Issue with cdi import", color='red')
                            return {'result': 'failure', 'reason': 'timeout waiting for cdi importer pod to complete'}
                        continue
                else:
                    copy = self.copy_image(diskpool, image, diskname)
                    if copy['result'] == 'failure':
                        reason = copy['reason']
                        return {'result': 'failure', 'reason': reason}
                    continue
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(pvcname, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % pvcname}
            # prepare = self.prepare_pvc(pvcname, size=pvcsize)
            # if prepare['result'] == 'failure':
            #    reason = prepare['reason']
            #    return {'result': 'failure', 'reason': reason}
        crds.create_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', vm)
        if reservedns and domain is not None:
            try:
                core.read_namespaced_service(domain, namespace)
            except:
                dnsspec = {'apiVersion': 'v1', 'kind': 'Service', 'metadata': {'name': domain},
                           'spec': {'selector': {'subdomain': domain}, 'clusterIP': 'None',
                                    'ports': [{'name': 'foo', 'port': 1234, 'targetPort': 1234}]}}
                core.create_namespaced_service(namespace, dnsspec)
        if netpublic:
            try:
                core.read_namespaced_service('%s-ssh' % name, namespace)
            except:
                localport = common.get_free_nodeport()
                sshspec = {'kind': 'Service', 'apiVersion': 'v1',
                           'metadata': {'namespace': namespace, 'name': '%s-ssh' % name},
                           'spec': {'externalTrafficPolicy': 'Cluster', 'sessionAffinity': 'None',
                                    'type': 'NodePort', 'ports':
                                    [{'protocol': 'TCP', 'targetPort': 22, 'nodePort': localport, 'port': 22}],
                                    'selector': {'kubevirt.io/provider': 'kcli', 'kubevirt.io/domain': name}}}
                core.create_namespaced_service(namespace, sshspec)
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

    def stop(self, name):
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
        if cdi:
            cdinamespace = self.cdinamespace
            print("Cdi Namespace: %s" % cdinamespace)
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
            common.pprint("This functionality is not supported in container mode", color='red')
            return
        kubectl = common.get_binary('kubectl', KUBECTL_LINUX, KUBECTL_MACOSX, compressed=True)
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        uid = vm.get("metadata")['uid']
        for pod in core.list_namespaced_pod(namespace).items:
            if pod.metadata.name.startswith("virt-launcher-%s-" % name) and\
                    pod.metadata.labels['kubevirt.io/domain'] == name:
                podname = pod.metadata.name
                localport = common.get_free_port()
                break
        # exe = ['/bin/sh', '-c', 'socat -d -d TCP4-LISTEN:%s,fork UNIX-CONNECT:/var/run/kubevirt-private/%s/virt-vnc'
        #       % (localport, uid)]
        # stream(core.connect_get_namespaced_pod_exec, podname, namespace, command=exe, stderr=True, stdin=False,
        #       stdout=True, tty=True, _preload_content=False)
        nccmd = "%s exec -n %s %s -- /bin/sh -c 'nc -l %s | nc -U /var/run/kubevirt-private/%s/virt-vnc'" % (kubectl,
                                                                                                             namespace,
                                                                                                             podname,
                                                                                                             localport,
                                                                                                             uid)
        nccmd += " &"
        os.system(nccmd)
        # stream(core.connect_post_namespaced_pod_portforward, podname, namespace, ports=localport,
        # _preload_content=False)
        forwardcmd = "%s port-forward %s %s:%s &" % (kubectl, podname, localport, localport)
        os.system(forwardcmd)
        time.sleep(15)
        if web:
            return "vnc://127.0.0.1:%s" % localport
        consolecommand = "remote-viewer vnc://127.0.0.1:%s &" % localport
        if self.debug:
            msg = "Run the following command:\n%s" % consolecommand if not self.debug else consolecommand
            common.pprint(msg)
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
            common.pprint("VM %s not found" % name, color='red')
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
        crds = self.crds
        if vm is None:
            try:
                vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
            except:
                common.pprint("VM %s not found" % name, color='red')
                return {}
        metadata = vm.get("metadata")
        spec = vm.get("spec")
        running = spec.get("running")
        annotations = metadata.get("annotations")
        spectemplate = vm['spec'].get('template')
        volumes = spectemplate['spec']['volumes']
        name = metadata["name"]
        # creationdate = metadata["creationTimestamp"].strftime("%d-%m-%Y %H:%M")
        creationdate = metadata["creationTimestamp"]
        profile, plan, image = 'N/A', 'N/A', 'N/A'
        kube, kubetype = None, None
        ip = None
        if annotations is not None:
            profile = annotations['kcli/profile'] if 'kcli/profile' in annotations else 'N/A'
            plan = annotations['kcli/plan'] if 'kcli/plan' in annotations else 'N/A'
            image = annotations['kcli/image'] if 'kcli/image' in annotations else 'N/A'
            ip = vm['metadata']['annotations']['kcli/ip'] if 'kcli/ip' in annotations else None
            kube = annotations['kcli/kube'] if 'kcli/kube' in annotations else None
            kubetype = annotations['kcli/kubetype'] if 'kcli/kubetype' in annotations else None
        host = None
        state = 'down'
        foundmacs = {}
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
                            if 'ipAddress' in interface\
                                    and IPAddress(interface['ipAddress'].split('/')[0]).version == 4:
                                ip = interface['ipAddress'].split('/')[0]
                            if 'mac' in interface:
                                foundmacs[index] = interface['mac']

            except:
                pass
        else:
            state = 'down'
        yamlinfo = {'name': name, 'nets': [], 'disks': [], 'state': state, 'creationdate': creationdate, 'host': host,
                    'status': state, 'namespace': namespace}
        if 'cpu' in spectemplate['spec']['domain']:
            numcpus = spectemplate['spec']['domain']['cpu']['cores']
            yamlinfo['cpus'] = numcpus
        if 'resources' in spectemplate['spec']['domain'] and 'requests' in spectemplate['spec']['domain']['resources']:
            memory = spectemplate['spec']['domain']['resources']['requests']['memory']
            yamlinfo['memory'] = memory
        if image is not None:
            yamlinfo['image'] = image
            if image != 'N/A':
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
        plaindisks = spectemplate['spec']['domain']['devices']['disks']
        disks = []
        for d in plaindisks:
            bus = 'N/A'
            if 'disk' in d:
                bus = d['disk'].get('bus', 'N/A')
            volumename = d['name']
            volumeinfo = [volume for volume in volumes if volume['name'] == volumename][0]
            size = '0'
            if 'persistentVolumeClaim' in volumeinfo:
                pvcname = volumeinfo['persistentVolumeClaim']['claimName']
                _type = 'pvc'
                try:
                    pvc = core.read_namespaced_persistent_volume_claim(pvcname, namespace)
                    size = pvc.spec.resources.requests['storage'].replace('Gi', '')
                except:
                    common.pprint("pvc %s not found. That can't be good" % pvcname, color='red')
                    size = 'N/A'
            elif 'cloudInitNoCloud' in volumeinfo:
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
        nodeport = self._node_port(name, namespace)
        if nodeport is not None:
            yamlinfo['nodeport'] = nodeport
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
            common.pprint("VM %s not found" % name, color='red')
            os._exit(1)
        return ip

    def volumes(self, iso=False):
        core = self.core
        namespace = self.namespace
        cdi = self.cdi
        if iso:
            return []
        images = []
        if cdi:
            cdinamespace = self.cdinamespace
            pvc = core.list_namespaced_persistent_volume_claim(cdinamespace)
            images = [self.get_image_name(p.metadata.annotations['cdi.kubevirt.io/storage.import.endpoint'])
                      for p in pvc.items if p.metadata.annotations is not None and
                      'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations]
        else:
            pvc = core.list_namespaced_persistent_volume_claim(namespace)
            images = [p.metadata.annotations['kcli/image'] for p in pvc.items
                      if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations]
        return sorted(images + CONTAINERDISKS)

    def delete(self, name, snapshots=False):
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
            crds.delete_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name,
                                                 client.V1DeleteOptions())
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        pvcvolumes = [v['persistentVolumeClaim']['claimName'] for v in vm['spec']['template']['spec']['volumes'] if
                      'persistentVolumeClaim' in v]
        pvcs = [pvc for pvc in core.list_namespaced_persistent_volume_claim(namespace).items
                if pvc.metadata.name in pvcvolumes]
        for p in sorted(pvcs):
            pvcname = p.metadata.name
            common.pprint("Deleting pvc %s" % pvcname, color='blue')
            core.delete_namespaced_persistent_volume_claim(pvcname, namespace, client.V1DeleteOptions())
        try:
            core.delete_namespaced_service('%s-ssh' % name, namespace)
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
            common.pprint("VM %s not found" % name, color='red')
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
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['resources']['requests']['memory'] = "%sM" % memory
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        common.pprint("Change will only appear next full lifeclyclereboot", color='yellow')
        return

    def update_cpus(self, name, numcpus):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['cpu']['cores'] = int(numcpus)
        common.pprint("Change will only appear next full lifeclyclereboot", color='yellow')
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        print("not implemented")
        return

    def update_flavor(self, name, flavor):
        print("Not implemented")
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        core = self.core
        namespace = self.namespace
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        images = {p.metadata.annotations['kcli/image']: p.metadata.name for p in pvc.items
                  if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations}
        try:
            pvc = core.read_namespaced_persistent_volume(name, namespace)
            common.pprint("Disk %s already there" % name, color='red')
            return 1
        except:
            pass
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'accessModes': [self.accessmode],
                                                         'resources': {'requests': {'storage': '%sGi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': name}}
        if image is not None:
            pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': images[image]}
        core.create_namespaced_persistent_volume_claim(namespace, pvc)
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio'):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        currentdisks = [disk for disk in vm['spec'][t]['spec']['domain']['devices']['disks']
                        if disk['name'] != 'cloudinitdisk']
        index = len(currentdisks)
        diskname = '%s-disk%d' % (name, index)
        self.create_disk(diskname, size=size, pool=pool, thin=thin, image=image)
        bound = self.pvc_bound(diskname, namespace)
        if not bound:
            return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % diskname}
        prepare = self.prepare_pvc(diskname, size=size)
        if prepare['result'] == 'failure':
            reason = prepare['reason']
            return {'result': 'failure', 'reason': reason}
        myvolume = {'name': diskname, 'persistentVolumeClaim': {'claimName': diskname}}
        newdisk = {'name': diskname}
        vm['spec'][t]['spec']['domain']['devices']['disks'].append(newdisk)
        vm['spec'][t]['spec']['volumes'].append(myvolume)
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def delete_disk(self, name=None, diskname=None, pool=None):
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        diskindex = [i for i, disk in enumerate(vm['spec'][t]['spec']['domain']['devices']['disks'])
                     if disk['name'] == diskname]
        if not diskindex:
            common.pprint("Disk %s not found" % diskname, color='red')
            return {'result': 'failure', 'reason': "disk %s not found in VM" % diskname}
        diskindex = diskindex[0]
        volname = vm['spec'][t]['spec']['domain']['devices']['disks'][diskindex]['name']
        volindex = [i for i, vol in enumerate(vm['spec'][t]['spec']['volumes']) if vol['name'] == volname]
        if volindex:
            volindex = volindex[0]
            del vm['spec'][t]['spec']['volumes'][volindex]
        del vm['spec'][t]['spec']['domain']['devices']['disks'][diskindex]
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        try:
            core.delete_namespaced_persistent_volume_claim(volname, namespace, client.V1DeleteOptions())
        except:
            common.pprint("Disk %s not found" % volname, color='red')
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
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        print("not implemented")
        return

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")
        return

    def delete_image(self, image):
        common.pprint("Deleting image %s" % image)
        core = self.core
        if self.cdi:
            cdinamespace = self.cdinamespace
            pvc = core.list_namespaced_persistent_volume_claim(cdinamespace)
            images = [p.metadata.name for p in pvc.items if p.metadata.annotations is not None and
                      'cdi.kubevirt.io/storage.import.endpoint' in p.metadata.annotations and
                      self.get_image_name(p.metadata.annotations['cdi.kubevirt.io/storage.import.endpoint']) ==
                      image]
            if images:
                core.delete_namespaced_persistent_volume_claim(images[0], cdinamespace, client.V1DeleteOptions())
                return {'result': 'success'}
        else:
            pvc = core.list_namespaced_persistent_volume_claim(self.namespace)
            images = [p.metadata.name for p in pvc.items
                      if p.metadata.annotations is not None and 'kcli/image' in p.metadata.annotations and
                      p.metadata.annotations['kcli/image'] == image]
            if images:
                core.delete_namespaced_persistent_volume_claim(images[0], self.namespace, client.V1DeleteOptions())
                return {'result': 'success'}
        return {'result': 'failure', 'reason': 'image %s not found' % image}

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        sizes = {'debian': 2, 'centos': 8, 'centos7': 8, 'fedora': 4, 'rhel': 10, 'trusty': 2.2, 'xenial': 2.2,
                 'yakkety': 2.2, 'zesty': 2.2, 'artful': 2.2, 'bionic': 2.2, 'cosmic': 2.2}
        core = self.core
        pool = self.check_pool(pool)
        namespace = self.namespace
        cdi = self.cdi
        shortimage = os.path.basename(image).split('?')[0]
        if name is None:
            volname = [k for k in IMAGES if IMAGES[k] == image][0]
        else:
            volname = name.replace('_', '-').replace('.', '-').lower()
        for key in sizes:
            if key in shortimage and shortimage.endswith('qcow2'):
                size = sizes[key]
                break
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        podname = '%s-%s-importer' % (now, volname)
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'accessModes': [self.accessmode],
                                                         'resources': {'requests': {'storage': '%sGi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': volname, 'annotations': {'kcli/image': shortimage}}}
        if cdi:
            cdinamespace = self.cdinamespace
            pvc['metadata']['annotations'] = {'cdi.kubevirt.io/storage.import.endpoint': image}
            namespace = cdinamespace
        else:
            pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never',
                                           'containers': [{'image': 'kubevirtci/disk-importer',
                                                           'volumeMounts': [{'mountPath': '/storage',
                                                                             'name': 'storage1'}],
                                                           'name': 'importer',
                                                           'env': [{'name': 'CURL_OPTS', 'value': '-L'},
                                                                   {'name': 'INSTALL_TO',
                                                                    'value': '/storage/disk.img'},
                                                                   {'name': 'URL', 'value': image}]}],
                                           'volumes': [{'name': 'storage1',
                                                        'persistentVolumeClaim': {'claimName': volname}}]},
                   'apiVersion': 'v1', 'metadata': {'name': podname}}
        try:
            core.read_namespaced_persistent_volume_claim(volname, namespace)
            common.pprint("Using existing pvc")
        except:
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(volname, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc to get bound'}
        if cdi:
            completed = self.import_completed(volname, namespace)
            if not completed:
                common.pprint("Issue with cdi import", color='red')
                return {'result': 'failure', 'reason': 'timeout waiting for cdi importer pod to complete'}
        else:
            core.create_namespaced_pod(namespace, pod)
            completed = self.pod_completed(podname, namespace)
            if not completed:
                common.pprint("Issue with pod %s. Leaving it for debugging purposes" % podname, color='red')
                return {'result': 'failure', 'reason': 'timeout waiting for importer pod to complete'}
            else:
                core.delete_namespaced_pod(podname, namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def copy_image(self, pool, ori, dest, size=1):
        sizes = {'debian': 2, 'centos': 8, 'fedora': 4, 'rhel': 10, 'trusty': 2.2, 'xenial': 2.2, 'yakkety': 2.2,
                 'zesty': 2.2, 'artful': 2.2}
        core = self.core
        namespace = self.namespace
        ori = ori.replace('_', '-').replace('.', '-').lower()
        for key in sizes:
            if key in ori and ori.endswith('qcow2'):
                size = sizes[key]
                break
        size = 1024 * int(size) + 100
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        podname = '%s-%s-copy' % (now, dest)
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool, 'accessModes': [self.accessmode],
                                                         'resources': {'requests': {'storage': '%sMi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': dest}}
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never',
                                       'containers': [{'image': 'alpine', 'volumeMounts': [{'mountPath': '/storage1',
                                                                                            'name': 'storage1'},
                                                                                           {'mountPath': '/storage2',
                                                                                            'name': 'storage2'}],
                                                       'name': 'copy', 'command': ['cp'], 'args': ['-u',
                                                                                                   '/storage1/disk.img',
                                                                                                   '/storage2']}],
                                       'volumes': [{'name': 'storage1', 'persistentVolumeClaim': {'claimName': ori}},
                                                   {'name': 'storage2', 'persistentVolumeClaim': {'claimName': dest}}]},
               'apiVersion': 'v1', 'metadata': {'name': podname}}
        try:
            core.read_namespaced_persistent_volume_claim(dest, namespace)
            common.pprint("Using existing pvc")
        except:
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(dest, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc to get bound'}
        core.create_namespaced_pod(namespace, pod)
        completed = self.pod_completed(podname, namespace)
        if not completed:
            common.pprint("Using with pod %s. Leaving it for debugging purposes" % podname, color='red')
            return {'result': 'failure', 'reason': 'timeout waiting for copy to finish'}
        else:
            core.delete_namespaced_pod(podname, namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        crds = self.crds
        namespace = self.namespace
        apiversion = "%s/%s" % (MULTUSDOMAIN, MULTUSVERSION)
        vlanconfig = '"vlan": %s' % overrides['vlan'] if 'vlan' in overrides is not None else ''
        config = '{ "cniVersion": "0.3.1", "type": "ovs", "bridge": "%s" %s}' % (name, vlanconfig)
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
                                                 'network-attachment-definitions', name,
                                                 client.V1DeleteOptions())
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
            # nodeip = node.status.addresses[0].address
            cidr = node.spec.pod_cidr
        networks = {'default': {'cidr': cidr, 'dhcp': True, 'type': 'bridge', 'mode': 'N/A'}}
        if self.multus:
            crds = self.crds
            namespace = self.namespace
            nafs = crds.list_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace,
                                                      'network-attachment-definitions')["items"]
            for naf in nafs:
                config = yaml.safe_load(naf['spec']['config'])
                name = naf['metadata']['name']
                _type = config['type']
                bridge = config['bridge']
                vlan = config.get('vlan', 'N/A')
                dhcp = False
                cidr = bridge
                if 'ipam' in config:
                    dhcp = True
                    cidr = config['ipam'].get('subnet', bridge)
                networks[name] = {'cidr': cidr, 'dhcp': dhcp, 'type': _type, 'mode': vlan}
            return networks

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
            common.pprint("Waiting for pvc %s to get bound..." % volname)
            pvcruntime += 2
        return True

    def import_completed(self, volname, namespace):
        core = self.core
        pvctimeout = 400
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
            common.pprint("Waiting for import to complete...")
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
            common.pprint("Waiting for pod %s to complete..." % podname)
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
            common.pprint("Using with pod %s. Leaving it for debugging purposes" % podname, color='red')
            return {'result': 'failure', 'reason': 'timeout waiting for preparation of disk to finish'}
        else:
            core.delete_namespaced_pod(podname, namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def check_pool(self, pool):
        storageapi = self.storageapi
        storageclasses = storageapi.list_storage_class().items
        if storageclasses:
            storageclasses = [s.metadata.name for s in storageclasses]
            if pool in storageclasses:
                return pool
        common.pprint("Pool %s not found. Using None" % pool, color='blue')
        return None

    def flavors(self):
        return []

    def get_image_name(self, name):
        if '?' in name:
            return os.path.basename(name).split('?')[0]
        else:
            return os.path.basename(name)

    def _node_port(self, name, namespace):
        try:
            sshservice = self.core.read_namespaced_service('%s-ssh' % name, namespace)
        except:
            return None
        return sshservice.spec.ports[0].node_port

    def list_dns(self, domain):
        return []
