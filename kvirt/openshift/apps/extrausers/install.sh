DEV_USER={{ extrausers_devuser }}
DEV_PASSWORD={{ extrausers_devpassword }}
ADMIN_USER={{ extrausers_adminuser }}
ADMIN_PASSWORD={{ extrausers_adminpassword }}
echo "Adding dev user $DEV_USER with password $DEV_PASSWORD"
echo "Adding admin user $ADMIN_USER with password $ADMIN_PASSWORD"
printf "$ADMIN_USER:$(openssl passwd -apr1 $ADMIN_PASSWORD )\n$DEV_USER:$(openssl passwd -apr1 $DEV_PASSWORD )\n" > htpasswd
oc create secret generic htpass-secret --from-file=htpasswd=htpasswd -n openshift-config
oc apply -f oauth.yml
echo "Granting cluster-admin role to $ADMIN_USER"
oc adm policy add-cluster-role-to-user cluster-admin $ADMIN_USER
