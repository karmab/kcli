VERSION="12"
#Stack user configure ssh 
cat > ~/.ssh/config <<EOF
Host *
User root
StrictHostkeyChecking no
UserKnownHostsFile /dev/null
EOF
chmod 600 ~/.ssh/config
#configure vbmc
ssh-keyscan -H 10.10.11.1 >> ~/.ssh/known_hosts
#ssh-keygen -N '' -t rsa -f /home/stack/.ssh/id_rsa
ssh-copy-id -i ~/.ssh/id_rsa.pub root@10.10.11.1
PORT=31 ; for i in ctrl01 ctrl02 ctrl03 c01 c02 ceph01 ceph02 ceph03 telemetry01 telemetry02 ; do vbmc add ${i} --port 62${PORT} --username admin --password unix1234 --libvirt-uri qemu+ssh://root@10.10.11.1/system; ((PORT++)); done
for i in ctrl01 ctrl02 ctrl03 c01 c02 ceph01 ceph02 ceph03 telemetry01 telemetry02 ; do vbmc start ${i} ; done
sudo iptables -I INPUT -p udp --match multiport  --dport 6231:6244 -j ACCEPT
#permanent rules

#configure overcloud images
mkdir ~/images
cd ~/images
for i in /usr/share/rhosp-director-images/overcloud-full-latest-${VERSION}.0.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-${VERSION}.0.tar; do tar -xvf ${i}; done
virt-customize -a /home/stack/images/overcloud-full.qcow2 --root-password password:redhat

#upload overcloud images
source ~/stackrc
openstack overcloud image upload --image-path /home/stack/images
neutron subnet-update `neutron subnet-list -c id -f value` --dns-nameserver 8.8.8.8

#import baremetal nodes
cd ~/
sh instackenv.sh
openstack baremetal instackenv validate
openstack baremetal import --json ~/instackenv.json
openstack overcloud node import instackenv.json

#configure root disk
for type in ctrl c0 ceph telemetry; do
for node in $(openstack baremetal node list  -f value -c Name | grep ${type})
  do
   ironic node-update ${node} add properties/root_device='{"name": "/dev/vda"}'
  done
done

#Introspection
sleep 9
openstack baremetal configure boot
openstack baremetal introspection bulk start

#configure overcloud profiles
for type in controller compute ceph telemetry ; do
if [ ${type} = controller ] ; then name=ctrl ; fi
if [ ${type} = compute ] ; then name=c0 ; fi
if [ ${type} = ceph ] ; then name=ceph ; fi
if [ ${type} = telemetry ] ; then name=telemetry ; fi
counter=0
	for node in $(openstack baremetal node list  -f value -c Name | grep ${name})
	do
    		ironic node-update ${node} add properties/capabilities="node:${type}-${counter},boot_option:local"
                counter=$(( counter +1))
        done
done

#Download docker images to local registry

VERSIONTAG=$(sudo openstack overcloud container image tag discover --image registry.access.redhat.com/rhosp12/openstack-base:latest --tag-from-label version-release)
ENV=$( for i in $(grep "-" /home/stack/templates/environments/deployment-answer-file.yaml | awk '{ print $NF }' | grep -v share) ; do echo "--environment-file $i" ; done)
openstack overcloud container image prepare \
  --namespace=registry.access.redhat.com/rhosp12  \
  --set ceph_namespace=registry.access.redhat.com/rhceph \
  --set ceph_image=rhceph-2-rhel7 \
  --set ceph_tag=latest \
  --prefix=openstack- \
  --tag=${VERSIONTAG} \
  --output-images-file=/home/stack/templates/local_registry_images.yaml \
  -e /usr/share/openstack-tripleo-heat-templates/environments/ceph-ansible/ceph-ansible.yaml \
  ${ENV}

sudo openstack overcloud container image upload \
  --config-file  /home/stack/templates/local_registry_images.yaml \
  --verbose


#Create the env file to use with the deploy command
openstack overcloud container image prepare \
  --namespace=$(docker images | grep -v redhat.com | grep -o '^.*rhosp12' | sort -u) \
  --set ceph_namespace=$(docker images | grep -v redhat.com | grep rhceph | awk ' { print $1}' | cut -d "/" -f 1,2) \
  --set ceph_image=rhceph-2-rhel7 \
  --set ceph_tag=latest \
  --prefix=openstack- \
  --tag=${VERSIONTAG} \
  --env-file=/home/stack/templates/environments/overcloud_images.yaml \
  -e /usr/share/openstack-tripleo-heat-templates/environments/ceph-ansible/ceph-ansible.yaml \
  ${ENV}

echo "  - /home/stack/templates/environments/overcloud_images.yaml" >> /home/stack/templates/environments/deployment-answer-file.yaml
