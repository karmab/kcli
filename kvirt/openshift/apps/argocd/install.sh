export ARGOCD_VERSION={{ 'argoproj/argo-cd' | githubversion(argocd_version) }}
echo "Deploying Argocd $ARGOCD_VERSION"
oc create namespace argocd
oc -n argocd apply -f https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml
ARGOCD_PASSWORD=$(oc -n argocd get pod -l "app.kubernetes.io/name=argocd-server" -o jsonpath='{.items[*].metadata.name}')
echo Use Initial Password $ARGOCD_PASSWORD
PATCH='{"spec":{"template":{"spec":{"$setElementOrder/containers":[{"name":"argocd-server"}],"containers":[{"command":["argocd-server","--insecure","--staticassets","/shared/app"],"name":"argocd-server"}]}}}}'
oc -n argocd patch deployment argocd-server -p $PATCH
oc -n argocd create route edge argocd-server --service=argocd-server --port=http --insecure-policy=Redirect
echo argo ui available at https://$(oc get route -n argocd argocd-server -o=jsonpath='{ .spec.host }')
echo Use Initial Password $ARGOCD_PASSWORD
