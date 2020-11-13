# coding=utf-8
UBUNTUS = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety', 'zesty', 'artful', 'bionic', 'cosmic', 'eoan', 'focal']
VERSION = "99.0"
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
VNC = False
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
IMAGES = {'arch': 'https://linuximages.de/openstack/arch/arch-openstack-LATEST-image-bootstrap.qcow2',
          'centos6': 'https://cloud.centos.org/centos/6/images/CentOS-6-x86_64-GenericCloud.qcow2',
          'centos7': 'https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2',
          'centos8': 'https://cloud.centos.org/centos/8/x86_64/images/'
          'CentOS-8-GenericCloud-8.2.2004-20200611.2.x86_64.qcow2',
          'cirros': 'http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img',
          'coreos': 'https://stable.release.core-os.net/amd64-usr/current/coreos_production_qemu_image.img.bz2',
          'debian8': 'https://cdimage.debian.org/cdimage/openstack/archive/8.11.0/'
          'debian-8.11.0-openstack-amd64.qcow2',
          'debian9': 'https://cdimage.debian.org/cdimage/openstack/current-9/debian-9-openstack-amd64.qcow2',
          'debian10': 'https://cdimage.debian.org/cdimage/openstack/current-10/debian-10-openstack-amd64.qcow2',
          'fedora28': 'https://download.fedoraproject.org/pub/fedora/linux/releases/28/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-28-1.1.x86_64.qcow2',
          'fedora29': 'https://download.fedoraproject.org/pub/fedora/linux/releases/29/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-29-1.2.x86_64.qcow2',
          'fedora30': 'https://download.fedoraproject.org/pub/fedora/linux/releases/30/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-30-1.2.x86_64.qcow2',
          'fcos': 'https://builds.coreos.fedoraproject.org/streams/stable.json',
          'fedora31': 'https://download.fedoraproject.org/pub/fedora/linux/releases/31/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-31-1.9.x86_64.qcow2',
          'fedora32': 'https://download.fedoraproject.org/pub/fedora/linux/releases/32/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-32-1.6.x86_64.qcow2',
          'fedora33': 'https://download.fedoraproject.org/pub/fedora/linux/releases/33/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-33-1.2.x86_64.qcow2',
          'freebsd112': 'https://bsd-cloud-image.org/images/freebsd/11.2/freebsd-11.2.qcow2',
          'freebsd121': 'https://bsd-cloud-image.org/images/freebsd/12.1/freebsd-12.1.qcow2',
          'netbsd81': 'https://bsd-cloud-image.org/images/netbsd/8.1/netbsd-8.1.qcow2',
          'netbsd90': 'https://bsd-cloud-image.org/images/netbsd/9.0/netbsd-9.0.qcow2',
          'openbsd66': 'https://bsd-cloud-image.org/images/openbsd/6.6/openbsd-6.6.qcow2',
          'openbsd67': 'https://bsd-cloud-image.org/images/openbsd/6.7/openbsd-6.7.qcow2',
          'gentoo': 'https://gentoo.osuosl.org/experimental/amd64/openstack/gentoo-openstack-amd64-default-20180621.'
          'qcow2',
          'opensuse': 'https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.2/images/'
          'openSUSE-Leap-15.2-OpenStack.x86_64.qcow2',
          'rhcos41': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.1',
          'rhcos42': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.2',
          'rhcos43': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.3',
          'rhcos44': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.4',
          'rhcos45': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.5',
          'rhcos46': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.6',
          'rhcos47': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.7',
          'rhcoslatest': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.7',
          'rhel7': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7',
          'rhel8': 'https://access.redhat.com/downloads/content/479/ver=/rhel---8',
          'ubuntu1804': 'https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img',
          'ubuntu1810': 'https://cloud-images.ubuntu.com/releases/cosmic/release-20190628/'
          'ubuntu-18.10-server-cloudimg-amd64.img',
          'ubuntu1904': 'https://cloud-images.ubuntu.com/releases/disco/release/ubuntu-19.04-server-cloudimg-amd64.img',
          'ubuntu1910': 'https://cloud-images.ubuntu.com/releases/eoan/release/ubuntu-19.10-server-cloudimg-amd64.img',
          'ubuntu2004': 'https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img'}

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
ENABLEROOT = False
PLANVIEW = False
PRIVATEKEY = False
TAGS = []
NETWORKWAIT = 0
RHNREGISTER = False
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
JENKINSMODE = "podman"
WEBSOCKIFYCERT = """-----BEGIN PRIVATE KEY-----
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
ZEROTIER_NETS = []
ZEROTIER_KUBELET = False
METADATA_FIELDS = ['plan', 'image', 'profile', 'owner', 'dnsclient', 'domain', 'kube', 'kubetype', 'loadbalancer']
CLIENTRULES = []
CACHE = False
