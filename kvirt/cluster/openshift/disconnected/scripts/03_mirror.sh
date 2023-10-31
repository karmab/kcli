export PATH=/root/bin:$PATH
export PULL_SECRET=/root/openshift_pull.json
IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY_NAME=$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io
REGISTRY_USER={{ disconnected_user if disconnected_user != None else 'dummy' }}
REGISTRY_PASSWORD={{ disconnected_password if disconnected_password != None else 'dummy' }}
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

export LOCAL_REG="$REGISTRY_NAME:5000"
KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
jq ".auths += {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\",\"email\": \"jhendrix@karmalabs.corp\"}}" < $PULL_SECRET > /root/temp.json
cat /root/temp.json | tr -d [:space:] > $PULL_SECRET
oc adm release mirror -a $PULL_SECRET --from=$OPENSHIFT_RELEASE_IMAGE  --to-release-image=${LOCAL_REG}/openshift/release-images:${OCP_RELEASE} --to=${LOCAL_REG}/openshift/release
echo "{\"auths\": {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.corp\"}}}" > /root/temp.json
echo $REGISTRY_NAME:5000/openshift/release-images:$OCP_RELEASE > /root/version.txt
