#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ipaddress import ip_network
from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import METADATA_FIELDS
from ibm_vpc import VpcV1, vpc_v1
import ibm_boto3
from ibm_botocore.client import Config
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core.api_exception import ApiException
from ibm_platform_services import GlobalTaggingV1, ResourceControllerV2, IamPolicyManagementV1, IamIdentityV1
from ibm_platform_services.iam_policy_management_v1 import PolicySubject, SubjectAttribute, PolicyResource, PolicyRole
from ibm_platform_services.iam_policy_management_v1 import ResourceAttribute
from ibm_cloud_networking_services import DnsRecordsV1, ZonesV1
import json
import os
from shutil import which
from time import sleep
from urllib.request import urlopen, Request
import webbrowser


def get_zone_href(region, zone):
    return f"https://{region}.iaas.cloud.ibm.com/v1/regions/{region}/zones/{zone}"


def get_s3_endpoint(region):
    return f'https://s3.{region}.cloud-object-storage.appdomain.cloud'


def get_service_instance_id(iam_api_key, name):
    if 'crn' in name:
        return name
    service_id = None
    headers = {'content-type': 'application/x-www-form-urlencoded', 'accept': 'application/json'}
    data = 'grant_type=urn%%3Aibm%%3Aparams%%3Aoauth%%3Agrant-type%%3Aapikey&apikey=%s' % iam_api_key
    data = data.encode()
    req = Request("https://iam.cloud.ibm.com/identity/token", headers=headers, method='POST', data=data)
    token = json.loads(urlopen(req).read().decode())['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    req = Request("https://resource-controller.cloud.ibm.com/v2/resource_instances", headers=headers)
    for entry in json.loads(urlopen(req).read())['resources']:
        if entry['name'] == name:
            service_id = entry['id']
            break
    return service_id


class Kibm(object):
    """

    """
    def __init__(self, iam_api_key, region, zone, vpc, debug=False, cos_api_key=None, cos_resource_instance_id=None,
                 cis_resource_instance_id=None):
        self.debug = debug
        self.authenticator = IAMAuthenticator(iam_api_key)
        self.iam_api_key = iam_api_key
        self.conn = VpcV1(authenticator=self.authenticator)
        self.conn.set_service_url(f"https://{region}.iaas.cloud.ibm.com/v1")
        if cos_api_key is not None and cos_resource_instance_id is not None:
            cos_resource_instance_id = get_service_instance_id(iam_api_key, cos_resource_instance_id)
            self.s3 = ibm_boto3.client(
                's3',
                ibm_api_key_id=cos_api_key,
                ibm_service_instance_id=cos_resource_instance_id,
                ibm_auth_endpoint="https://iam.bluemix.net/oidc/token",
                config=Config(signature_version="oauth"),
                endpoint_url=get_s3_endpoint(region)
            )
            self.cos_resource_instance_id = cos_resource_instance_id
        self.global_tagging_service = GlobalTaggingV1(authenticator=self.authenticator)
        self.global_tagging_service.set_service_url('https://tags.global-search-tagging.cloud.ibm.com')
        if cis_resource_instance_id is not None:
            cis_resource_instance_id = get_service_instance_id(iam_api_key, cis_resource_instance_id)
            self.dns = ZonesV1(authenticator=self.authenticator, crn=cis_resource_instance_id)
            self.dns.set_service_url('https://api.cis.cloud.ibm.com')
            self.cis_resource_instance_id = cis_resource_instance_id
        self.resources = ResourceControllerV2(authenticator=self.authenticator)
        self.resources.set_service_url('https://resource-controller.cloud.ibm.com')
        self.iam_api_key = iam_api_key
        self.region = region
        self.zone = zone if region in zone else f"{region}-2"
        self.vpc = vpc

    def close(self):
        return

    def exists(self, name):
        try:
            return self._get_vm(name) is not None
        except ApiException as e:
            error(f"Unable to retrieve VM. Hit {e}")
            return False

    def net_exists(self, name):
        try:
            return self._get_subnet(name) is not None
        except ApiException as e:
            error(f"Unable to retrieve available subnets. Hit {e}")
            return False

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt',
               cpumodel='host-model', cpuflags=[], cpupinning=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=[], iso=None, vnc=True,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=[], cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=[], storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False,
               placement=[], autostart=False, rng=False, metadata={}, securitygroups=[], vmuser=None):
        try:
            vpcs = self.conn.list_vpcs().result['vpcs']
            for vpc in vpcs:
                if self.vpc == vpc['name']:
                    vpc_id = vpc['id']
                    resource_group_id = vpc['resource_group']['id']
                    break
            else:
                return {'result': 'failure', 'reason': f'VPC {self.vpc} does not exist'}
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve vpc information. Hit {e}'}
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        key_list = []
        try:
            pub_ssh_keys = [x['id'] for x in self.conn.list_keys().result['keys']]
            if not pub_ssh_keys:
                resource_group = {'id': resource_group_id}
                publickeyfile = get_ssh_pub_key()
                if publickeyfile is None:
                    return {'result': 'failure', 'reason': 'Unable to use a valid public ssh key'}
                pprint("Adding a default ssh public key named kvirt")
                identityfile = publickeyfile.replace('.pub', '')
                _type = identityfile.split('_')[-1]
                public_key = open(publickeyfile).read()
                new_key = self.conn.create_key(public_key, name='kvirt', resource_group=resource_group, type=_type)
                pub_ssh_keys.append(new_key.result['id'])
            for key in pub_ssh_keys:
                key_list.append(key)
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to check keys. Hit {e}'}
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
        else:
            userdata = ''
        if len(nets) == 0:
            return {'result': 'failure', 'reason': 'Network not found in configuration'}
        net_list = []
        subnets = {x['name']: x for x in self._get_subnets()}
        try:
            default_subnet = None
            subnets = {}
            for x in self._get_subnets():
                subnet_name = x['name']
                subnets[subnet_name] = x
                if x['vpc']['name'] == self.vpc and x['zone']['name'] == self.zone:
                    default_subnet = subnet_name
            for index, net in enumerate(nets):
                if isinstance(net, str):
                    netname = net
                elif isinstance(net, dict) and 'name' in net:
                    netname = net['name']
                if netname == 'default' or netname == self.vpc:
                    netname = default_subnet
                elif netname not in subnets:
                    return {'result': 'failure', 'reason': f'Network {netname} not found'}
                subnet = subnets[netname]
                if subnet['zone']['name'] != self.zone:
                    return {'result': 'failure', 'reason': f'Network {netname} is not in zone {self.zone}'}
                net_list.append(vpc_v1.NetworkInterfacePrototype(subnet=vpc_v1.SubnetIdentityById(id=subnet['id']),
                                                                 allow_ip_spoofing=False, name=f"eth{index}"))
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to check networks. Hit {e}'}
        if flavor is None:
            flavors = [f for f in self.list_flavors() if f[1] >= numcpus and f[2] * 1024 >= memory]
            if flavors:
                flavor = min(flavors, key=lambda f: f[2])[0]
                pprint(f"Using flavor {flavor}")
            else:
                return {'result': 'failure', 'reason': "Couldn't find a flavor matching cpu/memory requirements"}
        try:
            provisioned_profiles = self._get_profiles()
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to check flavors. Hit {e}'}
        if flavor not in provisioned_profiles:
            return {'result': 'failure', 'reason': f'Flavor {flavor} not found'}
        try:
            image = self._get_image(image)
            if image is None:
                return {'result': 'failure', 'reason': f'Image {image} not found'}
            image_id = image['id']
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to check provisioned images. Hit {e}'}
        volume_attachments = []
        for index, disk in enumerate(disks[1:]):
            disksize = int(disk.get('size')) if isinstance(disk, dict) and 'size' in disk else int(disk)
            diskname = f"{name}-disk{index + 1}"
            volume_by_capacity = {'capacity': disksize, 'name': diskname, 'profile': {'name': 'general-purpose'}}
            volume_attachment = {'delete_volume_on_instance_delete': True, 'volume': volume_by_capacity}
            volume_attachments.append(vpc_v1.VolumeAttachmentPrototypeInstanceContext.from_dict(volume_attachment))
        try:
            result_create = self.conn.create_instance(
                vpc_v1.InstancePrototypeInstanceByImage(
                    image=vpc_v1.ImageIdentityById(id=image_id),
                    primary_network_interface=net_list[0],
                    zone=vpc_v1.ZoneIdentityByHref(get_zone_href(self.region, self.zone)),
                    keys=[vpc_v1.KeyIdentityById(id=x) for x in key_list],
                    name=name,
                    network_interfaces=net_list[1:],
                    profile=vpc_v1.InstanceProfileIdentityByName(
                        name=flavor),
                    resource_group=vpc_v1.ResourceGroupIdentityById(id=resource_group_id),
                    volume_attachments=volume_attachments,
                    vpc=vpc_v1.VPCIdentityById(id=vpc_id),
                    user_data=userdata
                )
            ).result
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to create VM {name}. Hit {e}'}

        tag_names = []
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            tag_names.append(f'{entry}:{metadata[entry]}')
        resource_model = {'resource_id': result_create['crn']}
        try:
            self.global_tagging_service.attach_tag(resources=[resource_model],
                                                   tag_names=tag_names, tag_type='user').get_result()
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to attach tags. Hit {e}'}
        try:
            result_ip = self.conn.create_floating_ip(vpc_v1.FloatingIPPrototypeFloatingIPByTarget(
                target=vpc_v1.FloatingIPByTargetNetworkInterfaceIdentityNetworkInterfaceIdentityById(
                    id=result_create['network_interfaces'][0]['id']
                ),
                name=name,
                resource_group=vpc_v1.ResourceGroupIdentityById(
                    id=resource_group_id),
            )).result
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to create floating ip. Hit {e}'}
        try:
            self.conn.add_instance_network_interface_floating_ip(
                instance_id=result_create['id'],
                network_interface_id=result_create['network_interfaces'][0]['id'],
                id=result_ip['id']
            )
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to add floating ip. Hit {e}'}
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name)
        return {'result': 'success'}

    def start(self, name):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': f'VM {name} not found'}
            vm_id = vm['id']
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve VM {name}. Hit {e}'}

        try:
            self.conn.create_instance_action(instance_id=vm_id, type='start')
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to start VM {name}. Hit {e}'}
        return {'result': 'success'}

    def stop(self, name, soft=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': f'VM {name} not found'}
            vm_id = vm['id']
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve VM {name}. Hit {e}'}
        try:
            self.conn.create_instance_action(instance_id=vm_id, type='stop')
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to stop VM {name}. Hit {e}'}
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
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': f'VM {name} not found'}
            vm_id = vm['id']
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve VM {name}. Hit {e}'}
        try:
            self.conn.create_instance_action(instance_id=vm_id, type='reboot')
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to restart VM {name}. Hit {e}'}
        return {'result': 'success'}

    def info_host(self):
        data = {}
        data['region'] = self.region
        data['zone'] = self.zone
        data['vpc'] = self.vpc
        data['vms'] = len(self.list())
        return data

    def status(self, name):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': f'VM {name} not found'}
            return vm['status']
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve VM {name}. Hit {e}'}

    def list(self):
        vms = []
        try:
            provisioned_vms = self._get_vms()
        except ApiException as e:
            error(f'Unable to retrieve VMs. Hit {e}')
            return vms
        try:
            floating_ips = {x['target']['id']: x for x in self.conn.list_floating_ips(
            ).result['floating_ips'] if x['status'] == 'available' and 'target' in x}
        except ApiException as e:
            error(f'Unable to retrieve floating ips. Hit {e}')
            return vms
        for vm in provisioned_vms:
            try:
                vms.append(self.info(vm['name'], vm=vm, ignore_volumes=True, floating_ips=floating_ips))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error(f"VM {name} not found")
                return None
        except ApiException as e:
            error(f"Unable to retrieve VM {name}. Hit {e}")
            return None
        try:
            url = f"https://cloud.ibm.com/vpc-ext/compute/vs/{self.region}~{vm['id']}/vnc"
        except ApiException as e:
            error(f"Unable to retrieve console access. Hit {e}")
            return None
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = f"Open the following url:\n{url}" if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint(f"Opening url: {url}")
            webbrowser.open(url, new=2, autoraise=True)
        return None

    def serialconsole(self, name, web=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error(f"VM {name} not found")
                return None
        except ApiException as e:
            error(f"Unable to retrieve VM {name}. Hit {e}")
            return None
        try:
            url = f"https://cloud.ibm.com/vpc-ext/compute/vs/{self.region}~{vm['id']}/serial"
        except ApiException as e:
            error(f"Unable to retrieve console access. Hit {e}")
            return None
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = f"Open the following url:\n{url}" if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint(f"Opening url: {url}")
            webbrowser.open(url, new=2, autoraise=True)
        return None

    def info(self, name, output='plain', fields=[], values=False, vm=None, ignore_volumes=False, floating_ips=None,
             debug=False):
        yamlinfo = {}
        if vm is None:
            try:
                vm = self._get_vm(name)
                if vm is None:
                    error(f'VM {name} not found')
                    return yamlinfo
            except ApiException as e:
                error(f'Unable to retrieve VM {name}. Hit {e}')
                return yamlinfo
        state = vm['status']
        if floating_ips is None:
            try:
                floating_ips = {x['target']['id']: x for x in
                                self.conn.list_floating_ips().result['floating_ips'] if x['status'] == 'available'}
            except ApiException as e:
                error(f'Unable to retrieve floating ips. Hit {e}')
                return yamlinfo
        ips = []
        for network in vm['network_interfaces']:
            if network['id'] not in floating_ips:
                continue
            ips.append(floating_ips[network['id']]['address'])
        ip = ','.join(ips)
        # zone = vm['zone']['name']
        image = vm['image']['name']
        yamlinfo['profile'] = vm['profile']['name']
        yamlinfo['name'] = name
        yamlinfo['status'] = state
        # yamlinfo['region'] = self.region
        # yamlinfo['zone'] = zone
        yamlinfo['ip'] = ip
        # yamlinfo['bandwidth'] = vm['bandwidth']
        yamlinfo['flavor'] = vm['profile']['name']
        yamlinfo['cpus'] = vm['vcpu']['count']
        yamlinfo['memory'] = vm['memory']
        yamlinfo['image'] = image
        yamlinfo['user'] = common.get_user(image)
        yamlinfo['creationdate'] = vm['created_at']
        yamlinfo['id'] = vm['id']
        # yamlinfo['resource_group'] = vm['resource_group']['name']
        # yamlinfo['resource_type'] = vm['resource_type']
        # yamlinfo['startable'] = vm['startable']
        # yamlinfo['vpc'] = vm['vpc']['name']
        yamlinfo['profile'] = ''
        yamlinfo['plan'] = ''
        tag_list = self.global_tagging_service.list_tags(attached_to=vm['crn']).get_result().items()
        for entry in tag_list:
            if entry[0] != 'items':
                continue
            tags = entry[1]
            for tag in tags:
                tagname = tag['name']
                if tagname.count(':') == 1:
                    key, value = tagname.split(':')
                    if key in METADATA_FIELDS:
                        yamlinfo[key] = value
            break
        nets = []
        for interface in vm['network_interfaces']:
            network = interface['subnet']['name']
            device = interface['name']
            private_ip = interface['primary_ipv4_address']
            nets.append({'device': device, 'net': network, 'type': private_ip, 'mac': 'N/A'})
            yamlinfo['private_ip'] = private_ip
        if nets:
            yamlinfo['nets'] = nets
            # yamlinfo['primary_network_interface'] = vm['primary_network_interface']['name']
        disks = []
        if ignore_volumes is False:
            try:
                volumes = self._get_volumes()
            except ApiException as e:
                error(f"Unable to retrieve volume information. Hit {e}")
                return yamlinfo
            for attachment in vm['volume_attachments']:
                devname = attachment['volume']['name']
                if devname in volumes:
                    volume = volumes[devname]
                    disksize = volume['capacity']
                    drivertype = volume['profile']['name']
                    diskformat = 'N/A'
                    path = 'N/A'
                    disks.append({'device': devname, 'size': disksize, 'format': diskformat, 'type': drivertype,
                                  'path': path})
        if disks:
            yamlinfo['disks'] = disks
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def ip(self, name):
        ips = []
        try:
            vm = self._get_vm(name)
            if vm is None:
                error(f'VM {name} not found')
                return ""
            for network in vm['network_interfaces']:
                response = self.conn.list_instance_network_interface_floating_ips(vm['id'], network['id'])
                ips.extend([x['address'] for x in response.result['floating_ips'] if x['status'] == 'available'])
        except ApiException as e:
            error(f"Unable to retrieve IP for {name}. Hit {e}")
        return ','.join(ips)

    def internalip(self, name):
        try:
            vm = self._get_vm(name)
        except ApiException:
            return None
        if 'primary_network_interface' not in vm:
            return None
        return vm['primary_network_interface']['primary_ipv4_address']

    def volumes(self, iso=False):
        image_list = []
        try:
            images = self.conn.list_images().result['images']
            for image in images:
                if image['status'] not in ['available', 'deprecated'] or \
                        image['operating_system']['name'].startswith('windows'):
                    continue
                image_list.append(image['name'])
        except ApiException as e:
            error(f"Unable to retrieve volume information. Hit {e}")
            return image_list
        return sorted(image_list, key=str.lower)

    def delete(self, name, snapshots=False):
        conn = self.conn
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': f'VM {name} not found'}
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve VM {name}. Hit {e}'}
        tags = []
        try:
            tags = self.global_tagging_service.list_tags(attached_to=vm['crn']).result['items']
        except Exception as e:
            error(f'Unable to retrieve tags. Hit {e}')
        dnsclient, domain = None, None
        for tag in tags:
            tagname = tag['name']
            if tagname.count(':') == 1:
                key, value = tagname.split(':')
                if key == 'domain':
                    domain = value
                if key == 'dnsclient':
                    dnsclient = value
        try:
            for network in vm['network_interfaces']:
                response = conn.list_instance_network_interface_floating_ips(instance_id=vm['id'],
                                                                             network_interface_id=network['id']).result
                if len(response['floating_ips']) == 0:
                    continue
                for floating_ip in response['floating_ips']:
                    conn.remove_instance_network_interface_floating_ip(id=floating_ip['id'],
                                                                       instance_id=vm['id'],
                                                                       network_interface_id=network['id'])
                    conn.delete_floating_ip(id=floating_ip['id'])
        except ApiException as e:
            return {'result': 'failure',
                    'reason': f'Unable to remove floating IPs for VM {name}. Hit {e}'}
        try:
            conn.delete_instance(id=vm['id'])
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to delete VM. Hit {e}'}
        if domain is not None and dnsclient is None:
            self.delete_dns(name, domain, name)
        return {'result': 'success'}

    def dnsinfo(self, name):
        dnsclient, domain = None, None
        try:
            vm = self._get_vm(name)
            if vm is None:
                error(f'VM {name} not found')
                return dnsclient, domain
        except ApiException as e:
            error(f'Unable to retrieve VM. Hit {e}')
            return dnsclient, domain
        try:
            tags = self.global_tagging_service.list_tags(attached_to=vm['crn']).result['items']
        except ApiException as e:
            error(f'Unable to retrieve tags. Hit {e}')
            return None, None
        for tag in tags:
            tagname = tag['name']
            if tagname.count(':') == 1:
                key, value = tagname.split(':')
                if key == 'dnsclient':
                    dnsclient = value
                if key == 'domain':
                    domain = value
        return dnsclient, domain

    def clone(self, old, new, full=False, start=False):
        print("not implemented")

    def update_metadata(self, name, metatype, metavalue, append=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error(f'VM {name} not found')
                return
        except ApiException as e:
            error(f'Unable to retrieve VM {name}. Hit {e}')
            return
        resource_model = {'resource_id': vm['crn']}
        tag_names = [f"{metatype}:{metavalue}"]
        try:
            self.global_tagging_service.attach_tag(resources=[resource_model],
                                                   tag_names=tag_names, tag_type='user').get_result()
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to attach tags. Hit {e}'}

    def update_memory(self, name, memory):
        print("not implemented")

    def update_cpus(self, name, numcpus):
        print("not implemented")

    def update_start(self, name, start=True):
        print("not implemented")

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)

    def update_iso(self, name, iso):
        print("not implemented")

    def update_flavor(self, name, flavor):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': f'VM {name} not found'}
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve VM {name}. Hit {e}'}
        if vm['status'] != 'stopped':
            return {'result': 'failure', 'reason': f'VM {name} must be stopped'}
        try:
            provisioned_profiles = self._get_profiles()
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve flavors. Hit {e}'}
        if flavor not in provisioned_profiles:
            return {'result': 'failure', 'reason': f'Flavor {flavor} not found'}
        try:
            self.conn.update_instance(id=vm['id'], instance_patch=vpc_v1.InstancePatch(
                profile=vpc_v1.InstancePatchProfileInstanceProfileIdentityByName(name=flavor)))
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to update instance. Hit {e}'}
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")

    def add_disk(self, name, size, pool=None, thin=True, image=None,
                 shareable=False, existing=None, interface='virtio', diskname=None):
        print("not implemented")

    def delete_disk(self, name, diskname, pool=None, novm=False):
        print("not implemented")

    def list_disks(self):
        print("not implemented")
        return {}

    def add_nic(self, name, network, model='virtio'):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error(f'VM {name} not found')
                return
        except ApiException as e:
            error(f'Unable to retrieve VM {name}. Hit {e}')
            return
        try:
            subnet = self._get_subnet(network)
            if subnet is None:
                error(f'Network {network} not found')
                return
        except ApiException as e:
            error(f'Unable to retrieve network information. Hit {e}')
            return
        try:
            self.conn.create_instance_network_interface(
                instance_id=vm['id'],
                subnet=vpc_v1.SubnetIdentityById(id=subnet['id']),
                allow_ip_spoofing=False
            )
        except ApiException as e:
            error(f'Unable to create NIC. Hit {e}')

    def delete_nic(self, name, interface):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error(f'VM {name} not found')
                return
        except ApiException as e:
            error(f'Unable to retrieve VM {name}. Hit {e}')
        try:
            for network in vm['network_interfaces']:
                if network['name'] == interface:
                    response = self.conn.delete_instance_network_interface(instance_id=vm['id'],
                                                                           id=network['id'])
                    if response.status_code != 204:
                        error(f'Unexpected status code received: {response.status_code}')
        except ApiException as e:
            error(f'Unable to delete NIC. Hit {e}')

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")

    def delete_image(self, image, pool=None):
        try:
            image = self._get_image(image)
            if image is None:
                return {'result': 'failure', 'reason': f'Image {image} not found'}
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve images. Hit {e}'}
        try:
            result = self.conn.delete_image(id=image['id'])
            if result.status_code != 202:
                return {'result': 'failure', 'reason': f'Unexpected status code received: {result.status_code}'}
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to delete image. Hit {e}'}
        return {'result': 'success'}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
        cos_id = self.cos_resource_instance_id.split(':')[7]
        identity_client = IamIdentityV1(authenticator=self.authenticator)
        api_key_detail = identity_client.get_api_keys_details(iam_api_key=self.iam_api_key).get_result()
        account_id = api_key_detail['account_id']
        iam_policy_management_service = IamPolicyManagementV1(authenticator=self.authenticator)
        image_policy_found = False
        for policy in iam_policy_management_service.list_policies(account_id).result['policies']:
            policy_type = policy['type']
            if policy_type != 'authorization':
                continue
            cos_found = [x for x in policy['resources'][0]['attributes'] if x['name'] == 'serviceInstance' and
                         x['value'] == cos_id]
            if cos_found:
                image_policy_found = True
                break
        if not image_policy_found:
            pprint("Adding authorization between image service and cloud storage instance")
            subject = PolicySubject(attributes=[SubjectAttribute(name='serviceName', value='is'),
                                                SubjectAttribute(name='accountId', value=account_id),
                                                SubjectAttribute(name='resourceType', value='image')])
            resources = PolicyResource(attributes=[ResourceAttribute(name='accountId', value=account_id),
                                                   ResourceAttribute(name='serviceName', value='cloud-object-storage'),
                                                   ResourceAttribute(name='serviceInstance', value=cos_id)])
            roles = [PolicyRole(role_id='crn:v1:bluemix:public:iam::::serviceRole:Writer')]
            iam_policy_management_service.create_policy(type='authorization', subjects=[subject],
                                                        roles=roles, resources=[resources]).get_result()
        if pool not in self.list_buckets():
            return {'result': 'failure', 'reason': f"Bucket {pool} doesn't exist"}
        shortimage = os.path.basename(url).split('?')[0]
        shortimage_unzipped = shortimage.replace('.gz', '')
        if shortimage_unzipped in self.volumes():
            return {'result': 'success'}
        delete_cos_image = False
        if shortimage_unzipped not in self.list_bucketfiles(pool):
            if not os.path.exists(f'/tmp/{shortimage}'):
                downloadcmd = f"curl -Lko /tmp/{shortimage} -f '{url}'"
                code = os.system(downloadcmd)
                if code != 0:
                    return {'result': 'failure', 'reason': "Unable to download indicated image"}
            if shortimage.endswith('gz'):
                if which('gunzip') is not None:
                    uncompresscmd = f"gunzip /tmp/{shortimage}"
                    os.system(uncompresscmd)
                else:
                    error("gunzip not found. Can't uncompress image")
                    return {'result': 'failure', 'reason': "gunzip not found. Can't uncompress image"}
                shortimage = shortimage_unzipped
            pprint("Uploading image to bucket")
            self.upload_to_bucket(pool, f'/tmp/{shortimage}')
            os.remove(f'/tmp/{shortimage}')
            delete_cos_image = True
        pprint("Importing image as template")
        image_file_prototype_model = {}
        image_file_prototype_model['href'] = f"cos://{self.region}/{pool}/{shortimage_unzipped}"
        operating_system_identity_model = {}
        operating_system_identity_model['name'] = 'centos-8-amd64'
        image_prototype_model = {}
        clean_image_name = shortimage_unzipped.replace('.', '-').replace('_', '-').lower()
        image_prototype_model['name'] = clean_image_name
        image_prototype_model['file'] = image_file_prototype_model
        image_prototype_model['operating_system'] = operating_system_identity_model
        image_prototype = image_prototype_model
        result_create = self.conn.create_image(image_prototype).get_result()
        while True:
            image = self._get_image(clean_image_name)
            if image['status'] == 'available':
                break
            else:
                pprint(f"Waiting for image {clean_image_name} to be available")
                sleep(10)
        tag_names = [f"image:{shortimage_unzipped}"]
        resource_model = {'resource_id': result_create['crn']}
        self.global_tagging_service.attach_tag(resources=[resource_model],
                                               tag_names=tag_names, tag_type='user').get_result()
        if delete_cos_image:
            self.delete_from_bucket(pool, shortimage_unzipped)
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        if cidr is not None:
            try:
                network = ip_network(cidr)
            except:
                return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
            if str(network.version) == "6":
                return {'result': 'failure', 'reason': 'IPv6 is not allowed'}
        try:
            vpcs = self.conn.list_vpcs().result['vpcs']
            for vpc in vpcs:
                if self.vpc == vpc['name']:
                    vpc_id = vpc['id']
                    resource_group_id = vpc['resource_group']['id']
                    break
            else:
                return {'result': 'failure', 'reason': f'vpc {self.vpc} does not exist'}
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve vpc information. Hit {e}'}
        try:
            self.conn.create_subnet(vpc_v1.SubnetPrototypeSubnetByCIDR(
                name=name,
                ipv4_cidr_block=cidr,
                vpc=vpc_v1.VPCIdentityById(id=vpc_id),
                resource_group=vpc_v1.ResourceGroupIdentityById(id=resource_group_id),
                zone=vpc_v1.ZoneIdentityByHref(
                    href=get_zone_href(self.region, self.zone)
                ),
            ))
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to create network. Hit {e}'}
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        try:
            subnets = self._get_subnets()
            for subnet in subnets:
                if name == subnet['name']:
                    subnet_id = subnet['id']
                    break
            else:
                return {'result': 'failure', 'reason': f'Subnet {name} not found'}
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to retrieve subnet {name} information. Hit {e}'}
        try:
            self.conn.delete_subnet(id=subnet_id)
        except ApiException as e:
            return {'result': 'failure', 'reason': f'Unable to delete subnet {name}. Hit {e}'}
        return {'result': 'success'}

    def list_pools(self):
        print("not implemented")
        return []

    def list_networks(self):
        networks = {}
        subnets = {}
        for subnet in self.conn.list_subnets().result['subnets']:
            newsubnet = {'name': subnet['name'], 'cidr': subnet['ipv4_cidr_block']}
            vpcid = subnet['vpc']['id']
            if vpcid in subnets:
                subnets[vpcid].append(newsubnet)
            else:
                subnets[vpcid] = [newsubnet]
        for net in self.conn.list_vpcs().result['vpcs']:
            networkname = net['name']
            vpcid = net['id']
            dhcp = net['default_network_acl']['name']
            mode = net['default_routing_table']['name']
            cidr = ''
            if vpcid in subnets:
                for subnet in subnets[vpcid]:
                    cidr = subnet['cidr']
                    if subnet['name'] == networkname:
                        break
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': vpcid, 'type': 'routed', 'mode': mode}
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        return networkinfo

    def list_subnets(self):
        subnets = {}
        try:
            provisioned_subnets = self._get_subnets()
        except ApiException as e:
            error(f'Unable to retrieve subnets. Hit {e}')
            return subnets
        for subnet in provisioned_subnets:
            subnets[subnet['name']] = {
                'az': subnet['zone']['name'],
                'cidr': subnet['ipv4_cidr_block'],
                'network': subnet['vpc']['name']
            }
        return subnets

    def delete_pool(self, name, full=False):
        print("not implemented")

    def network_ports(self, name):
        return []

    def vm_ports(self, name):
        return []

    def get_pool_path(self, pool):
        print("not implemented")

    def list_flavors(self):
        flavors = []
        try:
            for flavor in self.conn.list_instance_profiles().result['profiles']:
                if self.debug:
                    print(flavor)
                flavors.append([flavor['name'], flavor['vcpu_count']['value'], flavor['memory']['value']])
            return flavors
        except ApiException as e:
            error(f"Unable to retrieve available flavors. Hit {e}")
            return []

    def export(self, name, image=None):
        print("not implemented")

    def _wait_lb_active(self, id):
        while True:
            result = self.conn.get_load_balancer(id=id).result
            if result['provisioning_status'] == 'active':
                break
            pprint("Waiting 10s for lb to go active...")
            sleep(10)

    def _wait_lb_dead(self, id):
        while True:
            try:
                self.conn.get_load_balancer(id=id).result
                pprint("Waiting 10s for lb to disappear...")
                sleep(10)
            except:
                break

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False, dnsclient=None, ip=None):

        ports = [int(port) for port in ports]
        internal = False if internal is None else internal
        clean_name = name.replace('.', '-')
        pprint(f"Creating Security Group {clean_name}")
        security_group_ports = ports + [int(checkport)] if int(checkport) not in ports else ports
        security_group_id = self.create_security_group(clean_name, {'ports': security_group_ports})
        subnets = set()
        member_list = []
        resource_group_id = None
        if vms:
            for vm in vms:
                try:
                    virtual_machine = self._get_vm(vm)
                except ApiException as e:
                    return {'result': 'failure', 'reason': f'Unable to retrieve VM {vm}. Hit {e}'}
                member_list.append(virtual_machine['primary_network_interface']['primary_ipv4_address'])
                if 'primary_network_interface' in virtual_machine:
                    subnets.add(virtual_machine['primary_network_interface']['subnet']['id'])
                nic_id = virtual_machine['primary_network_interface']['id']
                self.conn.add_security_group_network_interface(security_group_id, nic_id)
                if resource_group_id is None:
                    resource_group_id = virtual_machine['resource_group']['id']
                self.update_metadata(vm, 'loadbalancer', clean_name, append=True)
        pprint("Creating load balancer pool...")
        try:
            lb = self.conn.create_load_balancer(
                is_public=not internal,
                name=clean_name,
                pools=[vpc_v1.LoadBalancerPoolPrototype(
                    algorithm='round_robin',
                    health_monitor=vpc_v1.LoadBalancerPoolHealthMonitorPrototype(
                        delay=20,
                        max_retries=2,
                        timeout=3,
                        # type='http',
                        type='tcp',
                        url_path=checkpath,
                        port=checkport,
                    ),
                    protocol='tcp',
                    members=[vpc_v1.LoadBalancerPoolMemberPrototype(
                        port=port,
                        target=vpc_v1.LoadBalancerPoolMemberTargetPrototypeIP(address=m)
                    ) for m in member_list],
                    name=f"{clean_name}-{port}",
                ) for port in ports],
                subnets=[vpc_v1.SubnetIdentityById(id=x) for x in subnets],
                resource_group_id=vpc_v1.ResourceGroupIdentityById(id=resource_group_id),
                security_groups=[vpc_v1.SecurityGroupIdentityById(id=security_group_id)],
            ).result
            self._wait_lb_active(id=lb['id'])
        except ApiException as e:
            error(f'Unable to create load balancer. Hit {e}')
            return {'result': 'failure', 'reason': f'Unable to create load balancer. Hit {e}'}
        pprint("Creating listeners...")
        for index, port in enumerate(ports):
            try:
                self.conn.create_load_balancer_listener(
                    load_balancer_id=lb['id'],
                    port=port,
                    protocol='tcp',
                    default_pool=vpc_v1.LoadBalancerPoolIdentityById(id=lb['pools'][index]['id'])
                )
                try:
                    self._wait_lb_active(id=lb['id'])
                except ApiException as e:
                    error(f'Unable to create load balancer. Hit {e}')
                    return {'result': 'failure', 'reason': f'Unable to create load balancer. Hit {e}'}
            except ApiException as e:
                error(f'Unable to create load balancer listener. Hit {e}')
                return {'result': 'failure', 'reason': f'Unable to create load balancer listener. Hit {e}'}
        pprint(f"Load balancer DNS name {lb['hostname']}")
        resource_model = {'resource_id': lb['crn']}
        try:
            tag_names = [f'realname:{name}']
            if domain is not None:
                tag_names.append(f'domain:{domain}')
            if dnsclient is not None:
                tag_names.append(f'dnsclient:{dnsclient}')
            self.global_tagging_service.attach_tag(resources=[resource_model],
                                                   tag_names=tag_names,
                                                   tag_type='user')
        except ApiException as e:
            error(f'Unable to attach tags. Hit {e}')
            return {'result': 'failure', 'reason': f'Unable to attach tags. Hit {e}'}
        if domain is not None:
            while True:
                try:
                    result = self.conn.get_load_balancer(id=lb['id']).result
                except ApiException as e:
                    pprint(f'Unable to check load balancer ip. Hit {e}')
                    return {'result': 'failure', 'reason': f'Unable to check load balancer ip. Hit {e}'}
                if len(result['private_ips']) == 0:
                    pprint("Waiting 10s to get private ips assigned")
                    sleep(10)
                    continue
                break
            ip = result['public_ips'][0]['address']
            if dnsclient is not None:
                return ip
            self.reserve_dns(name, ip=ip, domain=domain, alias=alias)
        return {'result': 'success'}

    def delete_loadbalancer(self, name):
        domain = None
        dnsclient = None
        clean_name = name.replace('.', '-')
        try:
            lbs = {x['name']: x for x in self.conn.list_load_balancers().result['load_balancers']}
            if clean_name not in lbs:
                error(f'Load balancer {name} not found')
                return
            lb = lbs[clean_name]
        except ApiException as e:
            error(f'Unable to retrieve load balancers. Hit {e}')
            return
        try:
            tags = self.global_tagging_service.list_tags(attached_to=lb['crn']).result['items']
        except ApiException as e:
            error(f'Unable to retrieve tags. Hit {e}')
            return
        realname = name
        for tag in tags:
            tagname = tag['name']
            if tagname.count(':') == 1:
                key, value = tagname.split(':')
                if key == 'domain':
                    domain = value
                if key == 'dnsclient':
                    dnsclient = value
                if key == 'realname':
                    realname = value
        try:
            self.conn.delete_load_balancer(id=lb['id'])
        except ApiException as e:
            error(f'Unable to delete load balancer. Hit {e}')
            return
        if domain is not None and dnsclient is None:
            pprint(f"Deleting DNS {realname}.{domain}")
            self.delete_dns(realname, domain, name)
        self._wait_lb_dead(id=lb['id'])
        try:
            pprint(f"Deleting Security Group {clean_name}")
            self.delete_security_group(clean_name)
        except Exception as e:
            error(f'Unable to delete security group. Hit {e}')
        if dnsclient is not None:
            return dnsclient

    def list_loadbalancers(self):
        results = []
        try:
            lbs = self.conn.list_load_balancers().result['load_balancers']
        except ApiException as e:
            error(f'Unable to retrieve LoadBalancers. Hit {e}')
            return results
        if lbs:
            vms_by_addresses = {}
            for vm in self.conn.list_instances().get_result()['instances']:
                vms_by_addresses[vm['network_interfaces'][0]['primary_ipv4_address']] = vm['name']
        for lb in lbs:
            protocols = set()
            ports = []
            lb_id = lb['id']
            name = lb['name']
            ip = lb['hostname']
            try:
                listeners = self.conn.list_load_balancer_listeners(load_balancer_id=lb_id).result['listeners']
            except ApiException as e:
                error(f'Unable to retrieve listeners for load balancer {name}. Hit {e}')
                continue
            for listener in listeners:
                protocols.add(listener['protocol'])
                ports.append(str(listener['port']))
            target = []
            if 'pools' in lb:
                pool_id = lb['pools'][0]['id']
                pool = self.conn.get_load_balancer_pool(id=pool_id, load_balancer_id=lb_id).get_result()
                for member in pool['members']:
                    member_data = self.conn.get_load_balancer_pool_member(lb_id, pool_id, member['id']).get_result()
                    if member_data['target']['address'] in vms_by_addresses:
                        member_name = vms_by_addresses[member_data['target']['address']]
                        target.append(member_name)
            target = ','.join(target)
            results.append([name, ip, ','.join(protocols), '+'.join(ports), target])
        return results

    def create_bucket(self, bucket, public=False):
        if bucket in self.list_buckets():
            error(f"Bucket {bucket} already there")
            return
        # location = {'LocationConstraint': self.region}
        args = {'Bucket': bucket}  # , "CreateBucketConfiguration": location} #TODO: fix this.
        if public:
            args['ACL'] = 'public-read'
        self.s3.create_bucket(**args)

    def delete_bucket(self, bucket):
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return
        for obj in self.s3.list_objects(Bucket=bucket).get('Contents', []):
            key = obj['Key']
            pprint(f"Deleting object {key} from bucket {bucket}")
            self.s3.delete_object(Bucket=bucket, Key=key)
        self.s3.delete_bucket(Bucket=bucket)

    def delete_from_bucket(self, bucket, path):
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return
        self.s3.delete_object(Bucket=bucket, Key=path)

    def download_from_bucket(self, bucket, path):
        self.s3.download_file(bucket, path, path)

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        if not os.path.exists(path):
            error(f"Invalid path {path}")
            return None
        if bucket not in self.list_buckets():
            error(f"Bucket {bucket} doesn't exist")
            return None
        extra_args = {'Metadata': overrides} if overrides else {}
        if public:
            extra_args['ACL'] = 'public-read'
        dest = os.path.basename(path)
        with open(path, "rb") as f:
            self.s3.upload_fileobj(f, bucket, dest, ExtraArgs=extra_args)
        if temp_url:
            expiration = 600
            return self.s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': dest},
                                                  ExpiresIn=expiration)
        return None

    def fast_upload_to_bucket(self, bucket, path):
        from ibm_s3transfer.aspera.manager import AsperaConfig, AsperaTransferManager
        transfer_manager = AsperaTransferManager(self.s3)
        ms_transfer_config = AsperaConfig(multi_session=2, multi_session_threshold_mb=100)
        transfer_manager = AsperaTransferManager(client=self.s3, transfer_config=ms_transfer_config)
        with AsperaTransferManager(self.s3) as transfer_manager:
            future = transfer_manager.upload(path, bucket, os.path.basename(path))
            future.result()

    def list_buckets(self):
        response = self.s3.list_buckets()
        return [bucket["Name"] for bucket in response['Buckets']]

    def list_bucketfiles(self, bucket):
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return []
        return [obj['Key'] for obj in self.s3.list_objects(Bucket=bucket).get('Contents', [])]

    def public_bucketfile_url(self, bucket, path):
        return f"https://s3.direct.{self.region}.cloud-object-storage.appdomain.cloud/{bucket}/{path}"

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None):
        if domain is None:
            domain = nets[0]
        pprint(f"Using domain {domain}...")
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        dnszone = self._get_dns_zone(domain)
        if dnszone is None:
            return
        if ip is None:
            counter = 0
            while counter != 100:
                ip = self.internalip(name)
                if ip is None:
                    sleep(5)
                    pprint(f"Waiting 5 seconds to grab internal ip and create DNS record for {name}...")
                    counter += 10
                else:
                    break
        if ip is None:
            error(f'Unable to find an IP for {name}')
            return
        try:
            dnszone.create_dns_record(name=name, type='A', ttl=60, content=ip)
        except ApiException as e:
            error(f'Unable to create DNS entry. Hit {e}')
            return
        if alias:
            for a in alias:
                if a == '*':
                    record_type = 'A'
                    content = ip
                    if cluster is not None and ('ctlplane' in name or 'worker' in name):
                        dnsname = f'*.apps.{cluster}.{domain}'
                    else:
                        dnsname = f'*.{name}.{domain}'
                else:
                    record_type = 'CNAME'
                    content = f"{name}.{domain}"
                    dnsname = f'{a}.{domain}' if '.' not in a else a
                try:
                    dnszone.create_dns_record(name=dnsname, type=record_type, ttl=60, content=content)
                except ApiException as e:
                    error(f'Unable to create DNS entry. Hit {e}')
                    return

    def create_dns(self):
        print("not implemented")

    def delete_dns(self, name, domain, allentries=False):
        dnszone = self._get_dns_zone(domain)
        if dnszone is None:
            return
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        dnsentry = name if cluster is None else f"{name}.{cluster}"
        entry = f"{dnsentry}.{domain}"
        clusterdomain = f"{cluster}.{domain}"
        try:
            records = dnszone.list_all_dns_records().get_result()['result']
        except ApiException as e:
            error(f"Unable to check DNS {dnszone['name']} records. Hit {e}")
            return
        recordsfound = False
        for record in records:
            if entry in record['name'] or ('ctlplane-0' in name and record['name'].endswith(clusterdomain))\
                    or (record['type'] == 'CNAME' and record['content'] == entry):
                record_identifier = record['id']
                try:
                    dnszone.delete_dns_record(dnsrecord_identifier=record_identifier)
                    recordsfound = True
                except ApiException as e:
                    error(f"Unable to delete record {record['name']}. Hit {e}")
        if not recordsfound:
            error(f"No records found for {entry}")
        return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        dnszone = self._get_dns_zone(domain)
        if dnszone is None:
            return []
        try:
            records = dnszone.list_all_dns_records().get_result()['result']
        except ApiException as e:
            error(f"Unable to check DNS {dnszone['name']} records. Hit {e}")
            return results
        for record in records:
            ip = record['content']
            results.append([record['name'], record['type'], record['ttl'], ip])
        return results

    def _get_vm(self, name):
        result = self.conn.list_instances(name=name).result
        if result['total_count'] == 0:
            return None
        return result['instances'][0]

    def _get_vms(self):
        result = self.conn.list_instances().result
        if result['total_count'] == 0:
            return []
        return result['instances']

    def _get_subnet(self, name):
        subnets = self._get_subnets()
        for subnet in subnets:
            if name == subnet['name'] and subnet['zone']['name'] == self.zone:
                return subnet
        return None

    def _get_subnets(self):
        return self.conn.list_subnets().result['subnets']

    def _get_image(self, name):
        result = self.conn.list_images(name=name).result
        if len(result['images']) == 0:
            return None
        return result['images'][0]

    def _get_profiles(self):
        return {x['name']: x for x in self.conn.list_instance_profiles().result['profiles']}

    def _get_volumes(self):
        return {x['name']: x for x in self.conn.list_volumes().result['volumes']}

    def _get_dns_zone(self, domain):
        try:
            dnslist = self.dns.list_zones().get_result()['result']
        except ApiException as e:
            error(f'Unable to check DNS resources. Hit {e}')
            return None
        dnsfound = False
        for dnsresource in dnslist:
            dnsid = dnsresource['id']
            dnsname = dnsresource['name']
            if dnsname == domain:
                dnsfound = True
                break
        if not dnsfound:
            error(f'Domain {domain} not found')
            return None
        try:
            dnszone = DnsRecordsV1(authenticator=self.authenticator, crn=self.cis_resource_instance_id,
                                   zone_identifier=dnsid)
        except ApiException as e:
            error(f'Unable to check DNS zones for DNS {domain}. Hit {e}')
            return None
        return dnszone

    def create_security_group(self, name, overrides={}):
        ports = overrides.get('ports', [])
        vpc_id = [net['id'] for net in self.conn.list_vpcs().result['vpcs'] if net['name'] == self.vpc][0]
        vpc_identity_model = {'id': vpc_id}
        rules = []
        security_group_rule_prototype_model = {}
        security_group_rule_prototype_model['direction'] = 'outbound'
        security_group_rule_prototype_model['ip_version'] = 'ipv4'
        security_group_rule_prototype_model['protocol'] = 'all'
        security_group_rule_prototype_model['remote'] = {'cidr_block': '0.0.0.0/0'}
        rules.append(security_group_rule_prototype_model)
        for port in ports:
            if isinstance(port, str) or isinstance(port, int):
                protocol = 'tcp'
                fromport, toport = int(port), int(port)
            elif isinstance(port, dict):
                protocol = port.get('protocol', 'tcp')
                fromport = port.get('from')
                toport = port.get('to') or fromport
                if fromport is None:
                    warning(f"Missing from in {ports}. Skipping")
                    continue
            pprint(f"Adding rule from {fromport} to {toport} protocol {protocol}")
            security_group_rule_prototype_model = {}
            security_group_rule_prototype_model['direction'] = 'inbound'
            security_group_rule_prototype_model['ip_version'] = 'ipv4'
            security_group_rule_prototype_model['protocol'] = protocol
            security_group_rule_prototype_model['port_min'] = fromport
            security_group_rule_prototype_model['port_max'] = toport
            security_group_rule_prototype_model['remote'] = {'cidr_block': '0.0.0.0/0'}
            rules.append(security_group_rule_prototype_model)
        response = self.conn.create_security_group(vpc_identity_model, name=name, rules=rules).result
        return response['id']

    def delete_security_group(self, name):
        security_groups = self.conn.list_security_groups().result['security_groups']
        matching_sgs = [x for x in security_groups if x['name'] == name]
        if matching_sgs:
            security_group = matching_sgs[0]
            security_group_id = security_group['id']
            for n in security_group['network_interfaces']:
                self.conn.remove_security_group_network_interface(security_group_id, n['id'])
            self.conn.delete_security_group(security_group_id)

    def _add_sno_security_group(self, cluster):
        security_group_id = self.create_security_group(f"{cluster}-sno", {'ports': [80, 443, 6443]})
        vm = self._get_vm(f"{cluster}-ctlplane-0")
        nic_id = vm['primary_network_interface']['id']
        self.conn.add_security_group_network_interface(security_group_id, nic_id)

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        return [x['name'] for x in self.conn.list_security_groups().result['security_groups']]

    def update_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def info_subnet(self, name):
        print("not implemented")
        return {}

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
        return [d['name'] for d in self.dns.list_zones().get_result()['result']]
