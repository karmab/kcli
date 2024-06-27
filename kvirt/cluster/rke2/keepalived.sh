PKGMGR="{{ 'apt-get' if ubuntu else 'dnf' }}"
$PKGMGR -y install keepalived
NETMASK=$(ip -o -f inet addr show | awk '/scope global/ {print $4}' | head -1 | cut -d'/' -f2)
sed -i "s/NETMASK/$NETMASK/" /root/keepalived.conf
NIC=$(find /sys/class/net -type l -not -lname '*virtual*' -printf '%f\n' | head -1)
sed -i "s/NIC/$NIC/" /root/keepalived.conf
cp /root/keepalived.conf /etc/keepalived
systemctl enable --now keepalived
