#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IBM Cloud provider class
"""

from kvirt import common
from kvirt.common import pprint, error
from kvirt.defaults import METADATA_FIELDS
from ibm_vpc import VpcV1, vpc_v1
from netaddr import IPNetwork
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core.api_exception import ApiException
from ibm_platform_services import GlobalTaggingV1, ResourceControllerV2
from ibm_cloud_networking_services import DnsSvcsV1, dns_svcs_v1
from time import sleep
import os
import ibm_boto3
import webbrowser

ENDPOINTS = {
    'us-south': 'https://us-south.iaas.cloud.ibm.com/v1',
    'us-east': 'https://us-east.iaas.cloud.ibm.com/v1',
    'ca-tor': 'https://ca-tor.iaas.cloud.ibm.com/v1',
    'eu-gb': 'https://eu-gb.iaas.cloud.ibm.com/v1',
    'eu-de': 'https://eu-de.iaas.cloud.ibm.com/v1',
    'jp-tok': 'https://jp-tok.iaas.cloud.ibm.com/v1',
    'jp-osa': 'https://jp-osa.iaas.cloud.ibm.com/v1',
    'au-syd': 'https://au-syd.iaas.cloud.ibm.com/v1'
}

DNS_RESOURCE_ID = 'b4ed8a30-936f-11e9-b289-1d079699cbe5'

def get_zone_href(region, zone):
    return "{}/regions/{}/zones/{}".format(
        ENDPOINTS.get(region),
        region,
        zone
    )


def get_s3_endpoint(region):
    return 'https://s3.{}.cloud-object-storage.appdomain.cloud'.format(region)


class Kibm(object):
    """

    """
    def __init__(self, iam_api_key, access_key_id, secret_access_key,
                 region, zone, vpc, debug=False):
        self.debug = debug
        self.authenticator = IAMAuthenticator(iam_api_key)
        self.conn = VpcV1(authenticator=self.authenticator)
        self.conn.set_service_url(ENDPOINTS.get(region))
        self.s3 = ibm_boto3.client(
            's3',
            endpoint_url=get_s3_endpoint(region),
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
        self.global_tagging_service = GlobalTaggingV1(authenticator=self.authenticator)
        self.global_tagging_service.set_service_url('https://tags.global-search-tagging.cloud.ibm.com')

        self.dns = DnsSvcsV1(authenticator=self.authenticator)
        self.dns.set_service_url('https://api.dns-svcs.cloud.ibm.com/v1')

        self.resources = ResourceControllerV2(authenticator=self.authenticator)
        self.resources.set_service_url('https://resource-controller.cloud.ibm.com')

        self.iam_api_key = iam_api_key
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.zone = zone
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
               diskinterface='virtio', nets=[], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=None, cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags=[], storemetadata=False, sharedfolders=[], kernel=None, initrd=None, cmdline=None,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False,
               placement=[], autostart=False, rng=False, metadata={}, securitygroups=[]):
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

        if keys is None:
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
                                           domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                           overrides=overrides, version=version, plan=plan, image=image)
            else:
                userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                            domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                            overrides=overrides,fqdn=True, storemetadata=storemetadata)[0]
        else:
            userdata = ''
        if len(nets) == 0:
            return {'result': 'failure', 'reason': 'Network not found in configuration'}
        net_list = []
        subnets = {x['name']: x for x in self._get_subnets()}
        try:
            subnets = {x['name']: x for x in self._get_subnets()}
            for index, net in enumerate(nets):
                if isinstance(net, str):
                    netname = net
                elif isinstance(net, dict) and 'name' in net:
                    netname = net['name']
                if netname not in subnets:
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
            return {'result': 'failure', 'reason': 'Flavor not found in configuration'}
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
            disksize = int(disk.get('size')) if isinstance(disk, list) and 'size' in disk else int(disk)
            diskname = "%s-disk%s" % (name, index + 1)
            volume_attachments.append(
                vpc_v1.VolumeAttachmentPrototypeInstanceContext(
                    volume=vpc_v1.VolumeAttachmentVolumePrototypeInstanceContextVolumePrototypeInstanceContextVolumePrototypeInstanceContextVolumeByCapacity(
                        profile=vpc_v1.VolumeProfileIdentityByName(
                            name='general-purpose'
                        ),
                        capacity=disksize,
                        name=diskname
                    ),
                    delete_volume_on_instance_delete=True,
                )
            )

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
                target= vpc_v1.FloatingIPByTargetNetworkInterfaceIdentityNetworkInterfaceIdentityById(
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

    def stop(self, name):
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

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")

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
            url = self.conn.create_instance_console_access_token(
                instance_id=vm['id'], console_type='serial').result['href']
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
        print("not implemented")

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
        except ApiException as exc:
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

        try:
            tags = self.global_tagging_service.list_tags(attached_to=vm['crn']).result['items']
        except ApiException as exc:
            error('Unable to retrieve tags. %s' % exc)
            return None, None
        domain = None
        for tag in tags:
            tagname = tag['name']
            if tagname.count(':') == 1:
                key, value = tagname.split(':')
                if key == 'domain':
                    domain = value

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
        if domain is not None:
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
        print("not implemented")

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
                    profile=vpc_v1.InstancePatchProfileInstanceProfileIdentityByName(name=flavor)
                )
            )
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

    def delete_image(self, image):
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
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        if cidr is not None:
            try:
                network = IPNetwork(cidr)
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
        with open(path, "rb") as file:
            self.s3.upload_fileobj(file, bucket, dest, ExtraArgs=extra_args)
        if temp_url:
            expiration = 600
            return self.s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': dest},
                                                  ExpiresIn=expiration)
        return None

    def list_buckets(self):
        response = self.s3.list_buckets()
        return [bucket["Name"] for bucket in response['Buckets']]

    def list_bucketfiles(self, bucket):
        if bucket not in self.list_buckets():
            error("Inexistent bucket %s" % bucket)
            return []
        return [obj['Key'] for obj in self.s3.list_objects(Bucket=bucket).get('Contents', [])]

    def public_bucketfile_url(self, bucket, path):
        return 'https://{}.s3.{}.cloud-object-storage.appdomain.cloud/{}'.format(bucket, self.region, path)

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
        try:
            dnslist = self._get_dns()
        except ApiException as exc:
            error('Unable to retrieve DNS service. %s' % exc)

        for dns in dnslist:
            try:
                dnszone = self._get_dns_zone(dns['guid'], domain)
            except ApiException as exc:
                error('Unable to retrieve DNS zones. %s' % exc)
                return
            if dnszone is not None:
                break
        else:
            error('Domain %s not found' % domain)
            return

        dnsentry = name if cluster is None else "%s.%s" % (name, cluster)
        entry = "%s.%s" % (dnsentry, domain)
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
            self.dns.create_resource_record(
                instance_id=dns['guid'],
                dnszone_id=dnszone['id'],
                type='A',
                ttl=60,
                name=entry,
                rdata=dns_svcs_v1.ResourceRecordInputRdataRdataARecord(ip=ip),
            )
        except ApiException as exc:
            error('Unable to create DNS entry. %s' % exc)
            return


        if alias:
            for a in alias:
                dnsname = ''
                type = ''
                rdata = None
                if a == '*':
                    type = 'A'
                    rdata = dns_svcs_v1.ResourceRecordInputRdataRdataARecord(ip=ip)
                    if cluster is not None and ('master' in name or 'worker' in name):
                        dnsname = '*.apps.%s.%s' % (cluster, domain)
                    else:
                        dnsname = '*.%s.%s' % (name, domain)
                else:
                    type = 'CNAME'
                    dnsname = '%s.%s' % (a, domain) if '.' not in a else a
                    rdata = dns_svcs_v1.ResourceRecordInputRdataRdataCnameRecord(cname=entry)
                try:
                    print("Creating", dnsname, type, entry, ip)
                    self.dns.create_resource_record(
                        instance_id=dns['guid'],
                        dnszone_id=dnszone['id'],
                        type=type,
                        ttl=60,
                        name=dnsname,
                        rdata=rdata
                    )
                except ApiException as exc:
                    error('Unable to create DNS entry. %s' % exc)
                    return

    def create_dns(self):
        print("not implemented")

    def delete_dns(self, name, domain, instanceid=None):
        cluster = None
        fqdn = "%s.%s" % (name, domain)
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace("%s." % name, '').replace("%s." % cluster, '')

        try:
            dnslist = self._get_dns()
        except ApiException as exc:
            return {'result': 'failure',
                    'reason': 'Unable to check DNS zones. %s' % exc}
        for dnsresource in dnslist:
            dnsid = dnsresource['guid']
            try:
                dnszone = self._get_dns_zone(dnsid, domain)
            except ApiException as exc:
                return {'result': 'failure',
                        'reason': 'Unable to check DNS zones. %s' % exc}
            if dnszone is None:
                continue
            try:
                records = self._get_dns_records(dnsid, dnszone['id'])
            except ApiException as exc:
                return {'result': 'failure',
                        'reason': 'Unable to check DNS records. %s' % exc}
            break
        else:
            return {'result': 'failure',
                    'reason': 'Domain %s not found' % domain}

        dnsentry = name if cluster is None else "%s.%s" % (name, cluster)
        entry = "%s.%s" % (dnsentry, domain)
        clusterdomain = "%s.%s" % (cluster, domain)
        for record in records:
            if entry in record['name'] or ('master-0' in name and record['name'].endswith(clusterdomain)):
                try:
                    self.dns.delete_resource_record(instance_id=dnsid, dnszone_id=dnszone['id'], record_id=record['id'])
                except ApiException as exc:
                    error('Unable to delete record %s. %s' % (record['name'], exc))
        return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        try:
            dnslist = self._get_dns()
        except ApiException as exc:
            error('Unable to check DNS resources. %s' % exc)
            return results
        for dnsresource in dnslist:
            dnsid = dnsresource['guid']
            try:
                dnszone = self._get_dns_zone(dnsid, domain)
            except ApiException as exc:
                error('Unable to check DNS zones for DNS %s. %s' % (dnsresource['name'], exc))
                return results
            if dnszone is None:
                error('Domain %s not found' % domain)
                return results
            try:
                records = self._get_dns_records(dnsid, dnszone['id'])
            except ApiException as exc:
                error('Unable to check DNS %s records. %s' % (dnszone['name'], exc))
                return results
            for record in records:
                ip = record['rdata']['ip'] if 'ip' in record['rdata'] else record['rdata']['cname']
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

    def _get_dns(self):
        return self.resources.list_resource_instances(resource_id=DNS_RESOURCE_ID).result['resources']

    def _get_dns_zone(self, dns_id, domain):
        for zone in self.dns.list_dnszones(instance_id=dns_id).result['dnszones']:
            if zone['name'] == domain and zone['state'] == 'ACTIVE':
                return zone
        return None

    def _get_dns_records(self, dns_id, zone_id):
        return self.dns.list_resource_records(instance_id=dns_id, dnszone_id=zone_id).result['resource_records']
