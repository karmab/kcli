VERSION="v[[ version ]]"
yum -y install xorg-x11-xauth remote-viewer
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
setenforce 0
oc project kube-system
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/kubevirt.yaml
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/spice-proxy.yaml
oc adm policy add-scc-to-user privileged -z kubevirt-infra
oc adm policy add-scc-to-user hostmount-anyuid -z kubevirt-infra
oc create -f kubevirt.yaml
oc create -f spice-proxy.yaml
oc expose deploy haproxy  --port=8184
oc expose svc haproxy
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/virtctl-$VERSION-linux-amd64
mv virtctl-$VERSION-linux-amd64 /usr/bin/virtctl
chmod u+x /usr/bin/virtctl
oc create -f /root/iscsi-demo-target.yaml
