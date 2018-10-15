heat stack-delete -y overcloud
uuids=`ironic node-list | grep -v UUID | awk -F'|' '{ print $2}' | xargs`
for uuid in ${uuids} ; do
    ironic node-set-maintenance ${uuid} false
    ironic node-delete ${uuid}
done
