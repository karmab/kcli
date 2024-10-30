VERSION={{ version or "$(curl -L -s https://dl.k8s.io/release/stable.txt)" }}
# Ensure the version is in the format v<major>.<minor> regardless of the source
VERSION=$(echo "v${VERSION#v}" | cut -d. -f1,2)

echo """[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/$VERSION/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/$VERSION/rpm/repodata/repomd.xml.key""" >/etc/yum.repos.d/kubernetes.repo
echo net.bridge.bridge-nf-call-iptables=1 >> /etc/sysctl.d/99-sysctl.conf
modprobe br_netfilter
sysctl -p
setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config

{% if nfs %}
dnf -y install nfs-utils
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
echo overlay >> /etc/modules
echo br_netfilter >> /etc/modules
cat <<EOF | tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sysctl --system
{% if engine == 'crio' %}
PROJECT_PATH={{ engine_version or 'stable:/$VERSION' }}
echo """[cri-o]
name=CRI-O
baseurl=https://pkgs.k8s.io/addons:/cri-o:/$PROJECT_PATH/rpm
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/addons:/cri-o:/$PROJECT_PATH/rpm/repodata/repomd.xml.key""" >/etc/yum.repos.d/cri-o.repo
dnf -y install container-selinux cri-o conntrack
sed -i 's@conmon = .*@conmon = "/bin/conmon"@' /etc/crio/crio.conf
echo """[crio.network]
plugin_dirs = [\"/opt/cni/bin\", \"/usr/libexec/cni\",]""" > /etc/crio/crio.conf.d/00-plugin-dir.conf
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

{% if registry %}
echo """[[registry]]
insecure = true
location = \"{{ api_ip }}\"""" >> /etc/containers/registries.conf
{% endif %}

systemctl enable --now crio
{% else %}
dnf install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/$TARGET/docker-ce.repo
dnf install -y containerd.io
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
{% if 'fedora' in image|lower or 'centos9stream' in image|lower %}
sed -i 's/SystemdCgroup = .*/SystemdCgroup = true/' /etc/containerd/config.toml
{% endif %}
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

{% if registry %}
sed -i "/registry.mirrors/a\        [plugins.\"io.containerd.grpc.v1.cri\".registry.mirrors.\"{{ api_ip }}:5000\"]\n          endpoint = [\"http://{{ api_ip }}:5000\"]\n          insecure_skip_verify = true" /etc/containerd/config.toml
{% endif %}

systemctl enable --now containerd
systemctl restart containerd
{% endif %}
{% endif %}

{% set kube_packages = 'kubelet-%s kubectl-%s kubeadm-%s' % (version, version, version) if version != None and version|count('.') == 2 else 'kubelet kubectl kubeadm' %}
dnf -y install -y {{ kube_packages }} git openssl
if [ "$TARGET" == 'fedora' ] ; then
  [ -d /opt/cni/bin ] || mkdir -p /opt/cni/bin
  cp /usr/libexec/cni/* /opt/cni/bin
fi
{% if engine == 'crio' %}
echo KUBELET_EXTRA_ARGS=--cgroup-driver=systemd --container-runtime-endpoint=unix:///var/run/crio/crio.sock > /etc/sysconfig/kubelet
{% endif %}
systemctl enable --now kubelet

{% if sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
{% endif %}
