export ARGOCD_VERSION={{ 'argoproj/argo-cd' | githubversion(argocd_version| default('latest')) }}
oc create namespace argocd
oc adm policy add-scc-to-user anyuid system:serviceaccount:argocd:default
oc -n argocd apply -f https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml
ARGOCD_PASSWORD=$(oc -n argocd get pod -l "app.kubernetes.io/name=argocd-server" -o jsonpath='{.items[*].metadata.name}')
PATCH='{"spec":{"template":{"spec":{"$setElementOrder/containers":[{"name":"argocd-server"}],"containers":[{"command":["argocd-server","--insecure","--staticassets","/shared/app"],"name":"argocd-server"}]}}}}'
oc -n argocd patch deployment argocd-server -p $PATCH
oc -n argocd create route edge argocd-server --service=argocd-server --port=http --insecure-policy=Redirect
ARGOCD_HOST=$(oc get route -n argocd argocd-server -o=jsonpath='{ .spec.host }')
oc patch serviceaccount -n argocd argocd-dex-server --type='json' -p="[{\"op\": \"add\", \"path\": \"/metadata/annotations/serviceaccounts.openshift.io~1oauth-redirecturi.argocd\", \"value\":\"https://$ARGOCD_HOST/api/dex/callback\"}]"
ARGOCD_SECRET=$(oc serviceaccounts get-token argocd-dex-server -n argocd)
sed "s/SECRET/$ARGOCD_SECRET/" configmap.yml | oc replace -f - -n argocd
echo argo ui available at https://$ARGOCD_HOST
echo Use Openshift Credentials or admin/$ARGOCD_PASSWORD
{% if argocd_download_cli %}
  OS="linux"
  [ -d /Users ] && OS="darwin"
  curl https://github.com/argoproj/argo-cd/releases/download/$ARGOCD_VERSION/argocd-$OS-amd64 > {{ cwd }}/argcod
  chmod u+x {{ cwd }}/argcod
  {% if argocd_password != None %}
    {{ cwd }}/argocd login argocd-server-argocd.apps.{ cluster }}.{{ domain }} --grpc-web --username admin --password $ARGOCD_PASSWORD --insecure
    {{ cwd }}/argocd account update-password --current-password $ARGOCD_PASSWORD --new-password {{ argocd_password }} --grpc-web
    echo Updated admin password to {{ argocd_password }}
  {% endif %}
{% endif %}
