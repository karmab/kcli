#!/bin/bash
# Variables to set, suit to your installation
cd /root
export PATH=/root/bin:$PATH
export OCP_RELEASE="{{ tag }}"
export OCP_PULLSECRET_AUTHFILE='/root/openshift_pull.json'
IP=$(hostname -I | awk -F' ' '{print $NF}')
REVERSE_NAME=$(dig -x $IP +short | sed 's/\.[^\.]*$//')
echo $IP | grep -q ':' && REVERSE_NAME=$(dig -6x $IP +short | sed 's/\.[^\.]*$//')
REGISTRY_NAME=${REVERSE_NAME:-$(hostname -f)}
export LOCAL_REGISTRY=$REGISTRY_NAME:5000
export LOCAL_REGISTRY_INDEX_TAG=olm-index/redhat-operator-index:v$OCP_RELEASE
export LOCAL_REGISTRY_IMAGE_TAG=olm

# Login registries
podman login -u '{{ disconnected_user if disconnected_user != None else "dummy" }}' -p '{{ disconnected_password if disconnected_password != None else "dummy" }}' $LOCAL_REGISTRY
#podman login registry.redhat.io --authfile /root/openshift_pull.json
REDHAT_CREDS=$(cat /root/openshift_pull.json | jq .auths.\"registry.redhat.io\".auth -r | base64 -d)
RHN_USER=$(echo $REDHAT_CREDS | cut -d: -f1)
RHN_PASSWORD=$(echo $REDHAT_CREDS | cut -d: -f2)
podman login -u "$RHN_USER" -p "$RHN_PASSWORD" registry.redhat.io

which opm >/dev/null 2>&1
if [ "$?" != "0" ] ; then
export REPO="operator-framework/operator-registry"
export VERSION=$(curl -s https://api.github.com/repos/$REPO/releases | grep tag_name | grep -v -- '-rc' | head -1 | awk -F': ' '{print $2}' | sed 's/,//' | xargs)
echo "Using Opm Version $VERSION"
curl -Lk https://github.com/operator-framework/operator-registry/releases/download/$VERSION/linux-amd64-opm > /usr/bin/opm
chmod u+x /usr/bin/opm
fi

# Set these values to true for the catalog and miror to be created
export RH_OP='true'
export RH_OP_INDEX="registry.redhat.io/redhat/redhat-operator-index:v${OCP_RELEASE}"
export CERT_OP_INDEX="registry.redhat.io/redhat/certified-operator-index:v${OCP_RELEASE}"
export COMM_OP_INDEX="registry.redhat.io/redhat/community-operator-index:v${OCP_RELEASE}"
export MARKETPLACE_OP_INDEX="registry.redhat.io/redhat-marketplace-index:v${OCP_RELEASE}"
#export RH_OP_PACKAGES='local-storage-operator,performance-addon-operator,ptp-operator,sriov-network-operator'
export RH_OP_PACKAGES='{{ disconnected_operators|join(",") }}'

opm index prune --from-index $RH_OP_INDEX --packages $RH_OP_PACKAGES --tag $LOCAL_REGISTRY/$LOCAL_REGISTRY_INDEX_TAG
podman push $LOCAL_REGISTRY/$LOCAL_REGISTRY_INDEX_TAG --authfile $OCP_PULLSECRET_AUTHFILE
oc adm catalog mirror $LOCAL_REGISTRY/$LOCAL_REGISTRY_INDEX_TAG $LOCAL_REGISTRY/$LOCAL_REGISTRY_IMAGE_TAG --registry-config=$OCP_PULLSECRET_AUTHFILE

cp /root/manifests-redhat-operator-index-*/imageContentSourcePolicy.yaml /root
cp /root/manifests-redhat-operator-index-*/catalogSource.yaml /root
