# coding=utf-8
from setuptools import setup, find_packages

import os
INSTALL = ['argcomplete', 'PyYAML', 'prettytable', 'jinja2', 'libvirt-python>=2.0.0']
AWS = ['boto3']
GCP = ['google-api-python-client', 'google-auth-httplib2', 'google-cloud-dns', 'google-cloud-storage']
KUBEVIRT = ['kubernetes']
OPENSTACK = ['python-cinderclient', 'python-neutronclient', 'python-glanceclient', 'python-keystoneclient',
             'python-novaclient', 'python-swiftclient']
OVIRT = ['ovirt-engine-sdk-python']
PACKET = ['packet-python']
VSPHERE = ['requests', 'pyvmomi']
IBMCLOUD = ['google-crc32c==1.1.2', 'ibm_vpc', 'ibm-cos-sdk', 'ibm-platform-services', 'ibm-cloud-networking-services']
#           'cos-aspera']
EXTRAS = ['pyghmi']
ALL = ['docker>=2.0'] + ['podman'] + ['websockify'] + EXTRAS + AWS + GCP + KUBEVIRT + OPENSTACK + OVIRT\
    + PACKET + VSPHERE + IBMCLOUD

description = 'Provisioner/Manager for Libvirt/Ovirt/Gcp/Aws/Openstack/Kubevirt/IBM Cloud and containers'
long_description = description
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()

setup(
    name='kcli',
    version='99.0',
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
        'ibm': IBMCLOUD,
    },
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
        kweb=kvirt.web.main:run
        klist.py=kvirt.klist:main
        ksushy=kvirt.ksushy.main:run
        ignitionmerger=kvirt.ignitionmerger:cli
    ''',
)
