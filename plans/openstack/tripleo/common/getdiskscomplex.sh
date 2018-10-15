#!/bin/bash

mkdir swift-data
cd swift-data
#export SWIFT_PASSWORD=`sudo openstack-config --get /etc/ironic-inspector/inspector.conf swift password`
export SWIFT_PASSWORD=`sudo grep '^password =' /etc/ironic-inspector/inspector.conf | tail -1 | awk -F'= ' '{print $2}'`
for node in $(ironic node-list | tail -4 | grep -v UUID| awk '{print $2}'); do swift -U service:ironic -K ${SWIFT_PASSWORD} download ironic-inspector inspector_data-${node}; done

for node in $(ironic node-list | tail -4 | grep -v UUID| awk '{print $2}'); do echo "NODE: $node" ; cat inspector_data-${node} | jq '.inventory.disks' ; echo "-----" ; done
