#!/usr/bin/python3
import logging
import os
import sys
from kvirt.config import Kconfig
from kvirt.expose import Kexposer
logging.basicConfig(stream=sys.stdout)

os.environ['HOME'] = '/usr/share/httpd'
inputfile = '/var/www/kcli-openshift4-baremetal/kcli_plan.yml'
overrides = {'openshift_image': 'registry.svc.ci.openshift.org/ocp/release:4.5'}
config = Kconfig()
kexposer = Kexposer(config, inputfile, overrides=overrides)
application = kexposer.app
application.secret_key = 'KcliExpose'
