oc get cm istio-sidecar-injector -n istio-system -oyaml  | sed -e 's/securityContext:/securityContext:\\n      privileged: true/' | oc replace -f -
oc delete pod -n istio-system -l istio=sidecar-injector
