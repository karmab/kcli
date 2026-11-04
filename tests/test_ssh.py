from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from kvirt import cli, common


class TestSSH(unittest.TestCase):
    def setUp(self):
        self.args = SimpleNamespace(L=None, R=None, D=None, X=False, Y=False, t=False,
                                    identityfile=None, user=None, port=None, client='utm', debug=False,
                                    region=None, zone=None, namespace=None, resource_group=None,
                                    name=['test'])
        base = SimpleNamespace(tunnel=False, tunnelhost=None, tunnelport=22,
                               tunneluser='root', insecure=True, type='utm')
        self.provider = Mock()
        self.provider.info.return_value = {'user': 'ubuntu', 'ip': '192.168.64.6', 'status': 'up'}
        config = SimpleNamespace(k=self.provider, type='utm', vmuser=None, vmport=None)
        for target, value in (('Kbaseconfig', base), ('Kconfig', config), ('which', '/usr/bin/ssh')):
            patcher = patch.object(cli, target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(cli.os, 'system', return_value=0)
        self.system = patcher.start()
        self.addCleanup(patcher.stop)

    def test_guest_not_ready_reports_reason_and_fails(self):
        reason = 'SSH is not ready for test at 192.168.64.6:22; try again after the guest boots'
        self.provider.info.return_value = {'user': 'ubuntu', 'status': 'up', 'ssh_error': reason}
        with patch.object(common, 'error') as error, self.assertRaises(SystemExit) as exit:
            cli.ssh_vm(self.args)
        self.assertEqual(exit.exception.code, 1)
        error.assert_called_once_with(reason)
        self.system.assert_not_called()

    def test_missing_vm_reports_error_and_fails(self):
        self.provider.info.return_value = {}
        with patch.object(common, 'error') as error, self.assertRaises(SystemExit) as exit:
            cli.ssh_vm(self.args)
        self.assertEqual(exit.exception.code, 1)
        self.assertIn('Could not find VM test', error.call_args.args[0])
        self.system.assert_not_called()

    def test_stopped_vm_does_not_attempt_ssh(self):
        self.provider.info.return_value['status'] = 'down'
        with patch.object(common, 'error') as error, self.assertRaises(SystemExit) as exit:
            cli.ssh_vm(self.args)
        self.assertEqual(exit.exception.code, 1)
        error.assert_called_once_with('test down')
        self.system.assert_not_called()

    def test_connection_failure_reports_target_and_preserves_exit_status(self):
        self.system.return_value = 255 << 8
        with patch.object(cli, 'error') as error, self.assertRaises(SystemExit) as exit:
            cli.ssh_vm(self.args)
        self.assertEqual(exit.exception.code, 255)
        self.assertIn('SSH connection to ubuntu@192.168.64.6 failed', error.call_args.args[0])

    def test_remote_command_failure_is_not_reported_as_a_connection_failure(self):
        self.args.name.append('false')
        self.system.return_value = 1 << 8
        with patch.object(cli, 'error') as error, self.assertRaises(SystemExit) as exit:
            cli.ssh_vm(self.args)
        self.assertEqual(exit.exception.code, 1)
        error.assert_not_called()

    def test_successful_session_exits_successfully(self):
        with self.assertRaises(SystemExit) as exit:
            cli.ssh_vm(self.args)
        self.assertEqual(exit.exception.code, 0)
        self.assertIn('ubuntu@192.168.64.6', self.system.call_args.args[0])

    def test_utm_login_probe_and_session_use_explicit_credentials(self):
        self.args.user = 'guest'
        self.args.port = '2222'
        self.args.identityfile = '/tmp/guest-key'
        with self.assertRaises(SystemExit) as exit:
            cli.ssh_vm(self.args)
        self.assertEqual(exit.exception.code, 0)
        self.assertEqual(self.provider.ssh_user, 'guest')
        self.assertEqual(self.provider.ssh_port, 2222)
        self.assertEqual(self.provider.ssh_identityfile, '/tmp/guest-key')
        command = self.system.call_args.args[0]
        self.assertIn('-p 2222', command)
        self.assertIn('-i /tmp/guest-key', command)
        self.assertIn('guest@192.168.64.6', command)

    def test_debug_enables_ssh_diagnostics(self):
        with patch.object(common, 'get_ssh_pub_key', return_value=None):
            insecure = common.ssh('test', ip='192.168.64.6', user='ubuntu', insecure=True, debug=True)
            secure = common.ssh('test', ip='192.168.64.6', user='ubuntu', debug=True)
        self.assertIn('LogLevel=DEBUG1', insecure)
        self.assertTrue(secure.startswith('ssh -v '))
