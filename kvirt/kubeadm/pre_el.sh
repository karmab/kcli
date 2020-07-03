echo """[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=0
repo_gpgcheck=0""" >/etc/yum.repos.d/kubernetes.repo
yum -y install git
echo net.bridge.bridge-nf-call-iptables=1 >> /etc/sysctl.d/99-sysctl.conf
sysctl -p
setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
{%- if version != None %}
VERSION=$(yum --showduplicates list kubectl  | grep kubectl | grep {{ version }} | tail -1 | awk '{print $2}' | xargs)
{%- else %}
VERSION=$(yum --showduplicates list kubectl  | grep kubectl | tail -1 | awk '{print $2}' | xargs)
{%- endif %}
yum install -y docker kubelet-$VERSION kubectl-$VERSION kubeadm-$VERSION
sed -i "s/--selinux-enabled //" /etc/sysconfig/docker
systemctl enable docker && systemctl start docker
systemctl enable kubelet && systemctl start kubelet
