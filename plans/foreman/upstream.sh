export ORG="Karmalabs"
export LOCATION="Madrid"
export PASSWORD="unix1234"
yum -y install foreman-installer wget
echo `hostname -I` `hostname -s`.default `hostname -s` >> /etc/hosts
foreman-installer --foreman-admin-username admin  --foreman-admin-password $PASSWORD --foreman-initial-location $LOCATION --foreman-initial-organization $ORG
