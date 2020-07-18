PKGMGR="{{ 'apt-get' if ubuntu else 'yum' }}"
$PKGMGR -y install keepalived
cp /root/keepalived.conf /etc/keepalived
systemctl enable --now keepalived
