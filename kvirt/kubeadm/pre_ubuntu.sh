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
{% elif engine == 'containerd' %}
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key --keyring /etc/apt/trusted.gpg.d/docker.gpg add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update 
apt-get install -y containerd.io
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
systemctl enable --now containerd
{% else %}
OS="xUbuntu_20.04"
cat <<EOF | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/ /
EOF
cat <<EOF | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable:cri-o:$VERSION.list
deb http://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable:/cri-o:/$VERSION/$OS/ /
EOF
curl -L https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/Release.key | sudo apt-key --keyring /etc/apt/trusted.gpg.d/libcontainers.gpg add -
curl -L https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable:cri-o:$VERSION/$OS/Release.key | sudo apt-key --keyring /etc/apt/trusted.gpg.d/libcontainers-cri-o.gpg add -
apt-get update
apt-get install cri-o cri-o-runc
systemctl enable --now crio
{% endif %}

apt-get -y install kubelet=$VERSION kubectl=$VERSION kubeadm=$VERSION
systemctl enable --now kubelet
