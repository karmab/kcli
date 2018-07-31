#!/bin/sh

IP=`ifconfig %s | grep \"inet \" | awk '{print $2}'`
ETCD_ENDPOINT="http://$IP:2379"
mkdir -p /etc/kubernetes/cni/net.d
echo -e "DOCKER_OPT_BIP=\"\"\nDOCKER_OPT_IPMASQ=\"\"" > /etc/kubernetes/cni/docker_opts_cni.env
cp /root/10-flannel.conf /etc/kubernetes/cni/net.d
echo -e FLANNELD_IFACE=$IP\nFLANNELD_ETCD_ENDPOINTS=http://$IP:2379 > /etc/flannel/options.env
sed -i "s/ADVERTISE_IP/$IP/" /etc/systemd/system/kubelet.service
sed -i "s@ETCD_ENDPOINT@$ETCD_ENDPOINT@" /root/kube-apiserver.yaml
sed -i "s/ADVERTISE_IP/$IP/" /root/kube-apiserver.yaml
mkdir -p /etc/kubernetes/manifests
mv /root/kube*.yaml /etc/kubernetes/manifests
systemctl daemon-reload

POD_NETWORK="10.2.0.0/16"
curl -X PUT -d "value={\"Network\":\"$POD_NETWORK\",\"Backend\":{\"Type\":\"vxlan\"}}" "$ETCD_ENDPOINT/v2/keys/coreos.com/network/config"
systemctl start flanneld
systemctl enable flanneld
systemctl start kubelet
systemctl enable kubelet

curl -O https://storage.googleapis.com/kubernetes-release/release/v1.6.1/bin/linux/amd64/kubectl
chmod +x kubectl
export CA_CERT=/etc/kubernetes/ssl/ca.pem
export ADMIN_KEY=/etc/kubernetes/ssl/admin.pem
export ADMIN_KEY=/etc/kubernetes/ssl/admin-key.pem
export ADMIN_CERT=/etc/kubernetes/ssl/admin.pem
./kubectl config set-cluster default-cluster --server=https://${MASTER_HOST} --certificate-authority=${CA_CERT}
./kubectl config set-credentials default-admin --certificate-authority=${CA_CERT} --client-key=${ADMIN_KEY} --client-certificate=${ADMIN_CERT}
./kubectl config set-context default-system --cluster=default-cluster --user=default-admin
./kubectl config use-context default-system
