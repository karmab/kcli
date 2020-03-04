export PATH=/root/bin:$PATH
yum -y install podman httpd httpd-tools jq
mkdir -p /opt/registry/{auth,certs,data}
openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 365 -out /opt/registry/certs/domain.crt -subj "/C=US/ST=Madrid/L=San Bernardo/O=Karmalabs/OU=Guitar/CN=$(hostname -f )" -addext "subjectAltName=DNS:$(hostname -f)"
cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract
htpasswd -bBc /opt/registry/auth/htpasswd {{ registry_user }} {{ registry_password }}
podman create --name registry --net host --security-opt label=disable -v /opt/registry/data:/var/lib/registry:z -v /opt/registry/auth:/auth:z -e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry" -e "REGISTRY_HTTP_SECRET=ALongRandomSecretForRegistry" -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd -v /opt/registry/certs:/certs:z -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key docker.io/library/registry:2
podman start registry
export OPENSHIFT_RELEASE_IMAGE={{ openshift_image }}
export OCP_RELEASE=$( echo $OPENSHIFT_RELEASE_IMAGE | cut -d: -f2)
export LOCAL_REG="$(hostname -f):5000"
export LOCAL_REPO='ocp/release'
export PULL_SECRET="/root/openshift_pull.json"
export OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE=${LOCAL_REG}/${LOCAL_REPO}:${OCP_RELEASE}
KEY=$( echo -n {{ registry_user }}:{{ registry_password }} | base64)
jq ".auths += {\"$(hostname -f):5000\": {\"auth\": \"$KEY\",\"email\": \"jhendrix@karmalabs.com\"}}" < $PULL_SECRET > /root/temp.json
mv /root/temp.json $PULL_SECRET
oc adm release mirror -a $PULL_SECRET --from=$OPENSHIFT_RELEASE_IMAGE --to-release-image=$LOCAL_REG/$LOCAL_REPO:$OCP_RELEASE --to=$LOCAL_REG/$LOCAL_REPO
echo "{\"auths\": {\"$(hostname -f):5000\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.com\"}}}" > /root/temp.json

echo "additionalTrustBundle: |" >> /root/results.txt
sed -e 's/^/  /' /opt/registry/certs/domain.crt >>  /root/results.txt
cat << EOF >> /root/results.txt
imageContentSources:
- mirrors:
  - $(hostname -f):5000/ocp/release
  source: quay.io/openshift-release-dev/ocp-v4.0-art-dev
- mirrors:
  - $(hostname -f):5000/ocp/release
  source: registry.svc.ci.openshift.org/ocp/release
EOF
