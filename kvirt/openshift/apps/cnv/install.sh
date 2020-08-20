oc create -f install.yml
oc wait --for=condition=Ready pod -l name=hyperconverged-cluster-operator -n openshift-cnv
oc create -f cr.yml
