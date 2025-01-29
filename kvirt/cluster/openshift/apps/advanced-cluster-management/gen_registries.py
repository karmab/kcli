#!/usr/bin/env python3

import os
import yaml

if os.path.exists('idms-oc-mirror.yaml'):
    results = ''
    with open('idms-oc-mirror.yaml') as f:
        data = yaml.safe_load_all(f)
        for d in data:
            mirrors = d['spec']['imageDigestMirrors']
            for mirror in mirrors:
                registry1 = mirror['source']
                registry2 = mirror['mirrors'][0]
                results += """\n    [[registry]]
        prefix = ""
        location = "{registry1}"
        mirror-by-digest-only = true

        [[registry.mirror]]
          location = "{registry2}"\n""".format(registry1=registry1, registry2=registry2)
    print(results)
