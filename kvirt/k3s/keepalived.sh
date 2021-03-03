export DEBIAN_FRONTEND=noninteractive
apt-get update 
apt-get -y install keepalived
cp /root/keepalived.conf /etc/keepalived
systemctl enable --now keepalived
systemctl start keepalived
