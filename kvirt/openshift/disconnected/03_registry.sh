export PATH=/root/bin:$PATH
export PULL_SECRET=/root/openshift_pull.json
dnf  -y install podman httpd httpd-tools jq bind-utils skopeo
IP=$(ip -o addr show eth0 |head -1 | awk '{print $4}' | cut -d'/' -f1)
REVERSE_NAME=$(dig -x $IP +short | sed 's/\.[^\.]*$//')
echo $IP | grep -q ':' && SERVER6=$(grep : /etc/resolv.conf | grep -v fe80 | cut -d" " -f2) && REVERSE_NAME=$(dig -6x $IP +short @$SERVER6 | sed 's/\.[^\.]*$//')
REGISTRY_NAME=${REVERSE_NAME:-$(hostname -f)}
echo $IP $REGISTRY_NAME >> /etc/hosts 
echo $REGISTRY_NAME:5000 > /root/url.txt
REGISTRY_USER={{ disconnected_user if disconnected_user != None else 'dummy' }}
REGISTRY_PASSWORD={{ disconnected_password if disconnected_password != None else 'dummy' }}
mkdir -p /opt/registry/{auth,certs,data,conf}
cat <<EOF > /opt/registry/conf/config.yml
version: 0.1
log:
  fields:
    service: registry
storage:
  cache:
    blobdescriptor: inmemory
  filesystem:
    rootdirectory: /var/lib/registry
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
compatibility:
  schema1:
    enabled: true
EOF
openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 365 -out /opt/registry/certs/domain.crt -subj "/C=US/ST=Madrid/L=San Bernardo/O=Karmalabs/OU=Guitar/CN=$REGISTRY_NAME" -addext "subjectAltName=DNS:$REGISTRY_NAME"
cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract
htpasswd -bBc /opt/registry/auth/htpasswd $REGISTRY_USER $REGISTRY_PASSWORD
podman create --name registry --net host --security-opt label=disable -v /opt/registry/data:/var/lib/registry:z -v /opt/registry/auth:/auth:z -v /opt/registry/conf/config.yml:/etc/docker/registry/config.yml -e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry" -e "REGISTRY_HTTP_SECRET=ALongRandomSecretForRegistry" -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd -v /opt/registry/certs:/certs:z -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key quay.io/saledort/registry:2
podman start registry
{% if openshift_release_image is defined and openshift_version is defined %}
export OPENSHIFT_RELEASE_IMAGE={{ openshift_release_image }}
export OCP_RELEASE={{ openshift_version }}-x86_64
{% elif version == 'ci' %}
export OPENSHIFT_RELEASE_IMAGE={{ 'registry.build01.ci.openshift.org' if 'ci' in tag|string else 'registry.ci.openshift.org' }}/ocp/release:{{ tag }}
export OCP_RELEASE={{ tag }}-x86_64
{% elif version in ['nightly', 'stable'] %}
{% set tag = tag|string %}
{% if tag.split('.')|length > 2 %}
TAG={{ tag }}
{% elif version == 'nightly' %}
TAG={{"latest-" + tag }}
{% else %}
TAG={{"stable-" + tag }}
{% endif %}
OCP_REPO={{ 'ocp-dev-preview' if version == 'nightly' else 'ocp' }}
curl -s https://mirror.openshift.com/pub/openshift-v4/clients/$OCP_REPO/$TAG/release.txt > /tmp/release.txt
export OPENSHIFT_RELEASE_IMAGE=$(grep 'Pull From: quay.io' /tmp/release.txt | awk -F ' ' '{print $3}')
export OCP_RELEASE=$(grep 'Name:' /tmp/release.txt | awk -F ' ' '{print $2}')-x86_64
{% else %}
curl -s https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{{ version }}-{{ tag }}/release.txt > /tmp/release.txt
export OPENSHIFT_RELEASE_IMAGE=$(grep 'Pull From: quay.io' /tmp/release.txt | awk -F ' ' '{print $3}')
export OCP_RELEASE=$(grep 'Name:' /tmp/release.txt | awk -F ' ' '{print $2}')-x86_64
{% endif %}

export LOCAL_REG="$REGISTRY_NAME:5000"
KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
jq ".auths += {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\",\"email\": \"jhendrix@karmalabs.com\"}}" < $PULL_SECRET > /root/temp.json
cat /root/temp.json | tr -d [:space:] > $PULL_SECRET
oc adm release mirror -a $PULL_SECRET --from=$OPENSHIFT_RELEASE_IMAGE  --to-release-image=${LOCAL_REG}/ocp4:${OCP_RELEASE} --to=${LOCAL_REG}/ocp4
echo "{\"auths\": {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.com\"}}}" > /root/temp.json
echo $REGISTRY_NAME:5000/ocp4:$OCP_RELEASE > /root/version.txt
