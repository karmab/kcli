import glob, os, base64, hashlib, string, random
from dateutil import parser as dateparser
from kvirt import common
from kvirt.common import pprint, error, warning, get_ssh_pub_key
from kvirt.defaults import UBUNTUS, METADATA_FIELDS
from getpass import getuser
from hcloud import Client
from hcloud.server_types import ServerType
from hcloud.servers import ServerCreatePublicNetwork


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
               sharedfolders=[], kernel=None, initrd=None, cmdline=None, placement=[], autostart=False,
               cpuhotplug=False, memoryhotplug=False, numamode=None, numa=[], pcidevices=[], tpm=False, rng=False,
               metadata={}, securitygroups=[], vmuser=None):
        if self.conn.servers.get_by_name(name):
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
            volumeresponse = self.conn.volumes.create(disksize, diskname, location=self.location, labels={"kcli-managed": ""})
            volumeresponses.append(volumeresponse)

        volumes = []
        for volumeresponse in volumeresponses:
            volumeresponse.action.wait_until_finished(100)
            volumes.append(volumeresponse.volume)

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
                md5_fingerprint = ':'.join(a+b for a,b in zip(hashed_key[::2], hashed_key[1::2]))
                hetzner_ssh_key = self.conn.ssh_keys.get_by_fingerprint(md5_fingerprint)
                if hetzner_ssh_keys is None:
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
               
        servertype = self.conn.server_types.get_by_name(flavor)
        if "snapshot_id" in overrides:
            hetzner_image = self.conn.images.get_by_id(overrides.get("snapshot_id"))
        else:
            hetzner_image = self.conn.images.get_by_name_and_architecture(image, servertype.architecture)

        created_vm = self.conn.servers.create(
            name=name,
            server_type=servertype,
            image=hetzner_image,
            start_after_create=False,
            user_data=userdata,
            volumes=volumes,
            ssh_keys=hetzner_ssh_keys,
            location=self.location,
            public_net=ServerCreatePublicNetwork(enable_ipv4=False, enable_ipv6=False),
            labels={"kcli-managed": ""}
        )

        created_vm.action.wait_until_finished(300)
        created_vm = created_vm.server

        for net in nets:
            if net["public"]:
                continue
            response = created_vm.attach_to_network(self.conn.networks.get_by_name(net["name"]), net["ip"])
            response.wait_until_finished(100)

        return {'result': 'success'}
    
    def start(self, name):
        response = self.conn.servers.get_by_name(name).power_on()
        if response.error:
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        else:
            response.wait_until_finished(100)
            return {'result': 'success'}

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
        yamlinfo['flavor'] = vm.server_type
        flavor_info = self.info_flavor(vm.server_type.name)
        yamlinfo['numcpus'], yamlinfo['memory'] = flavor_info['cpus'], flavor_info['memory']
        yamlinfo['image'] = vm.image.id_or_name
        yamlinfo['user'] = common.get_user(vm.image.name or vm.image.description)
        yamlinfo['creationdate'] = vm.created.strftime("%d-%m-%Y %H:%M")
        nets = []
        ips = []
        if vm.public_net:
            yamlinfo['ip'] = vm.public_net.primary_ipv4
            ips.append(vm.public_net.primary_ipv4)
            ips.append(vm.public_net.primary_ipv6)
            for floating_ip in vm.public_net.floating_ips:
                ips.append(floating_ip.ip)
            nets.append({'type': "public"})

        for private_net in vm.private_net:
            yamlinfo['private_ip'] = private_net.ip
            ips.append(private_net.ip)
            if 'ip' not in yamlinfo:
                yamlinfo['ip'] = private_net.ip

            for alias_ip in private_net.alias_ips:
                ips.append(alias_ip)

            nets.append({'mac': private_net.mac_address, 'net': private_net.network.name, 'type': "private"})
                
        if nets:
            yamlinfo['nets'] = nets
        if len(ips) > 1:
            yamlinfo['ips'] = ips
        disks = []
        for volume in vm.volumes:
            devname = volume.name
            path = os.path.basename(volume.linux_device)
            disksize = volume.size
            disks.append({'device': devname, 'size': disksize, 'path': path})
        if disks:
            yamlinfo['disks'] = disks
        if vm.labels:
            for key, value in vm.labels.items():
                if key in METADATA_FIELDS:
                    yamlinfo[key] = value
        if debug:
            yamlinfo['debug'] = vm
        return yamlinfo

    def info_flavor(self, name):
        conn = self.conn
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

    def volumes(self, iso=True):
        return glob.glob('*.iso')

    def add_image(self, url, pool, cmd=None, name=None, size=None, convert=False):
        os.system("curl -Lk %s > %s" % (url, os.path.basename(url)))

    def delete_image(self, image, pool=None):
        os.remove(image)

    def get_pool_path(self, pool):
        return '.'

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
