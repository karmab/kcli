{% if 'ubuntu' in image %}
export DEBIAN_FRONTEND=noninteractive
apt-get update 
apt-get -y install keepalived
{% endif %}
NIC=$(find /sys/class/net -type l -not -lname '*virtual*' -printf '%f\n' | head -1)
sed -i "s/NIC/$NIC/" /root/keepalived.conf
cp /root/keepalived.conf /etc/keepalived
systemctl enable --now keepalived
systemctl start keepalived
