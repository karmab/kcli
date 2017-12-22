openstack overcloud deploy --templates /usr/share/openstack-tripleo-heat-templates \
    --ntp-server 95.81.173.74 \
    -e /home/stack/templates/environments/password.yaml \
    --control-scale 1 \
    --compute-scale 1 \
    --control-flavor control \
    --compute-flavor compute \
    --neutron-tunnel-types vxlan \
    --neutron-network-type vxlan \
    --libvirt-type qemu
   
