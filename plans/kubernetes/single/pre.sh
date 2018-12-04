K8S="{{ k8s_version }}"
yum -y install wget
wget -P /root/ https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
mv /root/jq-linux64 /usr/bin/jq
chmod u+x /usr/bin/jq
echo net.bridge.bridge-nf-call-iptables=1 >> /etc/sysctl.d/99-sysctl.conf
sysctl -p
setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
if [ "$K8S" == "latest" ] ; then
  K8S=`curl -s https://api.github.com/repos/kubernetes/kubernetes/releases/latest| jq -r .tag_name | sed 's/v//'`
fi
yum install -y docker kubelet-$K8S kubectl-$K8S kubeadm-$K8S
sed -i "s/--selinux-enabled //" /etc/sysconfig/docker
systemctl enable docker && systemctl start docker
systemctl enable kubelet && systemctl start kubelet
