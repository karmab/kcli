NAMESPACE="openshift-operators"
SUBCRIPTION="serverless-operator"
oc delete -f eventing.yml
sleep 10
oc delete namespace knative-eventing
oc delete -f serving.yml
sleep 10
oc delete namespace knative-serving
oc delete subscription.operators.coreos.com -n $NAMESPACE $SUBCRIPTION
