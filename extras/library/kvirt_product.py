#!/usr/bin/env python
# coding=utf-8

from ansible.module_utils.basic import AnsibleModule
from kvirt.config import Kconfig


DOCUMENTATION = '''
module: kvirt_product
short_description: Deploy a product using kcli
description:
    - Longer description of the module
    - You might include instructions
version_added: "0.1"
author: "Karim Boumedhel, @karmab"
notes:
    - Details at https://github.com/karmab/kcli
requirements:
    - kcli python package you can grab from pypi'''

EXAMPLES = '''
- name: Deploy origin
  kvirt_product:
    name: my_origin
    product: origin

- name: Delete that product
  kvirt_product:
    name: my_origin
    state: absent

- name: Deploy fission with additional parameters
  kvirt_product:
    name: fission
    product: fission
    parameters:
     fission_type: all
     docker_disk_size: 10
'''


def main():
    """

    """
    argument_spec = {
        "state": {
            "default": "present",
            "choices": ['present', 'absent'],
            "type": 'str'
        },
        "name": {"required": True, "type": "str"},
        "client": {"required": False, "type": "str"},
        "product": {"required": True, "type": "str"},
        "repo": {"required": False, "type": "str"},
        "parameters": {"required": False, "type": "dict"},
    }
    module = AnsibleModule(argument_spec=argument_spec)
    client = module.params['client']
    config = Kconfig(client, quiet=True)
    name = module.params['name']
    product = module.params['product']
    repo = module.params['repo']
    state = module.params['state']
    if state == 'present':
        overrides = module.params['parameters'] if module.params['parameters'] is not None else {}
        meta = config.create_product(product, repo=repo, plan=name, overrides=overrides)
        changed = True if 'newvms' in meta else False
        skipped = False
    else:
        meta = config.plan(name, delete=True)
        changed = True if 'deletedvms' in meta else False
        skipped = False
    module.exit_json(changed=changed, skipped=skipped, meta=meta)


if __name__ == '__main__':
    main()
