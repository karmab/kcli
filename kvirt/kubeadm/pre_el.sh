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
{% if eksd %}
{% set split = eksd_version.split('-') %}
{% set kubernetes_version = split[0] + '-' + split[1] %}
VERSION=$(dnf --showduplicates list kubectl  | grep kubectl | grep {{ kubernetes_version|replace('-', '.') }} | tail -1 | awk '{print $2}' | xargs)
{% elif version != None %}
VERSION=$(dnf --showduplicates list kubectl  | grep kubectl | grep {{ version }} | tail -1 | awk '{print $2}' | xargs)
{% else %}
VERSION=$(dnf --showduplicates list kubectl  | grep kubectl | tail -1 | awk '{print $2}' | xargs)
{% endif %}

TARGET={{ 'fedora' if 'fedora' in image|lower else 'centos' }}
[ "$TARGET" == 'fedora' ] && dnf -y remove zram-generator-defaults && swapoff -a
{% if engine == 'docker' %}
dnf config-manager --add-repo=https://download.docker.com/linux/$TARGET/docker-ce.repo
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
OS="CentOS_8_Stream"
{% if engine_version != None %}
CRIO_VERSION={{ engine_version }}
{% else %}
CRIO_VERSION=$(echo $VERSION | cut -d. -f1,2)
{% endif %}
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable.repo https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/devel:kubic:libcontainers:stable.repo
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION/$OS/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo
dnf -y install containers-common-1-6.module_el8.6.0+954+963caf36
dnf -y install cri-o conntrack
sed -i 's@conmon = .*@conmon = "/bin/conmon"@' /etc/crio/crio.conf
{% if HTTP_PROXY is defined %}
mkdir /etc/systemd/system/crio.service.d
cat > /etc/systemd/system/crio.service.d/http_proxy.conf << EOF
[Service]
Environment="HTTP_PROXY={{ HTTP_PROXY }}"
EOF
{% if HTTPS_PROXY is defined %}
cat > /etc/systemd/system/crio.service.d/https_proxy.conf << EOF
[Service]
Environment="HTTPS_PROXY={{ HTTPS_PROXY }}"
EOF
{% if NO_PROXY is defined %}
cat > /etc/systemd/system/crio.service.d/no_proxy.conf << EOF
[Service]
Environment="NO_PROXY={{ NO_PROXY }}"
EOF
{% endif %}
{% endif %}
{% endif %}
rm -f /etc/cni/net.d/100-crio-bridge.conf
systemctl enable --now crio
{% else %}
dnf install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/$TARGET/docker-ce.repo
dnf install -y containerd.io
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
{% if HTTP_PROXY is defined %}
mkdir /etc/systemd/system/containerd.service.d
cat > /etc/systemd/system/containerd.service.d/http_proxy.conf << EOF
[Service]
Environment="HTTP_PROXY={{ HTTP_PROXY }}"
EOF
{% if HTTPS_PROXY is defined %}
cat > /etc/systemd/system/containerd.service.d/https_proxy.conf << EOF
[Service]
Environment="HTTPS_PROXY={{ HTTPS_PROXY }}"
EOF
{% if NO_PROXY is defined %}
cat > /etc/systemd/system/containerd.service.d/no_proxy.conf << EOF
[Service]
Environment="NO_PROXY={{ NO_PROXY }}"
EOF
{% endif %}
{% endif %}
{% endif %}
systemctl enable --now containerd
systemctl restart containerd
{% endif %}
{% endif %}

dnf -y install -y kubelet-$VERSION kubectl-$VERSION kubeadm-$VERSION git openssl
{% if engine == 'crio' %}
echo KUBELET_EXTRA_ARGS=--cgroup-driver=systemd --container-runtime-endpoint=unix:///var/run/crio/crio.sock > /etc/sysconfig/kubelet
{% endif %}
systemctl enable --now kubelet

{% if sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
{% endif %}
