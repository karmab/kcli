FISSION_VERSION="0.4.0"
oc new-project fission
export TILLER_NAMESPACE=helm
sleep 240
oc adm policy add-cluster-role-to-user cluster-admin -z fission-svc
helm install --namespace fission https://github.com/fission/fission/releases/download/$FISSION_VERSION/fission-core-$FISSION_VERSION.tgz
curl -Lo fission https://github.com/fission/fission/releases/download/$FISSION_VERSION/fission-cli-linux && chmod +x fission && mv fission /usr/bin/
oc expose svc controller
oc expose svc router
export FISSION_URL=http://$(oc --namespace fission get svc controller -o=jsonpath='{..ip}')
export FISSION_ROUTER=$(oc --namespace fission get svc router -o=jsonpath='{..ip}')
fission env create --name python --image fission/python-env
fission function create --name hellopy --env python --code hello.py
fission route create --method GET --url /hellopy --function hellopy
echo export FISSION_URL=http://$(oc --namespace fission get svc controller -o=jsonpath='{..ip}') > /etc/profile.d/fission.sh
echo export FISSION_ROUTER=$(oc --namespace fission get svc router -o=jsonpath='{..ip}') >> /etc/profile.d/fission.sh
