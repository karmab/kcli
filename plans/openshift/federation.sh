echo function contextswitch { >> /root/.bashrc
echo oc config use-context \$1 >> /root/.bashrc
echo } >> /root/.bashrc
oc login --insecure-skip-tls-verify=true -u admin -p admin https://origin1.default:8443
oc config rename-context `oc config current-context` cluster1
oc login --insecure-skip-tls-verify=true -u admin -p admin https://origin2.default:8443
oc config rename-context `oc config current-context` cluster2
curl -LOs https://github.com/kubernetes-sigs/federation-v2/releases/download/v0.0.2/kubefed2.tar.gz
tar xzf kubefed2.tar.gz -C /usr/local/bin
rm -f kubefed2.tar.gz
yum -y install git
git clone https://github.com/openshift/federation-dev.git
cd federation-dev
oc create clusterrolebinding federation-admin --clusterrole="cluster-admin" --serviceaccount="federation-system:default"
oc create -f cluster-registry.yaml
oc create -f federation.yaml
oc project federation-system
oc create -n federation-system -f federatedtypes/
kubefed2 join cluster1 --host-cluster-context cluster1 --add-to-registry --v=2
kubefed2 join cluster2 --host-cluster-context cluster1 --add-to-registry --v=2
