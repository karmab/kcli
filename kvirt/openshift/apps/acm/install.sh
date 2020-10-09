oc create -f install.yml
{{ 'multiclusterhub'| waitcrd }}
oc create -f cr.yml

# Enabling Bare metal consoles
oc -n open-cluster-management patch deploy console-header -p '{"spec":{"template":{"spec":{"containers":[{"name":"console-header","env":[{"name": "featureFlags_baremetal","value":"true"}]}]}}}}'
DEPLOY_NAME=$(oc -n open-cluster-management get deploy -o name | grep consoleui)
oc -n open-cluster-management patch ${DEPLOY_NAME} -p '{"spec":{"template":{"spec":{"containers":[{"name":"hcm-ui","env":[{"name": "featureFlags_baremetal","value":"true"}]}]}}}}'
