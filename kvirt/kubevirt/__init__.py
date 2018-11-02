#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kubevirt Provider Class
"""

from ast import literal_eval
from kubernetes import client, config
from kvirt import common
from kvirt.defaults import TEMPLATES
import datetime
from distutils.spawn import find_executable
import os
import time
import yaml
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "kubevirt.io"
VERSION = 'v1alpha2'
MULTUSDOMAIN = 'k8s.cni.cncf.io'
MULTUSVERSION = 'v1'
REGISTRYDISKS = ['kubevirt/alpine-registry-disk-demo', 'kubevirt/cirros-registry-disk-demo',
                 'kubevirt/fedora-cloud-registry-disk-demo']


def pretty_print(o):
    """

    :param o:
    """
    # print(yaml.dump(o, default_flow_style=False, indent=2, allow_unicode=True,
    #                encoding='utf-8').replace('!!python/unicode ', '').replace("'", '').replace('\n\n', '\n').
    #      replace('#cloud-config', '|\n            #cloud-config'))
    print(yaml.dump(o, default_flow_style=False, indent=2,
                    allow_unicode=True).replace('!!python/unicode ', '').replace("'", '').replace('\n\n', '\n').
          replace('#cloud-config', '|\n            #cloud-config'))


class Kubevirt(object):
    """

    """
    def __init__(self, context=None, cdi=False, multus=True, host='127.0.0.1', port=22, user='root', debug=False,
                 tags=None):
        self.host = host
        self.port = port
        self.user = user
        self.cdi = cdi
        self.multus = multus
        self.conn = 'OK'
        self.tags = tags
        contexts, current = config.list_kube_config_contexts()
        if context is not None:
            contexts = [entry for entry in contexts if entry['name'] == context]
            if contexts:
                context = contexts[0]
                contextname = context['name']
            else:
                self.conn = None
        else:
            context = current
            contextname = current['name']
        config.load_kube_config(context=contextname)
        if 'namespace' in context['context']:
            self.namespace = context['context']['namespace']
        else:
            self.namespace = 'default'
        self.crds = client.CustomObjectsApi()
        self.core = client.CoreV1Api()
        self.debug = debug
        # try:
        #    hosts = [node.metadata.name for node in self.core.list_node().items]
        # except client.rest.ApiException as e:
        #    common.pprint("Couldn't connect, got %s" % (e.reason), color='red')
        #    os._exit(1)
        # self.host = hosts[0]
        return

    def close(self):
        """

        :return:
        """
        return

    def exists(self, name):
        """

        :param name:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        allvms = crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines')["items"]
        vms = [vm for vm in allvms if vm.get("metadata")["namespace"] == namespace and
               vm.get("metadata")["name"] == name]
        result = True if vms else False
        return result

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace,
                                              'network-attachment-definitions', name)
        except:
            return False
        return True

    def disk_exists(self, pool, name):
        """

        :param pool:
        :param name:
        :return:
        """
        print("not implemented")
        return

    def create(self, name, virttype='kvm', profile='', flavor=None, plan='kvirt', cpumodel='host-model', cpuflags=[],
               numcpus=2, memory=512, guestid='guestrhel764', pool=None, template=None, disks=[{'size': 10}],
               disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[],
               ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[],
               enableroot=True, alias=[], overrides={}, tags=None, dnshost=None):
        """

        :param name:
        :param virttype:
        :param profile:
        :param flavor:
        :param plan:
        :param cpumodel:
        :param cpuflags:
        :param numcpus:
        :param memory:
        :param guestid:
        :param pool:
        :param template:
        :param disks:
        :param disksize:
        :param diskthin:
        :param diskinterface:
        :param nets:
        :param iso:
        :param vnc:
        :param cloudinit:
        :param reserveip:
        :param reservedns:
        :param reservehost:
        :param start:
        :param keys:
        :param cmds:
        :param ips:
        :param netmasks:
        :param gateway:
        :param nested:
        :param dns:
        :param domain:
        :param tunnel:
        :param files:
        :param enableroot:
        :param alias:
        :param overrides:
        :param tags:
        :return:
        """
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        if template is not None and template not in self.volumes():
            if template in ['alpine, cirros', 'fedora-cloud']:
                template = "kubevirt/%s-registry-disk-demo" % template
                common.pprint("Using registry disk %s as template" % template)
            elif template not in REGISTRYDISKS:
                return {'result': 'failure', 'reason': "you don't have template %s" % template}
            if template == 'kubevirt/fedora-cloud-registry-disk-demo' and memory <= 512:
                memory = 1024
        default_disksize = disksize
        default_diskinterface = diskinterface
        default_pool = pool
        crds = self.crds
        core = self.core
        namespace = self.namespace
        allpvc = core.list_namespaced_persistent_volume_claim(namespace)
        templates = {p.metadata.annotations['kcli/template']: p.metadata.name for p in allpvc.items
                     if p.metadata.annotations is not None and 'kcli/template' in p.metadata.annotations}
        vm = {'kind': 'VirtualMachine', 'spec': {'running': start, 'template':
                                                 {'metadata': {'labels': {'kubevirt.io/provider': 'kcli',
                                                                          'kubevirt.io/domain': name}},
                                                  'spec': {'domain': {'resources':
                                                                      {'requests': {'memory': '%sM' % memory}},
                                                                      # 'cpu': {'cores': numcpus, 'model': cpumodel},
                                                                      'cpu': {'cores': numcpus},
                                                                      'devices': {'disks': []}}, 'volumes': []}}},
              'apiVersion': 'kubevirt.io/%s' % VERSION, 'metadata': {'name': name, 'namespace': namespace,
                                                                     'labels': {'kubevirt.io/os': 'linux'},
                                                                     'annotations': {'kcli/plan': plan,
                                                                                     'kcli/profile': profile,
                                                                                     'kcli/template': template}}}
        if dnshost is not None:
            vm['metadata']['annotations']['kcli/dnshost'] = dnshost
        if domain is not None:
            vm['metadata']['annotations']['kcli/domain'] = domain
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
        if tags is not None and isinstance(tags, dict):
            vm['spec']['template']['spec']['nodeSelector'] = tags
        interfaces = []
        networks = []
        for index, net in enumerate(nets):
            newif = {'bridge': {}}
            # newnet = {'pod': {}}
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
            if index > 0:
                if self.multus:
                    newnet['multus'] = {'networkName': netname}
                else:
                    newnet['hostBridge'] = {'bridgeName': netname}
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
            diskname = "disk%s" % index
            volname = "%s-vol%s" % (name, index)
            letter = chr(index + ord('a'))
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
                    volname = disk['name']
                    existingpvc = True
            # myvolume = {'volumeName': volname, 'name': volname}
            myvolume = {'name': volname}
            if template is not None and index == 0:
                if template in REGISTRYDISKS:
                    myvolume['registryDisk'] = {'image': template}
                else:
                    myvolume['persistentVolumeClaim'] = {'claimName': volname}
            if index > 0 or template is None:
                myvolume['persistentVolumeClaim'] = {'claimName': volname}
            newdisk = {'volumeName': volname, 'disk': {'dev': 'vd%s' % letter, 'bus': diskinterface}, 'name': diskname}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec']['template']['spec']['volumes'].append(myvolume)
            if index == 0 and template in REGISTRYDISKS:
                continue
            if existingpvc:
                continue
            diskpool = self.check_pool(pool)
            pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': diskpool,
                                                             'accessModes': ['ReadWriteOnce'],
                                                             'resources': {'requests': {'storage': '%sGi' % disksize}}},
                   'apiVersion': 'v1', 'metadata': {'name': volname}}
            if template is not None and index == 0 and template not in REGISTRYDISKS and self.cdi:
                pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': templates[template]}
            pvcs.append(pvc)
            sizes.append(disksize)
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain,
                             reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides,
                             iso=False)
            cloudinitdata = open('/tmp/user-data', 'r').read().strip()
            cloudinitdisk = {'volumeName': 'cloudinitvolume', 'cdrom': {'readOnly': True, 'bus': 'sata'},
                             'name': 'cloudinitdisk'}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(cloudinitdisk)
            cloudinitvolume = {'cloudInitNoCloud': {'userData': cloudinitdata}, 'name': 'cloudinitvolume'}
            vm['spec']['template']['spec']['volumes'].append(cloudinitvolume)
        if self.debug:
            pretty_print(vm)
        for pvc in pvcs:
            pvcname = pvc['metadata']['name']
            pvcsize = pvc['spec']['resources']['requests']['storage'].replace('Gi', '')
            if template not in REGISTRYDISKS and index == 0:
                if self.cdi:
                    # NOTE: we should also check that cloning finished in this case
                    core.create_namespaced_persistent_volume_claim(namespace, pvc)
                    bound = self.pvc_bound(pvcname, namespace)
                    if not bound:
                        return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % pvcname}
                    completed = self.import_completed(self, pvc, namespace)
                    if completed is None:
                        common.pprint("Issue with cdi import", color='red')
                        return {'result': 'failure', 'reason': 'timeout waiting for cdi importer pod to complete'}
                    else:
                        core.delete_namespaced_pod(completed, namespace, client.V1DeleteOptions())
                    continue
                else:
                    volname = "%s-vol0" % name
                    copy = self.copy_image(diskpool, template, volname)
                    if copy['result'] == 'failure':
                        reason = copy['reason']
                        return {'result': 'failure', 'reason': reason}
                    continue
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(pvcname, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % pvcname}
            prepare = self.prepare_pvc(pvcname, size=pvcsize)
            if prepare['result'] == 'failure':
                reason = prepare['reason']
                return {'result': 'failure', 'reason': reason}
        crds.create_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', vm)
        # except Exception as err:
        #    return {'result': 'failure', 'reason': err}
        return {'result': 'success'}

    def start(self, name):
        """

        :param name:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        common.pprint("Using current namespace %s" % namespace, color='green')
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm['spec']['running'] = True
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return {'result': 'success'}

    def stop(self, name):
        """

        :param name:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        common.pprint("Using current namespace %s" % namespace, color='green')
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm["spec"]['running'] = False
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        """

        :param name:
        :param base:
        :param revert:
        :param delete:
        :param listing:
        :return:
        """
        print("not implemented")
        return

    def restart(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def report(self):
        """

        :return:
        """
        print("not implemented")
        return

    def status(self, name):
        """

        :param name:
        :return:
        """
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
        """

        :return:
        """
        crds = self.crds
        namespace = self.namespace
        vms = []
        for vm in crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines')["items"]:
            metadata = vm.get("metadata")
            name = metadata["name"]
            vms.append(self.info(name, vm=vm))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False):
        """

        :param name:
        :param tunnel:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if find_executable('virtctl') is not None:
            common.pprint("Using local virtctl")
            command = "virtctl vnc %s -n %s" % (name, namespace)
        else:
            common.pprint("Tunneling virtctl through remote host %s. Make sure virtctl is installed there" % self.host,
                          color='blue')
            command = "ssh -o LogLevel=QUIET -Xtp %s %s@%s virtctl vnc %s -n %s" % (self.port, self.user, self.host,
                                                                                    name, namespace)
        if self.debug:
            print(command)
        os.system(command)
        return

    def serialconsole(self, name):
        """

        :param name:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if find_executable('virtctl') is not None:
            common.pprint("Using local virtctl")
            home = os.path.expanduser('~')
            command = "virtctl console --kubeconfig=%s/.kube/config %s -n %s" % (home, name, namespace)
        else:
            common.pprint("Tunneling virtctl through remote host. Make sure virtctl is installed there", color='blue')
            command = "ssh -o LogLevel=QUIET -tp %s %s@%s virtctl console --kubeconfig=.kube/config %s -n %s"\
                % (self.port, self.user, self.host, name, namespace)
        if self.debug:
            print(command)
        os.system(command)
        return

    def dnsinfo(self, name):
        """

        :param name:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        crds = self.crds
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return None, None
        if self.debug:
            pretty_print(vm)
        dnshost, domain = None, None
        metadata = vm.get("metadata")
        annotations = metadata.get("annotations")
        if annotations is not None:
            if 'kcli/dnshost' in annotations:
                dnshost = annotations['kcli/dnshost']
            if 'kcli/domain' in annotations:
                domain = annotations['kcli/domain']
        return dnshost, domain

    def info(self, name, vm=None):
        """

        :param name:
        :param vm:
        :return:
        """
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
        if self.debug:
            pretty_print(vm)
        metadata = vm.get("metadata")
        spec = vm.get("spec")
        running = spec.get("running")
        annotations = metadata.get("annotations")
        spectemplate = vm['spec'].get('template')
        volumes = spectemplate['spec']['volumes']
        name = metadata["name"]
        # creationdate = metadata["creationTimestamp"].strftime("%d-%m-%Y %H:%M")
        creationdate = metadata["creationTimestamp"]
        profile, plan, template = 'N/A', 'N/A', 'N/A'
        if annotations is not None:
            profile = annotations['kcli/profile'] if 'kcli/profile' in annotations else 'N/A'
            plan = annotations['kcli/plan'] if 'kcli/plan' in annotations else 'N/A'
            template = annotations['kcli/template'] if 'kcli/template' in annotations else 'N/A'
        ip = None
        host = None
        if running:
            try:
                runvm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
            except:
                common.pprint("underlying VM %s not found" % name, color='red')
                return {'result': 'failure', 'reason': "underlying VM %s not found" % name}
            status = runvm.get('status')
            if status:
                state = status.get('phase').replace('Running', 'up')
                host = status['nodeName'] if 'nodeName' in status else None
                if 'interfaces' in status:
                    interfaces = runvm['status']['interfaces']
                    for interface in interfaces:
                        if 'ipAddress' in interface:
                            ip = interface['ipAddress']
                            break
        else:
            state = 'down'
        yamlinfo = {'name': name, 'nets': [], 'disks': [], 'state': state, 'creationdate': creationdate, 'host': host,
                    'status': state, 'report': namespace}
        if 'cpu' in spectemplate['spec']['domain']:
            numcpus = spectemplate['spec']['domain']['cpu']['cores']
            yamlinfo['cpus'] = numcpus
        if 'resources' in spectemplate['spec']['domain'] and 'requests' in spectemplate['spec']['domain']['resources']:
            memory = spectemplate['spec']['domain']['resources']['requests']['memory']
            yamlinfo['memory'] = memory
        if template is not None:
            yamlinfo['template'] = template
        if ip is not None:
            yamlinfo['ip'] = ip
        if plan is not None:
            yamlinfo['plan'] = plan
        if profile is not None:
            yamlinfo['profile'] = profile
        plaindisks = spectemplate['spec']['domain']['devices']['disks']
        disks = []
        for d in plaindisks:
            bus = 'N/A'
            if 'disk' in d:
                bus = d['disk'].get('bus', 'N/A')
            volumename = d['volumeName']
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
            elif 'registryDisk' in volumeinfo:
                _type = 'registrydisk'
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
            mac = interface['macAddress'] = interface['mac'] if 'mac' in interface else 'N/A'
            if 'multus' in net:
                network = net['multus']['networkName']
                network_type = 'multus'
            elif 'hostBridge' in net:
                network = net['hostBridge']['bridgeName']
                network_type = 'hostbridge'
            else:
                network = 'default'
                network_type = 'pod'
            yamlinfo['nets'].append({'device': device, 'mac': mac, 'net': network, 'type': network_type})
        return yamlinfo

    def ip(self, name):
        """

        :param name:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        ip = None
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachineinstances', name)
            status = vm['status']
            if 'interfaces' in status:
                interfaces = vm['status']['interfaces']
                for interface in interfaces:
                    if 'ipAddress' in interface:
                        ip = interface['ipAddress']
                        break
        except Exception:
            common.pprint("VM %s not found" % name, color='red')
            # return {'result': 'failure', 'reason': "VM %s not found" % name}
            os._exit(1)
        return ip

    def volumes(self, iso=False):
        """

        :param iso:
        :return:
        """
        core = self.core
        namespace = self.namespace
        if iso:
            return []
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        templates = [p.metadata.annotations['kcli/template'] for p in pvc.items
                     if p.metadata.annotations is not None and 'kcli/template' in p.metadata.annotations]
        if templates:
            return sorted(templates)
        else:
            common.pprint("No pvc based templates found, defaulting to registry disks", color='blue')
            return REGISTRYDISKS

    def delete(self, name, snapshots=False):
        """

        :param name:
        :param snapshots:
        :return:
        """
        crds = self.crds
        core = self.core
        namespace = self.namespace
        common.pprint("Using current namespace %s" % namespace, color='green')
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except Exception as e:
            return {'result': 'failure', 'reason': e}
        try:
            crds.delete_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name,
                                                 client.V1DeleteOptions())
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        volumes = [d['volumeName'] for d in vm['spec']['template']['spec']['domain']['devices']['disks']
                   if d['volumeName'] != 'cloudinitdisk']
        pvcs = [pvc for pvc in core.list_namespaced_persistent_volume_claim(namespace).items
                if pvc.metadata.name in volumes]
        for p in sorted(pvcs):
            pvcname = p.metadata.name
            print("Deleting pvc %s" % pvcname)
            core.delete_namespaced_persistent_volume_claim(pvcname, namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        """

        :param old:
        :param new:
        :param full:
        :param start:
        :return:
        """
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue):
        """

        :param name:
        :param metatype:
        :param metavalue:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm["metadata"]["annotations"]["kcli/%s" % metatype] = metavalue
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def update_memory(self, name, memory):
        """

        :param name:
        :param memory:
        :return:
        """
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
        common.pprint("Change will only appear next full lifeclyclereboot", color='blue')
        return

    def update_cpu(self, name, numcpus):
        """

        :param name:
        :param numcpus:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['cpu']['cores'] = int(numcpus)
        common.pprint("Change will only appear next full lifeclyclereboot", color='blue')
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def update_start(self, name, start=True):
        """

        :param name:
        :param start:
        :return:
        """
        print("not implemented")
        return

    def update_information(self, name, information):
        """

        :param name:
        :param information:
        :return:
        """
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        """

        :param name:
        :param iso:
        :return:
        """
        print("not implemented")
        return

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param template:
        :return:
        """
        core = self.core
        namespace = self.namespace
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        templates = {p.metadata.annotations['kcli/template']: p.metadata.name for p in pvc.items
                     if p.metadata.annotations is not None and 'kcli/template' in p.metadata.annotations}
        try:
            pvc = core.read_namespaced_persistent_volume(name, namespace)
            common.pprint("Disk %s already there" % name, color='red')
            return 1
        except:
            pass
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'accessModes': ['ReadWriteOnce'],
                                                         'resources': {'requests': {'storage': '%sGi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': name}}
        if template is not None:
            pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': templates[template]}
        core.create_namespaced_persistent_volume_claim(namespace, pvc)
        return

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param template:
        :param shareable:
        :param existing:
        :return:
        """
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
        volname = '%s-vol%d' % (name, index)
        diskname = 'disk%d' % index
        self.create_disk(volname, size=size, pool=pool, thin=thin, template=template)
        bound = self.pvc_bound(volname, namespace)
        if not bound:
            return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % volname}
        prepare = self.prepare_pvc(volname, size=size)
        if prepare['result'] == 'failure':
            reason = prepare['reason']
            return {'result': 'failure', 'reason': reason}
        myvolume = {'name': volname, 'persistentVolumeClaim': {'claimName': volname}}
        newdisk = {'volumeName': volname, 'name': diskname}
        vm['spec'][t]['spec']['domain']['devices']['disks'].append(newdisk)
        vm['spec'][t]['spec']['volumes'].append(myvolume)
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def delete_disk(self, name=None, diskname=None, pool=None):
        """

        :param name:
        :param diskname:
        :param pool:
        :return:
        """
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
        volname = vm['spec'][t]['spec']['domain']['devices']['disks'][diskindex]['volumeName']
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
        """

        :return:
        """
        disks = {}
        namespace = self.namespace
        core = self.core
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        for p in pvc.items:
            metadata = p.metadata
            annotations = p.metadata.annotations
            if annotations is not None and 'kcli/template' in annotations:
                continue
            else:
                name = metadata.name
                storageclass = p.spec.storage_class_name
                pv = p.spec.volume_name
                disks[name] = {'pool': storageclass, 'path': pv}
        return disks

    def add_nic(self, name, network):
        """

        :param name:
        :param network:
        :return:
        """
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        """

        :param name:
        :param interface:
        :return:
        """
        print("not implemented")
        return

    def _ssh_credentials(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        metadata = vm.get("metadata")
        annotations = metadata.get("annotations")
        template = annotations.get('kcli/template') if annotations is not None else None
        user = 'root'
        ip = self.ip(name)
        if template is not None:
            if 'centos' in template.lower():
                user = 'centos'
            elif 'cirros' in template.lower():
                user = 'cirros'
            elif [x for x in common.ubuntus if x in template.lower()]:
                user = 'ubuntu'
            elif 'fedora' in template.lower():
                user = 'fedora'
            elif 'rhel' in template.lower():
                user = 'cloud-user'
            elif 'debian' in template.lower():
                user = 'debian'
            elif 'arch' in template.lower():
                user = 'arch'
        return user, ip

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, Y=False,
            D=None):
        """

        :param name:
        :param user:
        :param local:
        :param remote:
        :param tunnel:
        :param insecure:
        :param cmd:
        :param X:
        :param Y:
        :param D:
        :return:
        """
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        # tunnel = True if 'TUNNEL' in os.environ and os.environ('TUNNEL').lower() == 'true' else False
        sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=user, local=local,
                                remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, Y=Y, D=D,
                                debug=self.debug)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        """

        :param name:
        :param user:
        :param source:
        :param destination:
        :param tunnel:
        :param download:
        :param recursive:
        :return:
        """
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        tunnel = True if 'TUNNEL' in os.environ and os.environ('TUNNEL').lower() == 'true' else False
        scpcommand = common.scp(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=user,
                                source=source, destination=destination, recursive=recursive, tunnel=tunnel,
                                debug=self.debug, download=download)
        return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        """

        :param name:
        :param poolpath:
        :param pooltype:
        :param user:
        :param thinpool:
        :return:
        """
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        """

        :param image:
        :param pool:
        :param short:
        :param cmd:
        :param name:
        :param size:
        :return:
        """
        sizes = {'debian': 2, 'centos': 8, 'fedora': 4, 'rhel': 10, 'trusty': 2.2, 'xenial': 2.2, 'yakkety': 2.2,
                 'zesty': 2.2, 'artful': 2.2}
        core = self.core
        pool = self.check_pool(pool)
        namespace = self.namespace
        shortimage = os.path.basename(image).split('?')[0]
        if name is None:
            volname = [k for k in TEMPLATES if TEMPLATES[k] == image][0]
        else:
            volname = name.replace('_', '-').replace('.', '-').lower()
        for key in sizes:
            if key in shortimage and shortimage.endswith('qcow2'):
                size = sizes[key]
                break
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        podname = '%s-%s-importer' % (now, volname)
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool,
                                                         'accessModes': ['ReadWriteOnce'],
                                                         'resources': {'requests': {'storage': '%sGi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': volname, 'annotations': {'kcli/template': shortimage}}}
        if self.cdi:
                pvc['metadata']['annotations'] = {'cdi.kubevirt.io/storage.import.endpoint': image}
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
        if self.cdi:
            completed = self.import_completed(self, volname, namespace)
            if completed is None:
                common.pprint("Issue with cdi import", color='red')
                return {'result': 'failure', 'reason': 'timeout waiting for cdi importer pod to complete'}
            else:
                core.delete_namespaced_pod(completed, namespace, client.V1DeleteOptions())
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
        """

        :param pool:
        :param ori:
        :param dest:
        :param size:
        :return:
        """
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
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool, 'accessModes': ['ReadWriteOnce'],
                                                         'resources': {'requests': {'storage': '%sMi' % size}}},
               'apiVersion': 'v1', 'metadata': {'name': dest}}
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never',
                                       'containers': [{'image': 'alpine', 'volumeMounts': [{'mountPath': '/storage1',
                                                                                            'name': 'storage1'},
                                                                                           {'mountPath': '/storage2',
                                                                                            'name': 'storage2'}],
                                                       'name': 'copy', 'command': ['cp'], 'args': ['/storage1/disk.img',
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

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None, vlan=None):
        """

        :param name:
        :param cidr:
        :param dhcp:
        :param nat:
        :param domain:
        :param plan:
        :param pxe:
        :param vlan:
        :return:
        """
        crds = self.crds
        namespace = self.namespace
        bridge = cidr
        apiversion = "%s/%s" % (MULTUSDOMAIN, MULTUSVERSION)
        vlanconfig = '"vlan": %s' % vlan if vlan is not None else ''
        config = '{ "cniVersion": "0.3.1", "type": "ovs", "bridge": "%s" %s}' % (bridge, vlanconfig)
        network = {'kind': 'NetworkAttachmentDefinition', 'spec': {'config': config}, 'apiVersion': apiversion,
                   'metadata': {'name': name}}
        crds.create_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace, 'network-attachment-definitions',
                                             network)
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        """

        :param name:
        :param cidr:
        :return:
        """
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
        """

        :return:
        """
        storageapi = client.StorageV1Api()
        pools = [x.metadata.name for x in storageapi.list_storage_class().items]
        return pools

    def list_networks(self):
        """

        :return:
        """
        networks = {}
        if self.multus:
            crds = self.crds
            namespace = self.namespace
            nafs = crds.list_namespaced_custom_object(MULTUSDOMAIN, MULTUSVERSION, namespace,
                                                      'network-attachment-definitions')["items"]
            for naf in nafs:
                config = literal_eval(naf['spec']['config'])
                name = naf['metadata']['name']
                _type = config['type']
                bridge = config['bridge']
                vlan = config.get('vlan', 'N/A')
                networks[name] = {'cidr': bridge, 'dhcp': 'N/A', 'type': _type, 'mode': vlan}
            return networks
        else:
            return {'default': {'cidr': 'N/A', 'dhcp': 'N/A', 'type': 'bridged', 'mode': 'N/A'}}

    def list_subnets(self):
        """

        :return:
        """
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        """

        :param name:
        :param full:
        :return:
        """
        print("not implemented")
        return

    def network_ports(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

    def vm_ports(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

    def get_pool_path(self, pool):
        """

        :param pool:
        :return:
        """
        storageapi = client.StorageV1Api()
        storageclass = storageapi.read_storage_class(pool)
        return storageclass.provisioner

    def pvc_bound(self, volname, namespace):
        """

        :param volname:
        :param namespace:
        :return:
        """
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
        """

        :param volname:
        :param namespace:
        :return:
        """
        core = self.core
        pvctimeout = 40
        pvcruntime = 0
        phase = ''
        while phase != 'Succeeded':
            if pvcruntime >= pvctimeout:
                return None
            pvc = core.read_namespaced_persistent_volume_claim(volname, namespace)
            pod = pvc.metadata.annotations['cdi.kubevirt.io/storage.import.importPodName']
            phase = pvc.metadata.annotations['cdi.kubevirt.io/storage.import.pod.phase']
            time.sleep(2)
            common.pprint("Waiting for import to complete...")
            pvcruntime += 2
        return pod

    def pod_completed(self, podname, namespace):
        """

        :param podname:
        :param namespace:
        :return:
        """
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
        """

        :param name:
        :param size:
        :return:
        """
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
        """

        :param pool:
        :return:
        """
        storage = client.StorageV1Api()
        storageclasses = storage.list_storage_class().items
        if storageclasses:
            storageclasses = [s.metadata.name for s in storageclasses]
            if pool in storageclasses:
                return pool
        common.pprint("Pool %s not found. Using None" % pool, color='blue')
        return None

    def flavors(self):
        """

        :return:
        """
        return []
