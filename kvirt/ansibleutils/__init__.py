#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

# from jinja2 import Environment
import os
import time


def play(self, name, playbook, variables=[], verbose=False):
    """

    :param self:
    :param name:
    :param playbook:
    :param variables:
    :param verbose:
    """
    counter = 0
    while counter != 80:
        ip = self.ip(name)
        if ip is None:
            time.sleep(5)
            print(("Retrieving ip of %s..." % name))
            counter += 10
        else:
            break
    login = self._ssh_credentials(name)[0]
    if '.' in ip:
        inventory = "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
    else:
        inventory = "%s ansible_host=127.0.0.1 ansible_user=%s ansible_port=%s" % (name, login, ip)
    ansiblecommand = "ansible-playbook"
    if verbose:
        ansiblecommand = "%s -vvv" % ansiblecommand
    if variables is not None:
        for variable in variables:
            if not isinstance(variable, dict) or len(list(variable)) != 1:
                continue
            else:
                key, value = list(variable)[0], variable[list(variable)[0]]
                inventory = "%s %s=%s" % (inventory, key, value)
    with open("/tmp/%s.inv" % name, 'w') as f:
        f.write("%s\n" % inventory)
    print("Ansible Command run:")
    print(("%s -T 20 -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook)))
    os.system("%s -T 20 -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))


def inventory(self, name):
    """

    :param self:
    :param name:
    :return:
    """
    counter = 0
    while counter != 80:
        ip = self.ip(name)
        if ip is None:
            time.sleep(5)
            print(("Retrieving ip of %s..." % name))
            counter += 10
        else:
            break
    login = self._ssh_credentials(name)[0]
    if ip is not None:
        if '.' in ip:
            return "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
        else:
            return "%s ansible_host=127.0.0.1 ansible_user=%s ansible_port=%s" % (name, login, ip)
    else:
        return None


def make_inventory(k, plan, vms, tunnel=True, groups={}):
    """

    :param k:
    :param plan:
    :param vms:
    :param tunnel:
    :param groups:
    """
    with open("/tmp/%s.inv" % plan, "w") as f:
        if groups:
            f.write("[%s:children]\n" % plan)
            for group in groups:
                f.write("%s\n" % group)
            for group in groups:
                nodes = groups[group]
                f.write("[%s]\n" % group)
                for name in nodes:
                    inv = inventory(k, name)
                    if inv is not None:
                        f.write("%s\n" % inv)
            if tunnel:
                f.write("[%s:vars]\n" % plan)
        else:
            f.write("[%s]\n" % plan)
            for name in vms:
                inv = inventory(k, name)
                if inv is not None:
                    f.write("%s\n" % inv)
            if tunnel:
                f.write("[%s:vars]\n" % plan)
