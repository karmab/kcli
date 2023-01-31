NAMESPACE={{ namespace|default("clusters") if hypershift|default(False) else 'openshift-config' }}
{% if hypershift|default(False) %}
oc patch hc -n $NAMESPACE $CLUSTER --type json -p '[{"op": "remove", "path": "/spec/configuration/oauth/identityProviders"}]'
{% else %}
oc patch oauth cluster --type=json -p '[{"op": "remove", "path": "/spec/identityProviders"}]'
{% endif %}
oc delete secret htpass-secret -n $NAMESPACE
