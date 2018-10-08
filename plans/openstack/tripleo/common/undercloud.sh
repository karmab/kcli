VERSION="10"

ssh-keyscan -H 192.168.101.1 >> ~/.ssh/known_hosts
ssh-keygen -N '' -t rsa -f ~/.ssh/id_rsa_libvirt
ssh-copy-id -i ~/.ssh/id_rsa_libvirt.pub root@192.168.101.1
echo -e "Host 192.168.101.1\n     IdentityFile ~/.ssh/id_rsa_libvirt\n" > ~/.ssh/config
chmod 0600 ~/.ssh/config

##yum -y install openvswitch
##wget -P /root http://cbs.centos.org/kojifiles/packages/openvswitch/2.5.0/22.git20160727.el7/x86_64/openvswitch-2.5.0-22.git20160727.el7.x86_64.rpm
##yum -y localinstall /root/openvswitch-2.5.0-22.git20160727.el7.x86_64.rpm
#openstack undercloud install
##mv /root/openvswitch-2.5.0-22.git20160727.el7.x86_64.rpm /var/www/html/o.rpm
##restorecon -Frv /var/www/html
mkdir images
tar zxvf templates.tar.gz
cd ~/images
for i in /usr/share/rhosp-director-images/overcloud-full-latest-${VERSION}.0.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-${VERSION}.0.tar; do tar -xvf ${i}; done

source ~/stackrc
openstack overcloud image upload --image-path /home/stack/images
neutron subnet-update `neutron subnet-list -c id -f value` --dns-nameserver 8.8.8.8

cd ~/
sh instackenv.sh
openstack baremetal import --json ~/instackenv.json
sleep 3
openstack baremetal configure boot
openstack baremetal introspection bulk start
sh assignprofiles.sh
sh deploy.sh
