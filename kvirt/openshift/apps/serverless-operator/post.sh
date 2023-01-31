echo """apiVersion: operator.knative.dev/v1alpha1
kind: KnativeEventing
metadata:
  name: knative-eventing
  namespace: knative-eventing""" | oc apply -f -
{% if knative_eventing_inbroker %}
oc label namespace knative-eventing eventing.knative.dev/injection=enabled
{% endif %}
