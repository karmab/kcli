#!/usr/bin/env bash

# set global variable
CIDR="10.244.0.0/16"

{% if config_type in ['aws', 'gcp', 'ibm'] %}
API_IP={{ "api.%s.%s" % (cluster, domain) }}
{% elif sslip|default(False) %}
API_IP={{ "api.%s.sslip.io" % api_ip.replace('.', '-').replace(':', '-') }}
{% else %}
API_IP={{ api_ip }}
{% endif %}

DOMAIN={{ domain }}

# initialize cluster
CERTKEY={{ cert_key }}
TOKEN={{ token }}
kubeadm init --control-plane-endpoint "${API_IP}:6443" --pod-network-cidr $CIDR --certificate-key $CERTKEY --upload-certs {{ '--image-repository public.ecr.aws/eks-distro/kubernetes --kubernetes-version $EKSD_API_VERSION' if eksd else '' }} --token $TOKEN --token-ttl 0

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
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
{% elif sdn == 'weavenet' %}
kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=`kubectl version | base64 | tr -d '\n'`"
{% elif sdn == 'calico' %}
CALICO_VERSION={{ 'projectcalico/calico'|github_version(calico_version) }}
curl -L https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml > /root/tigera-operator.yaml
curl -L https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/custom-resources.yaml > /root/tigera-custom-resources.yaml
sed -i "s@192.168.0.0/16@$CIDR@" /root/tigera-custom-resources.yaml
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
cilium install
{% endif %}
{% endif %}

# config cluster credentials
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config

{% if ingress %}
# (addon) install Ingress Controller
{% if ingress_method == 'nginx' %}
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/{{ 'cloud' if metallb else 'baremetal' }}/deploy.yaml
{% endif %}
{% endif %}

{% if policy_as_code %}
# (addon) install Policy-as-Code (PaC) Controller
{% if policy_as_code_method == 'gatekeeper' %}
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
{% elif policy_as_code_method == 'kyverno' %}
kubectl apply -f https://raw.githubusercontent.com/kyverno/kyverno/main/definitions/release/install.yaml
{% endif %}
{% endif %}

{% if autolabel %}
# (addon) install Autolabeler
kubectl apply -f https://raw.githubusercontent.com/karmab/autolabeller/main/autorules.yml
{% endif %}

{% if registry %}
# (addon) install Registry
mkdir -p /opt/registry/{auth,certs,data,conf}
REGISTRY_NAME="api.{{ cluster }}.{{ domain }}"
REGISTRY_USER={{ registry_user }}
REGISTRY_PASSWORD={{ registry_password }}
openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 365 -out /opt/registry/certs/domain.crt -subj "/C=US/ST=Madrid/L=San Bernardo/O=Karmalabs/OU=Guitar/CN=$REGISTRY_NAME" -addext "subjectAltName=DNS:$REGISTRY_NAME"
cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract
htpasswd -bBc /opt/registry/auth/htpasswd $REGISTRY_USER $REGISTRY_PASSWORD
kubectl apply -f /root/registry.yml
cp /opt/registry/certs/domain.{key,crt} /var/www/html
cp /opt/registry/auth/htpasswd /var/www/html
{% endif %}

{% if multus %}
/root/multus.sh
{% endif %}
{% if nfs %}
/root/nfs.sh
{% endif %}

{% if metallb %}
# (addon) install Metal Load Balancer (LB)
cd /root
bash /root/metallb.sh
{% endif %}
