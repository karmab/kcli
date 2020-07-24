export DEBIAN_FRONTEND=noninteractive
PKGMGR="apt-get"
$PKGMGR -y install keepalived
cp /root/keepalived.conf /etc/keepalived
systemctl enable --now keepalived
systemctl start keepalived
