curl -o oc.tar.gz https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/linux/oc.tar.gz
tar -xzvf oc.tar.gz
install -t /usr/bin {kubectl,oc}
test -f /root/auth.json && podman login registry.redhat.io --authfile /root/auth.json
