POD_CIDR={{ cluster_network_ipv6 if ipv6 else cluster_network_ipv4 }}
# install Container Network Interface (CNI)
{% if sdn == 'flannel' %}
{% if ipv6 %}
curl -Ls http://{{ disconnected_url.split(':')[0] }}:8080/sdn.yml > /root/sdn.yml
sed -i "s@10.244.0.0/16@$POD_CIDR@" /root/sdn.yml
sed -i 's/"Network":/"IPV6Network":/' /root/sdn.yml
sed -i '/"IPV6Network":/a\      "EnableIPV4": false,\n      "EnableIPV6": true,' /root/sdn.yml
{% else %}
FLANNEL_VERSION={{ 'flannel-io/flannel'|github_version(flannel_version) }}
curl -Ls https://raw.githubusercontent.com/flannel-io/flannel/$FLANNEL_VERSION/Documentation/kube-flannel.yml > /root/sdn.yml
sed -i "s@10.244.0.0/16@$POD_CIDR@" /root/sdn.yml
{% if dualstack %}
sed -i '/"Network":/a\      "IPV6Network": "{{ cluster_network_ipv6 }}",\n      "EnableIPV4": true,\n      "EnableIPV6": true,' /root/sdn.yml
{% endif %}
{% endif %}
kubectl apply -f /root/sdn.yml
{% elif sdn == 'calico' %}
CALICO_VERSION={{ 'projectcalico/calico'|github_version(calico_version) }}
curl -L https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml > /root/tigera-operator.yaml
curl -L https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/custom-resources.yaml > /root/tigera-custom-resources.yaml
sed -i "s@192.168.0.0/16@$POD_CIDR@" /root/tigera-custom-resources.yaml
kubectl create -f /root/tigera-operator.yaml
sleep 10
kubectl create -f /root/tigera-custom-resources.yaml
{% elif sdn == 'cilium' %}
curl -LO https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm -f cilium-linux-amd64.tar.gz
CILIUM_VERSION={{ "--version %s" % sdn_version if sdn_version != None else "" }}
CILIUM_REGISTRY={{ "--helm-set=image.repository=%s/cilium/cilium --helm-set image.useDigest=false --helm-set=envoy.image.repository=%s/cilium/cilium-envoy --helm-set=envoy.image.tag=latest --helm-set=envoy.image.useDigest=false --helm-set=operator.image.repository=%s/cilium/operator --helm-set=operator.image.useDigest=false" % (disconnected_url, disconnected_url, disconnected_url) if disconnected_url is defined else "" }}
CILIUM_IPV6={{ "--helm-set=ipv6.enabled=true" if ipv6 or dualstack else "" }}
cilium install $CILIUM_VERSION $CILIUM_REGISTRY $CILIUM_IPV6
{% endif %}
