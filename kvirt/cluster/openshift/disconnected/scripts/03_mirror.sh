#!/usr/bin/env bash

export HOME=/root
cd $HOME
export PATH=/root/bin:$PATH
export PULL_SECRET=/root/openshift_pull.json
IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY=$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io

# Add extra registry keys
curl -Lo /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv https://www.redhat.com/security/data/55A34A82.txt
jq ".transports.docker += {\"registry.redhat.io/redhat/certified-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}], \"registry.redhat.io/redhat/community-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}], \"registry.redhat.io/redhat/redhat-marketplace-operator-index\": [{\"type\": \"signedBy\",\"keyType\": \"GPGKeys\",\"keyPath\": \"/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-isv\"}]}" < /etc/containers/policy.json > /etc/containers/policy.json.new
mv /etc/containers/policy.json.new /etc/containers/policy.json

{% if version == 'ci' %}
export OCP_RELEASE={{ "scos-%s" % tag if okd else tag }}

{% elif version in ['nightly', 'stable'] %}

{% set tag = tag|string %}
{% if tag.split('.')|length > 2 %}
TAG={{ tag }}
{% else %}
{% set prefix = 'latest' if version == 'nightly' else 'stable' %}
TAG={{ prefix + '-' + tag }}
{% endif %}
curl -Ls https://mirror.openshift.com/pub/openshift-v4/clients/ocp/$TAG/release.txt > /tmp/release.txt
OCP_RELEASE=$(grep 'Name:' /tmp/release.txt | awk -F ' ' '{print $2}')-x86_64

{% elif version == 'candidate' %}
curl -Ls https://mirror.openshift.com/pub/openshift-v4/clients/ocp-dev-preview/{{ tag }}/release.txt > /tmp/release.txt
OCP_RELEASE=$(grep 'Name:' /tmp/release.txt | awk -F ' ' '{print $2}')-x86_64
{% endif %}

{% if okd %}
PREFIX=origin/release-scos
{% elif version == 'ci' %}
PREFFIX=ocp/ocp-release
{% else %}
PREFIX=openshift/release-images
# PREFIX=openshift-release-dev/ocp-release
{% endif %}
echo $REGISTRY:5000/$PREFIX:$OCP_RELEASE > /root/version.txt

REGISTRY_USER={{ disconnected_user }}
REGISTRY_PASSWORD={{ disconnected_password }}
podman login -u $REGISTRY_USER -p $REGISTRY_PASSWORD $REGISTRY:5000

KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
mv /root/openshift_pull.json /root/openshift_pull.json.old
jq ".auths += {\"$REGISTRY:5000\": {\"auth\": \"$KEY\",\"email\": \"jhendrix@karmalabs.corp\"}}" < /root/openshift_pull.json.old > /root/openshift_pull.json

REDHAT_CREDS=$(cat /root/openshift_pull.json | jq .auths.\"registry.redhat.io\".auth -r | base64 -d)
RHN_USER=$(echo $REDHAT_CREDS | cut -d: -f1)
RHN_PASSWORD=$(echo $REDHAT_CREDS | cut -d: -f2)
podman login -u "$RHN_USER" -p "$RHN_PASSWORD" registry.redhat.io

which oc-mirror >/dev/null 2>&1
if [ "$?" != "0" ] ; then
  OPENSHIFT_TAG=4.19
  curl -Ls https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable-$OPENSHIFT_TAG/oc-mirror.tar.gz | tar xvz -C /usr/bin
  chmod +x /usr/bin/oc-mirror
fi

mkdir -p /root/.docker
cp -f /root/openshift_pull.json /root/.docker/config.json

oc-mirror --v2 --workspace file:// --config=mirror-config.yaml docker://$REGISTRY:5000

{% if prega %}
sed -i 's@quay.io/prega/test@registry.redhat.io@' /root/working-dir/cluster-resources/idms-oc-mirror.yaml
{% endif %}

cp /root/working-dir/cluster-resources/{cs*,*oc-mirror*} /root
