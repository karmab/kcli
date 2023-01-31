DEV_USER={{ users_dev }}
DEV_PASSWORD={{ users_devpassword }}
ADMIN_USER={{ users_admin }}
ADMIN_PASSWORD={{ users_adminpassword }}
echo "Adding dev user $DEV_USER with password $DEV_PASSWORD"
echo "Adding admin user $ADMIN_USER with password $ADMIN_PASSWORD"
printf "$ADMIN_USER:$(openssl passwd -apr1 $ADMIN_PASSWORD )\n$DEV_USER:$(openssl passwd -apr1 $DEV_PASSWORD )\n" > htpasswd
NAMESPACE={{ "clusters" if hypershift|default(False) else 'openshift-config' }}
{% if hypershift|default(False) %}
CLUSTER={{ cluster }}
KUBECONFIGMGMT=$HOME/.kcli/clusters/$CLUSTER/kubeconfig.mgmt
KUBECONFIG=$KUBECONFIGMGMT oc patch hc -n $NAMESPACE $CLUSTER --patch-file oauth_hypershift.yml --type merge
KUBECONFIG=$KUBECONFIGMGMT oc create secret generic htpass-secret --from-file=htpasswd=htpasswd -n $NAMESPACE
{% else %}
oc apply -f oauth.yml
oc create secret generic htpass-secret --from-file=htpasswd=htpasswd -n $NAMESPACE
{% endif %}
echo "Granting cluster-admin role to $ADMIN_USER"
oc adm policy add-cluster-role-to-user cluster-admin $ADMIN_USER
