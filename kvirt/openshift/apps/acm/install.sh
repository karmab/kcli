oc create -f install.yml
sleep 10
oc wait --for=condition=Ready pod -l name=multiclusterhub-operator -n open-cluster-management
oc create -f cr.yml
