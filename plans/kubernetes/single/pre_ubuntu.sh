apt-get update && apt-get install -y apt-transport-https curl
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb http://apt.kubernetes.io/ kubernetes-xenial main
EOF
apt-get update
apt-get install -y docker.io kubelet=[[ version ]]-00 kubectl=[[ version ]]-00 kubeadm=[[ version ]]-00
systemctl enable docker && systemctl start docker
systemctl enable kubelet && systemctl start kubelet
