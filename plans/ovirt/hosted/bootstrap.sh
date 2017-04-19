yum -y install rhevm-appliance screen ovirt-hosted-engine-setup ovirt-engine-cli
sed -i /requiretty/d /etc/sudoers
hosted-engine --deploy --config-append=/root/answers.conf
hostnode="rhvnode1.default"
nfsnode="rhvnfs.default"
ovirt-shell -E "add storagedomain --name vms --host-name $hostnode --type data --storage-type nfs --storage-address $nfsnode --storage-path /vms"
ovirt-shell -E "add storagedomain --name vms --parent-datacenter-name Default"
ovirt-shell -E "add storagedomain --name isos --host-name $hostnode --type iso --storage-type nfs --storage-address $nfsnode --storage-path /isos"
ovirt-shell -E "add storagedomain --name isos --parent-datacenter-name Default"
python /root/rhvnode2.py
