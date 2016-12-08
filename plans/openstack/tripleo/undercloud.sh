yum clean all
openstack undercloud install
mkdir images
mkdir -p templates/environments
cd templates/environments
wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/environments/password.yaml
wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/environments/_password.yaml
cd ~/images
for i in /usr/share/rhosp-director-images/overcloud-full-latest-9.0.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-9.0.tar; do tar -xvf $i; done
source ~/stackrc
openstack overcloud image upload --image-path /home/stack/images
neutron subnet-update `neutron subnet-list -c id -f value` --dns-nameserver 8.8.8.8
ssh-keyscan -H 192.168.101.1 >> ~/.ssh/known_hosts
sh instackenv.sh
#tr '\n' '@' < .ssh/id_rsa  > prout
#sed -i "s/@/\\\\n/g" prout
openstack baremetal import --json ~/instackenv.json
sleep 3
openstack baremetal configure boot
openstack baremetal introspection bulk start
sh assignprofiles.sh
#openstack overcloud deploy --templates

# ISSUES FOUND
# you will need http://mirror.centos.org/centos/7/cloud/x86_64/openstack-mitaka/common/ipxe-roms-qemu-20160127-1.git6366fa7a.el7.noarch.rpm if using a centos hypervisor

