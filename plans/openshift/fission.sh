FISSION_VERSION="[[ fission_version ]]"
oc new-project fission
export TILLER_NAMESPACE=helm
sleep 240
oc adm policy add-cluster-role-to-user cluster-admin -z fission-svc
helm install --namespace fission https://github.com/fission/fission/releases/download/$FISSION_VERSION/fission-[[ fission_version ]]-$FISSION_VERSION.tgz
curl -Lo fission https://github.com/fission/fission/releases/download/$FISSION_VERSION/fission-cli-linux && chmod +x fission && mv fission /usr/bin/
oc expose svc controller
oc expose svc router
#export FISSION_URL=http://$(oc --namespace fission get svc controller -o=jsonpath='{..ip}')
#export FISSION_ROUTER=$(oc --namespace fission get svc router -o=jsonpath='{..ip}')
export FISSION_URL=http://`oc get route controller -o jsonpath={.spec.host}`
export FISSION_ROUTER=`oc get route router -o jsonpath={.spec.host}`
fission env create --name nodejs --image fission/node-env:[[ fission_version ]]
fission env create --name python --image fission/python-env
fission function create --name hello --env nodejs --code /root/hello.js
fission function create --name hellopy --env python --code /root/hello.py
fission route create --method GET --url /hello --function hello
fission route create --method GET --url /hellopy --function hellopy
#echo export FISSION_URL=http://$(oc --namespace fission get svc controller -o=jsonpath='{..ip}') > /etc/profile.d/fission.sh
#echo export FISSION_ROUTER=$(oc --namespace fission get svc router -o=jsonpath='{..ip}') >> /etc/profile.d/fission.sh
echo export FISSION_URL=http://`oc get route controller -o jsonpath={.spec.host}` > /etc/profile.d/fission.sh
echo export FISSION_ROUTER=`oc get route router -o jsonpath={.spec.host}` >> /etc/profile.d/fission.sh
