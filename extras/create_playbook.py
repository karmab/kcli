#!/usr/bin/env python
# coding=utf-8

import argparse
from getpass import getuser
from jinja2 import Environment, FileSystemLoader
from kvirt import common
from kvirt.baseconfig import Kbaseconfig
from kvirt.cli import handle_parameters
from kvirt.common import pprint, error, container_mode
from kvirt.jinjafilters import jinjafilters
import os
import sys
import yaml


def create_playbook(config, plan, inputfile, overrides={}, store=False):
    playbookdir = os.path.dirname(common.__file__)
    env = Environment(loader=FileSystemLoader(playbookdir), extensions=['jinja2.ext.do'],
                      trim_blocks=True, lstrip_blocks=True)
    for jinjafilter in jinjafilters.jinjafilters:
        env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
    inputfile = os.path.expanduser(inputfile) if inputfile is not None else 'kcli_plan.yml'
    basedir = os.path.dirname(inputfile)
    if basedir == "":
        basedir = '.'
    pprint(f"Using plan {inputfile}...")
    pprint("Make sure to export ANSIBLE_JINJA2_EXTENSIONS=jinja2.ext.do")
    jinjadir = os.path.dirname(jinjafilters.__file__)
    if not os.path.exists('filter_plugins'):
        pprint("Creating symlink to kcli jinja filters")
        os.symlink(jinjadir, 'filter_plugins')
    if not os.path.exists(inputfile):
        error("No input file found nor default kcli_plan.yml. Leaving....")
        sys.exit(1)
    entries, overrides, basefile, basedir = config.process_inputfile(plan, inputfile, overrides=overrides, full=True)
    config_data = {}
    config_data['config_host'] = config.ini[config.client].get('host', '127.0.0.1')
    config_data['config_type'] = config_data.get('config_type', 'kvm')
    default_user = getuser() if config_data['config_type'] == 'kvm'\
        and config_data['config_host'] in ['localhost', '127.0.0.1'] else 'root'
    config_data['config_user'] = config_data.get('config_user', default_user)
    overrides.update(config_data)
    renderfile = config.process_inputfile(plan, inputfile, overrides=overrides, onfly=False, ignore=True)
    try:
        data = yaml.safe_load(renderfile)
    except:
        error("Couldnt' parse plan. Leaving....")
        sys.exit(1)
    for key in data:
        if 'type' in data[key] and data[key]['type'] != 'kvm':
            continue
        elif 'scripts' not in data[key] and 'files' not in data[key] and 'cmds' not in data[key]:
            continue
        else:
            config.create_vm_playbook(key, data[key], overrides=overrides, store=store, env=env)


def run(args):
    store = args.store
    plan = args.plan or 'xxx'
    overrides = handle_parameters(args.param, args.paramfile)
    inputfile = overrides.get('inputfile') or args.inputfile or 'kcli_plan.yml'
    if container_mode():
        inputfile = f"/workdir/{inputfile}"
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    _type = baseconfig.ini[baseconfig.client].get('type', 'kvm')
    overrides.update({'type': _type})
    create_playbook(baseconfig, plan, inputfile, overrides=overrides, store=store)


parser = argparse.ArgumentParser(description='Create playbook from plan')
parser.add_argument('-C', '-c', '--client')
parser.add_argument('-d', '-D', '--debug', action='store_true')
parser.add_argument('-f', '--inputfile', help='Input Plan/File', default='kcli_plan.yml')
parser.add_argument('-P', '--param', action='append',
                    help='specify parameter or keyword for rendering (multiple can be specified)', metavar='PARAM')
parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE', action='append')
parser.add_argument('-s', '--store', action='store_true', help="Store results in files")
parser.add_argument('plan', metavar='PLAN', nargs='?')

args = parser.parse_args()
run(args)
