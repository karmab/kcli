#!/usr/bin/env bash

CLUSTER={{ cluster }}
DOMAIN={{ domain }}
POD_CIDR={{ cluster_network_ipv4 }}

echo $(hostname -I) api.$CLUSTER.$DOMAIN >> /etc/hosts

kubeadm init --config=/root/config.yaml --upload-certs

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
sleep 10
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
{% endif %}
