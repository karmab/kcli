{% if register_acm and kubeconfig_acm == None %}
echo register_acm requires to set kubeconfig_acm && exit 1
{% endif %}
