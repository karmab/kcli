images="quay.io/karmab/curl:multi quay.io/karmab/origin-coredns:multi quay.io/karmab/haproxy:multi quay.io/karmab/origin-keepalived-ipfailover:multi quay.io/karmab/mdns-publisher:multi quay.io/karmab/kubectl:multi {{ 'quay.io/karmab/kcli:latest' if async else '' }}"

for image in $images ; do
 /root/bin/sync_image.sh $image
done
