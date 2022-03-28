KUBECONFIG_MICROSHIFT=kubeconfig
KUBECONFIG_ACM=kubeconfig.extra
cd /root
export CLUSTER_NAME={{ name }}
export KUBECONFIG=${KUBECONFIG_ACM}
oc new-project ${CLUSTER_NAME}
cat <<EOF | oc apply -f -
apiVersion: agent.open-cluster-management.io/v1
kind: KlusterletAddonConfig
metadata:
  name: ${CLUSTER_NAME}
  namespace: ${CLUSTER_NAME}
spec:
  clusterName: ${CLUSTER_NAME}
  clusterNamespace: ${CLUSTER_NAME}
  applicationManager:
    enabled: true
  certPolicyController:
    enabled: true
  clusterLabels:
    cloud: auto-detect
    vendor: auto-detect
  iamPolicyController:
    enabled: true
  policyController:
    enabled: true
  searchCollector:
    enabled: true
  version: 2.2.0
EOF
cat <<EOF | oc apply -f -
apiVersion: cluster.open-cluster-management.io/v1
kind: ManagedCluster
metadata:
  name: ${CLUSTER_NAME}
spec:
  hubAcceptsClient: true
EOF
sleep 10
IMPORT=`oc get -n ${CLUSTER_NAME} secret ${CLUSTER_NAME}-import -o jsonpath='{.data.import\.yaml}'`
CRDS=`oc get -n ${CLUSTER_NAME} secret ${CLUSTER_NAME}-import -o jsonpath='{.data.crds\.yaml}'`
export KUBECONFIG=${KUBECONFIG_MICROSHIFT}
while true ; do
 /usr/bin/kubectl get pod -A | grep router | grep -q Running && break
 echo waiting 10s for microshift to be ready
 sleep 10
done

test -f /root/auth.json && podman login registry.redhat.io --authfile /root/auth.json

oc new-project open-cluster-management-agent
oc create secret generic rhacm --from-file=.dockerconfigjson=auth.json --type=kubernetes.io/dockerconfigjson
oc create sa klusterlet
oc patch sa klusterlet -p '{"imagePullSecrets": [{"name": "rhacm"}]}' -n open-cluster-management-agent
oc create sa klusterlet-registration-sa 
oc patch sa klusterlet-registration-sa -p '{"imagePullSecrets": [{"name": "rhacm"}]}'
oc create sa klusterlet-work-sa
oc patch sa klusterlet-work-sa -p '{"imagePullSecrets": [{"name": "rhacm"}]}'

oc new-project open-cluster-management-agent-addon
oc create secret generic rhacm --from-file=.dockerconfigjson=auth.json --type=kubernetes.io/dockerconfigjson
oc create sa klusterlet-addon-operator
oc patch sa klusterlet-addon-operator -p '{"imagePullSecrets": [{"name": "rhacm"}]}'

oc project open-cluster-management-agent
echo $CRDS | base64 -d | oc apply -f -
echo $IMPORT | base64 -d | oc apply -f -

sleep 300
oc project open-cluster-management-agent-addon
for sa in klusterlet-addon-appmgr klusterlet-addon-certpolicyctrl klusterlet-addon-iampolicyctrl-sa klusterlet-addon-policyctrl klusterlet-addon-search klusterlet-addon-workmgr ; do
  oc patch sa $sa -p '{"imagePullSecrets": [{"name": "rhacm"}]}'
done
oc delete pod --all -n open-cluster-management-agent-addon
