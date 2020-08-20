oc create -f install.yml
sleep 10
oc wait --for=condition=Ready pod -l name=hyperconverged-cluster-operator -n openshift-cnv
oc create -f cr.yml
