#!/usr/bin/env python
# coding=utf-8

import argparse
import json
import os


def error(text):
    color = "31"
    print('\033[0;%sm%s\033[0;0m' % (color, text))


def warning(text):
    color = "33"
    print('\033[0;%sm%s\033[0;0m' % (color, text))


def info(text):
    color = "36"
    print('\033[0;%sm%s\033[0;0m' % (color, text))


def success(text):
    color = "32"
    print('\033[0;%sm%s\033[0;0m' % (color, text))


def merge2ignitions(newdata, data):
    children = {'storage': 'files', 'passwd': 'users', 'systemd': 'units'}
    for key in children:
        childrenkey2 = 'path' if key == 'storage' else 'name'
        if key in data and key in newdata:
            if children[key] in data[key] and children[key] in newdata[key]:
                for entry in data[key][children[key]]:
                    if entry[childrenkey2] not in [x[childrenkey2] for x in newdata[key][children[key]]]:
                        newdata[key][children[key]].append(entry)
                    elif children[key] == 'users':
                        newusers = []
                        users = [x['name'] for x in data[key][children[key]] + newdata[key][children[key]]]
                        users = list(dict.fromkeys(users))
                        for user in users:
                            newuser = {'name': user}
                            sshkey1, sshkey2 = [], []
                            password = None
                            for y in data[key][children[key]]:
                                if y['name'] == user:
                                    sshkey1 = y['sshAuthorizedKeys'] if 'sshAuthorizedKeys' in y else []
                                    password = y.get('passwordHash')
                            for x in newdata[key][children[key]]:
                                if x['name'] == user:
                                    sshkey2 = x['sshAuthorizedKeys'] if 'sshAuthorizedKeys' in x else []
                                    password = x.get('passwordHash')
                            sshkeys = sshkey1
                            if sshkey2:
                                sshkeys.extend(sshkey2)
                            if sshkeys:
                                sshkeys = list(dict.fromkeys([sshkey.strip() for sshkey in sshkeys]))
                                newuser['sshAuthorizedKeys'] = sshkeys
                            if password is not None:
                                newuser['passwordHash'] = password
                            newusers.append(newuser)
                        newdata[key][children[key]] = newusers
            elif children[key] in data[key] and children[key] not in newdata[key]:
                newdata[key][children[key]] = data[key][children[key]]
        elif key in data and key not in newdata:
            newdata[key] = data[key]
    if 'ignition' in data and 'config' in data['ignition'] and data['ignition']['config']:
        newdata['ignition']['config'] = data['ignition']['config']
    return newdata


def mergeignition(args):
    version = '3.1.0'
    separators = (',', ':') if args.compact else (',', ': ')
    indent = 0 if args.compact else 4
    paths = args.paths
    data = {}
    for path in paths:
        if not os.path.exists(path):
            error("Missing path %s. Ignoring" % path)
            os._exit(1)
        else:
            with open(path, 'r') as extra:
                try:
                    newdata = json.load(extra)
                except:
                    error("Couldn't process %s. Leaving" % path)
                    os._exit(1)
            data = merge2ignitions(newdata, data)
    if 'ignition' not in data:
        data['ignition'] = {'config': {}, 'version': version}
    print(json.dumps(data, sort_keys=True, indent=indent, separators=separators))


def cli():
    parser = argparse.ArgumentParser(description="Merge your ignition files")
    parser.add_argument('-c', '--compact', action='store_true', help="Generate a compact ignition")
    parser.add_argument("paths", help="The path of your ignition files", nargs='+', type=str)
    parser.set_defaults(func=mergeignition)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    cli()
