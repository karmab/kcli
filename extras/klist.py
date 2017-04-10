#!/usr/bin/python

'''
ansible dynamic inventory script for use with kcli
'''

from kvirt import Kvirt
import json
import yaml
import os
import argparse


def empty():
    return {'_meta': {'hostvars': {}}}


class KcliInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            ini = {'default': {'client': 'local'}, 'local': {}}
            print("Using local hypervisor as no kcli.yml was found...")
        else:
            with open(inifile, 'r') as entries:
                ini = yaml.load(entries)
            if 'default' not in ini or 'client' not in ini['default']:
                print("Missing default section in config file. Leaving...")
                os._exit(1)
        client = ini['default']['client']
        if client not in ini:
            print("Missing section for client %s in config file. Leaving..." % client)
            os._exit(1)
        options = ini[client]
        host = options.get('host', '127.0.0.1')
        port = options.get('port', None)
        user = options.get('user', 'root')
        protocol = options.get('protocol', 'ssh')
        self.k = Kvirt(host=host, port=port, user=user, protocol=protocol)
        if self.k.conn is None:
            print("Couldnt connect to specify hypervisor %s. Leaving..." % host)
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
        print(json.dumps(self.inventory))

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
            ip = vm[2]
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
            if ip != '':
                hostvalues[name]['ansible_host'] = ip
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
KcliInventory()
