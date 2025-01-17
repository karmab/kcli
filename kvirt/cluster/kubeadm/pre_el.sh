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
sysctl -p
setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config

{% if nfs %}
dnf -y install nfs-utils
{% endif %}

TARGET={{ 'fedora' if 'fedora' in image|lower else 'centos' }}
[ "$TARGET" == 'fedora' ] && dnf -y remove zram-generator-defaults && swapoff -a

modprobe overlay
modprobe br_netfilter
echo -e 'overlay\nbr_netfilter' > /etc/modules-load.d/kubeadm.conf
cat <<EOF | tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sysctl --system

{% if engine == 'crio' %}
bash /root/crio-d.sh
{% else %}
bash /root/containerd.sh
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

{% if registry %}
mkdir -p /etc/containers
echo """[[registry]]
insecure = true
location = \"{{ api_ip }}\"""" >> /etc/containers/registries.conf
{% endif %}
