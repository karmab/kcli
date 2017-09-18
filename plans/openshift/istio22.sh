export version="0.2.2"
export checkout="9ac006e070b88dba19ad26048c1010675d77e321"
export project="istio-system"

git clone https://github.com/istio/istio.git
cd istio
git checkout $checkout
oc login -u system:admin
oc new-project $project
oc adm policy add-scc-to-user anyuid -z default
oc adm policy add-scc-to-user privileged -z default
oc adm policy add-cluster-role-to-user cluster-admin -z default
oc adm policy add-cluster-role-to-user cluster-admin -z istio-pilot-service-account
oc adm policy add-cluster-role-to-user cluster-admin -z istio-ingress-service-account
oc adm policy add-cluster-role-to-user cluster-admin -z istio-egress-service-account
oc adm policy add-cluster-role-to-user cluster-admin -z istio-mixer-service-account
oc adm policy add-scc-to-user anyuid -z istio-ingress-service-account
oc adm policy add-scc-to-user privileged -z istio-ingress-service-account
oc adm policy add-scc-to-user anyuid -z istio-egress-service-account
oc adm policy add-scc-to-user privileged -z istio-egress-service-account
oc adm policy add-scc-to-user anyuid -z istio-pilot-service-account
oc adm policy add-scc-to-user privileged -z istio-pilot-service-account
oc create -f install/kubernetes/istio-rbac-beta.yaml
oc create -f install/kubernetes/istio.yaml
oc expose svc istio-ingress
sleep 20
oc apply -f install/kubernetes/addons/prometheus.yaml
oc apply -f install/kubernetes/addons/grafana.yaml
oc apply -f install/kubernetes/addons/servicegraph.yaml
oc expose svc servicegraph
oc expose svc grafana
curl -LO https://github.com/istio/istio/releases/download/$version/istio-$version-linux.tar.gz
tar zxvf istio-$version-linux.tar.gz
sudo mv istio-$version/bin/istioctl /usr/bin
sudo chmod u+x /usr/bin/istioctl
sleep 20
source istio.VERSION
oc apply -f <(istioctl kube-inject --hub $PILOT_HUB --tag $PILOT_TAG -f samples/apps/bookinfo/bookinfo.yaml -n myproject)
oc expose svc productpage
