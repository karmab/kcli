export project="istio-system"
sed -i /requiretty/d /etc/sudoers
export KUBECONFIG=/root/.kube/config
cd /root
curl -L https://git.io/getLatestIstio | sh -
ISTIO=`ls | grep istio`
export PATH="$PATH:~/$ISTIO/bin"
echo export PATH="$PATH:~/$ISTIO/bin" >> /root/.bashrc
cd $ISTIO
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
#oc create -f install/kubernetes/istio-rbac-beta.yaml
oc create -f install/kubernetes/istio.yaml
oc expose svc istio-ingress
sleep 90
oc apply -f install/kubernetes/addons/prometheus.yaml
oc apply -f install/kubernetes/addons/grafana.yaml
oc apply -f install/kubernetes/addons/servicegraph.yaml
oc create -f install/kubernetes/addons/zipkin.yaml
oc expose svc servicegraph
oc expose svc grafana
oc expose svc zipkin
sleep 90
[% if deploy_book_info is defined and deploy_book_info %]
oc new-project bookinfo
istioctl kube-inject -f samples/bookinfo/kube/bookinfo.yaml | oc apply -f -
oc expose svc productpage
oc new-project istio-config-default
[% endif %]
oc create -f https://raw.githubusercontent.com/istio/istio/master/samples/bookinfo/kube/mixer-rule-additional-telemetry.yaml
oc project istio-system
