IP=$(hostname -I | awk -F' ' '{print $NF}')
REVERSE_NAME=$(dig -x $IP +short | sed 's/\.[^\.]*$//')
echo $IP | grep -q ':' && REVERSE_NAME=$(dig -6x $IP +short | sed 's/\.[^\.]*$//')
REGISTRY_NAME=${REVERSE_NAME:-$(hostname -f)}
REGISTRY=$REGISTRY_NAME:5000
PULL_SECRET="/root/openshift_pull.json"
image=$1
skopeo copy docker://$image docker://$REGISTRY/$(echo $image | cut -d'/' -f 2- ) --all --authfile $PULL_SECRET
