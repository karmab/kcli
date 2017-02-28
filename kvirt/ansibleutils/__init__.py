#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

# from jinja2 import Environment
import os
import time


def play(self, name, playbook, variables=[], verbose=False):
    counter = 0
    while counter != 80:
        ip = self.ip(name)
        if ip is None:
            time.sleep(5)
            print("Retrieving ip of %s..." % name)
            counter += 10
        else:
            break
    login = self._ssh_credentials(name)[0]
    inventory = "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
    ansiblecommand = "ansible-playbook"
    if verbose:
        ansiblecommand = "%s -vvv" % ansiblecommand
    # extravars = ''
    if variables is not None:
        for variable in variables:
            if not isinstance(variable, dict) or len(variable.keys()) != 1:
                continue
            else:
                key, value = variable.keys()[0], variable[variable.keys()[0]]
                # extravars = "%s -e \"%s=%s\"" % (extravars, key, value)
                inventory = "%s %s=%s" % (inventory, key, value)
    with open("/tmp/%s.inv" % name, 'w') as f:
        f.write("%s\n" % inventory)
    print("Ansible Command run:")
    # print("%s -T 20 -i ~/klist.py %s %s" % (ansiblecommand, extravars, playbook))
    # os.system("%s -T 20 -i ~/klist.py %s %s" % (ansiblecommand, extravars, playbook))
    print("%s -T 20 -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
    os.system("%s -T 20 -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))


def inventory(self, name):
    counter = 0
    while counter != 80:
        ip = self.ip(name)
        if ip is None:
            time.sleep(5)
            print("Retrieving ip of %s..." % name)
            counter += 10
        else:
            break
    login = self._ssh_credentials(name)[0]
    if ip is not None:
        return "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
    else:
        return None
