images="quay.io/karmab/curl:latest quay.io/openshift/origin-coredns:latest quay.io/karmab/haproxy:latest quay.io/openshift/origin-keepalived-ipfailover:latest quay.io/openshift-metal3/mdns-publisher:latest quay.io/karmab/kubectl:latest"

podman login -u dummy -p dummy $(hostname -f):5000
for image in $images ; do
  podman pull $image
  short=$(echo $image | cut -d: -f1)
  tag=$(podman images | grep $short | awk '{print $3}')
  image_registry=$(echo $image | cut -d/ -f1)
  image_name=$(echo $image | sed "s@$image_registry/@@")
  podman tag $tag $(hostname -f):5000/$image_name
  podman push $(hostname -f):5000/$image_name
done
