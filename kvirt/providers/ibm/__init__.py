#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IBM Cloud provider class
"""

from kvirt import common
from kvirt.common import pprint, error
import ibm_vpc
from netaddr import IPNetwork
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
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
    def __init__(self, iam_api_key, access_key_id, secret_access_key, region, zone, vpc, debug=False):
        self.debug = debug
        self.authenticator = IAMAuthenticator(iam_api_key)
        self.conn = ibm_vpc.VpcV1(authenticator=self.authenticator)
        self.conn.set_service_url(ENDPOINTS.get(region))
        self.s3 = ibm_boto3.client(
            's3',
            endpoint_url=get_s3_endpoint(region),
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
        self.iam_api_key = iam_api_key
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.zone = zone
        self.vpc = vpc
        return

    def close(self):
        return

    def exists(self, name):
        try:
            return self._get_vm(name) is not None
        except Exception as e:
            error("Unable to retrieve VM. %s" % e)
            return False

    def net_exists(self, name):
        try:
            return self._get_subnet(name) is not None
        except Exception as e:
            error("Unable to retrieve available subnets. %s" % (e))
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
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve vpc information. %s' % e}

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
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to check keys. %s' % e}
        if cloudinit:
            if image is not None and common.needs_ignition(image):
                version = common.ignition_version(image)
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                           overrides=overrides, version=version, plan=plan, image=image)
            else:
                userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                            domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                            overrides=overrides, fqdn=True, storemetadata=storemetadata)[0]
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
                    ibm_vpc.vpc_v1.NetworkInterfacePrototype(
                        subnet=ibm_vpc.vpc_v1.SubnetIdentityById(id=subnet['id']),
                        allow_ip_spoofing=False,
                        name="eth{}".format(index)
                        # TODO: security groups, ip address
                    )
                )
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to check networks. %s' % e}

        if flavor is None:
            return {'result': 'failure', 'reason': 'Flavor not found in configuration'}
        try:
            provisioned_profiles = self._get_profiles()
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to check flavors. %s' % e}
        if flavor not in provisioned_profiles:
            return {'result': 'failure', 'reason': 'Flavor %s not found' % flavor}

        try:
            image = self._get_image(image)
            if image is None:
                return {'result': 'failure', 'reason': 'Image %s not found' % image}
            image_id = image['id']
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to check provisioned images. %s' % e}

        volume_attachments = []
        for disk in disks:
            volume_attachments.append(
                ibm_vpc.vpc_v1.VolumeAttachmentPrototypeInstanceContext(
                    volume=ibm_vpc.vpc_v1.VolumeAttachmentVolumePrototypeInstanceContextVolumePrototypeInstanceContextVolumePrototypeInstanceContextVolumeByCapacity(
                        profile=ibm_vpc.vpc_v1.VolumeProfileIdentityByName(
                            name='general-purpose'
                        ),
                        capacity=disk.get('size', '100'),
                    ),
                    delete_volume_on_instance_delete=True,
                )
            )

        try:
            result_create = self.conn.create_instance(
                ibm_vpc.vpc_v1.InstancePrototypeInstanceByImage(
                    image=ibm_vpc.vpc_v1.ImageIdentityById(id=image_id),
                    primary_network_interface=net_list[0],
                    zone=ibm_vpc.vpc_v1.ZoneIdentityByHref(get_zone_href(self.region, self.zone)),
                    keys=[ibm_vpc.vpc_v1.KeyIdentityById(id=x) for x in key_list],
                    name=name,
                    network_interfaces=net_list[1:],
                    profile=ibm_vpc.vpc_v1.InstanceProfileIdentityByName(
                        name=flavor),
                    resource_group=ibm_vpc.vpc_v1.ResourceGroupIdentityById(id=resource_group_id),
                    volume_attachments=volume_attachments,
                    vpc=ibm_vpc.vpc_v1.VPCIdentityById(id=vpc_id),
                    user_data=userdata
                )
            ).result
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to create VM %s. %s' % (name, e)}

        try:
            result_ip = self.conn.create_floating_ip(ibm_vpc.vpc_v1.FloatingIPPrototypeFloatingIPByTarget(
                target=ibm_vpc.vpc_v1.FloatingIPByTargetNetworkInterfaceIdentityNetworkInterfaceIdentityById(
                    id=result_create['network_interfaces'][0]['id']
                ),
                name=name,
                resource_group=ibm_vpc.vpc_v1.ResourceGroupIdentityById(
                    id=resource_group_id),
            )).result
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to create floating ip. %s' % e}
        try:
            self.conn.add_instance_network_interface_floating_ip(
                instance_id=result_create['id'],
                network_interface_id=result_create['network_interfaces'][0]['id'],
                id=result_ip['id']
            )
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to add floating ip. %s' % e}
        return {'result': 'success'}

    def start(self, name):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
            vm_id = vm['id']
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, e)}

        try:
            self.conn.create_instance_action(instance_id=vm_id, type='start')
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to start VM %s. %s' % (name, e)}
        return {'result': 'success'}

    def stop(self, name):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
            vm_id = vm['id']
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, e)}
        try:
            self.conn.create_instance_action(instance_id=vm_id, type='stop')
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to stop VM %s. %s' % (name, e)}
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        print("not implemented")
        return

    def restart(self, name):
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
            vm_id = vm['id']
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, e)}
        try:
            self.conn.create_instance_action(instance_id=vm_id, type='reboot')
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to restart VM %s. %s' % (name, e)}
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
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, e)}

    def list(self):
        vms = []
        try:
            provisioned_vms = self._get_vms()
        except Exception as e:
            error('Unable to retrieve VMs. %s' % e)
            return vms
        try:
            floating_ips = {x['target']['id']: x for x in self.conn.list_floating_ips(
            ).result['floating_ips'] if x['status'] == 'available'}
        except Exception as e:
            error('Unable to retrieve floating ips. %s' % e)
            return vms
        for vm in provisioned_vms:
            vms.append(self.info(vm['name'], vm=vm, ignore_volumes=True, floating_ips=floating_ips))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error("VM %s not found" % name)
        except Exception as e:
            error("Unable to retrieve VM %s. %s" % (name, e))
            return
        try:
            url = self.conn.create_instance_console_access_token(
                instance_id=vm['id'], console_type='serial').result['href']
        except Exception as e:
            error("Unable to retrieve console access. %s" % e)
            return
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = "Open the following url:\n%s" % url if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint("Opening url: %s" % url)
            webbrowser.open(url, new=2, autoraise=True)
        return

    def serialconsole(self, name, web=False):
        print("not implemented")
        return

    def info(self, name, output='plain', fields=[], values=False, vm=None, ignore_volumes=False, floating_ips=None,
             debug=False):
        yamlinfo = {}
        if vm is None:
            try:
                vm = self._get_vm(name)
                if vm is None:
                    error('VM %s not found' % name)
                    return yamlinfo
            except Exception as e:
                error('Unable to retrieve VM %s. %s' % (name, e))
                return yamlinfo
        state = vm['status']
        if floating_ips is None:
            try:
                floating_ips = {x['target']['id']: x for x in
                                self.conn.list_floating_ips().result['floating_ips'] if x['status'] == 'available'}
            except Exception as e:
                error('Unable to retrieve floating ips. %s' % e)
                return yamlinfo
        ips = []
        for network in vm['network_interfaces']:
            if network['id'] not in floating_ips:
                continue
            ips.append(floating_ips[network['id']]['address'])
        ip = ','.join(ips)

        zone = vm['zone']['name']
        image = vm['image']['name']
        yamlinfo['profile'] = vm['profile']['name']
        yamlinfo['name'] = name
        yamlinfo['status'] = state
        yamlinfo['region'] = self.region
        yamlinfo['zone'] = zone
        yamlinfo['ip'] = ip
        yamlinfo['public_ip'] = ip
        yamlinfo['bandwidth'] = vm['bandwidth']
        yamlinfo['profile'] = vm['profile']['name']
        yamlinfo['cpus'] = vm['vcpu']['count']
        yamlinfo['memory'] = vm['memory']
        yamlinfo['image'] = image
        yamlinfo['creation_date'] = vm['created_at']
        yamlinfo['id'] = vm['id']
        yamlinfo['resource_group'] = vm['resource_group']['name']
        yamlinfo['resource_type'] = vm['resource_type']
        yamlinfo['startable'] = vm['startable']
        yamlinfo['vpc'] = vm['vpc']['name']

        nets = []
        for interface in vm['network_interfaces']:
            network = interface['subnet']['name']
            device = interface['name']
            private_ip = interface['primary_ipv4_address']
            nets.append({'device': device, 'net': network, 'type': private_ip, 'mac': 'N/A'})
            yamlinfo['private_ip'] = private_ip
        if nets:
            yamlinfo['nets'] = nets
            yamlinfo['primary_network_interface'] = vm['primary_network_interface']['name']

        disks = []
        if ignore_volumes is False:
            try:
                volumes = self._get_volumes()
            except Exception as e:
                error("Unable to retrieve volume information. %s" % e)
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
        except Exception as e:
            error("Unable to retrieve IP for %s. %s" % (name, e))
        return ','.join(ips)

    def volumes(self, iso=False):
        image_list = []
        try:
            images = self.conn.list_images().result['images']
            for image in images:
                if image['status'] not in ['available', 'deprecated'] or \
                        image['operating_system']['name'].startswith('windows'):
                    continue
                image_list.append(image['name'])
        except Exception as e:
            error("Unable to retrieve volume information. %s" % e)
            return image_list
        return sorted(image_list, key=str.lower)

    def delete(self, name, snapshots=False):
        conn = self.conn
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, e)}

        try:
            for network in vm['network_interfaces']:
                response = conn.list_instance_network_interface_floating_ips(instance_id=vm['id'],
                                                                             network_interface_id=network['id']).result
                if len(response['floating_ips']) == 0:
                    continue
                for floating_ip in response['floating_ips']:
                    conn.remove_instance_network_interface_floating_ip(id=floating_ip['id'], instance_id=vm['id'],
                                                                       network_interface_id=network['id'])
                    conn.delete_floating_ip(id=floating_ip['id'])
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to remove floating IPs for VM %s. %s' % (name, e)}
        try:
            conn.delete_instance(id=vm['id'])
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to delete VM. %s' % e}
        return {'result': 'success'}

    def dnsinfo(self, name):
        return None, None

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        print("not implemented")
        return

    def update_memory(self, name, memory):
        print("not implemented")
        return

    def update_cpus(self, name, numcpus):
        print("not implemented")
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
        try:
            vm = self._get_vm(name)
            if vm is None:
                return {'result': 'failure', 'reason': 'VM %s not found' % name}
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve VM %s. %s' % (name, e)}

        if vm['status'] != 'stopped':
            return {'result': 'failure', 'reason': 'VM %s must be stopped' % name}

        try:
            provisioned_profiles = self._get_profiles()
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve flavors. %s' % e}
        if flavor not in provisioned_profiles:
            return {'result': 'failure', 'reason': 'Flavor %s not found' % flavor}

        try:
            self.conn.update_instance(id=vm['id'], instance_patch=ibm_vpc.vpc_v1.InstancePatch(
                profile=ibm_vpc.vpc_v1.InstancePatchProfileInstanceProfileIdentityByName(name=flavor)))
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to update instance. %s' % e}
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None,
                 shareable=False, existing=None, interface='virtio'):
        print("not implemented")
        return

    def delete_disk(self, name, diskname, pool=None, novm=False):
        print("not implemented")
        return

    def list_disks(self):
        print("not implemented")
        return {}

    def add_nic(self, name, network):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error('VM %s not found' % name)
                return
        except Exception as e:
            error('Unable to retrieve VM %s. %s' % (name, e))
            return
        try:
            subnet = self._get_subnet(network)
            if subnet is None:
                error('Network %s not found' % network)
                return
        except Exception as e:
            error('Unable to retrieve network information. %s' % e)
            return
        try:
            # TODO: better name. Follow ethX scheme.
            self.conn.create_instance_network_interface(
                instance_id=vm['id'],
                subnet=ibm_vpc.vpc_v1.SubnetIdentityById(id=subnet['id']),
                allow_ip_spoofing=False
            )
        except Exception as e:
            error('Unable to create NIC. %s' % e)

    def delete_nic(self, name, interface):
        try:
            vm = self._get_vm(name)
            if vm is None:
                error('VM %s not found' % name)
                return
        except Exception as e:
            error('Unable to retrieve VM %s. %s' % (name, e))
        try:
            for network in vm['network_interfaces']:
                if network['name'] == interface:
                    response = self.conn.delete_instance_network_interface(instance_id=vm['id'], id=network['id'])
                    if response.status_code != 204:
                        error('Unexpected status code received: %d' % response.status_code)
        except Exception as e:
            error('Unable to delete NIC. %s' % e)

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")
        return

    def delete_image(self, image):
        try:
            image = self._get_image(image)
            if image is None:
                return {'result': 'failure', 'reason': 'Image %s not found' % image}
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve images. %s' % e}
        try:
            result = self.conn.delete_image(id=image['id'])
            if result.status_code != 202:
                return {'result': 'failure', 'reason': 'Unexpected status code received: %d' % result.status_code}
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to delete image. %s' % e}
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
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve vpc information. %s' % e}
        try:
            self.conn.create_subnet(ibm_vpc.vpc_v1.SubnetPrototypeSubnetByCIDR(
                name=name,
                ipv4_cidr_block=cidr,
                vpc=ibm_vpc.vpc_v1.VPCIdentityById(id=vpc_id),
                resource_group=ibm_vpc.vpc_v1.ResourceGroupIdentityById(id=resource_group_id),
                zone=ibm_vpc.vpc_v1.ZoneIdentityByHref(
                    href=get_zone_href(self.region, self.zone)
                ),
            ))
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to create network. %s' % e}
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
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to retrieve subnet %s information. %s' % (name, e)}
        try:
            self.conn.delete_subnet(id=subnet_id)
        except Exception as e:
            return {'result': 'failure', 'reason': 'Unable to delete subnet %s. %s' % (name, e)}
        return {'result': 'success'}

    def list_pools(self):
        print("not implemented")
        return

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
        except Exception as e:
            error('Unable to retrieve subnets. %s' % e)
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
        return

    def network_ports(self, name):
        return []

    def vm_ports(self, name):
        return []

    def get_pool_path(self, pool):
        print("not implemented")
        return

    def flavors(self):
        flavor_list = []
        try:
            for profile in self.conn.list_instance_profiles().result['profiles']:
                flavor_list.append([profile['name'], profile['vcpu_count']['value'], profile['memory']['value']])
        except Exception as e:
            error("Unable to retrieve available flavors. %s" % e)
            return []
        return flavor_list

    def export(self, name, image=None):
        print("not implemented")
        return

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
            return
        if bucket not in self.list_buckets():
            error("Bucket %s doesn't exist" % bucket)
            return
        ExtraArgs = {'Metadata': overrides} if overrides else {}
        if public:
            ExtraArgs['ACL'] = 'public-read'
        dest = os.path.basename(path)
        with open(path, "rb") as f:
            self.s3.upload_fileobj(f, bucket, dest, ExtraArgs=ExtraArgs)
        if temp_url:
            expiration = 600
            return self.s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': dest},
                                                  ExpiresIn=expiration)

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
