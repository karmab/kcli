#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Aws Provider Class
"""

from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import METADATA_FIELDS
import boto3
from netaddr import IPNetwork
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
               vnc=False, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=None,
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, alias=[], overrides={}, tags=[], storemetadata=False,
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False,
               metadata={}, securitygroups=[]):
        conn = self.conn
        if self.exists(name):
            return {'result': 'failure', 'reason': "VM %s already exists" % name}
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
                    pprint("Using ami %s" % imageid)
                image = imageinfo['Name']
            else:
                return {'result': 'failure', 'reason': 'Invalid image %s' % image}
        defaultsubnetid = None
        if flavor is None:
            matching = [f for f in staticf if staticf[f]['cpus'] >= numcpus and staticf[f]['memory'] >= memory]
            if matching:
                flavor = matching[0]
                pprint("Using instance type %s" % flavor)
            else:
                return {'result': 'failure', 'reason': 'Couldnt find instance type matching requirements'}
        vmtags = [{'ResourceType': 'instance',
                   'Tags': [{'Key': 'Name', 'Value': name}, {'Key': 'hostname', 'Value': name}]}]
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            vmtags[0]['Tags'].append({'Key': entry, 'Value': metadata[entry]})
        if keypair is None:
            keypair = 'kvirt_%s' % self.access_key_id
        keypairs = [k for k in conn.describe_key_pairs()['KeyPairs'] if k['KeyName'] == keypair]
        if not keypairs:
            pprint("Importing your public key as %s" % keypair)
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
                                           domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                           overrides=overrides, version=version, plan=plan, image=image)
            else:
                userdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                            domain=domain, reserveip=reserveip, files=files, enableroot=enableroot,
                                            overrides=overrides, fqdn=True, storemetadata=storemetadata)[0]
        else:
            userdata = ''
        networkinterfaces = []
        blockdevicemappings = []
        privateips = []
        vpcs = conn.describe_vpcs()
        subnets = conn.describe_subnets()
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
            # if securitygroups:
            #    netpublic = False
            networkinterface['AssociatePublicIpAddress'] = netpublic if index == 0 else False
            if netname in [subnet['SubnetId'] for subnet in subnets['Subnets']]:
                pass
            elif netname == 'default':
                if defaultsubnetid is not None:
                    netname = defaultsubnetid
                else:
                    vpcid = [vpc['VpcId'] for vpc in vpcs['Vpcs'] if vpc['IsDefault']][0]
                    subnetid = [subnet['SubnetId'] for subnet in subnets['Subnets']
                                if subnet['DefaultForAz'] and subnet['VpcId'] == vpcid][0]
                    netname = subnetid
                    defaultsubnetid = netname
                    pprint("Using subnet %s as default" % defaultsubnetid)
            else:
                vpcid = self.get_vpc_id(vpcs, netname) if not netname.startswith('vpc-') else netname
                if vpcid is None:
                    error("Couldn't find vpc %s" % netname)
                    sys.exit(1)
                subnetids = [subnet['SubnetId'] for subnet in subnets['Subnets'] if subnet['VpcId'] == vpcid]
                if subnetids:
                    netname = subnetids[0]
                else:
                    error("Couldn't find valid subnet for vpc %s" % netname)
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
                    pprint("Adding vm to security group %s" % kube)
                    kubesgid = self.get_security_group_id(kube, vpcid)
                    if kubesgid is None:
                        sg = self.resource.create_security_group(GroupName=kube, Description=kube)
                        sgtags = [{"Key": "Name", "Value": kube}]
                        sg.create_tags(Tags=sgtags)
                        kubesgid = sg.id
                        sg.authorize_ingress(GroupName=kube, FromPort=-1, ToPort=-1, IpProtocol='icmp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=22, ToPort=22, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=80, ToPort=80, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=8080, ToPort=8080, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=5443, ToPort=5443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=8443, ToPort=8443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=443, ToPort=443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=6443, ToPort=6443, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=22624, ToPort=22624, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=2379, ToPort=2380, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=30000, ToPort=32767, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=30000, ToPort=32767, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=10250, ToPort=10259, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=9000, ToPort=9999, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=9000, ToPort=9999, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=4789, ToPort=4789, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=4789, ToPort=4789, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=6081, ToPort=6081, IpProtocol='tcp',
                                             CidrIp="0.0.0.0/0")
                        sg.authorize_ingress(GroupName=kube, FromPort=6081, ToPort=6081, IpProtocol='udp',
                                             CidrIp="0.0.0.0/0")
                    SecurityGroupIds.append(kubesgid)
                networkinterface['Groups'] = SecurityGroupIds
            networkinterfaces.append(networkinterface)
        if len(privateips) > 1:
            networkinterface['PrivateIpAddresses'] = privateips
        for index, disk in enumerate(disks):
            if image is not None and index == 0:
                continue
            letter = chr(index + ord('a'))
            # devicename = '/dev/sd%s1' % letter if index == 0 else '/dev/sd%s' % letter
            devicename = '/dev/xvd%s' % letter
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
        conn.run_instances(ImageId=imageid, MinCount=1, MaxCount=1, InstanceType=flavor,
                           KeyName=keypair, BlockDeviceMappings=blockdevicemappings,
                           NetworkInterfaces=networkinterfaces, UserData=userdata, TagSpecifications=vmtags)
        if reservedns and domain is not None:
            # eip = conn.allocate_address(Domain='vpc')
            # vmid = reservation.instances[0].id
            # conn.associate_address(InstanceId=vmid, AllocationId=eip["AllocationId"])
            # self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name, ip=eip["PublicIp"])
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=name)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        conn.start_instances(InstanceIds=[instanceid])
        return {'result': 'success'}

    def stop(self, name, soft=False):
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
        print("not implemented")
        return

    def restart(self, name):
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
        print("Region: %s" % self.region)
        return

    def status(self, name):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
            vms.append(self.info(name))
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, web=False):
        try:
            if name.startswith('i-'):
                vm = self.conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
            else:
                Filters = {'Name': "tag:Name", 'Values': [name]}
                vm = self.conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            error("VM %s not found" % name)
        instanceid = vm['InstanceId']
        amid = vm['ImageId']
        image = self.resource.Image(amid)
        source = os.path.basename(image.image_location)
        user = common.get_user(source)
        user = 'ec2-user'
        url = "https://eu-west-3.console.aws.amazon.com/ec2/v2/connect/%s/%s" % (user, instanceid)
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
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            error("VM %s not found" % name)
            return
        instanceid = vm['InstanceId']
        response = conn.get_console_output(InstanceId=instanceid, DryRun=False, Latest=False)
        if 'Output' not in response:
            error("VM %s not ready yet" % name)
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
            return None
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
                error("VM %s not found" % name)
                return {}
        instanceid = vm['InstanceId']
        name = instanceid
        state = vm['State']['Name']
        ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else ''
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
        yamlinfo['ip'] = ip
        machinetype = vm['InstanceType']
        yamlinfo['flavor'] = machinetype
        if machinetype in staticf:
            yamlinfo['cpus'] = staticf[machinetype]['cpus']
            yamlinfo['memory'] = staticf[machinetype]['memory']
        # yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        yamlinfo['image'] = source
        yamlinfo['user'] = common.get_user(yamlinfo['image'])
        # yamlinfo['creationdate'] = dateparser.parse(vm['creationTimestamp']).strftime("%d-%m-%Y %H:%M")
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

    def ip(self, name):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else None
        return ip

    def internalip(self, name):
        ip = None
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
            return {'result': 'failure', 'reason': "VM %s not found" % name}
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
                        metavalue = "%s,%s" % (oldvalue, metavalue)
        newtags = [{"Key": metatype, "Value": metavalue}]
        conn.create_tags(Resources=[instanceid], Tags=newtags)
        return 0

    def update_memory(self, name, memory):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        state = vm['State']['Name']
        if state != 'stopped':
            error("Can't update memory of VM %s while up" % name)
            return {'result': 'failure', 'reason': "VM %s up" % name}
        instanceid = vm['InstanceId']
        instancetype = [f for f in staticf if staticf[f]['memory'] >= int(memory)]
        if instancetype:
            flavor = instancetype[0]
            pprint("Using flavor %s" % flavor)
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
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        instancetype = vm['InstanceType']
        state = vm['State']['Name']
        if state != 'stopped':
            error("Can't update cpus of VM %s while up" % name)
            return {'result': 'failure', 'reason': "VM %s up" % name}
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
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        instanceid = vm['InstanceId']
        state = vm['State']['Name']
        if state != 'stopped':
            error("Can't update cpus of VM %s while up" % name)
            return {'result': 'failure', 'reason': "VM %s up" % name}
        instancetype = [f for f in staticf if staticf[f]['cpus'] >= numcpus]
        if instancetype:
            flavor = instancetype[0]
            pprint("Using flavor %s" % flavor)
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

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
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
        pprint("Deleting image %s" % image)
        conn = self.conn
        try:
            conn.deregister_image(ImageId=image)
            return {'result': 'success'}
        except:
            return {'result': 'failure', 'reason': "Image %s not found" % image}

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        conn = self.conn
        if cidr is not None:
            try:
                network = IPNetwork(cidr)
            except:
                return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
            if str(network.version) == "6":
                msg = 'Primary cidr needs to be ipv4 in aws. Use dual to inject ipv6 or set aws_ipv6 parameter'
                return {'result': 'failure', 'reason': msg}
        Tags = [{"Key": "Name", "Value": name}, {"Key": "Plan", "Value": plan}]
        vpcargs = {"CidrBlock": cidr}
        if 'dual_cidr' in overrides:
            vpcargs["Ipv6CidrBlock"] = overrides['dual_cidr']
            vpcargs["Ipv6Pool"] = overrides['dual_cidr']
        if 'aws_ipv6' in overrides and overrides['aws_ipv6']:
            vpcargs["AmazonProvidedIpv6CidrBlock"] = True
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
            return {'result': 'failure', 'reason': "Network %s not found" % name}
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
        return

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
            pprint("Using ami %s" % image)
        return image

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None):
        if domain is None:
            domain = nets[0]
        internalip = None
        pprint("Using domain %s..." % domain)
        dns = self.dns
        cluster = None
        fqdn = "%s.%s" % (name, domain)
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace("%s." % name, '').replace("%s." % cluster, '')
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == '%s.' % domain]
        if not zone:
            error("Domain %s not found" % domain)
            return {'result': 'failure', 'reason': "Domain %s not found" % domain}
        zoneid = zone[0]
        dnsentry = name if cluster is None else "%s.%s" % (name, cluster)
        entry = "%s.%s." % (dnsentry, domain)
        if cluster is not None and ('master' in name or 'worker' in name):
            counter = 0
            while counter != 100:
                internalip = self.internalip(name)
                if internalip is None:
                    sleep(5)
                    pprint("Waiting 5 seconds to grab internal ip and create DNS record for %s..." % name)
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
            error("Couldn't assign DNS for %s" % name)
            return
        dnsip = ip if internalip is None else internalip
        changes = [{'Action': 'CREATE', 'ResourceRecordSet':
                   {'Name': entry, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': dnsip}]}}]
        if alias:
            for a in alias:
                if a == '*':
                    if cluster is not None and ('master' in name or 'worker' in name):
                        new = '*.apps.%s.%s.' % (cluster, domain)
                    else:
                        new = '*.%s.%s.' % (name, domain)
                    changes.append({'Action': 'CREATE', 'ResourceRecordSet':
                                    {'Name': new, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ip}]}})
                else:
                    new = '%s.%s.' % (a, domain) if '.' not in a else '%s.' % a
                    changes.append({'Action': 'CREATE', 'ResourceRecordSet':
                                    {'Name': new, 'Type': 'CNAME', 'TTL': 300, 'ResourceRecords': [{'Value': entry}]}})
        dns.change_resource_record_sets(HostedZoneId=zoneid, ChangeBatch={'Changes': changes})
        return {'result': 'success'}

    def delete_dns(self, name, domain, instanceid=None, allentries=False):
        dns = self.dns
        cluster = None
        fqdn = "%s.%s" % (name, domain)
        if fqdn.split('-')[0] == fqdn.split('.')[1]:
            cluster = fqdn.split('-')[0]
            name = '.'.join(fqdn.split('.')[:1])
            domain = fqdn.replace("%s." % name, '').replace("%s." % cluster, '')
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == '%s.' % domain]
        if not zone:
            error("Domain %s not found" % domain)
            return {'result': 'failure', 'reason': "Domain not found"}
        zoneid = zone[0]
        dnsentry = name if cluster is None else "%s.%s" % (name, cluster)
        entry = "%s.%s." % (dnsentry, domain)
        ip = self.ip(instanceid)
        if ip is None:
            error("Couldn't Get DNS Ip for %s" % name)
            return
        recs = []
        clusterdomain = "%s.%s" % (cluster, domain)
        for record in dns.list_resource_record_sets(HostedZoneId=zoneid)['ResourceRecordSets']:
            if entry in record['Name'] or ('master-0' in name and record['Name'].endswith("%s." % clusterdomain)):
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
                if z['Name'] == '%s.' % domain]
        if not zone:
            error("Domain not found")
        else:
            zoneid = zone[0]
            for record in dns.list_resource_record_sets(HostedZoneId=zoneid)['ResourceRecordSets']:
                name = record['Name']
                _type = record['Type']
                ttl = record.get('TTL', 'N/A')
                if _type not in ['NS', 'SOA']:
                    name = name.replace("%s." % domain, '')
                name = name[:-1]
                if 'ResourceRecords' in record:
                    data = ' '.join(x['Value'] for x in record['ResourceRecords'])
                elif 'AliasTarget' in record:
                    data = record['AliasTarget']['DNSName'][:-1]
                else:
                    continue
                results.append([name, _type, ttl, data])
        return results

    def flavors(self):
        results = []
        for flavor in staticf:
            name = flavor
            numcpus = staticf[flavor]['cpus']
            memory = staticf[flavor]['memory']
            results.append([name, numcpus, memory])
        return results

    def export(self, name, image=None):
        conn = self.conn
        try:
            Filters = {'Name': "tag:Name", 'Values': [name]}
            vm = conn.describe_instances(Filters=[Filters])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        InstanceId = vm['InstanceId']
        Name = image if image is not None else "kcli %s" % name
        Description = "image based on %s" % name
        conn.create_image(InstanceId=InstanceId, Name=Name, Description=Description, NoReboot=True)
        return {'result': 'success'}

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False, dnsclient=None):
        ports = [int(port) for port in ports]
        resource = self.resource
        conn = self.conn
        elb = self.elb
        # protocols = {80: 'HTTP', 8080: 'HTTP', 443: 'HTTPS'}
        # protocols = {80: 'HTTP', 8080: 'HTTP'}
        protocols = {}
        Listeners = []
        for port in ports:
            protocol = protocols[port] if port in protocols else 'TCP'
            Listener = {'Protocol': protocol, 'LoadBalancerPort': port, 'InstanceProtocol': protocol,
                        'InstancePort': port}
            Listeners.append(Listener)
        AvailabilityZones = ["%s%s" % (self.region, i) for i in ['a', 'b', 'c']]
        clean_name = name.replace('.', '-')
        sg = resource.create_security_group(GroupName=name, Description=name)
        sgid = sg.id
        sgtags = [{"Key": "Name", "Value": name}]
        sg.create_tags(Tags=sgtags)
        for port in ports:
            sg.authorize_ingress(GroupName=name, FromPort=port, ToPort=port, IpProtocol='tcp', CidrIp="0.0.0.0/0")
        lbinfo = {"LoadBalancerName": clean_name, "Listeners": Listeners, "AvailabilityZones": AvailabilityZones,
                  "SecurityGroups": [sgid]}
        if domain is not None:
            lbinfo['Tags'] = [{"Key": "domain", "Value": domain}]
            if dnsclient is not None:
                lbinfo['Tags'].append({"Key": "dnsclient", "Value": dnsclient})
        lb = elb.create_load_balancer(**lbinfo)
        # if 80 in ports:
        #    HealthTarget = 'HTTP:80%s' % checkpath
        # else:
        #   HealthTarget = '%s:%s' % (protocol, port)
        HealthTarget = '%s:%s' % (protocol, port)
        HealthCheck = {'Interval': 20, 'Target': HealthTarget, 'Timeout': 3, 'UnhealthyThreshold': 10,
                       'HealthyThreshold': 2}
        elb.configure_health_check(LoadBalancerName=clean_name, HealthCheck=HealthCheck)
        pprint("Reserved dns name %s" % lb['DNSName'])
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
                    pprint("Waiting 10s for %s to get an ip resolution" % lb_dns_name)
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
                        pprint("Using found domain %s" % domain)
        except:
            warning("Loadbalancer %s not found" % clean_name)
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
                pprint("Removing %s from security group %s" % (vm, name))
                conn.modify_instance_attribute(InstanceId=instanceid, Groups=sgids)
        elb.delete_load_balancer(LoadBalancerName=clean_name)
        if domain is not None and dnsclient is None:
            warning("Deleting DNS %s.%s" % (name, domain))
            self.delete_dns(name, domain, name)
        try:
            sleep(30)
            conn.delete_security_group(GroupName=name)
        except Exception as e:
            warning("Couldn't remove security group %s. Got %s" % (name, e))
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
            error("Bucket %s already there" % bucket)
            return
        location = {'LocationConstraint': self.region}
        # s3.create_bucket(Bucket=bucket, CreateBucketConfiguration=location)
        args = {'Bucket': bucket, "CreateBucketConfiguration": location}
        if public:
            args['ACL'] = 'public-read'
        s3.create_bucket(**args)

    def delete_bucket(self, bucket):
        s3 = self.s3
        if bucket not in self.list_buckets():
            error("Inexistent bucket %s" % bucket)
            return
        for obj in s3.list_objects(Bucket=bucket)['Contents']:
            key = obj['Key']
            pprint("Deleting object %s from bucket %s" % (key, bucket))
            s3.delete_object(Bucket=bucket, Key=key)
        s3.delete_bucket(Bucket=bucket)

    def delete_from_bucket(self, bucket, path):
        s3 = self.s3
        if bucket not in self.list_buckets():
            error("Inexistent bucket %s" % bucket)
            return
        s3.delete_object(Bucket=bucket, Key=path)

    def download_from_bucket(self, bucket, path):
        s3 = self.s3
        s3.download_file(bucket, path, path)

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
            error("Inexistent bucket %s" % bucket)
            return []
        return [obj['Key'] for obj in s3.list_objects(Bucket=bucket)['Contents']]

    def public_bucketfile_url(self, bucket, path):
        return "https://%s.s3.%s.amazonaws.com/%s" % (bucket, self.region, path)
