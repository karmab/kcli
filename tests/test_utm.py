import os
from pathlib import Path
import plistlib
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, mock_open, patch
import yaml

from kvirt.providers import utm


class TestUTM(unittest.TestCase):
    def setUp(self):
        self.provider = utm.Kutm.__new__(utm.Kutm)
        self.provider.backend = 'apple'
        self.provider.debug = False
        self.provider.exists = Mock(return_value=False)
        self.provider._set_vm_notes = Mock()
        self.provider._patch_vm_plist = Mock()
        self.scripting = patch.object(utm, '_osascript', return_value='')
        self.script = self.scripting.start()
        self.addCleanup(self.scripting.stop)

    def test_default_backend(self):
        with TemporaryDirectory() as directory, \
                patch.object(utm, 'UTM_POOL_DIR', directory), patch.object(utm, 'UTM_IMAGES_DIR', directory), \
                patch.object(utm, 'which', return_value='/usr/bin/osascript'):
            self.assertEqual(utm.Kutm().backend, 'qemu')
            self.assertEqual(utm.Kutm(backend='Apple').backend, 'apple')
            self.assertIsNone(utm.Kutm(backend='invalid').conn)

    def test_create_backends_and_displays(self):
        for backend in ('qemu', 'apple'):
            for display in (False, True):
                with self.subTest(backend=backend, display=display):
                    result = self.provider.create('test', overrides={'backend': backend}, vnc=display,
                                                  start=False, cloudinit=False)
                    self.assertEqual(result['result'], 'success')
                    script = self.script.call_args.args[0]
                    self.assertIn(f'backend:{backend}', script)
                    if backend == 'apple':
                        self.assertNotIn('hardware:', script)
                        self.assertNotIn('architecture:', script)
                        self.assertNotIn('hypervisor:', script)
                        self.assertNotIn('interface:VirtIO', script)
                    else:
                        self.assertIn('architecture:"aarch64"', script)
                    if display:
                        self.assertNotIn('displays:{}', script)
                        self.assertNotIn('displays:{{{', script)
                    else:
                        self.assertIn('displays:{}', script)

    def test_invalid_options_fail_before_creation(self):
        for options in ({'overrides': {'backend': 'invalid'}}, {'tpm': True},
                        {'overrides': {'uefi': False}}, {'nets': ['emulated']}, {'nets': ['host-only']}):
            with self.subTest(options=options):
                self.assertEqual(self.provider.create('test', **options)['result'], 'failure')
                self.script.assert_not_called()

    def test_network_models_and_bridge(self):
        nets = [{'name': 'bridged', 'bridge': 'en1', 'model': 'e1000', 'mac': '52:54:00:11:22:33'}]
        apple = self.provider._build_net_parts(nets, backend='apple')[0]
        self.assertIn('host interface:"en1"', apple)
        self.assertIn('mode:bridged', apple)
        self.assertNotIn('hardware:', apple)
        self.assertIn('hardware:"e1000"', self.provider._build_net_parts(nets)[0])

    def test_template_backend_mismatch(self):
        self.provider._find_template = Mock(return_value='template')
        self.provider._get_vm_backend = Mock(return_value='qemu')
        result = self.provider.create('test', image='template')
        self.assertEqual(result['result'], 'failure')
        self.script.assert_not_called()

    def test_template_resize_and_display(self):
        self.provider._find_template = Mock(return_value='template')
        self.provider._get_vm_backend = Mock(return_value='apple')
        self.provider.resize_disk = Mock(return_value={'result': 'success'})
        with patch.object(utm, '_find_vm_disk_files', return_value=['/tmp/root.img']):
            result = self.provider.create('test', image='template', disks=[20], start=False, cloudinit=False)
        self.assertEqual(result['result'], 'success')
        self.provider.resize_disk.assert_called_once_with('/tmp/root.img', 20)
        self.assertIn('displays:{{dynamic resolution:true}}', self.script.call_args.args[0])

    def test_start_failure_is_reported(self):
        self.provider.start = Mock(return_value={'result': 'failure', 'reason': 'Cannot boot'})
        self.assertEqual(self.provider.create('test')['reason'], 'Cannot boot')

    def test_qemu_clone_preserves_template_display_hardware(self):
        self.provider.backend = 'qemu'
        self.provider._find_template = Mock(return_value='template')
        self.provider._get_vm_backend = Mock(return_value='qemu')
        with patch.object(utm, '_find_vm_disk_files', return_value=[]):
            self.provider.create('test', image='template', start=False, cloudinit=False)
        self.assertNotIn('displays:', self.script.call_args.args[0])

    def test_apple_plist_is_not_patched_with_qemu_options(self):
        with TemporaryDirectory() as directory, patch.object(utm, 'UTM_DOCUMENTS_DIR', directory):
            bundle = Path(directory) / 'test.utm'
            bundle.mkdir()
            config = {'Backend': 'Apple', 'System': {'Boot': {'UEFIBoot': True}}}
            path = bundle / 'config.plist'
            path.write_bytes(plistlib.dumps(config))
            utm.Kutm._patch_vm_plist('test', tpm=True, machine='virt')
            self.assertEqual(plistlib.loads(path.read_bytes()), config)

    def test_disk_discovery_preserves_boot_order(self):
        with TemporaryDirectory() as directory, patch.object(utm, 'UTM_DOCUMENTS_DIR', directory):
            bundle = Path(directory) / 'test.utm'
            bundle.mkdir()
            config = {'Drive': [{'ImageName': 'z.img'}, {'ImageName': 'a.img'},
                                {'ImageName': 'cloudinit.ISO'}, {'Identifier': 'external'}]}
            (bundle / 'config.plist').write_bytes(plistlib.dumps(config))
            paths = utm._find_vm_disk_files('test')
            self.assertEqual([os.path.basename(path) for path in paths], ['z.img', 'a.img'])

    def test_raw_resize_preserves_data_and_never_shrinks(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'disk.img'
            path.write_bytes(b'boot sector')
            self.assertEqual(self.provider.resize_disk(str(path), 1)['result'], 'success')
            self.assertEqual(path.stat().st_size, 1024 ** 3)
            with path.open('rb') as disk:
                self.assertEqual(disk.read(11), b'boot sector')
            self.provider.resize_disk(str(path), 0)
            self.assertEqual(path.stat().st_size, 1024 ** 3)

    def test_apple_disk_add_uses_vm_backend(self):
        self.provider._get_vm_backend = Mock(return_value='apple')
        self.provider._add_disk('test', 10)
        self.assertIn('guest size:10240', self.script.call_args.args[0])
        self.assertNotIn('interface:VirtIO', self.script.call_args.args[0])

    def test_apple_template_conversion(self):
        with TemporaryDirectory() as directory, patch.object(utm, 'UTM_IMAGES_DIR', directory):
            source = Path(directory) / 'cloud.qcow2'
            source.write_bytes(b'QFI\xfb')
            with patch.object(utm, 'which', return_value='/usr/bin/qemu-img'), \
                    patch.object(utm.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
                self.provider._create_apple_template('template', str(source))
            args = run.call_args.args[0]
            self.assertEqual(args[:5], ['/usr/bin/qemu-img', 'convert', '-O', 'raw', str(source)])
            self.assertIn('backend:apple', self.script.call_args.args[0])
            self.assertIn('disk.raw', self.script.call_args.args[0])
            # UTM supplies a PTTY serial port by default. The explicit property
            # collides with the serial-port element in UTM's scripting dictionary.
            self.assertNotIn('serial ports:', self.script.call_args.args[0])

    def test_conversion_failure_does_not_create_template(self):
        with TemporaryDirectory() as directory, patch.object(utm, 'UTM_IMAGES_DIR', directory):
            source = Path(directory) / 'cloud.qcow2'
            source.write_bytes(b'QFI\xfb')
            with patch.object(utm, 'which', return_value=None), self.assertRaisesRegex(RuntimeError, 'qemu-img'):
                self.provider._create_apple_template('template', str(source))
            self.script.assert_not_called()

    def test_raw_template_needs_no_conversion(self):
        with TemporaryDirectory() as directory, patch.object(utm, 'UTM_IMAGES_DIR', directory):
            source = Path(directory) / 'cloud.img'
            source.write_bytes(b'raw disk')
            with patch.object(utm.subprocess, 'run') as run:
                self.provider._create_apple_template('template', str(source))
            run.assert_not_called()
            self.assertIn(str(source), self.script.call_args.args[0])

    def test_apple_sharing_updates_all_directories(self):
        with TemporaryDirectory() as directory:
            folders = [os.path.join(directory, 'first'), os.path.join(directory, 'second')]
            result = self.provider.create('test', sharedfolders=folders, start=False)
            self.assertEqual(result['result'], 'success')
            scripts = [call.args[0] for call in self.script.call_args_list]
            self.assertIn('directory shares of config to {{read only:false}, {read only:false}}', scripts[1])
            self.assertNotIn('virtfs', scripts[1])
            self.assertTrue(all(folder in scripts[2] for folder in folders))

    def test_apple_cloudinit_matches_the_vm_mac(self):
        self.provider._find_template = Mock(return_value='template')
        self.provider._get_vm_backend = Mock(return_value='apple')
        self.provider._attach_iso = Mock()
        for static in (False, True):
            with self.subTest(static=static):
                net = {'name': 'default', 'mac': '52:54:00:01:02:03'}
                if static:
                    net.update({'ip': '192.0.2.2', 'mask': 24})
                original = net.copy()
                with patch.object(utm, '_find_vm_disk_files', return_value=[]), \
                        patch.object(utm.common, 'get_ssh_pub_key', return_value=None), \
                        patch.object(utm.common, 'make_iso', return_value=0) as make_iso, \
                        patch.object(utm, 'copy2'):
                    result = self.provider.create('test', image='ubuntu2404', nets=[net],
                                                  keys=['ssh-ed25519 AAATEST'], start=False)
                self.assertEqual(result['result'], 'success')
                network = yaml.safe_load(make_iso.call_args.args[4])
                interface = network['ethernets']['eth0']
                self.assertEqual(interface['match'], {'macaddress': net['mac']})
                self.assertEqual(interface['set-name'], 'eth0')
                self.assertEqual(interface['dhcp4'], not static)
                if static:
                    self.assertEqual(interface['addresses'], ['192.0.2.2/24'])
                self.assertEqual(net, original)
                self.assertIn(f'address:"{net["mac"]}"', self.script.call_args.args[0])

    def test_apple_nic_rejects_unsupported_mode(self):
        self.provider._get_vm_status = Mock(return_value='stopped')
        self.provider._get_vm_backend = Mock(return_value='apple')
        self.assertEqual(self.provider.add_nic('test', 'emulated')['result'], 'failure')
        self.script.assert_not_called()

    def test_cloudinit_seed_is_imported_for_apple(self):
        for backend, removable in (('apple', 'false'), ('qemu', 'true')):
            with self.subTest(backend=backend):
                self.provider._get_vm_backend = Mock(return_value=backend)
                self.provider._attach_iso('test', '/tmp/seed.ISO')
                self.assertIn(f'removable:{removable}', self.script.call_args.args[0])

    def test_dhcp_ip_normalizes_mac(self):
        self.provider._get_vm_backend = Mock(return_value='apple')
        self.script.return_value = '52:54:00:01:02:03'
        leases = '{\n hw_address=1,52:54:0:1:2:3\n ip_address=192.168.64.2\n}\n'
        with patch('builtins.open', mock_open(read_data=leases)):
            self.assertEqual(self.provider.ip('test'), '192.168.64.2')
        self.assertNotIn('query ip', self.script.call_args.args[0])

    def test_qemu_ip_uses_guest_agent(self):
        self.provider._get_vm_backend = Mock(return_value='qemu')
        self.script.return_value = '192.168.64.3'
        self.assertEqual(self.provider.ip('test'), '192.168.64.3')
        self.assertIn('query ip', self.script.call_args.args[0])

    def test_dhcp_ip_with_duid(self):
        self.provider._get_vm_backend = Mock(return_value='apple')
        self.script.return_value = '52:54:00:01:02:03'
        leases = '{\n name=test\n hw_address=ff,1:2:3:4:5:6:7:8\n ip_address=192.168.64.4\n}\n'
        with patch('builtins.open', mock_open(read_data=leases)):
            self.assertEqual(self.provider.ip('test'), '192.168.64.4')
            self.assertIsNone(self.provider.ip('other'))


if __name__ == '__main__':
    unittest.main()
