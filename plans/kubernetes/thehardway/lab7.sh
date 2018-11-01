wget -q --show-progress --https-only --timestamping "https://github.com/coreos/etcd/releases/download/v3.3.9/etcd-v3.3.9-linux-amd64.tar.gz"
tar -xvf etcd-v3.3.9-linux-amd64.tar.gz
mv etcd-v3.3.9-linux-amd64/etcd* /usr/local/bin
mkdir -p /etc/etcd /var/lib/etcd
cp ca.pem kubernetes-key.pem kubernetes.pem /etc/etcd
for instance in controller-0 controller-1 controller-2; do
 INTERNAL_IP=$( dig +short ${instance})
 ETCD_NAME=${instance}
 sed "s/INTERNAL_IP/$INTERNAL_IP/" etcd.service> etcd.service_X
 sed "s/ETCD_NAME/$ETCD_NAME/" etcd.service_X > etcd.service_$instance
 scp etcd.service_$instance $instance:/etc/systemd/system/
 systemctl daemon-reload
 systemctl enable etcd
 systemctl start etcd
done
