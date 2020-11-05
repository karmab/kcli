export PATH=/root/bin:$PATH
yum -y install podman httpd httpd-tools jq bind-utils
IP=$(hostname -I | cut -d' ' -f1)
REVERSE_NAME=$(dig -x $IP +short | sed 's/\.[^\.]*$//')
REGISTRY_NAME=${REVERSE_NAME:-$(hostname -f)}
echo $REGISTRY_NAME:5000 > /root/url.txt
REGISTRY_USER={{ disconnected_user if disconnected_user != None else 'dummy' }}
REGISTRY_PASSWORD={{ disconnected_password if disconnected_password != None else 'dummy' }}
mkdir -p /opt/registry/{auth,certs,data}
openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 365 -out /opt/registry/certs/domain.crt -subj "/C=US/ST=Madrid/L=San Bernardo/O=Karmalabs/OU=Guitar/CN=$REGISTRY_NAME" -addext "subjectAltName=DNS:$REGISTRY_NAME"
cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract
htpasswd -bBc /opt/registry/auth/htpasswd $REGISTRY_USER $REGISTRY_PASSWORD
podman create --name registry --net host --security-opt label=disable -v /opt/registry/data:/var/lib/registry:z -v /opt/registry/auth:/auth:z -e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry" -e "REGISTRY_HTTP_SECRET=ALongRandomSecretForRegistry" -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd -v /opt/registry/certs:/certs:z -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key docker.io/library/registry:2
podman start registry
export UPSTREAM_REGISTRY="{{ disconnected_origin }}"
export OPENSHIFT_RELEASE_IMAGE={{ openshift_image|default(disconnected_origin + '/ocp/release:4.6') }}
export OCP_RELEASE=$( echo $OPENSHIFT_RELEASE_IMAGE | cut -d: -f2)
export LOCAL_REGISTRY="$REGISTRY_NAME:5000"
export RELEASE_NAME='{{ disconnected_prefix }}/release'
export PULL_SECRET="/root/openshift_pull.json"
export OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE=${LOCAL_REG}/${LOCAL_REPO}:${OCP_RELEASE}
KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
jq ".auths += {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\",\"email\": \"jhendrix@karmalabs.com\"}}" < $PULL_SECRET > /root/temp.json
mv /root/temp.json $PULL_SECRET
#oc adm release mirror -a $PULL_SECRET --from=$OPENSHIFT_RELEASE_IMAGE --to-release-image=${LOCAL_REGISTRY}/${RELEASE_NAME}:${OCP_RELEASE} --to=${LOCAL_REGISTRY}/$LOCAL_REPO
oc adm release mirror -a $PULL_SECRET --from=${UPSTREAM_REGISTRY}/${RELEASE_NAME}:${OCP_RELEASE} --to-release-image=${LOCAL_REGISTRY}/${RELEASE_NAME}:${OCP_RELEASE} --to=${LOCAL_REGISTRY}/{{ disconnected_prefix }}
echo "{\"auths\": {\"$REGISTRY_NAME:5000\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.com\"}}}" > /root/temp.json
OPENSHIFT_VERSION=$( grep cluster-openshift-apiserver-operator /var/log/cloud-init-output.log  | head -1 | awk '{print $NF}' | sed 's/-cluster-openshift-apiserver-operator//')
echo $REGISTRY_NAME:5000/{{ disconnected_prefix }}/release:$OPENSHIFT_VERSION > /root/version.txt
