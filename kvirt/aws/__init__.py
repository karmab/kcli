#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Interacts with aws ec2
"""

from kvirt import common
import boto3
# from botocore.exceptions import ClientError
from iptools import IpRange
import os
import time

flavors = {'t2.nano': {'cpus': 1, 'memory': 512}, 't2.micro': {'cpus': 1, 'memory': 1024},
           't2.small': {'cpus': 1, 'memory': 2048}, 't2.medium': {'cpus': 2, 'memory': 4096},
           't2.large': {'cpus': 2, 'memory': 8144}, 't2.xlarge': {'cpus': 2, 'memory': 16384},
           'm5.large': {'cpus': 2, 'memory': 8144}, 'm5.xlarge': {'cpus': 4, 'memory': 16384},
           'm5.2xlarge': {'cpus': 8, 'memory': 32768}, 'm5.4xlarge': {'cpus': 16, 'memory': 65536}
           }


# your base class __init__ needs to define the conn attribute and set it to None when backend cannot be reached
# it should also set debug from the debug variable passed in kcli client
class Kaws(object):
    def __init__(self, host='127.0.0.1', port=None, access_key_id=None, access_key_secret=None, debug=False,
                 region='us-west-1'):
        self.host = host
        self.port = port
        self.debug = debug
        self.conn = boto3.client('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                 region_name=region)
        self.resource = boto3.resource('ec2', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                       region_name=region)
        self.dns = boto3.client('route53', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                                region_name=region)
        return

    def close(self):
        return

    def exists(self, name):
        conn = self.conn
        try:
            conn.describe_instances(InstanceIds=[name])
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

    def create(self, name, virttype='kvm', profile='', plan='kvirt', cpumodel='Westmere', cpuflags=[], numcpus=2,
               memory=512, guestid='guestrhel764', pool='default', template=None, disks=[{'size': 10}], disksize=10,
               diskthin=True, diskinterface='virtio', nets=['default'], iso=None, vnc=False, cloudinit=True,
               reserveip=False, reservedns=False, reservehost=False, start=True, keys=None, cmds=[],
               ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False, files=[],
               enableroot=True, alias=[], overrides={}, tags=None):
        template = self.__evaluate_template(template)
        defaultsubnetid = None
        matchingflavors = [f for f in flavors if flavors[f]['cpus'] >= numcpus and flavors[f]['memory'] >= memory]
        if matchingflavors:
            flavor = matchingflavors[0]
            common.pprint("Using instance type %s" % flavor, color='green')
        else:
            return {'result': 'failure', 'reason': 'Couldnt find instance type matching requirements'}
        conn = self.conn
        tags = [{'ResourceType': 'instance',
                 'Tags': [{'Key': 'hostname', 'Value': name}, {'Key': 'plan', 'Value': plan},
                          {'Key': 'profile', 'Value': profile}]}]
        keypairs = [k for k in conn.describe_key_pairs()['KeyPairs'] if k['KeyName'] == 'kvirt']
        if not keypairs:
            common.pprint("Importing your public key as kvirt keyname", color='green')
            if not os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME'])\
                    and not os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
                common.pprint("No public key found. Leaving", color='red')
                return {'result': 'failure', 'reason': 'No public key found'}
            elif os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
                homekey = open("%s/.ssh/id_rsa.pub" % os.environ['HOME']).read()
            else:
                homekey = open("%s/.ssh/id_dsa.pub" % os.environ['HOME']).read()
            conn.import_key_pair(KeyName='kvirt', PublicKeyMaterial=homekey)
        if cloudinit:
            common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns, domain=domain,
                             reserveip=reserveip, files=files, enableroot=enableroot, overrides=overrides,
                             iso=False, fqdn=True)
            userdata = open('/tmp/user-data', 'r').read()
        else:
            userdata = ''
        networkinterfaces = []
        blockdevicemappings = []
        privateips = []
        for index, net in enumerate(nets):
            networkinterface = {'AssociatePublicIpAddress': False, 'DeleteOnTermination': True,
                                'Description': "eth%s" % index, 'DeviceIndex': index, 'Groups': ['string'],
                                'SubnetId': 'string'}
            if index == 0:
                networkinterface['AssociatePublicIpAddress'] = True
            ip = None
            if isinstance(net, str):
                netname = net
            elif isinstance(net, dict) and 'name' in net:
                netname = net['name']
                if 'ip' in net:
                    ip = net['ip']
                if 'alias' in net:
                    alias = net['alias']
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
                    common.pprint("Using subnet %s as default" % defaultsubnetid, color='green')
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
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')
                blockdevicemapping['Ebs']['VolumeType'] = disk.get('type', 'standard')
            blockdevicemapping['Ebs']['VolumeSize'] = disksize
            blockdevicemappings.append(blockdevicemapping)
#        try:
#            instance = conn.run_instances(ImageId=template, MinCount=1, MaxCount=1, InstanceType=flavor,
#                                          KeyName='kvirt', BlockDeviceMappings=blockdevicemappings,
#                                          UserData=userdata, TagSpecifications=tags)
#        except ClientError as e:
#            if self.debug:
#                print(e.response)
#            code = e.response['Error']['Code']
#            return {'result': 'failure', 'reason': code}
        if reservedns and domain is not None:
            tags[0]['Tags'].append({'Key': 'domain', 'Value': domain})
        instance = conn.run_instances(ImageId=template, MinCount=1, MaxCount=1, InstanceType=flavor,
                                      KeyName='kvirt', BlockDeviceMappings=blockdevicemappings,
                                      UserData=userdata, TagSpecifications=tags)
        newname = instance['Instances'][0]['InstanceId']
        common.pprint("%s created on aws" % newname, color='green')
        if reservedns and domain is not None:
            self.reserve_dns(name, nets=nets, domain=domain, alias=alias, instanceid=newname)
        return {'result': 'success'}

    def start(self, name):
        conn = self.conn
        conn.start_instances(InstanceIds=[name])
        return {'result': 'success'}

    def stop(self, name):
        conn = self.conn
        conn.stop_instances(InstanceIds=[name])
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
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
                return {'result': 'failure', 'reason': "VM/disk %s not found" % name}
        if revert:
            body['licenses'] = ["projects/vm-options/global/licenses/enable-vmx"]
        conn.images().insert(project=project, body=body).execute()
        return {'result': 'success'}

    def restart(self, name):
        conn = self.conn
        conn.start_instances(InstanceIds=[name])
        return {'result': 'success'}

    def report(self):
        print("not implemented")
        return

    def status(self, name):
        status = None
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
            status = vm['status']
        except:
            common.pprint("Vm %s not found" % name, color='red')
        return status

    def list(self):
        conn = self.conn
        resource = self.resource
        vms = []
        results = conn.describe_instances()
        reservations = results['Reservations']
        for reservation in reservations:
            vm = reservation['Instances'][0]
            name = vm['InstanceId']
            state = vm['State']['Name']
            ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else ''
            amid = vm['ImageId']
            image = resource.Image(amid)
            source = os.path.basename(image.image_location)
            plan = ''
            profile = ''
            report = 'N/A'
            if 'Tags' in vm:
                for tag in vm['Tags']:
                    if tag['Key'] == 'plan':
                        plan = tag['Value']
                    if tag['Key'] == 'profile':
                        profile = tag['Value']
            vms.append([name, state, ip, source, plan, profile, report])
        return vms

    def console(self, name, tunnel=False):
        print("not implemented")
        return

    def serialconsole(self, name):
        conn = self.conn
        project = self.project
        zone = self.zone
        console = conn.instances().getSerialPortOutput(zone=zone, project=project, instance=name).execute()
        if console is None:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        print(console['contents'])
        return

    def info(self, name, output='plain', fields=None, values=False):
        yamlinfo = {}
        conn = self.conn
        resource = self.resource
        try:
            vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.debug:
            print(vm)
        name = vm['InstanceId']
        state = vm['State']['Name']
        ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else ''
        amid = vm['ImageId']
        image = resource.Image(amid)
        source = os.path.basename(image.image_location)
        plan = ''
        profile = ''
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == 'plan':
                    plan = tag['Value']
                if tag['Key'] == 'profile':
                    profile = tag['Value']
        yamlinfo['name'] = name
        yamlinfo['status'] = state
        yamlinfo['ip'] = ip
        machinetype = vm['InstanceType']
        if machinetype in flavors:
            yamlinfo['cpus'], yamlinfo['memory'] = flavors[machinetype]['cpus'], flavors[machinetype]['memory']
        # yamlinfo['autostart'] = vm['scheduling']['automaticRestart']
        yamlinfo['template'] = source
        # yamlinfo['creationdate'] = dateparser.parse(vm['creationTimestamp']).strftime("%d-%m-%Y %H:%M")
        yamlinfo['plan'] = plan
        yamlinfo['profile'] = profile
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
            volname = disk['Ebs']['VolumeId']
            volume = conn.describe_volumes(VolumeIds=[volname])['Volumes'][0]
            disksize = volume['Size']
            diskformat = ''
            drivertype = volume['VolumeType']
            path = volume['AvailabilityZone']
            disks.append({'device': devname, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path})
        if disks:
            yamlinfo['disks'] = disks
        common.print_info(yamlinfo, output=output, fields=fields, values=values)
        return {'result': 'success'}

    def ip(self, name):
        ip = None
        conn = self.conn
        try:
            vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        if self.debug:
            print(vm)
        ip = vm['PublicIpAddress'] if 'PublicIpAddress' in vm else ''
        return ip

# should return a list of available templates, or isos ( if iso is set to True
    def volumes(self, iso=False):
        conn = self.conn
        images = []
        oses = ['Amazon Linux AMI*', 'Provided by Red Hat, Inc.', 'SUSE Linux Enterprise*', 'Ubuntu Server*']
        Filters = [{'Name': 'description', 'Values': oses}]
        allimages = conn.describe_images(Filters=Filters)
        for image in allimages['Images']:
            images.append("%s - %s" % (image['Name'], image['ImageId']))
        return sorted(images, key=str.lower)

    def delete(self, name, snapshots=False):
        conn = self.conn
        domain = None
        try:
            vm = conn.describe_instances(InstanceIds=[name])['Reservations'][0]['Instances'][0]
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        hostname = None
        if 'Tags' in vm:
            for tag in vm['Tags']:
                if tag['Key'] == 'domain':
                    domain = tag['Value']
                if tag['Key'] == 'hostname':
                    hostname = tag['Value']
        vm = conn.terminate_instances(InstanceIds=[name])
        if domain is not None and hostname is not None:
            self.delete_dns(hostname, domain, name)
        return {'result': 'success'}

    def clone(self, old, new, full=False, start=False):
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue):
        print("not implemented")
        return

    def update_memory(self, name, memory):
        print("not implemented")
        return

    def update_cpu(self, name, numcpus):
        print("not implemented")
        return

    def update_start(self, name, start=True):
        print("not implemented")
        return

    def update_information(self, name, information):
        print("not implemented")
        return

    def update_iso(self, name, iso):
        print("not implemented")
        return

    def create_disk(self, name, size, pool=None, thin=True, template=None):
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            vm = conn.instances().get(zone=zone, project=project, instance=name).execute()
        except:
            return {'result': 'failure', 'reason': "VM %s not found" % name}
        numdisks = len(vm['disks']) + 1
        diskname = "%s-disk%s" % (name, numdisks)
        body = {'sizeGb': size, 'sourceDisk': 'zones/%s/diskTypes/pd-standard' % zone, 'name': diskname}
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
                time.sleep(5)
                common.pprint("Waiting for disk to be ready", color='green')
        body = {'source': '/compute/v1/projects/%s/zones/%s/disks/%s' % (project, zone, diskname), 'autoDelete': True}
        conn.instances().attachDisk(zone=zone, project=project, instance=name, body=body).execute()
        return {'result': 'success'}

    def delete_disk(self, name, diskname):
        conn = self.conn
        project = self.project
        zone = self.zone
        try:
            conn.disks().delete(zone=zone, project=project, disk=diskname).execute()
        except Exception as e:
            print(e)
            return {'result': 'failure', 'reason': "Disk %s not found" % name}
        return

# should return a dict of {'pool': poolname, 'path': name}
    def list_disks(self):
        disks = {}
        conn = self.conn
        project = self.project
        zone = self.zone
        alldisks = conn.disks().list(zone=zone, project=project).execute()
        if 'items' in alldisks:
            for disk in alldisks['items']:
                if self.debug:
                    print(disk)
                diskname = disk['name']
                pool = os.path.basename(disk['type'])
                disks[diskname] = {'pool': pool, 'path': zone}
        return disks

    def add_nic(self, name, network):
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        print("not implemented")
        return

    def _ssh_credentials(self, name):
        user = 'ec2-user'
        ip = self.ip(name)
        return (user, ip)

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False, insecure=False, cmd=None, X=False, D=None):
        u, ip = self._ssh_credentials(name)
        sshcommand = common.ssh(name, ip=ip, host=self.host, port=self.port, user=u,
                                local=local, remote=remote, tunnel=tunnel, insecure=insecure, cmd=cmd, X=X,
                                debug=self.debug)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False, download=False, recursive=False):
        u, ip = self._ssh_credentials(name)
        scpcommand = common.scp(name, ip='', host=self.host, port=self.port, user=user,
                                source=source, destination=destination, recursive=recursive, tunnel=tunnel,
                                debug=self.debug, download=False)
        return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu'):
        print("not implemented")
        return

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', pxe=None):
        conn = self.conn
        if cidr is not None:
            try:
                IpRange(cidr)
            except TypeError:
                return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
        vpc = conn.create_vpc(CidrBlock=cidr)
        vpcid = vpc['Vpc']['VpcId']
        conn.create_subnet(CidrBlock=cidr, VpcId=vpcid)
        if nat:
            conn.create_internet_gateway()
        return {'result': 'success'}

    def delete_network(self, name=None):
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
        print("not implemented")
        return

    def list_networks(self):
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

# returns the path of the pool, if it makes sense. used by kcli list --pools
    def get_pool_path(self, pool):
        print("not implemented")
        return

    def __evaluate_template(self, template):
        if template.lower().startswith('centos'):
            amiid = 'ami-8352e3fe'
            common.pprint("Using ami %s" % amiid, color='green')
            return 'ami-8352e3fe'
        else:
            return template
        return template

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, instanceid=None):
        common.pprint("Reserving dns...", color='green')
        dns = self.dns
        net = nets[0]
        zone = [z['Id'].split('/')[2] for z in dns.list_hosted_zones_by_name()['HostedZones']
                if z['Name'] == '%s.' % domain]
        if not zone:
            common.pprint("Domain not found", color='red')
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
                        time.sleep(5)
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
        changes = [{'Action': 'DELETE', 'ResourceRecordSet':
                   {'Name': entry, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ip}]}}]
        entry = "%s.%s." % (name, domain)
        dns.change_resource_record_sets(HostedZoneId=zoneid, ChangeBatch={'Changes': changes})
        return {'result': 'success'}
