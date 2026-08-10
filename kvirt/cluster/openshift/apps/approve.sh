timeout=0
while [ "$timeout" -lt "360" ] ; do
  # Check if CSV is already installed
  oc get csv -A --no-headers 2>/dev/null | grep -q "^.*{{ csv }}.*Succeeded" && break
  INSTALL_PLAN=$(oc get installplan -A -o json | jq -r '.items[] | select(.spec.approved==false) | select(.spec.clusterServiceVersionNames[] == "{{
csv }}") | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
  if [ -n "$INSTALL_PLAN" ] ; then
    NAMESPACE=$(echo $INSTALL_PLAN | cut -d'/' -f1)
    PLAN=$(echo $INSTALL_PLAN | cut -d'/' -f2)
    oc patch installplan -n $NAMESPACE $PLAN --type merge -p '{"spec":{"approved":true}}'
  else
    echo "Waiting for InstallPlan for {{ csv }} to appear"
  fi
  sleep 5
  timeout=$(($timeout + 5))
done
