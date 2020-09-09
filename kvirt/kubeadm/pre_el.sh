echo """[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=0
repo_gpgcheck=0""" >/etc/yum.repos.d/kubernetes.repo
echo net.bridge.bridge-nf-call-iptables=1 >> /etc/sysctl.d/99-sysctl.conf
sysctl -p
setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
{%- if version != None %}
VERSION=$(dnf --showduplicates list kubectl  | grep kubectl | grep {{ version }} | tail -1 | awk '{print $2}' | xargs)
{%- else %}
VERSION=$(dnf --showduplicates list kubectl  | grep kubectl | tail -1 | awk '{print $2}' | xargs)
{%- endif %}
dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
dnf -y install -y docker-ce kubelet-$VERSION kubectl-$VERSION kubeadm-$VERSION git --nobest
systemctl enable --now docker
systemctl enable --now kubelet
