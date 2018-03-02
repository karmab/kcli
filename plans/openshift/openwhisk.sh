wget https://github.com/apache/incubator-openwhisk-cli/releases/download/latest/OpenWhisk_CLI-latest-linux-amd64.tgz
tar zxvf OpenWhisk_CLI-latest-linux-amd64.tgz
mv wsk /usr/bin/
chmod u+x /usr/bin/wsk
ip link set docker0 promisc on
docker pull strimzi/zookeeper:latest
docker pull strimzi/kafka:latest
[% if persistent %]
URL="https://raw.githubusercontent.com/projectodd/openwhisk-openshift/master/persistent-template.yml"
[% else %]
URL="https://git.io/openwhisk-template"
[% endif %]
[% if large %]
oc process -f $URL --param-file=/root/larger.env | oc create -f -
[% else %]
oc process -f $URL | oc create -f -
[% endif %]
