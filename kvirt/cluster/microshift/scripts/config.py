#!/usr/bin/env python

import sys
import yaml

if len(sys.argv) != 3:
    print("Usage config.py $domain $ip")
    sys.exit(1)

domain = sys.argv[1]
ip = sys.argv[2]

with open('/etc/microshift/config.yaml', 'r+') as f:
    data = yaml.safe_load(f)
    data['dns']['baseDomain'] = domain
    data['apiServer']['subjectAltNames'] = [f'api.{domain}']
    data['ingress']['listenAddress'] = ['eth0']
    data['apiServer']['advertiseAddress'] = ip
    yaml.safe_dump(data, f)
