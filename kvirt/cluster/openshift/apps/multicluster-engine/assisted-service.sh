#!/usr/bin/env bash
#
oc create -f 99-metal3-provisioning.yaml >/dev/null 2>&1 || oc patch provisioning provisioning-configuration --type merge -p '{"spec":{"watchAllNamespaces": true}}'

if [ "$(which openshift-install)" == "" ] ; then 
  echo openshift-install needs to be in your path
  exit 1
fi

export RHCOS_ISO=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["formats"]["iso"]["disk"]["location"]')
export RHCOS_ROOTFS=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["formats"]["pxe"]["rootfs"]["location"]')
{% if disconnected_url != None %}
curl -Lk $RHCOS_ISO > /var/www/html/rhcos-live.x86_64.iso
curl -Lk $RHCOS_ROOTFS > /var/www/html/rhcos-live-rootfs.x86_64.img
BAREMETAL_IP=$(ip -o addr show {{ assisted_download_nic }} | head -1 | awk '{print $4}' | cut -d'/' -f1)
echo $BAREMETAL_IP | grep -q ':' && BAREMETAL_IP=[$BAREMETAL_IP]
export RHCOS_ISO=http://${BAREMETAL_IP}/rhcos-live.x86_64.iso
export RHCOS_ROOTFS=http://${BAREMETAL_IP}/rhcos-live-rootfs.x86_64.img
{% endif %}

export MINOR=$(openshift-install version | head -1 | cut -d' ' -f2 | cut -d. -f1,2)

export PULLSECRET=$(cat {{ pull_scret|default('~/openshift_pull.json') }} | tr -d [:space:])
export SSH_PRIV_KEY=$(cat {{ pub_key|default('~/.ssh/id_rsa') }} |sed "s/^/    /")
export VERSION=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["release"]')
export RELEASE=$(openshift-install version | grep 'release image' | cut -d' ' -f3)

{% if disconnected_url != None %}
export LOCAL_REGISTRY={{ disconnected_url }}
export CA_CERT=$(openssl s_client -showcerts -connect $LOCAL_REGISTRY </dev/null 2>/dev/null| openssl x509 -outform PEM | sed "s/^/    /")
export DISCONNECTED_PREFIX=openshift/release
export DISCONNECTED_PREFIX_IMAGES=openshift/release-images
OCP_RELEASE=$(openshift-install version | head -1 | cut -d' ' -f2)-x86_64
export RELEASE=$LOCAL_REGISTRY/$DISCONNECTED_PREFIX_IMAGES:$OCP_RELEASE
oc get imagecontentsourcepolicy operator-0 -o yaml > imageContentSourcePolicy.yaml
python3 gen_registries.py > registries.txt
export REGISTRIES=$(cat registries.txt)
{% endif %}

oc wait -n openshift-machine-api --for=condition=Ready $(oc -n openshift-machine-api  get pod -l baremetal.openshift.io/cluster-baremetal-operator=metal3-state -o name | xargs)
until [ "$(oc get mce multiclusterengine -o jsonpath='{.status.phase}')" == "Available" ] ; do sleep 1 ; done

envsubst < assisted-service.sample.yml | oc create -f -

oc wait --for=condition=Ready pod -l app=assisted-image-service -A --timeout=300s
oc wait --for=condition=Ready pod -l app=assisted-service -A  --timeout=300s
oc wait --for=condition=Ready pod -l app=agentinstalladmission -A  --timeout=300s
