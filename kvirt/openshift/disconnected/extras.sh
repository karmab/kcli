images="quay.io/karmab/curl:latest quay.io/openshift/origin-coredns:latest quay.io/karmab/haproxy:latest quay.io/openshift/origin-keepalived-ipfailover:latest quay.io/openshift-metal3/mdns-publisher:latest quay.io/karmab/kubectl:latest"

for image in $images ; do
  /root/bin/sync_image.sh $image
done
