#!/usr/bin/env bash

cd /root
export PATH=/root/bin:$PATH
export OCP_PULLSECRET_AUTHFILE='/root/openshift_pull.json'
IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY_NAME=$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io
export LOCAL_REGISTRY=$REGISTRY_NAME:5000
export IMAGE_TAG=olm

# Add extra registry keys
curl -Lo /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv https://www.redhat.com/security/data/55A34A82.txt
jq ".transports.docker += {\"registry.redhat.io/redhat/certified-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}], \"registry.redhat.io/redhat/community-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}], \"registry.redhat.io/redhat/redhat-marketplace-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}]}" < /etc/containers/policy.json > /etc/containers/policy.json.new
mv /etc/containers/policy.json.new /etc/containers/policy.json

# Login registries
REGISTRY_USER={{ disconnected_user if disconnected_user != None else "dummy" }}
REGISTRY_PASSWORD={{ disconnected_password if disconnected_password != None else "dummy" }}
podman login -u $REGISTRY_USER -p $REGISTRY_PASSWORD $LOCAL_REGISTRY
#podman login registry.redhat.io --authfile /root/openshift_pull.json
REDHAT_CREDS=$(cat /root/openshift_pull.json | jq .auths.\"registry.redhat.io\".auth -r | base64 -d)
RHN_USER=$(echo $REDHAT_CREDS | cut -d: -f1)
RHN_PASSWORD=$(echo $REDHAT_CREDS | cut -d: -f2)
podman login -u "$RHN_USER" -p "$RHN_PASSWORD" registry.redhat.io

which oc-mirror >/dev/null 2>&1
if [ "$?" != "0" ] ; then
  curl -Ls https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/4.13.12/oc-mirror.tar.gz | tar xvz -C /usr/bin
  chmod +x /usr/bin/oc-mirror
fi

mkdir -p /root/.docker
cp -f /root/openshift_pull.json /root/.docker/config.json

envsubst < /root/scripts/mirror-config.yaml.sample > /root/mirror-config.yaml

rm -rf /root/oc-mirror-workspace || true
oc-mirror --config /root/mirror-config.yaml docker://$LOCAL_REGISTRY
cp /root/oc-mirror-workspace/results-*/imageContentSourcePolicy.yaml /root
cp /root/oc-mirror-workspace/results-*/catalogSource* /root
