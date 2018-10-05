#!/usr/bin/env bash
export OPENFAAS_URL=http://$(oc get route faas-netesd -o=jsonpath='{.spec.host}' --namespace=openfaas --config=/root/.kube/config)
export OPENFAAS_UI=$(oc get route gateway -o=jsonpath='{.spec.host}' --namespace=openfaas --config=/root/.kube/config)
