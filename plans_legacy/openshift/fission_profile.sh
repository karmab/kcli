export FISSION_URL=http://$(oc --namespace fission get svc controller -o=jsonpath='{..ip}')
export FISSION_ROUTER=$(oc --namespace fission get svc router -o=jsonpath='{..ip}')
