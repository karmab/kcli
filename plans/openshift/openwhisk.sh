wget https://github.com/apache/incubator-openwhisk-cli/releases/download/latest/OpenWhisk_CLI-latest-linux-amd64.tgz
tar zxvf OpenWhisk_CLI-latest-linux-amd64.tgz
mv wsk /usr/bin/
chmod u+x /usr/bin/wsk
ip link set docker0 promisc on
yum -y install git
git clone https://github.com/projectodd/incubator-openwhisk-deploy-kube.git
cd incubator-openwhisk-deploy-kube
git fetch origin
git checkout remotes/origin/simplify-deployment-openshift
oc create -f openshift/ -f kubernetes
oc volume deployment/couchdb --add --overwrite --claim-name=couchdb-claim --claim-size=100Mi --name=couchdb-data
