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
oc volume deployment/kafka --add --overwrite --claim-name=kafka-logs-claim --claim-size=100Mi --name=kafka-logs
oc volume deployment/kafka --add --overwrite --claim-name=kafka-claim --claim-size=100Mi --name=kafka
oc volume deployment/nginx --add --overwrite --claim-name=nginx-claim --claim-size=100Mi --name=logs
oc volume deployment/zookeper --add --overwrite --claim-name=zookeper-data-claim --claim-size=100Mi --name=zookeper-data
oc volume deployment/zookeeper --add --overwrite --claim-name=zookeper-datalog-claim --claim-size=100Mi --name=zookeeper-datalog
