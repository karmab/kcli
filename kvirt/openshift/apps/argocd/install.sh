oc create -f install.yml
sleep 20
oc create -f cr.yml
sleep 20
ARGOCD_PASSWORD=$(oc -n argocd get pod -l "app.kubernetes.io/name=argocd-server" -o jsonpath='{.items[*].metadata.name}')
oc -n argocd create route passthrough argocd --service=argocd-server --port=https --insecure-policy=Redirect
ARGOCD_HOST=$(oc get route -n argocd argocd-server -o=jsonpath='{ .spec.host }')
echo argo ui available at https://$ARGOCD_HOST
echo Use Openshift Credentials or admin/$ARGOCD_PASSWORD
{% if argocd_download_cli %}
  OS="linux"
  [ -d /Users ] && OS="darwin"
  curl -Lk https://github.com/argoproj/argo-cd/releases/download/$ARGOCD_VERSION/argocd-$OS-amd64 > {{ cwd }}/argocd
  chmod u+x {{ cwd }}/argocd
  {% if argocd_password != None %}
    export ARGOCD_VERSION={{ 'argoproj/argo-cd' | githubversion(argocd_version| default('latest')) }}
    sleep 20
    oc patch -n argocd secret argocd-secret  -p '{"data": {"admin.password": null, "admin.passwordMtime": null}}'
    oc delete pod -n argocd -l app.kubernetes.io/name=argocd-server
    oc wait -n argocd $(oc get pod -n argocd -l app.kubernetes.io/name=argocd-server -o name) --for=condition=Ready
    ARGOCD_PASSWORD=$(oc -n argocd get pod -l "app.kubernetes.io/name=argocd-server" -o jsonpath='{.items[*].metadata.name}')
    {{ cwd }}/argocd login argocd-server-argocd.apps.{ cluster }}.{{ domain }} --grpc-web --username admin --password $ARGOCD_PASSWORD --insecure
    {{ cwd }}/argocd account update-password --current-password $ARGOCD_PASSWORD --new-password {{ argocd_password }} --grpc-web
    echo Updated admin password to {{ argocd_password }}
  {% endif %}
{% endif %}
