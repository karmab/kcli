{% if register_acm %}
{% if kubeconfig_acm == None %}
echo register_acm requires kubeconfig_acm to be set && exit 1
{% else %}
KUBECONFIG={{ kubeconfig_acm }} oc get secret -n open-cluster-management open-cluster-management-image-pull-credentials >/dev/null 2&1 || echo missing open-cluster-management-image-pull-credentials secret on acm cluster && exit 1
{% endif %}
{% endif %}
