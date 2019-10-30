# coding=utf-8
NETS = ['default']
POOL = 'default'
IMAGE = None
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
AUTOSTART = False
TUNNEL = False
IMAGES = {'arch': 'https://linuximages.de/openstack/arch/arch-openstack-LATEST-image-bootstrap.qcow2',
          'atomic': 'https://download.fedoraproject.org/pub/alt/atomic/stable/Fedora-Atomic-26-20170905.0/'
          'CloudImages/x86_64/images/Fedora-Atomic-26-20170905.0.x86_64.qcow2',
          'centos6': 'https://cloud.centos.org/centos/6/images/CentOS-6-x86_64-GenericCloud.qcow2',
          'centos7': 'https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2',
          'centos7atomic': 'http://cloud.centos.org/centos/7/atomic/images/CentOS-Atomic-Host-GenericCloud.qcow2',
          'cirros': 'http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img',
          'coreos': 'https://stable.release.core-os.net/amd64-usr/current/coreos_production_qemu_image.img.bz2',
          'debian8': 'https://cdimage.debian.org/cdimage/openstack/archive/8.11.0/'
          'debian-8.11.0-openstack-amd64.qcow2',
          'debian9': 'https://cdimage.debian.org/cdimage/openstack/current-9/debian-9-openstack-amd64.qcow2',
          'debian10': 'https://cdimage.debian.org/cdimage/openstack/current-10/debian-10-openstack-amd64.qcow2',
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
          'fedora29': 'https://download.fedoraproject.org/pub/fedora/linux/releases/29/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-29-1.2.x86_64.qcow2',
          'fedora30': 'https://download.fedoraproject.org/pub/fedora/linux/releases/30/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-30-1.2.x86_64.qcow2',
          'fedoracoreos30': 'https://builds.coreos.fedoraproject.org/prod/streams/testing/builds/30.20190716.1/'
          'x86_64/fedora-coreos-30.20190716.1-qemu.qcow2.xz',
          'fedora31': 'https://download.fedoraproject.org/pub/fedora/linux/releases/31/Cloud/x86_64/images/'
          'Fedora-Cloud-Base-31-1.9.x86_64.qcow2',
          'gentoo': 'https://gentoo.osuosl.org/experimental/amd64/openstack/gentoo-openstack-amd64-default-20180621.'
          'qcow2',
          'opensuse': 'http://download.opensuse.org/pub/opensuse/repositories/Cloud:/Images:/Leap_42.3/images/'
          'openSUSE-Leap-42.3-OpenStack.x86_64.qcow2',
          'rhcosootpa': 'https://releases-rhcos.svc.ci.openshift.org/storage/releases/ootpa/420.8.20190611.0/'
          'rhcos-420.8.20190611.0-qemu.qcow2',
          'rhcoslatest': 'https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/rhcos-4.2',
          'rhel72': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.2/x86_64/product-software',
          'rhel73': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.3/x86_64/product-software',
          'rhel74': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.4/x86_64/product-software',
          'rhel75': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.5/x86_64/product-software',
          'rhel76': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.6/x86_64/product-software',
          'rhel77': 'https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.7/x86_64/product-software',
          'rhel80': 'https://access.redhat.com/downloads/content/479/ver=/rhel---8/8.0/x86_64/product-software',
          'ubuntu1404': 'https://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img',
          'ubuntu1604': 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img',
          'ubuntu1610': 'http://cloud-images-archive.ubuntu.com/releases/yakkety/release-20170719/'
          'ubuntu-16.10-server-cloudimg-amd64.img',
          'ubuntu1704': 'http://cloud-images-archive.ubuntu.com/releases/zesty/release-20171208/'
          'ubuntu-17.04-server-cloudimg-amd64.img',
          'ubuntu1710': 'http://cloud-images-archive.ubuntu.com/releases/artful/release-20180706/'
          'ubuntu-17.10-server-cloudimg-amd64.img',
          'ubuntu1804': 'https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img',
          'ubuntu1810': 'https://cloud-images.ubuntu.com/releases/cosmic/release-20190628/'
          'ubuntu-18.10-server-cloudimg-amd64.img',
          'ubuntu1904': 'https://cloud-images.ubuntu.com/releases/disco/release/'
          'ubuntu-19.04-server-cloudimg-amd64.img'}
IMAGESCOMMANDS = {'cloudforms': 'rm -f /etc/cloud/cloud.cfg.d/30_miq_datasources.cfg',
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
TAGS = []
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
NOTIFYTOKEN = None
NOTIFYCMD = "cat /var/log/cloud-init.log"
SHAREDFOLDERS = []
KERNEL = None
INITRD = None
CMDLINE = None
PLACEMENT = []
YAMLINVENTORY = False
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
