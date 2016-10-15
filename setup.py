from setuptools import setup, find_packages

import os
description = 'Libvirt wrapper on steroids'
long_description = description
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()

setup(
    name='kcli',
    version='1.0.51',
    packages=find_packages(),
    include_package_data=True,
    description=description,
    long_description=long_description,
    url='http://github.com/karmab/kcli',
    author='Karim Boumedhel',
    author_email='karimboumedhel@gmail.com',
    license='GPL',
    install_requires=[
        'libvirt-python>=2.2.0',
        'Click',
        'iptools',
        'netaddr',
        'PyYAML',
        'prettytable',
    ],
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
    ''',
)
