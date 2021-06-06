export DASHBOARD_VERSION={{ 'kubernetes/dashboard' | github_version(dashboard_version) }}
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/$DASHBOARD_VERSION/aio/deploy/recommended.yaml

if kubectl get ns metallb-system >/dev/null 2>&1 ; then
  kubectl patch svc -n kubernetes-dashboard kubernetes-dashboard -p '{"spec": {"type": "LoadBalancer"}}'
  sleep 10
  DASHBOARD_URL=$(kubectl get svc -n kubernetes-dashboard kubernetes-dashboard  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
#elif kubectl get ns ingress-nginx >/dev/null 2>&1 ; then
#  kubectl create -f ingress.yml
#  sleep 10
#  DASHBOARD_URL=$(kubectl get ingress -n kubernetes-dashboard ingress-k8s-dashboard-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/dashboard
else
  kubectl patch svc -n kubernetes-dashboard kubernetes-dashboard -p '{"spec": {"type": "NodePort"}}'
  sleep 10
  NODE=$(kubectl get node -o wide --no-headers | head -1 | awk '{print $6}')
  PORT=$(kubectl get svc -n kubernetes-dashboard  kubernetes-dashboard -o jsonpath='{.spec.ports[0].nodePort}')
  DASHBOARD_URL=$NODE:$PORT
fi

{% if dashboard_admin %}
kubectl replace -f admin.yml
{% endif %}

TOKEN=$(kubectl -n kubernetes-dashboard describe secret $(kubectl -n kubernetes-dashboard get secret | grep admin-user | awk '{print $1}') |grep 'token:' | awk -F: '{print $2}' | xargs)
echo "Login to dashboard at https://$DASHBOARD_URL with token $TOKEN"
