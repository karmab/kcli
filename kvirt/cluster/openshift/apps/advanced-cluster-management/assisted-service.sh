#!/usr/bin/env bash

if [ "$(which openshift-install)" == "" ] ; then 
  echo openshift-install needs to be in your path
  exit 1
fi

until oc get crd/agentserviceconfigs.agent-install.openshift.io >/dev/null 2>&1 ; do sleep 1 ; done
until oc get crd/clusterimagesets.hive.openshift.io >/dev/null 2>&1 ; do sleep 1 ; done

export RHCOS_ISO=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["formats"]["iso"]["disk"]["location"]')
export RHCOS_ROOTFS=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["formats"]["pxe"]["rootfs"]["location"]')
export MINOR=$(openshift-install version | head -1 | cut -d' ' -f2 | cut -d. -f1,2)

export PULLSECRET=$(cat ~/openshift_pull.json | tr -d [:space:])
export SSH_PRIV_KEY=$(cat ~/.ssh/id_rsa |sed "s/^/    /")
export VERSION=$(openshift-install coreos print-stream-json | jq -r '.["architectures"]["x86_64"]["artifacts"]["metal"]["release"]')
export RELEASE=$(openshift-install version | grep 'release image' | cut -d' ' -f3)

envsubst < assisted-service.sample.yml | oc create -f -
