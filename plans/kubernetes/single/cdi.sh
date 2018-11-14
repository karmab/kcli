kubectl create ns golden
kubectl create clusterrolebinding cdi --clusterrole=edit --user=system:serviceaccount:golden:default
kubectl create clusterrolebinding cdi-apiserver --clusterrole=cluster-admin --user=system:serviceaccount:golden:cdi-apiserver
kubectl create -f /root/cdi-controller.yaml
kubectl expose svc cdi-uploadproxy -n golden
