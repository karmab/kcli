IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY={{ disconnected_vm_name or "$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io" }}
PULL_SECRET="/root/kubeadm_pull.json"
image=$1
if [ "$(echo $image | grep coredns)" != "" ] ; then
 DESTS=$(basename $image)
elif [ "$(echo $image | grep registry.k8s.io/pause)" != "" ] ; then
 DESTS="$(echo $image | cut -d'/' -f 2- ) pause:latest"
else
 DESTS=$(echo $image | cut -d'/' -f 2- )
fi
for DEST in $DESTS ; do
  echo COPYING $image to $REGISTRY:5000/$DEST
  skopeo copy docker://$image docker://$REGISTRY:5000/$DEST --all --authfile $PULL_SECRET
done
