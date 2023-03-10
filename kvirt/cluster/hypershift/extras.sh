#!/usr/bin/env bash

export KUBECONFIG=/etc/kubernetes/kubeconfig.{{ cluster }}
while [ "$CLUSTER_VERSION" == "Completed" ] ; do
    CLUSTER_VERSION=$(kubectl get clusterversion version -o jsonpath='{.status.history[0].state}')
    sleep 20
done

{% if apps %}
oc create -f /etc/kubernetes/99-apps.yaml
oc create -f /etc/kubernetes/99-app-*.yaml
{% endif %}

{% if notify %}
oc create -f /etc/kubernetes/99-notifications.yaml
{% endif %}

{% if autoscale %}
oc create -f /etc/kubernetes/99-kcli-conf-cm.yaml
oc create -f /etc/kubernetes/99-kcli-ssh-cm.yaml
oc create -f /etc/kubernetes/autoscale.yaml
{% endif %}
