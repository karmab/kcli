# coding=utf-8
from setuptools import setup, find_packages

import os
description = 'Libvirt/VirtualBox wrapper on steroids'
long_description = description
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()

setup(
    name='kcli',
    version='14.6',
    include_package_data=True,
    packages=find_packages(),
    zip_safe=False,
    description=description,
    long_description=long_description,
    url='http://github.com/karmab/kcli',
    author='Karim Boumedhel',
    author_email='karimboumedhel@gmail.com',
    license='ASL',
    install_requires=[
        'netaddr',
        'PyYAML',
        'prettytable',
        'jinja2',
        'flask',
        'libvirt-python>=2.0.0',
    ],
    extras_require={
        'all': [
            'docker>=2.0',
            'kubernetes',
            'boto3',
            'google-api-python-client',
            'google-auth-httplib2',
            'google-cloud-dns',
            'ovirt-engine-sdk-python',
            'python-cinderclient',
            'python-neutronclient',
            'python-glanceclient',
            'python-keystoneclient',
            'python-novaclient',
        ]},
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
        kweb=kvirt.web:run
    ''',
)
