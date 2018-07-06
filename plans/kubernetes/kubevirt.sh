VERSION="[[ kubevirt_version ]]"
yum -y install xorg-x11-xauth virt-viewer wget
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
setenforce 0
kubectl config set-context `kubectl config current-context` --namespace=kube-system
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/kubevirt.yaml
kubectl create -f kubevirt.yaml
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/virtctl-$VERSION-linux-amd64
mv virtctl-$VERSION-linux-amd64 /usr/bin/virtctl
chmod u+x /usr/bin/virtctl
kubectl config set-context `kubectl config current-context` --namespace=default
docker pull karmab/kcli
echo alias kcli=\'docker run -it --rm -v ~/.kube:/root/.kube:Z  -v $SSH_AUTH_SOCK:/ssh-agent --env SSH_AUTH_SOCK=/ssh-agent -v ~/.kcli:/root/.kcli:Z karmab/kcli\' >> /root/.bashrc
