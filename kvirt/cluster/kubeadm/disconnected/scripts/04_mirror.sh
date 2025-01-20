VERSION="$(curl -L -s https://dl.k8s.io/release/stable.txt)"
# Ensure the version is in the format v<major>.<minor> regardless of the source
VERSION=$(echo "v${VERSION#v}" | cut -d. -f1,2)
echo $VERSION > /root/version.txt

echo """[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/$VERSION/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/$VERSION/rpm/repodata/repomd.xml.key""" >/etc/yum.repos.d/kubernetes.repo

export PATH=/root/bin:$PATH

# KUBEADM
IMAGES_VERSION=$(echo $VERSION| sed 's/^v/stable-/')
yum -y install kubeadm
for image in $(kubeadm config images list --kubernetes-version $IMAGES_VERSION) ; do sync_image.sh $image ; done

cd /root
# SDN
{% if sdn != None %}
{% if sdn == 'flannel' %}
FLANNEL_VERSION={{ 'flannel-io/flannel'|github_version(flannel_version) }}
curl -Ls https://raw.githubusercontent.com/flannel-io/flannel/$FLANNEL_VERSION/Documentation/kube-flannel.yml > sdn.yml
{% elif sdn == 'weavenet' %}
curl -Ls -f "https://cloud.weave.works/k8s/net?k8s-version=`kubectl version | base64 | tr -d '\n'`" > sdn.yml
{% elif sdn == 'calico' %}
CALICO_VERSION={{ 'projectcalico/calico'|github_version(calico_version) }}
curl -Ls https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml > sdn.yml
{% elif sdn == 'canal' %}
curl -Ls https://docs.projectcalico.org/v3.1/getting-started/kubernetes/installation/hosted/canal/canal.yaml > sdn.yml
{% elif sdn == 'romana' %}
curl -Ls https://raw.githubusercontent.com/romana/romana/master/containerize/specs/romana-kubeadm.yml > sdn.yml
{% elif sdn == 'cilium' %}
curl -LO https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm -f cilium-linux-amd64.tar.gz
CILIUM_VERSION={{ sdn_version or "$(/usr/local/bin/cilium install --list-versions | grep default | cut -d' ' -f1)" }}
CILIUM_IMAGES="quay.io/cilium/cilium quay.io/cilium/operator-generic quay.io/cilium/operator quay.io/cilium/clustermesh-apiserver quay.io/cilium/hubble-relay quay.io/cilium/docker-plugin"
for image in $CILIUM_IMAGES ; do echo image: $image:$CILIUM_VERSION >> sdn.yml ; done
echo image: quay.io/cilium/cilium-envoy:latest >> sdn.yml
{% endif %}

sdn_images=$(grep image: sdn.yml | sed 's/image: //' | sed 's/@.*//' | sort -u)
for image in $sdn_images ; do sync_image.sh $image ; done
{% endif %}

#NGINX
curl -Lk https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/{{ 'cloud' if metallb|default(False) else 'baremetal' }}/deploy.yaml > ingress.yml
nginx_images=$(grep image: ingress.yml | sed 's/.* image: //' | sed 's/@.*//' | sort -u)
for image in $nginx_images ; do sync_image.sh $image ; done

{% set kcli_images = ['quay.io/karmab/autolabeller:multi', 'ghcr.io/k8snetworkplumbingwg/multus-cni:snapshot-thick'] %}
{% for image in kcli_images + extra_images|default([]) %}
sync_image.sh {{ image }}
{% endfor %}
