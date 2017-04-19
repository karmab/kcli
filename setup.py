from setuptools import setup, find_packages

import os
description = 'Libvirt/VirtualBox wrapper on steroids'
long_description = description
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()

setup(
    name='kcli',
    version='6.6',
    include_package_data=True,
    packages=find_packages(),
    zip_safe=False,
    description=description,
    long_description=long_description,
    url='http://github.com/karmab/kcli',
    author='Karim Boumedhel',
    author_email='karimboumedhel@gmail.com',
    license='GPL',
    install_requires=[
        'libvirt-python>=2.2.0',
        'docker',
        'flask',
        'iptools',
        'netaddr',
        'PyYAML',
        'prettytable',
        'pyvbox',
    ],
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
        kweb=kvirt.web:run
    ''',
)
