export ORG="Karmalabs"
export LOCATION="Madrid"
export PASSWORD="unix1234"
echo `hostname -I` `hostname -s`.uci `hostname -s` >> /etc/hosts
yum -y install foreman-installer wget
