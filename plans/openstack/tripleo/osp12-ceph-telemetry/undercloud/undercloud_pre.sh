set -x
sysctl -w net.ipv4.ip_forward=1
sysctl -p /etc/sysctl.conf
useradd stack
echo stack | passwd --stdin stack
echo "stack ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/stack
chmod 0440 /etc/sudoers.d/stack
yum install -y  vim tmux screen wget mlocate facter python-tripleoclient libvirt libguestfs-tools openstack-utils sshpass ntpdate telnet
yum -y install rhosp-director-images rhosp-director-images-ipa ceph-ansible python-virtualbmc
ntpdate hora.rediris.es
systemctl stop NetworkManager
systemctl disable NetworkManager
systemctl restart network
yum -y -q update
sed -i /requiretty/d /etc/sudoers
unalias cp
cp -fR /root/stack/templates.tar.gz /home/stack/
cd /home/stack/
tar -zxvf  /home/stack/templates.tar.gz
chown -R stack:stack /home/stack/osp12-ceph-telemetry
mv /home/stack/osp12-ceph-telemetry /home/stack/templates
cp -fp /home/stack/templates/undercloud/undercloud.conf /home/stack/templates/undercloud/undercloud.sh /home/stack/templates/undercloud/instackenv.sh /home/stack/templates/undercloud/hieradata-override.yaml /home/stack/
#Install undercloud
su - stack -c "openstack undercloud install"
