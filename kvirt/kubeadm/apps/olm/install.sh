export OLM_VERSION={{ 'operator-framework/operator-lifecycle-manager' | githubversion(olm_version) }}
kubectl apply -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/$OLM_VERSION/crds.yaml
kubectl apply -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/$OLM_VERSION/olm.yaml
