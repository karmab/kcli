sed -i /requiretty/d /etc/sudoers
export KUBECONFIG=/root/.kube/config
git clone https://github.com/istio/istio.git /root/istio
cd /root/istio
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
sleep 60
oc apply -f install/kubernetes/addons/prometheus.yaml
oc apply -f install/kubernetes/addons/grafana.yaml
oc apply -f install/kubernetes/addons/servicegraph.yaml
oc expose svc servicegraph
oc expose svc grafana
sleep 60
curl -LO https://github.com/istio/istio/releases/download/$version/istio-$version-linux.tar.gz
tar zxvf istio-$version-linux.tar.gz
sudo mv istio-$version/bin/istioctl /usr/bin
sudo chmod u+x /usr/bin/istioctl
. istio.VERSION
oc apply -f <(istioctl kube-inject --hub $PILOT_HUB --tag $PILOT_TAG -f samples/apps/bookinfo/bookinfo.yaml -n $project)
oc expose svc productpage
oc new-project istio-config-default
oc create -f https://raw.githubusercontent.com/istio/istio/master/samples/apps/bookinfo/rules/mixer-rule-standard-metrics.yaml
