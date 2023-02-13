#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Aws Provider Class
"""

from ipaddress import ip_network
from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import METADATA_FIELDS
import boto3
import os
import sys
from socket import gethostbyname
from string import ascii_lowercase
from time import sleep
import webbrowser

staticf = {'t2.nano': {'cpus': 1, 'memory': 512}, 't2.micro': {'cpus': 1, 'memory': 1024},
           't2.small': {'cpus': 1, 'memory': 2048}, 't2.medium': {'cpus': 2, 'memory': 4096},
           't2.large': {'cpus': 2, 'memory': 8144}, 't2.xlarge': {'cpus': 2, 'memory': 16384},
           'm5.large': {'cpus': 2, 'memory': 8144}, 'm5.xlarge': {'cpus': 4, 'memory': 16384},
           'm5.2xlarge': {'cpus': 8, 'memory': 32768}, 'm5.4xlarge': {'cpus': 16, 'memory': 65536}
           }


class Kaws(object):
    """

    """
    def __init__(self, access_key_id=None, access_key_secret=None, debug=False,
                 region='eu-west-3', keypair=None, session_token=None):
        self.ami_date = 20195
        self.debug = debug
        self.conn = boto3.client('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                 region_name=region, aws_session_token=session_token)
        self.resource = boto3.resource('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                       region_name=region, aws_session_token=session_token)
        self.dns = boto3.client('route53', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                region_name=region, aws_session_token=session_token)
        self.elb = boto3.client('elb', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                region_name=region, aws_session_token=session_token)
        self.s3 = boto3.client('s3', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                               region_name=region, aws_session_token=session_token)
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = region
        self.keypair = keypair
        return

    def close(self):
        return

    def exists(self, name):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
            return True
        except:
            return False

    def net_exists(self, name):
        conn = self.conn
        try:
            conn.describe_subnets(SubnetIds=[name])
            return True
        except:
            return False

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
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        image = self.__evaluate_image(image)
        keypair = self.keypair
        if image is None:
            return {'result': 'failure', 'reason': 'An image (or amid) is required'}
        else:
            _filter = 'image-id' if image.startswith('ami-') else 'name'
            Filters = [{'Name': _filter, 'Values': [image]}]
            images = conn.describe_images(Filters=Filters)
            if 'Images' in images and images['Images']:
                imageinfo = images['Images'][0]
                imageid = imageinfo['ImageId']
                if _filter == 'name':
                    pprint(f"Using ami {imageid}")
                image = imageinfo['Name']
            else:
                return {'result': 'failure', 'reason': f'Invalid image {image}'}
        defaultsubnetid = None
        if flavor is None:
            matching = [f for f in staticf if staticf[f]['cpus'] >= numcpus and staticf[f]['memory'] >= memory]
            if matching:
                flavor = matching[0]
                pprint(f"Using instance type {flavor}")
            else:
                return {'result': 'failure', 'reason': 'Couldnt find instance type matching requirements'}
        vmtags = [{'ResourceType': 'instance',
                   'Tags': [{'Key': 'Name', 'Value': name}, {'Key': 'hostname', 'Value': name}]}]
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            vmtags[0]['Tags'].append({'Key': entry, 'Value': metadata[entry]})
        if keypair is None:
            keypair = f'kvirt_{self.access_key_id}'
        keypairs = [k for k in conn.describe_key_pairs()['KeyPairs'] if k['KeyName'] == keypair]
        if not keypairs:
            pprint(f"Importing your public key as {keypair}")
            publickeyfile = get_ssh_pub_key()
            if publickeyfile is None:
                error("No public key found. Leaving")
                return {'result': 'failure', 'reason': 'No public key found'}
            publickeyfile = open(publickeyfile).read()
            conn.import_key_pair(KeyName=keypair, PublicKeyMaterial=publickeyfile)
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
        networkinterfaces = []
        blockdevicemappings = []
        privateips = []
        vpcs = conn.describe_vpcs()
        subnets = conn.describe_subnets()
        for index, net in enumerate(nets):
            networkinterface = {'DeleteOnTermination': True, 'Description': f"eth{index}", 'DeviceIndex': index,
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
            # if securitygroups:
            #    netpublic = False
            networkinterface['AssociatePublicIpAddress'] = netpublic if index == 0 else False
            if netname in [subnet['SubnetId'] for subnet in subnets['Subnets']]:
                vpcid = [subnet['VpcId'] for subnet in subnets['Subnets'] if subnet['SubnetId'] == netname][0]
            elif netname == 'default':
                if defaultsubnetid is not None:
                    netname = defaultsubnetid
                else:
                    vpcid = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']]
                    if not vpcid:
                        error("Couldn't find default vpc")
                        sys.exit(1)
                    vpcid = vpcid[0]
                    subnetid = [subnet['SubnetId'] for subnet in subnets['Subnets']
                                if subnet['DefaultForAz'] and subnet['VpcId'] == vpcid][0]
                    netname = subnetid
                    defaultsubnetid = netname
                    pprint(f"Using subnet {defaultsubnetid} as default")
            else:
                vpcid = self.get_vpc_id(vpcs, netname) if not netname.startswith('vpc-') else netname
                if vpcid is None:
                    error(f"Couldn't find vpc {netname}")
                    sys.exit(1)
                subnetids = [subnet['SubnetId'] for subnet in subnets['Subnets'] if subnet['VpcId'] == vpcid]
                if subnetids:
                    netname = subnetids[0]
                else:
                    error(f"Couldn't find valid subnet for vpc {netname}")
                    sys.exit(1)
            if ips and len(ips) > index and ips[index] is not None:
                ip = ips[index]
                if index == 0:
                    networkinterface['PrivateIpAddress'] = ip
                    privateip = {'Primary': True, 'PrivateIpAddress': ip}
                else:
                    privateip = {'Primary': False, 'PrivateIpAddress': ip}
                privateips.append(privateip)
            networkinterface['SubnetId'] = netname
            if index == 0:
                SecurityGroupIds = []
                for sg in securitygroups:
                    sgid = self.get_security_group_id(sg, vpcid)
                    if sgid is not None:
                        SecurityGroupIds.append(sgid)
                if 'kubetype' in metadata and metadata['kubetype'] == "openshift":
                    kube = metadata['kube']
                    pprint(f"Adding vm to security group {kube}")
                    kubesgid = self.get_security_group_id(kube, vpcid)
                    if kubesgid is None:
                        sg = self.resource.create_security_group(GroupName=kube, Description=kube, VpcId=vpcid)
                        sgtags = [{"Key": "Name", "Value": kube}]
                        sg.create_tags(Tags=sgtags)
                        kubesgid = sg.id
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=-1, ToPort=-1, IpProtocol='icmp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=22, ToPort=22, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=80, ToPort=80, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=8080, ToPort=8080, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=5443, ToPort=5443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=8443, ToPort=8443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=443, ToPort=443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=6443, ToPort=6443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=22624, ToPort=22624, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=2379, ToPort=2380, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=30000, ToPort=32767, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=30000, ToPort=32767, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=10250, ToPort=10259, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=9000, ToPort=9999, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=9000, ToPort=9999, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=4789, ToPort=4789, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=4789, ToPort=4789, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=6081, ToPort=6081, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=6081, ToPort=6081, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                    SecurityGroupIds.append(kubesgid)
                elif 'kubetype' in metadata and metadata['kubetype'] == "generic":
                    kube = metadata['kube']
                    pprint(f"Adding vm to security group {kube}")
                    kubesgid = self.get_security_group_id(kube, vpcid)
                    if kubesgid is None:
                        sg = self.resource.create_security_group(GroupName=kube, Description=kube, VpcId=vpcid)
                        sgtags = [{"Key": "Name", "Value": kube}]
                        sg.create_tags(Tags=sgtags)
                        kubesgid = sg.id
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=-1, ToPort=-1, IpProtocol='icmp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=22, ToPort=22, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=6443, ToPort=6443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=2379, ToPort=2380, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kubesgid, FromPort=2380, ToPort=2380, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                    SecurityGroupIds.append(kubesgid)
                networkinterface['Groups'] = SecurityGroupIds
            networkinterfaces.append(networkinterface)
        if len(privateips) > 1:
            networkinterface['PrivateIpAddresses'] = privateips
        for index, disk in enumerate(disks):
            devicename = imageinfo['RootDeviceName'] if index == 0 else f"/dev/xvd{chr(index + ord('a'))}"
            blockdevicemapping = {'DeviceName': devicename, 'Ebs': {'DeleteOnTermination': True,
                                                                    'VolumeType': 'standard'}}
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
            elif isinstance(disk, dict):
                disksize = int(disk.get('size', 10))
                blockdevicemapping['Ebs']['VolumeType'] = disk.get('type', 'standard')
            blockdevicemapping['Ebs']['VolumeSize'] = disksize
            blockdevicemappings.append(blockdevicemapping)
        conn.run_instances(ImageId=imageid, MinCount=1, MaxCount=1, InstanceType=flavor,
                           KeyName=keypair, BlockDeviceMappings=blockdevicemappings,
                           NetworkInterfaces=networkinterfaces, UserData=userdata, TagSpecifications=vmtags)
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        conn.start_instances(InstanceIds=[instanceid])
        return {'result': 'success'}

    def stop(self, name, soft=False):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        conn.stop_instances(InstanceIds=[instanceid])
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
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        conn.start_instances(InstanceIds=[instanceid])
        return {'result': 'success'}

    def report(self):
        print(f"Region: {self.region}")
        return

    def status(self, name):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        status = vm['State']['Name']
        return status

    def list(self):
        conn = self.conn
        vms = []
        results = conn.describe_instances()
        reservations = results['Reservations']
        for reservation in reservations:
            vm = reservation['Instances'][0]
            name = vm['InstanceId']
            try:
                vms.append(self.info(name))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        try:
            if name.startswith('i-'):
                vm = self.conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
            else:
                Filters = {'Name': "tag:Name", 'Values': [name]}
                vm = self.conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
        instanceid = vm['InstanceId']
        amid = vm['ImageId']
        image = self.resource.Image(amid)
        source = os.path.basename(image.image_location)
        user = common.get_user(source)
        user = 'ec2-user'
        url = f"https://eu-west-3.console.aws.amazon.com/ec2/v2/connect/{user}/{instanceid}"
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
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return
        instanceid = vm['InstanceId']
        response = conn.get_console_output(InstanceId=instanceid, DryRun=False, Latest=False)
        if 'Output' not in response:
            error(f"VM {name} not ready yet")
            return
        if web:
            return response['Output']
        else:
            print(response['Output'])

    def dnsinfo(self, name):
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
        conn = self.conn
        try:
            if name.startswith('i-'):
                vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
            else:
                Filters = {'Name': "tag:Name", 'Values': [name]}
                vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return []
        return vm['SecurityGroups']

    def get_security_group_id(self, name, vpcid):
        conn = self.conn
        for sg in conn.describe_security_groups()['SecurityGroups']:
            if sg['VpcId'] == vpcid and (sg['GroupName'] == name or sg['GroupId'] == name):
                return sg['GroupId']
        return None

    def get_default_security_group_id(self, vpcid):
        conn = self.conn
        for sg in conn.describe_security_groups()['SecurityGroups']:
            if sg['VpcId'] == vpcid and (sg['GroupName'] == 'default'):
                return sg['GroupId']

    def get_vpc_id(self, vpcs, name):
        vpcid = None
        for vpc in vpcs['Vpcs']:
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name' and tag['Value'] == name:
                        vpcid = vpc['VpcId']
                        break
        return vpcid

    def info(self, name, vm=None, debug=False):
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
                error(f"VM {name} not found")
                return {}
        instanceid = vm['InstanceId']
        name = instanceid
        state = vm['State']['Name']
        amid = vm['ImageId']
        az = vm['Placement']['AvailabilityZone']
        image = resource.Image(amid)
        source = os.path.basename(image.image_location)
        yamlinfo['plan'] = ''
        yamlinfo['profile'] = ''
        if 'Tags' in vm:
            for tag in vm['Tags']:
                yamlinfo[tag['Key']] = tag['Value']
                if tag['Key'] == 'Name':
                    name = tag['Value']
        yamlinfo['name'] = name
        yamlinfo['status'] = state
        yamlinfo['az'] = az
        yamlinfo['ip'] = vm.get('PublicIpAddress')
        machinetype = vm['InstanceType']
        flavor = conn.describe_instance_types(InstanceTypes=[machinetype])['InstanceTypes'][0]
        yamlinfo['cpus'] = flavor['VCpuInfo']['DefaultVCpus']
        yamlinfo['memory'] = flavor['MemoryInfo']['SizeInMiB']
        yamlinfo['flavor'] = machinetype
        yamlinfo['image'] = source
        yamlinfo['user'] = common.get_user(yamlinfo['image'])
        yamlinfo['instanceid'] = instanceid
        nets = []
        for interface in vm['NetworkInterfaces']:
            network = interface['VpcId']
            device = interface['NetworkInterfaceId']
            mac = interface['MacAddress']
            private_ip = interface['PrivateIpAddresses'][0]['PrivateIpAddress']
            nets.append({'device': device, 'mac': mac, 'net': network, 'type': private_ip})
            yamlinfo['private_ip'] = private_ip

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
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def get_vpcid_of_vm(self, name):
        vcpid = None
        conn = self.conn
        try:
            if name.startswith('i-'):
                vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
            else:
                Filters = {'Name': "tag:Name", 'Values': [name]}
                vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return {}
        for interface in vm['NetworkInterfaces']:
            vpcid = interface['VpcId']
            return vpcid
        return vcpid

    def ip(self, name):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        return vm.get('PublicIpAddress')

    def internalip(self, name):
        ip = None
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['NetworkInterfaces'] and 'PrivateIpAddresses' in vm['NetworkInterfaces'][0]:
            ip = vm['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['PrivateIpAddress']
        if ip == '':
            ip = None
        return ip

    def volumes(self, iso=False):
        conn = self.conn
        images = []
        oses = ['CentOS Linux 7*', 'CentOS Stream*', 'CentOS Linux 8*', 'RHEL-7*', 'RHEL-8.*', 'rhcos-4*',
                'fedora-coreos*', 'Debian*', 'Ubuntu*']
        Filters = [{'Name': 'name', 'Values': oses}]
        rhcos = {}
        allimages = conn.describe_images(Filters=Filters)
        for image in allimages['Images']:
            name = image['Name']
            if name.startswith('rhcos') and 'devel' in name:
                continue
            elif 'beta' in name.lower():
                continue
            elif name.startswith('rhcos-4'):
                number = name[6:8]
                rhcos[number] = [name]
                continue
            else:
                images.append(name)
        for value in rhcos.values():
            images.append(value[0])
        return sorted(images, key=str.lower)

    def delete(self, name, snapshots=False):
        conn = self.conn
        dnsclient, domain = None, None
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['State']['Name'] not in ['pending', 'running']:
            return {'result': 'success'}
        instanceid = vm['InstanceId']
        kubetype, kube = None, None
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == 'domain':
                    domain = tag['Value']
                if tag['Key'] == 'dnsclient':
                    dnsclient = tag['Value']
                if tag['Key'] == 'kubetype':
                    kubetype = tag['Value']
                if tag['Key'] == 'kube':
                    kube = tag['Value']
            if kubetype is not None and kubetype == 'openshift':
                vpcid = vm['NetworkInterfaces'][0]['VpcId']
                defaultsgid = self.get_default_security_group_id(vpcid)
                conn.modify_instance_attribute(InstanceId=instanceid, Groups=[defaultsgid])
        vm = conn.terminate_instances(InstanceIds=[instanceid])
        if domain is not None and dnsclient is None:
            self.delete_dns(name, domain, name)
        if kubetype is not None and kubetype == 'openshift':
            try:
                conn.delete_security_group(GroupName=kube)
            except:
                pass
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return 1
        instanceid = vm['InstanceId']
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == metatype:
                    oldvalue = tag['Value']
                    oldtags = [{"Key": metatype, "Value": oldvalue}]
                    conn.delete_tags(Resources=[instanceid], Tags=oldtags)
                    if append:
                        metavalue = f"{oldvalue},{metavalue}"
        newtags = [{"Key": metatype, "Value": metavalue}]
        conn.create_tags(Resources=[instanceid], Tags=newtags)
        return 0

    def update_memory(self, name, memory):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        state = vm['State']['Name']
        if state != 'stopped':
            error(f"Can't update memory of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        instanceid = vm['InstanceId']
        instancetype = [f for f in staticf if staticf[f]['memory'] >= int(memory)]
        if instancetype:
            flavor = instancetype[0]
            pprint(f"Using flavor {flavor}")
            conn.modify_instance_attribute(InstanceId=instanceid, Attribute='instanceType', Value=flavor,
                                           DryRun=False)
            return {'result': 'success'}
        else:
            error("Couldn't find matching flavor for this amount of memory")
            return {'result': 'failure', 'reason': "Couldn't find matching flavor for this amount of memory"}

    def update_flavor(self, name, flavor):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        instancetype = vm['InstanceType']
        state = vm['State']['Name']
        if state != 'stopped':
            error(f"Can't update cpus of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        if instancetype != flavor:
            conn.modify_instance_attribute(InstanceId=instanceid, Attribute='instanceType', Value=flavor,
                                           DryRun=False)
        return {'result': 'success'}

    def update_cpus(self, name, numcpus):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        state = vm['State']['Name']
        if state != 'stopped':
            error(f"Can't update cpus of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        instancetype = [f for f in staticf if staticf[f]['cpus'] >= numcpus]
        if instancetype:
            flavor = instancetype[0]
            pprint(f"Using flavor {flavor}")
            conn.modify_instance_attribute(InstanceId=instanceid, Attribute='instanceType', Value=flavor,
                                           DryRun=False)
            return {'result': 'success'}
        else:
            error("Couldn't find matching flavor for this number of cpus")
            return {'result': 'failure', 'reason': "Couldn't find matching flavor for this number of cpus"}

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
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        AvailabilityZone = vm['Placement']['AvailabilityZone']
        volume = conn.create_volume(Size=size, AvailabilityZone=AvailabilityZone)
        volumeid = volume['VolumeId']
        numdisks = len(vm['BlockDeviceMappings']) + 1
        diskname = f"{name}-disk{numdisks}"
        newtags = [{"Key": "Name", "Value": diskname}]
        conn.create_tags(Resources=[volumeid], Tags=newtags)
        currentvolume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
        while currentvolume['State'] == 'creating':
            currentvolume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
            sleep(2)
        device = f"/dev/sd{ascii_lowercase[numdisks - 1]}"
        conn.attach_volume(VolumeId=volumeid, InstanceId=instanceid, Device=device)
        return

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        conn = self.conn
        volumeid = diskname
        try:
            volume = conn.describe_volumes(VolumeIds=[volumeid])['Volumes'][0]
        except:
            return {'result': 'failure', 'reason': f"Disk {diskname} not found"}
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
        print("not implemented")
        return

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
        try:
            conn.deregister_image(ImageId=image)
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': f"Image {image} not found"}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        conn = self.conn
        if cidr is not None:
            try:
                network = ip_network(cidr)
            except:
                return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
            if str(network.version) == "6":
                msg = 'Primary cidr needs to be ipv4 in aws. Use dual to inject ipv6 or set aws_ipv6 parameter'
                return {'result': 'failure', 'reason': msg}
        default = 'default' in overrides and overrides['default']
        Tags = [{"Key": "Name", "Value": name}, {"Key": "Plan", "Value": plan}]
        vpcargs = {"CidrBlock": cidr}
        if 'dual_cidr' in overrides:
            vpcargs["Ipv6CidrBlock"] = overrides['dual_cidr']
            vpcargs["Ipv6Pool"] = overrides['dual_cidr']
        if 'aws_ipv6' in overrides and overrides['aws_ipv6']:
            vpcargs["AmazonProvidedIpv6CidrBlock"] = True
        if default:
            networks = self.list_networks()
            default_network = [n for n in networks if networks[n]['mode'] == 'default']
            if default_network:
                msg = f"network {default_network[0]} is already default"
                return {'result': 'failure', 'reason': msg}
            vpc = conn.create_default_vpc(**vpcargs)
            vpcid = vpc['Vpc']['VpcId']
            conn.create_tags(Resources=[vpcid], Tags=Tags)
            return {'result': 'success'}
        vpc = conn.create_vpc(**vpcargs)
        vpcid = vpc['Vpc']['VpcId']
        conn.create_tags(Resources=[vpcid], Tags=Tags)
        vpcargs['VpcId'] = vpcid
        subnet = conn.create_subnet(**vpcargs)
        subnetid = subnet['Subnet']['SubnetId']
        conn.create_tags(Resources=[subnetid], Tags=Tags)
        if nat:
            gateway = conn.create_internet_gateway()
            gatewayid = gateway['InternetGateway']['InternetGatewayId']
            gateway = self.resource.InternetGateway(gatewayid)
            gateway.attach_to_vpc(VpcId=vpcid)
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None):
        conn = self.conn
        vpcid = None
        Filters = [{'Name': 'vpc-id', 'Values': [name]}]
        vpcs = conn.describe_vpcs(Filters=Filters)['Vpcs']
        if vpcs:
            vpcid = vpcs[0]['VpcId']
        else:
            Filters = [{'Name': "tag:Name", 'Values': [name]}]
            vpcs = conn.describe_vpcs(Filters=Filters)['Vpcs']
            if vpcs:
                vpcid = vpcs[0]['VpcId']
        if vpcid is None:
            return {'result': 'failure', 'reason': f"Network {name} not found"}
        Filters = [{'Name': 'vpc-id', 'Values': [vpcid]}]
        subnets = conn.describe_subnets(Filters=Filters)
        for subnet in subnets['Subnets']:
            subnetid = subnet['SubnetId']
            conn.delete_subnet(SubnetId=subnetid)
        for gateway in conn.describe_internet_gateways()['InternetGateways']:
            attachments = gateway['Attachments']
            for attachment in attachments:
                if attachment['VpcId'] == vpcid:
                    gatewayid = gateway['InternetGatewayId']
                    gateway = self.resource.InternetGateway(gatewayid)
                    gateway.detach_from_vpc(VpcId=vpcid)
                    gateway.delete()
        conn.delete_vpc(VpcId=vpcid)
        return {'result': 'success'}

    def list_pools(self):
        print("not implemented")
        return []

    def list_networks(self):
        conn = self.conn
        networks = {}
        vpcs = conn.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            plan = None
            networkname = vpc['VpcId']
            cidr = vpc['CidrBlock']
            domain = ''
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name':
                        domain = tag['Value']
                    if tag['Key'] == 'Plan':
                        plan = tag['Value']
            mode = 'default' if vpc['IsDefault'] else 'N/A'
            dhcp = vpc['DhcpOptionsId']
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': domain, 'type': 'routed', 'mode': mode}
            if plan is not None:
                networks[networkname]['plan'] = plan
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        return networkinfo

    def list_subnets(self):
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
        print("not implemented")
        return

    def network_ports(self, name):
        return []

    def vm_ports(self, name):
        return []

    def get_pool_path(self, pool):
        print("not implemented")
        return

    def __evaluate_image(self, image):
        if image is not None and image.lower().startswith('centos7'):
            image = 'ami-8352e3fe'
            pprint(f"Using ami {image}")
        return image

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None):
        if domain is None:
            domain = nets[0]
        internalip = None
        pprint(f"Using domain {domain}")
        dns = self.dns
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == f'{domain}.']
        if not zone:
            error(f"Domain {domain} not found")
            return {'result': 'failure', 'reason': f"Domain {domain} not found"}
        zoneid = zone[0]
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
        changes = [{'Action': 'CREATE', 'ResourceRecordSet':
                   {'Name': entry, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': dnsip}]}}]
        if alias:
            for a in alias:
                if a == '*':
                    if cluster is not None and ('ctlplane' in name or 'worker' in name):
                        new = f'*.apps.{cluster}.{domain}.'
                    else:
                        new = f'*.{name}.{domain}.'
                    changes.append({'Action': 'CREATE', 'ResourceRecordSet':
                                    {'Name': new, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ip}]}})
                else:
                    new = f'{a}.{domain}.' if '.' not in a else f'{a}.'
                    changes.append({'Action': 'CREATE', 'ResourceRecordSet':
                                    {'Name': new, 'Type': 'CNAME', 'TTL': 300, 'ResourceRecords': [{'Value': entry}]}})
        dns.change_resource_record_sets(HostedZoneId=zoneid, ChangeBatch={'Changes': changes})
        return {'result': 'success'}

    def delete_dns(self, name, domain, instanceid=None, allentries=False):
        dns = self.dns
        cluster = None
        fqdn = f"{name}.{domain}"
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace(f"{name}.", '').replace(f"{cluster}.", '')
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == f'{domain}.']
        if not zone:
            error(f"Domain {domain} not found")
            return {'result': 'failure', 'reason': f"Domain {domain} not found"}
        zoneid = zone[0]
        dnsentry = name if cluster is None else f"{name}.{cluster}"
        entry = f"{dnsentry}.{domain}."
        ip = self.ip(instanceid)
        if ip is None:
            error(f"Couldn't Get DNS Ip for {name}")
            return
        recs = []
        clusterdomain = f"{cluster}.{domain}"
        for record in dns.list_resource_record_sets(HostedZoneId=zoneid)['ResourceRecordSets']:
            if entry in record['Name'] or ('ctlplane-0' in name and record['Name'].endswith(f"{clusterdomain}.")):
                recs.append(record)
            else:
                if 'ResourceRecords' in record:
                    for rrdata in record['ResourceRecords']:
                        if name in rrdata['Value']:
                            recs.append(record)
        changes = [{'Action': 'DELETE', 'ResourceRecordSet': record} for record in recs]
        try:
            dns.change_resource_record_sets(HostedZoneId=zoneid, ChangeBatch={'Changes': changes})
        except:
            pass
        return {'result': 'success'}

    def list_dns(self, domain):
        results = []
        dns = self.dns
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == f'{domain}.']
        if not zone:
            error("Domain not found")
        else:
            zoneid = zone[0]
            for record in dns.list_resource_record_sets(HostedZoneId=zoneid)['ResourceRecordSets']:
                name = record['Name']
                _type = record['Type']
                ttl = record.get('TTL', 'N/A')
                if _type not in ['NS', 'SOA']:
                    name = name.replace(f"{domain}.", '')
                name = name[:-1]
                if 'ResourceRecords' in record:
                    data = ' '.join(x['Value'] for x in record['ResourceRecords'])
                elif 'AliasTarget' in record:
                    data = record['AliasTarget']['DNSName'][:-1]
                else:
                    continue
                results.append([name, _type, ttl, data])
        return results

    def list_flavors(self):
        results = []
        flavors = self.conn.describe_instance_types()['InstanceTypes']
        for flavor in flavors:
            if self.debug:
                print(flavor)
            name = flavor['InstanceType']
            numcpus = flavor['VCpuInfo']['DefaultVCpus']
            memory = flavor['MemoryInfo']['SizeInMiB']
            results.append([name, numcpus, memory])
        return sorted(results)

    def export(self, name, image=None):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        InstanceId = vm['InstanceId']
        Name = image if image is not None else f"kcli {name}"
        Description = f"image based on {name}"
        conn.create_image(InstanceId=InstanceId, Name=Name, Description=Description, NoReboot=True)
        return {'result': 'success'}

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False, dnsclient=None, subnetid=None):
        ports = [int(port) for port in ports]
        resource = self.resource
        conn = self.conn
        elb = self.elb
        protocols = {}
        Listeners = []
        for port in ports:
            protocol = protocols[port] if port in protocols else 'TCP'
            Listener = {'Protocol': protocol, 'LoadBalancerPort': port, 'InstanceProtocol': protocol,
                        'InstancePort': port}
            Listeners.append(Listener)
        AvailabilityZones = [f"{self.region}{i}" for i in ['a', 'b', 'c']]
        clean_name = name.replace('.', '-')
        sg_data = {'GroupName': name, 'Description': name}
        if subnetid is not None:
            vpcid = [sub['VpcId'] for sub in conn.describe_subnets()['Subnets'] if sub['SubnetId'] == subnetid][0]
            sg_data['VpcId'] = vpcid
        else:
            vpcid = None
        sg = resource.create_security_group(**sg_data)
        sgid = sg.id
        sgtags = [{"Key": "Name", "Value": name}]
        sg.create_tags(Tags=sgtags)
        for port in ports:
            sg.authorize_ingress(GroupId=sgid, FromPort=port, ToPort=port, IpProtocol='tcp', CidrIp="0.0.0.0/0")
        lbinfo = {"LoadBalancerName": clean_name, "Listeners": Listeners, "SecurityGroups": [sgid]}
        if subnetid is not None:
            lbinfo['Subnets'] = [subnetid]
        else:
            lbinfo['AvailabilityZones'] = AvailabilityZones
        if domain is not None:
            lbinfo['Tags'] = [{"Key": "domain", "Value": domain}]
            if dnsclient is not None:
                lbinfo['Tags'].append({"Key": "dnsclient", "Value": dnsclient})
        lb = elb.create_load_balancer(**lbinfo)
        HealthTarget = f'{protocol}:{port}'
        HealthCheck = {'Interval': 20, 'Target': HealthTarget, 'Timeout': 3, 'UnhealthyThreshold': 10,
                       'HealthyThreshold': 2}
        elb.configure_health_check(LoadBalancerName=clean_name, HealthCheck=HealthCheck)
        pprint(f"Reserved dns name {lb['DNSName']}")
        if vms:
            Instances = []
            for vm in vms:
                update = self.update_metadata(vm, 'loadbalancer', name, append=True)
                if domain is not None:
                    self.update_metadata(vm, 'domain', domain)
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
                elb.register_instances_with_load_balancer(LoadBalancerName=clean_name, Instances=Instances)
        if domain is not None:
            lb_dns_name = lb['DNSName']
            while True:
                try:
                    ip = gethostbyname(lb_dns_name)
                    break
                except:
                    pprint(f"Waiting 10s for {lb_dns_name} to get an ip resolution")
                    sleep(10)
            if dnsclient is not None:
                return ip
            self.reserve_dns(name, ip=ip, domain=domain, alias=alias)
        return

    def delete_loadbalancer(self, name):
        domain = None
        dnsclient = None
        elb = self.elb
        conn = self.conn
        clean_name = name.replace('.', '-')
        try:
            tags = elb.describe_tags(LoadBalancerNames=[clean_name])
            if tags:
                lbtags = tags['TagDescriptions'][0]['Tags']
                for tag in lbtags:
                    if tag['Key'] == 'dnsclient':
                        dnsclient = tag['Value']
                    if tag['Key'] == 'domain':
                        domain = tag['Value']
                        pprint(f"Using found domain {domain}")
        except:
            warning(f"Loadbalancer {clean_name} not found")
            pass
        vms = [v['name'] for v in self.list() if 'loadbalancer' in v and name in v['loadbalancer']]
        for vm in vms:
            instanceid = self.get_id(vm)
            sgs = self.get_security_groups(vm)
            sgids = []
            for sg in sgs:
                if sg['GroupName'] != name:
                    sgids.append(sg['GroupId'])
            if sgids:
                pprint(f"Removing {vm} from security group {name}")
                conn.modify_instance_attribute(InstanceId=instanceid, Groups=sgids)
        matching_lbs = [lb['LoadBalancerName'] for lb in elb.describe_load_balancers()['LoadBalancerDescriptions']
                        if lb['LoadBalancerName'] == clean_name]
        if matching_lbs:
            lb_found = True
            for lb_id in matching_lbs:
                elb.delete_load_balancer(LoadBalancerName=clean_name)
        else:
            lb_found = False
        if domain is not None and dnsclient is None:
            warning(f"Deleting DNS {name}.{domain}")
            self.delete_dns(name, domain, name)
        try:
            if lb_found:
                sleep(30)
            matching_sgs = [sg['GroupId'] for sg in self.conn.describe_security_groups()['SecurityGroups']
                            if sg['GroupName'] == clean_name]
            if matching_sgs:
                for sgid in matching_sgs:
                    conn.delete_security_group(GroupId=sgid)
        except Exception as e:
            warning(f"Couldn't remove security group {name}. Got {e}")
        if dnsclient is not None:
            return dnsclient

    def list_loadbalancers(self):
        results = []
        elb = self.elb
        lbs = elb.describe_load_balancers()
        for lb in lbs['LoadBalancerDescriptions']:
            ports = []
            name = lb['LoadBalancerName']
            ip = lb['DNSName']
            for listener in lb['ListenerDescriptions']:
                protocol = listener['Listener']['Protocol']
                ports.append(str(listener['Listener']['LoadBalancerPort']))
            ports = '+'.join(ports)
            target = ''
            results.append([name, ip, protocol, ports, target])
        return results

    def create_bucket(self, bucket, public=False):
        s3 = self.s3
        if bucket in self.list_buckets():
            error(f"Bucket {bucket} already there")
            return
        location = {'LocationConstraint': self.region}
        args = {'Bucket': bucket, "CreateBucketConfiguration": location}
        if public:
            args['ACL'] = 'public-read'
        s3.create_bucket(**args)

    def delete_bucket(self, bucket):
        s3 = self.s3
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return
        for obj in s3.list_objects(Bucket=bucket)['Contents']:
            key = obj['Key']
            pprint(f"Deleting object {key} from bucket {bucket}")
            s3.delete_object(Bucket=bucket, Key=key)
        s3.delete_bucket(Bucket=bucket)

    def delete_from_bucket(self, bucket, path):
        s3 = self.s3
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return
        s3.delete_object(Bucket=bucket, Key=path)

    def download_from_bucket(self, bucket, path):
        s3 = self.s3
        s3.download_file(bucket, path, path)

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        if not os.path.exists(path):
            error(f"Invalid path {path}")
            return
        if bucket not in self.list_buckets():
            error(f"Bucket {bucket} doesn't exist")
            return
        ExtraArgs = {'Metadata': overrides} if overrides else {}
        if public:
            ExtraArgs['ACL'] = 'public-read'
        dest = os.path.basename(path)
        s3 = self.s3
        with open(path, "rb") as f:
            s3.upload_fileobj(f, bucket, dest, ExtraArgs=ExtraArgs)
        if temp_url:
            expiration = 600
            return s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': dest}, ExpiresIn=expiration)

    def list_buckets(self):
        s3 = self.s3
        response = s3.list_buckets()
        return [bucket["Name"] for bucket in response['Buckets']]

    def list_bucketfiles(self, bucket):
        s3 = self.s3
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return []
        return [obj['Key'] for obj in s3.list_objects(Bucket=bucket)['Contents']]

    def public_bucketfile_url(self, bucket, path):
        return f"https://{bucket}.s3.{self.region}.amazonaws.com/{path}"

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        vpcid = None
        vpcs = self.conn.describe_vpcs()
        if network is not None:
            vpcid = self.get_vpc_id(vpcs, network) if not network.startswith('vpc-') else network
        else:
            vpcid = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']][0]
        if vpcid is None:
            error("Couldn't find vpcid")
            sys.exit(1)
        results = []
        conn = self.conn
        for sg in conn.describe_security_groups()['SecurityGroups']:
            if vpcid is not None and sg['VpcId'] != vpcid:
                continue
            results.append(sg['GroupName'])
        return results

    def create_security_group(self, name, overrides={}):
        ports = overrides.get('ports', [])
        defaultsubnetid = None
        vpcs = self.conn.describe_vpcs()
        subnets = self.conn.describe_subnets()
        network = overrides.get('network', 'default')
        if network in [subnet['SubnetId'] for subnet in subnets['Subnets']]:
            vpcid = [subnet['VpcId'] for subnet in subnets['Subnets'] if subnet['SubnetId'] == network][0]
        elif network == 'default':
            if defaultsubnetid is not None:
                network = defaultsubnetid
            else:
                vpcid = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']][0]
                subnetid = [subnet['SubnetId'] for subnet in subnets['Subnets']
                            if subnet['DefaultForAz'] and subnet['VpcId'] == vpcid][0]
                network = subnetid
                defaultsubnetid = network
                pprint(f"Using subnet {defaultsubnetid} as default")
        else:
            vpcid = self.get_vpc_id(vpcs, network) if not network .startswith('vpc-') else network
            if vpcid is None:
                error(f"Couldn't find vpc {network}")
                sys.exit(1)
        sg = self.resource.create_security_group(GroupName=name, Description=name, VpcId=vpcid)
        sgtags = [{"Key": "Name", "Value": name}]
        sg.create_tags(Tags=sgtags)
        sgid = sg.id
        sg.authorize_ingress(GroupId=sgid, FromPort=-1, ToPort=-1, IpProtocol='icmp',
                             CidrIp="0.0.0.0/0")
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
            sg.authorize_ingress(GroupId=sgid, FromPort=int(fromport), ToPort=int(toport), IpProtocol=protocol,
                                 CidrIp="0.0.0.0/0")
        return {'result': 'success'}

    def delete_security_group(self, name):
        self.conn.delete_security_group(GroupName=name)
        return {'result': 'success'}
