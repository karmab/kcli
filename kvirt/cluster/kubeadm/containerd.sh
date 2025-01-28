{% if ubuntu|default(False) %}
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key --keyring /etc/apt/trusted.gpg.d/docker.gpg add -
add-apt-repository "deb https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y containerd || apt-get install -y containerd.io
{% else %}
TARGET={{ 'fedora' if 'fedora' in image|lower else 'centos' }}
dnf install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/$TARGET/docker-ce.repo
dnf install -y containerd.io
{% endif %}

mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
{% if 'fedora' in image|lower or 'centos9stream' in image|lower or ubuntu|default(False) %}
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
sed -i 's%config_path = .*%config_path = "/etc/containerd/certs.d"%' /etc/containerd/config.toml
REGISTRY={{ api_ip }}:5000
mkdir -p /etc/containerd/certs.d/$REGISTRY
cat > /etc/containerd/certs.d/$REGISTRY/hosts.toml << EOF
[host."http://$REGISTRY"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
EOF
{% endif %}

{% if disconnected_url != None %}
REGISTRY={{ disconnected_url }}
REGISTRY_USER={{ disconnected_user }}
REGISTRY_PASSWORD={{ disconnected_password }}
KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
sed -i "s%sandbox_image = .*%sandbox_image = \"$REGISTRY/pause:latest\"%" /etc/containerd/config.toml
sed -i 's%config_path = .*%config_path = "/etc/containerd/certs.d"%' /etc/containerd/config.toml
mkdir -p /etc/containerd/certs.d/_default
cat > /etc/containerd/certs.d/_default/hosts.toml << EOF
[host."https://$REGISTRY"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
  [host."https://$REGISTRY".header]
    authorization = "Basic $KEY"
EOF
{% elif docker_user != None and docker_password != None %}
REGISTRY_USER={{ docker_user }}
REGISTRY_PASSWORD={{ docker_password }}
KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
sed -i 's%config_path = .*%config_path = "/etc/containerd/certs.d"%' /etc/containerd/config.toml
mkdir -p /etc/containerd/certs.d/docker.io
cat > /etc/containerd/certs.d/docker.io/hosts.toml << EOF
[host."https://registry-1.docker.io"]
  capabilities = ["pull", "resolve"]
  [host."https://registry-1.docker.io".header]
    authorization = "Basic $KEY"
EOF
{% endif %}

systemctl enable --now containerd || systemctl daemon-reload
systemctl restart containerd
