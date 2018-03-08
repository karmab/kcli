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
    def __init__(self, context=None, pvctemplate=False, host='127.0.0.1', port=22, user='root', debug=False):
        self.conn = 'OK'
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
        self.namespace = context['context']['namespace']
        self.crds = client.CustomObjectsApi()
        extensions = client.ApiextensionsV1beta1Api()
        current_crds = [x for x in extensions.list_custom_resource_definition().to_dict()['items'] if x['spec']['names']['kind'].lower() == 'virtualmachine']
        if 'virtualmachine' not in current_crds:
            common.pprint("Kubevirt not installed", color='red')
            self.conn = None
            self.host = context
            return
        self.core = client.CoreV1Api()
        self.debug = debug
        if host == '127.0.0.1' and len(contextname.split('/')) == 3 and len(contextname.split('/')[1].split(':')) == 2:
            host = contextname.split('/')[1].split(':')[0].replace('-', '.')
        self.host = host
        self.port = port
        self.user = user
        self.pvctemplate = pvctemplate
        return

    def close(self):
        return

    def exists(self, name):
        crds = self.crds
        namespace = self.namespace
        allvms = crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines')["items"]
        vms = [vm for vm in allvms if vm.get("metadata")["namespace"] == namespace and vm.get("metadata")["name"] == name]
        result = True if vms else False
        return result

    def net_exists(self, name):
        print("not implemented")
        return

    def disk_exists(self, pool, name):
        print("not implemented")
        return

    def create(self, name, virttype='kvm', profile='', plan='kvirt', cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512, guestid='guestrhel764', pool=None, template=None, disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[], enableroot=True, alias=[], overrides={}):
        print(pool)
        # default_diskinterface = diskinterface
        # default_diskthin = diskthin
        default_disksize = disksize
        default_pool = pool
        crds = self.crds
        core = self.core
        namespace = self.namespace
        if self.pvctemplate:
            pvc = core.list_namespaced_persistent_volume_claim(namespace)
            templates = {p.metadata.annotations['kcli/template']: p.metadata.name for p in pvc.items if 'kcli/template' in p.metadata.annotations}
        vm = {'kind': 'VirtualMachine', 'spec': {'terminationGracePeriodSeconds': 0, 'domain': {'resources': {'requests': {'memory': "%sM" % memory}}, 'devices': {'disks': []}}, 'volumes': []}, 'apiVersion': 'kubevirt.io/v1alpha1', 'metadata': {'namespace': namespace, 'name': name, 'annotations': {'kcli/plan': plan, 'kcli/profile': profile, 'kcli/template': template}}}
        pvcs = []
        for index, disk in enumerate(disks):
            diskname = "disk%s" % index
            volname = "%s-vol%s" % (name, index)
            letter = chr(index + ord('a'))
            if disk is None:
                disksize = default_disksize
                diskpool = default_pool
            elif isinstance(disk, int):
                disksize = disk
                diskpool = default_pool
            elif isinstance(disk, dict):
                disksize = disk.get('size', default_disksize)
                diskpool = disk.get('pool', default_pool)
                # diskthin = disk.get('thin', default_diskthin)
                # diskinterface = disk.get('interface', default_diskinterface)
            # myvolume = {'volumeName': volname, 'registryDisk': {'image': template}, 'name': volname}
            myvolume = {'volumeName': volname, 'name': volname}
            if template is not None and index == 0:
                if self.pvctemplate:
                    myvolume['persistentVolumeClaim'] = {'claimName': volname}
                else:
                    myvolume['registryDisk'] = {'image': template}
            if index > 0 or template is None:
                myvolume['persistentVolumeClaim'] = {'claimName': volname}
            newdisk = {'volumeName': volname, 'disk': {'dev': 'vd%s' % letter}, 'name': diskname}
            vm['spec']['domain']['devices']['disks'].append(newdisk)
            vm['spec']['volumes'].append(myvolume)
            if not self.pvctemplate and index == 0:
                continue
            pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': diskpool, 'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '%sGi' % disksize}}}, 'apiVersion': 'v1', 'metadata': {'name': volname}}
            if template is not None and index == 0 and self.pvctemplate:
                pvc['metadata']['annotations'] = {'k8s.io/CloneRequest': templates[template]}
            pvcs.append(pvc)
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain, reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides, iso=False)
            cloudinitdata = open('/tmp/user-data', 'r').read()
            cloudinitdisk = {'volumeName': 'cloudinitvolume', 'cdrom': {'readOnly': True}, 'name': 'cloudinitdisk'}
            # letter = chr(index + 1 + ord('a'))
            # cloudinitdisk = {'volumeName': 'cloudinitvolume', 'disk': {'dev': 'vd%s' % letter}, 'name': 'cloudinitdisk'}
            vm['spec']['domain']['devices']['disks'].append(cloudinitdisk)
            cloudinitencoded = base64.b64encode(cloudinitdata)
            cloudinitvolume = {'cloudInitNoCloud': {'userDataBase64': cloudinitencoded}, 'name': 'cloudinitvolume'}
            vm['spec']['volumes'].append(cloudinitvolume)
        if self.debug:
            pretty_print(vm)
        try:
            for pvc in pvcs:
                core.create_namespaced_persistent_volume_claim(namespace, pvc)
                if self.pvctemplate and index == 0:
                    common.pprint("Waiting 15 seconds for pvc to be bound")
                    time.sleep(15)
            crds.create_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', vm)
        except Exception as err:
            return {'result': 'failure', 'reason': err}
        return {'result': 'success'}

    def start(self, name):
        print("not implemented")
        return {'result': 'success'}

    def stop(self, name):
        self.delete(name)
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
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
            return vm['status']['phase']
        except Exception as err:
            return err
        return

    def list(self):
        crds = self.crds
        namespace = self.namespace
        vms = []
        for vm in crds.list_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines')["items"]:
            metadata = vm.get("metadata")
            annotations = metadata.get("annotations")
            name = metadata["name"]
            status = vm['status']
            state = status['phase']
            source = 'N/A'
            profile = annotations.get('kcli/profile', 'N/A')
            plan = annotations.get('kcli/plan', 'N/A')
            source = annotations.get('kcli/template')
            report = 'N/A'
            ip = 'N/A'
            if 'interfaces' in status:
                interfaces = vm['status']['interfaces']
                for interface in interfaces:
                    if 'ipAddress' in interface:
                        ip = interface['ipAddress']
                        break
            vms.append([name, state, ip, source, plan, profile, report])
        return vms

    def console(self, name, tunnel=False):
        namespace = self.namespace
        serialcommand = "ssh -Xtp %s %s@%s virtctl vnc --kubeconfig=.kube/config %s -n %s" % (self.port, self.user, self.host, name, namespace)
        os.system(serialcommand)
        return

    def serialconsole(self, name):
        namespace = self.namespace
        serialcommand = "ssh -tp %s %s@%s virtctl console --kubeconfig=.kube/config %s -n %s" % (self.port, self.user, self.host, name, namespace)
        os.system(serialcommand)
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
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.debug:
            pretty_print(vm)
        metadata = vm.get("metadata")
        annotations = metadata.get("annotations")
        spec = vm.get("spec")
        volumes = spec["volumes"]
        name = metadata["name"]
        # creationdate = metadata["creationTimestamp"].strftime("%d-%m-%Y %H:%M")
        creationdate = metadata["creationTimestamp"]
        status = vm['status']
        memory = vm['spec']['domain']['resources']['requests']['memory']
        state = status['phase']
        # source = 'N/A'
        profile = annotations.get('kcli/profile')
        plan = annotations.get('kcli/plan')
        template = annotations.get('kcli/template')
        # report = 'N/A'
        ip = None
        host = status['nodeName'] if 'nodeName' in status else None
        if 'interfaces' in status:
            interfaces = vm['status']['interfaces']
            for interface in interfaces:
                if 'ipAddress' in interface:
                    ip = interface['ipAddress']
                    break
        yamlinfo = {'name': name, 'nets': [], 'disks': [], 'state': state, 'memory': memory, 'creationdate': creationdate, 'host': host, 'status': state}
        if template is not None:
            yamlinfo['template'] = template
        if ip is not None:
            yamlinfo['ip'] = ip
        if plan is not None:
            yamlinfo['plan'] = plan
        if profile is not None:
            yamlinfo['profile'] = profile
        plaindisks = spec['domain']['devices']['disks']
        disks = []
        for d in plaindisks:
            if 'disk' not in d:
                bus = 'N/A'
            else:
                bus = d['disk']['bus']
            volumename = d['volumeName']
            volumeinfo = [volume for volume in volumes if volume['name'] == volumename][0]
            if 'persistentVolumeClaim' in volumeinfo:
                pvcname = volumeinfo['persistentVolumeClaim']['claimName']
                _type = 'pvc'
                pvc = core.read_namespaced_persistent_volume_claim(pvcname, namespace)
                size = pvc.spec.resources.requests['storage'].replace('Gi', '')
            elif 'cloudInitNoCloud' in volumeinfo:
                _type = 'cloudinit'
                size = '0'
            else:
                _type = 'other'
                size = '0'
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
        elif self.pvctemplate:
            pvc = core.list_namespaced_persistent_volume_claim(namespace)
            templates = [p.metadata.annotations['kcli/template'] for p in pvc.items if 'kcli/template' in p.metadata.annotations]
            return sorted(templates)
        else:
            return REGISTRYDISKS

        return

    def delete(self, name, snapshots=False):
        crds = self.crds
        core = self.core
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        crds.delete_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name, client.V1DeleteOptions())
        spec = vm.get("spec")
        volumes = [d['volumeName'] for d in spec['domain']['devices']['disks'] if d['volumeName'] != 'cloudinitdisk']
        pvcs = [pvc for pvc in core.list_namespaced_persistent_volume_claim(namespace).items if pvc.metadata.name in volumes]
        for p in sorted(pvcs):
            pvcname = p.metadata.name
            print("Deleting pvc %s" % pvcname)
            core.delete_namespaced_persistent_volume_claim(pvcname, namespace, p)
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue):
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
        crds = self.crds
        namespace = self.namespace
        try:
            vm = crds.get_namespaced_custom_object(DOMAIN, VERSION, namespace, 'virtualmachines', name)
        except:
            common.pprint("VM %s not found" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        vm['spec']['domain']['resources']['requests']['memory'] = "%sM" % memory
        crds.replace_namespaced_custom_object(DOMAIN, VERSION, namespace, "virtualmachines", name, vm)
        return

    def update_cpu(self, name, numcpus):
        print("not implemented")
        return

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        print("not implemented")
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        print("not implemented")
        return

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        core = self.core
        namespace = self.namespace
        pvc = core.list_namespaced_persistent_volume_claim(namespace)
        templates = {p.metadata.annotations['kcli/template']: p.metadata.name for p in pvc.items if 'kcli/template' in p.metadata.annotations}
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
        self.create_disk(name, size=size, pool=pool, thin=thin, template=template)
        return

    def delete_disk(self, name, diskname):
        core = self.core
        namespace = self.namespace
        try:
            pvc = core.read_namespaced_persistent_volume_claim(diskname, namespace, exact=True)
        except:
            common.pprint("Disk %s not found" % diskname, color='red')
            return 1
        core.delete_namespaced_persistent_volume_claim(diskname, namespace, pvc)
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
        template = ''
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        user = 'root'
        ip = self.ip(name)
        if template != '':
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

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False):
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        tunnel = True
        sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, hostuser=self.user, user=user, local=local, remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X, debug=self.debug)
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

    def add_image(self, image, pool, short=None, cmd=None):
        big = ['debian9']
        core = self.core
        namespace = self.namespace
        shortimage = os.path.basename(image).split('?')[0]
        volname = [k for k in TEMPLATES if TEMPLATES[k] == image][0]
        size = 3 if volname in big else 1
        now = datetime.datetime.now().strftime("%Y%M%d%H%M")
        pvc = {'kind': 'PersistentVolumeClaim', 'spec': {'storageClassName': pool, 'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '%sGi' % size}}}, 'apiVersion': 'v1', 'metadata': {'name': volname, 'annotations': {'kcli/template': shortimage}}}
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'OnFailure', 'containers': [{'image': 'kubevirtci/disk-importer', 'volumeMounts': [{'mountPath': '/storage', 'name': 'ceph-storage'}], 'name': 'importer', 'env': [{'name': 'CURL_OPTS', 'value': '-L'}, {'name': 'INSTALL_TO', 'value': '/storage/disk.img'}, {'name': 'URL', 'value': image}]}], 'volumes': [{'name': 'ceph-storage', 'persistentVolumeClaim': {'claimName': volname}}]}, 'apiVersion': 'v1', 'metadata': {'name': '%s-%s-importer' % (now, volname)}}
        try:
            core.read_namespaced_persistent_volume_claim(volname, namespace)
            # core.delete_namespaced_persistent_volume_claim(volname, namespace, oldpvc)
            common.pprint("Using exiting pvc")
        except:
            core.create_namespaced_persistent_volume_claim(namespace, pvc)
            common.pprint("Waiting 15 seconds for pvc to be bound")
            time.sleep(15)
        # try:
        #     common.pprint("Deleting old disk importer pod")
        #    oldpod = core.read_namespaced_pod('%s-importer' % volname, namespace)
        #     core.delete_namespaced_pod('%s-importer' % volname, namespace, oldpod)
        # except Exception:
        #    pass
        core.create_namespaced_pod(namespace, pod)
        common.pprint("Wait for %s-%s-importer pod to complete" % (now, volname))
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None):
        print("not implemented")
        return

    def delete_network(self, name=None):
        print("not implemented")
        return

    def list_pools(self):
        storageapi = client.StorageV1Api()
        pools = storageapi.list_storage_class().items
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
        return pool
