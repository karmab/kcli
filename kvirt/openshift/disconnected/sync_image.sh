IP=$(ip -o addr show eth0 |head -1 | awk '{print $4}' | cut -d'/' -f1)
REVERSE_NAME=$(dig -x $IP +short | sed 's/\.[^\.]*$//')
echo $IP | grep -q ':' && SERVER6=$(grep : /etc/resolv.conf | grep -v fe80 | cut -d" " -f2) && REVERSE_NAME=$(dig -6x $IP +short @$SERVER6 | sed 's/\.[^\.]*$//')
REGISTRY_NAME=${REVERSE_NAME:-$(hostname -f)}
REGISTRY=$REGISTRY_NAME:5000
PULL_SECRET="/root/openshift_pull.json"
image=$1
skopeo copy docker://$image docker://$REGISTRY/$(echo $image | cut -d'/' -f 2- ) --all --authfile $PULL_SECRET
