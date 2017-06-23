export PASSWORD="unix1234"
wget -O /root/.ovirtshellrc https://raw.githubusercontent.com/karmab/kcli/master/plans/ovirt/ovirtshellrc
sed -i "s/username =.*/username = admin@internal/" /root/.ovirtshellrc
sed -i "s/password =.*/password = $PASSWORD/" /root/.ovirtshellrc
sed -i "s/insecure = False/insecure = True/" /root/.ovirtshellrc
echo $PASSWORD | passwd --stdin root
sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config
systemctl restart sshd
ovirt-shell -E "add host --address rhvnode01.default --cluster-name Default --name rhvnode01.default --root_password $PASSWORD"
ovirt-shell -E "add host --address rhvnode02.default --cluster-name Default --name rhvnode02.default --root_password $PASSWORD"
sleep 240
ovirt-shell -E "add storagedomain --name vms --host-name rhvnode01.default --type data --storage-type nfs --storage-address rhvengine.default --storage-path /vms"
ovirt-shell -E "add storagedomain --name vms --parent-datacenter-name Default"
ovirt-shell -E "add storagedomain --name isos --host-name rhvnode01.default --type iso --storage-type nfs --storage-address rhvengine.default --storage-path /isos"
ovirt-shell -E "add storagedomain --name isos --parent-datacenter-name Default"
ovirt-shell -E "add openstackimageprovider --name glance --url http://192.168.122.162:9292 --authentication_url http://192.168.122.162:5000/v2.0 --username admin --password unix1234 --tenant_name admin --requires_authentication True"
ovirt-shell -E "add openstackvolumeprovider --name cinder --url http://192.168.122.162:8776 --authentication_url http://192.168.122.162:5000/v2.0 --username admin --password unix1234 --tenant_name admin --requires_authentication True"
ovirt
