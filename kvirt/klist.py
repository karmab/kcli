#!/usr/bin/env python3
# coding=utf-8

from kvirt.config import Kconfig
from kvirt.common import get_user
import json
import sys
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
            sys.exit(1)

        # Called with `--list`.
        if self.args.list:
            self.inventory = self._list()
        # Called with `--host [hostname]`.
        elif self.args.host:
            self.inventory = self.get(self.args.host)
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

    def _list(self):
        """

        :return:
        """
        k = self.k
        tunnel = self.tunnel
        metadata = {'_meta': {'hostvars': {}}}
        hostvalues = metadata['_meta']['hostvars']
        for vm in k.list():
            name = vm.get('name')
            status = vm.get('status')
            ip = vm.get('ip', '')
            image = vm.get('image')
            plan = vm.get('plan', 'kvirt')
            if plan == '':
                plan = 'kvirt'
            profile = vm.get('profile', '')
            if plan not in metadata:
                metadata[plan] = {"hosts": [name], "vars": {"plan": plan, "profile": profile}}
            else:
                metadata[plan]["hosts"].append(name)
            hostvalues[name] = {'status': status}
            if tunnel and self.type in ['kvm', 'kubevirt']:
                hostvalues[name]['ansible_ssh_common_args'] = \
                    "-o ProxyCommand='ssh -p %s -W %%h:%%p %s@%s'" % (self.port, self.user, self.host)
            if ip != '':
                hostvalues[name]['ansible_host'] = ip
                if image != '':
                    user = get_user(image)
                    hostvalues[name]['ansible_user'] = user
        return metadata

    def get(self, name):
        """

        :return:
        """
        k = self.k
        tunnel = self.tunnel
        metadata = {}
        vm = k.info(name)
        for entry in ['name', 'template', 'plan', 'profile', 'ip']:
            metadata[entry] = vm.get(entry)
        if metadata['plan'] == '':
            metadata['plan'] = 'kvirt'
        if tunnel and self.type in ['kvm', 'kubevirt']:
            metadata['ansible_ssh_common_args'] = \
                "-o ProxyCommand='ssh -p %s -W %%h:%%p %s@%s'" % (self.port, self.user, self.host)
        ip = metadata['ip']
        if ip != '':
            metadata['ansible_host'] = ip
            template = metadata['template']
            if template != '':
                user = get_user(template)
                metadata['ansible_user'] = user
        return metadata


def main():
    KcliInventory()


if __name__ == "__main__":
    main()
