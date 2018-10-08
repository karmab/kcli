#!/bin/bash

uuids=`ironic node-list | grep -v UUID | awk -F'|' '{ print $2}' | xargs`
counter=0
for uuid in ${uuids} ; do
  if [ ${counter} -eq 3 ] ; then
    #ironic node-update $uuid add properties/capabilities='profile:compute,boot_option:local'
    ironic node-update ${uuid} add properties/capabilities="node:compute-0,profile:compute,boot_option:local"
  else
    #ironic node-update $uuid add properties/capabilities='profile:control,boot_option:local'
    ironic node-update ${uuid} add properties/capabilities="node:controller-$counter,profile:control,boot_option:local"
  fi
counter=$(( counter +1))
done
