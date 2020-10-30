NAMESPACE="openshift-performance-addon"
SUBCRIPTION="performance-addon-operator-subscription"
OPERATORGROUP="openshift-performance-addon-operatorgroup"
CR="multicluster.yml"
# oc delete -f $CR
oc delete subscription.operators.coreos.com -n $NAMESPACE $SUBCRIPTION
oc delete OperatorGroup -n $NAMESPACE $OPERATORGROUP
oc delete namespace $NAMESPACE
