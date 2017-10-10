oc login -u system:admin
oc new-project helm
oc create serviceaccount helm --namespace=helm
docker exec -it origin oadm policy add-cluster-role-to-user cluster-admin system:serviceaccount:helm:helm
curl -LO https://kubernetes-helm.storage.googleapis.com/helm-v2.6.0-linux-amd64.tar.gz
tar zxvf helm-v2.6.0-linux-amd64.tar.gz
mv linux-amd64/helm /usr/bin
chmod u+x /usr/bin/helm
helm init --service-account helm --tiller-namespace helm
echo "export TILLER_NAMESPACE=helm" >>/root/.bashrc
