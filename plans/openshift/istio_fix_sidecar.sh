oc get cm istio-sidecar-injector -n istio-system -oyaml  | sed -e 's/securityContext:/securityContext:\\n      privileged: true/' | oc replace -f -
