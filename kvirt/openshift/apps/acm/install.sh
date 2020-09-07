oc create -f install.yml
sleep 10
oc wait --for=condition=Ready pod -l name=multiclusterhub-operator -n open-cluster-management
oc create -f cr.yml

# Enabling Bare metal consoles
oc -n open-cluster-management patch deploy console-header -p '{"spec":{"template":{"spec":{"containers":[{"name":"console-header","env":
[{"name": "featureFlags_baremetal","value":"true"}]}]}}}}'
DEPLOY_NAME=`oc -n open-cluster-management get deploy -o name | grep consoleui`
oc -n open-cluster-management patch ${DEPLOY_NAME} -p '{"spec":{"template":{"spec":{"containers":[{"name":"hcm-ui","env":
[{"name": "featureFlags_baremetal","value":"true"}]}]}}}}'
