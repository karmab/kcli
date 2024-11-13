PULL_SECRET={{ pull_secret if pull_secret.startswith('/') else cwd + '/' + pull_secret }}
oc create -n open-cluster-management secret generic open-cluster-management-image-pull-credentials --from-file=.dockerconfigjson=${PULL_SECRET} --type=kubernetes.io/dockerconfigjson
{% if acm_deploy_baremetal_console %}
STATUS="Installing"
while [ "${STATUS}" != "Running" ] ; do
 STATUS=$(oc -n open-cluster-management get multiclusterhub multiclusterhub -o jsonpath='{.status.phase}')
 sleep 5
done
# Enabling Bare metal consoles
oc -n open-cluster-management patch deploy console-header -p '{"spec":{"template":{"spec":{"containers":[{"name":"console-header","env":[{"name": "featureFlags_baremetal","value":"true"}]}]}}}}'
DEPLOY_NAME=$(oc -n open-cluster-management get deploy -o name | grep consoleui)
oc -n open-cluster-management patch ${DEPLOY_NAME} -p '{"spec":{"template":{"spec":{"containers":[{"name":"hcm-ui","env":[{"name": "featureFlags_baremetal","value":"true"}]}]}}}}'
{% endif %}

{% if assisted %}
bash assisted-service.sh
{% endif %}

{% if not acm_hypershift %}
oc -n open-cluster-management patch multiclusterhub multiclusterhub --type=merge -p '{"spec":{"overrides":{"components":[{"name":"hypershift","enabled": false}]}}}'
{% endif %}

{% if acm_siteconfig %}
oc -n open-cluster-management patch multiclusterhub multiclusterhub --type=merge -p '{"spec":{"overrides":{"components":[{"name":"siteconfig","enabled": true}]}}}'
{% endif %}
