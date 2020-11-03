#!/bin/bash -x

function patchfunc {
oc patch etcd cluster -p='{"spec": {"unsupportedConfigOverrides": {"useUnsupportedUnsafeNonHANonProductionUnstableEtcd": true}}}' --type=merge || return 1
oc patch authentications.operator.openshift.io cluster -p='{"spec": {"managementState": "Managed", "unsupportedConfigOverrides": {"useUnsupportedUnsafeNonHANonProductionUnstableOAuthServer": true}}}' --type=merge || return 1
# oc patch -n openshift-ingress-operator ingresscontroller/default -p='{"spec":{"replicas": 1}}' --type=merge || return 1
oc patch clusterversion/version -p="$(cat <<- EOF
 spec:
    overrides:
      - group: apps/v1
        kind: Deployment
        name: etcd-quorum-guard
        namespace: openshift-machine-config-operator
        unmanaged: true
EOF
)" --type=merge || return 1
oc scale --replicas=1 deployment/etcd-quorum-guard -n openshift-etcd || return 1
return 0
}

export KUBECONFIG=/opt/openshift/auth/kubeconfig
while ! patchfunc; do
    echo "Waiting 10s to retry..."
    sleep 10
done
touch kcli-patch.done
