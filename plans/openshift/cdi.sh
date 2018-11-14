oc new-project golden
oc adm policy add-scc-to-user privileged system:serviceaccount:golden:default
oc adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:golden:cdi-apiserver
oc create -f /root/cdi-controller.yaml
oc expose svc cdi-uploadproxy -n golden
