# coding=utf-8
from setuptools import setup, find_namespace_packages

import os
INSTALL = ['argcomplete', 'PyYAML', 'prettytable', 'jinja2', 'libvirt-python>=2.0.0']
AWS = ['boto3']
AZURE = ['azure-mgmt-compute', 'azure-mgmt-network', 'azure-mgmt-core', 'azure-identity', 'azure-mgmt-resource',
         'azure-mgmt-marketplaceordering', 'azure-storage-blob', 'azure-mgmt-dns', 'azure-mgmt-containerservice',
         'azure-mgmt-storage', 'azure-mgmt-msi', 'azure-mgmt-authorization']
GCP = ['google-api-python-client', 'google-auth-httplib2', 'google-cloud-dns', 'google-cloud-storage',
       'google-cloud-container', 'google-cloud-compute']
KUBEVIRT = ['kubernetes']
OPENSTACK = ['python-cinderclient', 'python-neutronclient', 'python-glanceclient', 'python-keystoneclient',
             'python-novaclient', 'python-swiftclient']
OVIRT = ['ovirt-engine-sdk-python']
PACKET = ['packet-python']
PROXMOX = ['proxmoxer']
VSPHERE = ['pyvmomi', 'cryptography']
IBMCLOUD = ['google-crc32c==1.1.2', 'ibm_vpc', 'ibm-cos-sdk', 'ibm-platform-services', 'ibm-cloud-networking-services']
#           'cos-aspera']
EXTRAS = ['pyghmi']
ALL = ['podman'] + ['websockify'] + EXTRAS + AWS + GCP + KUBEVIRT + OPENSTACK + OVIRT\
    + PACKET + VSPHERE + IBMCLOUD + AZURE

description = 'Provisioner/Manager for Libvirt/Vsphere/Aws/Gcp/Kubevirt/Ovirt/Openstack/IBM Cloud and containers'
long_description = description
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()

setup(
    name='kcli',
    version='99.0',
    include_package_data=True,
    packages=find_namespace_packages(),
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
        'libvirt': [],
        'aws': AWS,
        'azure': AZURE,
        'gcp': GCP,
        'ibm': IBMCLOUD,
        'kubevirt': KUBEVIRT,
        'openstack': OPENSTACK,
        'ovirt': OVIRT,
        'packet': PACKET,
        'proxmox': PROXMOX,
        'vsphere': VSPHERE
    },
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
        kweb=kvirt.web.main:run
        klist.py=kvirt.klist:main
        ksushy=kvirt.ksushy.main:run
        ignitionmerger=kvirt.ignitionmerger:cli
        ekstoken=kvirt.ekstoken:cli
        gketoken=kvirt.gketoken:cli
    ''',
)
