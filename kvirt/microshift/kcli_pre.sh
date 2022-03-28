{% if register_acm and kubeconfig_extra == None %}
echo register_acm requires to set kubeconfig_extra && exit 1
{% endif %}
