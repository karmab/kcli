NAMESPACE="open-cluster-management"
SUBCRIPTION="acm-operator-subscription"
OPERATORGROUP="advanced-cluster-management"
CR="cr.yml"
oc delete -f $CR
oc delete subscription.operators.coreos.com -n $NAMESPACE $SUBCRIPTION
oc delete OperatorGroup -n $NAMESPACE $OPERATORGROUP
oc delete namespace $NAMESPACE
