timeout=0
while [ "$timeout" -lt "360" ] ; do
  INSTALL_PLAN=$(oc get installplan -A -o json | jq -r '.items[] | select(.spec.approved==false) | select(.spec.clusterServiceVersionNames[] == "{{ csv }}") | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
  [ -n "$INSTALL_PLAN" ] && break
  echo "Waiting for InstallPlan for {{ csv }} to appear"
  sleep 5
  timeout=$(($timeout + 5))
done
if [ -n "$INSTALL_PLAN" ] ; then
  NAMESPACE=$(echo $INSTALL_PLAN | cut -d'/' -f1)
  PLAN=$(echo $INSTALL_PLAN | cut -d'/' -f2)
  oc patch installplan -n $NAMESPACE $PLAN --type merge -p '{"spec":{"approved":true}}'
fi
