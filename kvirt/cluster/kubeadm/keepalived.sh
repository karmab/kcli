PKGMGR="{{ 'apt-get' if ubuntu else 'dnf' }}"
$PKGMGR -y install keepalived
NETMASK=$(ip -o -f inet addr show | awk '/scope global/ {print $4}' | head -1 | cut -d'/' -f2)
sed -i "s/NETMASK/$NETMASK/" /root/keepalived.conf
NIC=$(awk '/default/ {for(i=1;i<=NF;i++) if($i=="dev") {print $(i+1); exit}}' <(ip route show default; ip -6 route show default))
sed -i "s/NIC/$NIC/" /root/keepalived.conf
cp /root/keepalived.conf /etc/keepalived
systemctl enable --now keepalived
