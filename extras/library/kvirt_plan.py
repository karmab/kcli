#!/usr/bin/env python
# coding=utf-8

from ansible.module_utils.basic import AnsibleModule
from kvirt.config import Kconfig


DOCUMENTATION = '''
module: kvirt_plan
short_description: Deploy a plan using kcli
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
  kvirt_plan:
    name: my_plan
    inputfile: my_plan.yml

- name: Delete that plan
  kvirt_plan:
    name: my_plan
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
        "inputfile": {"required": False, "type": "str"},
        "parameters": {"required": False, "type": "dict"},
    }
    module = AnsibleModule(argument_spec=argument_spec)
    client = module.params['client']
    config = Kconfig(client, quiet=True)
    name = module.params['name']
    inputfile = module.params['inputfile']
    state = module.params['state']
    if state == 'present':
        # if inputfile is None:
        #    module.fail_json(msg='Missing inputfile parameter')
        overrides = module.params['parameters'] if module.params['parameters'] is not None else {}
        meta = config.plan(name, inputfile=inputfile, overrides=overrides)
        changed = True if 'newvms' in meta else False
        skipped = False
    else:
        meta = config.plan(name, delete=True)
        changed = True if 'deletedvms' in meta else False
        skipped = False
    module.exit_json(changed=changed, skipped=skipped, meta=meta)


if __name__ == '__main__':
    main()
