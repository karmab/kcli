ADMIN_USER={{ admin_user | default('admin') }
ADMIN_PASSWORD={{ admin_password | default('admin') }
printf "$ADMIN_USER:$(openssl passwd -apr1 $ADMIN_PASSWORD )\n" > htpasswd
oc create secret generic htpass-secret --from-file=htpasswd=htpasswd -n openshift-config
oc apply -f oauth.yml
oc adm policy add-cluster-role-to-user cluster-admin $ADMIN_USER
