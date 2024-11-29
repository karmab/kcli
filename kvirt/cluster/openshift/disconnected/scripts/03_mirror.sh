#!/usr/bin/env bash

export HOME=/root
cd $HOME
export PATH=/root/bin:$PATH
export PULL_SECRET=/root/openshift_pull.json
IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY={{ disconnected_vm_name or "$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io" }}

# Add extra registry keys
curl -Lo /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv https://www.redhat.com/security/data/55A34A82.txt
jq ".transports.docker += {\"registry.redhat.io/redhat/certified-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}], \"registry.redhat.io/redhat/community-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}], \"registry.redhat.io/redhat/redhat-marketplace-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}]}" < /etc/containers/policy.json > /etc/containers/policy.json.new
mv /etc/containers/policy.json.new /etc/containers/policy.json

{% if openshift_release_image is defined and openshift_version is defined %}
export OPENSHIFT_RELEASE_IMAGE={{ openshift_release_image }}
export OCP_RELEASE={{ openshift_version }}-x86_64
{% elif version == 'ci' %}
export OPENSHIFT_RELEASE_IMAGE={{ 'registry.build01.ci.openshift.org' if 'ci' in tag|string else 'registry.ci.openshift.org' }}/ocp/release:{{ tag }}
export OCP_RELEASE={{ tag }}-x86_64
{% elif version in ['nightly', 'stable'] %}
{% set tag = tag|string %}
{% if tag.split('.')|length > 2 %}
TAG={{ tag }}
{% elif version == 'nightly' %}
TAG={{"latest-" + tag }}
{% else %}
TAG={{"stable-" + tag }}
{% endif %}
OCP_REPO={{ 'ocp-dev-preview' if version == 'nightly' else 'ocp' }}
curl -Ls https://mirror.openshift.com/pub/openshift-v4/clients/$OCP_REPO/$TAG/release.txt > /tmp/release.txt
export OPENSHIFT_RELEASE_IMAGE=$(grep 'Pull From: quay.io' /tmp/release.txt | awk -F ' ' '{print $3}')
export OCP_RELEASE=$(grep 'Name:' /tmp/release.txt | awk -F ' ' '{print $2}')-x86_64
{% else %}
curl -Ls https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{{ version }}-{{ tag }}/release.txt > /tmp/release.txt
export OPENSHIFT_RELEASE_IMAGE=$(grep 'Pull From: quay.io' /tmp/release.txt | awk -F ' ' '{print $3}')
export OCP_RELEASE=$(grep 'Name:' /tmp/release.txt | awk -F ' ' '{print $2}')-x86_64
{% endif %}
echo $REGISTRY:5000/openshift-release-dev/ocp-release:$OCP_RELEASE > /root/version.txt

REGISTRY_USER={{ disconnected_user or "dummy" }}
REGISTRY_PASSWORD={{ disconnected_password or "dummy" }}
podman login -u $REGISTRY_USER -p $REGISTRY_PASSWORD $REGISTRY:5000
#podman login registry.redhat.io --authfile /root/openshift_pull.json
REDHAT_CREDS=$(cat /root/openshift_pull.json | jq .auths.\"registry.redhat.io\".auth -r | base64 -d)
RHN_USER=$(echo $REDHAT_CREDS | cut -d: -f1)
RHN_PASSWORD=$(echo $REDHAT_CREDS | cut -d: -f2)
podman login -u "$RHN_USER" -p "$RHN_PASSWORD" registry.redhat.io

which oc-mirror >/dev/null 2>&1
if [ "$?" != "0" ] ; then
  TARGET={{ 'ocp-dev-preview' if version == 'dev-preview' else 'ocp' }}
  LONG_RELEASE={{ 'stable-4.17' if version == 'ci' else "$(cat /root/version.txt | awk -F: '{print $NF}' | rev | cut -d'-' -f2- | rev)" }}
  curl -Ls https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/$TARGET/$LONG_RELEASE/oc-mirror.tar.gz | tar xvz -C /usr/bin
  chmod +x /usr/bin/oc-mirror
fi

mkdir -p /root/.docker
cp -f /root/openshift_pull.json /root/.docker/config.json

oc-mirror --v2 --workspace file:// --secure-policy --config=mirror-config.yaml docker://$REGISTRY:5000

{% if prega %}
[ ! -d /root/idms ] || rm -rf /root/idms
mkdir /root/idms
sed -i -e '/source:/!b;/bundle/b;/cincinnati/b;s,quay.io/prega/test/,registry.redhat.io/,' /root/oc-mirror-workspace/results-*/*imageContentSourcePolicy.yaml
oc adm migrate icsp /root/oc-mirror-workspace/results-*/*imageContentSourcePolicy.yaml --dest-dir /root/idms
{% endif %}

if [ -d /root/idms ] ; then
  cp /root/idms/*yaml /root/manifests/imageContentSourcePolicy.yaml
fi
cp /root/working-dir/cluster-resources/{cs*,*oc-mirror*} /root

KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
jq ".auths += {\"$REGISTRY:5000\": {\"auth\": \"$KEY\",\"email\": \"jhendrix@karmalabs.corp\"}}" < $PULL_SECRET > /root/temp.json
cat /root/temp.json | tr -d [:space:] > $PULL_SECRET
echo "{\"auths\": {\"$REGISTRY:5000\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.corp\"}}}" > /root/temp.json
