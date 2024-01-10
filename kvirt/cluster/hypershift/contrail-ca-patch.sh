#!/bin/bash
success=0
until [ $success -gt 1 ]; do
  tmp=$(mktemp)
  cat <<EOF>${tmp} || true
data:
  requestheader-client-ca-file: |
$(while IFS= read -a line; do echo "    $line"; done < <(cat /etc/kubernetes/bootstrap-secrets/aggregator-ca.crt))
EOF
  KUBECONFIG=/etc/kubernetes/bootstrap-secrets/kubeconfig kubectl -n kube-system patch configmap extension-apiserver-authentication --patch-file ${tmp}
  if [[ $? -eq 0 ]]; then
	rm ${tmp}
	success=2
  fi
  rm ${tmp}
  sleep 60
done
