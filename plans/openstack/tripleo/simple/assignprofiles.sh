#!/bin/bash

uuids=`ironic node-list | grep -v UUID | awk -F'|' '{ print $2}' | xargs`
counter=0
for uuid in ${uuids} ; do
counter=$(( counter +1))
  if [ ${counter} -eq 2 ] ; then
    ironic node-update ${uuid} add properties/capabilities='profile:compute,boot_option:local'
  else
    ironic node-update ${uuid} add properties/capabilities='profile:control,boot_option:local'
  fi
done
