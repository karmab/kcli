yum install -y centos-release-openstack-[[ version ]]
#sed -i 's/$contentdir/centos/' /etc/yum.repos.d/CentOS-QEMU-EV.repo
echo centos >/etc/yum/vars/contentdir
