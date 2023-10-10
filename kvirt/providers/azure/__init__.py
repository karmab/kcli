#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base64 import b64encode
from ipaddress import ip_network
from kvirt import common
from kvirt.defaults import IMAGES, METADATA_FIELDS
from kvirt.common import error, warning, pprint
from azure.identity import ClientSecretCredential
from azure.mgmt.marketplaceordering import MarketplaceOrderingAgreements
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import SecurityRule
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import DiskCreateOption
from azure.storage.blob import BlobServiceClient
from azure.mgmt.dns import DnsManagementClient
import os
from random import choice
from string import ascii_letters, digits
from time import sleep
from urllib.request import urlopen
import webbrowser

URNS = [
    'OpenLogic:CentOS:7.5:latest',
    'OpenLogic:CentOS:8_5-gen2:latest'
    'Debian:debian-10:10:latest',
    'Debian:debian-11:11-backports-gen2:latest',
    'kinvolk:flatcar-container-linux-free:stable:latest',
    'kinvolk:flatcar-container-linux-free:stable-gen2:latest',
    'SUSE:opensuse-leap-15-3:gen2:latest',
    'SUSE:openSUSE-leap-15-4:gen2:latest',
    'RedHat:RHEL:7-LVM:latest',
    'RedHat:RHEL:8-lvm-gen2:latest',
    'RedHat:RHEL:9_2:latest',
    'SUSE:sles-15-sp3:gen2:latest',
    'SUSE:sles-15-sp3:gen2:latest',
    'Canonical:UbuntuServer:18.04-LTS:latest',
    'Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest',
    'MicrosoftWindowsServer:WindowsServer:2022-Datacenter:latest',
    'MicrosoftWindowsServer:WindowsServer:2022-datacenter-azure-edition-core:latest',
    'MicrosoftWindowsServer:WindowsServer:2019-Datacenter:latest',
    'MicrosoftWindowsServer:WindowsServer:2016-Datacenter:latest',
    'MicrosoftWindowsServer:WindowsServer:2012-R2-Datacenter:latest',
    'MicrosoftWindowsServer:WindowsServer:2012-Datacenter:latest',
    'MicrosoftWindowsServer:WindowsServer:2008-R2-SP1:latest'
]


def valid_password(password):
    return len(password) >= 8 and any(not c.isalnum() for c in password)\
        and any(c.isupper() for c in password) and any(c.islower() for c in password)


class Kazure(object):
    def __init__(self, subscription_id, tenant_id, app_id, secret, location='westus', resource_group='kcli',
                 admin_user='superadmin', admin_password=None, mail=None, storageaccount=None, debug=False):
        credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=secret)
        self.subscription_id = subscription_id
        self.resource_client = ResourceManagementClient(credential, subscription_id)
        self.compute_client = ComputeManagementClient(credential, subscription_id)
        self.conn = self.compute_client
        self.network_client = NetworkManagementClient(credential, subscription_id)
        self.agreements = MarketplaceOrderingAgreements(credential, subscription_id)
        self.resource_client.resource_groups.create_or_update(resource_group, {'location': location})
        self.location = location
        self.resource_group = resource_group
        self.debug = debug
        self.admin_user = admin_user
        if admin_password is not None and not valid_password(admin_password):
            error("admin_password doesn't comply with policy. It needs at least 8chars and a special character")
            self.conn = None
            return
        else:
            self.admin_password = admin_password
        self.mail = mail
        if storageaccount is not None:
            self.blob_service_client = BlobServiceClient(f"https://{storageaccount}.blob.core.windows.net",
                                                         credential=credential)
            self.storageaccount = storageaccount
        self.dns_client = DnsManagementClient(credential, subscription_id)

    def close(self):
        print("not implemented")

    def exists(self, name):
        try:
            self.compute_client.virtual_machines.get(self.resource_group, name)
            return True
        except:
            return False

    def net_exists(self, name):
        networks, subnets = [], []
        for network in self.network_client.virtual_networks.list(self.resource_group):
            networks.append(network.name)
            for subnet in self.network_client.subnets.list(self.resource_group, network.name):
                subnets.append(os.path.basename(subnet.id))
        return name in networks + subnets

    def disk_exists(self, pool, name):
        return name in [os.path.basename(d.name) for d in self.compute_client.disks.list(self.resource_group)]

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[], kernel=None,
               initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False,
               numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[],
               vmuser=None):
        if flavor is None:
            matching = [f for f in self.list_flavors() if f[1] >= numcpus and f[2] >= memory]
            if matching:
                flavor = matching[0][0]
                pprint(f"Using flavor {flavor}")
            else:
                return {'result': 'failure', 'reason': 'Couldnt find flavor matching requirements'}
        elif flavor not in [f[0] for f in self.list_flavors()]:
            return {'result': 'failure', 'reason': f'Flavor {flavor} not found'}
        compute_client = self.compute_client
        network_client = self.network_client
        if image is None:
            return {'result': 'failure', 'reason': 'An image (or urn) is required'}
        elif image in IMAGES:
            publisher, offer, sku, version = self.__evaluate_image(image)
            if publisher is None:
                return {'result': 'failure', 'reason': 'Only rhel, suse and ubuntu images are supported'}
        elif ':' in image and image.count(':') == 3:
            publisher, offer, sku, version = image.split(':')
        else:
            return {'result': 'failure', 'reason': f'Invalid image {image}'}
        need_agreement = False
        image_product, image_plan = None, None
        try:
            images = compute_client.virtual_machine_images.list(self.location, publisher, offer, sku)
            plan_id = os.path.basename(images[0].id)
            image_info = compute_client.virtual_machine_images.get(self.location, publisher, offer, sku, plan_id)
            if image_info.plan is not None:
                need_agreement = True
                image_product, image_plan = image_info.plan.product, image_info.plan.name
        except Exception as e:
            return {'result': 'failure', 'reason': f'Hit {e}'}
        if need_agreement:
            agreement = self.agreements.marketplace_agreements.get(publisher_id=publisher, offer_id=offer,
                                                                   plan_id=image_plan, offer_type='virtualmachine')
            if not agreement.accepted:
                parameters = {'publisher': publisher, 'product': image_product, 'plan': image_plan,
                              'license_text_link': agreement.license_text_link,
                              'privacy_policy_link': agreement.privacy_policy_link,
                              'marketplace_terms_link': agreement.marketplace_terms_link,
                              'retrieve_datetime': agreement.retrieve_datetime,
                              'signature': agreement.signature, 'accepted': True}
                self.agreements.marketplace_agreements.create(publisher_id=publisher, offer_id=offer,
                                                              plan_id=image_plan, offer_type='virtualmachine',
                                                              parameters=parameters)
        tags = {}
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            tags[entry] = metadata[entry]
        if self.admin_password is not None:
            admin_password = self.admin_password
        else:
            characters = ascii_letters + digits + '#%$+-?|!'
            admin_password = [choice(ascii_letters)] + [choice(digits)] + [choice(characters) for i in range(6)]
            admin_password = ''.join(admin_password).capitalize()
            pprint(f"Using admin_password {admin_password}")
        disk_size = int(disks[0]['size'] if isinstance(disks[0], dict) else disks[0])
        os_disk = {'name': f'{name}-disk-0', 'create_option': 'FromImage', 'delete_option': 'Delete'}
        if disk_size > 30:
            os_disk['disk_size_gb'] = disk_size
        data = {'location': self.location, 'os_profile': {'computer_name': name, 'admin_username': self.admin_user,
                                                          'admin_password': admin_password},
                'tags': tags,
                'hardware_profile': {'vm_size': flavor},
                'diagnostics_profile': {'boot_diagnostics': {'enabled': True, 'storage_uri': None}},
                'storage_profile': {'os_disk': os_disk,
                                    'image_reference': {'publisher': publisher, 'offer': offer, 'sku': sku,
                                                        'version': version}}}
        if need_agreement:
            data['plan'] = {'publisher': publisher, 'name': offer, 'product': sku}
        sg_data = {'id': f"{name}-sg", 'location': self.location}
        sg = network_client.network_security_groups.begin_create_or_update(self.resource_group, f"{name}-sg", sg_data)
        sg = sg.result()
        if 'kubetype' in metadata and metadata['kubetype'] == "openshift":
            for port in [80, 443, 2379, 2380, 4789, 8080, 5443, 6081, 6443, 8443, 22624]:
                rule_data = SecurityRule(protocol='Tcp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description=f'tcp {port}',
                                         source_port_range='*', destination_port_ranges=[f"{port}"],
                                         priority=100, name=f"tcp-{port}")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     f"tcp-{port}", rule_data)
                rule_data = SecurityRule(protocol='Udp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description='udp 4789',
                                         source_port_range='*', destination_port_ranges=["4789"],
                                         priority=100, name="udp-4789")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     "udp-4789", rule_data)
                rule_data = SecurityRule(protocol='Udp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description='udp 6081',
                                         source_port_range='*', destination_port_ranges=["6081"],
                                         priority=100, name="udp-6081")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     "udp-6081", rule_data)
                rule_data = SecurityRule(protocol='Tcp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description='tcp 30000-32767',
                                         source_port_range='*', destination_port_ranges=["30000", "32767"],
                                         priority=100, name="tcp-30000-32767")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     "tcp-30000-32767", rule_data)
                rule_data = SecurityRule(protocol='Ucp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description='udp 30000-32767',
                                         source_port_range='*', destination_port_ranges=["30000", "32767"],
                                         priority=100, name="udp-30000-32767")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     "udp-30000-32767", rule_data)
                rule_data = SecurityRule(protocol='Tcp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description='udp 10250-10259',
                                         source_port_range='*', destination_port_ranges=["10250", "10259"],
                                         priority=100, name="tcp-10250-10259")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     "tcp-10250-10259", rule_data)
                rule_data = SecurityRule(protocol='Tcp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description='tcp 9000-9999',
                                         source_port_range='*', destination_port_ranges=["9000", "9999"],
                                         priority=100, name="tcp-9000-9999")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     "tcp-9000-9999", rule_data)
                rule_data = SecurityRule(protocol='Udp', source_address_prefix='*',
                                         destination_address_prefix='*', access='Allow',
                                         direction='Inbound', description='udp 9000-9999',
                                         source_port_range='*', destination_port_ranges=["9000", "9999"],
                                         priority=100, name="udp-9000-9999")
                network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                     "udp-9000-9999", rule_data)
        network_interfaces = []
        subnets = self.list_subnets()
        for index, net in enumerate(nets):
            nic_name = f'{name}-eth{index}'
            public_ip = None
            if isinstance(net, str):
                netname = net
                netpublic = True
                alias = []
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                alias = net.get('alias', [])
                netpublic = net.get('public', True)
            if netname not in subnets:
                return {'result': 'failure', 'reason': f'Subnet {netname} not found'}
            else:
                subnet_id = subnets[netname]['id']
                nic_data = {'location': self.location,
                            'ip_configurations': [{'name': nic_name, 'subnet': {'id': subnet_id}}]}
                if index == 0:
                    nic_data['network_security_group'] = {"id": sg.id}
                    if netpublic:
                        ip_data = {"location": self.location, "sku": {"name": "Standard"},
                                   "public_ip_allocation_method": "Static", "public_ip_address_version": "IPV4"}
                        ip = network_client.public_ip_addresses.begin_create_or_update(self.resource_group,
                                                                                       f'{name}-ip', ip_data)

                        public_ip = ip.result()
                        rule_data = SecurityRule(protocol='Tcp', source_address_prefix='*',
                                                 destination_address_prefix='*', access='Allow',
                                                 direction='Inbound', description='tcp 22', source_port_range='*',
                                                 destination_port_ranges=["22"], priority=100, name="tcp-22")
                        network_client.security_rules.begin_create_or_update(self.resource_group, f"{name}-sg",
                                                                             "tcp-22", rule_data)
                        nic_data['ip_configurations'][0]['public_ip_address'] = {"id": public_ip.id,
                                                                                 'delete_option': 'Delete'}
                nic = network_client.network_interfaces.begin_create_or_update(self.resource_group, nic_name, nic_data)
                nic_id = nic.result().id
                nic_reference = {'id': nic_id, 'delete_option': 'Delete', 'primary': True if index == 0 else False}
                network_interfaces.append(nic_reference)
        data['network_profile'] = {'network_interfaces': network_interfaces}
        data_disks = []
        for index, disk in enumerate(disks):
            disk_name = f'{name}-disk{index}'
            if index == 0:
                continue
            lun = 10 + index
            if isinstance(disk, int):
                disk_size = disk
            elif isinstance(disk, str) and disk.isdigit():
                disk_size = int(disk)
            elif isinstance(disk, dict):
                disk_size = int(disk.get('size', 10))
            disk_data = {'location': self.location, 'disk_size_gb': disk_size,
                         'creation_data': {'create_option': DiskCreateOption.empty}}
            data_disk = compute_client.disks.begin_create_or_update(self.resource_group, disk_name, disk_data)
            data_disk_id = data_disk.result().id
            new_disk = {'lun': lun, 'name': disk_name, 'create_option': DiskCreateOption.attach,
                        'managed_disk': {'id': data_disk_id}, 'delete_option': 'Delete'}
            data_disks.append(new_disk)
        if data_disks:
            data['storage_profile']['data_disks'] = data_disks
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
            custom_data = b64encode(userdata.encode('utf-8')).decode('latin-1')
            data['os_profile']['custom_data'] = custom_data
        if self.debug:
            print(data)
        result = compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, data)
        result.wait()
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name)
        return {'result': 'success'}

    def start(self, name):
        try:
            result = self.compute_client.virtual_machines.begin_start(self.resource_group, name)
            result.wait()
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

    def stop(self, name, soft=False):
        try:
            if soft:
                result = self.compute_client.virtual_machines.begin_power_off(self.resource_group, name)
            else:
                result = self.compute_client.virtual_machines.begin_deallocate(self.resource_group, name)
            result.wait()
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

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
            result = self.compute_client.virtual_machines.begin_restart(self.resource_group, name)
            result.wait()
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

    def info_host(self):
        return {"location": self.location, 'vms': len(self.list())}

    def status(self, name):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        return os.path.basename(vm.instance_view.statuses[1].code)

    def list(self):
        vms = []
        instances = self.compute_client.virtual_machines.list(self.resource_group)
        for vm in instances:
            try:
                vms.append(self.info(os.path.basename(vm.id)))
            except:
                continue
        if not vms:
            return []
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        self.serialconsole(name, web=web)

    def serialconsole(self, name, web=False):
        if self.mail is None:
            error("Serial console requires to set mail in your configuration")
            return
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name)
        except:
            error(f"VM {name} not found")
            return
        if vm.diagnostics_profile is None or not vm.diagnostics_profile.boot_diagnostics.enabled:
            pprint(f"Enabling Boot diagnostics for VM {name} ")
            vm.diagnostics_profile = {'boot_diagnostics': {'enabled': True, 'storage_uri': None}}
            result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
            result.wait()
        user = f"{self.mail.split('@')[0]}{''.join(self.mail.split('@')[1].split('.')[:-1])}.onmicrosoft."
        user += self.mail.split('@')[1].split('.')[-1]
        url = f"https://portal.azure.com/?quickstart=true#@{user}/"
        url += f"resource/subscriptions/{self.subscription_id}/resourceGroups/kcli/providers/"
        url += f"Microsoft.Compute/virtualMachines/{name}/serialConsole"
        if web:
            return url
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = f"Open the following url:\n{url}" if os.path.exists("/i_am_a_container") else url
            pprint(msg)
        else:
            pprint(f"Opening url {url}")
            webbrowser.open(url, new=2, autoraise=True)

    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        compute_client = self.compute_client
        network_client = self.network_client
        yamlinfo = {}
        try:
            vm = compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {}
        yamlinfo['name'] = vm.name
        yamlinfo['status'] = os.path.basename(vm.instance_view.statuses[1].code)
        yamlinfo['id'] = vm.vm_id
        hardware_profile = vm.hardware_profile
        flavor = hardware_profile.vm_size
        yamlinfo['flavor'] = flavor
        yamlinfo['numcpus'], yamlinfo['memory'] = [f for f in self.list_flavors() if f[0] == flavor][0][1:]
        ips = []
        nets = []
        for index, nic in enumerate(vm.network_profile.network_interfaces):
            device = os.path.basename(nic.id)
            nic_data = network_client.network_interfaces.get(self.resource_group, device)
            if self.debug:
                print(nic_data)
            mac = nic_data.mac_address
            private_ip = nic_data.ip_configurations[0].private_ip_address
            ips.append(private_ip)
            public_address = nic_data.ip_configurations[0].public_ip_address
            if public_address is not None:
                public_address = network_client.public_ip_addresses.get(self.resource_group,
                                                                        os.path.basename(public_address.id)).ip_address
            if index == 0:
                yamlinfo['ip'] = public_address or private_ip
            subnet_name = os.path.basename(nic_data.ip_configurations[0].subnet.id)
            nets.append({'device': device, 'mac': mac, 'net': subnet_name, 'type': private_ip})
        yamlinfo['nets'] = nets
        if len(ips) > 1:
            yamlinfo['ips'] = ips
        tags = vm.tags
        if 'plan' in tags:
            yamlinfo['plan'] = tags['plan']
        if 'profile' in tags:
            yamlinfo['profile'] = tags['profile']
        storage_profile = vm.storage_profile
        image_reference = storage_profile.image_reference
        yamlinfo['image'] = f"{image_reference.offer}-{image_reference.sku}-{image_reference.version}"
        disks = []
        for index, disk in enumerate([storage_profile.os_disk] + storage_profile.data_disks):
            device, disksize, diskformat = f'disk{index}', disk.disk_size_gb, disk.caching
            drivertype, path = 'N/A', disk.name
            disks.append({'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        yamlinfo['disks'] = disks
        yamlinfo['creationdate'] = vm.time_created
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def ip(self, name):
        network_client = self.network_client
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        device = os.path.basename(vm.network_profile.network_interfaces[0].id)
        nic_data = network_client.network_interfaces.get(self.resource_group, device)
        private_ip = nic_data.ip_configurations[0].private_ip_address
        public_address = nic_data.ip_configurations[0].public_ip_address
        if public_address is not None:
            public_address = network_client.public_ip_addresses.get(self.resource_group,
                                                                    os.path.basename(public_address.id)).ip_address
        return public_address or private_ip

    def volumes(self, iso=False):
        if iso:
            return []
        else:
            return sorted(URNS)

    def delete(self, name, snapshots=False):
        compute_client = self.compute_client
        network_client = self.network_client
        try:
            vm = compute_client.virtual_machines.get(self.resource_group, name)
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        tags = vm.tags
        dnsclient, domain = tags.get('dnsclient'), tags.get('domain')
        result = compute_client.virtual_machines.begin_delete(self.resource_group, name, force_deletion=True)
        result.wait()
        try:
            network_client.network_security_groups.begin_delete(self.resource_group, f"{name}-sg")
        except:
            pass
        if domain is not None and dnsclient is None:
            self.delete_dns(name, domain, name)
        return {'result': 'success'}

    def dnsinfo(self, name):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name)
        except:
            return None, None
        tags = vm.tags
        dnsclient, domain = tags.get('dnsclient'), tags.get('domain')
        return dnsclient, domain

    def clone(self, old, new, full=False, start=False):
        print("not implemented")

    def update_metadata(self, name, metatype, metavalue, append=False):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name)
        except:
            error(f"VM {name} not found")
            return 1
        if vm.tags is None:
            vm.tags = {metatype: metavalue}
        else:
            vm.tags[metatype] = metavalue
        result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
        result.wait()

    def update_memory(self, name, memory):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        current_numcpus, current_memory = [f for f in self.list_flavors() if f[0] == vm.hardware_profile.vm_size][0][1:]
        if memory > current_memory:
            matching = [f for f in self.list_flavors() if f[2] >= memory]
            if matching:
                flavor = matching[0][0]
                pprint(f"Using flavor {flavor}")
            else:
                return {'result': 'failure', 'reason': 'Couldnt find flavor matching requirements'}
            if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
                error(f"Can't update memory of VM {name} while up")
                return {'result': 'failure', 'reason': f"VM {name} up"}
            vm.hardware_profile.vm_size = flavor
            result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
            result.wait()

    def update_cpus(self, name, numcpus):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        current_numcpus, current_memory = [f for f in self.list_flavors() if f[0] == vm.hardware_profile.vm_size][0][1:]
        if numcpus > current_numcpus:
            matching = [f for f in self.list_flavors() if f[1] >= numcpus]
            if matching:
                flavor = matching[0][0]
                pprint(f"Using flavor {flavor}")
            else:
                return {'result': 'failure', 'reason': 'Couldnt find flavor matching requirements'}
            if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
                error(f"Can't update cpus of VM {name} while up")
                return {'result': 'failure', 'reason': f"VM {name} up"}
            vm.hardware_profile.vm_size = flavor
            result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
            result.wait()

    def update_start(self, name, start=True):
        print("not implemented")

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)

    def update_iso(self, name, iso):
        print("not implemented")

    def update_flavor(self, name, flavor):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if flavor not in [f[0] for f in self.list_flavors()]:
            return {'result': 'failure', 'reason': f'Flavor {flavor} not found'}
        if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
            error(f"Can't update flavor of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        vm.hardware_profile.vm_size = flavor
        result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
        result.wait()

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        data = {'location': self.location, 'disk_size_gb': size,
                'creation_data': {'create_option': DiskCreateOption.empty}}
        self.compute_client.disks.begin_create_or_update(self.resource_group, name, data)

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        if novm:
            return self.create_disk(name=name, size=size, pool=pool, thin=thin, image=image)
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
            error(f"Can't add disk to VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        index = len(vm.storage_profile.data_disks) + 1
        disk_name = f"{name}-disk{index}"
        disk_data = {'location': self.location, 'disk_size_gb': size,
                     'creation_data': {'create_option': DiskCreateOption.empty}}
        data_disk = self.compute_client.disks.begin_create_or_update(self.resource_group, disk_name, disk_data)
        data_disk_id = data_disk.result().id
        lun = 10 + index
        new_disk = {'lun': lun, 'name': disk_name, 'create_option': DiskCreateOption.attach,
                    'managed_disk': {'id': data_disk_id}, 'delete_option': 'Delete'}
        vm.storage_profile.data_disks.append(new_disk)
        result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
        result.wait()

    def delete_disk(self, name, diskname, pool=None, novm=False):
        if novm:
            result = self.compute_client.disks.begin_delete(self.resource_group, diskname)
            result.wait()
            return {'result': 'success'}
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
            error(f"Can't delete disk from VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        disks = []
        for disk in vm.storage_profile.data_disks:
            if os.path.basename(disk.name).endswith(diskname):
                disk_name = os.path.basename(disk.name)
            else:
                disks.append(disk)
        if disks != vm.storage_profile.data_disks:
            vm.storage_profile.data_disks = disks
            result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
            result.wait()
            result = self.compute_client.disks.begin_delete(self.resource_group, disk_name)
            result.wait()

    def list_disks(self):
        disks = {}
        for disk in self.compute_client.disks.list():
            disks[disk.name] = {'pool': 'default', 'path': disk.name}
        return disks

    def add_nic(self, name, network, model='virtio'):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
            error(f"Can't add nic to VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        subnets = self.list_subnets()
        if network not in subnets:
            return {'result': 'failure', 'reason': f'Subnet {network} not found'}
        else:
            subnet_id = subnets[network]['az']
        index = len(vm.network_profile.network_interfaces)
        nic_name = f'{name}-eth{index}'
        nic_data = {'location': self.location, 'ip_configurations': [{'name': nic_name, 'subnet': {'id': subnet_id}}]}
        nic = self.network_client.network_interfaces.begin_create_or_update(self.resource_group, nic_name, nic_data)
        nic_id = nic.result().id
        nic_reference = {'id': nic_id, 'delete_option': 'Delete', 'primary': False}
        vm.network_profile.network_interfaces.append(nic_reference)
        result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
        result.wait()

    def delete_nic(self, name, interface):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
            error(f"Can't delete nic from VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        interfaces = []
        for nic in vm.network_profile.network_interfaces:
            if os.path.basename(nic.id).endswith(interface):
                nic_name = os.path.basename(nic.id)
            else:
                interfaces.append(nic)
        if interfaces != vm.network_profile.network_interfaces:
            vm.network_profile.network_interfaces = interfaces
            result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
            result.wait()
            result = self.network_client.network_interfaces.begin_delete(self.resource_group, nic_name)
            result.wait()

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        print("not implemented")

    def delete_image(self, image, pool=None):
        return {'result': 'success'}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        if cidr is not None:
            try:
                ip_network(cidr, strict=False)
            except:
                return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
        else:
            return {'result': 'failure', 'reason': "Cidr needed"}
        data = {'location': self.location, 'address_space': {'address_prefixes': [cidr]}, 'tags': {'plan': plan}}
        result = self.network_client.virtual_networks.begin_create_or_update(self.resource_group, name, data)
        result.wait()
        if overrides.get('create_subnet', True):
            subnet = name
            self.network_client.subnets.begin_create_or_update(self.resource_group, name,
                                                               subnet, {'address_prefix': cidr})
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        result = self.network_client.virtual_networks.begin_delete(self.resource_group, name)
        result.wait()
        return {'result': 'success'}

    def list_pools(self):
        return []

    def list_networks(self):
        resource_group = self.resource_group
        networks = {}
        network_client = self.network_client
        for network in network_client.virtual_networks.list(resource_group):
            networkname = network.name
            cidr = network_client.virtual_networks.get(resource_group, networkname).address_space.address_prefixes[0]
            dhcp = True
            domain = network.resource_guid
            mode = ''
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domain, 'type': 'routed', 'mode': mode}
            plan = network.tags['plan'] if network.tags is not None and 'plan' in network.tags else 'N/A'
            networks[networkname]['plan'] = plan
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        if self.debug and networkinfo:
            print(self.network_client.virtual_networks.get(self.resource_group, name))
        return networkinfo

    def info_subnet(self, name):
        subnets = self.list_subnets()
        if name in subnets:
            return subnets[name]
        else:
            msg = f"Subnet {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}

    def list_subnets(self):
        subnets = {}
        network_client = self.network_client
        for network in network_client.virtual_networks.list(self.resource_group):
            for subnet in network_client.subnets.list(self.resource_group, network.name):
                if self.debug:
                    print(subnet)
                address_prefixes = subnet.address_prefixes or [None]
                cidr = subnet.address_prefix or address_prefixes[0]
                subnet_id = subnet.id
                subnets[subnet.name] = {'cidr': cidr, 'id': subnet_id, 'network': network.name}
        return subnets

    def delete_pool(self, name, full=False):
        print("not implemented")

    def network_ports(self, name):
        print("not implemented")

    def vm_ports(self, name):
        return ['default']

    def get_pool_path(self, pool):
        print("not implemented")

    def list_flavors(self):
        vm_sizes = self.compute_client.virtual_machine_sizes.list(self.location)
        return [[e.name, e.number_of_cores, e.memory_in_mb] for e in vm_sizes]

    def export(self, name, image=None):
        print("not implemented")

    def create_bucket(self, bucket, public=False):
        if bucket in self.list_buckets():
            error(f"Bucket {bucket} already there")
            return
        public_access = 'container' if public else None
        self.blob_service_client.create_container(bucket, public_access=public_access)

    def delete_bucket(self, bucket):
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return
        self.blob_service_client.delete_container(bucket)

    def delete_from_bucket(self, bucket, path):
        if bucket not in self.list_buckets():
            error(f"Bucket {bucket} doesn't exist")
            return
        container_client = self.blob_service_client.get_container_client(bucket)
        if not os.path.basename(path) in container_client.list_blob_names():
            error(f"Bucket file {path} not found in Bucket {bucket}")
            return
        else:
            container_client.delete_blob(os.path.basename(path))

    def download_from_bucket(self, bucket, path):
        if bucket not in self.list_buckets():
            error(f"Bucket {bucket} doesn't exist")
            return
        container_client = self.blob_service_client.get_container_client(bucket)
        with open(path, mode="wb") as download_file:
            blob_name = os.path.basename(path)
            download_file.write(container_client.download_blob(blob_name).readall())

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        file_path = os.path.expanduser(path)
        file_name = os.path.basename(path)
        if bucket not in self.list_buckets():
            error(f"Bucket {bucket} doesn't exist")
            return
        if path.startswith('http'):
            response = urlopen(path)
            file_path = file_name
            with open(file_name, 'wb') as f:
                f.write(response.read())
        if not os.path.exists(file_path):
            error(f"Path {path} doesn't exist")
            return
        else:
            blob_client = self.blob_service_client.get_blob_client(bucket, file_name)
            with open(file=file_path, mode="rb") as data:
                blob_client.upload_blob(data)

    def list_buckets(self):
        return [bucket.name for bucket in self.blob_service_client.list_containers()]

    def list_bucketfiles(self, bucket):
        container_client = self.blob_service_client.get_container_client(bucket)
        return [blob.name for blob in container_client.list_blobs()]

    def public_bucketfile_url(self, bucket, path):
        return f"https://{self.storageaccount}.blob.core.windows.net/{bucket}/{path}"

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None):
        dns_client = self.dns_client
        if domain is None:
            domain = nets[0]
        internalip = None
        pprint(f"Using domain {domain}")
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        if domain not in [os.path.basename(z.id) for z in dns_client.zones.list()]:
            error(f"Domain {domain} not found")
            return {'result': 'failure', 'reason': f"Domain {domain} not found"}
        entry = name if cluster is None else f"{name}.{cluster}"
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
                    ip = self.ip(instanceid)
                    if ip is None:
                        sleep(5)
                        pprint("Waiting 5 seconds to grab ip and create DNS record...")
                        counter += 10
                    else:
                        break
        if ip is None:
            error(f"Couldn't assign DNS for {name}")
            return
        dnsip = ip if internalip is None else internalip
        dns_data = {"ttl": 300, "arecords": [{"ipv4_address": dnsip}]}
        dns_client.record_sets.create_or_update(self.resource_group, domain, entry, 'A', dns_data)
        for a in alias:
            if a == '*':
                if cluster is not None and ('ctlplane' in name or 'worker' in name):
                    alias_entry = f'*.apps.{cluster}'
                else:
                    alias_entry = f'*.{name}'
            else:
                alias_entry = a
            dns_data = {"ttl": 300, "cname_Record": {'cname': f"{entry}.{domain}"}}
            dns_client.record_sets.create_or_update(self.resource_group, domain, alias_entry, 'CNAME', dns_data)
        return {'result': 'success'}

    def delete_dns(self, name, domain, allentries=False):
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        if domain not in [os.path.basename(z.id) for z in self.dns_client.zones.list()]:
            error(f"Domain {domain} not found")
            return {'result': 'failure', 'reason': f"Domain {domain} not found"}
        entry = name if cluster is None else f"{name}.{cluster}"
        # clusterdomain = f"{cluster}.{domain}"
        found = False
        for record in self.dns_client.record_sets.list_all_by_dns_zone(self.resource_group, domain):
            # if entry in record.name or ('ctlplane-0' in name and record.name.endswith(f"{clusterdomain}.")):
            if entry in record.name:
                found = True
                _type = os.path.basename(record.type)
                self.dns_client.record_sets.delete(self.resource_group, domain, record.name, _type)
        if not found:
            error(f"Entry {entry} not found")
            return {'result': 'failure', 'reason': f"Entry {entry} not found"}
        else:
            return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        if domain not in [os.path.basename(d.id) for d in self.dns_client.zones.list()]:
            error(f"Domain {domain} not found")
            return results
        for entry in self.dns_client.record_sets.list_all_by_dns_zone(self.resource_group, domain):
            name, _type, ttl = entry.name, os.path.basename(entry.type), entry.ttl
            data = ''
            if entry.a_records is not None:
                data = ' '.join([x.ipv4_address for x in entry.a_records])
            elif entry.aaaa_records is not None:
                data = ' '.join([x.ipv6_address for x in entry.aaaa_records])
            elif entry.soa_record is not None:
                data = entry.soa_record.host
            elif entry.ns_records is not None:
                data = ' '.join([x.nsdname for x in entry.ns_records])
            elif entry.cname_record is not None:
                data = entry.cname_record.cname
            elif entry.mx_records is not None:
                data = ' '.join([x.exchange for x in entry.mx_records])
            elif entry.ptr_records is not None:
                data = ' '.join([x.ptrdname for x in entry.ptr_records])
            elif entry.srv_records is not None:
                data = ' '.join([f"{x.priority} {x.weight} {x.port} {x.target}" for x in entry.srv_records])
            elif entry.txt_records is not None:
                data = ' '.join([x.value for x in entry.txt_records])
            elif entry.caa_records is not None:
                data = ' '.join([f"{x.flag} {x.tag} {x.value}" for x in entry.caa_records])
            results.append([name, _type, ttl, data])
        return results

    def update_nic(self, name, index, network):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name, expand='instanceView')
        except:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        subnets = self.list_subnets()
        if network not in subnets:
            msg = f"Subnet {network} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        if len(vm.network_profile.network_interfaces) < index:
            msg = f"Nic {index} not found in VM {name}"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        if os.path.basename(vm.instance_view.statuses[1].code) == 'running':
            error(f"Can't update memory of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        vm.network_profile.network_interfaces.ip_configurations[index].subnet.id = subnets[network]['az']
        result = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, name, vm)
        result.wait()
        return {'result': 'success'}

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        return self.create_network(name, overrides=overrides)

    def list_security_groups(self, network=None):
        sgs = []
        network_client = self.network_client
        for sg in network_client.network_security_groups.list(self.resource_group):
            sgs.append(sg.name)
        return sgs

    def create_security_group(self, name, overrides={}):
        ports = overrides.get('ports', [])
        network_client = self.network_client
        sg_data = {'id': name, 'location': self.location}
        sg = network_client.network_security_groups.begin_create_or_update(self.resource_group, name, sg_data)
        sg = sg.result()
        for index, port in enumerate(ports):
            if isinstance(port, str) or isinstance(port, int):
                protocol = 'Tcp'
                destport = int(port)
            elif isinstance(port, dict):
                protocol = port.get('protocol', 'tcp').capitalize()
                destport = port.get('to')
                if destport is None:
                    warning(f"Missing to in {ports}. Skipping")
                    continue
            pprint(f"Adding rule to {protocol}/{destport} in sg {name}")
            priority = 100 + index
            rule_data = SecurityRule(protocol=protocol, source_address_prefix='*',
                                     destination_address_prefix='*', access='Allow',
                                     direction='Inbound', description=f'port {destport}', source_port_range='*',
                                     destination_port_ranges=[destport], priority=priority, name=f"port-{destport}")
            network_client.security_rules.begin_create_or_update(self.resource_group, name, f"port-{destport}",
                                                                 rule_data)
        return {'result': 'success'}

    def delete_security_group(self, name):
        self.network_client.network_security_groups.begin_delete(self.resource_group, name)
        return {'result': 'success'}

    def __evaluate_image(self, image):
        if image.startswith('rhel'):
            return 'RedHat', 'RHEL', '9_2', 'latest'
        elif image.startswith('rhcos'):
            return 'redhat-limited', 'rh-ocp-worker', 'rh-ocp-worker', 'latest'
        elif 'suse' in image:
            return 'SUSE', 'openSUSE-leap-15-4', 'gen2', 'latest'
        elif image.startswith('ubuntu'):
            return 'Canonical', '0001-com-ubuntu-server-jammy', '22_04-lts-gen2', 'latest'
        else:
            return None, None, None, None

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False, dnsclient=None, ip=None):
        # if not vms:
        #    msg = "Creating a load balancer requires to specify some vms"
        #    error(msg)
        #    return {'result': 'failure', 'reason': msg}
        ports = [int(port) for port in ports]
        network_client = self.network_client
        ip_data = {"location": self.location, "sku": {"name": "Standard"},
                   "public_ip_allocation_method": "Static", "public_ip_address_version": "IPV4"}
        public_ip = network_client.public_ip_addresses.begin_create_or_update(self.resource_group, f'{name}-ip',
                                                                              ip_data)
        public_ip = public_ip.result()
        frontend_ip_configurations = [{'name': name, 'public_ip_address': {'id': public_ip.id}}]
        backend_address_pools = [{'name': name}]
        probes = [{'name': name, 'protocol': 'tcp', 'port': checkport, 'interval_in_seconds': 15,
                   'number_of_probes': 4}]
        lb_data = {'location': self.location,
                   'sku': {'name': 'Standard'},
                   'frontend_ip_configurations': frontend_ip_configurations,
                   'backend_address_pools': backend_address_pools,
                   'probes': probes}
        lb = network_client.load_balancers.begin_create_or_update(self.resource_group, name, lb_data).result()
        frontend_id = lb.frontend_ip_configurations[0].id
        backend_id = lb.backend_address_pools[0].id
        inbound_nat_rules = [{'name': f"{name}-rule{index}", 'protocol': 'tcp',
                              'backend_address_pool': {'id': backend_id}, 'backend_port': port,
                              'frontend_port_range_start': port, 'frontend_port_range_end': port + 500,
                              'enable_floating_ip': False, 'idle_timeout_in_minutes': 4,
                              'frontend_ip_configuration': {'id': frontend_id}} for index, port in enumerate(ports)]
        lb.inbound_nat_rules = inbound_nat_rules
        lb = network_client.load_balancers.begin_create_or_update(self.resource_group, name, lb).result()
        if self.debug:
            print(lb)
        for index, vm in enumerate(vms):
            self.set_loadbalancer(vm, backend_id, ports)
            self.update_metadata(vm, 'loadbalancer', name)
        if domain is not None:
            ip = lb.frontend_ip_configurations[0].public_ip_address
            self.reserve_dns(name, ip=ip, domain=domain, alias=alias)
        return {'result': 'success'}

    def delete_loadbalancer(self, name):
        network_client = self.network_client
        for lb in network_client.load_balancers.list(self.resource_group):
            if lb.name == name:
                public_address = lb.frontend_ip_configurations[0].public_ip_address
                result = network_client.load_balancers.begin_delete(self.resource_group, name)
                result.wait()
                result = network_client.public_ip_addresses.begin_delete(self.resource_group,
                                                                         os.path.basename(public_address.id))
                result.wait()
                return {'result': 'success'}
        error(f"Loadbalancer {name} not found")
        return {'result': 'success'}

    def list_loadbalancers(self):
        network_client = self.network_client
        results = []
        for lb in network_client.load_balancers.list(self.resource_group):
            public_address = lb.frontend_ip_configurations[0].public_ip_address
            ip = network_client.public_ip_addresses.get(self.resource_group,
                                                        os.path.basename(public_address.id)).ip_address
            protocol, ports, target = 'N/A', 'N/A', 'N/A'
            rule = lb.inbound_nat_rules[0] if lb.inbound_nat_rules else lb.load_balancing_rules[0]
            protocol = rule.protocol
            ports = rule.frontend_port_range_start if lb.inbound_nat_rules else rule.frontend_port
            results.append([lb.name, ip, protocol, ports, target])
        return results

    def set_loadbalancer(self, name, backend_id, ports):
        try:
            vm = self.compute_client.virtual_machines.get(self.resource_group, name)
        except:
            error("VM {name} not found")
            return {'result': 'success'}
        device = os.path.basename(vm.network_profile.network_interfaces[0].id)
        nic_data = self.network_client.network_interfaces.get(self.resource_group, device)
        nic_data.ip_configurations[0].load_balancer_backend_address_pools = [{'id': backend_id}]
        result = self.network_client.network_interfaces.begin_create_or_update(self.resource_group, device, nic_data)
        result.wait()
        ports = [22] + ports
        self.create_security_group(f'{name}-sg', overrides={'ports': ports})
        return {'result': 'success'}

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        try:
            ip_network(cidr, strict=False)
        except:
            return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
        data = {'address_prefix': cidr, 'tags': {'plan': plan}}
        network = overrides.get('network', name)
        if network not in self.list_networks():
            msg = f'Network {network} not found'
            return {'result': 'failure', 'reason': msg}
        self.network_client.subnets.begin_create_or_update(self.resource_group, network, name, data)
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        subnets = self.list_subnets()
        if name not in subnets:
            msg = f'Subnet {name} not found'
            return {'result': 'failure', 'reason': msg}
        else:
            network = os.path.basename(subnets[name]['network'])
        result = self.network_client.subnets.begin_delete(self.resource_group, network, name)
        result.wait()
        return {'result': 'success'}

    def list_dns_zones(self):
        return [os.path.basename(z.id) for z in self.dns_client.zones.list()]
