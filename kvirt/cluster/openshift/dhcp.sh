yum -y install dnsmasq
cp /root/dhcp.conf /etc/dnsmasq.d/{{ domain }}.conf
systemctl enable --now dnsmasq
