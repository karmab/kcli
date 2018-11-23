sysctl vm.max_map_count=262144
echo vm.max_map_count = 262144 > /etc/sysctl.d/99-elasticsearch.conf 
oc new-project istio-operator
oc new-app -f https://raw.githubusercontent.com/Maistra/openshift-ansible/maistra-0.2.0-ocp-3.1.0-istio-1.0.2/istio/istio_community_operator_template.yaml --param=OPENSHIFT_ISTIO_MASTER_PUBLIC_URL=https://$DNS:8443
oc create -f /root/istio_knative.yml
