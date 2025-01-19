VERSION={{ version or "$(curl -L -s https://dl.k8s.io/release/stable.txt)" }}
# Ensure the version is in the format v<major>.<minor> regardless of the source
VERSION=$(echo "v${VERSION#v}" | cut -d. -f1,2)

{% if ubuntu|default(False) %}
PROJECT_PATH={{ engine_version or 'stable:/$VERSION' }}
curl -fsSL https://pkgs.k8s.io/addons:/cri-o:/$PROJECT_PATH/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/cri-o-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/cri-o-apt-keyring.gpg] https://pkgs.k8s.io/addons:/cri-o:/$PROJECT_PATH/deb/ /" > /etc/apt/sources.list.d/cri-o.list
apt-get update
apt-get -y install cri-o runc software-properties-common
{% else %}
PROJECT_PATH={{ engine_version or 'stable:/$VERSION' }}
echo """[cri-o]
name=CRI-O
baseurl=https://pkgs.k8s.io/addons:/cri-o:/$PROJECT_PATH/rpm
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/addons:/cri-o:/$PROJECT_PATH/rpm/repodata/repomd.xml.key""" >/etc/yum.repos.d/cri-o.repo
dnf -y install container-selinux cri-o conntrack
{% endif %}

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
systemctl daemon-reload
rm -f /etc/cni/net.d/100-crio-bridge.conf

{% if registry %}
echo """[[registry]]
insecure = true
location = \"{{ api_ip }}\"""" >> /etc/containers/registries.conf
{% endif %}

{% if disconnected_url != None %}
REGISTRY={{ disconnected_url }}
REGISTRY_USER={{ disconnected_user }}
REGISTRY_PASSWORD={{ disconnected_password }}
KEY=$(echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
echo """[[registry]]
insecure = true
location = \"$REGISTRY\"""" >> /etc/containers/registries.conf
echo {\"auths\": {\"$REGISTRY\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.corp\"}}} > /root/kubeadm_pull.json
echo """[crio.image]
global_auth_file = \"/root/kubeadm_pull.json\"
pause_image_auth_file = \"/root/kubeadm_pull.json\"
pause_image = \"$REGISTRY/pause:latest\"""" > /etc/crio/crio.conf.d/00-crio.conf
{% elif docker_user != None and docker_password != None %}
REGISTRY_USER={{ docker_user }}
REGISTRY_PASSWORD={{ docker_password }}
KEY=$(echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
echo """[[registry]]
insecure = true
location = \"registry-1.docker.io\"""" >> /etc/containers/registries.conf
echo {\"auths\": {\"registry-1.docker.io\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.corp\"}}} > /root/kubeadm_pull.json
echo """[crio.image]
global_auth_file = \"/root/kubeadm_pull.json\"""" > /etc/crio/crio.conf.d/00-crio.conf
{% endif %}

systemctl restart crio
systemctl enable crio
