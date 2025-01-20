#!/usr/bin/env bash

POD_CIDR={{ cluster_network_ipv4 }}
SERVICE_CIDR={{ service_network_ipv4 }}

{% if config_type in ['aws', 'gcp', 'ibm'] %}
API_IP={{ "api.%s.%s" % (cluster, domain) }}
echo $(hostname -I) api.{{ cluster }}.{{ domain }} >> /etc/hosts
{% elif sslip|default(False) %}
API_IP={{ "api.%s.sslip.io" % api_ip.replace('.', '-').replace(':', '-') }}
{% else %}
API_IP={{ api_ip }}
{% endif %}

DOMAIN={{ domain }}

# initialize cluster
CERTKEY={{ cert_key }}
TOKEN={{ token }}
K8S_VERSION='{{ "--kubernetes-version %s" % minor_version if minor_version is defined else "" }}'
REGISTRY='{{ "--image-repository %s" % disconnected_url if disconnected_url != None else "" }}'
kubeadm init --control-plane-endpoint "${API_IP}:6443" --pod-network-cidr $POD_CIDR --service-cidr $SERVICE_CIDR --certificate-key $CERTKEY --upload-certs --token $TOKEN --token-ttl 0 --apiserver-cert-extra-sans ${API_IP} $K8S_VERSION $REGISTRY

# config cluster credentials
cp /etc/kubernetes/admin.conf /root/kubeconfig
chown root:root /root/kubeconfig
export KUBECONFIG=/root/kubeconfig
echo "export KUBECONFIG=/root/kubeconfig" >> /root/.bashrc

{% if workers == 0 %}
# untaint ctlplane nodes when there are no workers
kubectl taint nodes --all node-role.kubernetes.io/master-
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
{% endif %}

{% if sdn != None %}
# install Container Network Interface (CNI)
{% if sdn == 'flannel' %}
FLANNEL_VERSION={{ 'flannel-io/flannel'|github_version(flannel_version) }}
curl -Ls https://raw.githubusercontent.com/flannel-io/flannel/$FLANNEL_VERSION/Documentation/kube-flannel.yml | sed "s@10.244.0.0/16@$POD_CIDR@" | kubectl apply -f -
{% elif sdn == 'weavenet' %}
kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=`kubectl version | base64 | tr -d '\n'`"
{% elif sdn == 'calico' %}
CALICO_VERSION={{ 'projectcalico/calico'|github_version(calico_version) }}
curl -L https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml > /root/tigera-operator.yaml
curl -L https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/custom-resources.yaml > /root/tigera-custom-resources.yaml
sed -i "s@192.168.0.0/16@$POD_CIDR@" /root/tigera-custom-resources.yaml
kubectl create -f /root/tigera-operator.yaml
kubectl create -f /root/tigera-custom-resources.yaml
{% elif sdn == 'canal' %}
kubectl apply -f https://docs.projectcalico.org/v3.1/getting-started/kubernetes/installation/hosted/canal/rbac.yaml
kubectl apply -f https://docs.projectcalico.org/v3.1/getting-started/kubernetes/installation/hosted/canal/canal.yaml
{% elif sdn == 'romana' %}
kubectl apply -f https://raw.githubusercontent.com/romana/romana/master/containerize/specs/romana-kubeadm.yml
{% elif sdn == 'cilium' %}
curl -LO https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm -f cilium-linux-amd64.tar.gz
CILIUM_VERSION='{{ "--version %s" % sdn_version if sdn_version != None else "" }}'
CILIUM_REGISTRY='{{ "--helm-set=image.repository=%s/cilium/cilium --set image.useDigest=false --helm-set=envoy.image.repository=%s/cilium/cilium-envoy --helm-set=envoy.image.tag=latest --helm-set=envoy.image.useDigest=false --helm-set=operator.image.repository=%s/cilium/operator --helm-set=operator.image.useDigest=false" % (disconnected_url, disconnected_url, disconnected_url) if disconnected_url is defined else "" }}'
cilium install $CILIUM_VERSION $CILIUM_REGISTRY
{% endif %}
{% endif %}

# config cluster credentials
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config

{% if multus %}
kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/master/deployments/multus-daemonset-thick.yml
{% endif %}

{% if nfs %}
/root/nfs.sh
{% endif %}

{% if registry %}
kubectl create -f /root/registry.yml
echo """[[registry]]
location=\"{{ api_ip }}:5000\"
insecure=true""" > /etc/containers/registries.conf.d/003-{{ cluster }}.conf
{% endif %}
