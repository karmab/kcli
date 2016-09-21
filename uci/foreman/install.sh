export ORG="Karmalabs"
export LOCATION="Madrid"
export PASSWORD="unix1234"
echo `hostname -I` `hostname -s`.uci `hostname -s` >> /etc/hosts
yum -y install foreman-installer
foreman-installer --scenario satellite --foreman-admin-username admin  --foreman-admin-password $PASSWORD --foreman-initial-location $LOCATION --foreman-initial-organization $ORG --capsule-puppet true --foreman-proxy-puppetca true --foreman-proxy-tftp true --enable-foreman-plugin-discovery
mkdir ~/.hammer
wget -O /root/cli_config.yml https://raw.githubusercontent.com/karmab/kcli/master/rhci/hammer.yml
chmod 600 ~/.hammer/cli_config.yml
hammer user update --login admin --default-location-id 1 --default-organization-id 1 --locations "$LOCATION" --organizations "$ORG"
