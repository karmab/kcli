# -*- coding: utf-8 -*-

from kvirt import common
from kvirt.common import pprint, error, warning
import base64
import json
import os
import plistlib
import subprocess
from shutil import which, copy2
from tempfile import TemporaryDirectory
from time import sleep
import struct
import uuid


UTM_POOL_DIR = os.path.expanduser('~/.kcli/utm/pool')
UTM_IMAGES_DIR = os.path.expanduser('~/.kcli/utm/images')
UTM_DOCUMENTS_DIR = os.path.expanduser('~/Library/Containers/com.utmapp.UTM/Data/Documents')
UTM_GALLERY_URL = 'https://mac.getutm.app/gallery/'


def _osascript(script):
    cmd = ['osascript', '-e', script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _osascript_lines(script):
    output = _osascript(script)
    if not output:
        return []
    return output.split(', ')


def _qcow2_virtual_size(path):
    try:
        with open(path, 'rb') as f:
            magic = f.read(4)
            if magic != b'QFI\xfb':
                return 0
            f.seek(24)
            return struct.unpack('>Q', f.read(8))[0]
    except Exception:
        return 0


def _find_vm_qcow2_files(vm_name):
    data_dir = os.path.join(UTM_DOCUMENTS_DIR, f"{vm_name}.utm", "Data")
    if not os.path.isdir(data_dir):
        return []
    return sorted([os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.qcow2')])


class Kutm(object):
    def __init__(self, debug=False):
        self.conn = None
        self.debug = debug
        if which('osascript') is None:
            error("osascript not found. UTM provider only works on macOS")
            return
        os.makedirs(UTM_POOL_DIR, exist_ok=True)
        os.makedirs(UTM_IMAGES_DIR, exist_ok=True)
        try:
            _osascript('tell application "UTM" to get UTM version')
            self.conn = 'utm'
        except Exception as e:
            error(f"Could not connect to UTM. Make sure UTM is running: {e}")

    def close(self):
        return

    def exists(self, name):
        try:
            script = '''tell application "UTM"
set vmNames to name of every virtual machine
return vmNames
end tell'''
            output = _osascript(script)
            return name in [n.strip() for n in output.split(', ')] if output else False
        except Exception:
            return False

    def net_exists(self, name):
        return True

    def disk_exists(self, pool, name):
        diskpath = f"{UTM_POOL_DIR}/{name}"
        return os.path.exists(diskpath)

    def _get_vm_id(self, name):
        script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
return id of vm
end tell'''
        return _osascript(script)

    def _get_vm_status(self, name):
        script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
return status of vm as string
end tell'''
        return _osascript(script).strip()

    def _get_vm_notes(self, name):
        script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
return notes of config
end tell'''
        try:
            notes = _osascript(script)
            if not notes:
                return {}
            if notes.startswith('kcli:'):
                decoded = base64.b64decode(notes[5:]).decode('utf-8')
                return json.loads(decoded)
            return json.loads(notes)
        except Exception:
            return {}

    def _set_vm_notes(self, name, metadata):
        encoded = base64.b64encode(json.dumps(metadata).encode('utf-8')).decode('utf-8')
        notes_str = f"kcli:{encoded}"
        script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set notes of config to "{notes_str}"
update configuration of vm with config
end tell'''
        _osascript(script)

    def _wait_for_status(self, name, target_status, timeout=120):
        for _ in range(timeout):
            try:
                status = self._get_vm_status(name)
                if status == target_status:
                    return True
            except Exception:
                pass
            sleep(1)
        return False

    @staticmethod
    def _disk_size(disk, default):
        if isinstance(disk, int):
            return disk
        elif isinstance(disk, str) and disk.isdigit():
            return int(disk)
        elif isinstance(disk, dict):
            return disk.get('size', default)
        return default

    @staticmethod
    def _disk_interface(interface):
        mapping = {'virtio': 'VirtIO', 'nvme': 'NVMe', 'scsi': 'SCSI', 'ide': 'IDE', 'usb': 'USB', 'sd': 'SD'}
        return mapping.get(interface.lower(), 'VirtIO') if interface else 'VirtIO'

    def _build_net_parts(self, nets):
        net_parts = []
        mode_mapping = {'bridge': 'bridged', 'bridged': 'bridged', 'emulated': 'emulated',
                        'host': 'host', 'host-only': 'host', 'shared': 'shared', 'default': 'shared'}
        for net in nets:
            if isinstance(net, str):
                mac = common.gen_mac()
                mode = mode_mapping.get(net, 'shared')
                if mode == 'bridged':
                    net_parts.append(f'{{mode:bridged, address:"{mac}", host interface:"en0"}}')
                else:
                    net_parts.append(f'{{mode:{mode}, address:"{mac}"}}')
            elif isinstance(net, dict):
                mac = net.get('mac', common.gen_mac())
                model = net.get('model', '')
                net_name = net.get('name', 'default')
                mode = mode_mapping.get(net_name, 'shared')
                props = []
                if mode == 'bridged':
                    host_if = net.get('bridge', 'en0')
                    props.append(f'mode:bridged, host interface:"{host_if}"')
                else:
                    props.append(f'mode:{mode}')
                props.append(f'address:"{mac}"')
                if model:
                    props.append(f'hardware:"{model}"')
                net_parts.append('{' + ', '.join(props) + '}')
        if not net_parts:
            mac = common.gen_mac()
            net_parts.append(f'{{mode:shared, address:"{mac}"}}')
        return net_parts

    def _add_disk(self, name, size, interface='VirtIO'):
        script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allDrives to drives of config
set newDrives to {{}}
repeat with d in allDrives
    copy d to end of newDrives
end repeat
copy {{guest size:{size * 1024}, interface:{interface}}} to end of newDrives
set drives of config to newDrives
update configuration of vm with config
end tell'''
        _osascript(script)

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[],
               cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False,
               numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[],
               vmuser=None, guestagent=True):
        if self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} already exists"}
        net_parts = self._build_net_parts(nets)
        if image is not None:
            template = self._find_template(image)
            if template is None:
                return {'result': 'failure', 'reason': f"Template VM {image} not found. Use kcli download image first"}
            try:
                nets_str = '{' + ', '.join(net_parts) + '}'
                script = f'''tell application "UTM"
set vm to virtual machine named "{template}"
duplicate vm with properties {{configuration:{{name:"{name}", memory:{memory}, cpu cores:{numcpus}, network interfaces:{nets_str}}}}}
end tell'''
                if self.debug:
                    pprint(f"AppleScript: {script}")
                _osascript(script)
            except Exception as e:
                return {'result': 'failure', 'reason': f"Failed to create VM {name} from template {template}: {e}"}
            first_disk_size = self._disk_size(disks[0], disksize)
            existing_qcow2 = set(_find_vm_qcow2_files(name))
            if existing_qcow2 and first_disk_size:
                self.resize_disk(sorted(existing_qcow2)[0], first_disk_size)
            if len(disks) > 1:
                for disk in disks[1:]:
                    size = self._disk_size(disk, disksize)
                    interface = disk.get('interface', diskinterface) if isinstance(disk, dict) else diskinterface
                    interface_str = self._disk_interface(interface)
                    self._add_disk(name, size, interface_str)
                    new_qcow2 = set(_find_vm_qcow2_files(name)) - existing_qcow2
                    if new_qcow2:
                        new_file = new_qcow2.pop()
                        self.resize_disk(new_file, size)
                        existing_qcow2.add(new_file)
        else:
            drives_parts = []
            for disk in disks:
                size = self._disk_size(disk, disksize)
                interface = disk.get('interface', diskinterface) if isinstance(disk, dict) else diskinterface
                interface_str = self._disk_interface(interface)
                drives_parts.append(f'{{guest size:{size * 1024}, interface:{interface_str}}}')
            if iso is not None:
                iso_path = iso if os.path.isabs(iso) else f"{UTM_POOL_DIR}/{iso}"
                if os.path.exists(iso_path):
                    drives_parts.append(f'{{removable:true, source:POSIX file "{iso_path}"}}')
                else:
                    warning(f"ISO {iso} not found at {iso_path}")
            drives_str = '{' + ', '.join(drives_parts) + '}'
            nets_str = '{' + ', '.join(net_parts) + '}'
            script = f'''tell application "UTM"
set vm to make new virtual machine with properties {{backend:qemu, configuration:{{name:"{name}", architecture:"aarch64", memory:{memory}, cpu cores:{numcpus}, drives:{drives_str}, network interfaces:{nets_str}, displays:{{{{hardware:"virtio-gpu-gl-pci"}}}}, hypervisor:true}}}}
end tell'''
            try:
                if self.debug:
                    pprint(f"AppleScript: {script}")
                _osascript(script)
            except Exception as e:
                return {'result': 'failure', 'reason': f"Failed to create VM {name}: {e}"}
        vm_metadata = {'plan': plan, 'profile': profile, 'image': image or '', 'user': common.getuser(),
                       'creationdate': common.datetime.now().strftime('%d-%m-%Y %H:%M'), 'domain': domain or '',
                       'tags': tags}
        vm_metadata.update(metadata)
        try:
            self._set_vm_notes(name, vm_metadata)
        except Exception as e:
            warning(f"Could not set metadata for {name}: {e}")
        if cloudinit and image is not None:
            needs_ignition = common.needs_ignition(image)
            if needs_ignition:
                version = common.ignition_version(image)
                userdata = common.ignition(name=name, keys=keys, cmds=cmds, nets=nets, gateway=gateway,
                                           dns=dns, domain=domain, files=files, enableroot=enableroot,
                                           overrides=overrides, version=version, plan=plan, image=image,
                                           vmuser=vmuser)
                metadata_ci, netdata = userdata, None
            else:
                userdata, metadata_ci, netdata = common.cloudinit(name=name, keys=keys, cmds=cmds, nets=nets,
                                                                  gateway=gateway, dns=dns, domain=domain,
                                                                  files=files, enableroot=enableroot,
                                                                  overrides=overrides, storemetadata=storemetadata,
                                                                  image=image, vmuser=vmuser)
            with TemporaryDirectory() as tmpdir:
                result = common.make_iso(name, tmpdir, userdata, metadata_ci, netdata, openstack=needs_ignition)
                if result != 0:
                    error("Hit issue when creating cloud-init iso")
                else:
                    cloudinitiso = f"{UTM_POOL_DIR}/{name}.ISO"
                    copy2(f"{tmpdir}/{name}.ISO", cloudinitiso)
                    try:
                        self._attach_iso(name, cloudinitiso)
                    except Exception as e:
                        warning(f"Could not attach cloud-init ISO to {name}: {e}")
        if start:
            self.start(name)
        return {'result': 'success'}

    def _find_template(self, image):
        try:
            script = '''tell application "UTM"
set vmNames to name of every virtual machine
return vmNames
end tell'''
            output = _osascript(script)
            if not output:
                return None
            vm_names = [n.strip() for n in output.split(', ')]
            if image in vm_names:
                return image
            for vm_name in vm_names:
                if image.lower() in vm_name.lower():
                    return vm_name
            return None
        except Exception:
            return None

    def _attach_iso(self, name, iso_path):
        script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allDrives to drives of config
set newDrives to {{}}
repeat with d in allDrives
    copy d to end of newDrives
end repeat
copy {{removable:true, source:POSIX file "{iso_path}"}} to end of newDrives
set drives of config to newDrives
update configuration of vm with config
end tell'''
        _osascript(script)

    def start(self, name):
        try:
            status = self._get_vm_status(name)
        except Exception as e:
            return {'result': 'failure', 'reason': f"VM {name} not found: {e}"}
        if status == 'started':
            return {'result': 'success'}
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
start vm
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': f"Failed to start VM {name}: {e}"}

    def stop(self, name, soft=False):
        try:
            status = self._get_vm_status(name)
        except Exception as e:
            return {'result': 'failure', 'reason': f"VM {name} not found: {e}"}
        if status == 'stopped':
            return {'result': 'success'}
        try:
            if soft:
                script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
stop vm by request
end tell'''
                _osascript(script)
                self._wait_for_status(name, 'stopped', timeout=240)
            else:
                script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
stop vm by force
end tell'''
                _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': f"Failed to stop VM {name}: {e}"}

    def create_snapshot(self, name, base):
        return {'result': 'failure', 'reason': "Snapshots are not supported in UTM"}

    def delete_snapshot(self, name, base):
        return {'result': 'failure', 'reason': "Snapshots are not supported in UTM"}

    def list_snapshots(self, base):
        return []

    def revert_snapshot(self, name, base):
        return {'result': 'failure', 'reason': "Snapshots are not supported in UTM"}

    def restart(self, name):
        result = self.stop(name)
        if result.get('result') != 'success':
            return result
        self._wait_for_status(name, 'stopped', timeout=60)
        return self.start(name)

    def info_host(self):
        info = {}
        try:
            version = _osascript('tell application "UTM" to get UTM version')
            info['utm_version'] = version
        except Exception:
            pass
        info['cpus'] = os.cpu_count()
        try:
            mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            info['memory'] = mem_bytes // (1024 * 1024)
        except Exception:
            pass
        return info

    def status(self, name):
        try:
            status = self._get_vm_status(name)
            status_map = {'started': 'up', 'stopped': 'down', 'paused': 'down',
                          'starting': 'up', 'stopping': 'down', 'pausing': 'down', 'resuming': 'up'}
            return status_map.get(status, status)
        except Exception:
            return None

    def list(self):
        vms = []
        try:
            script = '''tell application "UTM"
set vmNames to name of every virtual machine
return vmNames
end tell'''
            output = _osascript(script)
            if not output:
                return []
            vm_names = [n.strip() for n in output.split(', ')]
        except Exception:
            return []
        for name in vm_names:
            try:
                status = self._get_vm_status(name)
                state = 'up' if status == 'started' else 'down'
                ip = ''
                if status == 'started':
                    try:
                        ip = self.ip(name) or ''
                    except Exception:
                        pass
                metadata = self._get_vm_notes(name)
                if metadata.get('template'):
                    continue
                vms.append({
                    'name': name,
                    'status': state,
                    'ip': ip,
                    'source': metadata.get('image', ''),
                    'plan': metadata.get('plan', ''),
                    'profile': metadata.get('profile', ''),
                })
            except Exception:
                continue
        return sorted(vms, key=lambda x: x['name'])

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        if not self.exists(name):
            error(f"VM {name} not found")
            return
        subprocess.Popen(['open', '-a', 'UTM'])
        pprint(f"Opening UTM console for {name}")

    def serialconsole(self, name, web=False):
        if not self.exists(name):
            error(f"VM {name} not found")
            return
        status = self._get_vm_status(name)
        if status != 'started':
            error(f"VM {name} down")
            return
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
get address of first serial port of vm
end tell'''
            address = _osascript(script)
            if address:
                if web:
                    return address
                os.system(f"screen {address}")
            else:
                error("No serial Console found. Leaving...")
        except Exception as e:
            error(f"Could not get serial console for {name}: {e}")

    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        if not self.exists(name):
            error(f"VM {name} not found")
            return {}
        yamlinfo = {'name': name}
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set vmMem to memory of config
set vmCpus to cpu cores of config
return vmMem & "|" & vmCpus
end tell'''
            result = _osascript(script)
            parts = result.split('|')
            if len(parts) >= 2:
                yamlinfo['memory'] = int(parts[0].strip().rstrip(','))
                yamlinfo['numcpus'] = int(parts[1].strip().lstrip(','))
        except Exception:
            pass
        status = self._get_vm_status(name)
        yamlinfo['status'] = 'up' if status == 'started' else 'down'
        try:
            vm_id = self._get_vm_id(name)
            yamlinfo['id'] = vm_id
        except Exception:
            pass
        metadata = self._get_vm_notes(name)
        yamlinfo['plan'] = metadata.get('plan', '')
        yamlinfo['profile'] = metadata.get('profile', '')
        yamlinfo['image'] = metadata.get('image', '')
        image = yamlinfo['image']
        yamlinfo['user'] = common.get_user(image) if image else ''
        yamlinfo['creationdate'] = metadata.get('creationdate', '')
        yamlinfo['domain'] = metadata.get('domain', '')
        yamlinfo['tags'] = metadata.get('tags', [])
        if status == 'started':
            try:
                ip = self.ip(name)
                if ip:
                    yamlinfo['ip'] = ip
            except Exception:
                pass
        yamlinfo['nets'] = []
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allNics to network interfaces of config
set nicInfo to ""
repeat with n in allNics
    set nicInfo to nicInfo & mode of n & "," & address of n & "," & hardware of n & "|"
end repeat
return nicInfo
end tell'''
            result = _osascript(script)
            if result:
                for i, entry in enumerate(result.strip().rstrip('|').split('|')):
                    parts = entry.split(',')
                    if len(parts) >= 3:
                        mode, mac, hw = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        yamlinfo['nets'].append({'device': f'eth{i}', 'mac': mac, 'net': mode, 'type': hw or 'virtio-net-pci'})
        except Exception:
            pass
        yamlinfo['disks'] = []
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allDrives to drives of config
set driveInfo to ""
repeat with d in allDrives
    set driveInfo to driveInfo & interface of d & "," & removable of d & "|"
end repeat
return driveInfo
end tell'''
            result = _osascript(script)
            if result:
                qcow2_files = _find_vm_qcow2_files(name)
                disk_index = 0
                qcow2_index = 0
                for entry in result.strip().rstrip('|').split('|'):
                    parts = entry.split(',')
                    if len(parts) >= 2:
                        iface, removable = parts[0].strip(), parts[1].strip()
                        if removable == 'true':
                            continue
                        size_gb = 0
                        disk_path = ''
                        if qcow2_index < len(qcow2_files):
                            disk_path = qcow2_files[qcow2_index]
                            vsize = _qcow2_virtual_size(disk_path)
                            size_gb = vsize // (1024 ** 3) if vsize > 0 else 0
                            qcow2_index += 1
                        device = f'vd{chr(97 + disk_index)}'
                        yamlinfo['disks'].append({'device': device, 'size': size_gb, 'format': 'qcow2',
                                                  'type': iface, 'path': disk_path})
                        disk_index += 1
        except Exception:
            pass
        if fields:
            fields = fields.split(',') if isinstance(fields, str) else fields
        common.print_info(yamlinfo, output=output, fields=fields, values=values)
        return yamlinfo

    def ip(self, name):
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set ipList to query ip of vm
return item 1 of ipList
end tell'''
            ip = _osascript(script)
            return ip if ip else None
        except Exception:
            return None

    def volumes(self, iso=False, extended=False):
        if iso:
            results = []
            if os.path.exists(UTM_IMAGES_DIR):
                for f in sorted(os.listdir(UTM_IMAGES_DIR)):
                    if f.upper().endswith('.ISO'):
                        results.append(f)
            return results
        try:
            script = '''tell application "UTM"
set vmNames to name of every virtual machine
return vmNames
end tell'''
            output = _osascript(script)
            if not output:
                return []
            results = []
            for name in sorted([n.strip() for n in output.split(', ')]):
                metadata = self._get_vm_notes(name)
                if metadata.get('template'):
                    results.append(name)
            return results
        except Exception:
            return []

    def delete(self, name, snapshots=False):
        if not self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        try:
            status = self._get_vm_status(name)
            if status != 'stopped':
                script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
stop vm by force
end tell'''
                _osascript(script)
                self._wait_for_status(name, 'stopped', timeout=60)
        except Exception:
            pass
        try:
            script = f'''tell application "UTM"
delete virtual machine named "{name}"
end tell'''
            _osascript(script)
        except Exception as e:
            return {'result': 'failure', 'reason': f"Failed to delete VM {name}: {e}"}
        disk_dir = f"{UTM_POOL_DIR}/{name}"
        if os.path.exists(disk_dir):
            import shutil
            shutil.rmtree(disk_dir, ignore_errors=True)
        cloudinitiso = f"{UTM_POOL_DIR}/{name}.ISO"
        if os.path.exists(cloudinitiso):
            os.remove(cloudinitiso)
        return {'result': 'success'}

    def dnsinfo(self, name):
        return None, None

    def clone(self, old, new, full=False, start=False):
        if not self.exists(old):
            return {'result': 'failure', 'reason': f"VM {old} not found"}
        if self.exists(new):
            return {'result': 'failure', 'reason': f"VM {new} already exists"}
        try:
            mac = common.gen_mac()
            script = f'''tell application "UTM"
set vm to virtual machine named "{old}"
duplicate vm with properties {{configuration:{{name:"{new}", network interfaces:{{{{mode:shared, address:"{mac}"}}}}}}}}
end tell'''
            _osascript(script)
        except Exception as e:
            return {'result': 'failure', 'reason': f"Failed to clone VM: {e}"}
        if start:
            self.start(new)
        return {'result': 'success'}

    def update_metadata(self, name, metatype, metavalue, append=False):
        metadata = self._get_vm_notes(name)
        if append and metatype in metadata:
            metadata[metatype] = f"{metadata[metatype]},{metavalue}"
        else:
            metadata[metatype] = metavalue
        try:
            self._set_vm_notes(name, metadata)
        except Exception as e:
            error(f"Could not update metadata: {e}")

    def update_memory(self, name, memory):
        try:
            status = self._get_vm_status(name)
            if status != 'stopped':
                return {'result': 'failure', 'reason': "VM must be stopped to update memory"}
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set memory of config to {memory}
update configuration of vm with config
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def update_cpus(self, name, numcpus):
        try:
            status = self._get_vm_status(name)
            if status != 'stopped':
                return {'result': 'failure', 'reason': "VM must be stopped to update CPUs"}
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set cpu cores of config to {numcpus}
update configuration of vm with config
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def update_start(self, name, start=True):
        pprint("Autostart is not supported in UTM")

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)

    def update_iso(self, name, iso):
        if not os.path.exists(iso):
            iso_path = f"{UTM_POOL_DIR}/{iso}"
            if not os.path.exists(iso_path):
                return {'result': 'failure', 'reason': f"ISO {iso} not found"}
            iso = iso_path
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allDrives to drives of config
repeat with i from 1 to count of allDrives
    set d to item i of allDrives
    if removable of d then
        set driveId to id of d
        set item i of allDrives to {{id:driveId, source:POSIX file "{iso}"}}
        exit repeat
    end if
end repeat
set drives of config to allDrives
update configuration of vm with config
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def update_flavor(self, name, flavor):
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        return {'result': 'success'}

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}):
        if not self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        try:
            status = self._get_vm_status(name)
            if status != 'stopped':
                return {'result': 'failure', 'reason': "VM must be stopped to add disk"}
            size_mib = size * 1024
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allDrives to drives of config
set newDrives to {{}}
repeat with d in allDrives
    copy d to end of newDrives
end repeat
copy {{guest size:{size_mib}}} to end of newDrives
set drives of config to newDrives
update configuration of vm with config
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def delete_disk(self, name, diskname, pool=None, novm=False):
        if not self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        try:
            status = self._get_vm_status(name)
            if status != 'stopped':
                return {'result': 'failure', 'reason': "VM must be stopped to delete disk"}
            disk_index = ord(diskname[-1]) - ord('a') if diskname.startswith('vd') else int(diskname)
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allDrives to drives of config
set newDrives to {{}}
set diskIdx to 0
repeat with d in allDrives
    if removable of d is false then
        if diskIdx is not {disk_index} then
            copy d to end of newDrives
        end if
        set diskIdx to diskIdx + 1
    else
        copy d to end of newDrives
    end if
end repeat
set drives of config to newDrives
update configuration of vm with config
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def resize_disk(self, path, size):
        if not os.path.exists(path):
            return {'result': 'failure', 'reason': f"Disk {path} not found"}
        new_size = size * (1024 ** 3)
        try:
            with open(path, 'r+b') as f:
                f.seek(0)
                if f.read(4) != b'QFI\xfb':
                    return {'result': 'failure', 'reason': f"Not a qcow2 file: {path}"}
                f.seek(20)
                cluster_bits = struct.unpack('>I', f.read(4))[0]
                cluster_size = 1 << cluster_bits
                f.seek(24)
                current_size = struct.unpack('>Q', f.read(8))[0]
                if new_size <= current_size:
                    return {'result': 'success'}
                f.seek(36)
                l1_size = struct.unpack('>I', f.read(4))[0]
                f.seek(40)
                l1_offset = struct.unpack('>Q', f.read(8))[0]
                l2_entries = cluster_size // 8
                needed_l1 = (new_size + l2_entries * cluster_size - 1) // (l2_entries * cluster_size)
                if needed_l1 > l1_size:
                    extra = needed_l1 - l1_size
                    l1_end = l1_offset + l1_size * 8
                    f.seek(0, 2)
                    file_end = f.tell()
                    if l1_end == file_end or l1_end + extra * 8 <= file_end:
                        pass
                    else:
                        new_l1_offset = file_end
                        new_l1_offset = (new_l1_offset + cluster_size - 1) & ~(cluster_size - 1)
                        f.seek(l1_offset)
                        l1_data = f.read(l1_size * 8)
                        f.seek(new_l1_offset)
                        f.write(l1_data)
                        l1_offset = new_l1_offset
                        f.seek(40)
                        f.write(struct.pack('>Q', l1_offset))
                    f.seek(l1_offset + l1_size * 8)
                    f.write(b'\x00' * (extra * 8))
                    f.seek(36)
                    f.write(struct.pack('>I', needed_l1))
                f.seek(24)
                f.write(struct.pack('>Q', new_size))
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def list_disks(self):
        disks = {}
        try:
            vm_names = self._get_vm_names()
            for vm_name in vm_names:
                notes = self._get_vm_notes(vm_name)
                if notes.get('template'):
                    continue
                try:
                    qcow2_files = _find_vm_qcow2_files(vm_name)
                    for i, qpath in enumerate(qcow2_files):
                        disk_name = f"{vm_name}_vd{chr(97 + i)}"
                        disks[disk_name] = {'pool': 'default', 'path': vm_name}
                except Exception:
                    pass
        except Exception:
            pass
        return disks

    def add_nic(self, name, network, model='virtio'):
        try:
            status = self._get_vm_status(name)
            if status != 'stopped':
                return {'result': 'failure', 'reason': "VM must be stopped to add NIC"}
            mode = 'shared'
            host_if = ''
            if network in ('bridge', 'bridged'):
                mode = 'bridged'
                host_if = ', host interface:"en0"'
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allNets to network interfaces of config
set newNets to {{}}
repeat with n in allNets
    copy n to end of newNets
end repeat
copy {{mode:{mode}{host_if}}} to end of newNets
set network interfaces of config to newNets
update configuration of vm with config
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def delete_nic(self, name, interface):
        if not self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        try:
            status = self._get_vm_status(name)
            if status != 'stopped':
                return {'result': 'failure', 'reason': "VM must be stopped to delete NIC"}
            nic_index = int(interface.replace('eth', '')) if interface.startswith('eth') else int(interface)
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
set config to configuration of vm
set allNets to network interfaces of config
set newNets to {{}}
set nicIdx to 0
repeat with n in allNets
    if nicIdx is not {nic_index} then
        copy n to end of newNets
    end if
    set nicIdx to nicIdx + 1
end repeat
set network interfaces of config to newNets
update configuration of vm with config
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        pool_dir = poolpath or f"{UTM_POOL_DIR}/{name}"
        os.makedirs(pool_dir, exist_ok=True)
        return {'result': 'success'}

    def delete_image(self, image, pool=None):
        try:
            script = f'''tell application "UTM"
delete virtual machine named "{image}"
end tell'''
            _osascript(script)
        except Exception as e:
            return {'result': 'failure', 'reason': f"Failed to delete image {image}: {e}"}
        utm_bundle = os.path.join(UTM_IMAGES_DIR, f"{image}.utm")
        if os.path.exists(utm_bundle):
            import shutil
            shutil.rmtree(utm_bundle, ignore_errors=True)
        return {'result': 'success'}

    @staticmethod
    def _ensure_serial_in_plist(utm_dir):
        plist_path = os.path.join(utm_dir, "config.plist")
        if not os.path.exists(plist_path):
            return
        with open(plist_path, 'rb') as f:
            config = plistlib.load(f)
        if not config.get('Serial'):
            config['Serial'] = [{'Mode': 'Ptty', 'Target': 'Auto'}]
            with open(plist_path, 'wb') as f:
                plistlib.dump(config, f)

    def _create_utm_bundle(self, vm_name, qcow2_path):
        utm_dir = os.path.join(UTM_IMAGES_DIR, f"{vm_name}.utm")
        data_dir = os.path.join(utm_dir, "Data")
        os.makedirs(data_dir, exist_ok=True)
        disk_uuid = str(uuid.uuid4()).upper()
        disk_filename = f"{disk_uuid}.qcow2"
        dest_disk = os.path.join(data_dir, disk_filename)
        copy2(qcow2_path, dest_disk)
        efi_vars = os.path.join(data_dir, "efi_vars.fd")
        utm_efi_template = os.path.expanduser("~/Library/Containers/com.utmapp.UTM/Data/Library/Caches/qemu/edk2-arm-vars.fd")
        if os.path.exists(utm_efi_template):
            copy2(utm_efi_template, efi_vars)
        else:
            with open(efi_vars, 'wb') as f:
                f.write(b'\x00' * 329216)
        config = {
            'Backend': 'QEMU',
            'ConfigurationVersion': 4,
            'Display': [{'DownscalingFilter': 'Linear', 'DynamicResolution': False,
                         'Hardware': 'virtio-gpu-pci', 'NativeResolution': False,
                         'UpscalingFilter': 'Nearest'}],
            'Drive': [
                {'Identifier': str(uuid.uuid4()).upper(), 'ImageType': 'CD',
                 'Interface': 'USB', 'InterfaceVersion': 1, 'ReadOnly': True},
                {'Identifier': disk_uuid, 'ImageName': disk_filename,
                 'ImageType': 'Disk', 'Interface': 'VirtIO', 'InterfaceVersion': 1,
                 'ReadOnly': False}
            ],
            'Information': {'Icon': 'linux', 'IconCustom': False,
                            'Name': vm_name, 'UUID': str(uuid.uuid4()).upper()},
            'Input': {'MaximumUsbShare': 3, 'UsbBusSupport': '3.0', 'UsbSharing': False},
            'Network': [{'Hardware': 'virtio-net-pci', 'IsolateFromHost': False,
                         'MacAddress': common.gen_mac(), 'Mode': 'Shared', 'PortForward': []}],
            'QEMU': {'AdditionalArguments': ['-smbios', 'type=1,serial=ds=nocloud'], 'BalloonDevice': False, 'DebugLog': False,
                     'Hypervisor': True, 'PS2Controller': False, 'RNGDevice': True,
                     'RTCLocalTime': False, 'TPMDevice': False, 'TSO': False, 'UEFIBoot': True},
            'Serial': [{'Mode': 'Ptty', 'Target': 'Auto'}],
            'Sharing': {'ClipboardSharing': False, 'DirectoryShareMode': 'None',
                        'DirectoryShareReadOnly': False},
            'Sound': [{'Hardware': 'intel-hda'}],
            'System': {'Architecture': 'aarch64', 'CPU': 'default', 'CPUCount': 0,
                       'CPUFlagsAdd': [], 'CPUFlagsRemove': [], 'ForceMulticore': False,
                       'JITCacheSize': 0, 'MemorySize': 4096, 'Target': 'virt'}
        }
        plist_path = os.path.join(utm_dir, "config.plist")
        with open(plist_path, 'wb') as f:
            plistlib.dump(config, f)
        return utm_dir

    def _get_vm_names(self):
        try:
            script = '''tell application "UTM"
set vmNames to name of every virtual machine
return vmNames
end tell'''
            output = _osascript(script)
            if not output:
                return set()
            return set(n.strip() for n in output.split(', '))
        except Exception:
            return set()

    def _import_utm(self, utm_path):
        before = self._get_vm_names()
        script = f'''tell application "UTM"
import new virtual machine from POSIX file "{utm_path}"
end tell'''
        _osascript(script)
        after = self._get_vm_names()
        new_vms = after - before
        if new_vms:
            vm_name = new_vms.pop()
            try:
                self._set_vm_notes(vm_name, {'template': True})
            except Exception:
                pass

    def add_image(self, url, pool, short=None, cmds=[], name=None, size=None, convert=False):
        os.makedirs(UTM_IMAGES_DIR, exist_ok=True)
        if url.endswith('.zip'):
            zip_name = os.path.basename(url)
            zip_path = os.path.join(UTM_IMAGES_DIR, zip_name)
            pprint(f"Downloading {url}...")
            code = os.system(f"curl -Lf '{url}' -o '{zip_path}'")
            if code != 0:
                return {'result': 'failure', 'reason': f"Failed to download {url}"}
            pprint(f"Extracting {zip_name}...")
            code = os.system(f"unzip -o -q '{zip_path}' -d '{UTM_IMAGES_DIR}'")
            if code != 0:
                return {'result': 'failure', 'reason': f"Failed to extract {zip_name}"}
            os.remove(zip_path)
            utm_files = [f for f in os.listdir(UTM_IMAGES_DIR) if f.endswith('.utm')]
            if not utm_files:
                return {'result': 'failure', 'reason': "No .utm file found in archive"}
            utm_path = os.path.join(UTM_IMAGES_DIR, utm_files[-1])
            self._ensure_serial_in_plist(utm_path)
            pprint(f"Importing {utm_files[-1]} into UTM...")
            try:
                self._import_utm(utm_path)
            except Exception as e:
                return {'result': 'failure', 'reason': f"Failed to import into UTM: {e}"}
        else:
            if name is None:
                name = os.path.basename(url).split('.')[0]
            download_path = os.path.join(UTM_IMAGES_DIR, os.path.basename(url))
            pprint(f"Downloading {url}...")
            code = os.system(f"curl -Lf '{url}' -o '{download_path}'")
            if code != 0:
                return {'result': 'failure', 'reason': f"Failed to download {url}"}
            for ext in ('.gz', '.xz', '.bz2', '.zst'):
                if download_path.endswith(ext):
                    pprint(f"Decompressing {os.path.basename(download_path)}...")
                    decompress = {'.gz': 'gunzip', '.xz': 'xz -d', '.bz2': 'bzip2 -d', '.zst': 'zstd -d --rm'}
                    os.system(f"{decompress[ext]} '{download_path}'")
                    download_path = download_path[:-len(ext)]
                    break
            if not download_path.endswith('.qcow2'):
                qcow2_path = download_path.rsplit('.', 1)[0] + '.qcow2'
                os.rename(download_path, qcow2_path)
                download_path = qcow2_path
            pprint(f"Creating UTM bundle for {name}...")
            utm_path = self._create_utm_bundle(name, download_path)
            os.remove(download_path)
            self._ensure_serial_in_plist(utm_path)
            pprint(f"Importing {name} into UTM...")
            try:
                self._import_utm(utm_path)
            except Exception as e:
                return {'result': 'failure', 'reason': f"Failed to import into UTM: {e}"}
        pprint("Image imported successfully")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        warning("Network creation is managed by UTM internally")
        return {'result': 'success'}

    def delete_network(self, name=None, cidr=None, force=False):
        warning("Network deletion is managed by UTM internally")
        return {'result': 'success'}

    def list_pools(self):
        pools = ['default']
        if os.path.exists(UTM_POOL_DIR):
            for d in os.listdir(UTM_POOL_DIR):
                if os.path.isdir(os.path.join(UTM_POOL_DIR, d)):
                    pools.append(d)
        return pools

    def list_networks(self):
        return {
            'shared': {'cidr': 'N/A', 'dhcp': True, 'domain': '', 'type': 'routed', 'mode': 'nat'},
            'bridged': {'cidr': 'N/A', 'dhcp': False, 'domain': '', 'type': 'bridged', 'mode': 'bridge'},
            'host': {'cidr': 'N/A', 'dhcp': True, 'domain': '', 'type': 'isolated', 'mode': 'host-only'},
            'emulated': {'cidr': 'N/A', 'dhcp': True, 'domain': '', 'type': 'routed', 'mode': 'vlan'},
        }

    def info_network(self, name):
        networks = self.list_networks()
        if name in networks:
            return networks[name]
        return {}

    def info_subnet(self, name):
        return {}

    def list_subnets(self):
        return {}

    def delete_pool(self, name, full=False):
        pool_dir = f"{UTM_POOL_DIR}/{name}"
        if os.path.exists(pool_dir):
            if full:
                import shutil
                shutil.rmtree(pool_dir, ignore_errors=True)
            return {'result': 'success'}
        return {'result': 'failure', 'reason': f"Pool {name} not found"}

    def network_ports(self, name):
        return []

    def vm_ports(self, name):
        return ['default']

    def get_pool_path(self, pool):
        if pool == 'default':
            return UTM_POOL_DIR
        pool_path = f"{UTM_POOL_DIR}/{pool}"
        if os.path.exists(pool_path):
            return pool_path
        return UTM_POOL_DIR

    def list_flavors(self):
        return []

    def export(self, name, image=None):
        if not self.exists(name):
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        export_name = image or name
        dest = os.path.join(UTM_IMAGES_DIR, f"{export_name}.utm")
        try:
            script = f'''tell application "UTM"
set vm to virtual machine named "{name}"
export vm to POSIX file "{dest}"
end tell'''
            _osascript(script)
            return {'result': 'success'}
        except Exception as e:
            return {'result': 'failure', 'reason': str(e)}

    def create_bucket(self, bucket, public=False):
        return {'result': 'failure', 'reason': "Buckets are not supported in UTM"}

    def delete_bucket(self, bucket):
        return {'result': 'failure', 'reason': "Buckets are not supported in UTM"}

    def delete_from_bucket(self, bucket, path):
        return {'result': 'failure', 'reason': "Buckets are not supported in UTM"}

    def download_from_bucket(self, bucket, path):
        return {'result': 'failure', 'reason': "Buckets are not supported in UTM"}

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        return {'result': 'failure', 'reason': "Buckets are not supported in UTM"}

    def list_buckets(self):
        return []

    def list_bucketfiles(self, bucket):
        return []

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False, instanceid=None):
        return

    def update_nic(self, name, index, network):
        warning("NIC update is not fully supported in UTM via scripting")

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        return {'result': 'success'}

    def list_security_groups(self, network=None):
        return []

    def create_security_group(self, name, overrides={}):
        return {'result': 'success'}

    def delete_security_group(self, name):
        return {'result': 'success'}

    def update_security_group(self, name, overrides={}):
        return {'result': 'success'}

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        return {'result': 'success'}

    def update_subnet(self, name, overrides={}):
        return {'result': 'success'}

    def list_dns_zones(self):
        return []

    def detach_disks(self, name):
        return {'result': 'success'}
