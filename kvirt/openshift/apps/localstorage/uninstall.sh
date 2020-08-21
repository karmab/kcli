NAMESPACE="local-storage"
SUBCRIPTION="local-storage-operator"
OPERATORGROUP="local-operator-group"
CR="cr.yml"
oc delete -f $CR
oc delete subscription.operators.coreos.com -n $NAMESPACE $SUBCRIPTION
oc delete OperatorGroup -n $NAMESPACE $OPERATORGROUP
oc delete namespace $NAMESPACE
