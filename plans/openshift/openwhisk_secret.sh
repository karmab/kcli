AUTH_SECRET=$(oc get secret whisk.auth -o yaml | grep "system:" | awk '{print $2}' | base64 --decode)
wsk property set --auth ${AUTH_SECRET} --apihost $(oc get route/openwhisk --template={{.spec.host}})
