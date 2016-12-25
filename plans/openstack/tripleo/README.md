
# openstack undercloud install cant be launched from cloudinit , as a tty is required (for sudo). investigate whether disabling requiretty is enough
# you will need http://mirror.centos.org/centos/7/cloud/x86_64/openstack-mitaka/common/ipxe-roms-qemu-20160127-1.git6366fa7a.el7.noarch.rpm if using a centos hypervisor
# need to launch openstack undercloud install twice as default gateway disappears. should investigate whehther ifcfg-eth1  file misses something ( BOOTPROTO set to static ? )
# i add to add an extra iptables rule cos the default one  didnt work
-A PREROUTING -d 169.254.169.254/32 -i br-ctlplane -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 8775
instead i used
iptables -t nat -A PREROUTING -d 169.254.169.254/32 -s 10.0.0.0/24 -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 8775
