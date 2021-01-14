# coding=utf-8
from kvirt.common import warning
import os

IMAGES = {'CentOS-6-x86_64-GenericCloud.qcow2': 'CentOS 6 Generic Cloud Image',
          'CentOS-Atomic-Host-7-GenericCloud.qcow2': 'CentOS 7 Atomic Host Image',
          'CentOS-7-x86_64-GenericCloud.qcow2': 'CentOS 7 Generic Cloud Image',
          'cirros-0.4.0-x86_64-disk.img': 'CirrOS 0.4.0 for x86_64',
          'Fedora-Cloud-Base-24-1.2.x86_64.qcow2': 'Fedora 24 Cloud Base Image v20160921.0 for x86_64',
          'Fedora-Cloud-Base-25-1.3.x86_64.qcow2': 'Fedora 25 Cloud Base Image v20170106.0 for x86_64',
          'Fedora-Cloud-Base-26-1.5.x86_64.qcow2': 'Fedora 26 Cloud Base Image v1.5 for x86_64',
          'Fedora-Cloud-Base-27-1.6.x86_64.qcow2': 'Fedora 27 Cloud Base Image v1.6 for x86_64',
          'Fedora-Cloud-Base-28-1.1.x86_64.qcow2': 'Fedora 28 Cloud Base Image v1.1 for x86_64',
          'trusty-server-cloudimg-amd64-disk1.img':
          'Ubuntu Server 14.04 LTS (Trusty Tahr) Cloud Image v20170110 for x86_64',
          'xenial-server-cloudimg-amd64-disk1.img':
          'Ubuntu Server 16.04 LTS (Xenial Xerus) Cloud Image v20170111 for x86_64',
          'yakkety-server-cloudimg-amd64-disk1.img':
          'Ubuntu Server 16.10 (Yakkety Yak) Cloud Image v20170106 for x86_64'}


def get_home_ssh_key():
    """

    :return:
    """
    key = None
    if os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub")):
        publickeyfile = os.path.expanduser("~/.ssh/id_rsa.pub")
        with open(publickeyfile, 'r') as ssh:
            key = ssh.read().rstrip()
    elif os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub")):
        publickeyfile = os.path.expanduser("~/.ssh/id_dsa.pub")
        with open(publickeyfile, 'r') as ssh:
            key = ssh.read().rstrip()
    elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub")):
        publickeyfile = os.path.expanduser("~/.kcli/id_rsa.pub")
        with open(publickeyfile, 'r') as ssh:
            key = ssh.read().rstrip()
    elif os.path.exists(os.path.expanduser("~/.kcli/id_dsa.pub")):
        publickeyfile = os.path.expanduser("~/.kcli/id_rda.pub")
        with open(publickeyfile, 'r') as ssh:
            key = ssh.read().rstrip()
    else:
        warning("neither id_rsa or id_dsa public keys found in your .ssh or .kcli directory, you might have trouble "
                "accessing the vm")
    return key
