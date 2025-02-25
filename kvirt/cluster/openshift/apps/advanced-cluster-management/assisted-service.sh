#!/usr/bin/env bash

export HOME=${HOME:-/root}

oc create -f 99-metal3-provisioning.yaml >/dev/null 2>&1 || oc patch provisioning provisioning-configuration --type merge -p '{"spec":{"watchAllNamespaces": true}}'

oc -n open-cluster-management wait --for=condition=complete multiclusterhub/multiclusterhub --timeout=10m

until oc get crd/agentserviceconfigs.agent-install.openshift.io >/dev/null 2>&1 ; do sleep 1 ; done
until oc get crd/clusterimagesets.hive.openshift.io >/dev/null 2>&1 ; do sleep 1 ; done

if [ "$(which openshift-install)" == "" ] ; then 
  VERSION={{ version|default('stable') }}
  TAG={{ tag|default('4.18') }}
  kcli download openshift-install -P version=$VERSION -P tag=$TAG
  export PATH=.:$PATH
fi

export RHCOS_ISO=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["formats"]["iso"]["disk"]["location"]')
export RHCOS_ROOTFS=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["formats"]["pxe"]["rootfs"]["location"]')
export RHCOS_VERSION=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["release"]')
{% if disconnected_url != None %}
[ -f /var/www/html/rhcos-live.x86_64.iso ] || curl -Lk $RHCOS_ISO > /var/www/html/rhcos-live.x86_64.iso
[ -f /var/www/html/rhcos-live-rootfs.x86_64.img ] || curl -Lk $RHCOS_ROOTFS > /var/www/html/rhcos-live-rootfs.x86_64.img
BAREMETAL_IP=$(ip -o addr show {{ assisted_download_nic }} | head -1 | awk '{print $4}' | cut -d'/' -f1)
echo $BAREMETAL_IP | grep -q ':' && BAREMETAL_IP=[$BAREMETAL_IP]
export RHCOS_ISO=http://${BAREMETAL_IP}/rhcos-live.x86_64.iso
export RHCOS_ROOTFS=http://${BAREMETAL_IP}/rhcos-live-rootfs.x86_64.img
{% endif %}

export MINOR=$(openshift-install version | head -1 | cut -d' ' -f2 | cut -d. -f1,2)
export PULLSECRET=$(cat {{ pull_secret|default('$HOME/openshift_pull.json')|pwd_path }} | tr -d [:space:])
export SSH_PRIV_KEY=$(cat {{ pub_key|default('$HOME/.ssh/id_rsa') }} |sed "s/^/    /")
export RELEASE=$(openshift-install version | grep 'release image' | awk '{print $NF}')

{% if disconnected_url != None %}
export CA_CERT=$(openssl s_client -showcerts -connect {{ disconnected_url }} </dev/null 2>/dev/null| openssl x509 -outform PEM | sed "s/^/    /")
oc get imagedigestmirrorset idms-operator-0 -o yaml > idms-oc-mirror.yaml
python3 gen_registries.py > registries.txt
export REGISTRIES=$(cat registries.txt)
{% endif %}

oc wait -n openshift-machine-api --for=condition=Ready $(oc -n openshift-machine-api  get pod -l baremetal.openshift.io/cluster-baremetal-operator=metal3-state -o name | xargs)

envsubst < assisted-service.sample.yml | oc create -f -
