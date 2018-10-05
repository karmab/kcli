#!/usr/bin/env bash
yum -y install heketi-client heketi bind-utils
rm -f /etc/heketi/heketi.json
cp /root/heketi.json /etc/heketi
chown heketi.heketi /etc/heketi/heketi.json
sed -i "s/ -config/ --config/" /usr/lib/systemd/system/heketi.service
cp /root/.ssh/id_rsa /var/lib/heketi/
chown heketi.heketi /var/lib/heketi/id_rsa
systemctl enable heketi
systemctl start heketi
IP1=`dig +short gluster01`
IP2=`dig +short gluster02`
IP3=`dig +short gluster03`
sed -i "s/gluster01/$IP1/" /root/topology.json
sed -i "s/gluster02/$IP2/" /root/topology.json
sed -i "s/gluster03/$IP3/" /root/topology.json
export HEKETI_CLI_SERVER=http://127.0.0.1:8080
heketi-cli topology load --json=/root/topology.json
echo export HEKETI_CLI_SERVER=http://127.0.0.1:8080 >/etc/profile.d/heketi.sh
