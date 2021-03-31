echo """[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=0
repo_gpgcheck=0""" >/etc/yum.repos.d/kubernetes.repo
echo net.bridge.bridge-nf-call-iptables=1 >> /etc/sysctl.d/99-sysctl.conf
modprobe br_netfilter
sysctl -p
setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
{% if version != None %}
VERSION=$(dnf --showduplicates list kubectl  | grep kubectl | grep {{ version }} | tail -1 | awk '{print $2}' | xargs)
{% else %}
VERSION=$(dnf --showduplicates list kubectl  | grep kubectl | tail -1 | awk '{print $2}' | xargs)
{% endif %}

{% if engine == 'docker' %}
dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
dnf -y install -y docker-ce iptables --nobest
export PATH=/sbin:$PATH
systemctl enable --now docker
{% else %}
modprobe overlay
modprobe br_netfilter
cat <<EOF | tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sysctl --system
{% if engine == 'crio' %}
OS="CentOS_8"
CRIO_VERSION=$(echo $VERSION | cut -d. -f1,2)
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable.repo https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/devel:kubic:libcontainers:stable.repo
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION/$OS/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo
yum -y install cri-o conntrack
sed -i 's@conmon = .*@conmon = "/bin/conmon"@' /etc/crio/crio.conf
systemctl enable --now crio
{% else %}
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y containerd.io
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
systemctl enable --now containerd
systemctl restart containerd
{% endif %}
{% endif %}

dnf -y install -y kubelet-$VERSION kubectl-$VERSION kubeadm-$VERSION git
{% if engine == 'crio' %}
echo KUBELET_EXTRA_ARGS=--cgroup-driver=systemd --container-runtime-endpoint=unix:///var/run/crio/crio.sock > /etc/sysconfig/kubelet
{% endif %}
systemctl enable --now kubelet
