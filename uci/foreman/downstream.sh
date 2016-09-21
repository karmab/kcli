yum -y install satellite-installer wget
satellite-installer --scenario satellite --foreman-admin-username admin  --foreman-admin-password $PASSWORD --foreman-initial-location $LOCATION --foreman-initial-organization $ORG --capsule-puppet true --foreman-proxy-puppetca true --foreman-proxy-tftp true --enable-foreman-plugin-discovery
