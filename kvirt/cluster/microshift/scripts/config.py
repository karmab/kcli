#!/usr/bin/env python

import sys
import yaml

if len(sys.argv) != 2:
    print("Usage config.py $domain")
    sys.exit(1)

domain = sys.argv[1]

with open('/etc/microshift/config.yaml', 'rw') as f:
    data = yaml.safe_load(f)
    data['dns']['baseDomain'] = domain
    data['apiServer']['subjectAltNames'] = [f'api.{domain}']
    data['ingress']['listenAddress'] = ['eth0']
    yaml.safe_dump(data, f)
