PRODUCTPAGE=$(oc get route productpage -o jsonpath='{.spec.host}{"\n"}')
watch -n 1 curl -o /dev/null -s -w %{http_code}\n ${PRODUCTPAGE}/productpage
