# coding=utf-8
UBUNTUS = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety', 'zesty', 'artful', 'bionic', 'cosmic', 'eoan', 'focal',
           'groovy', 'hirsute', 'impish', 'jammy', 'kinetic']
VERSION = '99.0'
NETS = ['default']
POOL = 'default'
IMAGE = None
CPUMODEL = 'host-model'
NUMCPUS = 2
CPUHOTPLUG = False
CPUFLAGS = []
MEMORY = 512
MEMORYHOTPLUG = False
DISKINTERFACE = 'virtio'
DISKTHIN = True
DISKSIZE = 10
DISKS = [{'size': DISKSIZE, 'default': True}]
GUESTID = 'guestrhel764'
VNC = True
CLOUDINIT = True
RESERVEIP = False
RESERVEDNS = False
RESERVEHOST = False
NESTED = True
START = True
AUTOSTART = False
TUNNEL = False
TUNNELHOST = None
TUNNELUSER = 'root'
TUNNELDIR = '/var/www/html'
TUNNELPORT = 22
VMUSER = None
VMPORT = None
OPENSHIFT_TAG = '4.14'
ALMA = 'http://repo.ifca.es/almalinux'
BSD = 'https://object-storage.public.mtl1.vexxhost.net/swift/v1/1dbafeefbd4f4c80864414a441e72dd2'
BSD += '/bsd-cloud-image.org/images/dragonflybsd'
CENTOS = 'https://cloud.centos.org/centos'
DEBIAN = 'https://cdimage.debian.org/cdimage'
FEDORA = 'http://mirror.uv.es/mirror/fedora/linux/releases'
GENTOO = 'https://gentoo.osuosl.org/experimental/amd64/openstack'
SUSE = 'https://download.opensuse.org'
RHCOS = 'https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos'
ROCKY = 'https://dl.rockylinux.org/pub/rocky/'
UBUNTU = 'https://cloud-images.ubuntu.com/releases'
IMAGES = {'almalinux8': f'{ALMA}/8.8/cloud/x86_64/images/AlmaLinux-8-GenericCloud-latest.x86_64.qcow2',
          'almalinux9': f'{ALMA}/9.1/cloud/x86_64/images/AlmaLinux-9-GenericCloud-latest.x86_64.qcow2',
          'arch': 'https://linuximages.de/openstack/arch/arch-openstack-LATEST-image-bootstrap.qcow2',
          'centos7': f'{CENTOS}/7/images/CentOS-7-x86_64-GenericCloud.qcow2',
          'centos8stream': f'{CENTOS}/8-stream/x86_64/images/CentOS-Stream-GenericCloud-8-latest.x86_64.qcow2',
          'centos9stream': f'{CENTOS}/9-stream/x86_64/images/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2',
          'cirros': 'http://download.cirros-cloud.net/0.5.2/cirros-0.5.2-x86_64-disk.img',
          'debian10': f'{DEBIAN}/openstack/current-10/debian-10-openstack-amd64.qcow2',
          'debian11': f'{DEBIAN}/cloud/bullseye/latest/debian-11-generic-amd64.qcow2',
          'debian12': f'{DEBIAN}/cloud/bookworm/latest/debian-12-generic-amd64.qcow2',
          'fcos': 'https://builds.coreos.fedoraproject.org/streams/stable.json',
          'fedora37': f'{FEDORA}/37/Cloud/x86_64/images/Fedora-Cloud-Base-37-1.7.x86_64.qcow2',
          'fedora38': f'{FEDORA}/38/Cloud/x86_64/images/Fedora-Cloud-Base-38-1.6.x86_64.qcow2',
          'fedora39': f'{FEDORA}/39/Cloud/x86_64/images/Fedora-Cloud-Base-39-1.5.x86_64.qcow2',
          'fedoralatest': 'https://alt.fedoraproject.org/cloud',
          'freebsd122': f'{BSD}/freebsd/12.2/freebsd-12.2.qcow2',
          'freebsd130': f'{BSD}/freebsd/13.0/freebsd-13.0-zfs.qcow2',
          'netbsd82': f'{BSD}/netbsd/8.2/netbsd-8.2.qcow2',
          'netbsd92': f'{BSD}/netbsd/9.2/2021-12-11/netbsd-9.2.qcow2',
          'openbsd71': f'{BSD}/openbsd/7.1/2022-06-27/ufs/openbsd-7.1-2022-06-27.qcow2',
          'openbsd72': f'{BSD}/openbsd/7.2/2022-11-06/ufs/openbsd-7.2-2022-11-06.qcow2',
          'dragonflybsd601': f'{BSD}/dragonflybsd/6.0.1/2021-12-11/dragonflybsd-6.0.1-hammer2.qcow2',
          'dragonflybsd622': f'{BSD}/dragonflybsd/6.2.2/2022-09-06/hammer2/dragonflybsd-6.2.2-hammer2-2022-09-06.qcow2',
          'gentoo': f'{GENTOO}/gentoo-openstack-amd64-default-latest.qcow2',
          'opensuse155': f'{SUSE}/repositories/Cloud:/Images:/Leap_15.5/images/openSUSE-Leap-15.5.x86_64-NoCloud.qcow2',
          'rhcos410': f'{RHCOS}/4.10',
          'rhcos411': f'{RHCOS}/4.11',
          'rhcos412': f'{RHCOS}/4.12',
          'rhcos413': f'{RHCOS}/4.13',
          'rhcos414': f'{RHCOS}/4.14',
          'rhcos415': f'{RHCOS}/4.15',
          'rhcoslatest': f'{RHCOS}/4.15',
          'rhel7': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7',
          'rhel8': 'https://access.redhat.com/downloads/content/479/ver=/rhel---8',
          'rhel9': 'https://access.redhat.com/downloads/content/479/ver=/rhel---9',
          'ubuntu1804': f'{UBUNTU}/18.04/release/ubuntu-18.04-server-cloudimg-amd64.img',
          'ubuntu2004': f'{UBUNTU}/20.04/release/ubuntu-20.04-server-cloudimg-amd64.img',
          'ubuntu2204': f'{UBUNTU}/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img',
          'ubuntu2304': f'{UBUNTU}/23.04/release/ubuntu-23.04-server-cloudimg-amd64.img',
          'ubuntu2310': f'{UBUNTU}/23.10/release/ubuntu-23.10-server-cloudimg-amd64.img',
          'rockylinux8': f'{ROCKY}/8/images/Rocky-8-GenericCloud.latest.x86_64.qcow2',
          'rockylinux9': f'{ROCKY}/9/images/x86_64/Rocky-9-GenericCloud.latest.x86_64.qcow2'}

IMAGESCOMMANDS = {'debian8': 'echo datasource_list: [NoCloud, ConfigDrive, Openstack, Ec2] > /etc/cloud/cloud.cfg.d/'
                  '90_dpkg.cfg'}
INSECURE = True
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
TEMPKEY = False
TAGS = []
NETWORKWAIT = 0
RHNREGISTER = True
RHNUNREGISTER = False
RHNSERVER = 'https://subscription.rhsm.redhat.com'
RHNUSER = None
RHNPASSWORD = None
RHNAK = None
RHNORG = None
RHNPOOL = None
FLAVOR = None
KEEP_NETWORKS = False
DNSCLIENT = None
STORE_METADATA = False
NOTIFY = False
PUSHBULLETTOKEN = None
SLACKTOKEN = None
MAILSERVER = None
MAILFROM = None
MAILTO = []
NOTIFYCMD = None
NOTIFYSCRIPT = None
SLACKCHANNEL = None
NOTIFYMETHODS = ['pushbullet']
SHAREDFOLDERS = []
KERNEL = None
INITRD = None
CMDLINE = None
PLACEMENT = []
YAMLINVENTORY = False
CPUPINNING = []
NUMAMODE = None
NUMA = []
PCIDEVICES = []
TPM = False
RNG = False
JENKINSMODE = 'podman'
FAKECERT = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC5gvbJA3nzoIEF
5R+G3Vy1XwzKoGX7uoRPstBSgEQ967n7Y3WC3JT0r7Uq8Wyudm/8sEhK6PNFkarV
zsRZrszUF/qvLzIAg8wc7c2q3jlD1nYG8U6ngnSgcJxJdGKdYDraXwCPAbNjRd+8
KimOxGolOb57iWoZTwprNJ0B9gmfIo2i+f/rLlBJtOtITPypkt0GyRQaTD3zMEMd
azJcy3wCj1RfZ97oG9C2h6rcA0P+NEUqwwnKL/dIaJl+SJRp9GXrrVhIx+rN+lnN
dT6BzLEBGZ2IXG0Y6YxRDdMGMgVl2m78uMi0wxnOkAu7vg6jppqInNLakOexR0R4
qp7W+OCnAgMBAAECggEAKc5CsSAQbn/AM8Tjqu/dwZ3O8ybcdLMeuBsy6TSwrEeg
HO/X/oqZIt8p86h+dn6IVCih0gfXMtlV52L2SsOiszVIMAxxtz38VJSeoZ/8xbXh
2USuFf/HKpTWE5Of2ZljCe0Y4iFe/MM1XWEfBmZrCUKPE6Xu/A8c6PXtYBDDMFIl
puX8CtUDyvY3+mcprFM2z7bDLlwxAdBgfKAR84F3RazRB3KlgaqCR+KVrhVnFkBZ
ApWnkwGjxj8NrKj9JArGLwiTKeQg7w1jJGdPQwCDi14XZYFHsPEllQ3hBIJzOmAS
vHkr6DdyT6L25UY6mYfjyJy2ZIqvUObCTkTgJJ4pyQKBgQDpb3qiPpEpHipod2w+
vLmcGGnYX8K1ikplvUT1bPeRXZyzWEC3CHpK+8lktVNU3MRklyNaQJIR6P5iyP/c
C46IyPHszYnHFHGwx+hG2Ibqd1RcfjOTz04Y4WxJB5APTB24aWTy09T5k48X+iu9
Ifeqxd9cdmKiLf6CDRxvUE4r1QKBgQDLcZNRY08fpc/mAV/4H3toOkiCwng10KZ0
BZs2aM8i6CGbs7KAWy9Cm18sDW5Ffhy9oh7XnmVkaaULmrwdCrIGFLsR282c4izx
3HHhfHOl6xri2xq8XwjMruzjELiIw2A8iZZssQxzV/sRHXjf9VMdcYGXlK3HrZOw
ZIg7qxjEiwKBgQDEtIzZVPHLfUDtIN0VDME3eRcQHrmbcrn4e4I1cao4U3Ltacu2
sK0krIFrnKRo2VOhE/7VWZ38+6IJKij4isCEIRhDnHuiR2b6OapQsLsXrpBnFG1v
+3tq2eH+tCG/0jslH6LSQJCx8pbc9JGQ4aOqwuzSJGw/D5TskBHK9xe4NQKBgQCQ
FYUffDUaleWS4WBlq25MWBLowPBANODehOXzd/FTqJG841zFeU8UXlPeMDjr8LBM
QdiUHvNyVTv15wXZj6ybj+0ZbdHGjY0FUno5F1oUpVjqWAEsbiYeSLku67W17qFm
3o7xtca6nhILghMMkoPl83CzuTIGnFFf+SNfFwM4lwKBgFs5cPPw51YYwYDhhCqE
EewsK2jgc1ZqIbrGA5CbtfMIc5rhTuuJ9aWfpfF/kgUp9ruVklMrEcdTtUWn/EDA
erBsSfYdgXubBAajSxm3wFHk6bgGvKGT48++DnJWL+SFbmNhh5x9xRtMHR17K1nq
KpxLjDMW1gGkb22ggyP5MnJz
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDIDCCAggCCQC/KT3ImT8lHTANBgkqhkiG9w0BAQsFADBSMQswCQYDVQQGEwJF
UzEPMA0GA1UECAwGTWFkcmlkMQ8wDQYDVQQHDAZNYWRyaWQxEjAQBgNVBAoMCUth
cm1hbGFiczENMAsGA1UEAwwEa2NsaTAeFw0xOTA5MzAxMzM2MTBaFw0yOTA5Mjcx
MzM2MTBaMFIxCzAJBgNVBAYTAkVTMQ8wDQYDVQQIDAZNYWRyaWQxDzANBgNVBAcM
Bk1hZHJpZDESMBAGA1UECgwJS2FybWFsYWJzMQ0wCwYDVQQDDARrY2xpMIIBIjAN
BgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuYL2yQN586CBBeUfht1ctV8MyqBl
+7qET7LQUoBEPeu5+2N1gtyU9K+1KvFsrnZv/LBISujzRZGq1c7EWa7M1Bf6ry8y
AIPMHO3Nqt45Q9Z2BvFOp4J0oHCcSXRinWA62l8AjwGzY0XfvCopjsRqJTm+e4lq
GU8KazSdAfYJnyKNovn/6y5QSbTrSEz8qZLdBskUGkw98zBDHWsyXMt8Ao9UX2fe
6BvQtoeq3AND/jRFKsMJyi/3SGiZfkiUafRl661YSMfqzfpZzXU+gcyxARmdiFxt
GOmMUQ3TBjIFZdpu/LjItMMZzpALu74Oo6aaiJzS2pDnsUdEeKqe1vjgpwIDAQAB
MA0GCSqGSIb3DQEBCwUAA4IBAQAs7eRc4sJ2qYPY/M8+Lb2lMh+qo6FAi34kJYbv
xhnq61/dnBCPmk8JzOwBoPVREDBGmXktOwZb88t8agT/k+OKCCh8OOVa5+FafJ5j
kShh+IkztEZr+rE6gnxdcvSzUhbfet97nPo/n5ZqtoqdSm7ajnI2iiTI+AXOJAeN
0Y29Dubv9f0Vg4c0H1+qZl0uzLk3mooxyRD4qkhgtQJ8kElRCIjmceBkk+wKOnt/
oEO8BRcXIiXiQqW9KnF99fXOiQ/cKYh3kWBBPnuEOhC77Ke5aMlqMNOPULf3PMix
2bqeJlbpLt7PkZBSawXeu6sAhRsqlpEmiPGn8ujH/oKwIAgm
-----END CERTIFICATE-----"""
VIRTTYPE = None
METADATA_FIELDS = ['dnsclient', 'domain', 'image', 'kube', 'kubetype', 'loadbalancer', 'owner', 'plan', 'profile',
                   'user', 'redfish_iso']
VMRULES = []
VMRULES_STRICT = False
SECURITYGROUPS = []
LOCAL_OPENSHIFT_APPS = ['argocd', 'istio', 'users', 'autolabeller', 'nfs']
SSH_PUB_LOCATIONS = ['id_ed25519.pub', 'id_ecdsa.pub', 'id_dsa.pub', 'id_rsa.pub']
ROOTPASSWORD = None
WAIT = False
WAIT = False
WAITTIMEOUT = 0
WAITCOMMAND = None
BMC_USER = None
BMC_PASSWORD = None
BMC_MODEL = None

KSUSHYSERVICE = """[Unit]
Description=Ksushy emulator service
After=syslog.target
[Service]
Type=simple
ExecStart=/usr/bin/ksushy
StandardOutput=syslog
StandardError=syslog
Environment=HOME={home}
Environment=PYTHONUNBUFFERED=true
{port}{ipv6}{ssl}{user}{password}{bootonce}
[Install]
WantedBy=multi-user.target"""

WEBSERVICE = """[Unit]
Description=Kweb service
After=syslog.target
[Service]
Type=simple
ExecStart=/usr/bin/kweb
StandardOutput=syslog
StandardError=syslog
Environment=HOME={home}
Environment=PYTHONUNBUFFERED=true
{port}{ipv6}
[Install]
WantedBy=multi-user.target"""

PLANTYPES = ['ansible', 'bucket', 'cluster', 'container', 'disk', 'dns', 'image', 'kube', 'loadbalancer', 'network',
             'plan', 'pool', 'profile', 'securitygroup', 'vm', 'workflow']

AZURE = {'admin_user': 'superadmin', 'location': 'westus', 'resource_group': 'kcli'}

AWS = {'region': 'eu-west-3'}

IBM = {'region': 'eu-gb'}

GCP = {'region': 'europe-west1'}

KUBEVIRT = {'readwritemany': False, 'disk_hotplug': False, 'access_mode': 'NodePort',
            'volume_mode': 'Filesystem', 'volume_access': 'ReadWriteOnce', 'harvester': False, 'embed_userdata': False,
            'first_consumer': False}

OPENSTACK = {'version': '2', 'domain': 'Default', 'user': 'admin', 'project': 'admin'}

OVIRT = {'datacenter': 'Default', 'cluster': 'Default', 'user': 'admin@internal', 'filtervms': False,
         'filteruser': False}

VSPHERE = {'force_pool': False, 'dvs': True, 'restricted': False, 'import_network': 'VM Network',
           'filtervms': False, 'filteruser': False, 'category': 'kcli', 'timeout': 2700}
