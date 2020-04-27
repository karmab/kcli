apt-get update && apt-get install -y apt-transport-https curl wget
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
wget -P /root/ https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
mv /root/jq-linux64 /usr/bin/jq
chmod u+x /usr/bin/jq
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb http://apt.kubernetes.io/ kubernetes-xenial main
EOF
apt-get update
apt-get install -y docker.io kubelet kubectl kubeadm
systemctl enable docker && systemctl start docker
systemctl enable kubelet && systemctl start kubelet
