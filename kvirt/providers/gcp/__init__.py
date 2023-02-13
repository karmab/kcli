#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gcp Provider Class
"""

from ipaddress import ip_network
from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import UBUNTUS, METADATA_FIELDS
from dateutil import parser as dateparser
from getpass import getuser
import googleapiclient.discovery
from google.cloud import dns, storage
import os
from time import sleep
import webbrowser

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip']


class Kgcp(object):
    """

    """
    def __init__(self, debug=False, project="kubevirt-button", zone="europe-west1-b",
                 region='europe-west1'):
        self.conn = googleapiclient.discovery.build('compute', 'v1')
        self.conn_beta = googleapiclient.discovery.build('compute', 'beta')
        self.project = project
        self.zone = zone
        self.region = region
        self.debug = debug
        return

    def _wait_for_operation(self, operation):
        selflink = operation['selfLink']
        operation = operation['name']
        conn = self.conn
        project = self.project
        done = False
        timeout = 0
        while not done:
            if timeout > 60:
                return
            if 'zone' in selflink:
                check = conn.zoneOperations().get(project=project, zone=self.zone, operation=operation).execute()
            elif 'region' in selflink:
                check = conn.regionOperations().get(project=project, region=self.region, operation=operation).execute()
            else:
                check = conn.globalOperations().get(project=project, operation=operation).execute()
            if check['status'] == 'DONE':
                done = True
            else:
                sleep(1)
                timeout += 1
        if 'httpErrorMessage' in check:
            httperror = check['httpErrorMessage']
            code = check['error']['errors'][0]["code"]
            message = check['error']['errors'][0]["message"]
            error(f"Got {httperror} Code {code} Error {message}")
        return

    def close(self):
        return

    def exists(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.instances().get(zone=zone, project=project, instance=name).execute()
            return True
        except:
            return False

    def net_exists(self, name):
        conn = self.conn
        project = self.project
        try:
            conn.networks().get(project=project, network=name).execute()
        except:
            return False
        return True

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[],
               cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, alias=[], overrides={}, tags=[], storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False,
               metadata={}, securitygroups=[], vmuser=None):
        conn = self.conn
        project = self.project
        zone = self.zone
        region = self.region
        if flavor is None:
            if numcpus != 1 and numcpus % 2 != 0:
                return {'result': 'failure', 'reason': "Number of cpus is not even"}
            if memory != 512 and memory % 1024 != 0:
                return {'result': 'failure', 'reason': "Memory is not multiple of 1024"}
            if numcpus > 1 and memory < 2048:
                pprint("Rounding memory to 2048Mb as more than one cpu is used")
                memory = 2048
            machine_type = f'custom-{numcpus}-{memory}'
            if memory < 921.6:
                pprint("Rounding memory to 1024Mb")
                machine_type = 'f1-micro'
        else:
            machine_type = flavor
        machine_type = f"zones/{zone}/machineTypes/{machine_type}"
        body = {'name': name, 'machineType': machine_type, 'networkInterfaces': []}
        foundnets = []
        for index, net in enumerate(nets):
            if isinstance(net, str):
                netname = net
                netpublic = True
                ip = None
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                ip = net.get('ip')
                alias = net.get('alias')
                netpublic = net.get('public', True)
            if ips and len(ips) > index and ips[index] is not None:
                ip = ips[index]
            if netname in foundnets:
                continue
            else:
                foundnets.append(netname)
            newnet = {'network': f'global/networks/{netname}'}
            if netpublic and index == 0:
                newnet['accessConfigs'] = [{'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}]
            if netname != 'default':
                newnet['subnetwork'] = f'projects/{project}/regions/{region}/subnetworks/{netname}'
            if ip is not None:
                newnet['networkIP'] = ip
            body['networkInterfaces'].append(newnet)
        body['disks'] = []
        for index, disk in enumerate(disks):
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
            newdisk = {'boot': False, 'autoDelete': True}
            if index == 0 and image is not None:
                if image.startswith('rhcos'):
                    src = f"https://www.googleapis.com/compute/v1/projects/rhcos-cloud/global/images/{image}"
                else:
                    image = self.__evaluate_image(image)
                    imageproject = self.__get_image_project(image)
                    if imageproject is not None:
                        image_response = conn.images().getFromFamily(project=imageproject, family=image).execute()
                    else:
                        try:
                            image_response = conn.images().get(project=self.project, image=image).execute()
                        except:
                            return {'result': 'failure', 'reason': f'Issue with image {image}'}
                    src = image_response['selfLink']
                if image.startswith('centos-') and image.endswith('8') and disksize == 10:
                    disksize = 20
                    pprint("Rounding primary disk to to 20Gb")
                newdisk['initializeParams'] = {'sourceImage': src, 'diskSizeGb': disksize}
                newdisk['boot'] = True
            else:
                diskname = f"{name}-disk{index}"
                diskpath = f'/compute/v1/projects/{project}/zones/{zone}/disks/{diskname}'
                info = {'sizeGb': disksize, 'sourceDisk': f'zones/{zone}/diskTypes/pd-standard', 'name': diskname}
                conn.disks().insert(zone=zone, project=project, body=info).execute()
                timeout = 0
                while True:
                    if timeout > 60:
                        return {'result': 'failure', 'reason': f'timeout waiting for disk {diskname} to be ready'}
                    newstatus = conn.disks().get(zone=zone, project=project, disk=diskname).execute()
                    if newstatus['status'] == 'READY':
                        break
                    else:
                        timeout += 5
                        sleep(5)
                        pprint(f"Waiting for disk {diskname} to be ready")
                newdisk['source'] = diskpath
            body['disks'].append(newdisk)
        body['serviceAccounts'] = [{'email': 'default',
                                    'scopes': ['https://www.googleapis.com/auth/devstorage.read_write',
                                               'https://www.googleapis.com/auth/logging.write']}]
        body['labels'] = {}
        body['metadata'] = {'items': []}
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            value = metadata[entry].replace('.', '-')
            body['labels'][entry] = value
        publickeyfile = get_ssh_pub_key()
        if publickeyfile is None:
            warning("neither id_rsa, id_dsa nor id_ed25519 public keys found in your .ssh or .kcli directories, "
                    "you might have trouble accessing the vm")
        else:
            publickeyfile = open(publickeyfile).read()
            keys = [publickeyfile] + keys if keys is not None else [publickeyfile]
        if keys:
            user = common.get_user(image)
            if user == 'root':
                user = getuser()
            finalkeys = [f"{user}:{x}"for x in keys]
            if enableroot:
                finalkeys.extend([f"root:{x}" for x in keys])
                enablerootcmds = ['sed -i "s/.*PermitRootLogin.*/PermitRootLogin yes/" /etc/ssh/sshd_config',
                                  'systemctl restart sshd']
                cmds = enablerootcmds + cmds
            newval = {'key': 'ssh-keys', 'value': '\n'.join(finalkeys)}
            body['metadata']['items'].append(newval)
            newval = {'key': 'block-project-ssh-keys', 'value': 'TRUE'}
            body['metadata']['items'].append(newval)
        if cloudinit:
            if image is not None and common.needs_ignition(image):
                version = common.ignition_version(image)
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, files=files, enableroot=enableroot,
                                           overrides=overrides, version=version, plan=plan, image=image,
                                           vmuser=vmuser)
            else:
                userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                            domain=domain, files=files, enableroot=enableroot,
                                            overrides=overrides, fqdn=True, storemetadata=storemetadata,
                                            vmuser=vmuser)[0]
                if 'ubuntu' in image.lower() or [entry for entry in UBUNTUS if entry in image]:
                    pkgmgr = "apt-get"
                else:
                    pkgmgr = "yum"
                startup_script = "test -f /root/.kcli_startup && exit 0\n"
                startup_script += "sleep 10\nwhich cloud-init && touch /root/.kcli_startup && exit 0\n"
                startup_script += f"{pkgmgr} install -y cloud-init\n"
                startup_script += "systemctl enable --now cloud-init\n"
                startup_script += "touch /root/.kcli_startup\nreboot"
                newval = {'key': 'startup-script', 'value': startup_script}
                body['metadata']['items'].append(newval)
            newval = {'key': 'user-data', 'value': userdata}
            body['metadata']['items'].append(newval)
        if 'kubetype' in metadata and metadata['kubetype'] in ["generic", "openshift"]:
            kube = metadata['kube']
            kubetype = metadata['kubetype']
            if not [r for r in conn.firewalls().list(project=project).execute()['items'] if r['name'] == kube]:
                pprint(f"Adding vm to security group {kube}")
                tcp_ports = [22, 443, 2379, 2380]
                firewall_body = {"name": kube, "direction": "INGRESS", "targetTags": [kube],
                                 "allowed": [{"IPProtocol": "tcp", "ports": tcp_ports}]}
                if kubetype == 'openshift':
                    extra_tcp_ports = [80, 8080, 443, 5443, 8443, 22624, 4789, 6080, 6081, '30000-32767',
                                       '10250-10259', '9000-9999']
                    firewall_body['allowed'][0]['ports'].extend(extra_tcp_ports)
                    udp_ports = ['4789', '6081', '30000-32767', '9000-9999']
                    firewall_body['allowed'].append({"IPProtocol": "udp", "ports": udp_ports})
                pprint(f"Creating firewall rule {kube}")
                operation = conn.firewalls().insert(project=project, body=firewall_body).execute()
                self._wait_for_operation(operation)
            tags.extend([kube])
        if tags:
            body['tags'] = {'items': tags}
        newval = {'key': 'serial-port-enable', 'value': 1}
        body['metadata']['items'].append(newval)
        if self.debug:
            print(body)
        if storemetadata and overrides:
            existingkeys = [entry['key'] for entry in body['metadata']['items']]
            for key in overrides:
                if key not in existingkeys:
                    newval = {'key': key, 'value': overrides[key]}
                    body['metadata']['items'].append(newval)
        tpm, secureboot = overrides.get('tpm', False), overrides.get('secureboot', False)
        if tpm or secureboot:
            body['shielded_instance_config'] = {'enable_integrity_monitoring': False, 'enable_vtpm': tpm,
                                                'enable_secure_boot': secureboot}
        try:
            conn.instances().insert(project=project, zone=zone, body=body).execute()
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        action = conn.instances().start(zone=zone, project=project, instance=name).execute()
        if action is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        else:
            return {'result': 'success'}

    def stop(self, name, soft=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        action = conn.instances().stop(zone=zone, project=project, instance=name).execute()
        if action is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        else:
            return {'result': 'success'}

    def create_snapshot(self, name, base):
        conn = self.conn
        project = self.project
        zone = self.zone
        body = {'name': name, 'forceCreate': True}
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=base).execute()
            body['sourceDisk'] = vm['disks'][0]['source']
        except:
            try:
                disk = conn.images().get(project=project, image=base).execute()
                body['sourceImage'] = disk['selfLink']
            except:
                return {'result': 'failure', 'reason': f"VM/disk {name} not found"}
        body['licenses'] = ["projects/vm-options/global/licenses/enable-vmx"]
        conn.images().insert(project=project, body=body).execute()
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
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.instances().reset(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        return {'result': 'success'}

    def report(self):
        resource = googleapiclient.discovery.build('cloudresourcemanager', 'v1')
        project = self.project
        zone = self.zone
        print(f"Project: {project}")
        projectinfo = resource.projects().get(projectId=project).execute()
        print(f"ProjectNumber: {projectinfo['projectNumber']}")
        print(f"Creation Time: {projectinfo['createTime']}")
        print(f"Zone: {zone}")
        return

    def status(self, name):
        status = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            status = vm['status']
        except:
            error(f"Vm {name} not found")
        return status

    def list(self):
        conn = self.conn
        project = self.project
        zone = self.zone
        vms = []
        results = conn.instances().list(project=project, zone=zone).execute()
        if 'items' not in results:
            return []
        for vm in results['items']:
            try:
                vms.append(self.info(vm['name'], vm=vm))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        project = self.project
        zone = self.zone
        resource = googleapiclient.discovery.build('cloudresourcemanager', 'v1')
        projectinfo = resource.projects().get(projectId=project).execute()
        projectnumber = projectinfo['projectNumber']
        url = f"{project}/zones/{zone}/instances/{name}?authuser=1&hl=en_US&projectNumber={projectnumber}"
        url = f"https://ssh.cloud.google.com/projects/{url}"
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = f"Open the following url:\n{url}" if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint(f"Opening url: {url}")
            webbrowser.open(url, new=2, autoraise=True)
        return

    def serialconsole(self, name, web=False):
        project = self.project
        zone = self.zone
        user, ip = common._ssh_credentials(self, name)[:2]
        sshcommand = "ssh"
        identityfile = None
        if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
            identityfile = os.path.expanduser("~/.kcli/id_rsa")
        if identityfile is not None:
            sshcommand += f" -i {identityfile}"
        sshcommand = f"{sshcommand} -p 9600 {project}.{zone}.{name}.{user}@ssh-serialport.googleapis.com"
        if web:
            return sshcommand
        if self.debug:
            print(sshcommand)
        os.system(sshcommand)
        return

    def dnsinfo(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return None, None
        dnsclient, domain = None, None
        if 'labels' in vm:
            for key in vm['labels']:
                if key == 'dnsclient':
                    dnsclient = vm['labels'][key]
                if key == 'domain':
                    domain = vm['labels'][key].replace('-', '.')
        return dnsclient, domain

    def info(self, name, vm=None, debug=False):
        yamlinfo = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        if vm is None:
            try:
                vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            except:
                error(f"VM {name} not found")
                return {}
        yamlinfo['name'] = vm['name']
        yamlinfo['status'] = vm['status']
        machinetype = os.path.basename(vm['machineType'])
        yamlinfo['flavor'] = machinetype
        if 'custom' in machinetype:
            yamlinfo['cpus'], yamlinfo['memory'] = machinetype.split('-')[1:]
        yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        if 'accessConfigs' in vm['networkInterfaces'][0] and 'natIP' in vm['networkInterfaces'][0]['accessConfigs'][0]:
            yamlinfo['ip'] = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        source = os.path.basename(vm['disks'][0]['source'])
        source = conn.disks().get(zone=zone, project=self.project, disk=source).execute()
        if 'sourceImage' in source:
            yamlinfo['image'] = os.path.basename(source['sourceImage'])
        elif 'licenses' in vm['disks'][0]:
            yamlinfo['image'] = os.path.basename(vm['disks'][0]['licenses'][-1])
        if 'image' in yamlinfo:
            yamlinfo['user'] = common.get_user(yamlinfo['image'])
        yamlinfo['creationdate'] = dateparser.parse(vm['creationTimestamp']).strftime("%d-%m-%Y %H:%M")
        nets = []
        for interface in vm['networkInterfaces']:
            network = os.path.basename(interface['network'])
            device = interface['name']
            private_ip = interface['networkIP'] if 'networkIP' in interface else 'N/A'
            yamlinfo['private_ip'] = private_ip
            if 'ip' not in yamlinfo and private_ip != 'N/A':
                yamlinfo['ip'] = private_ip
            network_type = ''
            nets.append({'device': device, 'mac': private_ip, 'net': network, 'type': network_type})
        if nets:
            yamlinfo['nets'] = nets
        disks = []
        for index, disk in enumerate(vm['disks']):
            devname = disk['deviceName']
            diskname = os.path.basename(disk['source'])
            diskformat = disk['interface']
            drivertype = disk['type']
            path = os.path.basename(disk['source'])
            diskinfo = conn.disks().get(zone=zone, project=project, disk=diskname).execute()
            disksize = int(diskinfo['sizeGb'])
            disks.append({'device': devname, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        if disks:
            yamlinfo['disks'] = disks
        if 'labels' in vm:
            for key in vm['labels']:
                if key in METADATA_FIELDS:
                    yamlinfo[key] = vm['labels'][key]
        if 'tags' in vm and 'items' in vm['tags']:
            yamlinfo['tags'] = ','.join(vm['tags']['items'])
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def ip(self, name):
        ip = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            error(f"Vm {name} not found")
            return None
        if 'natIP' not in vm['networkInterfaces'][0]['accessConfigs'][0]:
            return None
        else:
            ip = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        return ip

    def internalip(self, name):
        ip = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            error(f"Vm {name} not found")
            return None
        if 'networkIP' not in vm['networkInterfaces'][0]:
            return None
        else:
            ip = vm['networkInterfaces'][0]['networkIP']
        return ip

    def volumes(self, iso=False):
        projects = ['centos-cloud', 'coreos-cloud', 'cos-cloud', 'debian-cloud', 'fedora-coreos-cloud', 'rhel-cloud',
                    'suse-cloud', 'ubuntu-os-cloud', self.project]
        conn = self.conn
        images = []
        for project in projects:
            results = conn.images().list(project=project, orderBy="creationTimestamp desc").execute()
            if 'items' in results:
                for image in results['items']:
                    if project == self.project:
                        images.append(image['name'])
                    elif 'family' not in image:
                        continue
                    elif image['family'] not in images:
                        images.append(image['family'])
        return sorted(images)

    def delete(self, name, snapshots=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        domain, dnsclient, kube = None, None, None
        if 'labels' in vm:
            for key in vm['labels']:
                if key == 'domain':
                    domain = vm['labels'][key].replace('-', '.')
                if key == 'dnsclient':
                    dnsclient = vm['labels'][key]
                if key == 'kube':
                    kube = vm['labels'][key]
        if domain is not None and dnsclient is None:
            self.delete_dns(name, domain)
        conn.instances().delete(zone=zone, project=project, instance=name).execute()
        if kube is not None:
            try:
                operation = conn.firewalls().delete(project=project, firewall=kube).execute()
                self._wait_for_operation(operation)
            except Exception:
                pass
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return 1
        labels = vm.get('labels')
        if labels is None:
            labels = {}
        if metatype not in labels or labels[metatype] != metavalue:
            labels[metatype] = metavalue
            label_body = {"labelFingerprint": vm['labelFingerprint'], "labels": [labels]}
            conn.instances().setLabels(project=project, zone=zone, instance=name, body=label_body).execute()
        return 0

    def update_flavor(self, name, flavor):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error(f"Can't update flavor of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        machinetype = os.path.basename(vm['machineType'])
        if machinetype == flavor:
            return {'result': 'success'}
        else:
            url = f"https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/machineTypes/{flavor}"
            body = {"machineType": url}
            conn.instances().setMachineType(project=project, zone=zone, instance=name, body=body).execute()
        return {'result': 'success'}

    def update_memory(self, name, memory):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error(f"Can't update memory of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        machinetype = os.path.basename(vm['machineType'])
        if 'custom' in machinetype:
            currentcpus, currentmemory = machinetype.split('-')[1:]
            if memory == currentmemory:
                return {'result': 'success'}
            url = f"https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/machineTypes"
            newmachinetype = f"{url}/custom-{currentcpus}-{memory}"
            body = {"machineType": newmachinetype}
            conn.instances().setMachineType(project=project, zone=zone, instance=name, body=body).execute()
        else:
            warning(f"No custom machine type found. Not updating memory of {name}")
        return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error(f"Can't update cpus of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        machinetype = os.path.basename(vm['machineType'])
        if 'custom' in machinetype:
            currentcpus, currentmemory = machinetype.split('-')[1:]
            if numcpus == currentcpus:
                return {'result': 'success'}
            url = f"https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/machineTypes"
            newmachinetype = f"{url}/custom-{numcpus}-{currentmemory}"
            body = {"machineType": newmachinetype}
            conn.instances().setMachineType(project=project, zone=zone, instance=name, body=body).execute()
        else:
            warning(f"No custom machine type found. Not updating memory of {name}")
        return {'result': 'success'}

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        print("not implemented")
        return

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        numdisks = len(vm['disks']) + 1
        diskname = f"{name}-disk{numdisks}"
        body = {'sizeGb': size, 'sourceDisk': f'zones/{zone}/diskTypes/pd-standard', 'name': diskname}
        conn.disks().insert(zone=zone, project=project, body=body).execute()
        timeout = 0
        while True:
            if timeout > 60:
                return {'result': 'failure', 'reason': 'timeout waiting for new disk to be ready'}
            newdisk = conn.disks().get(zone=zone, project=project, disk=diskname).execute()
            if newdisk['status'] == 'READY':
                break
            else:
                timeout += 5
                sleep(5)
                pprint("Waiting for disk to be ready")
        body = {'source': f'/compute/v1/projects/{project}/zones/{zone}/disks/{diskname}', 'autoDelete': True}
        conn.instances().attachDisk(zone=zone, project=project, instance=name, body=body).execute()
        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.disks().delete(zone=zone, project=project, disk=diskname).execute()
        except:
            return {'result': 'failure', 'reason': f"Disk {diskname} not found"}
        return

    def list_disks(self):
        disks = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        alldisks = conn.disks().list(zone=zone, project=project).execute()
        if 'items' in alldisks:
            for disk in alldisks['items']:
                if self.debug:
                    print(disk)
                diskname = disk['name']
                pool = os.path.basename(disk['type'])
                disks[diskname] = {'pool': pool, 'path': zone}
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

    def delete_image(self, image, pool=None):
        pprint(f"Deleting image {image}")
        conn = self.conn
        project = self.project
        try:
            operation = conn.images().delete(project=project, image=image).execute()
            self._wait_for_operation(operation)
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': f'Image {image} not found'}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None):
        conn = self.conn
        project = self.project
        shortimage = os.path.basename(url).split('?')[0].replace('.tar.gz', '').replace('.', '-').replace('-', '.')
        if 'rhcos' in url:
            shortimage = f"rhcos-{shortimage}"
        pprint(f"Adding image {shortimage}")
        image_body = {'name': shortimage, 'licenses': ["projects/vm-options/global/licenses/enable-vmx"]}
        if url.endswith('tar.gz'):
            image_body['rawDisk'] = {'source': url}
        operation = conn.images().insert(project=project, body=image_body).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        conn = self.conn
        project = self.project
        region = self.region
        body = {'name': name, 'autoCreateSubnetworks': True if cidr is None else False}
        operation = conn.networks().insert(project=project, body=body).execute()
        networkpath = operation["targetLink"]
        self._wait_for_operation(operation)
        # sleep(20)
        if cidr is not None:
            try:
                ip_network(cidr)
            except:
                return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
            regionpath = f"https://www.googleapis.com/compute/v1/projects/{project}/regions/{region}"
            subnet_body = {'name': name, "ipCidrRange": cidr, 'network': networkpath, "region": regionpath}
            operation = conn.subnetworks().insert(region=region, project=project, body=subnet_body).execute()
            self._wait_for_operation(operation)
        allowed = {"IPProtocol": "tcp", "ports": ["22"]}
        firewall_body = {'name': f'allow-ssh-{name}', 'network': f'global/networks/{name}',
                         'sourceRanges': ['0.0.0.0/0'], 'allowed': [allowed]}
        conn.firewalls().insert(project=project, body=firewall_body).execute()
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        conn = self.conn
        project = self.project
        region = self.region
        try:
            network = conn.networks().get(project=project, network=name).execute()
        except:
            return {'result': 'failure', 'reason': f"Network {name} not found"}
        if not network['autoCreateSubnetworks'] and 'subnetworks' in network:
            for subnet in network['subnetworks']:
                subnetwork = os.path.basename(subnet)
                operation = conn.subnetworks().delete(region=region, project=project, subnetwork=subnetwork).execute()
                self._wait_for_operation(operation)
        try:
            operation = conn.firewalls().delete(project=project, firewall=f'allow-ssh-{name}').execute()
            self._wait_for_operation(operation)
        except:
            pass
        operation = conn.networks().delete(project=project, network=name).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

# should return a dict of pool strings
    def list_pools(self):
        print("not implemented")
        return []

    def list_networks(self):
        conn = self.conn
        project = self.project
        region = self.region
        nets = conn.networks().list(project=project).execute()
        if 'items' not in nets:
            return {}
        subnets = conn.subnetworks().list(region=region, project=project).execute()['items']
        networks = {}
        for net in nets['items']:
            if self.debug:
                print(net)
            networkname = net['name']
            cidr = net['IPv4Range'] if 'IPv4Range' in net else ''
            if 'subnetworks' in net:
                for subnet in net['subnetworks']:
                    subnetname = os.path.basename(subnet)
                    for sub in subnets:
                        if sub['name'] == subnetname:
                            cidr = sub['ipCidrRange']
                            break
            dhcp = True
            domainname = ''
            mode = ''
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
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
        return []

    def vm_ports(self, name):
        return ['default']

    def get_pool_path(self, pool):
        print("not implemented")
        return

    def __get_image_project(self, image):
        if image.startswith('sles'):
            return 'suse-cloud'
        if image.startswith('ubuntu'):
            return 'ubuntu-os-cloud'
        elif any([image.startswith(s) for s in ['centos', 'coreos', 'cos', 'debian', 'rhel']]):
            project = image.split('-')[0]
            return f"{project}-cloud"
        else:
            return None

    def __evaluate_image(self, image):
        # image = image.lower()
        if 'CentOS-7' in image:
            return 'centos-7'
        elif 'debian-8' in image:
            return 'debian-8'
        elif 'debian-9' in image:
            return 'debian-9'
        elif 'rhel-guest-image-7' in image.lower() or 'rhel-server-7' in image.lower():
            return 'rhel-7'
        elif 'rhel-guest-image-8' in image.lower() or 'rhel-server-8' in image.lower():
            return 'rhel-8'
        elif [x for x in UBUNTUS if x in image.lower()]:
            return 'ubuntu-1804-lts'
        else:
            return image

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        if domain is None:
            domain = nets[0]
        internalip = None
        project = self.project
        zone = self.zone
        region = self.region
        client = dns.Client(project)
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        dnszones = [z for z in client.list_zones() if z.dns_name == f"{domain}." or z.name == domain]
        if not dnszones:
            error(f"Domain {domain} not found")
            return {'result': 'failure', 'reason': f"Domain {domain} not found"}
        else:
            dnszone = dnszones[0]
        dnsentry = name if cluster is None else f"{name}.{cluster}"
        entry = f"{dnsentry}.{domain}."
        if cluster is not None and ('ctlplane' in name or 'worker' in name):
            counter = 0
            while counter != 100:
                internalip = self.internalip(name)
                if internalip is None:
                    sleep(5)
                    pprint(f"Waiting 5 seconds to grab internal ip and create DNS record for {name}")
                    counter += 10
                else:
                    break
        if ip is None:
            net = nets[0]
            if isinstance(net, dict):
                ip = net.get('ip')
            if ip is None:
                counter = 0
                while counter != 100:
                    ip = self.ip(name)
                    if ip is None:
                        sleep(5)
                        pprint(f"Waiting 5 seconds to grab ip and create DNS record for {name}")
                        counter += 10
                    else:
                        address_body = {"name": name, "address": ip}
                        self.conn.addresses().insert(project=project, region=region, body=address_body).execute()
                        network_interface = "nic0"
                        access_config_body = {"natIP": ip}
                        self.conn.instances().updateAccessConfig(project=project, zone=zone, instance=name,
                                                                 networkInterface=network_interface,
                                                                 body=access_config_body).execute()
                        break
        if ip is None:
            error(f"Couldn't assign DNS for {name}")
            return
        changes = dnszone.changes()
        dnsip = ip if internalip is None else internalip
        record_set = dnszone.resource_record_set(entry, 'A', 300, [dnsip])
        changes.add_record_set(record_set)
        if alias:
            for a in alias:
                if a == '*':
                    if cluster is not None and ('ctlplane' in name or 'worker' in name):
                        new = f'*.apps.{cluster}.{domain}.'
                    else:
                        new = f'*.{name}.{domain}.'
                    alias_record_set = dnszone.resource_record_set(new, 'A', 300, [ip])
                else:
                    new = f'{a}.{domain}.' if '.' not in a else f'{a}.'
                    alias_record_set = dnszone.resource_record_set(new, 'CNAME', 300, [entry])
                changes.add_record_set(alias_record_set)
        changes.create()
        return {'result': 'success'}

    def delete_dns(self, name, domain, allentries=False):
        project = self.project
        region = self.region
        client = dns.Client(project)
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        dnszones = [z for z in client.list_zones() if z.dns_name == f"{domain}." or z.name == domain]
        if not dnszones:
            return
        else:
            dnszone = dnszones[0]
        dnsentry = name if cluster is None else f"{name}.{cluster}"
        entry = f"{dnsentry}.{domain}."
        changes = dnszone.changes()
        records = []
        for record in dnszone.list_resource_record_sets():
            if entry in record.name or ('ctlplane-0' in name and record.name.endswith(f"{cluster}.{domain}.")):
                records.append(record)
            else:
                for rrdata in record.rrdatas:
                    if name in rrdata:
                        records.append(record)
        if records:
            for record in records:
                record_set = dnszone.resource_record_set(record.name, record.record_type, record.ttl, record.rrdatas)
                changes.delete_record_set(record_set)
            changes.create()
        try:
            self.conn.addresses().delete(project=project, region=region, address=name).execute()
        except:
            pass
        return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        project = self.project
        client = dns.Client(project)
        dnszones = [z for z in client.list_zones() if z.dns_name == f"{domain}." or z.name == domain]
        if dnszones:
            dnszone = dnszones[0]
            for record in dnszone.list_resource_record_sets():
                results.append([record.name, record.record_type, record.ttl, ','.join(record.rrdatas)])
        return results

    def list_flavors(self):
        conn = self.conn
        project = self.project
        zone = self.zone
        flavors = []
        results = conn.machineTypes().list(project=project, zone=zone).execute()
        if 'items' not in results:
            return []
        for flavor in results['items']:
            if self.debug:
                print(flavor)
            name = flavor['name']
            numcpus = flavor['guestCpus']
            memory = flavor['memoryMb']
            flavors.append([name, numcpus, memory])
        return flavors

    def export(self, name, image=None):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            status = vm['status']
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if status.lower() == 'running':
            return {'result': 'failure', 'reason': f"VM {name} up"}
        newname = image if image is not None else name
        description = f"image based on {name}"
        body = {'name': newname, 'forceCreate': True, 'description': description,
                'sourceDisk': vm['disks'][0]['source'], 'licenses': ["projects/vm-options/global/licenses/enable-vmx"]}
        conn.images().insert(project=project, body=body).execute()
        return {'result': 'success'}

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False, dnsclient=None, subnetid=None):
        lb_scheme = 'INTERNAL' if internal else 'EXTERNAL'
        sane_name = name.replace('.', '-')
        ports = [int(port) for port in ports]
        conn = self.conn
        conn_beta = self.conn_beta
        project = self.project
        zone = self.zone
        region = self.region
        instances = []
        vmpath = f"https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/instances"
        if vms:
            for vm in vms:
                update = self.update_metadata(vm, 'loadbalancer', sane_name, append=True)
                if update == 0:
                    instances.append({"instance": f"{vmpath}/{vm}"})
        # add checkpath handling (and default to http when defined)
        health_check_body = {"checkIntervalSec": "10", "timeoutSec": "10", "unhealthyThreshold": 3,
                             "healthyThreshold": 3, "name": sane_name}
        health_check_body["type"] = "TCP"
        health_check_body["tcpHealthCheck"] = {"port": checkport}
        pprint(f"Creating healthcheck {name}")
        if internal:
            operation = conn.healthChecks().insert(project=project, body=health_check_body).execute()
        else:
            operation = conn.regionHealthChecks().insert(project=project, region=self.region,
                                                         body=health_check_body).execute()
        healthurl = operation['targetLink']
        self._wait_for_operation(operation)
        sane_name = name.replace('.', '-')
        instances_group_body = {"name": sane_name, "healthChecks": [healthurl]}
        pprint(f"Creating instances group {sane_name}")
        operation = conn.instanceGroups().insert(project=project, zone=zone, body=instances_group_body).execute()
        instances_group_url = operation['targetLink']
        self._wait_for_operation(operation)
        if instances:
            instances_body = {"instances": instances}
            operation = conn.instanceGroups().addInstances(project=project, zone=zone, instanceGroup=sane_name,
                                                           body=instances_body).execute()
            self._wait_for_operation(operation)
        backend_body = {"name": sane_name, "backends": [{"group": instances_group_url}],
                        "loadBalancingScheme": lb_scheme, "protocol": "TCP", "healthChecks": [healthurl]}
        pprint(f"Creating backend service {sane_name}")
        operation = conn.regionBackendServices().insert(project=project, region=region, body=backend_body).execute()
        backendurl = operation['targetLink']
        self._wait_for_operation(operation)
        address_body = {"name": sane_name, "addressType": lb_scheme}
        pprint(f"Creating address {sane_name}")
        operation = conn_beta.addresses().insert(project=project, region=region, body=address_body).execute()
        ipurl = operation['targetLink']
        self._wait_for_operation(operation)
        address = conn_beta.addresses().get(project=project, region=region, address=sane_name).execute()
        ip = address['address']
        if domain is not None:
            labels = {"domain": domain.replace('.', '-')}
            if dnsclient is not None:
                labels["dnsclient"] = dnsclient
            label_body = {"labelFingerprint": address['labelFingerprint'], "labels": labels}
            conn_beta.addresses().setLabels(project=project, region=region,
                                            resource=sane_name, body=label_body).execute()
        pprint(f"Using load balancer ip {ip}")
        self._wait_for_operation(operation)
        forwarding_name = sane_name
        forwarding_rule_body = {"IPAddress": ipurl, "name": forwarding_name}
        forwarding_rule_body["backendService"] = backendurl
        forwarding_rule_body["IPProtocol"] = "TCP"
        forwarding_rule_body["ports"] = ports
        forwarding_rule_body["loadBalancingScheme"] = lb_scheme
        pprint(f"Creating forwarding rule {forwarding_name}")
        operation = conn.forwardingRules().insert(project=project, region=region, body=forwarding_rule_body).execute()
        self._wait_for_operation(operation)
        if not internal:
            firewall_body = {"name": sane_name, "direction": "INGRESS",
                             "allowed": [{"IPProtocol": "tcp", "ports": ports}]}
            if sane_name.startswith('api-') or sane_name.startswith('apps-'):
                kube = '-'.join(sane_name.split('-')[1:])
                firewall_body["targetTags"] = [kube]
            pprint(f"Creating firewall rule {sane_name}")
            operation = conn.firewalls().insert(project=project, body=firewall_body).execute()
            self._wait_for_operation(operation)
        if domain is not None:
            if dnsclient is not None:
                return ip
            self.reserve_dns(name, ip=ip, domain=domain, alias=alias)
        return {'result': 'success'}

    def delete_loadbalancer(self, name):
        domain = None
        dnsclient = None
        name = name.replace('.', '-')
        conn = self.conn
        conn_beta = self.conn_beta
        project = self.project
        zone = self.zone
        region = self.region
        firewall_rules = conn.firewalls().list(project=project).execute()
        if 'items' in firewall_rules:
            for firewall_rule in firewall_rules['items']:
                firewall_rule_name = firewall_rule['name']
                if firewall_rule_name == name:
                    pprint(f"Deleting firewall rule {name}")
                    operation = conn.firewalls().delete(project=project, firewall=name).execute()
                    self._wait_for_operation(operation)
        forwarding_rules = conn.forwardingRules().list(project=project, region=region).execute()
        if 'items' in forwarding_rules:
            for forwarding_rule in forwarding_rules['items']:
                forwarding_rule_name = forwarding_rule['name']
                if forwarding_rule_name == name or forwarding_rule_name.startswith(f'{name}-'):
                    pprint(f"Deleting forwarding rule {forwarding_rule_name}")
                    operation = conn.forwardingRules().delete(project=project, region=region,
                                                              forwardingRule=forwarding_rule_name).execute()
                    self._wait_for_operation(operation)
        try:
            address = conn_beta.addresses().get(project=project, region=region, address=name).execute()
            if 'labels' in address and 'domain' in address['labels'] and 'dnsclient' not in address['labels']:
                domain = address["labels"]["domain"].replace('-', '.')
                pprint(f"Deleting DNS {name}.{domain}")
                self.delete_dns(name, domain=domain)
            pprint(f"Deleting address {name}")
            operation = conn.addresses().delete(project=project, region=region, address=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        backendservices = conn.regionBackendServices().list(project=project, region=region).execute()
        if 'items' in backendservices:
            for backendservice in backendservices['items']:
                backendservice_name = backendservice['name']
                if backendservice_name == name:
                    internal = True if backendservice['loadBalancingScheme'] == 'INTERNAL' else False
                    pprint("Waiting to make sure forwarding rule is gone")
                    sleep(10)
                    pprint(f"Deleting backend service {name}")
                    operation = conn.regionBackendServices().delete(project=project, region=region,
                                                                    backendService=name).execute()
                    self._wait_for_operation(operation)
                    for healthcheck in backendservice.get('healthChecks', []):
                        healthcheck_short = os.path.basename(healthcheck)
                        pprint(f"Deleting healthcheck {healthcheck_short}")
                        if internal:
                            operation = conn.healthChecks().delete(project=project,
                                                                   healthCheck=healthcheck_short).execute()
                        else:
                            operation = conn.regionHealthChecks().delete(project=project, region=region,
                                                                         healthCheck=healthcheck_short).execute()
                        self._wait_for_operation(operation)
        instancegroups = conn.instanceGroups().list(project=project, zone=zone).execute()
        if 'items' in instancegroups:
            for instancegroup in instancegroups['items']:
                instancegroup_name = instancegroup['name']
                if instancegroup_name == name:
                    pprint(f"Deleting instance group {name}")
                    operation = conn.instanceGroups().delete(project=project, zone=zone, instanceGroup=name).execute()
                    self._wait_for_operation(operation)
        if dnsclient is not None:
            return dnsclient
        return {'result': 'success'}

    def list_loadbalancers(self):
        conn = self.conn
        project = self.project
        region = self.region
        results = []
        results1 = conn.globalForwardingRules().list(project=project).execute()
        results2 = conn.forwardingRules().list(project=project, region=region).execute()
        if 'items' in results1:
            for lb in results1['items']:
                name = lb['name']
                ip = lb['IPAddress']
                protocol = lb['IPProtocol']
                port = lb['port']
                target = os.path.basename(lb['target'])
                results.append([name, ip, protocol, port, target])
        if 'items' in results2:
            for lb in results2['items']:
                name = lb['name']
                ip = lb['IPAddress']
                protocol = lb['IPProtocol']
                port = lb['portRange'] if 'portRange' in lb else ','.join(lb['ports'])
                target = lb['target'] if 'target' in lb else lb['backendService']
                target = os.path.basename(target)
                results.append([name, ip, protocol, port, target])
        return results

    def create_bucket(self, bucket, public=False):
        client = storage.Client(self.project)
        if bucket in self.list_buckets():
            error(f"Bucket {bucket} already there")
            return
        client.create_bucket(bucket)
        if public:
            bucket = client.get_bucket(bucket)
            acl = bucket.acl
            acl.all().grant_read()
            acl.save()

    def delete_bucket(self, bucket):
        client = storage.Client(self.project)
        try:
            bucket = client.get_bucket(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return
        for obj in bucket.list_blobs():
            pprint(f"Deleting object {obj.name} from bucket {bucket.name}")
            obj.delete()
        bucket.delete()

    def delete_from_bucket(self, bucket, path):
        client = storage.Client(self.project)
        try:
            bucketname = bucket
            bucket = client.get_bucket(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return
        try:
            blob = bucket.get_blob(path)
        except:
            error(f"Inexistent path {path} in bucket {bucketname}")
            return
        blob.delete()

    def download_from_bucket(self, bucket, path):
        client = storage.Client(self.project)
        try:
            bucket = client.get_bucket(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return
        blob = bucket.get_blob(path)
        with open(path, 'wb') as f:
            client.download_blob_to_file(blob, f)

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        client = storage.Client(self.project)
        if not os.path.exists(path):
            error(f"Invalid path {path}")
            return
        try:
            bucket = client.get_bucket(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return
        dest = os.path.basename(path)
        blob = storage.Blob(dest, bucket)
        try:
            with open(path, "rb") as f:
                blob.upload_from_file(f)
        except Exception as e:
            error(f"Got {e}")
        if public:
            acl = storage.acl.ObjectACL(blob)
            acl.all().grant_read()
            acl.save()

    def list_buckets(self):
        client = storage.Client(self.project)
        return [bucket.name for bucket in client.list_buckets()]

    def list_bucketfiles(self, bucket):
        client = storage.Client(self.project)
        try:
            bucket = client.get_bucket(bucket)
        except:
            error(f"Inexistent bucket {bucket}")
            return []
        return [obj.name for obj in bucket.list_blobs()]

    def public_bucketfile_url(self, bucket, path):
        return f"https://storage.googleapis.com/{bucket}/{path}"

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        return [firewall['name'] for firewall in self.conn.firewalls().list(project=self.project).execute()['items']]

    def create_security_group(self, name, overrides={}):
        ports = overrides.get('ports', [])
        sane_name = name.replace('.', '-')
        firewall_body = {"name": sane_name, "direction": "INGRESS",
                         "allowed": [{"IPProtocol": "tcp", "ports": ports}]}
        if sane_name.startswith('api-') or sane_name.startswith('apps-'):
            kube = '-'.join(sane_name.split('-')[1:])
            firewall_body["targetTags"] = [kube]
        pprint(f"Creating firewall rule {sane_name}")
        operation = self.conn.firewalls().insert(project=self.project, body=firewall_body).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

    def delete_security_group(self, name):
        operation = self.conn.firewalls().delete(project=self.project, firewall=name).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}
