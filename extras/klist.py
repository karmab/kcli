#!/usr/bin/env python3
# coding=utf-8

from kvirt.config import Kconfig
from kvirt.common import get_user
import json
import os
import argparse


def empty():
    """

    :return:
    """
    return {'_meta': {'hostvars': {}}}


class KcliInventory(object):
    """

    """
    def __init__(self):
        self.inventory = {}
        self.read_cli_args()
        config = Kconfig(quiet=True)
        self.host = config.host
        self.port = config.port
        self.user = config.user
        self.tunnel = config.tunnel
        self.k = config.k
        self.type = config.type
        if self.k.conn is None:
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
        """

        """
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action='store_true')
        parser.add_argument('--host', action='store')
        self.args = parser.parse_args()

    def get(self):
        """

        :return:
        """
        k = self.k
        tunnel = self.tunnel
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
            if tunnel and self.type in ['kvm', 'kubevirt']:
                hostvalues[name]['ansible_ssh_common_args'] = \
                    "-o ProxyCommand='ssh -p %s -W %%h:%%p %s@%s'" % (self.port, self.user, self.host)
            if ip != '':
                if self.type == 'vbox':
                    hostvalues[name]['ansible_host'] = '127.0.0.1'
                    hostvalues[name]['ansible_port'] = ip
                else:
                    hostvalues[name]['ansible_host'] = ip
                if template != '':
                    user = get_user(template)
                    hostvalues[name]['ansible_user'] = user
        return metadata


KcliInventory()
