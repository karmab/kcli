#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base64 import b64encode
from ipaddress import ip_network
from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import IMAGES, METADATA_FIELDS
import boto3
import os
import sys
from socket import gethostbyname
from string import ascii_lowercase
from tempfile import TemporaryDirectory
from time import sleep
import webbrowser
from yaml import safe_load

staticf = {'t2.nano': {'cpus': 1, 'memory': 512}, 't2.micro': {'cpus': 1, 'memory': 1024},
           't2.small': {'cpus': 1, 'memory': 2048}, 't2.medium': {'cpus': 2, 'memory': 4096},
           't2.large': {'cpus': 2, 'memory': 8144}, 't2.xlarge': {'cpus': 2, 'memory': 16384},
           'm5.large': {'cpus': 2, 'memory': 8144}, 'm5.xlarge': {'cpus': 4, 'memory': 16384},
           'm5.2xlarge': {'cpus': 8, 'memory': 32768}, 'm5.4xlarge': {'cpus': 16, 'memory': 65536}
           }


def tag_name(obj):
    for tag in obj.get('Tags', []):
        if tag['Key'] == 'Name':
            return tag['Value']
    return ''


def figure_image(image):
    if image == 'centos8stream':
        return 'CentOS Stream 8 x86_64'
    elif image == 'centos9stream':
        return 'CentOS Stream 9 x86_64 20230807'
    elif 'debian' in image:
        return 'Debian 12-prod-p3klrdq5ydktc'
    elif image == 'ubuntu2210':
        return 'Ubuntu 22.04'
    elif image == 'ubuntu2304':
        return 'Ubuntu 23.04 -873b1a26-f96b-4b0c-bf2c-3c8d8f2c8157'
    elif image == 'rhel7':
        return 'RHEL-7.9_HVM_GA-20200917-x86_64-0-Access2-GP2'
    elif image == 'rhel8':
        return 'RHEL-8.8.0_HVM-20230623-x86_64-3-Hourly2-GP2'
    elif image == 'rhel9':
        return 'RHEL-9.2.0_HVM-20230726-x86_64-61-Hourly2-GP2'


class Kaws(object):
    """

    """
    def __init__(self, access_key_id=None, access_key_secret=None, debug=False,
                 region='eu-west-3', keypair=None, session_token=None, zone=None):
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
        self.iconnect = boto3.client('ec2-instance-connect', aws_access_key_id=access_key_id,
                                     aws_secret_access_key=access_key_secret, region_name=region,
                                     aws_session_token=session_token)
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = region
        self.zone = zone
        self.keypair = keypair
        return

    def close(self):
        return

    def exists(self, name):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        image = self.__evaluate_image(image)
        keypair = self.keypair
        if image is None:
            return {'result': 'failure', 'reason': 'An image (or amid) is required'}
        else:
            if image in IMAGES:
                _filter = 'name'
                images = [f'{figure_image(image)}*']
                Filters = [{'Name': _filter, 'Values': images}, {'Name': 'architecture', 'Values': ['x86_64']}]
            else:
                _filter = 'image-id' if image.startswith('ami-') else 'name'
                Filters = [{'Name': _filter, 'Values': [image]}]
            images = conn.describe_images(Filters=Filters)
            if 'Images' in images and images['Images']:
                minimal_disksize = images['Images'][0]['BlockDeviceMappings'][0]['Ebs']['VolumeSize']
                imageinfo = images['Images'][0]
                imageid = imageinfo['ImageId']
                if _filter == 'name':
                    pprint(f"Using ami {imageid}")
                image = imageinfo['Name']
            else:
                return {'result': 'failure', 'reason': f'Invalid image {image}'}
        defaultsubnetid = None
        az = overrides.get('az') or overrides.get('availability_zone') or overrides.get('zone') or self.zone
        if az is not None and not az.startswith(self.region):
            return {'result': 'failure', 'reason': f'Invalid az {az}'}
        if flavor is None:
            matching = [f for f in staticf if staticf[f]['cpus'] >= numcpus and staticf[f]['memory'] >= memory]
            if matching:
                flavor = matching[0]
                pprint(f"Using instance type {flavor}")
            else:
                return {'result': 'failure', 'reason': 'Couldnt find instance type matching requirements'}
        # elif flavor not in [f[0] for f in self.list_flavors()]:
        #    return {'result': 'failure', 'reason': f'Invalid instance type {flavor}'}
        vmtags = [{'ResourceType': 'instance',
                   'Tags': [{'Key': 'Name', 'Value': name}, {'Key': 'hostname', 'Value': name}]}]
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            vmtags[0]['Tags'].append({'Key': entry, 'Value': metadata[entry]})
        if 'kubetype' in metadata and metadata['kubetype'] == "openshift":
            vmtags[0]['Tags'].append({'Key': f'kubernetes.io/cluster/{metadata["kube"]}', 'Value': 'owned'})
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
        networkinterfaces = []
        blockdevicemappings = []
        privateips = []
        vpcs = conn.describe_vpcs()
        subnets = conn.describe_subnets()['Subnets']
        subnet_azs = []
        for index, net in enumerate(nets):
            netpublic = overrides.get('public', True)
            networkinterface = {'DeleteOnTermination': True, 'Description': f"eth{index}", 'DeviceIndex': index}
            ip = None
            if isinstance(net, str):
                netname = net
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                ip = net.get('ip')
                alias = net.get('alias')
                netpublic = net.get('public') or netpublic
            matching_subnets = [sub for sub in subnets if sub['SubnetId'] == netname or tag_name(sub) == netname]
            if matching_subnets:
                subnet_az = matching_subnets[0]['AvailabilityZone']
                subnet_azs.append(subnet_az)
                vpc_id = matching_subnets[0]['VpcId']
                netname = matching_subnets[0]['SubnetId']
            elif netname == 'default':
                if defaultsubnetid is not None:
                    netname = defaultsubnetid
                else:
                    vpc_ids = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']]
                    if not vpc_ids:
                        return {'result': 'failure', 'reason': "Couldn't find default vpc"}
                    vpc_id = vpc_ids[0]
                    default_subnets = [sub for sub in subnets if sub['DefaultForAz'] and sub['VpcId'] == vpc_id]
                    if az is None:
                        default_subnet = default_subnets[0]
                    else:
                        az_subnets = [sub for sub in default_subnets if sub['AvailabilityZone'] == az]
                        if not az_subnets:
                            return {'result': 'failure', 'reason': "Couldn't find default subnet in specified AZ"}
                        else:
                            default_subnet = az_subnets[0]
                    subnetid = default_subnet['SubnetId']
                    subnet_az = default_subnet['AvailabilityZone']
                    subnet_azs.append(subnet_az)
                    netname = subnetid
                    defaultsubnetid = netname
                    pprint(f"Using subnet {defaultsubnetid} as default")
            else:
                vpc_id = self.get_vpc_id(netname, vpcs) if not netname.startswith('vpc-') else netname
                if vpc_id is None:
                    return {'result': 'failure', 'reason': f"Couldn't find vpc {netname}"}
                vpc_subnets = [sub for sub in subnets if sub['VpcId'] == vpc_id]
                if az is not None:
                    vpc_subnets = [sub for sub in vpc_subnets if sub['AvailabilityZone'] == az]
                if vpc_subnets:
                    subnet = vpc_subnets[0]
                    netname = subnet['SubnetId']
                    subnet_name = tag_name(subnet)
                    if subnet_name != '':
                        pprint(f"Using subnet {subnet_name}")
                    else:
                        pprint(f"Using subnet {netname}")
                    subnet_az = subnet['AvailabilityZone']
                    subnet_azs.append(subnet_az)
                else:
                    return {'result': 'failure', 'reason': f"Couldn't find valid subnet for vpc {netname}"}
            if az is not None and subnet_az != az:
                return {'result': 'failure', 'reason': f"Selected subnet doesnt belong to AZ {az}"}
            if ips and len(ips) > index and ips[index] is not None:
                ip = ips[index]
                if index == 0:
                    networkinterface['PrivateIpAddress'] = ip
                    privateip = {'Primary': True, 'PrivateIpAddress': ip}
                else:
                    privateip = {'Primary': False, 'PrivateIpAddress': ip}
                privateips.append(privateip)
            networkinterface['SubnetId'] = netname
            all_subnets = self.list_subnets()
            current_subnet = [all_subnets[s] for s in all_subnets if all_subnets[s]['id'] == netname][0]
            if ':' in current_subnet['cidr']:
                networkinterface['Ipv6AddressCount'] = 1
            if index == 0:
                if netpublic:
                    if len(nets) > 1:
                        warning("Disabling netpublic as vm has multiple nics")
                        netpublic = False
                    elif current_subnet['private']:
                        warning(f"Disabling netpublic as {netname} is private")
                        netpublic = False
                networkinterface['AssociatePublicIpAddress'] = netpublic
                SecurityGroupIds = []
                for sg in securitygroups:
                    sg_id = self.get_security_group_id(sg, vpc_id)
                    if sg_id is not None:
                        SecurityGroupIds.append(sg_id)
                if 'kubetype' in metadata and metadata['kubetype'] == "openshift":
                    kube = metadata['kube']
                    pprint(f"Adding vm to security group {kube}")
                    kube_sg_id = self.get_security_group_id(kube, vpc_id)
                    if kube_sg_id is None:
                        sg = self.resource.create_security_group(GroupName=kube, Description=kube, VpcId=vpc_id)
                        sgtags = [{"Key": "Name", "Value": kube}]
                        sg.create_tags(Tags=sgtags)
                        kube_sg_id = sg.id
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=-1, ToPort=-1, IpProtocol='icmp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=22, ToPort=22, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=80, ToPort=80, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=8080, ToPort=8080, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=5443, ToPort=5443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=8443, ToPort=8443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=443, ToPort=443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=6443, ToPort=6443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=22624, ToPort=22624, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=2379, ToPort=2380, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=30000, ToPort=32767, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=30000, ToPort=32767, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=10250, ToPort=10259, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=9000, ToPort=9999, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=9000, ToPort=9999, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=4789, ToPort=4789, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=4789, ToPort=4789, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=6081, ToPort=6081, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=6081, ToPort=6081, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                    SecurityGroupIds.append(kube_sg_id)
                elif 'kubetype' in metadata and metadata['kubetype'] == "generic":
                    kube = metadata['kube']
                    pprint(f"Adding vm to security group {kube}")
                    kube_sg_id = self.get_security_group_id(kube, vpc_id)
                    if kube_sg_id is None:
                        sg = self.resource.create_security_group(GroupName=kube, Description=kube, VpcId=vpc_id)
                        sgtags = [{"Key": "Name", "Value": kube}]
                        sg.create_tags(Tags=sgtags)
                        kube_sg_id = sg.id
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=-1, ToPort=-1, IpProtocol='icmp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=22, ToPort=22, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=6443, ToPort=6443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=2379, ToPort=2380, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupId=kube_sg_id, FromPort=2380, ToPort=2380, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                    SecurityGroupIds.append(kube_sg_id)
                networkinterface['Groups'] = SecurityGroupIds
            networkinterfaces.append(networkinterface)
        if len(list(dict.fromkeys(subnet_azs))) > 1:
            return {'result': 'failure', 'reason': "Subnets of multinic instance need to belong to a single AZ"}
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
                if index == 0 and disksize < minimal_disksize:
                    disksize = minimal_disksize
                blockdevicemapping['Ebs']['VolumeType'] = disk.get('type', 'standard')
            blockdevicemapping['Ebs']['VolumeSize'] = disksize
            blockdevicemappings.append(blockdevicemapping)
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
                if sys.getsizeof(userdata) > 16000:
                    warning("Storing cloudinit data in s3 as it's over 16k")
                    self.create_bucket(name)
                    with TemporaryDirectory() as tmpdir:
                        with open(f"{tmpdir}/cloudinit", 'w') as f:
                            f.write(userdata)
                        self.upload_to_bucket(name, f'{tmpdir}/cloudinit', public=True)
                    bucket_url = self.public_bucketfile_url(name, 'cloudinit')
                    userdata = '#!/bin/bash\ntest -f /etc/cloud/cloud.cfg.d/99-manual.cfg && exit 0\n'
                    userdata += f'curl -Lk {bucket_url} -o /etc/cloud/cloud.cfg.d/99-manual.cfg\n'
                    userdata += 'cloud-init clean --logs\nreboot'
        else:
            userdata = ''
        if (overrides.get('spot', False) or
                (overrides.get('spot_ctlplanes', False) and 'ctlplane' in name) or
                (overrides.get('spot_workers', False) and 'worker' in name)):
            userdata_encode = (b64encode(userdata.encode())).decode("utf-8")
            LaunchSpecification = {'SecurityGroups': SecurityGroupIds,
                                   'ImageId': imageid,
                                   'InstanceType': flavor,
                                   'KeyName': keypair,
                                   'BlockDeviceMappings': blockdevicemappings,
                                   'UserData': userdata_encode,
                                   'NetworkInterfaces': networkinterfaces}
            result = conn.request_spot_instances(InstanceCount=1, Type='one-time',
                                                 InstanceInterruptionBehavior='terminate',
                                                 LaunchSpecification=LaunchSpecification)
            requestid = result['SpotInstanceRequests'][0]['SpotInstanceRequestId']
            sleep(10)
            timeout = 0
            while True:
                spot_data = conn.describe_spot_instance_requests(SpotInstanceRequestIds=[requestid])
                instance_data = spot_data['SpotInstanceRequests'][0]
                if 'InstanceId' in instance_data:
                    instanceid = instance_data['InstanceId']
                    conn.create_tags(Resources=[instanceid], Tags=[{'Key': 'Name', 'Value': name}])
                    break
                elif timeout > 60:
                    warning("Timeout waiting for instanceid associated to spot request to show up")
                    break
                else:
                    pprint("Waiting for instanceid associated to spot request to show up")
                    sleep(5)
        else:
            data = {'ImageId': imageid, 'MinCount': 1, 'MaxCount': 1, 'InstanceType': flavor,
                    'KeyName': keypair, 'BlockDeviceMappings': blockdevicemappings,
                    'NetworkInterfaces': networkinterfaces, 'UserData': userdata,
                    'TagSpecifications': vmtags}
            if az is not None:
                data['Placement'] = {'AvailabilityZone': az}
            response = conn.run_instances(**data)
            instance_id = response['Instances'][0]['InstanceId']
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name)
        if 'kubetype' in metadata and metadata['kubetype'] == "openshift":
            cluster = metadata['kube']
            iam_role = cluster
            instance_profiles = self.list_instance_profiles()
            if cluster not in instance_profiles:
                if iam_role not in self.list_roles():
                    self.create_role(iam_role)
                self.create_instance_profile(cluster, iam_role)
                sleep(15)
            arn = self.get_instance_profile(cluster)['Arn']
            while True:
                current_status = self.status(name)
                if current_status == 'running':
                    break
                pprint(f"Waiting for vm {name} to be running to associate instance profile")
                sleep(5)
            conn.associate_iam_instance_profile(IamInstanceProfile={'Name': cluster, 'Arn': arn},
                                                InstanceId=instance_id)
        if overrides.get('SourceDestCheck', False) or overrides.get('router', False):
            conn.modify_instance_attribute(InstanceId=instance_id, Attribute='sourceDestCheck', Value='false',
                                           DryRun=False)
        if 'loadbalancer' in overrides:
            lb = overrides['loadbalancer']
            self.update_metadata(name, 'loadbalancer', lb, append=True)
            self.add_vm_to_loadbalancer(name, lb, vpc_id)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        conn.start_instances(InstanceIds=[instanceid])
        return {'result': 'success'}

    def stop(self, name, soft=False):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        instanceid = vm['InstanceId']
        conn.start_instances(InstanceIds=[instanceid])
        return {'result': 'success'}

    def info_host(self):
        return {"region": self.region, 'vms': len(self.list())}

    def status(self, name):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = self.conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return
        instanceid = vm['InstanceId']
        machinetype = vm['InstanceType']
        flavor = conn.describe_instance_types(InstanceTypes=[machinetype])['InstanceTypes'][0]
        processor_info = flavor.get('ProcessorInfo', {}).get('SupportedArchitectures', [])
        hypervisor = flavor.get('Hypervisor', '')
        if processor_info == ['x86_64'] and hypervisor == 'nitro':
            publickeyfile = get_ssh_pub_key()
            publickeyfile = open(publickeyfile).read()
            self.iconnect.send_serial_console_ssh_public_key(InstanceId=instanceid, SerialPort=0,
                                                             SSHPublicKey=publickeyfile)
            sshcommand = f'ssh {instanceid}.port0@serial-console.ec2-instance-connect.{self.region}.aws'
            code = os.WEXITSTATUS(os.system(sshcommand))
            sys.exit(code)
        else:
            warning(f"Instance Type {machinetype} of vm {name} doesnt support serial console, only printing output")
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return None
        return vm['InstanceId']

    def get_nic_id(self, name):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return None
        return vm['NetworkInterfaces'][0]['NetworkInterfaceId']

    def get_security_groups(self, name):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return []
        return vm['SecurityGroups']

    def get_security_group_id(self, name, vpc_id):
        conn = self.conn
        for sg in conn.describe_security_groups()['SecurityGroups']:
            group_name = sg['GroupName']
            group_id = sg['GroupId']
            group_tag = sg['GroupId']
            group_name = ''
            for tag in sg.get('Tags', []):
                if tag['Key'] == 'Name':
                    group_name = tag['Value']
                    break
            if sg['VpcId'] == vpc_id and (group_name == name or group_id == name or group_tag == name):
                return sg['GroupId']
        return None

    def get_default_security_group_id(self, vpc_id):
        conn = self.conn
        for sg in conn.describe_security_groups()['SecurityGroups']:
            if sg['VpcId'] == vpc_id and (sg['GroupName'] == 'default'):
                return sg['GroupId']

    def get_vpc_id(self, name, vpcs=None):
        if vpcs is None:
            vpcs = self.conn.describe_vpcs()
        vpc_id = None
        for vpc in vpcs['Vpcs']:
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name' and tag['Value'] == name:
                        vpc_id = vpc['VpcId']
                        break
        return vpc_id

    def info(self, name, vm=None, debug=False):
        yamlinfo = {}
        conn = self.conn
        resource = self.resource
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        if vm is None:
            try:
                vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
            except:
                error(f"VM {name} not found")
                return {}
        instanceid = vm['InstanceId']
        name = instanceid
        state = vm['State']['Name']
        amid = vm['ImageId']
        az = vm['Placement']['AvailabilityZone']
        yamlinfo['vpcid'] = vm.get('VpcId', 'N/A')
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
        machinetype = vm['InstanceType']
        flavor = conn.describe_instance_types(InstanceTypes=[machinetype])['InstanceTypes'][0]
        yamlinfo['cpus'] = flavor['VCpuInfo']['DefaultVCpus']
        yamlinfo['memory'] = flavor['MemoryInfo']['SizeInMiB']
        yamlinfo['flavor'] = machinetype
        yamlinfo['image'] = source
        yamlinfo['user'] = common.get_user(yamlinfo['image'])
        yamlinfo['instanceid'] = instanceid
        nets = []
        ips = []
        for index, interface in enumerate(vm['NetworkInterfaces']):
            subnetid = interface['SubnetId']
            subnet = self.info_subnet(subnetid)
            subnet_name = tag_name(subnet)
            if subnet_name != '':
                subnetid = subnet_name
            device = interface['Description']
            mac = interface['MacAddress']
            private_ip, private_ipv6 = None, None
            if interface['PrivateIpAddresses']:
                private_ip = interface['PrivateIpAddresses'][0]['PrivateIpAddress']
            if interface['Ipv6Addresses']:
                private_ipv6 = interface['Ipv6Addresses'][0]['Ipv6Address']
            net_ip = private_ip or private_ipv6
            nets.append({'device': device, 'mac': mac, 'net': subnetid, 'type': net_ip})
            if index == 0:
                yamlinfo['private_ip'] = private_ip or private_ipv6
            if private_ip is not None:
                ips.append(private_ip)
            if private_ipv6 is not None:
                ips.append(private_ipv6)
        if nets:
            yamlinfo['nets'] = sorted(nets, key=lambda x: x['device'])
        if 'PublicIpAddress' in vm:
            yamlinfo['ip'] = vm.get('PublicIpAddress')
        elif ips:
            ip4s = [i for i in ips if ':' not in i]
            ip6s = [i for i in ips if i not in ip4s]
            yamlinfo['ip'] = ip4s[0] if ip4s else ip6s[0]
        if len(ips) > 1:
            yamlinfo['ips'] = ips
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
            yamlinfo['disks'] = sorted(disks, key=lambda x: x['device'])
        if 'SecurityGroups' in vm:
            yamlinfo['sgs'] = [s['GroupName'] for s in vm.get('SecurityGroups')]
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def get_vpcid_of_vm(self, name):
        vcp_id = None
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return {}
        for interface in vm['NetworkInterfaces']:
            vpc_id = interface['VpcId']
            return vpc_id
        return vcp_id

    def ip(self, name):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        return vm.get('PublicIpAddress')

    def internalip(self, name):
        ip = None
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        oses = ['CentOS Stream*', 'CentOS Linux 8*', 'RHEL-7*', 'RHEL-8.*', 'RHEL-9.*', 'Debian*', 'Ubuntu*']
        Filters = [{'Name': 'name', 'Values': oses},
                   {'Name': 'architecture', 'Values': ['x86_64']},
                   {'Name': 'is-public', 'Values': ['true']}]
        allimages = conn.describe_images(Filters=Filters)
        for image in allimages['Images']:
            name = image['Name']
            _id = image['ImageId']
            if 'beta' in name.lower():
                continue
            else:
                images.append(f"{name} - {_id}")
        return sorted(images, key=str.lower)

    def delete(self, name, snapshots=False):
        conn = self.conn
        dnsclient, domain = None, None
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if vm['State']['Name'] == 'terminated':
            warning(f"VM {name} already deleted")
            return {'result': 'success', 'reason': f"VM {name} already deleted"}
        instance_id = vm['InstanceId']
        kubetype = None
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == 'domain':
                    domain = tag['Value']
                if tag['Key'] == 'dnsclient':
                    dnsclient = tag['Value']
                if tag['Key'] == 'kubetype':
                    kubetype = tag['Value']
            if kubetype is not None and kubetype == 'openshift':
                vpc_id = vm['NetworkInterfaces'][0]['VpcId']
                default_sgid = self.get_default_security_group_id(vpc_id)
                nic_id = self.get_nic_id(name)
                conn.modify_network_interface_attribute(NetworkInterfaceId=nic_id, Groups=[default_sgid])
        vm = conn.terminate_instances(InstanceIds=[instance_id])
        if domain is not None and dnsclient is None:
            self.delete_dns(name, domain, name)
        if name in self.list_buckets():
            self.delete_bucket(name)
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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
                 interface='virtio', novm=False, overrides={}, diskname=None):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
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

    def add_nic(self, name, network, model='virtio'):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        index = len(vm['NetworkInterfaces'])
        az = vm['Placement']['AvailabilityZone']
        vpc_id = vm['VpcId']
        vpcs = conn.describe_vpcs()['Vpcs']
        subnets = conn.describe_subnets()['Subnets']
        matching_subnets = [sub for sub in subnets if sub['SubnetId'] == network or tag_name(sub) == network]
        if matching_subnets:
            subnet_az = matching_subnets[0]['AvailabilityZone']
            if subnet_az != az:
                msg = "Couldn't find valid subnet in specified AZ"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            subnet_vpc_id = matching_subnets[0]['VpcId']
            if subnet_vpc_id != vpc_id:
                msg = "Couldn't find valid subnet in VPC"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            netname = matching_subnets[0]['SubnetId']
        elif network == 'default':
            default_subnets = [sub for sub in subnets if sub['DefaultForAz'] and sub['VpcId'] == vpc_id]
            az_subnets = [sub for sub in default_subnets if sub['AvailabilityZone'] == az]
            if not az_subnets:
                msg = "Couldn't find default subnet in specified AZ"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            else:
                default_subnet = az_subnets[0]
            subnet_id = default_subnet['SubnetId']
            subnet_az = default_subnet['AvailabilityZone']
            netname = subnet_id
            pprint(f"Using subnet {netname} as default")
        else:
            vpc_id = self.get_vpc_id(network, vpcs) if not network.startswith('vpc-') else network
            if vpc_id is None:
                msg = f"Couldn't find vpc {network}"
                error(msg)
                return {'result': 'failure', 'reason': msg}
            vpc_subnets = [sub for sub in subnets if sub['VpcId'] == vpc_id]
            vpc_subnets = [sub for sub in vpc_subnets if sub['AvailabilityZone'] == az]
            if vpc_subnets:
                subnet = vpc_subnets[0]
                netname = subnet['SubnetId']
                subnet_name = tag_name(subnet)
                if subnet_name != '':
                    pprint(f"Using subnet {subnet_name}")
                else:
                    pprint(f"Using subnet {netname}")
            else:
                msg = f"Couldn't find valid subnet for vpc {netname}"
                error(msg)
                return {'result': 'failure', 'reason': msg}
        networkinterface = {'SubnetId': netname, 'Description': f'eth{index}'}
        nic = conn.create_network_interface(**networkinterface)
        nic_id = nic['NetworkInterface']['NetworkInterfaceId']
        instance_id = vm['InstanceId']
        conn.attach_network_interface(DeviceIndex=index, InstanceId=instance_id, NetworkInterfaceId=nic_id)
        return {'result': 'success'}

    def delete_nic(self, name, interface):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        for entry in vm['NetworkInterfaces']:
            attachment = entry['Attachment']
            if interface in [entry['Description'], f"eth{attachment['DeviceIndex']}"]:
                network_interface_id = entry['NetworkInterfaceId']
                attachment_id = entry['Attachment']['AttachmentId']
                conn.detach_network_interface(AttachmentId=attachment_id)
                waiter = conn.get_waiter('network_interface_available')
                waiter.wait(NetworkInterfaceIds=[network_interface_id])
                conn.delete_network_interface(NetworkInterfaceId=network_interface_id)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': f"Nic {interface} not found in {name}"}

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

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        ipv6 = False
        conn = self.conn
        networks = self.list_networks()
        if name in networks:
            msg = f"Network {name} already exists"
            return {'result': 'failure', 'reason': msg}
        if cidr is not None:
            try:
                network = ip_network(cidr, strict=False)
            except:
                return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
            if str(network.version) == "6":
                msg = 'Primary cidr needs to be ipv4 in AWS. Set ipv6 to true to enable it'
                return {'result': 'failure', 'reason': msg}
        subnet_cidr = overrides.get('subnet_cidr')
        if subnet_cidr is not None:
            try:
                subnet = ip_network(subnet_cidr, strict=False)
            except:
                return {'result': 'failure', 'reason': f"Invalid Cidr {subnet_cidr}"}
            if not subnet.subnet_of(network):
                return {'result': 'failure', 'reason': f"{subnet_cidr} isnt part of {cidr}"}
        default = 'default' in overrides and overrides['default']
        Tags = [{"Key": "Name", "Value": name}, {"Key": "Plan", "Value": plan}]
        vpcargs = {"CidrBlock": cidr}
        if 'dual_cidr' in overrides:
            if 'ipv6_pool' in overrides:
                vpcargs["Ipv6Pool"] = overrides['ipv6_pool']
                vpcargs["Ipv6CidrBlock"] = overrides['dual_cidr']
            else:
                warning("Using AmazonProvidedIpv6CidrBlock since ipv6_pool wasnt specified")
                overrides['ipv6'] = True
        if 'ipv6' in overrides and overrides['ipv6']:
            vpcargs["AmazonProvidedIpv6CidrBlock"] = True
            ipv6 = True
        if default:
            networks = self.list_networks()
            default_network = [n for n in networks if networks[n]['mode'] == 'default']
            if default_network:
                msg = f"network {default_network[0]} is already default"
                return {'result': 'failure', 'reason': msg}
            vpc = conn.create_default_vpc(**vpcargs)
            vpc_id = vpc['Vpc']['VpcId']
            conn.create_tags(Resources=[vpc_id], Tags=Tags)
            return {'result': 'success'}
        vpc = conn.create_vpc(**vpcargs)
        vpc_id = vpc['Vpc']['VpcId']
        conn.create_tags(Resources=[vpc_id], Tags=Tags)
        conn.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
        gateway = conn.create_internet_gateway()
        gateway_id = gateway['InternetGateway']['InternetGatewayId']
        gateway = self.resource.InternetGateway(gateway_id)
        gateway.attach_to_vpc(VpcId=vpc_id)
        conn.create_tags(Resources=[gateway_id], Tags=Tags)
        pprint(f"Creating first subnet {name}-subnet1 as public")
        vpcargs['VpcId'] = vpc_id
        vpcargs['CidrBlock'] = subnet_cidr or cidr
        if 'AmazonProvidedIpv6CidrBlock' in vpcargs:
            del vpcargs['AmazonProvidedIpv6CidrBlock']
        subnet = conn.create_subnet(**vpcargs)
        subnet_id = subnet['Subnet']['SubnetId']
        subnet_tags = [{"Key": "Name", "Value": f"{name}-subnet1"}, {"Key": "Plan", "Value": plan},
                       {"Key": "kubernetes.io/role/elb", "Value": '1'}]
        conn.create_tags(Resources=[subnet_id], Tags=subnet_tags)
        response = conn.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        route_table_id = response['RouteTables'][0]['RouteTableId']
        data = {'DestinationCidrBlock': '0.0.0.0/0', 'RouteTableId': route_table_id, 'GatewayId': gateway_id}
        conn.create_route(**data)
        conn.create_tags(Resources=[route_table_id], Tags=subnet_tags)
        response = conn.allocate_address(Domain='vpc')
        allocation_id = response['AllocationId']
        conn.create_tags(Resources=[allocation_id], Tags=Tags)
        nat_gateway = conn.create_nat_gateway(SubnetId=subnet_id, AllocationId=allocation_id)
        nat_gateway_id = nat_gateway['NatGateway']['NatGatewayId']
        waiter = conn.get_waiter('nat_gateway_available')
        waiter.wait(NatGatewayIds=[nat_gateway_id])
        conn.create_tags(Resources=[nat_gateway_id], Tags=Tags)
        response = conn.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        sgid = response['SecurityGroups'][0]['GroupId']
        conn.authorize_security_group_ingress(CidrIp='0.0.0.0/0', GroupId=sgid, IpProtocol='-1',
                                              FromPort=0, ToPort=65535)
        if ipv6:
            Filters = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
            vpcs = conn.describe_vpcs(Filters=Filters)['Vpcs']
            ipv6_cidr = vpcs[0]['Ipv6CidrBlockAssociationSet'][0]['Ipv6CidrBlock']
            pprint(f"Using {ipv6_cidr} as IPV6 main cidr")
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        conn = self.conn
        vpc_id = None
        Filters = [{'Name': 'vpc-id', 'Values': [name]}]
        vpcs = conn.describe_vpcs(Filters=Filters)['Vpcs']
        if vpcs:
            vpc_id = vpcs[0]['VpcId']
        else:
            Filters = [{'Name': "tag:Name", 'Values': [name]}]
            vpcs = conn.describe_vpcs(Filters=Filters)['Vpcs']
            if vpcs:
                vpc_id = vpcs[0]['VpcId']
        if vpc_id is None:
            return {'result': 'failure', 'reason': f"Network {name} not found"}
        Filters = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
        for nat_gateway in conn.describe_nat_gateways()['NatGateways']:
            if nat_gateway['VpcId'] == vpc_id:
                nat_gateway_id = nat_gateway['NatGatewayId']
                nat_gateway_tag_name = tag_name(nat_gateway)
                nat_gateway_name = nat_gateway_tag_name if nat_gateway_tag_name != '' else nat_gateway_id
                pprint(f"Deleting nat_gateway {nat_gateway_name}")
                conn.delete_nat_gateway(NatGatewayId=nat_gateway_id)
                waiter = conn.get_waiter('nat_gateway_deleted')
                waiter.wait(NatGatewayIds=[nat_gateway_id])
        subnets = conn.describe_subnets(Filters=Filters)
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            subnet_tag_name = tag_name(subnet)
            subnet_name = subnet_tag_name if subnet_tag_name != '' else subnet_id
            pprint(f"Deleting subnet {subnet_name}")
            tables = conn.describe_route_tables(Filters=[{'Name': 'tag:Name', 'Values': [subnet_name]}])['RouteTables']
            conn.delete_subnet(SubnetId=subnet_id)
            if tables:
                main = False
                route_table = tables[0]
                for association in route_table['Associations']:
                    if association['Main']:
                        main = True
                        break
                if not main:
                    route_table_id = route_table['RouteTableId']
                    conn.delete_route_table(RouteTableId=route_table_id)
        for address in conn.describe_addresses()['Addresses']:
            if tag_name(address) == name:
                allocation_id = address['AllocationId']
                pprint(f"Deleting address {name}")
                conn.release_address(AllocationId=allocation_id)
        for gateway in conn.describe_internet_gateways()['InternetGateways']:
            attachments = gateway['Attachments']
            for attachment in attachments:
                if attachment['VpcId'] == vpc_id:
                    gateway_id = gateway['InternetGatewayId']
                    gateway = self.resource.InternetGateway(gateway_id)
                    gateway.detach_from_vpc(VpcId=vpc_id)
                    pprint(f"Deleting internet gateway {gateway_id}")
                    gateway.delete()
        conn.delete_vpc(VpcId=vpc_id)
        return {'result': 'success'}

    def list_pools(self):
        print("not implemented")
        return []

    def list_networks(self):
        conn = self.conn
        networks = {}
        vpcs = conn.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            if self.debug:
                print(vpc)
            plan = None
            vpc_id = vpc['VpcId']
            networkname = vpc_id
            cidr = vpc['CidrBlock']
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name':
                        networkname = tag['Value']
                    if tag['Key'] == 'Plan':
                        plan = tag['Value']
            mode = 'default' if vpc['IsDefault'] else 'N/A'
            dhcp = vpc['DhcpOptionsId']
            networks[networkname] = {'cidr': cidr, 'dhcp': dhcp, 'domain': vpc_id, 'type': 'routed', 'mode': mode}
            if plan is not None:
                networks[networkname]['plan'] = plan
            ipv6_associations = vpc.get('Ipv6CidrBlockAssociationSet', [])
            if ipv6_associations:
                networks[networkname]['dual_cidr'] = ipv6_associations[0]['Ipv6CidrBlock']
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        return networkinfo

    def list_subnets(self):
        conn = self.conn
        results = {}
        private_subnets = []
        for route_table in conn.describe_route_tables()['RouteTables']:
            if [route for route in route_table['Routes'] if route.get('GatewayId') is not None and
                    route.get('GatewayId').startswith('igw')]:
                continue
            for association in (route_table['Associations']):
                if 'SubnetId' in association:
                    private_subnets.append(association['SubnetId'])
        vpcs = conn.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            networkname = vpc['VpcId']
            Filters = [{'Name': 'vpc-id', 'Values': [networkname]}]
            subnets = conn.describe_subnets(Filters=Filters)
            for subnet in subnets['Subnets']:
                subnet_id = subnet['SubnetId']
                if subnet.get('Ipv6CidrBlockAssociationSet', []):
                    cidr = subnet['Ipv6CidrBlockAssociationSet'][0]['Ipv6CidrBlock']
                else:
                    cidr = subnet['CidrBlock']
                az = subnet['AvailabilityZone']
                subnet_name = subnet_id
                for tag in subnet.get('Tags', []):
                    if tag['Key'] == 'Name':
                        subnet_name = tag['Value']
                        break
                private = subnet_id in private_subnets
                default = subnet['DefaultForAz']
                new_subnet = {'cidr': cidr, 'az': az, 'network': networkname, 'id': subnet_id, 'private': private,
                              'default': default}
                if self.debug:
                    print(subnet_name, new_subnet)
                results[subnet_name] = new_subnet
        return results

    def delete_pool(self, name, full=False):
        print("not implemented")
        return

    def network_ports(self, name):
        machines = []
        for reservation in self.conn.describe_instances()['Reservations']:
            for vm in reservation['Instances']:
                for interface in vm['NetworkInterfaces']:
                    subnet_id = interface['SubnetId']
                    subnet = self.info_subnet(subnet_id)
                    subnet_name = tag_name(subnet)
                    if subnet_name == name or subnet_id == name:
                        vm_name = vm['InstanceId']
                        vm_tag_name = tag_name(vm)
                        if vm_tag_name != '':
                            vm_name = vm_tag_name
                        machines.append(vm_name)
        return machines

    def vm_ports(self, name):
        networks = []
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return networks
        for interface in vm['NetworkInterfaces']:
            subnet_id = interface['SubnetId']
            subnet = self.info_subnet(subnet_id)
            subnet_name = tag_name(subnet)
            if subnet_name != '':
                subnet_id = subnet_name
            networks.append(subnet_id)
        return networks

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

    def delete_dns(self, name, domain, allentries=False):
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
        if entry.startswith('api-int'):
            entry = entry.replace('api-int-', 'api-int.')
        elif entry.startswith('api-'):
            entry = entry.replace('api-', 'api.')
        elif entry.startswith('apps-'):
            entry = entry.replace('apps-', 'apps.')
        recs = []
        clusterdomain = f"{cluster}.{domain}"
        for record in dns.list_resource_record_sets(HostedZoneId=zoneid)['ResourceRecordSets']:
            if entry in record['Name'] or ('ctlplane-0' in name and record['Name'].endswith(f"{clusterdomain}.")):
                recs.append(record)
            else:
                if 'ResourceRecords' in record:
                    for rrdata in record['ResourceRecords']:
                        if entry in rrdata['Value']:
                            recs.append(record)
        if recs:
            changes = [{'Action': 'DELETE', 'ResourceRecordSet': record} for record in recs]
            dns.change_resource_record_sets(HostedZoneId=zoneid, ChangeBatch={'Changes': changes})
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
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        InstanceId = vm['InstanceId']
        Name = image if image is not None else f"kcli {name}"
        Description = f"image based on {name}"
        conn.create_image(InstanceId=InstanceId, Name=Name, Description=Description, NoReboot=True)
        return {'result': 'success'}

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False, dnsclient=None, ip=None):
        vpc_id = None
        if not vms:
            error(f"Vms for loadbalancer {name} need to be specified")
            return
        for vm in vms:
            if not self.exists(vm):
                error(f"Vm {vm} not found")
                return
            if vpc_id is None:
                vm_info = self.info(vm)
                vpc_id = vm_info['vpcid']
        subnets = self.list_subnets()
        availability_zones = []
        lb_subnets = []
        for sub in subnets:
            az = subnets[sub]['az']
            if subnets[sub]['network'] == vpc_id and not subnets[sub]['private'] and az not in availability_zones:
                pprint(f"Adding subnet {sub} from AZ {az}")
                lb_subnets.append(subnets[sub]['id'])
                availability_zones.append(az)
        ports = [int(port) for port in ports]
        resource = self.resource
        elb = self.elb
        protocols = {}
        Listeners = []
        for port in ports:
            protocol = protocols[port] if port in protocols else 'TCP'
            Listener = {'Protocol': protocol, 'LoadBalancerPort': port, 'InstanceProtocol': protocol,
                        'InstancePort': port}
            Listeners.append(Listener)
        clean_name = name.replace('.', '-')
        sg_id = self.get_security_group_id(name, vpc_id)
        if sg_id is None:
            sg_data = {'GroupName': name, 'Description': name, 'VpcId': vpc_id}
            sg = resource.create_security_group(**sg_data)
            sgtags = [{"Key": "Name", "Value": name}]
            sg.create_tags(Tags=sgtags)
            sg_id = sg.id
            for port in list(set(ports + [checkport])):
                sg.authorize_ingress(GroupId=sg_id, FromPort=port, ToPort=port, IpProtocol='tcp', CidrIp="0.0.0.0/0")
        lbinfo = {"LoadBalancerName": clean_name, "Listeners": Listeners, "SecurityGroups": [sg_id],
                  'Subnets': lb_subnets}
        lbinfo['Scheme'] = 'internal' if internal else 'internet-facing'
        if domain is not None:
            lbinfo['Tags'] = [{"Key": "domain", "Value": domain}]
            if dnsclient is not None:
                lbinfo['Tags'].append({"Key": "dnsclient", "Value": dnsclient})
        lb = elb.create_load_balancer(**lbinfo)
        HealthTarget = f'{protocol}:{checkport}'
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
                instance_id = self.get_id(vm)
                if update == 0 and instance_id is not None:
                    Instances.append({"InstanceId": instance_id})
                sgs = self.get_security_groups(vm)
                sg_names = [x['GroupName'] for x in sgs]
                if name not in sg_names:
                    sg_ids = [x['GroupId'] for x in sgs]
                    sg_ids.append(sg_id)
                    nic_id = self.get_nic_id(vm)
                    self.conn.modify_network_interface_attribute(NetworkInterfaceId=nic_id, Groups=sg_ids)
            if Instances:
                elb.register_instances_with_load_balancer(LoadBalancerName=clean_name, Instances=Instances)
        if domain is not None:
            lb_dns_name = lb['DNSName']
            while True:
                try:
                    ip = gethostbyname(lb_dns_name)
                    break
                except:
                    pprint(f"Waiting 10s for {lb_dns_name} to resolve")
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
            sgs = self.get_security_groups(vm)
            sgids = []
            for sg in sgs:
                if sg['GroupName'] != name:
                    sgids.append(sg['GroupId'])
            if sgids:
                pprint(f"Removing {vm} from security group {name}")
                nic_id = self.get_nic_id(vm)
                conn.modify_network_interface_attribute(NetworkInterfaceId=nic_id, Groups=sgids)
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
            for sg in self.conn.describe_security_groups()['SecurityGroups']:
                if sg['GroupName'] == name:
                    conn.delete_security_group(GroupName=name, GroupId=sg['GroupId'])
        except Exception as e:
            warning(f"Couldn't remove security group {name}. Got {e}")
        if dnsclient is not None:
            return dnsclient

    def list_loadbalancers(self):
        results = []
        elb = self.elb
        lbs = elb.describe_load_balancers()
        for lb in lbs['LoadBalancerDescriptions']:
            if self.debug:
                print(lb)
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
        args['ObjectOwnership'] = 'ObjectWriter'
        s3.create_bucket(**args)
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
            'BlockPublicAcls': False,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': False})

    def delete_bucket(self, bucket):
        s3 = self.s3
        if bucket not in self.list_buckets():
            error(f"Inexistent bucket {bucket}")
            return
        for obj in s3.list_objects(Bucket=bucket).get('Contents', []):
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
        bucketfiles = s3.list_objects(Bucket=bucket)['Contents']
        if self.debug:
            bucketurl = f"https://{bucket}.s3.{self.region}.amazonaws.com"
            return [f"{obj['Key']} ({bucketurl}/{obj['Key']})" for obj in bucketfiles]
        else:
            return [obj['Key'] for obj in bucketfiles]

    def public_bucketfile_url(self, bucket, path):
        return f"https://{bucket}.s3.{self.region}.amazonaws.com/{path}"

    def update_nic(self, name, index, network):
        print("not implemented")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        vpc_id = None
        vpcs = self.conn.describe_vpcs()
        if network is not None:
            vpc_id = self.get_vpc_id(network, vpcs) if not network.startswith('vpc-') else network
        else:
            vpc_ids = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']]
            if vpc_ids:
                vpc_id = vpc_ids[0]
            else:
                warning("No default vpc found")
        if vpc_id is None:
            error("Couldn't find vpc_id")
            sys.exit(1)
        results = []
        conn = self.conn
        for sg in conn.describe_security_groups()['SecurityGroups']:
            if vpc_id is not None and sg['VpcId'] != vpc_id:
                continue
            group_name = sg['GroupName']
            for tag in sg.get('Tags', []):
                if tag['Key'] == 'Name':
                    group_name = tag['Value']
                    break
            results.append(group_name)
        return results

    def create_security_group(self, name, overrides={}):
        ports = overrides.get('ports', [])
        default_subnet_id = None
        vpcs = self.conn.describe_vpcs()
        subnets = self.conn.describe_subnets()
        network = overrides.get('network', 'default')
        if network in [subnet['SubnetId'] for subnet in subnets['Subnets']]:
            vpc_id = [subnet['VpcId'] for subnet in subnets['Subnets'] if subnet['SubnetId'] == network][0]
        elif network == 'default':
            if default_subnet_id is not None:
                network = default_subnet_id
            else:
                vpc_id = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']][0]
                subnet_id = [subnet['SubnetId'] for subnet in subnets['Subnets']
                             if subnet['DefaultForAz'] and subnet['VpcId'] == vpc_id][0]
                network = subnet_id
                pprint(f"Using subnet {network} as default")
        else:
            vpc_id = self.get_vpc_id(network, vpcs) if not network .startswith('vpc-') else network
            if vpc_id is None:
                error(f"Couldn't find vpc {network}")
                sys.exit(1)
        sg = self.resource.create_security_group(GroupName=name, Description=name, VpcId=vpc_id)
        sgtags = [{"Key": "Name", "Value": name}]
        sg.create_tags(Tags=sgtags)
        sg_id = sg.id
        sg.authorize_ingress(GroupId=sg_id, FromPort=-1, ToPort=-1, IpProtocol='icmp',
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
            sg.authorize_ingress(GroupId=sg_id, FromPort=int(fromport), ToPort=int(toport), IpProtocol=protocol,
                                 CidrIp="0.0.0.0/0")
        return {'result': 'success'}

    def delete_security_group(self, name):
        for sg in self.conn.describe_security_groups()['SecurityGroups']:
            group_id = sg['GroupId']
            group_name = sg['GroupName']
            group_tag = ''
            for tag in sg.get('Tags', []):
                if tag['Key'] == 'Name':
                    group_tag = tag['Value']
                    break
            if group_name == name or group_id == name or group_tag == name:
                self.conn.delete_security_group(GroupName=group_name, GroupId=group_id)
                return {'result': 'success'}
        return {'result': 'failure', 'reason': f"security group {name} not found"}

    def update_security_group(self, name, overrides={}):
        found = False
        for sg in self.conn.describe_security_groups()['SecurityGroups']:
            group_id = sg['GroupId']
            group_name = sg['GroupName']
            group_tag = ''
            for tag in sg.get('Tags', []):
                if tag['Key'] == 'Name':
                    group_tag = tag['Value']
                    break
            if group_name == name or group_id == name or group_tag == name:
                found = True
                break
        if not found:
            return {'result': 'failure', 'reason': f"security group {name} not found"}
        sg = self.resource.SecurityGroup(group_id)
        default_cidr = overrides.get('cidr', "0.0.0.0/0")
        default_protocol = overrides.get('protocol', 'tcp')
        if 'ports' in overrides:
            overrides['rules'] = {"cidr": default_cidr, "ports": overrides['ports']}
        for route in overrides.get('rules', []):
            cidr = route.get('cidr', default_cidr)
            protocol = route.get('protocol', default_protocol)
            ports = route.get('ports', [])
            for port in ports:
                pprint(f"Adding rule to port {port} and with protocol {protocol}")
                sg.authorize_ingress(GroupId=group_id, FromPort=port, ToPort=port, IpProtocol=protocol, CidrIp=cidr)
        return {'result': 'success'}

    def info_subnet(self, name):
        subnets = self.conn.describe_subnets()
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            if subnet_id == name or tag_name(subnet) == name:
                return subnet
        msg = f"Subnet {name} not found"
        error(msg)
        return {'result': 'failure', 'reason': msg}

    def eks_get_network(self, netname):
        conn = self.conn
        vpcs = conn.describe_vpcs()
        subnets = conn.describe_subnets()
        if netname in [subnet['SubnetId'] for subnet in subnets['Subnets']]:
            subnet_id = netname
            vpc_id = [subnet['VpcId'] for subnet in subnets['Subnets'] if subnet['SubnetId'] == netname][0]
        elif netname == 'default':
            vpc_ids = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']]
            if not vpc_ids:
                error("Couldn't find default vpc")
                sys.exit(1)
            vpc_id = vpc_ids[0]
            subnet_id = [subnet['SubnetId'] for subnet in subnets['Subnets']
                         if subnet['DefaultForAz'] and subnet['VpcId'] == vpc_id][0]
            pprint(f"Using subnet {subnet_id} as default")
        else:
            vpc_id = self.get_vpc_id(netname, vpcs) if not netname.startswith('vpc-') else netname
            if vpc_id is None:
                error(f"Couldn't find vpc {netname}")
                sys.exit(1)
            subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets'] if subnet['VpcId'] == vpc_id]
            if subnet_ids:
                subnet_id = subnet_ids[0]
            else:
                error(f"Couldn't find valid subnet for vpc {netname}")
                sys.exit(1)
        return vpc_id, subnet_id

    def create_instance_profile(self, name, role):
        iam = boto3.client('iam', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.access_key_secret,
                           region_name=self.region)
        iam.create_instance_profile(InstanceProfileName=name)
        iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=role)

    def delete_instance_profile(self, name, role):
        iam = boto3.client('iam', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.access_key_secret,
                           region_name=self.region)
        iam.remove_role_from_instance_profile(InstanceProfileName=name, RoleName=role)
        iam.delete_instance_profile(InstanceProfileName=name)

    def get_instance_profile(self, name):
        iam = boto3.client('iam', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.access_key_secret,
                           region_name=self.region)
        return iam.get_instance_profile(InstanceProfileName=name)['InstanceProfile']

    def list_instance_profiles(self):
        iam = boto3.client('iam', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.access_key_secret,
                           region_name=self.region)
        response = iam.list_instance_profiles(MaxItems=1000)
        return [instance_profile['InstanceProfileName'] for instance_profile in response['InstanceProfiles']]

    def create_role(self, name, role='ctlplane'):
        plandir = os.path.dirname(self.__init__.__code__.co_filename)
        iam = boto3.client('iam', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.access_key_secret,
                           region_name=self.region)
        rolepolicy_document = open(f'{plandir}/assume_policy.json').read()
        tags = [{'Key': 'Name', 'Value': name}]
        iam.create_role(RoleName=name, AssumeRolePolicyDocument=rolepolicy_document, Tags=tags)
        document = open(f'{plandir}/{role}_policy.json').read()
        iam.put_role_policy(RoleName=name, PolicyName=name, PolicyDocument=document)

    def delete_role(self, name):
        iam_resource = boto3.resource('iam', aws_access_key_id=self.access_key_id,
                                      aws_secret_access_key=self.access_key_secret, region_name=self.region)
        role = iam_resource.Role(name)
        role_policy = iam_resource.RolePolicy(name, name)
        role_policy.delete()
        role.delete()

    def list_roles(self):
        iam = boto3.client('iam', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.access_key_secret,
                           region_name=self.region)
        response = iam.list_roles(MaxItems=1000)
        return [role['RoleName'] for role in response['Roles']]

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        gateway = overrides.get('gateway', True)
        dual_cidr = overrides.get('dual_cidr')
        az = overrides.get('az') or overrides.get('availability_zone') or overrides.get('zone') or self.zone
        if az is not None and not az.startswith(self.region):
            return {'result': 'failure', 'reason': f'Invalid az {az}'}
        conn = self.conn
        try:
            subnet = ip_network(cidr, strict=False)
            if str(subnet.version) == '6' and subnet.prefixlen != 64:
                return {'result': 'failure', 'reason': "Cidr needs to have a 64 prefix"}
        except:
            return {'result': 'failure', 'reason': f"Invalid Cidr {cidr}"}
        if dual_cidr is not None:
            try:
                dual_subnet = ip_network(dual_cidr, strict=False)
                if dual_subnet.version == subnet.version:
                    return {'result': 'failure', 'reason': "cidr and dual_cidr must be of different types"}
                if str(dual_subnet.version) == '6' and dual_subnet.prefixlen != 64:
                    return {'result': 'failure', 'reason': "Dual Cidr needs to have a 64 prefix"}
            except:
                return {'result': 'failure', 'reason': f"Invalid Dual Cidr {dual_cidr}"}
        network = overrides.get('network', 'default')
        nets = self.list_networks()
        if network == 'default':
            networks = [n for n in nets if nets[n]['mode'] == 'default']
        else:
            networks = [nets[n] for n in nets if n == network or nets[n]['domain'] == network]
        if not networks:
            msg = f'Network {network} not found'
            return {'result': 'failure', 'reason': msg}
        else:
            vpcid = networks[0]['domain']
            found = False
            dual_found = dual_cidr is None
            for net in networks:
                network_cidr = ip_network(net['cidr'])
                dual_network_cidr = ip_network(net['dual_cidr']) if 'dual_cidr' in net else None
                if not found and network_cidr.version == subnet.version and subnet.subnet_of(network_cidr):
                    found = True
                if dual_cidr is None and dual_network_cidr is not None and dual_network_cidr.version == subnet.version\
                   and subnet.subnet_of(dual_network_cidr):
                    found = True
                if not dual_found and dual_cidr is not None and dual_network_cidr is not None:
                    if dual_network_cidr.version == dual_subnet.version and dual_subnet.subnet_of(dual_network_cidr):
                        dual_found = True
            if not found:
                return {'result': 'failure', 'reason': f"{cidr} isnt part of any VPC cidrs"}
            if not dual_found:
                return {'result': 'failure', 'reason': f"{dual_cidr} isnt part of any VPC cidrs"}
        Tags = [{"Key": "Name", "Value": name}, {"Key": "Plan", "Value": plan}]
        alb_key = 'internal-elb' if not nat or not gateway else 'elb'
        alb_tag = {"Key": f"kubernetes.io/role/{alb_key}", "Value": "1"}
        Tags.append(alb_tag)
        block = 'Ipv6CidrBlock' if str(subnet.version) == "6" else 'CidrBlock'
        dual_block = 'Ipv6CidrBlock' if block == 'CidrBlock' else 'CidrBlock'
        args = {block: cidr, 'VpcId': vpcid}
        if dual_cidr is not None:
            args[dual_block] = overrides['dual_cidr']
        elif block == 'Ipv6CidrBlock':
            args['Ipv6Native'] = True
        if az is not None:
            args['AvailabilityZone'] = az
        subnet = conn.create_subnet(**args)
        subnetid = subnet['Subnet']['SubnetId']
        conn.create_tags(Resources=[subnetid], Tags=Tags)
        if not nat or not gateway:
            response = conn.create_route_table(VpcId=vpcid)
            route_table_id = response['RouteTable']['RouteTableId']
            conn.create_tags(Resources=[route_table_id], Tags=Tags)
            conn.associate_route_table(SubnetId=subnetid, RouteTableId=route_table_id)
            if gateway:
                Filters = [{'Name': "tag:Name", 'Values': [network]}, {'Name': 'vpc-id', 'Values': [vpcid]}]
                nat_gateways = conn.describe_nat_gateways(Filters=Filters)['NatGateways']
                if nat_gateways:
                    nat_gateway_id = nat_gateways[0]['NatGatewayId']
                    data = {'DestinationCidrBlock': '0.0.0.0/0', 'RouteTableId': route_table_id,
                            'NatGatewayId': nat_gateway_id}
                    conn.create_route(**data)
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        conn = self.conn
        subnets = conn.describe_subnets()
        matching = [subnet for subnet in subnets['Subnets'] if subnet['SubnetId'] == name or tag_name(subnet) == name]
        if not matching:
            return {'result': 'failure', 'reason': f"Subnet {name} not found"}
        subnet_id = matching[0]['SubnetId']
        vms = self.network_ports(name)
        if vms:
            if not force:
                vms = ','.join(vms)
                return {'result': 'failure', 'reason': f"Subnet {name} is being used by the following vms: {vms}"}
            for vm in vms:
                self.delete(vm)
            sleep(15)
        conn.delete_subnet(SubnetId=subnet_id)
        return {'result': 'success'}

    def update_attribute(self, name, attribute, value):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            msg = f"VM {name} not found"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        state = vm['State']['Name']
        if state != 'stopped':
            error(f"Can't update attribute of VM {name} while up")
            return {'result': 'failure', 'reason': f"VM {name} up"}
        instanceid = vm['InstanceId']
        data = {'InstanceId': instanceid}
        data[attribute] = {'Value': value}
        conn.modify_instance_attribute(**data)
        return {'result': 'success'}

    def spread_cluster_tag(self, cluster, subnet):
        conn = self.conn
        clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
        cluster_id = safe_load(open(f'{clusterdir}/metadata.json'))['infraID']
        subnets = self.list_subnets()
        if subnet == 'default':
            default_subnets = [subnets[sub] for sub in subnets if subnets[sub]['default']]
            vpc_id = default_subnets[0]['network']
        else:
            vpc_id = subnets[subnet]['network']
        pprint(f"Tagging vpc with cluster_id {cluster_id}")
        Tags = [{"Key": f'kubernetes.io/cluster/{cluster_id}', "Value": 'owned'}]
        conn.create_tags(Resources=[vpc_id], Tags=Tags)
        Tags.append({"Key": 'KubernetesCluster', "Value": cluster})
        sg_id = self.get_security_group_id(cluster, vpc_id)
        conn.create_tags(Resources=[sg_id], Tags=Tags)
        matching_subnets = [subnets[subnet]['id'] for subnet in subnets if subnets[subnet]['network'] == vpc_id]
        if matching_subnets:
            self.conn.create_tags(Resources=matching_subnets, Tags=Tags)

    def update_subnet(self, name, overrides={}):
        conn = self.conn
        subnets = conn.describe_subnets()
        matching = [subnet for subnet in subnets['Subnets'] if subnet['SubnetId'] == name or tag_name(subnet) == name]
        if not matching:
            return {'result': 'failure', 'reason': f"Subnet {name} not found"}
        subnet_vpc_id = matching[0]['VpcId']
        subnet_id = matching[0]['SubnetId']
        response = conn.describe_route_tables(Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}])
        if not response.get('RouteTables', []):
            return {'result': 'failure', 'reason': "Updating a subnet without route table is not supported"}
        route_table_id = response['RouteTables'][0]['RouteTableId']
        response = conn.describe_route_tables(RouteTableIds=[route_table_id])
        routes = response['RouteTables'][0]['Routes']
        existing_cidrs = [d.get('DestinationCidrBlock') or d.get('DestinationIpv6CidrBlock') for d in routes]
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
                df = {'InstanceIds': [vm]} if vm.startswith('i-') else {'Filters': [{'Name': "tag:Name",
                                                                                     'Values': [vm]}]}
                try:
                    vm_data = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
                except:
                    return {'result': 'failure', 'reason': f"Vm {vm} not found"}
                interface = vm_data['NetworkInterfaces'][0]
                vm_vpc_id = interface['VpcId']
                if vm_vpc_id != subnet_vpc_id:
                    return {'result': 'failure', 'reason': f"Vm {vm} primary nic doesnt belong to same vpc"}
                nic_id = interface['NetworkInterfaceId']
                block = 'DestinationIpv6CidrBlock' if ':' in cidr else 'DestinationCidrBlock'
                data = {block: cidr, 'RouteTableId': route_table_id, 'NetworkInterfaceId': nic_id}
                conn.create_route(**data)
        return {'result': 'success'}

    def list_dns_zones(self):
        dns = self.dns
        return [z['Name'] for z in dns.list_hosted_zones_by_name()['HostedZones']]

    def set_router_mode(self, name, mode=True):
        conn = self.conn
        df = {'InstanceIds': [name]} if name.startswith('i-') else {'Filters': [{'Name': "tag:Name", 'Values': [name]}]}
        try:
            vm = conn.describe_instances(**df)['Reservations'][0]['Instances'][0]
        except:
            error(f"VM {name} not found")
            return {}
        instance_id = vm['InstanceId']
        mode = 'false' if mode else 'true'
        conn.modify_instance_attribute(InstanceId=instance_id, Attribute='sourceDestCheck', Value=mode, DryRun=False)

    def add_vm_to_loadbalancer(self, vm, lb, vpc_id):
        sg_id = self.get_security_group_id(lb, vpc_id)
        instance_id = self.get_id(vm)
        Instances = [{"InstanceId": instance_id}]
        sgs = self.get_security_groups(lb)
        sg_names = [x['GroupName'] for x in sgs]
        if lb not in sg_names:
            sg_ids = [x['GroupId'] for x in sgs]
            sg_ids.append(sg_id)
            nic_id = self.get_nic_id(vm)
            self.conn.modify_network_interface_attribute(NetworkInterfaceId=nic_id, Groups=sg_ids)
        clean_name = lb.replace('.', '-')
        self.elb.register_instances_with_load_balancer(LoadBalancerName=clean_name, Instances=Instances)
