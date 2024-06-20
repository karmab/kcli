# -*- coding: utf-8 -*-

from ipaddress import ip_network, IPv6Network
from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import UBUNTUS, METADATA_FIELDS
from dateutil import parser as dateparser
from getpass import getuser
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest
from google_auth_httplib2 import AuthorizedHttp
from google.auth import default
from httplib2 import Http
from google.cloud import dns, storage, compute_v1
import os
import re
from time import sleep
import webbrowser

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip']


def build_request(http, *args, **kwargs):
    credentials = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])[0]
    new_http = AuthorizedHttp(credentials, http=Http())
    return HttpRequest(new_http, *args, **kwargs)


def is_ula(cidr):
    return IPv6Network(cidr).network_address in IPv6Network("fc00::/7")


class Kgcp(object):
    def __init__(self, project, region='europe-west1', zone=None, debug=False):
        credentials = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])[0]
        authorized_http = AuthorizedHttp(credentials, http=Http())
        self.conn = build('compute', 'v1', requestBuilder=build_request, http=authorized_http)
        self.conn_beta = build('compute', 'beta', requestBuilder=build_request, http=authorized_http)
        self.project = project
        self.region = region
        self.debug = debug
        self.machine_flavor_cache = {}
        request = self.conn.projects().getXpnHost(project=project)
        response = request.execute()
        self.xproject = response['name'] if response else None
        if zone is None:
            self.specific_zone = False
            for z in self.conn.zones().list(project=project).execute()['items']:
                if z['region'].endswith(region):
                    self.zone = z['name']
                    break
        else:
            self.zone = zone
            self.specific_zone = True
        self.router_client = compute_v1.RoutersClient(credentials=credentials)
        self.routes_client = compute_v1.RoutesClient(credentials=credentials)
        self.iam = build('iam', 'v1', credentials=credentials)

    def list_zones(self, project):
        return [z['name'] for z in self.conn.zones().list(project=project).execute()['items']
                if z['region'].endswith(self.region)]

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

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model', cpuflags=[],
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
        region = self.region
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        lb = overrides.get('loadbalancer')
        kubetype = metadata.get('kubetype')
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
        zone = overrides.get('az') or overrides.get('availability_zone') or overrides.get('zone') or self.zone
        machine_type = f"zones/{zone}/machineTypes/{machine_type}"
        body = {'name': name, 'machineType': machine_type, 'networkInterfaces': []}
        if cpumodel != 'host-model':
            body['minCpuPlatform'] = cpumodel
        gpus = overrides.get('accelerators') or overrides.get('gpus') or []
        if gpus:
            if len(gpus) > 1:
                return {'result': 'failure', 'reason': 'only a single accelerator type can be specified'}
            accelerators = []
            for accelerator in gpus:
                if isinstance(accelerator, str):
                    accelerator_type = accelerator
                    accelerator_count = 1
                elif isinstance(accelerator, dict):
                    accelerator_type = accelerator.get('name') or accelerator.get('type')\
                        or accelerator.get('acceleratorType')
                    if accelerator_type is None:
                        warning("Invalid accelerator {accelerator}")
                        continue
                    accelerator_count = accelerator.get('count') or accelerator.get('acceleratorCount') or 1
                else:
                    warning("Invalid accelerator {accelerator}")
                    continue
                if self.project not in accelerator_type:
                    accelerator_type = f"projects/{project}/zones/{zone}/acceleratorTypes/{accelerator_type}"
                new_accelerator = {'accelerator_type': accelerator_type, 'accelerator_count': accelerator_count}
                accelerators.append(new_accelerator)
            if accelerators:
                body['guestAccelerators'] = accelerators
                body['scheduling'] = {'preemptible': False, 'onHostMaintenance': 'TERMINATE'}
        use_xproject = False
        vm_networks = []
        networks = self.list_networks()
        subnets = self.list_subnets()
        for index, net in enumerate(nets):
            netpublic = overrides.get('public', True)
            reserveip = overrides.get('reserveip', False)
            nettype = 'virtio'
            if isinstance(net, str):
                netname = net
                ip = None
                secondary_cidr = None
                pod_cidr = None
                service_cidr = None
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                nettype = net.get('type', nettype)
                ip = net.get('ip')
                alias = net.get('alias')
                if 'public' in net:
                    netpublic = net.get('public')
                secondary_cidr = net.get('secondary_cidr') or overrides.get('secondary_cidr')
                pod_cidr = net.get('pod_cidr')
                service_cidr = net.get('service_cidr')
            if ips and len(ips) > index and ips[index] is not None:
                ip = ips[index]
            newnet = {}
            if index == 0:
                first_net = netname
                if netpublic:
                    access_config = {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
                    if reserveip or (reservedns and domain is not None):
                        address_body = {"name": f'{name}-ip', "addressType": 'EXTERNAL'}
                        operation = self.conn_beta.addresses().insert(project=project,
                                                                      region=region, body=address_body).execute()
                        self._wait_for_operation(operation)
                        address = self.conn_beta.addresses().get(project=project, region=region,
                                                                 address=f'{name}-ip').execute()
                        access_config['natIP'] = address['address']
                    newnet['accessConfigs'] = [access_config]
            if netname in subnets:
                network_project = subnets[netname]['id']
                if network_project == self.xproject:
                    use_xproject = True
                newnet['subnetwork'] = f'projects/{network_project}/regions/{region}/subnetworks/{netname}'
                if ':' in subnets[netname]['cidr']:
                    newnet["stackType"] = "IPV4_IPV6"
                subnet_region = subnets[netname]['az']
                if region != self.region:
                    return {'result': 'failure', 'reason': f'{netname} is in region {subnet_region}, not {region}'}
                current_network = subnets[netname]['network']
            elif netname in networks:
                newnet['network'] = f'global/networks/{netname}'
                current_network = netname
            else:
                return {'result': 'failure', 'reason': f'{netname} not in subnets nor in networks'}
            if current_network in vm_networks:
                return {'result': 'failure', 'reason': f'vm has several nics in network {current_network}'}
            else:
                vm_networks.append(current_network)
            if ip is not None:
                newnet['networkIP'] = ip
            aliases = []
            if secondary_cidr is not None:
                secondary_name = net.get('secondary_name') or f"secondary-{netname}"
                aliases.append({"ipCidrRange": secondary_cidr, "subnetworkRangeName": secondary_name})
            if pod_cidr is not None:
                pod_cidr_name = net.get('pod_cidr_name') or f"secondary-{netname}"
                aliases.append({"ipCidrRange": pod_cidr, "subnetworkRangeName": pod_cidr_name})
            if service_cidr is not None:
                service_cidr_name = net.get('service_cidr_name') or f"secondary-{netname}"
                aliases.append({"ipCidrRange": service_cidr, "subnetworkRangeName": service_cidr_name})
            if aliases:
                newnet["aliasIpRanges"] = aliases
            if nettype.lower() == 'gvnic':
                newnet["nic_type"] = 'gVNIC'
            body['networkInterfaces'].append(newnet)
        body['disks'] = []
        for index, disk in enumerate(disks):
            disk_type = overrides.get('diskinterface') or overrides.get('disktype')
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
                disk_type = disk.get('type') or disk.get('interface') or disk_type
            if disk_type is not None:
                disk_type = f'/compute/v1/projects/{project}/zones/{zone}/diskTypes/{disk_type}'
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
                if disk_type is not None:
                    newdisk['initializeParams']['diskType'] = disk_type
            else:
                diskname = f"{name}-disk{index}"
                diskpath = f'/compute/v1/projects/{project}/zones/{zone}/disks/{diskname}'
                init = {'name': diskname, 'sizeGb': disksize}
                if disk_type is not None:
                    init['type'] = disk_type
                conn.disks().insert(zone=zone, project=project, body=init).execute()
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
        if not keys:
            publickeyfile = get_ssh_pub_key()
            if publickeyfile is not None:
                publickeyfile = open(publickeyfile).read().strip()
                keys = [publickeyfile]
        if keys:
            user = common.get_user(image)
            if user == 'root':
                user = getuser()

            keysandusers = f"\\n{user}:".join(keys)
            newval = {'key': 'ssh-keys', 'value': f"{user}:{keysandusers}"}
            body['metadata']['items'].append(newval)
            newval = {'key': 'block-project-ssh-keys', 'value': 'TRUE'}
            body['metadata']['items'].append(newval)
        else:
            warning("neither id_rsa, id_dsa nor id_ed25519 public keys found in your .ssh or .kcli directories, "
                    "you might have trouble accessing the vm")

        if enableroot:
            enablerootcmds = ['sed -i "s/.*PermitRootLogin.*/PermitRootLogin yes/" /etc/ssh/sshd_config',
                              'systemctl restart sshd']
            cmds = enablerootcmds + cmds
        need_gcp_hack = kubetype is not None and kubetype == 'openshift' and 'ctlplane' in name
        if need_gcp_hack:
            gcpdir = os.path.dirname(Kgcp.create.__code__.co_filename)
            files.append({"path": "/usr/local/bin/gcp-hack.sh", "origin": f'{gcpdir}/gcp-hack.sh', "mode": 755})
            files.append({"path": "/etc/systemd/system/gcp-hack.service",
                          "origin": f'{gcpdir}/gcp-hack.service', "mode": 644})
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
                if need_gcp_hack:
                    startup_script += "systemctl start gcp-hack\n"
                startup_script += "sleep 10\nwhich cloud-init && touch /root/.kcli_startup && exit 0\n"
                startup_script += f"{pkgmgr} install -y cloud-init\n"
                startup_script += "systemctl enable --now cloud-init\n"
                startup_script += "touch /root/.kcli_startup\nreboot"
                newval = {'key': 'startup-script', 'value': startup_script}
                body['metadata']['items'].append(newval)
            newval = {'key': 'user-data', 'value': userdata}
            body['metadata']['items'].append(newval)
        if kubetype is not None and kubetype in ["generic", "openshift", "k3s"] and not use_xproject:
            kube = metadata['kube']
            firewalls = conn.firewalls().list(project=project).execute()
            firewalls = firewalls['items'] if 'items' in firewalls else []
            if not firewalls or not [r for r in firewalls if r['name'] == kube]:
                pprint(f"Creating firewall {kube}")
                network = f"global/networks/{first_net if first_net in networks else subnets[first_net]['network']}"
                tcp_ports = [22, 443, 2379, 2380]
                firewall_body = {"name": kube, "network": network, "direction": "INGRESS", "targetTags": [kube],
                                 "allowed": [{"IPProtocol": "tcp", "ports": tcp_ports}]}
                if kubetype == 'openshift':
                    extra_tcp_ports = [80, 8080, 443, 5443, 8443, 22624, 4789, 6080, 6081, '30000-32767',
                                       '10250-10259', '9000-9999']
                    firewall_body['allowed'][0]['ports'].extend(extra_tcp_ports)
                    udp_ports = ['4789', '6081', '30000-32767', '9000-9999']
                    firewall_body['allowed'].append({"IPProtocol": "udp", "ports": udp_ports})
                operation = conn.firewalls().insert(project=project, body=firewall_body).execute()
                self._wait_for_operation(operation)
            tags.extend([kube])
        if securitygroups:
            tags.extend(securitygroups)
        if lb is not None and lb.replace('.', '-') not in tags:
            tags.append(lb.replace('.', '-'))
        if tags:
            body['tags'] = {'items': tags}
        newval = {'key': 'serial-port-enable', 'value': 1}
        body['metadata']['items'].append(newval)
        if kubetype is not None:
            # Enable IP Forwarding on the VM instance
            # This is needed for K8s on GCP to leverage
            # VPC native routing which is the default from
            # K8s v1.21.0+. See: https://tinyurl.com/canIpForward
            body['canIpForward'] = True
            serviceaccounts = []
            for sa in overrides.get('serviceaccounts', []):
                if isinstance(sa, str):
                    email = f'{sa}@{self.project}.iam.gserviceaccount.com' if '@' not in sa else sa
                    serviceaccounts.append({'email': email, 'scopes': ['https://www.googleapis.com/auth/compute']})
                elif isinstance(sa, dict) and 'email' in sa:
                    if 'scope' not in sa:
                        sa['scopes'] = ['https://www.googleapis.com/auth/compute']
                    serviceaccounts.append(sa)
                else:
                    warning(f"Skipping invalid sa {sa}")
            if kubetype == 'openshift':
                serviceaccounts.append({'email': 'default',
                                        'scopes': ['https://www.googleapis.com/auth/cloud-platform']})
            if serviceaccounts:
                body['serviceAccounts'] = serviceaccounts
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
            integrity_monitoring = overrides.get('integrity_monitoring', False)
            body['shieldedInstanceConfig'] = {'enableIntegrityMonitoring': integrity_monitoring, 'enableVtpm': tpm,
                                              'enableSecureBoot': secureboot}
        if 'confidential' in overrides and overrides['confidential']:
            body['confidentialInstanceConfig'] = {'enableConfidentialCompute': True}
        if (overrides.get('spot', False) or
                (overrides.get('spot_ctlplanes', False) and 'ctlplane' in name) or
                (overrides.get('spot_workers', False) and 'worker' in name)):
            if 'scheduling' not in body:
                body['scheduling'] = {}
            body['scheduling']['provisioningModel'] = 'SPOT'
            if overrides.get('spot_delete', False):
                body['scheduling']['instanceTerminationAction'] = 'DELETE'
        if overrides.get('preemptible', False):
            if 'scheduling' not in body:
                body['scheduling'] = {}
            body['scheduling']['preemptible'] = True
        if overrides.get('router', False) or overrides.get('can_ip_forward', False):
            body['can_ip_forward'] = True
        try:
            conn.instances().insert(project=project, zone=zone, body=body).execute()
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias)
        if lb is not None:
            sane_lb = lb.replace('.', '-')
            self.update_metadata(name, 'loadbalancer', sane_lb, append=True)
            self.add_vm_to_loadbalancer(name, lb)
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

    def info_host(self):
        data = {}
        resource = build('cloudresourcemanager', 'v1')
        project = self.project
        zone = self.zone
        data['project'] = project
        projectinfo = resource.projects().get(projectId=project).execute()
        data['project_number'] = projectinfo['projectNumber']
        data['project_creation_time'] = projectinfo['createTime']
        data['zone'] = zone
        data['vms'] = len(self.list())
        return data

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
        vms = []
        zones = [self.zone] if self.specific_zone else self.list_zones(self.project)
        for zone in zones:
            instances = conn.instances().list(project=project, zone=zone).execute()
            instances_items = instances.get('items', [])
            for vm in instances_items:
                try:
                    vms.append(self.info(vm['name'], vm=vm))
                except:
                    continue
        if not vms:
            return []
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        project = self.project
        zone = self.zone
        resource = build('cloudresourcemanager', 'v1')
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
        if vm is None:
            try:
                vm = conn.instances().get(zone=self.zone, project=project, instance=name).execute()
            except:
                error(f"VM {name} not found")
                return {}
        zone = os.path.basename(vm['zone'])
        yamlinfo['name'] = vm['name']
        yamlinfo['status'] = vm['status']
        machinetype = os.path.basename(vm['machineType'])
        yamlinfo['flavor'] = machinetype
        if 'custom' in machinetype:
            yamlinfo['cpus'], yamlinfo['memory'] = machinetype.split('-')[1:]
        else:
            flavor_info = self.info_flavor(machinetype)
            yamlinfo['cpus'], yamlinfo['memory'] = flavor_info['cpus'], flavor_info['memory']
        yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        yamlinfo['az'] = zone
        first_nic = vm['networkInterfaces'][0]
        if 'accessConfigs' in first_nic and 'natIP' in first_nic['accessConfigs'][0]:
            yamlinfo['ip'] = first_nic['accessConfigs'][0]['natIP']
        if 'licenses' in vm['disks'][0]:
            yamlinfo['image'] = os.path.basename(vm['disks'][0]['licenses'][-1])
        else:
            source = os.path.basename(vm['disks'][0]['source'])
            source = conn.disks().get(zone=zone, project=self.project, disk=source).execute()
            if 'sourceImage' in source:
                yamlinfo['image'] = os.path.basename(source['sourceImage'])
        if 'image' in yamlinfo:
            yamlinfo['user'] = common.get_user(yamlinfo['image'])
        yamlinfo['creationdate'] = dateparser.parse(vm['creationTimestamp']).strftime("%d-%m-%Y %H:%M")
        nets = []
        ips = []
        for interface in vm['networkInterfaces']:
            network = os.path.basename(interface['network'])
            subnet = os.path.basename(interface['subnetwork']) if 'subnetwork' in interface else 'default'
            device = interface['name']
            private_ip = interface['networkIP'] if 'networkIP' in interface else 'N/A'
            yamlinfo['private_ip'] = private_ip
            if 'ip' not in yamlinfo and private_ip != 'N/A':
                yamlinfo['ip'] = private_ip
            ips.append(private_ip)
            private_ipv6 = interface.get('ipv6Address')
            if private_ipv6 is not None:
                ips.append(private_ipv6)
            nets.append({'device': device, 'mac': private_ip, 'net': network, 'type': subnet})
        if nets:
            yamlinfo['nets'] = nets
        if len(ips) > 1:
            yamlinfo['ips'] = ips
        disks = []
        for index, disk in enumerate(vm['disks']):
            devname = disk['deviceName']
            diskformat = disk['interface']
            drivertype = disk['type']
            path = os.path.basename(disk['source'])
            disksize = int(disk['diskSizeGb'])
            disks.append({'device': devname, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        if disks:
            yamlinfo['disks'] = disks
        if 'labels' in vm:
            for key in vm['labels']:
                if key in METADATA_FIELDS:
                    yamlinfo[key] = vm['labels'][key]
        if 'tags' in vm and 'items' in vm['tags']:
            yamlinfo['tags'] = ','.join(vm['tags']['items'])
        if 'guestAccelerators' in vm:
            accelerators = []
            for accelerator in vm['guestAccelerators']:
                accelerator_type = os.path.basename(accelerator['acceleratorType'])
                accelerator_count = accelerator['acceleratorCount']
                accelerators.append(f"{accelerator_count} {accelerator_type}")
            yamlinfo['accelerators'] = accelerators
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def ip(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            error(f"Vm {name} not found")
            return None
        if 'natIP' not in vm['networkInterfaces'][0]['accessConfigs'][0]:
            return vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        else:
            return vm['networkInterfaces'][0]['networkIP']

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
            image_items = results.get('items', [])
            for image in image_items:
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
        region = self.region
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        domain, dnsclient = None, None
        if 'labels' in vm:
            for key in vm['labels']:
                if key == 'domain':
                    domain = vm['labels'][key].replace('-', '.')
                if key == 'dnsclient':
                    dnsclient = vm['labels'][key]
        if domain is not None and dnsclient is None:
            self.delete_dns(name, domain)
        conn.instances().delete(zone=zone, project=project, instance=name).execute()
        try:
            operation = conn.addresses().delete(project=project, region=region, address=f'{name}-ip').execute()
            self._wait_for_operation(operation)
        except:
            pass
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def set_tags(self, name, tags):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return 1
        new_tags = vm['tags'].get('items', [])
        old_tags_number = len(new_tags)
        new_tags.extend(tags)
        new_tags = list(set(new_tags))
        new_tags_number = len(new_tags)
        if new_tags_number != old_tags_number:
            tags_body = {"fingerprint": vm['tags']['fingerprint'], "items": new_tags}
            conn.instances().setTags(project=project, zone=zone, instance=name, body=tags_body).execute()
        return 0

    def update_metadata(self, name, metatype, metavalue, append=False):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return 1
        labels = vm.get('labels', {})
        if metatype not in labels or labels[metatype] != metavalue:
            if metatype in labels and metavalue is None:
                del labels[metatype]
            else:
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

    def update_gpus(self, name, gpus):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error(f"Can't update gpus of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        if 'scheduling' not in vm:
            body = {'scheduling': {'preemptible': False, 'onHostMaintenance': 'TERMINATE'}}
            conn.instances().setScheduling(project=project, zone=zone, instance=name, body=body).execute()
        accelerators = []
        if len(gpus) > 1:
            return {'result': 'failure', 'reason': 'only a single accelerator type can be specified'}
        for accelerator in gpus:
            if isinstance(accelerator, str):
                accelerator_type = accelerator
                accelerator_count = 1
            elif isinstance(accelerator, dict):
                accelerator_type = accelerator.get('name') or accelerator.get('type')\
                    or accelerator.get('acceleratorType')
                if accelerator_type is None:
                    warning("Invalid accelerator {accelerator}")
                    continue
                accelerator_count = accelerator.get('count') or accelerator.get('acceleratorCount') or 1
            else:
                warning("Invalid accelerator {accelerator}")
                continue
            if self.project not in accelerator_type:
                accelerator_type = f"projects/{project}/zones/{zone}/acceleratorTypes/{accelerator_type}"
            new_accelerator = {'accelerator_type': accelerator_type, 'accelerator_count': accelerator_count}
            accelerators.append(new_accelerator)
        if accelerators:
            body = {'guestAccelerators': accelerators}
            conn.instances().setMachineResources(project=project, zone=zone, instance=name, body=body).execute()
        return {'result': 'success'}

    def update_reserveip(self, name):
        conn = self.conn
        project = self.project
        region = self.region
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except Exception:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['status'] in ['RUNNING', 'STOPPING']:
            error(f"Can't update cpus of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        nic = vm['networkInterfaces'][0]
        access_config = nic['accessConfigs'][0]
        access_config_name = access_config['name']
        nic = nic['name']
        address_body = {"name": f'{name}-ip', "addressType": 'EXTERNAL'}
        operation = self.conn_beta.addresses().insert(project=project, region=region, body=address_body).execute()
        self._wait_for_operation(operation)
        address = self.conn_beta.addresses().get(project=project, region=region, address=f'{name}-ip').execute()
        access_config['natIP'] = address['address']
        conn.instances().deleteAccessConfig(project=project, zone=zone, instance=name, networkInterface=nic,
                                            accessConfig=access_config_name).execute()
        conn.instances().addAccessConfig(project=project, zone=zone, instance=name, networkInterface=nic,
                                         body=access_config).execute()
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        conn = self.conn
        project = self.project
        zone = self.zone
        body = {'sizeGb': size, 'name': name}
        conn.disks().insert(zone=zone, project=project, body=body).execute()
        timeout = 0
        while True:
            if timeout > 60:
                return {'result': 'failure', 'reason': 'timeout waiting for new disk to be ready'}
            newdisk = conn.disks().get(zone=zone, project=project, disk=name).execute()
            if newdisk['status'] == 'READY':
                break
            else:
                timeout += 5
                sleep(5)
                pprint("Waiting for disk to be ready")
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}, diskname=None):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        numdisks = len(vm['disks']) + 1
        diskname = f"{name}-disk{numdisks}"
        body = {'sizeGb': size, 'name': diskname}
        disk_type = overrides.get('diskinterface') or overrides.get('disktype')
        if disk_type is not None:
            body['diskType'] = disk_type
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
        if novm:
            try:
                conn.disks().delete(zone=zone, project=project, disk=diskname).execute()
            except Exception as e:
                error(e)
                return {'result': 'failure', 'reason': e}
            return {'result': 'success'}
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        for disk in vm['disks']:
            devname = disk['deviceName']
            source = os.path.basename(disk['source'])
            if devname == diskname or source == diskname:
                operation = conn.instances().detachDisk(project=project, zone=zone, instance=name,
                                                        deviceName=devname).execute()
                self._wait_for_operation(operation)
                try:
                    conn.disks().delete(zone=zone, project=project, disk=diskname).execute()
                except Exception as e:
                    error(e)
                    return {'result': 'failure', 'reason': e}
                break
        return {'result': 'success'}

    def list_disks(self):
        disks = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        alldisks = conn.disks().list(zone=zone, project=project).execute()
        alldisks_items = alldisks.get('items', [])
        for disk in alldisks_items:
            if self.debug:
                print(disk)
            diskname = disk['name']
            pool = os.path.basename(disk['type'])
            disks[diskname] = {'pool': pool, 'path': zone}
        return disks

    def add_nic(self, name, network, model='virtio'):
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

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
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
        ipv6 = overrides.get('ipv6', False)
        dual_cidr = None
        subnet_body = {}
        cidr = overrides.get('subnet_cidr') or cidr
        if cidr is not None:
            try:
                network = ip_network(cidr, strict=False)
            except:
                return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
            if str(network.version) == "6":
                msg = 'Primary cidr needs to be ipv4 in GCP. Set ipv6 to true to enable it'
                return {'result': 'failure', 'reason': msg}
            subnet_body = {'name': f'{name}-subnet1', 'ipCidrRange': cidr}
            if 'dual_cidr' in overrides:
                dual_cidr = overrides['dual_cidr']
                try:
                    dual_network = ip_network(dual_cidr, strict=False)
                    dual_cidr_version = str(dual_network.version)
                    if dual_cidr_version == "4":
                        return {'result': 'failure', 'reason': "cidr and dual_cidr must be of different types"}
                except:
                    return {'result': 'failure', 'reason': f"Invalid Dual Cidr {dual_cidr}"}
                subnet_body["ipv6_cidr_range"] = dual_cidr
                subnet_body['stack_type'] = 'IPV4_IPV6'
                subnet_body['ipv6AccessType'] = 'INTERNAL' if is_ula(dual_cidr) else 'EXTERNAL'
        conn = self.conn
        project = self.project
        region = self.region
        networks = self.list_networks()
        if name in networks:
            msg = f"Network {name} already exists"
            return {'result': 'failure', 'reason': msg}
        body = {'name': name, 'autoCreateSubnetworks': cidr is None}
        body['enableUlaInternalIpv6'] = ipv6 or (dual_cidr is not None and is_ula(dual_cidr))
        operation = conn.networks().insert(project=project, body=body).execute()
        self._wait_for_operation(operation)
        allowed = {"IPProtocol": "tcp", "ports": ["22"]}
        firewall_body = {'name': f'allow-ssh-{name}', 'network': f'global/networks/{name}',
                         'sourceRanges': ['0.0.0.0/0'], 'allowed': [allowed]}
        conn.firewalls().insert(project=project, body=firewall_body).execute()
        if ipv6 and dual_cidr is None:
            ipv6_cidr = conn.networks().get(project=project, network=name).execute()['internalIpv6Range']
            ipv6_subnet_cidr = ipv6_cidr.replace('/48', '/64')
            pprint(f"Using {ipv6_cidr} as IPV6 main cidr")
            subnet_body["ipv6_cidr_range"] = ipv6_subnet_cidr
            subnet_body['stack_type'] = 'IPV4_IPV6'
            subnet_body['ipv6AccessType'] = 'INTERNAL'
        if not subnet_body:
            return {'result': 'success'}
        pprint(f"Creating first subnet {name}-subnet1")
        networkpath = operation["targetLink"]
        regionpath = f"https://www.googleapis.com/compute/v1/projects/{project}/regions/{region}"
        subnet_body.update({'network': networkpath, "region": regionpath})
        if 'secondary_cidr' in overrides:
            secondary_cidr = overrides['secondary_cidr']
            try:
                ip_network(secondary_cidr)
            except:
                return {'result': 'failure', 'reason': f"Invalid Secondary Cidr {secondary_cidr}"}
            secondary_name = overrides.get('secondary_name') or f"secondary-{name}"
            subnet_body['secondaryIpRanges'] = [{"rangeName": secondary_name, "ipCidrRange": secondary_cidr}]
        operation = conn.subnetworks().insert(region=region, project=project, body=subnet_body).execute()
        self._wait_for_operation(operation)
        subnet = f"projects/{project}/regions/{region}/subnetworks/{name}-subnet1"
        router_resource = {"name": name, "network": f"projects/{project}/global/networks/{name}", "region": region,
                           "nats": [{"name": name, "nat_ip_allocate_option": "AUTO_ONLY",
                                     "source_subnetwork_ip_ranges_to_nat": "LIST_OF_SUBNETWORKS",
                                     "subnetworks": [{'name': subnet}]}]}
        operation = self.router_client.insert(project=project, region=region, router_resource=router_resource)
        operation.result()
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        conn = self.conn
        project = self.project
        region = self.region
        try:
            network = conn.networks().get(project=project, network=name).execute()
        except:
            return {'result': 'failure', 'reason': f"Network {name} not found"}
        if name in [r.name for r in self.router_client.list(project=project, region=region)]:
            operation = self.router_client.delete(project=project, region=region, router=name)
            operation.result()
        if not network['autoCreateSubnetworks'] and 'subnetworks' in network:
            for subnet in network['subnetworks']:
                subnetwork = os.path.basename(subnet)
                self.delete_subnet(subnetwork)
        try:
            operation = conn.firewalls().delete(project=project, firewall=f'allow-ssh-{name}').execute()
            self._wait_for_operation(operation)
        except:
            pass
        operation = conn.networks().delete(project=project, network=name).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

    def list_pools(self):
        print("not implemented")
        return []

    def list_project_networks(self, project):
        networks = {}
        region = self.region
        conn = self.conn
        try:
            nets = conn.networks().list(project=project).execute()
        except:
            return {}
        nets_items = nets.get('items', [])
        for net in nets_items:
            networkname = net['name']
            cidr = net['IPv4Range'] if 'IPv4Range' in net else ''
            dhcp = True
            domainname = ''
            mode = ''
            if cidr == '':
                try:
                    subnet = conn.subnetworks().get(region=region, project=project, subnetwork=networkname).execute()
                    cidr = subnet['ipCidrRange']
                except:
                    pass
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
        return networks

    def list_networks(self):
        networks = {}
        projects = [self.project]
        if self.xproject is not None:
            projects.append(self.xproject)
        for project in projects:
            networks.update(self.list_project_networks(project))
        return networks

    def info_network(self, name):
        project = self.project
        networkinfo = common.info_network(self, name)
        if self.debug and networkinfo:
            network = self.conn.networks().get(project=project, network=name).execute()
            print(network)
        return networkinfo

    def list_subnets(self):
        subnets = {}
        conn = self.conn
        region = self.region
        projects = [self.project]
        if self.xproject is not None:
            projects.append(self.xproject)
        for project in projects:
            try:
                response = conn.subnetworks().list(region=region, project=project).execute()
            except:
                continue
            subnets_data = response.get('items', [])
            if subnets_data:
                for subnet in subnets_data:
                    if self.debug:
                        print(subnet)
                    subnetname = subnet['name']
                    networkname = os.path.basename(subnet['network'])
                    cidr = subnet.get('internalIpv6Prefix') or subnet['ipCidrRange']
                    region = os.path.basename(subnet['region'])
                    subnets[subnetname] = {'cidr': cidr, 'az': region, 'id': project, 'network': networkname}
            response = conn.networks().list(project=project).execute()
            nets_data = response.get('items', [])
            if nets_data:
                for net in nets_data:
                    networkname = net['name']
                    if 'subnetworks' in net:
                        for subnet in net['subnetworks']:
                            if self.debug:
                                print(subnet)
                            subnetname = os.path.basename(subnet)
                            region = re.match('.*regions/(.*)/subnetworks.*', subnet).group(1)
                            if subnetname not in subnets:
                                subnet_data = conn.subnetworks().get(region=region, project=project,
                                                                     subnetwork=subnetname).execute()
                                subnets[subnetname] = {'cidr': subnet_data['ipCidrRange'], 'id': project, 'az': region,
                                                       'network': networkname}
        return subnets

    def get_subnet(self, subnetwork):
        subnet = {}
        conn = self.conn
        region = self.region
        project = [self.project]
        if self.xproject is not None:
            project = self.xproject
        response = conn.subnetworks().get(region=region, project=project, subnetwork=subnetwork).execute()
        if response:
            subnet = response
        return subnet

    def delete_pool(self, name, full=False):
        print("not implemented")
        return

    def network_ports(self, name):
        return []

    def vm_ports(self, name):
        subnets = []
        try:
            vm = self.conn.instances().get(zone=self.zone, project=self.project, instance=name).execute()
        except:
            error(f"VM {name} not found")
            return []
        for interface in vm['networkInterfaces']:
            if 'subnetwork' in interface:
                subnets.append(os.path.basename(interface['subnetwork']))
        return subnets

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
        if domain is None and (name.startswith('apps.') or name.startswith('api.')):
            split = name.split('.')
            domain = '.'.join(split[2:])
            name = name.replace(f'.{domain}', '')
            pprint(f"Using domain {domain}")
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
        if domain is None and (name.startswith('apps.') or name.startswith('api.')):
            split = name.split('.')
            domain = '.'.join(split[2:])
            name = name.replace(f'.{domain}', '')
            pprint(f"Using domain {domain}")
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

    def info_flavor(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        if name in self.machine_flavor_cache:
            flavor = self.machine_flavor_cache[name]
        else:
            flavor = conn.machineTypes().get(project=project, zone=zone, machineType=name).execute()
            self.machine_flavor_cache[name] = flavor
        return {'cpus': flavor['guestCpus'], 'memory': flavor['memoryMb']}

    def list_flavors(self):
        conn = self.conn
        project = self.project
        zone = self.zone
        flavors = []
        results = conn.machineTypes().list(project=project, zone=zone).execute()
        flavors_items = results.get('items', [])
        for flavor in flavors_items:
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
                            internal=False, dnsclient=None, ip=None):
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
        use_xproject = False
        if not vms:
            msg = "Creating a load balancer requires to specify vms"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        need_subnet = False
        instancegroup = None
        instancegroups = [n['name'] for n in conn.instanceGroups().list(project=project,
                                                                        zone=zone).execute().get('items', [])]
        for index, vm in enumerate(vms):
            info = self.info(vm)
            if not info:
                msg = f"Vm {vm} not found"
                return {'result': 'failure', 'reason': msg}
            loadbalancer = info.get('loadbalancer')
            if loadbalancer is not None and loadbalancer in instancegroups:
                instancegroup = loadbalancer
            else:
                self.update_metadata(vm, 'loadbalancer', sane_name)
                instances.append({"instance": f"{vmpath}/{vm}"})
            self.set_tags(vm, [sane_name])
            if index == 0:
                network = info['nets'][0]['net']
                subnet = info['nets'][0]['type']
                if subnet != 'default':
                    network_project = self.list_subnets()[subnet]['id']
                    if network_project == self.xproject:
                        use_xproject = True
                        subnet = f'projects/{network_project}/regions/{region}/subnetworks/{subnet}'
                    else:
                        subnet = f"projects/{project}/regions/{region}/subnetworks/{subnet}"
                    need_subnet = lb_scheme == 'INTERNAL'
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
        if instancegroup is None:
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
        else:
            operation = conn.instanceGroups().get(project=project, zone=zone, instanceGroup=instancegroup).execute()
            instances_group_url = operation['selfLink']
        backend_body = {"name": sane_name, "backends": [{"group": instances_group_url}],
                        "loadBalancingScheme": lb_scheme, "protocol": "TCP", "healthChecks": [healthurl]}
        if need_subnet:
            backend_body['subnetwork'] = subnet
        pprint(f"Creating backend service {sane_name}")
        operation = conn.regionBackendServices().insert(project=project, region=region, body=backend_body).execute()
        backendurl = operation['targetLink']
        self._wait_for_operation(operation)
        if ip is None:
            address_body = {"name": sane_name, "addressType": lb_scheme}
            if need_subnet:
                address_body['subnetwork'] = subnet
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
        else:
            ipurl = ip
        pprint(f"Using load balancer ip {ip}")
        self._wait_for_operation(operation)
        forwarding_name = sane_name
        forwarding_rule_body = {"IPAddress": ipurl, "name": forwarding_name}
        forwarding_rule_body["backendService"] = backendurl
        forwarding_rule_body["IPProtocol"] = "TCP"
        forwarding_rule_body["ports"] = ports
        forwarding_rule_body["loadBalancingScheme"] = lb_scheme
        if use_xproject or need_subnet:
            forwarding_rule_body["subnetwork"] = subnet
        pprint(f"Creating forwarding rule {forwarding_name}")
        operation = conn.forwardingRules().insert(project=project, region=region, body=forwarding_rule_body).execute()
        self._wait_for_operation(operation)
        if not use_xproject:
            allowed_ports = ports
            if checkport not in allowed_ports:
                allowed_ports.append(checkport)
            network = f"global/networks/{network}"
            firewall_body = {"name": sane_name, "network": network, "direction": "INGRESS", "targetTags": [sane_name],
                             "allowed": [{"IPProtocol": "tcp", "ports": allowed_ports}]}
            pprint(f"Creating firewall rule {sane_name}")
            operation = conn.firewalls().insert(project=project, body=firewall_body).execute()
            self._wait_for_operation(operation)
        if domain is not None:
            if dnsclient is not None:
                return ip
            pprint(f"Creating DNS {name}.{domain}")
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
        firewall_rules_items = firewall_rules.get('items', [])
        for firewall_rule in firewall_rules_items:
            firewall_rule_name = firewall_rule['name']
            if firewall_rule_name == name:
                pprint(f"Deleting firewall rule {name}")
                operation = conn.firewalls().delete(project=project, firewall=name).execute()
                self._wait_for_operation(operation)
        forwarding_rules = conn.forwardingRules().list(project=project, region=region).execute()
        forwarding_rules_items = forwarding_rules.get('items', [])
        for forwarding_rule in forwarding_rules_items:
            forwarding_rule_name = forwarding_rule['name']
            if forwarding_rule_name == name or forwarding_rule_name.startswith(f'{name}-'):
                pprint(f"Deleting forwarding rule {forwarding_rule_name}")
                operation = conn.forwardingRules().delete(project=project, region=region,
                                                          forwardingRule=forwarding_rule_name).execute()
                self._wait_for_operation(operation)
                pprint("Waiting to make sure forwarding rule is gone")
                timeout = 0
                while True:
                    if timeout >= 60:
                        warning("Timeout waiting for forwarding rule to be gone")
                        break
                    new_forwarding_rules = conn.forwardingRules().list(project=project, region=region).execute()
                    items = new_forwarding_rules.get('items', [])
                    if not items or not [f for f in items if f['name'] == forwarding_rule_name]:
                        break
                    else:
                        sleep(5)
                        timeout += 5
        try:
            address = conn_beta.addresses().get(project=project, region=region, address=name).execute()
            if 'labels' in address and 'domain' in address['labels'] and 'dnsclient' not in address['labels']:
                domain = address["labels"]["domain"].replace('-', '.')
                dns_name = name
                if name.startswith('api-') or name.startswith('apps-'):
                    dns_name = name.replace('api-', 'api.').replace('apps-', 'apps.')
                pprint(f"Deleting DNS {name}.{domain}")
                self.delete_dns(dns_name, domain=domain)
            pprint(f"Deleting address {name}")
            operation = conn.addresses().delete(project=project, region=region, address=name).execute()
            self._wait_for_operation(operation)
        except Exception as e:
            if self.debug:
                print(e)
            pass
        backendservices = conn.regionBackendServices().list(project=project, region=region).execute()
        backendservices_items = backendservices.get('items', [])
        for backendservice in backendservices_items:
            backendservice_name = backendservice['name']
            if backendservice_name == name:
                pprint(f"Deleting backend service {name}")
                operation = conn.regionBackendServices().delete(project=project, region=region,
                                                                backendService=name).execute()
                self._wait_for_operation(operation)
        regionhealthchecks = conn.regionHealthChecks().list(project=project, region=region).execute()
        regionhealthchecks_items = regionhealthchecks.get('items', [])
        for healthcheck in regionhealthchecks_items:
            healthcheck_name = healthcheck['name']
            if healthcheck_name == name:
                pprint(f"Deleting healthcheck {name}")
                operation = conn.regionHealthChecks().delete(project=project, region=region, healthCheck=name).execute()
                self._wait_for_operation(operation)
        healthchecks = conn.healthChecks().list(project=project).execute()
        healthchecks_items = healthchecks.get('items', [])
        for healthcheck in healthchecks_items:
            healthcheck_name = healthcheck['name']
            if healthcheck_name == name:
                pprint(f"Deleting healthcheck {name}")
                operation = conn.healthChecks().delete(project=project, healthCheck=name).execute()
                self._wait_for_operation(operation)
        instancegroups = conn.instanceGroups().list(project=project, zone=zone).execute()
        instancegroups_items = instancegroups.get('items', [])
        for instancegroup in instancegroups_items:
            instancegroup_name = instancegroup['name']
            if instancegroup_name == name:
                pprint(f"Deleting instance group {name}")
                try:
                    operation = conn.instanceGroups().delete(project=project, zone=zone, instanceGroup=name).execute()
                    self._wait_for_operation(operation)
                except Exception as e:
                    warning(f"Hit {e} when deleting instance group {name}")
                    pass
        if dnsclient is not None:
            return dnsclient
        return {'result': 'success'}

    def list_loadbalancers(self):
        conn = self.conn
        project = self.project
        region = self.region
        results = []
        global_forwarding_rules = conn.globalForwardingRules().list(project=project).execute()
        global_forwarding_rules_items = global_forwarding_rules.get('items', [])
        forwarding_rules = conn.forwardingRules().list(project=project, region=region).execute()
        forwarding_rules_items = forwarding_rules.get('items', [])
        for lb in global_forwarding_rules_items:
            name = lb['name']
            ip = lb['IPAddress']
            protocol = lb['IPProtocol']
            port = lb['port']
            target = os.path.basename(lb['target'])
            results.append([name, ip, protocol, port, target])
        for lb in forwarding_rules_items:
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

    def update_security_group(self, name, overrides={}):
        conn = self.conn
        project = self.project
        try:
            firewall = conn.firewalls().get(project=project, firewall=name).execute()
        except:
            msg = f"Firewall {name} not found"
            return {'result': 'failure', 'reason': msg}
        existing_ports = []
        allowed = firewall['allowed']
        for rule in allowed:
            for port in rule.get('ports', []):
                if '-' in port:
                    start_port, end_port = port.split('-')
                    existing_ports.extend([int(port) for port in range(int(start_port), int(end_port) + 1)])
                else:
                    existing_ports.append(int(port))
        if 'ports' in overrides:
            overrides['rules'] = {"ports": overrides['ports']}
            if 'cidr' in overrides:
                overrides['rules']["cidr"] = overrides['cidr']
        for route in overrides.get('rules', []):
            cidr = route.get('cidr')
            if cidr is not None:
                warning("cidr is not used in GCP firewalls")
            ports = [str(port) for port in route.get('ports', []) if port not in existing_ports]
            if ports:
                allowed.append({"IPProtocol": "tcp", "ports": ports})
                operation = conn.firewalls().patch(project=project, firewall=name, body={'allowed': allowed}).execute()
                self._wait_for_operation(operation)
        return {'result': 'success'}

    def update_aliases(self, name, cidr):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        fingerprint = vm['networkInterfaces'][0]['fingerprint']
        vm_subnetwork = vm['networkInterfaces'][0]['subnetwork']
        vm_subnetwork_name = vm_subnetwork.split('/')[-1]
        subnet = self.get_subnet(vm_subnetwork_name)
        cidr_name = subnet['secondaryIpRanges'][0]['rangeName']
        body = {"aliasIpRanges": [{"ipCidrRange": cidr, "subnetworkRangeName": cidr_name}], "fingerprint": fingerprint}
        operation = self.conn.instances().updateNetworkInterface(project=project, zone=zone, instance=name,
                                                                 networkInterface='nic0', body=body).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

    def info_subnet(self, name):
        result = {}
        project = self.project
        xproject = self.xproject
        region = self.region
        try:
            subnet = self.conn.subnetworks().get(region=region, project=project, subnetwork=name).execute()
        except:
            msg = f"Subnet {name} not found"
            if xproject is not None:
                try:
                    subnet = self.conn.subnetworks().get(region=region, project=xproject, subnetwork=name).execute()
                except:
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
            else:
                error(msg)
                return {'result': 'failure', 'reason': msg}
        if self.debug:
            print(subnet)
        primary_range = 'ipCidrRange'
        cidr = subnet.get('ipCidrRange')
        if cidr is None:
            primary_range = 'internalIpv6Prefix'
            cidr = subnet.get(primary_range)
        result = {'cidr': cidr, 'id': project, 'network': os.path.basename(subnet['network'])}
        dual_cidr = subnet.get('internalIpv6Prefix' if primary_range == 'ipCidrRange' else 'ipCidrRange')
        if dual_cidr is not None:
            result['dual_cidr'] = dual_cidr
        secondary_cidrs = [entry['ipCidrRange'] for entry in subnet.get('secondaryIpRanges', [])]
        if secondary_cidrs:
            result['secondary_cidrs'] = secondary_cidrs
        return result

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        conn = self.conn
        project = self.project
        region = self.region
        network_name = overrides.get('network', name)
        if network_name not in self.list_networks():
            msg = f'Network {network_name} not found'
            return {'result': 'failure', 'reason': msg}
        try:
            network = ip_network(cidr)
            cidr_version = str(network.version)
        except:
            return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
        networkpath = self.conn.networks().get(project=project, network=network_name).execute()['selfLink']
        regionpath = f"https://www.googleapis.com/compute/v1/projects/{project}/regions/{region}"
        cidr_type = "ipv6_cidr_range" if cidr_version == '6' else "ipCidrRange"
        subnet_body = {'name': name, cidr_type: cidr, 'network': networkpath, "region": regionpath}
        if 'dual_cidr' in overrides:
            dual_cidr = overrides['dual_cidr']
            try:
                dual_network = ip_network(dual_cidr, strict=False)
                dual_cidr_version = str(dual_network.version)
                if dual_cidr_version == cidr_version:
                    return {'result': 'failure', 'reason': "cidr and dual_cidr must be of different types"}
            except:
                return {'result': 'failure', 'reason': f"Invalid Dual Cidr {dual_cidr}"}
            dual_cidr_type = "ipv6_cidr_range" if cidr_type == 'ipCidrRange' else "ipCidrRange"
            subnet_body[dual_cidr_type] = dual_cidr
            subnet_body['stack_type'] = 'IPV4_IPV6'
        if 'ipCidrRange' not in subnet_body:
            return {'result': 'failure', 'reason': "Missing Ipv4 Cidr. GCP doesnt support IPV6 only subnets"}
        ipv6 = cidr_type == 'ipv6_cidr_range' or ('dual_cidr' in overrides and dual_cidr_type == "ipv6_cidr_range")
        if ipv6:
            subnet_body['ipv6AccessType'] = 'INTERNAL' if is_ula(dual_cidr) else 'EXTERNAL'
        if 'secondary_cidr' in overrides:
            secondary_cidr = overrides['secondary_cidr']
            try:
                ip_network(secondary_cidr)
            except:
                return {'result': 'failure', 'reason': f"Invalid Secondary Cidr {secondary_cidr}"}
            secondary_name = overrides.get('secondary_name') or f"secondary-{name}"
            subnet_body['secondaryIpRanges'] = [{"rangeName": secondary_name, "ipCidrRange": secondary_cidr}]
        operation = conn.subnetworks().insert(region=region, project=project, body=subnet_body).execute()
        self._wait_for_operation(operation)
        if nat and network_name in [r.name for r in self.router_client.list(project=project, region=region)]:
            subnet = f"projects/{project}/regions/{region}/subnetworks/{name}"
            router_resource = self.router_client.get(project=project, region=region, router=network_name)
            router_resource.nats[0].subnetworks.append({'name': subnet})
            operation = self.router_client.update(project=project, region=region, router=network_name,
                                                  router_resource=router_resource)
            operation.result()
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        conn = self.conn
        project = self.project
        region = self.region
        subnets = self.list_subnets()
        if name not in subnets:
            msg = f'Subnet {name} not found'
            return {'result': 'failure', 'reason': msg}
        network_name = subnets[name]['network']
        if network_name in [r.name for r in self.router_client.list(project=project, region=region)]:
            subnet = f"projects/{project}/regions/{region}/subnetworks/{name}"
            router_resource = self.router_client.get(project=project, region=region, router=network_name)
            current_subnetworks = router_resource.nats[0].subnetworks
            router_resource.nats[0].subnetworks = [s for s in current_subnetworks if not s.name.endswith(subnet)]
            operation = self.router_client.update(project=project, region=region, router=network_name,
                                                  router_resource=router_resource)
            operation.result()
        operation = conn.subnetworks().delete(region=region, project=project, subnetwork=name).execute()
        self._wait_for_operation(operation)
        return {'result': 'success'}

    def delete_service_accounts(self, name):
        iam = self.iam
        accounts = iam.projects().serviceAccounts().list(name=f'projects/{self.project}').execute().get('accounts', [])
        for account in accounts:
            if account['name'].startswith(f'projects/{self.project}/serviceAccounts/{name}')\
               and account['displayName'].startswith(name) and account['email'].startswith(name):
                iam.projects().serviceAccounts().delete(name=account['name']).execute()

    def update_subnet(self, name, overrides={}):
        conn = self.conn
        project = self.project
        try:
            conn.networks().get(project=project, network=name).execute()
            network_name = name
        except:
            subnets = self.list_subnets()
            if name not in subnets:
                msg = f'Subnet {name} not found'
                return {'result': 'failure', 'reason': msg}
            else:
                network_name = subnets[name]['network']
        routes = self.routes_client.list(project=project)
        network_path = f'projects/{project}/global/networks/{network_name}'
        existing_cidrs = [route.dest_range for route in routes if route.network.endswith(network_path)]
        if 'cidr' in overrides and 'vm' in overrides:
            overrides['routes'] = {"cidr": overrides['cidr'], "vm": overrides['vm']}
        for route in overrides.get('routes', []):
            cidr = route.get('cidr')
            vm = route.get('vm')
            if vm is not None and cidr is not None:
                if cidr in existing_cidrs:
                    warning(f"cidr {cidr} already in route table")
                    continue
                try:
                    ip_network(cidr, strict=False)
                except:
                    return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
                try:
                    vm = conn.instances().get(zone=self.zone, project=project, instance=vm).execute()
                except:
                    return {'result': 'failure', 'reason': f"Vm {vm} not found"}
                self_link = vm['selfLink']
                route_name = f"kcli-{cidr.replace('.', '-').replace('/', '-')}"
                route_resource = {'name': route_name, 'dest_range': cidr, 'network': network_path,
                                  'next_hop_instance': self_link, 'priority': 100, 'description': route_name}
                self.routes_client.insert(project=project, route_resource=route_resource)
        return {'result': 'success'}

    def list_dns_zones(self):
        project = self.project
        client = dns.Client(project)
        return [z.dns_name for z in client.list_zones()]

    def set_router_mode(self, name, mode=True):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        vm['can_ip_forward'] = mode
        conn.instances().update(zone=zone, project=project, instance=name, body=vm).execute()

    def add_vm_to_loadbalancer(self, vm, lb):
        sane_name = lb.replace('.', '-')
        conn = self.conn
        project = self.project
        zone = self.zone
        vmpath = f"https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/instances"
        instances_body = {"instances": [{"instance": f"{vmpath}/{vm}"}]}
        operation = conn.instanceGroups().addInstances(project=project, zone=zone, instanceGroup=sane_name,
                                                       body=instances_body).execute()
        self._wait_for_operation(operation)
