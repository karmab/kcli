export DASHBOARD_VERSION={{ 'kubernetes/dashboard' | githubversion(dashboard_version) }}
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/$DASHBOARD_VERSION/aio/deploy/recommended.yaml
kubectl create -f ingress.yml
kubectl create -f user.yml
# kubectl patch svc -n kubernetes-dashboard kubernetes-dashboard -p '{"spec": {"type": "LoadBalancer"}}'
TOKEN=$(kubectl -n kubernetes-dashboard describe secret $(kubectl -n kubernetes-dashboard get secret | grep admin-user | awk '{print $1}') |grep 'token:' | awk -F: '{print $2}' | xargs)
DASHBOARD_URL=https://$(kubectl get ingress -n default ingress-k8s-dashboard-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/dashboard
echo "Login to dashboard at $DASHBOARD_URL with token $TOKEN"
