#!/usr/bin/env python
# coding=utf-8

import argparse
from getpass import getuser
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError, TemplateError
from kvirt.baseconfig import Kbaseconfig
from kvirt.cli import handle_parameters
from kvirt.common import pprint, error, container_mode
from kvirt.jinjafilters import jinjafilters
import os
import sys
from tempfile import TemporaryDirectory
import yaml

playbook_template = """---
- hosts: {{ hostname }}
  become: yes
  vars:
{% for override in overrides %}
    {{ override }}: {{ overrides[override] if overrides[override] != None else ''}}
{% endfor %}
  tasks:
{% for dir in dirs %}
  - name: Creates directory {{ dir }}
    file:
      path: {{ dir }}
      state: directory
{% endfor %}
{% for file in files %}
{% set mode = 700 if file['origin'].endswith('.py') or file['origin'].endswith('.sh') else 600 %}
  - name: Template file {{ file['origin'] }}
    {{ 'template' if file['render']|default(True) else 'copy' }}:
      src: {{ file['origin'] }}
      dest: {{ file['path'] }}
      owner: {{ file['owner']|default('root') }}
      mode: '{{ file['mode']|default(mode) }}'
{% endfor %}
{% if cmds != None %}
  - name: Copy cmds
    copy:
      content: {{ cmds }}
      dest: /root/.cmds.sh
      mode: '700'
  - name: Run cmds script
    shell: /root/.cmds.sh
    register: out
  - name: Result of cmds script
    debug: var=out.stdout_lines
{% endif %}
{% for script in scripts %}
  - name: Template script {{ script }}
    template:
      src: {{ script }}
      dest: /root/.{{ script }}
      owner: 'root'
      mode: '700'
  - name: Run script {{ script }} and log in /root/.{{ script }}.log
    shell: /root/.{{ script }} > /root/.{{ script }}.log 2>&1
#    register: out
#  - name: Result of script {{ script }}
#    debug: var=out.stdout_lines
{% endfor %}"""


def create_vm_playbook(env, name, profile, overrides={}):
    jinjadir = os.path.dirname(jinjafilters.__file__)
    if not os.path.exists('filter_plugins'):
        pprint("Creating symlink to kcli jinja filters")
        os.symlink(jinjadir, 'filter_plugins')
    dirs = []
    if 'scripts' not in profile:
        profile['scripts'] = []
    profile['cmds'] = '\n'.join(profile['cmds']) if 'cmds' in profile else None
    if 'files' in profile:
        files = []
        for _file in profile['files']:
            if isinstance(_file, str):
                entry = {'path': f'/root/{_file}', 'origin': _file, 'mode': 700}
            else:
                entry = _file
            if os.path.isdir(entry['origin']):
                dirs.append(entry['origin'])
                continue
            if entry['path'].count('/') > 2 and os.path.dirname(entry['path']) not in dirs:
                dirs.append(os.path.dirname(entry['path']))
            files.append(entry)
        profile['files'] = files
    else:
        profile['files'] = []
    try:
        templ = env.get_template(os.path.basename("playbook.j2"))
    except TemplateSyntaxError as e:
        error(f"Error rendering line {e.lineno} of file {e.filename}. Got: {e.message}")
        sys.exit(1)
    except TemplateError as e:
        error(f"Error rendering playbook. Got: {e.message}")
        sys.exit(1)
    hostname = overrides.get('hostname', name)
    profile['hostname'] = hostname
    if 'info' in overrides:
        del overrides['info']
    profile['overrides'] = overrides
    profile['dirs'] = dirs
    playbookfile = templ.render(**profile)
    playbookfile = '\n'.join([line for line in playbookfile.split('\n') if line.strip() != ""])
    print(playbookfile)


def create_playbook(baseconfig, plan, inputfile, overrides={}):
    playbooktmpdir = TemporaryDirectory()
    playbookdir = playbooktmpdir.name
    with open(f'{playbookdir}/playbook.j2', 'w') as f:
        f.write(playbook_template)
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
    if 'baseplan' in overrides:
        del overrides['baseplan']
    entries, overrides, basefile, basedir = baseconfig.process_inputfile(plan, inputfile, overrides=overrides,
                                                                         full=True)
    config_data = {}
    config_data['config_host'] = baseconfig.ini[baseconfig.client].get('host', '127.0.0.1')
    config_data['config_type'] = config_data.get('config_type', 'kvm')
    default_user = getuser() if config_data['config_type'] == 'kvm'\
        and config_data['config_host'] in ['localhost', '127.0.0.1'] else 'root'
    config_data['config_user'] = config_data.get('config_user', default_user)
    overrides.update(config_data)
    renderfile = baseconfig.process_inputfile(plan, inputfile, overrides=overrides)
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
            create_vm_playbook(env, key, data[key], overrides=overrides)
    playbooktmpdir.cleanup()


def run(args):
    plan = args.plan or 'playbook'
    overrides = handle_parameters(args.param, args.paramfile)
    inputfile = overrides.get('inputfile') or args.inputfile or 'kcli_plan.yml'
    if container_mode():
        inputfile = f"/workdir/{inputfile}"
    baseconfig = Kbaseconfig(client=args.client)
    _type = baseconfig.ini[baseconfig.client].get('type', 'kvm')
    overrides.update({'type': _type})
    create_playbook(baseconfig, plan, inputfile, overrides=overrides)


parser = argparse.ArgumentParser(description='Create playbook from plan')
parser.add_argument('-C', '-c', '--client')
parser.add_argument('-f', '--inputfile', help='Input Plan/File', default='kcli_plan.yml')
parser.add_argument('-P', '--param', action='append',
                    help='specify parameter or keyword for rendering (multiple can be specified)', metavar='PARAM')
parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE', action='append')
parser.add_argument('plan', metavar='PLAN', nargs='?')

args = parser.parse_args()
run(args)
