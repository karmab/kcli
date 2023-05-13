# coding=utf-8
from setuptools import setup

description = 'Redfish helper library'
long_description = description
setup(
    name='kfish',
    version='99.0',
    include_package_data=False,
    packages=['kfish'],
    package_dir={'kfish': 'kvirt/kfish'},
    zip_safe=False,
    description=description,
    long_description=long_description,
    url='https://github.com/karmab/kcli/blob/main/extras/kfish.md',
    author='Karim Boumedhel',
    author_email='karimboumedhel@gmail.com',
    license='ASL',
)
