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
         tunneluser=None, yamlinventory=False):
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
    if yamlinventory:
        info = {'ansible_user': login}
        inventoryfile = "/tmp/%s.inv.yaml" % name
        if '.' in ip:
            info['ansible_host'] = ip
        else:
            info['ansible_host'] = '127.0.0.1'
            info['ansible_port'] = ip
        inventory = {'ungrouped': {'hosts': {name: info}}}
    else:
        inventoryfile = "/tmp/%s.inv" % name
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
                if yamlinventory:
                    inventory['ungrouped']['hosts'][name][key] = value
                else:
                    inventory += " %s=%s" % (key, value)
    if tunnel and tunnelport and tunneluser:
        tunnelinfo = "-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"" % (tunnelport, tunneluser, tunnelhost)
        if yamlinventory:
            inventory['ungrouped']['hosts'][name]['ansible_ssh_common_args'] = tunnelinfo
        else:
            inventory += " ansible_ssh_common_args='%s'" % tunnelinfo
    with open(inventoryfile, 'w') as f:
        if yamlinventory:
            dump(inventory, f, default_flow_style=False)
        else:
            f.write("%s\n" % inventory)
    pprint("Ansible Command run:")
    pprint("%s -T 20 -i %s %s" % (ansiblecommand, inventoryfile, playbook))
    os.system("%s -T 20 -i %s %s" % (ansiblecommand, inventoryfile, playbook))


def vm_inventory(k, name, user=None, yamlinventory=False):
    """

    :param self:
    :param name:
    :return:
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
    info = {'ansible_user': login} if yamlinventory else ''
    if ip is not None:
        if '.' in ip:
            if yamlinventory:
                info['ansible_host'] = ip
            else:
                info = "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
        else:
            if yamlinventory:
                info['ansible_host'] = '127.0.0.1'
                info['ansible_port'] = ip
            else:
                info = "%s ansible_host=127.0.0.1 ansible_user=%s ansible_port=%s" % (name, login, ip)
        return info
    else:
        return None


def make_plan_inventory(vms_to_host, plan, vms, groups={}, user=None, yamlinventory=False):
    """

    :param vms_per_host:
    :param plan:
    :param vms:
    :param groups:
    :param user:
    :param yamlinventory:
    """
    inventory = {}
    clientinventory = {}
    inventoryfile = "/tmp/%s.inv.yaml" % plan if yamlinventory else "/tmp/%s.inv" % plan
    pprint("Generating inventory %s" % inventoryfile, color='blue')
    if groups:
        inventory[plan] = {'children': {}}
        for group in groups:
            inventory[plan]['children'][group] = {}
        for group in groups:
            nodes = groups[group]
            inventory[plan]['children'][group]['hosts'] = {}
            for name in nodes:
                k = vms_to_host[name].k
                client = vms_to_host[name].client
                if client not in clientinventory:
                    clientinventory[client] = {'hosts': {}}
                inv = vm_inventory(k, name, user=user, yamlinventory=yamlinventory)
                if inv is not None:
                    clientinventory[client]['hosts'][name] = inv
                    inventory[plan]['children'][group]['hosts'][name] = inv
    else:
        inventory[plan] = {'hosts': {}}
        for name in vms:
            k = vms_to_host[name].k
            client = vms_to_host[name].client
            if client not in clientinventory:
                clientinventory[client] = {'hosts': {}}
            inv = vm_inventory(k, name, user=user, yamlinventory=yamlinventory)
            if inv is not None:
                inventory[plan]['hosts'][name] = {} if yamlinventory else inv
                clientinventory[client]['hosts'][name] = inv
    for entry in vms_to_host.values():
        client = entry.client
        tunnel = entry.tunnel
        tunneluser = entry.user
        tunnelport = entry.port
        tunnelhost = entry.host
        if tunnel:
            tunnelinfo = "-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"" % (tunnelport, tunneluser, tunnelhost)
            if client in clientinventory and 'vars' not in clientinventory[client]:
                clientinventory[client]['vars'] = {'ansible_ssh_common_args': tunnelinfo}
    with open(inventoryfile, "w") as f:
        if yamlinventory:
            inventory.update(clientinventory)
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
            for cli in clientinventory:
                inventorystr += "[%s]\n" % cli
                for name in clientinventory[client]['hosts']:
                    inventorystr += "%s\n" % clientinventory[client]['hosts'][name]
                inventorystr += "[%s:vars]\n" % cli
                tunnelinfo = clientinventory[cli]['vars']['ansible_ssh_common_args']
                inventorystr += "ansible_ssh_common_args='%s'\n" % tunnelinfo
            f.write("%s\n" % inventorystr)
