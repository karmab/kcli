#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

import os
import time
from kvirt.common import pprint


def play(k, name, playbook, variables=[], verbose=False, user=None, tunnel=False, tunnelhost=None, tunnelport=None,
         tunneluser=None):
    """

    :param k:
    :param name:
    :param playbook:
    :param variables:
    :param verbose:
    :param tunnelhost:
    :param tunnelport:
    :param tunneluser:
    """
    counter = 0
    while counter != 80:
        ip = k.ip(name)
        if ip is None:
            time.sleep(5)
            pprint("Retrieving ip of %s..." % name)
            counter += 10
        else:
            break
    login = k._ssh_credentials(name)[0] if user is None else user
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
                inventory += " %s=%s" % (key, value)
    if tunnel and tunnelport and tunneluser:
        inventory += " ansible_ssh_common_args='-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"'" %\
            (tunnelport, tunneluser, tunnelhost)
    with open("/tmp/%s.inv" % name, 'w') as f:
        f.write("%s\n" % inventory)
    pprint("Ansible Command run:")
    pprint("%s -T 20 -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
    os.system("%s -T 20 -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))


def vm_inventory(self, name, user=None):
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
            pprint("Retrieving ip of %s..." % name)
            counter += 10
        else:
            break
    login = self._ssh_credentials(name)[0] if user is None else user
    if ip is not None:
        if '.' in ip:
            return "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
        else:
            return "%s ansible_host=127.0.0.1 ansible_user=%s ansible_port=%s" % (name, login, ip)
    else:
        return None


def make_plan_inventory(k, plan, vms, groups={}, user=None, tunnel=False, tunnelhost=None, tunnelport=None,
                        tunneluser=None):
    """

    :param k:
    :param plan:
    :param vms:
    :param groups:
    :param user:
    :param tunnel:
    :param tunnelhost:
    :param tunnelport:
    :param tunneluser:
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
                    inv = vm_inventory(k, name, user=user)
                    if inv is not None:
                        f.write("%s\n" % inv)
        else:
            f.write("[%s]\n" % plan)
            for name in vms:
                inv = vm_inventory(k, name, user=user)
                if inv is not None:
                    f.write("%s\n" % inv)
        if tunnel:
            f.write("[%s:vars]\n" % plan)
            f.write("ansible_ssh_common_args='-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"'" % (tunnelport,
                                                                                                  tunneluser,
                                                                                                  tunnelhost))
