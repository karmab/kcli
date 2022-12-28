API_IP={{ "api.%s.%s" % (cluster, domain) if config_type in ['aws', 'gcp', 'ibm'] else api_ip }}
cp /root/admin.conf /etc/kubernetes/admin.conf 
bash /root/ctlplanecmd.sh | tee /root/$(hostname).log 2>&1
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config
{% if registry %}
mkdir -p /opt/registry/{auth,certs,data,conf}
curl -Lk http://${API_IP}/domain.crt > /opt/registry/certs/domain.crt
curl -Lk http://${API_IP}/domain.key > /opt/registry/certs/domain.key
curl -Lk http://${API_IP}/htpasswd > /opt/registry/auth/htpasswd
cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract
{% endif %}
