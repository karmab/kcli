# coding=utf-8
from setuptools import setup, find_packages

import os
INSTALL = ['argcomplete', 'netaddr', 'PyYAML', 'prettytable', 'jinja2', 'flask', 'libvirt-python>=2.0.0', 'requests']
AWS = ['boto3']
GCP = ['google-api-python-client', 'google-auth-httplib2', 'google-cloud-dns']
KUBEVIRT = ['kubernetes']
OPENSTACK = ['python-cinderclient', 'python-neutronclient', 'python-glanceclient', 'python-keystoneclient',
             'python-novaclient']
OVIRT = ['ovirt-engine-sdk-python']
PACKET = ['packet-python']
VSPHERE = ['requests', 'pyvmomi']
GRPC = ['grpcio', 'grpcio-reflection']
EXTRAS = ['pyghmi']
ALL = ['docker>=2.0'] + ['podman'] + ['websockify'] + GRPC + EXTRAS + AWS + GCP + KUBEVIRT + OPENSTACK + OVIRT\
    + PACKET + VSPHERE

description = 'Provisioner/Manager for Libvirt/Ovirt/Gcp/Aws/Openstack/Kubevirt and containers'
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
        'grpc': GRPC,
    },
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
        kweb=kvirt.web.main:run
        klist.py=kvirt.klist:main
        kbmc=kvirt.kbmc:main
        krpc=kvirt.krpc.server:main
        kclirpc=kvirt.krpc.cli:cli
    ''',
)
