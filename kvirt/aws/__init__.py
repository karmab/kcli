#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Aws Provider Class
"""

from datetime import datetime
from kvirt import common
import boto3
from netaddr import IPNetwork
import os
from string import ascii_lowercase
from time import sleep

static_flavors = {'t2.nano': {'cpus': 1, 'memory': 512}, 't2.micro': {'cpus': 1, 'memory': 1024},
                  't2.small': {'cpus': 1, 'memory': 2048}, 't2.medium': {'cpus': 2, 'memory': 4096},
                  't2.large': {'cpus': 2, 'memory': 8144}, 't2.xlarge': {'cpus': 2, 'memory': 16384},
                  'm5.large': {'cpus': 2, 'memory': 8144}, 'm5.xlarge': {'cpus': 4, 'memory': 16384},
                  'm5.2xlarge': {'cpus': 8, 'memory': 32768}, 'm5.4xlarge': {'cpus': 16, 'memory': 65536}
                  }


class Kaws(object):
    """

    """
    def __init__(self, access_key_id=None, access_key_secret=None, debug=False,
                 region='eu-west-3', keypair=None):
        self.debug = debug
        self.conn = boto3.client('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                 region_name=region)
        self.resource = boto3.resource('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                       region_name=region)
        self.dns = boto3.client('route53', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                region_name=region)
        self.elb = boto3.client('elb', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                region_name=region)
        self.region = region
        self.keypair = keypair
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
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
            return True
        except:
            return False

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        try:
            conn.describe_subnets(SubnetIds=[name])
            return True
        except:
            return False

    def disk_exists(self, pool, name):
        """

        :param pool:
        :param name:
        """
        print("not implemented")

    def create(self, name, virttype='kvm', profile='', flavor=None, plan='kvirt', cpumodel='Westmere', cpuflags=[],
               numcpus=2, memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}],
               disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[],
               ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[],
               enableroot=True, alias=[], overrides={}, tags=None, dnsclient=None, storemetadata=False):
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
        template = self.__evaluate_template(template)
        keypair = self.keypair
        if template is not None and not template.startswith('ami-'):
                return {'result': 'failure', 'reason': 'Invalid template %s' % template}
        defaultsubnetid = None
        if flavor is None:
            matchingflavors = [f for f in static_flavors if static_flavors[f]['cpus'] >= numcpus and
                               static_flavors[f]['memory'] >= memory]
            if matchingflavors:
                flavor = matchingflavors[0]
                common.pprint("Using instance type %s" % flavor)
            else:
                return {'result': 'failure', 'reason': 'Couldnt find instance type matching requirements'}
        conn = self.conn
        tags = [{'ResourceType': 'instance',
                 'Tags': [{'Key': 'Name', 'Value': name}, {'Key': 'plan', 'Value': plan},
                          {'Key': 'hostname', 'Value': name}, {'Key': 'profile', 'Value': profile}]}]
        if keypair is None:
            keypair = 'kvirt_%s' % self.access_key_id
        keypairs = [k for k in conn.describe_key_pairs()['KeyPairs'] if k['KeyName'] == keypair]
        if not keypairs:
            common.pprint("Importing your public key as %s" % keypair)
            if not os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME'])\
                    and not os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME'])\
                    and not os.path.exists("%s/.kcli/id_rsa.pub" % os.environ['HOME'])\
                    and not os.path.exists("%s/.kcli/id_dsa.pub" % os.environ['HOME']):
                common.pprint("No public key found. Leaving", color='red')
                return {'result': 'failure', 'reason': 'No public key found'}
            elif os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
                homekey = open("%s/.ssh/id_rsa.pub" % os.environ['HOME']).read()
            elif os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
                homekey = open("%s/.ssh/id_dsa.pub" % os.environ['HOME']).read()
            elif os.path.exists("%s/.kcli/id_rsa.pub" % os.environ['HOME']):
                homekey = open("%s/.kcli/id_rsa.pub" % os.environ['HOME']).read()
            else:
                homekey = open("%s/.kcli/id_dsa.pub" % os.environ['HOME']).read()
            conn.import_key_pair(KeyName=keypair, PublicKeyMaterial=homekey)
        if cloudinit:
            if template is not None and (template.startswith('coreos') or template.startswith('rhcos')):
                etcd = None
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                           overrides=overrides, etcd=etcd)
            else:
                common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain,
                                 reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides,
                                 iso=False, fqdn=True, storemetadata=storemetadata)
                userdata = open('/tmp/user-data', 'r').read()
        else:
            userdata = ''
        networkinterfaces = []
        blockdevicemappings = []
        privateips = []
        for index, net in enumerate(nets):
            networkinterface = {'DeleteOnTermination': True, 'Description': "eth%s" % index, 'DeviceIndex': index,
                                'Groups': ['string'], 'SubnetId': 'string'}
            ip = None
            if isinstance(net, str):
                netname = net
                netpublic = True
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                ip = net.get('ip')
                alias = net.get('alias')
                netpublic = net.get('public', True)
            networkinterface['AssociatePublicIpAddress'] = netpublic if index == 0 else False
            if netname == 'default':
                if defaultsubnetid is not None:
                    netname = defaultsubnetid
                else:
                    # Filters = [{'Name': 'isDefault', 'Values': ['True']}]
                    # vpcs = conn.describe_vpcs(Filters=Filters)
                    vpcs = conn.describe_vpcs()
                    vpcid = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']][0]
                    # Filters = [{'Name': 'vpc-id', 'Values': [vpcid]}, {'Name': 'default-for-az', 'Values': ['True']}]
                    subnets = conn.describe_subnets()
                    subnetid = [subnet['SubnetId'] for subnet in subnets['Subnets']
                                if subnet['DefaultForAz'] and subnet['VpcId'] == vpcid][0]
                    netname = subnetid
                    defaultsubnetid = netname
                    common.pprint("Using subnet %s as default" % defaultsubnetid)
            if ips and len(ips) > index and ips[index] is not None:
                ip = ips[index]
                if index == 0:
                    networkinterface['PrivateIpAddress'] = ip
                    privateip = {'Primary': True, 'PrivateIpAddress': ip}
                else:
                    privateip = {'Primary': False, 'PrivateIpAddress': ip}
                privateips = privateips.append(privateip)
            networkinterface['SubnetId'] = netname
            networkinterfaces.append(networkinterface)
        if len(privateips) > 1:
            networkinterface['PrivateIpAddresses'] = privateips
        for index, disk in enumerate(disks):
            letter = chr(index + ord('a'))
            devicename = '/dev/sd%s1' % letter if index == 0 else '/dev/sd%s' % letter
            blockdevicemapping = {'DeviceName': devicename, 'Ebs': {'DeleteOnTermination': True,
                                                                    'VolumeType': 'standard'}}
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str) and disk.isdigit():
                disksize = str(disk)
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
                blockdevicemapping['Ebs']['VolumeType'] = disk.get('type', 'standard')
            blockdevicemapping['Ebs']['VolumeSize'] = disksize
            blockdevicemappings.append(blockdevicemapping)
        if reservedns and domain is not None:
            tags[0]['Tags'].append({'Key': 'domain', 'Value': domain})
        if dnsclient is not None:
            tags[0]['Tags'].append({'Key': 'dnsclient', 'Value': dnsclient})
        conn.run_instances(ImageId=template, MinCount=1, MaxCount=1, InstanceType=flavor,
                           KeyName=keypair, BlockDeviceMappings=blockdevicemappings,
                           UserData=userdata, TagSpecifications=tags)
        common.pprint("%s created on aws" % name)
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name)
        return {'result': 'success'}

    def start(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        conn.start_instances(InstanceIds=[instanceid])
        return {'result': 'success'}

    def stop(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        conn.stop_instances(InstanceIds=[instanceid])
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
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        conn.start_instances(InstanceIds=[instanceid])
        return {'result': 'success'}

    def report(self):
        """

        :return:
        """
        print("Region: %s" % self.region)
        return

    def status(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        status = vm['State']['Name']
        return status

    def list(self):
        """

        :return:
        """
        conn = self.conn
        vms = []
        results = conn.describe_instances()
        reservations = results['Reservations']
        for reservation in reservations:
            vm = reservation['Instances'][0]
            name = vm['InstanceId']
            vms.append(self.info(name))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False):
        """

        :param name:
        :param tunnel:
        :return:
        """
        print("not implemented")
        return

    def serialconsole(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        response = conn.get_console_output(InstanceId=instanceid, DryRun=False, Latest=False)
        print(response['Output'])
        return

    def dnsinfo(self, name):
        """

        :param name:
        :param output:
        :param fields:
        :param values:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return None, None
        dnsclient, domain = None, None
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == 'dnsclient':
                    dnsclient = tag['Value']
                if tag['Key'] == 'domain':
                    domain = tag['Value']
        return dnsclient, domain

    def get_id(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        try:
            if name.startswith('i-'):
                vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
            else:
                Filters = {'Name': "tag:Name", 'Values': [name]}
                vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return None
        return vm['InstanceId']

    def get_security_groups(self, name):
        """

        :param name:
        :return:
        """
        conn = self.conn
        try:
            if name.startswith('i-'):
                vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
            else:
                Filters = {'Name': "tag:Name", 'Values': [name]}
                vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return None
        return vm['SecurityGroups']

    def info(self, name, vm=None):
        """

        :param name:
        :param vm:
        :return:
        """
        yamlinfo = {}
        conn = self.conn
        resource = self.resource
        if vm is None:
            try:
                if name.startswith('i-'):
                    vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
                else:
                    Filters = {'Name': "tag:Name", 'Values': [name]}
                    vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
            except:
                common.pprint("VM %s not found" % name, color='red')
                return {}
        if self.debug:
            print(vm)
        instanceid = vm['InstanceId']
        name = instanceid
        state = vm['State']['Name']
        ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else ''
        amid = vm['ImageId']
        az = vm['Placement']['AvailabilityZone']
        image = resource.Image(amid)
        source = os.path.basename(image.image_location)
        plan = ''
        profile = ''
        loadbalancer = None
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == 'plan':
                    plan = tag['Value']
                if tag['Key'] == 'profile':
                    profile = tag['Value']
                if tag['Key'] == 'Name':
                    name = tag['Value']
                if tag['Key'] == 'loadbalancer':
                    loadbalancer = tag['Value']
        if loadbalancer is not None:
            yamlinfo['loadbalancer'] = loadbalancer
        yamlinfo['name'] = name
        yamlinfo['status'] = state
        yamlinfo['az'] = az
        yamlinfo['ip'] = ip
        machinetype = vm['InstanceType']
        yamlinfo['flavor'] = machinetype
        if machinetype in static_flavors:
            yamlinfo['cpus'] = static_flavors[machinetype]['cpus']
            yamlinfo['memory'] = static_flavors[machinetype]['memory']
        # yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        yamlinfo['template'] = source
        # yamlinfo['creationdate'] = dateparser.parse(vm['creationTimestamp']).strftime("%d-%m-%Y %H:%M")
        yamlinfo['plan'] = plan
        yamlinfo['profile'] = profile
        yamlinfo['instanceid'] = instanceid
        nets = []
        for interface in vm['NetworkInterfaces']:
            network = interface['VpcId']
            device = interface['NetworkInterfaceId']
            mac = interface['MacAddress']
            network_type = interface['PrivateIpAddresses'][0]['PrivateIpAddress']
            nets.append({'device': device, 'mac': mac, 'net': network, 'type': network_type})
        if nets:
            yamlinfo['nets'] = nets
        disks = []
        for index, disk in enumerate(vm['BlockDeviceMappings']):
            devname = disk['DeviceName']
            volumeid = disk['Ebs']['VolumeId']
            volume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
            disksize = volume['Size']
            diskformat = volume['AvailabilityZone']
            drivertype = volume['VolumeType']
            path = volumeid
            disks.append({'device': devname, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        if disks:
            yamlinfo['disks'] = disks
        return yamlinfo

    def ip(self, name):
        """

        :param name:
        :return:
        """
        ip = None
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.debug:
            print(vm)
        ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else ''
        return ip

    def volumes(self, iso=False):
        """

        :param iso:
        :return:
        """
        conn = self.conn
        images = {}
        finalimages = []
        oses = ['amzn*', 'CentOS Linux 7 x86_64*', 'RHEL-7.*GA*', 'suse-sles-1?-*', 'ubuntu-*-server-*', 'kcli*',
                'CoreOS-stable*']
        Filters = [{'Name': 'name', 'Values': oses}]
        allimages = conn.describe_images(Filters=Filters)
        for image in allimages['Images']:
            name = image['Name']
            amiid = image['ImageId']
            date = datetime.strptime(image['CreationDate'], '%Y-%m-%dT%H:%M:%S.000Z')
            if 'ProductCodes' in image:
                codeid = image['ProductCodes'][0]['ProductCodeId']
                if codeid not in images or date > images[codeid]['date']:
                    images[codeid] = {'name': name, 'date': date, 'id': amiid}
            else:
                finalimages.append("%s - %s" % (name, amiid))
        for image in images:
            finalimages.append("%s - %s" % (images[image]['name'], images[image]['id']))
        return sorted(finalimages, key=str.lower)

    def delete(self, name, snapshots=False):
        """

        :param name:
        :param snapshots:
        :return:
        """
        conn = self.conn
        domain = None
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == 'domain':
                    domain = tag['Value']
        instanceid = vm['InstanceId']
        vm = conn.terminate_instances(InstanceIds=[instanceid])
        if domain is not None:
            self.delete_dns(name, domain, name)
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
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return 1
        instanceid = vm['InstanceId']
        newtags = [{"Key": metatype, "Value": metavalue}]
        conn.create_tags(Resources=[instanceid], Tags=newtags)
        return 0

    def update_memory(self, name, memory):
        """

        :param name:
        :param memory:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        state = vm['State']['Name']
        if state != 'stopped':
            common.pprint("Can't update memory of VM %s while up" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s up" % name}
        instanceid = vm['InstanceId']
        instancetype = [f for f in static_flavors if static_flavors[f]['memory'] >= int(memory)]
        if instancetype:
            flavor = instancetype[0]
            common.pprint("Using flavor %s" % flavor)
            conn.modify_instance_attribute(InstanceId=instanceid, Attribute='instanceType', Value=flavor,
                                           DryRun=False)
            return {'result': 'success'}
        else:
            common.pprint("Couldn't find matching flavor for this amount of memory", color='red')
            return {'result': 'failure', 'reason': "Couldn't find matching flavor for this amount of memory"}

    def update_flavor(self, name, flavor):
        """

        :param name:
        :param flavor:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        instancetype = vm['InstanceType']
        state = vm['State']['Name']
        if state != 'stopped':
            common.pprint("Can't update cpus of VM %s while up" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s up" % name}
        if instancetype != flavor:
            conn.modify_instance_attribute(InstanceId=instanceid, Attribute='instanceType', Value=flavor,
                                           DryRun=False)
        return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        """

        :param name:
        :param numcpus:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        state = vm['State']['Name']
        if state != 'stopped':
            common.pprint("Can't update cpus of VM %s while up" % name, color='red')
            return {'result': 'failure', 'reason': "VM %s up" % name}
        instancetype = [f for f in static_flavors if static_flavors[f]['cpus'] >= numcpus]
        if instancetype:
            flavor = instancetype[0]
            common.pprint("Using flavor %s" % flavor)
            conn.modify_instance_attribute(InstanceId=instanceid, Attribute='instanceType', Value=flavor,
                                           DryRun=False)
            return {'result': 'success'}
        else:
            common.pprint("Couldn't find matching flavor for this number of cpus", color='red')
            return {'result': 'failure', 'reason': "Couldn't find matching flavor for this number of cpus"}

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
        print("not implemented")
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
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        AvailabilityZone = vm['Placement']['AvailabilityZone']
        volume = conn.create_volume(Size=size, AvailabilityZone=AvailabilityZone)
        volumeid = volume['VolumeId']
        numdisks = len(vm['BlockDeviceMappings']) + 1
        diskname = "%s-disk%s" % (name, numdisks)
        newtags = [{"Key": "Name", "Value": diskname}]
        conn.create_tags(Resources=[volumeid], Tags=newtags)
        currentvolume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
        while currentvolume['State'] == 'creating':
            currentvolume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
            sleep(2)
        device = "/dev/sd%s" % ascii_lowercase[numdisks - 1]
        conn.attach_volume(VolumeId=volumeid, InstanceId=instanceid, Device=device)
        return

    def delete_disk(self, name=None, diskname=None, pool=None):
        """

        :param name:
        :param diskname:
        :param pool:
        :return:
        """
        conn = self.conn
        volumeid = diskname
        try:
            volume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
        except:
            return {'result': 'failure', 'reason': "Disk %s not found" % diskname}
        for attachment in volume['Attachments']:
            instanceid = attachment['InstanceId']
            conn.detach_volume(VolumeId=volumeid, InstanceId=instanceid)
            currentvolume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
            while currentvolume['State'] == 'in-use':
                currentvolume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
                sleep(2)
        conn.delete_volume(VolumeId=volumeid)
        return

# should return a dict of {'pool': poolname, 'path': name}
    def list_disks(self):
        """

        :return:
        """
        print("not implemented")
        return

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
        conn = self.conn
        resource = self.resource
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            print("VM %s not found" % name)
            return '', ''
        amid = vm['ImageId']
        image = resource.Image(amid)
        template = os.path.basename(image.image_location)
        if template != '':
            user = common.get_user(template)
        ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else ''
        if ip == '':
            print("No ip found. Cannot ssh...")
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
        sshcommand = common.ssh(name, ip=ip, user=user, local=local, remote=remote, tunnel=tunnel, insecure=insecure,
                                cmd=cmd, X=X, Y=Y, D=D, debug=self.debug)
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
        scpcommand = common.scp(name, ip='', user=user, source=source, destination=destination, recursive=recursive,
                                tunnel=tunnel, debug=self.debug, download=False)
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

    def delete_image(self, image):
        common.pprint("Deleting image %s" % image)
        conn = self.conn
        try:
            conn.deregister_image(ImageId=image)
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': "Image %s not found" % image}

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
        print("not implemented")
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
        conn = self.conn
        if cidr is not None:
            try:
                IPNetwork(cidr)
            except:
                return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
        vpc = conn.create_vpc(CidrBlock=cidr)
        vpcid = vpc['Vpc']['VpcId']
        conn.create_subnet(CidrBlock=cidr, VpcId=vpcid)
        if nat:
            conn.create_internet_gateway()
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        """

        :param name:
        :param cidr:
        :return:
        """
        conn = self.conn
        Filters = [{'Name': 'vpc-id', 'Values': [name]}]
        subnets = conn.describe_subnets(Filters=Filters)
        for subnet in subnets['Subnets']:
            subnetid = subnet['SubnetId']
            conn.delete_subnet(SubnetId=subnetid)
        conn.delete_vpc(VpcId=name)
        return {'result': 'success'}

# should return a dict of pool strings
    def list_pools(self):
        """

        :return:
        """
        print("not implemented")
        return

    def list_networks(self):
        """

        :return:
        """
        conn = self.conn
        networks = {}
        vpcs = conn.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            networkname = vpc['VpcId']
            cidr = vpc['CidrBlock']
            domainname = vpc['IsDefault']
            dhcp = vpc['DhcpOptionsId']
            mode = ''
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domainname, 'type': 'routed', 'mode': mode}
        return networks

    def list_subnets(self):
        """

        :return:
        """
        conn = self.conn
        results = {}
        vpcs = conn.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            networkname = vpc['VpcId']
            Filters = [{'Name': 'vpc-id', 'Values': [networkname]}]
            subnets = conn.describe_subnets(Filters=Filters)
            for subnet in subnets['Subnets']:
                subnetid = subnet['SubnetId']
                cidr = subnet['CidrBlock']
                az = subnet['AvailabilityZone']
                results[subnetid] = {'cidr': cidr, 'az': az, 'network': networkname}
        return results

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
        return []

    def vm_ports(self, name):
        """

        :param name:
        :return:
        """
        return []

# returns the path of the pool, if it makes sense. used by kcli list --pools
    def get_pool_path(self, pool):
        """

        :param pool:
        :return:
        """
        print("not implemented")
        return

    def __evaluate_template(self, template):
        if template.lower().startswith('centos'):
            amiid = 'ami-8352e3fe'
            common.pprint("Using ami %s" % amiid)
            return 'ami-8352e3fe'
        else:
            return template
        return template

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, instanceid=None):
        """

        :param name:
        :param nets:
        :param domain:
        :param ip:
        :param alias:
        :param force:
        :param instanceid:
        :return:
        """
        common.pprint("Using domain %s..." % domain)
        dns = self.dns
        net = nets[0]
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == '%s.' % domain]
        if not zone:
            common.pprint("Domain %s not found" % domain, color='red')
            return {'result': 'failure', 'reason': "Domain not found"}
        zoneid = zone[0]
        entry = "%s.%s." % (name, domain)
        if ip is None:
            if isinstance(net, dict):
                ip = net.get('ip')
            if ip is None:
                counter = 0
                while counter != 100:
                    ip = self.ip(instanceid)
                    if ip is None:
                        sleep(5)
                        print("Waiting 5 seconds to grab ip and create DNS record...")
                        counter += 10
                    else:
                        break
        if ip is None:
            print("Couldn't assign DNS")
            return
        changes = [{'Action': 'CREATE', 'ResourceRecordSet':
                   {'Name': entry, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ip}]}}]
        if alias:
            for a in alias:
                if a == '*':
                    new = '*.%s.%s.' % (name, domain)
                    changes.append({'Action': 'CREATE', 'ResourceRecordSet':
                                    {'Name': new, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ip}]}})
                else:
                    new = '%s.%s.' % (a, domain) if '.' not in a else '%s.' % a
                    changes.append({'Action': 'CREATE', 'ResourceRecordSet':
                                    {'Name': new, 'Type': 'CNAME', 'TTL': 300, 'ResourceRecords': [{'Value': entry}]}})
        dns.change_resource_record_sets(HostedZoneId=zoneid, ChangeBatch={'Changes': changes})
        return {'result': 'success'}

    def delete_dns(self, name, domain, instanceid=None):
        """

        :param name:
        :param domain:
        :param instanceid:
        :return:
        """
        dns = self.dns
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == '%s.' % domain]
        if not zone:
            common.pprint("Domain not found", color='red')
            return {'result': 'failure', 'reason': "Domain not found"}
        zoneid = zone[0]
        entry = "%s.%s." % (name, domain)
        ip = self.ip(instanceid)
        if ip is None:
            print("Couldn't Get DNS Ip")
            return
        for entry in ["%s.%s." % (name, domain), "*.%s.%s." % (name, domain)]:
            changes = [{'Action': 'DELETE', 'ResourceRecordSet':
                        {'Name': entry, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ip}]}}]
            try:
                dns.change_resource_record_sets(HostedZoneId=zoneid, ChangeBatch={'Changes': changes})
            except:
                pass
        return {'result': 'success'}

    def flavors(self):
        """

        :return:
        """
        results = []
        for flavor in static_flavors:
            name = flavor
            numcpus = static_flavors[flavor]['cpus']
            memory = static_flavors[flavor]['memory']
            results.append([name, numcpus, memory])
        return results

    def export(self, name, template=None):
        """

        :param name:
        :param template:
        :return:
        """
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        InstanceId = vm['InstanceId']
        Name = template if template is not None else "kcli %s" % name
        Description = "template based on %s" % name
        conn.create_image(InstanceId=InstanceId, Name=Name, Description=Description, NoReboot=True)
        return {'result': 'success'}

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None):
        ports = [int(port) for port in ports]
        resource = self.resource
        conn = self.conn
        elb = self.elb
        protocols = {80: 'HTTP', 8080: 'HTTP', 443: 'HTTPS'}
        Listeners = []
        for port in ports:
            protocol = protocols[port] if port in protocols else 'TCP'
            Listener = {'Protocol': protocol, 'LoadBalancerPort': port, 'InstanceProtocol': protocol,
                        'InstancePort': port}
            Listeners.append(Listener)
        AvailabilityZones = ["%s%s" % (self.region, i) for i in ['a', 'b', 'c']]
        lb = elb.create_load_balancer(LoadBalancerName=name, Listeners=Listeners, AvailabilityZones=AvailabilityZones)
        sg = resource.create_security_group(GroupName=name, Description=name)
        sgid = sg.id
        sgtags = [{"Key": "Name", "Value": name}]
        sg.create_tags(Tags=sgtags)
        for port in ports:
            sg.authorize_ingress(GroupName=name, FromPort=port, ToPort=port, IpProtocol='tcp',
                                 CidrIp="0.0.0.0/0")
        if 80 in ports:
            HealthTarget = 'HTTP:80%s' % checkpath
        else:
            HealthTarget = '%s:%s' % (protocol, port)
        HealthCheck = {'Interval': 20, 'Target': HealthTarget, 'Timeout': 3, 'UnhealthyThreshold': 10,
                       'HealthyThreshold': 2}
        elb.configure_health_check(LoadBalancerName=name, HealthCheck=HealthCheck)
        common.pprint("Reserved dns name %s" % lb['DNSName'])
        if vms:
            Instances = []
            for vm in vms:
                update = self.update_metadata(vm, 'loadbalancer', name)
                instanceid = self.get_id(vm)
                if update == 0 and instanceid is not None:
                    Instances.append({"InstanceId": instanceid})
                sgs = self.get_security_groups(vm)
                sgnames = [x['GroupName'] for x in sgs]
                if name not in sgnames:
                    sgids = [x['GroupId'] for x in sgs]
                    sgids.append(sgid)
                    conn.modify_instance_attribute(InstanceId=instanceid, Groups=sgids)
            if Instances:
                elb.register_instances_with_load_balancer(LoadBalancerName=name, Instances=Instances)
        return

    def delete_loadbalancer(self, name):
        elb = self.elb
        conn = self.conn
        elb.delete_load_balancer(LoadBalancerName=name)
        vms = [v['name'] for v in self.list() if 'loadbalancer' in v and v['loadbalancer'] == name]
        for vm in vms:
            instanceid = self.get_id(vm)
            sgs = self.get_security_groups(vm)
            sgids = []
            for sg in sgs:
                if sg['GroupName'] != name:
                    sgids.append(sg['GroupId'])
            if sgids:
                conn.modify_instance_attribute(InstanceId=instanceid, Groups=sgids)
        conn.delete_security_group(GroupName=name)

    def list_loadbalancers(self):
        results = []
        elb = self.elb
        lbs = elb.describe_load_balancers()
        ports = []
        for lb in lbs['LoadBalancerDescriptions']:
            name = lb['LoadBalancerName']
            ip = lb['DNSName']
            for listener in lb['ListenerDescriptions']:
                protocol = listener['Listener']['Protocol']
                ports.append(str(listener['Listener']['LoadBalancerPort']))
            ports = '+'.join(ports)
            target = ''
            results.append([name, ip, protocol, ports, target])
        return results
