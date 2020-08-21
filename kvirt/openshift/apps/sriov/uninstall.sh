NAMESPACE="openshift-sriov-network-operator"
SUBCRIPTION="sriov-network-operator-subscription"
OPERATORGROUP="sriov-network-operators"
CR="cr.yml"
#oc delete -f $CR
oc delete subscription.operators.coreos.com -n $NAMESPACE $SUBCRIPTION
oc delete OperatorGroup -n $NAMESPACE $OPERATORGROUP
oc delete namespace $NAMESPACE
