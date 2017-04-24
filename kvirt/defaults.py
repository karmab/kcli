NETS = ['default']
POOL = 'default'
TEMPLATE = None
CPUMODEL = 'Westmere'
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
TEMPLATES = {'arch': 'https://linuximages.de/openstack/arch/arch-openstack-LATEST-image-bootstrap.qcow2',
             'centos6': 'https://cloud.centos.org/centos/6/images/CentOS-6-x86_64-GenericCloud.qcow2',
             'centos7': 'https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2',
             'cirros': 'https://download.cirros-cloud.net/0.3.5/cirros-0.3.5-x86_64-disk.img',
             'debian8': 'https://cdimage.debian.org/cdimage/openstack/current-8/debian-8-openstack-amd64.qcow2',
             'fedora24': 'https://download.fedoraproject.org/pub/fedora/linux/releases/24/CloudImages/x86_64/images/Fedora-Cloud-Base-24-1.2.x86_64.qcow2',
             'fedora25': 'https://download.fedoraproject.org/pub/fedora/linux/releases/25/CloudImages/x86_64/images/Fedora-Cloud-Base-25-1.3.x86_64.qcow2',
             'gentoo': 'http://gentoo.osuosl.org/experimental/amd64/openstack/gentoo-openstack-amd64-default-20170122.qcow2',
             'opensuse': 'http://download.opensuse.org/pub/opensuse/repositories/Cloud:/Images:/Leap_42.3/images/openSUSE-Leap-42.3-OpenStack.x86_64.qcow2',
             'rhel72': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.2/x86_64/product-software',
             'rhel73': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.3/x86_64/product-software',
             'ubuntu1404': 'https://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img',
             'ubuntu1604': 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img',
             'ubuntu1610': 'https://cloud-images.ubuntu.com/yakkety/current/yakkety-server-cloudimg-amd64-disk1.img',
             'ubuntu1704': 'https://cloud-images.ubuntu.com/zesty/current/zesty-server-cloudimg-amd64.img'}
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
