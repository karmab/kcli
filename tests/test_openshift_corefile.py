import re
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


class TestOpenShiftCorefile(unittest.TestCase):
    def test_apps_address_families(self):
        """Only the selected ingress VIP's family should have an address answer."""
        directory = Path(__file__).resolve().parents[1] / 'kvirt/cluster/openshift'
        environment = Environment(loader=FileSystemLoader(str(directory)), undefined=StrictUndefined)
        template = environment.get_template('Corefile')
        cases = [
            ('192.0.2.10', None, False, False, 'A', '192.0.2.10'),
            ('2001:db8::10', None, True, False, 'AAAA', '2001:db8::10'),
            ('192.0.2.10', None, False, True, 'A', '192.0.2.10'),
            ('192.0.2.10', '192.0.2.20', False, False, 'A', '192.0.2.20'),
            ('192.0.2.10', '2001:db8::20', False, True, 'AAAA', '2001:db8::20'),
            ('2001:db8::10', '192.0.2.20', True, True, 'A', '192.0.2.20'),
        ]
        for api_ip, ingress_ip, ipv6, dualstack, record_type, address in cases:
            with self.subTest(api_ip=api_ip, ingress_ip=ingress_ip, dualstack=dualstack):
                rendered = template.render(cluster='test', domain='example.com', name='test-ctlplane-0',
                                           ctlplanes=3, mdns=True, sno=False, api_ip=api_ip, ingress_ip=ingress_ip,
                                           ipv6=ipv6, dualstack=dualstack, coredns_nameserver='192.0.2.1')
                self.assertNotIn('template ANY ANY', rendered)
                blocks = dict(re.findall(r'template IN (A|AAAA) apps.test.example.com \{\n(.*?)\n    \}',
                                         rendered, flags=re.DOTALL))
                self.assertEqual(set(blocks), {'A', 'AAAA'})
                self.assertIn('answer "{{ .Name }} %s %s"' % (record_type, address), blocks[record_type])
                other_type = 'AAAA' if record_type == 'A' else 'A'
                self.assertIn('rcode NOERROR', blocks[other_type])
                self.assertNotIn('answer', blocks[other_type])
                self.assertNotIn('fallthrough', blocks[other_type])
                self.assertIn('forward . 192.0.2.1', rendered)


if __name__ == '__main__':
    unittest.main()
