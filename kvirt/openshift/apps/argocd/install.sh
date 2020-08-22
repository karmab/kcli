export ARGOCD_VERSION={{ 'argoproj/argo-cd' | githubversion(argocd_version| default('latest')) }}
oc create namespace argocd
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
echo Use Openshift Credentials or Initial Password $ARGOCD_PASSWORD
