#!/usr/bin/env bash

CLUSTER={{ cluster }}
DOMAIN={{ domain }}

echo $(hostname -I) api.$CLUSTER.$DOMAIN >> /etc/hosts

kubeadm init --config=/root/config.yaml --upload-certs

# config cluster credentials
cp /etc/kubernetes/admin.conf /root/kubeconfig
chown root:root /root/kubeconfig
export KUBECONFIG=/root/kubeconfig
echo "export KUBECONFIG=/root/kubeconfig" >> /root/.bashrc

{% if ctlplane_schedulable or workers == 0 %}
# untaint ctlplane nodes when there are no workers
kubectl taint nodes --all node-role.kubernetes.io/master-
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
{% endif %}

{% if sdn != None %}
bash /root/sdn.sh
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
