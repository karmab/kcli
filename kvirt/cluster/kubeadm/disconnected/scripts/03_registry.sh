export PATH=/root/bin:$PATH
export REGISTRY_IMAGE=quay.io/karmab/registry:latest
IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY_NAME={{ disconnected_vm_name or "$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io" }}
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
  delete:
    enabled: true
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
openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 3650 -out /opt/registry/certs/domain.crt -subj "/C=US/ST=Madrid/L=Chamberi/O=Karmalabs/OU=Guitar/CN=$REGISTRY_NAME" -addext "subjectAltName=DNS:$REGISTRY_NAME"
if [ "$(which dnf)" != "" ] ; then
 cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
 update-ca-trust extract
else
 cp /opt/registry/certs/domain.crt /usr/local/share/ca-certificates
 update-ca-certificates
fi
htpasswd -bBc /opt/registry/auth/htpasswd $REGISTRY_USER $REGISTRY_PASSWORD
podman create --name registry --net host --security-opt label=disable -v /opt/registry/data:/var/lib/registry:z -v /opt/registry/auth:/auth:z -v /opt/registry/conf/config.yml:/etc/docker/registry/config.yml -e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry" -e "REGISTRY_HTTP_SECRET=ALongRandomSecretForRegistry" -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd -v /opt/registry/certs:/certs:z -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key $REGISTRY_IMAGE
[ "$?" == "0" ] || !!
systemctl enable --now registry
