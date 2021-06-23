export PATH=/root/bin:$PATH
yum -y install podman httpd httpd-tools jq bind-utils skopeo
IP=$(hostname -I | awk -F' ' '{print $2}')
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
export UPSTREAM_REGISTRY={{ disconnected_origin }}
{% if ':' in tag|string %}
{% set release_name, ocp_release = (tag|string).split(':') %}
export RELEASE_NAME={{ release_name }}
export OCP_RELEASE={{ ocp_release }}
{% elif disconnected_origin != 'quay.io' %}
export RELEASE_NAME=ocp/release
export OCP_RELEASE={{ tag }}
{% else %}
export RELEASE_NAME=openshift-release-dev/ocp-release
export OCP_RELEASE={{ openshift_version|default(tag) }}-x86_64
{% endif %}
export LOCAL_REGISTRY=$REGISTRY_NAME:5000
export PULL_SECRET=/root/openshift_pull.json
KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
jq ".auths += {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\",\"email\": \"jhendrix@karmalabs.com\"}}" < $PULL_SECRET > /root/temp.json
cat /root/temp.json | tr -d [:space:] > $PULL_SECRET
oc adm release mirror -a $PULL_SECRET --from=${UPSTREAM_REGISTRY}/${RELEASE_NAME}:${OCP_RELEASE} --to-release-image=${LOCAL_REGISTRY}/{{ disconnected_prefix }}/release:${OCP_RELEASE} --to=${LOCAL_REGISTRY}/{{ disconnected_prefix }}
echo "{\"auths\": {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.com\"}}}" > /root/temp.json
#OPENSHIFT_VERSION=$( grep cluster-openshift-apiserver-operator /var/log/cloud-init-output.log  | head -1 | awk '{print $NF}' | sed 's/-cluster-openshift-apiserver-operator//')
echo $REGISTRY_NAME:5000/{{ disconnected_prefix }}/release:$OCP_RELEASE > /root/version.txt
