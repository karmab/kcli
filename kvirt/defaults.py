NETS = ['default']
POOL = 'default'
TEMPLATE = None
CPUMODEL = 'host-model'
NUMCPUS = 2
MEMORY = 512
DISKINTERFACE = 'virtio'
DISKTHIN = True
DISKSIZE = 10
DISKS = [{'size': DISKSIZE}]
GUESTID = 'guestrhel764'
VNC = False
CLOUDINIT = True
RESERVEIP = False
RESERVEDNS = False
RESERVEHOST = False
NESTED = True
START = True
TUNNEL = False
TEMPLATES = {'': None, 'arch': 'https://linuximages.de/openstack/arch/arch-openstack-LATEST-image-bootstrap.qcow2',
             'atomic': 'https://download.fedoraproject.org/pub/alt/atomic/stable/Fedora-Atomic-26-20170905.0/'
             'CloudImages/x86_64/images/Fedora-Atomic-26-20170905.0.x86_64.qcow2',
             'centos6': 'https://cloud.centos.org/centos/6/images/CentOS-6-x86_64-GenericCloud.qcow2',
             'centos7': 'https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2',
             'centos7atomic': 'http://cloud.centos.org/centos/7/atomic/images/CentOS-Atomic-Host-7-GenericCloud.qcow2',
             'cirros': 'http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img',
             'cloudforms42': 'https://access.redhat.com/downloads/content/167/ver=/cf-me---4.2/4.2/x86_64/'
             'product-software',
             'cloudforms45': 'https://access.redhat.com/downloads/content/167/ver=/cf-me---4.5/4.5/x86_64/'
             'product-software',
             'coreos': 'https://stable.release.core-os.net/amd64-usr/current/coreos_production_qemu_image.img.bz2',
             'debian8': 'https://cdimage.debian.org/cdimage/openstack/current-8/debian-8-openstack-amd64.qcow2',
             'debian9': 'https://cdimage.debian.org/cdimage/openstack/current-9/debian-9-openstack-amd64.qcow2',
             'fedora24': 'https://download.fedoraproject.org/pub/fedora/linux/releases/24/CloudImages/x86_64/images/'
             'Fedora-Cloud-Base-24-1.2.x86_64.qcow2',
             'fedora25': 'https://download.fedoraproject.org/pub/fedora/linux/releases/25/CloudImages/x86_64/images/'
             'Fedora-Cloud-Base-25-1.3.x86_64.qcow2',
             'fedora26': 'https://download.fedoraproject.org/pub/fedora/linux/releases/26/CloudImages/x86_64/images/'
             'Fedora-Cloud-Base-26-1.5.x86_64.qcow2',
             'fedora27': 'https://download.fedoraproject.org/pub/fedora/linux/releases/27/CloudImages/x86_64/images/'
             'Fedora-Cloud-Base-27-1.6.x86_64.qcow2',
             'fedora28': 'https://download.fedoraproject.org/pub/fedora/linux/releases/28/Cloud/x86_64/images/'
             'Fedora-Cloud-Base-28-1.1.x86_64.qcow2',
             'gentoo': 'https://gentoo.osuosl.org/experimental/amd64/openstack/gentoo-openstack-amd64-default-20180621.'
             'qcow2',
             'manageiq57': 'http://releases.manageiq.org/manageiq-openstack-euwe-3.qc2',
             'manageiq58': 'http://releases.manageiq.org/manageiq-openstack-fine-3.qc2',
             'opensuse': 'http://download.opensuse.org/pub/opensuse/repositories/Cloud:/Images:/Leap_42.3/images/'
             'openSUSE-Leap-42.3-OpenStack.x86_64.qcow2',
             'rhel66': 'https://access.redhat.com/downloads/content/69/ver=/rhel---6/6.6/x86_64/product-software',
             'rhel69': 'https://access.redhat.com/downloads/content/69/ver=/rhel---6/6.9/x86_64/product-software',
             'rhel72': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.2/x86_64/product-software',
             'rhel73': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.3/x86_64/product-software',
             'rhel74': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.4/x86_64/product-software',
             'rhel75': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.5/x86_64/product-software',
             'rhel72atomic': 'https://access.redhat.com/downloads/content/271/ver=/rhel---7/7.2.6-1/x86_64/'
             'product-software',
             'rhel73atomic': 'https://access.redhat.com/downloads/content/271/ver=/rhel---7/7.3.6/x86_64/'
             'product-software',
             'rhel74atomic': 'https://access.redhat.com/downloads/content/271/ver=/rhel---7/7.4.5/x86_64/'
             'product-software',
             'ubuntu1404': 'https://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img',
             'ubuntu1604': 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img',
             'ubuntu1610': 'https://cloud-images.ubuntu.com/yakkety/current/yakkety-server-cloudimg-amd64-disk1.img',
             'ubuntu1704': 'https://cloud-images.ubuntu.com/zesty/current/zesty-server-cloudimg-amd64.img',
             'ubuntu1710': 'https://cloud-images.ubuntu.com/artful/current/artful-server-cloudimg-amd64.img'}
TEMPLATESCOMMANDS = {'cloudforms': 'rm -f /etc/cloud/cloud.cfg.d/30_miq_datasources.cfg',
                     'debian8': 'echo datasource_list: [NoCloud, ConfigDrive, Openstack, Ec2] > /etc/cloud/cloud.cfg.d/'
                     '90_dpkg.cfg',
                     'manageiq': 'rm -f /etc/cloud/cloud.cfg.d/30_miq_datasources.cfg'}
REPORT = False
REPORTALL = False
REPORTURL = "http://127.0.0.1:9000"
REPORTDIR = "/tmp/static/reports"
INSECURE = False
KEYS = []
CMDS = []
SCRIPTS = []
FILES = []
DNS = None
DOMAIN = None
ISO = None
GATEWAY = None
NETMASKS = []
SHAREDKEY = False
ENABLEROOT = True
PLANVIEW = False
PRIVATEKEY = False
TAGS = None
RHNREGISTER = False
RHNUSER = None
RHNPASSWORD = None
RHNAK = None
RHNORG = None
FLAVOR = None
