FED="{{ federation_version }}"
yum -y install git bind-utils wget
echo function contextswitch { >> /root/.bashrc
echo oc config use-context \$1 >> /root/.bashrc
echo } >> /root/.bashrc
echo alias contextlist=\"oc config get-contexts\" >> /root/.bashrc
echo alias oc1=\"oc --context=cluster1\" >> /root/.bashrc
echo alias oc2=\"oc --context=cluster2\" >> /root/.bashrc
echo alias oclogin=\"oc config use cluster2 && oc login -u admin -p admin ; oc config use cluster1 && oc login -u admin -p admin\" >> /root/.bashrc
export CLUSTER1=`dig +short {{ cluster1 }}.default`.xip.io
export CLUSTER2=`dig +short {{ cluster2 }}.default`.xip.io
sleep 120
oc login --insecure-skip-tls-verify=true -u admin -p admin https://$CLUSTER2:8443
oc config rename-context `oc config current-context` cluster2
oc login --insecure-skip-tls-verify=true -u admin -p admin https://$CLUSTER1:8443
oc config rename-context `oc config current-context` cluster1
if [ "$FED" == "canary" ] ; then
  oc create ns federation-system
  oc create ns kube-multicluster-public
  oc create clusterrolebinding federation-admin --clusterrole=cluster-admin --serviceaccount="federation-system:default"
  wget https://dl.google.com/go/go{{ go_version }}.linux-amd64.tar.gz
  tar -C /usr/local -xzf go{{ go_version }}.linux-amd64.tar.gz
  export GOPATH=/root/go
  echo export GOPATH=/root/go >> /root/.bashrc
  mkdir -p ${GOPATH}/{bin,pkg,src}
  mkdir -p ${GOPATH}/src/github.com/kubernetes-sigs
  cd ${GOPATH}/src/github.com/kubernetes-sigs
  git clone https://github.com/kubernetes-sigs/federation-v2.git
  cd federation-v2
  ./scripts/download-binaries.sh
  export PATH=${GOPATH}/src/github.com/kubernetes-sigs/federation-v2/bin:${PATH}:/usr/local/go/bin:${GOPATH}/bin
  echo export PATH=\${GOPATH}/src/github.com/kubernetes-sigs/federation-v2/bin:\${PATH}:/usr/local/go/bin:\${GOPATH}/bin >> /root/.bashrc
  make kubefed2
  INSTALL_YAML="hack/install.yaml"
  IMAGE_NAME="quay.io/kubernetes-multicluster/federation-v2:canary"
  INSTALL_YAML="${INSTALL_YAML}" IMAGE_NAME="${IMAGE_NAME}" scripts/generate-install-yaml.sh
  oc create -f ${INSTALL_YAML} -n federation-system
  oc apply --validate=false -f vendor/k8s.io/cluster-registry/cluster-registry-crd.yaml
  for filename in ./config/federatedirectives/*.yaml; do kubefed2 federate enable -f "${filename}" --federation-namespace=federation-system; done
else
  curl -LOs https://github.com/kubernetes-sigs/federation-v2/releases/download/$KUBEFED_VERSION/kubefed2.tar.gz
  tar xzf kubefed2.tar.gz -C /usr/local/bin
  rm -f kubefed2.tar.gz
  git clone https://github.com/openshift/federation-dev.git /root/federation-dev
  cd /root/federation-dev
  oc create clusterrolebinding federation-admin --clusterrole="cluster-admin" --serviceaccount="federation-system:default"
  oc create -f cluster-registry.yaml
  oc create -f federation.yaml
  oc project federation-system
  oc create -n federation-system -f federatedtypes/
  sleep 60
fi
kubefed2 join cluster1 --host-cluster-context cluster1 --add-to-registry --v=2
kubefed2 join cluster2 --host-cluster-context cluster1 --add-to-registry --v=2
