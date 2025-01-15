IP=$(ip -o addr show eth0 | grep -v '169.254\|fe80::' | tail -1 | awk '{print $4}' | cut -d'/' -f1)
REGISTRY_NAME={{ disconnected_vm_name or "$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io" }}
REGISTRY={{ disconnected_vm_name or "$(echo $IP | sed 's/\./-/g' | sed 's/:/-/g').sslip.io" }}
REGISTRY_USER={{ disconnected_user or "dummy" }}
REGISTRY_PASSWORD={{ disconnected_password or "dummy" }}
KEY=$( echo -n $REGISTRY_USER:$REGISTRY_PASSWORD | base64)
echo {\"auths\": {\"$REGISTRY:5000\": {\"auth\": \"$KEY\", \"email\": \"jhendrix@karmalabs.corp\"}}} > /root/kubeadm_pull.json
