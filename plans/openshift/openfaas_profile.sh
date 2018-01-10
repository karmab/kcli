export OPENFAAS_URL=http://$(oc get route faas-netesd -o=jsonpath='{.spec.host}' --namespace=openfaas)
