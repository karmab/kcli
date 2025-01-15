{% if registry %}
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
{% endif %}
systemctl enable --now containerd || systemctl daemon-reload
systemctl restart containerd
