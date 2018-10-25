#!/usr/bin/python
# coding=utf-8

from ansible.module_utils.basic import AnsibleModule
from kvirt.config import Kconfig


DOCUMENTATION = '''
module: kvirt_vm
short_description: Handles libvirt vms using kcli
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
- name: Create a vm
  kvirt_vm:
    name: prout
    profile: centos

- name: Delete that vm
  kvirt_vm:
    name: prout
    state: absent
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
        "profile": {"required": True, "type": "str"},
        "parameters": {"required": False, "type": "dict"},
    }
    module = AnsibleModule(argument_spec=argument_spec)
    client = module.params['client']
    config = Kconfig(client=client, quiet=True)
    k = config.k
    name = module.params['name']
    exists = k.exists(name)
    state = module.params['state']
    if state == 'present':
        if exists:
            changed = False
            skipped = True
            meta = {'result': 'skipped'}
        else:
            profile = module.params['profile']
            overrides = module.params['parameters'] if module.params['parameters'] is not None else {}
            meta = config.create_vm(name, profile, overrides=overrides)
            changed = True
            skipped = False
    else:
        if exists:
            meta = k.delete(name)
            changed = True
            skipped = False
        else:
            changed = False
            skipped = True
            meta = {'result': 'skipped'}
    module.exit_json(changed=changed, skipped=skipped, meta=meta)


if __name__ == '__main__':
    main()
