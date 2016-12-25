
# important to have the provisioning network without nat
# also on the hypervisor 
echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/default/rp_filter
# openstack undercloud install cant be launched from cloudinit , as a tty is required (for sudo). investigate whether disabling requiretty is enough
# you will need http://mirror.centos.org/centos/7/cloud/x86_64/openstack-mitaka/common/ipxe-roms-qemu-20160127-1.git6366fa7a.el7.noarch.rpm if using a centos hypervisor
# need to launch openstack undercloud install twice as default gateway disappears. should investigate whehther ifcfg-eth1  file misses something ( BOOTPROTO set to static ? )
