#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kubevirt class
"""

from kubernetes import client, config
from kvirt import common
from kvirt.defaults import TEMPLATES
import base64
import datetime
from distutils.spawn import find_executable
import os
import time
import yaml
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "kubevirt.io"
VERSION = 'v1alpha1'
REGISTRYDISKS = ['kubevirt/alpine-registry-disk-demo', 'kubevirt/cirros-registry-disk-demo', 'kubevirt/fedora-cloud-registry-disk-demo']


def pretty_print(o):
    print yaml.dump(o, default_flow_style=False, indent=2, allow_unicode=True, encoding='utf-8').replace('!!python/unicode ', '').replace("'", '')


class Kubevirt(object):
    def __init__(self, context=None, usecloning=False, host='127.0.0.1', port=22, user='root', debug=False, tags={}):
        self.host = host
        self.port = port
        self.user = user
        self.usecloning = usecloning
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
        configuration = client.Configuration()
        configuration.assert_hostname = False
        if 'namespace' in context['context']:
            self.namespace = context['context']['namespace']
        else:
            self.namespace = 'default'
        self.crds = client.CustomObjectsApi()
        extensions = client.ApiextensionsV1beta1Api()
        current_crds = [x for x in extensions.list_custom_resource_definition().to_dict()['items'] if x['spec']['names']['kind'].lower() == 'offlinevirtualmachine']
        if not current_crds:
            common.pprint("Kubevirt not installed", color='red')
            self.conn = None
            self.host = context
            return
        self.core = client.CoreV1Api()
        self.debug = debug
        if host == '127.0.0.1' and len(contextname.split('/')) == 3 and len(contextname.split('/')[1].split(':')) == 2:
            self.host = contextname.split('/')[1].split(':')[0].replace('-', '.')
        return

    def close(self):
        return

    def exists(self, name):
        crds = self.crds
        namespace = self.namespace
        allvms = crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines')["items"]
        vms = [vm for vm in allvms if vm.get("metadata")["namespace"] == namespace and vm.get("metadata")["name"] == name]
        result = True if vms else False
        return result

    def net_exists(self, name):
        print("not implemented")
        return True

    def disk_exists(self, pool, name):
        print("not implemented")
        return

    def create(self, name, virttype='kvm', profile='', plan='kvirt', cpumodel='q35', cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool=None, template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}, tags={}):
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        if template is not None and template not in self.volumes() and template not in REGISTRYDISKS:
            return {'result': 'failure', 'reason': "you don't have template %s" % template}
        default_disksize = disksize
        default_diskinterface = diskinterface
        default_pool = pool
        crds = self.crds
        core = self.core
        namespace = self.namespace
        allpvc = core.list_namespaced_persistent_volume_claim(namespace)
        templates = {p.metadata.annotations['kcli/template']: p.metadata.name for p in allpvc.items if p.metadata.annotations is not None and 'kcli/template' in p.metadata.annotations}
        vm = {'kind': 'OfflineVirtualMachine', 'spec': {'running': start, 'template': {'metadata': {'labels': {'kubevirt.io/provider': 'kcli'}}, 'spec': {'domain': {'resources': {'requests': {'memory': '%sM' % memory}}, 'cpu': {'cores': numcpus}, 'devices': {'disks': []}}, 'volumes': []}}}, 'apiVersion': 'kubevirt.io/v1alpha1', 'metadata': {'name': name, 'namespace': namespace, 'annotations': {'kcli/plan': plan, 'kcli/profile': profile, 'kcli/template': template}}}
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
            vm['spec']['template']['spec']['nodeSelector'] = tags
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
            pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': diskpool, 'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '%sGi' % disksize}}}, 'apiVersion': 'v1', 'metadata': {'name': volname}}
            if template is not None and index == 0 and template not in REGISTRYDISKS and self.usecloning:
                pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': templates[template]}
            pvcs.append(pvc)
            sizes.append(disksize)
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain, reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides, iso=False)
            cloudinitdata = open('/tmp/user-data', 'r').read()
            cloudinitdisk = {'volumeName': 'cloudinitvolume', 'cdrom': {'readOnly': True}, 'name': 'cloudinitdisk'}
            vm['spec']['template']['spec']['domain']['devices']['disks'].append(cloudinitdisk)
            cloudinitencoded = base64.b64encode(cloudinitdata)
            cloudinitvolume = {'cloudInitNoCloud': {'userDataBase64': cloudinitencoded}, 'name': 'cloudinitvolume'}
            vm['spec']['template']['spec']['volumes'].append(cloudinitvolume)
        if self.debug:
            pretty_print(vm)
        for pvc in pvcs:
            pvcname = pvc['metadata']['name']
            pvcsize = pvc['spec']['resources']['requests']['storage'].replace('Gi', '')
            if template not in REGISTRYDISKS and index == 0:
                if self.usecloning:
                    # NOTE: we should also check that cloning finished in this case
                    core.create_namespaced_persistent_volume_claim(namespace, pvc)
                    bound = self.pvc_bound(pvcname, namespace)
                    if not bound:
                        return {'result': 'failure', 'reason': 'timeout waiting for pvc %s to get bound' % pvcname}
                    continue
                else:
                    volname = "%s-vol0" % (name)
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
        crds.create_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', vm)
        # except Exception as err:
        #    return {'result': 'failure', 'reason': err}
        return {'result': 'success'}

    def start(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm['spec']['running'] = True
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "offlinevirtualmachines", name, vm)
        return {'result': 'success'}

    def stop(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm["spec"]['running'] = False
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "offlinevirtualmachines", name, vm)
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")
        return

    def restart(self, name):
        print("not implemented")
        return {'result': 'success'}

    def report(self):
        print("not implemented")
        return

    def status(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except Exception:
            return None
        allvms = crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines')["items"]
        vms = [vm for vm in allvms if 'labels' in vm.get("metadata") and 'kubevirt-ovm' in vm["metadata"]['labels'] and vm["metadata"]['labels']['kubevirt-ovm'] == name]
        if vms:
            return 'up'
        return 'down'

    def list(self):
        crds = self.crds
        namespace = self.namespace
        vms = []
        for vm in crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines')["items"]:
            metadata = vm.get("metadata")
            spec = vm.get("spec")
            annotations = metadata.get("annotations")
            running = spec.get("running")
            name = metadata["name"]
            profile, plan, source = 'N/A', 'N/A', 'N/A'
            if annotations is not None:
                profile = annotations['kcli/profile'] if 'kcli/profile' in annotations else 'N/A'
                plan = annotations['kcli/plan'] if 'kcli/plan' in annotations else 'N/A'
                source = annotations['kcli/template'] if 'kcli/template' in annotations else 'N/A'
            report = 'N/A'
            ip = 'N/A'
            state = 'down'
            if running:
                try:
                    runvm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
                except:
                    common.pprint("underlying VM %s not found" % name, color='red')
                    runvm = {}
                status = runvm.get('status')
                if status:
                    state = status['phase'].replace('Running', 'up')
                    if 'interfaces' in status:
                        interfaces = runvm['status']['interfaces']
                        for interface in interfaces:
                            if 'ipAddress' in interface:
                                ip = interface['ipAddress']
                                break
            vms.append([name, state, ip, source, plan, profile, report])
        return vms

    def console(self, name, tunnel=False):
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if find_executable('virtctl') is not None:
            home = os.path.expanduser('~')
            command = "virtctl vnc --kubeconfig=%s/.kube/config %s -n %s" % (home, name, namespace)
        else:
            common.pprint("Tunneling virtctl through remote host %s. Make sure virtctl is installed there" % self.host, color='blue')
            command = "ssh -o LogLevel=QUIET -Xtp %s %s@%s virtctl vnc --kubeconfig=.kube/config %s -n %s" % (self.port, self.user, self.host, name, namespace)
        if self.debug:
            print(command)
        os.system(command)
        return

    def serialconsole(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if find_executable('virtctl') is not None:
            home = os.path.expanduser('~')
            command = "virtctl console --kubeconfig=%s/.kube/config %s -n %s" % (home, name, namespace)
        else:
            common.pprint("Tunneling virtctl through remote host. Make sure virtctl is installed there", color='blue')
            command = "ssh -o LogLevel=QUIET -tp %s %s@%s virtctl console --kubeconfig=.kube/config %s -n %s" % (self.port, self.user, self.host, name, namespace)
        if self.debug:
            print(command)
        os.system(command)
        return

    def info(self, name, output='plain', fields=None, values=False):
        if fields is not None:
            fields = fields.split(',')
        yamlinfo = {}
        core = self.core
        crds = self.crds
        namespace = self.namespace
        crds = self.crds
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
                runvm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
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
        yamlinfo = {'name': name, 'nets': [], 'disks': [], 'state': state, 'creationdate': creationdate, 'host': host, 'status': state}
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
        common.print_info(yamlinfo, output=output, fields=fields, values=values)
        return {'result': 'success'}

    def ip(self, name):
        crds = self.crds
        namespace = self.namespace
        ip = None
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
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
        core = self.core
        namespace = self.namespace
        if iso:
            return []
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        templates = [p.metadata.annotations['kcli/template'] for p in pvc.items if p.metadata.annotations is not None and 'kcli/template' in p.metadata.annotations]
        if templates:
            return sorted(templates)
        else:
            common.pprint("No pvc based templates found, defaulting to registry disks", color='blue')
            return REGISTRYDISKS

    def delete(self, name, snapshots=False):
        crds = self.crds
        core = self.core
        namespace = self.namespace
        crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        try:
            crds.delete_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name, client.V1DeleteOptions())
        except:
            pass
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except Exception as e:
            return {'result': 'failure', 'reason': e}
        try:
            crds.delete_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name, client.V1DeleteOptions())
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        volumes = [d['volumeName'] for d in vm['spec']['template']['spec']['domain']['devices']['disks'] if d['volumeName'] != 'cloudinitdisk']
        pvcs = [pvc for pvc in core.list_namespaced_persistent_volume_claim(namespace).items if pvc.metadata.name in volumes]
        for p in sorted(pvcs):
            pvcname = p.metadata.name
            print("Deleting pvc %s" % pvcname)
            core.delete_namespaced_persistent_volume_claim(pvcname, namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm["metadata"]["annotations"]["kcli/%s" % metatype] = metavalue
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "offlinevirtualmachines", name, vm)
        return

    def update_memory(self, name, memory):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['resources']['requests']['memory'] = "%sM" % memory
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "offlinevirtualmachines", name, vm)
        common.pprint("Change will only appear next full lifeclyclereboot", color='blue')
        return

    def update_cpu(self, name, numcpus):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        vm['spec'][t]['spec']['domain']['cpu']['cores'] = int(numcpus)
        common.pprint("Change will only appear next full lifeclyclereboot", color='blue')
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "offlinevirtualmachines", name, vm)
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

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        core = self.core
        namespace = self.namespace
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        templates = {p.metadata.annotations['kcli/template']: p.metadata.name for p in pvc.items if p.metadata.annotations is not None and 'kcli/template' in p.metadata.annotations}
        try:
            pvc = core.read_namespaced_persistent_volume(name, namespace)
            common.pprint("Disk %s already there" % name, color='red')
            return 1
        except:
            pass
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool, 'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '%sGi' % size}}}, 'apiVersion': 'v1', 'metadata': {'name': name}}
        if template is not None:
            pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': templates[template]}
        core.create_namespaced_persistent_volume_claim(namespace, pvc)
        return

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        currentdisks = [disk for disk in vm['spec'][t]['spec']['domain']['devices']['disks'] if disk['name'] != 'cloudinitdisk']
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
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "offlinevirtualmachines", name, vm)
        return

    def delete_disk(self, name, diskname):
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        t = 'Template' if 'Template' in vm['spec'] else 'template'
        diskindex = [i for i, disk in enumerate(vm['spec'][t]['spec']['domain']['devices']['disks']) if disk['name'] == diskname]
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
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "offlinevirtualmachines", name, vm)
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
            if annotations is not None and 'kcli/template' in annotations:
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

    def _ssh_credentials(self, name):
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'offlinevirtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        metadata = vm.get("metadata")
        annotations = metadata.get("annotations")
        template = annotations.get('kcli/template')
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        ip = self.ip(name)
        if template is not None:
            if 'centos' in template.lower():
                user = 'centos'
            elif 'cirros' in template.lower():
                user = 'cirros'
            elif [x for x in ubuntus if x in template.lower()]:
                user = 'ubuntu'
            elif 'fedora' in template.lower():
                user = 'fedora'
            elif 'rhel' in template.lower():
                user = 'cloud-user'
            elif 'debian' in template.lower():
                user = 'debian'
            elif 'arch' in template.lower():
                user = 'arch'
        return (user, ip)

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, D=None):
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        tunnel = True
        sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=user, local=local, remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, debug=self.debug, D=D)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        tunnel = True
        scpcommand = common.scp(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=user, source=source, destination=destination, recursive=recursive, tunnel=tunnel, debug=self.debug, download=download)
        return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        sizes = {'debian': 2, 'centos': 8, 'fedora': 4, 'rhel': 10, 'trusty': 2.2, 'xenial': 2.2, 'yakkety': 2.2, 'zesty': 2.2, 'artful': 2.2}
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
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool, 'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '%sGi' % size}}}, 'apiVersion': 'v1', 'metadata': {'name': volname, 'annotations': {'kcli/template': shortimage}}}
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never', 'containers': [{'image': 'kubevirtci/disk-importer', 'volumeMounts': [{'mountPath': '/storage', 'name': 'storage1'}], 'name': 'importer', 'env': [{'name': 'CURL_OPTS', 'value': '-L'}, {'name': 'INSTALL_TO', 'value': '/storage/disk.img'}, {'name': 'URL', 'value': image}]}], 'volumes': [{'name': 'storage1', 'persistentVolumeClaim': {'claimName': volname}}]}, 'apiVersion': 'v1', 'metadata': {'name': podname}}
        try:
            core.read_namespaced_persistent_volume_claim(volname, namespace)
            common.pprint("Using existing pvc")
        except:
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            bound = self.pvc_bound(volname, namespace)
            if not bound:
                return {'result': 'failure', 'reason': 'timeout waiting for pvc to get bound'}
        core.create_namespaced_pod(namespace, pod)
        completed = self.pod_completed(podname, namespace)
        if not completed:
            common.pprint("Issue with pod %s. Leaving it for debugging purposes" % podname, color='red')
            return {'result': 'failure', 'reason': 'timeout waiting for importer pod to complete'}
        else:
            core.delete_namespaced_pod(podname, namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def copy_image(self, pool, ori, dest, size=1):
        sizes = {'debian': 2, 'centos': 8, 'fedora': 4, 'rhel': 10, 'trusty': 2.2, 'xenial': 2.2, 'yakkety': 2.2, 'zesty': 2.2, 'artful': 2.2}
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
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool, 'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '%sMi' % size}}}, 'apiVersion': 'v1', 'metadata': {'name': dest}}
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never', 'containers': [{'image': 'alpine', 'volumeMounts': [{'mountPath': '/storage1', 'name': 'storage1'}, {'mountPath': '/storage2', 'name': 'storage2'}], 'name': 'copy', 'command': ['cp'], 'args': ['/storage1/disk.img', '/storage2']}], 'volumes': [{'name': 'storage1', 'persistentVolumeClaim': {'claimName': ori}}, {'name': 'storage2', 'persistentVolumeClaim': {'claimName': dest}}]}, 'apiVersion': 'v1', 'metadata': {'name': podname}}
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

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None):
        print("not implemented")
        return

    def delete_network(self, name=None):
        print("not implemented")
        return

    def list_pools(self):
        storageapi = client.StorageV1Api()
        pools = [x.metadata.name for x in storageapi.list_storage_class().items]
        return pools

    def list_networks(self):
        print("not implemented")
        return

    def delete_pool(self, name, full=False):
        print("not implemented")
        return

    def network_ports(self, name):
        print("not implemented")
        return

    def vm_ports(self, name):
        print("not implemented")
        return

    def get_pool_path(self, pool):
        storageapi = client.StorageV1Api()
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
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'OnFailure', 'containers': [{'image': 'alpine', 'volumeMounts': [{'mountPath': '/storage1', 'name': 'storage1'}], 'name': 'prepare', 'command': ['fallocate'], 'args': ['-l', '%sM' % size, '/storage1/disk.img']}], 'volumes': [{'name': 'storage1', 'persistentVolumeClaim': {'claimName': name}}]}, 'apiVersion': 'v1', 'metadata': {'name': podname}}
        core.create_namespaced_pod(namespace, pod)
        completed = self.pod_completed(podname, namespace)
        if not completed:
            common.pprint("Using with pod %s. Leaving it for debugging purposes" % podname, color='red')
            return {'result': 'failure', 'reason': 'timeout waiting for preparation of disk to finish'}
        else:
            core.delete_namespaced_pod(podname, namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def check_pool(self, pool):
        storage = client.StorageV1Api()
        storageclasses = storage.list_storage_class().items
        if storageclasses:
            storageclasses = [s.metadata.name for s in storageclasses]
            if pool in storageclasses:
                return pool
        common.pprint("Pool %s not found. Using None" % pool, color='blue')
        return None
