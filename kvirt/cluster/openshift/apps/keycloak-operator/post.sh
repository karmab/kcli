{% if install_cr|default(True) %}
timeout=0
while [ "$timeout" -lt 600 ] ; do
  ready=$(oc -n {{ namespace }} get keycloak {{ keycloak_name }} -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)
  [ "$ready" == "True" ] && break
  echo "Waiting for keycloak to be ready"
  sleep 10
  timeout=$(($timeout + 10))
done
host=$(oc -n {{ namespace }} get ingress -o jsonpath='{range .items[*]}{.spec.rules[0].host}{"\n"}{end}' 2>/dev/null | head -1)
{% if keycloak_users or keycloak_oauth %}
{% if keycloak_oauth %}
{% if not keycloak_oauth_ca %}
oc -n openshift-config-managed get configmap default-ingress-cert -o jsonpath='{.data.ca\.crt}' > ca.crt
oc -n openshift-config create configmap keycloak-ca --from-file=ca.crt=ca.crt
{% endif %}
oc -n openshift-config create secret generic keycloak-oauth-secret --from-literal=clientSecret={{ keycloak_oauth_clientsecret }}
domain=$(oc get ingresscontroller default -n openshift-ingress-operator -o jsonpath='{.status.domain}')
sed "s|OAUTH_REDIRECT|https://oauth-openshift.$domain/oauth2callback/{{ keycloak_oauth_idp }}|" realm.yml | oc create -f -
{% else %}
oc create -f realm.yml
{% endif %}
timeout=0
while [ "$timeout" -lt 600 ] ; do
  imported=$(oc -n {{ namespace }} get keycloakrealmimport {{ keycloak_name }}-realm-import -o jsonpath='{.status.conditions[?(@.type=="Done")].status}' 2>/dev/null)
  [ "$imported" == "True" ] && break
  echo "Waiting for keycloak realm import"
  sleep 10
  timeout=$(($timeout + 10))
done
{% endif %}
{% if keycloak_oauth %}
{% if keycloak_hostname %}
issuer=https://{{ keycloak_hostname }}/realms/{{ keycloak_realm }}
{% else %}
issuer=https://$host/realms/{{ keycloak_realm }}
{% endif %}
sed "s|KEYCLOAK_ISSUER|$issuer|" oauth.yml | oc apply -f -
echo "Keycloak is configured as oidc identity provider {{ keycloak_oauth_idp }}"
{% if keycloak_users %}
oc adm policy add-cluster-role-to-user cluster-admin {{ keycloak_admin }}
echo "Cluster role cluster-admin was granted to {{ keycloak_admin }}"
{% endif %}
{% endif %}
echo "Keycloak is available at https://$host"
echo "You can retrieve the initial admin credentials with those commands"
echo "oc -n {{ namespace }} get secret {{ keycloak_name }}-initial-admin -o jsonpath='{.data.username}' | base64 -d; echo"
echo "oc -n {{ namespace }} get secret {{ keycloak_name }}-initial-admin -o jsonpath='{.data.password}' | base64 -d; echo"
{% if keycloak_users %}
echo "Users {{ keycloak_admin }}, {{ keycloak_dev }} were imported in realm {{ keycloak_realm }}"
{% endif %}
{% endif %}
