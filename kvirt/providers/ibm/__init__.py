#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IBM Cloud provider class
"""

from ipaddress import ip_network
from kvirt import common
from kvirt.common import pprint, error
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
import os
from shutil import which
from time import sleep
from requests import get, post
import webbrowser


def get_zone_href(region, zone):
    return "{}/regions/{}/zones/{}".format(
        "https://%s.iaas.cloud.ibm.com/v1" % region,
        region,
        zone
    )


def get_s3_endpoint(region):
    return 'https://s3.{}.cloud-object-storage.appdomain.cloud'.format(region)


def get_service_instance_id(iam_api_key, name):
    if 'crn' in name:
        return name
    service_id = None
    headers = {'content-type': 'application/x-www-form-urlencoded', 'accept': 'application/json'}
    data = 'grant_type=urn%%3Aibm%%3Aparams%%3Aoauth%%3Agrant-type%%3Aapikey&apikey=%s' % iam_api_key
    req = post("https://iam.cloud.ibm.com/identity/token", data=data, headers=headers)
    token = req.json()['access_token']
    req = get("https://resource-controller.cloud.ibm.com/v2/resource_instances", headers=headers)
    headers = {'Authorization': 'Bearer %s' % token}
    req = get("https://resource-controller.cloud.ibm.com/v2/resource_instances", headers=headers)
    for entry in req.json()['resources']:
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
        self.conn.set_service_url("https://%s.iaas.cloud.ibm.com/v1" % region)
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
        self.zone = zone if region in zone else "%s-2" % region
        self.vpc = vpc

    def close(self):
        return

    def exists(self, name):
        try:
            return self._get_vm(name) is not None
        except ApiException as exc:
            error("Unable to retrieve VM. %s" % exc)
            return False

    def net_exists(self, name):
        try:
            return self._get_subnet(name) is not None
        except ApiException as exc:
            error("Unable to retrieve available subnets. %s" % (exc))
            return False

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt',
               cpumodel='Westmere', cpuflags=[], cpupinning=[], numcpus=2, memory=512,
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
                return {'result': 'failure', 'reason': 'VPC %s does not exist' % self.vpc}
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve vpc information. %s' % exc}
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
        if not keys:
            return {'result': 'failure', 'reason': 'SSH Keys not found in configuration'}
        key_list = []
        try:
            ssh_keys = {x['name']: x for x in self.conn.list_keys().result['keys']}
            for key in keys:
                if key not in ssh_keys:
                    return {'result': 'failure', 'reason': 'Key %s not found' % key}
                key_list.append(ssh_keys[key]['id'])
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to check keys. %s' % exc}
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
                    return {'result': 'failure', 'reason': 'Network %s not found' % netname}
                subnet = subnets[netname]
                if subnet['zone']['name'] != self.zone:
                    return {'result': 'failure', 'reason': 'Network %s is not in zone %s' % (netname, self.zone)}
                net_list.append(
                    vpc_v1.NetworkInterfacePrototype(
                        subnet=vpc_v1.SubnetIdentityById(id=subnet['id']),
                        allow_ip_spoofing=False,
                        name="eth{}".format(index)
                        # TODO: security groups, ip address
                    )
                )
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to check networks. %s' % exc}
        if flavor is None:
            flavors = [f for f in self.flavors() if f[1] >= numcpus and f[2] * 1024 >= memory]
            if flavors:
                flavor = min(flavors, key=lambda f: f[2])[0]
                pprint("Using flavor %s" % flavor)
            else:
                return {'result': 'failure', 'reason': "Couldn't find a flavor matching cpu/memory requirements"}
        try:
            provisioned_profiles = self._get_profiles()
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to check flavors. %s' % exc}
        if flavor not in provisioned_profiles:
            return {'result': 'failure', 'reason': 'Flavor %s not found' % flavor}
        try:
            image = self._get_image(image)
            if image is None:
                return {'result': 'failure', 'reason': 'Image %s not found' % image}
            image_id = image['id']
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to check provisioned images. %s' % exc}
        volume_attachments = []
        for index, disk in enumerate(disks[1:]):
            disksize = int(disk.get('size')) if isinstance(disk, dict) and 'size' in disk else int(disk)
            diskname = "%s-disk%s" % (name, index + 1)
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
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to create VM %s. %s' % (name, exc)}

        tag_names = []
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            tag_names.append('%s:%s' % (entry, metadata[entry]))
        resource_model = {'resource_id': result_create['crn']}
        try:
            self.global_tagging_service.attach_tag(resources=[resource_model],
                                                   tag_names=tag_names, tag_type='user').get_result()
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to attach tags. %s' % exc}
        try:
            result_ip = self.conn.create_floating_ip(vpc_v1.FloatingIPPrototypeFloatingIPByTarget(
                target=vpc_v1.FloatingIPByTargetNetworkInterfaceIdentityNetworkInterfaceIdentityById(
                    id=result_create['network_interfaces'][0]['id']
                ),
                name=name,
                resource_group=vpc_v1.ResourceGroupIdentityById(
                    id=resource_group_id),
            )).result
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to create floating ip. %s' % exc}
        try:
            self.conn.add_instance_network_interface_floating_ip(
                instance_id=result_create['id'],
                network_interface_id=result_create['network_interfaces'][0]['id'],
                id=result_ip['id']
            )
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to add floating ip. %s' % exc}
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name)
        return {'result': 'success'}

    def start(self, name):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
            vm_id = vm['id']
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, exc)}

        try:
            self.conn.create_instance_action(instance_id=vm_id, type='start')
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to start VM %s. %s' % (name, exc)}
        return {'result': 'success'}

    def stop(self, name, soft=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
            vm_id = vm['id']
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, exc)}
        try:
            self.conn.create_instance_action(instance_id=vm_id, type='stop')
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to stop VM %s. %s' % (name, exc)}
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
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
            vm_id = vm['id']
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, exc)}
        try:
            self.conn.create_instance_action(instance_id=vm_id, type='reboot')
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to restart VM %s. %s' % (name, exc)}
        return {'result': 'success'}

    def report(self):
        print("Region:", self.region)
        print("Zone:", self.zone)
        print("VPC:", self.vpc)
        return

    def status(self, name):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
            return vm['status']
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, exc)}

    def list(self):
        vms = []
        try:
            provisioned_vms = self._get_vms()
        except ApiException as exc:
            error('Unable to retrieve VMs. %s' % exc)
            return vms
        try:
            floating_ips = {x['target']['id']: x for x in self.conn.list_floating_ips(
            ).result['floating_ips'] if x['status'] == 'available' and 'target' in x}
        except ApiException as exc:
            error('Unable to retrieve floating ips. %s' % exc)
            return vms
        for vm in provisioned_vms:
            vms.append(self.info(vm['name'], vm=vm, ignore_volumes=True, floating_ips=floating_ips))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error("VM %s not found" % name)
                return None
        except ApiException as exc:
            error("Unable to retrieve VM %s. %s" % (name, exc))
            return None
        try:
            # url = self.conn.create_instance_console_access_token(
            #    instance_id=vm['id'], console_type='serial').result['href']
            url = "https://cloud.ibm.com/vpc-ext/compute/vs/%s~%s/vnc" % (self.region, vm['id'])
        except ApiException as exc:
            error("Unable to retrieve console access. %s" % exc)
            return None
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = "Open the following url:\n%s" % url if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint("Opening url: %s" % url)
            webbrowser.open(url, new=2, autoraise=True)
        return None

    def serialconsole(self, name, web=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error("VM %s not found" % name)
                return None
        except ApiException as exc:
            error("Unable to retrieve VM %s. %s" % (name, exc))
            return None
        try:
            url = "https://cloud.ibm.com/vpc-ext/compute/vs/%s~%s/serial" % (self.region, vm['id'])
        except ApiException as exc:
            error("Unable to retrieve console access. %s" % exc)
            return None
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = "Open the following url:\n%s" % url if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint("Opening url: %s" % url)
            webbrowser.open(url, new=2, autoraise=True)
        return None

    def info(self, name, output='plain', fields=[], values=False, vm=None, ignore_volumes=False, floating_ips=None,
             debug=False):
        yamlinfo = {}
        if vm is None:
            try:
                vm = self._get_vm(name)
                if vm is None:
                    error('VM %s not found' % name)
                    return yamlinfo
            except ApiException as exc:
                error('Unable to retrieve VM %s. %s' % (name, exc))
                return yamlinfo
        state = vm['status']
        if floating_ips is None:
            try:
                floating_ips = {x['target']['id']: x for x in
                                self.conn.list_floating_ips().result['floating_ips'] if x['status'] == 'available'}
            except ApiException as exc:
                error('Unable to retrieve floating ips. %s' % exc)
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
            except ApiException as exc:
                error("Unable to retrieve volume information. %s" % exc)
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
                error('VM %s not found' % name)
                return ""
            for network in vm['network_interfaces']:
                response = self.conn.list_instance_network_interface_floating_ips(vm['id'], network['id'])
                ips.extend([x['address'] for x in response.result['floating_ips'] if x['status'] == 'available'])
        except ApiException as exc:
            error("Unable to retrieve IP for %s. %s" % (name, exc))
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
        except ApiException as exc:
            error("Unable to retrieve volume information. %s" % exc)
            return image_list
        return sorted(image_list, key=str.lower)

    def delete(self, name, snapshots=False):
        conn = self.conn
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, exc)}
        tags = []
        try:
            tags = self.global_tagging_service.list_tags(attached_to=vm['crn']).result['items']
        except Exception as exc:
            error('Unable to retrieve tags. %s' % exc)
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
        except ApiException as exc:
            return {'result': 'failure',
                    'reason': 'Unable to remove floating IPs for VM %s. %s' % (name, exc)}
        try:
            conn.delete_instance(id=vm['id'])
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to delete VM. %s' % exc}
        if domain is not None and dnsclient is None:
            self.delete_dns(name, domain, name)
        return {'result': 'success'}

    def dnsinfo(self, name):
        dnsclient, domain = None, None
        try:
            vm = self._get_vm(name)
            if vm is None:
                error('VM %s not found' % name)
                return dnsclient, domain
        except ApiException as exc:
            error('Unable to retrieve VM. %s' % exc)
            return dnsclient, domain
        try:
            tags = self.global_tagging_service.list_tags(attached_to=vm['crn']).result['items']
        except ApiException as exc:
            error('Unable to retrieve tags. %s' % exc)
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
                error('VM %s not found' % name)
                return
        except ApiException as exc:
            error('Unable to retrieve VM %s. %s' % (name, exc))
            return
        resource_model = {'resource_id': vm['crn']}
        tag_names = ["%s:%s" % (metatype, metavalue)]
        try:
            self.global_tagging_service.attach_tag(resources=[resource_model],
                                                   tag_names=tag_names, tag_type='user').get_result()
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to attach tags. %s' % exc}

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
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, exc)}
        if vm['status'] != 'stopped':
            return {'result': 'failure', 'reason': 'VM %s must be stopped' % name}
        try:
            provisioned_profiles = self._get_profiles()
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve flavors. %s' % exc}
        if flavor not in provisioned_profiles:
            return {'result': 'failure', 'reason': 'Flavor %s not found' % flavor}
        try:
            self.conn.update_instance(id=vm['id'], instance_patch=vpc_v1.InstancePatch(
                profile=vpc_v1.InstancePatchProfileInstanceProfileIdentityByName(name=flavor)))
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to update instance. %s' % exc}
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")

    def add_disk(self, name, size, pool=None, thin=True, image=None,
                 shareable=False, existing=None, interface='virtio'):
        print("not implemented")

    def delete_disk(self, name, diskname, pool=None, novm=False):
        print("not implemented")

    def list_disks(self):
        print("not implemented")
        return {}

    def add_nic(self, name, network):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error('VM %s not found' % name)
                return
        except ApiException as exc:
            error('Unable to retrieve VM %s. %s' % (name, exc))
            return
        try:
            subnet = self._get_subnet(network)
            if subnet is None:
                error('Network %s not found' % network)
                return
        except ApiException as exc:
            error('Unable to retrieve network information. %s' % exc)
            return
        try:
            # TODO: better name. Follow ethX scheme.
            self.conn.create_instance_network_interface(
                instance_id=vm['id'],
                subnet=vpc_v1.SubnetIdentityById(id=subnet['id']),
                allow_ip_spoofing=False
            )
        except ApiException as exc:
            error('Unable to create NIC. %s' % exc)

    def delete_nic(self, name, interface):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error('VM %s not found' % name)
                return
        except ApiException as exc:
            error('Unable to retrieve VM %s. %s' % (name, exc))
        try:
            for network in vm['network_interfaces']:
                if network['name'] == interface:
                    response = self.conn.delete_instance_network_interface(instance_id=vm['id'],
                                                                           id=network['id'])
                    if response.status_code != 204:
                        error('Unexpected status code received: %d' % response.status_code)
        except ApiException as exc:
            error('Unable to delete NIC. %s' % exc)

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")

    def delete_image(self, image, pool=None):
        try:
            image = self._get_image(image)
            if image is None:
                return {'result': 'failure', 'reason': 'Image %s not found' % image}
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve images. %s' % exc}
        try:
            result = self.conn.delete_image(id=image['id'])
            if result.status_code != 202:
                return {'result': 'failure', 'reason': 'Unexpected status code received: %d' % result.status_code}
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to delete image. %s' % exc}
        return {'result': 'success'}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None):
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
            return {'result': 'failure', 'reason': "Bucket %s doesn't exist" % pool}
        shortimage = os.path.basename(url).split('?')[0]
        shortimage_unzipped = shortimage.replace('.gz', '')
        if shortimage_unzipped in self.volumes():
            return {'result': 'success'}
        delete_cos_image = False
        if shortimage_unzipped not in self.list_bucketfiles(pool):
            if not os.path.exists('/tmp/%s' % shortimage):
                downloadcmd = "curl -Lko /tmp/%s -f '%s'" % (shortimage, url)
                code = os.system(downloadcmd)
                if code != 0:
                    return {'result': 'failure', 'reason': "Unable to download indicated image"}
            if shortimage.endswith('gz'):
                if which('gunzip') is not None:
                    uncompresscmd = "gunzip /tmp/%s" % (shortimage)
                    os.system(uncompresscmd)
                else:
                    error("gunzip not found. Can't uncompress image")
                    return {'result': 'failure', 'reason': "gunzip not found. Can't uncompress image"}
                shortimage = shortimage_unzipped
            pprint("Uploading image to bucket")
            self.upload_to_bucket(pool, '/tmp/%s' % shortimage)
            os.remove('/tmp/%s' % shortimage)
            delete_cos_image = True
        pprint("Importing image as template")
        image_file_prototype_model = {}
        image_file_prototype_model['href'] = "cos://%s/%s/%s" % (self.region, pool, shortimage_unzipped)
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
                pprint("Waiting for image %s to be available" % clean_image_name)
                sleep(10)
        tag_names = ["image:%s" % shortimage_unzipped]
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
                return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
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
                return {'result': 'failure', 'reason': 'vpc %s does not exist' % self.vpc}
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve vpc information. %s' % exc}
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
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to create network. %s' % exc}
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        try:
            subnets = self._get_subnets()
            for subnet in subnets:
                if name == subnet['name']:
                    subnet_id = subnet['id']
                    break
            else:
                return {'result': 'failure', 'reason': 'Subnet %s not found' % name}
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to retrieve subnet %s information. %s' % (name, exc)}
        try:
            self.conn.delete_subnet(id=subnet_id)
        except ApiException as exc:
            return {'result': 'failure', 'reason': 'Unable to delete subnet %s. %s' % (name, exc)}
        return {'result': 'success'}

    def list_pools(self):
        print("not implemented")

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
        except ApiException as exc:
            error('Unable to retrieve subnets. %s' % exc)
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

    def flavors(self):
        flavor_list = []
        try:
            for profile in self.conn.list_instance_profiles().result['profiles']:
                flavor_list.append([profile['name'], profile['vcpu_count']['value'], profile['memory']['value']])
        except ApiException as exc:
            error("Unable to retrieve available flavors. %s" % exc)
            return []
        return flavor_list

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
                            internal=False, dnsclient=None, subnetid=None):

        ports = [int(port) for port in ports]
        internal = False if internal is None else internal
        clean_name = name.replace('.', '-')
        pprint("Creating Security Group %s" % clean_name)
        security_group_ports = ports + [int(checkport)] if int(checkport) not in ports else ports
        security_group_id = self.create_security_group(clean_name, security_group_ports)
        subnets = set()
        member_list = []
        resource_group_id = None
        if vms:
            for vm in vms:
                try:
                    virtual_machine = self._get_vm(vm)
                except ApiException as exc:
                    return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (vm, exc)}
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
                    name="%s-%s" % (clean_name, port),
                ) for port in ports],
                subnets=[vpc_v1.SubnetIdentityById(id=x) for x in subnets],
                resource_group_id=vpc_v1.ResourceGroupIdentityById(id=resource_group_id),
                security_groups=[vpc_v1.SecurityGroupIdentityById(id=security_group_id)],
            ).result
            self._wait_lb_active(id=lb['id'])
        except ApiException as exc:
            error('Unable to create load balancer. %s' % exc)
            return {'result': 'failure', 'reason': 'Unable to create load balancer. %s' % exc}
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
                except ApiException as exc:
                    error('Unable to create load balancer. %s' % exc)
                    return {'result': 'failure', 'reason': 'Unable to create load balancer. %s' % exc}
            except ApiException as exc:
                error('Unable to create load balancer listener. %s' % exc)
                return {'result': 'failure', 'reason': 'Unable to create load balancer listener. %s' % exc}
        pprint("Load balancer DNS name %s" % lb['hostname'])
        resource_model = {'resource_id': lb['crn']}
        try:
            tag_names = ['realname:%s' % name]
            if domain is not None:
                tag_names.append('domain:%s' % domain)
            if dnsclient is not None:
                tag_names.append('dnsclient:%s' % dnsclient)
            self.global_tagging_service.attach_tag(resources=[resource_model],
                                                   tag_names=tag_names,
                                                   tag_type='user')
        except ApiException as exc:
            error('Unable to attach tags. %s' % exc)
            return {'result': 'failure', 'reason': 'Unable to attach tags. %s' % exc}
        if domain is not None:
            while True:
                try:
                    result = self.conn.get_load_balancer(id=lb['id']).result
                except ApiException as exc:
                    pprint('Unable to check load balancer ip. %s' % exc)
                    return {'result': 'failure', 'reason': 'Unable to check load balancer ip. %s' % exc}
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
                error('Load balancer %s not found' % name)
                return
            lb = lbs[clean_name]
        except ApiException as exc:
            error('Unable to retrieve load balancers. %s' % exc)
            return
        try:
            tags = self.global_tagging_service.list_tags(attached_to=lb['crn']).result['items']
        except ApiException as exc:
            error('Unable to retrieve tags. %s' % exc)
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
        except ApiException as exc:
            error('Unable to delete load balancer. %s' % exc)
            return
        if domain is not None and dnsclient is None:
            pprint("Deleting DNS %s.%s" % (realname, domain))
            self.delete_dns(realname, domain, name)
        self._wait_lb_dead(id=lb['id'])
        try:
            pprint("Deleting Security Group %s" % clean_name)
            self.delete_security_group(clean_name)
        except Exception as exc:
            error('Unable to delete security group. %s' % exc)
        if dnsclient is not None:
            return dnsclient

    def list_loadbalancers(self):
        results = []
        try:
            lbs = self.conn.list_load_balancers().result['load_balancers']
        except ApiException as exc:
            error('Unable to retrieve LoadBalancers. %s' % exc)
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
            except ApiException as exc:
                error('Unable to retrieve listeners for load balancer %s. %s' % (name, exc))
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
            error("Bucket %s already there" % bucket)
            return
        # location = {'LocationConstraint': self.region}
        args = {'Bucket': bucket}  # , "CreateBucketConfiguration": location} #TODO: fix this.
        if public:
            args['ACL'] = 'public-read'
        self.s3.create_bucket(**args)

    def delete_bucket(self, bucket):
        if bucket not in self.list_buckets():
            error("Inexistent bucket %s" % bucket)
            return
        for obj in self.s3.list_objects(Bucket=bucket).get('Contents', []):
            key = obj['Key']
            pprint("Deleting object %s from bucket %s" % (key, bucket))
            self.s3.delete_object(Bucket=bucket, Key=key)
        self.s3.delete_bucket(Bucket=bucket)

    def delete_from_bucket(self, bucket, path):
        if bucket not in self.list_buckets():
            error("Inexistent bucket %s" % bucket)
            return
        self.s3.delete_object(Bucket=bucket, Key=path)

    def download_from_bucket(self, bucket, path):
        self.s3.download_file(bucket, path, path)

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        if not os.path.exists(path):
            error("Invalid path %s" % path)
            return None
        if bucket not in self.list_buckets():
            error("Bucket %s doesn't exist" % bucket)
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
            error("Inexistent bucket %s" % bucket)
            return []
        return [obj['Key'] for obj in self.s3.list_objects(Bucket=bucket).get('Contents', [])]

    def public_bucketfile_url(self, bucket, path):
        return "https://s3.direct.%s.cloud-object-storage.appdomain.cloud/%s/%s" % (self.region, bucket, path)

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None):
        if domain is None:
            domain = nets[0]
        pprint("Using domain %s..." % domain)
        cluster = None
        fqdn = "%s.%s" % (name, domain)
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace("%s." % name, '').replace("%s." % cluster, '')
        dnszone = self._get_dns_zone(domain)
        if dnszone is None:
            return
        if ip is None:
            counter = 0
            while counter != 100:
                ip = self.internalip(name)
                if ip is None:
                    sleep(5)
                    pprint(
                        "Waiting 5 seconds to grab internal ip and create DNS record for %s..." % name)
                    counter += 10
                else:
                    break
        if ip is None:
            error('Unable to find an IP for %s' % name)
            return
        try:
            dnszone.create_dns_record(name=name, type='A', ttl=60, content=ip)
        except ApiException as exc:
            error('Unable to create DNS entry. %s' % exc)
            return
        if alias:
            for a in alias:
                if a == '*':
                    record_type = 'A'
                    content = ip
                    if cluster is not None and ('master' in name or 'worker' in name):
                        dnsname = '*.apps.%s.%s' % (cluster, domain)
                    else:
                        dnsname = '*.%s.%s' % (name, domain)
                else:
                    record_type = 'CNAME'
                    content = "%s.%s" % (name, domain)
                    dnsname = '%s.%s' % (a, domain) if '.' not in a else a
                try:
                    dnszone.create_dns_record(name=dnsname, type=record_type, ttl=60, content=content)
                except ApiException as exc:
                    error('Unable to create DNS entry. %s' % exc)
                    return

    def create_dns(self):
        print("not implemented")

    def delete_dns(self, name, domain, instanceid=None, allentries=False):
        dnszone = self._get_dns_zone(domain)
        if dnszone is None:
            return
        cluster = None
        fqdn = "%s.%s" % (name, domain)
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace("%s." % name, '').replace("%s." % cluster, '')
        dnsentry = name if cluster is None else "%s.%s" % (name, cluster)
        entry = "%s.%s" % (dnsentry, domain)
        clusterdomain = "%s.%s" % (cluster, domain)
        try:
            records = dnszone.list_all_dns_records().get_result()['result']
        except ApiException as exc:
            error('Unable to check DNS %s records. %s' % (dnszone['name'], exc))
            return
        recordsfound = False
        for record in records:
            if entry in record['name'] or ('master-0' in name and record['name'].endswith(clusterdomain))\
                    or (record['type'] == 'CNAME' and record['content'] == entry):
                record_identifier = record['id']
                try:
                    dnszone.delete_dns_record(dnsrecord_identifier=record_identifier)
                    recordsfound = True
                except ApiException as exc:
                    error('Unable to delete record %s. %s' % (record['name'], exc))
        if not recordsfound:
            error("No records found for %s" % entry)
        return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        dnszone = self._get_dns_zone(domain)
        if dnszone is None:
            return []
        try:
            records = dnszone.list_all_dns_records().get_result()['result']
        except ApiException as exc:
            error('Unable to check DNS %s records. %s' % (dnszone['name'], exc))
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
        except ApiException as exc:
            error('Unable to check DNS resources. %s' % exc)
            return None
        dnsfound = False
        for dnsresource in dnslist:
            dnsid = dnsresource['id']
            dnsname = dnsresource['name']
            if dnsname == domain:
                dnsfound = True
                break
        if not dnsfound:
            error('Domain %s not found' % domain)
            return None
        try:
            dnszone = DnsRecordsV1(authenticator=self.authenticator, crn=self.cis_resource_instance_id,
                                   zone_identifier=dnsid)
        except ApiException as exc:
            error('Unable to check DNS zones for DNS %s. %s' % (domain, exc))
            return None
        return dnszone

    def create_security_group(self, name, ports):
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
            security_group_rule_prototype_model = {}
            security_group_rule_prototype_model['direction'] = 'inbound'
            security_group_rule_prototype_model['ip_version'] = 'ipv4'
            security_group_rule_prototype_model['protocol'] = 'tcp'
            security_group_rule_prototype_model['port_min'] = port
            security_group_rule_prototype_model['port_max'] = port
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
        security_group_id = self.create_security_group("%s-sno" % cluster, [80, 443, 6443])
        vm = self._get_vm("%s-master-0" % cluster)
        nic_id = vm['primary_network_interface']['id']
        self.conn.add_security_group_network_interface(security_group_id, nic_id)

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
        return {'result': 'success'}
