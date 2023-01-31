{% set eksd_version = 'aws/eks-distro'|github_version(eksd_version, tag_mode=True)|replace('v', '') %}
{% set split = eksd_version.split('-') %}
{% set kubernetes_version = split[0] + '-' + split[1] %}
curl https://distro.eks.amazonaws.com/kubernetes-{{ kubernetes_version }}/kubernetes-{{ eksd_version }}.yaml > /root/eksd.yaml

{% if engine == 'docker' %}
DOCKER="docker"
{% elif engine == 'crio' %}
DOCKER="crictl"
{% else %}
DOCKER="ctr images"
{% endif %}

PAUSE=$(grep public.ecr.aws/eks-distro/kubernetes/pause /root/eksd.yaml | sed 's/uri: //')
EKSD_API_VERSION=$(echo $PAUSE | awk -F':' '{ print $NF }')
COREDNS=$(grep public.ecr.aws/eks-distro/coredns /root/eksd.yaml | sed 's/uri: //')
ETCD=$(grep public.ecr.aws/eks-distro/etcd-io /root/eksd.yaml | sed 's/uri: //')
$DOCKER pull $PAUSE
$DOCKER pull $COREDNS
$DOCKER pull $ETCD

kubeadm config images list --image-repository public.ecr.aws/eks-distro/kubernetes --kubernetes-version $EKSD_API_VERSION > /tmp/images.txt
PAUSE2=$(grep pause /tmp/images.txt)
COREDNS2=$(grep coredns /tmp/images.txt)
ETCD2=$(grep etcd /tmp/images.txt)

${TAG:-$DOCKER} tag $PAUSE $PAUSE2
${TAG:-$DOCKER} tag $COREDNS $COREDNS2
${TAG:-$DOCKER} tag $ETCD $ETCD2
