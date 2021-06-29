images="quay.io/karmab/curl:latest quay.io/karmab/origin-coredns:latest quay.io/karmab/haproxy:latest quay.io/karmab/origin-keepalived-ipfailover:latest quay.io/karmab/mdns-publisher:latest quay.io/karmab/kubectl:latest"

for image in $images ; do
  /root/bin/sync_image.sh $image
done
