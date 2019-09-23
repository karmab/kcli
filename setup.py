# coding=utf-8
from setuptools import setup, find_packages

import os
INSTALL = ['netaddr', 'PyYAML', 'prettytable', 'jinja2', 'flask', 'libvirt-python>=2.0.0']
AWS = ['boto3']
GCP = ['google-api-python-client', 'google-auth-httplib2', 'google-cloud-dns']
KUBEVIRT = ['kubernetes']
OPENSTACK = ['python-cinderclient', 'python-neutronclient', 'python-glanceclient', 'python-keystoneclient',
             'python-novaclient']
OVIRT = ['ovirt-engine-sdk-python']
VSPHERE = ['pyvmomi']
ALL = ['docker>=2.0'] + ['podman'] + AWS + GCP + KUBEVIRT + OPENSTACK + OVIRT + VSPHERE

description = 'Provisioner/Manager for Libvirt/Ovirt/Gcp/Aws/Openstack/Kubevirt and containers'
long_description = description
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()

setup(
    name='kcli',
    version='15.1',
    include_package_data=True,
    packages=find_packages(),
    zip_safe=False,
    description=description,
    long_description=long_description,
    url='http://github.com/karmab/kcli',
    author='Karim Boumedhel',
    author_email='karimboumedhel@gmail.com',
    license='ASL',
    install_requires=INSTALL,
    extras_require={
        'all': ALL,
        'aws': AWS,
        'gcp': GCP,
        'kubevirt': KUBEVIRT,
        'openstack': OPENSTACK,
        'ovirt': OVIRT,
        'vsphere': VSPHERE,
    },
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
        kweb=kvirt.web:run
    ''',
)
