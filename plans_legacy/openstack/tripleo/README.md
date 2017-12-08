
those deployment files creates an undercloud and nodes for the overcloud, either 2 for the tripleo.yml and 4 for the tripleoadvanced.yml

a undercloud_pre.sh is passed to the undercloud machine to prepare it, installing packages, creating users and updating the system and finally rebooting ( this is necessary as a recent kernel is needed for undercloud install to work )

from there, one can use the undercloud.sh script as a reference for the step, making use of the provided helper scripts
also note that there s an "advanced" directory with a specific assignprofile.sh and deploy.sh

note we explicitly dont want to used nested cos it s causing some issues on :

- the undercloud, when trying to customize overcloud images
- the overcloud, when launching vms. Note that deploy.sh script sets the libvirt type to qemu ( though you wouldnt use this line on real production)

 important to have the provisioning network without nat
also on the hypervisor 

```
echo net.ipv4.conf.all.rp_filter=0 >> /etc/sysctl.d/99-sysctl.conf
echo net.ipv4.conf.default.rp_filter=0 >> /etc/sysctl.d/99-sysctl.conf
sysctl -p /etc/sysctl.conf
```

you can check it with 

`cat /proc/sys/net/ipv4/conf/all/rp_filter`
`cat /proc/sys/net/ipv4/conf/default/rp_filter`

openstack undercloud install cant be launched from cloudinit , as a tty is required (for sudo).

Investigate whether disabling requiretty is enough

IMPORTANT: you will need http://mirror.centos.org/centos/7/cloud/x86_64/openstack-mitaka/common/ipxe-roms-qemu-20160127-1.git6366fa7a.el7.noarch.rpm if using a centos hypervisor
