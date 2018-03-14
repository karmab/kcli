openstack overcloud deploy --templates /usr/share/openstack-tripleo-heat-templates \
    --ntp-server hora.rediris.es \
    --answers-file /home/stack/templates/environments/deployment-answer-file.yaml \
    -r /home/stack/templates/environments/roles_data.yaml \
    --libvirt-type qemu 
 #    2>&1 | tee overcloud-$(date +%d%m%Y-%H%M%S).log &
