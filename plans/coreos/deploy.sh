#!/bin/sh

IP=`ifconfig %s | grep \"inet \" | awk '{print $2}'`
ETCD_ENDPOINT="http://$IP:2379"
mkdir -p /etc/kubernetes/cni/net.d
echo -e "DOCKER_OPT_BIP=\"\"\nDOCKER_OPT_IPMASQ=\"\"" > /etc/kubernetes/cni/docker_opts_cni.env
cp /root/10-flannel.conf /etc/kubernetes/cni/net.d
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
