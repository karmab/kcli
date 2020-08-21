NAMESPACE="openshift-storage"
SUBCRIPTION="ocs-operator"
OPERATORGROUP="openshift-storage-operatorgroup"
oc delete subscription.operators.coreos.com -n $NAMESPACE $SUBCRIPTION
oc delete OperatorGroup -n $NAMESPACE $OPERATORGROUP
oc delete namespace $NAMESPACE
