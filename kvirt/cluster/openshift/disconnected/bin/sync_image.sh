IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY_NAME=$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io
REGISTRY=$REGISTRY_NAME:5000
PULL_SECRET="/root/openshift_pull.json"
image=$1
skopeo copy docker://$image docker://$REGISTRY/$(echo $image | cut -d'/' -f 2- ) --all --authfile $PULL_SECRET
