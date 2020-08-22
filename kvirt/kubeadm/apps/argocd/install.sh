set -euo pipefail
export ARGOCD_VERSION={{ 'argoproj/argo-cd' | githubversion(argocd_version) }}
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml
echo Giving sometime for ingress controller to get ready...
sleep 30
kubectl apply -f ingress.yml
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
ARGO_PASSWORD=$(kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server -o name | cut -d'/' -f 2)
echo argo ui available at http://$(kubectl get ingress -n argocd argocd-server-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo Use Initial Password $ARGO_PASSWORD
