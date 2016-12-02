openstack undercloud install
mkdir images
mkdir templates
cd images
for i in /usr/share/rhosp-director-images/overcloud-full-latest-9.0.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-9.0.tar; do tar -xvf $i; done
openstack overcloud image upload --image-path /home/stack/images
neutron subnet-update `neutron subnet-list -c id -f value` --dns-nameserver 8.8.8.8
ssh-keyscan -H 192.168.101.1 >> ~/.ssh/known_hosts
tr '\n' '@' < .ssh/id_rsa  > prout
sed -i "s/@/\\\\n/g" prout
# edit damn instackenv.json to put the correct key
openstack baremetal import --json ~/instackenv.json
openstack baremetal configure boot

