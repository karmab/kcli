from kvirt.common import pprint
import os

TEMPLATES = {'CentOS-6-x86_64-GenericCloud.qcow2': 'CentOS 6 Generic Cloud Image v1802 for x86_64',
             'CentOS-Atomic-Host-7-GenericCloud.qcow2': 'CentOS 7 Atomic Host Image v1802 for x86_64',
             'CentOS-7-x86_64-GenericCloud.qcow2': 'CentOS 7 Generic Cloud Image v1805 for x86_64',
             'cirros-0.4.0-x86_64-disk.img': 'CirrOS 0.4.0 for x86_64',
             'Fedora-Cloud-Base-24-1.2.x86_64.qcow2': 'Fedora 24 Cloud Base Image v20160921.0 for x86_64',
             'Fedora-Cloud-Base-25-1.3.x86_64.qcow2': 'Fedora 25 Cloud Base Image v20170106.0 for x86_64',
             'Fedora-Cloud-Base-26-1.5.x86_64.qcow2': 'Fedora 26 Cloud Base Image v1.5 for x86_64',
             'Fedora-Cloud-Base-27-1.6.x86_64.qcow2': 'Fedora 27 Cloud Base Image v1.6 for x86_64',
             'Fedora-Cloud-Base-28-1.1.x86_64.qcow2': 'Fedora 28 Cloud Base Image v1.1 for x86_64',
             'manageiq-openstack-euwe-3.qc2': 'ManageIQ Fine-4 for x86_64',
             'manageiq59': 'ManageIQ Gaprindashvili-2 for x86_64',
             'trusty-server-cloudimg-amd64-disk1.img':
             'Ubuntu Server 14.04 LTS (Trusty Tahr) Cloud Image v20170110 for x86_64',
             'xenial-server-cloudimg-amd64-disk1.img':
             'Ubuntu Server 16.04 LTS (Xenial Xerus) Cloud Image v20170111 for x86_64',
             'yakkety-server-cloudimg-amd64-disk1.img':
             'Ubuntu Server 16.10 (Yakkety Yak) Cloud Image v20170106 for x86_64'}


def get_home_ssh_key():
    key = None
    if os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
        publickeyfile = "%s/.ssh/id_rsa.pub" % os.environ['HOME']
        with open(publickeyfile, 'r') as ssh:
            key = ssh.read().rstrip()
    elif os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
        publickeyfile = "%s/.ssh/id_dsa.pub" % os.environ['HOME']
        with open(publickeyfile, 'r') as ssh:
            key = ssh.read().rstrip()
    else:
        pprint("neither id_rsa or id_dsa public keys found in your .ssh directory, you might have trouble "
               "accessing the vm", color='red')
    return key
