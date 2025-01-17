apt-get update && apt-get -y install apt-transport-https curl git

VERSION={{ version or "$(curl -L -s https://dl.k8s.io/release/stable.txt)" }}
# Ensure the version is in the format v<major>.<minor> regardless of the source
VERSION=$(echo "v${VERSION#v}" | cut -d. -f1,2)
mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/$VERSION/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$VERSION/deb/ /
EOF
apt-get update

{% if nfs %}
apt-get -y install nfs-common
{% endif %}

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

{% set kube_packages = 'kubelet=%s* kubectl=%s* kubeadm=%s*' % (version, version, version) if version != None and version|count('.') == 2 else 'kubelet kubectl kubeadm' %}
apt-get -y install {{ kube_packages }} openssl
{% if engine == 'crio' %}
echo KUBELET_EXTRA_ARGS=--cgroup-driver=systemd --container-runtime-endpoint=unix:///var/run/crio/crio.sock > /etc/default/kubelet
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
