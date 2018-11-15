# kubectl create -f https://raw.githubusercontent.com/kubernetes/dashboard/master/src/deploy/recommended/kubernetes-dashboard.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/master/src/deploy/alternative/kubernetes-dashboard.yaml
kubectl create clusterrolebinding kubernetes-dashboard-head --clusterrole=cluster-admin --user=system:serviceaccount:kube-system:kubernetes-dashboard
