#!/bin/bash -x

systemctl disable --now ironic
while [ ! -e "/opt/openshift/.bootkube.done" ] ; do
    echo "Waiting 10s to retry..."
    sleep 10
done
KUBECONFIG=/opt/openshift/auth/kubeconfig oc create cm bootstrap -n kube-system --from-literal status=complete
touch kcli-metal3-patch.done
