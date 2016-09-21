yum -y install foreman-installer wget
foreman-installer --foreman-admin-username admin  --foreman-admin-password $PASSWORD --foreman-initial-location $LOCATION --foreman-initial-organization $ORG
