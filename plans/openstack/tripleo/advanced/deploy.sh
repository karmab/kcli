#!/usr/bin/env bash
openstack overcloud deploy --templates /usr/share/openstack-tripleo-heat-templates \
    --ntp-server 95.81.173.74 \
    -e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml \
    -e /home/stack/templates/network-environment.yaml \
    -e /home/stack/templates/HostnameMap.yaml \
    -e /home/stack/templates/ips-from-pool-all.yaml \
    -e /home/stack/templates/environments/password.yaml \
    -e /home/stack/templates/environments/postconfig.yaml \
    --control-scale 3 \
    --compute-scale 1 \
    --control-flavor control \
    --compute-flavor compute \
    --neutron-tunnel-types vxlan \
    --neutron-network-type vxlan \
    --libvirt-type qemu
