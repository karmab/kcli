VERSION="[[ kubevirt_version ]]"
yum -y install xorg-x11-xauth virt-viewer
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
setenforce 0
oc project kube-system
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/kubevirt.yaml
oc adm policy add-scc-to-user privileged -z kubevirt-privileged
oc adm policy add-scc-to-user privileged -z kubevirt-controller
oc create -f kubevirt.yaml
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/virtctl-$VERSION-linux-amd64
mv virtctl-$VERSION-linux-amd64 /usr/bin/virtctl
chmod u+x /usr/bin/virtctl
oc project default
docker pull karmab/kcli
echo alias kcli=\'docker run -it --rm -v ~/.kube:/root/.kube:Z -v ~/.ssh:/root/.ssh karmab/kcli\' >> /root/.bashrc
