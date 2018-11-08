oc adm policy add-scc-to-user anyuid -z build-controller -n knative-build
oc adm policy add-scc-to-user anyuid -z controller -n knative-serving
oc adm policy add-scc-to-user anyuid -z autoscaler -n knative-serving
oc adm policy add-scc-to-user anyuid -z kube-state-metrics -n knative-monitoring
oc adm policy add-scc-to-user anyuid -z node-exporter -n knative-monitoring
oc adm policy add-scc-to-user anyuid -z prometheus-system -n knative-monitoring
oc adm policy add-cluster-role-to-user cluster-admin -z build-controller -n knative-build
oc adm policy add-cluster-role-to-user cluster-admin -z controller -n knative-serving
curl -L https://storage.googleapis.com/knative-releases/serving/latest/release-lite.yaml | sed 's/LoadBalancer/NodePort/' | oc apply -f -
