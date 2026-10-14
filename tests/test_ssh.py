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

