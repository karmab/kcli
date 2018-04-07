#!/usr/bin/env python

'''
ansible dynamic inventory script for use with kcli and libvirt
'''

from jinja2 import Environment, FileSystemLoader
from kvirt.common import get_overrides, get_parameters, pprint
from kvirt.config import __version__
import argparse
import os
import yaml


def render(args):
    info = args.info
    inputfile = args.inputfile
    inputfile = os.path.expanduser(inputfile)
    if not os.path.exists(inputfile):
        pprint("No input file found.Leaving....", color='red')
        os._exit(1)
    overrides = get_overrides(paramfile=args.paramfile, param=args.param)
    parameters = get_parameters(inputfile)
    if parameters is not None:
        parameters = yaml.load(parameters)['parameters']
        numparameters = len(parameters)
        for parameter in parameters:
            if parameter not in overrides:
                overrides[parameter] = parameters[parameter]
    if info:
        for parameter in overrides:
            print("Using parameter %s: %s" % (parameter, overrides[parameter]))
        os._exit(0)
    basedir = os.path.dirname(inputfile) if os.path.dirname(inputfile) != '' else '.'
    env = Environment(block_start_string='[%', block_end_string='%]', variable_start_string='[[', variable_end_string=''
                      ']]', loader=FileSystemLoader(basedir))
    templ = env.get_template(os.path.basename(inputfile))
    fileentries = templ.render(overrides)
    parametersfound = -1
    for line in fileentries.split('\n'):
        if line.strip() == '':
            continue
        elif line.startswith('parameters:'):
            parametersfound = 0
        elif parametersfound > -1 and parametersfound < numparameters:
            parametersfound += 1
        else:
            print(line.strip())


def cli():
    parser = argparse.ArgumentParser(description='Render scripts manually using kcli helpers')
    parser.add_argument('-i', '--info', help='Only report parameters used in the file', action='store_true')
    parser.add_argument('-f', '--inputfile', help='Input Plan file', required=True)
    parser.add_argument('-P', '--param', action='append', help='Define parameter for rendering within scripts. '
                        'Can be repeated', metavar='PARAM')
    parser.add_argument('--paramfile', help='Param file', metavar='PARAMFILE')
    parser.add_argument('--version', action='version', version=__version__)
    args = parser.parse_args()
    render(args)


if __name__ == '__main__':
    cli()
