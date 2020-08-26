set -euo pipefail
export ARGOCD_VERSION={{ 'argoproj/argo-cd' | githubversion(argocd_version) }}
{%- if argocd_ingress %}
kubectl delete -f ingress.yml
{%- endif %}
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml
kubectl delete namespace argocd
