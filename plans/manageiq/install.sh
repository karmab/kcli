export MANAGEIQ_PASSWORD="unix1234"
export OVIRT_PASSWORD="unix1234"
export OPENSTACK_PASSWORD="unix1234"
export OPENSTACK_NAME="liberty.default"
export OVIRT_NAME="proutengine.default"
hostnamectl set-hostname manageiq
echo $MANAGEIQ_PASSWORD | passwd --stdin root
appliance_console_cli --host=manageiq --region=01 --internal --password="$MANAGEIQ_PASSWORD" --key --force-key --dbdisk=/dev/vdb --sshpassword="$MANAGEIQ_PASSWORD"
/var/www/miq/vmdb/script/rails r "User.find_by_userid('admin').update_attributes(:password => $MANAGEIQ_PASSWORD)"
curl -k -u admin:$MANAGEIQ_PASSWORD -i -X POST -H "Accept: application/json" -d "{ 'action' : 'create', 'resource' : { 'type': 'ManageIQ::Providers::Redhat::InfraManager','name': 'ovirt','hostname':$OVIRT_NAME,'credentials' : {'userid':'admin@internal','password':$OVIRT_PASSWORD}}}" https://127.0.0.1/api/providers
curl --user admin:$MANAGEIQ_PASSWORD -i -k -X POST -H "Accept: application/json" -d "{ 'action' : 'create', 'resource' : { 'type' : 'ManageIQ::Providers::Openstack::CloudManager', 'name' : 'openstack', 'hostname' : $OPENSTACK_NAME, 'port' : '5000', 'credentials' : [ { 'userid' : 'admin', 'password' : $OPENSTACK_PASSWORD }, { 'userid' : 'guest', 'password' : 'guest', 'auth_type' : 'amqp' } ]  } }" https://127.0.0.1/api/providers
