#!/usr/bin/env bash

export KUBECONFIG=/etc/kubernetes/kubeconfig.{{ cluster }}

while [ "$CLUSTER_VERSION" != "Completed" ] ; do
  CLUSTER_VERSION=$(kubectl get clusterversion version -o jsonpath='{.status.history[0].state}')
  echo "Waiting for Cluster to be ready"
  sleep 20
done

oc create ns kcli-infra
oc adm policy add-cluster-role-to-user cluster-admin -z default -n kcli-infra

if [ -f /etc/kubernetes/99-apps.yaml ] ; then
  oc create -f /etc/kubernetes/99-apps.yaml
  oc create -f /etc/kubernetes/99-app-*.yaml
fi

if [ -f /etc/kubernetes/99-notifications.yaml ] ; then
  oc create -f /etc/kubernetes/99-notifications.yaml
fi

if [ -f /etc/kubernetes/autoscale.yaml ] ; then
  oc create -f /etc/kubernetes/99-kcli-conf-cm.yaml
  oc create -f /etc/kubernetes/99-kcli-ssh-cm.yaml
  oc create -f /etc/kubernetes/autoscale.yaml
fi
