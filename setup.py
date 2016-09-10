from setuptools import setup, find_packages

setup(
    name='kcli',
    version='0.99.4',
    packages=find_packages(),
    include_package_data=True,
    description='Libvirt wrapper on steroids',
    url='http://github.com/karmab/kcli',
    author='Karim Boumedhel',
    author_email='karimboumedhel@gmail.com',
    license='GPL',
    install_requires=[
        'libvirt-python',
        'Click',
    ],
    entry_points='''
        [console_scripts]
        kcli=kvirt.cli:cli
    ''',
)
