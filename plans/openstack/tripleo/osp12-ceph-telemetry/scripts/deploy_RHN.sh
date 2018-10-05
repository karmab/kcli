#!/usr/bin/env bash
openstack overcloud deploy --templates /usr/share/openstack-tripleo-heat-templates \
    --ntp-server hora.rediris.es \
    -e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml \
    -e /home/stack/templates/environments/network-environment.yaml \
    -e /home/stack/templates/environments/HostnameMap.yaml \
    -e /home/stack/templates/environments/nic-names.yaml \
    -e /home/stack/templates/environments/ips-from-pool-all.yaml \
    -e /home/stack/templates/environments/storage-environment.yaml \
    -e /home/stack/templates/environments/firstboot.yaml \
    -e /home/stack/templates/environments/postconfig.yaml \
    -e /home/stack/templates/environments/timezone.yaml \
    -e /home/stack/templates/environments/fencing.yaml \
    -e /home/stack/templates/environments/parameters_extraconf.yaml \
    -e /home/stack/templates/environments/firewall-rules.yaml \
    -e /home/stack/templates/environments/overcloud_images.yaml \
    -e /home/stack/templates/rhel-registration/environment-rhel-registration.yaml \
    -e /home/stack/templates/rhel-registration/rhel-registration-resource-registry.yaml \
    --control-scale 3 \
    --compute-scale 2 \
    --ceph-storage-scale 3 \
    --control-flavor baremetal \
    --compute-flavor baremetal \
    --ceph-storage-flavor baremetal \
    --libvirt-type qemu 
 #    2>&1 | tee overcloud-$(date +%d%m%Y-%H%M%S).log &
