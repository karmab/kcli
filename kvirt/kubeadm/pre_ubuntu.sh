apt-get update && apt-get -y install apt-transport-https curl git
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb http://apt.kubernetes.io/ kubernetes-xenial main
EOF
apt-get update
{% if version != None %}
VERSION=$(apt-cache show kubectl | grep Version | grep {{ version }} | head -1 | awk -F: '{print $2}' | xargs)
{% else %}
VERSION=$(apt-cache show kubectl | grep Version | head -1 | awk -F: '{print $2}' | xargs)
{% endif %}

{% if engine == 'docker' %}
apt-get -y install docker.io
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
OS="xUbuntu_20.04"
CRIO_VERSION=$(echo $VERSION | cut -d. -f1,2)
cat <<EOF | tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/ /
EOF
cat <<EOF | tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.list
deb http://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable:/cri-o:/$CRIO_VERSION/$OS/ /
EOF
curl -L https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/Release.key | apt-key --keyring /etc/apt/trusted.gpg.d/libcontainers.gpg add -
curl -L https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION/$OS/Release.key | apt-key --keyring /etc/apt/trusted.gpg.d/libcontainers-cri-o.gpg add -
apt-get update
apt-get -y install cri-o cri-o-runc
sed -i 's@conmon = .*@conmon = "/bin/conmon"@' /etc/crio/crio.conf
systemctl restart crio
{% else %}
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key --keyring /etc/apt/trusted.gpg.d/docker.gpg add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y containerd.io
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
systemctl restart containerd
{% endif %}
{% endif %}
apt-get -y install kubelet=$VERSION kubectl=$VERSION kubeadm=$VERSION
{% if engine == 'crio' %}
echo KUBELET_EXTRA_ARGS=--cgroup-driver=systemd --container-runtime-endpoint=unix:///var/run/crio/crio.sock > /etc/default/kubelet
{% endif %}
systemctl enable --now kubelet

{% if sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
{% endif %}
