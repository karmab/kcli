#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

import os
import time
from kvirt.common import pprint
from yaml import dump


def play(k, name, playbook, variables=[], verbose=False, user=None, tunnel=False, tunnelhost=None, tunnelport=None,
         tunneluser=None, yamlinventory=False, insecure=True):
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
    if user is None:
        info = k.info(name, debug=False)
        user = info.get('user', 'root')
    ip = None
    counter = 0
    while counter != 180:
        ip = k.ip(name)
        if ip is not None:
            break
        else:
            pprint("Retrieving ip of %s..." % name, color='blue')
            time.sleep(5)
            counter += 10
    if ip is None:
        pprint("No ip found for %s. Not running playbook" % name, color='red')
        return
    if yamlinventory:
        info = {'ansible_user': user}
        inventoryfile = "/tmp/%s.inv.yaml" % name
        info['ansible_host'] = ip
        inventory = {'ungrouped': {'hosts': {name: info}}}
    else:
        inventoryfile = "/tmp/%s.inv" % name
        inventory = "%s ansible_host=%s ansible_user=%s" % (name, ip, user)
    ansiblecommand = "ansible-playbook"
    if verbose:
        ansiblecommand = "%s -vvv" % ansiblecommand
    if variables is not None:
        for variable in variables:
            if not isinstance(variable, dict) or len(list(variable)) != 1:
                continue
            else:
                key, value = list(variable)[0], variable[list(variable)[0]]
                if yamlinventory:
                    inventory['ungrouped']['hosts'][name][key] = value
                else:
                    inventory += " %s=%s" % (key, value)
    ssh_args = "-o CheckHostIP=no -o StrictHostKeyChecking=no" if insecure else ""
    if tunnel and tunnelport and tunneluser:
        tunnelinfo = "-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"" % (tunnelport, tunneluser, tunnelhost)
        ssh_args += " %s" % tunnelinfo
    if yamlinventory:
        inventory['ungrouped']['hosts'][name]['ansible_ssh_common_args'] = ssh_args
    else:
        inventory += " ansible_ssh_common_args='%s'" % ssh_args
    with open(inventoryfile, 'w') as f:
        if yamlinventory:
            dump(inventory, f, default_flow_style=False)
        else:
            f.write("%s\n" % inventory)
    pprint("Ansible Command run:")
    pprint("%s -T 20 -i %s %s" % (ansiblecommand, inventoryfile, playbook))
    os.system("%s -T 20 -i %s %s" % (ansiblecommand, inventoryfile, playbook))


def vm_inventory(k, name, user=None, yamlinventory=False, insecure=True):
    """

    :param self:
    :param name:
    :return:
    """
    if user is None:
        info = k.info(name, debug=False)
        user = info.get('user', 'root')
    counter = 0
    while counter != 180:
        ip = k.ip(name)
        if ip is None:
            time.sleep(5)
            pprint("Retrieving ip of %s..." % name)
            counter += 10
        else:
            break
    ssh_args = "-o CheckHostIP=no -o StrictHostKeyChecking=no" if insecure else ""
    info = {'ansible_user': user} if yamlinventory else ''
    if ip is not None:
        if yamlinventory:
            info['ansible_host'] = ip
        else:
            info = "%s ansible_host=%s ansible_user=%s ansible_ssh_common_args='%s'" % (name, ip, user, ssh_args)
        return info
    else:
        return None


def make_plan_inventory(vms_to_host, plan, vms, groups={}, user=None, yamlinventory=False, insecure=True):
    """

    :param vms_per_host:
    :param plan:
    :param vms:
    :param groups:
    :param user:
    :param yamlinventory:
    """
    inventory = {}
    inventoryfile = "/tmp/%s.inv.yaml" % plan if yamlinventory else "/tmp/%s.inv" % plan
    pprint("Generating inventory %s" % inventoryfile, color='blue')
    allvms = vms
    inventory[plan] = {}
    if groups:
        inventory[plan] = {'children': {}}
        for group in groups:
            inventory[plan]['children'][group] = {}
        for group in groups:
            nodes = groups[group]
            inventory[plan]['children'][group]['hosts'] = {}
            for name in nodes:
                allvms.remove(name)
                k = vms_to_host[name].k
                inv = vm_inventory(k, name, user=user, yamlinventory=yamlinventory, insecure=insecure)
                if inv is not None:
                    inventory[plan]['children'][group]['hosts'][name] = inv
    inventory[plan]['hosts'] = {}
    for name in allvms:
        k = vms_to_host[name].k
        inv = vm_inventory(k, name, user=user, yamlinventory=yamlinventory, insecure=insecure)
        if inv is not None:
            inventory[plan]['hosts'][name] = inv
    with open(inventoryfile, "w") as f:
        if yamlinventory:
            dump({'all': {'children': inventory}}, f, default_flow_style=False)
        else:
            inventorystr = ''
            if groups:
                for group in inventory[plan]['children']:
                    inventorystr += "[%s]\n" % group
                    for name in inventory[plan]['children'][group]['hosts']:
                        inventorystr += "%s\n" % inventory[plan]['children'][group]['hosts'][name]
            else:
                inventorystr += "[%s]\n" % plan
                for name in inventory[plan]['hosts']:
                    inventorystr += "%s\n" % inventory[plan]['hosts'][name]
            f.write("%s\n" % inventorystr)
