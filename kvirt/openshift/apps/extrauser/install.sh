USER={{ extrauser_user }}
PASSWORD={{ extrauser_password }}
echo "Adding user $USER with password $PASSWORD"
printf "$USER:$(openssl passwd -apr1 $PASSWORD )\n" > htpasswd
oc create secret generic htpass-secret --from-file=htpasswd=htpasswd -n openshift-config
oc apply -f oauth.yml
{% if extrauser_admin %}
echo "Granting cluster-admin role to $USER"
oc adm policy add-cluster-role-to-user cluster-admin $USER
{% endif %}
