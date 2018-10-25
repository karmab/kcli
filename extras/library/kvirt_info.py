#!/usr/bin/python
# coding=utf-8

from ansible.module_utils.basic import AnsibleModule
from kvirt.config import Kconfig


DOCUMENTATION = '''
module: kvirt_info
short_description: Retrieves info using kcli library
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
- name: Get Complete Info
  kvirt_info:
    name: prout

- name: Only get ip
  kvirt_info:
    name: prout
    fields:
    - ip
'''


def main():
    """

    """
    argument_spec = {
        "name": {"required": True, "type": "str"},
        "client": {"required": False, "type": "str"},
        "fields": {"required": False, "type": "list"},
    }
    module = AnsibleModule(argument_spec=argument_spec)
    client = module.params['client']
    config = Kconfig(client, quiet=True)
    k = config.k
    name = module.params['name']
    exists = k.exists(name)
    fields = module.params['fields']
    if exists:
        meta = k.info(name, output='yaml', fields=fields, values=True, pretty=False)
        changed = True
        skipped = False
    else:
        changed = False
        skipped = False
        module.fail_json(msg='Vm %s not found' % name)
    module.exit_json(changed=changed, skipped=skipped, meta=meta)


if __name__ == '__main__':
    main()
