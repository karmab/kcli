# -*- coding: utf-8 -*-

import base64
from getpass import getuser
import glob
import hashlib
from hcloud import Client, APIException
from hcloud.servers import ServerCreatePublicNetwork
from hcloud.load_balancers import LoadBalancerAlgorithm, LoadBalancerService, LoadBalancerHealthCheck
from hcloud.load_balancers import LoadBalancerTarget
import json
from kvirt import common
from kvirt.common import error, warning, get_ssh_pub_key
from kvirt.defaults import METADATA_FIELDS
import os


class Khcloud():
    def __init__(self, api_key=None, location=None):
        self.conn = Client(token=api_key)
        self.location = self.conn.locations.get_by_name(location)
        self.machine_flavor_cache = {}
        return

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model', cpuflags=[],
               cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, alias=[], overrides={}, tags=[], storemetadata=False,
               sharedfolders=[], cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False,
               numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[],
               vmuser=None, guestagent=True):
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}

        # Discard the boot disk since hetzner includes a boot disk in their VM's
        if len(disks) > 0:
            disks = disks[1:]

        volumeresponses = []
        for index, disk in enumerate(disks):
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
            elif isinstance(disk, dict):
                disksize = disk.get('size', '10')

            diskname = f"{name}-disk{index}"
            volumeresponse = self.conn.volumes.create(disksize, diskname, location=self.location,
                                                      labels={"kcli-managed": "volume"})
            volumeresponses.append(volumeresponse)

        if not keys:
            publickeyfile = get_ssh_pub_key()
            if publickeyfile is not None:
                publickeyfile = open(publickeyfile).read().strip()
                keys = [publickeyfile]

        hetzner_ssh_keys = []
        if keys:
            user = common.get_user(image)
            if user == 'root':
                user = getuser()

            for key in keys:
                decoded_key = base64.b64decode(key.strip().split()[1].encode('ascii'))
                hashed_key = hashlib.md5(decoded_key).hexdigest()
                md5_fingerprint = ':'.join(a + b for a, b in zip(hashed_key[::2], hashed_key[1::2]))
                hetzner_ssh_key = self.conn.ssh_keys.get_by_fingerprint(md5_fingerprint)
                if hetzner_ssh_key is None:
                    hetzner_ssh_key = self.conn.ssh_keys.create(name=f"kcli-uploaded-key-{hashed_key}", public_key=key)

                hetzner_ssh_keys.append(hetzner_ssh_key)
        else:
            warning("neither id_rsa, id_dsa nor id_ed25519 public keys found in your .ssh or .kcli directories, "
                    "you might have trouble accessing the vm")

        userdata = None
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

        labels = {"kcli-managed": "vm"}
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            value = metadata[entry].replace('.', '-')
            labels[entry] = value

        placement_group = None
        if "worker" not in name:
            placement_group_name = f"kcli-{labels['plan']}"
            placement_group = self.conn.placement_groups.get_by_name(placement_group_name)
            if not placement_group:
                response = self.conn.placement_groups.create(name=placement_group_name, type="spread",
                                                             labels={"kcli-managed": "placement-group",
                                                                     "plan": labels["plan"]})
                if response.action:
                    response.action.wait_until_finished(300)

                    if response.action.error:
                        return {'result': 'failure', 'reason': json.dumps(response.error)}

                placement_group = response.placement_group

        flavor_options = overrides.get("flavor_options", [flavor] if flavor is not None else [])

        for idx, flavor_option in enumerate(flavor_options):
            servertype = self.conn.server_types.get_by_name(flavor_option)
            if "snapshot_id" in overrides:
                hetzner_image = self.conn.images.get_by_id(overrides.get("snapshot_id"))
            else:
                hetzner_image = self.conn.images.get_by_name_and_architecture(image, servertype.architecture)

            try:
                created_vm = self.conn.servers.create(
                    name=name,
                    server_type=servertype,
                    image=hetzner_image,
                    start_after_create=False,
                    user_data=userdata,
                    volumes=[],
                    ssh_keys=hetzner_ssh_keys,
                    location=self.location,
                    public_net=ServerCreatePublicNetwork(enable_ipv4=False, enable_ipv6=False),
                    labels=labels,
                    placement_group=placement_group
                )

                created_vm.action.wait_until_finished(300)
                break
            except APIException as e:
                if e.code == "resource_unavailable":
                    msg = f"Could not get server of type '{flavor_option}' in location '{self.location.name}'"
                    if len(flavor_options) > (idx + 1):
                        warning(f"{msg}' trying the next configured flavor option.")
                    else:
                        warning(msg)
                        error("No more flavors available to try. Define more flavors in 'flavor_options'.")

        created_vm = created_vm.server

        for volumeresponse in volumeresponses:
            volumeresponse.action.wait_until_finished(300)
            response = volumeresponse.volume.attach(server=created_vm, automount=False)
            response.wait_until_finished(300)

        for net in nets:
            if net["public"]:
                continue
            response = created_vm.attach_to_network(self.conn.networks.get_by_name(net["name"]), net["ip"])
            response.wait_until_finished(300)

        response = self.start(created_vm.name)

        if response["result"] == "failure":
            msg = f"Could not start VM {name}, after creation, with the following reason {response['reason']}"
            return {'result': 'failure', 'reason': msg}

        lb = overrides.get('loadbalancer')
        if lb is not None:
            self.add_vm_to_loadbalancer(name, lb)

        return {'result': 'success'}

    def delete(self, name, snapshots=False):
        server = self.conn.servers.get_by_name(name)
        if server is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

        volumes = server.volumes
        response = server.delete()

        if response.error:
            return {'result': 'failure', 'reason': json.dumps(response.error)}

        response.wait_until_finished(300)
        for volume in volumes:
            success = volume.delete()
            if not success:
                return {'result': 'failure', 'reason': f"failed to delete volume {volume.name}"}
        return {'result': 'success'}

    def start(self, name):
        server = self.conn.servers.get_by_name(name)
        if server is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

        response = server.power_on()
        if response.error:
            return {'result': 'failure', 'reason': json.dumps(response.error)}

        response.wait_until_finished(300)
        return {'result': 'success'}

    def stop(self, name, soft=False):
        server = self.conn.servers.get_by_name(name)
        if server is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

        if soft:
            response = server.shutdown()
        else:
            response = server.power_off()

        if response.error:
            return {'result': 'failure', 'reason': json.dumps(response.error)}
        else:
            response.wait_until_finished(300)
            return {'result': 'success'}

    def restart(self, name):
        server = self.conn.servers.get_by_name(name)
        if server is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

        response = server.reboot()

        if response.error:
            return {'result': 'failure', 'reason': json.dumps(response.error)}
        else:
            response.wait_until_finished(300)
            return {'result': 'success'}

    def dnsinfo(self, name):
        server = self.conn.servers.get_by_name(name)
        if server is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

        dnsclient, domain = None, None
        for key, value in server.labels.items():
            if key == 'dnsclient':
                dnsclient = value
            if key == 'domain':
                domain = value
        return dnsclient, domain

    def info(self, name, vm=None, debug=False):
        yamlinfo = {}
        conn = self.conn
        if vm is None:
            vm = conn.servers.get_by_name(name=name)
        if vm is None:
            error(f"VM {name} not found")
            return {}
        yamlinfo['name'] = vm.name
        yamlinfo['status'] = vm.status
        yamlinfo['flavor'] = vm.server_type.name
        flavor_info = self.info_flavor(yamlinfo['flavor'], vm.server_type)
        yamlinfo['numcpus'], yamlinfo['memory'] = flavor_info['cpus'], flavor_info['memory']
        yamlinfo['image'] = vm.image.id_or_name
        yamlinfo['user'] = common.get_user(vm.image.name or vm.image.description)
        yamlinfo['creationdate'] = vm.created.strftime("%d-%m-%Y %H:%M")
        nets = []
        ips = []
        if vm.public_net:
            ipv4 = vm.public_net.primary_ipv4
            if ipv4:
                yamlinfo['ip'] = ipv4
                ips.append(ipv4)
            ipv6 = vm.public_net.primary_ipv6
            if ipv6:
                ips.append(ipv6)
            for floating_ip in vm.public_net.floating_ips:
                ips.append(floating_ip.ip)
            nets.append({'device': 'eth0', 'mac': '', 'net': '', 'type': "public"})

        for private_net in vm.private_net:
            yamlinfo['private_ip'] = private_net.ip
            ips.append(yamlinfo['private_ip'])
            if 'ip' not in yamlinfo:
                yamlinfo['ip'] = yamlinfo['private_ip']

            for alias_ip in private_net.alias_ips:
                ips.append(alias_ip)

            nets.append({'device': 'enp7s0', 'mac': private_net.mac_address, 'net': private_net.network.name,
                         'type': "private", "ip": yamlinfo['private_ip']})

        if nets:
            yamlinfo['nets'] = nets
        if len(ips) > 1:
            yamlinfo['ips'] = ips
        disks = []
        for volume in vm.volumes:
            volume = self.conn.volumes.get_by_id(volume.id)
            devname = volume.name
            path = os.path.basename(volume.linux_device)
            disksize = volume.size
            disks.append({'device': devname, 'size': disksize, 'format': volume.format, 'type': 'volume', 'path': path})
        if disks:
            yamlinfo['disks'] = disks
        if vm.labels:
            for key, value in vm.labels.items():
                if key in METADATA_FIELDS:
                    yamlinfo[key] = value
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def info_flavor(self, name, flavor=None):
        conn = self.conn
        if not flavor:
            if name in self.machine_flavor_cache:
                flavor = self.machine_flavor_cache[name]
            else:
                flavor = conn.server_types.get_by_name(name)
                self.machine_flavor_cache[name] = flavor
        return {'cpus': flavor.cores, 'memory': flavor.memory}

    def exists(self, name):
        conn = self.conn
        vm = conn.servers.get_by_name(name=name)
        if vm:
            return True
        return False

    def list(self):
        vms = []
        instances = self.conn.servers.get_all(label_selector="kcli-managed")
        for instance in instances:
            vminfo = self.info(instance.name, instance)
            if vminfo:
                vms.append(vminfo)
        if not vms:
            return []
        return sorted(vms, key=lambda x: x['name'])

    def create_loadbalancer(self, name, ports=[], checkpath='/index.html', vms=[], domain=None, checkport=80, alias=[],
                            internal=False, dnsclient=None, ip=None):
        sane_name = name.replace('.', '-')
        ports = [int(port) for port in ports]
        load_balancer_type = self.conn.load_balancer_types.get_by_name("lb11")
        load_balancer_algorithm = LoadBalancerAlgorithm("round_robin")
        load_balancer_services = []
        for port in ports:
            load_balancer_health_check = LoadBalancerHealthCheck(protocol="tcp",
                                                                 port=checkport,
                                                                 interval=10,
                                                                 timeout=10,
                                                                 retries=3)
            load_balancer_service = LoadBalancerService(protocol="tcp",
                                                        listen_port=port,
                                                        destination_port=port,
                                                        health_check=load_balancer_health_check)
            load_balancer_services.append(load_balancer_service)

        response = self.conn.load_balancers.create(name=sane_name,
                                                   load_balancer_type=load_balancer_type,
                                                   algorithm=load_balancer_algorithm,
                                                   services=load_balancer_services,
                                                   labels={"kcli-managed": "loadbalancer"},
                                                   location=self.location,
                                                   public_interface=(not internal))

        response.action.wait_until_finished(300)
        created_load_balancer = response.load_balancer

        private_network_name = ""
        load_balancer_targets = []
        for vm in vms:
            info = self.info(vm, debug=True)
            use_private_ip = False
            for net in info['nets']:
                if net["type"] == "private":
                    private_network_name = net['net']
                    use_private_ip = True
            vm_object = info["debug"]
            load_balancer_target = LoadBalancerTarget(type="server", server=vm_object, use_private_ip=use_private_ip)
            load_balancer_targets.append(load_balancer_target)

        if private_network_name:
            response = created_load_balancer.attach_to_network(self.conn.networks.get_by_name(private_network_name), ip)
            response.wait_until_finished(300)

        responses = []
        for load_balancer_target in load_balancer_targets:
            response = created_load_balancer.add_target(load_balancer_target)
            responses.append(response)

        for response in responses:
            response.wait_until_finished(300)

        return {'result': 'success'}

    def delete_loadbalancer(self, name):
        sane_name = name.replace('.', '-')

        load_balancer = self.conn.load_balancers.get_by_name(sane_name)
        if load_balancer is None:
            error(f"load balancer {sane_name} not found")

        deleted = load_balancer.delete()
        if not deleted:
            return {'result': 'failure', 'reason': f"Could not delete loadbalancer {name}"}

        return {'result': 'success'}

    def list_loadbalancers(self):
        load_balancers = self.conn.load_balancers.get_all(label_selector="kcli-managed")

        result = []
        for load_balancer in load_balancers:
            ip = load_balancer.public_net.ipv4 if load_balancer.public_net.enabled else load_balancer.private_net[0].ip
            result.append([load_balancer.name, ip, '', '', ''])

        return result

    def add_vm_to_loadbalancer(self, vm, lb):
        sane_name = lb.replace('.', '-')

        load_balancer = self.conn.load_balancers.get_by_name(sane_name)
        if load_balancer is None:
            error(f"load balancer {sane_name} not found")

        info = self.info(vm, debug=True)
        use_private_ip = False
        for net in info['nets']:
            if net["type"] == "private":
                use_private_ip = True
        vm_object = info["debug"]
        load_balancer_target = LoadBalancerTarget(type="server", server=vm_object, use_private_ip=use_private_ip)

        response = load_balancer.add_target(load_balancer_target)
        response.wait_until_finished(300)
        if response.error:
            error(json.dumps(response.error))

    def ip(self, name):
        info = self.info(name)
        if not info:
            return None

        return info["ip"]

    def volumes(self, iso=True):
        return glob.glob('*.iso')

    def add_image(self, url, pool, cmd=None, name=None, size=None, convert=False):
        os.system("curl -Lk %s > %s" % (url, os.path.basename(url)))

    def delete_image(self, image, pool=None):
        os.remove(image)

    def get_pool_path(self, pool):
        return '.'

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        response = self.conn.volumes.create(size=size, name=name, location=self.location,
                                            labels={"kcli-managed": "volume"})
        response.action.wait_until_finished(300)

        if response.action.error:
            return {'result': 'failure', 'reason': json.dumps(response.error)}

        return {'result': 'success'}

    def delete_disk(self, name=None, diskname=None, pool=None, novm=False):
        if novm:
            volume = self.conn.volumes.get_by_name(diskname)
            if volume is None:
                return {'result': 'failure', 'reason': f"volume {diskname} not found"}

            if volume.server:
                return {'result': 'failure', 'reason': f"volume {diskname} is attached to a server"}
            success = volume.delete()

            if not success:
                return {'result': 'failure', 'reason': f"failed to delete volume {diskname}"}

            return {'result': 'success'}

        server = self.conn.servers.get_by_name(name)
        if server is None:
            return {'result': 'failure', 'reason': f"VM {name} not found"}

        for volume in server.volumes:
            devname = volume.name
            source = os.path.basename(volume.linux_device)
            if devname == diskname or source == diskname:
                response = volume.detach()
                response.wait_until_finished(300)

                if response.error:
                    return {'result': 'failure', 'reason': json.dumps(response.error)}

                success = volume.delete()

                if not success:
                    return {'result': 'failure', 'reason': f"failed to delete volume {diskname}"}
                break
        return {'result': 'success'}

    def list_disks(self):
        disks = {}
        alldisks = self.conn.volumes.get_all(label_selector="kcli-managed")
        for disk in alldisks:
            if self.debug:
                print(disk)
            disks[disk.name] = {'pool': "", 'path': self.location}
        return disks

    def list_buckets(self):
        return []
