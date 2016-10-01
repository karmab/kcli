#!/usr/bin/python

from ansible.module_utils.basic import *
from kvirt import Kvirt

DOCUMENTATION = '''
module: kvirt_vm
short_description: Handles libvirt vms using kcli
description:
    - Longer description of the module
    - You might include instructions
version_added: "0.1"
author: "Karim Boumedhel, @awesome-github-id"
notes:
    - Details at https://github.com/karmab/kcli
requirements:
    - kcli python package you can grab from pypi'''

EXAMPLES = '''
- name: Create a vm
  kvirt_vm:
    name: prout
    host: 192.168.0.1
    user: root
  register: result

- name: Delete that vm
  kvirt_vm:
    name: prout
    host: 192.168.0.1
    user: root
    state: absent
  register: result
'''


def main():
    argument_spec = {
        "host": {"default": '127.0.0.1', "type": "str"},
        "port": {"default": '22', "type": "str"},
        "user": {"default": 'root', "type": "str"},
        "protocol": {"default": 'ssh', "type": "str", 'choices': ['ssh', 'tcp']},
        "url": {"default": None, "type": "str"},
        "state": {
            "default": "present",
            "choices": ['present', 'absent'],
            "type": 'str'
        },
        "name": {"required": True, "type": "str"},
        "description": {"default": 'kvirt', "type": "str"},
        "numcpus": {"default": 2, "type": "int"},
        "memory": {"default": 512, "type": "int"},
        "pool": {"default": 'default', "type": "str"},
        "template": {"type": "str"},

    }
    module = AnsibleModule(argument_spec=argument_spec)
    # url = module.params['url'] if 'url' in module.params else None
    # k = Kvirt(host=module.params['host'], port=module.params['port'], user=module.params['user'], protocol=module.params['protocol'], url=url)
    k = Kvirt(host=module.params['host'], port=module.params['port'], user=module.params['user'], protocol=module.params['protocol'])
    name = module.params['name']
    exists = k.exists(name)
    state = module.params['state']
    if state == 'present':
        if exists:
            changed = False
            skipped = True
            meta = {'result': 'skipped'}
        else:
            template = module.params['template'] if 'template' in module.params else None
            # description = module.params['description'] if 'description' in module.params else None
            pool = module.params['pool'] if 'pool' in module.params else 'default'
            numcpus = module.params['numcpus'] if 'numcpus' in module.params else 2
            memory = module.params['memory'] if 'numcpus' in module.params else '512'
            # meta = k.create(name=name, description=description, numcpus=numcpus, memory=memory, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=vnc, cloudinit=cloudinit, start=start, keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain)
            meta = k.create(name=name, numcpus=numcpus, memory=memory, pool=pool, template=template)
            # meta = k.create(name)
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
