# -*- coding: utf-8 -*-

from kvirt.common import (
    pprint,
    warning,
    get_user,
    cloudinit as gen_cloudinit,
    ignition as gen_ignition,
    needs_ignition,
    netmask_to_prefix,
    ignition_version,
)

from kvirt.providers.sampleprovider import Kbase
import proxmoxer
from proxmoxer.tools import Tasks
import urllib3
import re
import time
from textwrap import dedent
import os
from subprocess import call
from pprint import pprint as pp
from tempfile import TemporaryDirectory
from pathlib import Path


VM_STATUS = {"running": "up", "stopped": "down", "unknown": "unk"}


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
        if not verify_ssl:
            urllib3.disable_warnings()

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
        # self.host = host

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
        all_vms = self._get_vms()
        for vm in all_vms:
            ips = []
            if vm["status"] == "running":
                try:
                    nets = (
                        self.conn.nodes(vm["node"])
                        .qemu(vm["vmid"])
                        .agent("network-get-interfaces")
                        .get()["result"]
                    )
                except proxmoxer.core.ResourceException:
                    nets = []
                    pass
                for net in nets:
                    if net["name"] != "lo" and "ip-addresses" in net:
                        for nic in net["ip-addresses"]:
                            if nic["ip-address-type"] == "ipv4":
                                ips.append(nic["ip-address"])
            try:
                vm_config = self.conn.nodes(vm["node"]).qemu(vm["vmid"]).config.get()
            except:
                continue
            metadata = self._parse_notes(vm_config.get("description"))

            vms.append(
                dict(
                    {
                        "name": vm["name"],
                        "status": VM_STATUS.get(vm["status"]),
                        "ip": ",".join(ips),
                    },
                    **metadata,
                )
            )
        return vms

    def volumes(self, iso=False):
        # return iso or vm templates
        vols = []
        if iso:
            vols = [t["name"] for t in self._get_isos()]
        else:
            vols = [t["name"] for t in self._get_templates()]

        return vols

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
            pprint(f"Template {name} already there")
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
            return {
                "result": "failure",
                "reason": f"node {self.node} not found.",
            }

        # Check that template storage is available on this node
        if not self._check_storage(pool, node=pve_node["name"]):
            return {
                "result": "failure",
                "reason": f"storage {pool} not found on {pve_node['name']}.",
            }

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
        description = f"""
            Template created with kcli from {shortimage} on {now}
            """

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
        pprint(f"Template {name} created on {pve_node['name']}")

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
        if not template:
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
            pprint(f"ISO {image} not found")
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
            return {
                "result": "failure",
                "reason": f"node {pve_node} not found.",
            }

        # Check that template storage is available on this node
        if not self._check_storage(pool, node=pve_node):
            return {
                "result": "failure",
                "reason": f"storage {pool} not found on {pve_node}.",
            }

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
        # pp(locals())

        # Check if vm already exists
        vm = self._get_vm_info(name)
        if vm:
            return {"result": "failure", "reason": f"VM {name} already exists."}

        # Get next available ID
        new_vmid = self.conn.cluster.nextid.get()
        imagepool = self.imagepool if self.imagepool else pool

        if image:
            # Get image template
            template = self._get_template_info(image)
            if not template:
                return {
                    "result": "failure",
                    "reason": f"image {image} not found. Use kcli download image {image}.",
                }
        if iso:
            isos = [
                i
                for i in self._get_isos()
                if i["name"] == iso and i["pool"] == imagepool
            ]
            if not isos:
                pprint(f"ISO {iso} not found")
                return {"result": "failure", "reason": f"ISO {iso} not found"}

        # Check target node
        new_vmnode = overrides.get("node") or self.node or template["node"]
        cluster_status = self.conn.cluster.status.get()
        for n in cluster_status:
            if n["type"] == "node" and n["name"] == new_vmnode:
                pve_node = n
                break
        if not pve_node:
            return {
                "result": "failure",
                "reason": f"node {new_vmnode} not found.",
            }

        # Check pool storage
        storages = self.conn.nodes(new_vmnode).storage.get(content="images")
        storage = None
        for s in storages:
            if s["storage"] == pool:
                storage = s
        if not storage:
            return {
                "result": "failure",
                "reason": f"storage {pool} not found on {new_vmnode}.",
            }

        if image:
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
                    target=new_vmnode,
                    storage=pool if not linked_clone else None,
                    full=int(not linked_clone),
                )
            )
        elif iso:
            # Create empty VM
            ok, status = self._wait_for(
                self.conn.nodes(new_vmnode).qemu.post(
                    vmid=new_vmid,
                    name=name,
                    scsihw="virtio-scsi-pci",
                    virtio0=f"file={pool}:{disksize},format=qcow2",
                )
            )
            if not ok:
                return {"result": "failure", "reason": status}
        else:
            return {"result": "failure", "reason": "No ISO or image specified."}

        new_vm = self.conn.nodes(new_vmnode).qemu(new_vmid)

        # Add tag
        if self.filtertag:
            new_vm.config.post(tags=self.filtertag)

        # Metadata
        now = time.strftime("%d-%m-%Y %H:%M", time.gmtime())
        metadata["creationdate"] = now
        metadata["user"] = vmuser or get_user(image) if image is not None else "root"
        description = ""
        for entry in [field for field in metadata]:
            description += f"  \nkvirt:{entry}: {metadata[entry]}"

        if metadata["user"] == "root":
            enableroot = True

        if image:
            if needs_ignition(image):
                self._set_ignition(
                    vmid=new_vmid,
                    name=name,
                    node_name=new_vmnode,
                    node_ip=pve_node["ip"],
                    pool=pool,
                    keys=keys,
                    cmds=cmds,
                    nets=nets,
                    gateway=gateway,
                    dns=dns,
                    domain=domain,
                    files=files,
                    enableroot=enableroot,
                    overrides=overrides,
                    storemetadata=storemetadata,
                    image=image,
                    vmuser=vmuser,
                )
            else:
                # Cloud-Init
                self._set_cloudinit(
                    vmid=new_vmid,
                    name=name,
                    node_name=new_vmnode,
                    node_ip=pve_node["ip"],
                    pool=pool,
                    keys=keys,
                    cmds=cmds,
                    nets=nets,
                    gateway=gateway,
                    dns=dns,
                    domain=domain,
                    files=files,
                    enableroot=enableroot,
                    overrides=overrides,
                    storemetadata=storemetadata,
                    image=image,
                    vmuser=vmuser,
                )

        if cpumodel == "host-model":
            cpumodel = "host"

        # Network
        net0 = []
        net0.append("model=virtio")

        if nets and "name" in nets[0] and nets[0]["name"] != "default":
            bridge = nets[0]["name"]
        else:
            # Take the first bridge available on the target node
            networks = self.list_networks()
            for n_name, n in networks.items():
                if n_name.split("/")[0] == new_vmnode:
                    bridge = n_name.split("/")[1]
                    break
        if bridge:
            net0.append(f"bridge={bridge}")

        # Configure VM
        self._wait_for(
            new_vm.config.post(
                name=name,
                cores=numcpus,
                memory=memory,
                cpu=cpumodel,
                agent="enabled=1",
                net0=",".join(net0),
                description=dedent(description),
            )
        )

        # Disks
        default_disksize = disksize
        for index, disk in enumerate(disks):
            diskname = f"virtio{index}"
            if isinstance(disk, int):
                disksize = disk
            elif isinstance(disk, dict):
                disksize = disk.get("size", default_disksize)
            else:
                disksize = default_disksize
            if index == 0:
                # Extend main disk
                new_vm.resize.put(disk=diskname, size=f"{disksize}G")
            else:
                self._wait_for(
                    new_vm.config.post(
                        **{diskname: f"file={pool}:{disksize},format=qcow2"}
                    )
                )

        # Add ISO
        if iso:
            self._wait_for(
                new_vm.config.post(cdrom=f"file={imagepool}:iso/{iso},media=cdrom")
            )

        # Start VM
        if start:
            ok, status = self._wait_for(
                self.conn.nodes(new_vmnode).qemu(new_vmid).status.start.post()
            )
            if not ok:
                return {"result": "failure", "reason": status}

        # Wait until vm info are up-to-date
        while not self._get_vm_info(name):
            time.sleep(1)

        return {"result": "success"}

    def info(self, name, output="plain", fields=[], values=False, vm=None, debug=False):
        vm_info = self._get_vm_info(name)
        if not vm_info:
            return {"result": "failure", "reason": f"VM {name} does not exists."}

        vm = self.conn.nodes(vm_info["node"]).qemu(vm_info["vmid"])
        info = {
            "name": vm_info["name"],
            "node": vm_info["node"],
            "vmid": vm_info["vmid"],
            "status": VM_STATUS.get(vm_info["status"]),
            "numcpus": vm_info["maxcpu"],
            "memory": int(vm_info["maxmem"] / 1024 / 1024),
        }
        vm_config = vm.config.get()

        net0 = vm_config.get("net0")
        mac = None
        if net0:
            mac = re.search(r"(\w+:\w+:\w+:\w+:\w+:\w+)", net0)
            if mac:
                mac = mac.group(0).lower()

        if vm_info["status"] == "running" and mac:
            try:
                nets = vm.agent("network-get-interfaces").get().get("result")
            except proxmoxer.core.ResourceException:
                nets = []
            for net in nets:
                if net["hardware-address"] == mac:
                    for nic in net.get("ip-addresses", []):
                        if nic["ip-address-type"] == "ipv4":
                            info["ip"] = nic["ip-address"]
                            break

        # metadata
        metadata = self._parse_notes(vm_config.get("description"))
        info.update(metadata)

        return info

    def delete(self, name, snapshots=False):
        info = self._get_vm_info(name)
        if not info:
            return {"result": "failure", "reason": f"VM {name} not found."}

        if info["status"] == "running":
            # stop vm
            self.stop(name, soft=False)

        vm = self.conn.nodes(info["node"]).qemu(info["vmid"])
        # delete
        ok, status = self._wait_for(vm.delete())
        if not ok:
            return {"result": "failure", "reason": status}
        return {"result": "success"}

    def stop(self, name, soft=False):
        vm = self._get_vm(name)
        if not vm:
            return {"result": "failure", "reason": f"VM {name} not found."}

        if soft:
            self._wait_for(vm.status.shutdown.post())
        else:
            self._wait_for(vm.status.stop.post())
        return {"result": "success"}

    def start(self, name):
        vm = self._get_vm(name)
        if not vm:
            return {"result": "failure", "reason": f"VM {name} not found."}

        self._wait_for(vm.status.start.post())
        return {"result": "success"}

    def update_memory(self, name, memory):
        vm = self._get_vm(name)
        if not vm:
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
                            "cidr": net["cidr"],
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
        pp(info)
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
        return True if self._get_vm(name) else False

    def _get_vm_info(self, name):
        all_vms = self._get_vms()
        for vm in all_vms:
            if "name" in vm and vm["name"] == name:
                return vm
        return None

    def _get_vm(self, name):
        vm = self._get_vm_info(name)
        if vm:
            return self.conn.nodes(vm["node"]).qemu(vm["vmid"])

    def _get_vms(self):
        all_vms = self.conn.cluster.resources.get(type="vm")
        if self.filtertag is not None:
            return filter(
                lambda v: "tags" in v and self.filtertag in v["tags"], all_vms
            )
        else:
            return filter(lambda v: v["status"] != "unknown", all_vms)

    def _get_template_info(self, name):
        all_templates = self._get_templates()
        for template in all_templates:
            if template["name"] == name:
                return template
        return None

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
        return None

    def _wait_for(self, task):
        ret = Tasks.blocking_status(self.conn, task, polling_interval=1)
        if not ret["exitstatus"].endswith("OK"):
            return False, ret["exitstatus"]

        return True, None

    def _parse_notes(self, notes):
        values = {}
        if notes:
            for line in notes.splitlines():
                match = re.search(r"^kvirt:(\w+): (.*)$", line)
                if match:
                    values[match.group(1)] = match.group(2).strip()

        return values

    def _set_cloudinit(
        self,
        vmid,
        name=None,
        node_name=None,
        node_ip=None,
        pool=None,
        keys=[],
        cmds=[],
        nets=[],
        gateway=None,
        dns=None,
        domain=None,
        files=[],
        enableroot=False,
        overrides={},
        storemetadata=True,
        image=None,
        vmuser=None,
    ):
        # Make sure guest-agent is installed on debian/ubuntu as we need it to retrieve IP
        if "ubuntu" in image or "debian" in image:
            gcmds = ["ip a > /dev/tty1; sleep 5"]
            gcmds.append("apt-get update")
            gcmds.append("apt-get -y install qemu-guest-agent")
            gcmds.append("/etc/init.d/qemu-guest-agent start")
            gcmds.append("update-rc.d qemu-guest-agent defaults")
            cmds = gcmds + cmds

        # Generate userdata & metadata
        userdata, metadata, _ = gen_cloudinit(
            name=name,
            keys=keys,
            cmds=cmds,
            files=files,
            enableroot=enableroot,
            overrides=overrides,
            storemetadata=storemetadata,
            image=image,
            vmuser=vmuser,
        )

        # Use proxmox's buitin network configuration
        vm = self.conn.nodes(node_name).qemu(vmid)
        net0 = []
        if nets and "ip" in nets[0] and "mask" in nets[0]:
            cidr = netmask_to_prefix(nets[0]["mask"])
            net0.append(f"ip={nets[0]['ip']}/{cidr}")
        else:
            net0.append("ip=dhcp")
        if nets and "gateway" in nets[0]:
            net0.append(f"gw={nets[0]['gateway']}")

        # Send generated cloudinit files to pve node
        with TemporaryDirectory() as tmpdir:
            with open(f"{tmpdir}/{vmid}-cloudinit-userdata.yaml", "w") as f:
                f.write(userdata)
            with open(f"{tmpdir}/{vmid}-cloudinit-metadata.yaml", "w") as f:
                f.write(metadata)

            snippetspath = "/var/lib/vz/snippets/"
            ssh_user = "root"

            scpcmd = f"scp {tmpdir}/{vmid}-cloudinit-*.yaml {ssh_user}@{node_ip}:{snippetspath}"
            pprint(f"Uploading cloudinit files for {name} on {node_name}...")
            code = call(scpcmd, shell=True)
            if code != 0:
                return {
                    "result": "failure",
                    "reason": "Unable to upload cloudinit files",
                }

        ci = f"meta=local:snippets/{vmid}-cloudinit-metadata.yaml,user=local:snippets/{vmid}-cloudinit-userdata.yaml"
        self._wait_for(
            vm.config.post(
                cicustom=ci,
                ipconfig0=",".join(net0),
                ide0=f"{pool}:cloudinit",
                serial0="socket",
            )
        )

    def _set_ignition(
        self,
        vmid,
        name=None,
        node_name=None,
        node_ip=None,
        pool=None,
        keys=[],
        cmds=[],
        nets=[],
        gateway=None,
        dns=None,
        domain=None,
        files=[],
        enableroot=False,
        overrides={},
        storemetadata=True,
        image=None,
        vmuser=None,
    ):
        # Generate ignition data
        version = ignition_version(image)
        ignitiondata = gen_ignition(
            name=name,
            keys=keys,
            cmds=cmds,
            nets=nets,
            gateway=gateway,
            dns=dns,
            domain=domain,
            files=files,
            enableroot=enableroot,
            overrides=overrides,
            version=version,
            image=image,
            vmuser=vmuser,
        )

        # Send generated ignition file to pve node
        with TemporaryDirectory() as tmpdir:
            with open(f"{tmpdir}/{vmid}-ignition.ign", "w") as f:
                f.write(ignitiondata)

            snippetspath = "/var/lib/vz/snippets/"
            ssh_user = "root"

            scpcmd = (
                f"scp {tmpdir}/{vmid}-ignition.ign {ssh_user}@{node_ip}:{snippetspath}"
            )
            pprint(f"Uploading ignition file for {name} on {node_name}...")
            code = call(scpcmd, shell=True)
            if code != 0:
                return {
                    "result": "failure",
                    "reason": "Unable to upload ignition file",
                }

        # Configure Ignition through fw_cfg arg
        vm = self.conn.nodes(node_name).qemu(vmid)
        self._wait_for(
            vm.config.post(
                args=f"-fw_cfg name=opt/com.coreos/config,file={snippetspath}{vmid}-ignition.ign"
            )
        )

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
        print("not implemented")

    def serialconsole(self, name, web=False):
        print("not implemented")
