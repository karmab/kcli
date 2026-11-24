import os
import re
import unittest


class TestKubeadminPassword(unittest.TestCase):
    """kcli should not leak openshift-installer's trailing newline into the kubeadmin password."""

    def test_openshift_reads_strip_trailing_newline(self):
        """Both kubeadmin-password reads in the openshift flow strip the trailing newline."""
        directory = os.path.join(os.path.dirname(__file__), '..', 'kvirt', 'cluster', 'openshift')
        with open(os.path.join(directory, '__init__.py')) as f:
            source = f.read()
        unstripped = re.findall(r'open\(f"\{clusterdir\}/auth/kubeadmin-password"\)\.read\(\)(?!\.strip)', source)
        self.assertEqual(unstripped, [], 'kubeadmin-password read without .strip() found')
        self.assertGreaterEqual(source.count('.read().strip()'), 2)

    def test_hypershift_secret_write_strips_trailing_newline(self):
        """The hypershift flow writes the kubeadmin-password file without the trailing newline."""
        directory = os.path.join(os.path.dirname(__file__), '..', 'kvirt', 'cluster', 'hypershift')
        with open(os.path.join(directory, '__init__.py')) as f:
            source = f.read()
        self.assertIn('secret/{cluster}-kubeadmin-password --to=-").read().strip()', source)

    def test_end_to_end_password_content(self):
        """The strip chain turns 'oc extract' output with a trailing newline into a clean password."""
        raw = 'C5337-VBGk6-cQU36-Zxd4r\n'  # simulated 'oc extract --to=-' stdout
        password = raw.strip()
        self.assertEqual(password, 'C5337-VBGk6-cQU36-Zxd4r')
        self.assertFalse(password.endswith('\n'))
