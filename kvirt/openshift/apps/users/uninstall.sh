oc patch oauth cluster -p='[{"op": "remove", "path": "/spec/identityProviders"}]'  --type=json
oc delete secret htpass-secret -n openshift-config
