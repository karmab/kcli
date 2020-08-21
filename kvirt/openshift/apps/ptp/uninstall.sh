NAMESPACE="openshift-ptp"
SUBCRIPTION="ptp-operator-subscription"
OPERATORGROUP="ptp-operators"
CR="cr.yml"
#oc delete -f $CR
oc delete subscription.operators.coreos.com -n $NAMESPACE $SUBCRIPTION
oc delete OperatorGroup -n $NAMESPACE $OPERATORGROUP
oc delete namespace $NAMESPACE
