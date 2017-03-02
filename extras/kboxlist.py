#!/usr/bin/python

'''
ansible dynamic inventory script for use with kcli and virtualbox
'''

from kvirt.vbox import Kbox
import json
import os
import argparse


def empty():
    return {'_meta': {'hostvars': {}}}


class KBoxInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()
        self.k = Kbox()
        if self.k.conn is None:
            print "Couldnt connect to specify hypervisor %s. Leaving..." % self.host
            os._exit(1)

        # Called with `--list`.
        if self.args.list:
            self.inventory = self.get()
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = empty()
        # If no groups or vars are present, return an empty inventory.
        else:
            self.inventory = empty()
        print json.dumps(self.inventory)

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action='store_true')
        parser.add_argument('--host', action='store')
        self.args = parser.parse_args()

    def get(self):
        ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety']
        k = self.k
        metadata = {'_meta': {'hostvars': {}}}
        hostvalues = metadata['_meta']['hostvars']
        for vm in k.list():
            name = vm[0]
            status = vm[1]
            port = vm[2]
            template = vm[3]
            description = vm[4]
            profile = vm[5]
            if description == '':
                description = 'kvirt'
            if description not in metadata:
                metadata[description] = {"hosts": [name], "vars": {"plan": description, "profile": profile}}
            else:
                metadata[description]["hosts"].append(name)
            hostvalues[name] = {'status': status}
            hostvalues[name]['ansible_host'] = '127.0.0.1'
            if port != '':
                hostvalues[name]['ansible_port'] = port
            if template != '':
                if 'centos' in template.lower():
                    hostvalues[name]['ansible_user'] = 'centos'
                elif 'cirros' in template.lower():
                    hostvalues[name]['ansible_user'] = 'cirros'
                elif [x for x in ubuntus if x in template.lower()]:
                    hostvalues[name]['ansible_user'] = 'ubuntu'
                elif 'fedora' in template.lower():
                    hostvalues[name]['ansible_user'] = 'fedora'
                elif 'rhel' in template.lower():
                    hostvalues[name]['ansible_user'] = 'cloud-user'
                elif 'debian' in template.lower():
                    hostvalues[name]['ansible_user'] = 'debian'
                elif 'arch' in template.lower():
                    hostvalues[name]['ansible_user'] = 'arch'
        return metadata

# Get the inventory.
KBoxInventory()
