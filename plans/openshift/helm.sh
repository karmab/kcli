VERSION=v[[ helm_version ]]
oc login -u system:admin
oc new-project helm
oc create serviceaccount helm --namespace=helm
oc adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:helm:helm
curl -LO https://kubernetes-helm.storage.googleapis.com/helm-$VERSION-linux-amd64.tar.gz
tar zxvf helm-$VERSION-linux-amd64.tar.gz
mv linux-amd64/helm /usr/bin
chmod u+x /usr/bin/helm
cd /root
helm init --service-account helm --tiller-namespace helm
echo "export TILLER_NAMESPACE=helm" >>/root/.bashrc
echo "export HELM_HOME=/.helm" >>/root/.bashrc
