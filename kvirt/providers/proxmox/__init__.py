# -*- coding: utf-8 -*-

from datetime import datetime
from kvirt import common
from kvirt.common import error, pprint, warning, sdn_ip
from kvirt.defaults import METADATA_FIELDS, UBUNTUS
from kvirt.providers.sampleprovider import Kbase
import os
from pathlib import Path
import proxmoxer
from proxmoxer.tools import Tasks
import re
from subprocess import CalledProcessError, call, check_call
import time
from textwrap import dedent
from tempfile import TemporaryDirectory
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import webbrowser
from yaml import safe_dump


VM_STATUS = {"running": "up", "stopped": "down", "unknown": "unk"}


def patch_cmds(image, cmds):
    gcmds = []
    lower = image.lower()
    if lower.startswith('fedora') or lower.startswith('rhel') or lower.startswith('centos'):
        gcmds.append('yum -y install qemu-guest-agent')
        gcmds.append('systemctl enable --now qemu-guest-agent')
    elif lower.startswith('debian') or [x for x in UBUNTUS if x in lower] or 'ubuntu' in lower:
        gcmds.append('apt-get update')
        gcmds.append('apt-get -y install qemu-guest-agent')
        gcmds.append('/etc/init.d/qemu-guest-agent start')
        gcmds.append('update-rc.d qemu-guest-agent defaults')
    index = 1 if cmds and 'sleep' in cmds[0] else 0
    if image.startswith('rhel'):
        subindex = [i for i, value in enumerate(cmds) if value.startswith('subscription-manager')]
        if subindex:
            index = subindex.pop() + 1
    return cmds[:index] + gcmds + cmds[index:]


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


class Kproxmox(Kbase):
    def __init__(
        self,
        host="127.0.0.1",
        port=None,
        user="root@pam",
        password=None,
        token_name=None,
        token_secret=None,
        filtertag=None,
        node=None,
        verify_ssl=True,
        imagepool=None,
        debug=False,
    ):
        self.conn = proxmoxer.ProxmoxAPI(
            host,
            port=port,
            user=user,
            password=password,
            token_name=token_name,
            token_value=token_secret,
            verify_ssl=verify_ssl,
            timeout=60,
        )
        self.filtertag = filtertag
        if not node:
            # Get responding node
            status = self.conn.cluster.status.get()
            for s in status:
                if s["type"] == "node" and s["local"] == 1:
                    node = s["name"]
                    break
        self.node = node
        self.imagepool = imagepool
        self.host = host
        self.user = user
        self.debug = debug

    def info_host(self):
        nodes = self.conn.cluster.resources.get(type="node")
        cl_status = self.conn.cluster.status.get()
        data = {
            "cluster_name": "",
            "nodes_online": 0,
            "cpus": 0,
            "memory_used": 0,
            "memory_total": 0,
            "vms_running": 0,
            "storages": [],
        }

        for status in cl_status:
            if status["type"] != "cluster":
                data["nodes_online"] += status["online"]
                continue
            data["cluster_name"] = status["name"]

        for node in nodes:
            if node["status"] != "online":
                continue
            data["memory_total"] += node["maxmem"]
            data["memory_used"] += node["mem"]
            data["cpus"] += node["maxcpu"]

        all_vms = self.conn.cluster.resources.get(type="vm")
        data["vms_running"] = len(
            list(filter(lambda v: v["status"] == "running", all_vms))
        )

        data["storages"] = self._get_storages()

        # Human readable sizes
        data["memory_total"] = sizeof_fmt(data["memory_total"])
        data["memory_used"] = sizeof_fmt(data["memory_used"])

        return data

    def list(self):
        vms = []
        for vm in self._get_all_vms():
            name, _type, template = vm['name'], vm['type'], vm['template']
            if _type == 'lxc' or template == 1:
                continue
            try:
                vms.append(self.info(name, vm=vm))
            except:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def volumes(self, iso=False):
        return [t["name"] for t in self._get_isos()] if iso else [t["name"] for t in self._get_templates()]

    def _check_node(self, node):
        # Check target node
        ret = None
        cluster_status = self.conn.cluster.status.get()
        for n in cluster_status:
            if n["type"] == "node" and n["name"] == node:
                ret = n
                break
        return ret

    def _check_storage(self, pool, node=None):
        if not node:
            node = self.node
        # Check that template storage is available on this node
        storages = self.conn.nodes(node).storage.get(content="images")
        ret = None
        for s in storages:
            if s["storage"] == pool:
                ret = s
        return ret

    def add_image(self, url, pool, cmds=[], name=None, size=None, convert=False):
        if self.imagepool:
            pool = self.imagepool

        if url.endswith(".iso") or name.endswith(".iso"):
            return self.add_iso(url, pool, name=name)

        if pool is None:
            return {"result": "failure", "reason": "No pool storage defined."}

        # Check if template already exists
        if self._get_template_info(name):
            pprint(f"Image {name} already there")
            return {"result": "success", "found": True}

        new_vmid = self.conn.cluster.nextid.get()
        shortimage = os.path.basename(url).split("?")[0]

        is_valid = False
        uncompresscmd = None
        compressed = {"bz2": "bunzip2 -f", "gz": "gunzip -f", "xz": "unxz -f", "zst": "zstd --decompress"}
        for ext in reversed(shortimage.split(".")[-2:]):
            if ext in compressed.keys():
                uncompresscmd = compressed[ext]
                continue
            if ext in ("qcow2", "img"):
                is_valid = True
            break
        if not is_valid:
            return {"result": "failure", "reason": "Image format unsupported"}

        if shortimage.endswith(".img"):
            shortimage = Path(shortimage).with_suffix(".qcow2").name

        # Check target node
        pve_node = self._check_node(self.node)
        if not pve_node:
            return {"result": "failure", "reason": f"node {self.node} not found."}

        # Check that template storage is available on this node
        if not self._check_storage(pool, node=pve_node["name"]):
            return {"result": "failure", "reason": f"storage {pool} not found on {pve_node['name']}."}

        # Download image in /var/lib/vz/images/0
        downloadpath = "/var/lib/vz/images/0"
        ssh_user = "root"

        downloadcmds = [
            f"mkdir -p {downloadpath}",
            f"curl -L '{url}' -o {downloadpath}/{shortimage}",
        ]
        if uncompresscmd:
            downloadcmds.append(f"{uncompresscmd} {downloadpath}/{shortimage}")
            shortimage = Path(shortimage).stem
        sshcmd = f'ssh {ssh_user}@{pve_node["ip"]} "{" && ".join(downloadcmds)}"'
        pprint(f"Downloading image {name} on {pve_node['name']}...")
        code = call(sshcmd, shell=True)
        if code != 0:
            return {"result": "failure", "reason": "Unable to download indicated image"}

        now = time.strftime("%d-%m-%Y %H:%M", time.gmtime())
        description = f"Image created with kcli from {shortimage} on {now}"

        # Create template
        ok, status = self._wait_for(
            self.conn.nodes(pve_node["name"]).qemu.post(
                vmid=new_vmid,
                name=name,
                scsihw="virtio-scsi-pci",
                virtio0=f"file={pool}:0,import-from=local:0/{shortimage}",
                description=dedent(description),
            )
        )
        if not ok:
            return {"result": "failure", "reason": status}

        self._wait_for(self.conn.nodes(pve_node["name"]).qemu(new_vmid).template.post())
        pprint(f"Image {name} created on {pve_node['name']}")

        # Remove image in /var/lib/vz/images/0
        pprint(f"Removing image {downloadpath}/{shortimage} on {pve_node['name']}...")
        sshcmd = f'ssh {ssh_user}@{pve_node["ip"]} "rm {downloadpath}/{shortimage}"'
        code = call(sshcmd, shell=True)
        if code != 0:
            warning("Unable to delete image.")

        # Wait until template info are up-to-date
        while not self._get_template_info(name):
            time.sleep(1)

        return {"result": "success"}

    def delete_image(self, image, pool=None):
        if image.endswith(".iso"):
            return self.delete_iso(image, pool=pool)
        # Check if template exists
        template = self._get_template_info(image)
        if template is None:
            return {"result": "failure", "reason": f"Image {image} not found"}

        ok, status = self._wait_for(
            self.conn.nodes(template["node"]).qemu(template["vmid"]).delete()
        )
        if not ok:
            return {"result": "failure", "reason": status}
        return {"result": "success"}

    def delete_iso(self, image, pool=None):
        if self.imagepool:
            pool = self.imagepool

        if pool is None:
            return {"result": "failure", "reason": "No pool storage specified."}

        isos = [i for i in self._get_isos() if i["name"] == image and i["pool"] == pool]
        if not isos:
            error(f"ISO {image} not found")
            return {"result": "failure", "reason": f"ISO {image} not found"}

        ok, status = self._wait_for(
            self.conn.nodes(self.node).storage(pool).content(f"iso/{image}").delete()
        )
        if not ok:
            return {"result": "failure", "reason": status}
        return {"result": "success"}

    def add_iso(self, url, pool, name=None):
        if self.imagepool:
            pool = self.imagepool
        if pool is None:
            return {"result": "failure", "reason": "No pool storage defined."}

        # Check if iso already exists
        isos = [i for i in self._get_isos() if i["name"] == name and i["pool"] == pool]
        if isos:
            pprint(f"ISO {name} already there")
            return {"result": "success", "found": True}

        # Check target node
        pve_node = self.node
        if not self._check_node(pve_node):
            return {"result": "failure", "reason": f"node {pve_node} not found."}

        # Check that template storage is available on this node
        if not self._check_storage(pool, node=pve_node):
            return {"result": "failure", "reason": f"storage {pool} not found on {pve_node}."}

        # All good, upload ISO
        if os.path.exists(url):
            # is path
            with open(url, "rb") as f:
                pprint(f"uploading {name} to {pve_node}...")
                ok, status = self._wait_for(
                    self.conn.nodes(pve_node)
                    .storage(pool)
                    .upload.post(content="iso", filename=f)
                )
        else:
            # is url
            ok, status = self._wait_for(
                self.conn.nodes(pve_node)
                .storage(pool)("download-url")
                .post(content="iso", filename=name, url=url)
            )
        if not ok:
            return {"result": "failure", "reason": status}
        return {"result": "success"}

    def create(
        self,
        name,
        virttype=None,
        profile="",
        flavor=None,
        plan="kvirt",
        cpumodel="host",
        cpuflags=[],
        cpupinning=[],
        numcpus=2,
        memory=512,
        guestid="guestrhel764",
        pool=None,
        image=None,
        disks=[{"size": 10}],
        disksize=10,
        diskthin=True,
        diskinterface="virtio",
        nets=[],
        iso=None,
        vnc=True,
        cloudinit=True,
        reserveip=False,
        reservedns=False,
        reservehost=False,
        start=True,
        keys=[],
        cmds=[],
        ips=None,
        netmasks=None,
        gateway=None,
        nested=True,
        dns=None,
        domain=None,
        tunnel=False,
        files=[],
        enableroot=False,
        overrides={},
        tags=[],
        storemetadata=False,
        sharedfolders=[],
        cmdline=None,
        placement=[],
        autostart=False,
        cpuhotplug=False,
        memoryhotplug=False,
        numamode=None,
        numa=[],
        pcidevices=[],
        tpm=False,
        rng=False,
        metadata={},
        securitygroups=[],
        vmuser=None,
        guestagent=True,
    ):
        imagepool = self.imagepool or pool
        if overrides.get('lxc', False):
            if image is None:
                return {"result": "failure", "reason": "Image not specified"}
            if '/' not in image:
                image = f'{imagepool}:vztmpl/{image}'
            if image not in self.list_images():
                return {"result": "failure", "reason": f"Image {image} not found"}
            disk = disks[0] if disks else [disksize]
            disksize = disk.get('size', disksize) if isinstance(disk, dict) else disk
            password = overrides.get('rootpassword', 'password')
            params = {'vmid': self.conn.cluster.nextid.get(), 'hostname': name, 'memory': memory, 'swap': 512,
                      'cores': numcpus, 'rootfs': f'{imagepool}:{disksize}', 'ostemplate': image,
                      'password': password, 'net0': 'name=eth0,bridge=vmbr0,ip=dhcp', 'start': 1}
            params['description'] = f'image={os.path.basename(image)},plan={plan},profile={profile}'
            self._wait_for(self.conn.nodes(self.node).lxc.post(**params))
            return {"result": "success"}
        qemuextra = overrides.get('qemuextra')
        if qemuextra is not None and not self.user.startswith('root'):
            return {"result": "failure", "reason": "Adjusting arg requires root user"}
        enableiommu = overrides.get('iommu', False)
        default_diskinterface = diskinterface
        needs_ignition = image is not None and (common.needs_ignition(image) or 'ignition_file' in overrides)
        if cpumodel == "host-model":
            cpumodel = "host"
        machine = None
        uefi = overrides.get('uefi', False)
        uefi_legacy = overrides.get('uefi_legacy', False)
        secureboot = overrides.get('secureboot', False)
        if (uefi or uefi_legacy or secureboot or enableiommu):
            machine = 'q35'
        # Check if vm already exists
        if self._get_vm_id(name) is not None:
            return {"result": "failure", "reason": f"VM {name} already exists"}

        # Get next available ID
        new_vmid = self.conn.cluster.nextid.get()

        if image is not None:
            # Get image template
            template = self._get_template_info(image)
            if template is None:
                return {"result": "failure", "reason": f"image {image} not found. Use kcli download image {image}."}
        if iso is not None:
            if not [i for i in self._get_isos() if i["name"] == iso and i["pool"] == imagepool]:
                return {"result": "failure", "reason": f"ISO {iso} not found"}

        # Check target node
        node = overrides.get("node") or self.node or template["node"]
        cluster_status = self.conn.cluster.status.get()
        for n in cluster_status:
            if n["type"] == "node" and n["name"] == node:
                pve_node = n
                break
        if not pve_node:
            return {"result": "failure", "reason": f"node {node} not found."}

        # Check pool storage
        storages = self.conn.nodes(node).storage.get(content="images")
        storage = None
        for s in storages:
            if s["storage"] == pool:
                storage = s
        if not storage:
            return {"result": "failure", "reason": f"storage {pool} not found on {node}."}

        if image is not None:
            # Clone template
            linked_clone = True
            if (self.imagepool and self.imagepool != pool) or overrides.get("pool"):
                linked_clone = False

            self._wait_for(
                self.conn.nodes(template["node"])
                .qemu(template["vmid"])
                .clone.post(
                    newid=new_vmid,
                    name=name,
                    target=node,
                    storage=pool if not linked_clone else None,
                    full=int(not linked_clone),
                )
            )
        else:
            # Create empty VM
            ok, status = self._wait_for(self.conn.nodes(node).qemu.post(vmid=new_vmid, name=name,
                                                                        scsihw="virtio-scsi-pci"))
            if not ok:
                return {"result": "failure", "reason": status}

        new_vm = self.conn.nodes(node).qemu(new_vmid)

        # Add tag
        if self.filtertag:
            new_vm.config.post(tags=self.filtertag)

        # Metadata
        now = time.strftime("%d-%m-%Y %H:%M", time.gmtime())
        metadata["creationdate"] = now
        description = []
        for entry in [field for field in metadata if field in METADATA_FIELDS]:
            description.append(f"{entry}={metadata[entry]}")
        description = ','.join(description)

        vm_data = {'name': name, 'cores': numcpus, 'memory': memory, 'cpu': cpumodel, 'agent': 'enabled=1',
                   'description': dedent(description), 'onboot': 1}

        sriov_nic = False
        for index, net in enumerate(nets):
            if isinstance(net, str):
                netname = net
                net = {'name': netname}
            if net.get('sriov', False):
                nets[index]['type'] = 'igb'
                nets[index]['vfio'] = True
                nets[index]['noconf'] = True
                sriov_nic = True
                if machine is None:
                    machine = 'q35'
                    warning("Forcing machine type to q35")
            nettype = net.get('type', 'virtio')
            bridge = self._get_default_network(node) if net['name'] == 'default' else net["name"]
            vm_data[f'net{index}'] = f"model={nettype},bridge={bridge}"
            mac = net.get('mac')
            if mac is not None:
                vm_data[f'net{index}'] += f",macaddr={mac}"
            vlan = net.get('vlan')
            if vlan is not None:
                if not isinstance(vlan, int):
                    return {'result': 'failure', 'reason': f"Invalid vlan value in nic {index}. Must be an int"}
                vm_data[f'net{index}'] += f",tag={vlan}"
                del nets[index]['vlan']
            multiqueues = net.get('multiqueues')
            if multiqueues is not None:
                if not isinstance(multiqueues, int):
                    return {'result': 'failure', 'reason': f"Invalid multiqueues value in nic {index}. Must be an int"}
                elif not 0 < multiqueues < 257:
                    return {'result': 'failure', 'reason': f"multiqueues value in nic {index} not between 0 and 256 "}
                else:
                    vm_data[f'net{index}'] += f",queues={multiqueues}"
            mtu = net.get('mtu')
            if mtu is not None:
                if not isinstance(mtu, int):
                    return {'result': 'failure', 'reason': f"Invalid mtu value in nic {index}. Must be an int"}
                vm_data[f'net{index}'] += f",mtu={mtu}"

        # ISO
        if iso is not None:
            vm_data['cdrom'] = f"file={imagepool}:iso/{iso},media=cdrom"

        # Cloudinit
        userdata, netdata = None, None
        if image is not None:
            node_ip = pve_node["ip"]
            noname = overrides.get('noname', False)
            meta = safe_dump({"instance-id": name, "local-hostname": name} if not noname else {})
            code = self._upload_file(node_ip, f"{name}-metadata.yaml", meta)
            if code != 0:
                return {"result": "failure", "reason": "Unable to upload metadata"}
            if needs_ignition:
                ignition = 'qemu' in image
                if not self.user.startswith('root'):
                    return {"result": "failure", "reason": "Adjusting arg requires root user"}
                ignition_path = f"{name}.ign" if ignition else f"{name}-userdata.yaml"
                version = common.ignition_version(image)
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway, dns=dns,
                                           domain=domain, files=files, enableroot=enableroot,
                                           overrides=overrides, version=version, plan=plan, image=image,
                                           vmuser=vmuser)
                code = self._upload_file(node_ip, ignition_path, userdata)
                if code != 0:
                    return {"result": "failure", "reason": "Unable to upload userdata"}
                if not ignition:
                    vm_data['citype'] = 'configdrive2'
                else:
                    arg = f" -fw_cfg name=opt/com.coreos/config,file=/var/lib/vz/snippets/{ignition_path}"
                    qemuextra = qemuextra + arg if qemuextra is not None else arg
                    userdata = None
            else:
                cmds = patch_cmds(image, cmds)
                userdata, meta, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                           gateway=gateway, dns=dns, domain=domain,
                                                           files=files, enableroot=enableroot, overrides=overrides,
                                                           storemetadata=storemetadata, machine='proxmox',
                                                           image=image, vmuser=vmuser)
                code = self._upload_file(node_ip, f"{name}-userdata.yaml", userdata)
                if code != 0:
                    return {"result": "failure", "reason": "Unable to upload userdata"}
                code = self._upload_file(node_ip, f"{name}-netdata.yaml", netdata)
                if code != 0:
                    return {"result": "failure", "reason": "Unable to upload netdata"}
        if userdata is not None:
            vm_data['cicustom'] = f'meta=local:snippets/{name}-metadata.yaml'
            vm_data['cicustom'] += f',user=local:snippets/{name}-userdata.yaml'
            if netdata is not None:
                vm_data['cicustom'] += f',network=local:snippets/{name}-netdata.yaml'
            vm_data['ide0'] = f"{pool}:cloudinit"

        initial_disks = self._get_current_disks(new_vm.config.get())
        # Disks
        default_disksize = disksize
        for index, disk in enumerate(disks):
            diskinterface = default_diskinterface
            diskserial = None
            diskwwn = None
            if isinstance(disk, str) and disk.isdigit():
                disksize = int(disk)
            elif isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, dict):
                disksize = disk.get("size", default_disksize)
                diskinterface = disk.get('interface', default_diskinterface)
                diskwwn = disk.get('wwn')
                diskserial = disk.get('serial')
            else:
                disksize = default_disksize
            diskname = f"{diskinterface}{index}"
            if index < len(initial_disks):
                current_diskname = initial_disks[index]['name']
                current_disksize = int(initial_disks[index]['size'])
                if disksize != current_disksize and current_disksize > 1:
                    pprint(f"Waiting for image disk {index} to be resized")
                    new_vm.resize.put(disk=diskname, size=f"{disksize}G")
                vm_data[current_diskname] = initial_disks[index]['full']
            else:
                vm_data[diskname] = f"file={pool}:{disksize},format=qcow2"
                if diskwwn is not None:
                    vm_data[diskname] += ',wwn={diskwwn}'
                if diskserial is not None:
                    vm_data[diskname] += ',serial={diskserial}'

        if machine is not None:
            vm_data['machine'] = f'type={machine}'
            if enableiommu:
                vm_data['machine'] += ',viommu=intel'

        if uefi or uefi_legacy or secureboot:
            vm_data['bios'] = 'ovmf'
            if secureboot:
                vm_data['efidisk0'] = f"{pool}:32"
                vm_data['smbios1'] = 'uuid=auto'
            if tpm:
                vm_data['tpmstate'] = f"{pool}:4"
                vm_data['tpmversion'] = '2.0'

        if qemuextra is not None:
            vm_data['args'] = qemuextra

        qemuextra = overrides.get('rng', False)
        if rng:
            vm_data['rng'] = 'source=/dev/urandom'

        if sriov_nic:
            vm_data['acpi'] = 1

        for index, cell in enumerate(numa):
            cellid = cell.get('id', index)
            cellcpus = cell.get('vcpus')
            cellmemory = cell.get('memory')
            # siblings = cell.get('siblings', [])
            if cellcpus is None or cellmemory is None:
                msg = f"Can't properly use cell {index} in numa block"
                return {'result': 'failure', 'reason': msg}
            new_numa = f"cpus={cellcpus},memory={cellmemory},hostnodes={cellid}"
            if numamode is not None:
                new_numa += f',policy={numamode}'
            vm_data[f'numa{cellid}'] = new_numa

        for index, pcidevice in enumerate(pcidevices):
            vm_data['hostpci{index}'] = pcidevices

        # Configure VM
        self._wait_for(new_vm.config.post(**vm_data))

        # Start VM
        if start:
            ok, status = self._wait_for(self.conn.nodes(node).qemu(new_vmid).status.start.post())
            if not ok:
                return {"result": "failure", "reason": status}
        # Wait until vm info are up-to-date
        while self._get_vm_id(name) is None:
            time.sleep(1)
        return {"result": "success"}

    def info(self, name, output="plain", fields=[], values=False, vm=None, debug=False):
        if vm is None:
            listinfo = False
            vm_info = self._get_vm_info(name)
            if vm_info is None:
                error(f"VM {name} not found")
                return {}
        else:
            listinfo = True
            vm_info = vm
        vm = self._get_vm(name)
        vm_config = vm.config.get()
        if 'meta' not in vm_config:
            return self._get_lxc_info(name, vm_config)
        yamlinfo = {"name": vm_info["name"], "node": vm_info["node"], "id": vm_info["vmid"],
                    "status": VM_STATUS.get(vm_info["status"]), "numcpus": vm_info["maxcpu"],
                    "memory": int(vm_info["maxmem"] / 1024 / 1024), 'nets': [], 'disks': []}
        timestamp = int(self._parse_notes(vm_config['meta'])['ctime'])
        yamlinfo['creationdate'] = datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
        description_data = self._parse_notes(vm_config.get("description"))
        metadata = {k: description_data[k] for k in description_data if k in METADATA_FIELDS}
        yamlinfo.update(metadata)
        if 'image' in yamlinfo:
            yamlinfo['user'] = common.get_user(yamlinfo['image'])
        kubetype = yamlinfo.get('kubetype')
        cluster_network = yamlinfo.get('cluster_network')

        if vm_info["status"] == "running":
            try:
                nets = vm.agent("network-get-interfaces").get().get("result")
            except proxmoxer.core.ResourceException:
                nets = []
            ips = []
            for net in nets:
                for nic in net.get("ip-addresses", []):
                    ip = nic["ip-address"]
                    if not nic["ip-address"].startswith(tuple(['127.0.0.1', '::1', 'fe80::', '169.254.169', 'fd69']))\
                       and not sdn_ip(ip, kubetype, cluster_network):
                        ips.append(ip)
            if ips and 'ip' not in yamlinfo:
                ip4s = [i for i in ips if ':' not in i]
                ip6s = [i for i in ips if i not in ip4s]
                yamlinfo['ip'] = ip4s[0] if ip4s else ip6s[0]
            if len(ips) > 1:
                yamlinfo['ips'] = ips
        if listinfo:
            return yamlinfo
        for entry in vm_config:
            if re.findall(r"net\d+", entry):
                device = entry
                nic_data = vm_config[entry].split(',')
                network = nic_data[1].split('=')[1]
                networktype, mac = nic_data[0].split('=')
                yamlinfo['nets'].append({'device': device, 'mac': mac.lower(), 'net': network, 'type': networktype})
            if re.findall(r"(scsi|ide|virtio)\d+", entry):
                device, diskformat, drivertype = entry, entry, entry
                disk_data = vm_config[entry].split(',')
                path = disk_data[0]
                disktype, disksize = disk_data[-1].split('=')
                if disktype == 'media':
                    continue
                yamlinfo['disks'].append({'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype,
                                          'path': path})
        yamlinfo['nets'] = sorted(yamlinfo['nets'], key=lambda x: x['device'])
        yamlinfo['disks'] = sorted(yamlinfo['disks'], key=lambda x: x['device'])
        if debug:
            yamlinfo['debug'] = vm_config
        return yamlinfo

    def delete(self, name, snapshots=False):
        vm_info = self._get_vm_info(name)
        if not vm_info:
            return {"result": "failure", "reason": f"VM {name} not found."}
        if vm_info["status"] == "running":
            self.stop(name, soft=False)
        vm = self.conn.nodes(vm_info["node"]).qemu(vm_info["vmid"])
        ok, status = self._wait_for(vm.delete())
        if not ok:
            return {"result": "failure", "reason": status}
        return {"result": "success"}

    def stop(self, name, soft=False):
        vm = self._get_vm(name)
        if vm is None:
            return {"result": "failure", "reason": f"VM {name} not found."}
        if soft:
            self._wait_for(vm.status.shutdown.post())
        else:
            self._wait_for(vm.status.stop.post())
        return {"result": "success"}

    def start(self, name):
        vm = self._get_vm(name)
        if vm is None:
            return {"result": "failure", "reason": f"VM {name} not found."}
        self._wait_for(vm.status.start.post())
        return {"result": "success"}

    def update_memory(self, name, memory):
        vm = self._get_vm(name)
        if vm is None:
            return {"result": "failure", "reason": f"VM {name} not found."}
        self._wait_for(vm.config.post(memory=memory))
        return {"result": "success"}

    def list_pools(self):
        return self._get_storages().keys()

    def list_networks(self):
        nets = {}
        nodes = self.conn.cluster.resources.get(type="node")
        for n in nodes:
            if n["status"] == "online":
                node_nets = self.conn.nodes(n["node"]).network.get(type="any_bridge")
                for net in node_nets:
                    if "active" in net and net["active"]:
                        netname = f"{n['node']}/{net['iface']}"
                        nets[netname] = {
                            "cidr": net.get("cidr", ""),
                            "dhcp": True,
                            "type": "bridged",
                            "mode": "N/A",
                        }

        return nets

    def list_disks(self):
        storages = self._get_storages()
        disks = {}
        for pool, pool_info in storages.items():
            node = pool_info["node"].split(",")[0]
            images = (
                self.conn.nodes(node)
                .storage(pool.split("/")[-1])
                .content.get(content="images")
            )
            for image in images:
                filename = os.path.basename(image["volid"].split(":")[-1])
                disks[filename] = {"pool": pool, "path": image["volid"]}
        return disks

    def ip(self, name):
        info = self.info(name)
        if info and "ip" in info:
            return info["ip"]
        return None

    def get_pool_path(self, pool):
        storages = self.conn.storage.get()
        node = None
        if "/" in pool:
            node, pool = pool.split("/")

        storage = None
        for s in storages:
            if s["storage"] == pool:
                storage = s
                break
        if not storage:
            return {"result": "failure", "reason": f"pool {pool} not found."}

        if "path" in storage:
            return storage["path"]
        if storage["type"] in ["lvm", "lvmthin"]:
            return f"[{storage['type']}] vg:{storage['vgname']}"

        return f"[{storage['type']}]"

    def _get_storages(self):
        all_storages = self.conn.cluster.resources.get(type="storage")

        storages = {}
        for storage in all_storages:
            if storage["status"] != "available" or "images" not in storage["content"]:
                continue
            if storage["shared"] == 0:
                storage_name = f"{storage['node']}/{storage['storage']}"
            else:
                storage_name = storage["storage"]
            if storage_name in storages:
                storages[storage_name]["node"] = ",".join(
                    storages[storage_name]["node"].split(",") + [
                        storage["node"],
                    ]
                )
            else:
                free_size = sizeof_fmt(storage["maxdisk"] - storage["disk"])
                total_size = sizeof_fmt(storage["maxdisk"])
                storages[storage_name] = {
                    "type": storage["plugintype"],
                    "node": storage["node"],
                    "size": f"{free_size} free / {total_size} total",
                }

        return storages

    def exists(self, name):
        return self._get_vm(name) is not None

    def _get_vm_info(self, name):
        all_vms = self._get_all_vms()
        for vm in all_vms:
            if "name" in vm and vm["name"] == name:
                return vm

    def _get_vm_id(self, name):
        vm_info = self._get_vm_info(name)
        return vm_info['vmid'] if vm_info is not None else None

    def _get_vm(self, name):
        for vm in self._get_all_vms():
            if vm.get("name", '') == name:
                _id, _type, _node = vm['vmid'], vm['type'], vm['node']
                return self.conn.nodes(_node).lxc(_id) if _type == 'lxc' else self.conn.nodes(_node).qemu(_id)

    def _get_all_vms(self):
        all_vms = self.conn.cluster.resources.get(type="vm")
        if self.filtertag is not None:
            return filter(lambda v: "tags" in v and self.filtertag in v["tags"], all_vms)
        else:
            return filter(lambda v: v["status"] != "unknown", all_vms)

    def _get_template_info(self, name):
        all_templates = self._get_templates()
        for template in all_templates:
            if template["name"] == name:
                return template

    def _get_templates(self):
        all_vms = self.conn.cluster.resources.get(type="vm")
        return filter(lambda v: "template" in v and v["template"] == 1, all_vms)

    def _get_isos(self):
        isos = []
        processed = []
        for node in self.conn.nodes.get():
            if node["status"] == "online":
                # list iso storage
                storages = self.conn.nodes(node["node"]).storage.get(content="iso")
                for storage in storages:
                    if storage["shared"] == 1:
                        storage_name = storage["storage"]
                    else:
                        storage_name = f"{node['node']}-{storage['storage']}"
                    if storage_name not in processed:
                        for image in (
                            self.conn.nodes(node["node"])
                            .storage(storage["storage"])
                            .content.get(content="iso")
                        ):
                            image["name"] = os.path.basename(
                                image["volid"].split(":")[-1]
                            )
                            image["pool"] = storage["storage"]
                            isos.append(image)
                        processed.append(storage_name)
        return isos

    def _get_iso_info(self, name):
        all_isos = self._get_isos()
        for iso in all_isos:
            if iso["name"] == name:
                return iso

    def _wait_for(self, task):
        ret = Tasks.blocking_status(self.conn, task, polling_interval=1)
        exitstatus = ret["exitstatus"]
        if exitstatus.endswith("OK") or exitstatus.startswith("WARNING"):
            return True, None
        return False, exitstatus

    def _parse_notes(self, notes):
        data = {}
        if notes is None:
            return data
        for entry in notes.split(','):
            desc = entry.split('=')
            if len(desc) == 2:
                field, value = desc
                data[field] = value
        return data

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        print("not implemented")
        return {'result': 'success'}

    def update_subnet(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_dns_zones(self):
        print("not implemented")
        return []

    def list_security_groups(self, network=None):
        print("not implemented")
        return []

    def create_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_security_group(self, name):
        print("not implemented")
        return {'result': 'success'}

    def update_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        vm_info = self._get_vm_info(name)
        if vm_info is None:
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        vm_id = os.path.basename(vm_info['id'])
        vmurl = f"https://{self.host}:8006/?console=kvm&novnc=1&vmid={vm_id}&vmname={name}&node=pve&resize=off"
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = f"Open the following url:\n{vmurl}" if os.path.exists("/i_am_a_container") else vmurl
            pprint(msg)
        else:
            pprint(f"Opening url {vmurl}")
            webbrowser.open(vmurl, new=2, autoraise=True)

    def serialconsole(self, name, web=False):
        return self.console(name)

    def _get_default_network(self, node):
        networks = self.list_networks()
        for n_name, n in networks.items():
            if n_name.split("/")[0] == node:
                return n_name.split("/")[1]

    def update_metadata(self, name, metatype, metavalue, append=False):
        vm = self._get_vm(name)
        if vm is None:
            return {"result": "failure", "reason": f"VM {name} not found."}
        vm_config = vm.config.get()
        description = self._parse_notes(vm_config.get("description"))
        if metatype not in description or metavalue is None or description[metatype] != metavalue:
            if metavalue is None:
                del description[metatype]
            else:
                description[metatype] = metavalue
            description = [f"{key}={description[key]}" for key in description]
            description = ','.join(description)
            vm_data = {'name': name, 'description': description}
            self._wait_for(vm.config.post(**vm_data))

    def _upload_file(self, node_ip, path, data):
        target_dir = "/var/lib/vz/snippets/"

        # Ensure the target directory exists on the remote system
        try:
            check_call(
                f"ssh -q root@{node_ip} 'mkdir -p {target_dir} && test -d {target_dir}'",
                shell=True
            )
        except CalledProcessError as e:
            raise RuntimeError(f"Failed to ensure directory {target_dir} exists on {node_ip}: {e}")

        # Create a temporary file and upload it
        with TemporaryDirectory() as tmpdir:
            temp_file_path = os.path.join(tmpdir, path)
            with open(temp_file_path, "w") as f:
                f.write(data)

            scp_cmd = f"scp -q {temp_file_path} root@{node_ip}:{target_dir}{path}"
            try:
                return call(scp_cmd, shell=True)
            except CalledProcessError as e:
                raise RuntimeError(f"Failed to upload file {temp_file_path} to {target_dir}: {e}")

    def _get_current_disks(self, vm_config):
        disks = []
        for entry in vm_config:
            if re.findall(r"(scsi|ide|virtio)\d+", entry):
                device = entry
                disk_data = vm_config[entry].split(',')
                path = disk_data[0]
                disktype, disksize = disk_data[-1].split('=')
                disksize = 1 if disksize.endswith('M') else int(disksize.replace('G', ''))
                if disktype == 'media':
                    continue
                disks.append({'name': device, 'size': disksize, 'path': path, 'full': vm_config[entry]})
        return disks

    def _get_lxc(self, name):
        for container in self.conn.nodes(self.node).lxc.get():
            if container['name'] == name:
                container_id = container['vmid']
                return self.conn.nodes(self.node).lxc(container_id)

    def create_container(self, name, image, nets=None, cmds=[], ports=[], volumes=[], environment=[], label=None,
                         overrides={}):
        print("NOT IMPLEMENTED")
        return {'result': 'success'}

    def delete_container(self, name):
        container = self._get_lxc(name)
        if container is None:
            return {"result": "failure", "reason": f"Container {name} not found."}
        self._wait_for(container.status.stop.post())
        self._wait_for(container.delete())
        return {'result': 'success'}

    def start_container(self, name):
        container = self._get_lxc(name)
        if container is None:
            return {"result": "failure", "reason": f"Container {name} not found."}
        self._wait_for(container.status.start.post())
        return {'result': 'success'}

    def stop_container(self, name):
        container = self._get_lxc(name)
        if container is None:
            return {"result": "failure", "reason": f"Container {name} not found."}
        self._wait_for(container.status.stop.post())
        return {'result': 'success'}

    def console_container(self, name):
        container = self._get_lxc(name)
        if container is None:
            error(f"Container {name} not found")
            return {'result': 'failure', 'reason': f"Container {name} not found"}
        cont_id = container.status.current.get().get('vmid')
        container_url = f"https://{self.host}:8006/?console=lxc&xtermjs=1&vmid={cont_id}&vmname={name}&node=pve&cmd="
        if self.debug or os.path.exists("/i_am_a_container"):
            msg = f"Open the following url:\n{container_url}" if os.path.exists("/i_am_a_container") else container_url
            pprint(msg)
        else:
            pprint(f"Opening url {container_url}")
            webbrowser.open(container_url, new=2, autoraise=True)
        return {'result': 'success'}

    def list_containers(self):
        containers = []
        for container in self.conn.nodes(self.node).lxc.get():
            name = container['name']
            state = container['status']
            state = 'up' if state.split(' ')[0].startswith('running') else 'down'
            lxc_info = self._get_lxc_info(name, self._get_vm(name).config.get())
            ip, ports, deploy = lxc_info['ip'], '', ''
            plan, image = lxc_info.get('plan', ''), lxc_info.get('image', '')
            containers.append([name, state, image, plan, ip, ports, deploy])
        return containers

    def exists_container(self, name):
        return len([cont for cont in self.conn.nodes(self.node).lxc.get() if cont['name'] == name]) > 0

    def list_images(self):
        images = []
        for storage in self.conn.nodes(self.node).storage.get(content="vztmpl"):
            templates = self.conn.nodes(self.node).storage(storage['storage']).content.get()
            images.extend([item['volid'] for item in templates if item.get("content") == "vztmpl"])
        return sorted(images)

    def _get_lxc_info(self, name, config=None):
        ips = []
        yamlinfo = {'name': config['hostname'], 'memory': config['memory'], 'numcpus': config['cores'], 'nets': []}
        for net in [key for key in config if key.startswith('net')]:
            net = self._parse_notes(config[net])
            device, mac, network, networktype = net['name'], net['hwaddr'].lower(), net['bridge'], net['type']
            yamlinfo['nets'].append({'device': device, 'mac': mac.lower(), 'net': network, 'type': networktype})
            ip = net['ip'].split('/')[0]
            if 'ip' not in yamlinfo:
                yamlinfo['ip'] = ip
            ips.append(ip)
        if len(ips) > 1:
            yamlinfo['ips'] = ips
        path, size = config['rootfs'].split(',')
        disksize = size.replace('size=', '')
        disk = {'device': 'rootfs', 'size': disksize, 'format': 'raw', 'type': 'virtio', 'path': path}
        yamlinfo['disks'] = [disk]
        if 'description' in config:
            description = self._parse_notes(config['description'])
            if 'plan' in description:
                yamlinfo['plan'] = description['plan']
            if 'image' in description:
                yamlinfo['image'] = description['image']
        return yamlinfo

    def detach_disks(self, name):
        print("not implemented")
        return {'result': 'success'}
