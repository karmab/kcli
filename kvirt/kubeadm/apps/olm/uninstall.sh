export OLM_VERSION={{ 'operator-framework/operator-lifecycle-manager' | githubversion(olm_version) }}
kubectl delete -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/$OLM_VERSION/olm.yaml
kubectl delete -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/$OLM_VERSION/crds.yaml
