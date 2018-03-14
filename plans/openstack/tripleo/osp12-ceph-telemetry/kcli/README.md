### Notes ###
This deploys 1 undercloud node + 10 overcloud nodes. 3 controllers, 2 computes, 3 ceph nodes, 2 telemetry nodes.

The undercloud installs vbmc so you can use ipmilan with ironic, and also test configure instance-ha on the overcloud.

The templates configure the overcloud using OVN, ceph with ceph-ansible, custom roles(using the telemetry role).

1. Cloud-init runs the undercloud_pre.sh script that prepairs the undercloud node and runs the undercloud instalation: su - stack -c "openstack undercloud install"
2. You can use the undercloud.sh script that is located in /home/stack and configures the undercloud as a docker registry and downloads all the needed openstack docker images
3. Creates and env file so the overcloud nodes can use the docker imates.
4. Run the deploy.sh script in /home/stack/templates/scripts to deploy the overcloud
