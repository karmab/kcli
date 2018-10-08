#!/bin/bash

uuids=`ironic node-list | grep -v UUID | awk -F'|' '{ print $2}' | xargs`
counter=0
for uuid in ${uuids} ; do
  if [ ${counter} -lt 3 ] ; then
    ironic node-update ${uuid} add properties/capabilities="node:controller-$counter,profile:control,boot_option:local"
  elif [ ${counter} -eq 3 ] ; then
    ironic node-update ${uuid} add properties/capabilities="node:compute-0,profile:compute,boot_option:local"
  else
    #ironic node-update $uuid add properties/capabilities='profile:control,boot_option:local'
    other=$(( counter -4))
    ironic node-update ${uuid} add properties/capabilities="node:ceph-storage-$other,profile:ceph-storage,boot_option:local"
    ##ironic node-update $uuid add properties/root_device='{"wwn": "0x0000000000000001"}'
    ironic node-update ${uuid} add properties/root_device='{"name": "/dev/vda"}'
  fi
counter=$(( counter +1))
done
